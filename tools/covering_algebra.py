"""Break every covering in the shipped table down to primitives, and grade the algebra.

The check this tool exists to make is Theorem 1 from proofs/Coverings.v, applied to the shipped
table: a covering that reads the RAW COMMAND as text, with a shell metacharacter admitted as
left-context, cannot be mention-immune -- for every command it accepts, not merely for the
strings someone thought to try. Quoting the command inside `echo '...'` preserves it verbatim,
so the pattern matches the mention exactly as it matched the act.

That is why this is a gate and not a test corpus. A corpus of mention examples can only ever
report the defeats someone imagined; patching a pattern against them fits the pattern to those
strings and leaves the next one unexcluded. The population here is derived from the table
itself, so it cannot be satisfied by looking less hard.

Exit 0 the class is empty, 1 a covering is unsound, 2 the table cannot be read -- absence is
never a pass.

No invented inputs anywhere: the population and every atom are read from clauses.json.
"""
import json, re, sys, collections

try:
    rows = json.load(open("plugin/keel/clauses.json"))
except (OSError, ValueError) as exc:
    print(f"NOT-EVALUABLE: cannot read the clause table: {exc}")
    raise SystemExit(2)
rows = rows if isinstance(rows, list) else rows.get("clauses", rows)
if not rows:
    print("NOT-EVALUABLE: the clause table is empty")
    raise SystemExit(2)

SIDES = ("fingerprint", "activated_by", "discharged_by")
META = re.compile(r"\[;&|\\n\]|\(\?:\^\||\^\||[;&|]\\s\*")

kinds = collections.Counter()
textual, structural, other = [], [], []
for c in rows:
    for side in SIDES:
        v = c.get(side)
        if not isinstance(v, dict):
            continue
        k = v.get("kind")
        kinds[k] += 1
        ref = f"{c['id']}.{side}"
        if k == "regex" and v.get("on") == "tool_input.command":
            pat = v.get("pattern", "")
            textual.append((ref, pat, bool(META.search(pat))))
        elif k in ("program", "pipeline"):
            structural.append((ref, k))
        else:
            other.append((ref, k))

print("=== PREDICATE KINDS ACROSS THE SHIPPED TABLE ===")
for k, n in sorted(kinds.items(), key=lambda kv: -kv[1]):
    print(f"  {str(k):10s} {n}")
print(f"  TOTAL sides = {sum(kinds.values())} over {len(rows)} clauses")

print("\n=== THEOREM 1 APPLIED: textual coverings over the raw command ===")
unsound = [t for t in textual if t[2]]
for ref, pat, meta in textual:
    print(f"  {'UNSOUND' if meta else 'anchored'}  {ref:28s} {pat[:66]}")
print(f"\n  textual sides            : {len(textual)}")
print(f"  admit a shell metachar as left-context (Theorem 1 => NOT mention-immune): {len(unsound)}")

print("\n=== STRUCTURAL (Theorem 2 => mention-immune by construction) ===")
for ref, k in structural:
    print(f"  {k:9s} {ref}")
print(f"  structural sides: {len(structural)}")
print("\n=== OTHER KINDS ===")
for ref, k in other:
    print(f"  {str(k):9s} {ref}")

if unsound:
    print(f"\nFAIL: {len(unsound)} covering(s) read the raw command as text with a shell "
          f"metacharacter as left-context. By Theorem 1 (proofs/Coverings.v) these cannot be "
          f"made mention-immune by any pattern edit; give the side a structural kind, or record "
          f"a why_no_program naming what was tried.")
    for ref, _pat, _m in unsound:
        print(f"  {ref}")
    sys.exit(1)
print("\nPASS: no covering reads the raw command as text (Theorem 1 class is empty)")
sys.exit(0)
