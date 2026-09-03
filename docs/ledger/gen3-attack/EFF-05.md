# EFF-05 CONFIRMED [agnostic/break] effects.delta -> report_effects(response.get('stdout'), ...); clauses U01, U20, U24, U25, C08

## claim
report_pass = 'the act printed a test-report datum with no failures'; report_fail = 'the act printed a report datum with failures or findings'.

## reproducer
setsid python3 /tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/attack/m6.py > m6.out 2>&1 </dev/null; cat m6.out
cells: F2 = "echo 'PASS'; exit 7";  F3 = "echo '3 passed'; echo '2 failed' 1>&2" (delta called with both stdout and stderr in tool_response)

## observed
m6.out:
  F2 'echo PASS; exit 7' rc=7 -> report_pass=True report_nowarn=True
  F3 failures on stderr      -> report_pass=True report_fail=False (stderr='2 failed')
A run that failed with a nonzero status, or that reported 2 failures on stderr, is recorded as a clean PASS and pays U01/U20/U24 and activates C08. Symmetrically, a checker that prints its FAIL on stderr can never pay C08's or U25's guard (false negative on report_fail).
