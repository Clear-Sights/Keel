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
from keel import clauses as C
from keel.clauses import _base_predicate, load_default

CLAUSES = PLUGIN / "keel" / "clauses.json"
# Beside MEASURED.tsv at the repository root, NOT inside `plugin/`: `plugin/` is what the
# marketplace installs, so a ledger only the suite reads would ship to every user's machine.
LEDGER = REPO / "OVERLAPS.tsv"
HEADER = ("A", "RELATION", "B", "WITNESS", "WHY")
COMMAND = "tool_input.command"


def clauses():
    loaded = json.loads(CLAUSES.read_text(encoding="utf-8"))
    return loaded["clauses"] if isinstance(loaded, dict) else loaded


def observations(records):
    """Every effect RECORD any clause offers as a fixture, positive or negative -- the corpus the
    effect occasions range over, beside the command corpus below. Canonical JSON, so two clauses
    offering the same observation index the same element."""
    seen = {}
    for c in records:
        for key in ("fixtures_pos", "fixtures_neg"):
            for f in (c.get(key) or []):
                if isinstance(f, dict) and isinstance(f.get("keel_effect"), dict):
                    seen.setdefault(json.dumps(f["keel_effect"], sort_keys=True), f)
    return [seen[k] for k in sorted(seen)]


def corpus(records):
    """Every command string any clause offers as a fixture, positive or negative.

    Derived from the input's own structure rather than a hand-written sample: a sample cannot
    report what it omits, and one written today goes stale the first time a clause is added.
    """
    return sorted({f for c in records for key in ("fixtures_pos", "fixtures_neg")
                   for f in (c.get(key) or []) if isinstance(f, str)})


def extensions(records, commands, records_seen=()):
    """{clause id: frozenset of corpus elements its fingerprint matches}.

    Two corpora, one index space: a COMMAND fingerprint ranges over the command strings and an
    EFFECT fingerprint over the observation records, and an element is tagged with which. An
    `always` fingerprint matches every element of both by construction and is left out; the
    totality law below says it is graded by its corpus session instead.

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
        if not isinstance(fp, dict):
            continue
        event = {"hook_event_name": c.get("event"),
                 "tool_name": (c.get("tools") or ["Bash"])[0],
                 "session_id": "occasion-algebra"}
        if fp.get("on") == COMMAND:
            out[c["id"]] = frozenset(
                ("cmd", n) for n, s in enumerate(commands)
                if _base_predicate(fp, {**event, "tool_input": {"command": s}}))
        elif C.classify_side(fp) == "effect":
            out[c["id"]] = frozenset(
                ("rec", n) for n, r in enumerate(records_seen)
                if _base_predicate(fp, {**event, **r}))
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
        self.seen = observations(self.records)
        self.ext = extensions(self.records, self.commands, self.seen)
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
                f"{len(self.commands)} fixture commands or {len(self.seen)} observations: it can "
                f"never fire. Either give it a "
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

        ungraded = sorted(c["id"] for c in self.records
                          if c["id"] not in self.ext and c["id"] not in declared)
        self.assertFalse(
            ungraded,
            f"these clauses are held by nothing: {ungraded}. `extensions()` drops them (their "
            f"fingerprint is not a regex on {COMMAND!r}) and no session in eval/corpus declares "
            f"them -- so nothing in this repository has observed them deny. Either give one a "
            f"corpus session naming it, or withdraw it. There is no third disposition.")

    def test_every_clause_is_driven_through_the_real_dispatcher(self):
        """Every clause has a session that drives it.

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

        There is no third disposition: nothing parks a clause.
        """
        corpus = REPO / "eval" / "corpus"
        declared = set()
        for session in sorted(corpus.glob("*.jsonl")):
            header = json.loads(session.read_text().splitlines()[0])
            if header.get("clause"):
                declared.add(header["clause"])
        undriven = sorted(c["id"] for c in self.records if c["id"] not in declared)
        self.assertFalse(
            undriven,
            f"these clauses have never been observed denying through the real dispatcher: "
            f"{undriven}. Being extended by the occasion algebra is not that -- it says the "
            f"fingerprint could match something, not that the clause denied. Add a session to "
            f"eval/corpus declaring the clause.")

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

    def test_the_fixture_law_refuses_a_table_whose_fixtures_disagree(self):
        """The fixture law lives in `clauses._admit`, and nothing witnessed it.

        What stood here instead was a test that could not fail. It re-derived the positive-fixture
        law itself -- `re.compile(fingerprint["pattern"]).search(fixture)` -- over the clauses in
        `self.ext`, i.e. exactly the regex-kind fingerprints. But `_admit` already applies
        `_base_predicate` to every clause's discriminator at LOAD time, and for a regex-kind
        fingerprint `_base_predicate` requires that same `re.search` to hit before it looks at
        anything else. So any clause the old test could have caught raised CLAUSE-FIXTURE-POS-MISS
        inside `load_default()` in this class's own setUp, before its body ever ran: the assertion
        was implied by its own precondition. It was also strictly weaker than the thing it
        shadowed -- it never applied `unless`, never used `_discriminator` (so terminal clauses,
        whose fixtures test the GUARD, were outside it entirely), and never checked the negative
        half at all.

        This tests the enforcement that actually exists, by planting a fault in the table and
        requiring the load to refuse it -- both halves, over the real predicate."""
        bundle = json.loads((PLUGIN / "keel" / "clauses.json").read_text())
        self.assertTrue(bundle, "no clauses, so nothing below is being tested")

        def load_planted(records):
            with tempfile.TemporaryDirectory(prefix="keel-fixture-plant-") as name:
                path = Path(name) / "clauses.json"
                path.write_text(json.dumps(records), encoding="utf-8")
                return C.load_bundle(path)

        # The unplanted table must load, or a refusal below proves nothing about the plant.
        self.assertEqual(len(bundle), len(load_planted(bundle)),
                         "the shipped table does not load unplanted; the plants below are void")

        planted_pos = planted_neg = 0
        for index, record in enumerate(bundle):
            for slot, sentinel, kind in (("fixtures_pos", "keel-fixture-plant-no-clause-matches-this",
                                          "CLAUSE-FIXTURE-POS-MISS"),
                                         ("fixtures_neg", None, "CLAUSE-FIXTURE-NEG-HIT")):
                if slot == "fixtures_neg":
                    # PLANT the other direction with a string the clause's OWN positive fixture
                    # uses, so the negative half is required to be excluded by the real predicate.
                    positives = [f for f in (record.get("fixtures_pos") or []) if isinstance(f, str)]
                    if not positives:
                        continue
                    sentinel = positives[0]
                elif not [f for f in (record.get("fixtures_pos") or []) if isinstance(f, str)]:
                    continue
                copy = [dict(r) for r in bundle]
                copy[index] = dict(record)
                copy[index][slot] = [sentinel]
                with self.assertRaises(C.ClauseError) as caught:
                    load_planted(copy)
                self.assertEqual(kind, caught.exception.code,
                                 f"{record['id']}: planting {slot} raised "
                                 f"{caught.exception.code}, not {kind}")
                self.assertIn(record["id"], caught.exception.detail,
                              f"{record['id']}: the refusal does not name the clause it refused")
                if slot == "fixtures_pos":
                    planted_pos += 1
                else:
                    planted_neg += 1

        self.assertGreater(planted_pos, 0, "no positive fixture was planted, so nothing was shown")
        self.assertGreater(planted_neg, 0, "no negative fixture was planted, so nothing was shown")
        print(f"DENOMINATOR subject=fixture-law clauses={len(bundle)} "
              f"pos-plants={planted_pos} neg-plants={planted_neg}")

    def test_no_positive_fixture_is_one_the_clause_cannot_key(self):
        """A fixture the clause cannot key is not evidence that the clause covers it.

        `_admit` checked positive fixtures against the FINGERPRINT only. A clause whose `subject`
        is an extractor needs one thing more: when the extractor finds no operand, the dispatcher
        treats the event as NOT-EVALUABLE and passes it -- correctly, since an empty key would
        merge every demand for the clause into one bucket. So a fixture could match the
        fingerprint, be admitted as evidence that the occasion is covered, and be silently
        unenforceable.

        Measured when this law was added: A02 declared three positive fixtures and could deny
        exactly one. `git clean -fd` and `find . -name '*.tmp' -delete` name no trailing-slash
        path, its extractor returned "", and the shipped dispatcher ALLOWED both -- a bulk delete
        walking past the clause written to stop it.
        """
        bundle = json.loads((PLUGIN / "keel" / "clauses.json").read_text())
        # An effect subject (`{"effect": "files_changed"}`) is keyed on the datum the record
        # carries, not on an operand extracted from the event; it has no pattern to defeat.
        with_extractor = [r for r in bundle
                          if isinstance(r.get("subject"), dict) and "pattern" in r["subject"]]
        self.assertTrue(with_extractor, "no clause keys on an extractor; this law is vacuous")

        planted = 0
        for record in with_extractor:
            # String or record fixtures alike: the loader resolves the extractor's field from
            # either, so an effect clause keyed on an operand is held to this law too.
            positives = list(record.get("fixtures_pos") or [])
            if not positives:
                continue
            copy = [dict(r) for r in bundle]
            index = bundle.index(record)
            copy[index] = dict(record)
            copy[index]["subject"] = dict(record["subject"])
            # An extractor that cannot match anything: the exact shape A02 shipped with.
            copy[index]["subject"]["pattern"] = "(keel-no-operand-can-match-this)"
            with tempfile.TemporaryDirectory(prefix="keel-unkeyable-") as name:
                path = Path(name) / "clauses.json"
                path.write_text(json.dumps(copy), encoding="utf-8")
                with self.assertRaises(C.ClauseError) as caught:
                    C.load_bundle(path)
            self.assertEqual("CLAUSE-FIXTURE-POS-UNKEYABLE", caught.exception.code,
                             f"{record['id']}: {caught.exception.code}")
            planted += 1
        self.assertGreater(planted, 0, "nothing was planted, so nothing was shown")
        print(f"DENOMINATOR subject=unkeyable-fixture extractors={len(with_extractor)} "
              f"plants={planted}")

    def test_A02_denies_the_first_act_whatever_it_is(self):
        """The behaviour behind the `always` occasion, driven through the real dispatcher.

        A02 used to name `rm`, `find`, `truncate` and `git clean`, and two of its three declared
        occasions were allowed by the shipped plugin. It now fires on the first act of a session
        that has listed nothing, because before the act nothing but the name told a bulk delete
        from `ls`; so every first act is denied, naming A02, and its guard -- a host Glob, or a
        Read of Keel's own listing -- is not."""
        with tempfile.TemporaryDirectory(prefix="keel-a02-") as state:
            for command in ("rm -rf build/", "git clean -fd", "echo hello", "python3 x.py"):
                denied, _ = self._drive(command, f"a02-{abs(hash(command))}", state)
                self.assertIn("A02", denied,
                              f"{command!r} is a first act and the dispatcher answered {denied!r}")
            # The guard is a host Glob: it lists a set through the closed tool enum, so it
            # licenses A02 before the first act -- and is itself refused by nothing.
            allowed, _ = self._drive("build/**", "a02-guard", state, tool="Glob")
            self.assertEqual([], allowed, "A02's own guard was refused")
            denied, _ = self._drive("rm -rf build/", "a02-guard", state)
            self.assertNotIn("A02", denied, "the listing did not license A02")
            self.assertIn("A01", denied, "the listing licensed more than A02")

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
            index = None
            if witness in self.commands:
                index = ("cmd", self.commands.index(witness))
            else:
                keys = [json.dumps(r["keel_effect"], sort_keys=True) for r in self.seen]
                try:
                    index = ("rec", keys.index(json.dumps(json.loads(witness), sort_keys=True)))
                except (ValueError, TypeError):
                    index = None
            self.assertIsNotNone(
                index, f"OVERLAPS.tsv witness for {a}/{b} is no longer a fixture: {witness!r}")
            for clause_id in (a, b):
                self.assertIn(
                    index, self.ext[clause_id],
                    f"OVERLAPS.tsv witness for {a}/{b} is no longer matched by {clause_id}: "
                    f"{witness!r}")

    def _drive(self, command, session, state, tool="Bash"):
        """One PreToolUse event through the real dispatcher; return (denying id, quoted remedy)."""
        event = json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool,
                            "session_id": session, "cwd": "/tmp",
                            "tool_input": {"command": command} if tool == "Bash"
                            else {"pattern": command}})
        done = subprocess.run(
            [sys.executable, "-m", "keel.dispatch"], input=event, text=True, capture_output=True,
            env={**os.environ, "KEEL_STATE_DIR": state, "CLAUDE_PLUGIN_ROOT": str(PLUGIN),
                 "PYTHONPATH": str(PLUGIN)})
        body = json.loads(done.stdout or "{}")
        reason = (body.get("hookSpecificOutput") or {}).get("permissionDecisionReason") or ""
        denied = re.findall(r"\[([A-Z]\d\d(?:-[a-z-]+)?)\]", reason)
        remedy = re.search(r"`([^`]+)`", reason)
        return denied, (remedy.group(1) if remedy else None)

    def _post(self, keel_effect: dict, session, state):
        event = json.dumps({"hook_event_name": "PostToolUse", "tool_name": "Bash",
                            "session_id": session, "cwd": "/tmp",
                            "tool_input": {"command": "<observed>"}, "keel_effect": keel_effect})
        subprocess.run(
            [sys.executable, "-m", "keel.dispatch"], input=event, text=True, capture_output=True,
            env={**os.environ, "KEEL_STATE_DIR": state, "CLAUDE_PLUGIN_ROOT": str(PLUGIN),
                 "PYTHONPATH": str(PLUGIN)})

    def _sequences(self):
        """Per declared pair: put the shared observation to the dispatcher, then ask the next
        call, and record which of the pair the ONE refusal names.

        THE DISPATCHER, NOT A READING OF THE TABLE. A shared occasion is not a double denial any
        more: a refusal names every clause refusing, at once, so two clauses on one effect cost
        one interruption listing two guards. What is measured is that both are named -- neither
        is silently shadowed by the other -- and each guard pays its own.
        """
        results = {}
        for a, _rel, b, witness, _why in ledger_rows():
            with tempfile.TemporaryDirectory() as state:
                session = f"algebra-{a}-{b}"
                for opening in ("git status", "git fetch origin"):
                    self._drive(opening, session, state)
                self._post(json.loads(witness), session, state)
                named, _ = self._drive("echo next", session, state)
                results[(a, b)] = ("both" if a in named and b in named
                                   else ("one" if a in named or b in named else "none"), named)
        return results

    def test_every_declared_pair_is_named_together_by_one_refusal(self):
        """Pinned to what the dispatcher does: a pair sharing an occasion is refused ONCE, naming
        both, so neither clause is shadowed and the session learns both guards in one message."""
        sequences = self._sequences()
        self.assertTrue(sequences, "no declared pairs were driven; nothing was measured")
        self.assertEqual(
            [], sorted(f"{a}/{b}={kind}:{who}" for (a, b), (kind, who) in sequences.items()
                       if kind != "both"),
            "a declared pair no longer answers the shared occasion with one refusal naming both")

    def test_the_check_can_fail(self):
        """Widen one fingerprint so it swallows another, and this module must go red naming both.

        smoke_replace runs the named test GREEN on the unmutated file first: a plant satisfied by
        red-with-fault alone is satisfied by a target that is red always.
        """
        smoke_replace(
            self, CLAUSES,
            # RE-AIMED for the effect representation. The fault is unchanged: widen one
            # fingerprint until it swallows occasions another clause owns, and this module must
            # go red naming the pair. U09 reads `head_switched` -- HEAD moved to a commit that
            # already existed. Widened to `head_moved` it also claims every commit U08 owns and
            # every reset U20 owns, and the algebra reports the undeclared pairs. The `expected`
            # string below was read off that run, not predicted.
            b'"effect": "head_switched"',
            b'"effect": "head_moved"',
            "tests.test_occasion_algebra.OccasionAlgebra.test_every_relation_is_declared",
            "U08 SUBSET U09",
        )


if __name__ == "__main__":
    unittest.main()
