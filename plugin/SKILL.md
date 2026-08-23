---
name: keel
description: >-
  Use before a call that decides what the rest of the run inherits — pushing, force-pushing,
  deleting files or rules, checking out a ref, applying a patch, rewriting text in place, signing
  a commit, releasing an artifact, traversing JSON, signalling a PID, mutating an external
  service, launching a nested worker, dispatching work to a subagent, presenting a plan, reading
  what a subagent returned, trusting a process listing, trusting a scanner, trusting a checker
  never seen failing, or declaring a run finished — and when a default, budget, plan, or bare
  result is being set or adopted. The hooks deny each costly act until its cheap guard is on
  record this session; this page names the construction, where one exists, that makes the guard
  unnecessary from then on — a data dependency, a single door, a resident failing case, a setting
  every later call inherits, or a declared count — so the safe outcome arrives when nobody does
  anything.
---

# Keel

One sentence underneath both halves of this package:

> Asymmetry is where the DEFAULT is the unhealing issue.

Read for harm, that finds the moments where *doing nothing* lands somewhere that does not heal —
the push nobody checked, the delete nobody listed, the green nobody has seen fail. The hooks
read it that way and **deny**: a costly call is refused until the cheap call that licenses it is
on record, so forgetting produces the safe outcome instead of the unhealing one.

Read the other way, the same sentence finds **benefit that arrives with no author**: an advantage
that, once set up, arrives on every later turn while nobody attends it. This page and the pages
beside it read it that way and **construct**: for each denied moment, what to build so the
guard's outcome is a property of the path and the deny never fires again.

The deny buys one session. The construction retires the payment.

## The one test

> **If nobody does anything next time, does the good outcome still arrive?**

Run it on the state a setup leaves, never on the setup act. Yes — a construction; build it.
No — a ritual, forgotten by the third turn, or one of the [counterfeits](#counterfeits) below.

## The five constructions

Two tiers. The first two remove the wrong path; the last three leave it reachable but make
missing it loud instead of silent. Prefer the higher tier.

### Tier 1 — the wrong outcome becomes unconstructible

**1. Data dependency.** Make the guard's output the act's input. The act cannot be typed
without it.

```
before   rm -rf build/                                                  # the list is a thing you were meant to run
after    find build -type f -print0 > list && xargs -0 rm -- < list     # the list IS the argument
```

**2. One door.** Give the act exactly one entry point and put the guard inside it. Every later
call inherits the guard because there is nowhere else to call from.

```
before   "remember to exclude your own pid from the ps match"
after    procs() { ps -eo pid,args \
                   | awk -v me=$$ -v kid="$BASHPID" -v pat="${1-.}" '$1!=me && $1!=kid && $0~pat'; }
```

### Tier 2 — the wrong outcome stays reachable, but cannot be silent

**3. Resident failing case.** Move the planted fault into the suite. Every future run re-proves
the check has teeth, with nobody remembering to plant anything.

**4. Set once, inherited.** One setting makes the safe fate the default for every later call in
that repository, tool, or environment — `filterwarnings = ["error"]` and nobody types `-W error`
again.

**5. Declared count.** Have the operation state what it expects to change, and fail on
divergence. A rewrite that matched nothing, or forty places instead of one, stops being
survivable.

Each point's entry in [POINTS.md](POINTS.md) names which construction it takes; `P01` and `P02`
carry none and say so — two points out of twenty-four are recorded unsolved rather than filled
with something that merely reads like a construction.

## The clause routes

The table below is a generated view of `keel/clauses.json`, the artifact the dispatcher
actually loads — one writer, and the build compares this rendering against it byte for byte, so
this page cannot quietly lag the table it describes.

<!-- BEGIN GENERATED: clause-routes | source: keel/clauses.json | regenerate: python3 tools/render_views.py --write -->

| ID | Costly fate | Guard | Construction |
| --- | --- | --- | --- |
| `A01` | push without knowing what is staged or which branch is current | run `git status` first | [POINTS.md#a01](POINTS.md#a01) |
| `A02` | delete a set whose members were never listed, so the loss leaves no record of what it was | list the set first (`ls`, `find` without -delete, or `git status`) | [POINTS.md#a02](POINTS.md#a02) |
| `A03` | overwrite remote history that was never read, discarding commits with no local copy | fetch the ref first (`git fetch`) | [POINTS.md#a03](POINTS.md#a03) |
| `C03-verify-what-returns` | end the run by inheriting delegated work without inspecting what came back | read a returned artifact after dispatch and before stopping | [POINTS.md#c03-verify-what-returns](POINTS.md#c03-verify-what-returns) |
| `C08-check-can-fail` | accepting a checker PASS that has never demonstrated it can reject an invalid or absent input | observe a nonzero PostToolUse result from the same normalized checker invocation | [POINTS.md#c08-check-can-fail](POINTS.md#c08-check-can-fail) |
| `C09-checker-excludes-self` | count or trust a grep-shaped process match without excluding the observer identity | run a process listing filtered by the shell or checker PID before trusting the match | [POINTS.md#c09-checker-excludes-self](POINTS.md#c09-checker-excludes-self) |
| `D01` | fan out work with nothing probed first | probe the ground first with a read or a search, so the brief describes what is there | [POINTS.md#d01](POINTS.md#d01) |
| `P01` | adopt a plan built on nothing read | read something first, so the plan describes this repository and not a remembered one | unsolved — [POINTS.md#p01](POINTS.md#p01) |
| `P02` | adopt a plan built on a guessed reading of the request | ask one question about the ambiguity before the plan is fixed | unsolved — [POINTS.md#p02](POINTS.md#p02) |
| `T01` | declare the run finished without ever asking the tree whether it is | run `git status` at least once this session | [POINTS.md#t01](POINTS.md#t01) |
| `T02` | end the run treating a push report as a landing | fetch or `git ls-remote` the ref after pushing | [POINTS.md#t02](POINTS.md#t02) |
| `U01` | launch a nested worker | run `python3 tools/probe_child_capability.py --writable-home --response-transport --result-write` | [POINTS.md#u01](POINTS.md#u01) |
| `U02` | re-launch a nested-worker target | run `python3 tools/probe_child_capability.py --target TARGET --after-failure --require-change` | [POINTS.md#u02](POINTS.md#u02) |
| `U03` | use a PID in a signal operation | run `ps`, `pgrep`, or an equivalent observer-namespace process listing | [POINTS.md#u03](POINTS.md#u03) |
| `U06` | send a mutating request to an external service | run an authenticated read canary such as `curl ... -H 'Authorization: ...'` | [POINTS.md#u06](POINTS.md#u06) |
| `U08` | create a signed git commit | run a signer canary such as `printf test \| gpg --clearsign` | [POINTS.md#u08](POINTS.md#u08) |
| `U09` | switch or check out a git ref | know the ref exists: `git rev-parse --verify REF`, or have created it yourself with `git checkout -b/-B REF` or `git branch REF` | [POINTS.md#u09](POINTS.md#u09) |
| `U10` | traverse structured JSON data | look at the structure first: `jq 'keys'`, `jq 'type'`, `jq -e 'has(...)'`, or any jq structure assertion on the same file | [POINTS.md#u10](POINTS.md#u10) |
| `U12` | apply a patch | run `rg`/`grep` for the patch context and read the target immediately before applying | [POINTS.md#u12](POINTS.md#u12) |
| `U13` | apply a generated patch | run `git apply --check PATCH` first | [POINTS.md#u13](POINTS.md#u13) |
| `U19` | perform an in-place text rewrite | look at the text you are about to rewrite: `rg`/`grep` for the pattern, or `cmp`/checksum the file | [POINTS.md#u19](POINTS.md#u19) |
| `U20` | make a destructive behavior-changing mutation | run an independent behavior observer such as the relevant test or probe first | [POINTS.md#u20](POINTS.md#u20) |
| `U24` | publish or release an artifact after runtime testing | run the suite with warnings promoted to errors on a supported runtime | [POINTS.md#u24](POINTS.md#u24) |
| `U25` | run a scanner as an acceptance check | run its prefix-distractor regression test first | [POINTS.md#u25](POINTS.md#u25) |

<!-- END GENERATED: clause-routes -->

## The four shapes

A benefit compounds through the same four positions a harm cascades through. They locate; they
do not define. The one test defines.

| shape | position | a benefit here |
|---|---|---|
| **built upon** | before the run | a pinned baseline every later comparison inherits |
| **governing** | above the run | a default that makes the right call the cheap one |
| **repeated** | across the run | a check that runs itself on every pass |
| **terminal** | at the end | a done-bar that is a command, so it evaluates itself |

## Counterfeits

Three things pass as constructions without being one; all three fail the one test.

**The added ritual.** If the fate is the same performed or skipped, a cost was added to one side
and nothing was repriced. "Always run `git status` before pushing" is this; the hooks' repricing
of the push itself is not.

**The mandate.** "Never force-push" removes a fate instead of repricing it, and prohibitions get
suspended the first time the work needs the other fate. `--force-with-lease` is the repricing:
the fate is still there, it just costs a lease a stale ref cannot produce.

**The setup that needs its own upkeep.** A hook nobody installs on a fresh clone, a config in a
file that gets regenerated. If the construction itself needs maintenance, its maintenance cost
was moved, not removed.

## Where the detail lives

- **[POINTS.md](POINTS.md)** — the twenty-four moments the clauses name, one authored entry
  each: what is denied, what the discharge buys, and what to build so the discharge is never
  needed again — or, for the two unsolved points, what is known and what is still missing. Open
  this when a deny names it.
- **[ACTS.md](ACTS.md)** — the seven coarser acts: the decisions that set what the rest of the
  run inherits, whether or not a clause fires.
- **[vocabulary.json](vocabulary.json)** — the definition sentence and the four shapes, vendored
  from the development repository's register with the commit and blob shas they were taken from.
- **`keel/clauses.json`** — the clause table itself: fingerprints, guards, deny reasons,
  fixtures, and each row's `construction` anchor into POINTS.md.

## Limits

- The pages advise; only the hooks deny. A construction here can be ignored, and it can be
  unhelpful; it carries no admission machinery, because a deny's false positive costs every turn
  of every session and a page's costs the moment it is read. The test fence refuses the ten
  capitalised RFC 2119 tokens across these pages, so they cannot acquire a mandate's voice
  without going red.
- Nothing here establishes outcome efficacy. The dispatcher's denial is replay-verified; what a
  live agent does after a denial, and whether these constructions help, is unmeasured.
- The shapes are one list against a large body of prior art, and incomplete.
