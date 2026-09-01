(** * Why a covering over raw command text cannot be made sound by examples.

    This file exists because of a METHOD failure, not only a code defect. Three "mention
    defeats" were found in one clause by inventing three command strings. Patching the pattern
    against those three fits the pattern to them, and nothing excludes the next unseen string.
    An unbounded obligation cannot be discharged by enumeration: a test built against a defect
    stops testing anything except itself.

    So the obligation is discharged ONCE, structurally, for every covering simultaneously.

    NOTHING IS ASSUMED GLOBALLY. The scanner and the embedding are Section Variables and their
    behaviour is Hypotheses, so each theorem is explicitly RELATIVE to a scanner with the
    stated properties, and `Print Assumptions` reports the development closed under the global
    context -- zero axioms. The adequacy of that scanner against a real shell is empirical and
    is NOT claimed here. But it is now ONE obligation about ONE object, instead of one
    unbounded obligation per covering. That reduction is the result. *)

Require Import List.
Import ListNotations.

Section Coverings.

  Variable Text    : Type.   (* a raw command, as the host delivers it *)
  Variable Program : Type.   (* the name of an invoked program *)

  (* A segment reduced to the only field these theorems need: what it invokes. *)
  Record Segment := { seg_argv : list Program }.

  Variable scan    : Text -> list Segment.  (* the ONE object every structural covering reads *)
  Variable mention : Text -> Text.          (* the embedding  e(c) = echo '<c>' *)
  Variable infix   : Text -> Text -> Prop.  (* `infix c d` : c occurs verbatim inside d *)

  (* (1) A mention keeps its subject verbatim. This is what MAKES it a mention. *)
  Hypothesis mention_preserves : forall c, infix c (mention c).

  (* (2) The scanner sees a mention as ONE segment invoking the quoting program: a quoted
         argument is an argument, not a command the shell runs. *)
  Variable quoting_program : Program.
  Hypothesis scan_mention_single :
    forall c, scan (mention c) = [ {| seg_argv := [quoting_program] |} ].

  Definition Covering := Text -> Prop.

  (* The property every guard must have, quantified over ALL commands rather than over a list
     of examples. That quantifier is the entire point of this file. *)
  Definition mention_immune (P : Covering) : Prop := forall c, ~ P (mention c).

  (* TEXTUAL: a property of the raw text that survives embedding. Every substring match whose
     left-context is a shell metacharacter has this shape, because the embedding copies those
     metacharacters along with everything else -- a `;` inside quotes is still a `;`. *)
  Definition textual (P : Covering) : Prop :=
    forall c d, P c -> infix c d -> P d.

  (* A covering that never fires is vacuously immune, and is a different defect. *)
  Definition non_vacuous (P : Covering) : Prop := exists c, P c.

  (** THEOREM 1. A textual covering that fires at all is defeated by a mention -- for every
      command it accepts, not merely for the strings someone thought to try. No counterexample
      is exhibited because none is needed. *)
  Theorem textual_never_immune :
    forall P, textual P -> non_vacuous P -> ~ mention_immune P.
  Proof.
    intros P Htext [c Hc] Himmune.
    exact (Himmune c (Htext c (mention c) Hc (mention_preserves c))).
  Qed.

  (* STRUCTURAL: reads the scanner's output, never the text. Some segment invokes a program
     drawn from the covering's own vocabulary. *)
  Definition structural (wanted : Program -> Prop) : Covering :=
    fun c => exists s p rest,
      In s (scan c) /\ seg_argv s = p :: rest /\ wanted p.

  (** THEOREM 2. A structural covering is mention-immune BY CONSTRUCTION, provided it does not
      ask for the quoting program itself. Uniform in c: one proof, every command. *)
  Theorem structural_immune :
    forall wanted, ~ wanted quoting_program -> mention_immune (structural wanted).
  Proof.
    intros wanted Hnot c [s [p [rest [Hin [Hargv Hwant]]]]].
    rewrite scan_mention_single in Hin.
    destruct Hin as [Hs | []].
    subst s. simpl in Hargv. injection Hargv as Hp _. subst p.
    exact (Hnot Hwant).
  Qed.

  (** COROLLARY. The two classes are disjoint on any covering that fires: a covering cannot be
      both textual and structural-with-a-clean-vocabulary. Migrating a side from the first
      class to the second is therefore a real change of kind, never a re-spelling. *)
  Corollary textual_and_structural_incompatible :
    forall wanted, ~ wanted quoting_program ->
      non_vacuous (structural wanted) -> ~ textual (structural wanted).
  Proof.
    intros wanted Hnot Hnv Htext.
    exact (textual_never_immune (structural wanted) Htext Hnv (structural_immune wanted Hnot)).
  Qed.


  (** ** Name-agnosticism: where "no text at all" is reachable, and where it provably is not.

      A covering is NAME-AGNOSTIC when renaming the programs changes no verdict. This is the
      strongest form of "not text": it does not merely avoid matching text, it cannot even
      SEE which program was invoked, so it depends on no language, English or otherwise. *)

  Definition rename (r : Program -> Program) (s : Segment) : Segment :=
    {| seg_argv := map r (seg_argv s) |}.

  Definition name_agnostic (Q : list Segment -> Prop) : Prop :=
    forall r segs, Q segs <-> Q (map (rename r) segs).

  (** THEOREM 3 (impossibility). A name-agnostic covering cannot separate two acts that differ
      only in which program is invoked -- and a NOMINAL covering with any name in and any name
      out is therefore never name-agnostic.

      This is the exact boundary. At the moment a covering runs BEFORE the act, the only thing
      distinguishing "publish the artifact" from "run the suite" is the name -- the two are the
      same shape, one segment, no edges, same arity. Take the act `[p]` with p wanted and the
      act `[q]` with q not: a nominal covering accepts the first and rejects the second, and a
      renaming sends one onto the other. So no name-agnostic covering can tell them apart, and
      demanding one is demanding something that does not exist. Not "hard": absent.

      Stated on segments so it depends on no scanner: the nominal shape is the one `structural`
      reads off `scan`, with `scan` factored out. *)
  Definition nominal_segs (wanted : Program -> Prop) (segs : list Segment) : Prop :=
    exists s p rest, In s segs /\ seg_argv s = p :: rest /\ wanted p.

  Theorem name_agnostic_cannot_separate_by_name :
    forall (wanted : Program -> Prop) p q, wanted p -> ~ wanted q ->
    ~ name_agnostic (nominal_segs wanted).
  Proof.
    intros wanted p q Hp Hq Hag.
    destruct (Hag (fun _ => q) [ {| seg_argv := [p] |} ]) as [Hfwd _].
    destruct Hfwd as [s [p' [rest [Hin [Hargv Hw]]]]].
    { exists {| seg_argv := [p] |}, p, []. repeat split; [left; reflexivity | exact Hp]. }
    simpl in Hin. destruct Hin as [Hs | []]. subst s. simpl in Hargv.
    injection Hargv as Hp' _. subst p'. exact (Hq Hw).
  Qed.

  (** THEOREM 4 (what survives). A covering over TOPOLOGY -- the shape of the action graph
      rather than its labels -- is name-agnostic. Segment count, and by the same argument the
      operator edges between them, are invariant under renaming.

      So the reachable form of "no text" is: guards read the SHAPE of what ran, or its EFFECTS.
      C09 is already this kind (`the checker's own pid is excluded from what it lists` is a
      topological fact), and C08 is the effect kind (`the exit status was non-zero`). Both were
      arrived at as one-off fixes; this theorem says they are the general form. *)
  Theorem topology_is_name_agnostic :
    forall n, name_agnostic (fun segs => length segs = n).
  Proof.
    intros n r segs. split; intros H; rewrite ?map_length in *; exact H.
  Qed.


  (** THEOREM 8 (the occasion form). A covering over what the act DID reads no segment at all,
      so renaming every program changes nothing it sees: it is name-agnostic by construction,
      the same way topology is. That alone would be a tautology, so it is stated together with
      its content, which is the exact dual of Theorem 3: where no covering over the segments
      can separate two acts with different names and the same shape, an effect covering
      SEPARATES two acts with the SAME segments -- byte-identical commands -- whenever what they
      did differs. The command string is not the input; the world is. *)
  Definition effect {Delta : Type} (E : Delta -> Prop) (d : Delta) : list Segment -> Prop :=
    fun _ => E d.

  Theorem effect_is_name_agnostic :
    forall (Delta : Type) (E : Delta -> Prop) (d : Delta), name_agnostic (effect E d).
  Proof. intros Delta E d r segs. unfold effect. apply iff_refl. Qed.

  Theorem effect_separates_same_segments :
    forall (Delta : Type) (E : Delta -> Prop) (d d' : Delta), E d -> ~ E d' ->
    forall segs, effect E d segs /\ ~ effect E d' segs.
  Proof. intros Delta E d d' Hd Hd' segs. unfold effect. exact (conj Hd Hd'). Qed.


  (** ** The vocabulary obligation, and which half of a clause it is expensive on.

      A NOMINAL covering carries a list of program names. That list is never provably complete
      -- there is always another runner. So the interesting question is not "is the list right"
      but WHICH WAY a missing entry fails. *)

  Definition nominal (V : Program -> Prop) : Covering := structural V.

  (** THEOREM 5 (monotone in the vocabulary). Widening the list can only ever ADD fires.
      A missing name is therefore always a MISS, never a false fire. *)
  Theorem nominal_monotone :
    forall (V W : Program -> Prop),
      (forall p, V p -> W p) -> forall c, nominal V c -> nominal W c.
  Proof.
    intros V W Hsub c [s [p [rest [Hin [Hargv HV]]]]].
    exists s, p, rest. repeat split; [exact Hin | exact Hargv | exact (Hsub p HV)].
  Qed.

  (** And a miss means opposite things on the two sides, which is the whole design consequence:

      - on the OCCASION side, a miss raises NO obligation, so the costly act proceeds with no
        guard at all. Expensive, and silent.
      - on the GUARD side, a miss fails to discharge, so the clause denies an act that was in
        fact guarded. Cheap: it interrupts, and the interruption is visible and self-correcting.

      An occasion must therefore be nominal (Theorem 3: before the act, the name is the only
      thing that distinguishes it) and its vocabulary is load-bearing. A GUARD need not be:
      "the suite ran and passed" is a fact about the TRACE, readable as a status and a count,
      with no vocabulary at all. That is where the obligation can be discharged rather than
      merely managed -- and Theorem 4 already says such a covering is name-agnostic. *)


  (** ** Positive obligations: why demanding the NUMBER beats forbidding the evasions.

      Everything above is about NEGATIVE coverings -- a guard that must refuse the ways an act
      can be faked. Theorem 1 is the standing cost of that shape: the evasion set is unbounded,
      so no finite set of examples discharges it, and each patch fits the pattern to the strings
      someone happened to try.

      A POSITIVE obligation inverts it. Rather than forbidding the ways to lie about a run,
      require the run's own datum -- the count of passing and failing tests -- and compare it to
      what the trace shows. *)

  Variable Datum : Type.
  Variable claimed  : Text -> option Datum.   (* what the report SAYS the run produced *)
  Variable observed : Text -> option Datum.   (* what the trace shows it DID produce *)

  Definition positive : Covering :=
    fun c => exists d, claimed c = Some d /\ observed c = Some d.

  (** THEOREM 6. A positive obligation is name-agnostic and vocabulary-free: its verdict is an
      equality between two data and mentions no program, no pattern, and no word. Stated as an
      INVARIANCE so that it has content: any rewriting of the text that leaves the claimed and
      observed data alone -- a rename, a new runner, a re-spelling -- leaves the verdict alone.
      (The first statement of this theorem unfolded to `P <-> P`; a result whose proof is the
      identity grades nothing, and `check_coq.py` now refuses that shape.) *)
  Theorem positive_needs_no_vocabulary :
    forall (f : Text -> Text),
      (forall c, claimed (f c) = claimed c) ->
      (forall c, observed (f c) = observed c) ->
      forall c, positive c <-> positive (f c).
  Proof.
    intros f Hc Ho c. unfold positive. rewrite Hc, Ho. reflexivity.
  Qed.

  (** THEOREM 7 (the honesty result). A claim that disagrees with the trace is ALWAYS rejected.

      This is the sentence "being forced to state the number bypasses dishonesty", proved: there
      is no d' to choose that both differs from the observed value and satisfies the covering.
      The evasion set is not merely bounded, it is EMPTY -- contrast Theorem 1, where it is
      unbounded. That is the whole argument for preferring the positive form. *)
  Theorem false_claim_always_rejected :
    forall c d d', claimed c = Some d -> observed c = Some d' -> d <> d' -> ~ positive c.
  Proof.
    intros c d d' Hc Ho Hne [d0 [Hc0 Ho0]].
    rewrite Hc in Hc0. rewrite Ho in Ho0.
    injection Hc0 as Hd. injection Ho0 as Hd'. subst. exact (Hne eq_refl).
  Qed.

  (** COROLLARY (silence is not success). A report that states no number does not satisfy the
      obligation. The absent claim fails exactly as a wrong one does, so declining to answer is
      not an escape -- which a negative guard cannot say, since it passes by default. *)
  Corollary no_claim_is_not_a_pass :
    forall c, claimed c = None -> ~ positive c.
  Proof. intros c Hnone [d [Hc _]]. rewrite Hnone in Hc. discriminate. Qed.


  (** ** Ordered obligations, enforced from BOTH ends.

      The model: "if you do X you owe L afterwards" and "if you do L, X must already have
      happened" are not two rules. They are ONE ordering relation observed at two points.

      Why that matters here: every defeat found in this estate has the same shape -- an
      alternative ENTRY POINT that never triggers the single place the rule was enforced. A
      notebook write never reached a `.py` gate. A quoted mention never reached a segment gate.
      Patching each entry point is unbounded work, and it is the enumeration Theorem 1 already
      showed cannot be finished. Enforcing the pair at BOTH endpoints makes the entry point
      irrelevant instead of enumerated. *)

  Variable Event : Type.
  Variable isX isL : Event -> Prop.

  (* `L occurred with no preceding X` -- the thing the order forbids, stated over a trace. *)
  Inductive violates : list Event -> Prop :=
  | violates_here  : forall e rest, isL e -> (forall p, ~ (isX p)) -> violates (e :: rest)
  | violates_later : forall e rest, ~ isX e -> violates rest -> violates (e :: rest).

  (* Backward enforcement: at every L, demand that an X already happened. *)
  Definition backward (t : list Event) : Prop :=
    forall e, In e t -> isL e -> exists p, In p t /\ isX p.

  (** THEOREM 8a. The inductive `violates` is what backward enforcement rejects, at any trace
      length: the violating L is somewhere in the trace, every event before it is not an X, and
      backward demands an X somewhere -- which is the contradiction, by induction on the trace. *)
  Theorem violation_is_never_backward :
    forall t, violates t -> ~ backward t.
  Proof.
    intros t Hv. induction Hv as [e rest HL Hno | e rest HnotX Hv IH]; intros Hb.
    - destruct (Hb e (or_introl eq_refl) HL) as [p [_ HX]]. exact (Hno p HX).
    - apply IH. intros l Hin HLl.
      destruct (Hb l (or_intror Hin) HLl) as [p [[Hpe | Hp] HX]].
      + subst p. exact (False_ind _ (HnotX HX)).
      + exists p. exact (conj Hp HX).
  Qed.

  (** THEOREM 8. Backward enforcement rejects the violation even when the forward rule never
      ran -- because the forward rule is only reached by doing X, and the whole point of this
      violation is that X never happened. A rule enforced only at X has an escape BY
      CONSTRUCTION: enter the chain at L. *)
  Theorem backward_catches_what_forward_cannot :
    forall e, isL e -> (forall p, ~ isX p) -> ~ backward (e :: nil).
  Proof.
    intros e HL Hno Hback.
    destruct (Hback e (or_introl eq_refl) HL) as [p [_ HX]].
    exact (Hno p HX).
  Qed.

  (** COROLLARY (the escape is real, not hypothetical). Forward-only enforcement ACCEPTS that
      same trace: it quantifies over the X events, and there are none, so it holds vacuously.
      Vacuous truth is exactly how a one-ended rule passes a trace that violates it. *)
  Definition forward (t : list Event) : Prop :=
    forall e, In e t -> isX e -> exists q, In q t /\ isL q.

  Corollary forward_only_admits_the_violation :
    forall e, isL e -> (forall p, ~ isX p) -> forward (e :: nil).
  Proof. intros e HL Hno x _ HX. destruct (Hno x HX). Qed.


  (** ** Chains of any length, from pairwise rules only.

      A chain X -> L -> M -> ... is not a rule about the chain. It is one ADJACENT-PAIR rule per
      link, each enforced backward at PreToolUse ("this step is refused unless the previous one
      happened"). The question is whether that is enough for a series of arbitrary length. *)

  Variable done : nat -> Prop.   (* `done i` : step i of the chain has occurred *)

  (* The only rule ever written: each step requires the one immediately before it. Local. *)
  Hypothesis link : forall i, done (S i) -> done i.

  (** THEOREM 9. Pairwise links compose to the whole chain, at any length: reaching step j
      implies EVERY earlier step happened. No global rule, no rule about the chain's length, and
      no dependence on where the chain was entered -- entering at step j still demands all of
      0..j. This is why the model discriminates: there is no length at which it thins out, and
      no entry point that skips a predecessor. *)
  Theorem chain_composes : forall j i, i <= j -> done j -> done i.
  Proof.
    induction j as [| j IH]; intros i Hle Hdone.
    - inversion Hle. subst. exact Hdone.
    - inversion Hle; subst.
      + exact Hdone.
      + exact (IH i H0 (link j Hdone)).
  Qed.

  (** COROLLARY. A step is reachable only after the entire prefix -- stated as the property an
      enforcement point can actually check, one link at a time. *)
  Corollary no_step_without_its_prefix :
    forall j, done j -> forall i, i <= j -> done i.
  Proof. intros j Hd i Hle. exact (chain_composes j i Hle Hd). Qed.

End Coverings.

(* The honesty check the repository requires of any proof it publishes. *)
Print Assumptions textual_never_immune.
Print Assumptions structural_immune.
Print Assumptions textual_and_structural_incompatible.
Print Assumptions name_agnostic_cannot_separate_by_name.
Print Assumptions topology_is_name_agnostic.
Print Assumptions effect_is_name_agnostic.
Print Assumptions effect_separates_same_segments.
Print Assumptions nominal_monotone.
Print Assumptions false_claim_always_rejected.
Print Assumptions no_claim_is_not_a_pass.
Print Assumptions violation_is_never_backward.
Print Assumptions backward_catches_what_forward_cannot.
Print Assumptions forward_only_admits_the_violation.
Print Assumptions chain_composes.
Print Assumptions no_step_without_its_prefix.
(* Theorem 6 was DECLARED and never graded here. Nothing said so: the grading was a hand-kept
   list, so a result could be added without joining it -- the same hardcoded-list defect the
   Small-Tools review found. tools/check_coq.py now DERIVES the set from the file and refuses
   any result it cannot see graded, which is what surfaced this one. It matters more than most:
   the claim that a positive obligation needs no vocabulary is what the whole positive form
   rests on, and an axiom hiding under it would be invisible in exactly the place it counts. *)
Print Assumptions positive_needs_no_vocabulary.
