# dispatch-missing-field-sentinel [dead] _MISSING_FIELD module constant and the `if not isinstance(raw, str)` re-test in _subject
LOC 30 -> 26

## description
`_MISSING_FIELD = None` was a module-level name with exactly one reader (`raw = _MISSING_FIELD` on the next-but-one line). The loop below it only ever assigns `raw` when `isinstance(candidate, str) and candidate` is true, so `not isinstance(raw, str)` was exactly `raw is None` -- a second spelling of 'no field matched'. Seed `raw` with the empty string instead and the sentinel, its name, and the type test all go. `fields = C.subject_fields(spec)` was a one-use temporary; inlined (the substring `C.subject_fields(spec)` is what tests/test_subject_across_surfaces.py asserts on, and it survives verbatim).

## diff
--- a/plugin/keel/dispatch.py
+++ b/plugin/keel/dispatch.py
-_MISSING_FIELD = None
-
-
 def _subject(clause, event: dict) -> str:
@@
-        fields = C.subject_fields(spec)
-        raw = _MISSING_FIELD
-        for field in fields:
+        raw = ""
+        for field in C.subject_fields(spec):
             candidate = _get(event, field)
             if isinstance(candidate, str) and candidate:
                 raw = candidate
                 break
-        if not isinstance(raw, str):
-            return ""
-        m = re.search(spec.get("pattern") or "", raw)
+        m = re.search(spec.get("pattern") or "", raw) if raw else None
         if not m:
             return ""

## gate
Ran 245 tests in 207.617s / OK ; REPLAY sessions=26 passed=26 failed=0 ; views/coverings/coq/corpus all exit 0 ; git status --porcelain | wc -l = 3

## complexity
-4 LOC and one module-level name gone. Both the old and new forms return "" for 'no field carried a non-empty string', which the caller reads as unkeyable -- the fail direction is untouched. `tests/test_subject_across_surfaces.py` (the multi-surface subject law and its plant) is green.

## verdict
{"id": "dispatch-missing-field-sentinel", "refuted": false, "reason": "Applied in rd-c5 (1 file). Gate green. LOC real: 557 -> 553 NCNB (-4), as claimed. BEHAVIOUR: byte-identical decisions and ledger rows over all 27 corpus sessions. The equivalence is airtight by construction: `raw` is only ever assigned inside `if isinstance(candidate, str) and candidate`, so after the loop `raw` is either the empty seed or a non-empty str, which makes `if raw` exactly the old `isinstance(raw, str)` test and makes `re.search(pattern, '')` unreachable in both forms. Both return '' for 'no field carried a non-empty string', and the caller reads '' as unkeyable and abstains -- the fail direction is untouched, and `tests/test_subject_across_surfaces.py` (the multi-surface subject law and its plant) is green. The inlining of `fields = C.subject_fields(spec)` keeps the literal substring `C.subject_fields(spec)` that test asserts on. TRIED TO BREAK IT: planted `raw = \"phantom\"` (a bogus operand where no field matched) and planted dropping the `if raw` guard; both are green on the cut tree -- and, importantly for the refutation, the PARITY plant on pristine (`raw = _MISSING_FIELD` -> `\"phantom\"`) is green too. So no coverage was lost; that seam simply was never covered, before or after. No named sentinel remains at module scope.", "gate_output": "cd /tmp/.../simplify/rd-c5 && python3 -m unittest discover -s tests -> Ran 252 tests in 335.807s / OK (exit 0) ; eval/replay.py -> REPLAY sessions=27 passed=27 failed=0 (exit 0) ; render_views.py --check (exit 0) ; render_coverings.py --check (exit 0) ; check_coq.py -> COQ=PASS (exit 0) ; generate_corpus.py --check -> matches 27 specs (exit 0) ; git status --porcelain | wc -l = 1 (M plugin/keel/dispatch.py)."}
