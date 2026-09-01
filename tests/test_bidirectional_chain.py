"""The obligation chain, driven end to end through the REAL hook -- both directions, composing.

WHAT THIS PINS, and why it was worth a file of its own: every other cell here evaluates a
predicate, or a clause, or the ledger. None of them drives the whole relation. The property the
table exists to provide is not "A01's guard matches `git status`" -- it is:

    BACKWARD   attempt an act whose predecessor is not on record  -> the act is REFUSED
    FORWARD    the obligation that refusal incurred is still owed -> the ENDING is refused
    COMPOSING  discharging one link surfaces what remains, and no entry point skips a
               predecessor; when the last link closes, the ending is clean

CHAINING IS NOT A MECHANISM HERE, and that is the design rather than a shortfall. There is no
chain object, no ordering table, no transitive closure computed anywhere. Obligations accumulate
in ONE ledger and every one of them must clear, so a chain of any length is what you get from
composing pairwise links without limiting them (Coverings.v, Theorem 9 `chain_composes`).

A STATIC READING OF THE TABLE CANNOT SEE THIS, and one such reading reported the opposite. A graph
built by asking "does clause X's guard signature equal clause Y's occasion signature" found ZERO
composed chains and concluded the chain model was unimplemented. That was a defect in the reading:
composition does not happen by two coverings being syntactically the same act, it happens through
the shared ledger. Hence this test drives the hook instead of inspecting the table -- the only
reading that can be right about a runtime property.

Measured by this sequence, which is exactly what the cells below assert:

    git push, nothing on record  -> deny            (backward)
    Stop                          -> block, 3 owed  (forward)
    git status                    -> allowed; discharges A01 AND T01 with one act
    Stop                          -> 1 remaining: T02
    git push                      -> ALLOWED
    git fetch origin              -> discharges T02
    Stop                          -> {} clean
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import tempfile
import unittest

from tests.plant_support import PLUGIN, smoke_replace

SHIM = PLUGIN / "hooks" / "dispatch.sh"
SESSION = "chaintest"


class TheChainComposesThroughTheRealHook(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="keel-chain-")
        self.env = dict(os.environ)
        self.env["KEEL_STATE_DIR"] = str(pathlib.Path(self.tmp) / "state")
        self.env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN)

    def _hook(self, **payload) -> dict:
        payload.setdefault("session_id", SESSION)
        payload.setdefault("cwd", self.tmp)
        proc = subprocess.run(["bash", str(SHIM)], input=json.dumps(payload),
                              capture_output=True, text=True, env=self.env, timeout=60)
        out = proc.stdout.strip()
        # `{}` IS the allow envelope. Reading an empty-looking body as "still denied" is a
        # misreading this suite has made before; assert on the parsed object, never on emptiness.
        return json.loads(out) if out else {}

    def _bash(self, event: str, command: str) -> dict:
        return self._hook(hook_event_name=event, tool_name="Bash",
                          tool_input={"command": command})

    def test_the_whole_chain_end_to_end(self) -> None:
        deny = self._bash("PreToolUse", "git push")
        self.assertEqual(
            deny.get("hookSpecificOutput", {}).get("permissionDecision"), "deny",
            "BACKWARD: a push with no predecessor on record was not refused")

        blocked = self._hook(hook_event_name="Stop")
        self.assertEqual(blocked.get("decision"), "block",
                         "FORWARD: the obligation the refusal incurred did not reach the ending")
        self.assertIn("A01", blocked.get("reason", ""),
                      "the PreToolUse clause's demand never reached Stop -- the two directions "
                      "are not sharing one ledger")

        self._bash("PreToolUse", "git status")
        self._bash("PostToolUse", "git status")

        after = self._hook(hook_event_name="Stop")
        self.assertEqual(after.get("decision"), "block",
                         "one act cleared every obligation -- the remaining link vanished")
        self.assertNotIn("A01", after.get("reason", ""), "A01 did not discharge")
        self.assertIn("T02", after.get("reason", ""),
                      "COMPOSING: the next link did not surface once its predecessors cleared")

        self.assertEqual(self._bash("PreToolUse", "git push"), {},
                         "the act stayed refused after its predecessor was satisfied")

        self._bash("PostToolUse", "git fetch origin")
        self.assertEqual(self._hook(hook_event_name="Stop"), {},
                         "the ending is still refused with every obligation discharged")

    def test_NON_VACUITY_a_session_that_does_nothing_is_not_silently_clean(self) -> None:
        """If Stop returned {} unconditionally the cell above would still pass its last line."""
        self.assertEqual(self._hook(hook_event_name="Stop").get("decision"), "block",
                         "a fresh session with standing obligations ended clean")

    def test_the_check_can_fail(self) -> None:
        """Disarm the ONE line that carries keyed demands into the terminal decision.

        `open_rows` holds the demands recorded by PreToolUse clauses; `undischarged` holds the
        standing ones. Dropping the first half is exactly the "backward-only" system I wrongly
        reported this already to be, so the plant reproduces that world and the chain must break.
        """
        smoke_replace(
            self, PLUGIN / "keel" / "dispatch.py",
            b"    open_rows = list(open_rows) + undischarged",
            b"    open_rows = undischarged",
            "tests.test_bidirectional_chain.TheChainComposesThroughTheRealHook."
            "test_the_whole_chain_end_to_end",
            "A01",
        )


if __name__ == "__main__":
    unittest.main()
