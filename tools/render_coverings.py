#!/usr/bin/env python3
"""Instantiate the Coverings theory on every side of every shipped clause.

`proofs/Coverings.v` proves what each CLASS of covering can be. This renders
`proofs/Clauses.v`, which applies those results to the table as shipped -- one line per side and one result per class
of every clause -- so that the theorem is applied to `plugin/keel/clauses.json` rather than
cited over it. The class of each side is read from `keel.clauses.classify_side`, the same
function the loader admits rows by, so the proof and the product cannot disagree about what a
side is. `tools/check_coq.py` compiles the result and grades every instance for axioms.

    python3 tools/render_coverings.py --check   # exit 1 if proofs/Clauses.v drifted from the table
    python3 tools/render_coverings.py --write   # regenerate it

What each class gets, and what it does not:
  tool-enum   closed by the host; no text is read, so Theorem 1 has nothing to say.
  always      the terminal shape; Theorem 3 says a covering that fires before the act must
              name something, so this one is the boundary, stated as such.
  effect      Theorem 8: reads what the act did, never a segment; name-agnostic, and it
              separates byte-identical commands by their effects. On the guard side the
              effect is a datum the trace holds or a report shape where no trace exists.
  positive    NOT PRODUCIBLE: no admitted kind classifies as `positive`. Theorems 6 and 7 are
              proven in Coverings.v and instantiated by no shipped side.
  composed    a composition of the classes above: each branch gets its own instance.
  nominal     the loader refuses the row on EVERY side (`CLAUSE-OCCASION-NOMINAL`,
              `CLAUSE-GUARD-NOMINAL`); this script never sees one.
  textual     the loader refuses the row; this script never sees one.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "plugin"))
from keel import clauses as C  # noqa: E402

TABLE = REPO / "plugin" / "keel" / "clauses.json"
OUT = REPO / "proofs" / "Clauses.v"
SIDES = ("fingerprint", "activated_by", "discharged_by")


def coq_ident(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", text)


def _leaves(predicate: dict) -> list[dict]:
    branches = (predicate.get("any_of") or []) + (predicate.get("all_of") or [])
    if not branches:
        return [predicate]
    return [leaf for sub in branches for leaf in _leaves(sub)]


RESULTS = {
    # class -> (enumeration, result, statement lines, proof lines). ONE result per class, quantified
    # over an enumeration whose constructors are the sides of that class. The theorem's statement
    # never mentioned the side -- 74 copies were byte-identical apart from their names -- so the
    # per-side fact is MEMBERSHIP, which the enumeration carries and check_coq censuses from
    # coqc's own index (`constr`), refusing an enumeration no result quantifies over.
    "effect": ("EffectSide", "effect_sides_read_the_world_not_the_command", [
        "  forall (s : EffectSide) (D : Type) (E : D -> Prop) (d d' : D), E d -> ~ E d' ->",
        "    name_agnostic string (effect string E d)",
        "    /\\ (forall segs, effect string E d segs /\\ ~ effect string E d' segs)."], [
        "  intros s D E d d' Hd Hd'.",
        "  split; [ exact (effect_is_name_agnostic string D E d)",
        "         | exact (effect_separates_same_segments string D E d d' Hd Hd') ]."]),
    # NO `positive` ENTRY. `classify_side` can no longer return that class: its only producer
    # was `kind: nonzero`, which had zero shipped uses and was removed from the loader, so this
    # map's positive arm could never be selected by any table this renderer is allowed to read.
    # Theorems 6 and 7 remain PROVEN in proofs/Coverings.v and are cited in README as
    # proven-not-instantiated; the arm returns when a side that compares a claimed datum to an
    # observed one exists to instantiate them.
}
BOUNDARY = ("always", "tool-enum")  # no text is read: Theorem 1 has nothing to say, Theorem 3 is the edge


def side_line(clause_id: str, side: str, predicate: dict, members: dict[str, list[str]],
              branch: str | None = None) -> list[str]:
    """One comment per side (and per branch of a composed one); the side joins its class."""
    cls = C.classify_side(predicate)
    effects = sorted({leaf["effect"] for leaf in _leaves(predicate) if leaf.get("kind") == "effect"})
    note = f" effects={','.join(effects)}" if cls == "effect" else ""
    mark = f"SIDE {clause_id}_{side}" if branch is None else f"  BRANCH {branch}"
    line = [f"  (* {mark} *) (* class={cls} closure={C.derive_closure(predicate)}{note} *)"]
    if cls == "composed":
        for i, leaf in enumerate(_leaves(predicate)):
            line += side_line(clause_id, f"{side}_branch{i}", leaf, members,
                              coq_ident(f"{clause_id}_{side}_branch{i}"))
        return line
    if cls in RESULTS:
        members.setdefault(cls, []).append(coq_ident(f"{clause_id}_{side}"))
    elif cls not in BOUNDARY:
        raise SystemExit(f"{clause_id}.{side}: class {cls!r} has no instance; the loader should have refused it")
    return line


def render(rows: list[dict]) -> str:
    out = [
        "(* GENERATED by tools/render_coverings.py from plugin/keel/clauses.json -- do not edit.",
        "   One line per side of every shipped clause; one enumeration and one result per class,",
        "   instantiating proofs/Coverings.v on the sides of that class. tools/check_coq.py",
        "   compiles this, grades every result for axioms, and censuses the sides from the index.",
        "   PARAMETERS: *)",
        "Require Import String.",
        "Require Import Coverings.",
        "",
    ]
    members: dict[str, list[str]] = {}
    for clause in rows:
        for side in SIDES:
            predicate = clause.get(side)
            if isinstance(predicate, dict):
                out += side_line(clause["id"], side, predicate, members)
    out.append("")
    for cls, idents in sorted(members.items()):
        enum, name, statement, proof = RESULTS[cls]
        out += [f"Inductive {enum} :="] + [f"  | {i}" for i in idents]
        out[-1] += "."
        out += ["", f"Theorem {name} :"] + statement + ["Proof."] + proof + ["Qed.", ""]
    out += [f"Print Assumptions {RESULTS[cls][1]}." for cls in sorted(members)]
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    if argv[1:] not in (["--check"], ["--write"]):
        print("usage: render_coverings.py --check | --write", file=sys.stderr)
        return 2
    rows = json.loads(TABLE.read_text(encoding="utf-8"))
    fresh = render(rows)
    if argv[1] == "--write":
        OUT.write_text(fresh, encoding="utf-8")
        print(f"wrote {OUT.relative_to(REPO)}")
        return 0
    if not OUT.exists():
        print(f"NOT-EVALUABLE: {OUT.relative_to(REPO)} is absent", file=sys.stderr)
        return 2
    if OUT.read_text(encoding="utf-8") != fresh:
        print(f"DRIFT: {OUT.relative_to(REPO)} does not match the table; run --write", file=sys.stderr)
        return 1
    print(f"{OUT.relative_to(REPO)} matches plugin/keel/clauses.json")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
