# Audit — marks.carriage.tsv (auditor: review, 2026-09-02)

Source read: `plugin/keel/ledger.py`, `journal.py`, `wire.py`, `plugin/hooks/dispatch.sh`,
`plugin/hooks/hooks.json`, `README.md`, `proofs/Coverings.v`, `plugin/keel/clauses.py`,
`plugin/keel/dispatch.py`, `tests/`. Output: `marks.carriage.audited.tsv` (128 rows, same columns).

## 1. Counts

| verdict | n |
|---|---|
| confirm | 107 |
| amend | 16 |
| reject | 5 |
| **total** | **128** |

- amend: C-CAR-007, 008, 012, 013, 033, 036, 037, 046, 056, 106, 107, 108, 109, 122, 126, 128.
- reject: C-CAR-110, 116, 117, 119, 120 (all five paired to M-LAW-057; wrong law — see ADD-1).
- Relation changes: 012 `none`→`near` (M-LAW-067); 033 `equal`→`near` (M-LAW-067); 110/116/117/119/120 `near`(M-LAW-057)→`none`(`-`). All other amendments keep the relation and rewrite the evidence.

## 2. REMOVE (code no statement, law, comment-argument or test asks for)

1. **`plugin/keel/journal.py:241` — `list(clause_ids)[:10]`** (C-CAR-078). Nothing asks for it: no Law in `math.tsv`, no README sentence, no comment in `note_block`'s docstring (journal.py:230-237, which argues only about `open_count` being `None` vs `0`), and no test (`tests/test_journal_and_wire.py:138` asserts only that `clause_ids` is non-empty; :459-460 uses 0 ids). It is also actively harmful to the row's stated job: `open_count` is written untruncated from `_stated_count`, so a Stop block owing 14 clauses writes `open_count:14` beside 10 ids — the log whose purpose is telling outcomes apart (journal.py:9-12) emits a row that disagrees with itself. The usual bound-the-payload argument does not reach here: the ids come from `dispatch._bracketed_ids` (dispatch.py:968), already bounded by the regex to ≤40 chars and by the table to 24 rows, so the cap protects at most ~960 bytes. Remove the slice; keep `[str(c) for c in ...]`.

That is the only REMOVE. Each of the builder's other three candidate groups is kept, with the exact ask:

- **C-CAR-007/008 (`legacy_state`, ledger.py:96-101)** — KEPT. `ledger.py:72-83` states the duty as a law of the estate ("A HARD RENAME OWES THE OLD NAME A SENTENCE") with a measurement; `tests/test_bypass.py:179-184` plants exactly the C-CAR-007 lines via `smoke_replace` and requires red; C-CAR-008's ledger-FILE-not-directory test is argued at ledger.py:90-94 and held by `tests/test_bypass.py:161-169`.
- **C-CAR-012/013 (`derive_id`, `Demand.id`, ledger.py:121-143)** — KEPT, and mis-marked: `derive_id` is the licence key M-LAW-067 is a statement about, not carriage (see REPLACE/STATEMENT-FIX). `Demand.id` as a property is argued at ledger.py:132-134 and relied on by nine call sites in `dispatch.py`.
- **C-CAR-106/107/108/109 (`fail_open` case arms, dispatch.sh:25-28)** — KEPT. `dispatch.sh:22-23` is a fail-direction argument in the code's own comment: "The message text is a fixed literal per branch: interpolating a path or interpreter name would put unescaped bytes inside a JSON string." Arms 107 and 108 are precisely what strip `$plugin_root` and `$python` out of the emitted JSON string; arm 109 is what makes `visible_fault` always set, so `:30` can never print an empty message. `tests/test_shim_visibility.py:57-61` plants that printf and requires red; :117-119 requires the default arm's text.

Adjacent constants examined and kept: `_STALE_CLAIM_SECONDS` (C-CAR-056) is a stated limit (journal.py:97-105) joined to the 60 s `hooks.json` timeout by `tests/test_bounds.py`; `COMPACT_AT` (C-CAR-036/037) carries the measured DL-10 argument at ledger.py:259-266; `subject[:200]`/`reason[:400]`/`detail[:400]` (C-CAR-075, 080) bound unbounded host strings, unlike the ids cap.

## 3. ADD (statements the carriage claims but does not satisfy; laws it relies on that no page states)

1. **State as a Law: the fail-open / fail-closed split.** The tree says it twice in its own words — `plugin/hooks/dispatch.sh:33-35` ("Carriage must fail OPEN, so a wiring fault emits `{}` and exits 0; exit 2 would deny every tool call for the rest of the session") and `plugin/keel/journal.py:250-251` ("Keel's answer is split by design -- carriage open, decision closed") — and `math.tsv` has no such row. Five carriage rows (C-CAR-110, 116, 117, 119, 120) were pinned to M-LAW-057 for want of it; M-LAW-057 (Coverings.v:198-203) is about a miss on a clause's occasion vs guard side and reaches no carriage. `journal.note_fault`'s `failed_closed` field (journal.py:246-255) exists only to make this split countable, and it too has no law to be countable against.
2. **State as a Law: the ledger set difference.** `ledger.py:187-193` states it as law — "DEMAND, DISCHARGE AND OPEN ARE NOT THREE CONCEPTS. They are one set difference, `demanded - discharged` ... a licence is membership in the second set and NOTHING else. Deliberately not 'absent from the first'" — and `README.md:76-77` repeats it ("A licence is an **observed discharge**, never an absent demand"). Neither line is in `math.tsv`. Seven marks (C-CAR-022, 023, 024, 030-035) lean on M-LAW-067, which states scoping, not the difference.
3. **State as a Law: absence is not a pass.** `README.md:80-85` and `ledger.py:14-16` state it ("an empty ledger at Stop ... is NOT-EVALUABLE"); `math.tsv` has no row for it, so nothing in the carriage ledger can be marked against the one property that decides what an empty file means.
4. **State as a Law: obligations are un-windowed within a session.** `README.md:78-79`, `ledger.py:35-36`. Absent from `math.tsv`; it is the premise under C-CAR-029/031's idempotence.
5. **State as a Law: the chain hash is advisory only.** `ledger.py:296` says "Advisory only"; README:86-89 and :159-161 (M-LAW-065, M-LAW-066) say the chain "detects" corruption in the present tense. **The carriage does not satisfy that claim**: `verify_chain` has no production caller (only `tests/test_ledger_growth.py:107-148`, whose own docstring records "a TRACE pass over this tree found the method on no input-to-output chain at all"). Either state the advisory-only limit as a Law, or call it (see REPLACE-1).
6. **State as a Law: exactly one JSON object reaches the wire.** `dispatch.sh:57-70` argues it at length and `tests/test_shim_visibility.py:66-121` holds it; C-CAR-115 (the `out=$(...)` capture) is the code, and it is marked `none` because no page states the rule.
7. **State as a Law: no surrogate code point survives `wire`.** `wire.py:23` states it verbatim ("ONE GUARANTEE"); `math.tsv` has no row, so all eighteen wire rows (C-CAR-085-102) mark as `none`. With the law stated they become `instance` of it.
8. **State as a Law: the journal is observability, never policy.** `journal.py:35-36` ("Every entry point swallows everything"); five rows (C-CAR-074, 076, 079, 081, 084) are the enactment and have nothing to point at.
9. **State as a Law: compaction rewrites the chain.** `ledger.py:284-292` recomputes every kept row's `prev`/`hash`, so after a compaction every stored hash differs from the one an earlier reader saw. M-LAW-065/066 say the chain detects "altered rows"; nothing states that Keel itself alters all of them at SessionStart (`dispatch.py:791`).
10. **State as a Law (or fix the code): the digest width.** `_digest` truncates SHA-256 to 16 hex = 64 bits (ledger.py:109) for both the chain link and `derive_id`. No page states the width or its collision bound; a `derive_id` collision silently merges two demands into one licence.

## 4. REPLACE (unique near-matches where the code should become the corrected form)

1. **C-CAR-046/048 — `verify_chain` (ledger.py:295-303) is the ONLY candidate for M-LAW-065/M-LAW-066 and for M-COV-048 (`chain_composes`), and no shipped path calls it.** Corrected form: call it where `compact` already runs (`dispatch.py:791`, SessionStart) and report a divergence through `journal.note_fault(..., failed_closed=False)`, so the advertised detection is a fact about a session and not only about the suite. Its "returns the FIRST divergent hash" shape is the right read-side analogue of `chain_composes` once something reads it.
2. **C-CAR-038/039 — `compact`'s owing accounting (ledger.py:274-279) is a SECOND copy of the set difference `scope` takes at ledger.py:195-205.** The file's own rule for exactly this hazard is stated one screen above, about the chain rule: "written ONCE ... two copies of one expression is exactly how a verifier starts reporting corruption on a sound ledger" (ledger.py:113-116), and `scope`'s docstring says the difference is taken "here and nowhere else" (ledger.py:188). Corrected form: compute `owing` from one shared expression (a per-session fold reused by `scope`), so the two cannot drift.
3. **C-CAR-033 — `is_licensed` is not `equal` to M-LAW-067 as written.** Unique candidate for the law; the code is the correct half (subject-keying is argued at dispatch.py:411-412 and `_subject`, dispatch.py:204-215). The replacement is on the statement side — see STATEMENT-FIX 1 — not on the code.

## 5. STATEMENT-FIX

1. **`README.md:162-164` (M-LAW-067) overstates the licence scope.** It says one observed guard licenses later matching calls "for that clause anywhere in the same session, not just against the same file, branch, or command". The code keys the licence on `(session, agent, clause_id, subject)` (`derive_id`, ledger.py:121-127; `is_licensed`, :245-247), and `dispatch.py:411-412` states the opposite in the same tree: "a Read of `other.json` does not pay for the traversal of `payload.json`." Fix: the licence is session-wide only where the subject is session-wide (the empty key, dispatch.py:491-497); otherwise it is per-subject. The law also omits `agent`, on which the code keys.
2. **`plugin/keel/journal.py:19` — "FOUR ROW KINDS, deliberately not five".** The module emits five: `session`, `deny`, `block`, `fault`, and `repair` (`note_repair`, journal.py:280). The sentence that names the count is the one place a reader checks it.
3. **`plugin/keel/journal.py:3-5` — "six event families".** `hooks.json` registers eight and `dispatch.HANDLERS` routes eight (`tests/test_event_surface.py:44-52` requires the two to be equal); `PreCompact` and `UserPromptSubmit` are missing from the sentence.
4. **`README.md:86-89` and `README.md:159-161` — present tense "detects".** No shipped path calls `verify_chain`; either adopt REPLACE-1 or say "a checker the suite runs" rather than a property of a session.
5. **`plugin/hooks/dispatch.sh:53-56` — "this branch is currently unreachable".** `tests/test_shim_visibility.py:122-127` reaches it through the `KEEL_PYTHON` seam. Fix: "no shipped dispatcher path emits exit 2; the suite drives this branch through the `KEEL_PYTHON` seam."
6. **`math.tsv` is missing every ledger property README states at :76-85** (observed discharge / un-windowed / absence is not a pass), while carrying M-LAW-064..067 from the same list at :86-96 and :159-164 — the gap is what forced 95 carriage rows to `none`. See ADD 2-4.
