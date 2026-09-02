"""Load and evaluate clauses identically from development files or a shipped bundle."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from . import effects as _effects


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


# The one field a command covering reads. Named once so the loader's admissibility
# rule and the predicates agree on what "reads the command" means.
COMMAND_FIELD = "tool_input.command"


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
    # The GUARD side's own fixtures. `fixtures_pos`/`fixtures_neg` discriminate the OCCASION and
    # say nothing about what discharges a clause, which left the guard half of all 24 points
    # un-witnessed by construction -- the loader had nothing to validate there, so a guard that
    # could be spent by a document loaded clean. C09 was exactly that, and the first run of these
    # fixtures found it.
    fixtures_discharge: list[Any] = field(default_factory=list)
    fixtures_no_discharge: list[Any] = field(default_factory=list)
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
    # There is no field for an excuse. A covering's class -- textual, nominal, composed over a
    # host enum, topological, positive -- is DERIVED from its shape by `classify_side`, and what
    # each class can and cannot be is a theorem in `proofs/Coverings.v`, instantiated on this
    # very row by the generated `proofs/Clauses.v`. A row that carried `why_no_program` or
    # `guard_vocabulary` was stating in prose what the proof decides; the loader now refuses
    # both (`CLAUSE-CARRIES-AN-EXCUSE`), and refuses a textual covering outright (Theorem 1:
    # no pattern edit can make it mention-immune), with no exemption to write.


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
    # COMPOSITION ACROSS FIELDS, and it has to live here rather than inside one kind. `any_of`
    # already existed, but only INSIDE `kind == "program"`, so it could only ever compose two
    # readings of `tool_input.command`. That made one act unexpressible: the SAME act performed
    # through a different host surface. Searching is `grep` in a Bash command AND it is the host's
    # own `Grep` tool -- one obligation, two surfaces, different `on` fields. With no top-level
    # composition the guard could name only one of them, so an agent that searched the ordinary
    # way was told it had not. Measured before this change: the `Grep` tool discharged neither
    # U12 nor U19.
    #
    # A predicate carrying `any_of`/`all_of` and NO `kind` of its own is therefore a COMPOSITION
    # of whole predicates, each evaluated on its own terms.
    if predicate.get("kind") is None:
        if predicate.get("any_of"):
            return any(_base_predicate(sub, event) for sub in predicate["any_of"])
        if predicate.get("all_of"):
            return all(_base_predicate(sub, event) for sub in predicate["all_of"])
    if predicate.get("event") is not None and event.get("hook_event_name") != predicate["event"]:
        return False
    tools = predicate.get("tools")
    if tools and tools != ["*"] and event.get("tool_name") not in tools:
        return False
    kind = predicate.get("kind")
    if kind == "always":
        return True
    if kind == "effect":
        # What the act DID, attached to the event by the dispatcher (or recorded in a fixture).
        # An unmeasured effect is None: not False, and `_predicate` reports it as NOT-EVALUABLE
        # rather than letting a composition read "could not see" as "did not happen".
        value = _resolve(event, "keel_effect." + str(predicate.get("effect", "")))
        return value is not _MISSING and value is not None and bool(value)
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
        return _regex_predicate(predicate, value)
    return False


def _regex_predicate(predicate: dict[str, Any], value: str) -> bool:
    if re.search(predicate["pattern"], value) is None:
        return False
    return all(
        re.search(entry, value) is None
        for entry in predicate.get("unless") or []
    )


def _predicate(predicate: dict[str, Any], event: dict[str, Any]) -> bool | None:
    # NOT-EVALUABLE IS LIVE FOR A COMPOSED SIDE TOO. This read only the predicate's own kind, so
    # a top-level `any_of` (which has none) let an unmeasured branch fall through as False: U20's
    # `head_reset` under a snapshot that could not see refs was "did not fire". Every effect leaf
    # is asked, so one branch the observer could not measure makes the side unmeasured.
    if any(leaf.get("kind") == "effect" and _unmeasured(leaf, event) for leaf in _leaves(predicate)):
        return None
    # The cheap event fingerprint is the mandatory first gate. In particular, a missing field or
    # mismatch must not pay the process cost and must not let a failing probe affect this event.
    if not _base_predicate(predicate, event):
        return False
    probe = predicate.get("probe")
    return _run_probe(probe) if probe is not None else True


def _unmeasured(predicate: dict[str, Any], event: dict[str, Any]) -> bool:
    """True when the event carries an effect record in which this effect is None.

    An event with NO record at all (a PreToolUse, a Stop that measured nothing) is simply not
    the surface this predicate reads, and that is False, not unmeasured. A record that says
    None for this effect is the observer saying it could not see -- the snapshot was missing,
    /proc was absent, git timed out -- and that is the case the fail-closed rule is for.
    """
    record = event.get("keel_effect")
    if not isinstance(record, dict):
        return False
    if predicate.get("event") is not None and event.get("hook_event_name") != predicate["event"]:
        return False
    tools = predicate.get("tools")
    if tools and tools != ["*"] and event.get("tool_name") not in tools:
        return False
    return record.get(str(predicate.get("effect", ""))) is None


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


def _matches_a_tool_enum(predicate: Any) -> bool:
    """True when some branch of the guard reads `tool_name`.

    This is what makes `composed` a CHECK rather than a claim: `tool_name` is a closed host
    enum, so a branch reading it covers the act however the operator spells the shell command.
    A clause may say it composed; this asks the table whether it did.
    """
    if not isinstance(predicate, dict):
        return False
    if predicate.get("on") == "tool_name":
        return True
    return any(_matches_a_tool_enum(sub)
               for sub in (predicate.get("any_of") or []) + (predicate.get("all_of") or []))


# Fields a row may not carry: each was a place to write, in English, what `classify_side` and
# the generated proof now decide. A requirement outside the math does not get an excuse.
EXCUSE_FIELDS = frozenset({"why_no_program", "guard_vocabulary", "waiver"})

def classify_side(predicate: Any) -> str:
    """The Coverings.v class of one covering, read from its shape. ONE owner.

    The loader refuses what the class forbids, and `tools/render_coverings.py` emits the
    theorem instance the class licenses, so the two cannot disagree about what a side is:

      always      fires on every event of its surface; the terminal shape (Thm 3 boundary)
      tool-enum   reads `tool_name`, a closed host enum: covered however the shell is spelled
      effect      reads what the act DID -- a worktree, ref, process, network or output delta
                  named in `keel.effects.EFFECTS` (Thm 8: name-agnostic; on the guard side a
                  datum the trace holds, or a report shape where no trace exists)
      positive    compares a datum the trace produced to one the report states (Thm 6, 7)
      composed    a composition of the classes above, every branch agnostic
      textual     reads the raw command as text (Thm 1: never mention-immune) -- refused
      nominal     selects on a program's name -- refused on every side (Thm 3, Thm 5)
    """
    if not isinstance(predicate, dict):
        return "absent"
    kind = predicate.get("kind")
    branches = (predicate.get("any_of") or []) + (predicate.get("all_of") or [])
    if branches:
        parts = {classify_side(dict(sub, kind=sub.get("kind", kind), on=sub.get("on", predicate.get("on"))))
                 for sub in branches}
        if "textual" in parts:
            return "textual"
        if "nominal" in parts:
            return "nominal"
        if len(parts) == 1:
            return parts.pop()
        if parts <= AGNOSTIC_CLASSES:
            return "composed"
        return "unclassified"
    if kind == "always":
        return "always"
    if kind == "effect":
        return "effect"
    if kind == "tool":
        return "tool-enum"
    if kind == "regex":
        if predicate.get("on") == "tool_name":
            return "tool-enum"
        return "textual" if predicate.get("on") == COMMAND_FIELD else "unclassified"
    if kind in ("program", "pipeline"):
        return "nominal"
    if kind == "nonzero":
        return "positive"
    return "unclassified"


# The classes a side may have, on EITHER side. Each is name-agnostic or is the Theorem 3
# boundary itself. A guard is discharged by a host tool call or by an observed effect of the
# discharging act, never by what the act was called: tool calls are agnostic, so nominal
# coverage of a guard has no excuse.
AGNOSTIC_CLASSES = frozenset({"always", "tool-enum", "effect", "positive", "composed"})


def derive_closure(predicate: Any) -> str:
    """Whether a side is closed, DERIVED from its class -- never declared.

    `host`: a closed host enum covers the act. `world`: the observer measures it. `datum`: a
    report is compared to the trace. There is no `open`: a side whose closure would be open
    is nominal, and the loader refuses it.
    """
    cls = classify_side(predicate)
    if cls in ("composed", "tool-enum"):
        return "host"
    if cls == "effect":
        return "world"
    if cls == "positive":
        return "datum"
    return cls


def subject_fields(spec: Any) -> list[str]:
    """The event fields a subject extractor may read, in order.

    ONE reading of `on`, called by everything that needs it. A subject may name several
    surfaces because an act and its guard do not always arrive through the same one -- a jq
    traversal carries its file in the command, the host `Read` that inspects the same file
    carries it in `tool_input.file_path`. Three call sites were about to spell this rule three
    times; the writer and the checker have to be the same line of code or they are not the
    same rule.
    """
    if isinstance(spec, dict):
        on = spec.get("on") or "tool_input.command"
    else:
        on = spec or ""
    if isinstance(on, str):
        return [on] if on else []
    return [f for f in on if isinstance(f, str) and f]


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
    # A string fixture is a command, so it is placed in the FIRST surface named. Fixtures for
    # the other surfaces ship as explicit dicts, which never reach this function.
    fields = subject_fields(predicate)
    parts = (fields[0] if fields else "").split(".")
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
    for leaf in _leaves(predicate):
        if leaf.get("kind") == "effect" and leaf.get("effect") not in _effects.EFFECTS:
            raise ClauseError("CLAUSE-EFFECT-UNKNOWN",
                              f"{clause_id}: {leaf.get('effect')!r} is not an effect the observer measures")
    if predicate.get("kind") == "regex":
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


def _leaves(predicate: dict[str, Any]) -> list[dict[str, Any]]:
    branches = (predicate.get("any_of") or []) + (predicate.get("all_of") or [])
    if not branches:
        return [predicate]
    return [leaf for sub in branches for leaf in _leaves(sub)]


AGNOSTIC_OCCASIONS = AGNOSTIC_CLASSES


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
    # THE CLASS OF EVERY SIDE IS CHECKED FIRST: a side the table may not carry is refused by
    # its shape, before any fixture is graded against it.
    for name in ("fingerprint", "activated_by", "discharged_by"):
        predicate = getattr(clause, name)
        if not isinstance(predicate, dict):
            continue
        if classify_side(predicate) == "textual":
            raise ClauseError(
                "CLAUSE-TEXT-COVERING",
                f"{clause.id}.{name}: reads the raw command as text; by Theorem 1 no pattern "
                f"edit makes that mention-immune, so it is refused with no exemption to write")
        if classify_side(predicate) == "unclassified":
            raise ClauseError(
                "CLAUSE-SIDE-UNCLASSIFIED",
                f"{clause.id}.{name}: no class in Coverings.v covers this shape")
        # AN OCCASION MUST BE NAME-AGNOSTIC. Theorem 3 says a nominal covering with a name in
        # and a name out is never name-agnostic; Theorem 5 says an unlisted spelling is a miss.
        # On the occasion side a miss is the costly act proceeding with its guard removed. So a
        # nominal occasion is refused outright: not carried as `open` with a theorem instance
        # documenting the gap, which is what this table did for sixteen sides, but refused.
        if name in ("fingerprint", "activated_by") and classify_side(predicate) not in AGNOSTIC_CLASSES:
            raise ClauseError(
                "CLAUSE-OCCASION-NOMINAL",
                f"{clause.id}.{name}: selects the act by the program's name; an act spelled "
                f"under another name proceeds unguarded (Theorem 3, Theorem 5)")
        # A GUARD MUST BE NAME-AGNOSTIC TOO. Tool calls are agnostic: a guard is discharged by
        # a host tool call (the closed `tool_name` enum) or by an observed effect of the
        # discharging act (a datum the trace holds, a report shape where no trace exists),
        # never by what the act was called. Nominal coverage of a guard fails closed, which is
        # the cheap direction -- and it is still a list of spellings standing in for an
        # observation, with no excuse. Refused, not carried as `open`.
        if name == "discharged_by" and classify_side(predicate) not in AGNOSTIC_CLASSES:
            raise ClauseError(
                "CLAUSE-GUARD-NOMINAL",
                f"{clause.id}.{name}: names the program that discharges; a guard is a host "
                f"tool call or an observed effect of the guard act, never a spelling")
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
    # A COVERING OVER THE COMMAND IS AN INVOCATION, OR IT SAYS WHY NOT -- enforced HERE, in the
    # product, rather than only in the suite. The rule was written as a test first, and the field
    # law caught that: `why_no_program` was read by the suite and by nothing the plugin runs, so
    # the suite was asserting a property of the table instead of a property of the plugin. This
    # is the same shape as the merged Swale loader refusing a row that carries neither
    # `construction` nor `why_none` -- the loader is where an admissibility rule belongs, because
    # a table that cannot state why it reads raw text is a table nobody should be able to ship.
    #
    # Matching TEXT against the command cannot tell an invocation from a mention: `echo 'first;
    # git status'` discharged a push guard, measured, because the pattern's own separator
    # alternation matched a `;` inside quotes. No side reads the command as text.
    # An effect is observed AFTER the act, so a clause whose occasion is an effect is enforced at
    # PostToolUse: the demand is raised there, the next call is denied until the guard is seen.
    if classify_side(clause.fingerprint) == "effect" and clause.event != "PostToolUse":
        raise ClauseError("CLAUSE-EFFECT-EVENT",
                          f"{clause.id}: an effect occasion is observed after the act; declare PostToolUse")
    disc = _discriminator(clause)
    for fixture in clause.fixtures_pos:
        if not _base_predicate(disc, _fixture_event(disc, fixture)):
            raise ClauseError("CLAUSE-FIXTURE-POS-MISS", f"{clause.id}: {fixture!r}")
        # A FIXTURE THE CLAUSE CANNOT KEY IS NOT EVIDENCE THAT THE CLAUSE COVERS IT.
        #
        # Matching the fingerprint was the whole admission test, and the dispatcher needs one
        # thing more: a dict `subject` is an EXTRACTOR, and when it finds no operand the clause
        # abstains -- `dispatch.pre_tool_use` treats an empty key as NOT-EVALUABLE and passes the
        # event, because denying under the empty key would merge every demand for the clause into
        # one bucket. That abstention is right. What was wrong is that a positive fixture could
        # match the fingerprint, be admitted as evidence that the clause covers that occasion,
        # and then be silently unenforceable.
        #
        # Measured when this was added: A02 declared three positive fixtures and could deny only
        # one. `git clean -fd` and `find . -name '*.tmp' -delete` name no trailing-slash path, so
        # its extractor returned "" and the dispatcher allowed both -- a bulk delete passing the
        # clause written to stop it, with the fixture list asserting the opposite.
        if isinstance(clause.subject, dict):
            keyed = _fixture_event(clause.subject, fixture)
            fields = subject_fields(clause.subject)
            value = _resolve(keyed, fields[0] if fields else "")
            found = (re.search(clause.subject["pattern"], value)
                     if isinstance(value, str) and clause.subject.get("pattern") else None)
            if not (found and found.group(clause.subject.get("group", 0))):
                raise ClauseError(
                    "CLAUSE-FIXTURE-POS-UNKEYABLE",
                    f"{clause.id}: {fixture!r} matches the fingerprint but the subject extractor "
                    f"finds no operand in it, so the clause abstains and this occasion is never "
                    f"denied")
    for fixture in clause.fixtures_neg:
        if _base_predicate(disc, _fixture_event(disc, fixture)):
            raise ClauseError("CLAUSE-FIXTURE-NEG-HIT", f"{clause.id}: {fixture!r}")
    # THE GUARD SIDE, WITNESSED IN BOTH DIRECTIONS -- and enforced HERE rather than in a test.
    #
    # Everything above discriminates the OCCASION. Nothing declared what DISCHARGES a clause, so
    # the guard half of every point was un-witnessed by construction: the loader had nothing to
    # check, and a guard that a document could spend loaded clean. That is the asymmetric
    # direction -- a false discharge removes the guard while the costly act proceeds.
    #
    # The event is built by `_fixture_event` from the guard's OWN declaration, so a guard reading
    # `tool_name` takes tool names and C08's `nonzero` guard on `tool_response.exit_code` at
    # PostToolUse takes exit codes, without this law knowing anything special about either.
    #
    # Every command-string `fixtures_no_discharge` set carries the ECHO-MENTION of one of its own
    # positives. That single case is what found C09: `echo 'ps aux | grep -v $$'` discharged the
    # guard, so an agent that never listed a process could claim it had.
    # A clause with NO discharge predicate has no guard side to witness -- `clauses/fixtures/E3`
    # is guarded by a PROBE on its fingerprint, and demanding discharge fixtures of it would be
    # demanding evidence about a predicate that does not exist. The exemption is exactly that
    # narrow: it keys on the predicate's absence, not on any declared opt-out, so a clause cannot
    # buy its way out of this law by claiming one.
    if clause.discharged_by is None:
        return clause
    if not clause.fixtures_discharge or not clause.fixtures_no_discharge:
        raise ClauseError("CLAUSE-NO-GUARD-FIXTURES", clause.id)
    for fixture in clause.fixtures_discharge:
        if not _base_predicate(clause.discharged_by,
                               _fixture_event(clause.discharged_by, fixture)):
            raise ClauseError("CLAUSE-GUARD-FIXTURE-MISS", f"{clause.id}: {fixture!r}")
    for fixture in clause.fixtures_no_discharge:
        if _base_predicate(clause.discharged_by,
                           _fixture_event(clause.discharged_by, fixture)):
            raise ClauseError("CLAUSE-GUARD-FIXTURE-HIT", f"{clause.id}: {fixture!r}")
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
        fixtures_discharge=data.get("fixtures_discharge") or [],
        fixtures_no_discharge=data.get("fixtures_no_discharge") or [],
        construction=data.get("construction") or "",
    )
    carried = sorted(EXCUSE_FIELDS & set(data))
    if carried:
        raise ClauseError(
            "CLAUSE-CARRIES-AN-EXCUSE",
            f"{data.get('id')}: {carried} state in prose what the proof derives; delete them")
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
