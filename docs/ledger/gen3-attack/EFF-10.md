# EFF-10 CONFIRMED [agnostic/break] effects.delta (`made = git log -1 --format=%ct`; `existed = ... int(made) < int(before['t'])`); effects commit_signed, head_switched; clauses U08, U09

## claim
commit_signed = 'the act CREATED the commit HEAD now names, and that commit carries a signature'; head_switched = 'HEAD moved to a commit that already existed before the act'.

## reproducer
setsid python3 /tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/attack/m2.py > m2.out 2>&1 </dev/null; cat m2.out
Cells A and B write a real commit object carrying a gpgsig header via `git hash-object -t commit -w` + `git update-ref HEAD`, once with a current committer timestamp and once with one 100000 s in the past.

## observed
m2.out:
  A: fresh signed commit     -> head_moved=True head_switched=False commit_signed=True
  B: BACKDATED signed commit -> head_moved=True head_switched=True  commit_signed=False
Same act, same signature, one field changed: the signed commit stops being observed as signed (U08 never demands 'produce a signature datum') and is instead reported as a checkout (a spurious U09). The observer's 'created vs existed' distinction is decided by data the act controls.
