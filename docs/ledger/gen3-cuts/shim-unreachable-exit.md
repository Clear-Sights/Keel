# shim-unreachable-exit [dead] the trailing `exit 0` after `fail_open "Python dispatcher failed"`
LOC 33 -> 32

## description
`fail_open` is the fail-open exit: its last statement is `exit 0`, and `exit` inside a POSIX sh function exits the shell. The `exit 0` on the line after the call can therefore never run. It is also not a safety net in disguise -- if `fail_open` ever returned instead of exiting, the script would fall off its end with the status of its last command (`printf`), which is 0: the same answer. Cut the line, kept a comment saying why nothing follows the call.

## diff
--- a/plugin/hooks/dispatch.sh
+++ b/plugin/hooks/dispatch.sh
@@ -77,5 +77,6 @@ if [ -n "$out" ]; then
 fi
 [ "$status" -eq 0 ] && exit 0
 [ "$status" -eq 2 ] && exit 2
+# `fail_open` exits 0 itself -- it IS the fail-open exit -- so nothing follows it. A trailing
+# `exit 0` here was a second spelling of that exit that the shell can never reach.
 fail_open "Python dispatcher failed"
-exit 0

## gate
Ran 245 tests in 207.617s / OK (includes tests/test_shim_visibility.py -- both wiring-fault classes, the exit-2 forwarding law, and both shim plants -- and tests/test_fence.py's shipped-file checks) ; sh -n plugin/hooks/dispatch.sh exit 0 ; REPLAY sessions=26 passed=26 failed=0 ; git status --porcelain | wc -l = 3

## complexity
-1 LOC. Nothing about the fail direction moves: exit 2 is still forwarded from both the output and the no-output branches, and the wiring fault still emits its `systemMessage` and exits 0 -- both proven by test_shim_visibility's plants, which are untouched.

## verdict
{"id": "shim-unreachable-exit", "refuted": false, "reason": "Applied in rd-c9 (1 file). Gate green, and `sh -n plugin/hooks/dispatch.sh` exits 0. LOC real: shim 33 -> 32 NCNB. UNREACHABILITY VERIFIED, not assumed: `fail_open`'s last statement is `exit 0` and `exit` inside a POSIX sh function exits the shell; none of the four call sites is in a subshell (`|| fail_open` after a test, a cd, a `command -v`, and the final top-level call), so nothing after the last call can run. I DROVE ALL FOUR WIRE PATHS against a fake interpreter on both trees and they are byte-identical: nonzero death with no output -> exit 0 + {\"systemMessage\":\"keel hook wiring fault: Python dispatcher failed\"}; exit 2 with no output -> exit 2; exit 2 WITH output -> the decision printed, exit 2; exit 0 with output -> output, exit 0. So the fail-OPEN direction and the exit-2 forwarding in both branches are unchanged. I ALSO TESTED THEIR OWN HYPOTHETICAL, which is the only way the removed line could be a net: I changed `fail_open` to `return 0` instead of exiting, in both trees -- both still emit the wiring-fault object and exit 0, because falling off the end returns the status of the last command (`printf`, 0). So the line was a second spelling of an exit already taken, with nothing under it. Both tests/test_shim_visibility.py plant seams (the systemMessage printf, and `if [ -n \"$out\" ]`) are untouched and neither anchors on the removed line; tests/test_fence.py's shipped-file checks are green.", "gate_output": "cd /tmp/.../simplify/rd-c9 && python3 -m unittest discover -s tests -> Ran 252 tests in 315.253s / OK (exit 0) ; eval/replay.py -> REPLAY sessions=27 passed=27 failed=0 (exit 0) ; render_views.py --check (exit 0) ; render_coverings.py --check (exit 0) ; check_coq.py -> COQ=PASS (exit 0) ; generate_corpus.py --check -> matches 27 specs (exit 0) ; git status --porcelain | wc -l = 1 (M plugin/hooks/dispatch.sh) ; sh -n plugin/hooks/dispatch.sh exit 0. CUMULATIVE CHECK: all nine cuts together in rd-all also pass the whole gate -- Ran 252 tests OK, REPLAY 27/27, views/coverings/coq/corpus exit 0, 3 changed files, dispatch.py 557 -> 543 NCNB and shim 33 -> 32."}
