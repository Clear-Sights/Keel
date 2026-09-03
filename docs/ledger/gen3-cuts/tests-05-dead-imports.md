# tests-05-dead-imports [dead] tests/test_bypass.py (contextlib, dataclasses, io, datetime.date), tests/test_clause_fields.py (keel.clauses as C), tests/test_effects.py (sys), tests/test_journal_and_wire.py (time), tests/test_occasion_algebra.py (load_default), tests/test_probe_cache.py (dispatch), tests/test_probe_child_capability.py (json, re)
LOC 11 -> 0

## description
Eleven imports that no name in their module reads, measured with `python3 -m pyflakes tests/*.py` on the pristine tree (11 findings, all 'imported but unused'). Four of them are in one file. `from keel.clauses import _base_predicate, load_default` and `from keel import clauses as C, dispatch` were trimmed to the half that is used rather than deleted whole. After the cut `python3 -m pyflakes tests/*.py` exits 0 with no output -- the five further imports my other cuts made dead (subprocess/os/sys/pathlib/json across five files) are included in that zero.

## diff
tests/test_bypass.py:
-import contextlib
-import dataclasses
-import io
-from datetime import date

tests/test_clause_fields.py:
-from keel import clauses as C

tests/test_effects.py:
-import sys

tests/test_journal_and_wire.py:
-import time

tests/test_occasion_algebra.py:
-from keel.clauses import _base_predicate, load_default
+from keel.clauses import _base_predicate

tests/test_probe_cache.py:
-from keel import clauses as C, dispatch
+from keel import clauses as C

tests/test_probe_child_capability.py:
-import json
-import re

## gate
python3 -m pyflakes tests/*.py -> (no output), exit 0. Whole gate: Ran 246 tests in 203.270s / OK | REPLAY sessions=26 passed=26 failed=0 | views match | coverings match | axioms=0 | eval/corpus matches 26 specs | git status --porcelain | wc -l = 16

## complexity
Time: `import io`/`contextlib`/`dataclasses`/`datetime`/`re`/`json` dropped from module import paths; below measurement noise per module.

## verdict
{"id": "tests-05-dead-imports", "refuted": false, "reason": "Sustains, and this one I could confirm directly rather than infer: I ran `python3 -m pyflakes tests/*.py` on the pristine tree and got exactly the eleven findings the cut names, in the same files and at the same line numbers -- test_bypass (contextlib:12, dataclasses:13, io:15, datetime.date:21), test_clause_fields (keel.clauses as C:35), test_effects (sys:31), test_journal_and_wire (time:26), test_occasion_algebra (keel.clauses.load_default:43), test_probe_cache (keel.dispatch:19), test_probe_child_capability (json:31, re:32). Unused names cannot change behaviour. The two partial trims are safe rather than lucky: `load_default` comes from keel.clauses, already imported for _base_predicate, so dropping the name imports no less module and loses no import side effect; and keel.dispatch in test_probe_cache is a sibling of keel.clauses, which that module still imports, so the package is still initialised. Note that test_bypass's contextlib/io removal is not undermined by test_journal_and_wire::_main_on, which imports both LOCALLY inside the function body.", "gate_output": "NOT RUN as a whole -- plan mode blocked edits and execution; the suite/replay/coq/corpus gate is taken as reported. I did run the read-only half myself: `cd /home/user/Keel && python3 -m pyflakes tests/*.py` -> 11 findings, byte-identical to the cut's target list (test_bypass.py:12,13,15,21; test_clause_fields.py:35; test_effects.py:31; test_journal_and_wire.py:26; test_occasion_algebra.py:43; test_probe_cache.py:19; test_probe_child_capability.py:31,32). The claimed post-cut `pyflakes -> exit 0` is unverified."}
