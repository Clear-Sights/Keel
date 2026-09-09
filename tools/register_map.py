#!/usr/bin/env python3
"""Grade keel's coverage of the blindspot register.

docs/REGISTER.md is a vendored copy; the source is measure-zero-dev/REGISTER.md.
docs/REGISTER-MAP.tsv gives every entry in it one of three verdicts:

  RUNNER          a named admitted clause, or a structural property of the
                  dispatcher, raises the demand the entry asks for
  NOT-RAISABLE    the entry is about a sequence of acts -- keel's subject -- but
                  what it needs is not observable from the act about to run. The
                  note says what would have to be visible.
  OUT-OF-SUBJECT  the entry governs code keel does not execute or a system it
                  does not configure.

The clause population is closed at 24 and this runner does not widen it. A
register entry with no clause is recorded as such rather than answered with a
new one: a 25th clause is the owner's decision, not this file's.

A verdict with no note is NOT-EVALUABLE and exits 2 -- an unexplained
NOT-RAISABLE is how a gap becomes invisible.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTER = ROOT / "docs" / "REGISTER.md"
MAP = ROOT / "docs" / "REGISTER-MAP.tsv"
CLAUSES = ROOT / "plugin" / "keel" / "clauses.json"
VERDICTS = {"RUNNER", "NOT-RAISABLE", "OUT-OF-SUBJECT"}
ENTRY_RX = re.compile(r"^([A-G]\d+)\s+[A-Z]")
CLAUSE_RX = re.compile(r"^[A-Z]\d\d(-[a-z-]+)?$")
ADMITTED = 24


def main():
    entries = [m.group(1) for m in
               (ENTRY_RX.match(ln) for ln in REGISTER.read_text(encoding="utf-8").splitlines())
               if m]
    clauses = {c["id"] for c in json.loads(CLAUSES.read_text(encoding="utf-8"))}

    rows, errors = {}, []
    if len(clauses) != ADMITTED:
        errors.append(f"clause table carries {len(clauses)}, not the admitted {ADMITTED}")

    for n, line in enumerate(MAP.read_text(encoding="utf-8").splitlines()[1:], start=2):
        if not line.strip():
            continue
        entry, verdict, runner, note = line.split("\t")
        if entry in rows:
            errors.append(f"line {n}: {entry} stated twice")
        rows[entry] = (verdict, runner, note)
        if verdict not in VERDICTS:
            errors.append(f"line {n}: {entry} verdict {verdict!r} is not one of {sorted(VERDICTS)}")
        if not note.strip():
            errors.append(f"line {n}: {entry} has a verdict and no note")
        if verdict == "RUNNER":
            if CLAUSE_RX.match(runner) and runner not in clauses:
                errors.append(f"line {n}: {entry} cites clause {runner}, which is not admitted")
            elif "/" in runner and not (ROOT / runner).exists():
                errors.append(f"line {n}: {entry} cites {runner}, which is not on disk")
        elif runner != "-":
            errors.append(f"line {n}: {entry} is {verdict} but names a runner")

    for missing in sorted(set(entries) - set(rows)):
        errors.append(f"register entry {missing} has no row in the map")
    for invented in sorted(set(rows) - set(entries)):
        errors.append(f"map row {invented} is not an entry in the register")

    counts = {v: sum(1 for r in rows.values() if r[0] == v) for v in sorted(VERDICTS)}
    cited = {r[1] for r in rows.values() if r[0] == "RUNNER" and CLAUSE_RX.match(r[1])}
    print(f"REGISTER MAP  register entries={len(entries)}  rows={len(rows)}  clauses={len(clauses)}")
    for v, c in counts.items():
        print(f"  {v:<15s} {c}")
    print(f"  clauses cited   {len(cited)} of {len(clauses)}")
    for idle in sorted(clauses - cited):
        print(f"    no register entry names {idle}")
    if errors:
        print(f"  NOT-EVALUABLE   {len(errors)}")
        for e in errors:
            print(f"    {e}")
        return 2
    print("REGISTER MAP: every entry carried, every clause cited is admitted, every verdict explained.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
