"""The Theorem 1 class stays empty, and the gate that says so can fail.

`tools/covering_algebra.py` grades the shipped table against Theorem 1 of proofs/Coverings.v:
a covering reading the RAW COMMAND as text, with a shell metacharacter admitted as left-context,
cannot be mention-immune. Not "is defeated by the three strings we tried" -- defeated for every
command it accepts, because `echo '<c>'` preserves c verbatim and the metacharacter comes along
with it.

This is the reason the gate is not a corpus of mention examples. A corpus reports only the
defeats someone imagined; patching a pattern against them fits it to those strings and excludes
nothing else. Three real defeats in U24 were found that way during this work, and the fix was
not to widen the pattern -- it was to stop reading text, after which all three die together with
no case analysis at all.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
TOOL = REPO / "tools" / "covering_algebra.py"
TABLE = REPO / "plugin" / "keel" / "clauses.json"


def _run(cwd: pathlib.Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOL)], cwd=cwd,
                          capture_output=True, text=True)


class TheTextualClassIsEmpty(unittest.TestCase):
    def test_the_shipped_table_passes(self) -> None:
        done = _run(REPO)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("Theorem 1 class is empty", done.stdout)

    def test_the_denominator_is_stated_and_conserved(self) -> None:
        """A gate reporting only its hits is the defect this estate keeps finding."""
        done = _run(REPO)
        self.assertIn("TOTAL sides = 51 over 24 clauses", done.stdout,
                      "population moved; re-measure rather than edit the expectation")

    def test_the_check_can_fail(self) -> None:
        """Plant a textual covering back into a COPY of the table and require exit 1.

        The fault is a real covering of the retired shape -- the exact form U24's guard had --
        not a marker the tool looks for. Written into a temporary tree so the shipped table is
        never touched, which also means this cell cannot leave a plant behind if it dies."""
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "plugin" / "keel").mkdir(parents=True)
            rows = json.loads(TABLE.read_text(encoding="utf-8"))
            rows[0]["discharged_by"] = {
                "kind": "regex", "on": "tool_input.command",
                "pattern": r"(?:^|[;&|\n]\s*)\s*(?:pytest|go\s+test)\b",
            }
            (root / "plugin" / "keel" / "clauses.json").write_text(
                json.dumps(rows, indent=2), encoding="utf-8")
            done = _run(root)
            self.assertEqual(done.returncode, 1,
                             f"the plant did not redden the gate:\n{done.stdout}{done.stderr}")
            self.assertIn("Theorem 1", done.stdout)
            self.assertIn(f"{rows[0]['id']}.discharged_by", done.stdout)

    def test_NOT_EVALUABLE_when_the_table_is_unreadable(self) -> None:
        """Absence is never a pass: a missing subject exits 2, not 0."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            done = _run(pathlib.Path(tmp))
            self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
            self.assertIn("NOT-EVALUABLE", done.stdout)


if __name__ == "__main__":
    unittest.main()
