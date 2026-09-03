# MATH-03 NOVERDICT [math/break] tools/check_coq.py :: RESULT regex, grade()

## claim
'every declared result ... is `Print Assumptions`-ed, and every one is closed under the global context -- zero axioms'

## reproducer
W=/tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/attack/math/Keel
cd $W
# control: the naive form IS caught
cat >> proofs/Coverings.v <<'EOF'

Axiom cheat : forall P : Prop, P.
Theorem naive_bad : forall (T:Type) (x y : T), x = y.
Proof. intros. exact (cheat _). Qed.
Print Assumptions naive_bad.
EOF
rm -f proofs/*.vo proofs/*.glob; python3 tools/check_coq.py; echo EXIT=$?
# evasion A: declaration not at line start
git checkout proofs/Coverings.v 2>/dev/null || cp /tmp/V.orig proofs/Coverings.v
cat >> proofs/Coverings.v <<'EOF'

Axiom cheat : forall P : Prop, P.
Definition anchor := 0. Theorem hidden_bad : forall (T:Type) (x y:T), x = y.
Proof. intros. exact (cheat _). Qed.
EOF
rm -f proofs/*.vo proofs/*.glob; python3 tools/check_coq.py; echo EXIT=$?
# evasion B: attribute prefix
cp /tmp/V.orig proofs/Coverings.v
cat >> proofs/Coverings.v <<'EOF'

Axiom cheat2 : False.
#[local] Theorem hidden_bad2 : forall P:Prop, P.
Proof. destruct cheat2. Qed.
EOF
rm -f proofs/*.vo proofs/*.glob; python3 tools/check_coq.py; echo EXIT=$?

## observed
control:   COQ=FAIL Coverings.v: compiled, but 16 of 17 results are closed under the global context -- one rests on an axiom / EXIT=1
evasion A: COQ=PASS ... Coverings.v: results=16 axioms=0 / EXIT=0
evasion B: COQ=PASS ... Coverings.v: results=16 axioms=0 / EXIT=0

Both `Definition anchor := 0. Theorem hidden_bad : ...` and `#[local] Theorem hidden_bad2 : ...` keep a live global `Axiom` in the file that the gate reports as axioms=0. Combined with MATH-02, the poisoned file carrying BOTH a `Hypothesis : False` and a global `Axiom : forall P, P` passes check_coq.py (exit 0), render_coverings.py --check (exit 0), and all 7 tests in tests/test_derived_closure.py.
