"""A guard that names programs says whether its vocabulary is closed, and the loader checks it.

Coverings.v Thm 5: a nominal covering is MONOTONE in vocabulary. It is discharged by the names
it lists and defeated by doing the same act under any other name. Eleven of the 24 guards name
programs, and whether that is a hole is not readable from the name list -- `probe_child_
capability.py` is Keel's own and has no second name, while `pytest` stands in for a category
with no end. Same shape on the page, opposite meaning.

So each such guard declares its closure and argues it, and the loader refuses one that says
nothing -- the same shape as `why_no_program` for text coverings, one axis up. Three
dispositions:

  shipped   the program is this bundle's own; there is no other name for the act
  composed  a branch of the guard also matches `tool_name`, a CLOSED host enum, so the act is
            covered however the shell command is spelled
  open      the act has many names, no host surface performs it, and the argument says what was
            tried and why it was rejected

`open` is not a defect to be closed later by lengthening the list: a longer list is exactly as
monotone as a short one. It is a STATED LIMIT, and the checks below exist so it cannot be
softened into a closure it did not earn -- which is why `composed` is verified against the
table rather than believed: a clause may SAY it composed, and `_matches_a_tool_enum` asks
whether it did.
"""
from __future__ import annotations

import collections
import unittest

from tests.plant_support import PLUGIN, smoke_replace
from keel import clauses as C

CLAUSES = PLUGIN / "keel" / "clauses.json"


class EveryNominalGuardDeclaresItsClosure(unittest.TestCase):
    def setUp(self) -> None:
        self.clauses = C.load_default()
        self.nominal = [c for c in self.clauses if C._guard_names(c.discharged_by)]

    def test_NON_VACUITY_the_population_is_measured_not_asserted(self) -> None:
        """Without this, every cell below passes the day the last name list disappears."""
        self.assertTrue(self.nominal, "no guard names a program; this module grades nothing")
        census = collections.Counter(
            c.guard_vocabulary["closure"] for c in self.nominal)
        # Re-MEASURE this if it moves; never edit it to match a run. It is here so a closure
        # quietly changing from `open` to `composed` has to face a test.
        self.assertEqual(dict(census), {"open": 6, "composed": 3, "shipped": 2})
        self.assertEqual(len(self.nominal), 11)

    def test_TEETH_every_nominal_guard_carries_an_argued_closure(self) -> None:
        for clause in self.nominal:
            with self.subTest(clause=clause.id):
                declared = clause.guard_vocabulary or {}
                self.assertIn(declared.get("closure"), ("shipped", "composed", "open"))
                self.assertTrue(len(declared.get("why", "")) > 80,
                                "a closure asserted in a phrase is asserted, not argued")

    def test_TEETH_composed_is_verified_against_the_table(self) -> None:
        """The one that keeps `composed` from being a sentence. A clause claiming it must have a
        branch reading `tool_name`; otherwise the shell vocabulary is all there is and the claim
        is the opposite of true."""
        for clause in self.nominal:
            if clause.guard_vocabulary["closure"] != "composed":
                continue
            with self.subTest(clause=clause.id):
                self.assertTrue(C._matches_a_tool_enum(clause.discharged_by))

    def test_TEETH_an_open_closure_names_what_was_tried(self) -> None:
        """An `open` that does not say what was rejected is indistinguishable from one nobody
        looked at, and the second is the thing this whole axis exists to surface."""
        for clause in self.nominal:
            if clause.guard_vocabulary["closure"] != "open":
                continue
            with self.subTest(clause=clause.id):
                self.assertIn("TRIED AND REJECTED", clause.guard_vocabulary["why"],
                              "an open vocabulary must name the composition that was attempted")

    def test_the_check_can_fail(self) -> None:
        """Delete one clause's declaration: the LOADER must refuse the whole table.

        Aimed at the loader, not at this module, because a test-only bar is what let the guard
        side go un-witnessed in the first place -- the suite would assert a property of the JSON
        while the plugin happily shipped without it.
        """
        smoke_replace(
            self, CLAUSES,
            b'"closure": "open",\n      "why": "The guard names `ps` and `pgrep`',
            b'"closure": "opne",\n      "why": "The guard names `ps` and `pgrep`',
            "tests.test_guard_vocabulary.EveryNominalGuardDeclaresItsClosure."
            "test_TEETH_every_nominal_guard_carries_an_argued_closure",
            "CLAUSE-GUARD-VOCABULARY-UNDISPOSITIONED: U03",
        )

    def test_the_composed_check_can_fail(self) -> None:
        """Claim `composed` without composing. Two plants, because the two laws fail apart:
        the cell above catches a MISSING declaration, this one catches a FALSE one, and a false
        closure is the direction that quietly removes a stated limit."""
        smoke_replace(
            self, CLAUSES,
            b'"closure": "open",\n      "why": "The guard names `gpg`',
            b'"closure": "composed",\n      "why": "The guard names `gpg`',
            "tests.test_guard_vocabulary.EveryNominalGuardDeclaresItsClosure."
            "test_TEETH_composed_is_verified_against_the_table",
            "CLAUSE-GUARD-VOCABULARY-NOT-COMPOSED: U08",
        )


if __name__ == "__main__":
    unittest.main()
