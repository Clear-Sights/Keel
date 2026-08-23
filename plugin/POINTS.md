# The twenty-four points

The exact moments this plugin's clauses name. The hooks stop the run and name a guard; the guard
buys one session. Each entry below names what to build so the guard's outcome arrives on every
later turn with nobody running anything — except two, `P01` and `P02`, which record an unsolved
gap instead.

The trigger text lives verbatim in `keel/clauses.json` beside this page, which is the authority:
each clause row's `construction` field anchors into this page, and the test fence resolves every
anchor against these headings. The `Denies` and `guard` lines here restate the row in prose. The
construction itself is authored — judgement lives here, and nothing generates it.

Construction numbers refer to [SKILL.md](SKILL.md): **1** data dependency, **2** one door,
**3** resident failing case, **4** set once inherited, **5** declared count.

## Contents

| | | | |
|---|---|---|---|
| [A01](#a01) push | [A02](#a02) bulk delete | [A03](#a03) force-push | [C03](#c03-verify-what-returns) what returned |
| [C08](#c08-check-can-fail) checker teeth | [C09](#c09-checker-excludes-self) self in ps | [D01](#d01) dispatch | [P01](#p01) plan from nothing |
| [P02](#p02) guessed reading | [T01](#t01) declaring done | [T02](#t02) push landed | [U01](#u01) nested worker |
| [U02](#u02) re-launch | [U03](#u03) signal a pid | [U06](#u06) external mutation | [U08](#u08) signed commit |
| [U09](#u09) checkout a ref | [U10](#u10) traverse JSON | [U12](#u12) apply a patch | [U13](#u13) generated patch |
| [U19](#u19) in-place rewrite | [U20](#u20) behaviour mutation | [U24](#u24) release | [U25](#u25) scanner |

---

## A01
**Push with no `git status` on record.**

- **Denies:** push without knowing what is staged or which branch is current.
- **Its guard:** run `git status` first — buys the session.
- **Construction (4):** two settings and one habit, and the question stops being askable.
  `git config --global push.default simple` refuses a bare `git push` whose upstream is named
  differently, so for refspec-free pushes "which branch" is answered by refusal rather than by
  memory. `git config --global status.showUntrackedFiles all` stops the collapsed-directory
  summary that hides new files. Then stage by explicit path only — never `git add -A` — so this
  invocation stages nothing you did not name; what was staged earlier is what the honest `status`
  now shows. `--global` matters: a `--local` setting is one setup act per clone, which is the
  caveat below applied to this entry's own settings.
- **Caveat, and it is the third counterfeit:** a `pre-push` hook is the obvious answer and it is not
  cloned. `core.hooksPath .githooks` moves the hooks into the tree but the setting itself is still
  per-clone. Anything needing one setup act per clone has moved its maintenance cost, not removed it.

## A02
**Bulk delete over a set nobody enumerated.**

- **Denies:** delete a set whose members were never listed, so the loss leaves no record of what it was.
- **Its guard:** list the set first (`ls`, `find` without `-delete`, or `git status`).
- **Construction (1):** make the list the argument. The delete then cannot be typed without it.
  ```sh
  find build -type f -print0 > deleted.list && xargs -0 rm -- < deleted.list
  ```
  The manifest lands whole before the first removal — a streaming `tee` starts deleting while the
  record is still being written — and the NUL delimiters keep a space in a filename from splitting
  one path into two.
  `git rm` is the same construction with the record kept for you: the set is in the index, so what
  was there is reconstructible from a tree that already exists.
- **Then:** every future delete carries its own manifest, because a delete without one does not run.

## A03
**Force-push over a ref whose tip was never fetched.**

- **Denies:** overwrite remote history that was never read, discarding commits with no local copy.
- **Its guard:** fetch the ref first (`git fetch`).
- **Construction (4):** `--force-with-lease` carries the check inside the act — it refuses when the remote
  moved past what you last saw. Add `git config --global push.useForceIfIncludes true` so a lease
  silently refreshed by a background fetch does not cover commits you never integrated — it guards
  the bare and ref-only lease forms, is bypassed by an explicit `<ref>:<expect>` lease, and does
  nothing without the lease flag, so the lease is the construction, not the setting.
- **Then:** forgetting to fetch produces a refusal instead of an overwrite. Both fates stay
  reachable; the destructive one now costs a lease a stale ref cannot produce.

## C03-verify-what-returns
**Ending after delegated work with nothing read.**

- **Denies:** end the run by inheriting delegated work without inspecting what came back.
- **Its guard:** read a returned artifact after dispatch and before stopping.
- **Construction (1):** have dispatch return a **path**, not a summary. If the contract is "write your
  result to `out/<unit>.json` and return the path", then using the result requires opening it, and a
  unit that wrote nothing leaves a missing or empty file rather than a confident paragraph.
- **Then:** "work returning no output did not happen" becomes observable instead of remembered.

## C08-check-can-fail
**A checker PASS that has never been observed rejecting anything.**

- **Denies:** accepting a checker PASS that has never demonstrated it can reject an invalid or
  absent input.
- **Its guard:** observe a nonzero result from the same normalized checker invocation.
- **Construction (3):** move the plant into the suite. A `test_the_check_can_fail` that copies the input,
  mutates one byte, runs the **real** checker under the identical invocation, asserts nonzero, and
  restores byte-exact — then every future run of that suite re-proves the fence has teeth.
- **Restore by copy, not by arithmetic.** Truncating back by a byte count is how a restore silently
  under-counts; compare shas after restoring rather than trusting the subtraction.
- **Also plant absence, not only corruption.** Delete the input and require red. A fence that passes
  when its input is gone is not a fence.

## C09-checker-excludes-self
**A `ps` pipeline that can match its own checker.**

- **Denies:** count or trust a grep-shaped process match without excluding the observer identity.
- **Its guard:** run a process listing filtered by the shell or checker PID before trusting the match.
- **Construction (2):** one door. Define the listing once, with the exclusion and the match inside it,
  and never call `ps` directly again.
  ```sh
  procs() { ps -eo pid,args | awk -v me="$$" -v kid="$BASHPID" -v pat="${1-.}" \
              '$1 != me && $1 != kid && $0 ~ pat'; }
  ```
- **Match inside the door:** `procs worker` filters in the same `awk` that excludes self. A
  downstream `procs | grep worker` reopens the hole — `grep` is a new process the snapshot can see.
- **Then:** the self-match is unconstructible, because the only listing in the repository excludes self.

## D01
**Dispatching work with nothing probed.**

- **Denies:** fan out work with nothing probed first.
- **Its guard:** probe the ground first with a read or a search, so the brief describes what is there.
- **Construction (1):** make the search's output a field of the brief, and let the render step run the
  search and inject what it returned. A field a hand can fill is a field a hand will fill; the
  dependency holds only while the tool, not the author, supplies it.
- **Then:** the returned work is built on this repository rather than a remembered one — and the
  result of a bad brief is inherited whole.

## P01
**Presenting a plan built on nothing read.**

- **Denies:** adopt a plan built on nothing read.
- **Its guard:** read something first, so the plan describes this repository and not a remembered one.
- **Construction: unsolved.**
- **Candidate, untried:** require every claim in a plan to carry a `path:line` anchor, and render the
  plan through a tool that resolves each anchor against the tree and refuses any that does not
  resolve. That would be construction 1 — a plan citing nothing that resolves would not render.
- **The candidate's own limit:** an anchor can be guessed and still resolve — resolution proves the
  place exists, not that it was read — so the candidate narrows the failure rather than removing
  it. The vendored guard shares the softness: it observes that a read-shaped call happened, not
  that it landed or mattered.
- **Why the obvious answer fails:** "read something first" as a checklist item is the added ritual
  exactly. The plan still presents when nobody reads.
- **Where the candidate comes from:** the execution prompt's "Absence is a claim: name where you
  looked and where it could remain" — a resident prompt of the imperative half, quoted whole in
  the private dev-record — made typeable: the anchor field is where you looked, and a plan that
  cannot fill it does not render.

## P02
**Presenting a plan whose ambiguity was settled by guessing.**

- **Denies:** adopt a plan built on a guessed reading of the request.
- **Its guard:** ask one question about the ambiguity before the plan is fixed.
- **Construction: unsolved, and likely unsolvable here.** Asking is a communicative act with a second party;
  no local construction makes an answer arrive when nobody asks. Reading files resolves what the
  repository is, never what was wanted.
- **Nearest miss:** give the plan a section that states, per fork, the reading taken and the reason
  it was taken without asking. An unrecorded fork is then a visible hole rather than an invisible
  assumption. That is loudness, not construction, and it depends on a reader.
- **The protocol worth following meanwhile:** the ask prompt — a resident prompt of the
  imperative half, quoted whole in the private dev-record — in one breath:
  what looking can settle is settled by looking; a fork between
  two defensible ways to do the work climbs to a more capable executor; only a fork about the
  request reaches the owner — one question per fork, every open fork batched, never serial. Record
  the decision not to ask with its reason, so judgement cannot be read as oversight, and treat a
  reaffirmed instruction as the fork's decision: proceed with the full request. The record is the
  one part that leaves a resting state behind.

## T01
**Declaring the run finished without ever asking the tree.**

- **Denies:** declare the run finished without ever asking the tree whether it is.
- **Its guard:** run `git status` at least once this session.
- **Construction (5):** make the done-bar a command rather than a sentence. If done is defined as
  `out=$(git status --porcelain --untracked-files=all) && test -z "$out"` plus a green suite — the assignment carries
  `git`'s own exit status, where `$(…)` buried in another command's arguments would discard it — then claiming done requires
  running it,
  and the claim carries its own exit code.
- **The trap this point exists for:** `git status --porcelain | wc -l` reports `wc`'s exit status,
  not `git`'s. Without `pipefail`, a pipe hands you the last command's verdict. Read the bare exit
  code.

## T02
**Ending the run treating a push report as a landing.**

- **Denies:** end the run treating a push report as a landing.
- **Its guard:** fetch or `git ls-remote` the ref after pushing.
- **Construction (5, then 2):** put the verification inside the thing you type, then wrap that in the one
  push function you use — `git` refuses an alias that shadows `push`, so the door is the shell's.
  ```sh
  git push -u origin HEAD && test "$(git rev-parse HEAD)" = \
    "$(git ls-remote origin "refs/heads/$(git rev-parse --abbrev-ref HEAD)" | cut -f1)"
  ```
  `ls-remote` asks the remote itself; a plain `git fetch` in a narrow-refspec clone can leave
  `@{u}` stale while looking fresh.
- **Then:** "it landed" stops being a belief carried forward from a success message and becomes a
  comparison that either passed or did not.

## U01
**Launching a nested worker with no capability probe.**

- **Denies:** launch a nested worker.
- **Its guard:** probe writable home, response transport, and result write before launching.
- **Construction (2):** one launcher. It probes on first use, caches the verdict for the session, and
  refuses when a capability is absent. Launching by any other path is not available.
- **Then:** capability is a property of the launcher, not of whoever remembered to check.

## U02
**Re-launching a nested-worker target after a failure.**

- **Denies:** re-launch a nested-worker target.
- **Its guard:** probe the target after failure, requiring an observed change.
- **Construction (2):** have the re-launch door refuse an invocation byte-identical to the one that just
  failed. A retry then has to carry a difference — not the full observed-target-change the guard asks
  for, but the part of it a door can hold.
- **Then:** a silent retry of a dead route stops being expressible — record the trigger and tier and
  reroute, or stop, but do not repeat the same call and hope.

## U03
**Signalling a PID that was never observed.**

- **Denies:** use a PID in a signal operation.
- **Its guard:** run `ps`, `pgrep`, or an equivalent observer-namespace process listing.
- **Construction (1):** never carry a literal PID. Let the listing produce it, so no listing means no
  argument to signal.
  ```sh
  pid=$(pgrep -f 'unique-pattern') && [ "$(echo "$pid" | wc -w)" -eq 1 ] && kill "$pid"
  ```
  Require exactly one match — several PIDs newline-joined are one invalid `kill` argument — and
  when the observer's own command line carries the pattern (a `bash -c` wrapper does), exclude
  yourself the way `C09`'s door does.
- **Then:** the observation is a data dependency of the kill, and a stale PID from three turns ago
  has nowhere to enter from.

## U06
**A mutating request to an external service with no read canary.**

- **Denies:** send a mutating request to an external service.
- **Its guard:** run an authenticated read canary first.
- **Construction (2):** one client wrapper that performs a cheap authenticated read on first use and caches
  the result for the session; every mutation goes through it.
- **Then:** an expired credential or an unreachable service surfaces on a harmless read, instead
  of on a mutation that half-applied and left a state nobody enumerated. What a read cannot prove
  — write scope, or a credential that expires after the cached first use — stays the mutation's
  own risk; the canary narrows the failure, not removes it.

## U08
**Creating a signed commit with no signer canary.**

- **Denies:** create a signed git commit.
- **Its guard:** run a signer canary such as `printf test | gpg --clearsign`.
- **Construction (4):** `git config --global commit.gpgsign true` with the signing key set, verified once
  at configuration time through git itself — a signed commit in a scratch repository; a bare
  `gpg --clearsign` exercises OpenPGP, not whatever signer git is configured to call. The failure
  this closes is the forgotten `-S`: an explicit `-S` already fails loudly, but an omitted one
  quietly produces unsigned history that looks the same in the log, and with signing the default,
  omission stops being expressible.
- **Then:** unsigned history at review stops being a discovery, because producing it now takes a
  deliberate `--no-gpg-sign`.

## U09
**Checking out a ref that was never verified.**

- **Denies:** switch or check out a git ref.
- **Its guard:** `git rev-parse --verify REF`, or having created it yourself.
- **Construction (4):** for a branch you own, `git checkout -B BRANCH START-POINT`. It creates the branch
  when absent, so "the branch exists" is true by construction rather than by having checked — one
  character over `-b`, and `-b` itself fails when the branch is already there. For any other ref —
  a tag, a remote ref — `-B` would quietly mint a new local branch at `HEAD`, so `git rev-parse
  --verify REF` stays the act.
- **Watch the other half:** `-B` resets an existing branch to the new start point. That is what you
  want when restarting a branch off a merged base, and not what you want when the branch carries
  unmerged work. Look before you reset.

## U10
**Traversing JSON whose structure was never looked at.**

- **Denies:** traverse structured JSON data.
- **Its guard:** `jq 'keys'`, `jq 'type'`, `jq -e 'has(...)'`, or any structure assertion on the file.
- **Construction (5):** make the read path assert instead of default. In `jq`, assert the shape —
  `-e 'has("key")'` on an object, `-se 'length > 0 and all(.[]; has("key"))'` over a stream —
  empty input is not an established shape — rather than the
  value: `-e` judges
  its last output, so a truthy tail can cover a missing head, and a present-but-`false` value
  fails on truthiness alone. In Python, index at the boundary and let `KeyError` land.
- **The specific defect:** `d.get("key", default)` is where a structure error becomes a silent wrong
  value that travels. Reserve defaults for fields that are genuinely optional, and let the rest raise.
- **Then:** a missing shape fails at the access that needed it, instead of defaulting into a
  wrong value that travels.

## U12
**Applying a patch.**

- **Denies:** apply a patch.
- **Its guard:** `rg`/`grep` for the patch context and read the target immediately before applying.
- **Construction (2):** one door for patch application, with `git apply --3way` inside it. When the base
  blobs are known to the repository, a three-way apply surfaces overlapping edits as conflict
  markers instead of a quiet landing — when they are not, it falls back to a plain apply, and
  context that matches in two places stays the read's job: `--check` cannot see placement, as
  `U13` records.
- **Better where it is available:** regenerate the change from source rather than transporting a
  diff. A patch is a diff against a tree you are asserting you still have.

## U13
**Applying a generated patch.**

- **Denies:** apply a generated patch.
- **Its guard:** `git apply --check PATCH` first.
- **Construction (2):** the same door as `U12`, with `--check` as its first statement, run with the same
  options the apply will use (`git apply --check --3way PATCH`) so the preflight exercises the
  path the apply takes. A generated patch has a producer and a consumer in one session, so the
  door is the only place both meet.
- **Known limitation of the guard:** `git apply --check` establishes that the hunks apply, not that
  they apply where you meant. Pair it with the `U12` context read; `--check` alone is a weaker claim
  than it reads as.

## U19
**Rewriting text in place without looking at the text.**

- **Denies:** perform an in-place text rewrite.
- **Its guard:** `rg`/`grep` for the pattern, or `cmp`/checksum the file.
- **Construction (5):** declare the count. A rewrite that states how many places it expects to change, and
  fails on any other number, cannot match zero and report success, and cannot match forty and take
  them all.
  ```python
  n = src.count(old)
  if n != 1:
      raise ValueError(f"expected 1 occurrence, found {n}")
  path.write_text(src.replace(old, new))
  ```
  A raise, not an `assert` — Python drops assertions under `-O`, and a count fence that an
  interpreter flag can remove is a fence with a gate in it.
- **Why counts and not eyes:** `sed -i` exits 0 whether it matched nothing or everything.

## U20
**A destructive behaviour-changing mutation with no independent observer.**

- **Denies:** make a destructive behavior-changing mutation.
- **Its guard:** run an independent behavior observer such as the relevant test or probe first.
- **Construction (3):** commit the observer's output as a fixture, and let the suite run the comparison.
  Once the golden output is in the tree and a test diffs against it, the "before" is already
  recorded and every later mutation is judged with nobody remembering to capture a baseline — a
  snapshot nothing compares is a photograph, not an observer.
- **Then:** the observer stops being a step in front of the mutation and becomes a resident of the
  suite, which is the same move `C08` makes for the checker itself.

## U24
**Publishing or releasing an artifact after runtime testing.**

- **Denies:** publish or release an artifact after runtime testing.
- **Its guard:** run the suite with warnings promoted to errors on a supported runtime.
- **Construction (4):** one line in the project config.
  ```toml
  [tool.pytest.ini_options]
  filterwarnings = ["error"]
  ```
- **Then:** every future pytest run that loads this config — local, CI, someone else's clone —
  promotes warnings, and nobody types `-W error` again for those. Runs outside pytest stay
  uncovered, and the plugin's own release guard stays its own. Still the purest entry in this
  table: one line, inherited by callers who never heard of it.

## U25
**Running a scanner as an acceptance check.**

- **Denies:** run a scanner as an acceptance check.
- **Its guard:** run its prefix-distractor regression test first.
- **Construction (3):** move the distractor into the scanner's own test file — a valid near-miss the
  scanner accepts, then a bad target it rejects, in that order — so the case runs whenever the
  scanner's suite runs. A scanner is trusted on the strength of what it refuses to match, and that
  refusal wants to be a permanent resident rather than an act somebody performs.
- **Then:** a pattern that silently widens — the substring match that matches a whole document
  instead of a table row — goes red on the next run rather than on the next incident.
