"""Every break an audit found, re-planted on every push: eval/attacks.jsonl is the regression list.

A cell is (angle, layer, target, expect, reproducer). Two laws, the same two `pollinate` grades in
Clear-Sights/Small-Tools: an angle with a verdict on some targets of a layer and none on the rest
is a dropped cell (absent is not held), and a recorded colour that no longer re-runs is a
regression (green gone red) or drift (red gone green: a break vanished with no fix on record).
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import unittest

EVAL = pathlib.Path(__file__).resolve().parent.parent / "eval"
CELLS = [json.loads(l) for l in (EVAL / "attacks.jsonl").read_text().splitlines() if l.strip()]
CLASSES = json.loads((EVAL / "attacks.classes.json").read_text())


class TheAttackLedgerHolds(unittest.TestCase):
    def test_no_cell_is_dropped(self) -> None:
        self.assertTrue(CELLS, "an empty ledger holds nothing")
        for angle, layer in {(c["angle"], c["layer"]) for c in CELLS}:
            have = {c["target"] for c in CELLS if c["angle"] == angle and c["layer"] == layer}
            self.assertIn(layer, CLASSES, f"{angle}: layer {layer} is not declared")
            self.assertEqual(set(CLASSES[layer]), have, f"{angle}/{layer}: a target has no verdict")

    def test_every_colour_re_runs_as_recorded(self) -> None:
        for c in CELLS:
            if c["expect"] == "none":
                continue
            with self.subTest(angle=c["angle"], target=c["target"]):
                got = "green" if subprocess.run(c["reproducer"], shell=True, cwd=EVAL / c.get("cwd", "."),
                                                capture_output=True, timeout=600).returncode == 0 else "red"
                self.assertEqual(c["expect"], got, f"{c['reproducer']}: recorded {c['expect']}, re-run {got}")


if __name__ == "__main__":
    unittest.main()
