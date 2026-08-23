"""C08's occasion is a checker INVOCATION, not any token that happens to contain "check".

The occasion pattern ended `[^\\s;&|]*(?:check|verify)[^\\s;&|]*\\.(?:py|sh)`, and a shell
variable assignment satisfies it: `F=plugin/makoto/checks/writeThrashRevert.py` contains "check"
and ends `.py`, so it both activated the clause AND became the obligation's key. Nothing can ever
discharge such a row, because it names no checker that can be run -- it is an assignment.

Measured in one live session before the fix: 114 C08 demand rows, of which 19 were keyed on a
token containing `=`, spread over 18 distinct never-dischargeable subjects
(`F=`/`M=`/`T=`/`SLICE="` shapes). Those rows blocked every Stop for the rest of the session.

This is the lookalike failure mode, and it is the expensive one: a clause that fires on things it
cannot possibly be satisfied by produces recurring noise, the noise gets the gate switched off,
and switching the gate off silently removes all of its coverage at once. Excluding `=` and quote
characters from the command-word class costs nothing real -- a genuine invocation never carries
`=` inside the program token, and `export PYTHONPATH=/x; python3 -m pytest tests/` still keys off
its second segment exactly as before.
"""

from __future__ import annotations

import re
import unittest

from keel import clauses as C

# the pre-fix spelling, kept ONLY so the teeth test below can show this file is not vacuous
_BROAD_CLASS = r"""[^\s;&|]*"""
_NARROW_CLASS = r"""[^\s;&|="']*"""

INVOCATIONS = [
    "python3 -m pytest -q tests/",
    "pytest -q",
    "python3 -m unittest tests.test_engine",
    "python3 tools/check_schema.py",
    "./verify.sh",
    "python3 $SP/check_equiv.py",
    "export PYTHONPATH=/x; python3 -m pytest tests/",
]

LOOKALIKES = [
    "F=plugin/makoto/checks/writeThrashRevert.py",
    "M=$SP/plugin_mut/makoto/checks/verifierExitMasking.py",
    "T=plugin/makoto/checks/canonFingerprints.py",
]


def c08() -> C.Clause:
    """The C08 row as the RUNTIME loads it.

    `load_default`, which is the one loader there is: the frozen dev archive authors one file per
    clause under plugin/clauses/, while the shipped package carries the built clauses.json, and it
    is the built table the runtime reads. Reading the authoring form would have tested a file the
    installed plugin never sees -- which is the same mistake this whole finding is about.
    """
    for clause in C.load_default():
        if clause.id.startswith("C08"):
            return clause
    raise AssertionError("C08 is not in the shipped clause table")


class OccasionIsAnInvocation(unittest.TestCase):
    def test_TEETH_real_checker_invocations_still_activate(self) -> None:
        pattern = c08().activated_by["pattern"]
        for command in INVOCATIONS:
            with self.subTest(command=command):
                self.assertIsNotNone(re.search(pattern, command),
                                     "narrowing the occasion must not lose a real checker run")

    def test_TEETH_a_variable_assignment_is_not_an_invocation(self) -> None:
        pattern = c08().activated_by["pattern"]
        for command in LOOKALIKES:
            with self.subTest(command=command):
                self.assertIsNone(re.search(pattern, command),
                                  "an assignment keyed an obligation nothing can discharge")

    def test_TEETH_the_key_never_captures_an_assignment(self) -> None:
        """Activation and keying are separate patterns; both had the defect, so both are checked."""
        for spec in (c08().activated_by["key_from"], c08().discharged_by["key_from"]):
            for command in LOOKALIKES:
                with self.subTest(command=command, on=spec["on"]):
                    self.assertIsNone(re.search(spec["pattern"], command))

    def test_the_check_can_fail(self) -> None:
        """Put the pre-fix character class back and the assertion above must go red.

        Without this, `assertIsNone` would pass just as happily against a pattern that matches
        nothing at all, and the two tests above would prove nothing about the narrowing.
        """
        narrowed = c08().activated_by["pattern"]
        self.assertIn(_NARROW_CLASS, narrowed, "the narrowed class is what ships")
        broad = narrowed.replace(_NARROW_CLASS, _BROAD_CLASS)
        self.assertNotEqual(broad, narrowed, "the plant must actually change the pattern")
        for command in LOOKALIKES:
            with self.subTest(command=command):
                self.assertIsNotNone(re.search(broad, command),
                                     "the old spelling must match, or these tests are vacuous")


if __name__ == "__main__":
    unittest.main()
