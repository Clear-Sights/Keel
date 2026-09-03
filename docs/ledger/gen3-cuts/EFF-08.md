# EFF-08 [time] assigned_process()
LOC 8 -> 7

## description
assigned_process(pid, before, in_tree) did `set(before.get('alive') or [])` and `set(before.get('sids') or [])` on EVERY call -- and it is called once per candidate pid inside delta's `spawned` comprehension over the whole host process table. `alive` is every pid on the host (thousands of entries on a real machine), so the predicate was O(host pids) per candidate, i.e. O(n^2) in the number of candidates. delta had ALREADY built `alive_then = set(before.get('alive') or [])` two lines above and thrown it away. The two sets are now built once, in delta, and passed in; the sid comes off the one /proc pass instead of a fresh read of the pid's stat line.

## diff
--- a/plugin/keel/effects.py
+++ b/plugin/keel/effects.py
-def assigned_process(pid: int, before: dict[str, Any], in_tree: dict[int, str]) -> bool:
+def assigned_process(pid: int, sid: int, in_tree: dict[int, str],
+                     sids_then: set[int], alive_then: set[int]) -> bool:
     if pid in in_tree:
         return True
-    sid = process_session(pid)
     if not sid:  # kernel threads carry session 0: no lineage, never this session's
         return False
-    alive = set(before.get("alive") or [])
-    return sid in set(before.get("sids") or []) or (bool(alive) and sid not in alive)
+    return sid in sids_then or (bool(alive_then) and sid not in alive_then)

@@ delta
-        alive_then = set(before.get("alive") or [])
+        # Both lineage sets are built ONCE: built inside the test they were rebuilt, whole, for
+        # every candidate pid.
+        alive_then, sids_then = set(before.get("alive") or []), set(before.get("sids") or [])
         spawned = sorted(
-            p for p, s in everyone.items()
+            p for p, (start, _, sid) in table.items()
             if p not in own
-            and (p not in alive_then or (str(p) in then and then[str(p)] != s))
-            and assigned_process(p, before, in_tree))
+            and (p not in alive_then or (str(p) in then and then[str(p)] != start))
+            and assigned_process(p, sid, in_tree, sids_then, alive_then))

## gate
Ran 244 tests in 196.393s / OK ; REPLAY sessions=26 passed=26 failed=0 ; views match plugin/keel/clauses.json ; proofs/Clauses.v matches plugin/keel/clauses.json ; COQ=PASS ; eval/corpus matches 26 specs ; git status --porcelain | wc -l = 26 ; chained exit=0

## complexity
Per candidate pid: 2 set constructions over `before['alive']` (host-wide pid list) + 1 /proc/<pid>/stat read -> 0. Cost of the spawned test goes from O(candidates x host pids) to O(candidates). On this 97-process host the harness shows the /proc read gone; on a host with thousands of processes the set rebuild is the dominant term. Semantics preserved exactly: the differential harness (32 acts) records identical pids_* fields when the assignment rule is exercised.

## verdict
{"id": "EFF-08", "refuted": false, "reason": "STANDS, jointly with EFF-04 -- as filed it CANNOT be applied alone either: its diff destructures `table.items()` into (start, _, sid), which is EFF-04's proc_table(). The two findings are one cut split across two rows; I built and gated them together in re-runs/c04 and the whole gate is green.\n\nTHE O(n^2) IS REAL, and I measured it rather than taking the argument. assigned_process built `set(before['alive'])` and `set(before['sids'])` on every call, inside delta's `spawned` comprehension. Timed at 2,000 repetitions with 10 candidate pids:\n  host with 150 pids: 0.0510 ms/act -> 0.0074 ms/act (6.9x)\n  host with 5,000 pids: 1.0919 ms/act -> 0.1462 ms/act (7.5x)\nPlus one /proc/<pid>/stat read per candidate removed (the sid now comes off the single walk) -- visible in own-pid reads/act 9 -> 6 for the pair. The cost of the spawned test goes from O(candidates x host pids) to O(candidates), and delta had genuinely already built the identical `alive_then` two lines above and thrown it away.\n\nSEMANTICS PRESERVED, including the direction. The one behavioural difference I could find: base called process_session(pid) fresh, so a pid that died between the walk and the check yielded None and was NOT assigned; the cut uses the sid captured during the walk and DOES assign it. That is more pids_spawned, i.e. more live occasions -- fail closed. The kernel-thread guard (`if not sid: return False`, session 0 has no lineage) is preserved verbatim, and the setsid-worker plant (a real daemonized process reparented out of the tree) is still assigned by both builds.\n\nLOC: filed 8 -> 7 (-1); the pair measures -7 across effects.py, so this row's share is about -1. Accurate.", "gate_output": "c04 (EFF-08 with EFF-04, which it requires): Ran 245 tests OK ; REPLAY sessions=26 passed=26 failed=0 ; views match plugin/keel/clauses.json ; proofs/Clauses.v matches plugin/keel/clauses.json ; COQ=PASS Clauses.v covers sides=51 of clauses=24 ; Coverings.v: results=16 axioms=0 ; Clauses.v: results=72 axioms=0 ; eval/corpus matches 26 specs ; git status --porcelain | wc -l = 2 ; EXITS 0 0 0 0 0 0."}
