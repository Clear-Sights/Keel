# MATH-07 CONFIRMED [math/break] proofs/Coverings.v :: effect, effect_is_name_agnostic, effect_separates_same_segments (Theorem 8) ; every `*_name_agnostic` / `*_separates` in proofs/Clauses.v

## claim
Coverings.v Thm 8: 'A covering over what the act DID reads no segment at all, so renaming every program changes nothing it sees: it is name-agnostic by construction.' render_coverings.py emits this pair as the certificate for the 36 effect-class sides. Owner's law: guards must be name-agnostic; loader refuses CLAUSE-GUARD-NOMINAL.

## reproducer
W=/tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/attack/math/Keel
cd $W/proofs && cat > Break_effect.v <<'EOF'
Require Import List String. Import ListNotations. Require Import Coverings.
Open Scope string_scope.
Section Attack.
  Variable wanted : string -> Prop. Variable p q : string.
  Hypothesis Hp : wanted p. Hypothesis Hq : ~ wanted q.
  Definition nominal_guard := nominal_segs string wanted.
  Theorem the_guard_is_nominal : ~ name_agnostic string nominal_guard.
  Proof. exact (name_agnostic_cannot_separate_by_name string wanted p q Hp Hq). Qed.
  Theorem the_same_guard_certifies_as_agnostic :
    forall d : list (Segment string), name_agnostic string (effect string nominal_guard d).
  Proof. intro d. exact (effect_is_name_agnostic string (list (Segment string)) nominal_guard d). Qed.
  Theorem the_same_guard_also_separates :
    forall d d', nominal_guard d -> ~ nominal_guard d' ->
      forall segs, effect string nominal_guard d segs /\ ~ effect string nominal_guard d' segs.
  Proof. intros d d'. exact (effect_separates_same_segments string (list (Segment string)) nominal_guard d d'). Qed.
End Attack.
Theorem name_agnostic_only_says_the_argument_is_ignored :
  forall (P:Type)(Q:list (Segment P)->Prop), (forall s1 s2, Q s1 <-> Q s2) -> name_agnostic P Q.
Proof. intros P Q H r segs. apply H. Qed.
EOF
coqc -q -Q . "" Break_effect.v && echo COMPILED

## observed
COMPILED

The same covering `nominal_segs wanted` -- selection on a program's NAME -- is (a) proved NOT name-agnostic by the file's own Theorem 3, and (b) proved to satisfy BOTH halves of the certificate that render_coverings.py emits for A01, A02, A03, C08, C09, T01, T02, U01, U02, U03, U06, U08 and every other effect side, simply by taking Delta := list (Segment string), E := the nominal predicate, d := what ran. The reason is general and I proved it: `name_agnostic Q` is implied by `Q` ignoring its argument, and `effect E d` ignores its argument by definition. So the 72 shipped certificates are compatible with every guard whatsoever, nominal guards included: they carry no information about name-agnosticism at all.
