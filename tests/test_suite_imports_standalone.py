"""Every test module must load on its own, with no PYTHONPATH and no alphabetical luck.

`keel` lives in `plugin/`, and two separate mechanisms claimed to put it on `sys.path`:

  * `.github/workflows/ci.yml` sets `PYTHONPATH: plugin` on the suite step;
  * `tests/plant_support.py` inserts `PLUGIN` at import time -- "So `import keel` does not
    depend on which directory the runner was started from."

Two spellings of one requirement, and nothing compared them. Eight modules imported
`tests.plant_support` before `keel` and resolved by the second mechanism; `test_c08_activation`
imported `keel` directly and resolved by neither, because it is alphabetically FIRST so no
sibling had run the insert yet. Measured: `python3 -m unittest discover -s tests` at the repo
root gave `ModuleNotFoundError: No module named 'keel'`, while CI stayed green on the env var.

That is not a missing import. It is a contract that existed only as a habit, so conformance was
decided by filename order. What it left unguarded is not incidental: C08's occasion firing on
`F=…/writeThrashRevert.py` -- a variable ASSIGNMENT, not an invocation -- produced 114 demand
rows, 19 of them never dischargeable, blocking every Stop for a session.

`plant_support.smoke_replace` already runs its targets one module at a time with an explicit
environment, which is why a plant on that module would have surfaced it. This file does it for
every module, so the next one to forget is caught at the earliest moment rather than only
outside CI.

WHY EACH CHILD IMPORTS RATHER THAN RUNS. The claim here is exactly "this module resolves its own
imports", and `unittest`'s discovery failure IS an import failure -- so the child imports the
module and nothing else. Two consequences, both load-bearing. The first is that this file
appears in its own module list, as it must (it is a module, and it must load alone too) WITHOUT
running itself: an earlier draft ran `python3 -m unittest tests.<module>` per module, which
re-entered this sweep for its own name and recursed until the runner was killed -- measured as a
10-minute hang. Excluding this file by name would have been a hand-made exclusion, and the
narrower check removes the recursion instead, by construction. The second is that the verdict no
longer depends on `unittest` spelling its diagnostic "Failed to import test module": a check
that reads another tool's prose is a join that breaks silently when that prose changes, which is
the defect class this suite exists to catch. An exit status cannot drift.
"""

from __future__ import annotations

import os
import subprocess
import unittest

from tests.plant_support import REPO, TESTS_CWD, smoke_replace

MODULES = sorted(p.stem for p in (TESTS_CWD / "tests").glob("test_*.py"))
# Deliberately stripped, never merely unset-if-absent: inheriting the parent's PYTHONPATH would
# let this file pass for the same reason CI did, which is the reason it exists.
CLEAN = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}


class EveryTestModuleLoadsAlone(unittest.TestCase):
    maxDiff = None

    def test_the_suite_declares_its_own_imports(self) -> None:
        self.assertTrue(MODULES, "a sweep over no modules measures nothing")
        broken = []
        for module in MODULES:
            done = subprocess.run(
                ["python3", "-c", f"import tests.{module}"], cwd=TESTS_CWD,
                env={**CLEAN, "PYTHONDONTWRITEBYTECODE": "1"},
                text=True, capture_output=True, check=False)
            if done.returncode != 0:
                # The exception line, which names the missing module; the traceback above it is
                # this harness's own frames and says nothing the reader needs.
                lines = [l for l in done.stderr.splitlines() if l.strip()]
                broken.append(f"{module}: {lines[-1] if lines else 'import failed'}")
        self.assertEqual([], broken,
                         "these modules load only when an earlier module happens to have "
                         "imported `tests.plant_support` first, or when PYTHONPATH is set for "
                         "them; import what you depend on")

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red
        """Remove one module's stated dependency and this sweep must name that module."""
        smoke_replace(
            self, REPO / "tests" / "test_c08_activation.py",
            # The seam is the DEPENDENCY, not the names imported through it: quoting the whole
            # import line pinned this plant to one module's import list, and it went stale the
            # first time that list changed. Commenting the statement out leaves the names behind
            # as prose, which removes exactly the thing under test -- the import that puts `keel`
            # on `sys.path` -- and stays true however that list is spelled next.
            b"from tests.plant_support import ",
            b"# dependency removed by the plant: ",
            "tests.test_suite_imports_standalone.EveryTestModuleLoadsAlone."
            "test_the_suite_declares_its_own_imports",
            "test_c08_activation")


if __name__ == "__main__":
    unittest.main()
