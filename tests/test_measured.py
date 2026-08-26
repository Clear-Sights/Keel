"""Every row of MEASURED.tsv, re-measured by the command the row itself carries.

WHY THIS EXISTS. `MEASURED.tsv` is this repository's table of measured facts, and every row ships
the command that produced its value -- which is the right design and was never run. Nothing in the
suite, the tools or CI executed a single one. A table whose entire subject is measurement, holding
numbers nobody re-measured.

It had already gone stale. `act-count` read 7 while `plugin/ACTS.md` carried ten headings and the
row's own one-line command printed 10. That drift landed in the same change that raised the acts
from seven to ten, alongside the one in SKILL.md's prose -- and the prose one was caught, by the
join in `test_fence.py`, because a page is prose and a TSV is not. This is the same defect in the
file least able to afford it.

The row's command IS the join. Nothing here restates a value or knows what any row means: it runs
what the row says and compares to what the row claims, so a fact that moves is red on the next run
whether or not anyone remembered this file existed.

WHAT IS NOT CHECKED, said plainly: that a row's COMMAND actually measures what its SUBJECT column
describes. That is a claim about English and is left to the reader. What cannot happen any more is
a row whose own command disagrees with its own value.
"""
from __future__ import annotations

import csv
import os
import subprocess
import unittest

from tests.plant_support import REPO, smoke_replace

MEASURED = REPO / "MEASURED.tsv"
HEADER = ("KEY", "VALUE", "DENOMINATOR", "COMMAND", "SUBJECT")

# A row's command is repository tooling, not a network call: the slowest today is the corpus
# replay, which is seconds. This bounds a row that hangs so the suite reports a stuck measurement
# instead of stalling the run; on exhaustion the row fails, naming itself, and is never skipped.
ROW_TIMEOUT_SECONDS = 300


def rows() -> list[tuple[str, ...]]:
    with MEASURED.open(encoding="utf-8") as handle:
        found = [tuple(r) for r in csv.reader(handle, delimiter="\t") if r]
    assert found and tuple(found[0]) == HEADER, f"MEASURED.tsv header changed: {found[:1]}"
    return found[1:]


class EveryMeasuredRowStillMeasuresThat(unittest.TestCase):
    def test_the_check_has_a_subject(self) -> None:
        """No rows means every assertion below is vacuously true."""
        self.assertGreater(len(rows()), 3, "MEASURED.tsv carries almost nothing; nothing was checked")

    def test_every_row_is_well_formed(self) -> None:
        for row in rows():
            self.assertEqual(len(HEADER), len(row), f"{row[0] if row else row}: wrong field count")
            self.assertTrue(row[3].strip(), f"{row[0]}: no command, so the value rests on nothing")
            self.assertTrue(row[4].strip(), f"{row[0]}: no subject, so nobody can tell what it counts")

    def test_every_row_recomputes_to_the_value_it_claims(self) -> None:
        wrong = []
        for key, value, _denominator, command, _subject in rows():
            done = subprocess.run(
                command, shell=True, cwd=REPO, capture_output=True, text=True,
                timeout=ROW_TIMEOUT_SECONDS, env={**os.environ, "PYTHONPATH": "plugin"})
            printed = (done.stdout or done.stderr).strip().splitlines()
            got = printed[-1].strip() if printed else "(no output)"
            if got != value.strip():
                wrong.append(f"{key}: claims {value!r}, its own command printed {got!r}")
        self.assertEqual([], sorted(wrong),
                         "a measured row disagrees with the command that measured it")

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red
        """Move a value away from what its command prints, and this must go red naming the row.

        Planted on `act-count` deliberately: that is the row that was actually wrong, reading 7
        against ten headings, and it stayed wrong because nothing here ran its command.
        """
        smoke_replace(
            self, MEASURED, b"act-count\t10\t", b"act-count\t9\t",
            "tests.test_measured.EveryMeasuredRowStillMeasuresThat."
            "test_every_row_recomputes_to_the_value_it_claims",
            "act-count: claims '9', its own command printed '10'",
        )


if __name__ == "__main__":
    unittest.main()
