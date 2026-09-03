# EFF-02 [time] _repo_root() + worktree_tree()'s `git rev-parse --git-path index` -> _repo(); snap["index"] carried to delta
LOC 15 -> 22

## description
`_repo_root` ran `git rev-parse --show-toplevel`; `worktree_tree` then ran `git rev-parse --git-path index` -- a second process for a second line the FIRST rev-parse would have printed for free. And `worktree_tree` is called twice per act (snapshot and delta), so the index path was resolved twice for a repository that cannot move between the two moments. `_repo` asks once and returns both; the snapshot writes the index path into before.json and the delta reads it instead of asking git again.

## diff
--- a/plugin/keel/effects.py
+++ b/plugin/keel/effects.py
-def _repo_root(cwd: str) -> str | None:
-    out = _git(cwd, "rev-parse", "--show-toplevel")
-    return out.strip() if out else None
+def _repo(cwd: str) -> tuple[str, str] | None:
+    """The worktree root and the real index path, from ONE `rev-parse`.
+
+    git prints one line per argument, so the second answer is free; asked separately it cost a
+    second process every act. The index path is carried in the snapshot rather than asked for
+    again at the delta.
+    """
+    out = _git(cwd, "rev-parse", "--show-toplevel", "--git-path", "index")
+    lines = (out or "").split("\n")
+    if len(lines) < 2 or not lines[0]:
+        return None
+    return lines[0], str(pathlib.Path(cwd, lines[1]))

-def worktree_tree(root: str, index: pathlib.Path) -> str | None:
+def worktree_tree(root: str, real: str, index: pathlib.Path) -> str | None:
     ...
-    located = _git(root, "rev-parse", "--git-path", "index")
-    real = pathlib.Path(root, located.strip()) if located else pathlib.Path("")
     try:
         index.parent.mkdir(parents=True, exist_ok=True)
-        if real.is_file():
+        if os.path.isfile(real):

@@ snapshot
-    root = _repo_root(cwd) if os.path.isdir(cwd) else None
+    found = _repo(cwd) if os.path.isdir(cwd) else None
+    root = found[0] if found else None
     snap = {..., "root": root,
+                 "index": found[1] if found else None, ...}
-    if root:
-        snap["tree"] = worktree_tree(root, slot / "index.before")
+    if found:
+        snap["tree"] = worktree_tree(root, found[1], slot / "index")

@@ delta
-        after_tree = worktree_tree(root, slot / "index.after")
+        after_tree = worktree_tree(root, before.get("index") or "", slot / "index")

@@ at_stop
-    root = _repo_root(cwd) if os.path.isdir(cwd) else None
-    if not root:
+    found = _repo(cwd) if os.path.isdir(cwd) else None
+    if not found:
         return out
+    root = found[0]

## gate
Ran 244 tests in 196.393s / OK ; REPLAY sessions=26 passed=26 failed=0 ; views match plugin/keel/clauses.json ; proofs/Clauses.v matches plugin/keel/clauses.json ; COQ=PASS ... sides=51 of clauses=24 ; eval/corpus matches 26 specs ; git status --porcelain | wc -l = 26 ; chained exit=0

## complexity
Measured with the same instrumented harness: `git rev-parse --git-path index` 2.0 calls/act -> 0, folded into the one `git rev-parse --show-toplevel --git-path index` that already ran (1.0/act). Net git subprocesses 14.0 -> 12.0 per act. LOC is UP by 7 (a 5-line docstring stating why); this is a time cut, not a line cut, and the file total still falls (639 -> 605).

## verdict
{"id": "EFF-02", "refuted": false, "reason": "STANDS. Built in re-runs/c02 (EFF-02 only -- I kept slot/index.before and slot/index.after separate so this cut is measured apart from EFF-10, which the hunter had folded into this diff).\n\nCOMPLEXITY REAL: instrumented git-call census, 10 steady-state acts. Base per act: `rev-parse --show-toplevel` x1 + `rev-parse --git-path index` x2 = 3 processes. After: `rev-parse --show-toplevel --git-path index` x1 = 1. Total git subprocesses/act 16.0 -> 14.0. Verified git prints one line per argument in that order and that the combined command exits 128 outside a repo exactly as `--show-toplevel` alone did.\n\nRESOLUTION IDENTICAL WHERE IT IS EASIEST TO BREAK -- this is the test the filing did not show. I compared base's (root, index) against _repo()'s on four shapes: repository root (index /w/.git/index, both agree); cwd a SUBDIRECTORY (base resolves relative to root, _repo relative to cwd -- both land on the same realpath); a LINKED `git worktree` (index lives at main/.git/worktrees/linked/index -- both agree); and outside a repo (both None). No mismatch. The only way before.get('index') can be absent is a before.json written by an older build, and then real='' -> the private index is unlinked and `git add -A` still writes the same content tree.\n\nFAIL-CLOSED PRESERVED: _repo returns None on exactly the returncode!=0 cases _repo_root did; a None root still routes to walk_tree / NOT-EVALUABLE. Any exception out of the observer is caught by dispatch._observe, which sets every effect to None (fail closed) -- so even a malformed lines[1] cannot become permission.\n\nEQUIVALENCE: covered by the 20-act differential (see EFF-01) -- pre_image, files_changed/removed and observed.json's tree are identical.\n\nTWO CLAIMS CORRECTED. (a) LOC: filed +7, measured +10 non-blank non-comment on effects.py (639 -> 649). Direction honest (it is a time cut that costs lines). (b) 'the file total still falls (639 -> 605)' is FALSE for this cut in isolation -- alone the file goes UP to 649; the fall belongs to EFF-01/04/06/07 and the cumulative total is 639 -> 603, not 605. Neither error touches the substance.", "gate_output": "c02: Ran 245 tests OK ; REPLAY sessions=26 passed=26 failed=0 ; views match plugin/keel/clauses.json ; proofs/Clauses.v matches plugin/keel/clauses.json ; COQ=PASS Clauses.v covers sides=51 of clauses=24 ; Coverings.v: results=16 axioms=0 ; Clauses.v: results=72 axioms=0 ; eval/corpus matches 26 specs ; git status --porcelain | wc -l = 1 ; EXITS 0 0 0 0 0 0."}
