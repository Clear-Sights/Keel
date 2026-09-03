# dispatch-ledger-read-per-event [time] pre_tool_use / post_tool_use clause loops; _open_effect_denial signature
LOC 555 -> 556

## description
Both clause loops called `ledger.open_ids(session, agent)` INSIDE the per-clause body, and `Ledger` has no cache: every call reopens `obligations.jsonl` and json-parses every line. So one PostToolUse event cost up to one full ledger parse per clause (24), and pre_tool_use paid a second full read on top of the `open_demands` that `_open_effect_denial` had just done for the same event. Both are hoisted to one read per event. This is safe by construction and the comment says why: `derive_id` mixes the clause id into the key, so a discharge or demand made while processing clause A can never change the membership answer clause B is asking about. In pre_tool_use the set is derived from the `open_rows` that `_open_effect_denial` already read (`open_demands` returns exactly one row per open id), so the extra read disappears entirely rather than moving.

## diff
--- a/plugin/keel/dispatch.py
+++ b/plugin/keel/dispatch.py
-def _open_effect_denial(table, ledger: Ledger, event: dict, session: str, agent: str):
+def _open_effect_denial(table, ledger: Ledger, event: dict, session: str, agent: str, open_rows):
     ...
+    `open_rows` is passed in rather than read here, because the caller needs the same answer:
+    one read of the ledger per event, not one per reader of it.
     """
-    open_rows = ledger.open_demands(session, agent)
     if not open_rows:
         return None, False

@@ pre_tool_use @@
-    held, progress = _open_effect_denial(table, ledger, event, session, agent)
+    # ONE LEDGER READ PER EVENT. Every `open_ids`/`open_demands`/`is_licensed` call re-opens and
+    # re-parses the whole append-only file, so asking inside the clause loop made the cost of one
+    # event linear in the table AND in the ledger. The set below is read once and reused: each
+    # clause tests only its own `did`, and `derive_id` mixes the clause id in, so a discharge or
+    # demand made for one clause can never be the answer another clause is asking for.
+    open_rows = ledger.open_demands(session, agent)
+    held, progress = _open_effect_denial(table, ledger, event, session, agent, open_rows)
     if held is not None:
         return held
+    open_ids = {row["id"] for row in open_rows}
     _effect_record(ledger, event, "before")
 ...
-                if (C.classify_side(cl.fingerprint) != "effect"
-                        or did in ledger.open_ids(session, agent)):
+                if C.classify_side(cl.fingerprint) != "effect" or did in open_ids:

@@ post_tool_use @@
+    open_ids = ledger.open_ids(session, agent)  # once per event; see `pre_tool_use`
     for cl in table:
 ...
-                if not after_the_act or did in ledger.open_ids(session, agent):
+                if not after_the_act or did in open_ids:

## gate
Ran 245 tests in 207.617s / OK ; REPLAY sessions=26 passed=26 failed=0 ; views match plugin/keel/clauses.json ; proofs/Clauses.v matches plugin/keel/clauses.json ; COQ=PASS ; eval/corpus matches 26 specs ; git status --porcelain | wc -l = 3

## complexity
MEASURED by wrapping `Ledger._rows` (the only file reader) with a counter and driving all 26 corpus sessions (231 events) in-process. Full-ledger parses: BEFORE 1677, AFTER 1354 (-19.3%). Per event: PostToolUse 8.43 -> 6.68, PreToolUse 6.44 -> 5.24, Stop 7.33 -> 7.00. Callers eliminated: `open_ids <- post_tool_use` 251 -> 92, `open_ids <- pre_tool_use` 156 -> 0. Wall-clock on a synthetic 120-event session against a 2000-row ledger (3 interleaved runs each): BEFORE 19.5/15.3/11.6 s, AFTER 16.9/10.8/10.7 s; scans 1888 -> 1712. Costs +1 LOC; this cut is time, not lines. Clause table loads were already correct at exactly 1.00 per event (`C.load_default()` in main) -- measured, unchanged.

## verdict
{"id": "dispatch-ledger-read-per-event", "refuted": false, "reason": "Applied in rd-c2 (1 file). Gate green. LOC +1 (557 -> 558 NCNB), which they report as a cost. BEHAVIOUR: byte-identical decisions AND byte-identical ledger rows over all 27 corpus sessions -- 256 rows written either way (67 demand, 189 discharge). Their safety argument holds under audit: the only staleness window is ids discharged inside `_open_effect_denial`, and a stale-open id can only make `did in open_ids` MORE permissive, after which `Ledger.discharge` early-returns on `is_licensed`, so no discharge row can exist that did not exist before -- which the identical row dump confirms empirically. `derive_id` mixes the clause id in, so no clause's write can answer another clause's question. HEADLINE MEASUREMENT REPRODUCES: wrapping `Ledger._rows` (the only file reader) and driving the corpus in-process gives 1776 -> 1442 full-file parses (-18.8%); per event PostToolUse 8.65 -> 6.89, PreToolUse 6.49 -> 5.30, Stop 7.33 unchanged. TWO QUALIFICATIONS I FOUND BY ATTACKING IT, neither meeting a refutation criterion but both material. (1) The wall-clock claim does not reproduce: 2000-row padded ledger, 120 events, 3 interleaved runs each -- pristine best 9.05/9.24s, cut best 9.36/9.52s, i.e. no improvement, inside the noise. Their own figures (19.5/15.3/11.6s in ONE condition) span 8s and cannot support the conclusion either. (2) The `post_tool_use` hoist is UNCONDITIONAL, so on any event where no clause's guard matches, the cut pays one full ledger parse the original never paid. Measured on a guard-free Bash workload: 1807 -> 1867 parses (+3.3%), exactly +1 per PostToolUse event. So this is a workload trade, not a monotone win; the derived form should read `open_ids` lazily on first guard hit, which would be strictly better than both. Fail directions untouched, no plant lost, no limit softened.", "gate_output": "cd /tmp/.../simplify/rd-c2 && python3 -m unittest discover -s tests -> Ran 252 tests in 224.955s / OK (exit 0) ; eval/replay.py -> REPLAY sessions=27 passed=27 failed=0 (exit 0) ; render_views.py --check (exit 0) ; render_coverings.py --check (exit 0) ; check_coq.py -> COQ=PASS (exit 0) ; generate_corpus.py --check -> eval/corpus matches 27 specs (exit 0) ; git status --porcelain | wc -l = 1 (M plugin/keel/dispatch.py). Complexity, measured: corpus ledger parses 1776 -> 1442; guard-free synthetic 1807 -> 1867."}
