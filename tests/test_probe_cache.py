"""One probe result per event, not one per segment per direction.

A clause is scanned segment by segment, and each scan runs twice -- once locating the act, once
locating the guard. With a probe on both predicates an 8-segment command asked the SAME question
16 times: measured 2N exactly. At the 5000 ms per-probe cap that is 80 seconds against a 20 second
hook timeout, so the hook is CANCELED, renders no decision, and the deny row fails OPEN through
the hang. The cost is not the subprocesses; it is that enough of them invert the fail direction.

The cache is module-level rather than a threaded parameter because its lifetime is already correct
by construction: the dispatcher is a fresh process per event, so the module dies with the event
and nothing has to decide when to invalidate. Tests share one process, so they reset explicitly.
"""

from __future__ import annotations

import unittest
from tests.plant_support import PLUGIN, smoke_replace

from keel import clauses as C

PROBE = {"cmd": ["git", "status", "--porcelain"], "timeout_ms": 5000, "expect": "empty"}


def clause_with_probes() -> C.Clause:
    predicate = {"kind": "regex", "on": "tool_input.command", "pattern": "deploy", "probe": PROBE}
    return C.Clause(
        id="P99", event="PreToolUse", tools=["Bash"], occasion="x", costly="x", guard="x",
        subject="tool_input.command", fingerprint=dict(predicate),
        discharged_by=dict(predicate), window="session", deny_reason="x",
        fixtures_pos=["deploy"], fixtures_neg=["x"])


class ProbeRunsOncePerEvent(unittest.TestCase):
    def setUp(self) -> None:
        C.reset_probe_cache()
        self._real = C._measure_probe
        self.calls = 0

        def counting(spec):
            self.calls += 1
            return False   # never satisfied, so the segment scan keeps going -- the worst case

        C._measure_probe = counting
        self.addCleanup(lambda: setattr(C, "_measure_probe", self._real))
        self.addCleanup(C.reset_probe_cache)

    def _scan(self) -> int:
        clause = clause_with_probes()
        command = " && ".join(f"deploy {i}" for i in range(8))
        event = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                 "tool_input": {"command": command}, "session_id": "p"}
        self.calls = 0
        C.match(clause, event)
        C.discharges(clause, event)
        return self.calls

    def test_TEETH_eight_segments_two_directions_measure_once(self) -> None:
        self.assertEqual(1, self._scan(), "the same probe was measured more than once per event")

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red; a checker that cannot follow an imported helper reads this body as empty
        path = PLUGIN / "keel" / "clauses.py"
        smoke_replace(self, path, b"    key = json.dumps(spec, sort_keys=True, separators=(\",\", \":\"))\n",
                      b"    return _measure_probe(spec)\n", "tests.test_probe_cache."
                      "ProbeRunsOncePerEvent.test_TEETH_eight_segments_two_directions_measure_once", "same probe was measured more than once per event")

    def test_TEETH_reset_restores_per_event_scope(self) -> None:
        self._scan()
        C.reset_probe_cache()
        self.assertEqual(1, self._scan(), "a new event must measure again, not inherit")


if __name__ == "__main__":
    unittest.main()
