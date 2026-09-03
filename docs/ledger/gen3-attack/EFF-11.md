# EFF-11 CONFIRMED [agnostic/break] effects.at_stop (`if not memory.get('net_out'): out['remote_ref_moved'], out['remote_landed'] = [], True`); effect remote_landed; clause T02

## claim
remote_landed = 'every remote head this session moved is equal to a local ref (MEASURED AT THE REMOTE)'; T02: 'let the ending measure the remote... Keel lists the remote itself at Stop'.

## reproducer
setsid python3 /tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/attack/m5.py > m5.out 2>&1 </dev/null; cat m5.out
Bare origin + two clones; the OTHER clone pushes a foreign commit to origin/main; then the session pushes 'git push -q origin HEAD:refs/heads/side' over the local path (no TCP). at_stop is called as Keel calls it, then again with session memory net_out forced True to show what the honest measurement returns.
See also m4.out cell E3 (push to a second remote).

## observed
m5.out:
  origin tip after the FOREIGN push: c3c83f7721   local HEAD: ba34b7e9f8
  delta: net_out=False remote_ref_moved=['refs/remotes/origin/side']
  at_stop (as Keel computes it)         : {'remote_ref_moved': [], 'remote_landed': True}
  at_stop with the remote actually asked: {'remote_ref_moved': ['refs/heads/main'], 'remote_landed': False}
The same function, on the same repository, one second apart: Keel's ending says CLEAN, the measurement it claims to make says NOT LANDED. T02's terminal guard is discharged by an observation that was never taken.
