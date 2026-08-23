"""A fail-open must reach a seat that can act on it -- at EVERY boundary, not just the shim.

`docs/FAIL-DIRECTION.md` §3 states the rule and, unusually, states that it was not true:

    Hook stderr on exit 0 goes to the debug log only. Not the transcript, not the user, not the
    model. So "loud-allow + stderr" was loud to nobody: a skipped check was indistinguishable,
    from every seat, from a clean pass. That is how 30 fail-opens in one day went unnoticed.

It was made true one layer out, in the shim, and asserted by `tests/test_shim_visibility.py`.
One layer in, the dispatcher's own three fail-open exits still printed a bare `{}`. Measured
before this file existed:

    $ printf 'not json at all' | python3 -c "…dispatch.main()"
    keel: unreadable event (JSONDecodeError) -- NOT-EVALUABLE      <- stderr, debug log only
    {}                                                              <- stdout: a bare allow
    exit=0

The unreadable-event exit runs BEFORE the event name is known, so that `{}` allowed an
unparseable `PreToolUse` with no user-visible trace anywhere. One rule, two boundaries,
enforced at one -- the fix at the first boundary never swept back through the second.

So this file checks the property at the boundary, and separately checks the SHAPE that made
the omission possible: a bare `{}` written as a fail-open exit. The behavioural tests below
cover the three exits that exist today; the shape check covers the fourth one nobody has
written yet, which is the only reason the shape check is here at all.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import unittest
from unittest import mock

from tests.plant_support import PLUGIN, smoke_replace

DISPATCH = PLUGIN / "keel" / "dispatch.py"
# Any event that is neither PreToolUse nor Stop/SubagentStop: those three have a deny/block wire,
# so they fail CLOSED and are not this file's subject. Everything else can only fail open.
NO_CLOSED_WIRE = {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                  "tool_input": {"command": "true"}, "session_id": "t"}


def _run_main(stdin_text: str, state: str, **patches):
    """Drive `dispatch.main()` in process and return its single stdout object."""
    from keel import dispatch
    out = io.StringIO()
    with mock.patch.dict(os.environ, {"KEEL_STATE_DIR": state}), \
            mock.patch("sys.stdin", io.StringIO(stdin_text)), \
            contextlib.ExitStack() as stack:
        for target, new in patches.items():
            stack.enter_context(mock.patch.object(dispatch, target, new))
        with contextlib.redirect_stdout(out):
            code = dispatch.main()
    return code, out.getvalue()


class _Raises(dict):
    """A HANDLERS stand-in whose lookup yields a handler that raises."""

    def get(self, _key, _default=None):
        def handler(*_a, **_kw):
            raise RuntimeError("planted")
        return handler


class _Unserializable(dict):
    def get(self, _key, _default=None):
        return lambda *_a, **_kw: {"nope": object()}


class FailOpensAreVisible(unittest.TestCase):
    maxDiff = None

    def _assert_loud_allow(self, code: int, stdout: str, because: str) -> dict:
        self.assertEqual(0, code, "a fail-open must still exit 0; carriage that blocks is worse")
        payload = json.loads(stdout)
        self.assertIn("systemMessage", payload,
                      f"{because}: an allow whose only explanation is stderr is, at exit 0, "
                      f"byte-identical to a clean pass from every seat")
        self.assertIn("WITHOUT BEING CHECKED", payload["systemMessage"])
        # Failing open means rendering no decision, not allowing loudly.
        self.assertNotIn("hookSpecificOutput", payload)
        self.assertNotIn("decision", payload)
        return payload

    def test_TEETH_an_unreadable_event_says_it_was_not_checked(self) -> None:
        with self.subTest("in process"):
            code, stdout = _run_main("not json at all", state=self._state())
            self._assert_loud_allow(code, stdout, "unreadable event")
        # Also through a real process, because this exit is reached before anything else runs and
        # an in-process harness could mask an import-time difference.
        done = subprocess.run(
            ["python3", "-c", "import sys; sys.path.insert(0, '.'); "
                              "from keel import dispatch; sys.exit(dispatch.main())"],
            cwd=PLUGIN, input="not json at all", text=True, capture_output=True, check=False,
            env={**os.environ, "KEEL_STATE_DIR": self._state(), "PYTHONDONTWRITEBYTECODE": "1"})
        self._assert_loud_allow(done.returncode, done.stdout, "unreadable event, real process")

    def test_TEETH_an_evaluation_fault_with_no_deny_wire_says_it_was_not_checked(self) -> None:
        code, stdout = _run_main(json.dumps(NO_CLOSED_WIRE), state=self._state(),
                                 HANDLERS=_Raises())
        payload = self._assert_loud_allow(code, stdout, "evaluation fault")
        self.assertIn("RuntimeError", payload["systemMessage"])

    def test_TEETH_a_serialization_fault_with_no_deny_wire_says_it_was_not_checked(self) -> None:
        code, stdout = _run_main(json.dumps(NO_CLOSED_WIRE), state=self._state(),
                                 HANDLERS=_Unserializable())
        self._assert_loud_allow(code, stdout, "serialization fault")

    def test_TEETH_the_healthy_path_says_nothing(self) -> None:
        """Without this, a dispatcher that warned on EVERY event would pass every test above."""
        code, stdout = _run_main(json.dumps(NO_CLOSED_WIRE), state=self._state())
        self.assertEqual(0, code)
        self.assertNotIn("systemMessage", json.loads(stdout or "{}"),
                         "a healthy dispatch must not tell the user anything was skipped")

    def test_no_fail_open_exit_writes_a_bare_empty_object(self) -> None:
        """The shape that let three exits be silent, so the fourth cannot be written silently.

        `print("{}")` is the spelling of "allow, explaining nothing". There is no case in this
        dispatcher where that is the right thing to emit: an exit that can decide uses its deny
        or block wire, and one that cannot must say so where the user reads.
        """
        source = DISPATCH.read_text(encoding="utf-8")
        self.assertNotIn('print("{}")', source,
                         "a bare `{}` on stdout is a fail-open that explains nothing; emit "
                         "`_open_not_evaluable(...)` instead")

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red
        smoke_replace(
            self, DISPATCH,
            b'''        print(json.dumps(_open_not_evaluable(f"the event could not be read "\n'''
            b'''                                             f"({type(exc).__name__})")))\n''',
            b'''        print("{}")\n''',
            "tests.test_fail_open_is_visible.FailOpensAreVisible."
            "test_TEETH_an_unreadable_event_says_it_was_not_checked",
            "an allow whose only explanation is stderr")

    def _state(self) -> str:
        import tempfile
        directory = tempfile.mkdtemp(prefix="keel-failopen.")
        self.addCleanup(lambda: __import__("shutil").rmtree(directory, ignore_errors=True))
        return directory


if __name__ == "__main__":
    unittest.main()
