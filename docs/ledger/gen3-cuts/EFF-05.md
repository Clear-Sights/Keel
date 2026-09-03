# EFF-05 [space] trace_effects()'s report_paths block
LOC 13 -> 8

## description
To decide `did this act print a path the worktree snapshot holds`, the observer materialised `held` -- every path in the tree, plus every basename, plus EVERY directory prefix of every path -- and then asked whether any of the act's ~10 output tokens was in it. That is one set entry per path segment in the repository, rebuilt on every act, to answer a question about ten tokens; and it was built even when the act was loud, where the answer is False regardless. Turned around, the set is the tokens' (2 entries per token), the scan runs over the ls-tree output and stops at the first path that answers. The predicate is provably the same: `exists t: t' in held or basename(t) in held` <=> `exists p: ({p} u {basename(p)} u prefixes(p)) n wanted != {}`.

## diff
--- a/plugin/keel/effects.py
+++ b/plugin/keel/effects.py
     if paths is not None:
-        held = set()
-        for path in paths:
-            if not path:
-                continue
-            held.add(path)
-            held.add(path.rsplit("/", 1)[-1])
-            parts = path.split("/")
-            for i in range(1, len(parts)):
-                held.add("/".join(parts[:i]))
-        out["report_paths"] = quiet and any(
-            t.removeprefix("./").rstrip("/") in held or t.rsplit("/", 1)[-1] in held for t in tokens)
+        # THE SMALL SIDE IS THE TOKENS. An act's output names a few paths; the tree holds every
+        # file in the repository. Unfolding the tree into a set of every path, every basename
+        # and every directory prefix held one entry per path segment in the repository, per act,
+        # to answer a question about a handful of tokens. Asked the other way round the set is
+        # the tokens', and the scan stops at the first path that answers.
+        wanted = ({t.removeprefix("./").rstrip("/") for t in tokens}
+                  | {t.rsplit("/", 1)[-1] for t in tokens})
+        out["report_paths"] = quiet and any(
+            path and (path in wanted or path.rsplit("/", 1)[-1] in wanted
+                      or any(path[:i] in wanted for i, c in enumerate(path) if c == "/"))
+            for path in paths)

## gate
Ran 244 tests in 196.393s / OK ; REPLAY sessions=26 passed=26 failed=0 ; views match plugin/keel/clauses.json ; proofs/Clauses.v matches plugin/keel/clauses.json ; COQ=PASS ; eval/corpus matches 26 specs ; git status --porcelain | wc -l = 26 ; chained exit=0

## complexity
Both spellings run on the same synthetic listing under tracemalloc. 20 000 files, depth 5, a matching token: set entries 83 650 -> 10, peak 9 790.2 KiB -> 2.2 KiB, time 376.5 ms -> 0.042 ms. Same tree, NO matching token (worst case, no early exit): entries 83 650 -> 12, peak 9 790.2 KiB -> 3.2 KiB, time 306.4 ms -> 133.8 ms. 200 files: 850 -> 10 entries, 69.0 KiB -> 2.2 KiB, 1.92 ms -> 0.029 ms. Space goes from O(path segments in the repository) to O(tokens in one act's output).

## verdict
{"id": "EFF-05", "refuted": false, "reason": "STANDS -- the strongest finding in the lane. Built in re-runs/c05.\n\nEQUIVALENCE PROVEN BY FUZZING, not by the algebra in the filing. I ran the old and new predicates against each other on 300,000 random (paths, tokens) pairs drawn from an alphabet chosen to hit every edge the rewrite could plausibly get wrong -- './' prefixes, trailing slashes, LEADING slashes (where the new `path[:i]` prefix scan can produce the empty string), empty paths, empty tokens, and bare '/'. 0 mismatches. I then ran the live functions: 120 trace_effects scenarios (exact path, basename, directory prefix, './'-prefixed, absent, trailing-slash, ref names, abbreviated shas, pid listings, self-listing output) x quiet=True/False x three commands, base vs cut: 0 differences on report_ref, report_paths, report_pids and report_listing together.\n\nSPACE REAL AND LARGE, measured under tracemalloc on the same synthetic listing:\n  20,000 files / depth 5 / matching token: set entries 66,631 -> 9, peak 4,755.5 KiB -> 2.2 KiB, 407.8 ms -> 0.042 ms\n  20,000 files, NO matching token (worst case, no early exit): 66,631 -> 5 entries, 4,755.3 KiB -> 2.4 KiB, 477.9 ms -> 197.8 ms\n  200 files: 979 -> 9 entries, 77.2 KiB -> 2.2 KiB, 6.23 ms -> 0.033 ms\nMy absolute numbers differ from the filing's because my synthetic tree has a different shape, but the shape of the result is theirs: space goes from O(path segments in the repository) to O(tokens in one act's output), and even the no-early-exit case more than halves the time.\n\nLOC: filed 13 -> 8 (-5); measured -5 non-blank non-comment. Exact. No fail-closed direction touched -- `quiet and ...` still short-circuits, and the predicate is the same function of the same inputs.", "gate_output": "c05: Ran 245 tests OK ; REPLAY sessions=26 passed=26 failed=0 ; views match plugin/keel/clauses.json ; proofs/Clauses.v matches plugin/keel/clauses.json ; COQ=PASS Clauses.v covers sides=51 of clauses=24 ; Coverings.v: results=16 axioms=0 ; Clauses.v: results=72 axioms=0 ; eval/corpus matches 26 specs ; git status --porcelain | wc -l = 1 ; EXITS 0 0 0 0 0 0."}
