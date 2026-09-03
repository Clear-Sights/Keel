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

look_survives_sibling_spawn() {  # a process born beside the act does not make a look loud
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
import pathlib, subprocess, tempfile
from keel import effects
d = tempfile.mkdtemp(); repo = pathlib.Path(d, "repo"); repo.mkdir(); state = pathlib.Path(d, "state")
g = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=True)
g("init", "-q", "-b", "main"); g("config", "user.email", "k@x"); g("config", "user.name", "k")
pathlib.Path(repo, "a.txt").write_text("one\n"); g("add", "a.txt"); g("commit", "-q", "-m", "a")
effects.snapshot(state, "s", "", str(repo))
sibling = subprocess.Popen(["sleep", "30"])  # born in this session tree during the act, not by it
out = subprocess.run("git status", shell=True, cwd=repo, capture_output=True, text=True)
d = effects.delta(state, "s", "", {"cwd": str(repo), "tool_input": {"command": "git status"}, "tool_response": {"stdout": out.stdout}})
sibling.kill()
raise SystemExit(0 if d["report_ref"] else 1)
PY
}

write_surface_is_observed() {  # the host's write tools are matched by the hooks and fire the effect occasions
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
import json
from keel import clauses
hooks = json.load(open("plugin/hooks/hooks.json"))["hooks"]
ok = all(any(t in (h.get("matcher") or "").split("|") for h in hooks[m]) for t in ("Write", "Edit", "MultiEdit", "NotebookEdit") for m in ("PreToolUse", "PostToolUse"))
u19 = next(c for c in clauses.load_default() if c.id == "U19")
ev = {"hook_event_name": "PostToolUse", "tool_name": "Edit", "tool_input": {"file_path": "x"}, "keel_effect": {"files_changed": ["x"]}}
raise SystemExit(0 if ok and clauses._predicate(u19.fingerprint, ev) is True else 1)
PY
}

unmeasured_network_asks_the_remote() {  # a session whose network could not be measured does not end as "landed"
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
import json, pathlib, subprocess, tempfile
from keel import effects
d = tempfile.mkdtemp(); repo = pathlib.Path(d, "repo"); repo.mkdir()
g = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=True)
g("init", "-q", "-b", "main"); g("remote", "add", "origin", str(pathlib.Path(d, "no-such-remote")))
state = pathlib.Path(d, "state"); slot = effects._slot(state, "s", ""); slot.mkdir(parents=True)
(slot / "session.json").write_text(json.dumps({"spawns": 0, "net_out": None}))
unknown = effects.at_stop(state, "s", "", str(repo))
(slot / "session.json").write_text(json.dumps({"spawns": 0, "net_out": False}))
measured = effects.at_stop(state, "s", "", str(repo))
raise SystemExit(0 if unknown["remote_landed"] is None and measured["remote_landed"] is True else 1)
PY
}
subagent_ending_is_reconciled() {  # a clause declaring Stop is reconciled at SubagentStop under that agent's ledger
  cd "$REPO" && W=$(mktemp -d) && out=$(printf '%s' '{"hook_event_name":"SubagentStop","session_id":"s","agent_id":"sub","cwd":"'"$W"'"}' | KEEL_STATE_DIR="$W/state" CLAUDE_PLUGIN_ROOT="$REPO/plugin" bash plugin/hooks/dispatch.sh) && printf '%s' "$out" | grep -q '"decision": *"block"' && printf '%s' "$out" | grep -q 'T01'; }

look_is_not_a_rewrite_under_a_stat_cache() {  # 80 rewrite-then-look cycles: a look never reads as a rewrite (was 5/80 with a copied index)
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
import os, pathlib, subprocess, tempfile
from keel import effects
def git(repo, *a): return subprocess.run(["git", "-C", repo, *a], check=True, capture_output=True, text=True).stdout
def obs(state, repo, cmd):
    effects.snapshot(state, "s", "", repo); done = subprocess.run(cmd, shell=True, cwd=repo, capture_output=True, text=True)
    return effects.delta(state, "s", "", {"tool_input": {"command": cmd}, "tool_response": {"stdout": done.stdout}})
miss = 0
for i in range(80):
    tmp = tempfile.mkdtemp(); repo = os.path.join(tmp, "repo"); state = pathlib.Path(tmp, "state"); os.mkdir(repo)
    git(repo, "init", "-q", "-b", "main"); git(repo, "config", "user.email", "k@x"); git(repo, "config", "user.name", "k")
    p = pathlib.Path(repo, "a.txt"); p.write_text("one\n"); git(repo, "add", "-A"); git(repo, "commit", "-qm", "base")
    obs(state, repo, "ls"); p.write_text("two\n")
    d = obs(state, repo, "git diff")
    miss += d["files_changed"] != [] or not d["report_paths"]
print("misses", miss, "of 80"); raise SystemExit(1 if miss else 0)
PY
}
backdated_commit_is_a_creation() {  # K11: the switch/create split must not read the committer date the act sets
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
import os, pathlib, subprocess, tempfile
from keel import effects
tmp = tempfile.mkdtemp(); repo = os.path.join(tmp, "repo"); state = pathlib.Path(tmp, "state"); os.mkdir(repo)
git = lambda *a: subprocess.run(["git", "-C", repo, *a], check=True, capture_output=True, text=True)
git("init", "-q", "-b", "main"); git("config", "user.email", "k@x"); git("config", "user.name", "k")
pathlib.Path(repo, "a.txt").write_text("one\n"); git("add", "-A"); git("commit", "-qm", "base")
effects.snapshot(state, "s", "", repo)
subprocess.run("printf two > a.txt && git add -A && GIT_COMMITTER_DATE=2000-01-01T00:00:00 git commit -qm back", shell=True, cwd=repo)
d = effects.delta(state, "s", "", {"tool_input": {"command": "git commit"}, "tool_response": {"stdout": ""}})
raise SystemExit(0 if d["head_moved"] and not d["head_switched"] else 1)
PY
}

emptied_is_removed() {  # K17: content loss by truncation is files_removed in both observers
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
from keel import effects
w_before = {"a.txt": (4, 1), "b.txt": (0, 1)}; w_after = {"a.txt": (0, 2), "b.txt": (0, 1)}
changed, removed = effects._walk_delta(w_before, w_after)
ok = changed == [] and removed == ["a.txt"]
import os, pathlib, subprocess, tempfile
tmp = tempfile.mkdtemp(); repo = os.path.join(tmp, "repo"); state = pathlib.Path(tmp, "state"); os.mkdir(repo)
git = lambda *a: subprocess.run(["git", "-C", repo, *a], check=True, capture_output=True, text=True)
git("init", "-q", "-b", "main"); git("config", "user.email", "k@x"); git("config", "user.name", "k")
pathlib.Path(repo, "a.txt").write_text("one\n"); git("add", "-A"); git("commit", "-qm", "base")
effects.snapshot(state, "s", "", repo); subprocess.run(": > a.txt", shell=True, cwd=repo)
d = effects.delta(state, "s", "", {"tool_input": {"command": ": > a.txt"}, "tool_response": {"stdout": ""}})
raise SystemExit(0 if ok and d["files_removed"] == ["a.txt"] and d["files_changed"] == [] else 1)
PY
}

constant_payload_pays_no_keyed_demand() {  # AG-10: a look at another target pays nothing for a rewrite
  cd "$REPO" && PYTHONPATH=plugin python3 -m unittest -q tests.test_keyed_effects.ALookPaysOnlyWhatItNames.test_TEETH_a_read_of_another_file_pays_nothing tests.test_keyed_effects.ALookPaysOnlyWhatItNames.test_TEETH_a_listing_that_names_another_path_pays_nothing >/dev/null 2>&1; }

stop_hook_active_rearms() {  # DL-04: the Stop after our own block is evaluated again, not waved through
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
import sys, tempfile, pathlib; sys.path.insert(0, ".")
from tests.plant_support import record, hook_decision
st = pathlib.Path(tempfile.mkdtemp())
hook_decision({"session_id":"s","cwd":"/tmp","hook_event_name":"PostToolUse","tool_name":"Bash","tool_input":{"command":"rm f"},"tool_response":{"stdout":""},"keel_effect":record(files_removed=["f"])}, st)
out = hook_decision({"session_id":"s","cwd":"/tmp","hook_event_name":"Stop","stop_hook_active":True}, st)
raise SystemExit(0 if out.get("decision") == "block" and "U20" in out.get("reason","") else 1)
PY
}
keyed_pre_image() {  # DL-06: two PreToolUse before either PostToolUse: each act reads its OWN pre-image
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
import sys, tempfile, pathlib, subprocess, os; sys.path.insert(0, ".")
from keel import effects
w = tempfile.mkdtemp(); st = pathlib.Path(tempfile.mkdtemp())
subprocess.run("git init -q && git config user.email a@b && git config user.name a && echo 1>f1 && echo 2>f2 && git add -A && git commit -qm i", shell=True, cwd=w, check=True)
effects.snapshot(st, "s", "", w, act="tA"); effects.snapshot(st, "s", "", w, act="tB")
os.remove(w + "/f1")
a = effects.delta(st, "s", "", {"tool_use_id":"tA","tool_input":{"command":"echo"},"tool_response":{"stdout":""}})
b = effects.delta(st, "s", "", {"tool_use_id":"tB","tool_input":{"command":"rm f1"},"tool_response":{"stdout":""}})
raise SystemExit(0 if a.get("not_evaluable") is None and b.get("not_evaluable") is None and b["files_removed"] == ["f1"] else 1)
PY
}
empty_envelope_is_loud() {  # DL-08: a closed stdin is an unreadable event, with a message and a fault row
  cd "$REPO" && st=$(mktemp -d) && out=$(printf '' | KEEL_STATE_DIR="$st" CLAUDE_PLUGIN_ROOT="$REPO/plugin" bash plugin/hooks/dispatch.sh) \
    && printf '%s' "$out" | grep -q systemMessage && grep -q '"fault"' "$st/decisions.jsonl"
}
unknown_event_pays_nothing() {  # DL-13: an event no handler knows discharges no demand
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
import sys, tempfile, pathlib; sys.path.insert(0, ".")
from tests.plant_support import hook_decision
from keel.ledger import Ledger
st = pathlib.Path(tempfile.mkdtemp())
hook_decision({"session_id":"e","cwd":"/tmp","hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"git push"}}, st)
before = len(Ledger(st).open_ids("e", ""))
out = hook_decision({"session_id":"e","cwd":"/tmp","hook_event_name":"TotallyMadeUpEvent","tool_name":"Glob","tool_input":{"pattern":"*"}}, st)
raise SystemExit(0 if before == 3 == len(Ledger(st).open_ids("e", "")) and "systemMessage" in out else 1)
PY
}
foreign_datum_pays_nothing() {  # DL-11: a Read of a measurement another session took of another tree pays no guard
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
import sys, tempfile, pathlib, subprocess; sys.path.insert(0, ".")
from tests.plant_support import hook_decision
from keel.ledger import Ledger
st = pathlib.Path(tempfile.mkdtemp()); wa, wb = tempfile.mkdtemp(), tempfile.mkdtemp()
for w in (wa, wb):
    subprocess.run("git init -q && git config user.email a@b && git config user.name a && echo 1>f && git add -A && git commit -qm i", shell=True, cwd=w, check=True)
hook_decision({"session_id":"A","cwd":wa,"hook_event_name":"SessionStart"}, st)
hook_decision({"session_id":"A","cwd":wa,"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"git push --force"}}, st)
hook_decision({"session_id":"B","cwd":wb,"hook_event_name":"SessionStart"}, st)  # rewrites the one file for B's tree
hook_decision({"session_id":"A","cwd":wa,"hook_event_name":"PostToolUse","tool_name":"Read","tool_input":{"file_path":str(st/"observed.json")},"tool_response":{}}, st)
raise SystemExit(0 if len(Ledger(st).open_ids("A", "")) == 3 else 1)
PY
}
errored_read_pays_nothing() {  # EFF-06: a Read the host answered with an error returned no datum
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
import json, tempfile, pathlib
from keel import effects
st = pathlib.Path(tempfile.mkdtemp()); (st/"observed.json").write_text(json.dumps({"root":None,"session":"s","head":"abc"}))
ev = {"session_id":"s","hook_event_name":"PostToolUse","tool_name":"Read","tool_input":{"file_path":str(st/"observed.json")},"tool_response":{"error":"exceeds maximum"}}
raise SystemExit(0 if effects.read_delta(st, ev)["observed_read"] is False else 1)
PY
}
killed_hook_is_named() {  # DL-09: a hook the host killed mid-evaluation is named at the ending, with a fault row
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
import sys, tempfile, pathlib, json, time; sys.path.insert(0, ".")
from tests.plant_support import hook_decision
st = pathlib.Path(tempfile.mkdtemp()); (st/"pending").mkdir()
(st/"pending"/"s-999999.json").write_text(json.dumps({"event":"PostToolUse","tool":"Bash","act":"rm -f x","t":time.time()}))
out = hook_decision({"session_id":"s","cwd":"/tmp","hook_event_name":"Stop"}, st)
raise SystemExit(0 if out.get("decision") == "block" and "never completed" in out.get("reason","") and "hook_killed" in (st/"decisions.jsonl").read_text() else 1)
PY
}
ledger_compacts() {  # DL-10: a session start drops the rows of sessions that owe nothing; the dirty one stays
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
import sys, tempfile, pathlib, json; sys.path.insert(0, ".")
from tests.plant_support import hook_decision
st = pathlib.Path(tempfile.mkdtemp())
with (st/"obligations.jsonl").open("w") as f:
    for i in range(20000):
        f.write(json.dumps({"kind":"demand","id":f"x{i}","session":"other","agent":"","clause_id":"ZZ","subject":"s","reason":"r","prev":"","hash":"h"})+"\n")
        f.write(json.dumps({"kind":"discharge","id":f"x{i}","session":"other","agent":"","how":"g","prev":"","hash":"g"})+"\n")
    f.write(json.dumps({"kind":"demand","id":"open1","session":"dirty","agent":"","clause_id":"ZZ","subject":"s","reason":"r","prev":"","hash":"q"})+"\n")
hook_decision({"session_id":"L","cwd":"/tmp","hook_event_name":"SessionStart"}, st)
rows = [json.loads(l) for l in (st/"obligations.jsonl").read_text().splitlines()]
raise SystemExit(0 if len(rows) < 100 and any(r["session"] == "dirty" for r in rows) else 1)
PY
}
reflog_move_is_observed() {  # EFF-09: commit-then-reset inside one act leaves HEAD where it was; the reflog says what happened
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
import tempfile, pathlib, subprocess
from keel import effects
w = tempfile.mkdtemp(); st = pathlib.Path(tempfile.mkdtemp())
subprocess.run("git init -q -b main && git config user.email a@b && git config user.name a && echo 1>a && git add -A && git commit -qm i", shell=True, cwd=w, check=True)
effects.snapshot(st, "s", "", w)
subprocess.run("printf two > a && git add -A && git commit -qm x && git reset -q --hard HEAD~1", shell=True, cwd=w, check=True)
d = effects.delta(st, "s", "", {"tool_input":{"command":"x"},"tool_response":{"stdout":""}})
effects.snapshot(st, "s", "", w)
subprocess.run("git checkout -q -b tmpb && git checkout -q main", shell=True, cwd=w, check=True)
e = effects.delta(st, "s", "", {"tool_input":{"command":"y"},"tool_response":{"stdout":""}})
raise SystemExit(0 if d["head_reset"] is True and e["head_switched"] is True else 1)
PY
}
local_push_asks_the_remote() {  # EFF-11: a push over a local path opens no connection; the ending still asks the remote
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
import tempfile, pathlib, subprocess
from keel import effects
base = tempfile.mkdtemp(); st = pathlib.Path(tempfile.mkdtemp())
subprocess.run(f"git init -q --bare origin.git && git clone -q origin.git w && git clone -q origin.git other && cd w && git config user.email a@b && git config user.name a && echo 1>a && git add -A && git commit -qm i && git push -q origin HEAD:main", shell=True, cwd=base, check=True)
w = base + "/w"
effects.snapshot(st, "s", "", w)
subprocess.run("git push -q origin HEAD:refs/heads/side", shell=True, cwd=w, check=True)
d = effects.delta(st, "s", "", {"tool_input":{"command":"git push"},"tool_response":{"stdout":""}})
subprocess.run("git config user.email a@b && git config user.name a && git pull -q origin main && echo 2>b && git add -A && git commit -qm foreign && git push -q origin HEAD:main", shell=True, cwd=base + "/other", check=True)
s = effects.at_stop(st, "s", "", w)
raise SystemExit(0 if d["remote_ref_moved"] and s["remote_landed"] is False else 1)
PY
}
act_is_not_its_own_canary() {  # EFF-12: a quiet connection raises U06; it cannot pay the demand it just raised
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
import sys, tempfile, pathlib; sys.path.insert(0, ".")
from tests.plant_support import record, hook_decision
from keel.ledger import Ledger
st = pathlib.Path(tempfile.mkdtemp())
hook_decision({"session_id":"q","cwd":"/tmp","hook_event_name":"PostToolUse","tool_name":"Bash","tool_input":{"command":"python3 -c 'import socket'"},"tool_response":{"stdout":""},"keel_effect":record(net_out=True, net_read=True)}, st)
raise SystemExit(0 if "U06" in {r["clause_id"] for r in Ledger(st).open_demands("q", "")} else 1)
PY
}
mention_is_one_segment() {  # MATH-10: the observer's scanner sees a quoted mention as one segment, as the theory assumes
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
from keel import effects
one = effects._segments("echo 'ps aux | grep x'") == ["echo 'ps aux | grep x'"]
mention = effects._lists_itself("ps aux | grep x\n", "echo 'ps aux | grep x'") is False
real = effects._lists_itself("root 1 sh -c ps aux | grep x\nroot 2 grep x\n", "ps aux | grep x") is True
raise SystemExit(0 if one and mention and real else 1)
PY
}
non_acts_pass_open_demands() {  # DL-14/P-23: a refused push does not refuse the question that would resolve it
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
import sys, tempfile, pathlib; sys.path.insert(0, ".")
from tests.plant_support import hook_decision
st = pathlib.Path(tempfile.mkdtemp())
hook_decision({"session_id":"n","cwd":"/tmp","hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"git push"}}, st)
ask = hook_decision({"session_id":"n","cwd":"/tmp","hook_event_name":"PreToolUse","tool_name":"AskUserQuestion","tool_input":{"questions":[]}}, st)
task = hook_decision({"session_id":"n","cwd":"/tmp","hook_event_name":"PreToolUse","tool_name":"Task","tool_input":{"prompt":"x"}}, st)
raise SystemExit(0 if ask == {} and task.get("hookSpecificOutput", {}).get("permissionDecision") == "deny" else 1)
PY
}
unkeyable_subject_is_not_a_pass() {  # L2: an occasion whose extractor finds no operand still fires, session-wide
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
import sys, tempfile, pathlib, dataclasses; sys.path.insert(0, ".")
from keel import clauses as C, dispatch
from keel.ledger import Ledger
st = pathlib.Path(tempfile.mkdtemp())
u10 = next(c for c in C.load_default() if c.id == "U10")
row = dataclasses.replace(u10, fingerprint={"kind": "regex", "on": "tool_name", "pattern": "^Bash$"}, event="PreToolUse", tools=["Bash"])
out = dispatch.pre_tool_use([row], Ledger(st), {"session_id":"k","cwd":"/tmp","hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"true"}})
raise SystemExit(0 if "U10" in str(out) else 1)
PY
}
coq_identity_shapes() {  # MATH-04: iff_refl, an identity lambda pair, and a bare conj of hypotheses are refused as results
  for shape in 'apply iff_refl' 'exact (conj H1 H2)' 'split; [ exact (fun h => h) | exact (fun h => h) ]'; do
    W=$(copy); python3 - "$W/proofs/Coverings.v" "$shape" <<'PY'
import pathlib, sys
p, shape = pathlib.Path(sys.argv[1]), sys.argv[2]; t = p.read_text()
stmt = "forall (P : Covering) c, P c -> ~ P c -> P c /\\ ~ P c" if "conj" in shape else "forall (P : Covering) c, P c <-> P c"
intro = "intros P c H1 H2." if "conj" in shape else "intros P c."
t = t.replace("End Coverings.", f"\n  Theorem vac : {stmt}.\n  Proof. {intro} {shape}. Qed.\n\nEnd Coverings.")
p.write_text(t.replace("Print Assumptions textual_never_immune.", "Print Assumptions vac.\nPrint Assumptions textual_never_immune."))
PY
    gate_red "$W" || return 1
  done; }
coq_out_of_order_trace() {  # MATH-06: [L; X] is a violation and backward rejects it (the earlier definitions accepted it)
  W=$(copy); cat > "$W/proofs/Break_order.v" <<'V'
Require Import List Bool. Import ListNotations. Require Import Coverings.
Definition isX (e:bool) : Prop := e = true.
Definition isL (e:bool) : Prop := e = false.
Theorem rejected : ~ backward bool isX isL [false; true].
Proof. exact (out_of_order_is_rejected bool isX isL false true eq_refl eq_refl). Qed.
V
  (cd "$W/proofs" && coqc -q -Q . "" Coverings.v >/dev/null 2>&1 && coqc -q -Q . "" Break_order.v >/dev/null 2>&1); }
# The replay cells need the corpus and the replay script as well as the package, because what
# they gut is the observer the replay is supposed to be exercising.
copy_eval() { W=$(mktemp -d); cp -r "$REPO/plugin" "$REPO/proofs" "$REPO/tools" "$REPO/eval" "$W"/; echo "$W"; }

replay_sees_a_blind_observer() {  # EV-01: gut every effect reading to a constant and the replay must go red
  W=$(copy_eval); python3 - "$W/plugin/keel/effects.py" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); t = p.read_text()
blind = {
  "def report_effects(stdout: Any, command: Any) -> dict[str, bool]:":
    '\n    return {n: False for n in ("report_null", "report_pass", "report_clean", "report_fail",'
    '\n            "report_nowarn", "report_signature", "report_structured", "report_self")}',
  "                  listed_self: bool = False) -> dict[str, Any]:":
    '\n    return {n: False for n in ("report_ref", "report_paths", "report_pids", "report_listing")}',
  "def delta(state: pathlib.Path, session: str, agent: str, event: dict[str, Any]) -> dict[str, Any]:":
    '\n    return {name: None for name in EFFECTS}',
}
for head, body in blind.items():
    assert t.count(head) == 1, head
    t = t.replace(head, head + body, 1)
p.write_text(t)
PY
  ! (cd "$W" && python3 eval/replay.py >/dev/null 2>&1); }

replay_refuses_a_dead_dispatcher() {  # EV-10: every handler returning {} is NOT-EVALUABLE (exit 2), never a pass
  W=$(copy_eval); python3 - "$W/plugin/keel/dispatch.py" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); t = p.read_text()
head = 'HANDLERS = {\n    "PreToolUse": pre_tool_use,'
assert t.count(head) == 1
t = t.replace(head, 'def _nothing(table, ledger, event):\n    return {}\n\n\nHANDLERS = {\n    "PreToolUse": _nothing,', 1)
for row in ('"UserPromptSubmit": user_prompt_submit,', '"PreCompact": pre_compact,',
            '"PostToolUse": post_tool_use,', '"Stop": reconcile,', '"SubagentStop": reconcile,',
            '"SessionStart": session_start,', '"SubagentStart": session_start,'):
    assert t.count(row) == 1, row
    t = t.replace(row, row.split(":")[0] + ": _nothing,", 1)
p.write_text(t)
PY
  (cd "$W" && python3 eval/replay.py >/dev/null 2>&1); [ $? -eq 2 ]; }

artifact_read_refuses_a_document_that_is_not_a_measurement() {  # EV-08: a right-named file holding junk pays nothing
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
import json, pathlib, tempfile
from keel import effects
st = pathlib.Path(tempfile.mkdtemp())
(st / "observed.json").write_text(json.dumps({"junk": True}))
(st / "remote.json").write_text(json.dumps({"junk": True}))
read = lambda n: effects.read_delta(st, {"tool_name": "Read", "tool_input": {"file_path": str(st / n)}})
raise SystemExit(0 if not read("observed.json")["observed_read"] and not read("remote.json")["remote_read"] else 1)
PY
}

artifact_read_survives_a_malformed_artifact() {  # EV-08: a JSON list where a document belongs is False, never a raise
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
import pathlib, tempfile
from keel import effects
st = pathlib.Path(tempfile.mkdtemp())
for name in ("observed.json", "remote.json"):
    (st / name).write_text("[]")
for name in ("observed.json", "remote.json"):
    rec = effects.read_delta(st, {"tool_name": "Read", "tool_input": {"file_path": str(st / name)}})
    assert rec["observed_read"] is False and rec["remote_read"] is False, (name, rec)
raise SystemExit(0)
PY
}

net_read_counts_a_closed_port() {  # K13, the stated limit on U06's guard, re-measured rather than assumed
  cd "$REPO" && PYTHONPATH=plugin python3 - <<'PY'
import pathlib, subprocess, tempfile
from keel import effects
d = pathlib.Path(tempfile.mkdtemp()); repo = d / "repo"; repo.mkdir(); state = d / "state"
g = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)
g("init", "-q", "-b", "main"); g("config", "user.email", "k@x"); g("config", "user.name", "k")
(repo / "a.txt").write_text("one\n"); g("add", "-A"); g("commit", "-q", "-m", "a")
effects.snapshot(state, "s", "", str(repo))
cmd = "exec 3<>/dev/tcp/127.0.0.1/9"   # nothing listens there; the handshake is refused
out = subprocess.run(["bash", "-c", cmd], cwd=repo, capture_output=True, text=True)
rec = effects.delta(state, "s", "", {"cwd": str(repo), "tool_input": {"command": cmd},
                                     "tool_response": {"stdout": out.stdout}})
# The limit README states: the counter cannot say what was reached, so a refused handshake is
# still a network read. NOT-EVALUABLE (None) is the honest answer when the counter moved
# unassignably and is not a counter-example; what would be is False -- a claim that the
# connection was measured and was not a read.
raise SystemExit(0 if rec["net_read"] is not False else 1)
PY
}
"$@"
