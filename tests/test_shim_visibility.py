"""A wiring fault must fail OPEN and still be visible.

The shim's contract was "loud stderr + {} exit 0". The loud half was not loud: stderr from a hook
that exits 0 goes to the DEBUG LOG ONLY -- never the transcript, and the model never sees it. So a
plugin could be 100% non-functional with nothing surfacing anywhere anyone looks, which is exactly
the silent wiring death the shim exists to prevent. It was a guarantee that read as satisfied
because a diagnostic was written somewhere.

`systemMessage` is a universal output field shown to the user, so carriage keeps failing OPEN --
carriage that blocks is worse than carriage that is absent -- while no longer failing invisibly.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from tests.plant_support import PLUGIN, smoke_replace

SHIM = PLUGIN / "hooks" / "dispatch.sh"
EVENT = ('{"hook_event_name":"PreToolUse","tool_name":"Bash",'
         '"tool_input":{"command":"git push --force origin main"},"session_id":"t"}')


def run(env_extra: dict[str, str]) -> subprocess.CompletedProcess:
    env = {**os.environ, **env_extra}
    return subprocess.run([str(SHIM)], input=EVENT, text=True, capture_output=True,
                          check=False, env=env)


class WiringFaultsAreOpenButVisible(unittest.TestCase):
    def test_TEETH_a_missing_interpreter_surfaces_and_still_allows(self) -> None:
        done = run({"KEEL_PYTHON": "/nonexistent/python"})
        self.assertEqual(0, done.returncode, "carriage must fail OPEN")
        payload = json.loads(done.stdout)
        self.assertIn("systemMessage", payload,
                      "a wiring fault that only writes stderr is invisible at exit 0")
        self.assertIn("wiring fault", payload["systemMessage"])
        # No decision field: failing open means rendering no decision, not allowing loudly.
        self.assertNotIn("hookSpecificOutput", payload)
        self.assertNotIn("decision", payload)

    def test_TEETH_the_working_path_says_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as state:
            done = run({"KEEL_STATE_DIR": state})
        self.assertEqual(0, done.returncode, done.stderr)
        payload = json.loads(done.stdout)
        self.assertNotIn("systemMessage", payload,
                         "a healthy dispatch must not warn the user about anything")
        hook = payload.get("hookSpecificOutput", {})
        self.assertEqual("deny", hook.get("permissionDecision"),
                         "the healthy path must prove the dispatcher actually evaluated a guard")

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red; a checker that cannot follow an imported helper reads this body as empty
        smoke_replace(self, SHIM,
                      b'''    printf '{"systemMessage":"keel hook wiring fault: %s"}\\n' "$visible_fault"\n''',
                      b"    printf '{}\\n'\n", "tests.test_shim_visibility."
                      "WiringFaultsAreOpenButVisible."
                      "test_TEETH_a_missing_interpreter_surfaces_and_still_allows", "a wiring fault that only writes stderr is invisible at exit 0")


if __name__ == "__main__":
    unittest.main()
