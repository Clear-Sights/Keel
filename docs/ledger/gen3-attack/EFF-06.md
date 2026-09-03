# EFF-06 CONFIRMED [agnostic/break] effects._artifact_read; effects observed_read / remote_read; clauses A01, A02, A03, T01, T02, U03, U09

## claim
observed_read = 'the host Read tool RETURNED Keel's own worktree measurement (observed.json), as written'; remote_read likewise.

## reproducer
setsid python3 /tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/attack/hook3.py > h3.out 2>&1 </dev/null; cat h3.out
The PostToolUse Read is sent through the real shim with tool_response={"error":"File content (25000 tokens) exceeds maximum allowed tokens; the file was NOT returned"} and, for remote.json, {"error":"EACCES"}

## observed
h3.out:
  D0 first act denied: deny ... owed: ['A01','A02','A03']
  D1 Read that ERRORED: owed now: ['A03']
  D2 remote.json Read that ERRORED: owed: []
A Read whose content was never returned to the model discharges A01/A02 (and T01), and the same for A03/remote_read. The clause text ('Read Keel's worktree measurement ... the branch, HEAD and dirty paths Keel measured') is satisfied by a Read that returned nothing.
