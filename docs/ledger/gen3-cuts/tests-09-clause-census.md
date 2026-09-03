# tests-09-clause-census [theorem] tests/test_guard_coverings.py::EveryGuardIsWitnessedInBothDirections.test_the_loader_enforces_it_rather_than_this_test
LOC 1 -> 2

## description
`self.assertEqual(len(clauses), 24)` is a literal clause count in a test whose subject is 'every guard is witnessed'. tests/test_effects.py::test_NON_VACUITY_the_shipped_table_has_no_nominal_occasion already declares that census (`self.assertEqual(24, len(table))`, beside its 27 and 16 with 're-measure rather than edit'), so this was a second home for it and said nothing about the loader besides. Replaced by a join to the shipped table: the loader must return one clause per row in clauses.json. Same non-vacuity guarantee (plus an explicit `assertTrue(clauses)`), and it additionally catches a loader that silently drops a row -- the way this population could actually go quiet.

## diff
tests/test_guard_coverings.py:
+import json
 import unittest

         clauses = C.load_default()
-        self.assertEqual(len(clauses), 24)
+        # DERIVED from the shipped table, not a second writer of its size: a literal here was a
+        # third home for a number `test_effects` already declares, and it says nothing about the
+        # loader besides. Read off `clauses.json`, the same assertion also catches a loader that
+        # silently drops a row -- which is the way this population could go quiet.
+        self.assertEqual(len(json.loads(CLAUSES.read_text(encoding="utf-8"))), len(clauses))
+        self.assertTrue(clauses, "an empty table witnesses nothing")
         self.assertTrue(all(c.fixtures_discharge and c.fixtures_no_discharge for c in clauses))

## gate
Ran 246 tests in 203.270s / OK | REPLAY sessions=26 passed=26 failed=0 | views match | coverings match | axioms=0 | eval/corpus matches 26 specs | git status --porcelain | wc -l = 16

## complexity
The non-vacuity floor is not softened: an empty table now fails on both the join (0 != 0 is passed, so the explicit assertTrue catches it) and the fixture sweep.

## verdict
{"id": "tests-09-clause-census", "refuted": false, "reason": "Sustains. The obvious refutation is that this test is itself a plant target -- test_guard_coverings.py:97-106 plants '\"effect\": \"report_listing\"' -> '\"effect\": \"report_self\"' in clauses.json and requires test_the_loader_enforces_it_rather_than_this_test to go red naming CLAUSE-GUARD-FIXTURE-MISS -- so I checked whether the rewritten body can still redden. It can, and for the same reason as before: the mutation makes C09's own positive discharge fixture stop discharging, so `C.load_default()` raises CLAUSE-GUARD-FIXTURE-MISS on line 1 of the test body, before either assertion is reached. The plant is untouched by the cut. Nor is the non-vacuity floor softened: an empty table gives 0 == 0 on the join, but the added `assertTrue(clauses, 'an empty table witnesses nothing')` catches it, and the fixture sweep on the next line is unchanged. The census keeps a home -- tests/test_effects.py:85 is `self.assertEqual(24, len(table))` -- so a clause added or removed from clauses.json still reddens the suite. The join is a real if modest gain: it reddens when the loader returns a different number of clauses than clauses.json holds, which the literal 24 could only catch when the drop happened to land off 24.", "gate_output": "NOT RUN -- plan mode blocked edits and execution; gate taken as reported. Read-only checks: tests/test_guard_coverings.py:60-66 (the test body being rewritten), :44 (CLAUSES is defined at module scope, so the new json.loads has its path), :97-106 (the plant targeting this test, which reddens via a load_default raise before any assertion); tests/test_effects.py:85 (`self.assertEqual(24, len(table))` -- the census's surviving declared home); plugin/keel/clauses.json -> 24 rows."}
