# EFF-01 NOVERDICT [agnostic/break] effects.report_effects / trace_effects; effects report_paths; clauses U12, U13, U19

## claim
report_paths = 'an act that changed no file, ref or process printed a path the worktree snapshot holds' -- the guard for 'look at the target before applying'.

## reproducer
mkdir -p /tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/attack && cp -r /home/user/Keel /tmp/.../attack/eff2
Script: /tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/attack/hook.py  (drives the REAL plugin/hooks/dispatch.sh on a real git repo, KEEL_STATE_DIR set)
Run: cd /tmp/.../attack && setsid python3 hook.py > h.out 2>&1 </dev/null; cat h.out
Key sequence inside: SessionStart -> Read observed.json -> Read remote.json -> Bash 'printf changed > a.txt' -> Bash '# keel-guard: U12 U13 U19\necho a.txt'
Pure-observer cell: setsid python3 /tmp/.../attack/forge.py (and forge3.py against the CURRENT /home/user/Keel working tree)

## observed
h.out:
  rewrite pre: allow owed after: ['U12', 'U13', 'U19']
  FORGED GUARD 'echo a.txt' pre: allow | owed now: []
forge.out / f3.out: "echo a.txt" -> ['pre_image', 'report_paths'].
Nothing was listed, no path was read, no diff was taken: the six characters 'a.txt' printed to stdout discharged all three 'look before you write' clauses, and (subject = session_id) licensed them for the rest of the session.
