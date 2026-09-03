# Owner sign-off sign-off — Makoto math ledger (2026-09-02, head 6e577b4)

Verified at the head before signing: claimedRunningAbsent.py:128-142 (`_latest_process_call_failed`
returns None when no command matches the net), :145-164 (None -> BLOCK), :87-93 (the author already
fails OPEN on an undecodable row, stating that silently dropping it "would push the emptiness branch
toward BLOCK, the opposite of fail-open"), the SCOPE note :29-45, and docs/CATALOG.md:18.

## 1. APPROVE REPLACE — the false block (highest value item in this ledger)
An unlisted launcher (`air`, `bun run dev`, `php artisan serve`, `caddy run`) does not match
`_PROCESS_LIFECYCLE_CMD_RX`, so the verdict is None, and None is routed to the UNFULFILLED BLOCK whose
message says "no process-start or liveness-check Bash command appears". The agent DID start the
process; only the classifier missed the name. docs/CATALOG.md:18 states this case is "a documented
recall bound, never a false-block source" — false as shipped, in the expensive direction.

CORRECTED RULE (three-valued, and it is the module's own fail-open rule applied consistently):
  - no Bash terminal in history at all            -> UNFULFILLED, fire (the claim has no world behind it)
  - Bash terminals exist, none matched the net     -> NOT-EVALUABLE, SILENT (a vocabulary miss is not a
                                                      contradiction; identical in kind to the
                                                      `saw_undecodable` arm already at :140-141)
  - most recent matching call errored/interrupted  -> MISREPORTED, fire (unchanged)
  - most recent matching call clean                -> silent (unchanged)
`_latest_process_call_failed` must therefore report the three cases apart, not collapse two into None.
WITNESS both directions before either colour: a session whose only Bash call is `air` + a running claim
must NOT fire (red on the shipped code); a session with NO Bash call + the same claim must still fire.
Do not widen the launcher net as the fix — a longer list is as monotone as a short one, and widening it
would leave the false block in place for the next unlisted name.

## 2. APPROVE REPLACE — the second runner list
`_LEAD_RUNNER_RX` (24 branches) diverges from the shared `vocab._TEST_RUNNER_RX`; `python -m unittest`,
`tox`, `nox`, `just test`, `rails test`, `cargo nextest` escape verifierExitMasking while sitting in the
package's own lexicon. Read the shared lexicon; delete the private copy. If the masking check needs a
narrower set than the lexicon, it takes a documented SUBSET of it, derived from the lexicon at import,
never a second hand-maintained list. Witness: a masked `tox || true` fires after, does not before.

## 3. APPROVE STATEMENT-FIX (code right, sentence wrong)
- claimedRunningAbsent.py:43-45 "unlike every other gate, this one reads history_all_agents" —
  claimedShippedAbsent.py:310 reads it too. Fix the sentence.
- claimedRunningAbsent.py:29-33 "anywhere in the same message" — the code requires the verb outside
  `_code_spans` (:72-74). State the exclusion.
- docs/CATALOG.md:18 — rewrite the "never a false-block source" clause to the behaviour after item 1
  (an unlisted shape is silent because it is NOT-EVALUABLE, and say so).

## 4. OWNER ROW (new, do not build) — the world-fact boundary
`gate.claimed_shipped` runs `git ls-remote` against origin. README:13-16 says makoto reads no world
fact, and claimedRunningAbsent.py:16-18 cites that same rule to refuse curling a port. Two sibling
gates sit on opposite sides of one stated line. Either the README limit moves (makoto reads the remote
for landing claims, and says so) or claimed_shipped loses the network route. That is the owner's call,
not a builder's; it changes what Makoto IS. Recorded, not built.
Also recorded for that row: a real `gh pr merge` escapes both the 4-name tool set and `_is_git_push_argv`,
so "I merged it" false-blocks by the same shape as item 1.

## 5. APPROVE ledger corrections (no code)
wm08.audited.tsv replaces wm08.tsv (y=9/n=26 re-derived; the builder's TOTALS line matched neither its
own rows nor the truth). Fix `eats` rows: `open_commits`/`empty_keys` do not exist; kit.py:944
DISCHARGE_EATS is {touched, fs_exists, empty, fs_size}. Correct the vocab.py line citations (C63-C69,
off by ~300) and add `_normalized_segments`, `_top_level_count`, `PushTipResult` to code.tsv.

## 6. DEFER
verifier_exit_masking cannot move to a typed field: it is a Pre check with no tool_response, and the
vocabulary-free `testrun_exit` exists only at Stop. Recorded as a stated limit in the module, not a fix.
`run_in_background` as a typed liveness signal: `grep -rn run_in_background plugin/` returns nothing, so
it is unread today; it is a candidate for item 1's future sharpening, not part of this build.
