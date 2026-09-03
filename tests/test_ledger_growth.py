"""A licence is a state transition, not an event log.

Re-observing the same guard in the same scope changes no ledger state, so retaining every
observation only makes every later read scan duplicate history. Measured through the dispatcher
before the fix: 40 identical guard calls wrote 120 rows -- three per call,
one per clause the guard discharges -- and each subsequent read is linear in what was written.

The Rust dispatcher has always carried this guard (`if self.licensed(s,a,id){return}`), so until
now the two implementations agreed on every VERDICT while disagreeing about what they WROTE. The
equivalence gate compares decisions, not their side effects, so it could not see that: 4401 calls
and 0 divergences held throughout.
"""

from __future__ import annotations

import os
import pathlib
import tempfile
import unittest
import unittest.mock

from tests.plant_support import PLUGIN, smoke_replace
from keel import clauses as C, dispatch
from keel.ledger import Demand, Ledger, derive_id


def rows_written(state: str) -> int:
    return sum(len([line for line in path.read_text().splitlines() if line.strip()])
               for path in pathlib.Path(state).rglob("*.jsonl"))


class RepeatedGuardsDoNotGrowTheLedger(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.state = self._temp.name
        previous = os.environ.get("KEEL_STATE_DIR")
        self.addCleanup(
            lambda: os.environ.pop("KEEL_STATE_DIR", None)
            if previous is None else os.environ.__setitem__("KEEL_STATE_DIR", previous))
        os.environ["KEEL_STATE_DIR"] = self.state

    def test_TEETH_forty_identical_guards_write_one_row_per_clause(self) -> None:
        # `load_default()`, the one loader production uses, and a floor under the table -- because
        # an upper bound alone is satisfied perfectly by a table that loaded NOTHING. This ran in
        # a layout with no loose clause directory, took an empty table, wrote zero rows, and
        # passed its `<= 10` assertion having exercised no deduplication at all; it went on
        # passing with the dedup guard deleted. An assertion that only bounds from above cannot
        # tell "correctly deduplicated" from "never ran", which is this project's own
        # absence-must-never-read-as-green law turned on one of its own tests. `load_default()` is
        # also what production loads, so the test now exercises the table users actually get.
        table = C.load_default()
        self.assertTrue(table, "an empty clause table makes the bound below vacuous")
        # A host Read: the guard three clauses (C03, D01, P01) are paid by in advance. No guard
        # reads a command, so a repeated Bash call would discharge nothing and prove nothing.
        event = {"hook_event_name": "PreToolUse", "tool_name": "Read",
                 "tool_input": {"file_path": "/work/repo/calc.py"},
                 "session_id": "s", "agent_id": "a"}
        for _ in range(40):
            dispatch.pre_tool_use(table, Ledger(), event)
        written = rows_written(self.state)
        self.assertGreater(written, 0, "40 guards wrote nothing: the ledger never ran")
        self.assertLessEqual(written, 10,
                             f"{written} rows for 40 identical guards; the ledger is an "
                             "obligation register, not an observation log")

    def test_TEETH_forty_identical_demands_write_one_row(self) -> None:
        """The DEMAND side of the same law, which nothing exercised.

        This module is titled "Repeated guards do not grow the ledger" and every test in it drove
        a DISCHARGE -- `pre_tool_use` with a host Read, `Ledger.discharge` directly -- so
        `Ledger.demand`'s own idempotence guard was never reached. MEASURED: with
        `if d.id in self.open_ids(...): return False` deleted, the whole suite returned OK and 40
        identical demands wrote 40 rows where the unmutated ledger writes 1. Half the subject of
        a module named for it was unmeasured.
        """
        ledger = Ledger()
        demand = Demand("s", "a", "U19", "build/", "a rewrite nobody looked at")
        results = [ledger.demand(demand) for _ in range(40)]
        self.assertEqual([True] + [False] * 39, results,
                         "`demand` must report False for a demand already open (idempotent)")
        self.assertEqual(1, rows_written(self.state),
                         f"{rows_written(self.state)} rows for 40 identical demands; a licence is "
                         "a state transition, not an event log")

    def test_TEETH_a_subagent_demand_does_not_block_the_main_thread(self) -> None:
        """Scope is `(session_id, agent_id)`, and the ledger's own docstring says so.

        `ledger.py` records this as a defect measured in a sibling plugin, not a hypothesis:
        "Pooling lets a sibling's dangling demand block every later Stop." Nothing held it.
        MEASURED: with `_ids` returning `("sid", "")` -- one line, agent scoping deleted -- the
        suite returned OK, while a main-thread Stop that had been blocking on its own single
        demand blocked instead on four, having inherited a subagent's.
        """
        table = C.load_default()
        ledger = Ledger()
        sub = {"hook_event_name": "PreToolUse", "session_id": "s1", "agent_id": "sub-7",
               "cwd": "/work/repo", "tool_name": "Bash", "tool_input": {"command": "echo hi"}}
        dispatch.pre_tool_use(table, ledger, sub)
        # READ FROM THE ROWS, NOT FROM A SCOPE. Asking `open_ids("s1", "sub-7")` for the
        # subagent's demands makes the scoping rule decide what the subject of this test is: with
        # `_ids` returning `("s1", "")` the query comes back empty and the test would go red for
        # having nothing to look at, instead of red for the pooling it exists to catch.
        borrowed = {row["clause_id"] for row in ledger._rows() if row.get("kind") == "demand"}
        self.assertTrue(borrowed,
                        "the subagent raised no demand, so this test would pass over nothing")
        main = dispatch.reconcile(table, ledger, {"hook_event_name": "Stop", "session_id": "s1"})
        named = str(main)
        leaked = sorted(c for c in borrowed if f"[{c}]" in named)
        self.assertEqual(
            [], leaked,
            f"the main thread's Stop names {leaked}, which only the subagent `sub-7` owes. "
            "Scope is keyed on (session_id, agent_id) precisely so a sibling's dangling demand "
            "cannot block every later Stop.")

    def test_TEETH_a_repeat_discharge_is_a_no_op(self) -> None:
        ledger = Ledger()
        demand_id = derive_id("s", "a", "T01", "x")
        ledger.demand(Demand("s", "a", "T01", "x", "guard first"))
        ledger.discharge("s", "a", demand_id, "observed")
        first = rows_written(self.state)
        for _ in range(20):
            ledger.discharge("s", "a", demand_id, "observed again")
        self.assertEqual(first, rows_written(self.state))
        # The licence itself must survive: skipping the write must not skip the state.
        self.assertNotIn(demand_id, ledger.open_ids("s", "a"))

    # makoto-allow: every assertion is delegated to `smoke_replace`, which asserts the plant
    # seam is present, the mutated run exits NON-ZERO, the named failure text appears, and
    # the file is byte-identical again afterwards. Observed failing: removing the dedup
    # guard makes this test red with `plant seam changed`.
    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red; a checker that cannot follow an imported helper reads this body as empty
        path = PLUGIN / "keel" / "ledger.py"
        smoke_replace(self, path,
                      b"        if self.is_licensed(session, agent, demand_id):\n            return\n",
                      b"", "tests.test_ledger_growth.RepeatedGuardsDoNotGrowTheLedger."
                      "test_TEETH_a_repeat_discharge_is_a_no_op", "AssertionError: 2 != 22")
        # The SAME seam again, against the OTHER test -- because a plant only defends the test it
        # names, and that is exactly how this module rotted. It always carried a plant, the plant
        # pointed at the repeat-discharge test, and the growth test beside it went vacuous
        # undetected. Coverage of a module is not coverage of its assertions.
        smoke_replace(self, path,
                      b"        if self.is_licensed(session, agent, demand_id):\n            return\n",
                      b"", "tests.test_ledger_growth.RepeatedGuardsDoNotGrowTheLedger."
                      "test_TEETH_forty_identical_guards_write_one_row_per_clause", "rows for 40 identical guards")
        # And the FLOOR, planted against the precise mechanism that made this test vacuous: an
        # empty table. Reading zero clauses satisfied the `<= 10` bound perfectly while exercising
        # nothing. The upper bound cannot tell that apart from a correct deduplication; only the
        # floor can, so the floor gets its own proof that it fires.
        smoke_replace(self, PLUGIN / "keel" / "clauses.py",
                      b"    return load_bundle(default_bundle())",
                      b"    return []", "tests.test_ledger_growth."
                      "RepeatedGuardsDoNotGrowTheLedger."
                      "test_TEETH_forty_identical_guards_write_one_row_per_clause", "an empty clause table makes the bound below vacuous")
        # The DEMAND-side dedup guard. Every plant above aims at the discharge side or at
        # `load_default`, which is exactly why this one was deletable with 246 tests green.
        smoke_replace(self, path,
                      b"        if d.id in self.open_ids(d.session, d.agent):\n            return False\n",
                      b"", "tests.test_ledger_growth.RepeatedGuardsDoNotGrowTheLedger."
                      "test_TEETH_forty_identical_demands_write_one_row",
                      "must report False for a demand already open")
        # Agent scoping. One line, and with it gone a subagent's demands block the main thread's
        # Stop -- the precise defect `ledger.py` records as measured in a sibling plugin.
        smoke_replace(self, PLUGIN / "keel" / "dispatch.py",
                      b'    return str(event.get("session_id") or ""), str(event.get("agent_id") or "")',
                      b'    return str(event.get("session_id") or ""), ""',
                      "tests.test_ledger_growth.RepeatedGuardsDoNotGrowTheLedger."
                      "test_TEETH_a_subagent_demand_does_not_block_the_main_thread",
                      "which only the subagent `sub-7` owes")


class CompactionAsksTheSameQuestionScopeAsks(unittest.TestCase):
    """C-CAR-038/039: `compact` kept its OWN copy of the set difference `scope` takes, folding a
    session's rows by session alone while `scope` keys on (session, agent). Two copies of one
    expression is the hazard ledger.py:113-116 states about the chain rule, and here it had teeth:
    a discharge written under a DIFFERENT agent cancelled a demand it never paid, so compaction
    read the session as owing nothing and dropped rows `scope` still reports as open -- a live
    obligation retired by a bookkeeping pass. Both readers now eat `Ledger._books`.
    """

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.ledger = Ledger(root=pathlib.Path(self._temp.name))

    def test_TEETH_a_cross_agent_discharge_does_not_let_compaction_drop_an_open_demand(self) -> None:
        self.ledger.demand(Demand("s-owing", "", "A01", "subj", "r"))
        # The same id, discharged by a DIFFERENT agent: not a payment of the demand above.
        # `scope("s-owing", "")` must still call it open, and compaction must not disagree.
        self.ledger.discharge("s-owing", "other", derive_id("s-owing", "", "A01", "subj"), "guard")
        self.ledger.demand(Demand("s-other", "", "A01", "filler", "r"))
        self.ledger.discharge("s-other", "", derive_id("s-other", "", "A01", "filler"), "guard")

        still_open = self.ledger.scope("s-owing", "")[0]
        self.assertTrue(still_open, "scope stopped calling the unpaid demand open")

        with unittest.mock.patch.object(Ledger, "COMPACT_AT", 0):
            self.ledger.compact("s-keep")

        self.assertTrue(self.ledger.scope("s-owing", "")[0],
                        "compaction dropped a demand scope still counts as open")
        self.assertIsNone(self.ledger.verify_chain(), "the rewrite left an unsound chain")


class TheChainDetectsWhatItClaims(unittest.TestCase):
    """What `verify_chain` reports when it is CALLED -- which, in a session, is never.

    The chain's stated reach is altered rows, truncated writes, bit-rot; never deliberate
    forgery, and never the deletion of a valid tail. Until this class nothing had ever observed
    `verify_chain` report any of it. A checker never seen failing is the exact shape clause
    C08-check-can-fail refuses to trust, and a TRACE pass over this tree found the method on no
    input-to-output chain at all: an advertised property whose checker was dead code. Both
    directions live here as residents: a sound ledger reads clean, and each planted corruption
    is named -- with nobody remembering to plant anything.

    THE LIMIT OF WHAT THIS CLASS PROVES, stated because the class name overstates it: these
    tests build a ledger, corrupt it, and call the checker directly. THIS FILE IS THE ONLY
    CALLER `verify_chain` HAS -- `grep -rn verify_chain plugin/` hits ledger.py and nothing
    else. So what is witnessed here is that the checker works, not that a session detects
    anything: a real session whose ledger is corrupted mid-run reads the altered row back as a
    live demand and allows and denies exactly as if it were sound. README's "Honest limitations"
    says so. Giving the chain a production caller is a change to the dispatcher, not to this
    file, and until it lands nothing here may be cited as a property of a session.
    """

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.ledger = Ledger(root=pathlib.Path(self._temp.name))
        for n in range(3):
            self.ledger.demand(Demand("s", "", "A01", f"s{n}", "r"))
        self.ledger.discharge("s", "", derive_id("s", "", "A01", "s1"), "guard observed")

    def test_a_sound_chain_reads_clean(self) -> None:
        self.assertIsNone(self.ledger.verify_chain())

    def test_an_altered_row_is_named(self) -> None:
        lines = self.ledger.path.read_text(encoding="utf-8").splitlines()
        # Alter row content without recomputing its hash -- the accidental-corruption shape.
        # `_canon` writes compact separators, and a replace that misses writes nothing: require
        # the mutation to have landed before trusting what the checker says about it.
        mutated = lines[1].replace('"clause_id":"A01"', '"clause_id":"A99"')
        self.assertNotEqual(mutated, lines[1], "the plant never reached the row")
        lines[1] = mutated
        self.ledger.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        divergent = self.ledger.verify_chain()
        self.assertIsNotNone(divergent, "an altered row read back as a sound chain")
        self.assertIn(divergent, lines[1], "the reported hash is not the altered row's")

    def test_a_missing_hash_is_named(self) -> None:
        import json as _json
        lines = self.ledger.path.read_text(encoding="utf-8").splitlines()
        row = _json.loads(lines[2])
        del row["hash"]
        lines[2] = _json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.ledger.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.assertEqual(self.ledger.verify_chain(), "<missing>")

    def test_TEETH_the_page_says_who_calls_this_and_that_is_who_calls_it(self) -> None:
        """The README's claim about the chain is a claim about its CALLERS. Held here.

        SUPERSEDES the version that asserted `callers == []`, and the succession is worth stating
        rather than editing the expectation quietly. That version was written when the page said
        "no shipped path reads it", and its own docstring named this exact future: "wiring it into
        the dispatcher is a fine thing to do -- it is the fix the carriage audit recommends -- and
        the moment somebody does, this goes red and the page gets rewritten in the same commit."
        Somebody did (the SessionStart carriage fix), this went red on the very run that first
        composed the two changes, and this is that rewrite. The law was not loosened to admit the
        new call; it was re-aimed at the new truth.

        The page's claim is now about WHERE and WHEN, so the check is too: exactly one shipped
        caller, and it is the dispatcher's. Teeth in both directions -- delete the call and "read
        once per session" is false; add a second and "once, at SessionStart" is. Found by parsing
        rather than grepping: a comment naming the method is not a caller.
        """
        import ast

        callers = []
        for source in sorted((PLUGIN / "keel").rglob("*.py")):
            tree = ast.parse(source.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "verify_chain"):
                    callers.append(f"{source.relative_to(PLUGIN)}:{node.lineno}")
        self.assertEqual(
            ["keel/dispatch.py"], sorted({c.rsplit(":", 1)[0] for c in callers}),
            f"the shipped callers of `verify_chain` are {callers}, but README.md says the chain is "
            "read once per session, by the dispatcher, at SessionStart. An empty census makes "
            "'read once per session' false; a caller outside the dispatcher makes 'at "
            "SessionStart' false. Move the page and the code together.")
        self.assertEqual(
            1, len(callers),
            f"README.md says the chain is read ONCE per session; found {len(callers)} shipped call "
            f"sites ({callers}).")
        here = pathlib.Path(__file__).read_text(encoding="utf-8")
        self.assertIn(
            ".verify_chain()", here,
            "this module is the suite's own caller and it has stopped calling it, so the method "
            "is graded by nothing here")

    def test_the_caller_census_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red
        """Remove `verify_chain`'s one shipped caller, and the census above must go red.

        The plant inverted along with the law. It used to ADD a call to a package that had none;
        it now REMOVES the one the dispatcher makes, because that is the direction in which the
        page's claim becomes false.
        """
        smoke_replace(
            self, PLUGIN / "keel" / "dispatch.py",
            b"            divergent = ledger.verify_chain()",
            b"            divergent = None",
            "tests.test_ledger_growth.TheChainDetectsWhatItClaims."
            "test_TEETH_the_page_says_who_calls_this_and_that_is_who_calls_it",
            "read once per session",
        )


if __name__ == "__main__":
    unittest.main()
