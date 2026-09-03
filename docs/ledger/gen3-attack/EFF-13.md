# EFF-13 CONFIRMED [agnostic/weakness] effects.delta files_changed / files_removed; clauses U12, U13, U19, U20

## claim
'AN OBSERVATION IS THE ACT'S ONLY IF IT IS ASSIGNED TO THE ACT.' files_changed = 'a file has different content after the act'.

## reproducer
setsid python3 /tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/attack/m6.py > m6.out 2>&1 </dev/null; cat m6.out
cell F1: effects.snapshot, then a background thread rewrites a.txt 200 ms in, while the observed act is 'cat a.txt', then effects.delta

## observed
m6.out:
  F1 'cat a.txt' while another process wrote -> files_changed=['a.txt'] (the act only read)
A read-only act is charged with a rewrite it did not perform, so U12/U13/U19 are demanded of it -- and, since the demands are keyed on session_id, the operator pays them once with any 'look' and the clause is then licensed for the real rewrite that follows. Editors, watchers, sibling agents and background builds all feed this channel.
