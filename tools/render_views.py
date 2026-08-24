#!/usr/bin/env python3
"""One generator, every rendered view of the clause facts.

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
TABLE_MARKER = "clause-routes"

# Every table view: (file, link prefix that makes POINTS.md anchors resolve from that file's place).
TABLE_VIEWS = (
    (REPO / "plugin" / "SKILL.md", ""),
    (REPO / "README.md", "plugin/"),
)

README = REPO / "README.md"


def render_clause_count(rows: list[dict], marker: str) -> list[str]:
    """Render prose whose cardinal is owned by the loaded clause table."""
    count = len(rows)
    if marker == "stop-ledger-read":
        missing = [row["id"] for row in rows if not row.get("discharged_by")]
        if missing:
            raise SystemExit(
                "the Stop summary says every clause has a discharge demand, but these do not: "
                + ", ".join(missing)
            )
        return [
            "",
            "**discharge**; at `Stop` anything still open blocks. That is the whole model — every",
            f"one of the {count} clause demands is read at Stop by one mechanism",
            "([`keel/ledger.py`](plugin/keel/ledger.py) states this where the mechanism is defined).",
            "",
        ]
    if marker == "package-clause-count":
        return [
            "",
            "- **the dispatcher** (`keel/`) and the shipped clause table (`keel/clauses.json`,",
            f"  {count} admitted clauses), the POSIX shim (`hooks/dispatch.sh`), and hook manifests for both",
            "  supported hosts. Every fingerprint is an exact predicate over command, tool, or path identity",
            "  — no clause infers intent from prose. The hook fails open: if the dispatcher cannot run, it",
            "  stays silent rather than blocking the host.",
            "",
        ]
    if marker == "shipped-clause-count":
        return [
            "",
            f"The dispatcher loads `plugin/keel/clauses.json` — {count} admitted clauses, every one carrying",
            "positive and negative fixtures checked at load. The table below is a generated view of that",
            "file, byte-compared against it by the test fence on every push, so it cannot quietly lag the",
            "artifact the dispatcher loads. Each row's construction column anchors the clause's positive",
            "half in [`plugin/POINTS.md`](plugin/POINTS.md).",
            "",
        ]
    raise AssertionError(marker)


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


def _region(text: str, path: Path, marker: str) -> tuple[int, int, list[str]]:
    """Line index just after BEGIN, line index of the matching END, and the file's lines.

    A MATCHED PAIR, not the last of each. The loop here used to rebind `begin` and `end` on every
    hit and never stop, so with two BEGIN markers in a file the region silently became the LAST
    BEGIN to the LAST END -- which is not a region either marker delimits. Everything between the
    first BEGIN and the last one would then be left untouched by `--write` and unexamined by
    `--check`: a stale table sitting inside what reads, to anyone looking at the page, like
    generated territory. The generator's whole job is that a view cannot quietly lag its source,
    so "quietly" is the word it cannot afford anywhere, least of all in the function that decides
    what it is allowed to look at.

    A second BEGIN is an error rather than a silent choice, because there is no reading of two
    openers that is obviously right, and guessing one is how the last-wins behaviour arrived.
    """
    lines = text.split("\n")
    begin = end = None
    for index, line in enumerate(lines):
        if line.startswith(f"<!-- BEGIN GENERATED: {marker}"):
            if begin is not None:
                raise SystemExit(
                    f"{path}: a second {marker} BEGIN marker at line {index + 1} -- one view, "
                    f"one region, and which of the two this one closes is not a guess to make")
            begin = index
        elif line.startswith(f"<!-- END GENERATED: {marker}") and end is None:
            end = index
    if begin is None or end is None or end <= begin:
        raise SystemExit(f"{path}: no {marker} marker region -- the view has lost its home")
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
    renderings = [
        (path, TABLE_MARKER, ["", *render_table(rows, prefix), ""])
        for path, prefix in TABLE_VIEWS
    ]
    renderings.extend(
        (README, marker, render_clause_count(rows, marker))
        for marker in ("stop-ledger-read", "package-clause-count", "shipped-clause-count")
    )
    for path, marker, fresh in renderings:
        start, stop, lines = _region(path.read_text(encoding="utf-8"), path, marker)
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
