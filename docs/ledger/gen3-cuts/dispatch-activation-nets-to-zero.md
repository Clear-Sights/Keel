# dispatch-activation-nets-to-zero [space] the unkeyed `activated_by` branch in _watch_standing
LOC 4 -> 3

## description
The unkeyed activation branch wrote a demand under subject "activated" and discharged it on the very next line. Nothing reads that demand: `reconcile` asks `ledger.is_licensed(...derive_id(..., 'activated'))`, which looks only for the discharge row; `open_demands` never sees it because it is closed the instant it opens. The file's own keyed branch already argues exactly this -- 'rows that net to zero and mean nothing, in the journal whose whole job is saying what was owed' -- as the reason the two shapes were split; the unkeyed shape was still doing it. Kept the discharge, dropped the demand.

## diff
--- a/plugin/keel/dispatch.py
+++ b/plugin/keel/dispatch.py
@@ _watch_standing @@
                 else:
-                    # The UNKEYED shape only. Dropping the `continue` above ... rows that net to
-                    # zero and mean nothing, in the journal whose whole job is saying what was owed.
-                    aid = derive_id(session, agent, cl.id, "activated")
-                    ledger.demand(Demand(id=aid, session=session, agent=agent, clause_id=cl.id,
-                                         subject="activated", reason="occasion observed"))
-                    ledger.discharge(session, agent, aid, "occasion observed")
+                    # The UNKEYED shape only, and it writes ONE row. It used to write a demand
+                    # under the subject "activated" and discharge it on the next line -- a pair
+                    # that nets to zero in the journal whose whole job is saying what was owed,
+                    # which is the very complaint that separated this branch from the keyed one
+                    # above. `reconcile` asks `is_licensed`, so only the discharge was ever read;
+                    # the demand was a row written for nobody, once per activating event.
+                    ledger.discharge(session, agent,
+                                     derive_id(session, agent, cl.id, "activated"),
+                                     "occasion observed")

@@ (the branch's shared preamble comment, corrected) @@
-            # ... recorded through the same demand/discharge pair under a distinct subject -- so the
-            # ledger needs no new row shape to carry "the occasion happened".
+            # ... recorded as a discharge under a distinct subject -- so the ledger needs no new row
+            # shape to carry "the occasion happened".

## gate
Ran 245 tests in 207.617s / OK (includes tests/test_clause_fields.py's end-to-end activation law -- two sessions, armed and unarmed, T02 raised only when a remote ref moved -- and tests/test_ledger_growth.py's row-count bound) ; REPLAY sessions=26 passed=26 failed=0 ; git status --porcelain | wc -l = 3

## complexity
SPACE: one fewer persisted ledger row per activating event, forever (the ledger is append-only and every later read is linear in it). TIME: `Ledger.demand` internally calls `open_ids` (one full parse) and `_append` calls `_tail_hash` (another), so the cut also removes 2 full-file parses per activating event. Also removes a latent oddity: on a SECOND activation the old code appended a fresh demand row and then skipped the discharge (already licensed), leaving a duplicate demand id that only `open_ids`' set arithmetic kept harmless.

## verdict
{"id": "dispatch-activation-nets-to-zero", "refuted": false, "reason": "Applied in rd-c7 (1 file). Gate green -- including tests/test_clause_fields.py's end-to-end activation law and tests/test_ledger_growth.py's row-count bound. LOC real: 557 -> 556 NCNB. This is the one I attacked hardest and the hunter is right, including the part I initially believed was overstated. FIRST I TRIED TO SHOW THE REMOVED DEMAND MATTERED: it cannot. `open_ids` is set arithmetic (opened minus closed), so once the single discharge row exists the id is closed forever no matter how many demand rows follow; `reconcile` asks `is_licensed`, which reads only discharge rows. Corpus evidence: decisions byte-identical over all 27 sessions, and the ONLY ledger difference is 4 removed `activated` demand rows (2 in the t02 session, 1 in c03, 1 in d01). THEN I DOUBTED 'one fewer row per activating event, forever' AND MEASURED IT, expecting a cap of 2: driving 1/2/5/20 activations of C03 writes 2/3/6/21 activation rows on pristine and exactly 1 on the cut. So `demand()` appends a fresh junk row on EVERY activation after the first (a closed id is never open, so its idempotence guard never fires), which is unbounded append-only growth in a file every later `open_ids`/`open_demands`/`is_licensed` read is linear in -- an O(n^2) source, not clutter. Their claim is exact, and stronger than they argued. The parse claim reproduces too: 4/7/16/61 ledger parses on pristine for N=1/2/5/20 vs 2/3/6/21 on the cut, i.e. 2 saved per activating event. FAIL DIRECTION PRESERVED AND TESTED: I planted away the surviving discharge -- which would be a fail-OPEN, since `reconcile` skips a clause whose activation is unlicensed -- and it reddens `test_activation_is_observed_and_not_merely_declared`.", "gate_output": "cd /tmp/.../simplify/rd-c7 && python3 -m unittest discover -s tests -> Ran 252 tests in 329.104s / OK (exit 0) ; eval/replay.py -> REPLAY sessions=27 passed=27 failed=0 (exit 0) ; render_views.py --check (exit 0) ; render_coverings.py --check (exit 0) ; check_coq.py -> COQ=PASS (exit 0) ; generate_corpus.py --check -> matches 27 specs (exit 0) ; git status --porcelain | wc -l = 1 (M plugin/keel/dispatch.py). Measured: corpus rows 256 -> 252; scale test 20 activations 21 rows -> 1 row, 61 parses -> 21."}
