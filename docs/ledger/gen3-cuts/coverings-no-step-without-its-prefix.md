# coverings-no-step-without-its-prefix [theorem] Corollary no_step_without_its_prefix
LOC 4 -> 0

## description
`no_step_without_its_prefix : forall j, done j -> forall i, i <= j -> done i` and `chain_composes : forall j i, i <= j -> done j -> done i` are the same proposition with `i <= j` and `done j` exchanged; the proof is literally `exact (chain_composes j i Hle Hd)`. It is an identity restatement, not a consequence. Nothing in Clauses.v, the tests, eval/attacks.sh or the README cites it by name. Removed together with its `Print Assumptions` line.

## diff
--- a/proofs/Coverings.v
+++ b/proofs/Coverings.v
-  (** COROLLARY. A step is reachable only after the entire prefix -- stated as the property an
-      enforcement point can actually check, one link at a time. *)
-  Corollary no_step_without_its_prefix :
-    forall j, done j -> forall i, i <= j -> done i.
-  Proof. intros j Hd i Hle. exact (chain_composes j i Hle Hd). Qed.
-
 End Coverings.
@@
-Print Assumptions no_step_without_its_prefix.

## gate
COQ=PASS ... Coverings.v: results=14 axioms=0 parameters=16 (was results=16) ; 246 tests OK ; REPLAY 26/26

## complexity
coqc Coverings.v median 0.348s -> 0.306s over 5 runs each, together with the other Coverings cut (-12%); two fewer kernel checks and two fewer Print Assumptions.

## verdict
{"id": "coverings-no-step-without-its-prefix", "refuted": false, "reason": "NOT INDEPENDENTLY GATED (plan mode active); verdict from static verification only.\n\nThe replication claim is exact. proofs/Coverings.v:341 'chain_composes : forall j i, i <= j -> done j -> done i' and :352 'no_step_without_its_prefix : forall j, done j -> forall i, i <= j -> done i' are the same proposition with the two hypotheses exchanged, and the corollary's entire proof is 'intros j Hd i Hle. exact (chain_composes j i Hle Hd).' - an eta-expanded argument permutation, not a consequence. It states nothing chain_composes did not.\n\nNo dependency: 'grep -rn no_step_without_its_prefix' over the whole tree hits only proofs/Coverings.v (its statement, its proof, and its Print Assumptions at :373). It is not named by proofs/Clauses.v, by any test, by eval/attacks.sh (whose only two Coq theorem names are textual_never_immune and every_covering_is_immune), or by README.md.\n\nNo fail-closed direction and no limit is touched: the ordering claim the repository actually argues from is chain_composes ('THEOREM 9'), which survives with its comment, and README:324-325's ordering sentence cites the violates/backward result, not this corollary.\n\nArithmetic is self-consistent: Coverings.glob currently records prf=16 against 16 'Print Assumptions' lines; removing this one and cut 7's gives 14, exactly the 'results=14' the report claims. The PARAMETERS line's 16 names are unaffected - 'done' and 'link' remain used by chain_composes - matching the reported 'parameters=16'.", "gate_output": "NOT RUN - plan mode active. Static verification: Coverings.v:341 vs :352 are the same proposition with hypotheses swapped, proof is a single 'exact (chain_composes j i Hle Hd)'. grep over the tree finds zero citations outside proofs/Coverings.v. Coverings.glob prf=16 today; 16 - 2 (this cut + cut 7) = the reported results=14; PARAMETERS' 16 names unaffected since chain_composes still uses done/link."}
