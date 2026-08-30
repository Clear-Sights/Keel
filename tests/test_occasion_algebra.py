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
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.plant_support import PLUGIN, REPO, smoke_replace
from keel.clauses import _regex_predicate, load_default, waiver_status

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
    """{clause id: frozenset of corpus indices its fingerprint matches}.

    THE DISPATCHER'S OWN MATCHER, imported rather than rebuilt. This function used to compile
    `fp["pattern"]` and search with it, which is most of what a fingerprint means and not all of
    it: `unless` entries subtract from the match, and a second copy of the rule here answered a
    question the plugin does not ask. It went wrong the first time it mattered -- U20 was narrowed
    with an `unless` so it would stop claiming the deletes A02 owns, the dispatcher stopped
    raising both, and this module still reported the overlap because it could not see the field.

    A private name is imported deliberately. The alternative is a second writer for "what a
    fingerprint matches", which is the defect `C14-one-path-one-writer` is about, and this module
    exists to compare clauses against each other -- it can afford no disagreement with the thing
    that actually matches them.
    """
    out = {}
    for c in records:
        fp = c.get("fingerprint")
        if isinstance(fp, dict) and fp.get("kind") == "regex" and fp.get("on") == COMMAND:
            out[c["id"]] = frozenset(n for n, s in enumerate(commands)
                                     if _regex_predicate(fp, s))
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



def rendered(sequences):
    """The measured sequences, in the shortest form that still identifies each pair."""
    return ", ".join(f"{a}/{b}={kind}" + (f"->{who}" if who else "")
                     for (a, b), (kind, who) in sorted(sequences.items()))


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
            if matched:
                continue
            self.fail(
                f"{clause_id} is live and its fingerprint matches none of the "
                f"{len(self.commands)} fixture commands: it can never fire. Either give it a "
                f"fixture that exercises its occasion, or withdraw it. It cannot be parked: this "
                f"table has no field that stops a clause firing.")

    def test_no_clause_escapes_both_the_algebra_and_the_corpus(self):
        """Every clause is graded by SOMETHING. A clause in neither place is graded by nothing.

        `extensions()` admits a clause only when its fingerprint is `kind: regex` AND keyed
        `on: tool_input.command`. That is correct for what this module computes -- an algebra over
        command strings -- but it is a silent filter, and the two laws above range over its output.
        A clause it drops is not held to them and nothing said so: no warning, no count, no `else`.

        Seven of the twenty-four are dropped today. Four are `kind: always` (C03, C08, T01, T02)
        and three are keyed `on: tool_name` (D01, P01, P02). Before this law, five of those seven
        had no evidence of any kind that they can deny, and the table-wide guarantee read as
        though it covered them.

        This is the totality: a clause is either extended here, or it is named by a replay session
        in `eval/corpus`, which drives it through the real dispatcher and requires the denial to
        name it. Neither is a subset of the other and a clause may have both. What no clause may
        have is neither.
        """
        corpus = REPO / "eval" / "corpus"
        declared = set()
        for session in sorted(corpus.glob("*.jsonl")):
            header = json.loads(session.read_text().splitlines()[0])
            if header.get("clause"):
                declared.add(header["clause"])

        # A clause parked by a LIVE waiver is the third disposition, and it is a real one: it
        # cannot be driven, because `_applicable` skips it. It is not silence -- the waiver
        # carries its research and an expiry. The expiry is why this stays honest: on the day it
        # lapses the clause enforces again with no edit, and this law goes red until a session
        # for it exists. Inaction restores the demand rather than retiring it.
        parked = {clause.id for clause in load_default()
                  if waiver_status(clause) == "live"}

        ungraded = sorted(c["id"] for c in self.records
                          if c["id"] not in self.ext and c["id"] not in declared
                          and c["id"] not in parked)
        self.assertFalse(
            ungraded,
            f"these clauses are held by nothing: {ungraded}. `extensions()` drops them (their "
            f"fingerprint is not a regex on {COMMAND!r}), no session in eval/corpus declares "
            f"them, and no live waiver parks them -- so nothing in this repository has observed "
            f"them deny. Either give one a corpus session naming it, or withdraw it. If one was "
            f"parked, its waiver has lapsed and the clause is enforcing again.")

    def test_every_clause_is_driven_through_the_real_dispatcher(self):
        """Every clause not parked by a live waiver has a session that drives it.

        The totality law above accepts three dispositions, and one of them -- extension by the
        occasion algebra -- is a property of a clause's FINGERPRINT, not evidence that the
        clause denies. Under that law alone a corpus session could be deleted and nothing
        would go red, because the algebra still holds the clause. Measured: removing U24's
        session left the whole suite green.

        That is a weaker standard than the sibling repositories meet. Ward requires a session
        in eval/corpus for all twelve of its rows and for its fail-closed preflight; Makoto
        fires every live gate through its real .run(ctx). This law brings Keel to the same
        bar: the algebra says a clause COULD match something, a session says it DID deny, and
        replay requires the first fire to name the clause the session declares, so a session
        is evidence about its own row rather than about the table.

        A live waiver is still the third disposition and still a real one -- it cannot be
        driven because `_applicable` skips it -- and it carries research and an expiry, so on
        the day it lapses the clause enforces again and this law goes red with no edit.
        """
        corpus = REPO / "eval" / "corpus"
        declared = set()
        for session in sorted(corpus.glob("*.jsonl")):
            header = json.loads(session.read_text().splitlines()[0])
            if header.get("clause"):
                declared.add(header["clause"])
        parked = {clause.id for clause in load_default()
                  if waiver_status(clause) == "live"}
        undriven = sorted(c["id"] for c in self.records
                          if c["id"] not in declared and c["id"] not in parked)
        self.assertFalse(
            undriven,
            f"these clauses have never been observed denying through the real dispatcher: "
            f"{undriven}. Being extended by the occasion algebra is not that -- it says the "
            f"fingerprint could match something, not that the clause denied. Add a session to "
            f"eval/corpus declaring the clause, or park it with a waiver carrying research and "
            f"an expiry.")

    def test_every_corpus_session_declares_a_clause_that_exists(self):
        """A session naming a clause the table does not carry grades a rule nobody ships."""
        corpus = REPO / "eval" / "corpus"
        known = {c["id"] for c in self.records}
        for session in sorted(corpus.glob("*.jsonl")):
            header = json.loads(session.read_text().splitlines()[0])
            declared = header.get("clause")
            if declared is None:
                self.assertEqual(
                    header.get("expect"), "none",
                    f"{session.name} declares no clause and is not a control session; a session "
                    f"that names no clause is evidence about nothing")
                continue
            self.assertIn(declared, known,
                          f"{session.name} declares {declared}, which is not a clause in "
                          f"clauses.json")

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

    def _drive(self, command, session, state):
        """One PreToolUse event through the real dispatcher; return (denying id, quoted remedy)."""
        event = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                            "session_id": session, "cwd": "/tmp",
                            "tool_input": {"command": command}})
        done = subprocess.run(
            [sys.executable, "-m", "keel.dispatch"], input=event, text=True, capture_output=True,
            env={**os.environ, "KEEL_STATE_DIR": state, "CLAUDE_PLUGIN_ROOT": str(PLUGIN),
                 "PYTHONPATH": str(PLUGIN)})
        body = json.loads(done.stdout or "{}")
        reason = (body.get("hookSpecificOutput") or {}).get("permissionDecisionReason") or ""
        denied = re.search(r"\[([A-Z]\d\d(?:-[a-z-]+)?)\]", reason)
        remedy = re.search(r"`([^`]+)`", reason)
        return (denied.group(1) if denied else None), (remedy.group(1) if remedy else None)

    def _sequences(self):
        """Per declared pair: obey the deny, retry the same command, and record what happens.

        THE DISPATCHER, NOT A READING OF THE TABLE. Two plausible readings both got this wrong:

          * "both clauses are un-quarantined, so both fire" -- said all four pairs double-deny.
            `_quarantine_reason` was never read by the dispatcher, so it never suppressed
            anything; but U12/U13 still does not double-deny.
          * "no single command satisfies both discharges" -- said all four again, over 120
            candidate commands. Also wrong, and not repairable by adding candidates: the absence
            of a shared discharge cannot be proved from a sample.

        A third reading, held here briefly and also wrong, said U12/U13 was not a double denial at
        all. It is. That reading came from the ledger's own witness, `git apply --check
        generated.patch`, which U13 has never matched: U13's fingerprint carries an `unless`
        excluding the --check form, and nothing could see it while this module compiled
        `pattern` by hand. Correct the witness to a command U13 actually matches and the pair
        denies twice like the others. A wrong witness is a wrong measurement, not a safe one.
        """
        results = {}
        for a, _rel, b, witness, _why in ledger_rows():
            with tempfile.TemporaryDirectory() as state:
                session = f"algebra-{a}-{b}"
                first, remedy = self._drive(witness, session, state)
                if first is None:
                    results[(a, b)] = ("no-denial", None)
                elif not remedy:
                    results[(a, b)] = ("no-quoted-remedy", first)
                else:
                    self._drive(remedy, session, state)
                    second, _ = self._drive(witness, session, state)
                    results[(a, b)] = (("double" if second else "single"), second)
        return results

    def test_the_declared_pairs_that_double_deny(self):
        """Pinned to what the dispatcher does, so a fix shrinks this and a regression grows it.

        A double denial is one command answered twice with unrelated remedies. That is Asymmetric
        by GROUND's own test: the noise does not heal, the gate gets switched off, and the real
        catches leave with it.
        """
        sequences = self._sequences()
        self.assertTrue(sequences, "no declared pairs were driven; nothing was measured")
        double = sorted(pair for pair, (kind, _) in sequences.items() if kind == "double")
        self.assertEqual(
            [("A01", "A03"), ("U01", "U02"), ("U12", "U13")], double,
            "the set of declared overlaps answering one command with two unrelated remedies has "
            f"changed: {rendered(sequences)}")

    def test_every_pair_is_measurable_by_following_the_instruction(self):
        """A deny whose remedy is not a command cannot be obeyed mechanically, or measured here.

        Reported rather than skipped: a pair that drops out of the measurement above looks
        identical to one that passed it, and that is the shape this module refuses.
        """
        unmeasurable = sorted(f"{a}/{b} (denied by {who}, which quotes no command)"
                              for (a, b), (kind, who) in self._sequences().items()
                              if kind == "no-quoted-remedy")
        self.assertEqual(
            [], unmeasurable,
            "the set of declared pairs whose denial names no runnable remedy has changed; each "
            "is a pair this module cannot measure and a user cannot mechanically obey")

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
