# MATH-08 NOVERDICT [math/break] plugin/keel/effects.py :: report_effects, _lists_itself, REPORT_PASS/REPORT_CLEAN/WARNING_LINE ; plugin/keel/clauses.py :: classify_side (kind=='effect' -> 'effect'), derive_closure -> 'world'

## claim
effects.py header cites 'Coverings.v Theorem 3' and says the effect 'is read from the world: the worktree, the refs'. derive_closure: "`world`: the observer measures it." Theorem 8 comment: 'it cannot even SEE which program was invoked, so it depends on no language, English or otherwise.' Theorem 1: a textual non-vacuous covering is NEVER mention-immune, and the loader refuses textual sides outright.

## reproducer
W=/tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/attack/math/Keel
cd $W/plugin && python3 - <<'PY'
from keel import effects as F
print("rename-only flip:")
print("  report_self('ps aux'):", F.report_effects("ps aux\n1 2 3","ps aux")["report_self"])
print("  report_self('PS aux'):", F.report_effects("ps aux\n1 2 3","PS aux")["report_self"])
print("mentions discharge effect-class guards:")
for c,o in [("echo 'the suite would print 12 passed'","the suite would print 12 passed\n"),
            ("echo '0 findings'","0 findings\n"),("echo 'all checks passed'","all checks passed\n"),
            ("echo 'PASS'","PASS\n")]:
    r=F.report_effects(o,c); print(f"  {c:42} pass={r['report_pass']} clean={r['report_clean']} nowarn={r['report_nowarn']}")
c="12 passed"
print("Theorem 1 test:  P(c)=",F.report_effects(c,"x")["report_pass"]," P(mention c)=",F.report_effects("echo '%s'"%c,"x")["report_pass"])
PY

## observed
rename-only flip:
  report_self('ps aux'): True
  report_self('PS aux'): False
mentions discharge effect-class guards:
  echo 'the suite would print 12 passed'     pass=True clean=False nowarn=True
  echo '0 findings'                          pass=False clean=True nowarn=False
  echo 'all checks passed'                   pass=False clean=True nowarn=False
  echo 'PASS'                                pass=True clean=False nowarn=True
Theorem 1 test:  P(c)= True  P(mention c)= True

Two correspondence failures. (1) `report_self`/`report_listing` call `_lists_itself(text, command)`, which SPLITS THE COMMAND STRING and tests its segments against the output -- so the effect's value is a function of the program's spelling: `ps aux` -> True, `PS aux` -> False with identical output. The Coq model `effect E d segs := E d` says renaming changes nothing it sees; here it flips the verdict. (2) `report_pass`, `report_clean`, `report_nowarn`, `report_fail`, `report_signature` are English-language regexes over stdout -- exactly Coverings.v's `textual` class (P c -> infix c d -> P d), non-vacuous, hence by the file's own Theorem 1 never mention-immune -- and indeed `echo '12 passed'` and `echo '0 findings'` satisfy them. A census over clauses.json shows 17 shipped sides across 12 clauses (C08, C09, U01, U03, U08, U09, U10, U12, U13, U19, U20, U24, U25) classed `effect`/closure=`world` while resting on these text-derived effects. The loader refuses a regex on `tool_input.command` as textual, but the same textual covering relocated to the act's stdout is admitted and then certified name-agnostic by MATH-07's contentless theorem.
