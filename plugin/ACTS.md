# The seven acts

The twenty-four points in [POINTS.md](POINTS.md) are exact moments named by the plugin's
admitted clauses. They do not reach everywhere. These seven acts are the coarser index — the moments where a
decision sets what the rest of the run inherits, whether or not a point fires.

The seven act names originate in the development repository's register; these headings are their
single home in the shipped product — the fence checks them against the pinned seven, and nothing
else spells the list. Construction numbers refer to [SKILL.md](SKILL.md).

The question is the same at all seven: **if nobody does anything next time, does the good outcome
still arrive?**

---

## accept_report

**The moment.** A result arrives — a suite verdict, a benchmark number, a scanner's silence, a
subagent's summary — and gets adopted as fact for everything after it.

Points `C03-verify-what-returns`, `C08-check-can-fail` and `U25` cover parts of this: read what
returned, prove the checker can fail,
prove the scanner refuses distractors. What none of them covers is a bare **number** entering the
run with no origin attached.

**Construction (1).** Have the report format carry its own provenance: the command, the input sha, the
host, the runtime. A naked number then has nowhere to enter from, because the shape it enters through
has fields it cannot fill. One assertion of origin converts every future green in the repository from
ambiguous to attributable.

**A record that gets cut is a report too.** A summary, a handoff, a compaction — the next reader
inherits it whole, so the cut decides what survives. Give the cut a preserve list stated in
advance — what has to survive verbatim, failures with their root causes, the done-bar as a check
that can fail — and the provenance fields above complete that list as a report format.

**And run the un-planted control first.** A probe that reports the expected failure without the fault
planted has not reached its predicate — it is reporting something else. The control costs one run and
it is what stops a wrong finding from being reported as a real one.

## choose_spend

**The moment.** Deciding how much to commit — calls, agents, scope, authority, context. No point
fires here; spending is not a command shape.

**Construction (5).** Freeze the bar the result has to clear *before* spending; then start with the
smallest candidate that could clear it, and climb only when it does not. A bar written afterwards
is written to fit what happened.

The tier question is the same act asked about capability instead of quantity, and it takes the
same bar.
Name what the cheap rung has to fail at before the dear one is bought, and make the bar "does the
failure heal", never "is this hard" — hard is a feeling and it inflates, while healing is checkable
at the moment of asking: if this comes back wrong, does a later observation report it, or does the
wrongness become part of what everything after it is built on? The first kind of work rests on the
cheap rung and redoing it costs one more cheap unit; the second is where intelligence earns its
price, because the discount is paid back with interest by everything downstream.

A budget is a record: name, at creation, its warning threshold and what happens at exhaustion. An
exhausted budget that fires a failure report is a construction paying out; one that lapses quietly is the thing this
exists to prevent, because a partial result that looks complete is what ends a run.

**Frugality is the point, not asceticism.** The smallest sufficient amount, then stop — not the
smallest amount.

## delete

**The moment.** Removing something: a file, a rule, a section, a test, a clause, a plan.

Point `A02` covers bulk file deletion, where the loss is bytes. It does not cover the removal of a
**reason**, which is the more expensive case: the artifact goes and the argument for it goes with it,
leaving nothing to correct from.

**Construction (1).** Make the removal form require the ground: what covers this place now, named
specifically, or the argument that the place self-heals. A removal with an empty ground field does
not render, so an unreasoned deletion stops being expressible.

**Conserve rather than erase** — nothing is destroyed until it is replaced. Keep the removed
thing and its reason where it can be re-examined.
Identical reasons across distinct items are the tell that the brief was wrong, not the items — one bad
brief produces twenty identical wrong verdicts in a single pass.

## dispatch_work

**The moment.** Sending a unit to an executor other than yourself.

Point `D01` covers the probe: the brief describes what is there. What it does not cover is whether
the route you are dispatching to exists.

**Construction (4).** The route is a default, so shape the ladder once. Rank the rungs cheap-to-dear by
capability, never by model name: names live in a bindings file the resolver reads, so a rename
cannot silently reroute work while every test spelling the old name stays green. The cheap rung is
the resting state; the bar for leaving it is `choose_spend`'s.

**Triggers fall upward only.** Each unit states its rung; unhealing, cascading, or cross-cutting
lifts it, and nothing lowers it — a one-way rule cannot be argued downward under deadline pressure,
which is exactly when it would be. When no trigger is stated, the unit falls up, because the fate
you can afford to arrive by accident is overspending on one unit, not underspending on an unhealing
one. And the case that hides: bulk verification of work that is about to be trusted has bulk's
shape and unhealing's fate — a wrong item is built upon by work that never re-runs the check — so
it takes the dear rung, not the cheap one.

**Prove the route is reachable before dispatching, and record what you learned.** A tier named in a
config file is a claim a destination exists, not evidence it answers. A dead route escalates one
rung, never straight to the top — the condition that killed the cheapest route is rarely specific
to the unit that found it — and never retries silently. If nothing above is reachable, park the
unit at the top marked blocking: visible beats a result-shaped nothing. Write the dead route down
with its trigger, tier and the observed error, in the bindings file — a recorded deadness is a
claim the next session can re-probe, instead of rediscovering one failure at a time.

**Concurrency is a claim about the tracker.** Reads, defined pieces and design alternatives run in
parallel; wiring, shared-parent integration and writes land in sequence. Model it as a graph and
maximise only the safe part.

## finalize_plan

**The moment.** Fixing a plan for adoption. A plan is followed by default — nobody decides to follow
it — which makes it the highest-leverage thing in a run.

Points `P01` and `P02` cover reading and asking. They are two enforcement rows over one point —
a step adopted on ground never established — and share one construction, written under
[P01](POINTS.md#p01).

**Construction (5).** Make the plan's done-bar a list of calls, each returning nonzero when its claim
does not hold, rather than a list of sentences. Then finishing is evaluable by anyone, including later you, without reconstructing what
was meant.

**A plan fails standing up two ways: wrong, or never landing.** `P01` and `P02` guard the first.
The second: it gets refined without ever landing, because refinement always looks like progress
and the appearance of progress consumes the occasion to notice there is none. The reversal is a push. Steer for complete and sufficient, but
done — not for never finishing, and not for endless churn.

## push

**The moment.** Publishing: a push, a tag, a release, a merge.

Points `A01`, `A03` and `T02` cover this densely — status, lease, landing. What they do not cover is
whether what you published was **derived** or **typed**.

**Construction (1).** Derive the version from the artifact that declares it, never from a hand-typed
workflow input. Once the tag is computed from the tree it is cut from, that path cannot emit a
version the tree does not declare — the guarantee is the door's, so release only through the door.
A hand-typed version is correct exactly as often as somebody checks.

## write_default_rule

**The moment.** Writing something that decides by not being noticed: a default value, a config, a
fallback, a lint rule, a clause, a waiver. No point covers the decision itself — the write can
still fire `U12`, `U13` or `U19` on its way in — and a default steers every later call precisely
because nobody looks at it.

**Construction (4).** Assign the cost so that inaction produces the safe fate,
and add nothing. Same object, both fates still reachable, the prices swapped. Forgetting then
produces the outcome you wanted, so the rule is not defeated by ordinary forgetting.

**One path.** Two branches that do the same thing are two places to be wrong and one place to be
tested. Collapse them, and there is one implementation to cover instead of two.

**A waiver is default-dead or it is nothing.** It carries the condition that excused it and a date;
when it lapses it goes red rather than quiet; renewal is re-argued. Renewed twice means the baseline
was wrong, not the waiver.

**Absence of a rule is a claim too.** Say where you looked and where the rule could still be, so the
gap is falsifiable rather than assumed.
