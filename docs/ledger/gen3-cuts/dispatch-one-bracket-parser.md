# dispatch-one-bracket-parser [replication] _record's hand-rolled first-`[`-to-next-`]` scan
LOC 24 -> 20

## description
`_record` writes two kinds of journal row from a rendered message. The block row already used `_bracketed_ids` (a regex constrained to `[A-Za-z0-9._-]{1,40}`); the deny row hand-rolled a second parser with `reason.find('[')` / `reason.find(']', start)` and 4 lines of index arithmetic, which accepted ANY bytes between the brackets. Two readers of one fact, disagreeing about what a clause id even is. The deny row now takes the first id the shared parser names. `_keyed_reason` always renders the clause's own id first, and every shipped clause id matches the regex (checked: 24 ids, max length 25, all within [A-Za-z0-9._-]{1,40}).

## diff
--- a/plugin/keel/dispatch.py
+++ b/plugin/keel/dispatch.py
@@ _record @@
             reason = str(wire_out.get("permissionDecisionReason") or "")
-            clause_id = ""
-            start = reason.find("[")
-            end = reason.find("]", start)
-            if start != -1 and end != -1:
-                clause_id = reason[start + 1:end]
-            journal.note_deny(event, clause_id, _subject_of(reason), reason)
+            # ONE PARSER FOR "the clause ids this message names", shared with the block row
+            # below. A deny used to hand-roll a second one (first `[` to the next `]`), and a
+            # second reader of one fact is a second answer waiting to happen: that one accepted
+            # anything between the brackets, so the two rows could disagree about what a clause
+            # id even looks like. `_keyed_reason` writes the clause's own id first.
+            named = _bracketed_ids(reason)
+            journal.note_deny(event, named[0] if named else "", _subject_of(reason), reason)

## gate
Ran 245 tests in 207.617s / OK (includes tests/test_journal_and_wire.py's deny-row law and its two plants) ; REPLAY sessions=26 passed=26 failed=0 ; views/coverings/coq/corpus all exit 0 ; git status --porcelain | wc -l = 3

## complexity
-4 LOC in `_record`, and `_bracketed_ids` goes from one caller to two, which is what makes it a shared rule rather than a helper for one site. Both parsers return "" for a message with no brackets (the `_closed_not_evaluable` deny), so the not-evaluable row is unchanged.

## verdict
{"id": "dispatch-one-bracket-parser", "refuted": false, "reason": "Applied in rd-c6 (1 file). Gate green. LOC real: 557 -> 553 NCNB (-4). BEHAVIOUR: byte-identical decisions and ledger rows over all 27 corpus sessions; both deny-row laws stay green (`test_deny_row_names_clause_and_subject` -> 'A01', `test_keyed_deny_row_names_the_operand` -> 'U10'). Equivalence holds because every deny message that carries brackets is rendered by `_keyed_reason`, which writes `[{clause.id}]` at position 0, and the not-evaluable deny carries no brackets so both parsers return ''. COVERAGE GREW, measured: breaking `_bracketed_ids`' charset reddens 3 tests on the CUT tree INCLUDING both deny-row tests, whereas the identical break on PRISTINE leaves the deny-row tests green and reddens only the block row and the bidirectional chain. That is exactly what a one-parser cut is supposed to buy, and it is the second reader that makes it real. ONE LATENT DEPENDENCY THE CUT CREATES, which I report as a caveat rather than a refutation: equivalence rests on every clause id matching `[A-Za-z0-9._-]{1,40}`. All 24 shipped ids do (max length 25), but I could find NO id-shape validation anywhere -- not in clauses.py's loader (which reads `data['id']` raw) and not in tests/test_fence.py. An id outside that charset would make the new parser SKIP to the next bracketed token in the message and record a different clause than the one that denied, which is precisely the record-vs-reality disagreement the `_KEYED_ON_RX` comment two screens below treats as the cardinal sin. It does not refute the cut as applied -- the log is deliberately powerless and no fail direction moves -- but the derived form should carry the id-shape check the parser now silently assumes.", "gate_output": "cd /tmp/.../simplify/rd-c6 && python3 -m unittest discover -s tests -> Ran 252 tests in 316.978s / OK (exit 0) ; eval/replay.py -> REPLAY sessions=27 passed=27 failed=0 (exit 0) ; render_views.py --check (exit 0) ; render_coverings.py --check (exit 0) ; check_coq.py -> COQ=PASS (exit 0) ; generate_corpus.py --check -> matches 27 specs (exit 0) ; git status --porcelain | wc -l = 1 (M plugin/keel/dispatch.py)."}
