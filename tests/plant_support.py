"""The plant harness, and the two roots every plant needs to find.

WHY THE ROOTS ARE SEARCHED FOR RATHER THAN COUNTED. These exact bytes run from two different
places. In the development repository the suite sits at `plugin/tests/`, beside the `keel`
package. Here it sits at `tests/`, at the repository root and OUTSIDE `plugin/` -- because
`plugin/` is precisely what the marketplace installs (`git-subdir`, `path: "plugin"`), so a test
file inside it is a test file on every user's machine. Every module in this suite used to open
with `root = Path(__file__).resolve().parents[1]`, which names a DIFFERENT directory in each of
those two layouts; deriving the roots by looking for the package instead is what lets the two
copies stay byte-identical across the move, and is the reason that line is now written once.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# The directory `tests/` sits in: `plugin/` in development, the repository root when shipped.
# A child running `python3 -m unittest tests.…` needs this as its cwd for the target to resolve.
TESTS_CWD = Path(__file__).resolve().parents[1]

# The directory holding the `keel` package. The same directory in both layouts, reached
# differently: it IS `TESTS_CWD` in development, and `TESTS_CWD / "plugin"` when shipped.
PLUGIN = TESTS_CWD if (TESTS_CWD / "keel").is_dir() else TESTS_CWD / "plugin"

# The repository root, for the gates that read COMMITTED bytes through `git show`.
REPO = PLUGIN.parent

if str(PLUGIN) not in sys.path:
    # So `import keel` does not depend on which directory the runner was started from.
    sys.path.insert(0, str(PLUGIN))


def smoke_replace(case: unittest.TestCase, path: Path, old: bytes, new: bytes,
                  target: str, expected: str) -> str:
    """Mutate one seam, prove the NAMED test goes red because of it, restore, return the output.

    The child's environment is set explicitly rather than inherited, because the two directories
    it needs are no longer the same one: `TESTS_CWD` is where `tests.…` resolves from, `PLUGIN` is
    where `keel` resolves from, and in the shipped layout those are parent and child. A plant
    that ran only when the parent happened to be launched from the right directory would report a
    green seam for the wrong reason.

    The child's combined output is RETURNED so a caller can assert a property of its OWN on it.

    THE TARGET IS RUN TWICE, and the first run is the point. A plant that only shows the target
    RED with the fault is satisfied by a target that is red ALWAYS -- one already broken, or one
    whose `expected` string went stale when the code moved underneath it. That is not
    hypothetical: a plant in this family kept asserting a count that had changed, and stayed
    "passing" because red-with-fault was all it ever checked. So the target must be observed GREEN
    on the unmutated file first; only then does the red run below carry information.

    That property lives HERE rather than in each caller, because it is the same property at every
    plant site and a rule with two homes drifts apart at the first edit. It also means a caller's
    body need not re-assert anything to be a real test: `target` names a single test METHOD at
    every plant site, so the child runs exactly one test and the green-then-red pair already
    proves THAT test went red BECAUSE of this seam. Ceremony is not the same as teeth.
    """
    original = path.read_bytes()
    case.assertIn(old, original, f"plant seam changed in {path}")
    backup = tempfile.NamedTemporaryFile(prefix=path.name + ".", delete=False)
    backup_path = Path(backup.name)
    backup.write(original)
    backup.close()
    def restore() -> None:
        if backup_path.exists():
            path.write_bytes(backup_path.read_bytes())
            backup_path.unlink()
    case.addCleanup(restore)
    def run() -> subprocess.CompletedProcess:
        return subprocess.run(["python3", "-m", "unittest", target], cwd=TESTS_CWD,
                              text=True, capture_output=True, check=False,
                              env={**os.environ, "PYTHONPATH": str(PLUGIN)})

    before = run()
    case.assertEqual(0, before.returncode,
                     f"{target} is not green BEFORE the seam is mutated, so the red run below "
                     f"would prove nothing:\n{before.stdout}{before.stderr}")
    path.write_bytes(original.replace(old, new, 1))
    done = run()
    output = done.stdout + done.stderr
    case.assertNotEqual(0, done.returncode, output)
    case.assertIn(expected, output)
    restore()
    case.assertEqual(original, path.read_bytes(), f"restore differs from backup: {path}")
    return output
