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
    # of whole predicates, each evaluated on its own terms. `kind`-bearing predicates are
    # untouched, so U20's and U24's existing program-level `any_of` keeps its current meaning --
    # this branch cannot reach them, because they declare a `kind`.
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
    if kind == "program":
        if not isinstance(value, str):
            return False
        # `any_of` composes whole program-predicates rather than widening one. U20's occasion is
        # three unrelated invocations -- a bare `rm`, `git reset --hard`, `find ... -delete` --
        # whose flag requirements differ per program. Folding them into one `then_matches` would
        # either demand a flag of `rm` that it does not take, or make `--hard` optional for `git
        # reset`, and the second is a false positive on every `git reset --soft`.
        alternatives = predicate.get("any_of")
        if alternatives is not None:
            return any(
                _base_predicate(dict(alt, kind="program", on=predicate.get("on", "")), event)
                for alt in alternatives
            )
        return any(_segment_matches_program(predicate, segment) for segment in segments(value))
    if kind == "pipeline":
        if not isinstance(value, str):
            return False
        return _pipeline_predicate(predicate, value)
    return False


def _pipeline_predicate(predicate: dict[str, Any], value: str) -> bool:
    """An invocation FEEDING another -- the relation `kind: program` cannot state.

    A program predicate asks what one segment ran. C09's occasion is not one invocation but the
    join between two: a process listing whose output is consumed by a matcher excluding the
    checker's own pid. Both halves are ordinary segment questions; only the EDGE between them
    was unexpressible, because the operator was discarded by the splitter.

    `upstream` is a full program predicate, so the leading-argv machinery (wrappers, `sh -c`,
    delegated runners) is reused rather than restated -- one owner for "what ran".

    Downstream is searched THROUGH a chain of pipes: `ps aux | grep foo | grep -v $$` feeds the
    listing to the exclusion just as directly as the two-stage form, and stopping at the first
    stage would let one extra filter walk the guard. The walk stops at the first operator that
    is not the pipe, because `;` and `||` do not feed anything.

    This is also what closes the mention hole that `kind: regex` left open on this clause: a
    quoted `echo 'ps aux | grep -v $$'` is ONE segment with no following operator, so there is
    no edge to match and the guard is not spent by a document.
    """
    operator = predicate.get("operator", "|")
    downstream = predicate.get("downstream_matches")
    if downstream is None:
        return False
    upstream = dict(predicate.get("upstream") or {}, kind="program")
    pipeline = segment_pipeline(value)
    for index, (text, joins) in enumerate(pipeline):
        if joins != operator or not _segment_matches_program(upstream, text):
            continue
        following = index
        while following < len(pipeline) and pipeline[following][1] == operator:
            following += 1
            if re.search(downstream, pipeline[following][0]):
                return True
    return False


def _regex_predicate(predicate: dict[str, Any], value: str) -> bool:
    if re.search(predicate["pattern"], value) is None:
        return False
    return all(
        re.search(entry, value) is None
        for entry in predicate.get("unless") or []
    )


_WRAPPERS = frozenset({"sudo", "env", "time", "nice", "exec", "command", "builtin"})


_INTERPRETERS = re.compile(r"^python[0-9.]*$")


# A shell reached with `-c` EXECUTES its argument. Measured before this existed: `bash -c 'git
# push origin main'` read as argv ['bash', 'git'] and A01 DID NOT FIRE, while the identical plain
# push did -- so seven characters of prefix walked any command past the whole table. That is a
# MISSED ACTIVATION, and a missed activation is not the cheap direction: the costly act proceeds
# with its guard removed, which is exactly what a false discharge buys. The argument is re-parsed
# as the command it is, which cannot reopen the mention hole -- reaching this branch requires a
# shell to have been INVOKED with `-c`, not a string that merely looks like one.
_SHELLS = frozenset({"sh", "bash", "zsh", "dash", "ksh", "ash", "fish"})

# Launchers whose job is to run ANOTHER program in a prepared environment. `python3 -m pytest`
# was already normalised to `pytest`; `uv run pytest` was not, and read as ['uv', 'run'] -- the
# same invocation, seen differently because one route was Python's and the other was not. The
# table is what removes that privilege: the delegated program is the subject in every ecosystem,
# not only where the interpreter happens to be CPython.
_RUN_LAUNCHERS = frozenset({"uv", "poetry", "pipenv", "pdm", "rye", "hatch", "nix"})
_DIRECT_LAUNCHERS = frozenset({"npx", "bunx", "pnpx", "dlx"})

# Options that consume the NEXT token as their value, per program. Finite and declared rather
# than inferred: a value we fail to consume becomes a phantom subcommand, and a subcommand we
# invent is a clause matching something that never ran. Only git's documented pre-subcommand
# globals are listed, because those are the ones that can appear BEFORE the subcommand at all.
# Options that are KNOWN to take no value, so the subcommand behind them is still reachable.
# Declared for the same reason the value-taking set is: the alternative to a declaration here is
# a guess, and a guess in this position forges a subcommand.
_NO_VALUE_OPTIONS = {
    "npm": frozenset({"--silent", "--quiet", "-s", "--verbose", "--no-color"}),
    "yarn": frozenset({"--silent", "--verbose"}),
    "pnpm": frozenset({"--silent"}),
    "cargo": frozenset({"--quiet", "-q", "--verbose", "-v", "--offline", "--locked", "--release"}),
    "go": frozenset({"-v", "-x"}),
    "deno": frozenset({"-A", "--quiet"}),
    "docker": frozenset({"--debug"}),
    "git": frozenset({"--no-pager", "--paginate", "--bare", "--literal-pathspecs"}),
}


# Interpreter options taking a SEPARATE value token, so a `-m` scan does not halt on the value.
# `-W error` is the shape U24 turns on; `-Werror` (joined) needs no entry, it is one token.
_INTERPRETER_VALUE_OPTIONS = frozenset({"-W", "-X", "--check-hash-based-pycs"})

_VALUE_OPTIONS = {
    "git": frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}),
}


def _invocation_scan(segment: str) -> tuple[dict[str, str], list[str], list[str]]:
    """The segment's ENVIRONMENT ASSIGNMENTS and its tokens from the invoked program onward.

    One owner for the stripping rules -- and it now RETURNS the env prefix instead of dropping
    it. The drop was the same defect as the discarded pipe operator: the scanner identified the
    `VAR=value` tokens and then threw them away one line later, so the only signal distinguishing
    a warnings-as-errors run from an ordinary suite run was invisible to every predicate BY
    CONSTRUCTION. U24 said exactly that in its `why_no_program`, and it was true because the fact
    had already been deleted before any predicate could ask.

    The same applies to the INTERPRETER'S OWN OPTIONS. `python -W error -m pytest` is a suite run
    configured to promote warnings, and skipping past `-W error` to reach `pytest` discarded the
    one token that said so -- the third instance of this identical shape, after the pipe operator
    and the env prefix. They are returned as `opts`.

    `leading_argv`, `leading_env` and `leading_opts` are thin readers over this, so they cannot
    drift apart."""
    env: dict[str, str] = {}
    opts: list[str] = []
    tokens = segment.split()
    index = 0
    while index < len(tokens):
        # Quotes and a subshell's opening paren are SHELL SYNTAX, not part of the program name.
        # Measured against this estate's own gates: `( cd "$STAGE" && "$VENV/bin/python" -m
        # pytest ... )` yielded `python"` with the quote attached, so the interpreter was not
        # recognised and the pytest behind it was invisible.
        token = tokens[index].strip("\"'()")
        if not token:
            index += 1
            continue
        if "=" in token and not token.startswith("-") and token.split("=", 1)[0].isidentifier():
            name_part, value_part = token.split("=", 1)
            env[name_part] = value_part.strip("\"'")
            index += 1          # VAR=value prefix: recorded, no longer discarded
            continue
        # The BASENAME decides, because an interpreter is just as much an interpreter when it is
        # reached by path: `"$VENV/bin/python" -m pytest` is a pytest run, and testing the whole
        # token against the interpreter pattern says it is not.
        name = token.rsplit("/", 1)[-1]
        if name in _WRAPPERS:
            index += 1
            continue
        if _INTERPRETERS.match(name):
            # Skip the INTERPRETER's own options before looking for `-m`. Measured:
            # `python -W error -m pytest` read argv[0] as `-W`, so a warnings-as-errors suite run
            # -- the exact command U24's guard exists to recognise -- was not seen as a pytest run
            # at all. `-m` is not at a fixed offset the moment any interpreter flag precedes it.
            probe = index + 1
            while probe < len(tokens) and tokens[probe].startswith("-") and tokens[probe] != "-m":
                if tokens[probe] in _INTERPRETER_VALUE_OPTIONS and probe + 1 < len(tokens):
                    opts.append(f"{tokens[probe]} {tokens[probe + 1].strip(chr(34) + chr(39))}")
                    probe += 2
                else:
                    opts.append(tokens[probe])
                    probe += 1
            if probe + 1 < len(tokens) and tokens[probe] == "-m":
                module = tokens[probe + 1].strip("\"'").rsplit(".", 1)[-1]
                return env, opts, [module, *tokens[probe + 2:]]
            # No `-m`: the interpreter runs a SCRIPT, and the same option skip applies -- landing
            # on `-W` would report the flag as the program. `probe` already sits past the options.
            index = probe
            continue
        # A shell's `-c` argument IS the command. Re-parse it and answer about what it runs.
        if name in _SHELLS:
            rest = tokens[index + 1:]
            if "-c" in rest:
                inner = " ".join(rest[rest.index("-c") + 1:]).strip("\"'")
                # Guarded against a self-referential `sh -c "sh -c ..."` chain: one unwrap per
                # level, and an empty argument answers nothing rather than answering about `sh`.
                if not inner.strip():
                    return env, opts, []
                inner_env, inner_opts, inner_tokens = _invocation_scan(inner)
                return {**env, **inner_env}, opts + inner_opts, inner_tokens
        # `uv run pytest` and `python3 -m pytest` are one invocation reached two ways.
        if name in _RUN_LAUNCHERS and index + 2 < len(tokens) and tokens[index + 1] == "run":
            inner_env, inner_opts, inner_tokens = _invocation_scan(" ".join(tokens[index + 2:]))
            return {**env, **inner_env}, opts + inner_opts, inner_tokens
        if name in _DIRECT_LAUNCHERS and index + 1 < len(tokens):
            inner_env, inner_opts, inner_tokens = _invocation_scan(" ".join(tokens[index + 1:]))
            return {**env, **inner_env}, opts + inner_opts, inner_tokens
        return env, opts, [name, *tokens[index + 1:]]
    return env, opts, []


def _invocation_tokens(segment: str) -> list[str]:
    """The tokens reader over `_invocation_scan`. Every existing caller reads exactly this."""
    return _invocation_scan(segment)[2]


def leading_env(segment: str) -> dict[str, str]:
    """The environment assignments a segment sets for the program it runs.

    The primitive U24's exemption named as missing. It is a fact about the ACT -- the run was
    configured to promote warnings -- not a word in the command, so a covering over it is
    name-agnostic and cannot be spent by a mention: a quoted `echo '...'` sets no variables."""
    return _invocation_scan(segment)[0]


def leading_opts(segment: str) -> list[str]:
    """The interpreter options a segment ran under -- `-W error`, `-X dev`.

    A fact about how the act was CONFIGURED, not a word in it: `echo '...'` runs no interpreter,
    so this is empty for a mention without any pattern being consulted."""
    return _invocation_scan(segment)[1]


def leading_operands(segment: str) -> list[str]:
    """Every token the invoked program received -- flags, values and paths alike.

    `leading_argv` deliberately stops at the subcommand, because its job is to say WHICH program
    ran. That truncation is right for it and wrong for a covering that turns on what the program
    was POINTED AT: `go test ./scanner -run Acceptance` reduces to `['go', 'test']` there, and
    the target disappears. Same shape as the discarded pipe operator, the discarded env prefix
    and the discarded interpreter options -- computed by the scanner, then dropped before any
    predicate could ask. Read from the scan, so the mention still yields nothing."""
    return _invocation_scan(segment)[2][1:]


def leading_argv(segment: str) -> list[str]:
    """The argv a shell segment actually EXECUTES, program first, wrappers and env stripped.

    `leading_program` is this function's first element and delegates to it, so the rule for what
    counts as the invoked program is written ONCE. Two copies of that walk is precisely how a
    predicate starts disagreeing with the discharge it is paired with.

    WHY MORE THAN THE PROGRAM NAME. `leading_program` returns `git` for `git push` and for `git
    status` alike, so it can distinguish a checker by its script name -- C08's case -- and cannot
    distinguish the eighteen clauses of this table whose occasion and guard are BOTH `git
    <subcommand>`. The discriminator there is the subcommand, and the subcommand is the first
    argument that is not an option.
    """
    tokens = _invocation_tokens(segment)
    if not tokens:
        return []
    argv = [tokens[0]]
    takes_value = _VALUE_OPTIONS.get(tokens[0], frozenset())
    index = 1
    while index < len(tokens):
        token = tokens[index].strip("\"'")
        if token.startswith("-"):
            # `--opt=value` carries its own value; `-C dir` consumes the next token. An option
            # whose value we failed to consume would land in the subcommand slot: `git -C /tmp
            # status` read as subcommand `/tmp`, and the clause would never match a real one.
            if "=" not in token and token in takes_value:
                index += 2
                continue
            if "=" in token or token in _NO_VALUE_OPTIONS.get(argv[0], frozenset()):
                index += 1
                continue
            # REFUSE RATHER THAN GUESS. Whether an unlisted option consumes the next token is
            # not knowable from the command text, and guessing "it does not" was measured to
            # FORGE a subcommand: `npm --prefix test install` read as ['npm', 'test'], byte-
            # identical to a real `npm test`, so a clause discharging on the test run was
            # licensed by a command that ran no tests. Answering [program] instead loses the
            # narrowing and costs an interruption; inventing a subcommand removes a guard. The
            # asymmetry decides, and the fix for the loss is to DECLARE the option, not to guess.
            return [argv[0]]
        argv.append(token)
        break   # STOP AT THE FIRST ONE. Everything after belongs to the subcommand, not to the
                # invocation: scanning on would read `git commit -m push` as `git push` and
                # match a clause about pushing on a commit -- a false LICENCE, the one direction
                # this table cannot afford to be wrong in.
    return argv


def leading_program(segment: str) -> str:
    """The program a shell segment actually EXECUTES, as a bare basename.

    WHY A PROGRAM AND NOT A PATTERN. Every other predicate in this table matches text against
    the command about to run, which is the right instrument when the guard IS a look -- `git
    status` before a push is a look whose occurrence is its own success, and a regex sees it.
    It is the wrong instrument when the guard is a JUDGEMENT some program renders: whether a
    checker can fail, whether a push landed, whether a rewrite preserved behaviour. Those have
    answers, the answers are exit codes, and matching the text of the question is not reading
    the answer. This function is what lets a clause name the program instead.

    LEADING, not anywhere. The token must be what the segment invokes, so a program named
    inside an argument does not discharge anything: `grep meta_test.py notes.md` reads a file
    ABOUT the guard and runs no guard. That is the same failure the sibling estate's exit-mask
    recognizer documents ("The runner must be the LEADING command of a statement (an actual
    invocation), NOT an argument"), and it is worth restating here because a discharge is a
    licence -- a false one is strictly worse than a missed one, which merely blocks.

    Interpreter and wrapper prefixes are stripped so one name covers the spellings a caller
    actually types: `python3 tools/x.py`, `./tools/x.py`, `env python3 tools/x.py` and
    `tools/x.py` all yield `x.py`. `python3 -m pytest` yields `pytest`, because the module IS
    the program there. A leading VARIABLE ASSIGNMENT is skipped rather than returned: C08's own
    `_note` records a live session where `F=plugin/.../writeThrashRevert.py` was taken for a
    checker, keying 19 demand rows on a token naming nothing runnable.
    """
    tokens = _invocation_tokens(segment)
    return tokens[0] if tokens else ""


def _scan(command: str) -> list[tuple[str, str]]:
    """Split shell control segments, KEEPING the operator that joined them.

    Each entry is `(segment text, the operator that FOLLOWS it)` -- `""` for the last.

    The operator used to be computed here and dropped one line later, and that discard was
    itself a defect. A `|` means the next command EATS this one's output; a `;` means only
    that it runs after. C09's whole subject is the difference -- `ps ... | grep -v $$`, a
    process listing that excludes the checker itself -- and with the operator gone no
    predicate could see it. Its `why_no_program` says argv on `ps` "fires on every process
    listing whether or not it is piped into a matcher", which was true precisely because the
    pipe fact had already been deleted before any predicate ran.

    `||` and `&&` are recorded whole and are NOT pipes: `a || b` runs b when a FAILS, which is
    the opposite of feeding it. Reading `||` as `|` would license the guard on a command whose
    matcher may never have run at all.

    Two rules a naive scanner gets wrong, both measured before the fix:

    Backslash escapes only inside DOUBLE quotes. POSIX gives `\\` no special meaning inside
    single quotes, so treating it as an escape there makes `'a\\'` look unterminated and the
    rest of the line is swallowed into one segment: `'a\\' ; rm -rf /` returned a single
    segment, and `rm -rf /` was never seen as a segment start at all.

    An `&` after `<` or `>` is a REDIRECT, not a control operator. `make 2>&1 | tee log` split
    into `['make 2>', '1', 'tee log']` -- two segments that are not commands, and a real one
    whose text no longer resembles what ran.

    A HEREDOC BODY IS DATA, NOT COMMANDS, and this is the third rule, measured the same way. The
    scanner read `cat <<EOF\n; git rev-parse --verify main\nEOF` as two segments and handed the
    second to the predicates as though something had run it -- so U09 DISCHARGED on a heredoc
    that executed nothing, and the guard it protects was spent by a document. Quoting was already
    handled and heredocs were not, which left the exact same hole one syntax over: text the shell
    never executes, read as an invocation. The body is consumed to its delimiter and contributes
    no segment; the `cat <<EOF` line itself still does, because that command really does run.
    """
    out, buf, quote, i = [], [], "", 0
    pending_heredocs: list[tuple[str, bool]] = []
    while i < len(command):
        ch = command[i]
        # `<<WORD` / `<<-WORD` / `<<"WORD"`: remember the delimiter, keep scanning this line.
        if not quote and ch == "<" and command[i:i + 2] == "<<":
            j = i + 2
            strip_tabs = j < len(command) and command[j] == "-"
            j += 1 if strip_tabs else 0
            while j < len(command) and command[j] in " \t":
                j += 1
            k, delim_quote = j, ""
            if k < len(command) and command[k] in "'\"":
                delim_quote = command[k]
                k += 1
                start = k
                while k < len(command) and command[k] != delim_quote:
                    k += 1
                word = command[start:k]
                k += 1
            else:
                start = k
                while k < len(command) and (command[k].isalnum() or command[k] in "_-."):
                    k += 1
                word = command[start:k]
            if word:
                pending_heredocs.append((word, strip_tabs))
                buf.append(command[i:k])
                i = k
                continue
        if not quote and ch == "\n" and pending_heredocs:
            # Close the line, then swallow every pending body without scanning it.
            out.append(("".join(buf), "\n"))
            buf = []
            i += 1
            for word, strip_tabs in pending_heredocs:
                while i < len(command):
                    end = command.find("\n", i)
                    line = command[i:] if end == -1 else command[i:end]
                    i = len(command) if end == -1 else end + 1
                    if (line.lstrip("\t") if strip_tabs else line).strip() == word:
                        break
            pending_heredocs = []
            continue
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
            # A NEWLINE IS A SEPARATOR. A shell starts a new command at a newline exactly as it
            # does at `;`, and omitting it was a hole straight through the fence: `# note\nrm -rf
            # build/` was ONE segment whose text begins with `#`, so prefixing any command with a
            # comment line walked it past the table -- measured on the shipped clauses, `rm -rf
            # build/`, `git push --force origin main` and `kill -9 1234` all went from deny to
            # allow behind two characters and a newline. That is a MISSED ACTIVATION, which costs
            # what a false discharge costs: the act proceeds with its guard removed. A quoted
            # newline still cannot separate, because the quote branch above consumes it first --
            # the same rule the other operators already follow. `\n\n` is not a `||`-style
            # doubled operator, so the doubling skip below must not apply to it.
            if ch == "&" and buf and buf[-1] in "<>":
                buf.append(ch)
                i += 1
                continue
            operator = ch
            if ch != "\n" and i + 1 < len(command) and command[i + 1] == ch:
                operator = ch * 2
                i += 1
            out.append(("".join(buf), operator))
            buf = []
        else:
            buf.append(ch)
        i += 1
    out.append(("".join(buf), ""))
    return [(text.strip(), operator) for text, operator in out if text.strip()]


def segments(command: str) -> list[str]:
    """The segment texts alone -- the shape every caller but the pipeline predicate reads."""
    return [text for text, _ in _scan(command)]


def segment_pipeline(command: str) -> list[tuple[str, str]]:
    """Segments paired with the operator that follows each. See `_scan`."""
    return _scan(command)


def _segment_matches_program(predicate: dict[str, Any], segment: str) -> bool:
    """Does THIS one segment satisfy the invocation predicate? One owner, used by both callers."""
    alternatives = predicate.get("any_of")
    if alternatives is not None:
        return any(_segment_matches_program(dict(alt), segment) for alt in alternatives)
    argv = leading_argv(segment)
    if not argv:
        return False
    if any(re.search(entry, segment) for entry in predicate.get("unless") or []):
        return False
    then = predicate.get("then_matches")
    if then is not None and not re.search(then, segment):
        return False
    # HOW the act was configured, not what it is called. `env` and `opts` are facts about the
    # invocation -- a mention sets no variables and runs no interpreter -- so a covering over
    # them is name-agnostic and cannot be spent by quoting the command. They CONSTRAIN a match
    # rather than granting one: the argv test below still has to succeed.
    wanted_env = predicate.get("env")
    if wanted_env is not None:
        actual = leading_env(segment)
        if not any(name in actual and re.search(want, actual[name])
                   for name, want in wanted_env.items()):
            return False
    wanted_opts = predicate.get("opts")
    if wanted_opts is not None:
        actual_opts = leading_opts(segment)
        if not any(re.search(want, opt) for want in wanted_opts for opt in actual_opts):
            return False
    # WHAT the program was pointed at. The arguments are already in `argv`; nothing could read
    # them, so U25 -- whose two sides are the same runner with different targets -- had to fall
    # back to matching the raw command text. This reads the parsed operands instead, so the
    # quoted forms that defeat a text pattern never reach it.
    wanted_args = predicate.get("args")
    if wanted_args is not None:
        operands = leading_operands(segment)
        if not any(re.search(want, operand) for want in wanted_args for operand in operands):
            return False
    names, pattern = predicate.get("names"), predicate.get("pattern")
    if names is not None and argv[0] in names:
        return True
    if pattern is not None and re.fullmatch(pattern, argv[0]):
        return True
    for wanted in predicate.get("argv") or []:
        if list(wanted) == argv[:len(wanted)]:
            return True
    return False


def matching_segment(predicate: dict[str, Any], event: dict[str, Any]) -> str | None:
    """Return the first live segment for a segment-scoped predicate."""
    value = _resolve(event, predicate.get("on", ""))
    if not isinstance(value, str):
        return None
    # The program kind is segment-scoped BY CONSTRUCTION -- it matches the leading argv of a
    # segment -- so it belongs here whether or not the clause spells `scope`. Leaving this
    # regex-only was measured wrong: for `git apply --check checked.patch; git apply live.diff
    # --index`, the subject came back `checked.patch`, naming the file that was CHECKED as the
    # subject of the apply that ran on another. The deny then cited the wrong artifact.
    if predicate.get("kind") == "program":
        return next((segment for segment in segments(value)
                     if _segment_matches_program(predicate, segment)), None)
    if predicate.get("scope") != "segment":
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


def _guard_names(predicate: Any) -> list[str]:
    """Every program name a guard names, compound branches included."""
    if not isinstance(predicate, dict):
        return []
    found = list(predicate.get("names") or [])
    for sub in (predicate.get("any_of") or []) + (predicate.get("all_of") or []):
        found += _guard_names(sub)
    return found


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

# The programs this bundle ships under its own names. A vocabulary drawn wholly from these is
# CLOSED by construction: there is no other spelling of "run Keel's own probe".
SHIPPED_PROGRAMS = frozenset(
    p.name for d in ("tools", "hooks")
    for p in (Path(__file__).resolve().parent.parent / d).glob("*") if p.is_file())


def vocabulary(predicate: Any) -> list[str]:
    """Every leading program a side selects on, compound branches included, in table order."""
    if not isinstance(predicate, dict):
        return []
    found = list(predicate.get("names") or [])
    found += [entry[0] for entry in predicate.get("argv") or [] if entry]
    for sub in (predicate.get("any_of") or []) + (predicate.get("all_of") or []):
        found += vocabulary(sub)
    return found


def classify_side(predicate: Any) -> str:
    """The Coverings.v class of one covering, read from its shape. ONE owner.

    The loader refuses what the class forbids, and `tools/render_coverings.py` emits the
    theorem instance the class licenses, so the two cannot disagree about what a side is:

      always      fires on every event of its surface; the terminal shape (Thm 3 boundary)
      tool-enum   reads `tool_name`, a closed host enum: covered however the shell is spelled
      nominal     selects on a segment's leading program (Thm 2: mention-immune when the
                  vocabulary excludes the quoting program; Thm 5: monotone in that vocabulary)
      composed    a nominal branch joined with a tool-enum branch (Thm 5 retired, not widened)
      topology    reads the operator edge between segments (Thm 4: name-agnostic)
      positive    compares a datum the trace produced to one the report states (Thm 6, 7)
      textual     reads the raw command as text (Thm 1: never mention-immune) -- refused
    """
    if not isinstance(predicate, dict):
        return "absent"
    kind = predicate.get("kind")
    branches = (predicate.get("any_of") or []) + (predicate.get("all_of") or [])
    if branches:
        parts = {classify_side(dict(sub, kind=sub.get("kind", kind), on=sub.get("on", predicate.get("on"))))
                 for sub in branches}
        if "textual" in parts or "unclassified" in parts:
            return "textual" if "textual" in parts else "unclassified"
        if parts == {"nominal"}:
            return "nominal"
        if parts <= {"nominal", "tool-enum"}:
            return "composed"
        return "unclassified"
    if kind == "always":
        return "always"
    if kind == "tool":
        return "tool-enum"
    if kind == "regex":
        if predicate.get("on") == "tool_name":
            return "tool-enum"
        return "textual" if predicate.get("on") == COMMAND_FIELD else "unclassified"
    if kind == "program":
        return "nominal"
    if kind == "pipeline":
        return "topology"
    if kind == "nonzero":
        return "positive"
    return "unclassified"


def derive_closure(predicate: Any) -> str:
    """Whether a side's vocabulary is closed, DERIVED -- never declared.

    `shipped`: nominal, and every name is a program this bundle ships. `composed` / `host`:
    a closed host enum covers the act. `open`: nominal over foreign names -- Theorem 5 says a
    missing spelling is a miss, and that is the stated limit, with nothing to argue.
    """
    cls = classify_side(predicate)
    if cls == "nominal":
        names = vocabulary(predicate)
        return "shipped" if names and set(names) <= SHIPPED_PROGRAMS else "open"
    if cls in ("composed", "tool-enum"):
        return "host"
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
    # alternation matched a `;` inside quotes. `kind: program` decides on the leading argv of a
    # segment instead, and text may then only narrow WHICH VARIANT ran.
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
