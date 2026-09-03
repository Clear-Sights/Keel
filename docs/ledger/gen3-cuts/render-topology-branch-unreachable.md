# render-topology-branch-unreachable [dead] side_block()'s `if cls == "topology":` arm, and its consumer Coverings.topology_is_name_agnostic
LOC 5 -> 0

## description
`side_block` dispatched on `C.classify_side(predicate)` and had an arm for cls == 'topology'. `keel.clauses.classify_side` returns exactly: absent, textual, nominal, composed, unclassified, always, effect, tool-enum, positive -- never 'topology'. The arm was unreachable for ANY predicate, not just for the shipped table, and it was the only consumer of Coverings.v's Theorem 4 (`topology_is_name_agnostic`). The arm is gone. Theorem 4 is KEPT: README line 321 argues from it ('a covering over the pipe topology is name-agnostic (Theorem 4)') and it is the theory's statement of which shape of 'no text' is reachable -- so it is a theorem nothing in Coq depends on, but its dead CONSUMER is what was cut, not the claim.

## diff
--- a/tools/render_coverings.py
+++ b/tools/render_coverings.py
-    if cls == "topology":
-        return head + [
-            f"  Theorem {name}_name_agnostic : forall n, name_agnostic string (fun segs => List.length segs = n).",
-            f"  Proof. exact (topology_is_name_agnostic string). Qed.",
-        ]
(the remaining classes are dispatched through RESULTS / BOUNDARY; an unknown class still
 raises SystemExit "class {cls!r} has no instance; the loader should have refused it")

## gate
proofs/Clauses.v matches plugin/keel/clauses.json ; COQ=PASS Clauses.v covers sides=51 of clauses=24: instantiated=36 empty-by-class[always=7 tool-enum=8] ; 246 tests OK

## complexity
Confirmed unreachable by reading every return of classify_side (plugin/keel/clauses.py:357-403) and by `grep -rn topology` over the tree: the only non-prose hits were this branch and its Coverings.v callee.

## verdict
{"id": "render-topology-branch-unreachable", "refuted": false, "reason": "NOT INDEPENDENTLY GATED (plan mode active); verdict from static verification only.\n\nThe unreachability claim is airtight and I checked it by enumerating every return of the classifier rather than by grepping. plugin/keel/clauses.py:357-403, classify_side, has exactly these returns: 'absent' (374), 'textual' (381), 'nominal' (383), the recursive single-part pop (386), 'composed' (387), 'unclassified' (388, 398, 403), 'always' (390), 'effect' (392), 'tool-enum' (394, 397), 'positive' (402). 'topology' is not among them, and the recursive branch can only return a value the same function already produced. So side_block's 'if cls == \"topology\":' arm is dead for EVERY possible predicate, not merely for the shipped table - which is the stronger claim the report makes and it holds.\n\nThe cut is correctly scoped and does not overreach: it removes the dead ARM, and explicitly KEEPS Coverings.v's Theorem 4 (topology_is_name_agnostic). That matters, because README:321 argues from it ('a covering over the pipe topology is name-agnostic (Theorem 4)') and Coverings.v:142-154 uses it to state which shape of 'no text' is reachable. Cutting the theorem would have dangled the README; cutting only its dead consumer does not. Consistent with the reported Coverings.v results=14 (16 minus cuts 6 and 7 only).\n\nFail-closed direction preserved: the fallthrough 'raise SystemExit(f\"{clause_id}.{side}: class {cls!r} has no instance; the loader should have refused it\")' survives in the new dispatch (the report's replacement keeps 'elif cls not in BOUNDARY: raise SystemExit(...)'). An unknown class still stops the render rather than silently emitting nothing.", "gate_output": "NOT RUN - plan mode active. Static verification: every return statement of classify_side (plugin/keel/clauses.py:357-403) enumerated - {absent, textual, nominal, composed, unclassified, always, effect, tool-enum, positive}; 'topology' is unreachable on all inputs. Theorem 4 retained, so README:321 still resolves. The unknown-class SystemExit fallthrough is preserved in the replacement."}
