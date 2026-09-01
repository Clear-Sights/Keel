"""One obligation, two surfaces: the SAME act performed through a different host surface must
discharge the same obligation.

THE DEFECT THIS CLOSES, measured on the shipped table before the change:

    U12 guard {"names": ["rg", "grep"]}      Grep TOOL -> does NOT discharge
    U19 guard {"names": [... "rg","grep"]}   Grep TOOL -> does NOT discharge

Searching is `grep` typed into a Bash command AND it is the host's own `Grep` tool. One
obligation, two surfaces. The guard could name only one of them, because `any_of` existed only
INSIDE `kind == "program"` -- it composed two readings of `tool_input.command` and could not
reach `tool_name` at all. So an agent that searched the ordinary way was told it had not.

WHICH DIRECTION THIS IS, stated rather than assumed. By Theorem 5 a missing name on a GUARD is
the interrupting direction, not the silent one: the work was done and the obligation stays open.
That is still the failure mode C08's own comment records as the expensive one -- recurring noise
gets the gate switched off, and switching it off removes all of its coverage at once.

THE FIX IS A COMPOSITION PRIMITIVE, not a wider name list. Adding "Grep" to a `names` list would
have been the vocabulary move Theorem 5 says can only ever manage the problem. `tool_name` is a
CLOSED host enum, so composing over it retires the vocabulary for this act instead of widening it.
"""

from __future__ import annotations

import unittest

from tests.plant_support import PLUGIN, smoke_replace
from keel import clauses as C


def _guard(cid: str):
    return {c.id: c for c in C.load_default()}[cid].discharged_by


def _ev(**kw):
    e = {"hook_event_name": "PreToolUse"}
    e.update(kw)
    return e


BASH_SEARCHES = ("rg pattern src/", "grep -rn pattern src/")
# A mention is not an act, and a lookalike token is not the program -- both must stay refused, or
# the composition bought reach at the cost of the property Theorem 2 provides.
# `grep -rn 'x; rg pattern' notes.md` is deliberately ABSENT. It was in this list on the first
# draft and the cell failed -- correctly. The leading program there IS `grep`, so it is a real
# search invocation, and searching a notes file is still searching. The mention shape that must
# refuse is `echo '...'`, where the program is `echo` and the search words are cargo. Keeping the
# grep case would have asserted that the guard must refuse an act that genuinely performs it.
BASH_REFUSED = ("echo 'rg pattern src/'", "echo 'grep -rn pattern src/'", "rgb")


class OneObligationTwoSurfaces(unittest.TestCase):
    def test_the_host_search_tool_discharges_the_search_obligation(self) -> None:
        for cid in ("U12", "U19"):
            with self.subTest(clause=cid):
                self.assertTrue(
                    C._predicate(_guard(cid), _ev(tool_name="Grep",
                                                  tool_input={"pattern": "x", "path": "."})),
                    f"{cid}: the host's own Grep tool did not discharge a search obligation")

    def test_NON_VACUITY_the_shell_form_still_discharges(self) -> None:
        """Refusing nothing would satisfy the cell above and destroy the clause."""
        for cid in ("U12", "U19"):
            for command in BASH_SEARCHES:
                with self.subTest(clause=cid, command=command):
                    self.assertTrue(
                        C._predicate(_guard(cid),
                                     _ev(tool_name="Bash", tool_input={"command": command})),
                        f"{cid}: composition lost the shell form it already had")

    def test_TEETH_a_mention_and_a_lookalike_still_refuse(self) -> None:
        for cid in ("U12", "U19"):
            for command in BASH_REFUSED:
                with self.subTest(clause=cid, command=command):
                    self.assertFalse(
                        C._predicate(_guard(cid),
                                     _ev(tool_name="Bash", tool_input={"command": command})),
                        f"{cid}: composition widened the guard into accepting {command!r}")

    def test_an_unrelated_tool_does_not_discharge(self) -> None:
        for cid in ("U12", "U19"):
            with self.subTest(clause=cid):
                self.assertFalse(
                    C._predicate(_guard(cid),
                                 _ev(tool_name="Write", tool_input={"file_path": "/x"})),
                    f"{cid}: any tool_name at all discharged it -- the enum is not being read")

    def test_composition_does_not_disturb_kind_bearing_any_of(self) -> None:
        """U20 and U24 declare a `kind`, so the new branch must not reach them."""
        self.assertTrue(C._predicate(_guard("U24"),
                                     _ev(tool_name="Bash",
                                         tool_input={"command": "PYTHONWARNINGS=error pytest"})))
        self.assertFalse(C._predicate(_guard("U24"),
                                      _ev(tool_name="Bash",
                                          tool_input={"command": "pytest -q"})))

    def test_the_check_can_fail(self) -> None:
        """Disarm the composition primitive itself -- the one line that provides the property."""
        smoke_replace(
            self, PLUGIN / "keel" / "clauses.py",
            b'    if predicate.get("kind") is None:\n'
            b'        if predicate.get("any_of"):',
            b'    if predicate.get("kind") is None:\n'
            b'        if False and predicate.get("any_of"):',
            "tests.test_surface_composition.OneObligationTwoSurfaces."
            "test_the_host_search_tool_discharges_the_search_obligation",
            # The plant produces a STRONGER outcome than this cell going red on its own:
            # every clause with a composed guard declares tool-event fixtures, those are
            # loader-checked, so with the primitive disarmed NO clause ships at all rather
            # than one misbehaving.
            #
            # The expectation names the ERROR CLASS and not a clause id, and the reason is a
            # false red this cell already produced: it read `CLAUSE-GUARD-FIXTURE-MISS: U12`,
            # and when U10 composed its guard over the host `Read`, U10 became the first row
            # the loader refuses -- so the plant reported failure while the property it tests
            # held perfectly. An assertion pinned to whichever clause sorts first is a
            # denominator of one masquerading as the property, and it goes red on every future
            # composition. What is being tested is that the table does not ship.
            "CLAUSE-GUARD-FIXTURE-MISS",
        )


if __name__ == "__main__":
    unittest.main()
