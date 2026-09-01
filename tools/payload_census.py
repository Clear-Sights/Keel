#!/usr/bin/env python3
"""What does this host actually put in `tool_response`? Answered from captured shapes.

    python3 tools/payload_census.py [--shapes PATH]

Exit 0 the census is decidable and printed / 1 a key that looks like an exit status IS present
(the finding that would delete C08's waiver) / 2 NOT-EVALUABLE.

THE REFUSAL IS THE POINT. This tool exists because C08 -- the one clause of 24 that does not
enforce -- is parked on a measurement of 71 payloads in a database that no longer holds any,
and nothing in Keel could reproduce it. An instrument that answered "no exit status found"
over an empty corpus would recreate that exact failure with a fresh date on it, and the answer
would be indistinguishable from the real one. So a census over zero payloads is NOT-EVALUABLE,
never a verdict, and the denominator is printed on the same line as every claim.

Absence of a key is only evidence when something was actually read.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

# Names an exit status could plausibly arrive under. Deliberately BROAD: this list decides what
# gets LOOKED AT, never what is true, and a census that only looked for the spelling it already
# expected would confirm the belief it was built to test.
STATUS_SHAPED = ("exit", "code", "status", "returncode", "rc", "signal")


def load(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue  # a truncated final line is not a payload; it is also not a verdict
    return rows


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shapes", default=None,
                        help="path to payload_shapes.jsonl (default: Keel's state dir)")
    args = parser.parse_args(argv[1:])

    if args.shapes:
        path = pathlib.Path(args.shapes)
    else:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "plugin"))
        from keel.ledger import state_dir
        from keel.recorder import SHAPES_FILE
        path = state_dir() / SHAPES_FILE

    rows = load(path)
    post = [r for r in rows if r.get("hook_event") == "PostToolUse"]
    print(f"CENSUS shapes_file={path} rows={len(rows)} post_tool_use={len(post)}")

    if not post:
        print("CENSUS=NOT-EVALUABLE no PostToolUse shapes captured -- absence of a key is not "
              "evidence when nothing was read. Enable KEEL_RECORD_SHAPES in a session with the "
              "plugin installed, exercise both a succeeding and a FAILING command, and re-run.",
              file=sys.stderr)
        return 2

    keys = collections.Counter()
    truthy = collections.Counter()
    for row in post:
        for name, shape in (row.get("keys") or {}).items():
            keys[name] += 1
            if shape.get("truthy"):
                truthy[name] += 1

    print(f"CENSUS key frequency over {len(post)} PostToolUse payloads:")
    for name, count in keys.most_common():
        print(f"   {count:5}/{len(post)}  truthy={truthy[name]:<5} {name}")

    suspects = sorted(n for n in keys if any(s in n.lower() for s in STATUS_SHAPED))
    if not suspects:
        print(f"CENSUS=PASS no status-shaped key in {len(post)} payloads "
              f"(looked for: {', '.join(STATUS_SHAPED)})")
        return 0

    print(f"CENSUS=FINDING status-shaped key(s) present: {', '.join(suspects)}")
    for name in suspects:
        # Present on EVERY payload means it is not a status -- a field that cannot distinguish
        # a failing run from a passing one discharges C08 on both, which is the false-discharge
        # direction: the guard removed while the act proceeds.
        always = keys[name] == len(post)
        print(f"   {name}: present {keys[name]}/{len(post)}, truthy {truthy[name]} -- "
              + ("present on every payload, so it does not by itself separate pass from fail; "
                 "check its VALUE before believing it" if always
                 else "present on only some, which is what a status looks like"))
    print("CENSUS: C08's waiver says 'if the host ships an exit status, delete the waiver "
          "instead' -- decide it against this table, not against this sentence.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
