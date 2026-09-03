# EFF-02 NOVERDICT [agnostic/break] effects.trace_effects report_ref; clause U09

## claim
report_ref = 'an act that changed no file, ref or process printed a ref name or commit id the ref snapshot holds' -- the guard for 'know the ref'.

## reproducer
setsid python3 /tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/attack/forge.py > forge.out 2>&1 </dev/null; cat forge.out
setsid python3 /tmp/.../attack/m2.py > m2.out 2>&1 </dev/null; cat m2.out
cells: 'echo main'; 'echo <HEAD sha>'; and 'cat note.txt' where note.txt merely CONTAINS the sha

## observed
forge.out: 'echo main' -> ['pre_image', 'report_ref']; 'echo c5966245...' -> ['pre_image', 'report_ref']
m2.out: F: 'cat note.txt' (sha in file) -> report_ref=True
U09's guard ('git rev-parse --verify REF, git branch, git show-ref, or any listing of refs') is paid by echoing the word 'main' or by cat-ing a file that has a sha in it. No ref was ever read.
