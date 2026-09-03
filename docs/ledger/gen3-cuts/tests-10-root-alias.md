# tests-10-root-alias [loc] tests/test_host_shape.py (`ROOT = REPO`)
LOC 2 -> 1

## description
The module imports `REPO` from plant_support and immediately rebinds it as `ROOT`, used once. One name.

## diff
tests/test_host_shape.py:
 from tests.plant_support import REPO
 
-ROOT = REPO
 CLAUDE = "plugin/hooks/hooks.json"

 def committed(path: str) -> dict:
-    shown = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=ROOT,
+    shown = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=REPO,

## gate
Ran 246 tests in 203.270s / OK | REPLAY sessions=26 passed=26 failed=0 | views match | coverings match | axioms=0 | eval/corpus matches 26 specs | git status --porcelain | wc -l = 16

## complexity
None.

## verdict
{"id": "tests-10-root-alias", "refuted": false, "reason": "Sustains. `grep -n ROOT tests/test_host_shape.py` shows exactly two occurrences: the rebinding `ROOT = REPO` at line 28 and its single use as the `cwd` of the `git show` call at line 35. Substituting REPO at that one site and deleting the alias is a pure rename with no reachable behaviour, since REPO is imported from plant_support and is the same object. Nothing fail-closed, no stated limit, no plant seam, no clause coverage is involved. Small, but real: 2 non-blank lines become 1.", "gate_output": "NOT RUN -- plan mode blocked edits and execution; gate taken as reported. Read-only check: `grep -n ROOT tests/test_host_shape.py` -> 28 (`ROOT = REPO`) and 35 (`cwd=ROOT`), no others."}
