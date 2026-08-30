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


def replay(path: pathlib.Path) -> bool:
    lines = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    header, events = lines[0], lines[1:]
    expect = header.get("expect", "fires")
    with tempfile.TemporaryDirectory() as state:
        results = [dispatch(event, state) for event in events]

    reasons = [fired(result) for result in results]
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


def main() -> int:
    paths = sorted(CORPUS.glob("*.jsonl"))
    if not paths:
        print(f"no corpus sessions found in {CORPUS}", file=sys.stderr)
        return 1
    outcomes = [replay(path) for path in paths]
    passed = sum(outcomes)
    print(f"\nREPLAY sessions={len(outcomes)} passed={passed} failed={len(outcomes) - passed}")
    return 0 if all(outcomes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
