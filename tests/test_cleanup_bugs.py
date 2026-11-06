"""Regression tests for defects found in the 2026-11-06 cleanup. Each fails on the code it names."""
from __future__ import annotations

import io
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from types import SimpleNamespace
from unittest import mock

from tests.plant_support import REPO
from keel import clauses as C
from keel import dispatch as D
from keel import effects as E
from tests.test_loader_refuses import base


def refused(**overrides):
    return C._load_object(base("Z-NEW", **overrides))


class LoaderRefusesInsteadOfCrashing(unittest.TestCase):
    """A malformed row must be a ClauseError (a named refusal), never a raw exception."""

    def test_missing_required_field(self):
        row = base("Z-MISSING")
        del row["event"]
        with self.assertRaises(C.ClauseError):
            C._load_object(row)

    def test_unhashable_kind(self):
        with self.assertRaises(C.ClauseError):
            refused(fingerprint={"kind": ["regex"], "on": "tool_name", "pattern": "^Bash$"})

    def test_probe_not_an_object(self):
        with self.assertRaises(C.ClauseError):
            refused(fingerprint={"kind": "regex", "on": "tool_name", "pattern": "^Bash$",
                                 "probe": "git status"})

    def test_subject_pattern_not_a_regex(self):
        with self.assertRaises(C.ClauseError):
            refused(subject={"on": "tool_input.command", "pattern": "git push ("},
                    tools=["Bash"], fixtures_pos=["git push origin"], fixtures_neg=["ls"])

    def test_subject_group_out_of_range(self):
        with self.assertRaises(C.ClauseError):
            refused(subject={"on": "tool_input.command", "pattern": "git push (\\S+)", "group": 2},
                    tools=["Bash"], fixtures_pos=["git push origin"], fixtures_neg=["ls"])

    def test_admission_reads_the_group_dispatch_reads(self):
        """Admission defaulted the group to 0 and dispatch to 1: a pattern with no capture group
        was admitted as keyable and then keyed every act under the empty string."""
        with self.assertRaises(C.ClauseError):
            refused(subject={"on": "tool_input.command", "pattern": "rm -rf \\S+/"},
                    tools=["Bash"], fixtures_pos=["rm -rf build/"], fixtures_neg=["ls"])


class DispatchKeying(unittest.TestCase):
    def test_overlong_subject_can_be_discharged_by_the_file_that_names_it(self):
        path = "d/" + "a" * 200 + ".txt"
        clause = SimpleNamespace(subject={"effect": "files_changed"})
        event = {"tool_name": "Read", "tool_input": {"file_path": path},
                 "keel_effect": {"observed_read": False, "named_paths": [path]}}
        (subject,) = D._subjects(clause, {"keel_effect": {"files_changed": [path]}})
        self.assertTrue(D._names(clause, event, subject))

    def test_a_live_process_of_another_user_is_not_a_lost_hook(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            pending = D._pending_dir(root)
            pending.mkdir(parents=True, exist_ok=True)
            (pending / "S1-1.json").write_text("{}")
            with mock.patch.object(D.os, "kill", side_effect=PermissionError):
                self.assertEqual(D._pending_lost(root, "S1"), [])

    def test_serialization_failure_is_journalled_as_the_deny_that_was_printed(self):
        event = {"hook_event_name": "PreToolUse", "session_id": "s", "tool_name": "Bash",
                 "tool_input": {"command": "ls"}}
        verdict = {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                          "permissionDecision": "allow", "x": object()}}
        recorded = []
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"KEEL_STATE_DIR": tmp}), \
                mock.patch.object(D.wire, "read_stdin", return_value=(__import__("json").dumps(event), 0)), \
                mock.patch.dict(D.HANDLERS, {"PreToolUse": lambda *a, **k: verdict}), \
                mock.patch.object(D, "_record", side_effect=lambda ev, out: recorded.append(out)), \
                redirect_stdout(io.StringIO()) as printed, redirect_stderr(io.StringIO()):
            D.main()
        wire_out = __import__("json").loads(printed.getvalue())
        self.assertEqual(wire_out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(recorded[0], wire_out)


class ShellScope(unittest.TestCase):
    def test_c08_activates_on_a_powershell_test_pass_like_a_bash_one(self):
        c08 = next(c for c in C.load_default() if c.id.startswith("C08"))
        def post(tool):
            return {"hook_event_name": "PostToolUse", "tool_name": tool,
                    "tool_input": {"command": "pytest -q"},
                    "keel_effect": {"report_pass": True}}
        self.assertTrue(C._predicate(c08.activated_by, post("Bash")))
        self.assertTrue(C._predicate(c08.activated_by, post("PowerShell")))


def _git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


class RemoteObservation(unittest.TestCase):
    def test_observe_remote_lists_a_remote_that_is_not_named_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            bare, work, state = (pathlib.Path(tmp) / n for n in ("bare", "work", "state"))
            for p in (bare, work, state):
                p.mkdir()
            _git(bare, "init", "--bare", "-q")
            _git(work, "init", "-q")
            _git(work, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "--allow-empty", "-qm", "x")
            _git(work, "remote", "add", "upstream", str(bare))
            _git(work, "push", "-q", "upstream", "HEAD:refs/heads/main")
            self.assertIsNotNone(E.observe_remote(state, str(work)))


    def test_at_stop_is_not_evaluable_when_the_remotes_cannot_be_listed(self):
        real = E._git
        with tempfile.TemporaryDirectory() as tmp:
            work, state = pathlib.Path(tmp) / "work", pathlib.Path(tmp) / "state"
            work.mkdir()
            state.mkdir()
            _git(work, "init", "-q")
            slot = E._slot(state, "s", "a")
            slot.mkdir()
            E._remember(slot, {"net_out": True})
            def no_remote_listing(root, *args, **kw):
                return None if args[:1] == ("remote",) else real(root, *args, **kw)
            with mock.patch.object(E, "_git", side_effect=no_remote_listing):
                out = E.at_stop(state, "s", "a", str(work))
        self.assertIsNone(out["remote_landed"])
        self.assertTrue(out.get("not_evaluable"))


class ReplayHarness(unittest.TestCase):
    def test_a_dispatcher_that_prints_a_non_object_is_reported_not_crashed_on(self):
        sys.path.insert(0, str(REPO))
        try:
            from eval import replay
        finally:
            sys.path.remove(str(REPO))
        proc = SimpleNamespace(stdout="null", stderr="", returncode=0)
        with mock.patch.object(replay.subprocess, "run", return_value=proc):
            result = replay.dispatch({}, "/nonexistent")
        self.assertIsNone(replay.fired(result))
        self.assertIsNotNone(replay.crashed(result))


if __name__ == "__main__":
    unittest.main()
