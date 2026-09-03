# MATH-05 CONFIRMED [math/break] tools/render_coverings.py :: side_block ; proofs/Clauses.v (all 72 results)

## claim
render_coverings.py: 'applies those results to the table as shipped -- one block per side of every clause -- so that the theorem is applied to plugin/keel/clauses.json rather than cited over it.' README: 'instantiates the licensed theorems on all 51 sides of the 24 clauses.'

## reproducer
W=/tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/attack/math/Keel
cd $W && python3 - <<'PY'
import re,pathlib,collections
t=pathlib.Path("proofs/Clauses.v").read_text()
b=re.findall(r"^  Theorem [^\n]*\n(?:[^\n]*\n)*?  Proof\.[^\n]*\n", t, re.M)
n=collections.Counter(re.sub(r"Theorem [A-Za-z0-9_']+_(name_agnostic|separates|rejects_false_claims)",r"Theorem THM_\1",x) for x in b)
print("blocks:",len(b),"distinct after erasing the clause id:",len(n))
PY
# mutate A01's guard effect and regenerate
cp proofs/Clauses.v /tmp/C.before
python3 - <<'PY'
import json,pathlib
p=pathlib.Path("plugin/keel/clauses.json"); rows=json.loads(p.read_text())
for c in rows:
  if c["id"]=="A01":
    def s(d):
      if isinstance(d,dict):
        if d.get("kind")=="effect": d["effect"]="pids_gone"
        for k in ("any_of","all_of"):
          for x in d.get(k) or []: s(x)
    s(c["discharged_by"])
p.write_text(json.dumps(rows,indent=2)+"\n")
PY
python3 tools/render_coverings.py --write >/dev/null; diff /tmp/C.before proofs/Clauses.v
# and: fabricate clause ids in every instance name
cp /tmp/C.before proofs/Clauses.v; git checkout plugin/keel/clauses.json 2>/dev/null
python3 -c "import re,pathlib;p=pathlib.Path('proofs/Clauses.v');p.write_text(re.sub(r'\b([A-Z]\d\d[A-Za-z0-9_\']*)_(name_agnostic|separates)\b',r'NOSUCHCLAUSE_\1_\2',p.read_text()))"
rm -f proofs/*.vo proofs/*.glob; python3 tools/check_coq.py; echo EXIT=$?

## observed
blocks: 72 distinct after erasing the clause id: 2

20c20
<   (* effects: observed_read -- what the act did, read from the world, not the command *)
---
>   (* effects: pids_gone -- what the act did, read from the world, not the command *)

COQ=PASS ... Clauses.v: results=72 axioms=0 / EXIT=0

All 72 'instances' are two statements repeated 36 times each, both universally quantified over an ARBITRARY `Delta`, `E : Delta -> Prop`, `d : Delta`. The clause appears only inside the theorem's NAME. Changing A01's guard from `observed_read` ('the operator read Keel's own measurement') to `pids_gone` ('a process died') changes exactly one COMMENT WORD in the proof; the theorem certifying A01's guard is byte-identical. Renaming every instance to a clause id that is not in the table compiles and passes the gate. Also: `grep -c 'rejects_false_claims\|topology_is_name_agnostic' proofs/Clauses.v` returns 0 -- the positive (Thm 6/7) and topology (Thm 4) classes are instantiated on nothing.
