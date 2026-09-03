# EFF-03 NOVERDICT [agnostic/break] effects.trace_effects report_pids / report_listing; clauses U03, C09-checker-excludes-self

## claim
report_pids = 'the act printed at least two pids that were alive at the snapshot'; report_listing = 'report_pids, and the output holds no segment of the act's own command: a listing that excluded the observer'.

## reproducer
setsid python3 /tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/attack/m2.py > m2.out 2>&1 </dev/null; cat m2.out
cell C runs the act 'echo <caller-pid> 1' through effects.snapshot/delta; cell D is the honest 'ps -eo pid | head -5' for comparison

## observed
m2.out:
  C: 'echo <pid> 1'         -> report_pids=True report_listing=True report_self=False
  D: 'ps -eo pid | head -5' -> report_pids=True report_listing=True report_self=False
The forged echo is INDISTINGUISHABLE from the real process listing. C09's guard 'produce a listing that excludes the observer' and U03's guard 'produce a process listing' are both paid by `echo 1 <pid>`.
