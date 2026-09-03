# Audit of marks.clauses.tsv (auditor: review, 2026-09-02)

Source read: plugin/keel/clauses.py, plugin/keel/clauses.json (all 24 rows, every side re-classified
by running classify_side/derive_closure against the shipped table), proofs/Coverings.v,
proofs/Clauses.v, plugin/keel/effects.py, README.md.

## (1) Counts

| verdict | rows |
|---|---|
| confirm | 177 |
| amend   | 59 |
| reject  | 2 |
| total   | 238 |

Relations after audit: equal 79, instance 113, near 20, none 26 (was equal 87 / instance 89 / near 16 / none 46).
The 20 removed `none`s were false removes: 18 bare-`session_id` subjects (they implement README:162-164)
and 2 classifier branches that decide a stated side class.

## (2) REMOVE (code implementing no statement, no stated law, and not necessary carriage)

- C-CLS-021 `_base_predicate` kind=='tool' (clauses.py:258-259) -- a second spelling of the tool-enum class; zero shipped sides use `"kind": "tool"` (grep count 0 in clauses.json); every tool-enum side is `kind: regex, on: tool_name` (C-CLS-047). Two spellings of one class, one of them dead.
- C-CLS-026 `_regex_predicate` `unless` exclusion list (clauses.py:275-278) -- zero shipped uses; an exclusion list is only meaningful over a raw-text pattern, and every textual side is refused at clauses.py:620-624. It also breaks the upward closure Definition `textual` (Coverings.v:56-57) requires, so it implements no covering the math defines.
- C-CLS-055 `derive_closure` composed-with-no-tool_name -> 'world' (clauses.py:449-450) -- unreachable on the shipped table: all five composed sides (A02, U10, U12, U13, U19 discharged_by) carry a tool_name branch.
- C-CLS-058 `derive_closure` passthrough, nominal/unclassified/absent arms (clauses.py:455) -- unreachable: those sides are refused by CLAUSE-SIDE-UNCLASSIFIED / -OCCASION-NOMINAL / -GUARD-NOMINAL before any closure is derived. (The `always` -> `always` arm is NOT a remove: it produces the `closure=always` every always SIDE law records.)
- C-CLS-076 `AGNOSTIC_OCCASIONS = AGNOSTIC_CLASSES` (clauses.py:595) -- an alias that asserts the occasion side is licensed by the same five classes as the guard side, which README:188-197 denies (occasions are `always`, a host tool enum, or an effect). It is also read by nothing: the occasion check at clauses.py:634 uses AGNOSTIC_CLASSES directly. Remove the alias, or replace it (see REPLACE 2).
- Conditional, tied to ADD (e): the whole `derive_closure` (C-CLS-053..058, clauses.py:435-455) is a host/world/datum dimension with NO definition anywhere in the math -- Clauses.v only echoes back the value this function computed. Either define closure in Coverings.v or delete the dimension from code and from the renderer.

Not removes, though the builder marked them `none`: the anchor regex (C-CLS-001, stated law clauses.py:101-111), `_NON_ENFORCING` (C-CLS-003, stated law clauses.py:44-47), the probe cache (C-CLS-006, measured bound clauses.py:170-180), `_leaves` (C-CLS-074/075, the "any leaf" quantifier of CLAUSE-EFFECT-UNKNOWN), `_matches_a_tool_enum` (C-CLS-035), the single-class collapse (C-CLS-039, what keeps U03/U09/U20 `effect`), `subject_fields` (C-CLS-060), `load_default` (C-CLS-107), and all 18 `session_id` subjects.

## (3) ADD

### 3a. Statements the loader should enforce and does not (from residue.math.tsv)

- M-COV-031/032/033/034 (Definition `positive`, Thm 6, Thm 7, Cor no_claim_is_not_a_pass) -- NO shipped side is `positive`: `nonzero` is the only code candidate and is not it (see REPLACE 1). The whole positive form, which README:321-322 (M-LAW-076) advertises, is enforced by nothing in the table.
- M-COV-016/M-COV-017 (Definition `structural`, Thm 2 structural_immune) -- no code element reads `scan` at all; the estate has no structural covering. Thm 2's mention-immunity is claimed in README:316-320 but instantiated by no clause side.
- M-COV-023 (Thm 4, topology) -- README:320-321 (M-LAW-075) cites it as a shipped form; no clause side covers pipe topology or segment count. Either instantiate it or drop the citation.
- M-COV-027 (Thm 5, nominal_monotone) -- RELIED ON: it is named in the refusal text of CLAUSE-OCCASION-NOMINAL (clauses.py:630, 638) and CLAUSE-GUARD-NOMINAL (clauses.py:639-649), yet was unmarked against any code row. Marked in this audit at C-CLS-082/083.
- M-LAW-073 (README:286-293) -- states U25 "is discharged only by a test invocation whose command text contains prefix or distractor". The shipped U25.discharged_by is `{kind: effect, effect: report_fail}` and contains no such condition; a text condition would be refused by CLAUSE-TEXT-COVERING. Unenforceable as stated (see STATEMENT-FIX 4).

### 3b. Theorems the loader relies on that Coverings.v does not state (ADD to proofs)

- (a) COMPOSITION. `composed` is in AGNOSTIC_CLASSES (clauses.py:432) and five shipped guard sides are composed, so the loader assumes: a disjunction (and conjunction) of name-agnostic coverings is name-agnostic. Coverings.v proves no such closure result.
- (b) HOST-ENUM CLASS. `tool-enum` (clauses.py:415-419) licenses the occasions of D01/P01/P02 and the guards of C03/D01/P01/P02 and every composed side. Coverings.v has no element for a covering over the host's closed `tool_name` enum -- it is not `structural` (it never reads `scan`) and not `effect`.
- (c) THE `always` CLASS. Seven shipped fingerprints are `always`, licensed as the Theorem 3 boundary in a docstring only. Note the adversarial reading: P = True is `textual` by Definition (Coverings.v:56-57, vacuously upward-closed) and `non_vacuous`, so Theorem 1 formally applies to it. The needed statement is that a covering reading no segment and no text is name-agnostic, and that it is the only pre-act occasion that separates nothing.
- (d) THE DISJUNCT COROLLARY. classify_side contaminates a whole side from one textual/nominal branch (clauses.py:394-397). The sound statement -- a covering with a non-vacuous textual disjunct is not mention-immune -- is not in Coverings.v; and the same rule OVER-refuses `all_of`, where a textual conjunct with an effect conjunct can be mention-immune. State both.
- (e) CLOSURE. host/world/datum (clauses.py:435-455) is defined nowhere in Coverings.v; Clauses.v renders back the value the code computed.
- (f) A PER-SIDE RESULT. proofs/Clauses.v:113-121 is `forall (s : EffectSide) ...` and its proof never uses `s`: it grades nothing per side. It also enumerates `C09_checker_excludes_self_fingerprint`, whose datum effects.py:62 says is read from the COMMAND TEXT -- which Coverings.v:169-172 explicitly places outside Theorem 8. Either exclude that constructor or prove the side separately.
- (g) NOT-EVALUABLE IS LIVE. The fail-closed rule (clauses.py:316-331 occasion side -> True; 335-341 guard side -> falsy; README:203-204) is the estate's central asymmetry and has no Coverings.v result and no math.tsv Law row; M-LAW-057 states the miss asymmetry, not the unmeasured one.

## (4) REPLACE (unique near-matches; the code should become the corrected form)

1. C-CLS-022 / C-CLS-050 / C-CLS-057 -- `nonzero` (clauses.py:260-264, 423-424, 453-454) is the ONLY candidate for Definition `positive` (M-COV-031) and is not it. CORRECTED RULE: a `positive` side names a claimed field and an observed field and fires only when both resolve and are equal; a bare `int(value) != 0` on one field classifies `unclassified` and is refused.
2. C-CLS-076 -- AGNOSTIC_OCCASIONS vs README:188-197 (M-LAW-071). CORRECTED RULE: an occasion's class must be one of {always, tool-enum, effect}; `positive` and `composed` are guard-side classes only, and clauses.py:634 must read that narrower set.
3. C-CLS-151 -- U02.subject regex over `tool_input.command` (clauses.json:2007-2011). CORRECTED RULE: key U02's demand on a world datum the record carries as a list (record `pids_spawned` as pids and add it to KEYABLE_EFFECTS), or on `session_id`; never on a regex over the command text -- an unmatched or mention-spoofed extraction yields "" and the dispatcher abstains, so the demand is never raised (clauses.py:711-736).
4. C-CLS-166 -- U10.subject over `[tool_input.command, tool_input.file_path]` (clauses.json:3183-3190). CORRECTED RULE: key on the path the act actually read (a world datum) or on `session_id`; drop the command arm -- `tool_input.file_path` is present only on host tool calls, which are not the Bash acts a `report_null` occasion fires on, so in practice it reads raw text.
5. C-CLS-060 -- `subject_fields` defaults a subject with no `on` to `tool_input.command` (clauses.py:472). CORRECTED RULE: a subject must name its `on` explicitly; there is no default, and the raw command is not one of the surfaces a subject may default to.

ANSWER to the builder's flagged question (subject extractors exempt from CLAUSE-TEXT-COVERING): it is a
REAL hole, in the OPEN direction. The refusal loop runs only over fingerprint/activated_by/discharged_by
(clauses.py:616-628), so a subject may read raw text; a mention or an unexpected spelling makes the
extractor return "" and dispatch treats the empty key as NOT-EVALUABLE and PASSES the event -- the costly
act proceeds with its guard removed, which is M-LAW-057's expensive-and-silent side. CLAUSE-FIXTURE-POS-
UNKEYABLE (clauses.py:711-736) bounds only the fixtures someone wrote down, which is exactly the
enumeration Theorem 1 says cannot be finished. It fires nothing wrongly; it fails to fire.

## (5) STATEMENT-FIX

1. Coverings.v:205-209 (M-LAW-058) says "An occasion must therefore be NOMINAL"; clauses.py:634-638 refuses a nominal occasion outright (CLAUSE-OCCASION-NOMINAL), citing the same Theorems 3 and 5. FIX the prose: an occasion that must SEPARATE two acts before the act would have to be nominal; Keel therefore does not separate before the act (its pre-act occasions are `always` and fire on every Bash call, at the cost of firing always) and every separating occasion is post-act, an effect.
2. proofs/Clauses.v is GENERATED from plugin/keel/clauses.json (its own header says so), so M-CLS-001..M-CLS-064 are a rendering of the code. The ~60 `equal` marks of a clause side against its own SIDE comment record self-agreement, not conformance to math; they are factually correct and are confirmed, but the ledger should mark each side against the Coverings.v element that licenses its class (M-COV-024/025/026 for effect; the missing results (a)-(c) for tool-enum/always/composed).
3. proofs/Clauses.v:113-121 -- quantifies over `s : EffectSide` without using it, and includes `C09_checker_excludes_self_fingerprint`, a command-derived datum Coverings.v:169-172 excludes from Theorem 8. Fix the enumeration or state the exclusion in the generated file.
4. README.md:286-293 (M-LAW-073) -- U25's discharge is described as a command-text condition (`prefix`/`distractor`); the shipped guard is `{kind: effect, effect: report_fail}`, and a text condition could not be admitted. Correct the README to the effect it actually ships.
5. M-LAW-005 (clauses.py:558-579) bundles four independent checks (cmd shape, timeout bound, expect shape, expect regex compiles). Split it so C-CLS-069 and C-CLS-072 can each be `equal` rather than `instance`.
6. math.tsv is missing Law rows for six stated laws the code carries, each of which turned a code row into a false REMOVE candidate: the negative/positive pairing anchor (clauses.py:101-111), the undecided-event law (44-47), the measured 2N-probe / 20s-hook fail-open bound (170-180), the terminal-clause discriminator rule (598-606), NOT-EVALUABLE-is-live (316-331 and README:203-204), and one-table-no-second-place (829-841).
7. M-LAW-071 (README:188-197) and AGNOSTIC_OCCASIONS disagree about which classes may be an occasion; one must move (see REPLACE 2). As shipped no row exercises the gap -- all 24 occasions are `always`, tool-enum or effect -- so the code, not the statement, is the loose one.
