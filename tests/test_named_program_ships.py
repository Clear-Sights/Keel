"""A guard that names a script must name one the operator actually has.

U01 and U02 are the two clauses whose guard names a program by filename rather than by a
system tool: `probe_child_capability.py`. That is NOT the open-vocabulary weakness the other
name-list guards carry -- Coverings.v Thm 5 says a nominal covering is defeated by doing the
same act under another name, and there is no other name for this act. The set is closed at
size one, by construction, because the program is Keel's own and ships in the bundle.

"By construction" is a sentence, and a sentence is not a check. What makes the closure real is
that the file is THERE, and the LOADER is what checks it (`CLAUSE-NAMED-PROGRAM-MISSING`): a
named program absent from the bundle, or a `$CLAUDE_PLUGIN_ROOT/...` path in the sentence
shown to the operator that does not resolve, refuses the whole table. This file no longer
carries that law; it carries the population and the plant that shows the loader's refusal.

The population is DERIVED from the shipped table, never listed here.
"""
from __future__ import annotations

import unittest

from tests.plant_support import PLUGIN, smoke_replace
from keel import clauses as C


class ANamedScriptShips(unittest.TestCase):
    def setUp(self) -> None:
        self.clauses = C.load_default()

    def test_NON_VACUITY_some_guard_names_a_script(self) -> None:
        """Without this the whole module passes over an empty set the day the last one moves."""
        named = [(c.id, n) for c in self.clauses for n in C.vocabulary(c.discharged_by)
                 if n.endswith((".py", ".sh"))]
        self.assertTrue(named, "no guard names a script; the loader's law now grades nothing")
        self.assertEqual({c for c, _ in named}, {"U01", "U02"},
                         "the population moved -- re-measure it, do not edit this set to fit")
        cited = [c.id for c in self.clauses if C._PLUGIN_ROOT_RX.search(c.deny_reason or "")]
        self.assertEqual(sorted(cited), ["U01", "U02"])

    def test_the_loader_refuses_a_remedy_path_that_does_not_resolve(self) -> None:
        """Break the path the operator is told to run: the table refuses to load."""
        smoke_replace(
            self, PLUGIN / "keel" / "clauses.json",
            b'run `python3 \\"$CLAUDE_PLUGIN_ROOT/tools/probe_child_capability.py\\" '
            b'--target TARGET --after-failure --require-change` before the next act",\n    "construction"',
            b'run `python3 \\"$CLAUDE_PLUGIN_ROOT/tools/probe_child_capabilities.py\\" '
            b'--target TARGET --after-failure --require-change` before the next act",\n    "construction"',
            "tests.test_named_program_ships.ANamedScriptShips."
            "test_NON_VACUITY_some_guard_names_a_script",
            "CLAUSE-NAMED-PROGRAM-MISSING",
        )


if __name__ == "__main__":
    unittest.main()
