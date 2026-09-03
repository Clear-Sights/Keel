# EFF-03 [time] refs()
LOC 12 -> 18

## description
refs() is called once in snapshot and once in delta, so its two subprocesses were four per act. `git show-ref --head` is the single command that lists HEAD together with every ref, in the same (sha, name) form. The one behavioural difference is a repository with NO refs at all (unborn HEAD, `git init` with no commit): show-ref exits non-zero, so refs() returns None -- NOT-EVALUABLE, which the dispatcher treats as the occasion being LIVE. That is the fail-closed direction (previously such a repo reported HEAD="" and a comparable ref table, i.e. an answer), so no stated limit is softened.

## diff
--- a/plugin/keel/effects.py
+++ b/plugin/keel/effects.py
 def refs(root: str) -> dict[str, str] | None:
-    out = _git(root, "for-each-ref", "--format=%(refname) %(objectname)")
+    """Every ref AND HEAD, from ONE reading of the ref store.
+
+    `for-each-ref` cannot report HEAD, so the pair cost two processes for one reading -- twice
+    per act, since the delta reads the store again. `show-ref --head` is that one reading. A
+    repository with no refs at all makes it exit non-zero, and an unborn HEAD is a ref store
+    this observer cannot compare against: None, NOT-EVALUABLE, which the dispatcher treats as
+    the occasion being live.
+    """
+    out = _git(root, "show-ref", "--head")
     if out is None:
         return None
     table: dict[str, str] = {}
     for line in out.splitlines():
-        name, _, sha = line.partition(" ")
+        sha, _, name = line.partition(" ")
         if name and sha:
             table[name] = sha
-    head = _git(root, "rev-parse", "--verify", "-q", "HEAD")
-    table["HEAD"] = head.strip() if head else ""
+    table.setdefault("HEAD", "")
     return table

## gate
Ran 244 tests in 196.393s / OK ; REPLAY sessions=26 passed=26 failed=0 ; views match plugin/keel/clauses.json ; proofs/Clauses.v matches plugin/keel/clauses.json ; COQ=PASS ... results=72 axioms=0 ; eval/corpus matches 26 specs ; git status --porcelain | wc -l = 26 ; chained exit=0

## complexity
Instrumented harness, 10 steady-state acts: `git for-each-ref` 2.0/act + `git rev-parse --verify -q HEAD` 2.0/act -> `git show-ref --head` 2.0/act. Net git subprocesses 12.0 -> 10.0 per act. Cumulative with EFF-01/EFF-02: 16.0 -> 10.0 git subprocesses per act (-37.5%); wall clock per act 0.0500 s -> 0.0302 s (-40%), same harness, same host. Ref tables verified identical on a repo with branches, a tag, a remote-tracking ref and a detached checkout.

## verdict
{"id": "EFF-03", "refuted": false, "reason": "STANDS. Built in re-runs/c03.\n\nCOMPLEXITY REAL: `git for-each-ref` x2/act + `git rev-parse --verify -q HEAD` x2/act -> `git show-ref --head` x2/act. Total git subprocesses/act 16.0 -> 14.0, measured on the instrumented harness.\n\nTABLE EQUIVALENCE MEASURED, not argued: I ran base refs() and cut refs() side by side on a repo with two branches, an annotated tag, a remote-tracking ref and a detached HEAD; on a bare repo; outside a repository; and on a fresh `git init` with no commit. IDENTICAL on all but the last.\n\nTHE ONE DIFFERENCE, AND ITS DIRECTION. Unborn HEAD with no refs at all: base returned {'HEAD': ''}; the cut returns None. I drove that repo end to end. head_moved False -> None, remote_ref_moved [] -> None, report_ref False -> None. Every one of those is fail-CLOSED: _predicate returns None for an unmeasured effect and match() prints 'NOT-EVALUABLE -- treating the occasion as live', while discharges() returns None, which is falsy, so nothing is discharged by an unmeasured effect. I looked specifically for a case where the cut ALLOWS what base denied and there is none -- the change can only add demands.\n\nONE CAVEAT THE HUNTER'S JUSTIFICATION MISSED (reported, not refuting). Their line 'no stated limit is softened' examines only the occasion side. On the ARTIFACT side, in that same no-ref repository observed.json goes from {head: \"\", branch: \"main\", refs: {HEAD: \"\"}} to {head: null, branch: null, refs: null}, and _artifact_read still grants A01 its discharge (it only requires a 'head' key). So on a fresh `git init` the operator now Reads a document that no longer names the branch, and A01 counts as discharged anyway. I judged this short of a refutation: base's document in that state already carried no HEAD and no dirty list, the DECISION is identical before and after, and no plant that reddened goes green. But if the owner cares about A01's substance, the fix belongs in _artifact_read (require a non-null head), not in refs().\n\nLOC: filed 12 -> 18 (+6); measured +6 non-blank non-comment. Exact.", "gate_output": "c03: Ran 245 tests OK ; REPLAY sessions=26 passed=26 failed=0 ; views match plugin/keel/clauses.json ; proofs/Clauses.v matches plugin/keel/clauses.json ; COQ=PASS Clauses.v covers sides=51 of clauses=24 ; Coverings.v: results=16 axioms=0 ; Clauses.v: results=72 axioms=0 ; eval/corpus matches 26 specs ; git status --porcelain | wc -l = 1 ; EXITS 0 0 0 0 0 0."}
