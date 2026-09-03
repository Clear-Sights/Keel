"""M-COV-043 / `out_of_order_is_rejected` (Coverings.v:316-317): `[L; X]` -- the guard arriving
AFTER the act it would license -- must be rejected. `pre_tool_use` checks `C.discharges(cl, event)`
before it checks `_applies(cl, event)`/`C.match(cl, event)` for the same clause on the same event
(dispatch.py, in the per-clause loop): when the discharge check is true the clause is paid and
`continue`d, so the occasion check never runs for that event. If a single PreToolUse event could
satisfy BOTH a clause's `discharged_by` and its own occasion, that one event would license itself
-- the guard and the act it guards would be the same call.

THE QUESTION THIS FILE ANSWERS, over the WHOLE SHIPPED TABLE: is there a clause, and an event, for
which this is possible? Not by inspection of one clause but by driving the predicates directly, per
clause, on the occasion event `C.match` says fires it -- the actual test the code path applies, not
a hand-argued case.
"""
from __future__ import annotations

import unittest

from tests.plant_support import PLUGIN  # noqa: F401 -- puts `keel` on sys.path

from keel import clauses as C


def _events(cl):
    """Every minimal PreToolUse event this clause's occasion could fire on: ONE PER TOOL in its
    enum, not just the first.

    Probing `tools[0]` alone is not this test. The shipped table is exactly where that shortcut
    breaks: D01 and P01 name `Read`, `Glob` and `Grep` in BOTH their occasion tool list and their
    `discharged_by` regex, so the only thing standing between them and a self-licence is the
    fingerprint refusing those tools -- and `tools[0]` for both is `Agent`/`ExitPlanMode`, which
    is not the tool the discharge reads. A per-clause probe that never sends `Read` would report
    the whole table clean while the one dangerous event went untried.
    """
    if cl.event != "PreToolUse":
        return
    for tool in (cl.tools or ["Bash"]):
        if tool == "*":
            tool = "Bash"
        yield tool, {"hook_event_name": "PreToolUse", "tool_name": tool,
                     "session_id": "s-selflicence",
                     "tool_input": {"command": "true"} if tool == "Bash" else {}}


class NoShippedClauseCanSelfLicense(unittest.TestCase):
    """For every PreToolUse clause, the event that fires its own occasion must NOT also
    satisfy its `discharged_by` -- or `pre_tool_use` would pay the clause with the very call
    that was supposed to raise its demand."""

    def test_no_clauses_occasion_event_also_discharges_it(self) -> None:
        table = C.load_default()
        offenders = []
        probed = 0
        for cl in table:
            for tool, event in _events(cl):
                probed += 1
                if C.match(cl, event) and C.discharges(cl, event):
                    offenders.append(f"{cl.id} on {tool}")
        # A floor, so an enumeration that silently probes nothing cannot read as a clean table:
        # the emptiness of `offenders` means nothing unless events were actually driven.
        self.assertGreaterEqual(probed, 12,
                                f"only {probed} events driven -- the enumeration went vacuous")
        self.assertEqual(offenders, [],
                         f"clause(s) {offenders} self-license: their own occasion event also "
                         f"satisfies their discharged_by, in one PreToolUse")


if __name__ == "__main__":
    unittest.main()
