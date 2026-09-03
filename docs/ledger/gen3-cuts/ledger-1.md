# ledger-1 [function] Ledger._tail_hash, Ledger.is_licensed, Ledger.open_ids, Ledger.open_demands -> one Ledger.scope(); dispatch's per-clause ledger.is_licensed/open_ids/open_demands calls -> one hoisted read per handler
LOC 123 -> 103

## description
ANSWER TO THE QUESTION: demand/discharge/open are ONE set difference, and the code said it four times. `open_ids` walked the file to build `opened - closed`; `open_demands` called `open_ids` (walk 1) and then walked AGAIN to fetch the rows for those ids; `is_licensed` walked a third time to answer `id in closed`; and `_append` walked a fourth time (via `_tail_hash`) for the chain head, so every `demand()` and every `discharge()` cost two full walks. Worse, `dispatch` asked those questions inside its per-clause loop, so a 24-clause table re-opened and re-parsed an R-row ledger O(C*R) times per event. All four answers -- the open demand rows, the discharged ids, the chain head -- fall out of one pass, so `scope(session, agent)` is that pass and the three public readers are deleted. `pre_tool_use`, `post_tool_use` and `reconcile` take one snapshot before their clause loop; that is exact, not approximate, because a demand id is derived from its own `cl.id`, so no clause's write inside the loop can move another clause's answer (post_tool_use's post-loop `still` read is left fresh, since it must see the loop's writes). NOT SOFTENED: `scope` keeps the fail-closed rule verbatim -- a licence is membership in `discharged` and nothing else, never 'absent from open'.

## diff
--- a/plugin/keel/ledger.py
+++ b/plugin/keel/ledger.py
@@
-# row kinds -- `open_ids` is the demand rows minus the discharge rows -- so a stored state would
+# row kinds -- `scope` is the demand rows minus the discharge rows -- so a stored state would
@@
-    def _append(self, row: dict) -> None:
-        prev = self._tail_hash()
+    def _append(self, row: dict, prev: str) -> None:
         row = dict(row)
@@
-    def _tail_hash(self) -> str:
-        last = ""
-        for row in self._rows():
-            last = row.get("hash", "")
-        return last
-
     def _rows(self):
@@ (after _rows)
+    def scope(self, session: str, agent: str):
+        """ONE pass over the file, answering every question this ledger has: the OPEN demand rows
+        by id, the ids a guard call has DISCHARGED, and the chain head the next row links to.
+
+        DEMAND, DISCHARGE AND OPEN ARE NOT THREE CONCEPTS. They are one set difference,
+        `demanded - discharged`, taken here and nowhere else -- and a licence is membership in
+        the second set and NOTHING else. Deliberately not "absent from the first": a demand that
+        was never raised is also not open, and reading that as a licence would let the costly act
+        through on the strength of nothing ever having happened.
+
+        SEVEN WALKS WERE ONE. `is_licensed`, `open_ids` and `open_demands` were three methods
+        over three walks, asked once PER CLAUSE, so a table of C clauses re-opened and re-parsed
+        an R-row file O(C*R) times per event; `demand` and `discharge` each read state and then
+        walked again for the tail hash; `open_demands` walked once for the ids and once for the
+        rows. Every one of those answers is a read of this single pass.
+
+        `.get` throughout: a row missing `id`, `session` or `kind` is malformed and skipped,
+        not a KeyError. First demand row per id wins; that IS the dedup.
+        """
+        demanded, closed, tail = {}, set(), ""
+        for row in self._rows():
+            tail = row.get("hash", "")
+            rid = row.get("id")
+            if rid is None or row.get("session") != session or row.get("agent") != agent:
+                continue
+            if row.get("kind") == "demand":
+                demanded.setdefault(rid, row)
+            elif row.get("kind") == "discharge":
+                closed.add(rid)
+        return {i: r for i, r in demanded.items() if i not in closed}, closed, tail
+
     def demand(self, d: Demand) -> bool:
         """Record a demand. Returns False if this exact demand is already open (idempotent)."""
-        if d.id in self.open_ids(d.session, d.agent):
+        open_rows, _, tail = self.scope(d.session, d.agent)
+        if d.id in open_rows:
             return False
-        self._append({"kind": "demand", **asdict(d)})
+        self._append({"kind": "demand", **asdict(d)}, tail)
         return True
@@ (discharge; the comment block above it is unchanged)
-        if self.is_licensed(session, agent, demand_id):
+        _, closed, tail = self.scope(session, agent)
+        if demand_id in closed:
             return
         self._append({"kind": "discharge", "session": session, "agent": agent,
-                      "id": demand_id, "how": how})
-
-    def is_licensed(self, session: str, agent: str, demand_id: str) -> bool:
-        """True once the guard call for this exact subject has been observed.
-
-        This is the whole point of the mechanism and it is deliberately NOT `demand_id not in
-        open_ids`: a demand that was never raised is also "not open", and treating that as a
-        licence would let the costly act through on the strength of nothing ever having happened.
-        Absence is not a licence; only an observed discharge is.
-        """
-        return any(
-            row.get("kind") == "discharge" and row.get("id") == demand_id
-            and row.get("session") == session and row.get("agent") == agent
-            for row in self._rows()
-        )
-
-    def open_ids(self, session: str, agent: str) -> set[str]:
-        opened, closed = set(), set()
-        for row in self._rows():
-            if row.get("session") != session or row.get("agent") != agent:
-                continue
-            rid = row.get("id")  # .get, like every other row access: a scoped demand row
-            if rid is None:      # missing "id" is a malformed row to skip, not a KeyError.
-                continue
-            if row.get("kind") == "demand":
-                opened.add(rid)
-            elif row.get("kind") == "discharge":
-                closed.add(rid)
-        return opened - closed
-
-    def open_demands(self, session: str, agent: str) -> list[dict]:
-        ids = self.open_ids(session, agent)  # a fresh set per call, so spending from it is safe
-        out = []
-        for row in self._rows():
-            rid = row.get("id")
-            if row.get("kind") == "demand" and rid in ids:
-                ids.discard(rid)  # first row per id wins; discarding it IS the dedup
-                out.append(row)
-        return out
+                      "id": demand_id, "how": how}, tail)

--- a/plugin/keel/dispatch.py
+++ b/plugin/keel/dispatch.py
@@ _open_effect_denial
-    open_rows = ledger.open_demands(session, agent)
+    open_rows = ledger.scope(session, agent)[0]
     if not open_rows:
         return None, False
@@
-    for row in open_rows:
+    for row in open_rows.values():
@@ pre_tool_use
     applicable = {id(cl) for cl in _applicable(table, event)}
+    # ONE LEDGER READ FOR THE WHOLE TABLE. Every clause below asks the same two questions of the
+    # same scope, and each answer used to cost its own walk of the file. Taken here, after the
+    # writes above and before the loop: a clause's id is derived from its own `cl.id`, so no
+    # clause's write can move another clause's answer.
+    open_rows, licensed, _ = ledger.scope(session, agent)
     for cl in table:
@@
-                if (C.classify_side(cl.fingerprint) != "effect"
-                        or did in ledger.open_ids(session, agent)):
+                if C.classify_side(cl.fingerprint) != "effect" or did in open_rows:
@@
-                if ledger.is_licensed(session, agent, did):
+                if did in licensed:
                     continue
@@ post_tool_use
     applicable = {id(cl) for cl in _applicable(table, event)}
+    open_rows, licensed, _ = ledger.scope(session, agent)  # one read; see `pre_tool_use`
@@
-                if not after_the_act or did in ledger.open_ids(session, agent):
+                if not after_the_act or did in open_rows:
@@
-                if not ledger.is_licensed(session, agent, did):
+                if did not in licensed:
@@
-        still = {row["clause_id"] for row in ledger.open_demands(session, agent)}
+        still = {row["clause_id"] for row in ledger.scope(session, agent)[0].values()}
@@ reconcile
-        open_rows = ledger.open_demands(session, agent)
+        open_rows, licensed, _ = ledger.scope(session, agent)
@@
-        # They need no synthetic session-wide standing row; open_demands above reconciles them.
+        # They need no synthetic session-wide standing row; the open rows above reconcile them.
@@
-        if cl.activated_by is not None and not ledger.is_licensed(
-                session, agent, derive_id(session, agent, cl.id, "activated")):
+        if cl.activated_by is not None and derive_id(
+                session, agent, cl.id, "activated") not in licensed:
             continue
-        did = derive_id(session, agent, cl.id, "standing")
-        if not ledger.is_licensed(session, agent, did):
+        if derive_id(session, agent, cl.id, "standing") not in licensed:
             undischarged.append({"clause_id": cl.id, "reason": cl.deny_reason})
@@
-    open_rows = list(open_rows) + undischarged
+    open_rows = list(open_rows.values()) + undischarged

TESTS CARRIED WITH THE CUT (rule 3 -- each merely names the old spelling of the thing cut, and is re-pointed at the new one; none is weakened):
--- a/tests/test_ledger_growth.py   (two mutation plants naming the discharge dedup guard by its exact bytes)
-                      b"        if self.is_licensed(session, agent, demand_id):\n            return\n",
+                      b"        if demand_id in closed:\n            return\n",
   (x2; both still assert the mutated run goes RED with "AssertionError: 2 != 22" / "rows for 40 identical guards")
-        self.assertNotIn(demand_id, ledger.open_ids("s", "a"))
+        self.assertNotIn(demand_id, ledger.scope("s", "a")[0])
--- a/tests/test_effects.py
-        return {row["clause_id"] for row in Ledger(self.state).open_demands("fx", "")}
+        return {row["clause_id"] for row in Ledger(self.state).scope("fx", "")[0].values()}
--- a/tests/test_bidirectional_chain.py   (plant seam in reconcile)
-            b"    open_rows = list(open_rows) + undischarged",
+            b"    open_rows = list(open_rows.values()) + undischarged",

## gate
cd /tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/simplify/ledger
$ python3 -m unittest discover -s tests 2>&1 | tail -3
Ran 246 tests in 217.545s

OK                                  (unittest_exit=0)
$ python3 eval/replay.py | tail -1
REPLAY sessions=26 passed=26 failed=0   (exit 0)
$ python3 tools/render_views.py --check
views match plugin/keel/clauses.json    (exit 0)
$ python3 tools/render_coverings.py --check
proofs/Clauses.v matches plugin/keel/clauses.json  (exit 0)
$ python3 tools/check_coq.py
COQ=PASS Clauses.v covers sides=51 of clauses=24: instantiated=36 empty-by-class[always=7 tool-enum=8] ; Coverings.v: results=16 axioms=0 parameters=16 ; Clauses.v: results=74 axioms=0 parameters=3  (exit 0)
$ python3 eval/generate_corpus.py --check
eval/corpus matches 26 specs            (exit 0)
$ git status --porcelain | wc -l
7   -- exactly the expected files: plugin/keel/{dispatch,journal,ledger,wire}.py and tests/{test_bidirectional_chain,test_effects,test_ledger_growth}.py

NOTE ON GATE FLAKINESS (not caused by this diff): tests/test_effects.TheObserverSeesTheWorld reads the HOST's global process table (`quiet = ... and not pids_spawned` in effects.delta). Sibling agents were running up to 18 concurrent `unittest discover` suites on this box; under that load report_ref/report_paths/net_read intermittently go False on both the pristine tree and this one (pristine also failed a run, on test_measured). The green run above was taken at load 1.4.

## complexity
MEASURED by wrapping Ledger._rows to count file walks and rows parsed, on a ledger holding 200 open demand rows (24-clause default table), timed with perf_counter:
                    BEFORE (walks/rows/us)   AFTER (walks/rows/us)
  open demands       2 / 400 / 1345          1 / 200 /  631   (2.1x)
  demand()           2 / 400 / 1358          1 / 200 /  791   (1.7x)
  reconcile()        6 / 1252 / 3778         2 / 403 / 1499   (2.5x)
  pre_tool_use()     9 / 1962 / 6712         5 / 1023 / 4486  (1.5x)
  post_tool_use()    7 / 1432 / 4805         4 /  820 / 3497  (1.4x)
Asymptotics: the per-event ledger cost was O(C*R) in clauses C and rows R (each clause's is_licensed/open_ids was its own full open+parse); it is now O(R) -- the residual walks are the writes (each discharge/demand is one pass) plus one snapshot.
EQUIVALENCE, not just green tests: 4 differential runs through the REAL hook binary (bash plugin/hooks/dispatch.sh / python -m keel.dispatch) against the pristine tree -- 52 hand-built events plus 3 randomized 246-event sessions (2 agent threads, 6 tool kinds, 17 command shapes, synthetic effect records) -- produced byte-identical verdicts AND byte-identical obligations.jsonl including every `prev`/`hash` chain field. 790 events, 0 divergences.

## verdict
{"id": "ledger-1", "refuted": false, "reason": "SURVIVES source-level attack. (a) The dispatch hoist is exact. Every demand id is derive_id(session, agent, cl.id, subject), and clause ids are unique -- clauses.json holds 24 ids, 24 distinct, and clauses.load_bundle ends in _unique_sorted -- so no clause's write inside a loop can move another clause's snapshot answer. In pre_tool_use the two branches are mutually exclusive (branch A ends in `continue`), and the snapshot is taken AFTER _watch_standing and _open_effect_denial, both of which write. In post_tool_use branch B writes only demand rows, which cannot change `licensed` (a discharge-row set) at all, and the post-loop `still` read is left fresh. reconcile's clause loop performs NO writes whatsoever, so hoisting there is trivially equivalent. (b) Message text is preserved byte-for-byte: `demanded.setdefault(rid, row)` inserts in file order with first-row-per-id winning, the comprehension preserves that order, so `open_rows.values()` yields exactly what `open_demands` returned as a list -- which matters because _open_effect_denial's `owed` order and reconcile's `lines` order are user-visible. (c) The fail-closed direction is intact: `closed` is built only from rows with kind=='discharge', never from 'absent from open', and the 'absence is not a licence' paragraph is carried verbatim into scope()'s docstring. (d) Fail direction on faults is HARDENED, not softened: reconcile's per-clause is_licensed reads move INSIDE the existing try that emits 'keel could not read its ledger ... NOT-EVALUABLE, not a pass', and pre_tool_use's ledger read moves out of the per-clause `except Exception: continue` (which is correct -- a whole-store fault swallowed 24 times is the exact defect wire.py was written against) into main's evaluation except, which for PreToolUse yields _closed_not_evaluable = deny. (e) The tail-hash read is now marginally earlier relative to the write, but the whole demand()/discharge() call is one walk instead of two, so the total read-to-write window SHRINKS; verify_chain is declared advisory and the pre-existing read-then-append TOCTOU is unchanged in kind. (f) Plants re-point equivalently: removing `if demand_id in closed:\\n            return\\n` leaves `_, closed, tail = self.scope(...)` followed by the unconditional _append, so 20 repeat discharges still write 20 rows and the target still fails '2 != 22'; the bidirectional seam `open_rows = list(open_rows.values()) + undischarged` mutates to `open_rows = undischarged` with identical effect. (g) I found only one behavioural narrowing and it is unreachable: old open_demands did NOT filter its second pass by session/agent, so a foreign-scope demand row sharing an id could be returned; derive_id embeds session and agent, so no production id can collide across scopes. (h) Only test_plant_recovery.py mentions `is_licensed` outside the changed set, and only inside a module docstring narrating history -- not a live seam -- so the 7-file chan
