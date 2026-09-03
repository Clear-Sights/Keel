# MATH-02 NOVERDICT [math/break] proofs/Coverings.v (Section Coverings) ; tools/check_coq.py :: grade

## claim
proofs/Coverings.v header: 'NOTHING IS ASSUMED GLOBALLY... `Print Assumptions` reports the development closed under the global context -- zero axioms.' check_coq.py: 'every one is closed under the global context -- zero axioms'. tests/test_derived_closure.py::test_TEETH_the_proof_compiles_with_zero_axioms.

## reproducer
W=/tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/attack/math/Keel
cd $W && python3 - <<'PY'
import pathlib
p=pathlib.Path("proofs/Coverings.v"); t=p.read_text()
inj='''\n  Hypothesis world_is_convenient : False.\n  Theorem every_covering_is_immune : forall P : Covering, mention_immune P.\n  Proof. intros P c H. destruct world_is_convenient. Qed.\n\n'''
t=t.replace("End Coverings.", inj+"End Coverings.")
t=t.replace("Print Assumptions textual_never_immune.","Print Assumptions every_covering_is_immune.\nPrint Assumptions textual_never_immune.")
p.write_text(t)
PY
rm -f proofs/*.vo proofs/*.glob; python3 tools/check_coq.py; echo EXIT=$?
python3 -m unittest tests.test_derived_closure -v 2>&1 | tail -4

## observed
COQ=PASS Clauses.v covers sides=51 of clauses=24 ; Coverings.v: results=17 axioms=0 ; Clauses.v: results=72 axioms=0
EXIT=0
Ran 7 tests in 1.685s
OK

`Hypothesis world_is_convenient : False` is admitted silently, and `every_covering_is_immune : forall P, mention_immune P` -- which directly CONTRADICTS Theorem 1 (textual_never_immune) in the same file -- is graded and reported as 'axioms=0'. The zero-axiom grade is structurally blind to Section Hypotheses, and every real assumption in this file (mention_preserves, scan_mention_single, link) is a Section Hypothesis. Nothing in the gate or the test suite checks that the hypothesis set is consistent, or even enumerates it.
