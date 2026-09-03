# check-coq-one-coqc-per-file [time] compile_and_index() called from both grade() and instance_covers_table()
LOC 121 -> 125

## description
check_coq.py ran coqc THREE times per invocation: once on Coverings.v, once on Clauses.v inside grade(), and a THIRD time on Clauses.v inside instance_covers_table(), which discarded the stdout and kept only the index it had just thrown away. grade() now takes the (stdout, index) its caller already has, and instance_covers_table() takes the index; main() compiles each file exactly once. No check was dropped -- the same stdout is graded and the same index is censused. Measured by monkeypatching subprocess.run: 3 coqc calls -> 2.

## diff
--- a/tools/check_coq.py
+++ b/tools/check_coq.py
-def grade(path: pathlib.Path) -> tuple[int, str]:
+def grade(path: pathlib.Path, stdout: str | None, index: dict[str, list[str]]) -> tuple[int, str]:
     text = path.read_text(encoding="utf-8")
     body = strip_comments(text)
     if IDENTITY.search(body):
         return 1, f"{path.name}: a result is proved by the identity, so it states nothing"
-    stdout, index = compile_and_index(path)
     if stdout is None:
@@
-def instance_covers_table() -> tuple[int, str]:
+def instance_covers_table(index: dict[str, list[str]]) -> tuple[int, str]:
@@
-    _, index = compile_and_index(INSTANCE)
@@ main()
-    lines = []
+    lines, index = [], {}
     for path in (THEORY, INSTANCE):
-        status, note = grade(path)
+        stdout, index = compile_and_index(path)  # ONE coqc per file; INSTANCE is last, so the
+        status, note = grade(path, stdout, index)
         if status:
             print(f"COQ=FAIL {note}", file=sys.stderr)
             return 1
         lines.append(note)
-    status, note = instance_covers_table()
+    status, note = instance_covers_table(index)   # index it leaves is the one censused here

## gate
COQ=PASS Clauses.v covers sides=51 of clauses=24: instantiated=36 empty-by-class[always=7 tool-enum=8] ; Coverings.v: results=14 axioms=0 parameters=16 ; Clauses.v: results=1 axioms=0 parameters=0 (rc=0); full gate: 246 tests OK, REPLAY 26/26, all --check pass, 4 files changed

## complexity
Measured by wrapping subprocess.run and importing check_coq as a module: BEFORE 3 calls ['coqc','coqc','coqc'] in 1.150s; AFTER 2 calls ['coqc','coqc'] in 0.626s. End-to-end `python3 tools/check_coq.py` median over 5 runs: 1.238s -> 0.689s (-44%), of which ~0.24s is this cut and ~0.30s the smaller Clauses.v. check_coq.py grew 4 code lines net: -1 for the removed compile, +2 to record glob R-references, +2 for the orphan-enumeration guard that cut 1 needs.

## verdict
{"id": "check-coq-one-coqc-per-file", "refuted": false, "reason": "NOT INDEPENDENTLY GATED (plan mode active); verdict from static verification only.\n\nThe time claim is real and I verified the call sites by reading tools/check_coq.py in full: main() line 153 calls grade(THEORY) -> compile_and_index at line 82 (coqc #1); grade(INSTANCE) -> line 82 again (coqc #2); instance_covers_table() at line 126 calls compile_and_index(INSTANCE) a THIRD time and discards the stdout, keeping only an index identical to the one grade() had just computed and dropped. Three coqc invocations per run, two of them on the same file with the same inputs. The cut collapses that to one per file. 3 -> 2 is a real, checkable delta, not a rounding claim.\n\nNo check is dropped: the same stdout is graded (grade's closed/Axioms checks) and the same index is censused. Ordering is preserved - Coverings.v is compiled before Clauses.v, which requires it - and the early-return-on-failure structure of main() is unchanged, so a non-compiling INSTANCE still fails in grade() before instance_covers_table() ever sees the index.\n\nTwo honest notes, neither meeting the refutation bar:\n1. LOC goes UP (+4, 121 -> 125). The report says so plainly and attributes the +4 to cut 1's needs (recording glob R-references, and the orphan guard). Cut 2 in isolation is about -1 line. The claim is a TIME cut, and the time claim is what I checked.\n2. instance_covers_table(index) now consumes the loop variable left behind after 'for path in (THEORY, INSTANCE)', so correctness depends on INSTANCE being iterated last. The report's own comment flags this. It is fragile rather than wrong.\n\nOne behavioural nuance: originally grade() ran the IDENTITY regex BEFORE compiling, so a file with an identity proof failed without paying a compile; after the cut main() compiles first. That makes the failure path marginally slower, never more permissive - the identity check still fires and still fails closed.", "gate_output": "NOT RUN - plan mode active. Static verification of the claim instead: three compile_and_index() call sites confirmed by reading tools/check_coq.py (line 82 reached twice via grade() from main() line 153, plus line 126 inside instance_covers_table()), the third discarding proc.stdout and recomputing the index grade() already had."}
