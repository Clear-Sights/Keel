# EFF-09 [replication] trace_effects()'s report_listing; delta's dict(before, command=...)
LOC 4 -> 5

## description
`_lists_itself(text, command)` -- 'the act's output holds a whole segment of its own command' -- was computed twice per act on the identical (stdout, command) pair: once as `report_self` in report_effects(), and again inside trace_effects() to derive report_listing. To make the second call possible, delta built a COPY of the whole before-snapshot with the command grafted onto it (`dict(before, command=tool_input.get('command'))`), so a field of the act was travelling inside the record of the world before the act. report_listing is now derived from the report_self already computed, `before` is passed as itself, and the command no longer enters the snapshot dict. The guard-coverings test composes the same two calls delta composes and now reads report_self from report_effects' own output rather than making the observer compute it twice.

## diff
--- a/plugin/keel/effects.py
+++ b/plugin/keel/effects.py
-def trace_effects(text: str, before: dict[str, Any], root: str | None, quiet: bool) -> dict[str, Any]:
+def trace_effects(text: str, before: dict[str, Any], root: str | None, quiet: bool,
+                  listed_self: bool = False) -> dict[str, Any]:
@@
         out["report_pids"] = len(claimed) >= LISTING_FLOOR
-        out["report_listing"] = out["report_pids"] and not _lists_itself(text, before.get("command"))
+        out["report_listing"] = out["report_pids"] and not listed_self
@@ delta
     out.update(trace_effects(response.get("stdout") if isinstance(response.get("stdout"), str) else "",
-                             dict(before, command=tool_input.get("command")), root, still))
+                             before, root, still, out["report_self"]))

--- a/tests/test_guard_coverings.py
     record = effects.report_effects(stdout, command)
-    record.update(effects.trace_effects(stdout, {"alive": list(alive), "command": command},
-                                        None, quiet=True))
+    record.update(effects.trace_effects(stdout, {"alive": list(alive)}, None, quiet=True,
+                                        listed_self=record["report_self"]))

## gate
Ran 244 tests in 196.393s / OK ; REPLAY sessions=26 passed=26 failed=0 ; views match plugin/keel/clauses.json ; proofs/Clauses.v matches plugin/keel/clauses.json ; COQ=PASS ; eval/corpus matches 26 specs ; git status --porcelain | wc -l = 26 ; chained exit=0

## complexity
One `_SEGMENT_SPLIT.split(command)` plus one substring scan of the whole stdout per act removed (2 -> 1), and one shallow copy of the ~14-key snapshot dict per act removed. C09's teeth are preserved: tests/test_guard_coverings.py::test_TEETH_a_mention_never_discharges_C09 and ::test_NON_VACUITY_the_real_listing_still_discharges both pass, and test_effects.py::test_a_listing_that_lists_itself_is_seen_and_one_that_does_not_is_the_guard drives report_self/report_listing through the live observer.

## verdict
{"id": "EFF-09", "refuted": false, "reason": "STANDS. Built in re-runs/c09 (effects.py + tests/test_guard_coverings.py).\n\nC09'S TEETH PLANTED DIRECTLY. The whole risk here is that a checker which counts itself starts discharging C09. I drove the plant through the live observer on both builds: output containing a whole segment of the act's own command (`ps aux | grep worker`, output carrying that segment plus eight live pids) gives report_self=True, report_pids=True, report_listing=False -- NOT discharged -- in base and after the cut alike; and the clean listing (`pgrep -f worker`, pids only) gives report_self=False, report_listing=True -- discharged -- in both. Unchanged.\n\nEQUIVALENCE: the text and command reaching _lists_itself are provably the same object in both call sites (report_effects coerces a non-str stdout to \"\", delta passes the identical coercion into trace_effects), and out['report_self'] is set by the report_effects update before the before.json read, so it is always present at the call. Confirmed empirically in the 120-scenario trace_effects differential and the 20-act end-to-end differential: report_listing identical everywhere.\n\nTHE `listed_self: bool = False` DEFAULT IS NOT A NEW FAIL-OPEN -- I checked this specifically, because a defaulted False on a guard-discharge input is exactly the shape that goes wrong. In BASE, trace_effects read the command out of `before.get('command')`, and a caller that did not graft it in got None -> _lists_itself returns False -> report_listing = report_pids. The default reproduces base's own behaviour for that caller precisely; the latent hole is unchanged, merely moved into the signature where it is visible.\n\nAnd the smuggling the cut removes is real: base built `dict(before, command=tool_input.get('command'))` -- a shallow copy of the whole ~15-key pre-act snapshot with a field of the ACT grafted onto the record of the world BEFORE the act, once per act. Gone, along with one redundant `_SEGMENT_SPLIT.split(command)` plus a substring scan of the whole stdout (2 -> 1 per act).\n\nLOC: filed 4 -> 5 (+1); measured +1. Exact.", "gate_output": "c09: Ran 245 tests OK ; REPLAY sessions=26 passed=26 failed=0 ; views match plugin/keel/clauses.json ; proofs/Clauses.v matches plugin/keel/clauses.json ; COQ=PASS Clauses.v covers sides=51 of clauses=24 ; Coverings.v: results=16 axioms=0 ; Clauses.v: results=72 axioms=0 ; eval/corpus matches 26 specs ; git status --porcelain | wc -l = 2 ; EXITS 0 0 0 0 0 0."}
