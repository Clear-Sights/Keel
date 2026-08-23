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
