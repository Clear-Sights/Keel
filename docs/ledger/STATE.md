# STATE (memory on disk; deltas only in chat)
## Blocking on owner (rows the oracle does not decide)
1. COMMITMENT MARKER (`# keel-guard:` / `# keel-allow:`): foundations C1-C9, EF-01, AG-3, K26 confirmed it is a textual covering relocated to the wire (the refusal prints the string that defeats it; # keel-allow returns before the snapshot). C9's design space: (a) keep marker = keep a spelling; (b) refuse every Bash under an open effect-demand = deadlock for the 9 Bash-only-guard clauses (C08 C09 U01 U02 U06 U08 U20 U24 U25); (c) SUBTRACTION: drop the pre-act denial for those nine, report the unpaid effect on PostToolUse systemMessage, enforce at Stop (already works). (c) is the simplest sound member but changes "refuses the next act" for nine clauses. Owner decides.
2. DECISION-INERT ROWS (B2, K21, machine-checked, 986 traces): A02, U12, U19 change no deny/allow on any trace (U12 ≡ U19 byte-identical predicates; A02 ⊂ A01 occasion with a superset guard). Delete → 21 rows, byte-identical behaviour. Changes the 24. Owner decides.
3. REPORT-SHAPE GUARDS (AG-1, P4): `echo PASS` pays U20/U24; report_pass/fail/clean/nowarn/signature/structured have no trace to cross-check (Theorem 7 converse, stated limit). 13 of 24 guards rest on them. Options: state it in README limits naming the clauses (assignment of scope) or delete those guard branches and the 7 clauses left without one. Owner decides.
4. SMALL-TOOLS DISPOSITIONS: ranking + per-seat grades at scratchpad/ledger/small-tools-rank.md and small-tools-grades.tsv (19 seats: 6 folds, 5 skills, 10 retire candidates per the ranker; tier rule inside). Owner decides.
5. B1 coverage claim: README now says the 24 name moments and claim no spanning (done); FRONTIER's 2/10 one-session figure not printed (BASIS.md disowns 1/71). Owner may want the 2/10 printed.
## Open PRs
- Small-Tools #21 MERGED 419f354; branch reset onto main
- Keel #34 MERGED ebe230d | Keel #35 head 8df26db (write surface + endings + codex manifest), CI restarted 15:20Z; d776cdd was red on test_host_shape (codex manifest not widened)
## Merged
- Keel #33 483e6b9 | Small-Tools #20 de3de88
## Workflows
- gen1 done: attack (wf_d6d25c82: 2 lanes safeguard-refused: agnostic, dispatch; verify/prop cut by spend limit), simplify (36 candidates, 0 judged: limit), foundations (71 standing, synth failed: limit), outer (32 confirmed), rank (complete)
- gen2 running: wf_c2a82659-d81 propagation (8 lanes) | wf_d6d25c82-4eb attack resumed (agnostic+dispatch rephrased as coverage audits) | wf_9e4847ca-53b simplify resumed (5 hunts + refuters per scope)
## Gen1 fixes landed in tree (Keel)
- check_coq.py reads coqc's .glob (prf/var/ax); PARAMETERS line in both proof files; census instantiated=36 empty-by-class[always=7 tool-enum=8]; 4 plants red (eval/attacks.sh)
- K16: NOT-EVALUABLE reaches any_of/all_of leaves (_predicate over _leaves)
- B6/K18: created files are files_changed (_tree_delta A, _walk_delta after-only)
- K27/EFF-01: fetch_head_written deleted (effects, snapshot, corpus, 60 fixture keys, 1 test)
- positive-01: A02 pays on report_paths (construction now discharges); deny_reason/guard text
- positive-03: POINTS.md C08/U25 Limit lines; README:41 + SKILL:30 qualified (C08, U25)
- B1: README count sentence states no spanning claim
- eval/attacks.jsonl + attacks.classes.json + attacks.sh + tests/test_attacks.py (9 cells)
- CI: push only on main; plant sweep on 3.11 only
## Numbers
- plugin LOC 2205 → 2188 (effects 639→622); tests +1 file; Small-Tools 21 seats 41 gates
## Owed next gen
- simplify 36 candidates unjudged (EFF-02..12, dispatch-*, C1..C15): re-run refuters (1 per scope)
- attack lanes agnostic+dispatch: rephrase as coverage audit (safeguards flagged 'cyber')
- foundations synth; GYRO-13 suite order-dependence; Courthouse CH-02/03/05 (renders keys Keel never writes; failed hardcoded 0); Ward WM-05..07; Makoto WM-08 (30/36 lexicon)
- remaining Small-Tools open cells (6 red in repo/pollinate.jsonl)
- tag: bump plugin.json 2.1.0 after this batch merges, then release.yml on main
- gen1 fix: CI intermittent test_a_printed_path (3/15 jobs) = sibling spawn in session tree made a look loud; fixed 247603f; note: concurrent check_coq runs in one proofs dir raced on .vo deletion, deletion removed
## Gen2 propagation (786 cells, 8/8 lanes, scratchpad/ledger/gen2-propagation.tsv)
- SYSTEMIC, near-total: K03 30/31 (file-mutation points Bash-only; Write/Edit unregistered), K08 30/31, K20 30/31 (Stop clauses skipped at SubagentStop), K17 29/30, AG-10 29/30 (trace-checked guards payable by constant payloads), K13 28/30, positive-01 26/30 (constructions never discharge their clause: guards are host-enum reads, constructions are Bash acts), positive-06 26/30, K14 25/30, K11 24/30, B9 23/30
- narrow: K21 8/31 (U12≡U19), K24 6/30, EF-02 4/30, K27 9/30
## Gen2 fixes landed (Keel #35)
- K03/H7/POSTURE-08: hooks match Write|Edit|MultiEdit|NotebookEdit; _effect_record observes every non-host-read tool; 14 effect occasions tools ["*"]; corpus u19-edit-rewrite-unverified; tests/test_write_surface.py; cell write_surface_is_observed
- dispatch: Stop block names every open row (was [:5]; replay had read 5 as the whole)
- t01 corpus session's Write act now carries its effect record (it had none; under the wider surface a recordless act is NOT-EVALUABLE-live and fired 7 clauses)
## Still owed from gen2 matrix (owner rows or next gen)
- positive-01 26/30: constructions never discharge their clause (guards are host-enum reads or effects a Bash construction cannot emit) -- OWNER ROW 6: either constructions become host-enum acts, or each guard gains its construction's observable (per clause, e.g. A02 manifest = files_changed[deleted.list] then files_removed)
- K20 30/31: Stop clauses skipped at SubagentStop; K08 30/31; K17 29/30; AG-10 29/30 (constant payloads pay trace-checked guards); K13 28/30; K14 25/30 (at_stop remote_landed True when unmeasured); K11 24/30; B9 23/30 (only 3 rows deny the act they name before it runs)
- K20: Stop clauses reconciled at SubagentStop under the agent's own key (cost stated: a read-only subagent's ending now owes one Read of observed.json for T01); K14: net_out memory tri-state, unmeasured → ls-remote at Stop; cells + tests/test_endings.py

## 15:30Z correction (owner: "Why 34 refute for 8 hunts? 55 verifies for 8 attacks?")
Measured from agent transcripts: the refute stage grouped by the finding's free-text `layer` / cut's `scope` field, so 61 attack refuters (30 first run + 31 resumed) and 14 simplify refuters ran, each prompted as "the ONE refuter". Fixed: findings tagged with the producing lane at collection (`lane: LAYERS[i].key` / `SCOPES[i][0]`), grouped by `lane`. Both runs stopped and resumed (tasks w65x45yi4 attack, wdfirg1zh simplify; same run ids). Expected: 8 and 9 refuters. Verify with:
  for f in subagents/workflows/wf_d6d25c82-4eb/agent-*.jsonl; do [ "$(stat -c %Y $f)" -gt "$(date -d 15:28 +%s)" ] && grep -o "ONE REFUTER for every finding from the '[^']*'" $f | head -1; done

## 16:5xZ (post-restart) landed locally on Keel branch (not yet pushed; #35 3.11 plant sweep still running since 15:20Z)
- ROOT CAUSE of intermittent test_a_printed_path: worktree_tree copied the real index -> stat cache trusted -> stale blob in a same-second rewrite-then-look (4-5/80 measured). Fix: empty private index each snapshot (0/200). Supersedes the sibling-spawn reading (that was a second, real, cause).
- K11: switch/create split now by reachability from pre-act refs, never committer date. Stated limit: unreachable checkout reads as creation.
- Cells: look_is_not_a_rewrite_under_a_stat_cache, backdated_commit_is_a_creation (both red-on-old witnessed). Suite 254 OK, replay 27/27, views/cov match, COQ=PASS.
- Workflows resumed after container restart (tasks wh3janpnf attack, w712k8l8r simplify); verified one refuter per lane (attack: dispatch, loader seen; simplify: dispatch, effects seen).
- #35 MERGED 4f50fcd (3/3 green; 3.11 plant sweep took 67 min + missing-input 20 min). Branch rebased --onto main; pushed e6f4e8e (cache/K11), 2a60957 (K17 emptied=removed), 256d44b (version 2.1.0). PR #36 opened. After merge: trigger release.yml on main (mcp__github__actions_run_trigger), then Courthouse marketplace pin.
- One intermittent full-suite failure seen once (254 tests, not reproduced in 2 logged runs); which test unknown -- log every run to scratchpad/suite.log from now on.
- AG-10 landed (pushed to #36): effect subjects {"effect": files_changed|files_removed|pids_gone} on U12 U13 U19 U03; one demand per datum; `_pay`/`_names` unify three discharge sites; observer keeps named_paths/named_pids; corpus regenerated (guard acts carry named lists); tests/test_keyed_effects.py 11 cells; cell constant_payload_pays_no_keyed_demand. Suite OK (full), replay 27/27, COQ PASS, views/cov match.
- Owner Q answered: refute stage -> Builder/medium on next resume; propagate stage -> table-derived candidate list on Builder (scripts edited; running processes still use the old text). Better still: propagation is the class-cell loop in eval/attacks.jsonl (code, no model).
- Interrupted suite run left a plant in MEASURED.tsv (act-count 9); restored with git checkout. Rule: never kill a suite mid-run; check `git status` before believing any failure.

## 19:2xZ Batch 1 landed (Keel f24eac2 on #36; CI queued 19:22Z, ~90 min)
- Simplify cuts applied by hand on head: EFF-04/06/07/08/09/10/11, ledger-1/2, dispatch-* (one-header-scan, applicable-predicate, missing-field-sentinel, one-bracket-parser, activation-nets-to-zero, unreachable-defaults), journal-2, wire-1, shim-unreachable-exit, coverings x3 (Theorem 8a label KEPT: README:325 cites it), render-coq-string-dead, render-topology-branch-unreachable, check-coq-one-coqc-per-file, clauses-v-one-result-per-class + dead-preamble (Clauses.v 537->123, results=1; both new guards witnessed red), tests-01..05/07..11 (+3 record copies the harvest predated: test_keyed_effects/test_endings/test_write_surface).
- Skipped: EFF-02/03 (LOC rises), EFF-05 (superseded by named_paths). Plant re-aimed: test_bypass header-scan `return`.
- Gates: 263 OK (scratchpad/suite.log), REPLAY 27/27, views/coverings match, COQ=PASS, pyflakes clean. LOC plugin/keel/*.py 3267->3219 (+dispatch.sh 3300); tests 6308->6249; proofs 917->487. Launch figure 2188 was a different measure (effects 622 then; now 783 after keyed effects) -- done-bar "below launch" NOT met by this measure.
- Owner 19:1xZ: scope of "finish efficiently" is EVERYTHING pending across the estate, not only Keel/Makoto/Small-Tools.

## 19:5xZ Batch 2 in progress (uncommitted in /home/user/Keel; CI on f24eac2 running since 19:22Z; check-in trig_01BEMw7TjGPQAgvoVqiSxEc2 at 21:20Z)
- Landed + cells (14 in eval/attacks.sh, all green on head, all red on f24eac2 worktree): DL-04 stop_hook_active re-arms (STOP_ROUNDS=3 then loud allow + fault row), DL-06 pre-image keyed by tool_use_id, DL-08 empty stdin loud, DL-09 pending markers -> killed hook named at Stop (hooks.json timeout 20->60), DL-10 Ledger.compact at SessionStart past 1 MiB, DL-11 observed.json carries session + root checked, DL-13 unknown event NOT-EVALUABLE (no wildcard), DL-14/P-23 AskUserQuestion/ExitPlanMode pass open demands (Task still refused), EFF-06 errored Read pays nothing, EFF-09 reflog reset/checkout observed, EFF-11 remote asked when a tracking ref moved (every remote), EFF-12 act cannot pay the demand it raised (`within=open_before`; occasion still read after the guard), MATH-10 quote-aware _segments, L2 unkeyable subject -> session-wide demand.
- Loader (Builder agent, uncommitted): L1 own-kind classification, L3 C08 key_from unwraps sh -c / keys program+subcommand, L4 leaves incl. top-level, L6 tests/test_loader_refuses.py (26 codes + census), L7 CLAUSE-NONZERO-NOT-RESPONSE + CLAUSE-GUARD-ALWAYS, L8 composed closure host only with a tool_name branch (no shipped side changed), L9 event/tools before branches.
- Stated limits written into EFFECTS text: EFF-13 concurrent writer charged to the act; DL-07 gitignored content / outside-root unobserved (top-level ignored removals now named); EFF-14 short-lived worker; MATH-07 report_self reads the command.
- No-verdict rerun (scratchpad/ledger/gen3-noverdict-rerun.md): FIXED DL-01 P-02 MATH-01/02/03. Still reproducing and DISPOSITIONED: owner row 1 (marker): DL-03 P-20; owner row 3 (report shapes): EFF-01/02/03/04 P-11 P-13 MATH-08; owner row 2 (inert/duplicate rows): DL-02 P-21 P-04 P-25 P-01 P-24; stated limits: DL-05 (one state dir, sessions distinct by id -- check), DL-12 (ledger writable by the agent: outside the threat model), P-14 (pids_gone assignment, same as EFF-13), P-26 (T02 measured by Keel itself, by design). DL-14/P-23 fixed above.
- Still to do in Batch 2: MATH-04 IDENTITY shapes, MATH-06 backward requires X before L (re-prove 8a), MATH-07/09 comments; full gates; commit; push after #36 merges (rebase --onto).
- OWNER 20:0xZ (verbatim): "Also we need a check, if the code directly was built from the math there would be nothing to remove, so we need multiple agents to check for mismatch's via a mathmatics ledger that find the equivalency of it exists, and marks it off, not the whole functions necessarily btw it's a very granular marking, once everything is done, what isn't filled and isn't marked becomes a list of what to add and remove, anything that is close but not quite a match and it's the only one, gets replaced with the corrected version" -> task #8, run on Keel after Batch 2 commits.
- OWNER 20:1xZ (verbatim) on the math-ledger process: "We use BUILDER Audited by review With the actual edits approved by signoff once, for this process" / "Then built by builder, audited by review signed off briefly by signoff".
- 20:2xZ Batch 2 COMMITTED ba072ce and PUSHED to #36 (restarts CI; ~90 min). Old worktree removed. Next: math ledger (task #8) on ba072ce; then Batch 3 pages after merge.
- 20:5xZ: Ward PR #20 (418f4e9+12ca939: WM-05/06/07, 3 cells red-on-old) open+subscribed. Discontinuity matrix.py:112 row CLOSED (stale: tests/test_hinges.py landed earlier; full-suite coverage of matrix.py = 100%). #36 on ba072ce: 3.12/3.13 green, 3.11 running since 20:05Z. Math ledger: 5 enumerations done (math 229; code 266+192+184+128); 4 Builder matchers running -> marks.*.tsv; next Review audit, then Owner sign-off sign-off.
- 21:0xZ: Courthouse PR #22 (65b2d36: CH-02/03/05, 6 cells, 4 red-on-old) open+subscribed. GYRO-13 (Keel suite order-dependence): not reproduced in 4 logged full runs since; stays a watch item (every run logged to scratchpad/suite.log).
- 21:1xZ: Ward #20 MERGED 27af7a1; Courthouse #22 MERGED 2422d35; both branches reset onto main. Math marks: carriage (eq1 inst13 near19 none95), dispatch (eq4 inst52 near21 none115) done; effects + clauses matchers running. Small-Tools pollinate agent running (6 cells).
- 21:2xZ: all 4 marks done (effects eq66 inst47 near25 none128; clauses eq87 inst89 near16 none46); residue.math.tsv = 44 unmarked math rows (6 Theorems, 4 Corollaries, 6 Definitions, 12 Laws...). 4 Review auditors running -> marks.*.audited.tsv + audit.*.md. Then Owner sign-off sign-off -> edits by Builder, audit by Review, sign-off by Owner sign-off.

## 2026-09-02 20:5xZ addendum
- OWNER row 1 (commitment marker) gains a sub-item from the dispatch audit: `# gyroscope-allow:` is an
  undocumented second exemption spelling (dispatch.py:71, :119-121, :462-468); README documents only
  `# keel-allow:`. Recommendation: REMOVE the legacy spelling (an extra allow route no page states);
  the rename notice can ride on a deny that names the rename. Not built without the owner.
- Small-Tools: PR #22 open (aa5c3be), six pollinate cells closed; gate 41/41, pollinate 63/63.
  Dispositions (small-tools-rank.md) still the owner's.
- Math ledger: four Review audits in; Owner sign-off sign-off at math/SIGNOFF.md; builders A-D running in
  worktrees at ba072ce, patches land as math/patch.{A,B,C,D}.diff. Next: Review audit of the four
  patches, Owner sign-off sign-off, integrate on the branch after #36 merges and rebases, one push.

## Instrument defect (2026-09-02 20:5xZ), root cause recorded
`isolation: worktree` does NOT create the worktree at the session's current HEAD. All four math-ledger
builder worktrees were created at 4f50fcd (Keel main, the #35 squash) while the working tree and the
branch are at ba072ce (Batch 2). Only builder A checked and `git reset --hard ba072ce`; builder D did
not, and reported four "pre-existing failures" that are simply Batch 2 missing from its tree. B and C
were corrected mid-run; D was resumed to rebuild on ba072ce.
STANDING RULE: every worktree agent's prompt must make its FIRST action `git rev-parse --short HEAD`
and reset to the assigned sha, and must report the base it actually built on. A red witness observed
on the wrong base proves nothing.
Verified after the correction: patch.A.diff applies clean to ba072ce (`git apply --check` exit 0);
suite at ba072ce is 271 tests, green (builder A, executed).
