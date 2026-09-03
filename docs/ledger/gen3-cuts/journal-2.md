# journal-2 [dead] journal._root
LOC 114 -> 112

## description
`_root` deferred `from .ledger import state_dir` into the function body -- the shape used to break an import cycle. There is no cycle: `keel.ledger` imports nothing from `keel.journal` (it imports only hashlib/json/os/pathlib/dataclasses), and `keel.dispatch` already imports both at module level. So the deferral defended an impossible state, and paid for it on every row written (`_append` calls `_root` per row, `note_session` per tool call). Hoisted to the module header; the body becomes the single expression it always was.

## diff
--- a/plugin/keel/journal.py
+++ b/plugin/keel/journal.py
 from datetime import datetime, timezone
 
+from .ledger import state_dir
+
 PLUGIN = "keel"
 
 
 def _root(root=None) -> pathlib.Path:
-    if root:
-        return pathlib.Path(root)
-    from .ledger import state_dir
-    return state_dir()
+    return pathlib.Path(root) if root else state_dir()

## gate
Same single green gate run (one built tree). The import order is exercised in both directions by tests/test_suite_imports_standalone.py, which imports every test module in a clean subprocess with PYTHONPATH stripped -- exit 0.
  unittest discover -s tests -> Ran 246 tests ... OK (exit 0); replay 26/26; views/coverings/coq/corpus all exit 0; git status --porcelain | wc -l -> 7

## complexity
Removes one `import` statement execution (a sys.modules lookup and a name bind) per journal row written and per `note_session` call -- i.e. per tool call of every session. journal.py executable lines 114 -> 112 (ast counter).

## verdict
{"id": "journal-2", "refuted": false, "reason": "SURVIVES. The claim is that the function-local import defends an import cycle that does not exist, and that is verifiable by reading: plugin/keel/ledger.py's module header imports only hashlib, json, os, pathlib and dataclasses -- nothing from the keel package -- so `from .ledger import state_dir` at journal.py's module level cannot close a cycle in either direction, and plugin/keel/dispatch.py already imports both at module level anyway. plugin/keel/__init__.py is a bare docstring, so package import pulls nothing that could reorder this. (a) Semantics of _root are identical: `pathlib.Path(root) if root else state_dir()` reproduces `if root: return pathlib.Path(root)` / `return state_dir()` exactly, including the falsy-root case (empty string, which both send to state_dir()). (b) The one live hazard I looked for -- that the deferred import was really preserving late binding, so a test patching keel.ledger.state_dir would stop reaching journal after hoisting -- does not exist: I grepped tests/, eval/ and tools/ and every occurrence of state_dir is either a local parameter name in tests/test_journal_and_wire.py and eval/replay.py or the KEEL_STATE_DIR environment variable, which is read INSIDE state_dir() at call time and is therefore unaffected by when the name was bound. Every test that redirects the store does it with KEEL_STATE_DIR or with an explicit root= argument, both of which still work. (c) tests/test_suite_imports_standalone.py imports every test module in a clean subprocess with PYTHONPATH stripped, so a genuine cycle or a load-order regression would surface there. (d) No fail-direction or coverage change: _root is pure path selection and touches no verdict. (e) The LOC delta is real and small: 114 -> 112 under the metric I reproduced (four lines out, two in). (f) The complexity claim -- one saved import statement execution per journal row and per note_session call -- is real but trivial (a sys.modules lookup and a name bind against a file open and a JSON dump); the hunter states it as such rather than overselling it, so the delta is not misrepresented.", "gate_output": "GATE NOT EXECUTED -- plan mode; the suite mutates plugin/keel/*.py via smoke_replace and so is not runnable read-only. Read-only evidence: plugin/keel/ledger.py's import block is `import hashlib, json, os, pathlib` plus `from dataclasses import dataclass, asdict` and contains no keel-package import, so no cycle exists for the deferral to break; plugin/keel/__init__.py is a docstring only. `grep -rn state_dir tests/ eval/ tools/ --include=*.py` returns only local parameter names (tests/test_journal_and_wire.py:35,43,482-489; eval/replay.py:45) -- nothing patches keel.ledger.state_dir, so hoisting the name does not defeat any test's redirection, which all go through KEEL_STATE_DIR (read inside state_dir at call time) or an explicit root= argument. No plant seam touches journal._root. journal.py loc_before 114 reproduced exa
