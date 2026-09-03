# EFF-09 CONFIRMED [agnostic/break] effects head_moved / head_reset / files_changed; clauses U09, U20

## claim
head_moved = 'HEAD names a different commit after the act'; head_reset = 'HEAD moved to an ancestor of where it was, and the worktree changed with it'.

## reproducer
setsid python3 /tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/attack/matrix.py > mx.out 2>&1 </dev/null; cat mx.out
cells:
  B4 'git checkout -q -b tmpb && git checkout -q main'
  B5 'printf two > a.txt && git add -A && git commit -qm x && git reset -q --hard HEAD~1'

## observed
mx.out:
  B4 -> {'head_moved': False, 'head_switched': False, 'head_reset': False, 'files_changed': []}
  B5 -> {'head_moved': False, 'head_reset': False, 'files_changed': []}
A branch switch (U09's occasion) and a commit-then-hard-reset (U20's occasion, the destructive one the clause names) both record nothing, so no guard is ever owed for them.
