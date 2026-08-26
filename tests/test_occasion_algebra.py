"""Two clauses that fire on the same occasion, and a clause that fires on none.

`clauses.json` says when each clause arms, but nothing computed what those conditions actually
RANGE OVER, so two questions had no mechanism: does any clause overlap another, and does any clause
have an occasion at all. Both were answered by reading, and reading does not scale past 24 clauses.

This module computes each command fingerprint's EXTENSION -- the set of commands it matches -- over
the corpus formed by every clause's own fixtures, and compares extensions instead of patterns. That
is why it finds what a digest cannot: two clauses can be spelled differently and still arm on the
same commands, and a digest reports them as unrelated.

OVERLAP IS DECLARED, NEVER CONDEMNED. Three of the four relations it finds are a general clause
layered with a specific one -- A01 denies a push nobody checked, A03 a force-push nobody fetched --
and a check that condemned subsumption outright would go red on all three for no defect. A gate
firing on lookalikes is itself Asymmetric: the noise does not heal, the gate gets disabled, and its
real catches go with it. So `OVERLAPS.tsv` carries a row per relation with the reason, and this
module fails on an UNDECLARED relation and on a declared one that no longer holds.

RESIDUE, stated rather than implied. The fixture corpus is far narrower than real traffic. It
cannot find an overlap only real commands exhibit, and it proves nothing about disjointness: two
fingerprints agreeing here may still diverge elsewhere. It reports candidates, not proofs. Proving
disjointness needs regular-language algebra, which is sound in theory -- all 24 fingerprints are
regular -- but unavailable in practice: `greenery` 4.2.2 parses 3 of 20, rejecting the rest on `\\b`,
whose desugaring is the real cost of that route and whose wrong implementation yields a false clean.

The A02/U20 row is the one relation both corpora found: partial overlap here, strict subsumption
over 2266 real Bash calls. It is the only pair where both clauses are live.
"""
from __future__ import annotations

import itertools
import json
import re
import unittest
from pathlib import Path

from tests.plant_support import PLUGIN, REPO, smoke_replace

CLAUSES = PLUGIN / "keel" / "clauses.json"
# Beside MEASURED.tsv at the repository root, NOT inside `plugin/`: `plugin/` is what the
# marketplace installs, so a ledger only the suite reads would ship to every user's machine.
LEDGER = REPO / "OVERLAPS.tsv"
HEADER = ("A", "RELATION", "B", "WITNESS", "WHY")
COMMAND = "tool_input.command"


def clauses():
    loaded = json.loads(CLAUSES.read_text(encoding="utf-8"))
    return loaded["clauses"] if isinstance(loaded, dict) else loaded


def corpus(records):
    """Every command string any clause offers as a fixture, positive or negative.

    Derived from the input's own structure rather than a hand-written sample: a sample cannot
    report what it omits, and one written today goes stale the first time a clause is added.
    """
    return sorted({f for c in records for key in ("fixtures_pos", "fixtures_neg")
                   for f in (c.get(key) or []) if isinstance(f, str)})


def extensions(records, commands):
    """{clause id: frozenset of corpus indices its fingerprint matches}."""
    out = {}
    for c in records:
        fp = c.get("fingerprint")
        if isinstance(fp, dict) and fp.get("kind") == "regex" and fp.get("on") == COMMAND:
            pattern = re.compile(fp["pattern"])
            out[c["id"]] = frozenset(n for n, s in enumerate(commands) if pattern.search(s))
    return out


def relation(a, b):
    """How extension `a` stands to extension `b`, or None when they share nothing."""
    if not a or not b or not (a & b):
        return None
    if a == b:
        return "IDENTICAL"
    if b < a:
        return "SUPERSET"
    if a < b:
        return "SUBSET"
    return "OVERLAP"


def ledger_rows():
    rows = []
    lines = [l for l in LEDGER.read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.startswith("#")]
    for number, raw in enumerate(lines, 1):
        fields = raw.split("\t")
        if len(fields) != len(HEADER):
            raise AssertionError(
                f"OVERLAPS.tsv row {number}: expected {len(HEADER)} tab-separated fields "
                f"{HEADER}, got {len(fields)}")
        rows.append(tuple(fields))
    return rows


class OccasionAlgebra(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.records = clauses()
        self.commands = corpus(self.records)
        self.ext = extensions(self.records, self.commands)
        self.byid = {c["id"]: c for c in self.records}
        # Absence is a failure, never a skip: no corpus means nothing was compared, and reporting
        # that as a pass is the exact shape this file exists to refuse.
        self.assertTrue(self.commands, "no fixture commands; nothing was compared")
        self.assertTrue(self.ext, "no command fingerprints; nothing was compared")

    def _live(self, clause_id):
        return not self.byid[clause_id].get("_quarantine_reason")

    def _found(self):
        """{(A, B): RELATION} for every pair sharing at least one command, A before B in id order."""
        out = {}
        for a, b in itertools.combinations(sorted(self.ext), 2):
            rel = relation(self.ext[a], self.ext[b])
            if rel:
                out[(a, b)] = rel
        return out

    def test_every_live_clause_has_an_occasion(self):
        """A fingerprint matching nothing is a clause that can never fire -- the stone case."""
        for clause_id, matched in sorted(self.ext.items()):
            if matched or not self._live(clause_id):
                continue
            self.fail(
                f"{clause_id} is live and its fingerprint matches none of the "
                f"{len(self.commands)} fixture commands: it can never fire. Either give it a "
                f"fixture that exercises its occasion, or quarantine it with the denominator that "
                f"measured the absence -- absence is never a pass.")

    def test_every_clause_matches_its_own_positive_fixtures(self):
        """A positive fixture its own fingerprint misses means the two disagree about the occasion."""
        for clause_id in sorted(self.ext):
            fp = self.byid[clause_id]["fingerprint"]
            pattern = re.compile(fp["pattern"])
            missed = [f for f in (self.byid[clause_id].get("fixtures_pos") or [])
                      if isinstance(f, str) and not pattern.search(f)]
            self.assertFalse(
                missed,
                f"{clause_id}: fingerprint does not match its own fixtures_pos {missed}")

    def test_every_relation_is_declared(self):
        declared = {(a, b) for a, _, b, _, _ in ledger_rows()}
        undeclared = sorted(f"{a} {rel} {b}" for (a, b), rel in self._found().items()
                            if (a, b) not in declared)
        self.assertFalse(
            undeclared,
            f"clause pairs sharing an occasion with no row in OVERLAPS.tsv: {undeclared}. "
            f"Declare each with its reason, or change a fingerprint so they stop overlapping.")

    def test_every_declared_relation_still_holds(self):
        found = self._found()
        for a, rel, b, witness, _ in ledger_rows():
            for clause_id in (a, b):
                self.assertIn(clause_id, self.ext,
                              f"OVERLAPS.tsv names {clause_id}, which has no command fingerprint")
            self.assertEqual(
                rel, found.get((a, b)),
                f"OVERLAPS.tsv declares {a} {rel} {b}; the fixture corpus now shows "
                f"{found.get((a, b)) or 'no shared command'}. The declaration went stale.")
            index = self.commands.index(witness) if witness in self.commands else None
            self.assertIsNotNone(
                index, f"OVERLAPS.tsv witness for {a}/{b} is no longer a fixture: {witness!r}")
            for clause_id in (a, b):
                self.assertIn(
                    index, self.ext[clause_id],
                    f"OVERLAPS.tsv witness for {a}/{b} is no longer matched by {clause_id}: "
                    f"{witness!r}")

    def test_only_one_declared_pair_has_both_clauses_live(self):
        """Two live clauses on one command means two denials with two remedies.

        Recurring double-denial is Asymmetric by GROUND's own test, so the count is pinned rather
        than left to drift: a new live pair must be argued for, not merely declared.
        """
        both_live = sorted((a, b) for a, _, b, _, _ in ledger_rows()
                           if self._live(a) and self._live(b))
        self.assertEqual(
            [("A02", "U20")], both_live,
            "the set of declared overlaps where BOTH clauses are live has changed. Each one makes "
            "a single command raise two denials with unrelated remedies; that is the noise that "
            "gets a gate disabled.")

    def test_the_check_can_fail(self):
        """Widen one fingerprint so it swallows another, and this module must go red naming both.

        smoke_replace runs the named test GREEN on the unmutated file first: a plant satisfied by
        red-with-fault alone is satisfied by a target that is red always.
        """
        smoke_replace(
            self, CLAUSES,
            b'"pattern": "(?:^|[;&|\\\\n]\\\\s*)\\\\s*(?:git\\\\s+apply|patch\\\\s+-p\\\\d+)\\\\b"',
            b'"pattern": "(?:^|[;&|\\\\n]\\\\s*)\\\\s*(?:git\\\\s+apply|patch\\\\s+-p\\\\d+|rm)\\\\b"',
            "tests.test_occasion_algebra.OccasionAlgebra.test_every_relation_is_declared",
            "U12",
        )


if __name__ == "__main__":
    unittest.main()
