# MATH-06 CONFIRMED [math/break] proofs/Coverings.v :: violates, backward, violation_is_never_backward (Thm 8a), backward_catches_what_forward_cannot (Thm 8)

## claim
'Ordered obligations, enforced from BOTH ends... Backward enforcement: at every L, demand that an X ALREADY happened.' 'The inductive `violates` is what backward enforcement rejects, at any trace length.' This section is the stated mathematical justification for the plugin's bidirectional chain.

## reproducer
W=/tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/attack/math/Keel
cd $W/proofs && cat > Break_order.v <<'EOF'
Require Import List Bool.
Import ListNotations.
Require Import Coverings.
Definition E := bool.
Definition isX (e:E) : Prop := e = true.
Definition isL (e:E) : Prop := e = false.
Definition bad_trace : list E := [false; true].   (* L first, X only afterwards *)
Theorem backward_accepts_out_of_order : backward E isX isL bad_trace.
Proof. unfold backward, bad_trace. intros e Hin HL. exists true. split; [right;left;reflexivity|reflexivity]. Qed.
Theorem not_a_violation : ~ violates E isX isL bad_trace.
Proof. intro H. inversion H as [e r HL Hno Heq|e r HnX Hr Heq].
  - subst. exact (Hno true eq_refl).
  - subst. inversion Hr as [e2 r2 HL2 Hno2 H2|e2 r2 HnX2 Hr2 H2].
    + subst. discriminate HL2. + subst. exact (HnX2 eq_refl). Qed.
Theorem violates_forces_no_X_anywhere : forall (Ev:Type)(iX iL:Ev->Prop)(t:list Ev),
  violates Ev iX iL t -> forall p, ~ iX p.
Proof. intros Ev iX iL t H. induction H as [e r HL Hno|e r HnX H IH]; assumption. Qed.
Theorem theorem_8a_is_vacuous_whenever_an_X_exists : forall (Ev:Type)(iX iL:Ev->Prop)(x:Ev),
  iX x -> forall t, ~ violates Ev iX iL t.
Proof. intros Ev iX iL x Hx t Hv. exact (violates_forces_no_X_anywhere Ev iX iL t Hv x Hx). Qed.
EOF
coqc -q -Q . "" Break_order.v && echo COMPILED

## observed
COMPILED (all four theorems accepted by coqc 8.18.0)

The ordering section encodes no order. (1) `backward t := forall e, In e t -> isL e -> exists p, In p t /\ isX p` uses membership only: the trace [L, X] -- do the guarded act first, satisfy its prerequisite afterwards -- SATISFIES `backward`. (2) `violates`'s base constructor takes `forall p, ~ isX p`, a GLOBAL emptiness claim, not 'no X before this L'; I proved `violates t -> forall p, ~ iX p`, so `violates` is uninhabited the moment any X exists anywhere in the event type. (3) Therefore Theorem 8a has zero instances in any world where the prerequisite act is possible, and Theorem 8's hypothesis `(forall p, ~ isX p)` is that same X-free universe. The pair proves only 'if the prerequisite can never occur, demanding it fails' -- not the claimed 'entering the chain at L is caught'.
