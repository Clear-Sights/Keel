# Keel Batch 3 spec (evidence and pages), decided by Owner sign-off; built by Builder; audited by Review; signed off by Owner sign-off
Rules: subtraction or tightening only; every fix carries a cell (eval/attacks.sh function + eval/attacks.jsonl row, layer = target,
declare the target in eval/attacks.classes.json) or a unittest plant via tests/plant_support.smoke_replace; every cell/plant is witnessed
RED on the pre-fix tree (git stash, or a copy) before it is trusted green. Never soften a stated number: re-measure it.
Findings: /tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/ledger/gen3-attack/EV-01..EV-10.md

EV-01 recorded effect records make the corpus replay blind to the observer. Fix: eval/replay.py additionally drives ONE authored
  session with `keel_effect` STRIPPED, in a temp git repo it builds, so the live observer must produce the record (pick the simplest
  fires session whose acts are file mutations); release.yml runs the unit suite before the replay. Cell: gut effects.delta to
  constant blind values in a copy -> replay red.
EV-02 README.md:113 "the seven acts" vs ACTS.md 10. Fix the sentence from the MEASURED value; add README.md to tests/test_fence.py
  PAGES so spelled counts are swept there too. Witness: plant "seven" back -> fence red.
EV-03 README 10/15/1 corpus breakdown vs measured 9/16/1. Fix numbers; add a law: every README number carrying a `[^m-<row>]`
  footnote equals MEASURED.tsv's value for that row (parse both; one test). Witness: plant 10 -> red.
EV-04 README:286-287 "Two clauses (U01, U02) name Keel's own probe; the loader refuses the table if that file is not in the bundle".
  Measured: the footnoted command matches U01 and U25; the loader does NOT refuse. Fix the sentence to what holds (which clauses,
  and that the loader does not refuse -- or, if the probe is genuinely required by a guard's probe field, restore the refusal as a
  loader law CLAUSE-PROBE-MISSING with a plant). Decide from the table; state which.
EV-05 tests/test_bypass.py:219 compares `_preserve_list()` to itself. Fix: compare the injected context to the BYTES of
  plugin/keel/compaction.json's `preserve` field. Witness: truncate at delivery in a copy -> red.
EV-06 agent scoping (`_ids`) deletable with the suite green. Add a plant: a subagent's demand must not block the main thread's Stop
  (drive the shim: agent_id sub raises a demand; main Stop must not name it); smoke_replace on `_ids` returning ("sid","").
EV-07 Ledger.demand dedup deletable. Plant: 40 identical demands write one row; smoke_replace the `if d.id in self.open_ids` guard.
EV-08 _artifact_read shape: a doc `{"junk": true}` must not pay; a JSON list must not raise. Cells for both (the list case may
  already hold after the isinstance fix; witness on the old tree ba072ce~1 = f24eac2).
EV-09 CONSTRUCTION_ANCHOR widened to `.*` leaves fence and dispatcher green. Plant: fence must refuse `see POINTS.md#a01 for details`
  and `_construction` must return "" for it; smoke_replace the pattern to `.*` -> red.
EV-10 a dead dispatcher passes the control session. Fix in eval/replay.py: the run is NOT-EVALUABLE (exit 2) unless at least one
  fires session actually produced a deny/block from the live dispatcher (count them; a zero count is never a pass). Cell: gut
  HANDLERS to `return {}` in a copy -> replay exit != 0.
Gates: full suite to scratchpad/suite.log, eval/replay.py, render_views --check, render_coverings --check, check_coq.py, pyflakes,
clean tree; commit as "Batch 3: evidence and pages" with the standard trailers; do not push.
