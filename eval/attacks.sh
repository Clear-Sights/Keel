#!/usr/bin/env bash
# Each function re-plants one break an audit found and exits 0 only if the defence now holds.
# A cell in eval/attacks.jsonl names one of these; tests/test_attacks.py re-runs every cell.
set -u
REPO=$(cd "$(dirname "$0")/.." && pwd)
copy() { W=$(mktemp -d); cp -r "$REPO/plugin" "$REPO/proofs" "$REPO/tools" "$W"/; echo "$W"; }
gate_red() { ! (cd "$1" && python3 tools/check_coq.py >/dev/null 2>&1); }

coq_comments_only() {  # 901 lines of Coq replaced by the side markers alone must be red
  W=$(copy); { echo 'Require Import List.'; grep -o '^  (\* SIDE [^*]*\*)' "$W/proofs/Clauses.v"; } > "$W/proofs/Clauses.v.new"
  printf '(* PARAMETERS: *)\nRequire Import List.\n' > "$W/proofs/Coverings.v"; mv "$W/proofs/Clauses.v.new" "$W/proofs/Clauses.v"; gate_red "$W"; }
coq_section_hypothesis() {  # a Hypothesis inside the Section is not an axiom to Print Assumptions
  W=$(copy); python3 - "$W/proofs/Coverings.v" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); t = p.read_text()
inj = "\n  Hypothesis world_is_convenient : False.\n  Theorem every_covering_is_immune : forall P : Covering, mention_immune P.\n  Proof. intros P c H. destruct world_is_convenient. Qed.\n\n"
t = t.replace("End Coverings.", inj + "End Coverings.", 1)
p.write_text(t.replace("Print Assumptions textual_never_immune.", "Print Assumptions every_covering_is_immune.\nPrint Assumptions textual_never_immune."))
PY
  gate_red "$W"; }
coq_axiom_behind_attribute() {  # a global Axiom used by a #[local] Theorem the old regex never saw
  W=$(copy); printf '\nAxiom cheat2 : False.\n#[local] Theorem hidden_bad2 : forall P:Prop, P.\nProof. destruct cheat2. Qed.\n' >> "$W/proofs/Coverings.v"; gate_red "$W"; }
coq_admitted() {  # an Admitted result
  W=$(copy); python3 - "$W/proofs/Coverings.v" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); t = p.read_text(); i = t.index("Qed.", t.index("Theorem textual_never_immune")); p.write_text(t[:i] + "Admitted." + t[i+4:])
PY
  gate_red "$W"; }
composed_side_unmeasured_is_live() {  # an unmeasured branch of an any_of occasion is NOT-EVALUABLE, not False
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
from keel import clauses
u20 = next(c for c in clauses.load_default() if c.id == "U20")
ev = {"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "x"}, "keel_effect": {"files_removed": [], "head_reset": None}}
raise SystemExit(0 if clauses._predicate(u20.fingerprint, ev) is None else 1)
PY
}
creation_is_a_change() {  # a created file is files_changed in both observers
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
import subprocess, tempfile, pathlib
from keel import effects
assert effects._walk_delta({}, {"new.txt": (1, 2)})[0] == ["new.txt"]
d = tempfile.mkdtemp(); g = lambda *a: subprocess.run(["git", "-C", d, *a], capture_output=True, text=True, check=True).stdout.strip()
g("init", "-q"); pathlib.Path(d, "a").write_text("a"); g("add", "a"); before = g("write-tree")
pathlib.Path(d, "b").write_text("b"); g("add", "b"); after = g("write-tree")
raise SystemExit(0 if effects._tree_delta(d, before, after)[0] == ["b"] else 1)
PY
}
dead_effect_is_gone() {  # an effect no clause names is not in the vocabulary
  cd "$REPO" && PYTHONPATH=plugin python3 -c '
import json; from keel import effects
named = {l.get("effect") for c in json.load(open("plugin/keel/clauses.json")) for s in ("fingerprint","activated_by","discharged_by") if isinstance(c.get(s), dict) for l in [c[s]] + (c[s].get("any_of") or []) + (c[s].get("all_of") or [])}
raise SystemExit(0 if "fetch_head_written" not in effects.EFFECTS and "fetch_head_written" not in named else 1)'; }

"$@"
