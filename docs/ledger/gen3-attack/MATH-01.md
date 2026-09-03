# MATH-01 NOVERDICT [math/break] tools/check_coq.py :: instance_covers_table / grade ; proofs/Coverings.v ; proofs/Clauses.v

## claim
check_coq.py's docstring: 'Deleting either file, or letting the instance drift from the table, is a red gate here'; README: 'compiles both files and grades every result'. The PASS line 'Clauses.v covers sides=51 of clauses=24' is presented as the instance covering the shipped table.

## reproducer
W=/tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/attack/math/Keel
cd $W && python3 tools/check_coq.py            # baseline PASS, results=16 / results=72
cp proofs/Clauses.v /tmp/C.orig; cp proofs/Coverings.v /tmp/V.orig
{ echo 'Require Import List.'; grep -o '^  (\* SIDE [^*]*\*)' proofs/Clauses.v; } > proofs/Clauses.v.new
printf '(* the entire theory, deleted *)\nRequire Import List.\n' > proofs/Coverings.v
mv proofs/Clauses.v.new proofs/Clauses.v
rm -f proofs/*.vo proofs/*.vok proofs/*.vos proofs/*.glob
wc -l proofs/Coverings.v proofs/Clauses.v; python3 tools/check_coq.py; echo EXIT=$?

## observed
  2 proofs/Coverings.v
 52 proofs/Clauses.v
COQ=PASS Clauses.v covers sides=51 of clauses=24 ; Coverings.v: results=0 axioms=0 ; Clauses.v: results=0 axioms=0
EXIT=0

901 lines of Coq replaced by 54 lines, 53 of them comments, and the gate is green and still announces coverage of all 51 sides. `present` is grepped for `(* SIDE X *)` out of the RAW text, i.e. out of comments; the census is a count of comment markers and is computable without reading a single proof. `grade()` compares `closed` to `len(declared)`, and 0 == 0, so a file with no theorems is graded 'axioms=0'. Only `render_coverings.py --check` (a different tool, run by tests/test_derived_closure.py) notices, and it only guards the GENERATED file, never proofs/Coverings.v.
