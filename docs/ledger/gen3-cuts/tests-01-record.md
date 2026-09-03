# tests-01-record [replication] tests/plant_support.py::record (new); removed 7 copies in tests/test_bidirectional_chain.py (x2), tests/test_c08_activation.py::passed, tests/test_clause_fields.py::_record, tests/test_journal_and_wire.py (KEYED_EFFECT, test_clean_terminal_is_recorded_as_a_positive_result), tests/test_subject_across_surfaces.py::record
LOC 44 -> 14

## description
Seven modules each carried the same dict comprehension `{n: [] if n in ('files_changed','files_removed','remote_ref_moved','pids_gone','pids_spawned') else False for n in effects.EFFECTS}` plus `rec['remote_landed']=None`. That is the product's own knowledge -- which effect names are list-valued -- restated seven times in the suite, each copy silently wrong the day EFFECTS gains a list-valued name. The product already spells it once: `effects.read_delta(state, event)` is the observer's answer for an act that touched nothing, and for an event naming no file it reads neither argument. One helper `record(**eff)` in plant_support now derives the record from `read_delta`, so the suite feeds the dispatcher the exact shape production feeds it. Also removed the two now-unused `from keel import effects` imports this exposed.

## diff
tests/plant_support.py (added):
+def record(**eff) -> dict:
+    """A full observation record for an act that changed nothing in the world, plus `eff`.
+    DERIVED, not restated. Seven test modules carried their own copy of one dict comprehension
+    that re-listed which effect names are list-valued -- a rule with seven homes ... `read_delta`
+    is the observer's OWN answer for an act that touched nothing (the host Read path) ...
+    `remote_landed` is NOT-EVALUABLE: nothing was pushed, so nothing landed."""
+    from keel import effects
+    rec = effects.read_delta(PLUGIN, {})
+    rec["remote_landed"] = None
+    rec.update(eff)
+    return rec

tests/test_c08_activation.py:
-from keel import effects
 def passed(command: str) -> dict:
-    record = {n: [] if n in ("files_changed", "files_removed", "remote_ref_moved", "pids_gone",
-                             "pids_spawned") else False for n in effects.EFFECTS}
-    record["remote_landed"] = None
-    record["report_pass"] = True
     return {"hook_event_name": "PostToolUse", "tool_name": "Bash",
-            "tool_input": {"command": command}, "keel_effect": record}
+            "tool_input": {"command": command}, "keel_effect": record(report_pass=True)}

tests/test_subject_across_surfaces.py:
-from keel import effects
-def record(**eff) -> dict:
-    rec = {n: [] if n in ("files_changed", ...) else False for n in effects.EFFECTS}
-    rec["remote_landed"] = None
-    rec.update(eff)
-    return rec
+from tests.plant_support import PLUGIN, REPO, record, smoke_replace

(same shape at the other five sites; full unified diff at /tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/tests.diff)

## gate
Ran 246 tests in 203.270s / OK | REPLAY sessions=26 passed=26 failed=0 | views match plugin/keel/clauses.json | proofs/Clauses.v matches plugin/keel/clauses.json | PASS Clauses.v covers sides=51 of clauses=24: instantiated=36 ... Coverings.v axioms=0 ... Clauses.v axioms=0 | eval/corpus matches 26 specs | git status --porcelain | wc -l = 16

## complexity
Space/knowledge: 7 writers of one list -> 1 derivation. No runtime cost change (read_delta is a dict build); measured suite total unchanged by this cut alone.

## verdict
{"id": "tests-01-record", "refuted": false, "reason": "Static analysis sustains the cut, with one scope caveat. The substantive risk is that read_delta does NOT produce the shape the seven hand-written copies produced: plugin/keel/effects.py:648-651 sets SEVEN names to [] (files_changed, files_removed, remote_ref_moved, pids_gone, pids_spawned, named_paths, named_pids), while every hand-written copy set only FIVE, leaving named_paths/named_pids as False. I chased both consumers of that difference and it is inert. (a) dispatch._subjects keys on record[effect] only for clauses whose subject is {'effect': ...}; the only such subjects in the shipped table are pids_gone (U03) and files_changed (U12,U13,U19) -- no clause keys on named_paths or named_pids, so _subjects never reads them. (b) dispatch._names does `named = record.get(_NAMED_BY.get(effect,''))` then `if isinstance(named,list) and subject in {...}` -- False is not a list and skips; [] is a list but `subject in set()` is False; both fall through to the tool_input.file_path branch identically. So no decision can differ. The [] form is in fact MORE faithful for the Bash acts these fixtures drive: production's own delta() reaches trace_effects, which sets named_paths = sorted(named) if quiet else [] (effects.py:568) -- a list, never False. _artifact_read(PLUGIN, {}) returns False at its first guard (no tool_input.file_path), so observed_read/remote_read match the old copies and no filesystem access is added. No fail-closed direction is dropped, no deny_reason/README/EFFECTS text is touched, no clause coverage moves. CAVEAT, not a refutation: the tree carries NINE hand-written copies of that comprehension, not seven -- tests/test_keyed_effects.py:28, tests/test_endings.py:42 and tests/test_write_surface.py:43 are untouched, so the rule still has four homes (plant_support plus those three) rather than one, and the 44->14 LOC delta covers only the seven converted sites.", "gate_output": "NOT RUN. Plan mode was active for this session and forbids edits and non-read-only tool use, so I could not apply the cut or run the gate. Gate-greenness is taken as the hunter reported it (246 tests OK / replay 26/26 / views, coverings, coq axioms=0 / corpus 26 / 16 changed files), not verified by me. Verified read-only instead: plugin/keel/effects.py:646-654 (read_delta's 7 list-valued names), plugin/keel/dispatch.py:143-176 (_NAMED_BY, _names, _subjects), plugin/keel/clauses.json (24 rows; effect subjects are only pids_gone and files_changed), effects.py:568 (trace_effects sets named_paths to a list), and `grep -rn ... tests/` showing 9 copies of the comprehension where the cut names 7."}
