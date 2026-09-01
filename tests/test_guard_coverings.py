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

THE FIX WAS TO STOP DISCARDING INFORMATION, not to add a mechanism. `segments()` identified which
operator split each segment and then dropped it one line later, returning `list[str]`. A `|`
means the next command EATS this one's output; a `;` means only that it runs after, and C09's
whole subject is that difference. With the operator gone, no predicate could see it -- which is
exactly what C09's `why_no_program` reported ("argv on `ps` fires on every process listing
whether or not it is piped into a matcher"). It was true, and true because the pipe fact had
already been deleted before any predicate ran. `_scan` now keeps the operator, `kind: pipeline`
reads the edge between two segments, and that exemption is SUPERSEDED rather than merely
tolerated -- both of C09's sides are structural now, so the field is gone.

The mention hole closes as a CONSEQUENCE, not as a special case: a quoted `echo '...'` is ONE
segment with no following operator, so there is no edge to match.
"""

from __future__ import annotations

import unittest

from tests.plant_support import PLUGIN, smoke_replace

from keel import clauses as C

CLAUSES = PLUGIN / "keel" / "clauses.json"




def _event(predicate: dict, command: str) -> dict:
    return {"hook_event_name": "PreToolUse", "tool_name": "Bash",
            "tool_input": {"command": command}}


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
        for command in ("echo 'ps aux | grep -v $$'",
                        "grep -rn 'ps | grep -v $$' notes.md"):
            with self.subTest(command=command):
                self.assertFalse(C._predicate(guard, _event(guard, command)),
                                 f"C09 discharged on a MENTION: {command!r}")

    def test_NON_VACUITY_the_real_pipeline_still_discharges(self) -> None:
        """Refusing everything would satisfy the cell above and destroy the clause."""
        guard = {c.id: c for c in C.load_default()}["C09-checker-excludes-self"].discharged_by
        for command in ("ps aux | grep -v $$",
                        "ps aux | grep node | grep -v $$",
                        "ps -eo pid,comm | awk -v self_pid=$$ '$1 != self_pid'"):
            with self.subTest(command=command):
                self.assertTrue(C._predicate(guard, _event(guard, command)),
                                f"C09 no longer discharges on a real guard: {command!r}")

    def test_the_operator_is_the_point_not_merely_adjacency(self) -> None:
        """`;` and `||` are not pipes, and reading them as one would license the guard.

        `a || b` runs b when a FAILS -- the opposite of feeding it -- so an exclusion filter
        joined that way may never have run against the listing at all.
        """
        guard = {c.id: c for c in C.load_default()}["C09-checker-excludes-self"].discharged_by
        for command in ("ps aux ; grep -v $$", "ps aux || grep -v $$"):
            with self.subTest(command=command):
                self.assertFalse(C._predicate(guard, _event(guard, command)),
                                 f"a non-pipe operator discharged C09: {command!r}")

    def test_the_splitter_keeps_the_operator_and_segments_is_unchanged(self) -> None:
        """One scanner, two readings -- not two spellings that can drift apart."""
        self.assertEqual(C.segment_pipeline("ps aux | grep -v $$"),
                         [("ps aux", "|"), ("grep -v $$", "")])
        self.assertEqual(C.segment_pipeline("ps aux || grep -v $$"),
                         [("ps aux", "||"), ("grep -v $$", "")])
        # A mention is ONE segment: this is why the hole closes without a special case.
        self.assertEqual(C.segment_pipeline("echo 'ps aux | grep -v $$'"),
                         [("echo 'ps aux | grep -v $$'", "")])
        # The public shape every other caller reads is untouched.
        self.assertEqual(C.segments("ps aux | grep -v $$"), ["ps aux", "grep -v $$"])
        self.assertEqual(C.segments("make 2>&1 | tee log"), ["make 2>&1", "tee log"])

    def test_the_check_can_fail(self) -> None:
        # The fault is a DATA edit to the mechanism this law is about -- the operator C09's guard
        # keys on -- not a special case wired to this test's own input. With the edge declared as
        # `;`, the clause's own positive fixture `ps aux | grep -v $$` no longer discharges, and
        # the loader must refuse the table rather than ship a guard nothing witnesses.
        smoke_replace(
            self, CLAUSES,
            b'"operator": "|",\n      "downstream_matches": "(?:^(?:grep|rg)',
            b'"operator": ";",\n      "downstream_matches": "(?:^(?:grep|rg)',
            "tests.test_guard_coverings.EveryGuardIsWitnessedInBothDirections."
            "test_the_loader_enforces_it_rather_than_this_test",
            "CLAUSE-GUARD-FIXTURE-MISS")


if __name__ == "__main__":
    unittest.main()
