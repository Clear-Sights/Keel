# dispatch-unreachable-defaults [dead] _subject's `re.error`, _construction's `getattr` fallback, _context's `event_name` default, main's `repaired = escaped = 0`
LOC 4 -> 3

## description
Four unreachable things, cut together. (1) `except (IndexError, re.error)` around `m.group(...)`: a Match object raises IndexError for a group that is not there and never raises re.error -- the pattern was already compiled by the `re.search` above. (2) `getattr(clause, 'construction', '')`: `construction` is a declared `Clause` field with a default of "", and every test double in the suite carries it -- the fallback names no reachable state. (3) `_context(text, event_name='SessionStart')`: both callers pass the name explicitly; the default was a third answer nobody asked for. (4) `repaired = escaped = 0` as main's first statement: every path that reaches the `if repaired or escaped` has assigned both from `wire.read_stdin()` / `wire.scrub()`, and every path that does not returns from the except block first.

## diff
--- a/plugin/keel/dispatch.py
+++ b/plugin/keel/dispatch.py
@@ _subject @@
-        except (IndexError, re.error):
+        except IndexError:

@@ _construction @@
-    anchor = getattr(clause, "construction", "") or ""
+    anchor = clause.construction or ""

@@ module @@
-def _context(text: str, event_name: str = "SessionStart") -> dict:
+def _context(text: str, event_name: str) -> dict:

@@ main @@
 def main() -> int:
-    repaired = escaped = 0
     try:
         raw, repaired = wire.read_stdin()

## gate
Ran 245 tests in 207.617s / OK (includes tests/test_journal_and_wire.py's repair-count law and its plant, which inserts `repaired += escaped` at the seam immediately after the removed line) ; REPLAY sessions=26 passed=26 failed=0 ; git status --porcelain | wc -l = 3

## complexity
-1 LOC plus three zero-line branch removals. None of these is a fail-direction: (1) and (2) are handler arms for exceptions/attributes that cannot occur, (3) and (4) are defaults every caller overrides. NOT cut, deliberately: `session_start`'s `event.get('hook_event_name', 'SessionStart')` and `reconcile`'s `event.get(..., 'Stop')` are unreachable via HANDLERS but their absence would make `event_name` None -- and a None event name in reconcile's `if cl.event != event_name` enforces nothing, which is a fail-OPEN. Those stay.

## verdict
{"id": "dispatch-unreachable-defaults", "refuted": false, "reason": "Applied in rd-c8 (1 file). Gate green. LOC real: 557 -> 556 NCNB plus three zero-line branch removals. BEHAVIOUR: byte-identical decisions and ledger rows over all 27 corpus sessions. Each of the four checked separately. (1) `re.error` cannot escape `Match.group` -- the pattern was compiled by the `re.search` on the line ABOVE, which is outside the try, so a bad pattern raises there and lands in the per-clause isolation exactly as before; IndexError (bad group index or name) is the only arm reachable. (2) `construction: str = \"\"` is a declared field of the frozen `Clause` dataclass, so `getattr`'s default names no state the loader can produce, and every test double in the suite declares it (tests/test_journal_and_wire.py's three doubles all carry it). Crucially the STATED LIMIT survives: 'an absent or misshapen anchor costs this sentence and nothing else' -- MISSHAPEN is still handled by `CONSTRUCTION_ANCHOR.fullmatch`, and only the unreachable ABSENT-ATTRIBUTE arm is gone. (3) `_context` has exactly two callers (session_start, user_prompt_submit), both passing `event_name` explicitly; no test calls it. (4) Every path that reaches `if repaired or escaped` has assigned both inside the try, and every path that does not returns from the except first -- and the repair-count plant seam is `b'        event, escaped = wire.scrub(event)\\n    except Exception as exc:'`, which does not include the deleted line, so the plant is intact and green. They also correctly REFUSED to cut `session_start`'s and `reconcile`'s `event.get(..., default)`, where a None event name would make `cl.event != event_name` enforce nothing -- a fail-OPEN. Coverage parity: planting `anchor = \"\"` is green on both the cut tree and pristine, so nothing was lost.", "gate_output": "cd /tmp/.../simplify/rd-c8 && python3 -m unittest discover -s tests -> Ran 252 tests in 317.769s / OK (exit 0) ; eval/replay.py -> REPLAY sessions=27 passed=27 failed=0 (exit 0) ; render_views.py --check (exit 0) ; render_coverings.py --check (exit 0) ; check_coq.py -> COQ=PASS (exit 0) ; generate_corpus.py --check -> matches 27 specs (exit 0) ; git status --porcelain | wc -l = 1 (M plugin/keel/dispatch.py)."}
