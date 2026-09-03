# tests-11-plant-seam [test] tests/test_suite_imports_standalone.py::EveryTestModuleLoadsAlone.test_the_check_can_fail
LOC 2 -> 2

## description
REPORTED AS PART OF CUT tests-01 PER RULE (3): this test failed when I removed the seven record-dict copies, because its plant quoted test_c08_activation.py's whole import line verbatim (`from tests.plant_support import PLUGIN, smoke_replace`) and that line gained `record`. Its own four-line comment records that the seam had ALREADY gone stale once for the same reason. The test does not restate the loader -- it is a real property (every module resolves its own imports) -- but its fixture restated a list that lives in another file. Rewritten to derive: the seam is now the DEPENDENCY (`from tests.plant_support import `), replaced by a comment prefix that leaves the imported names behind as prose. That removes exactly the thing under test, however the import list is spelled next, and the four lines explaining the last drift go with it. Verified red-for-the-right-reason by the plant itself: `smoke_replace` runs the target green, plants the fault, and requires red naming `test_c08_activation`.

## diff
tests/test_suite_imports_standalone.py:
         smoke_replace(
             self, REPO / "tests" / "test_c08_activation.py",
-            # The seam follows the module: `test_c08_activation` now imports `smoke_replace`
-            # alongside `PLUGIN`, because its own plant became a real fault injection rather than
-            # a string edit. The dependency being removed is the same one -- the import that puts
-            # `keel` on `sys.path` -- so the property under test is unchanged.
-            b"from tests.plant_support import PLUGIN, smoke_replace",
-            b"# dependency removed by the plant",
+            # The seam is the DEPENDENCY, not the names imported through it: quoting the whole
+            # import line pinned this plant to one module's import list, and it went stale the
+            # first time that list changed. Commenting the statement out leaves the names behind
+            # as prose, which removes exactly the thing under test -- the import that puts `keel`
+            # on `sys.path` -- and stays true however that list is spelled next.
+            b"from tests.plant_support import ",
+            b"# dependency removed by the plant: ",
             "tests.test_suite_imports_standalone.EveryTestModuleLoadsAlone."
             "test_the_suite_declares_its_own_imports",
             "test_c08_activation")

## gate
python3 -m unittest tests.test_suite_imports_standalone -> Ran 2 tests in 5.490s / OK. Whole gate: Ran 246 tests in 203.270s / OK | REPLAY sessions=26 passed=26 failed=0 | views match | coverings match | axioms=0 | eval/corpus matches 26 specs | git status --porcelain | wc -l = 16

## complexity
The plant still spawns two child runs (green then red); this cut changes the fixture, not the cost.

## verdict
{"id": "tests-11-plant-seam", "refuted": false, "reason": "Sustains, and it is correctly reported as part of tests-01 per rule (3) rather than smuggled in. I tried three ways to break the new seam and none work. (a) Does it still match? test_c08_activation.py holds exactly one line beginning `from tests.plant_support import `, so smoke_replace's `assertIn(old, original)` guard holds and the single-occurrence `replace(old, new, 1)` hits the right statement. (b) Does it still remove the dependency? Substituting `# dependency removed by the plant: ` yields `# dependency removed by the plant: PLUGIN, record, smoke_replace` -- a valid comment that disables the whole statement, so the module loses the import that puts PLUGIN on sys.path, which is precisely the thing test_the_suite_declares_its_own_imports measures. The target reddens naming test_c08_activation either via the failed `from keel import ...` or via a NameError on the now-unbound names; both are red for the right reason. (c) Is it looser in a way that could match something else? The prefix is anchored to a full import statement of one specific module, and no other line in that file begins with it. This is a genuine derivation: the old seam quoted another module's whole import LIST, which is why it went stale when tests-01 added `record` -- and the four-line comment in the file records that it had already gone stale once for exactly the same reason, so the cut removes a known-recurring coupling rather than a hypothetical one. The property under test is unchanged and nothing is softened.", "gate_output": "NOT RUN -- plan mode blocked edits and execution; gate taken as reported, including the module-level `python3 -m unittest tests.test_suite_imports_standalone -> Ran 2 tests / OK`. Read-only checks: tests/plant_support.py smoke_replace (`case.assertIn(old, original)` and `original.replace(old, new, 1)` -- single occurrence, guarded); tests/test_c08_activation.py has exactly one `from tests.plant_support import ` line; the existing four-line comment at the plant site documenting the previous staleness of the quoted-import-list seam."}
