# Keel

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/img/keel-hero-dark.png">
  <img src="docs/img/keel-hero-light.png" alt="Keel — do not let the session capsize irreversibly">
</picture>

**One purpose: do not let the session capsize irreversibly.**

Shipped plugin — installable and versioned. The dispatcher is replay-tested against authored sessions; its effect on a live session's outcome is unmeasured.

*Formerly Gyroscope; renamed at v2.0.0, when the positive half merged in. The mechanism is
unchanged — GitHub redirects the old repository name.*

The drift it opposes is the one where the DEFAULT is the unhealing issue. Not where an act
is dangerous, not where something ends badly — where *doing nothing* lands you somewhere that
does not heal. `rm -rf build/` is a moment; the state it leaves is one where the evidence of what
was there is gone, and you cannot correct what you cannot reconstruct. The worst of it is when
the correct path is unreachable without reversing the default — a green check is the pure case:
greenness is what ends the run, so investigating requires first reversing "it's green."

## How it heals: reversal

Keel reverses that default. Where the session would otherwise capsize — the costly act just
runs, the cheap guard is forgotten — it makes denial the resting state, so what happens when
nobody acts is the safe fate instead of the unhealing one. The method is a repricing, not a
prohibition:

| | the costly call | the guard |
|---|---|---|
| before | free — it just runs | takes effort, and is forgotten |
| after | costs one cheap call on record | free — denial is the resting state |

Same object, two reachable fates, the cost assignment swapped, nothing added. Forgetting now
produces the safe outcome, so the rule is not defeated by ordinary forgetting, and its failure
mode is loud rather than silent: the thing you wanted requires an artifact that is either there
or is not.

The repricing buys one session at a time. The pages shipped beside the clause table carry the
other half: for each denied moment, the authored **construction** that makes the guard's outcome
a property of the path — so on a path built right, the deny stops firing at all. Every clause row
anchors its construction, and the fence refuses a pairing that does not resolve.

## Why a keel

A session is a flow — the default toward *proceed, it looks complete, keep going* reasserts at
every turn, not once at entry, so one instruction at the entrance is spent by turn three. What
holds a hull against standing pressure is a keel: built once, below the waterline, permanently
there. It needs no spin, no attention and no trigger — being present is its whole job, which is
why this is a hook registered on every event rather than something that runs at session start.
With the same wind, a keel keeps the hull from being capsized or shoved
sideways — the deny half — and it is what makes sailing *toward* something possible at all: the
same pressure that would only push the boat off course becomes headway — the construction half,
where the default that used to cost you is turned into the thing that carries the work forward.
It does not choose the course; it makes the course you set holdable. The ledger is the ballast
bolted along it: the stored state that keeps the keel biting across turns, so each turn inherits
the opposition instead of re-earning it.

## The mechanism

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/img/ledger-flow-dark.png">
  <img src="docs/img/ledger-flow-light.png" alt="A costly call is denied and recorded as a demand; the cheap guard discharges it; the same call then executes; Stop blocks while demands stay open">
</picture>

A `PreToolUse` deny records a **demand**; a later call matching the clause's guard records a
<!-- BEGIN GENERATED: stop-ledger-read | source: plugin/keel/clauses.json | regenerate: python3 tools/render_views.py --write -->

**discharge**; at `Stop` anything still open blocks. That is the whole model — every
one of the 24 clause demands is read at Stop by one mechanism
([`keel/ledger.py`](plugin/keel/ledger.py) states this where the mechanism is defined).

<!-- END GENERATED: stop-ledger-read -->
A licence is an **observed discharge**, never an absent demand — the absence of evidence is never
treated as permission. The ledger's properties, each stated in the code it constrains:

- **Obligations are un-windowed within a session.** A promise does not expire because an hour
  passed; events may be windowed for cost, demands never are.
- **Absence is not a pass.** An empty ledger at Stop means nothing was recorded, which is not the
  same as nothing being owed — it is NOT-EVALUABLE. A shipped verifier once scored an *absent*
  check better than an empty one, and that inversion is the defect the ledger refuses to repeat:
  with the clause directory emptied, `rm -rf build/` was ALLOWED and Stop returned `{}` — a clean
  bill of health from a gate that checked nothing — so a zero-clause load now blocks Stop rather
  than passing it.
- **The hash chain detects corruption, not forgery.** The ledger is written by the same agent it
  constrains. The chain detects accidental corruption, a truncated write, bit-rot; it does NOT
  detect deliberate forgery — anyone who can append to the ledger can append a matching hash. No
  mechanism inside this trust boundary can do better.
- **A measured scoping limit (2026-08-14, observed, not theorised).** A nested `claude -p`
  invocation reported the SAME `session_id` as the session that launched it, with `agent_id`
  empty. Scope is keyed on `(session_id, agent_id)`, so a nested run shares its parent's ledger
  and the parent can be blocked at Stop by a demand the child raised. The keying is correct for
  the ids the host supplies — it cannot separate threads the host does not distinguish. Recorded
  rather than papered over, because a scope that silently pools is worse than one that says it
  pools.

`plugin/` is the whole package — exactly what the marketplace installs:

<!-- BEGIN GENERATED: package-clause-count | source: plugin/keel/clauses.json | regenerate: python3 tools/render_views.py --write -->

- **the dispatcher** (`keel/`) and the shipped clause table (`keel/clauses.json`,
  24 admitted clauses), the POSIX shim (`hooks/dispatch.sh`), and hook manifests for both
  supported hosts. Every fingerprint is an exact predicate over command, tool, or path identity
  — no clause infers intent from prose. The hook fails open: if the dispatcher cannot run, it
  stays silent rather than blocking the host.

<!-- END GENERATED: package-clause-count -->
- **one skill** ([`plugin/SKILL.md`](plugin/SKILL.md), with
  [`POINTS.md`](plugin/POINTS.md) and [`ACTS.md`](plugin/ACTS.md) beside it) — the positive
  half. For each denied moment it names the construction that makes the guard unnecessary from
  then on, and for the moments that leave no mark in a call sequence — budgets, plans, defaults,
  reports — the seven acts[^m-act-count] carry the same reading. Each clause row's `construction` field
  anchors into `POINTS.md`, so every negative is followed by its positive as a schema property
  the loader checks, not a cross-document convention.

### Install

- **Claude Code** — `hooks/hooks.json` is already the right shape; the bundle registers via
  `.claude-plugin/plugin.json`. Zero extra action.
- **Codex** — copy `hooks/hooks.codex.json` to the location Codex reads (`.codex/hooks.json` in a
  project).

### The cut

A bare `/compact` asks for a compaction with no preserve list. `UserPromptSubmit` supplies the
vendored one (`plugin/keel/compaction.json`, pinned by a digest of its own bytes) as context the
model acts on; a `/compact` that already carries instructions is left untouched. An automatic
compaction submits no prompt and cannot be instructed — `PreCompact`'s context is documented as
not affecting the cut, and blocking it would wedge a session whose window is already full — so
that path only reports that it ran unsteered.

### Manual bypass

A Bash command whose **leading comment block** carries `# keel-allow:` followed by a reason makes
`PreToolUse` return an empty decision before evaluating any clause:

```
# keel-allow: reviewed with the owner, the build directory is generated
rm -rf build/
```

The scan starts at the first line and stops at the first line that is not blank and not a `#`
comment, so the marker is a header an author types above the command — never something the
command supplies for itself. A marker in a heredoc body, inside a quoted string, in an appended
segment, or on a trailing comment is payload, and payload does not exempt anything. `//` and `--`
are not comment introducers here; the field is a shell command.

## Honest limitations

Limits before capability claims — read these before the clause table below.

- **The ledger constrains an honest-but-forgetful agent, not a forging one.** Its hash chain
  detects altered rows and broken or missing hashes, but not deletion of a valid tail; a writer
  able to forge rows can recompute hashes.
- **A licence is scoped to its clause and session** — one observed guard licenses later
  matching calls for that clause anywhere in the same session, not just against the same file,
  branch, or command.
- **A discharge records that the guard was invoked, not that it succeeded.** Except for
  `C08-check-can-fail`, which requires an observed nonzero exit from the checker, discharge
  predicates match the guard's command text at `PreToolUse`/`PostToolUse` — a guard command that
  fails, or names a tool this repository does not have, still discharges.
- **It does not judge prose.** Every fingerprint is an exact predicate over command, tool, or
  path identity; a clause that would need to infer intent from a command string is not admitted.
- **The denial is verified; the behaviour change is not.** "Prevented" here means exactly one
  thing: a matching costly call is denied before it executes, and that firing is deterministic —
  the corpus replay below proves the dispatcher denies at or before the derailment event in every
  authored fixture. What remains unmeasured is what a live agent does *after* the denial: whether
  it discharges the guard and retries, or routes around it. Built and mechanism-verified is not
  live-model measured; the replay proves where the dispatcher fires, not what an agent does about
  it.

## What Keel writes down

`obligations.jsonl` is a **ledger**, not a log: it records outstanding obligations, so a session in
which every clause passed leaves nothing behind — and so does a session in which the plugin never
ran. "Did Keel catch anything?" therefore had no answer at all. Not "no": *unanswerable*,
which is indistinguishable from never-installed, and which is the same absence-reads-as-green
failure this plugin refuses to accept from a session.

`keel/journal.py` closes that. It appends to `decisions.jsonl` beside the ledger: one
`session` row the first time a session is seen, carrying the loaded **clause count** — a row saying
`clauses: 0`[^m-zero-clauses] is a gate that checked nothing while everyone believes it is on — plus one row per
`deny`, per terminal `block` (including clean reconciliations, which are a positive result a
fires-only log would erase), per `fault`, and per repaired envelope. There is deliberately no row
per allowed call.

Every row names `plugin`, `session_id`, `agent_id` and `tool_name`, and every deny and block on the
wire is now prefixed `keel:`. Plugins on the
[Courthouse bench](https://github.com/Clear-Sights/Courthouse#why-a-courthouse) register
`PreToolUse`, and the host shows the user a reason but never a source.

`fault` rows carry `failed_closed`, which makes Keel's split direction — carriage open,
decision closed — checkable against the record rather than against its docstrings. See
[Courthouse docs/FAIL-DIRECTION.md](https://github.com/Clear-Sights/Courthouse/blob/main/docs/FAIL-DIRECTION.md).

## The shipped clause table

<!-- BEGIN GENERATED: shipped-clause-count | source: plugin/keel/clauses.json | regenerate: python3 tools/render_views.py --write -->

The dispatcher loads `plugin/keel/clauses.json` — 24 admitted clauses, every one carrying
positive and negative fixtures checked at load. The table below is a generated view of that
file, byte-compared against it by the test fence on every push, so it cannot quietly lag the
artifact the dispatcher loads. Each row's construction column anchors the clause's positive
half in [`plugin/POINTS.md`](plugin/POINTS.md).

<!-- END GENERATED: shipped-clause-count -->

<!-- BEGIN GENERATED: clause-routes | source: plugin/keel/clauses.json | regenerate: python3 tools/render_views.py --write -->

| ID | Costly fate | Guard | Construction |
| --- | --- | --- | --- |
| `A01` | push without knowing what is staged or which branch is current | run `git status` first | [POINTS.md#a01](plugin/POINTS.md#a01) |
| `A02` | delete a set whose members were never listed, so the loss leaves no record of what it was | list the set first (`ls`, `find` without -delete, or `git status`) | [POINTS.md#a02](plugin/POINTS.md#a02) |
| `A03` | overwrite remote history that was never read, discarding commits with no local copy | fetch the ref first (`git fetch`) | [POINTS.md#a03](plugin/POINTS.md#a03) |
| `C03-verify-what-returns` | end the run by inheriting delegated work without inspecting what came back | read a returned artifact after dispatch and before stopping | [POINTS.md#c03-verify-what-returns](plugin/POINTS.md#c03-verify-what-returns) |
| `C08-check-can-fail` | accepting a checker PASS that has never demonstrated it can reject an invalid or absent input | observe a nonzero PostToolUse result from the same normalized checker invocation | [POINTS.md#c08-check-can-fail](plugin/POINTS.md#c08-check-can-fail) |
| `C09-checker-excludes-self` | count or trust a grep-shaped process match without excluding the observer identity | run a process listing filtered by the shell or checker PID before trusting the match | [POINTS.md#c09-checker-excludes-self](plugin/POINTS.md#c09-checker-excludes-self) |
| `D01` | fan out work with nothing probed first | probe the ground first with a read or a search, so the brief describes what is there | [POINTS.md#d01](plugin/POINTS.md#d01) |
| `P01` | adopt a plan built on nothing read | read something first, so the plan describes this repository and not a remembered one | [POINTS.md#p01](plugin/POINTS.md#p01) |
| `P02` | adopt a plan built on a guessed reading of the request | ask one question about the ambiguity before the plan is fixed | [POINTS.md#p01](plugin/POINTS.md#p01) |
| `T01` | declare the run finished without ever asking the tree whether it is | run `git status` at least once this session | [POINTS.md#t01](plugin/POINTS.md#t01) |
| `T02` | end the run treating a push report as a landing | fetch or `git ls-remote` the ref after pushing | [POINTS.md#t02](plugin/POINTS.md#t02) |
| `U01` | launch a nested worker | run `python3 tools/probe_child_capability.py --writable-home --response-transport --result-write` | [POINTS.md#u01](plugin/POINTS.md#u01) |
| `U02` | re-launch a nested-worker target | run `python3 tools/probe_child_capability.py --target TARGET --after-failure --require-change` | [POINTS.md#u02](plugin/POINTS.md#u02) |
| `U03` | use a PID in a signal operation | run `ps`, `pgrep`, or an equivalent observer-namespace process listing | [POINTS.md#u03](plugin/POINTS.md#u03) |
| `U06` | send a mutating request to an external service | run an authenticated read canary such as `curl ... -H 'Authorization: ...'` | [POINTS.md#u06](plugin/POINTS.md#u06) |
| `U08` | create a signed git commit | run a signer canary such as `printf test \| gpg --clearsign` | [POINTS.md#u08](plugin/POINTS.md#u08) |
| `U09` | switch or check out a git ref | know the ref exists: `git rev-parse --verify REF`, or have created it yourself with `git checkout -b/-B REF` or `git branch REF` | [POINTS.md#u09](plugin/POINTS.md#u09) |
| `U10` | traverse structured JSON data | look at the structure first: `jq 'keys'`, `jq 'type'`, `jq -e 'has(...)'`, or any jq structure assertion on the same file | [POINTS.md#u10](plugin/POINTS.md#u10) |
| `U12` | apply a patch | run `rg`/`grep` for the patch context and read the target immediately before applying | [POINTS.md#u12](plugin/POINTS.md#u12) |
| `U13` | apply a generated patch | run `git apply --check PATCH` first | [POINTS.md#u13](plugin/POINTS.md#u13) |
| `U19` | perform an in-place text rewrite | look at the text you are about to rewrite: `rg`/`grep` for the pattern, or `cmp`/checksum the file | [POINTS.md#u19](plugin/POINTS.md#u19) |
| `U20` | make a destructive behavior-changing mutation | run an independent behavior observer such as the relevant test or probe first | [POINTS.md#u20](plugin/POINTS.md#u20) |
| `U24` | publish or release an artifact after runtime testing | run the suite with warnings promoted to errors on a supported runtime | [POINTS.md#u24](plugin/POINTS.md#u24) |
| `U25` | run a scanner as an acceptance check | run its prefix-distractor regression test first | [POINTS.md#u25](plugin/POINTS.md#u25) |

<!-- END GENERATED: clause-routes -->

Three clauses[^m-local-tooling-clauses] (`U01`, `U02`, `U25`) name repository-local tooling in their guards or
fingerprints. What happens when that tooling does not exist in the current repository — read from the
dispatch code, not guessed:

- **The demand is raised anyway.** `pre_tool_use` demands whenever a clause's fingerprint matches,
  with no check that the guard is runnable here; an open demand then blocks at Stop.
- **In practice `U01`/`U02` are scoped out by their own fingerprints**, which match a
  `dispatch.sh` invocation — a repository without that launcher never triggers them.
- **`U25` is demanded anyway.** Its fingerprint is generic (any `python3 …scan….py`, or a
  `npm/go/cargo test … scanner` invocation), so a new adopter running any scanner script is denied
  and, undischarged, Stop-blocked — dischargeable only by a test invocation whose command text
  contains `prefix` or `distractor`. Per the discharge limit above, the ledger records that such a
  command was *invoked*, not that the named regression test exists or passed.

## Evidence

`python3 eval/replay.py` from the repository root replays recorded sessions through the real
dispatcher: three derailments[^m-derailments] (a push with no status on record, a force-push with no fetch, a
"done" claim over a dirty tree) each denied at or before the event where the session went wrong,
a recovery session where the same denied call passes after its guard, and a benign control that
stays silent — 5/5,[^m-replay] standard library only, and succeeds iff every session meets its expectation.

## Why this is not a deny list

[Ward](https://github.com/Clear-Sights/Ward), a sibling plugin, is a deny list: its verdict is a
pure function of one event. For a matching costly call, Keel's decision
is a function of `(event, ledger)`: it is denied before the clause's guard discharge and admitted
afterward. Keel does not substitute a safer action and does not remove a fate — it changes
whether the *same* call executes now or waits until its licensing evidence exists.

## Siblings

Keel is the sequence engine in Courthouse's act/sequence/statement taxonomy; the engines share
nothing else. They install from the [Courthouse](https://github.com/Clear-Sights/Courthouse)
marketplace: `claude plugin marketplace add Clear-Sights/Courthouse`.

| Engine | Judges | One line |
|---|---|---|
| [**Ward**](https://github.com/Clear-Sights/Ward) | the pending **act** | nothing outright bad happens |
| **Keel** (this repo) | the **sequence** | a session neither capsizes nor gets lost |
| [**Makoto**](https://github.com/Clear-Sights/Makoto) | the **statement** | words aren't empty |

## License

Apache-2.0 — see [LICENSE](LICENSE).

[^m-act-count]: The act headings in `plugin/ACTS.md`, counted by the `act-count` command in `MEASURED.tsv`.
[^m-zero-clauses]: A session journal row produced with an empty admitted-clause set, read by the `zero-clauses` command in `MEASURED.tsv`.
[^m-local-tooling-clauses]: Clause rows whose guard or fingerprint names Keel's repository-local tools, counted by the `local-tooling-clauses` command in `MEASURED.tsv`.
[^m-derailments]: Corpus headers with the ordinary firing expectation, counted by the `derailments` command in `MEASURED.tsv`.
[^m-replay]: Passing sessions over corpus sessions, measured by the `replay` command in `MEASURED.tsv`.
