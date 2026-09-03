# coverings-nominal-alias [dead] Definition nominal (V : Program -> Prop) : Covering := structural V
LOC 3 -> 2

## description
`nominal` was defined as `structural` with nothing added, and its only use was to state Theorem 5. The alias claims a distinction the formalism does not make: a nominal covering IS a structural one whose `wanted` predicate is a vocabulary of program names. Theorem 5 is now stated directly on `structural` (same proof, unchanged), and the word 'nominal' -- which the loader and classify_side use as a class name -- survives where it belongs, in the theorem's comment.

## diff
--- a/proofs/Coverings.v
+++ b/proofs/Coverings.v
-  Definition nominal (V : Program -> Prop) : Covering := structural V.
-
-  (** THEOREM 5 (monotone in the vocabulary). Widening the list can only ever ADD fires.
-      A missing name is therefore always a MISS, never a false fire. *)
+  (** THEOREM 5 (monotone in the vocabulary). A NOMINAL covering is `structural` over a
+      vocabulary of program names -- the same object, not a second one. Widening the list can
+      only ever ADD fires. A missing name is therefore always a MISS, never a false fire. *)
   Theorem nominal_monotone :
     forall (V W : Program -> Prop),
-      (forall p, V p -> W p) -> forall c, nominal V c -> nominal W c.
+      (forall p, V p -> W p) -> forall c, structural V c -> structural W c.
   Proof.
     intros V W Hsub c [s [p [rest [Hin [Hargv HV]]]]].
     exists s, p, rest. repeat split; [exact Hin | exact Hargv | exact (Hsub p HV)].
   Qed.

## gate
COQ=PASS ... Coverings.v: results=14 axioms=0 parameters=16 ; 246 tests OK ; REPLAY 26/26 ; tests/test_subject_across_surfaces.py (cites Thm 5) passes unchanged

## complexity
One fewer definition to unfold; the theorem's statement is now in the same vocabulary as Theorem 2, which is about `structural`.

## verdict
{"id": "coverings-nominal-alias", "refuted": false, "reason": "NOT INDEPENDENTLY GATED (plan mode active); verdict from static verification only.\n\nThe claim is confirmed by coqc's own index, which is stronger than a grep. Coverings.glob records 'def 9889:9895 <> nominal' and exactly TWO references to it: 'R10216:10222 Coverings <> nominal def' and 'R10231:10237 Coverings <> nominal def'. Both byte offsets fall inside Theorem 5's statement (Coverings.v:187-189, 'forall c, nominal V c -> nominal W c'). So the alias has precisely one consumer, and restating that theorem on 'structural' leaves nothing behind. The definition itself is 'Definition nominal (V : Program -> Prop) : Covering := structural V' - a second name for one object with nothing added, so 'nominal V c' and 'structural V c' are definitionally equal and the proof (which destructs the existential directly) is unchanged.\n\nNo limit softened and no citation dangled. The theorem NAME 'nominal_monotone' is preserved, which is what everything outside the proofs actually cites: README:319 ('monotone in that vocabulary (Theorem 5)'), plugin/keel/clauses.py:371 and :588-596 (the CLAUSE-OCCASION-NOMINAL deny reason citing 'Theorem 3, Theorem 5'), tests/test_derived_closure.py:9, tests/test_subject_across_surfaces.py:5. None of them names the Coq identifier 'nominal', so none breaks. The word survives where the report says it does, in the theorem's comment.\n\nArithmetic consistent: 'nominal' is a 'def', not a 'prf', so removing it leaves prf at the post-cut-6/7 count of 14, matching the reported results=14, and touches no Section variable, matching parameters=16.\n\nThe one thing worth weighing against the cut is that 'nominal' was the formalism's only named referent for the class the loader refuses by that name - but since the two are definitionally equal, nothing provable changes, and the deny_reason text (which cites theorem NUMBERS, not identifiers) is untouched. Not a softened limit.", "gate_output": "NOT RUN - plan mode active. Static verification from coqc's own index: Coverings.glob has 'def 9889:9895 <> nominal' with exactly two references, 'R10216:10222 Coverings <> nominal def' and 'R10231:10237 Coverings <> nominal def', both inside Theorem 5's statement (Coverings.v:187-189). Theorem name nominal_monotone preserved, so README:319, clauses.py:371/:588-596, test_derived_closure.py:9 and test_subject_across_surfaces.py:5 all still resolve. 'nominal' is a def not a prf, so results stays 14 and parameters stays 16."}
