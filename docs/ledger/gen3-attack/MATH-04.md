# MATH-04 CONFIRMED [math/break] tools/check_coq.py :: IDENTITY regex ; proofs/Coverings.v Theorem 8 pair (effect_is_name_agnostic, effect_separates_same_segments)

## claim
check_coq.py: 'no result is the identity -- a statement whose proof is `exact H` after `split` grades nothing'. Coverings.v Theorem 6 comment: 'a result whose proof is the identity grades nothing, and `check_coq.py` now refuses that shape.'

## reproducer
W=/tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/attack/math/Keel
cd $W && python3 - <<'PY'
import pathlib
p=pathlib.Path("proofs/Coverings.v"); t=p.read_text()
inj='''\n  Theorem vacuous_iff : forall (P : Covering) c, P c <-> P c.\n  Proof. intros P c. apply iff_refl. Qed.\n\n  Theorem vacuous_restates_hypotheses : forall (P : Covering) c, P c -> ~ P c -> P c /\\ ~ P c.\n  Proof. intros P c H1 H2. exact (conj H1 H2). Qed.\n\n  Theorem vacuous_split : forall (P : Covering) c, P c <-> P c.\n  Proof. intros P c; split; [ exact (fun h => h) | exact (fun h => h) ]. Qed.\n\n'''
t=t.replace("End Coverings.", inj+"End Coverings.")
t=t.replace("Print Assumptions textual_never_immune.","Print Assumptions vacuous_iff.\nPrint Assumptions vacuous_restates_hypotheses.\nPrint Assumptions vacuous_split.\nPrint Assumptions textual_never_immune.")
p.write_text(t)
PY
rm -f proofs/*.vo proofs/*.glob; python3 tools/check_coq.py; echo EXIT=$?

## observed
COQ=PASS Clauses.v covers sides=51 of clauses=24 ; Coverings.v: results=19 axioms=0 ; Clauses.v: results=72 axioms=0
EXIT=0

Three provably content-free results pass. Spelled `split; intro h; exact h` the SAME theorem fails ('a result is proved by the identity'); spelled `split; [exact (fun h=>h)|exact (fun h=>h)]` it passes. Decisively: the two shapes that pass -- `apply iff_refl` and `exact (conj H1 H2)` -- are EXACTLY the proof scripts of the shipped `effect_is_name_agnostic` (`Proof. intros Delta E d r segs. unfold effect. apply iff_refl. Qed.`) and `effect_separates_same_segments` (`Proof. ... exact (conj Hd Hd'). Qed.`), which are then replicated 36 times each as the entire instance over the table. The gate that was added to refuse identity proofs does not see the file's own.
