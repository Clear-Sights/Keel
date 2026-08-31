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

# `keel` lives in `plugin/`, and what puts it on `sys.path` is importing `tests.plant_support`
# -- its module-level insert, whose comment states the intent: "So `import keel` does not depend
# on which directory the runner was started from." Eight sibling modules import it first and
# resolve; this one imported `keel` directly and did not, because it is alphabetically first so
# nothing had run the insert yet. It failed only OUTSIDE CI, which sets `PYTHONPATH: plugin` --
# two spellings of one requirement, neither checked against the other. See
# `tests/test_suite_imports_standalone.py`, which now makes that unreachable rather than unlikely.
from tests.plant_support import PLUGIN, smoke_replace
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
    # ADDED because the three above could not activate even with the assignment rule DISARMED:
    # the activation names the program, and none of their BASENAMES carries `check` or `verify`
    # (`checks/` is in the path, not the program). So every one of them was refused for a reason
    # unrelated to the property under test, and the cell was weaker than it read. This one is a
    # real assignment of a real checker path, and it is refused ONLY because an assignment is not
    # an invocation -- which is what makes the plant below able to redden the cell at all.
    "F=tools/check_schema.py",
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
    # DRIVEN THROUGH THE PREDICATE, not through a second copy of it. These two cells used to
    # compile `activated_by["pattern"]` and `re.search` it against the command themselves, which
    # is a second spelling of the rule the dispatcher applies -- the same defect that let a `;`
    # inside quotes discharge a push guard. It also broke the moment the row stopped being a
    # regex: under `kind: program` the pattern is matched against argv[0], so searching it over
    # the whole command reported that `F=path/to/checks/x.py` ACTIVATED, which the dispatcher
    # never did. Asking `_base_predicate` is asking what actually happens.
    def _activates(self, command: str) -> bool:
        predicate = c08().activated_by
        return C._base_predicate(predicate, C._fixture_event(predicate, command)) is True

    def test_TEETH_real_checker_invocations_still_activate(self) -> None:
        for command in INVOCATIONS:
            with self.subTest(command=command):
                self.assertTrue(self._activates(command),
                                "narrowing the occasion must not lose a real checker run")

    def test_TEETH_a_variable_assignment_is_not_an_invocation(self) -> None:
        for command in LOOKALIKES:
            with self.subTest(command=command):
                self.assertFalse(self._activates(command),
                                 "an assignment keyed an obligation nothing can discharge")

    def test_TEETH_the_key_never_captures_an_assignment(self) -> None:
        """Activation and keying are separate patterns; both had the defect, so both are checked."""
        for spec in (c08().activated_by["key_from"], c08().discharged_by["key_from"]):
            for command in LOOKALIKES:
                with self.subTest(command=command, on=spec["on"]):
                    self.assertIsNone(re.search(spec["pattern"], command))

    def test_the_check_can_fail(self) -> None:
        """RE-AIMED at the mechanism that now provides the property.

        The old plant re-broadened a character class inside the activation regex, because the
        narrowing lived in that class. It does not any more: under `kind: program` the predicate
        asks what the segment INVOKES, and `F=path/to/checks/x.py` invokes nothing -- the
        tokenizer consumes a `VAR=value` prefix and finds no program behind it, so no pattern
        could make an assignment activate. The property became structural, which is stronger than
        a character class and is exactly why the old seam no longer exists to plant.

        So the plant is now the tokenizer rule itself: stop recognising an assignment prefix, and
        the assignment is read as the program it is not, and the TEETH cell above must go red.
        """
        smoke_replace(
            self, PLUGIN / "keel" / "clauses.py",
            b'if "=" in token and not token.startswith("-") '
            b'and token.split("=", 1)[0].isidentifier():',
            b'if False and "=" in token and not token.startswith("-") '
            b'and token.split("=", 1)[0].isidentifier():',
            "tests.test_c08_activation.OccasionIsAnInvocation."
            "test_TEETH_a_variable_assignment_is_not_an_invocation",
            "an assignment keyed an obligation nothing can discharge",
        )


if __name__ == "__main__":
    unittest.main()
