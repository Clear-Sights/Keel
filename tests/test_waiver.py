"""A waiver parks one clause; the WAIVER is what dies by default, never the clause.

C08 forced this. Its guard asks to observe a nonzero PostToolUse result, and this host sends no
exit status in any form -- measured over 71 recorded Bash PostToolUse payloads, whose
tool_response is a dict keyed (stdout, stderr, interrupted, isImage, noOutputExpected). So the
clause could be demanded and never discharged: 114 demand rows in one session, 0 discharges ever,
every Stop blocked. The end state of that is the whole gate being switched off, which costs all
24 clauses at once -- strictly worse than parking one.

The danger in any waiver is that it becomes a silent, permanent hole. Three properties stop that,
and each has a test below:

  * it LAPSES BY ITSELF. `until` is a plain date; the day after, the clause enforces again with
    no edit and no renewal. Doing nothing restores the check rather than retiring it.
  * an UNREADABLE waiver is already dead. Missing, non-string or unparseable `until` reads as
    expired, so a typo cannot buy silence.
  * it is NEVER SILENT. Stop announces a parked clause every ending, and announces an expired one
    loudly as it starts enforcing again.

The clause itself stays in the table -- loaded, admitted, fixture-checked -- so a waiver hides no
drift in the row it parks.
"""

from __future__ import annotations

import contextlib
import dataclasses
import io
import tempfile
import unittest
from datetime import date

from keel import clauses as C, dispatch
from keel.ledger import Ledger

PRE = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "session_id": "w", "agent_id": "",
       "tool_input": {"command": "python3 -m pytest -q tests/"}}
STOP = {"hook_event_name": "Stop", "session_id": "w", "agent_id": ""}


def waived_clause() -> C.Clause:
    for clause in C.load_default():
        if clause.id.startswith("C08"):
            return clause
    raise AssertionError("C08 is not in the shipped clause table")


def drive(clause: C.Clause):
    """One PreToolUse then one Stop. Returns (decision, open row count, stderr)."""
    with tempfile.TemporaryDirectory() as state:
        ledger = Ledger(state)
        dispatch.pre_tool_use([clause], ledger, PRE)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            out = dispatch.reconcile([clause], ledger, STOP)
        return out.get("decision"), len(list(ledger.open_demands("w", ""))), err.getvalue()


class WaiverIsDefaultDead(unittest.TestCase):
    def test_TEETH_a_live_waiver_parks_the_clause(self) -> None:
        decision, rows, err = drive(waived_clause())
        self.assertIsNone(decision, "a parked clause must not block the ending")
        self.assertEqual(0, rows, "a parked clause must accrue no rows nothing can discharge")
        self.assertIn("PARKED", err, "a parked clause the operator cannot see is a silent hole")

    def test_TEETH_an_expired_waiver_enforces_again_by_itself(self) -> None:
        """The whole point: no edit, no renewal, and the check comes back."""
        stale = dataclasses.replace(waived_clause(),
                                    waiver={"until": "2020-01-01", "because": "long gone"})
        decision, rows, err = drive(stale)
        self.assertEqual("block", decision, "an expired waiver must not keep parking the clause")
        self.assertEqual(1, rows)
        self.assertIn("EXPIRED", err, "an expired waiver must never lapse quietly")

    def test_TEETH_an_unreadable_waiver_is_already_dead(self) -> None:
        for spelling in ({}, {"until": "soon"}, {"until": 20261120}, {"until": None}):
            with self.subTest(waiver=spelling):
                clause = dataclasses.replace(waived_clause(), waiver=spelling)
                self.assertEqual("expired", C.waiver_status(clause),
                                 "a waiver nobody can read must not buy silence")

    def test_TEETH_the_boundary_day_is_still_live(self) -> None:
        clause = waived_clause()
        until = date.fromisoformat(clause.waiver["until"])
        self.assertEqual("live", C.waiver_status(clause, until), "the last day is still covered")
        self.assertEqual("expired", C.waiver_status(clause, until.replace(day=until.day + 1)))

    def test_TEETH_the_parked_clause_is_still_in_the_table(self) -> None:
        """Parking enforcement is not deleting the row: it stays loaded and admitted."""
        table = C.load_default()
        self.assertEqual(24, len(table))
        self.assertIn("C08-check-can-fail", [c.id for c in table])

    def test_TEETH_a_clause_without_a_waiver_is_untouched(self) -> None:
        for clause in C.load_default():
            if not clause.id.startswith("C08"):
                with self.subTest(clause=clause.id):
                    self.assertEqual("none", C.waiver_status(clause))

    def test_the_check_can_fail(self) -> None:
        """Both directions come from the SAME driver, so neither assertion can be vacuous.

        If `waiver_status` were stubbed to one answer, or if dispatch ignored it, one of these two
        would go red -- they demand opposite outcomes from identical input.
        """
        live = drive(waived_clause())
        stale = drive(dataclasses.replace(waived_clause(),
                                          waiver={"until": "2020-01-01", "because": "x"}))
        self.assertNotEqual(live[0], stale[0], "the waiver date changed nothing about the verdict")
        self.assertNotEqual(live[1], stale[1], "the waiver date changed nothing about the ledger")


if __name__ == "__main__":
    unittest.main()
