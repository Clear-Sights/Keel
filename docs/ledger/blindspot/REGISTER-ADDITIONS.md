# Blindspot register — additions from the agent-transcript pass

Corpus: 766 transcripts, 59,765 records, every subagent and workflow run of this session plus the
main thread. Mined mechanically (`mine.py`), then each candidate taken through the register's own
ADDING procedure: fix line written first, set beside every existing fix line in all families,
tool-nouns struck, one discriminating input named, two-fixes-two-entries.

The denominator is stated below, not only the hits: **31 incidents examined, 5 new entries, 3
widenings, 23 incidents cited to entries that already carry them.** An incident that fires an
existing entry is a success of the register, not a gap in it, and is recorded as such.

---

## New entries

Append these within their families. Never renumber.

```
A14 NORMALIZATION MERGES
    a cleanup mapped two distinct inputs onto one
  > assert count in equals count out
```

Two incidents. A repair pass scrubbed damaged text and two differently-damaged keys collapsed onto
one replacement character, dropping the earlier one's value — in the module whose one promise is
that repair is on the record. Separately a key function split on non-alphanumerics, so two distinct
senses of one word keyed identically; the agreement statistic that read those keys never saw a
sense at all, and every mechanism claim resting on it was retracted.

Not A2: A2 is *same spelling taken as same thing*, and here the spellings differ — A2's fix does
not fire on this input. Not A4: defining a winner among duplicates does not help when the transform
is what created the duplicate. Discriminating input: two distinct keys that normalize to one
string; count-in-equals-count-out trips, nothing else does.

```
B34 UNMATCHED RESIDUE UNREPORTED
    a recognizer's misses vanish instead of counting
  > report what it did not match, not only what it did
```

Two incidents. A proof grader recognized `Theorem|Lemma|Corollary`, so a result stated as `Fact`,
`Remark`, `Proposition` or `Example` was silently ungraded while the grader reported full coverage.
A citation checker skipped non-local targets silently and returned the full census regardless of
what it had skipped.

Not B6: counts sum perfectly — everything found is graded, and the found-set is the defect. Not B2:
counting the population independently presupposes knowing what counts as a member, which is the
thing at issue. Nearest is C5 (feed foreign shapes), but C5's fix is an error branch, and a scanner
that errors on every unrecognized line is unusable — the fix here is a positive residue count, a
different fix, so per rule 5 a different entry. Discriminating input: a document holding one
`Proposition` beside one `Theorem`; the grader reports 1/1 and the residue report reports 1.

```
B35 UNDECLARED EXEMPTION
    the code exempts what the rule never mentions
  > enumerate exemptions from the code; each must be declared
```

Two incidents. A second, undocumented spelling of a bypass marker disarmed all 24 clauses while the
page documented only one spelling. Separately a terminal-clause special case silently rerouted
fixture grading for a whole predicate class, a carve-out the law it exempts from does not state.

Not B9: B9 assumes the waiver is *visible* and asks it to name an end; here there is nothing visible
to attach an end to, so B9's fix cannot reach it. B9's fix and this one are two fixes, so two
entries. Discriminating input: a subject carrying the undeclared marker — every clause reports pass
and the declared-exemption census is empty.

```
C11 REPORT BEFORE DECIDE
    the outcome was emitted after the narration about it
  > emit the outcome first; reporting comes after
```

Two incidents. A fail-closed handler wrote its diagnostic before emitting its denial; with the
diagnostic channel unwritable the denial never ran and the process exited in the permitting
direction — fail-open caused by an observability failure. Separately an error *logger* that raised
abandoned every pattern after it, so a later denial never ran and the catch-all recorded a
permissive result.

Not C4: C4 resolves an error *as* a denial, but here the denial was already computed and correct —
it died in the reporting path ordered ahead of it. Discriminating input: a run whose reporting
channel fails while the outcome is already computed.

```
C12 VERDICT WITHOUT ITS SUBJECT
    a failure was counted but never named
  > capture the failing identity in the run that produced it
```

One incident, this session, still unresolved: a suite reported `Ran 267 tests ... FAILED
(failures=1)` and the immediately following run was clean. The failing test was never identified,
because the only run that knew its name was the one discarded by re-running. An intermittent
failure is a real defect; here it is a defect that cannot even be addressed.

Not C1 (the status was not lost — it arrived, as a count). Not C3 (nothing masked anything).
Discriminating input: any verdict reporting a failure count without the failing identities,
followed by a passing re-run.

---

## Widenings

Each re-runs step 1 for every id the entry already carries.

```
B17 PLANT CONTAMINATES DETECTOR
    the checker contains the pattern it hunts, or the target was already red
  > require green before the plant
```
"Red with the fault" is satisfied by a target red *always* — already broken, or carrying an
expected string that went stale when the code moved underneath it. Same fix, so a widening, not a
twin. Re-check of B17's own id: a checker containing its quarry is red before the plant, so
green-before-plant still catches it.

```
B20 PLANT WITHDRAWN
    the test input was edited until it passed, or the mutation changed nothing
  > the mutation must be observed to change the subject
```
Setting an attribute that does not exist succeeds silently: a disarm landed nowhere and the row
read "carries no load" while disarming nothing. Re-check of B20's own id: an edit that touched the
input rather than the subject is caught by the same requirement.

```
D13 UNENUMERATED DESTRUCTION
    removing a set you never listed, or whose members enclose others
  > list first, expand each member to what it contains, act on exactly that list
```
A condemnation pass checked whether a span was *contained by* another condemned span but never
whether it *contained* a live one, so deleting an outer function silently deleted a live nested one
registered elsewhere. Re-check of D13's own id: an unlisted set is still caught by "list first".

---

## Incidents cited to existing entries — the denominator, not only the hits

| incident | entry |
|---|---|
| A suite imported the package from a *different* checkout via a stale editable install; neutering a check in this tree left the run green, so every green figure ever reported was a claim about other bytes | **D3** |
| Worktree agents built and graded at an ancestor commit while the branch was elsewhere; one reported "four pre-existing failures" that were only missing commits | **D3** |
| A derived cache, a stale bytecode file inflating mutation counts, a documented output claiming 2 failures against an actual 5, a page figure never printed | **D4** |
| Two workers killed at ~4.5GB; the pool repopulated and the run wedged unnoticed | **B26** |
| Twenty-one dispatched units each wrote a completion marker and each landed nothing — their sandbox made the repository read-only and every commit failed silently | **D1** |
| A manifest shape the real loader rejects outright; every hook the repository generated had been absent for the plugin's entire life because nothing ever ran the real loader | **D2** |
| Work product written where the consumer does not read it | **D2** |
| A constant relation stated only in prose in a third file naming neither constant | **B7** |
| A loader admitted 17 of 24 and dropped 7; a subtraction produced `open: -2` where a membership check belonged | **B6** |
| An invalid pattern accepted, its refusal code never firing; a rule requiring literal headings that fired on nothing but the document it was ported from | **E1**, **B18** |
| A theorem whose statement unfolds to itself, proved by identity | **B32** |
| A bound with slack (`<= 10`) satisfied equally by "deduplicated" and "never ran"; tests that never ran counted as passed | **B23**, **B2** |
| An obligation discharged by an unrelated earlier act in the same session | **B28** |
| A field built and never read; a check defined and never called | **B14** |
| A hard-coded absolute path that published one machine's layout and made every corpus-backed check quietly not-evaluable elsewhere | **E7** |
| A harness default silently reasserting itself over a standing instruction | **E4** |
| Jobs failing in 3 seconds read as test failures when the cause was an exhausted budget | **E10** |
| Five parallel workers dispatched against one shared monthly pool, all dying at once | **E11** |
| Two writers over two registers, neither naming the other; two spellings of one rule | **F2** |
| Cached results from a prior run presented as current | **F10** |
| "Nothing matched" forced into a block whose message asserted absence | **C2** |
| An act that licenses itself | **D9** |

---

## Applied

**C2** and **B35** are not filed as observations. Both were fixed in this pass:
`gate.claimed_running`'s vocabulary miss now answers NOT-EVALUABLE instead of blocking, and the
undeclared bypass spelling is now declared on the page with a deadline that fails as a check.
