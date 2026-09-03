# render-coq-string-dead [dead] coq_string()
LOC 2 -> 0

## description
`coq_string()` was defined and called from nowhere. The generated Clauses.v contains no Coq string literal -- every emitted token is an identifier, a comment, or fixed proof text -- so nothing ever needed quoting. Deleted; grep confirms zero references remain in the repo.

## diff
--- a/tools/render_coverings.py
+++ b/tools/render_coverings.py
-def coq_string(text: str) -> str:
-    return '"' + text.replace('"', '""') + '"'
-
-

## gate
proofs/Clauses.v matches plugin/keel/clauses.json ; COQ=PASS ... ; 246 tests OK ; REPLAY 26/26

## complexity
No runtime effect; one fewer function in the generator's surface.

## verdict
{"id": "render-coq-string-dead", "refuted": false, "reason": "NOT INDEPENDENTLY GATED (plan mode active); verdict from static verification only.\n\nThe claim is exactly true and cheap to check: 'grep -rn coq_string' over the entire tree (including tests, eval, plugin, docs and README) returns ONE line - the definition itself at tools/render_coverings.py:47-48. Zero call sites.\n\nI also checked the premise rather than just the reference count: the generated proofs/Clauses.v contains no Coq string literal at all. Every token side_block() emits is an identifier, a comment, or fixed proof text; the only occurrences of the word 'string' are the Coq TYPE 'string' passed as the Text/Program parameter, never a quoted literal. So the escaping problem coq_string() solves never arises for this generator, and it could not have been called even in principle by any of the class branches.\n\nTwo lines, no runtime effect, no fail-closed direction, no coverage. Nothing to break.", "gate_output": "NOT RUN - plan mode active. Static verification: 'grep -rn coq_string' over /home/user/Keel returns exactly one hit, tools/render_coverings.py:47 (its own def). proofs/Clauses.v contains no Coq string literal (checked by reading the header and the emitted blocks)."}
