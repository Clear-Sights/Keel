"""A guard that names a script must name one the operator actually has.

U01 and U02 are the two clauses whose guard names a program by filename rather than by a
system tool: `probe_child_capability.py`. That is NOT the open-vocabulary weakness the other
name-list guards carry -- Coverings.v Thm 5 says a nominal covering is defeated by doing the
same act under another name, and there is no other name for this act. The set is closed at
size one, by construction, because the program is Keel's own and ships in the bundle.

"By construction" is a sentence, and a sentence is not a check. What makes the closure real is
that the file is THERE: the clause denies an act and its `deny_reason` tells the operator to
run `python3 "$CLAUDE_PLUGIN_ROOT/tools/probe_child_capability.py" ...`. If that file is ever
renamed, moved, or dropped from the bundle, the clause becomes a deny with no remedy anyone
could follow -- an obligation nothing can discharge, which is the expensive failure mode C08's
own incident record describes: recurring noise gets the gate switched off, and switching it
off removes all of that clause's coverage at once.

The population is DERIVED from the shipped table, never listed here. A clause added tomorrow
whose guard names a script is covered the day it is added, and this file does not have to
change for that to be true.
"""
from __future__ import annotations

import re
import unittest

from tests.plant_support import PLUGIN, smoke_replace
from keel import clauses as C

# What the deny_reason tells an operator to run, in the spelling it uses.
PLUGIN_ROOT_RX = re.compile(r"\$CLAUDE_PLUGIN_ROOT/([\w./-]+)")


def guard_names(predicate) -> list[str]:
    """Every program name a guard names, compound guards included."""
    if not isinstance(predicate, dict):
        return []
    found = list(predicate.get("names") or [])
    for sub in (predicate.get("any_of") or []) + (predicate.get("all_of") or []):
        found += guard_names(sub)
    return found


class ANamedScriptShips(unittest.TestCase):
    def setUp(self) -> None:
        self.clauses = C.load_default()

    def test_NON_VACUITY_some_guard_names_a_script(self) -> None:
        """Without this the whole module passes over an empty set the day the last one moves."""
        named = [(c.id, n) for c in self.clauses for n in guard_names(c.discharged_by)
                 if n.endswith((".py", ".sh"))]
        self.assertTrue(named, "no guard names a script; this law now grades nothing")
        self.assertEqual({c for c, _ in named}, {"U01", "U02"},
                         "the population moved -- re-measure it, do not edit this set to fit")

    def test_TEETH_every_script_a_guard_names_is_in_the_bundle(self) -> None:
        for clause in self.clauses:
            for name in guard_names(clause.discharged_by):
                if not name.endswith((".py", ".sh")):
                    continue  # a system tool, not something this repo ships
                with self.subTest(clause=clause.id, script=name):
                    matches = list(PLUGIN.rglob(name))
                    self.assertTrue(matches,
                                    f"{clause.id}'s guard names {name}, which the bundle does "
                                    f"not contain: the clause denies with a remedy nobody can run")

    def test_TEETH_the_deny_reason_names_a_path_that_resolves(self) -> None:
        """The guard's NAME and the sentence shown to the operator are two different strings,
        and only the second one is what a person acts on. A correct name behind a wrong path
        still leaves the operator stuck."""
        checked = 0
        for clause in self.clauses:
            for rel in PLUGIN_ROOT_RX.findall(clause.deny_reason or ""):
                with self.subTest(clause=clause.id, path=rel):
                    self.assertTrue((PLUGIN / rel).exists(),
                                    f"{clause.id} tells the operator to run "
                                    f"$CLAUDE_PLUGIN_ROOT/{rel}, which is not in the bundle")
                    checked += 1
        self.assertTrue(checked, "no deny_reason cites a plugin-root path; nothing was graded")

    def test_the_check_can_fail(self) -> None:
        """Break the path the operator is told to run.

        RE-AIMED, and the reason is worth keeping. The first plant renamed the guard's program
        (`probe_child_capability.py` -> `...capabilities.py`) and expected the bundle cell to go
        red. It does not get the chance: U01's own discharge fixtures invoke the real name, the
        LOADER checks guard fixtures, and the table refuses to ship at all --
        `CLAUSE-GUARD-FIXTURE-MISS: U01`. That is a stronger outcome than this law reddening, so
        a renamed program is already covered and needs nothing here. What is NOT covered by any
        loader check is the sentence shown to the operator: `deny_reason` is prose to the table,
        so a path that stopped resolving passes every other gate in the repo. That is the gap
        this law exists for, so that is where the plant belongs.
        """
        smoke_replace(
            self, PLUGIN / "keel" / "clauses.json",
            b'run `python3 \\"$CLAUDE_PLUGIN_ROOT/tools/probe_child_capability.py\\" '
            b'--target TARGET --after-failure --require-change`",\n    "construction"',
            b'run `python3 \\"$CLAUDE_PLUGIN_ROOT/tools/probe_child_capabilities.py\\" '
            b'--target TARGET --after-failure --require-change`",\n    "construction"',
            "tests.test_named_program_ships.ANamedScriptShips."
            "test_TEETH_the_deny_reason_names_a_path_that_resolves",
            "is not in the bundle",
        )


if __name__ == "__main__":
    unittest.main()
