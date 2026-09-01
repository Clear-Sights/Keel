"""Break every covering in the shipped table down to its class, and grade the algebra.

The class of each side is `keel.clauses.classify_side` -- the same function the loader admits
rows by and `tools/render_coverings.py` instantiates the proof by -- so this tool cannot
disagree with either about what a side is. It prints the census and applies Theorem 1 of
`proofs/Coverings.v`: a covering that reads the RAW COMMAND as text cannot be mention-immune,
for every command it accepts, not merely for the strings someone thought to try.

That is why this is a gate and not a test corpus. A corpus of mention examples can only ever
report the defeats someone imagined; the population here is derived from the table itself, so
it cannot be satisfied by looking less hard.

Exit 0 the class is empty, 1 a covering is unsound, 2 the table cannot be read -- absence is
never a pass.
"""
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "plugin"))
from keel import clauses as C  # noqa: E402

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

kinds = collections.Counter()
classes = collections.defaultdict(list)
closures = collections.defaultdict(collections.Counter)
for c in rows:
    for side in SIDES:
        v = c.get(side)
        if not isinstance(v, dict):
            continue
        kinds[v.get("kind")] += 1
        cls = C.classify_side(v)
        classes[cls].append(f"{c['id']}.{side}")
        closures[cls][C.derive_closure(v)] += 1

print("=== PREDICATE KINDS ACROSS THE SHIPPED TABLE ===")
for k, n in sorted(kinds.items(), key=lambda kv: -kv[1]):
    print(f"  {str(k):10s} {n}")
print(f"  TOTAL sides = {sum(kinds.values())} over {len(rows)} clauses")

print("\n=== CLASSES (Coverings.v), derived by keel.clauses.classify_side ===")
for cls in sorted(classes):
    print(f"  {cls:11s} {len(classes[cls]):3d}  closure={dict(closures[cls])}")
    for ref in classes[cls]:
        print(f"      {ref}")

unsound = classes.get("textual", []) + classes.get("unclassified", [])
if unsound:
    print(f"\nFAIL: {len(unsound)} covering(s) read the raw command as text or have no class. By "
          f"Theorem 1 (proofs/Coverings.v) a textual side cannot be made mention-immune by any "
          f"pattern edit; give the side a structural kind. There is no exemption to write.")
    for ref in unsound:
        print(f"  {ref}")
    sys.exit(1)
print("\nPASS: no covering reads the raw command as text (Theorem 1 class is empty)")
sys.exit(0)
