"""The host's own write tools are inside the observer: a rewrite by Edit raises the same demand as by Bash.

Measured before this cell existed: hooks.json registered PreToolUse for eight tools and PostToolUse
for two, neither list holding Write, Edit, MultiEdit or NotebookEdit, and `_effect_record` observed
only Bash. So every file-mutation clause fired on one surface and was bypassed on the other, and the
propagation matrix read 30 of 31 targets broken under that one angle.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import tempfile
import unittest

from tests.plant_support import PLUGIN, record

SHIM = PLUGIN / "hooks" / "dispatch.sh"


class TheWriteSurfaceIsObserved(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="keel-write-")
        self.env = dict(os.environ, KEEL_STATE_DIR=str(pathlib.Path(self.tmp) / "state"),
                        CLAUDE_PLUGIN_ROOT=str(PLUGIN))

    def _hook(self, **payload) -> dict:
        payload.setdefault("session_id", "writetest"); payload.setdefault("cwd", self.tmp)
        proc = subprocess.run(["bash", str(SHIM)], input=json.dumps(payload), capture_output=True,
                              text=True, env=self.env, timeout=60)
        return json.loads(proc.stdout) if proc.stdout.strip() else {}

    def test_every_write_tool_is_registered_for_both_moments(self) -> None:
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())["hooks"]
        for tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
            for moment in ("PreToolUse", "PostToolUse"):
                self.assertTrue(any(tool in (h.get("matcher") or "").split("|") for h in hooks[moment]),
                                f"{tool} is not matched at {moment}: the surface is unobserved")

    def test_a_rewrite_by_edit_raises_the_rewrite_demand(self) -> None:
        self.assertEqual(self._hook(hook_event_name="PreToolUse", tool_name="Edit",
                                    tool_input={"file_path": "app.py", "old_string": "a", "new_string": "b"}), {})
        self._hook(hook_event_name="PostToolUse", tool_name="Edit",
                   tool_input={"file_path": "app.py", "old_string": "a", "new_string": "b"}, keel_effect=record(files_changed=["app.py"]))
        deny = self._hook(hook_event_name="PreToolUse", tool_name="Bash", tool_input={"command": "echo next"})
        reason = deny.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
        self.assertEqual(deny.get("hookSpecificOutput", {}).get("permissionDecision"), "deny")
        self.assertIn("U19", reason, "a rewrite by the host's Edit tool raised no rewrite demand")

    def test_a_live_edit_is_seen_by_the_observer(self) -> None:
        from keel import effects
        repo = pathlib.Path(self.tmp, "repo"); repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        pathlib.Path(repo, "app.py").write_text("a\n"); state = pathlib.Path(self.tmp, "state")
        effects.snapshot(state, "s", "", str(repo))
        pathlib.Path(repo, "app.py").write_text("b\n")
        d = effects.delta(state, "s", "", {"cwd": str(repo), "tool_name": "Edit",
                                           "tool_input": {"file_path": "app.py", "old_string": "a", "new_string": "b"}})
        self.assertEqual(d["files_changed"], ["app.py"], "the observer did not see a file the host's Edit changed")


if __name__ == "__main__":
    unittest.main()
