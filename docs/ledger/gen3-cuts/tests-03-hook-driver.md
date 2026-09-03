# tests-03-hook-driver [replication] tests/plant_support.py::hook_decision (new); tests/test_bidirectional_chain.py::TheChainComposesThroughTheRealHook._hook, tests/test_effects.py::TheDispatcherEnforcesAnEffect._hook
LOC 16 -> 12

## description
Both modules built `env = {**os.environ, KEEL_STATE_DIR, CLAUDE_PLUGIN_ROOT}`, ran `bash hooks/dispatch.sh` with `timeout=60`, and parsed `json.loads(stdout.strip() or '{}')` -- and one of them carried a three-line comment about `{}` being the allow envelope that the other did not. One `hook_decision(payload, state)` in plant_support, and the comment has one home. test_bidirectional_chain's `SHIM` constant and its whole `self.env` construction in setUp fall out with it.

## diff
tests/plant_support.py (added):
+def hook_decision(payload: dict, state, *, timeout=60) -> dict:
+    """One event through the SHIPPED shim, as the single decision object it printed. ...
+    Two modules wrote this call out identically; `{}` IS the allow envelope ..."""
+    done = subprocess.run(["bash", str(PLUGIN / "hooks" / "dispatch.sh")],
+                          input=json.dumps(payload), capture_output=True, text=True,
+                          timeout=timeout,
+                          env={**os.environ, "KEEL_STATE_DIR": str(state),
+                               "CLAUDE_PLUGIN_ROOT": str(PLUGIN)})
+    return json.loads(done.stdout.strip() or "{}")

tests/test_bidirectional_chain.py:
-SHIM = PLUGIN / "hooks" / "dispatch.sh"
     def setUp(self) -> None:
         self.tmp = tempfile.mkdtemp(prefix="keel-chain-")
-        self.env = dict(os.environ)
-        self.env["KEEL_STATE_DIR"] = str(pathlib.Path(self.tmp) / "state")
-        self.env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN)
+        self.state = pathlib.Path(self.tmp) / "state"
     def _hook(self, **payload) -> dict:
         payload.setdefault("session_id", SESSION)
         payload.setdefault("cwd", self.tmp)
-        proc = subprocess.run(["bash", str(SHIM)], input=json.dumps(payload),
-                              capture_output=True, text=True, env=self.env, timeout=60)
-        out = proc.stdout.strip()
-        return json.loads(out) if out else {}
+        return hook_decision(payload, self.state)

tests/test_effects.py:
     def _hook(self, **payload) -> dict:
         payload.setdefault("session_id", "fx")
         payload.setdefault("cwd", self.repo)
-        env = dict(os.environ, KEEL_STATE_DIR=str(self.state), CLAUDE_PLUGIN_ROOT=str(PLUGIN))
-        done = subprocess.run(["bash", str(SHIM)], input=json.dumps(payload), capture_output=True,
-                              text=True, env=env, timeout=60)
-        return json.loads(done.stdout.strip() or "{}")
+        return hook_decision(payload, self.state)

## gate
Ran 246 tests in 203.270s / OK | REPLAY sessions=26 passed=26 failed=0 | views match | coverings match | axioms=0 | eval/corpus matches 26 specs | git status --porcelain | wc -l = 16

## complexity
Two writers -> one. tests/test_subject_across_surfaces.py::send and tests/test_shim_visibility.py::run were left alone deliberately: they drive the shim with a DIFFERENT environment on purpose (HOME redirection, a broken KEEL_PYTHON) and read the raw string, so folding them in would have meant parameters, not subtraction.

## verdict
{"id": "tests-03-hook-driver", "refuted": false, "reason": "Sustains. The two folded bodies were genuinely identical in every parameter that reaches the shim: both built {**os.environ, KEEL_STATE_DIR, CLAUDE_PLUGIN_ROOT}, both ran `bash <PLUGIN>/hooks/dispatch.sh`, both used timeout=60, both parsed json.loads(stdout.strip() or '{}'). Nothing is softened -- the `{}`-is-allow convention is preserved verbatim, and CLAUDE_PLUGIN_ROOT (which the shim genuinely reads, dispatch.sh:6) is still set. I checked the two constants the cut drops: in tests/test_bidirectional_chain.py, SHIM appears only at its definition (line 47) and inside _hook (61-62), and self.env only at 54-56 and 62, so both fall out cleanly; pathlib survives because setUp still needs pathlib.Path(self.tmp). In tests/test_effects.py, SHIM is ALSO used at line 387 by a different test, and the hunter's diff correctly leaves the constant in place there and folds only _hook. The two shim drivers deliberately left alone (test_subject_across_surfaces::send, test_shim_visibility::run) do drive it with a different environment on purpose, so excluding them is right rather than lazy.", "gate_output": "NOT RUN -- plan mode blocked edits and execution; gate taken as reported. Read-only checks: `grep -n 'SHIM|self.env|subprocess\\.' tests/test_bidirectional_chain.py` -> SHIM only at 47 and 61-62, self.env only at 54-56 and 62; `grep -n 'SHIM' tests/test_effects.py` -> 43 (def) and 387 (a second, unfolded user); plugin/hooks/dispatch.sh:6 reads CLAUDE_PLUGIN_ROOT."}
