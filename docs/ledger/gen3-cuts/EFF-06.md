# EFF-06 [replication] observe()
LOC 22 -> 2

## description
observe() (session start) was a 21-line re-spelling of snapshot(): resolve the repo root, build the worktree tree through a private index, read the refs, measure the remote once, else walk the tree, read the process table, drop the own-chain, write observed.json. Every one of those rules already lives in snapshot(); the ONLY difference is that observe must not leave a before.json, because a snapshot left there would let a PostToolUse with no PreToolUse report a clean act instead of NOT-EVALUABLE. That difference is one boolean. Note the drift the duplication had already produced: observe()'s remote measurement had no REMOTE_RETRY_S gate while snapshot()'s did -- one rule, two spellings, already diverging.

## diff
--- a/plugin/keel/effects.py
+++ b/plugin/keel/effects.py
-def snapshot(state, session, agent, cwd) -> dict[str, Any]:
-    """Record the world before the act. Written under the state dir for `delta` to read."""
+def snapshot(state, session, agent, cwd, opens_act: bool = True) -> dict[str, Any]:
+    """Record the world before the act. Written under the state dir for `delta` to read.
+
+    `opens_act=False` is the session start: the SAME measurement, written for the operator to
+    Read, leaving no pre-image behind -- there is no act for a `delta` to describe yet, and a
+    snapshot left there would let a PostToolUse with no PreToolUse report a clean act instead
+    of NOT-EVALUABLE.
+    """
@@ end of snapshot
-    (slot / "before.json").write_text(json.dumps(snap), encoding="utf-8")
+    if opens_act:
+        (slot / "before.json").write_text(json.dumps(snap), encoding="utf-8")
     write_observed(state, root, snap)
     return snap

 def observe(state, session, agent, cwd) -> None:
     """Write the artifacts without opening an act: the session start, before anything runs."""
-    slot = _slot(state, session, agent)
-    slot.mkdir(parents=True, exist_ok=True)
-    root = _repo_root(cwd) if os.path.isdir(cwd) else None
-    snap = {"t": time.time(), "tree": None, "refs": None, "walk": None, "pids": None}
-    if root:
-        snap["tree"] = worktree_tree(root, slot / "index.before")
-        snap["refs"] = refs(root)
-        memory = _memory(slot)
-        if not memory.get("remote_measured"):
-            memory["remote_measured"] = observe_remote(state, root) is not None
-            memory["remote_tried"] = time.time()
-            memory["net_after"] = net_active_opens()
-            _remember(slot, memory)
-    elif os.path.isdir(cwd):
-        snap["walk"] = walk_tree(cwd)
-    table = pids(session_root())
-    if table is not None:
-        snap["pids"] = {str(p): s for p, s in table.items() if p not in _own_chain()}
-    write_observed(state, root, snap)
+    snapshot(state, session, agent, cwd, opens_act=False)

## gate
Ran 244 tests in 196.393s / OK ; REPLAY sessions=26 passed=26 failed=0 ; views match plugin/keel/clauses.json ; proofs/Clauses.v matches plugin/keel/clauses.json ; COQ=PASS ; eval/corpus matches 26 specs ; git status --porcelain | wc -l = 26 ; chained exit=0

## complexity
Not a hot-path cut (observe runs once, at SessionStart) -- it is a replication cut: 20 lines of duplicated measurement removed, and the two spellings of the remote-measurement rule (one gated by REMOTE_RETRY_S, one not) collapse to the gated one. Verified in the differential harness: observed.json and remote.json written by observe() are byte-identical before and after, and `(slot/'before.json').exists()` is False after observe() in both.

## verdict
{"id": "EFF-06", "refuted": false, "reason": "STANDS. Built in re-runs/c06.\n\nTHE ONE THING THAT MUST NOT BREAK, PLANTED AND CHECKED: after observe(), (slot/'before.json').exists() is False in base and False after the cut; and a PostToolUse delivered with no PreToolUse still returns not_evaluable='no pre-act snapshot' in both. The `opens_act` boolean carries exactly the difference the hunter claims and nothing else.\n\nARTIFACT IDENTICAL: observed.json written by observe() compared field by field, base vs cut, on (a) a repository -- identical including head, branch, tree, dirty, refs; (b) a plain directory outside any repository -- identical including the walked `paths` list (the only field that moved was `pids`, and only because the two runs sampled /proc at different instants -- the cumulative build, sampled closer together, came out byte-identical); (c) a cwd that does not exist -- both return the same all-null document without raising. remote.json is written in both.\n\nTHE DRIFT THE HUNTER NAMES IS REAL: base's observe() measured the remote with no REMOTE_RETRY_S gate while snapshot()'s copy had one. Collapsing onto snapshot() keeps the GATED spelling, which is the stricter of the two; at SessionStart memory is empty so remote_tried defaults to 0 and the gate passes, so the first measurement still happens -- test_the_operator_reads_keels_own_measurement (which asserts remote.json exists after observe()) passes.\n\nLOC CORRECTED: filed 22 -> 2 (-20). That counts only the deleted observe() body and ignores the nine lines added to snapshot() (the six-line docstring and the `if opens_act:` guard). Measured across the file: -11 non-blank non-comment (639 -> 628). Still a real subtraction, about half the advertised size.", "gate_output": "c06: Ran 245 tests OK ; REPLAY sessions=26 passed=26 failed=0 ; views match plugin/keel/clauses.json ; proofs/Clauses.v matches plugin/keel/clauses.json ; COQ=PASS Clauses.v covers sides=51 of clauses=24 ; Coverings.v: results=16 axioms=0 ; Clauses.v: results=72 axioms=0 ; eval/corpus matches 26 specs ; git status --porcelain | wc -l = 1 ; EXITS 0 0 0 0 0 0."}
