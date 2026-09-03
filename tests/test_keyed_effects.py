"""A demand keyed on what the act did is paid only by a look that names it.

U12, U13 and U19 fire on `files_changed`, U03 on `pids_gone`. Their subject used to be the
session, so any look at any path paid every rewrite: `ls` printing one held path discharged the
demand a rewrite of another file had raised (AG-10: a constant payload pays a trace-checked
guard, 29 of 30 targets). The subject is now the datum the effect produced -- one demand per
changed path, per gone pid -- and the guard must name it: a Read of that file, a Grep aimed at
it, a quiet act whose output names it, or a Read of Keel's own measurement of the dirty paths.

Every cell drives the SHIPPED hook as a subprocess with recorded effects, never `_predicate`.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest

from tests.plant_support import PLUGIN, REPO, record, smoke_replace

HOOK = PLUGIN / "hooks" / "dispatch.sh"
STATE_PATH = "/home/operator/.claude/keel_state/observed.json"


class ALookPaysOnlyWhatItNames(unittest.TestCase):
    def setUp(self) -> None:
        self.state = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.state, True)
        self.session = "keyed"
        # The session's opening debt: A01/A02/A03 paid by the two artifact reads.
        self._read(STATE_PATH, observed_read=True)
        self._read("/home/operator/.claude/keel_state/remote.json", remote_read=True)

    def _send(self, event: dict) -> dict:
        event = dict(event, session_id=self.session, cwd=self.state)
        env = dict(os.environ, KEEL_STATE_DIR=self.state, HOME=self.state)
        out = subprocess.run(["bash", str(HOOK)], input=json.dumps(event), text=True,
                             capture_output=True, env=env, cwd=str(REPO)).stdout.strip()
        return json.loads(out) if out else {}

    def _read(self, path: str, **eff) -> dict:
        pre = self._send({"hook_event_name": "PreToolUse", "tool_name": "Read",
                          "tool_input": {"file_path": path}})
        self._send({"hook_event_name": "PostToolUse", "tool_name": "Read",
                    "tool_input": {"file_path": path}, "keel_effect": record(**eff)})
        return pre

    def _bash(self, command: str, **eff) -> dict:
        pre = self._send({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                          "tool_input": {"command": command}})
        self._send({"hook_event_name": "PostToolUse", "tool_name": "Bash",
                    "tool_input": {"command": command}, "keel_effect": record(**eff)})
        return pre

    def _next(self) -> str:
        out = self._send({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                          "tool_input": {"command": "echo next"}})
        return out.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")

    def test_the_refusal_is_keyed_on_the_changed_path(self) -> None:
        self._bash("sed -i s/a/b/ config.txt", files_changed=["config.txt"])
        reason = self._next()
        self.assertIn("U19", reason)
        self.assertIn("`config.txt`", reason, "the refusal must name what the look has to name")

    def test_TEETH_a_read_of_another_file_pays_nothing(self) -> None:
        self._bash("sed -i s/a/b/ config.txt", files_changed=["config.txt"])
        self._read("other.txt")
        self.assertIn("U19", self._next(), "a Read of another file paid a rewrite of config.txt")

    def test_TEETH_a_listing_that_names_another_path_pays_nothing(self) -> None:
        self._bash("sed -i s/a/b/ config.txt", files_changed=["config.txt"])
        self._bash("ls", report_paths=True, named_paths=["other.txt"])
        self.assertIn("U19", self._next(), "a listing naming only other.txt paid config.txt")

    def test_a_read_of_the_changed_file_pays(self) -> None:
        self._bash("sed -i s/a/b/ config.txt", files_changed=["config.txt"])
        self._read("config.txt")
        self.assertNotIn("U19", self._next())
        self.assertNotIn("U12", self._next())

    def test_a_quiet_act_naming_the_path_pays(self) -> None:
        self._bash("sed -i s/a/b/ src/config.txt", files_changed=["src/config.txt"])
        self._bash("git diff", report_paths=True, named_paths=["src/config.txt"])
        self.assertEqual("", self._next())

    def test_two_files_are_two_demands(self) -> None:
        self._bash("patch -p1 < p", files_changed=["a.py", "b.py"])
        self._read("a.py")
        reason = self._next()
        self.assertIn("`b.py`", reason, "paying a.py must leave b.py owed")
        self.assertNotIn("`a.py`", reason)
        self._read("b.py")
        self.assertEqual("", self._next())

    def test_keels_own_measurement_names_every_dirty_path(self) -> None:
        self._bash("patch -p1 < p", files_changed=["a.py", "b.py"])
        self._read(STATE_PATH, observed_read=True)
        self.assertEqual("", self._next())

    def test_a_gone_pid_is_paid_by_a_listing_that_names_it(self) -> None:
        self._bash("kill 4821", pids_gone=[4821])
        self._bash("ps aux", report_pids=True, named_pids=[100, 200])
        self.assertIn("`4821`", self._next(), "a listing without the ended pid paid U03")
        self._bash("ps aux", report_pids=True, named_pids=[100, 4821])
        self.assertEqual("", self._next())

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red
        """Make every look name everything: the other-file cell must go red."""
        smoke_replace(
            self, PLUGIN / "keel" / "dispatch.py",
            b'    if record.get("observed_read") is True:\n        return True\n',
            b'    if True:\n        return True\n',
            "tests.test_keyed_effects.ALookPaysOnlyWhatItNames."
            "test_TEETH_a_read_of_another_file_pays_nothing",
            "paid a rewrite of config.txt",
        )


if __name__ == "__main__":
    unittest.main()
