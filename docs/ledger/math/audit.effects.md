# Audit: marks.effects.tsv (auditor: review, 2026-09-02)
Source of truth: plugin/keel/effects.py, proofs/Coverings.v, README.md. Audited file: marks.effects.audited.tsv.

## 1. Counts
- confirm 205
- amend 46
- reject 15
- total 266 (equal 66 -> 5 rejected as false passes; near 25 -> 4 rejected as not-near; none 128 -> 4 rejected as false removes)

## 2. REMOVE (code implementing no statement and no stated law, not necessary carriage)
- C-EFF-160, effects.py:579-587 -- `held` (full paths, basenames, ancestor prefixes) is built and never read; the matcher at 588-599 iterates `paths`, not `held`. Dead computation, one git ls-tree walk wasted per quiet act.

## 3. ADD (statements in residue.math.tsv that effects.py should implement and does not)
- none. Three residue rows are in fact implemented and were mis-marked `none`, so they leave residue rather than becoming ADDs: M-LAW-064 by C-EFF-091 (effects.py:335-337), M-LAW-071's pre-image sentence by C-EFF-205 (effects.py:736), M-LAW-060's C09 by C-EFF-164 (effects.py:608). Every other residue row is a proven theorem, a proof variable, or a ledger/clause-loader limit that prescribes no measurement (M-LAW-059/062/063/066/073/074/075/076/077, M-COV-*, M-CLS-065).
- Not an ADD but a math-side gap: the NOT-EVALUABLE law (effects.py:21-24, README.md:207-208) governs 23 audited code rows and has no row in math.tsv.

## 4. REPLACE (unique near-matches where the CODE moves; corrected one-line rule)
- C-EFF-074, effects.py:239-243 -- `_ANCESTRY_CAP=64` drops a legitimately deep descendant: walk the ppid chain with a visited set, stopping only on a repeat (cycle) or pid<=1.
- C-EFF-131, effects.py:486 -- `report_null` accepts a bare `null` ungated: `report_null = reads_structured and stripped in ("null", "")`.
- C-EFF-161, effects.py:597-598 -- the directory-prefix arm lets a bare `src` pay a demand keyed on `src/main.py`: drop `path.startswith(t + "/")`, keep exact / suffix / basename.
- C-EFF-213, effects.py:751-752 -- `bool(changed or removed)` turns NOT-EVALUABLE into False: `head_reset = None if changed is None else (ancestor is not None and bool(changed or removed))`.
- C-EFF-084, effects.py:318-323 -- M-LAW-072's third lineage clause is unimplemented: assign a pid also when its process-session leader is in `in_tree`, so a session born during the act (setsid + reparent) is still the session's.

## 5. STATEMENT-FIX (near-matches where the STATEMENT moves and the code is right)
- M-LAW-043 (effects.py:58) -- add the abbreviation floor: "a ref name, or a hex prefix of at least 7 characters of a commit the ref snapshot holds" (C-EFF-038, C-EFF-157).
- M-LAW-043 / M-LAW-044 / M-LAW-052 (effects.py:58,59,67) -- delete "or process" / "left no process": `still` at effects.py:825 tests files and refs only, deliberately and by measurement (effects.py:818-824) (C-EFF-157, C-EFF-162, C-EFF-163, C-EFF-241, C-EFF-243).
- M-LAW-027 (effects.py:40) -- state the non-repository fallback: content is proxied by (size, mtime_ns), so a same-signature rewrite is unobserved and a touch reads as changed (C-EFF-057, 104, 122, 125, 225).
- M-LAW-028 (effects.py:41) -- state that outside a repository "has none" is inferred from size==0 alone (C-EFF-124, C-EFF-126).
- M-LAW-027 (effects.py:40) -- state the fallback's own exclusions: .git, node_modules, __pycache__, there being no .gitignore to honour (C-EFF-058).
- M-LAW-027 (effects.py:40) -- state that a tree over WALK_CAP=20000 entries outside a repository is NOT-EVALUABLE (C-EFF-061).
- M-LAW-035 / M-LAW-036 (effects.py:48,49) -- exclude the observer: "a process of this session other than the hook's own chain", which is alive at snapshot and gone at delta by construction (C-EFF-078).
- M-LAW-048 (effects.py:63) -- state the two limits the code already carries: a segment under 3 characters never counts, and the comparison is literal text so shell-expanded segments are missed (C-EFF-150, C-EFF-152).
- M-LAW-055 (effects.py:70) -- "as written" is not measured: say validated by path identity, JSON shape, and (session_id, worktree root) scope (C-EFF-183, C-EFF-185, C-EFF-186).
- M-LAW-069 (README.md:175-180) -- "listed once per session" omits the retry: a remote that could not be listed is re-tried, never more often than REMOTE_RETRY_S=60s (C-EFF-039, C-EFF-100).
- M-LAW-038 / M-LAW-034 (effects.py:51,47) -- state the session-level three-valued net memory: once None, never False, so an unmeasurable network cannot end as "the push landed" (C-EFF-238).
- M-LAW-033 (effects.py:46) -- state the second, session-end definition: at Stop, `remote_ref_moved` means the remote's head disagrees with the local tracking ref (C-EFF-263).
