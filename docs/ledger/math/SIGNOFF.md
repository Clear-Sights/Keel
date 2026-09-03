# Owner sign-off sign-off on the four Review audits (2026-09-02, Keel head ba072ce)

Verified by reading the head before signing: dispatch.py:482-488 (pay-then-continue), :172-180
(_names basename arm), :71/:119-121 (gyroscope-allow); effects.py:579-599 (`held` unread),
:751-752 (head_reset), :486 (report_null); journal.py:241 ([:10]); verify_chain callers = tests only;
clauses.py:258-259 kind==tool and :275-278 `unless` have 0 uses in clauses.json;
AGNOSTIC_OCCASIONS alias at clauses.py:595 read by nothing.

Rule for every builder: subtraction or correction only; every code change carries a cell witnessed
RED on ba072ce before green; never soften a stated limit; no new clause; no new covering kind with
no shipped user. Anything marked DEFER is not built.

## A. effects.py (builder A)
APPROVE REMOVE  C-EFF-160 `held` set (effects.py:579-587).
APPROVE REPLACE C-EFF-074 ancestry cap -> visited-set walk (stop on repeat or pid<=1).
APPROVE REPLACE C-EFF-161 drop the directory-prefix arm `path.startswith(t + "/")`; keep exact/suffix/basename.
APPROVE REPLACE C-EFF-213 head_reset = None when `changed is None` (NOT-EVALUABLE stays NOT-EVALUABLE).
APPROVE REPLACE C-EFF-084 M-LAW-072 third lineage clause: a pid whose session leader is in the tree is the session's.
DECIDE  C-EFF-131 report_null: the CODE stays (a bare `null` output fires the occasion; firing wide is the
        cheap direction). The EFFECTS text moves to say so. Statement-fix, not replace.
APPROVE all 11 STATEMENT-FIX groups (EFFECTS texts at effects.py:40-70 and README:175-180): the
        7-hex floor; delete "or process"/"left no process" (still is files+refs by measurement); the
        (size, mtime_ns) proxy, size==0 rule, fallback exclusions, WALK_CAP NOT-EVALUABLE; exclude the
        observer's own chain; report_self 3-char and literal-text limits; observed_read validated by path
        identity + shape + (session, root) scope; REMOTE_RETRY_S retry; sticky three-valued net memory;
        Stop-time remote_ref_moved definition.

## B. dispatch.py, journal.py, ledger.py, wire.py, dispatch.sh (builder B)
APPROVE REPLACE C-DSP-023 `_names`: value == subject or value.endswith("/" + subject) only; basename arm gone.
DECIDE  M-COV-043 self-licence: first write the cell (one Bash command whose text satisfies both a
        pre-act clause's discharged_by and its occasion in one PreToolUse). If any shipped clause can be
        self-licensed, reject the pay when `_applies(cl, event)` is also true for the same event and
        witness red->green. If none can (guards are host-enum or effect; no record at PreToolUse), the
        cell stays as the proof and the comment at dispatch.py:612-618 is rewritten to say the refusal
        is structural (no guard predicate can match a Bash event), not a segment-order check.
APPROVE REMOVE  C-CAR-078 `[:10]` on clause_ids (journal.py:241).
APPROVE REPLACE C-CAR-046/048 call verify_chain at SessionStart BEFORE compact (dispatch.py ~791);
        divergence -> journal.note_fault(..., "chain_divergent", failed_closed=False). Cell: a corrupted row
        produces the fault row in a real SessionStart.
APPROVE REPLACE C-CAR-038/039 compact's owing set computed by the same expression scope uses (one fold).
APPROVE STATEMENT-FIX journal.py:19 five row kinds; journal.py:3-5 eight event families;
        dispatch.sh:53-56 reachable through KEEL_PYTHON; ledger.py docstring states the 64-bit digest
        width and that compaction rewrites every hash.
DEFER   C-DSP-002/011/071 gyroscope-allow legacy spelling -> folded into OWNER row 1 (commitment marker)
        with recommendation REMOVE (an undocumented second exemption route). Not built alone.
KEEP    C-DSP-137/138/140 stranded state-dir notice (changes no decision; rename not declared finished).
KEEP    legacy_state, derive_id, fail_open arms, _STALE_CLAIM_SECONDS, COMPACT_AT (audit agrees).

## C. clauses.py, clauses.json, render_coverings (builder C)
APPROVE REMOVE  C-CLS-021 kind=="tool" arm; C-CLS-026 `unless` arm (and any loader validation of it);
        C-CLS-055 and C-CLS-058 unreachable derive_closure arms; C-CLS-076 AGNOSTIC_OCCASIONS alias.
APPROVE REPLACE C-CLS-076/M-LAW-071: occasion classes = {always, tool-enum, effect}; the occasion check at
        clauses.py:634 reads that set. Witness: plant a composed fingerprint -> CLAUSE-OCCASION-NOMINAL
        (or a new code CLAUSE-OCCASION-CLASS) red.
APPROVE REPLACE subject hole: new loader law CLAUSE-SUBJECT-TEXT refuses a subject whose `on` includes
        tool_input.command; `subject_fields` has no default `on`. U02 keyed on session_id (or on
        pids_spawned if the record carries pids); U10 keyed on session_id. Witness the law RED on the
        shipped table first (U02, U10, and the default), then green after the table moves. Re-derive
        fixtures; replay corpus by re-running the dispatcher, never by editing json.
DECIDE  nonzero (C-CLS-022/050/057): count shipped uses. If 0 -> REMOVE the kind (no positive form is built:
        a covering kind with no user is addition). If >0 -> report, do not change.
APPROVE STATEMENT-FIX M-LAW-005 split into four laws (clauses.py:558-579 comments/codes stay one loop).
APPROVE render_coverings: Clauses.v per-side theorem must use `s` (one result per side) and must exclude
        C09's command-derived fingerprint from the Theorem 8 enumeration, stating the exclusion.

## D. proofs + README + math.tsv (builder D; README is D's file only)
APPROVE Coverings.v additions, each a real theorem with content (check_coq refuses identity proofs):
        (a) composition: any_of/all_of of name-agnostic coverings is name-agnostic;
        (c) the always covering reads no segment and is name-agnostic;
        (d) a covering with a non-vacuous textual disjunct is not mention-immune;
        (g) NOT-EVALUABLE-is-live: an unmeasured occasion is treated as fired, an unmeasured guard as
            not paid (state as a Definition + one theorem that a trace with an unmeasured guard
            is never licensed).
        (e) closure: a Definition only (host/world/datum by what a side reads), no theorem.
        (b) host-enum class: Definition + a mention-immunity theorem (reads tool_name, never scan).
DEFER   (f) beyond C's renderer change.
APPROVE STATEMENT-FIX Coverings.v:205-209 prose (Keel does not separate before the act; every
        separating occasion is post-act); README:162-164 licence scope is per (session, agent, clause,
        subject), session-wide only for the empty key; README:186-187 names NON_ACTS beside the host
        reads; README:191 states the opening-move waiver; README:286-293 U25 discharge = report_fail;
        README:316-322 says which proven forms are instantiated by a shipped side and which are proven
        only (sharpen, never soften); README:86-89/159-161 chain "detects" becomes true once B lands
        (say "at SessionStart").
APPROVE math.tsv rows for every implemented-but-unstated law the four audits list (absence-is-not-a-pass,
        NOT-EVALUABLE-is-live, the set difference, un-windowed obligations, one-object-on-the-wire,
        no-surrogate, journal-never-policy, compaction-rewrites-chain, digest width, fail-direction
        split, STOP_ROUNDS, killed hook = debt, unrouted event discharges nothing, /compact cut,
        deny key read back, opening-move waiver, anchor regex, undecided-event, probe bound,
        terminal-discriminator, one-table). Each row cites the README/code line that states it; where
        only code states it, D adds the sentence to README or the module docstring.

## Residue after sign-off
residue.math.tsv rows that remain: proven theorems/variables/hypotheses (no code owed) and the
positive/structural/topology forms, now stated in README as proven-not-instantiated.
