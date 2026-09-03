# MATH-10 CONFIRMED [math/break] proofs/Clauses.v (Variables scan, mention) ; proofs/Coverings.v :: Hypothesis scan_mention_single, textual_never_immune, structural_immune ; plugin/keel/effects.py :: _SEGMENT_SPLIT

## claim
Coverings.v: 'the obligation is discharged ONCE, structurally, for every covering simultaneously'; 'each theorem is explicitly RELATIVE to a scanner with the stated properties'; Hypothesis scan_mention_single: 'The scanner sees a mention as ONE segment invoking the quoting program.'

## reproducer
W=/tmp/claude-0/-home-user/6821575c-1522-5dd1-b244-faf3d1a3848f/scratchpad/attack/math/Keel
cd $W && grep -n 'scan\|mention' proofs/Clauses.v
grep -o 'exact ([a-z_]*' proofs/Clauses.v | sort -u
cd plugin && python3 -c "
from keel.effects import _SEGMENT_SPLIT
for c in [\"echo 'rm -rf /; git push'\", 'echo \"a | b\"', \"echo 'c'\"]:
    print(repr(c),'->',_SEGMENT_SPLIT.split(c))"

## observed
11:  Variable scan : Text -> list (Segment string).
12:  Variable mention : Text -> Text.
(no other occurrence)
exact (effect_is_name_agnostic
exact (effect_separates_same_segments

"echo 'rm -rf /; git push'" -> ["echo 'rm -rf /", " git push'"]
'echo "a | b"' -> ['echo "a ', ' b"']
"echo 'c'" -> ["echo 'c'"]

Two things. (1) Clauses.v DECLARES `scan` and `mention` and never uses them: only 2 of Coverings.v's 16 results are ever instantiated on the table, and both are the tautologies of MATH-07. Theorems 1, 2, 3, 4, 5, 6, 7, 8a, 9 and every corollary -- the entire 'structural covering' theory that the file's opening paragraph presents as the discharged obligation -- are instantiated on ZERO of the 51 shipped sides. (2) The one segment splitter in the plugin, `_SEGMENT_SPLIT = re.compile(r'\|\||&&|[|;\n]')`, splits INSIDE quotes: `echo 'rm -rf /; git push'` becomes two segments. So it falsifies `Hypothesis scan_mention_single`, the hypothesis every immunity theorem is explicitly relative to. The relativised guarantee has no witness in this repository, and its only candidate refutes it.
