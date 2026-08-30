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
import shlex
import subprocess
import unittest

from tests.plant_support import REPO, smoke_replace

MEASURED = REPO / "MEASURED.tsv"
HEADER = ("KEY", "VALUE", "DENOMINATOR", "DENOMINATOR_COMMAND", "COMMAND", "SUBJECT")

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
            self.assertTrue(row[4].strip(), f"{row[0]}: no command, so the value rests on nothing")
            self.assertTrue(row[5].strip(), f"{row[0]}: no subject, so nobody can tell what it counts")
            # A numeric DENOMINATOR is a measured fact exactly like the VALUE, so it must ship the
            # command that produced it. `-` is the honest spelling for "this row is an absolute
            # count, out of nothing" -- and it is the ONLY spelling that excuses a row from the
            # re-measurement below, so a denominator cannot be asserted and left unchecked.
            if row[2].strip() != "-":
                self.assertRegex(row[2].strip(), r"^\d+$",
                                 f"{row[0]}: a denominator is a number or `-`, nothing else")
                self.assertTrue(row[3].strip() and row[3].strip() != "-",
                                f"{row[0]}: claims denominator {row[2]!r} with no command behind it")
            else:
                self.assertEqual("-", row[3].strip(),
                                 f"{row[0]}: no denominator, so a denominator command measures nothing")

    @staticmethod
    def _measure(command: str) -> tuple[str, int]:
        """Run a row's command; return (its last printed line, its bare exit code).

        The exit code is returned, not discarded. A command that raises after printing -- or that
        fails in a stage of a pipeline before its last stage -- still leaves a plausible-looking
        final line, so comparing only that line reads a crash as a measurement."""
        done = subprocess.run(
            command, shell=True, cwd=REPO, capture_output=True, text=True,
            timeout=ROW_TIMEOUT_SECONDS, env={**os.environ, "PYTHONPATH": "plugin"})
        printed = (done.stdout or done.stderr).strip().splitlines()
        return (printed[-1].strip() if printed else "(no output)"), done.returncode

    def test_every_row_recomputes_to_the_value_it_claims(self) -> None:
        wrong = []
        for key, value, _denominator, _denominator_command, command, _subject in rows():
            got, code = self._measure(command)
            if code != 0:
                wrong.append(f"{key}: its own command exited {code}, so it measured nothing")
            elif got != value.strip():
                wrong.append(f"{key}: claims {value!r}, its own command printed {got!r}")
        self.assertEqual([], sorted(wrong),
                         "a measured row disagrees with the command that measured it")

    def test_every_numeric_denominator_recomputes_to_what_it_claims(self) -> None:
        """The DENOMINATOR column was unpacked and thrown away, so it was decoration: `replay`
        read `25` out of `10` -- the value had been re-measured when the corpus grew and the
        denominator had not, and nothing could see it. Denominators are now re-measured by their
        own command, exactly as values are."""
        wrong, evaluated = [], 0
        for key, _value, denominator, denominator_command, _command, _subject in rows():
            if denominator.strip() == "-":
                continue
            evaluated += 1
            got, code = self._measure(denominator_command)
            if code != 0:
                wrong.append(f"{key}: its denominator command exited {code}")
            elif got != denominator.strip():
                wrong.append(f"{key}: claims denominator {denominator!r}, "
                             f"its own command printed {got!r}")
        self.assertEqual([], sorted(wrong),
                         "a measured row's denominator disagrees with the command behind it")
        self.assertGreater(evaluated, 0,
                           "no row carries a numeric denominator, so this test checked nothing")

    # THE TWO HALVES OF A RATIO MUST COME FROM ONE OBSERVATION. Each row's VALUE and
    # DENOMINATOR are recomputed above by their own command, in their own process. That
    # makes each half true on its own and says nothing about the pair: `23/25` is
    # `fires(glob A) / files(glob B)` and `25/25` is `passed(replay A) / sessions(replay B)`.
    # A corpus that changed between the two, or a replay that is not deterministic, would
    # publish a coherent-looking fraction that no single run ever produced. These rows name
    # the joint measurement that produces both numbers at once.
    JOINT = {
        "derailments": (
            'import glob,json; paths=sorted(glob.glob("eval/corpus/*.jsonl")); '
            'print(sum(json.loads(open(p).readline()).get("expect","fires")=="fires" '
            'for p in paths), len(paths))'),
        "replay": (
            'import re,subprocess; '
            'p=subprocess.run(["python3","eval/replay.py"],capture_output=True,text=True); '
            'm=re.search(r"REPLAY sessions=(\\d+) passed=(\\d+) failed=0",p.stdout); '
            'print(m.group(2), m.group(1)) if p.returncode==0 and m else print("FAIL FAIL")'),
    }

    def test_every_ratio_is_produced_by_a_single_run(self) -> None:
        published = {key: (value.strip(), denominator.strip())
                     for key, value, denominator, *_ in rows()}
        missing = sorted(set(self.JOINT) - set(published))
        self.assertEqual([], missing,
                         f"JOINT names rows MEASURED.tsv no longer carries: {missing}")
        # Every row with a numeric denominator is a ratio, so every one of them needs a
        # joint measurement. A row added without one is the defect, not an omission.
        ratios = sorted(key for key, (_v, d) in published.items() if d != "-")
        self.assertEqual(ratios, sorted(self.JOINT),
                         "a row publishes a ratio with no joint measurement behind it")
        wrong = []
        for key, script in sorted(self.JOINT.items()):
            got, code = self._measure(f"python3 -c {shlex.quote(script)}")
            if code != 0:
                wrong.append(f"{key}: its joint command exited {code}")
                continue
            parts = tuple(got.split())
            if parts != published[key]:
                wrong.append(f"{key}: publishes {published[key][0]}/{published[key][1]}, "
                             f"but one run produced {'/'.join(parts)}")
        self.assertEqual([], wrong,
                         "a published ratio was assembled from two separate observations")

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

    def test_the_denominator_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red
        """Move a denominator away from what its command prints, and this must go red naming it.

        Planted on `replay` deliberately: that is the denominator that was actually wrong,
        reading 10 against a 25-session corpus, and it stayed wrong because nothing ran the
        command behind it."""
        smoke_replace(
            self, MEASURED, b"replay\t25\t25\t", b"replay\t25\t10\t",
            "tests.test_measured.EveryMeasuredRowStillMeasuresThat."
            "test_every_numeric_denominator_recomputes_to_what_it_claims",
            "replay: claims denominator '10', its own command printed '25'",
        )

    def test_the_exit_code_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red
        """Make a row's command print the right answer and then die. The value comparison alone
        cannot see this -- the last printed line is still correct -- so only reading the exit
        code catches it."""
        smoke_replace(
            self, MEASURED,
            b'act-count\t10\t-\t-\tpython3 -c ',
            b'act-count\t10\t-\t-\tpython3 -c \'print(10); raise SystemExit(3)\' # ',
            "tests.test_measured.EveryMeasuredRowStillMeasuresThat."
            "test_every_row_recomputes_to_the_value_it_claims",
            "act-count: its own command exited 3, so it measured nothing",
        )


if __name__ == "__main__":
    unittest.main()
