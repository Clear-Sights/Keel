"""A plant that is killed mid-flight must not leave the fault in the working tree.

Every teeth-check in this suite works by mutating a source file, running one test against the
mutated file, and restoring. The restore is registered with `addCleanup` and called again inline,
and a SIGKILL skips both -- so an interrupt or a timeout during the child leaves the planted fault
sitting in the tree, in a file nobody edited.

MEASURED, and it cost a false diagnosis before this file existed. A suite run killed at a
ten-minute timeout left `plugin/keel/ledger.py` without the two lines one plant removes:

    $ git diff plugin/keel/ledger.py
    -        if self.is_licensed(session, agent, demand_id):
    -            return

The next run reported a missing dedup guard, with the comment describing that guard still sitting
above the hole -- which reads exactly like a real defect, in exactly the shape this project hunts.
Only `git diff` told the two apart, and nothing in the suite pointed there.

The repair had to outlive the process that made the mutation, so `smoke_replace` now records a
marker before mutating and clears it after restoring, and `recover_stale_plants` undoes whatever a
marker still describes. This file is what makes that claim checkable: it builds the wreckage a
kill leaves behind and requires the recovery to undo it, refuse it, or stay out of the way --
never to guess.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.plant_support import (PLANT_ACTIVE_ENV, _drop_bytecode, _sha,
                                 recover_stale_plants, smoke_replace,
                                REPO)

ORIGINAL = b"the bytes that were there before the plant\n"
MUTATED = b"the bytes the plant wrote\n"
EDITED = b"bytes someone wrote after the plant died\n"


class AKilledPlantIsUndone(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        # An isolated state directory, never the live `PLANT_STATE`: this test runs inside a real
        # plant when it is the target of one, and recovery pointed at the live directory would
        # undo that plant's own mutation while it was still being measured.
        self.state = Path(tempfile.mkdtemp(prefix="keel-plant-recovery."))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.state, ignore_errors=True))

    def _wreckage(self, current: bytes) -> Path:
        """The exact on-disk state a kill during a plant leaves behind."""
        target = self.state / "target.py"
        backup = self.state / "target.py.backup"
        target.write_bytes(current)
        backup.write_bytes(ORIGINAL)
        (self.state / "plant.json").write_text(json.dumps({
            "path": str(target), "backup": str(backup), "pid": 999999,
            "original": _sha(ORIGINAL), "mutated": _sha(MUTATED)}), encoding="utf-8")
        return target

    def _clear_active(self):
        """Recovery declines while a plant is in flight, which is true whenever this file IS the
        plant's target. Removing the flag is what lets the real path run under measurement."""
        return mock.patch.dict(os.environ, {k: v for k, v in os.environ.items()
                                            if k != PLANT_ACTIVE_ENV}, clear=True)

    def test_TEETH_the_planted_fault_is_undone(self) -> None:
        target = self._wreckage(MUTATED)
        with self._clear_active():
            recovered = recover_stale_plants(state=self.state)
        self.assertEqual(ORIGINAL, target.read_bytes(),
                         "a killed plant left this fault in the tree and it was not undone")
        self.assertEqual([str(target)], recovered)
        self.assertEqual([], sorted(self.state.glob("*.json")),
                         "the marker outlived the repair, so the next run repairs a clean file")

    def test_TEETH_a_file_edited_since_the_kill_is_refused_not_clobbered(self) -> None:
        """The backup is older than the edit; writing it back would destroy work silently."""
        target = self._wreckage(EDITED)
        with self._clear_active(), self.assertRaises(RuntimeError) as caught:
            recover_stale_plants(state=self.state)
        self.assertEqual(EDITED, target.read_bytes())
        self.assertIn("edited since", str(caught.exception))
        self.assertIn(str(target), str(caught.exception))

    def test_a_restore_that_already_ran_leaves_only_a_marker_to_clear(self) -> None:
        target = self._wreckage(ORIGINAL)
        with self._clear_active():
            recovered = recover_stale_plants(state=self.state)
        self.assertEqual([], recovered, "nothing was mutated, so nothing was repaired")
        self.assertEqual(ORIGINAL, target.read_bytes())
        self.assertEqual([], sorted(self.state.glob("*.json")))

    def test_a_plant_still_in_flight_is_never_recovered(self) -> None:
        """Without this, recovery would undo the mutation a plant is currently measuring, and
        every teeth-check in this suite would go green for the wrong reason."""
        target = self._wreckage(MUTATED)
        with mock.patch.dict(os.environ, {PLANT_ACTIVE_ENV: "plant.json"}):
            self.assertEqual([], recover_stale_plants(state=self.state))
        self.assertEqual(MUTATED, target.read_bytes())

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red
        """Take the restore out of the recovery and the check above must name it."""
        smoke_replace(
            self, REPO / "tests" / "plant_support.py",
            b"        target.write_bytes(backup.read_bytes())\n",
            b"        pass  # restore removed by the plant\n",
            "tests.test_plant_recovery.AKilledPlantIsUndone."
            "test_TEETH_the_planted_fault_is_undone",
            "was not undone")


if __name__ == "__main__":
    unittest.main()


class AnEqualLengthPlantIsNotSwallowedByBytecode(unittest.TestCase):
    """A plant that swaps equal-length bytes must reach the interpreter that runs it.

    MEASURED, and it cost two misdiagnosed suite failures before it was understood. CPython treats
    a `.pyc` as current when the source's mtime and size both match what the cache recorded, and
    mtime is stored to the SECOND. Swapping `60` for `10` changes neither, so a plant landing in
    the same second as the last compile is invisible: the next interpreter loads stale bytecode
    and runs the unmutated code.

    Both directions are wrong and the quiet one is worse. Forward, the child misses the fault and
    the target stays green, which `smoke_replace` reports as an inert plant -- a real defect it
    would be pointing at the wrong place. Backward, the RESTORE is the colliding write, and a
    later process reads the mutant long after the file on disk is correct; that is how this was
    found, as a failure naming a value no file contained.

    This is the resident case for `_drop_bytecode`. Without it the symptom is intermittent and
    lands on whichever test imported the module, never on the plant that caused it.
    """

    def test_a_same_length_mutation_is_seen_by_a_fresh_interpreter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            module = Path(directory) / "planted_module.py"
            module.write_text("VALUE = 60\n", encoding="utf-8")
            read_it = ["python3", "-c", "import planted_module; print(planted_module.VALUE)"]

            first = subprocess.run(read_it, cwd=directory, capture_output=True, text=True)
            self.assertEqual("60", first.stdout.strip(), first.stderr)
            self.assertTrue((Path(directory) / "__pycache__").is_dir(),
                            "no bytecode was cached, so this test cannot observe the collision")

            # Same length, and within the same second as the compile above -- the collision.
            module.write_text("VALUE = 10\n", encoding="utf-8")
            _drop_bytecode(module)
            after = subprocess.run(read_it, cwd=directory, capture_output=True, text=True)
            self.assertEqual(
                "10", after.stdout.strip(),
                "an equal-length plant did not reach a fresh interpreter, so every plant in this "
                "suite that swaps a digit can report a green target while the fault is present")
