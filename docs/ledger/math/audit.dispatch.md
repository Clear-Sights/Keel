# Audit — marks.dispatch.tsv (auditor: review, 2026-09-02)

Source read: `plugin/keel/dispatch.py` (1074 lines), `proofs/Coverings.v`, `README.md`,
`plugin/keel/clauses.py` (for M-LAW-014 / `_EVENTS`). Output: `marks.dispatch.audited.tsv`.

## 1. Counts

| verdict | rows |
|---|---|
| confirm | 129 |
| amend | 63 |
| reject | 0 |
| **total** | **192** |

Relation distribution after audit: equal 3 (was 4), instance 67 (was 52), near 6 (was 21), none 116 (was 115).
No row was rejected outright: every pairing had a true statement behind it, but 63 named the wrong
statement, the wrong relation, or claimed "no math element" where a stated law exists.

The two `# keel-guard:` / `# keel-allow:` owner rows (C-DSP-001, C-DSP-003, C-DSP-008..C-DSP-012,
C-DSP-069..C-DSP-072) are confirmed `none` as instructed; no law was invented for them.

## 2. REMOVE — code implementing no statement, no stated law, and not necessary carriage

- `C-DSP-002` `ALLOW_LEGACY` regex, dispatch.py:71 — a SECOND exemption spelling (`# gyroscope-allow:`). `grep -rn gyroscope README.md docs/` returns nothing: README.md:133-147 documents `# keel-allow:` and only that. An undocumented second way to turn all 24 clauses off for a call is a covering with no statement anywhere.
- `C-DSP-011` `_allow_marker` legacy branch, dispatch.py:119-121 — the parse half of the same undocumented spelling; falls with C-DSP-002.
- `C-DSP-071` `pre_tool_use` legacy-allow exemption + rename notice, dispatch.py:462-468 — the decision half: exempts the call on a spelling no document states. The rename notice is the only part with a purpose, and it can be delivered by a deny that names the rename instead of by an allow.
- `C-DSP-137` / `C-DSP-138` / `C-DSP-140`, dispatch.py:796-803 — the stranded pre-rename state-directory notice. Same family: a migration affordance for a rename that no README limit, no clause law and no theorem mentions. Weaker than the three above (it changes no decision, only prints), so remove only if the rename is declared finished.

Nothing else in the 116 `none` rows is a remove. The wire builders (C-DSP-035/043/044), the dotted-path
and id helpers (C-DSP-013/014/015), the `_subject` extractor mechanics (C-DSP-029..033), the
`_pending_*` family (C-DSP-107..118), the journal parse-back (C-DSP-158..170) and `main`'s envelope
handling (C-DSP-171..192) are carriage the math is silent about by necessity, or serve a stated law
listed in §5.

## 3. ADD — residue.math.tsv rows the dispatcher should implement and does not

- `M-COV-043` `out_of_order_is_rejected` (Coverings.v:316-317): `[L; X]` — the guard arriving after the act it would license — must be rejected. `pre_tool_use` does not reject it. dispatch.py:482-488: when `C.discharges(cl, event)` is true the clause is paid and `continue`d, so `_applies`/`C.match` are never reached for that clause on that event. One Bash command that satisfies both a clause's `discharged_by` and its occasion therefore self-licenses in a single PreToolUse. `only_open` guards only effect-side clauses (dispatch.py:486); a pre-act clause is paid with `only_open=False`. dispatch.py:612-618 asserts that `pre_tool_use` refuses exactly this shape ("`git push && git status`, where the guard arrives too late"); no code in dispatch.py or in `clauses.discharges` (clauses.py:335-341) performs that segment-order check. The assertion is presently unbacked.

No other residue row is an ADD for this module: M-COV-001/003..010/012/014/016/019/028..030/035..038/044 are
definitions, variables and hypotheses; M-COV-017/018/023/026/027/032/033/034/045 are proven results that
prescribe no dispatcher behaviour; M-LAW-059/060/062/063/074/075/076/077 are consequences of those;
M-LAW-064/066/073 belong to `ledger.py`, `effects.py` and the clause table, not the dispatcher.
`M-CLS-065` is the generated clause-side inductive.

Mark gap (not an ADD): `M-LAW-064` (README.md:90-96, nested `claude -p` shares its parent's
`session_id`) is the exact statement behind `C-DSP-015` (`_ids`, dispatch.py:134-137), which is
marked `none`/"carriage plumbing". Keying on `(session_id, agent_id)` and letting an ambiguous agent
id contribute nothing IS that limit, implemented.

## 4. REPLACE — unique near-matches where the code should become the corrected form

- `C-DSP-023` `_names` path arm, dispatch.py:174-179, against `M-LAW-068` (README.md:165-174). Corrected rule: **a demand keyed on a path is named by `tool_input.file_path`/`path`/`notebook_path` only when the value equals the subject or is a true path-suffix of it (`value.endswith("/" + subject)`); the basename arm at dispatch.py:177-178 is dropped.** As written, `subject.endswith("/" + basename(value))` discharges a demand keyed on `docs/notes.md` from a Read of `/other/place/notes.md` — a guard paying for a file it never looked at, which is exactly the "a discharge records what the guard act did" law it is marked against. (The trailing `and basename(value) == basename(subject)` conjunct is dead: the `endswith` already implies it.) Only candidate for this statement in the module, so the code moves.

## 5. STATEMENT-FIX — the statement is wrong or missing and the code is right

- `C-DSP-156` (dispatch.py:871): the mark said `SessionStart` is "outside the five clause-enforceable events". False — `SessionStart` is in `_EVENTS` (clauses.py:41). The code is right; the evidence was wrong. Amended.
- `C-DSP-062` / `C-DSP-065` (dispatch.py:429-430, 439) vs `M-LAW-070`: README.md:186-187 exempts only `Read`, `Grep`, `Glob` from being refused by an open demand. The code also exempts `NON_ACTS` = `{AskUserQuestion, ExitPlanMode}`, on measured grounds (DL-14, P-23: a refused push blocked the very question that would resolve it). README.md:186-187 should name the non-act tools alongside the host reads.
- `C-DSP-080` (dispatch.py:518-519) vs `M-LAW-071`: the code waives `always`-kind denials on any event that made progress on any clause, so the first guard call is not refused by the other two opening clauses. README.md:191 names `always` as an occasion kind but states no waiver; no math row states it. The README limit should carry the opening-move rule.
- `C-DSP-129` (dispatch.py:758-762) vs `M-COV-041`: a hook the host killed becomes an open obligation with no `isL` event and no clause. Coverings.v has no notion of an unevaluated act as a source of debt; dispatch.py:752-756 states it and the code is right. Add the statement.
- `C-DSP-184` (dispatch.py:1027-1036): an event outside `HANDLERS` evaluates nothing and DISCHARGES nothing (DL-13, the old wildcard default gave a free guard). This is an ordering fact, not `M-LAW-014` (a loader law about `clause.event`). No math row states "an unrouted event may not supply an X".
- Missing law rows in `math.tsv`, each implemented and each currently making a code row read as a remove candidate: README.md:80-85 (absence is not a pass; a zero-clause load blocks Stop — `C-DSP-181`, `C-DSP-182`); README.md:207-208 (an unmeasurable effect is NOT-EVALUABLE and its occasion is treated as live — `C-DSP-054`); README.md:126-131 (the cut: bare `/compact` gets the vendored list, an instructed one is untouched, the automatic path only reports — `C-DSP-143`..`C-DSP-149`); dispatch.py:13-18 (the split fail direction: carriage fails OPEN, a decision fails CLOSED, an event with no closed wire falls back to carriage — `C-DSP-045`..`C-DSP-048`, `C-DSP-123`, `C-DSP-142`, `C-DSP-176`, `C-DSP-188`, `C-DSP-190`); dispatch.py:696-713 (STOP_ROUNDS: three refusals then a loud allow, rows staying open — `C-DSP-106`, `C-DSP-120`); dispatch.py:752-756 (a hook the host killed evaluated nothing — the `_pending_*` family); dispatch.py:902-924 (the deny's key is read back out of the rendered prose, last match, so the log cannot disagree with what the agent was told — `C-DSP-159`, `C-DSP-164`).

## 6. False passes corrected (equal/instance whose code differed)

- `C-DSP-063` was `equal` to `M-LAW-078` (backward). It is the FORWARD endpoint: an effect demand refuses the NEXT act. Re-pointed at `M-LAW-071` (README.md:194-195), where it is genuinely equal in quantifier, domain and fail direction.
- `C-DSP-133` was `equal` to `M-LAW-078`. `backward` (M-COV-041) quantifies at every position of a trace; `reconcile` quantifies once, over the open rows at the ending. Downgraded to `instance`.
- `C-DSP-080` was `equal` to `M-LAW-058`. M-LAW-058 is about occasion nominality and says nothing about waiving denials. Downgraded to `near` on `M-LAW-071` (see §5).
- `C-DSP-078` was `instance` of `M-LAW-058`; it is the backward endpoint (`M-LAW-078`), not a nominality claim.
- `C-DSP-086` / `C-DSP-073` / `C-DSP-085` were `instance` of the miss asymmetry / licence scope; all three are the ordering pair (`M-COV-041`): an act cannot be its own guard (EFF-12), and a terminal clause's guard is an ordinary earlier call.
- `C-DSP-124` was `near` on `M-COV-048` (`chain_composes`). Terminal-event scoping is not a chain step; re-marked `none` with its stated source at dispatch.py:724-734, and it is not a remove.
- `C-DSP-055`/`061`/`081`/`132`/`130` cited theorem `M-COV-042` for branches that PASS; a pass is an instance of the definition `M-COV-041`, not of a theorem about violations.

## 7. False removes corrected (a `none` that implements a stated law)

- `C-DSP-094` (dispatch.py:571-578) was `near` "beyond what the commitment law states". README.md:184-186 states the journal row and the demand staying open verbatim; only the stderr line is extra. Now `instance`.
- `C-DSP-064` (`HOST_READS`, dispatch.py:435) was `near` "a domain restriction not in backward's abstract Event type". README.md:186-187 names `Read`, `Grep`, `Glob` exactly. Now `equal` on `M-LAW-070`.
- `C-DSP-024` (dispatch.py:180) was `near`; returning False when nothing named the subject is the discharge law's own fail direction. Now `instance`.
- `C-DSP-027` (dispatch.py:199-200) was `near` "an implementation-only guard". `only_open` IS the ordering: a guard seen before the demand cannot license it (measured, U20). Now `instance` on `M-COV-041`.
- `C-DSP-057` (dispatch.py:406-407) was `near` "an extra scope carve-out". A terminal clause's L is the ending, so its backward check lives in `reconcile`. Now `instance`.
- `C-DSP-095` (dispatch.py:579) was `none` "a dispatcher design invariant". README.md:194-195 states it: the demand refuses the NEXT act, so this event cannot be refused. Now `instance` on `M-LAW-071`.
- `C-DSP-038` (dispatch.py:280-281) was `near` "an extra degenerate case". The empty key is the stated coarse-but-honest key (dispatch.py:214-215, 493-497). Now `instance`.
- The eight `HANDLERS` rows plus `C-DSP-183` were all `near` "wider than CLAUSE-EVENT-UNKNOWN's domain". `M-LAW-014` ASSERTS the eight-routed/five-enforceable gap, so each routed row instantiates it rather than diverging from it. All now `instance`.
