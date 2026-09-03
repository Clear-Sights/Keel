# dispatch-applicable-predicate [function] _applicable(table, event) and its two `applicable = {id(cl) for cl in _applicable(...)}` call sites
LOC 555 -> 550

## description
`_applicable` was a generator that walked the whole clause table, whose only two callers immediately collapsed it into a set of CPython `id()` values and then walked the table again, testing `id(cl) not in applicable`. That is one extra full table walk, one N-element set, and an identity-keyed membership test, per PreToolUse and per PostToolUse event -- to answer a question about a single clause that the caller already has in hand. Replaced by a predicate `_applies(cl, event)` called at the point of use. Nothing outside dispatch.py referenced `_applicable`.

## diff
--- a/plugin/keel/dispatch.py
+++ b/plugin/keel/dispatch.py
-def _applicable(table, event: dict):
-    name, tool = event.get("hook_event_name"), event.get("tool_name")
-    for cl in table:
-        if cl.event != name:
-            continue
-        if cl.tools and cl.tools != ["*"] and tool not in cl.tools:
-            continue
-        yield cl
+def _applies(cl, event: dict) -> bool:
+    """Does this clause declare this event and this tool? Asked of one clause at the moment the
+    answer is used, rather than pre-walked into a set of `id()`s: the caller is already looping
+    the table, so the pre-pass was a second walk and a second copy of the table's identity."""
+    if cl.event != event.get("hook_event_name"):
+        return False
+    return not cl.tools or cl.tools == ["*"] or event.get("tool_name") in cl.tools

@@ pre_tool_use @@
     denials = []
-    applicable = {id(cl) for cl in _applicable(table, event)}
     for cl in table:

@@ post_tool_use @@
-    applicable = {id(cl) for cl in _applicable(table, event)}
     for cl in table:

@@ both loops (identical hunk) @@
-            if id(cl) not in applicable:
+            if not _applies(cl, event):
                 continue

## gate
Ran 245 tests in 207.617s / OK ; REPLAY sessions=26 passed=26 failed=0 ; views/coverings/coq/corpus all exit 0 ; git status --porcelain | wc -l = 3

## complexity
SPACE: one set of |table| ids allocated per PreToolUse and per PostToolUse event is now zero -- 225 sets of up to 24 entries removed across the 231-event corpus. TIME: 2 full table walks per event become 1 (the pre-pass is gone; the predicate is O(1) per clause and runs on clauses the loop already visits). -5 LOC. Behaviour: `_applies` now runs inside the per-clause `try`, which only widens the existing isolation; the comparisons it makes (dataclass field vs dict `.get`) cannot raise.

## verdict
{"id": "dispatch-applicable-predicate", "refuted": false, "reason": "Applied in rd-c3 (1 file). Gate green. LOC real: 557 -> 552 NCNB (-5), exactly as claimed. BEHAVIOUR: byte-identical decisions and ledger rows over all 27 corpus sessions. The predicate is exactly De Morgan of the generator's two `continue`s (`cl.event != name` -> False; excluded iff `cl.tools and cl.tools != ['*'] and tool not in cl.tools`, so included iff `not cl.tools or cl.tools == ['*'] or tool in cl.tools`). NO COVERAGE LOST, measured rather than argued: planting `_applies -> return True` on the cut tree and planting the equivalent widening of `_applicable` (yield every clause) on the pristine tree produce the IDENTICAL 14-failure set across the full 252-test suite (test_bidirectional_chain x2, test_effects x2, test_measured x4, plus their can-fail plants). THE ONE REAL SEMANTIC MOVE, which I checked rather than accepted: `_applies` now runs inside the per-clause `try`, so a raise there would abstain per clause instead of failing the whole event closed through main()'s `_closed_not_evaluable`. It is unreachable -- `event` and `tools` are required `Clause` dataclass fields, `event` is guaranteed a dict before any handler runs (main raises ValueError otherwise), string `!=` and `in`-on-a-list cannot raise -- and moving it inside is what the loop's own docstring already asks for ('a clause that raises must never suppress the other twenty-five'). Space claim verified: the per-event set of up to 24 `id()` values is gone on both PreToolUse and PostToolUse; two full table walks become one.", "gate_output": "cd /tmp/.../simplify/rd-c3 && python3 -m unittest discover -s tests -> Ran 252 tests in 328.592s / OK (exit 0) ; eval/replay.py -> REPLAY sessions=27 passed=27 failed=0 (exit 0) ; render_views.py --check (exit 0) ; render_coverings.py --check (exit 0) ; check_coq.py -> COQ=PASS (exit 0) ; generate_corpus.py --check -> matches 27 specs (exit 0) ; git status --porcelain | wc -l = 1 (M plugin/keel/dispatch.py)."}
