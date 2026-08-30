"""Load and evaluate clauses identically from development files or a shipped bundle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


# A construction anchor names a section of the page shipped beside this table. Shape only: the
# fence resolves it, so anything stricter here would be a second opinion about a fact the fence
# already owns -- and a wrong one, since rows may legitimately share a section.
# Public, because it now has readers outside this module: `dispatch` renders the pointer only
# when it matches, and `tests/test_fence.py` asserts the shape it names. One spelling of the
# anchor shape, read by everything that needs it.
CONSTRUCTION_ANCHOR = re.compile(r"POINTS\.md#[a-z0-9][a-z0-9-]*")

# The events a clause may target. A clause naming anything else is refused
# CLAUSE-EVENT-UNKNOWN by `_admit`, and because a single `_admit` failure makes the whole
# table unloadable -- which the dispatcher reports as a deny -- such a clause would deny
# every tool call, not merely fail to fire.
#
# This is a STRICT SUBSET of what the dispatcher routes, and that gap was undeclared: the
# plugin registers eight events in hooks.json and HANDLERS routes all eight, but only these
# five can carry enforcement. The other three are named below rather than left as an
# absence, so that adding a handler without deciding whether clauses may target it is a
# decision someone has to make out loud. `tests/test_event_surface.py` holds the two sets to
# exactly the dispatcher's own, so neither can drift alone.
_EVENTS = {
    "PreToolUse",
    "PostToolUse",
    "Stop",
    "SubagentStop",
    "SessionStart",
}

# Routed by the dispatcher and registered with the host, but deliberately NOT targetable by a
# clause. Each entry says why it is bookkeeping rather than an enforcement point. An event in
# neither this set nor `_EVENTS` is undecided, and the law in tests/test_event_surface.py
# goes red rather than letting it default to unenforceable in silence.
_NON_ENFORCING = {
    "SubagentStart": "seeds a subagent's session state; the obligations it seeds are enforced "
                     "at SubagentStop, which is where a subagent can still be denied",
    "UserPromptSubmit": "records the turn boundary. Denying here would refuse a prompt before "
                        "any tool is proposed, which is not what any clause in this table is "
                        "about",
    "PreCompact": "records that context was compacted. There is no act to permit or refuse, "
                  "and a deny would block compaction rather than any behaviour",
}


class ClauseError(Exception):
    def __init__(self, code: str, detail: Any):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True)
class Clause:
    id: str
    event: str
    tools: list[str]
    occasion: str
    costly: str
    guard: str
    subject: str
    fingerprint: dict[str, Any]
    discharged_by: dict[str, Any] | None
    window: str
    deny_reason: str
    fixtures_pos: list[Any]
    fixtures_neg: list[Any]
    # Optional, terminal clauses only. A clause with `activated_by` produces NO demand until
    # that predicate has been observed in the session, so a standing obligation waits for its
    # occasion instead of firing at every ending. Declared in the table rather than coded in
    # the dispatcher, like `unless` and `scope`.
    activated_by: dict[str, Any] | None = None
    # Commands that constitute the occasion. Required when activated_by is present:
    # a precondition nothing exercises is a precondition nobody can show works.
    fixtures_activate: list[Any] | None = None
    # Optional. Parks enforcement of THIS clause until `until`, because research established the
    # guard is not evaluable against the host. The clause stays in the table -- still loaded,
    # still admitted, still fixture-checked -- so a waiver hides no drift in the row itself.
    # {"until": "YYYY-MM-DD", "because": "...", "renewed": <int>}. The WAIVER is what is
    # default-dead, never the clause: on the day it lapses the clause enforces again and the
    # lapse is announced, so doing nothing restores the check rather than retiring it.
    waiver: dict[str, Any] | None = None
    # The clause's positive half: an anchor into the constructions page shipped beside this
    # table ("POINTS.md#a01"), naming what to build so this guard is never needed again.
    # "Every negative followed by its true positive" is a property this loader checks, not a
    # cross-document convention -- every row carries one, with no null case.
    #
    # SEVERAL ROWS MAY SHARE ONE ANCHOR. A point can need more than one row to enforce because
    # the rows key on different discharges, not because it is more than one point: P01 and P02
    # are one plan point split by which ground a step is missing. Pinning the fragment to the
    # row's own id would make that unrepresentable and force the page to say it twice. So this
    # loader checks SHAPE only; resolution against the page's actual headings, and that no
    # section is left unclaimed, is the test fence's half -- it owns the page, this owns the row.
    construction: str = ""


def waiver_status(clause: Clause, today: date | None = None) -> str:
    """`none`, `live`, or `expired` -- and anything unreadable is `expired`.

    A waiver parks ONE clause whose guard research has shown is not evaluable against the host,
    so a permanently undischargeable row stops blocking every ending. C08 is the case that forced
    it: its guard asks for a nonzero PostToolUse result, and the host sends no exit status in any
    form -- measured over 71 recorded Bash PostToolUse payloads, whose tool_response is always a
    dict keyed (stdout, stderr, interrupted, isImage, noOutputExpected). A clause that can be
    demanded and never discharged blocks forever, and the natural end of that is the whole gate
    being switched off, which costs all 24 clauses at once.

    The WAIVER is the thing that is default-dead, never the clause. `until` is a plain ISO date
    compared in UTC; on the day it lapses the clause enforces again with no edit and no renewal,
    so inaction restores the check rather than retiring it. A missing, non-string or unparseable
    `until` reads as `expired` for the same reason: a waiver nobody can read is not a waiver, and
    the safe fate is the clause doing its job. Renewal means arguing the research again and
    writing a new date; twice renewed is the signal to change the baseline, not the waiver.
    """
    waiver = getattr(clause, "waiver", None)
    if not isinstance(waiver, dict):
        return "none"
    raw = waiver.get("until")
    if not isinstance(raw, str):
        return "expired"
    try:
        until = date.fromisoformat(raw)
    except ValueError:
        return "expired"
    return "live" if (today or datetime.now(timezone.utc).date()) <= until else "expired"


def _resolve(event: dict[str, Any], dotted: str) -> Any:
    value: Any = event
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            return _MISSING
        value = value[part]
    return value


_MISSING = object()


def event_key(predicate: dict[str, Any] | None, event: dict[str, Any]) -> str:
    """Extract the cross-event correlation key declared by a predicate.

    A bare dotted path preserves the whole field.  The object form can normalize a field by
    retaining one regex group, which lets a PreToolUse command and its PostToolUse echo resolve
    to the same checker identity without making that identity the clause's ordinary subject.
    """
    if predicate is None:
        return ""
    spec = predicate.get("key_from")
    if isinstance(spec, str):
        on, pattern, group = spec, None, 1
    elif isinstance(spec, dict):
        on = spec.get("on") or ""
        pattern, group = spec.get("pattern"), spec.get("group", 1)
    else:
        return ""
    value = _resolve(event, on)
    if value is _MISSING:
        return ""
    if pattern is not None:
        if not isinstance(value, str):
            return ""
        match = re.search(pattern, value)
        if match is None:
            return ""
        try:
            value = match.group(group)
        except (IndexError, TypeError):
            return ""
    return str(value or "")[:200]


_READ_ONLY_PROBES = (("git", "status", "--porcelain"),)


# One probe result per (spec, process). A clause is scanned segment by segment and each scan is
# run twice, once for the act and once for the guard, so an 8-segment command asked the SAME
# question 16 times -- measured, 2N exactly. At the 5000 ms per-probe cap that is 80 s of blocked
# dispatch against a 20 s hook timeout, so the hook is canceled, renders no decision, and the deny
# row fails OPEN through the hang.
#
# The cache is module-level rather than threaded through five signatures because the lifetime is
# already correct by construction: hooks.json registers a `type: "command"` hook, so the
# dispatcher is a FRESH PROCESS per event and the module dies with it. Nothing needs to decide
# when to invalidate. Tests share one process, so they call reset_probe_cache() to get the same
# per-event scope production gets for free.
_PROBE_CACHE: dict[str, bool | None] = {}


def reset_probe_cache() -> None:
    """Restore per-event probe scope inside a process that handles more than one event."""
    _PROBE_CACHE.clear()


def _run_probe(spec: dict[str, Any]) -> bool | None:
    """Return the measured truth, or None when no measurement was obtained."""
    key = json.dumps(spec, sort_keys=True, separators=(",", ":"))
    if key in _PROBE_CACHE:
        return _PROBE_CACHE[key]
    _PROBE_CACHE[key] = result = _measure_probe(spec)
    return result


def _measure_probe(spec: dict[str, Any]) -> bool | None:
    try:
        completed = subprocess.run(
            spec["cmd"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=spec["timeout_ms"] / 1000, check=False,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        )
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None
    if completed.returncode != 0:
        return None
    output = completed.stdout.decode("utf-8", errors="replace")
    expect = spec["expect"]
    if expect == "empty":
        return output == ""
    if expect == "nonempty":
        return output != ""
    return re.search(expect["regex"], output) is not None


def _base_predicate(predicate: dict[str, Any], event: dict[str, Any]) -> bool:
    if predicate.get("event") is not None and event.get("hook_event_name") != predicate["event"]:
        return False
    tools = predicate.get("tools")
    if tools and tools != ["*"] and event.get("tool_name") not in tools:
        return False
    kind = predicate.get("kind")
    if kind == "always":
        return True
    value = _resolve(event, predicate.get("on", ""))
    if value is _MISSING:
        return False
    if kind == "tool":
        return value == predicate.get("equals")
    if kind == "nonzero":
        try:
            return int(value) != 0
        except (TypeError, ValueError):
            return False
    if kind == "regex":
        if not isinstance(value, str):
            return False
        if predicate.get("scope") == "segment":
            return any(_regex_predicate(predicate, segment) for segment in segments(value))
        return _regex_predicate(predicate, value)
    return False


def _regex_predicate(predicate: dict[str, Any], value: str) -> bool:
    if re.search(predicate["pattern"], value) is None:
        return False
    return all(
        re.search(entry, value) is None
        for entry in predicate.get("unless") or []
    )


def segments(command: str) -> list[str]:
    """Split shell control segments while preserving quoted operators.

    Two rules a naive scanner gets wrong, both measured before the fix:

    Backslash escapes only inside DOUBLE quotes. POSIX gives `\\` no special meaning inside
    single quotes, so treating it as an escape there makes `'a\\'` look unterminated and the
    rest of the line is swallowed into one segment: `'a\\' ; rm -rf /` returned a single
    segment, and `rm -rf /` was never seen as a segment start at all.

    An `&` after `<` or `>` is a REDIRECT, not a control operator. `make 2>&1 | tee log` split
    into `['make 2>', '1', 'tee log']` -- two segments that are not commands, and a real one
    whose text no longer resembles what ran.

    A NEWLINE IS A SEPARATOR, and leaving it out was a hole straight through the fence. A shell
    starts a new command at a newline exactly as it does at `;`, but this scanner did not, so
    `# note\nrm -rf build/` was ONE segment whose text begins with `#`. Measured on the shipped
    table: prefixing any command with a comment line allowed it -- `rm -rf build/`,
    `git push --force origin main`, `kill -9 1234`, `curl -X POST ...` all went from deny to
    allow behind two characters and a newline. A quoted newline still cannot separate, because
    the quote branch above consumes it like any other character, which is the same rule the
    other operators already follow.
    """
    out, buf, quote, i = [], [], "", 0
    while i < len(command):
        ch = command[i]
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = ""
            elif quote == '"' and ch == "\\" and i + 1 < len(command):
                i += 1
                buf.append(command[i])
        elif ch in "'\"":
            quote = ch
            buf.append(ch)
        elif ch in ";|&\n":
            if ch == "&" and buf and buf[-1] in "<>":
                buf.append(ch)
                i += 1
                continue
            if ch != "\n" and i + 1 < len(command) and command[i + 1] == ch:
                i += 1
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    out.append("".join(buf))
    return [segment.strip() for segment in out if segment.strip()]


def matching_segment(predicate: dict[str, Any], event: dict[str, Any]) -> str | None:
    """Return the first live segment for a segment-scoped predicate."""
    value = _resolve(event, predicate.get("on", ""))
    if predicate.get("scope") != "segment" or not isinstance(value, str):
        return None
    return next((segment for segment in segments(value)
                 if _regex_predicate(predicate, segment)), None)


def _predicate(predicate: dict[str, Any], event: dict[str, Any]) -> bool | None:
    # The cheap event fingerprint is the mandatory first gate. In particular, a missing field or
    # mismatch must not pay the process cost and must not let a failing probe affect this event.
    if not _base_predicate(predicate, event):
        return False
    probe = predicate.get("probe")
    return _run_probe(probe) if probe is not None else True


def match(clause: Clause, event: dict) -> bool:
    """Fails CLOSED. An unmeasurable probe is not permission.

    This returned None, and None is falsy, so every caller read "the clause does not fire" and
    ALLOWED the costly act -- while stderr printed "NOT-EVALUABLE, not a pass", asserting the
    opposite of what happened. A probe that cannot run (no git index, detached worktree, a 200ms
    timeout under load) silently disabled the clause it was added to strengthen. Measured: outside
    a git repo the destructive call was permitted.

    The occasion did not stop existing because the measurement failed. Treat it as firing: the
    guard is unproven, which is exactly what the demand is for.
    """
    result = _predicate(clause.fingerprint, event)
    if result is None:
        print(f"keel: [{clause.id}] probe NOT-EVALUABLE -- treating the occasion as live",
              file=sys.stderr)
        return True
    return result


def discharges(clause: Clause, event: dict) -> bool | None:
    if clause.discharged_by is None:
        return False
    result = _predicate(clause.discharged_by, event)
    if result is None:
        print(f"keel: [{clause.id}] probe NOT-EVALUABLE, not a pass", file=sys.stderr)
    return result


def _fixture_event(predicate: dict[str, Any], fixture: Any) -> dict[str, Any]:
    if isinstance(fixture, dict):
        return fixture
    event: dict[str, Any] = {}
    if predicate.get("event") is not None:
        event["hook_event_name"] = predicate["event"]
    tools = predicate.get("tools") or []
    if tools and tools != ["*"]:
        event["tool_name"] = tools[0]
    cursor = event
    parts = predicate.get("on", "").split(".")
    for part in parts[:-1]:
        child: dict[str, Any] = {}
        cursor[part] = child
        cursor = child
    if parts and parts[0]:
        cursor[parts[-1]] = fixture
    return event


# The ceiling on a clause's `probe.timeout_ms`. Not a preference, and not a number picked for
# feeling right: a probe runs INSIDE the hook, and a hook that reaches its own timeout is canceled
# with its output discarded -- it renders no decision at all, so a deny row becomes an allow. A
# probe allowed to outlive the hook hosting it is therefore a guaranteed fail-open. The bound that
# matters is the hook timeout declared in `hooks/hooks.json`, and `tests/test_bounds.py` holds this
# constant at or under it, so lowering that timeout goes red here instead of quietly permitting the
# hang. Sitting below rather than at it is a choice with a reason: the rest of the hook's work --
# scanning the segments, appending the journal row, rendering the decision -- has to fit the same
# budget. On exhaustion the child is killed and the predicate is treated as unsatisfied, never as
# assumed true.
PROBE_TIMEOUT_CEILING_MS = 5000


def _compile(predicate: dict[str, Any] | None, clause_id: str) -> None:
    if predicate is None:
        return
    if predicate.get("kind") == "regex":
        if predicate.get("scope", "field") not in ("field", "segment"):
            raise ClauseError("CLAUSE-SCOPE-INVALID", clause_id)
        try:
            re.compile(predicate.get("pattern", ""))
            for entry in predicate.get("unless") or []:
                re.compile(entry)
        except (re.error, TypeError) as exc:
            raise ClauseError("CLAUSE-REGEX-INVALID", f"{clause_id}: {exc}") from exc
    key_from = predicate.get("key_from")
    if key_from is not None:
        if isinstance(key_from, str):
            valid_key = bool(key_from)
        else:
            valid_key = (isinstance(key_from, dict)
                         and isinstance(key_from.get("on"), str)
                         and bool(key_from.get("on")))
        if not valid_key:
            raise ClauseError("CLAUSE-KEY-FROM-INVALID", clause_id)
        if isinstance(key_from, dict) and key_from.get("pattern") is not None:
            try:
                re.compile(key_from["pattern"])
            except (re.error, TypeError) as exc:
                raise ClauseError("CLAUSE-KEY-FROM-INVALID", f"{clause_id}: {exc}") from exc
            if not isinstance(key_from.get("group", 1), (int, str)):
                raise ClauseError("CLAUSE-KEY-FROM-INVALID", clause_id)
    probe = predicate.get("probe")
    if probe is None:
        return
    cmd, timeout, expect = probe.get("cmd"), probe.get("timeout_ms"), probe.get("expect")
    valid_expect = expect in ("empty", "nonempty") or (
        isinstance(expect, dict) and set(expect) == {"regex"} and isinstance(expect["regex"], str)
    )
    if not (isinstance(cmd, list) and cmd and all(isinstance(x, str) and x for x in cmd)
            and isinstance(timeout, int) and not isinstance(timeout, bool)
            and 0 < timeout <= PROBE_TIMEOUT_CEILING_MS
            and valid_expect):
        raise ClauseError("CLAUSE-PROBE-INVALID", clause_id)
    # Compare the WHOLE argv, and refuse any path separator. Normalising to the basename
    # let /tmp/evil/git and ./git through: an allowlist that bounds only the name bounds
    # nothing, because the gate then executes an attacker-chosen file with os.environ.
    if any(("/" in part or "\\" in part) for part in cmd[:1]):
        raise ClauseError("CLAUSE-PROBE-MUTATING", f"{clause_id}: path-qualified probe {cmd!r}")
    normalized = tuple(cmd)
    if normalized not in _READ_ONLY_PROBES:
        raise ClauseError("CLAUSE-PROBE-MUTATING", f"{clause_id}: {cmd!r}")
    if isinstance(expect, dict):
        try:
            re.compile(expect["regex"])
        except re.error as exc:
            raise ClauseError("CLAUSE-PROBE-INVALID", f"{clause_id}: {exc}") from exc


def _discriminator(clause: "Clause") -> dict:
    """Which predicate the fixtures test.

    For an ordinary clause it is the fingerprint: the fixtures say what the costly act looks
    like. For a TERMINAL clause the fingerprint is `always` -- every Stop is the occasion -- so
    the fingerprint discriminates nothing and the fixtures must test the GUARD instead. Getting
    this wrong makes a terminal clause unloadable for the wrong reason, which is how a whole
    clause shape gets quietly abandoned.
    """
    fp = clause.fingerprint or {}
    if fp.get("kind") == "always" and clause.discharged_by:
        return clause.discharged_by
    return fp


def _admit(clause: Clause) -> Clause:
    if clause.activated_by is not None and not clause.fixtures_activate:
        raise ClauseError("CLAUSE-NO-ACTIVATION-FIXTURES", clause.id)
    for fixture in clause.fixtures_activate or []:
        if not _base_predicate(clause.activated_by,
                               _fixture_event(clause.activated_by, fixture)):
            raise ClauseError("CLAUSE-ACTIVATION-FIXTURE-MISS", f"{clause.id}: {fixture!r}")
    if clause.event not in _EVENTS:
        raise ClauseError("CLAUSE-EVENT-UNKNOWN", f"{clause.id}: {clause.event}")
    if not clause.fixtures_pos or not clause.fixtures_neg:
        raise ClauseError("CLAUSE-NO-FIXTURES", clause.id)
    # THE PAIRING RULE IS NOT CHECKED HERE, and that placement is the fix. Every row names its
    # positive half, and this function used to raise when one did not -- at DISPATCH time, inside
    # the load that every hook invocation performs. `_admit` failing anywhere makes the whole
    # table unloadable, and an unloadable table is NOT-EVALUABLE, which the dispatcher correctly
    # reports as a deny. So a typo in ONE row's documentation pointer denied every tool call in
    # the session: `ls -la` came back
    # "keel could not evaluate this event: ClauseError -- NOT-EVALUABLE, not a pass".
    #
    # A documentation anchor is a BUILD fact. It cannot change between the build and the call, so
    # runtime strictness buys nothing that the build has not already bought -- and it charges for
    # it on every turn of every session. `tests/test_fence.py` owns the check instead, where it
    # belongs: it resolves every anchor against a real POINTS.md heading AND refuses a heading no
    # row claims, which is strictly more than the shape test that stood here, and a violation
    # costs a red build rather than a dead agent. `CONSTRUCTION_ANCHOR` is the shape the fence
    # asserts; it is defined here because this module owns the field.
    _compile(clause.fingerprint, clause.id)
    _compile(clause.activated_by, clause.id)
    _compile(clause.discharged_by, clause.id)
    disc = _discriminator(clause)
    for fixture in clause.fixtures_pos:
        if not _base_predicate(disc, _fixture_event(disc, fixture)):
            raise ClauseError("CLAUSE-FIXTURE-POS-MISS", f"{clause.id}: {fixture!r}")
    for fixture in clause.fixtures_neg:
        if _base_predicate(disc, _fixture_event(disc, fixture)):
            raise ClauseError("CLAUSE-FIXTURE-NEG-HIT", f"{clause.id}: {fixture!r}")
    return clause


def _load_object(data: dict[str, Any]) -> Clause:
    clause = Clause(
        id=data["id"],
        event=data["event"],
        tools=data["tools"],
        occasion=data["occasion"],
        costly=data["costly"],
        guard=data["guard"],
        subject=data["subject"],
        fingerprint=data["fingerprint"],
        discharged_by=data.get("discharged_by"),
        window=data["window"],
        deny_reason=data["deny_reason"],
        fixtures_pos=data["fixtures_pos"],
        fixtures_neg=data["fixtures_neg"],
        activated_by=data.get("activated_by"),
        fixtures_activate=data.get("fixtures_activate"),
        waiver=data.get("waiver"),
        construction=data.get("construction") or "",
    )
    return _admit(clause)


def _unique_sorted(clauses: list[Clause]) -> list[Clause]:
    seen: set[str] = set()
    for clause in clauses:
        if clause.id in seen:
            raise ClauseError("CLAUSE-ID-DUPLICATE", clause.id)
        seen.add(clause.id)
    return sorted(clauses, key=lambda clause: clause.id)


def load_bundle(path) -> list[Clause]:
    """Load one shipped table through the same parser and admission checks as loose files."""
    with Path(path).open(encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, list):
        raise ClauseError("CLAUSE-BUNDLE-INVALID", "top level is not a list")
    return _unique_sorted([_load_object(item) for item in data])


def default_bundle():
    """The one clause table this package loads. One file, and there is no second place."""
    return Path(__file__).resolve().with_name("clauses.json")


def load_default() -> list[Clause]:
    """Load the one shipped table.

    THERE USED TO BE A SECOND PATH HERE, and cutting it is the fix. `load_default` fell back to
    `load_dir(default_dir())` -- a folder of loose per-clause files -- whenever `clauses.json` was
    absent. That folder does not exist in this repository and never has; the loose form lives only
    in the frozen development archive, which is read-only and never executes this module. So the
    branch was unreachable in every layout that runs, which is bad enough, and worse than
    unreachable if it ever ran: not one of those archived files carries a `construction`, so the
    admission checks would have rejected every row it loaded. A fallback that cannot be reached,
    and would fail if it were, is not a safety net. It is a second answer to a question that has
    one, kept alive by nothing but the sentence that described it.

    A missing bundle now raises instead of silently returning some other table, and `main` already
    treats a table it cannot fill as NOT-EVALUABLE rather than as a clean run.
    """
    return load_bundle(default_bundle())
