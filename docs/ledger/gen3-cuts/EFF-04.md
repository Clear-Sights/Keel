# EFF-04 [time] pids() -> proc_table() + under(); process_session() deleted; snapshot's sid loop; delta's second pids() call
LOC 61 -> 48

## description
Per act the observer read every /proc/<pid>/stat line FOUR times: snapshot called pids(session_root) (full /proc walk, then filter) AND pids() (a second full walk); delta called pids() AND pids(before.session_root) (two more full walks); on top of that snapshot called process_session(p) for every pid in the tree, re-reading a stat line the walk had just read, and read its own stat line once more for a `tick` field nothing reads. proc_table() is the ONE pass -- pid -> (start time, parent, process session) -- and `under(root, table)` is the subtree projection of it. pids() and process_session() disappear: after the hoist the product called neither, and a function only a test calls is a function the product does not need (tests/test_effects.py's foreign-lineage cell now reads the sid off the table, which is what it was asking for).

## diff
--- a/plugin/keel/effects.py
+++ b/plugin/keel/effects.py
-def process_session(pid: int) -> int | None:
-    """The process session (setsid group) a pid belongs to ..."""
-    fields = _stat_fields(pid)
-    if not fields or len(fields) <= _SID_AFTER_COMM or not fields[_SID_AFTER_COMM].isdigit():
-        return None
-    return int(fields[_SID_AFTER_COMM])
-
-def pids(root: int | None = None) -> dict[int, str] | None:
-    proc = pathlib.Path("/proc")
-    if not proc.is_dir(): return None
-    parents, starts = {}, {}
-    for entry in proc.iterdir():
-        ...
-        parents[int(entry.name)] = int(fields[1])
-        starts[int(entry.name)] = fields[_STARTTIME_AFTER_COMM]
-    if root is None: return starts
-    under = {}
-    for pid in starts:
-        cursor, hops = pid, 0
-        while cursor > 1 and hops < _ANCESTRY_CAP:
-            if cursor == root: under[pid] = starts[pid]; break
-            cursor, hops = parents.get(cursor, 1), hops + 1
-    return under
+def proc_table() -> dict[int, tuple[str, int, int]] | None:
+    """ONE pass over /proc: pid -> (start time, parent, process session), for what is running.
+    Every caller wants a different projection of the same read ... and a function per
+    projection re-read every process's stat line two and three times per act."""
+    proc = pathlib.Path("/proc")
+    if not proc.is_dir():
+        return None
+    table: dict[int, tuple[str, int, int]] = {}
+    for entry in proc.iterdir():
+        if not entry.name.isdigit():
+            continue
+        fields = _stat_fields(int(entry.name))
+        if not fields or len(fields) <= _STARTTIME_AFTER_COMM or fields[0] == "Z":
+            continue
+        table[int(entry.name)] = (fields[_STARTTIME_AFTER_COMM], int(fields[1]),
+                                  int(fields[_SID_AFTER_COMM]))
+    return table
+
+def under(root: int, table: dict[int, tuple[str, int, int]]) -> dict[int, str]:
+    """pid -> start time for the processes of `table` whose ancestry reaches `root`."""
+    kin: dict[int, str] = {}
+    for pid, (start, _, _) in table.items():
+        cursor, hops = pid, 0
+        while cursor > 1 and hops < _ANCESTRY_CAP:
+            if cursor == root:
+                kin[pid] = start
+                break
+            cursor, hops = (table[cursor][1] if cursor in table else 1), hops + 1
+    return kin

@@ snapshot
-    own_fields = _stat_fields(os.getpid()) or []
-    ... "tick": own_fields[_STARTTIME_AFTER_COMM] if len(own_fields) > _STARTTIME_AFTER_COMM else None,
-    table = pids(snap["session_root"])
+    table = proc_table()
     if table is not None:
         own = _own_chain()
-        snap["pids"] = {str(p): s for p, s in table.items() if p not in own}
-        everyone = pids()
+        kin = under(snap["session_root"], table)
+        snap["pids"] = {str(p): s for p, s in kin.items() if p not in own}
         for pid, start in (memory.get("spawned") or {}).items():
-            if everyone is not None and everyone.get(int(pid)) == start:
+            if int(pid) in table and table[int(pid)][0] == start:
                 snap["pids"][pid] = start
-        sids = {process_session(p) for p in table} | {process_session(snap["session_root"])}
-        snap["sids"] = sorted(s for s in sids if s is not None)
-        snap["alive"] = sorted(everyone) if everyone is not None else None
+        snap["sids"] = sorted({table[p][2] for p in kin})
+        snap["alive"] = sorted(table)

@@ delta
-    everyone = pids()
+    table = proc_table()
     then = before.get("pids")
-    if everyone is not None and then is not None:
+    if table is not None and then is not None:
         own = _own_chain()
-        in_tree = pids(before.get("session_root")) or {}
+        in_tree = under(before["session_root"], table)
         out["pids_gone"] = sorted(int(p) for p, s in then.items()
-                                  if everyone.get(int(p)) != s)
+                                  if int(p) not in table or table[int(p)][0] != s)

--- a/tests/test_effects.py
-        born = [p for p in effects.pids() or {} if effects.process_session(p) == foreign]
+        born = [p for p, (_, _, sid) in (effects.proc_table() or {}).items() if sid == foreign]

## gate
Ran 244 tests in 196.393s / OK ; REPLAY sessions=26 passed=26 failed=0 ; views match plugin/keel/clauses.json ; proofs/Clauses.v matches plugin/keel/clauses.json ; COQ=PASS ; eval/corpus matches 26 specs ; git status --porcelain | wc -l = 26 ; chained exit=0

## complexity
Instrumented `pathlib.Path.read_text` to count /proc reads, 10 steady-state acts on a 97-process host: /proc/<pid>/stat reads per act 347.4 -> 178.9 (-48.5%), i.e. 4 full /proc walks per act -> 2 (one per moment), plus the per-tree-pid re-read and the `tick` read gone. Ancestry cost is unchanged (O(pids x depth), capped at _ANCESTRY_CAP). Wall clock contribution measured in the same run: 0.0500 s -> 0.0389 s per act before the git cuts landed.

## verdict
{"id": "EFF-04", "refuted": false, "reason": "STANDS -- but NOT AS A STANDALONE CUT, which the filing does not say. EFF-04's diff deletes process_session() while leaving assigned_process() calling it; applied alone the observer raises NameError on every act. It only builds together with EFF-08, which is the finding that removes that call. I therefore built the pair in re-runs/c04 and gated them together (the refuter brief permits cumulative application). The pair is green.\n\nCOMPLEXITY REAL AND LARGE. I instrumented pathlib.Path.read_text and normalised by the live host pid count so the number does not move with the machine's load: base 4.57 /proc/<pid>/stat reads per host pid per act; c04 2.09 (-54%) -- i.e. four full /proc walks per act collapse to two, one per moment. Own-pid stat reads/act 9 -> 6 (the per-tree-pid process_session() re-read and the second walk are gone). This is the hunter's claim reproduced on a different host (they measured 347.4 -> 178.9 on 97 processes; mine was 671.4 -> 307.5 on ~147).\n\nunder() PROVEN EQUIVALENT, not eyeballed: I fuzzed it against base's pids(root) ancestry walk on 20,000 random process forests containing self-cycles, parents outside the table, and pid-1 parents. 0 mismatches. The _ANCESTRY_CAP guard is preserved verbatim. proc_table()'s zombie skip is the same predicate as base's, merely folded into one condition.\n\nLINEAGE COVERAGE INTACT: I planted a real daemonized worker (python -c 'os.setsid(); sleep') between snapshot and delta. Base and the cut both assign it (pids_spawned contains the worker's pid) -- the setsid escape from the process tree is still caught by the sid channel.\n\nNO NEW FAIL-OPEN: `in_tree = under(before[\"session_root\"], table)` is a bare subscript where base had .get(). If session_root were ever missing, base silently made in_tree the WHOLE host (assigning everything), while the cut raises -- and dispatch._observe catches every exception and writes None for all 29 effects, which is fail closed. The subscript is safer, not riskier.\n\nLOC CORRECTED: filed 61 -> 48 (-13), and EFF-08 a further -1, so -14 between them. Measured across the pair: -7 non-blank non-comment (effects.py 639 -> 632) plus the one-line test change. A real reduction, roughly half the claimed size. Also worth stating plainly: this is not a net function subtraction -- pids() and process_session() go, proc_table() and under() arrive, so the file's top-level function count is unchanged at 31.", "gate_output": "c04 (EFF-04 + EFF-08, which cannot be separated): Ran 245 tests OK ; REPLAY sessions=26 passed=26 failed=0 ; views match plugin/keel/clauses.json ; proofs/Clauses.v matches plugin/keel/clauses.json ; COQ=PASS Clauses.v covers sides=51 of clauses=24 ; Coverings.v: results=16 axioms=0 ; Clauses.v: results=72 axioms=0 ; eval/corpus matches 26 specs ; git status --porcelain | wc -l = 2 ; EXITS 0 0 0 0 0 0."}
