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


class ExactlyOneObjectReachesTheWire(unittest.TestCase):
    """A hook speaks by writing ONE JSON object, and a second one erases the first.

    The shim wrote the child's output straight through and then appended `fail_open`'s object on
    any nonzero exit. A dispatcher that printed its decision and then died therefore put two
    objects on stdout:

        {"hookSpecificOutput": {... "permissionDecision": "deny" ...}}
        {"systemMessage":"keel hook wiring fault: Python dispatcher failed"}

    By the rule the shim itself quotes, "exit 0 with a parsed object that fails schema validation
    is a non-blocking error: the action proceeds" -- so a host reading the last object, or the
    concatenation, allows the call. A deny became an allow because the process died AFTER saying
    deny, which is the one failure a fail-open shim must not turn into a decision.

    The stub interpreter is the whole apparatus: `KEEL_PYTHON` already exists as a seam, so the
    child's behaviour can be chosen without touching the shipped package.
    """

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)

    def _python(self, body: str) -> str:
        """A stand-in interpreter that ignores `-m keel.dispatch` and does `body` instead."""
        path = os.path.join(self._temp.name, "fake-python")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("#!/bin/sh\n" + body + "\n")
        os.chmod(path, 0o755)
        return path

    def test_TEETH_a_decision_printed_before_death_is_the_only_object(self) -> None:
        deny = '{"hookSpecificOutput":{"permissionDecision":"deny"}}'
        done = run({"KEEL_PYTHON": self._python(f"printf '%s\\n' '{deny}'\nexit 7")})
        self.assertEqual(0, done.returncode, "carriage must fail OPEN")
        # `json.loads` on the whole stream is the assertion: two objects do not parse as one.
        payload = json.loads(done.stdout)
        # Read defensively rather than subscripting: a dropped decision must arrive as THIS
        # assertion's message, not as a KeyError, or the plant below proves the seam went red
        # while saying nothing about why.
        decision = payload.get("hookSpecificOutput", {}).get("permissionDecision")
        self.assertEqual("deny", decision,
                         f"the decision did not survive the death: {done.stdout!r}")
        self.assertNotIn("wiring fault", done.stdout,
                         f"a second object was appended to a real decision: {done.stdout!r}")

    def test_TEETH_a_silent_death_still_reports_the_wiring_fault(self) -> None:
        # The other direction, so the fix cannot be "never report anything". `fail_open` is for a
        # child that said nothing, which is the only state it was ever describing.
        done = run({"KEEL_PYTHON": self._python("exit 7")})
        self.assertEqual(0, done.returncode, "carriage must fail OPEN")
        self.assertIn("wiring fault", json.loads(done.stdout).get("systemMessage", ""))

    def test_TEETH_a_closed_decision_keeps_its_exit_status(self) -> None:
        # Exit 2 is the only closed signal that survives a payload the host refuses to parse, so
        # capturing the output must not swallow it.
        block = '{"decision":"block"}'
        done = run({"KEEL_PYTHON": self._python(f"printf '%s\\n' '{block}'\nexit 2")})
        self.assertEqual(2, done.returncode, done.stdout)
        self.assertEqual("block", json.loads(done.stdout)["decision"])

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red; a checker that cannot follow an imported helper reads this body as empty
        smoke_replace(self, SHIM,
                      b'if [ -n "$out" ]; then\n', b'if false; then\n',
                      "tests.test_shim_visibility.ExactlyOneObjectReachesTheWire."
                      "test_TEETH_a_decision_printed_before_death_is_the_only_object",
                      "the decision did not survive the death")
