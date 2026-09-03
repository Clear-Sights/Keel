# dispatch-one-header-scan [replication] _guard_marker, _allow_marker, and the three `isinstance(command, str)` guards in pre_tool_use / _open_effect_denial / post_tool_use
LOC 37 -> 34

## description
_guard_marker and _allow_marker each carried their own copy of the leading-comment-block scan -- the loop whose stopping rule IS the exemption's whole security (the module comment says so: it was narrowed twice because the wider form let a command supply its own licence in a heredoc). Two copies means the plant that defends it (tests/test_bypass.py) defended only one of them: the guard-marker copy had no plant at all. On top of that, three call sites each spelled `isinstance(command, str)` -- three spellings of 'an event with no command field commits to nothing and exempts nothing'. Extracted one generator `_header(command)` that owns both the type guard and the stopping rule; both markers iterate it. The plant seam moved with it, and now covers BOTH markers because there is only one loop to widen.

## diff
--- a/plugin/keel/dispatch.py
+++ b/plugin/keel/dispatch.py
-def _guard_marker(command: str) -> set[str]:
-    """The clause ids a Bash call commits to pay, from its leading comment header."""
+def _header(command):
+    # WHERE A MARKER MAY APPEAR, SPELLED ONCE. Both markers are read from this block and for the
+    # same reason (see ALLOW above): two copies of the loop is how the next marker gets read from
+    # somewhere wider. The scan stops dead at the first line that is not blank and not a comment.
+    #
+    # A MISSING COMMAND IS AN EMPTY HEADER, said here rather than at each call site. All three
+    # call sites guarded `isinstance(command, str)` themselves -- three spellings of "an event
+    # with no command field commits to nothing and exempts nothing", any one of which could be
+    # forgotten by the fourth reader.
+    if not isinstance(command, str):
+        return
     for line in command.split("\n"):
         stripped = line.strip()
         if not stripped:
             continue
         if not stripped.startswith("#"):
-            return set()
-        found = GUARD.match(stripped)
+            # Command text. Everything from here on is payload, not preamble.
+            return
+        yield stripped
+
+
+def _guard_marker(command) -> set[str]:
+    """The clause ids a Bash call commits to pay, from its leading comment header."""
+    for line in _header(command):
+        found = GUARD.match(line)
         if found:
             return {p for p in re.split(r"[,\s]+", found.group(1)) if p}
     return set()

@@ _allow_marker @@
-    for line in command.split("\n"):
-        stripped = line.strip()
-        if not stripped:
-            continue
-        if not stripped.startswith("#"):
-            # Command text. Everything from here on is payload, not preamble.
-            return None
-        found = ALLOW.match(stripped)
+    for line in _header(command):
+        found = ALLOW.match(line)
         if found:
             return "keel", found.group(1)
-        found = ALLOW_LEGACY.match(stripped)
+        found = ALLOW_LEGACY.match(line)

@@ pre_tool_use @@
-    bypass = _get(event, "tool_input.command")
-    marker = _allow_marker(bypass) if isinstance(bypass, str) else None
+    marker = _allow_marker(_get(event, "tool_input.command"))

@@ _open_effect_denial and post_tool_use (identical hunk in both) @@
-    command = _get(event, "tool_input.command")
-    committed = _guard_marker(command) if isinstance(command, str) else set()
+    committed = _guard_marker(_get(event, "tool_input.command"))

--- a/tests/test_bypass.py   (the plant seam follows the rule it defends; rule 3)
+++ b/tests/test_bypass.py
@@ TheAllowMarkerIsAHeaderNotAPayload.test_the_check_can_fail @@
-        # The seam is the one line that decides a header from a payload. Widen it back to a
-        # whole-string search and the heredoc walks straight through.
+        # The seam is the one line that decides a header from a payload. It now lives in
+        # `_header`, the single scanner BOTH markers read, so widening it back to a whole-string
+        # search lets the heredoc walk through the guard marker as well as the allow marker --
+        # one plant where the duplicated loop needed two.
         smoke_replace(self, PLUGIN / "keel" / "dispatch.py",
                       b'        if not stripped.startswith("#"):\n'
                       b'            # Command text. Everything from here on is payload, not preamble.\n'
-                      b"            return None\n",
+                      b"            return\n",

## gate
Ran 245 tests in 207.617s / OK ; REPLAY sessions=26 passed=26 failed=0 ; views match plugin/keel/clauses.json ; proofs/Clauses.v matches plugin/keel/clauses.json ; COQ=PASS Clauses.v covers sides=51 of clauses=24 ; Coverings.v: results=16 axioms=0 ; Clauses.v: results=72 axioms=0 ; eval/corpus matches 26 specs ; git status --porcelain | wc -l = 3 (plugin/keel/dispatch.py, plugin/hooks/dispatch.sh, tests/test_bypass.py)

## complexity
Same work per call (one pass over the leading comment lines); the scan is now generated lazily rather than re-implemented. The test change is not a softening: it plants the SAME fault at the SAME rule, and now that rule is the only one, so the plant's blast radius grew from one marker to two. Verified: `git stash`-free check -- the seam bytes appear exactly once in the file.

## verdict
{"id": "dispatch-one-header-scan", "refuted": false, "reason": "Applied verbatim in /tmp/.../simplify/rd-c1 (dispatch.py + tests/test_bypass.py, 2 files). Gate green. LOC real: dispatch.py 557 -> 554 non-blank non-comment (`grep -vE '^\\s*(#|$)' | wc -l`). BEHAVIOUR: I drove all 27 corpus sessions (241 events) in-process through pristine and the cut, dumping every decision and every ledger row (minus hash/prev): byte-identical. Non-string commands also identical (decisions digest 5448d2a4 both trees) -- the type guard moved from three call sites into `_header` with no change at the wire. TRIED TO BREAK IT: (a) the plant seam moved correctly -- planting the widened stop in the shared `_header` on the cut tree goes RED with 3 failures (test_TEETH_a_marker_in_a_heredoc_body_does_not, test_TEETH_a_marker_below_the_command_does_not, test_the_check_can_fail). (b) The coverage claim is not just rhetoric, it is measured: I removed the header stop from `_guard_marker` ONLY on the PRISTINE tree and the whole 252-test suite stayed GREEN -- while `_guard_marker(\"rm -rf build/ ; cat > n.md <<'EOF'\\n# keel-guard: A02\\nEOF\")` then returns {'A02'}, i.e. a command supplies its own commitment from a heredoc body and walks past `_open_effect_denial`'s refusal (`if cl.id in committed: progress = True; continue`). That live hole is undefended before the cut and defended after it. No fail-closed direction dropped, no limit softened, no plant lost (all 41 smoke_replace anchors resolve -- a missing one fails `assertIn(old, original, 'plant seam changed')`). ONE REPORTING ERROR, not a refutation: their gate_output lists 3 changed files including plugin/hooks/dispatch.sh, which this cut does not touch; the real count is 2.", "gate_output": "cd /tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/simplify/rd-c1 && python3 -m unittest discover -s tests -> Ran 252 tests in 228.035s / OK (exit 0) ; python3 eval/replay.py -> REPLAY sessions=27 passed=27 failed=0 (exit 0) ; render_views.py --check -> views match plugin/keel/clauses.json (exit 0) ; render_coverings.py --check -> proofs/Clauses.v matches plugin/keel/clauses.json (exit 0) ; check_coq.py -> COQ=PASS Clauses.v covers sides=51 of clauses=24 ; Coverings.v results=16 axioms=0 ; Clauses.v results=74 axioms=0 (exit 0) ; generate_corpus.py --check -> eval/corpus matches 27 specs (exit 0) ; git status --porcelain | wc -l = 2 (M plugin/keel/dispatch.py, M tests/test_bypass.py). NOTE: this checkout is 8df26db, not the 5f5dfa6 named in the brief (5f5dfa6 exists but is not an ancestor), so the baseline is 252 tests / 27 replay sessions, not 245 / 26."}
