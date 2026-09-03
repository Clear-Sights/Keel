# tests-02-dispatch-driver [replication] tests/plant_support.py::run_dispatcher, ::dispatch_event (new); removed 6 hand-written copies in tests/test_clause_fields.py (_denying_clause, _drive_event, _clauses_at_stop), tests/test_occasion_algebra.py (_drive, _post), tests/test_event_surface.py (test_every_registered_event_renders_a_decision), tests/test_journal_and_wire.py::run
LOC 49 -> 29

## description
Six call sites across four modules each wrote `subprocess.run([sys.executable, '-m', 'keel.dispatch'], input=..., text=True, capture_output=True, env={**os.environ, 'KEEL_STATE_DIR': state, 'CLAUDE_PLUGIN_ROOT': str(PLUGIN), 'PYTHONPATH': str(PLUGIN)})` followed by `json.loads(stdout or '{}')`. Two of the six disagreed with the other four (journal's copy set neither CLAUDE_PLUGIN_ROOT nor PYTHONPATH and leaned on cwd instead; event_surface's copy respelled PLUGIN as REPO/'plugin'), which is exactly the drift six writers produce. One `run_dispatcher` returns the raw CompletedProcess (the surface test reads exit code and stderr), and `dispatch_event` returns the single decision object on top of it.

## diff
tests/plant_support.py (added):
+def run_dispatcher(payload, state, *, cwd=None, timeout=None) -> subprocess.CompletedProcess:
+    return subprocess.run(
+        [sys.executable, "-m", "keel.dispatch"], input=payload,
+        text=not isinstance(payload, bytes), capture_output=True, timeout=timeout,
+        cwd=None if cwd is None else str(cwd),
+        env={**os.environ, "KEEL_STATE_DIR": str(state),
+             "CLAUDE_PLUGIN_ROOT": str(PLUGIN), "PYTHONPATH": str(PLUGIN)})
+
+def dispatch_event(event, state, **kwargs) -> dict:
+    payload = event if isinstance(event, (str, bytes)) else json.dumps(event)
+    done = run_dispatcher(payload, state, **kwargs)
+    out = done.stdout if isinstance(done.stdout, str) else done.stdout.decode()
+    return json.loads(out or "{}")

tests/test_clause_fields.py::_denying_clause:
-    event = json.dumps({...})
-    done = subprocess.run(
-        [sys.executable, "-m", "keel.dispatch"], input=event, text=True, capture_output=True,
-        env={**os.environ, "KEEL_STATE_DIR": state, "CLAUDE_PLUGIN_ROOT": str(PLUGIN),
-             "PYTHONPATH": str(PLUGIN)})
-    body = json.loads(done.stdout or "{}")
+    body = dispatch_event({"hook_event_name": "PreToolUse", "tool_name": "Bash",
+                           "session_id": session, "cwd": "/tmp",
+                           "tool_input": {"command": command}}, state)

tests/test_journal_and_wire.py:
 def run(raw: bytes, state_dir: Path) -> dict:
-    env = os.environ.copy()
-    env["KEEL_STATE_DIR"] = str(state_dir)
-    proc = subprocess.run([sys.executable, "-m", "keel.dispatch"], input=raw,
-                          capture_output=True, env=env, cwd=str(PLUGIN_ROOT))
-    return json.loads(proc.stdout.decode() or "{}")
+    return dispatch_event(raw, state_dir, cwd=PLUGIN)

tests/test_event_surface.py:
-                    done = subprocess.run(
-                        [sys.executable, "-m", "keel.dispatch"], input=json.dumps(payload),
-                        text=True, capture_output=True, timeout=120,
-                        env={**os.environ, "KEEL_STATE_DIR": state,
-                             "CLAUDE_PLUGIN_ROOT": str(REPO / "plugin"),
-                             "PYTHONPATH": str(REPO / "plugin")})
+                    done = run_dispatcher(json.dumps(payload), state, timeout=120)

## gate
Ran 246 tests in 203.270s / OK | REPLAY sessions=26 passed=26 failed=0 | views match plugin/keel/clauses.json | proofs/Clauses.v matches plugin/keel/clauses.json | PASS Clauses.v ... axioms=0 | eval/corpus matches 26 specs | git status --porcelain | wc -l = 16

## complexity
Six writers of one child-process environment -> one. Child-process count per test unchanged (this is a spelling cut, not a call cut).

## verdict
{"id": "tests-02-dispatch-driver", "refuted": false, "reason": "Sustains. The only behavioural delta I could find is that the folded driver adds CLAUDE_PLUGIN_ROOT and PYTHONPATH to the two sites that previously omitted them, and both additions are inert here. CLAUDE_PLUGIN_ROOT has zero readers in the Python dispatcher -- `grep -rn CLAUDE_PLUGIN_ROOT plugin/keel/*.py` returns nothing; the only reader is plugin/hooks/dispatch.sh:6, and this driver invokes `python3 -m keel.dispatch` directly, never the shim. clauses.load_default resolves its table from `Path(__file__).resolve().with_name('clauses.json')` (clauses.py:774), not from the environment, so the added variable cannot move which table loads. PYTHONPATH=PLUGIN is redundant with the cwd=PLUGIN the journal copy already used. No test asserts the ABSENCE of either variable, so no coverage of a fallback path is lost. The bytes/str handling reproduces both call styles: `text = not isinstance(payload, bytes)` gives text=False for test_journal_and_wire's raw-bytes calls (every call site there passes bytes -- the one dict-shaped call at line 141 is .encode()d at 143) and text=True for the str call sites, and the stdout decode branch mirrors it. test_event_surface's site keeps timeout=120 and reads returncode/stderr as str, unchanged. The two disagreeing copies the hunter cites are real: journal set neither CLAUDE_PLUGIN_ROOT nor PYTHONPATH, and event_surface respelled PLUGIN as REPO/'plugin'.", "gate_output": "NOT RUN -- plan mode blocked edits and execution; gate taken as reported. Read-only checks that back the verdict: `grep -rn CLAUDE_PLUGIN_ROOT plugin/keel/*.py` -> no matches; plugin/hooks/dispatch.sh:6 is the sole reader; plugin/keel/clauses.py:774 `return Path(__file__).resolve().with_name('clauses.json')`; tests/test_journal_and_wire.py:35-40 (old run, cwd-only) and 141-143 (.encode()); tests/test_event_surface.py:136-141 (old inline call)."}
