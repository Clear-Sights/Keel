# wire-1 [dead] wire.read_stdin
LOC 51 -> 47

## description
`read_stdin` had a three-level ladder: a `getattr(sys.stdin, "buffer", None)` probe, a try/except that converted a read failure into `data = None`, and then an `if data is not None` guard before decoding -- three branches to reach one of two outcomes. Both the missing-`buffer` case and the failed-read case already funnel to the same text fallback, so `try/except` states that once; and the only surviving reason for the `data is None` guard (a stream answering a read with None) produces `("", 0)` from `_decode_counting(b"")` -- exactly what the fallback `scrub_text(sys.stdin.read() or "")` would produce -- so `or b""` covers it with no branch. Behaviour is unchanged on every path, including the module's one guarantee: no surrogate code point leaves here.

## diff
--- a/plugin/keel/wire.py
+++ b/plugin/keel/wire.py
@@ read_stdin (docstring unchanged)
-    buffer = getattr(sys.stdin, "buffer", None)
-    if buffer is not None:
-        try:
-            data = buffer.read()
-        except (AttributeError, ValueError, OSError):
-            data = None
-        if data is not None:
-            return _decode_counting(data)
-    return scrub_text(sys.stdin.read() or "")
+    try:
+        # `or b""`: a stream that answers a read with None is the same empty envelope the text
+        # fallback would produce, so it needs no branch of its own.
+        data = sys.stdin.buffer.read() or b""
+    except (AttributeError, ValueError, OSError):
+        return scrub_text(sys.stdin.read() or "")
+    return _decode_counting(data)

## gate
Same single green gate run (one built tree). The wire boundary is exercised end-to-end by tests/test_journal_and_wire.py through the real shim on byte-level fixtures (bad-byte payload, BOM-prefixed payload, unpaired \\uD8xx escape, byte-count-vs-escape-count separation) -- all green.
  unittest discover -s tests -> Ran 246 tests ... OK (exit 0); replay 26/26 (each replay session is a real stdin envelope); views/coverings/coq/corpus all exit 0; git status --porcelain | wc -l -> 7

## complexity
No asymptotic change (one read of stdin either way); it removes two branches and one sentinel variable from the first thing that runs on every hook invocation. wire.py executable lines 51 -> 47, and its branch count on the happy path drops from 3 to 1 (ast counter; `grep -vE '^[[:space:]]*(#|$)'` reads 86 -> 82).

## verdict
{"id": "wire-1", "refuted": false, "reason": "SURVIVES, with one residual I could not turn into a break. The three-level ladder does collapse: the missing-`buffer` case and the failed-read case both funnel to the same text fallback, so one try/except states them once -- old `getattr(sys.stdin, 'buffer', None)` returning None becomes a caught AttributeError on `sys.stdin.buffer`, and old `data = None` after a caught read failure becomes the same `return scrub_text(sys.stdin.read() or '')`. The module's one guarantee is untouched: both exits still pass through scrub_text or _decode_counting, so no surrogate code point leaves. No fail-closed direction is dropped -- both the old and new unreadable paths reach dispatch.main's first except, which is DECLARED fail-open carriage ('carriage that blocks is worse than carriage that is absent'), so this is not a fail-closed seam at all. THE ONE DIVERGENCE I FOUND, and it is not enough: if `buffer.read()` returns None rather than bytes (a stream in non-blocking mode with nothing ready), the old code fell through to `sys.stdin.read()`, which could in principle return real text, while the new `or b\"\"` yields _decode_counting(b'') = ('', 0) and the envelope reads as empty -> unreadable -> fail-open allow with the clause table skipped. I could not make that reachable: it requires a non-blocking stdin, and the TextIOWrapper fallback over the same non-blocking buffer would not reliably return the payload either; both hosts spawn the hook on an ordinary blocking pipe; and the only stdin double in the suite (FakeStdin in tests/test_journal_and_wire.py, an io.BytesIO whose read() never returns None) does not exercise it. I record it as a residual rather than a refutation. Other checks: no plant seam anywhere in tests/ touches read_stdin, so no plant is re-pointed or defused by this cut; `sys.stdin` being None raises AttributeError out of read_stdin in both versions; a ValueError from a closed stream raises in both, just from a different line. The LOC delta is real and I verified it by hand from the statement structure -- old body is 8 statements (assign, if, try, assign, assign, if, return, return), new is 4 (try, assign, return, return), matching the claimed 51 -> 47, and the grep figure 86 -> 82 has the same delta; wire.py's loc_before of 51 reproduces exactly under the hunter's metric.", "gate_output": "GATE NOT EXECUTED -- plan mode; the suite mutates plugin/keel/*.py via smoke_replace and is not runnable read-only. Read-only evidence: no smoke_replace seam in tests/ names read_stdin or any byte of it (I enumerated every plant seam in the suite), so no plant is affected; the only stdin double is FakeStdin at tests/test_journal_and_wire.py:176-181, backed by io.BytesIO, whose read() cannot return None, so the single behavioural divergence I identified is unexercised by the gate in either direction; _decode_counting sits outside the try in both versions, so the exception surface of the decode path is unchanged. wi
