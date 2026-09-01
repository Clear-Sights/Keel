#!/usr/bin/env python3
"""Compile the proof and its instance over the shipped table, and grade every result for axioms.

Two files. `proofs/Coverings.v` is the theory: what a covering over raw text can and cannot be,
relative to a scanner with stated properties. `proofs/Clauses.v` is GENERATED from
`plugin/keel/clauses.json` by `tools/render_coverings.py` and instantiates that theory on every
side of every shipped clause -- so the theorem is applied to the table rather than cited over it.
Deleting either file, or letting the instance drift from the table, is a red gate here.

What is graded, all DERIVED from the files rather than kept as a list:
  * every declared result (Theorem, Lemma, Corollary, Fact, Remark, Proposition, Example) is
    `Print Assumptions`-ed, and every one is closed under the global context -- zero axioms;
  * no result is the identity -- a statement whose proof is `exact H` after `split` grades
    nothing, and the first Theorem 6 was exactly that shape;
  * every side of every clause in the table has its instance in Clauses.v, and Clauses.v names
    no clause the table lacks.

Exit 0 PASS / 1 FAIL / 2 NOT-EVALUABLE. Absence of coqc is NOT-EVALUABLE, never a pass.
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
PROOFS = REPO / "proofs"
THEORY = PROOFS / "Coverings.v"
INSTANCE = PROOFS / "Clauses.v"
TABLE = REPO / "plugin" / "keel" / "clauses.json"
RESULT = r"^\s*(?:Theorem|Lemma|Corollary|Fact|Remark|Proposition|Example)\s+([A-Za-z_0-9']+)"
IDENTITY = re.compile(r"Proof\.\s*(?:intros?[^.]*\.\s*)?split;\s*intro\s+\w+;\s*exact\s+\w+\.\s*Qed\.")


def strip_comments(text: str) -> str:
    """Remove (* ... *) blocks, which nest in Coq."""
    out, depth, i = [], 0, 0
    while i < len(text):
        if text.startswith("(*", i):
            depth += 1; i += 2; continue
        if text.startswith("*)", i) and depth:
            depth -= 1; i += 2; continue
        if not depth:
            out.append(text[i])
        i += 1
    return "".join(out)


def grade(path: pathlib.Path) -> tuple[int, str]:
    body = strip_comments(path.read_text(encoding="utf-8"))
    declared = set(re.findall(RESULT, body, re.M))
    graded = set(re.findall(r"^\s*Print\s+Assumptions\s+([A-Za-z_0-9']+)", body, re.M))
    ungraded = sorted(declared - graded)
    if ungraded:
        return 1, f"{path.name}: declared and never graded for axioms: {ungraded}"
    stray = sorted(graded - declared)
    if stray:
        return 1, f"{path.name}: Print Assumptions names nothing it declares: {stray}"
    if IDENTITY.search(body):
        return 1, f"{path.name}: a result is proved by the identity, so it states nothing"
    proc = subprocess.run(["coqc", "-q", "-Q", str(PROOFS), "", path.name], cwd=PROOFS,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        return 1, f"{path.name}: does not compile\n{proc.stdout}{proc.stderr}"
    closed = len(re.findall(r"Closed under the global context", proc.stdout))
    if closed != len(declared):
        return 1, (f"{path.name}: compiled, but {closed} of {len(declared)} results are closed "
                   "under the global context -- one rests on an axiom")
    return 0, f"{path.name}: results={len(declared)} axioms=0"


def instance_covers_table() -> tuple[int, str]:
    rows = json.loads(TABLE.read_text(encoding="utf-8"))
    expected = {f"{c['id']}_{side}" for c in rows
                for side in ("fingerprint", "activated_by", "discharged_by")
                if isinstance(c.get(side), dict)}
    body = strip_comments(INSTANCE.read_text(encoding="utf-8"))
    present = set(re.findall(r"^\s*\(\*\s*SIDE\s+(\S+)\s*\*\)", INSTANCE.read_text(encoding="utf-8"), re.M))
    missing = sorted(expected - present)
    extra = sorted(present - expected)
    if missing:
        return 1, f"Clauses.v has no instance for {len(missing)} table side(s): {missing}"
    if extra:
        return 1, f"Clauses.v instantiates sides the table lacks: {extra}"
    if not body.strip():
        return 1, "Clauses.v is empty"
    return 0, f"Clauses.v covers sides={len(expected)} of clauses={len(rows)}"


def main() -> int:
    for path in (THEORY, INSTANCE, TABLE):
        if not path.exists():
            print(f"COQ=NOT-EVALUABLE {path} is absent -- absence is never a pass", file=sys.stderr)
            return 2
    if shutil.which("coqc") is None:
        print("COQ=NOT-EVALUABLE coqc absent -- absence is never a pass", file=sys.stderr)
        return 2
    status, note = instance_covers_table()
    if status:
        print(f"COQ=FAIL {note}", file=sys.stderr)
        return 1
    lines = [note]
    for path in (THEORY, INSTANCE):
        status, note = grade(path)
        if status:
            print(f"COQ=FAIL {note}", file=sys.stderr)
            return 1
        lines.append(note)
    print("COQ=PASS " + " ; ".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
