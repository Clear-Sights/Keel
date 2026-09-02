"""The GUARD side of every clause is witnessed in both directions, or the table does not load.

WHY THIS LAW EXISTS -- the gap it was written against, measured on this table before the fix:

    clauses declaring a discharge fixture: 0 of 24

Every clause shipped `fixtures_pos`/`fixtures_neg`, and the loader validated them. But those
discriminate the OCCASION. Nothing declared what DISCHARGES a clause, so the guard half of all
24 points was un-witnessed BY CONSTRUCTION: there was no population to check, and a guard that a
document could spend loaded perfectly clean.

That is the asymmetric direction. A false discharge REMOVES the guard while the costly act goes
ahead; a false activation only interrupts. So the un-witnessed half was the expensive one.

The gap hid a live defect, which these fixtures found on their first run. C09's guard was a regex
over the raw command, and:

    ps aux | grep -v $$                  DISCHARGES   <- correct
    echo 'ps aux | grep -v $$'           DISCHARGES   <- a MENTION spent the guard
    grep -rn 'ps | grep -v $$' notes.md  DISCHARGES   <- so did a search for the phrase

An agent that never listed a process could claim it had. C09 was alone -- U24 and U25, the other
two `why_no_program` clauses, both correctly refused the mention -- so the exemption class was
not leaking; one clause was.

THE FIX, TWICE. First the splitter stopped discarding the pipe operator and C09 read the edge
between `ps` and its matcher. That still named `ps`. Now both of C09's sides are EFFECTS read
off the listing itself: the occasion is `report_self` (the act's output contains a segment of
its own command -- the checker appeared in its own result), the guard is `report_listing` (the
output holds live pids and none of the act's own command text). A mention prints its own text,
never a listing, so it cannot spend the guard; and no program is named on either side.
"""

from __future__ import annotations

import unittest

from tests.plant_support import PLUGIN, smoke_replace

from keel import clauses as C
from keel import effects

CLAUSES = PLUGIN / "keel" / "clauses.json"




def _record(command: str, stdout: str, alive=(41, 42)) -> dict:
    """What the observer records for a listing act, computed by the observer's own readers."""
    record = effects.report_effects(stdout, command)
    record.update(effects.trace_effects(stdout, {"alive": list(alive), "command": command},
                                        None, quiet=True))
    return {"hook_event_name": "PostToolUse", "tool_name": "Bash",
            "tool_input": {"command": command}, "keel_effect": record}


class EveryGuardIsWitnessedInBothDirections(unittest.TestCase):
    def test_the_loader_enforces_it_rather_than_this_test(self) -> None:
        """A bar living only in a test is a property of the table, not of the plugin.

        `load_default()` runs on every hook invocation, so a clause CANNOT ship with an
        un-witnessed guard. This cell asserts the enforcement is reachable from the product.
        """
        clauses = C.load_default()
        self.assertEqual(len(clauses), 24)
        self.assertTrue(all(c.fixtures_discharge and c.fixtures_no_discharge for c in clauses))

    def test_TEETH_a_mention_never_discharges_C09(self) -> None:
        """The defect these fixtures found, driven through the production predicate."""
        guard = {c.id: c for c in C.load_default()}["C09-checker-excludes-self"].discharged_by
        for command, stdout in (("echo 'ps aux | grep -v $$'", "ps aux | grep -v $$\n"),
                                ("grep -rn 'ps | grep -v $$' notes.md", "notes.md:3: ps | grep -v $$\n")):
            with self.subTest(command=command):
                self.assertFalse(C._predicate(guard, _record(command, stdout)),
                                 f"C09 discharged on a MENTION: {command!r}")

    def test_NON_VACUITY_the_real_listing_still_discharges(self) -> None:
        """Refusing everything would satisfy the cell above and destroy the clause."""
        guard = {c.id: c for c in C.load_default()}["C09-checker-excludes-self"].discharged_by
        for command, stdout in (("pgrep -af worker", "41 worker --queue\n42 worker --queue\n"),
                                ("ps -eo pid,comm | awk -v self_pid=$$ '$1 != self_pid'",
                                 "41 worker\n42 worker\n")):
            with self.subTest(command=command):
                self.assertTrue(C._predicate(guard, _record(command, stdout)),
                                f"C09 no longer discharges on a real listing: {command!r}")

    def test_a_listing_that_lists_itself_is_the_occasion_not_the_guard(self) -> None:
        """`ps aux | grep worker` prints its own `grep worker` line: the checker counted itself."""
        clause = {c.id: c for c in C.load_default()}["C09-checker-excludes-self"]
        event = _record("ps aux | grep worker", "root 41 worker\nroot 42 grep worker\n")
        self.assertTrue(C._predicate(clause.fingerprint, event))
        self.assertFalse(C._predicate(clause.discharged_by, event))

    def test_the_check_can_fail(self) -> None:
        # The fault is a DATA edit to the guard: discharge on the listing that listed ITSELF.
        # C09's own positive discharge fixture then no longer discharges, and the loader must
        # refuse the table rather than ship a guard nothing witnesses.
        smoke_replace(
            self, CLAUSES,
            b'"effect": "report_listing"', b'"effect": "report_self"',
            "tests.test_guard_coverings.EveryGuardIsWitnessedInBothDirections."
            "test_the_loader_enforces_it_rather_than_this_test",
            "CLAUSE-GUARD-FIXTURE-MISS")


if __name__ == "__main__":
    unittest.main()
