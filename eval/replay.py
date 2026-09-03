#!/usr/bin/env python3
"""Replay recorded sessions through the hook and show where it fires.

Each corpus file is one session: a JSON header line, then hook events in order.
The header names the event where the real pattern derailed (`derails_at`, 0-based
index into the events). The claim under test is narrow and mechanical:

    the hook fires at or before the derailing event, and its decision at that
    moment would have denied the call (or blocked the stop) with a stated reason.

This is not a behaviour experiment. It proves the trigger, not the outcome: a
live agent receiving the denial may still find another path. What it makes
reproducible is that the moment the corpus went wrong is a moment this hook
speaks, and what it would have said.

Sessions with `"expect": "none"` are controls: the hook must stay silent for
every event. Sessions with `"expect": "recovery"` additionally require that the
same call, made again after the guard, passes — denial is a repricing, not a
prohibition.

Run from the repository root:

    python3 eval/replay.py

Exit 0 iff every session meets its expectation. Python standard library only.
"""

from __future__ import annotations

import json
import re
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORPUS = pathlib.Path(__file__).resolve().parent / "corpus"

DISPATCH_CWD = ROOT / "plugin"
STATE_ENV = "KEEL_STATE_DIR"


def dispatch(event: dict, state_dir: str) -> dict:
    env = dict(os.environ, **{STATE_ENV: state_dir})
    proc = subprocess.run(
        [sys.executable, "-m", "keel.dispatch"],
        input=json.dumps(event), capture_output=True, text=True,
        cwd=DISPATCH_CWD, env=env,
    )
    try:
        decision = json.loads(proc.stdout or "{}")
        parsed = True
    except json.JSONDecodeError:
        decision, parsed = {}, False
    return {"decision": decision, "exit": proc.returncode, "parsed": parsed,
            "stdout": proc.stdout, "stderr": proc.stderr[-400:]}


def crashed(result: dict) -> str | None:
    """Why this dispatch rendered no decision, or None if it rendered one.

    SILENCE AND A CRASH ARE THE SAME BYTES TO `fired`. A hook that dies prints nothing, so
    `fired` returns None -- exactly as it does for an allow -- and a control session then reads
    "silent on every event -- OK" over a dispatcher that never evaluated a clause. `fired` reads
    exit 2 as a block and treats EVERY OTHER non-zero exit as silence, which is where a crash
    lands. Keel's contract is 0 for a rendered decision and 2 for a block, so anything else is a
    fault; unparseable stdout is never a decision either.

    Keel also fails OPEN on an internal error -- exit 0, with a notice saying the call was
    allowed without being checked. That is the honest behaviour and it is exactly what makes the
    fault observable here, so it counts as a fault too rather than as quiet.
    """
    if result["exit"] not in (0, 2):
        return f"the dispatcher exited {result['exit']}: {result['stderr'].strip()!r}"
    if not result["parsed"]:
        return "the dispatcher printed something that is not JSON, so it rendered no decision"
    if "WITHOUT BEING CHECKED" in result["stdout"]:
        return "keel failed open: the event was allowed without being checked"
    return None


_CLAUSE_IN_REASON = re.compile(r"\[([A-Za-z][A-Za-z0-9_-]*)\]")


def clauses_named(reason: str | None) -> list[str]:
    """The clause ids a denial names. A fire that names none is a fire nobody can attribute."""
    return _CLAUSE_IN_REASON.findall(reason or "")


def fired(result: dict) -> str | None:
    """Return the denial/block reason if this decision stops the call, else None."""
    decision = result["decision"]
    hook = decision.get("hookSpecificOutput", {})
    if hook.get("permissionDecision") == "deny":
        return hook.get("permissionDecisionReason", "(denied, no reason field)")
    if decision.get("decision") == "block":
        return decision.get("reason", "(blocked, no reason field)")
    if result["exit"] == 2:
        return "(exit 2: block)"
    return None


# session file -> did the dispatcher actually deny or block anything in it, and which clauses it
# named. Read by `main`: the first decides whether the run is evidence at all (see the
# NOT-EVALUABLE note there), the second is the baseline the live-observer lane is held to.
# RECORDED FROM THE GRADED RUN rather than measured again -- one observation, read twice, and one
# fewer pass of subprocesses over the corpus.
DENIED: dict[pathlib.Path, bool] = {}
NAMED: dict[pathlib.Path, set[str]] = {}


def replay(path: pathlib.Path) -> bool:
    lines = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    header, events = lines[0], lines[1:]
    expect = header.get("expect", "fires")
    with tempfile.TemporaryDirectory() as state:
        results = [dispatch(event, state) for event in events]

    reasons = [fired(result) for result in results]
    DENIED[path] = any(reason is not None for reason in reasons)
    NAMED[path] = {clause for reason in reasons for clause in clauses_named(reason)}
    first = next((i for i, reason in enumerate(reasons) if reason), None)

    print(f"\n== {path.stem}: {header['description']}")

    # A SESSION WITH NO EVENTS EVALUATED NOTHING and would otherwise pass: with `results` empty
    # `first` is None, which a control session reads as correct silence, and the file still
    # counts toward `sessions` and `passed`. An empty denominator is not a clean one.
    if not events:
        print("   FAIL: this session carries no events, so it is evidence about nothing")
        return False

    # A CRASH IS NOT SILENCE. Checked before anything reads `reasons`, so no later branch can
    # read a dead hook as an allow.
    faults = [(i, why) for i, why in ((i, crashed(r)) for i, r in enumerate(results)) if why]
    if faults:
        for index, why in faults:
            print(f"   FAIL: event [{index}] rendered no decision -- {why}")
        return False
    if expect == "none":
        ok = first is None
        print("   control session: " + ("silent on every event — OK"
              if ok else f"UNEXPECTED fire at event {first}: {reasons[first]}"))
        return ok

    derails_at = header["derails_at"]
    print(f"   derailing event [{derails_at}]: {header['derailment']}")
    if first is None:
        print("   FAIL: the hook never fired")
        return False
    print(f"   first fire at event [{first}]: {reasons[first]}")
    ok = first <= derails_at

    # A SESSION MUST NAME THE CLAUSE IT EXERCISES, AND THE FIRE MUST BE THAT CLAUSE.
    #
    # Until this existed, replay asked only whether SOMETHING denied in time. A session named for
    # one clause passed on a denial from any other, so a corpus file was evidence that the hook
    # fires -- never evidence about the clause in its filename. The check did not name its
    # subject, so a green replay could not tell a covered clause from an uncovered one, which is
    # the whole question a corpus is kept to answer.
    declared = header.get("clause")
    if not declared:
        print("   FAIL: the header names no clause, so this session is evidence about nothing")
        return False
    named = clauses_named(reasons[first])
    if declared not in named:
        print(f"   FAIL: declared clause {declared} did not fire; the first fire names "
              f"{named or 'no clause at all'}")
        return False
    print(f"   the fire is {declared}, which is the clause this session declares")
    print("   fires at or before the derailment — OK" if ok
          else "   FAIL: first fire comes after the derailing event")

    if expect == "recovery":
        last = len(events) - 1
        recovered = reasons[last] is None
        print("   same call after the guard passes — OK" if recovered
              else f"   FAIL: still denied after the guard: {reasons[last]}")
        ok = ok and recovered
    return ok


# The one authored session replayed a second time against the LIVE observer. Chosen because its
# acts are file mutations in a worktree, which is the effect the observer can be made to measure
# for real in a repository this file builds -- no network, no process table, nothing that depends
# on the machine underneath.
LIVE_SESSION = "t01-done-while-dirty"


def _live_ground(work: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    """A real git repository and a state directory carrying a real `remote.json`."""
    repo, state = work / "repo", work / "state"
    repo.mkdir(); state.mkdir()

    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)

    git("init", "-q", "-b", "main")
    git("config", "user.email", "replay@keel.invalid")
    git("config", "user.name", "replay")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "seed")
    root = subprocess.run(["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True, check=True).stdout.strip()
    # `_artifact_read` accepts REMOTE when `tips` is a dict and the root matches the worktree the
    # event names, which is what makes the session's Read of it pay A03 rather than nothing.
    (state / "remote.json").write_text(json.dumps({"root": root, "tips": {}}), encoding="utf-8")
    return repo, state


def _live_event(event: dict, repo: pathlib.Path, state: pathlib.Path) -> dict:
    """One authored event re-aimed at the real ground, with its authored record REMOVED."""
    event = json.loads(json.dumps(event))
    event.pop("keel_effect", None)          # the whole point: the observer must produce it
    event["cwd"] = str(repo)
    tool_input = event.get("tool_input")
    if isinstance(tool_input, dict) and isinstance(tool_input.get("file_path"), str):
        name = pathlib.PurePath(tool_input["file_path"]).name
        home = state if "keel_state" in tool_input["file_path"] else repo
        tool_input["file_path"] = str(home / name)
    return event


def live_session(path: pathlib.Path, recorded: set[str]) -> bool:
    """Replay one session with no authored records, against a worktree that really changes.

    WHY THIS LANE EXISTS. `dispatch._effect_record` returns immediately when the event already
    carries a `keel_effect`, and `generate_corpus.py` writes a complete authored record into
    every `PostToolUse` event -- so the corpus replay never calls `effects.delta`,
    `effects.report_effects` or `effects.trace_effects` even once. MEASURED: with every one of
    those gutted to constant blind values, the whole replay stayed green and exit 0. The corpus
    proves the dispatcher reads a record correctly; it proved nothing at all about the thing that
    writes the record, which is half the plugin.

    So one session is driven again with `keel_effect` stripped and its acts performed for real in
    a git repository built here. The bar is that every clause the RECORDED run blocks on is named
    by the live run too: the authored record and the live observation must license the same
    refusals. It is a subset rather than an equality because the live machine has effects the
    corpus cannot author -- the host's connection counter ticks under `git` on some runs and not
    others, raising `U06`/`U24` -- and a bar that goes red with the weather is not a bar.
    """
    with tempfile.TemporaryDirectory() as work:
        repo, state = _live_ground(pathlib.Path(work))
        events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()][1:]
        results = []
        for event in events:
            event = _live_event(event, repo, state)
            tool_input = event.get("tool_input") or {}
            # The act itself, performed. A Write that never writes leaves nothing for the
            # observer to see, and the lane would be measuring an empty worktree.
            if event["hook_event_name"] == "PostToolUse" and event.get("tool_name") == "Write":
                pathlib.Path(tool_input["file_path"]).write_text(
                    tool_input.get("content", ""), encoding="utf-8")
            results.append(dispatch(event, str(state)))

    print(f"\n== {path.stem} [LIVE OBSERVER]: authored effect records stripped; "
          "the hook must observe the acts itself")
    faults = [(i, why) for i, why in ((i, crashed(r)) for i, r in enumerate(results)) if why]
    for index, why in faults:
        print(f"   FAIL: event [{index}] rendered no decision -- {why}")
    if faults:
        return False
    named = {c for r in results for c in clauses_named(fired(r))}
    missing = sorted(recorded - named)
    print(f"   recorded run named {sorted(recorded)}; live run named {sorted(named)}")
    if missing:
        print(f"   FAIL: the live observer licensed what the authored record refused: {missing} "
              "went unnamed, so the record the decision rests on was not measured")
        return False
    print("   every clause the authored record refuses is refused live too — OK")
    return True


def main() -> int:
    paths = sorted(CORPUS.glob("*.jsonl"))
    if not paths:
        print(f"no corpus sessions found in {CORPUS}", file=sys.stderr)
        return 1
    outcomes = [replay(path) for path in paths]

    live = next((p for p in paths if p.stem == LIVE_SESSION), None)
    if live is None:
        print(f"\nFAIL: the live-observer session {LIVE_SESSION!r} is not in the corpus, so "
              "nothing here exercises the observer", file=sys.stderr)
        return 1
    outcomes.append(live_session(live, NAMED[live]))

    passed = sum(outcomes)
    print(f"\nREPLAY sessions={len(outcomes) - 1} passed={passed - 1} "
          f"failed={len(outcomes) - passed}")

    # A RUN THAT DENIED NOTHING IS NOT A GREEN RUN. Every handler in `HANDLERS` replaced by
    # `return {}` leaves the benign control passing -- "silent on every event" is exactly what a
    # dead dispatcher produces -- and the only thing separating that from a working table is
    # whether anything, anywhere, actually refused. Counted rather than assumed, and a zero count
    # exits 2 (NOT-EVALUABLE) rather than 1, because "the corpus disagrees with the dispatcher"
    # and "there was no dispatcher to disagree with" are different findings.
    denials = sum(1 for path in paths if DENIED.get(path))
    print(f"REPLAY live-denials={denials}")
    if not denials:
        print("\nNOT-EVALUABLE: no session produced a denial or block from the dispatcher, so "
              "nothing here observed the table refuse anything. A silent dispatcher passes every "
              "control session; silence is not evidence.", file=sys.stderr)
        return 2
    return 0 if all(outcomes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
