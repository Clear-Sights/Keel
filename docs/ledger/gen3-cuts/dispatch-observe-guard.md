# dispatch-observe-guard [replication] the guard-observation block duplicated in pre_tool_use and post_tool_use
LOC 555 -> 562

## description
pre_tool_use and post_tool_use each carried the same rule: skip terminal clauses, ask `C.discharges`, derive the id, and discharge only if the clause is not effect-side or its demand is already open. 14 lines, twice, with a comment block each. The two copies had ALREADY diverged: pre wrote `how="guard call observed"` and post wrote `how="guard call completed"` -- two words for one event, in a field the ledger stores and nothing anywhere reads (grep: `how` appears only at the 4 dispatch call sites and in `Ledger.discharge`'s row literal). Extracted `_observe_guard(...)` returning None (not this clause's guard) / True (a demand was discharged) / False (guard seen, bought nothing) -- the tri-state is what lets pre keep its `progress` bookkeeping while post ignores it.

## diff
--- a/plugin/keel/dispatch.py
+++ b/plugin/keel/dispatch.py
+# EVERY CLAUSE IS READ AS A GUARD ON EVERY EVENT ... (the two comment blocks, merged)
+# ONE FUNCTION, BOTH SIDES OF THE ACT. `pre_tool_use` and `post_tool_use` carried this rule as two
+# copies that differed only in the word they wrote into `how` -- a field the ledger stores and
+# nothing reads.
+def _observe_guard(ledger: Ledger, event: dict, session: str, agent: str, cl, open_ids):
+    """None if this event is not `cl`'s guard; else whether the guard discharged a demand."""
+    if cl.event in ("Stop", "SubagentStop") or not C.discharges(cl, event):
+        return None
+    did = derive_id(session, agent, cl.id, _subject(cl, event))
+    if C.classify_side(cl.fingerprint) != "effect" or did in open_ids:
+        ledger.discharge(session, agent, did, "guard call observed")
+        return True
+    return False

@@ pre_tool_use loop @@
-            if cl.event not in ("Stop", "SubagentStop") and C.discharges(cl, event):
-                subject = _subject(cl, event)
-                did = derive_id(session, agent, cl.id, subject)
-                if (C.classify_side(cl.fingerprint) != "effect"
-                        or did in ledger.open_ids(session, agent)):
-                    ledger.discharge(session, agent, did, "guard call observed")
-                    progress = True
+            observed = _observe_guard(ledger, event, session, agent, cl, open_ids)
+            if observed is not None:
+                progress = progress or observed
                 continue

@@ post_tool_use loop @@
-            after_the_act = C.classify_side(cl.fingerprint) == "effect"
-            if cl.event not in ("Stop", "SubagentStop") and C.discharges(cl, event):
-                did = derive_id(session, agent, cl.id, _subject(cl, event))
-                if not after_the_act or did in ledger.open_ids(session, agent):
-                    ledger.discharge(session, agent, did, "guard call completed")
-                continue
-            if id(cl) not in applicable:
-                continue
+            if _observe_guard(ledger, event, session, agent, cl, open_ids) is not None:
+                continue
+            if not _applies(cl, event):
+                continue
+            after_the_act = C.classify_side(cl.fingerprint) == "effect"

## gate
Ran 245 tests in 207.617s / OK ; REPLAY sessions=26 passed=26 failed=0 ; views/coverings/coq/corpus all exit 0 ; git status --porcelain | wc -l = 3

## complexity
HONEST LOC: this one COSTS +7 lines (measured by isolated application; 555 -> 562). What it buys is 14 duplicated lines of the mechanism's most load-bearing rule collapsing to 9 shared lines plus a 4-line and a 2-line call site, and the elimination of a live divergence between the copies (two different `how` strings). Function count in the file goes 28 -> 30 overall (`_header`, `_observe_guard` added, `_applicable` reshaped to `_applies`); I report that against the empty-program standard rather than hiding it. Same runtime work per clause.

## verdict
{"id": "dispatch-observe-guard", "refuted": false, "reason": "This diff does not apply on its own -- it references `open_ids` (from dispatch-ledger-read-per-event) and `_applies` (from dispatch-applicable-predicate) -- so I built it cumulatively in rd-c234 and the whole gate is green there. BEHAVIOUR: decisions byte-identical over all 27 corpus sessions; the ONLY difference anywhere in the ledger is 90 `how` values changing from 'guard call completed' to 'guard call observed'. I verified their central claim that nothing reads `how` rather than taking it: it is written once in `Ledger.discharge`'s row literal and read by no test, no README/docs prose, no proof, no eval/replay code, no journal code (`grep` for `row['how']` / `.get('how')` across the tree returns nothing), and neither string literal occurs outside dispatch.py. So the divergence they collapse is real and unobservable, and collapsing it changes no decision. Equivalence of the tri-state also checks out: None/True/False preserves `progress` for pre and is ignored by post, and the reordering of `after_the_act` behind `_applies` cannot change outcomes because a raise from `classify_side` lands in the same per-clause `except` either way. HONEST COST, with one number to correct: measured on top of c2+c3, this costs +3 NCNB lines (553 -> 556), not the +7 they report; the direction of their self-report is right and they state the cost plainly, so this is them being harder on themselves than the measurement warrants. Function count 28 -> 29 in this tree. No fail-closed direction dropped, no limit softened, no plant lost, no ledger-parse regression (parse counts identical to c2 alone).", "gate_output": "cd /tmp/.../simplify/rd-c234 (c2+c3+c4) && python3 -m unittest discover -s tests -> Ran 252 tests in 351.792s / OK (exit 0) ; eval/replay.py -> REPLAY sessions=27 passed=27 failed=0 (exit 0) ; render_views.py --check (exit 0) ; render_coverings.py --check (exit 0) ; check_coq.py -> COQ=PASS (exit 0) ; generate_corpus.py --check -> matches 27 specs (exit 0) ; git status --porcelain | wc -l = 1 (M plugin/keel/dispatch.py). Corpus diff vs pristine: 90 `how` strings, zero decision changes, zero row-count changes."}
