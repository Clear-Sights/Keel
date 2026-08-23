#!/usr/bin/env python3
"""One generator, every tabular view of the clause facts.

`plugin/keel/clauses.json` is the single authoritative home of the clause facts -- it is
the artifact the dispatcher loads. Every tabular appearance of those facts anywhere in this
repository is a region this script renders between markers, and CI byte-compares the committed
regions against a fresh rendering. A generated view that silently rots (the shipped SKILL.md
once listed seven clauses that no longer existed and missed eight that did) is a red build by
construction, not a thing reviewers must catch.

    python3 tools/render_views.py --check   # exit 1 naming any view that drifted (CI, fence)
    python3 tools/render_views.py --write   # rewrite the regions in place

Standard library only. The script reads the JSON directly rather than importing the package:
a rendering tool that cannot run is a rendering tool whose views rot exactly like hand-edits.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CLAUSES = REPO / "plugin" / "keel" / "clauses.json"
MARKER = "clause-routes"

# Every view: (file, link prefix that makes POINTS.md anchors resolve from that file's place).
VIEWS = (
    (REPO / "plugin" / "SKILL.md", ""),
    (REPO / "README.md", "plugin/"),
)


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def render_table(rows: list[dict], prefix: str) -> list[str]:
    lines = [
        "| ID | Costly fate | Guard | Construction |",
        "| --- | --- | --- | --- |",
    ]
    for row in sorted(rows, key=lambda r: r["id"]):
        anchor = row.get("construction")
        if anchor:
            construction = f"[{anchor}]({prefix}{anchor})"
        else:
            slot = f"POINTS.md#{row['id'].lower()}"
            construction = f"unsolved — [{slot}]({prefix}{slot})"
        lines.append(
            f"| `{row['id']}` | {_cell(row['costly'])} | {_cell(row['guard'])} "
            f"| {construction} |"
        )
    return lines


def _region(text: str, path: Path) -> tuple[int, int, list[str]]:
    """Line index just after BEGIN, line index of END, and the file's lines."""
    lines = text.split("\n")
    begin = end = None
    for index, line in enumerate(lines):
        if line.startswith(f"<!-- BEGIN GENERATED: {MARKER}"):
            begin = index
        elif line.startswith(f"<!-- END GENERATED: {MARKER}"):
            end = index
    if begin is None or end is None or end <= begin:
        raise SystemExit(f"{path}: no {MARKER} marker region -- the view has lost its home")
    return begin + 1, end, lines


def main(argv: list[str]) -> int:
    if argv[1:] not in (["--check"], ["--write"]):
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        print("usage: render_views.py --check | --write", file=sys.stderr)
        return 2
    write = argv[1] == "--write"
    rows = json.loads(CLAUSES.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise SystemExit(f"{CLAUSES}: not a non-empty list -- nothing to render is a failure")
    drifted = []
    for path, prefix in VIEWS:
        fresh = ["", *render_table(rows, prefix), ""]
        start, stop, lines = _region(path.read_text(encoding="utf-8"), path)
        if lines[start:stop] == fresh:
            continue
        if write:
            lines[start:stop] = fresh
            path.write_text("\n".join(lines), encoding="utf-8")
            print(f"wrote {path.relative_to(REPO)}")
        else:
            drifted.append(str(path.relative_to(REPO)))
    if drifted:
        print("GENERATED VIEW DRIFT -- the committed rendering no longer matches "
              f"{CLAUSES.relative_to(REPO)}: {', '.join(drifted)}. "
              "Run: python3 tools/render_views.py --write", file=sys.stderr)
        return 1
    if not write:
        print(f"views match {CLAUSES.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
