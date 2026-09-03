# Audit — makoto ledger (auditor: review, 2026-09-02, head 6e577b4)

Sources read: `plugin/makoto/checks/claimedRunningAbsent.py` (182 lines), `claimedShippedAbsent.py` (312),
`verifierExitMasking.py` (273), the shared lexicon `plugin/makoto/vocab.py` (607 lines — the module 30 of
the 35 check modules import word lists from), `plugin/makoto/registry.py`, `tests/test_check_law_eats.py`,
`README.md`, `docs/CATALOG.md`, `docs/self-defense-asymmetry-followup.md`, plus every module under
`plugin/makoto/checks/` and the atoms/plumbing they fire through (`substrate/_canonAtoms.py`,
`core/_shell.py`, `state/plan.py`, `kit.py`, `context.py`, `dispatch.py`).
Outputs: `marks.audited.tsv`, `wm08.audited.tsv`.

## 1. Counts

| verdict | rows |
|---|---|
| confirm | 23 |
| amend | 24 |
| reject | 0 |
| **total** | **47** |

Relation distribution after audit: equal 8 (was 20), instance 26 (was 17), near 10 (was 9), none 3 (was 1).
No row was rejected: every pairing had a real statement behind it, but 24 named the wrong relation, cited
a line the code does not contain, or rested on an evidence sentence that is factually false about the code.

The dominant amend class (12 rows) is **compound law vs. one branch**: the builder wrote `equal` where a
single `if` arm implements one disjunct of a two- or three-clause docstring sentence. Per SCHEMA's
"same quantifier, same fail direction, same domain", those are `instance`. The rule I applied and did not
apply uniformly by name: a **constant** whose members are verbatim the law's enumeration stays `equal`
(L25/C24, L14/C24); a **branch** implementing one clause of a compound behavioural sentence becomes
`instance`.

WM-08 census, re-derived from every firing predicate (`wm08.audited.tsv`):
`can_fire_without_any_word_or_name` **y=9, n=26** (builder: y=12, n=23 — and its own TOTALS line said
y=13/n=22, which matched neither its rows nor the code). `own_word_list` y=21, n=14 (builder: y=20, n=15
with 2 rows left "unknown"). `imports_lexicon` y=14, n=21 — confirmed unchanged.

## 2. REMOVE — code implementing no statement, no stated law, and not necessary carriage

Nothing in these three modules is a remove. Every element in `code.tsv` either implements a stated law or
is necessary carriage (decode, subprocess plumbing, tokenizing, dataclass shape). Two near-misses, both
kept:

- `C55` `_STATUS_CAPTURE_RX = \$\?` (verifierExitMasking.py:96) is a one-token regex, but the docstring
  names "`$?` captured but never returned" as a masking shape, so it carries L27.
- `C42` `_is_exit_zero_literal` accepts `:` as well as `true`; the docstring says "`true` (any spelling) or
  `:`" at :174, so it is stated.

The one genuinely unstated behaviour is not a remove but a REPLACE (§4): the classifier's fail direction.

## 3. ADD — residue math rows the code should implement and does not

- **`L03` (README.md:13-16) — "never the world's truth; it holds no facts."** `pushed_tip_matches_remote`
  (claimedShippedAbsent.py:35-89) shells out to `git ls-remote origin` and decides a BLOCK on what the
  network answers. That is a world fact, fetched live, by makoto itself — the one thing README:13-16 says
  makoto never does, and the same sentence claimedRunningAbsent.py:16-18 invokes to explain why it will not
  "go curl a port". Either the README limit needs an explicit remote-observation carve-out, or the push
  route needs to fall back to the recorded-mutation evidence it already has (C27). Today the two most
  similar gates in the catalog take opposite sides of that line with no statement reconciling them.
- **`L08` (README.md:266-270) — no non-blocking tier — is implemented in `registry`'s advisory allowlist and
  in each advisory module's `level=`, none of which is in `code.tsv`.** Not an ADD against the code; an ADD
  against the census (§6).
- **`L16`/`L17` (self-defense-asymmetry-followup.md) have no code at all, correctly.** The document records
  an OPEN ticket and a settings.json install state; `selfWiredCheck.py` implements the partial-strip
  detection README:279-293 describes, not the asymmetry the followup says is unclosed. Leaving it unmarked
  is right — but note the followup's factual claim ("this repo's live wiring is legacy settings.json") is a
  claim about the environment, not about `plugin/`, and nothing in `plugin/` can satisfy or falsify it.
- **`L34` (vocab.py:43) — `fire_level` "no longer runtime-checked here"** is satisfied by absence in
  `vocab.py` and enforced in `tests/test_stop_gate_level_invariant.py`, outside the marked surface. Not an
  ADD; a census gap.

## 4. REPLACE — unique near-matches where the code should become the corrected form

- **`C65`/`C10` — `_PROCESS_LIFECYCLE_CMD_RX` (vocab.py:437-449) against `L12` (CATALOG.md:18) and `L20`
  (claimedRunningAbsent.py:35-41).** Both statements say an unlisted launcher/healthcheck shape is "a
  documented RECALL bound, never a false-block source", and that only a POSITIVE contradiction bites. The
  code does the opposite. `_latest_process_call_failed` returns `None` when no command matched
  (claimedRunningAbsent.py:134-135, 142), and `None` is routed at :155-164 to a **BLOCK** — "no
  process-start or liveness-check Bash command appears". So `air -c .air.toml`, `bun run dev`, `php artisan
  serve`, `deno task start`, `caddy run`, `make serve`, `tmux new-session -d '…'` — every real launch the
  34-branch net does not spell — produces a *false block*, not a recall miss. Corrected one-line rule:
  **an unmatched command vocabulary yields no verdict, not a contradiction: when no lifecycle-shaped call is
  recognised, `claimed_running_gate` must fall open exactly as it does for a clean exit (:175), and fire
  only on the positive `failed is True` branch.** This is the module's own fail-open doctrine (:124-127
  already returns `False` rather than `None` when a single undecodable row makes emptiness unassertable —
  the same reasoning, applied to one row but not to the vocabulary as a whole). Only candidate for the
  statement, so the code moves.
- **`C36` — `_LEAD_RUNNER_RX` (verifierExitMasking.py:46-51) against `L31`.** A second, divergent runner
  vocabulary sits beside `vocab.py:_TEST_RUNNER_RX` and is *narrower*: `tox`, `nox`, `unittest`, `just
  test`, `rails test`, `cargo nextest` are in the shared lexicon and absent here, so `python -m unittest ||
  true` and `tox || true` pass the gate while `pytest || true` is blocked. Corrected one-line rule: **the
  runner set for exit-masking is the shared `_TEST_RUNNER_RX` lexicon (L32's "one edit governs every
  surface"), anchored to the post-launcher leading command; a runner in one list and not the other is a
  vocabulary bug, not a scope decision.**

## 5. STATEMENT-FIX — the statement is wrong or missing and the code is right

- **claimedRunningAbsent.py:43-45** — "unlike every other gate, this one reads `ctx.history_all_agents`".
  False: `claimedShippedAbsent.py:310` declares the same field. The code is right; the uniqueness clause
  must go (mark L21/C13).
- **claimedRunningAbsent.py:29-33** — the FP firewall says the start verb need only co-occur "anywhere in
  the same message". The code additionally requires it OUTSIDE quoted/fenced spans (:72-74), for the reason
  the function docstring gives at :66-69. The narrower rule is correct; the module docstring should state it
  (mark L19/C02).
- **claimedShippedAbsent.py:101-106** — the CLOSED NON-BASH SET paragraph says `merge_pull_request` and
  `push_files` "are actual shipping actions" and stops there. The code demands `merged: true` for merges
  (:228, C28); only CATALOG.md:21 states that. The module docstring should carry it (mark L25/C28).
- **claimedShippedAbsent.py:234-253** — the routing docstring never states the `pos = claim.end()` loop's
  own fail direction: an unevaluable claim is skipped, and the gate returns `None` only when the text runs
  out (:277-278). Correct and deliberate, unstated.
- **Missing math rows, each implemented and each making a code row read as an orphan:**
  `_response_succeeded`'s fail-closed rule (claimedShippedAbsent.py:143-149 — a missing/empty response is
  not evidence, C26); the explicit-`exitCode == 0` bar for Bash pushes, stricter than `_response_succeeded`
  alone (:216-225, C29); the MCP JSON-string/envelope unwrapping (:174-205, C28) — a shape fact about the
  live harness with no statement anywhere in README/CATALOG; `_top_level_count`'s nested-shell scope rule
  (verifierExitMasking.py:99-115) and `_normalized_segments`' group-dissolving rule (:118-142), which are
  the actual implementation of L30 (verifierExitMasking.py:18-22) and appear in **no** `code.tsv` row; and
  the per-scope errexit/pipefail state machine (:207-233), whose "measured producing DENYs on false facts"
  justification is a stated design law with no math row.

## 6. False passes and false removes corrected

**False passes (an `equal` whose code differs from the statement):**
- `L24/C17` was `equal` on "no tool transcript accepted as a proxy". C17 fires on *missing claim text or
  cwd* — an input gap, not one of the law's enumerated unobservable-world cases. Re-marked `none`.
- `L30/C39` was `equal`. L30 is the tokenize-and-only-count-executed-commands law; `_is_runner_command`
  implements L31's leading-command clause instead. The real implementers (`_shell_segments`,
  `_normalized_segments`) are absent from `code.tsv`. Downgraded to `near`.
- `L18/C01`, `L20/C12`, `L10/C10`, `L10/C11`, `L26/C31`, `L26/C32`, `L26/C34`, `L07/C34`, `L24/C21`,
  `L11/C07` — all `equal` on compound sentences implemented one branch at a time. Ten downgrades to
  `instance` (one to `near`, L11: the same element also applies the lexical `_PROCESS_LIFECYCLE_CMD_RX`
  filter the "agnostic" sentence does not cover).
- `L19/C02` was `equal`; the code is strictly narrower than the sentence (span-filtered). Now `near`.
- `L33/C68`, `L32/C63-C67` are correctly related but every one cites a **wrong source line**: `code.tsv`
  records `vocab.py:105-114 / 116-121 / 123-137 / 453-464 / 466-478 / 52-57 / 60-71` for elements that live
  at `413-416 / 426-429 / 437-449 / 506-511 / 518-525 / 37-47 / 50-58`. The builder's vocab line numbers are
  offset by roughly 300 lines throughout; the marks are sound, the citations are not.

**False evidence corrected (relation right, reason false):**
- `L14/C29` said C29 "is the Bash-push fallback path used only when no cwd". False:
  `_successful_remote_mutation` is called at :295 for **every** claim, push or not, cwd or not; it is the
  primary evidence route for merge/publish claims.
- `L26/C32` said C32 is the "recorded ATTEMPT … FIRES" routing. False: C32 is the *continue* branch (no cwd
  AND no attempt → outside a verdict); the FIRES path is the fall-through at :295→:297.
- `L21/C13` rested on a residual-risk caveat; the actual divergence is the falsified uniqueness clause.

**False removes (a `none`/`near` that does implement a stated law):** none found. `L22/C07` is confirmed
`none` — the 1-hour window really is upstream (`dispatch.py:388`, `_select_recent`), invisible in this
module. `L29/C36` moved the other way, from `near` to `none`: a scope-cut satisfied by the *absence* of a
redirection branch is not implemented by `_LEAD_RUNNER_RX`.

**WM-08 rows the builder got wrong (all five re-derived from the firing predicate):**
- `canonFingerprints.py` y→**n**. All four `BLOCK_IDS` formulas (`_canonAtoms.py:484-489`) conjoin
  `destructive_command`, `check_disabled` or `test_run_green`, and each of those atoms is a closed
  command/flag/success-word list (`_is_destructive_argv:185`, `_DISABLE_RX:150`, `_SUCCESS_SUMMARY_RX` via
  `_test_verdict:251-269`). The advisory sibling stays **y**: `nogreen_revert_timeout` fires on
  `atom_revert_loop` (structural edit-pair reversal) plus `atom_tool_timeout`'s
  `result.get("interrupted") is True` (:334-336) with no vocabulary touched.
- `hollowTest.py` y→**n**. The AST analysis only reaches a `test_*.py`/`*_test.py` file and a `test_*`
  function (:54-57, :64-95) — a naming convention over agent-authored content is a name gate.
- `identicalRetryInterdiction.py` y→**n**. Byte-identical retry is not sufficient: :90 requires
  `classify_failure(prior_result_text) is True`, a match against `kit.py`'s `_DETERMINISTIC_MARKERS`.
- `planItemDrift.py` "y (probable)" → **n**, definitively. The module matches nothing, but a row reaches
  `open_plan_items` only because `state/plan.py:306-321` matched `_LABEL_RX` (`§9.3` / `Task #19`) **and**
  the closed `_FORWARD_VERB_RX` over chat prose. The word gate is displaced, not absent. Contrast
  `staleEstablisher.py`/`contractOrder.py`'s Stop side, which stay **y**: their `Plan` rows come from a
  declared JSONL artifact via `declare_plan` (`state/plan.py:68-95`), structured input, no vocabulary.
- `unsourcedWebfetch.py` n→**y**. The URL is read from the typed `tool_input.url` field (:134); firing needs
  no vocabulary at all — `_TRUSTED_HOSTS` only *exempts*, and the finding is produced by *absence* from
  prior `tool_response` content and the transcript (:201-223).
- Field fixes: `deferredCheckboxTheater.py` own_word_list "unknown"→y (literal `[x] DEFERRED` body regex,
  :19-22); `planItemDrift.py` own_word_list "unknown"→n; `claimedProduceAbsent.py` eats is
  `{text,cwd} | DISCHARGE_EATS{touched,fs_exists,empty,fs_size}` (:135); `undischargedCommitment.py` eats is
  `{text,opens} | DISCHARGE_EATS` (:153) — the builder wrote `open_commits` and `empty_keys`, neither of
  which exists (`kit.py:944`); `undeclaredFalsifiable.py` declares no `eats` at all.

## 7. The three raw-command checks: closed vocabularies, escapes, typed alternatives

### gate.claimed_running — three stacked closed vocabularies

| gate | vocabulary | size | source |
|---|---|---|---|
| claim subject | `_RUNNING_SUBJECT` | 18 (`it`/`this`/`that` + 15 `the <noun>` heads) | vocab.py:394-399 |
| claim predicate | `_RUNNING_PRED` + 2 banner forms | 6 state words | vocab.py:406-416 |
| FP firewall | `_PROCESS_START_VERB_RX` | 13 first-person verbs | vocab.py:426-429 |
| evidence classifier | `_PROCESS_LIFECYCLE_CMD_RX` | 34 alternation branches | vocab.py:437-449 |

All four are closed. **What escapes:** on the claim side, "the queue is up", "Postgres is accepting
connections", "the dev server came up on :3000" (verb not in the 13). On the evidence side, any launcher
outside the 34 branches — and, because of the fail direction in §4, that escape does not merely miss, it
*fires* (claimedRunningAbsent.py:134→142→155-164).

**Typed replacement: yes, partially, and it is not used.** The host already supplies the two fields this
gate needs. The verdict half is typed today (`tool_response.interrupted`, `exitCode`, PostToolUseFailure's
`error` — :136-139). The *selection* half, "was this call a process launch", has a typed answer too:
Claude Code's Bash tool carries `tool_input.run_in_background`, and `grep -rn run_in_background
plugin/` returns **nothing** — the field is never read anywhere in the package. A backgrounded launch is
exactly the case the module calls out at :38-41 as unreadable from the exit code; the host labels it, and
the gate reads a 34-branch regex instead. That would not cover foreground healthchecks, so it narrows the
vocabulary rather than eliminating it.

### gate.claimed_shipped — closed on the claim side, argv-structured on the evidence side

| gate | vocabulary | size | source |
|---|---|---|---|
| action claim | `_SHIPPED_ACTION_CLAIM_RX` | 6 verbs × 2 subject forms | vocab.py:506-511 |
| state claim | `_SHIPPED_STATE_CLAIM_RX` | 13 subjects × 6 predicates | vocab.py:518-525 |
| non-Bash evidence | `_REMOTE_MUTATING_TOOL_NAMES` | 4 names | claimedShippedAbsent.py:107-112 |
| Bash evidence | `_is_git_push_argv` | 1 program + 1 subcommand | core/_shell.py:275-288 |

**What escapes:** a real merge performed as `gh pr merge 42 --squash` matches neither the 4-name set nor
`_is_git_push_argv` (which requires `basename(argv[0]) == "git"` and subcommand `push`), so "I merged it"
with a genuine `gh` merge on record **fires a false block**. Likewise `hg push`, `jj git push`, `git subtree
push`, `git svn dcommit`, and a push performed by a CI job the agent triggered. On the claim side, "it's
landed", "it's on main now", "rolled out" escape the 6 verbs entirely.

**Typed replacement: yes, and this module already proves it.** For a claim containing `"pushed"` (:280 — a
substring test on the matched claim text, itself the last piece of vocabulary in the routing) the gate
abandons the transcript and compares `refs/heads/<branch>` with `git ls-remote` (:65-89): a world
observation with no vocabulary at all, exactly what CATALOG.md:21 means by "a successful-looking push
transcript is never accepted as a proxy". The same route is available for merge/publish claims (a PR's
merged state is observable) and is not taken; and `tool_name` plus `tool_response.exitCode` are typed host
fields, so the non-Bash half of the evidence set is already vocabulary-free — only the `git push` argv
parse and the claim regexes are not.

### content.verifier_exit_masking — one closed runner vocabulary, no typed alternative

| gate | vocabulary | size | source |
|---|---|---|---|
| runner | `_LEAD_RUNNER_RX` | 24 alternation branches (~35 distinct spellings) | verifierExitMasking.py:46-51 |
| wrappers stripped | `_WRAPPERS` | 7 | :52 |
| launchers stripped | `_LAUNCHER_SUBCOMMANDS` + `python -m` + `npx` | 6 + 2 | :55-58, :83-88 |

Closed, and narrower than the package's own shared runner lexicon. **What escapes:** `python -m unittest ||
true`, `tox || true`, `nox || true`, `just test || true`, `rails test || true`, `cargo nextest run || true`,
`deno test || true`, `bun test || true`, `./scripts/test.sh || true`, `make verify || true` (only
`test|check|lint` are spelled), and any project's own wrapper script. Every one of these is the *identical
act* the check exists to block, spelled differently. The mask side is by contrast nearly vocabulary-free —
operators, `true`/`:`, `set ±e`, `$?` — so the runner list is the whole of the recall bound.

**Typed replacement: no, not at this edge.** This is a PreToolUse check: the command has not run, so there
is no exit status, no `tool_response`, and no history row for the act being judged. `predicate` reads only
`current_event` (:197-204; `eats={"current_event","pattern"}` at :273) because nothing else exists yet. The
typed signal that would make the vocabulary unnecessary — the runner's real exit status against the green
the agent then claims — exists only *after* the call, and the repo already reads it there: head commit
6e577b4 added `testrun_exit` to `gate.green_claim` (falseGreenClaim.py:40, "THE STATUS FIRST, the tail
second… it carries no vocabulary, cannot be paraphrased"). So the honest statement of the trade is: the Pre
check can only ever be a vocabulary, and the vocabulary-free enforcement of the same law is the Stop-edge
exit-status comparison — which means the Pre check's runner list should be treated as an FP-safety filter
on a *blocking* action, not as the coverage story, and every escape above is already covered downstream by
`testrun_exit` iff the masked run still produced a `testrun` ledger row (it does not, when `|| true` makes
the shell exit 0 — which is precisely why the Pre check exists, and why widening its list buys real
coverage that no typed field at this edge can).
