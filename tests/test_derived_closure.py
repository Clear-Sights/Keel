"""A covering's class is DERIVED from its shape and PROVED on the row; nothing is argued in prose.

Coverings.v proves what each class of covering can be. `keel.clauses.classify_side` reads the
class off a side's shape, the loader refuses what the class forbids (a textual side, Theorem 1),
and `tools/render_coverings.py` instantiates the licensed theorems on every side of every shipped
clause in `proofs/Clauses.v`, which `tools/check_coq.py` compiles and grades for axioms.

What this retires: `guard_vocabulary`, `why_no_program` and `waiver` -- three places a row could
state in English what the proof decides. Theorem 5 says a nominal covering is monotone in its
vocabulary, so an unlisted spelling is a miss. On the GUARD side that miss is an undischarged
demand (fail-closed) and is carried as a theorem instance per side. On the OCCASION side it would
be the costly act proceeding unguarded, so the loader refuses a nominal occasion outright
(`CLAUSE-OCCASION-NOMINAL`): every occasion is `always`, a host tool enum, a topology, or an
EFFECT read from the world (Theorem 8). A row carrying any of the three fields is refused
(`CLAUSE-CARRIES-AN-EXCUSE`).
"""
from __future__ import annotations

import collections
import json
import shutil
import subprocess
import sys
import unittest

from tests.plant_support import PLUGIN, REPO, smoke_replace
from keel import clauses as C

CLAUSES = PLUGIN / "keel" / "clauses.json"
CLAUSES_V = REPO / "proofs" / "Clauses.v"
SIDES = ("fingerprint", "activated_by", "discharged_by")


def _sides():
    return [(c.id, name, getattr(c, name)) for c in C.load_default()
            for name in SIDES if isinstance(getattr(c, name), dict)]


class EverySideHasAClassAndAnInstance(unittest.TestCase):
    def test_NON_VACUITY_the_population_is_measured_not_asserted(self) -> None:
        sides = _sides()
        self.assertEqual(51, len(sides), "side count moved; re-measure rather than edit")
        census = collections.Counter(C.classify_side(p) for _, _, p in sides)
        # Re-MEASURE if this moves. It is here so a side quietly changing class faces a test.
        self.assertEqual(dict(census), {"effect": 16, "nominal": 13, "tool-enum": 8, "always": 7,
                                        "composed": 5, "topology": 2})
        closure = collections.Counter(C.derive_closure(p) for _, _, p in sides)
        self.assertEqual(closure["shipped"], 2, "U01/U02's guards name only Keel's own probe")
        # Every open vocabulary is on a GUARD side, where a missing spelling fails closed (an
        # undischarged demand). No occasion is open: the loader refuses one at load.
        self.assertEqual(closure["open"], 11)
        self.assertEqual([], [f"{cid}.{n}" for cid, n, p in sides
                              if n != "discharged_by" and C.derive_closure(p) == "open"])

    def test_TEETH_shipped_means_every_name_is_ours(self) -> None:
        for cid, name, predicate in _sides():
            if C.derive_closure(predicate) == "shipped":
                with self.subTest(side=f"{cid}.{name}"):
                    self.assertTrue(set(C.vocabulary(predicate)) <= C.SHIPPED_PROGRAMS)

    def test_TEETH_the_instance_covers_every_side_and_is_current(self) -> None:
        text = CLAUSES_V.read_text(encoding="utf-8")
        for cid, name, _ in _sides():
            with self.subTest(side=f"{cid}.{name}"):
                self.assertIn(f"(* SIDE {cid}_{name} *)", text)
        done = subprocess.run([sys.executable, str(REPO / "tools" / "render_coverings.py"),
                               "--check"], capture_output=True, text=True)
        self.assertEqual(0, done.returncode, done.stdout + done.stderr)

    @unittest.skipIf(shutil.which("coqc") is None, "coqc absent: NOT-EVALUABLE here, graded in CI")
    def test_TEETH_the_proof_compiles_with_zero_axioms(self) -> None:
        done = subprocess.run([sys.executable, str(REPO / "tools" / "check_coq.py")],
                              capture_output=True, text=True)
        self.assertEqual(0, done.returncode, done.stdout + done.stderr)
        self.assertIn("axioms=0", done.stdout)
        self.assertIn("sides=51", done.stdout)

    def test_the_loader_refuses_an_authored_excuse(self) -> None:
        """Plant a `guard_vocabulary` back onto U03: the LOADER refuses the whole table."""
        smoke_replace(
            self, CLAUSES,
            b'"id": "U03",\n', b'"id": "U03",\n    "guard_vocabulary": {"closure": "open"},\n',
            "tests.test_derived_closure.EverySideHasAClassAndAnInstance."
            "test_NON_VACUITY_the_population_is_measured_not_asserted",
            "CLAUSE-CARRIES-AN-EXCUSE")

    def test_the_loader_refuses_a_textual_side(self) -> None:
        """Turn A01's guard back into a regex over the raw command: refused, with no exemption."""
        smoke_replace(
            self, CLAUSES,
            b'"discharged_by": {\n      "kind": "program",\n      "on": "tool_input.command",\n'
            b'      "argv": [\n        [\n          "git",\n          "status"\n        ]\n'
            b'      ]\n    }',
            b'"discharged_by": {\n      "kind": "regex",\n      "on": "tool_input.command",\n'
            b'      "pattern": "git status"\n    }',
            "tests.test_derived_closure.EverySideHasAClassAndAnInstance."
            "test_NON_VACUITY_the_population_is_measured_not_asserted",
            "CLAUSE-TEXT-COVERING")

    def test_a_stale_instance_is_loud(self) -> None:
        """Drop one side's block from Clauses.v: `--check` reports drift."""
        smoke_replace(
            self, CLAUSES_V,
            b"(* SIDE U03_fingerprint *)", b"(* SIDE U03_fingerprint_gone *)",
            "tests.test_derived_closure.EverySideHasAClassAndAnInstance."
            "test_TEETH_the_instance_covers_every_side_and_is_current",
            "U03_fingerprint")


if __name__ == "__main__":
    unittest.main()
