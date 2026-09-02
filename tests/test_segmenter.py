"""Shell segmentation, on the two shapes a naive scanner gets wrong.

Segments decide where a clause may match and which operand a deny names, so a bad split is not
cosmetic: it either invents a segment that never ran, or hides one that did. Both defects below
were measured on the shipped splitter, and both HID a real occasion rather than inventing a false
one -- the direction that fails silent.

  make 2>&1 | tee log   ->  ['make 2>', '1', 'tee log']   the & of a redirect split the command
  'a\\' ; rm -rf /       ->  ["'a\\' ; rm -rf /"]           backslash treated as an escape inside
                                                          single quotes, so the quote never
                                                          closed and `rm -rf /` was never a
                                                          segment start at all

POSIX gives backslash no special meaning inside single quotes; it escapes only within double
quotes. An `&` following `<` or `>` is a redirect, not a control operator.

And the third, found after the other two and worse than either, because it needed no crafted
quoting at all -- a NEWLINE did not separate:

  # note\nrm -rf build/   ->  ['# note\nrm -rf build/']   one segment, beginning with `#`

A shell starts a new command at a newline exactly as it does at `;`. Because the splitter did
not, and because thirty-seven predicates in the clause table spell "where a command starts" by
hand, prefixing ANY command with a comment line turned the whole fence off. Measured on the
shipped table: `rm -rf build/`, `git push --force origin main`, `kill -9 1234`,
`curl -X POST ...` and `git checkout main` all went from deny to allow behind `# note` and a
newline. The last class here is what makes that loud instead of quiet next time -- it asks the
question of the TABLE, per row, from the rows' own fixtures, so a new predicate spelled a new
way cannot reopen the hole by being spelled a new way.
"""

from __future__ import annotations

import unittest
from tests.plant_support import PLUGIN, smoke_replace

from keel import clauses as C

CASES = [
    ("make 2>&1 | tee log", ["make 2>&1", "tee log"]),
    ("'a\\' ; rm -rf /", ["'a\\'", "rm -rf /"]),
    ("git push && git status", ["git push", "git status"]),
    ("grep 'a|b' f", ["grep 'a|b' f"]),
    ('echo "a\\"b" ; rm x', ['echo "a\\"b"', "rm x"]),
    ("# note\nrm -rf build/", ["# note", "rm -rf build/"]),
    ("a\n\nb", ["a", "b"]),
    # A newline inside quotes is text, not a separator -- the same rule the other operators
    # already follow, and the reason the quote branch has to come first.
    ("echo 'a\nb' ; rm x", ["echo 'a\nb'", "rm x"]),
]


class SegmentsSplitOnControlOperatorsOnly(unittest.TestCase):
    def test_TEETH_redirects_and_quoted_backslashes_do_not_split(self) -> None:
        for command, expected in CASES:
            with self.subTest(command=command):
                self.assertEqual(expected, C.segments(command))

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red; a checker that cannot follow an imported helper reads this body as empty
        path = PLUGIN / "keel" / "clauses.py"
        smoke_replace(self, path, b"            elif quote == '\"' and ch == \"\\\\\"",
                      b"            elif ch == \"\\\\\"", "tests.test_segmenter."
                      "SegmentsSplitOnControlOperatorsOnly."
                      "test_TEETH_redirects_and_quoted_backslashes_do_not_split",
                      "'rm -rf /'")
        smoke_replace(self, path, b'            if ch == "&" and buf and buf[-1] in "<>":',
                      b'            if False:', "tests.test_segmenter."
                      "SegmentsSplitOnControlOperatorsOnly."
                      "test_TEETH_redirects_and_quoted_backslashes_do_not_split",
                      "'make 2>', '1'")


if __name__ == "__main__":
    unittest.main()


class ACommentLineDoesNotDisarmTheTable(unittest.TestCase):
    """Every row that fires on a command must still fire when the command has a comment above it.

    THE POINT IS THAT THIS ASKS THE TABLE, NOT THE PATTERNS. Thirty-seven predicates in
    `clauses.json` write "where a command starts" by hand, in three different spellings. When the
    newline was added to two of the three, the third kept the bypass open -- six predicates,
    including `git push`, still allowed a commented command while the other thirty-one had been
    fixed. A syntactic check would have had to know all three spellings, and would go quiet the
    day someone invents a fourth.

    So the question is behavioural and comes from each row's OWN positive fixtures: whatever this
    row says fires, must still fire with `# note` and a newline in front of it. A new predicate
    spelled a new way is judged the same as the old ones, because nothing here reads a pattern.
    """

    PREFIX = "# note\n"

    def test_TEETH_every_command_fixture_still_fires_behind_a_comment_line(self) -> None:
        checked = 0
        for clause in C.load_default():
            for name in ("fingerprint", "activated_by", "discharged_by"):
                predicate = getattr(clause, name, None)
                if not isinstance(predicate, dict):
                    continue
                # NO KIND BRANCH. Selecting `kind == "regex"` here bound this law to one
                # REPRESENTATION of a command covering rather than to the property it is about,
                # which is whether a comment line disarms a row. When the table migrated to
                # invocation matching the loop kept passing while examining ten fixtures instead
                # of thirty-one -- and only the floor below reported it. The property is the same
                # for every kind, so the question is asked of every command predicate.
                if predicate.get("on") != "tool_input.command":
                    continue
                for fixture in self._positives(clause, name):
                    if not isinstance(fixture, str):
                        continue
                    bare = C._fixture_event(predicate, fixture)
                    if not C._base_predicate(predicate, bare):
                        # This fixture is not a positive for THIS predicate; only the ones the
                        # row already claims fire are evidence about the newline.
                        continue
                    commented = C._fixture_event(predicate, self.PREFIX + fixture)
                    checked += 1
                    self.assertTrue(
                        C._base_predicate(predicate, commented),
                        f"{clause.id}.{name}: {fixture!r} fires, but the same command behind a "
                        f"comment line does not -- a comment line disarms this row",
                    )
        # A floor, for the same reason every other count in this suite has one: a loop that
        # examined nothing passes every assertion inside it.
        self.assertGreater(checked, 20, f"only {checked} command fixtures reached the assertion")

    @staticmethod
    def _positives(clause, name: str) -> list:
        if name == "activated_by":
            return list(clause.fixtures_activate or [])
        if name == "discharged_by":
            return list(clause.fixtures_discharge or [])
        return list(clause.fixtures_pos or [])
