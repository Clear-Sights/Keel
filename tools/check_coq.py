#!/usr/bin/env python3
"""Compile the proof and its instance over the shipped table, and grade every result for axioms.

Two files. `proofs/Coverings.v` is the theory: what a covering over raw text can and cannot be,
relative to a scanner with stated properties. `proofs/Clauses.v` is GENERATED from
`plugin/keel/clauses.json` by `tools/render_coverings.py` and instantiates that theory on every
side of every shipped clause whose class has a result to instantiate.

EVERYTHING GRADED IS READ FROM coqc's OWN INDEX, never from the text. The first grader counted
`(* SIDE X *)` comment markers as coverage, found result names with a line-anchored regex, and
called a Section Hypothesis "zero axioms" because `Print Assumptions` does not list what a
Section discharged. So 901 lines of Coq replaced by 54 lines of comments graded PASS, a
`Hypothesis : False` inside the Section graded PASS, and `#[local] Theorem` beside a global
`Axiom` graded PASS. Now the `.glob` file coqc writes is the census: `prf` entries are the
results, `var` entries are the Section parameters, `ax` entries are global axioms.

Graded, all DERIVED from the files:
  * every result (`prf`) is `Print Assumptions`-ed and comes back closed under the global
    context; a result graded to an `Axioms:` block, an `Admitted`, or any `ax` entry is red;
  * the Section parameters (`var`) are exactly the ones the file's `PARAMETERS:` line names, so a
    hypothesis cannot be added to the theory without being declared beside the claim;
  * every side of every table clause has its block in Clauses.v, no block names a side the
    table lacks, and the census says how many sides carry a result and how many are empty by
    class (`always` and `tool-enum` sides state a boundary, not a theorem);
  * a result proved by `split; intro H; exact H` is refused. That is ONE spelling family of an
    identity proof, not a vacuity check; the test is stated at its width.

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
IDENTITY = re.compile(r"Proof\.\s*(?:intros?[^.]*\.\s*)?split;\s*intro\s+\w+;\s*exact\s+\w+\.\s*Qed\.")
EMPTY_BY_DESIGN = {"always", "tool-enum"}


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


def compile_and_index(path: pathlib.Path) -> tuple[str | None, dict[str, list[str]]]:
    """coqc the file; return its stdout and the .glob index grouped by entry kind."""
    # coqc rewrites .vo/.glob itself; deleting them first raced a concurrent grader.
    proc = subprocess.run(["coqc", "-q", "-Q", str(PROOFS), "", path.name], cwd=PROOFS,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        return None, {"error": [proc.stdout + proc.stderr]}
    index: dict[str, list[str]] = {}
    for line in (PROOFS / (path.stem + ".glob")).read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 4 and not parts[0].startswith("R"):
            index.setdefault(parts[0], []).append(parts[3])
    return proc.stdout, index


def grade(path: pathlib.Path) -> tuple[int, str]:
    text = path.read_text(encoding="utf-8")
    body = strip_comments(text)
    if IDENTITY.search(body):
        return 1, f"{path.name}: a result is proved by the identity, so it states nothing"
    stdout, index = compile_and_index(path)
    if stdout is None:
        return 1, f"{path.name}: does not compile\n{index['error'][0]}"
    results = index.get("prf", [])
    axioms = index.get("ax", [])
    params = index.get("var", [])
    if axioms:
        return 1, f"{path.name}: declares global axioms: {sorted(axioms)}"
    if not results:
        return 1, f"{path.name}: compiles and proves nothing (no result in its index)"
    graded = set(re.findall(r"\bPrint\s+Assumptions\s+([A-Za-z_0-9']+)", body))
    ungraded = sorted(set(results) - graded)
    if ungraded:
        return 1, f"{path.name}: results never graded for axioms: {ungraded}"
    stray = sorted(graded - set(results))
    if stray:
        return 1, f"{path.name}: Print Assumptions names nothing it proves: {stray}"
    closed = len(re.findall(r"Closed under the global context", stdout))
    if "Axioms:" in stdout or closed != len(results):
        return 1, (f"{path.name}: compiled, but {closed} of {len(results)} results are closed under "
                   f"the global context -- one rests on an axiom or an Admitted")
    declared = re.search(r"PARAMETERS:\s*([^*]*)\*\)", text)
    stated = set(declared.group(1).split()) if declared else set()
    if stated != set(params):
        return 1, (f"{path.name}: Section parameters {sorted(set(params) - stated)} are not on the "
                   f"PARAMETERS line, or it names {sorted(stated - set(params))} the file lacks -- "
                   "a hypothesis the claim does not declare")
    return 0, f"{path.name}: results={len(results)} axioms=0 parameters={len(params)}"


def instance_covers_table() -> tuple[int, str]:
    rows = json.loads(TABLE.read_text(encoding="utf-8"))
    expected = {f"{c['id']}_{side}" for c in rows
                for side in ("fingerprint", "activated_by", "discharged_by")
                if isinstance(c.get(side), dict)}
    text = INSTANCE.read_text(encoding="utf-8")
    blocks = re.split(r"\(\*\s*SIDE\s+(\S+)\s*\*\)", text)
    present = {blocks[i]: blocks[i + 1] for i in range(1, len(blocks), 2)}
    missing = sorted(expected - set(present))
    extra = sorted(set(present) - expected)
    if missing:
        return 1, f"Clauses.v has no block for {len(missing)} table side(s): {missing}"
    if extra:
        return 1, f"Clauses.v instantiates sides the table lacks: {extra}"
    _, index = compile_and_index(INSTANCE)
    results = set(index.get("prf", []))
    empty: dict[str, int] = {}
    for side, block in present.items():
        if any(r.startswith(side.replace("-", "_")) for r in results):  # Coq names carry no hyphen
            continue
        cls = re.search(r"class=(\S+)", block)
        cls = cls.group(1) if cls else "?"
        if cls not in EMPTY_BY_DESIGN:
            return 1, f"Clauses.v side {side} (class {cls}) carries no result and its class is not one that states a boundary"
        empty[cls] = empty.get(cls, 0) + 1
    instantiated = len(expected) - sum(empty.values())
    by_class = " ".join(f"{k}={v}" for k, v in sorted(empty.items()))
    return 0, (f"Clauses.v covers sides={len(expected)} of clauses={len(rows)}: "
               f"instantiated={instantiated} empty-by-class[{by_class}]")


def main() -> int:
    for path in (THEORY, INSTANCE, TABLE):
        if not path.exists():
            print(f"COQ=NOT-EVALUABLE {path} is absent -- absence is never a pass", file=sys.stderr)
            return 2
    if shutil.which("coqc") is None:
        print("COQ=NOT-EVALUABLE coqc absent -- absence is never a pass", file=sys.stderr)
        return 2
    lines = []
    for path in (THEORY, INSTANCE):
        status, note = grade(path)
        if status:
            print(f"COQ=FAIL {note}", file=sys.stderr)
            return 1
        lines.append(note)
    status, note = instance_covers_table()
    if status:
        print(f"COQ=FAIL {note}", file=sys.stderr)
        return 1
    print("COQ=PASS " + note + " ; " + " ; ".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
