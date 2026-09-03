# MATH-09 CONFIRMED [math/break] proofs/Coverings.v :: chain_composes (Thm 9) + Hypothesis link ; positive_needs_no_vocabulary (Thm 6)

## claim
Thm 9: 'Pairwise links compose to the whole chain, at any length... This is why the model discriminates.' Thm 6: 'A positive obligation is name-agnostic and VOCABULARY-FREE... Stated as an INVARIANCE so that it has content: (The first statement of this theorem unfolded to `P <-> P`...)'

## reproducer
W=/tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/attack/math/Keel
cd $W/proofs && cat > Break_chain.v <<'EOF'
Require Import List Arith. Require Import Coverings.
Theorem chain_composes_is_just_link : forall (done : nat -> Prop),
  (forall j i, i <= j -> done j -> done i) <-> (forall i, done (S i) -> done i).
Proof. intro done. split.
  - intros H i Hd. exact (H (S i) i (Nat.le_succ_diag_r i) Hd).
  - intro link. exact (chain_composes done link). Qed.
Section Positive.
  Variable Text Datum : Type. Variable claimed observed : Text -> option Datum.
  Variable R : option Datum -> option Datum -> Prop.
  Definition any_covering (c:Text) : Prop := R (claimed c) (observed c).
  Theorem the_certificate_holds_for_every_such_covering : forall f : Text -> Text,
    (forall c, claimed (f c) = claimed c) -> (forall c, observed (f c) = observed c) ->
    forall c, any_covering c <-> any_covering (f c).
  Proof. intros f Hc Ho c. unfold any_covering. rewrite Hc, Ho. reflexivity. Qed.
End Positive.
Section Vocabulary.
  Variable Text : Type. Variable claimed_program observed_program : Text -> option nat.
  Theorem a_vocabulary_covering_passes_theorem_6 : forall f : Text -> Text,
    (forall c, claimed_program (f c) = claimed_program c) ->
    (forall c, observed_program (f c) = observed_program c) ->
    forall c, positive Text nat claimed_program observed_program c
          <-> positive Text nat claimed_program observed_program (f c).
  Proof. intros f Hc Ho c. exact (positive_needs_no_vocabulary Text nat claimed_program observed_program f Hc Ho c). Qed.
End Vocabulary.
EOF
coqc -q -Q . "" Break_chain.v && echo COMPILED

## observed
COMPILED

Theorem 9's conclusion `forall j i, i <= j -> done j -> done i` is logically EQUIVALENT to its hypothesis `link : forall i, done (S i) -> done i` -- I proved the iff. The chain is not shown to compose; downward-closure of `done` is assumed as a fact about the world, and nothing anywhere connects `link` to what dispatch.py enforces. Theorem 6's repaired statement is a generic congruence: I proved the identical invariance for an ARBITRARY relation R on (claimed c, observed c). It therefore establishes nothing about vocabulary -- I instantiated `Datum := nat` read as a program-name code, i.e. a covering that compares the program the report names to the program the trace names (a covering WITH a vocabulary), and `positive_needs_no_vocabulary` certifies it unchanged. The 'fix' for the vacuous Theorem 6 is vacuous in the same way, just past one `rewrite`.
