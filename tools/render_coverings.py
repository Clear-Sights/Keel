#!/usr/bin/env python3
"""Instantiate the Coverings theory on every side of every shipped clause.

`proofs/Coverings.v` proves what each CLASS of covering can be. This renders
`proofs/Clauses.v`, which applies those results to the table as shipped -- one block per side
of every clause -- so that the theorem is applied to `plugin/keel/clauses.json` rather than
cited over it. The class of each side is read from `keel.clauses.classify_side`, the same
function the loader admits rows by, so the proof and the product cannot disagree about what a
side is. `tools/check_coq.py` compiles the result and grades every instance for axioms.

    python3 tools/render_coverings.py --check   # exit 1 if proofs/Clauses.v drifted from the table
    python3 tools/render_coverings.py --write   # regenerate it

What each class gets, and what it does not:
  nominal     Theorem 2 (mention-immune) when its vocabulary excludes the quoting program --
              a fact this script CHECKS over the names and states as a lemma proved by
              `discriminate`; and Theorem 5 (monotone): a spelling not in the list is a miss.
              That second instance IS the disposition of an open vocabulary. Nothing is argued.
  composed    the nominal branch's two instances, plus the fact that a `tool_name` branch is a
              closed enum, which the loader already checks (`_matches_a_tool_enum`).
  tool-enum   closed by the host; no text is read, so Theorem 1 has nothing to say.
  topology    Theorem 4: the class is name-agnostic by construction.
  always      the terminal shape; Theorem 3 says a covering that fires before the act must
              name something, so this one is the boundary, stated as such.
  effect      Theorem 8: reads what the act did, never a segment; name-agnostic, and it
              separates byte-identical commands by their effects.
  positive    Theorems 6 and 7.
  textual     the loader refuses the row; this script never sees one.
A `pattern` selects programs by regex, so its vocabulary is not a finite list: its Theorem 2
instance is stated CONDITIONAL on the pattern excluding the quoting program, and the condition
is checked here in Python (`re.fullmatch`) where regex semantics live.
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
QUOTING = "echo"
SIDES = ("fingerprint", "activated_by", "discharged_by")


def coq_ident(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", text)


def coq_string(text: str) -> str:
    return '"' + text.replace('"', '""') + '"'


def nominal_block(name: str, predicate: dict) -> list[str]:
    names = C.vocabulary(predicate)
    patterns = [p["pattern"] for p in _leaves(predicate) if p.get("pattern")]
    lines = []
    if names:
        if QUOTING in names:
            raise SystemExit(f"{name}: names the quoting program {QUOTING!r}; Theorem 2 cannot "
                             "apply and the side is defeated by a mention")
        lines += [
            f"  Definition {name}_names : list string := [{'; '.join(coq_string(n) for n in names)}].",
            f"  Lemma {name}_clean : ~ In {coq_string(QUOTING)} {name}_names.",
            "  Proof. simpl; intuition discriminate. Qed.",
            f"  Theorem {name}_immune :",
            f"    mention_immune Text mention (structural Text string scan (fun p => In p {name}_names)).",
            f"  Proof. exact (structural_immune Text string scan mention {coq_string(QUOTING)} "
            f"scan_mention_single _ {name}_clean). Qed.",
            f"  Theorem {name}_monotone : forall W, (forall p, In p {name}_names -> W p) ->",
            f"    forall c, nominal Text string scan (fun p => In p {name}_names) c -> nominal Text string scan W c.",
            f"  Proof. intros W H. exact (nominal_monotone Text string scan _ W H). Qed.",
        ]
    for i, pattern in enumerate(patterns):
        if re.fullmatch(pattern, QUOTING):
            raise SystemExit(f"{name}: pattern {pattern!r} admits {QUOTING!r}; Theorem 2 cannot apply")
        lines += [
            f"  (* pattern {i}: {pattern!r} -- a regular vocabulary, checked in Python to exclude "
            f"{QUOTING!r}; the instance is conditional on that. *)",
            f"  Theorem {name}_pattern{i}_immune : forall V : string -> Prop,",
            f"    ~ V {coq_string(QUOTING)} -> mention_immune Text mention (structural Text string scan V).",
            f"  Proof. intros V H. exact (structural_immune Text string scan mention {coq_string(QUOTING)} "
            "scan_mention_single V H). Qed.",
        ]
    return lines


def _leaves(predicate: dict) -> list[dict]:
    branches = (predicate.get("any_of") or []) + (predicate.get("all_of") or [])
    if not branches:
        return [predicate]
    return [leaf for sub in branches for leaf in _leaves(sub)]


def side_block(clause_id: str, side: str, predicate: dict) -> list[str]:
    name = coq_ident(f"{clause_id}_{side}")
    cls = C.classify_side(predicate)
    closure = C.derive_closure(predicate)
    head = [f"  (* SIDE {clause_id}_{side} *)", f"  (* class={cls} closure={closure} *)"]
    if cls in ("nominal", "composed"):
        return head + nominal_block(name, predicate)
    if cls == "tool-enum":
        return head + [f"  (* reads tool_name, a closed host enum: no text, no vocabulary *)"]
    if cls == "topology":
        return head + [
            f"  Theorem {name}_name_agnostic : forall n, name_agnostic string (fun segs => List.length segs = n).",
            f"  Proof. exact (topology_is_name_agnostic string). Qed.",
        ]
    if cls == "always":
        return head + ["  (* terminal: fires on every event of its surface; the Theorem 3 boundary *)"]
    if cls == "effect":
        effects = sorted({leaf["effect"] for leaf in _leaves(predicate) if leaf.get("kind") == "effect"})
        return head + [
            f"  (* effects: {', '.join(effects)} -- what the act did, read from the world, not the command *)",
            f"  Theorem {name}_name_agnostic : forall (Delta : Type) (E : Delta -> Prop) (d : Delta),",
            f"    name_agnostic string (effect string E d).",
            f"  Proof. intros Delta E d. exact (effect_is_name_agnostic string Delta E d). Qed.",
            f"  Theorem {name}_separates : forall (Delta : Type) (E : Delta -> Prop) (d d' : Delta), E d -> ~ E d' ->",
            f"    forall segs, effect string E d segs /\ ~ effect string E d' segs.",
            f"  Proof. intros Delta E d d'. exact (effect_separates_same_segments string Delta E d d'). Qed.",
        ]
    if cls == "positive":
        return head + [
            f"  Theorem {name}_rejects_false_claims : forall (D : Type) (cl ob : Text -> option D) c d d',",
            f"    cl c = Some d -> ob c = Some d' -> d <> d' -> ~ positive Text D cl ob c.",
            f"  Proof. intros D cl ob. exact (false_claim_always_rejected Text D cl ob). Qed.",
        ]
    raise SystemExit(f"{clause_id}.{side}: class {cls!r} has no instance; the loader should have refused it")


def render(rows: list[dict]) -> str:
    out = [
        "(* GENERATED by tools/render_coverings.py from plugin/keel/clauses.json -- do not edit.",
        "   One block per side of every shipped clause, instantiating proofs/Coverings.v on it.",
        "   tools/check_coq.py compiles this and grades every result for axioms. *)",
        "Require Import List String.",
        "Import ListNotations.",
        "Require Import Coverings.",
        "Open Scope string_scope.",
        "",
        "Section Instance.",
        "  Variable Text : Type.",
        "  Variable scan : Text -> list (Segment string).",
        "  Variable mention : Text -> Text.",
        "  Hypothesis scan_mention_single :",
        f"    forall c, scan (mention c) = [ {{| seg_argv := [{coq_string(QUOTING)}] |}} ].",
        "",
    ]
    results: list[str] = []
    for clause in rows:
        for side in SIDES:
            predicate = clause.get(side)
            if not isinstance(predicate, dict):
                continue
            block = side_block(clause["id"], side, predicate)
            out += block + [""]
            results += re.findall(r"^\s*(?:Theorem|Lemma)\s+([A-Za-z_0-9']+)", "\n".join(block), re.M)
    out += ["End Instance.", ""]
    out += [f"Print Assumptions {r}." for r in results]
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
