"""An ending is an ending, and an unmeasured network is not a landed push.

Two rows of the propagation matrix (K20 30/31, K14 25/30). A clause declaring Stop was enforced
only at the exact event, so a subagent could push and end unreconciled under its own ledger. And
a session whose network counter could not be assigned ended with `remote_landed: True`, the
fail-open direction on the one clause that measures the remote.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import tempfile
import unittest

from tests.plant_support import PLUGIN, record, smoke_replace

SHIM = PLUGIN / "hooks" / "dispatch.sh"


class AnEndingIsAnEnding(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="keel-endings-")
        self.env = dict(os.environ, KEEL_STATE_DIR=str(pathlib.Path(self.tmp) / "state"),
                        CLAUDE_PLUGIN_ROOT=str(PLUGIN))

    def _hook(self, **payload) -> dict:
        payload.setdefault("session_id", "endings"); payload.setdefault("cwd", self.tmp)
        proc = subprocess.run(["bash", str(SHIM)], input=json.dumps(payload), capture_output=True,
                              text=True, env=self.env, timeout=60)
        return json.loads(proc.stdout) if proc.stdout.strip() else {}

    def test_a_subagent_ending_is_reconciled_under_its_own_ledger(self) -> None:
        out = self._hook(hook_event_name="SubagentStop", agent_id="sub")
        self.assertEqual(out.get("decision"), "block", "a subagent ended with standing obligations and was let go")
        self.assertIn("T01", out.get("reason", ""))
        # Its own guard, under its own key, clears it -- the main thread's ledger is untouched.
        path = str(pathlib.Path(self.tmp, "state", "observed.json"))
        self._hook(hook_event_name="PreToolUse", tool_name="Read", agent_id="sub", tool_input={"file_path": path})
        self._hook(hook_event_name="PostToolUse", tool_name="Read", agent_id="sub", tool_input={"file_path": path}, keel_effect=record(observed_read=True))
        self.assertNotIn("T01", self._hook(hook_event_name="SubagentStop", agent_id="sub").get("reason", ""))
        self.assertIn("T01", self._hook(hook_event_name="Stop").get("reason", ""), "the main thread's ledger was paid by a subagent's read")

    def test_an_unmeasured_network_asks_the_remote_instead_of_assuming(self) -> None:
        self.assertEqual(subprocess.run(["bash", str(PLUGIN.parent / "eval" / "attacks.sh"), "unmeasured_network_asks_the_remote"],
                                        cwd=PLUGIN.parent, capture_output=True).returncode, 0)

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red
        smoke_replace(
            self, PLUGIN / "keel" / "dispatch.py",
            b'        if cl.event not in ("Stop", "SubagentStop") or event_name not in ("Stop", "SubagentStop"):\n',
            b'        if True:\n',
            "tests.test_endings.AnEndingIsAnEnding.test_a_subagent_ending_is_reconciled_under_its_own_ledger",
            "was let go",
        )


if __name__ == "__main__":
    unittest.main()
