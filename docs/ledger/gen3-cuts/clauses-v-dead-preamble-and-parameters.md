# clauses-v-dead-preamble-and-parameters [space] the emitted `Section Instance.` / `Variable Text` / `Variable scan` / `Variable mention` / `End Instance.`, `Import ListNotations.`, `Open Scope string_scope.`, and `List` in the Require
LOC 10 -> 2

## description
The generated Clauses.v opened a Section with three Variables. `scan` and `mention` were referenced by NO branch of side_block -- every emitted statement is about `string` and `effect`, never about a scanner or an embedding. `Text` was used only by the positive branch, which the shipped table never reaches; quantifying it inside the statement (`forall (T D : Type) (cl ob : T -> option D)`) removes the need for it entirely, so the Section itself goes too. `Import ListNotations` had no `[...]` to notate and `Open Scope string_scope` had no string literal to scope (see the coq_string cut). check_coq's PARAMETERS check stays fail-closed and was re-verified: planting `Section S. Variable sneaky : Prop. End S.` into Clauses.v gives 'COQ=FAIL Clauses.v: Section parameters [sneaky] are not on the PARAMETERS line'. The gate now reports `Clauses.v: results=1 axioms=0 parameters=0`.

## diff
--- proofs/Clauses.v (generated header)
-   PARAMETERS: Text scan mention *)
-Require Import List String.
-Import ListNotations.
 Require Import Coverings.
-Open Scope string_scope.
-
-Section Instance.
-  Variable Text : Type.
-  Variable scan : Text -> list (Segment string).
-  Variable mention : Text -> Text.
...
-End Instance.
+   PARAMETERS: *)
+Require Import String.
+Require Import Coverings.

--- a/tools/render_coverings.py (the positive statement quantifies its own Text)
-            f"  Theorem {name}_rejects_false_claims : forall (D : Type) (cl ob : Text -> option D) c d d',",
-            f"    cl c = Some d -> ob c = Some d' -> d <> d' -> ~ positive Text D cl ob c.",
+        "  forall (s : PositiveSide) (T D : Type) (cl ob : T -> option D) c d d',",
+        "    cl c = Some d -> ob c = Some d' -> d <> d' -> ~ positive T D cl ob c.",

## gate
COQ=PASS ... Clauses.v: results=1 axioms=0 parameters=0 ; teeth re-verified: planted `Variable sneaky` -> COQ=FAIL 'Section parameters [sneaky] are not on the PARAMETERS line'

## complexity
Part of the coqc Clauses.v 0.563s -> 0.323s measurement; removing the `List` require and ListNotations alone drops one module load per compile.

## verdict
{"id": "clauses-v-dead-preamble-and-parameters", "refuted": false, "reason": "NOT INDEPENDENTLY GATED (plan mode active); verdict from static verification only.\n\nEvery factual premise checks out against the generated file and its glob:\n(a) Clauses.glob records exactly 'var 414:417 Instance Text', 'var 438:441 Instance scan', 'var 487:493 Instance mention' - the three Section parameters the header's 'PARAMETERS: Text scan mention' line declares.\n(b) 'scan' and 'mention' appear in NO emitted statement. Reading proofs/Clauses.v: every theorem is over 'string' and 'effect', e.g. 'name_agnostic string (effect string E d)'. Neither a scanner nor an embedding is ever mentioned. 'Text' is used only by the positive branch, which the shipped table never reaches (test_derived_closure.py:46 measures the census as {effect:31, tool-enum:8, always:7, composed:5} - zero positive sides). Quantifying T inside the positive statement removes the last use, so the Section itself goes.\n(c) 'Import ListNotations' has no [...] notation to serve in the generated body, and 'Open Scope string_scope' has no string literal to scope (see cut 3 - the file has none). Dropping 'List' from the Require is safe because the only list former used is Coq.Init's 'list', and Coverings.v itself Requires List.\n\nThe PARAMETERS fail-closed check survives intact and I checked its regex by hand rather than trusting the report: 're.search(r\"PARAMETERS:\\s*([^*]*)\\*\\)\", text)' against a header ending 'PARAMETERS: *)' matches with group(1)=\"\", giving stated=set() against params=[] - equal, so PASS; and any planted 'Variable sneaky' adds a 'var' entry not on the line, so 'stated != set(params)' fires. The report's re-verification ('COQ=FAIL Clauses.v: Section parameters [sneaky] are not on the PARAMETERS line') is exactly what that code path produces. The teeth are not softened - the check simply now compares an empty declared set to an empty measured set instead of a 3-element set to a 3-element set, and 'no hypothesis may be added undeclared' is unchanged.\n\nNote the dependency direction: this cut is a PRECONDITION of cut 1, not merely a companion. See my cut-1 verdict - the orphan guard's ind/ref name comparison only works outside a Section, because in-Section defs index bare ('Text') while references index qualified ('Instance.Text').", "gate_output": "NOT RUN - plan mode active. Static verification: Clauses.glob shows exactly the three Section vars ('var 414:417 Instance Text', 'var 438:441 Instance scan', 'var 487:493 Instance mention'); proofs/Clauses.v body reads only 'string' and 'effect' - no scan, no mention, no string literal, no [...] notation. PARAMETERS regex traced by hand: 'PARAMETERS: *)' yields stated=set(), matching params=[]; a planted Variable still reddens."}
