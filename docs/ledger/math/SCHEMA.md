# Mathematics ledger for Keel (owner's check, 2026-09-02)
Purpose: if the code were built directly from the math there would be nothing to remove. Mark, GRANULARLY,
each code element against the math element it implements. What is left unmarked on either side is the
add/remove list. A code element that is CLOSE to a math element but not equal, and is the ONLY candidate
for it, is replaced with the corrected form.
Process (owner): built by Builder, audited by Review, signed off briefly by Owner sign-off; the edits likewise.

## Files (TSV, tab-separated, one row per element; no prose columns longer than 200 chars)
math.tsv    id | kind (Definition|Inductive|Constructor|Hypothesis|Variable|Theorem|Corollary|Section|Law) | source (file:line) | statement (one line, exact or faithfully condensed) | depends_on (ids, comma)
code.tsv    id | kind (function|branch|constant|regex|field|law-code|effect-name|hook-row|clause-side) | source (file:line-line) | what (one line: what it decides or computes) | reads (fields/inputs) | writes/returns
marks.tsv   math_id | code_id | relation (equal|instance|near|none) | evidence (one line: WHY equal / WHAT differs) | auditor (blank until Review) | verdict (blank until Review: confirm|reject|amend) | signoff (blank until sign-off)

## Granularity
- A math element is one definition/constructor/hypothesis/theorem, never a whole section.
- A code element is one decision: a branch (`if` arm), a predicate kind, a constant, one effect's measurement,
  one loader law (CLAUSE-* code), one hook row, one clause side of the table. Not whole functions unless the
  function is one decision.
- Where the "math" is not in proofs/ but in a stated law inside the code/docs (EFFECTS text, a loader law's
  sentence, a README limit), enter it in math.tsv with kind=Law and source pointing at the sentence.

## Sources
Math: proofs/Coverings.v, proofs/Clauses.v (generated: one row per class result + one per side comment), the
laws stated in plugin/keel/clauses.py docstrings (CLAUSE-* refusal codes), plugin/keel/effects.py EFFECTS text,
README.md "limits" and theorem citations.
Code: plugin/keel/{clauses,dispatch,effects,ledger,journal,wire}.py, plugin/hooks/{dispatch.sh,hooks.json},
plugin/keel/clauses.json (each side of each of the 24 rows).

## Marking rules
- equal: the code computes exactly the math element (same quantifier, same fail direction, same domain).
- instance: the code is one instantiation of a general result (e.g. a clause side of class `effect` for Thm 8).
- near: same intent, differs in a stated way (domain narrower/wider, fail direction, an extra case). Say what.
- none: a code element with no math element (candidate REMOVE) or a math element with no code (candidate ADD).
- A code element may be marked against several math elements and vice versa; one row per pair.
- Never mark on the name. Mark on what the code DOES against what the statement SAYS.
