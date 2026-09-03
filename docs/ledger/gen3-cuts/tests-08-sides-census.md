# tests-08-sides-census [theorem] tests/test_derived_closure.py::EverySideHasAClassAndAnInstance.test_TEETH_the_proof_compiles_with_zero_axioms
LOC 1 -> 1

## description
`self.assertEqual(51, len(sides), 'side count moved; re-measure rather than edit')` at line 43 is the declared census and its stated home. Forty-four lines later `self.assertIn('sides=51', done.stdout)` restated the same 51 against check_coq.py's output -- so the grader's count was being compared to a literal rather than to the sides it graded, and adding a clause meant editing the number in two places. Derived from the loaded table instead: `f'sides={len(_sides())}'`. The check is now strictly stronger (the proof's coverage is joined to the live table, not to a constant) and the census keeps one home.

## diff
tests/test_derived_closure.py:
         self.assertIn("axioms=0", done.stdout)
-        self.assertIn("sides=51", done.stdout)
+        # DERIVED from the loaded table. The census has one home, twelve lines up; restating it
+        # here made the grader's count agree with a literal rather than with the sides it graded.
+        self.assertIn(f"sides={len(_sides())}", done.stdout)

## gate
python3 tools/check_coq.py -> PASS Clauses.v covers sides=51 of clauses=24: instantiated=36 empty-by-class[always=7 tool-enum=8] ; Coverings.v: results=16 axioms=0 parameters=16 ; Clauses.v: results=74 axioms=0 parameters=3 (exit 0). Suite: Ran 246 tests in 203.270s / OK | git status --porcelain | wc -l = 16

## complexity
coqc is present in this environment, so the test is not skipped and the derived form was actually exercised.

## verdict
{"id": "tests-08-sides-census", "refuted": false, "reason": "Sustains, and the derived form is strictly stronger rather than softer. The two numbers are NOT two derivations of the same thing: tools/check_coq.py:113-139 builds `expected` from the RAW clauses.json rows (`{f\"{c['id']}_{side}\" for c in rows ... if isinstance(c.get(side), dict)}`) and prints sides=len(expected), whereas tests/test_derived_closure.py::_sides builds its list from `C.load_default()`, i.e. from Clause objects the LOADER constructed. So `assertIn(f'sides={len(_sides())}')` joins the proof's coverage to the loader's output, and it reddens on a loader that silently drops or retypes a side -- a defect the literal 'sides=51' could not see, because check_coq would still have printed 51. I checked the two ways this could have been a softening and neither holds. First, the census keeps its declared home: tests/test_derived_closure.py:43 still carries `assertEqual(51, len(sides), 'side count moved; re-measure rather than edit')`, so a clauses.json that loses a clause still reddens there (and at render_views/render_coverings/check_coq --check), even though it would no longer redden inside test_TEETH. Second, no plant depends on the literal: the plants in this module (lines 95 and 106) both target test_NON_VACUITY_the_population_is_measured_not_asserted, not test_TEETH_the_proof_compiles_with_zero_axioms, so nothing that used to redden goes green. The test is genuinely exercised rather than skipped -- coqc is present at /usr/bin/coqc, so the skipIf does not fire.", "gate_output": "NOT RUN -- plan mode blocked edits and execution; gate taken as reported. Read-only checks: tools/check_coq.py:113-116 (expected built from raw rows) and :139 (`sides={len(expected)}`); tests/test_derived_closure.py:35-37 (_sides from C.load_default()), :43 (the surviving literal census with its 're-measure rather than edit' note), :95 and :106 (both plants target test_NON_VACUITY..., not test_TEETH); `which coqc` -> /usr/bin/coqc, so the skipIf does not fire."}
