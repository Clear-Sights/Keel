# EFF-11 [field] snap["tick"] and its `own_fields = _stat_fields(os.getpid())`
LOC 2 -> 0

## description
snapshot() read its own /proc/<pid>/stat line to store `tick` (the hook process's start time) in before.json. Grepping the whole repository for `tick` finds exactly one hit: the line that writes it. No reader in plugin/, tests/, eval/ or tools/ ever names it.

## diff
--- a/plugin/keel/effects.py
+++ b/plugin/keel/effects.py
@@ snapshot
-    own_fields = _stat_fields(os.getpid()) or []
@@
     snap: dict[str, Any] = {"t": time.time(), "cwd": cwd, "root": root,
                             "index": found[1] if found else None,
                             "tree": None, "walk": None, "refs": None, "session_root": session_root(),
-                            "tick": own_fields[_STARTTIME_AFTER_COMM] if len(own_fields) > _STARTTIME_AFTER_COMM else None,
                             "pids": None, "sids": None, "alive": None, "net": net_now,

## gate
Ran 244 tests in 196.393s / OK ; REPLAY sessions=26 passed=26 failed=0 ; views match plugin/keel/clauses.json ; proofs/Clauses.v matches plugin/keel/clauses.json ; COQ=PASS ; eval/corpus matches 26 specs ; git status --porcelain | wc -l = 26 ; chained exit=0

## complexity
One /proc/<pid>/stat read per snapshot removed, and one field per before.json write. Confirmed dead by `grep -rn 'tick' --include='*.py' .` returning only the write site.

## verdict
{"id": "EFF-11", "refuted": false, "reason": "STANDS -- the cleanest cut in the lane, and every claim in it checks out exactly. Built in re-runs/c11.\n\nDEAD CONFIRMED: grepping the WHOLE tree (not just *.py -- including README.md, docs/, proofs/*.v, MEASURED.tsv, OVERLAPS.tsv, eval/corpus and clauses.json) for `tick` returns exactly one line, the write site at effects.py:387. No reader anywhere. The value never leaves before.json, and before.json is read only by delta(), which never names it.\n\nCOMPLEXITY REAL AND EXACTLY AS CLAIMED. Counting stat reads whose pid is the hook's own process -- a figure that does not move with host load, unlike the raw total: base 9.0 own-pid /proc/<pid>/stat reads per act, c11 8.0. That is precisely the one `_stat_fields(os.getpid())` per snapshot the cut removes, and one field per before.json write.\n\nLOC: filed 2 -> 0 (-2); measured -2 non-blank non-comment. Exact.\n\nNothing to break: the removed value fed no predicate, no artifact and no test, and removing it cannot change any effect's value or evaluability.", "gate_output": "c11: Ran 245 tests OK ; REPLAY sessions=26 passed=26 failed=0 ; views match plugin/keel/clauses.json ; proofs/Clauses.v matches plugin/keel/clauses.json ; COQ=PASS Clauses.v covers sides=51 of clauses=24 ; Coverings.v: results=16 axioms=0 ; Clauses.v: results=72 axioms=0 ; eval/corpus matches 26 specs ; git status --porcelain | wc -l = 1 ; EXITS 0 0 0 0 0 0."}
