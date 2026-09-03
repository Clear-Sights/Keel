# tests-04-dead-syspath [dead] tests/test_journal_and_wire.py (10 x `sys.path.insert(0, str(PLUGIN_ROOT))` + the `PLUGIN_ROOT = PLUGIN` alias), tests/test_probe_child_capability.py (1 x `sys.path.insert(0, str(PLUGIN))`)
LOC 12 -> 0

## description
test_journal_and_wire.py imports `tests.plant_support` at module top, and plant_support's line 34-36 is precisely `if str(PLUGIN) not in sys.path: sys.path.insert(0, str(PLUGIN))`. Ten test bodies then re-inserted the same path immediately before `from keel import ...` -- eleven inserts for a path that is already there, growing sys.path by ten entries per run and lengthening every subsequent import's search. The alias `PLUGIN_ROOT = PLUGIN` was a second name for one thing and went with them; test_probe_child_capability.py had the same insert before its `import tools.probe_child_capability`.

## diff
tests/test_journal_and_wire.py:
-from tests.plant_support import PLUGIN, smoke_replace
-
-PLUGIN_ROOT = PLUGIN
+from tests.plant_support import PLUGIN, dispatch_event, record, smoke_replace

     def _round_trip(self, subject):
-        sys.path.insert(0, str(PLUGIN_ROOT))
         from keel import dispatch

     def test_a_session_wide_deny_still_reads_as_session_wide(self):
-        sys.path.insert(0, str(PLUGIN_ROOT))
         from keel import dispatch
   ... (8 more identical removals at lines 398, 451, 457, 470, 480, 506, 514, 532)

tests/test_probe_child_capability.py:
-sys.path.insert(0, str(PLUGIN))
-import tools.probe_child_capability as probe_module  # noqa: E402
+import tools.probe_child_capability as probe_module  # noqa: E402  (PLUGIN is on sys.path: plant_support)

## gate
Ran 246 tests in 203.270s / OK | REPLAY sessions=26 passed=26 failed=0 | views match | coverings match | axioms=0 | eval/corpus matches 26 specs | git status --porcelain | wc -l = 16

## complexity
Space: sys.path stops growing by 10 entries over a test_journal_and_wire run, so every import after the first stops paying 10 extra stat() prefixes. Not separately timeable against noise at this module's 16 s.

## verdict
{"id": "tests-04-dead-syspath", "refuted": false, "reason": "Sustains, including the part I most expected to break. tests/plant_support.py:33-35 is `if str(PLUGIN) not in sys.path: sys.path.insert(0, str(PLUGIN))`, and tests/test_journal_and_wire.py imports plant_support at module top (line 28) before any test body runs, so all ten inner inserts push a path that is already present -- pure duplication, and the sys.path growth the hunter describes is real. The risky one is tests/test_probe_child_capability.py, where the insert precedes `import tools.probe_child_capability`: REPO/tools and PLUGIN/tools BOTH exist and hold different files, so ordering looks load-bearing. It is not: neither directory has an __init__.py (`ls -a tools/`, `ls -a plugin/tools/`), so `tools` resolves as a namespace package whose __path__ merges every portion on sys.path, and tools.probe_child_capability is found in plugin/tools whatever the order -- and plant_support (imported at line 40, before the insert at 44) has already put PLUGIN on the path in any case. The PLUGIN_ROOT = PLUGIN alias has all its uses rewritten. Nothing fail-closed, no limit, no plant seam is touched.", "gate_output": "NOT RUN -- plan mode blocked edits and execution; gate taken as reported. Read-only checks: tests/plant_support.py:33-35 (the single conditional insert); tests/test_journal_and_wire.py:28 imports plant_support at module top; tests/test_probe_child_capability.py:40 imports plant_support, then 44 re-inserts and 45 imports tools.probe_child_capability; `ls -a tools/` and `ls -a plugin/tools/` -> no __init__.py in either, so `tools` is a namespace package."}
