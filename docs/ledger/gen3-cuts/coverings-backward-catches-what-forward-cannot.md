# coverings-backward-catches-what-forward-cannot [theorem] Theorem backward_catches_what_forward_cannot
LOC 8 -> 0

## description
`backward_catches_what_forward_cannot e HL Hno : ~ backward (e :: nil)` is exactly `violation_is_never_backward (e :: nil) (violates_here e nil HL Hno)`: the constructor `violates_here` takes precisely its two hypotheses (`isL e` and `forall p, ~ isX p`). The general result already covers every trace length, so the singleton case is a copy. It is not cited by Clauses.v, the tests, eval/attacks.sh or the README (attacks.sh names only `textual_never_immune` and `every_covering_is_immune`). Its comment -- the argument that a rule enforced only at X can be escaped by entering at L -- is what mattered, so that paragraph was folded into Theorem 8's own comment rather than deleted, and the contrast is still stated in Coq by the surviving `forward_only_admits_the_violation`.

## diff
--- a/proofs/Coverings.v
+++ b/proofs/Coverings.v
-  (** THEOREM 8a. The inductive `violates` is what backward enforcement rejects, at any trace
+  (** THEOREM 8. The inductive `violates` is what backward enforcement rejects, at any trace
       length: the violating L is somewhere in the trace, every event before it is not an X, and
-      backward demands an X somewhere -- which is the contradiction, by induction on the trace. *)
+      backward demands an X somewhere -- which is the contradiction, by induction on the trace.
+
+      This is already "backward catches what forward cannot", at every length rather than one:
+      `violates_here e nil` IS the trace where L happened and X never did, so backward rejects
+      the very trace the forward rule can never reach -- the forward rule is only entered by
+      doing X. A rule enforced only at X has an escape BY CONSTRUCTION: enter the chain at L. *)
   Theorem violation_is_never_backward :
     forall t, violates t -> ~ backward t.
@@
-  (** THEOREM 8. Backward enforcement rejects the violation even when the forward rule never
-      ran -- because the forward rule is only reached by doing X, and the whole point of this
-      violation is that X never happened. A rule enforced only at X has an escape BY
-      CONSTRUCTION: enter the chain at L. *)
-  Theorem backward_catches_what_forward_cannot :
-    forall e, isL e -> (forall p, ~ isX p) -> ~ backward (e :: nil).
-  Proof.
-    intros e HL Hno Hback.
-    destruct (Hback e (or_introl eq_refl) HL) as [p [_ HX]].
-    exact (Hno p HX).
-  Qed.
-
   (** COROLLARY (the escape is real, not hypothetical). ...
@@
-Print Assumptions backward_catches_what_forward_cannot.

## gate
COQ=PASS ... Coverings.v: results=14 axioms=0 parameters=16 ; 246 tests OK ; REPLAY 26/26 ; eval/attacks.sh cells re-run by tests/test_attacks.py all pass

## complexity
Included in the Coverings.v 0.348s -> 0.306s measurement. The theorem is recoverable in one application term, recorded in the comment that replaced it.

## verdict
{"id": "coverings-backward-catches-what-forward-cannot", "refuted": false, "reason": "NOT INDEPENDENTLY GATED (plan mode active); verdict from static verification only.\n\nThe derivability claim is exact, and I checked the constructor's type rather than taking it on trust. proofs/Coverings.v:281 gives 'violates_here : forall e rest, isL e -> (forall p, ~ (isX p)) -> violates (e :: rest)', so 'violates_here e nil HL Hno : violates (e :: nil)', and :291 'violation_is_never_backward : forall t, violates t -> ~ backward t' applied to it yields precisely '~ backward (e :: nil)' - the removed theorem's statement, from its own two hypotheses, in one application term. It is the general result at one trace length, not a separate result.\n\nNo dependency: 'grep -rn backward_catches_what_forward_cannot' hits only proofs/Coverings.v (:306, :312, :370). eval/attacks.sh names only textual_never_immune and every_covering_is_immune; no test and no README line cite it.\n\nNo fail-closed direction lost. The contrast the theorem carried - that a rule enforced only at X is escapable by entering at L - is still STATED IN COQ by the surviving 'forward_only_admits_the_violation' (:320-322), which proves forward-only enforcement ACCEPTS that same trace. Losing the rejection half while keeping the acceptance half would have been a real cut into the argument; it is not lost, because violation_is_never_backward covers e::nil among all t.\n\nDEFECT IN THE SUBMITTED CUT, which must be fixed but does not meet the refutation bar: the diff renames the comment 'THEOREM 8a' to 'THEOREM 8', while README.md:325 cites '(Theorem 8a)' for exactly this claim ('an ordering enforced backward rejects every trace the inductive violates describes'), and Coverings.v:157 already carries another 'THEOREM 8 (the occasion form)'. After the cut the README's label resolves to nothing and the file has two THEOREM 8s. Nothing in the gate cross-checks README labels against the proofs (the only tests touching README are test_fence.py:585 on PNGs, test_ledger_growth.py:108 on the hash chain, test_workflow_gates.py:67 on dependencies), so this drift is silent and the gate stays green - which is why I do not refute on it. It is still the cut re-introducing exactly the replication the owner is removing, in a file the 4-file changeset does not touch. Keep the 8a label, or update README:325 in the same change.", "gate_output": "NOT RUN - plan mode active. Static verification: violates_here's type (Coverings.v:281) composed with violation_is_never_backward (:291) yields the removed statement exactly. grep finds zero citations outside proofs/Coverings.v; attacks.sh names only textual_never_immune and every_covering_is_immune. Contrast preserved by forward_only_admits_the_violation (:320). Unfixed drift: README.md:325 cites 'Theorem 8a', which the diff renames away; no gate command checks README labels (README-touching tests are test_fence.py:585, test_ledger_growth.py:108, test_workflow_gates.py:67, none of w
