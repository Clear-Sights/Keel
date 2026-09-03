# tests-07-event-surface-root [replication] tests/test_event_surface.py (module header, `_registered`, the dispatcher call)
LOC 6 -> 2

## description
plant_support.py's whole docstring is about why `root = Path(__file__).resolve().parents[1]` must be written once: it names a DIFFERENT directory in the development layout (plugin/tests/) than in the shipped one (tests/ at the repo root). test_event_surface.py opened with exactly that line plus its own `sys.path.insert(0, str(REPO / 'plugin'))` -- a second mechanism for the thing plant_support already does, and one that resolves to `plugin/plugin` in the development layout. test_fence.py had already been converted and says so in a comment; this was the module left behind. `REPO / 'plugin'` appeared three times and is now `PLUGIN`.

## diff
tests/test_event_surface.py:
 import dataclasses
 import json
-import os
-import pathlib
-import subprocess
-import sys
 import tempfile
 import unittest
 
-REPO = pathlib.Path(__file__).resolve().parents[1]
-sys.path.insert(0, str(REPO / "plugin"))
+from tests.plant_support import PLUGIN, run_dispatcher
 
 from keel import clauses as C          # noqa: E402
 from keel import dispatch              # noqa: E402

 def _registered(name: str) -> set[str]:
-    return set(json.loads((REPO / "plugin" / name).read_text())["hooks"].keys())
+    return set(json.loads((PLUGIN / name).read_text())["hooks"].keys())

## gate
Ran 246 tests in 203.270s / OK | REPLAY sessions=26 passed=26 failed=0 | views match | coverings match | axioms=0 | eval/corpus matches 26 specs | git status --porcelain | wc -l = 16

## complexity
Second derivation of the roots removed; the module is now byte-portable across the two layouts like the rest of the suite. Module time 1.7 s, unchanged.

## verdict
{"id": "tests-07-event-surface-root", "refuted": false, "reason": "Sustains, and the portability claim checks out exactly. tests/test_event_surface.py:33-34 is `REPO = pathlib.Path(__file__).resolve().parents[1]` followed by `sys.path.insert(0, str(REPO / 'plugin'))` -- a second, independent derivation of the roots that plant_support's whole module docstring exists to make once. In the development layout the suite sits at plugin/tests/, so parents[1] is plugin/ and REPO/'plugin' names plugin/plugin, which does not exist: the module was genuinely correct in only one of the two layouts it is meant to be byte-identical across, and test_fence.py had already been converted with a comment saying so. The cut is complete rather than partial: `grep -n 'os\\.|sys\\.|pathlib\\.|subprocess\\.' tests/test_event_surface.py` finds uses at only lines 33, 34, 136, 137, 139 -- every one of them inside the header or the inline dispatcher call the cut replaces -- so removing the four imports leaves no dangling reference, and json/tempfile/dataclasses stay because they are used elsewhere (pyflakes flags none of them). No decision, limit or plant seam is touched; the three REPO/'plugin' spellings collapse to PLUGIN, which is the same directory in the shipped layout and the correct one in the development layout.", "gate_output": "NOT RUN -- plan mode blocked edits and execution; gate taken as reported. Read-only checks: tests/test_event_surface.py:33-34 (the duplicate root derivation) and its only other os/sys/pathlib/subprocess uses at 136-141; tests/plant_support.py module docstring, which states the two-layout problem this line reintroduces; `grep -n REPO tests/test_event_surface.py` -> 33, 34, 43, 140, 141 only."}
