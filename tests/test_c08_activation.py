"""C08's occasion is a PASS the act PRINTED, keyed on the checker that printed it.

The occasion used to be a checker INVOCATION matched by name (`pytest`, `unittest`, `*check*.py`),
and a shell variable assignment satisfied it: `F=plugin/makoto/checks/writeThrashRevert.py`
contains "check" and ends `.py`, so it both activated the clause AND became the obligation's
key. Nothing can ever discharge such a row, because it names no checker that can be run.
Measured in one live session before the fix: 114 C08 demand rows, of which 19 were keyed on a
token containing `=`, spread over 18 distinct never-dischargeable subjects.

The occasion is now name-agnostic: a `report_pass` datum in the call's output (Theorem 8), so a
checker under any name activates it and an assignment that prints nothing cannot. The KEY is
still read from the command, because a PASS and the failing run that pays for it must pair on
the checker's identity; it is read from the LAST segment, past any `VAR=value` prefix, and a
command that is only an assignment yields no key at all -- and a keyed activation with no key
is skipped by the dispatcher rather than recorded under an empty subject.
"""
from __future__ import annotations

import re
import unittest

from tests.plant_support import PLUGIN, record, smoke_replace
from keel import clauses as C

INVOCATIONS = [
    "python3 -m pytest -q tests/",
    "pytest -q",
    "python3 -m unittest tests.test_engine",
    "python3 tools/check_schema.py",
    "./verify.sh",
    "python3 $SP/check_equiv.py",
    "export PYTHONPATH=/x; python3 -m pytest tests/",
    "PYTHONWARNINGS=error pytest -q",
]
LOOKALIKES = [
    "F=plugin/makoto/checks/writeThrashRevert.py",
    "M=$SP/plugin_mut/makoto/checks/verifierExitMasking.py",
    "T=plugin/makoto/checks/canonFingerprints.py",
    "F=tools/check_schema.py",
]


def c08() -> C.Clause:
    for clause in C.load_default():
        if clause.id.startswith("C08"):
            return clause
    raise AssertionError("C08 is not in the shipped clause table")


def passed(command: str) -> dict:
    """A PostToolUse event whose act printed a passing report, as the observer records it."""
    return {"hook_event_name": "PostToolUse", "tool_name": "Bash",
            "tool_input": {"command": command}, "keel_effect": record(report_pass=True)}


class OccasionIsAPrintedPass(unittest.TestCase):
    def _activates(self, command: str) -> bool:
        return C._base_predicate(c08().activated_by, passed(command)) is True

    def test_TEETH_a_printed_pass_activates_under_any_name(self) -> None:
        for command in INVOCATIONS:
            with self.subTest(command=command):
                self.assertTrue(self._activates(command))
                self.assertTrue(C.event_key(c08().activated_by, passed(command)),
                                "a real checker run must yield a key to pair its failing run on")

    def test_NON_VACUITY_a_run_that_printed_no_pass_does_not_activate(self) -> None:
        event = passed("pytest -q")
        event["keel_effect"]["report_pass"] = False
        self.assertFalse(C._base_predicate(c08().activated_by, event))

    def test_TEETH_the_key_never_captures_an_assignment(self) -> None:
        """Activation and keying are separate; the key is what an assignment used to poison."""
        for spec in (c08().activated_by["key_from"], c08().discharged_by["key_from"]):
            for command in LOOKALIKES:
                with self.subTest(command=command, on=spec["on"]):
                    self.assertEqual("", C.event_key({"key_from": spec},
                                                     {"tool_input": {"command": command}}))
                    self.assertNotIn("=", re.search(spec["pattern"], "X=1 pytest -q").group(1))

    def test_the_key_is_the_checker_past_its_environment(self) -> None:
        spec = {"key_from": c08().activated_by["key_from"]}
        for command, key in (("PYTHONWARNINGS=error pytest -q", "pytest"),
                             ("export PYTHONPATH=/x; python3 -m pytest tests/", "pytest"),
                             ("python3 tools/check_schema.py", "tools/check_schema.py")):
            self.assertEqual(key, C.event_key(spec, {"tool_input": {"command": command}}))

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red
        """Let the key pattern capture an assignment again, and the assignment cell goes red."""
        smoke_replace(
            self, PLUGIN / "keel" / "clauses.json",
            b'(?=[\\\\s;&|]|$)',
            b'',
            "tests.test_c08_activation.OccasionIsAPrintedPass."
            "test_TEETH_the_key_never_captures_an_assignment",
            "'' != 'F'",
        )


if __name__ == "__main__":
    unittest.main()
