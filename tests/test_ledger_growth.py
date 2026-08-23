"""A licence is a state transition, not an event log.

Re-observing the same guard in the same scope changes no ledger state, so retaining every
observation only makes every later read scan duplicate history. Measured through the dispatcher
before the fix: 40 identical `git status --porcelain` calls wrote 120 rows -- three per call,
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
        # `load_default()`, NOT `load_dir(default_dir())`, and a floor under the table -- because
        # an upper bound alone is satisfied perfectly by a table that loaded NOTHING. This ran in
        # a layout with no loose clause directory, took an empty table, wrote zero rows, and
        # passed its `<= 10` assertion having exercised no deduplication at all; it went on
        # passing with the dedup guard deleted. An assertion that only bounds from above cannot
        # tell "correctly deduplicated" from "never ran", which is this project's own
        # absence-must-never-read-as-green law turned on one of its own tests. `load_default()` is
        # also what production loads, so the test now exercises the table users actually get.
        table = C.load_default()
        self.assertTrue(table, "an empty clause table makes the bound below vacuous")
        event = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                 "tool_input": {"command": "git status --porcelain"},
                 "session_id": "s", "agent_id": "a"}
        for _ in range(40):
            dispatch.pre_tool_use(table, Ledger(), event)
        written = rows_written(self.state)
        self.assertGreater(written, 0, "40 guards wrote nothing: the ledger never ran")
        self.assertLessEqual(written, 10,
                             f"{written} rows for 40 identical guards; the ledger is an "
                             "obligation register, not an observation log")

    def test_TEETH_a_repeat_discharge_is_a_no_op(self) -> None:
        ledger = Ledger()
        demand_id = derive_id("s", "a", "T01", "x")
        ledger.demand(Demand(demand_id, "s", "a", "T01", "x", "guard first"))
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
                      b"    return load_bundle(bundle) if bundle.is_file() else load_dir(default_dir())",
                      b"    return []", "tests.test_ledger_growth."
                      "RepeatedGuardsDoNotGrowTheLedger."
                      "test_TEETH_forty_identical_guards_write_one_row_per_clause", "an empty clause table makes the bound below vacuous")


if __name__ == "__main__":
    unittest.main()
