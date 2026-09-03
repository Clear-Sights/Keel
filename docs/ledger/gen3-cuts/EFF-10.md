# EFF-10 [space] slot/index.before and slot/index.after
LOC 3 -> 2

## description
The private index the observer builds the worktree tree through was written to `index.before` at PreToolUse and `index.after` at PostToolUse -- two copies of the repository index per slot on disk, permanently. Nothing ever reads index.before again after write-tree: the pre-image lives in the object store, which is the entire point of the private-index construction. One path, `slot/index`, serves both moments.

## diff
--- a/plugin/keel/effects.py
+++ b/plugin/keel/effects.py
@@ snapshot
-        snap["tree"] = worktree_tree(root, slot / "index.before")
+        snap["tree"] = worktree_tree(root, found[1], slot / "index")
@@ observe (folded into snapshot by EFF-06)
-        snap["tree"] = worktree_tree(root, slot / "index.before")
@@ delta
-        after_tree = worktree_tree(root, slot / "index.after")
+        after_tree = worktree_tree(root, before.get("index") or "", slot / "index")

## gate
Ran 244 tests in 196.393s / OK ; REPLAY sessions=26 passed=26 failed=0 ; views match plugin/keel/clauses.json ; proofs/Clauses.v matches plugin/keel/clauses.json ; COQ=PASS ; eval/corpus matches 26 specs ; git status --porcelain | wc -l = 26 ; chained exit=0

## complexity
One copy of the repository index per slot instead of two -- on this checkout `.git/index` is 34 KiB, so 34 KiB of state dir per (session, agent) slot reclaimed, scaling with repository size. test_effects.py::test_a_rewrite_is_seen_and_its_pre_image_is_recoverable and ::test_an_untracked_file_removed_is_seen_with_its_pre_image still recover the pre-image with `git show <pre_image>:<path>`, which is the property the two files were suspected of carrying.

## verdict
{"id": "EFF-10", "refuted": false, "reason": "STANDS. Built in re-runs/c10 as the pure rename (slot/'index.before' x2 and slot/'index.after' x1 -> slot/'index'), separated from EFF-02 which had swallowed it.\n\nSPACE CLAIM MEASURED, not asserted. On a 300-file scratch repository, after SessionStart + one act, the slot holds:\n  base: ['index.after', 'index.before', 'session.json'], 2 index copies, 43,334 bytes\n  cut:  ['index', 'session.json'],                      1 index copy,  21,667 bytes\nExactly halved, and it scales with repository size as claimed.\n\nTHE PROPERTY THE TWO FILES WERE SUSPECTED OF CARRYING IS INTACT -- planted and checked. After an act that rewrote a tracked file and deleted an untracked one, `git show <pre_image>:a.txt` still returns 'one\\n' and `git show <pre_image>:u.txt` still returns 'untracked\\n' on both builds. No stale-index reuse is possible: worktree_tree copies the real index over the path before every `add -A`, or unlinks it when there is no real index, so the second moment never reads the first moment's leftovers.\n\nONE CAVEAT (reported, not refuting). Base kept the two moments on different paths, so a PostToolUse of act A and a PreToolUse of act B could not collide on the index file; they now can. But the slot is ALREADY single-act by construction -- before.json is one path shared by both moments, so two concurrent acts in one (session, agent) slot already destroy each other's pre-image. This cut does not create the serial-only assumption, it just stops paying for a second copy under it. And the collision that could occur fails closed: git's index.lock makes the loser's `add -A` exit non-zero, _git returns None, worktree_tree returns None, tree is None, NOT-EVALUABLE.\n\nLOC CORRECTED: filed 3 -> 2 (-1). Measured 0 -- it is a rename, and the -1 the hunter counted is EFF-06's deletion of observe()'s copy of the line, not this cut's. The value here is space, and the space is real.", "gate_output": "c10: Ran 245 tests OK ; REPLAY sessions=26 passed=26 failed=0 ; views match plugin/keel/clauses.json ; proofs/Clauses.v matches plugin/keel/clauses.json ; COQ=PASS Clauses.v covers sides=51 of clauses=24 ; Coverings.v: results=16 axioms=0 ; Clauses.v: results=72 axioms=0 ; eval/corpus matches 26 specs ; git status --porcelain | wc -l = 1 ; EXITS 0 0 0 0 0 0."}
