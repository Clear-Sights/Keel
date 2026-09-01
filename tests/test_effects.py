"""The occasion side reads the WORLD, not the command -- and the world is really observed.

Coverings.v Theorem 3: before the act, the program's name is the only thing that separates one
command from another, so no name-agnostic covering over the command can select the act. Every
occasion in the shipped table is therefore `always`, a host tool enum, a pipe topology, or an
EFFECT (Theorem 8): what the act did, observed by `keel.effects` before and after the call.

Three things are pinned here, each in both directions:

  * the LOADER refuses an occasion that selects by name (`CLAUSE-OCCASION-NOMINAL`), an effect
    the observer does not measure (`CLAUSE-EFFECT-UNKNOWN`), and an effect occasion declared
    before the act (`CLAUSE-EFFECT-EVENT`) -- and the shipped table has no nominal occasion;
  * the OBSERVER sees real effects on a real repository -- content rewritten with the pre-image
    recoverable, a file removed, HEAD switched versus a commit made, a reset, a process gone, a
    process surviving its launch, a connection opened, and each report shape -- and reports
    NOT-EVALUABLE when it has nothing to compare against;
  * the DISPATCHER, driven through the shipped hook on a real repository, refuses the call
    AFTER a rewrite nobody looked at, admits the guard, and admits the call after it.

Every measurement here is made on a temporary repository this file creates; nothing reads the
checkout it runs in.
"""
from __future__ import annotations

import json
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import time
import unittest

from tests.plant_support import PLUGIN, smoke_replace
from keel import clauses as C
from keel import effects

CLAUSES = PLUGIN / "keel" / "clauses.json"
SHIM = PLUGIN / "hooks" / "dispatch.sh"


def git(repo: str, *args: str) -> str:
    return subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True,
                          text=True).stdout


class Repo(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="keel-effects-")
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)
        self.repo = os.path.join(self.tmp, "repo")
        self.state = pathlib.Path(self.tmp, "state")
        os.mkdir(self.repo)
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "k@e.el")
        git(self.repo, "config", "user.name", "keel")
        git(self.repo, "config", "commit.gpgsign", "false")
        pathlib.Path(self.repo, "a.txt").write_text("one\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")

    def observe(self, command: str, stdout: str = "") -> dict:
        effects.snapshot(self.state, "s", "", self.repo)
        subprocess.run(command, shell=True, cwd=self.repo, capture_output=True)
        return effects.delta(self.state, "s", "", {"tool_input": {"command": command},
                                                    "tool_response": {"stdout": stdout}})


class TheLoaderRefusesANominalOccasion(unittest.TestCase):
    def _load(self, mutate) -> None:
        rows = json.loads(CLAUSES.read_text(encoding="utf-8"))
        mutate({r["id"]: r for r in rows})
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d, "clauses.json")
            path.write_text(json.dumps(rows), encoding="utf-8")
            C.load_bundle(path)

    def test_NON_VACUITY_the_shipped_table_has_no_nominal_occasion(self) -> None:
        table = C.load_default()
        self.assertEqual(24, len(table))
        classes = {f"{c.id}.{side}": C.classify_side(getattr(c, side)) for c in table
                   for side in ("fingerprint", "activated_by") if isinstance(getattr(c, side), dict)}
        self.assertEqual(27, len(classes), "occasion sides moved; re-measure rather than edit")
        self.assertEqual([], [k for k, v in classes.items() if v not in C.AGNOSTIC_OCCASIONS])
        self.assertEqual(15, sum(v == "effect" for v in classes.values()))

    def test_a_program_name_on_the_occasion_side_is_refused(self) -> None:
        def plant(by):
            by["U19"]["fingerprint"] = {"kind": "program", "on": "tool_input.command",
                                       "names": ["sed", "perl"]}
            by["U19"]["fixtures_pos"] = ["sed -i s/a/b/ f"]
            by["U19"]["fixtures_neg"] = ["cat f"]
        with self.assertRaises(C.ClauseError) as caught:
            self._load(plant)
        self.assertEqual("CLAUSE-OCCASION-NOMINAL", caught.exception.code)
        self.assertIn("U19", str(caught.exception))

    def test_a_program_name_on_the_activation_side_is_refused(self) -> None:
        def plant(by):
            by["T02"]["activated_by"] = {"kind": "program", "on": "tool_input.command",
                                        "argv": [["git", "push"]]}
            by["T02"]["fixtures_activate"] = ["git push origin main"]
        with self.assertRaises(C.ClauseError) as caught:
            self._load(plant)
        self.assertEqual("CLAUSE-OCCASION-NOMINAL", caught.exception.code)

    def test_an_effect_the_observer_does_not_measure_is_refused(self) -> None:
        def plant(by):
            by["U19"]["fingerprint"] = {"kind": "effect", "effect": "files_glanced_at"}
        with self.assertRaises(C.ClauseError) as caught:
            self._load(plant)
        self.assertEqual("CLAUSE-EFFECT-UNKNOWN", caught.exception.code)

    def test_an_effect_occasion_before_the_act_is_refused(self) -> None:
        def plant(by):
            by["U19"]["event"] = "PreToolUse"
        with self.assertRaises(C.ClauseError) as caught:
            self._load(plant)
        self.assertEqual("CLAUSE-EFFECT-EVENT", caught.exception.code)

    def test_every_effect_a_clause_names_is_one_the_observer_measures(self) -> None:
        named = {leaf["effect"] for c in C.load_default()
                 for side in (c.fingerprint, c.activated_by, c.discharged_by) if isinstance(side, dict)
                 for leaf in C._leaves(side) if leaf.get("kind") == "effect"}
        self.assertTrue(named)
        self.assertLessEqual(named, set(effects.EFFECTS))


class TheObserverSeesTheWorld(Repo):
    def test_a_rewrite_is_seen_and_its_pre_image_is_recoverable(self) -> None:
        d = self.observe("printf two > a.txt")
        self.assertEqual(["a.txt"], d["files_changed"])
        self.assertEqual([], d["files_removed"])
        self.assertEqual("one\n", git(self.repo, "show", f"{d['pre_image']}:a.txt"))

    def test_an_untracked_file_removed_is_seen_with_its_pre_image(self) -> None:
        pathlib.Path(self.repo, "scratch.txt").write_text("gone soon\n", encoding="utf-8")
        d = self.observe("rm scratch.txt")
        self.assertEqual(["scratch.txt"], d["files_removed"])
        self.assertEqual("gone soon\n", git(self.repo, "show", f"{d['pre_image']}:scratch.txt"))

    def test_the_same_act_under_another_name_is_the_same_effect(self) -> None:
        """Theorem 8 on the ground: the observation does not depend on what removed the file."""
        for command in ("rm a.txt", "python3 -c \"import os; os.remove('a.txt')\"",
                        "find . -name a.txt -delete"):
            git(self.repo, "checkout", "-q", "--", "a.txt")
            with self.subTest(command=command):
                self.assertEqual(["a.txt"], self.observe(command)["files_removed"])

    def test_a_commit_moves_head_but_is_not_a_switch(self) -> None:
        d = self.observe("printf two > a.txt && git add -A && git commit -qm second")
        self.assertTrue(d["head_moved"])
        self.assertFalse(d["head_switched"])
        self.assertFalse(d["head_reset"])
        self.assertFalse(d["commit_signed"])

    def test_a_checkout_of_an_existing_commit_is_a_switch(self) -> None:
        git(self.repo, "checkout", "-q", "-b", "other")
        pathlib.Path(self.repo, "b.txt").write_text("b\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "on other")
        git(self.repo, "checkout", "-q", "main")
        time.sleep(1.1)  # the commit predates the snapshot by a whole second
        d = self.observe("git checkout -q other")
        self.assertTrue(d["head_moved"])
        self.assertTrue(d["head_switched"])

    def test_a_hard_reset_to_an_ancestor_is_a_reset(self) -> None:
        pathlib.Path(self.repo, "a.txt").write_text("two\n", encoding="utf-8")
        git(self.repo, "commit", "-qam", "second")
        d = self.observe("git reset -q --hard HEAD~1")
        self.assertTrue(d["head_reset"])
        self.assertEqual(["a.txt"], d["files_changed"])

    def test_a_process_ended_during_the_act_is_seen(self) -> None:
        child = subprocess.Popen(["sleep", "60"])
        self.addCleanup(lambda: child.poll() is None and child.kill())
        time.sleep(0.2)
        effects.snapshot(self.state, "s", "", self.repo)
        child.kill()
        child.wait()
        d = effects.delta(self.state, "s", "", {})
        self.assertIn(child.pid, d["pids_gone"])

    def test_a_worker_surviving_its_launch_is_seen_orphaned_and_a_second_is_a_relaunch(self) -> None:
        """A daemonized worker is reparented to pid 1 and leaves the session's tree; it is
        still this session's process -- seen when it appears, remembered, seen when it ends."""
        first = self.observe("nohup sleep 60 >/dev/null 2>&1 &")
        self.assertTrue(first["pids_spawned"])
        self.assertFalse(first["pids_spawned_again"])
        second = self.observe("nohup sleep 60 >/dev/null 2>&1 &")
        self.assertTrue(second["pids_spawned"])
        self.assertTrue(second["pids_spawned_again"])
        launched = first["pids_spawned"] + second["pids_spawned"]
        effects.snapshot(self.state, "s", "", self.repo)
        ended = []
        for pid in launched:
            try:
                os.kill(pid, 9)
                ended.append(pid)
            except ProcessLookupError:
                pass  # a short-lived helper the launch left behind, already gone
        self.assertTrue(ended, "nothing launched was still alive to end")
        time.sleep(0.2)
        d = effects.delta(self.state, "s", "", {})
        self.assertEqual(sorted(ended), sorted(set(d["pids_gone"]) & set(ended)))

    def test_an_outbound_connection_is_seen_and_a_local_command_is_not(self) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        self.addCleanup(listener.close)
        port = listener.getsockname()[1]
        # The negative half needs a host that opens no connections of its own while a local
        # command runs. A CI runner is not one -- measured, its counters moved during `git
        # status` -- and the observer counts the host's connections as the act's (stated on the
        # effect). So the half is reported NOT-EVALUABLE on such a host, never asserted false.
        quiet = self.observe("git status")
        if quiet["net_out"]:
            ambient = effects.net_active_opens()
            time.sleep(1.0)
            if effects.net_active_opens() != ambient:
                self.skipTest("this host opens connections on its own; the negative half is "
                              "NOT-EVALUABLE here, not passed")
            quiet = self.observe("git status")
        self.assertFalse(quiet["net_out"])
        self.assertTrue(self.observe(
            f"python3 -c \"import socket; socket.create_connection(('127.0.0.1', {port}))\"")["net_out"])

    def test_report_shapes(self) -> None:
        self.assertTrue(self.observe("true", "== 40 passed in 1.2s ==")["report_pass"])
        self.assertTrue(self.observe("true", "Ran 3 tests\n\nOK\n")["report_pass"])
        self.assertTrue(self.observe("true", "1 failed, 39 passed")["report_fail"])
        self.assertFalse(self.observe("true", "1 failed, 39 passed")["report_pass"])
        self.assertTrue(self.observe("true", "0 findings")["report_clean"])
        self.assertTrue(self.observe("jq .x f.json", "null")["report_null"])
        self.assertFalse(self.observe("echo hi", "hi")["report_null"])

    def test_no_snapshot_is_not_evaluable_not_clean(self) -> None:
        d = effects.delta(self.state, "never", "", {})
        self.assertEqual("no pre-act snapshot", d["not_evaluable"])
        self.assertIsNone(d["files_changed"])
        self.assertIsNone(d["pids_gone"])

    def test_outside_a_repository_content_change_is_still_seen(self) -> None:
        plain = os.path.join(self.tmp, "plain")
        os.mkdir(plain)
        pathlib.Path(plain, "x").write_text("a", encoding="utf-8")
        effects.snapshot(self.state, "p", "", plain)
        time.sleep(0.01)
        pathlib.Path(plain, "x").write_text("bb", encoding="utf-8")
        d = effects.delta(self.state, "p", "", {})
        self.assertEqual(["x"], d["files_changed"])
        self.assertIsNone(d["head_moved"], "no repository, so no ref was observable")


class TheDispatcherEnforcesAnEffect(Repo):
    def _hook(self, **payload) -> dict:
        payload.setdefault("session_id", "fx")
        payload.setdefault("cwd", self.repo)
        env = dict(os.environ, KEEL_STATE_DIR=str(self.state), CLAUDE_PLUGIN_ROOT=str(PLUGIN))
        done = subprocess.run(["bash", str(SHIM)], input=json.dumps(payload), capture_output=True,
                              text=True, env=env, timeout=60)
        return json.loads(done.stdout.strip() or "{}")

    def _act(self, command: str, run: bool = True, live: bool = True) -> tuple[dict, dict]:
        """A Bash call through the hook. `live` measures the world around it; otherwise the
        PostToolUse event carries an explicit empty record, because on a shared host the
        world moves on its own (a CI runner opened connections during `git status`) and only
        the act under test is meant to be observed."""
        before = self._hook(hook_event_name="PreToolUse", tool_name="Bash",
                            tool_input={"command": command})
        if run and not before:
            subprocess.run(command, shell=True, cwd=self.repo, capture_output=True)
        post = dict(hook_event_name="PostToolUse", tool_name="Bash",
                    tool_input={"command": command}, tool_response={"stdout": ""})
        if not live:
            record = {n: [] if n in ("files_changed", "files_removed", "remote_ref_moved",
                                     "pids_gone", "pids_spawned") else False
                      for n in effects.EFFECTS}
            record["remote_landed"] = None
            post["keel_effect"] = record
        after = self._hook(**post)
        return before, after

    @staticmethod
    def denied(out: dict) -> str:
        return (out.get("hookSpecificOutput") or {}).get("permissionDecisionReason", "")

    def test_a_rewrite_nobody_looked_at_refuses_the_next_call_until_the_diff_is_seen(self) -> None:
        # The session's opening debt, paid the way any session pays it.
        self.assertEqual({}, self._act("git status", live=False)[0])
        self.assertEqual({}, self._act("git fetch origin", run=False, live=False)[0])
        # The act itself is not refused: nothing before it could tell it from `cat`.
        before, _ = self._act("printf changed > a.txt")
        self.assertEqual({}, before)
        self.assertEqual("changed", pathlib.Path(self.repo, "a.txt").read_text())
        # The NEXT call is, naming every clause the rewrite owes.
        refused = self.denied(self._hook(hook_event_name="PreToolUse", tool_name="Bash",
                                         tool_input={"command": "echo next"}))
        for owed in ("U12", "U13", "U19"):
            self.assertIn(owed, refused)
        # The guard passes, and pays. What may still be refused afterwards is whatever the HOST
        # did around this test -- on a CI runner the network counters move on their own, and a
        # connection nobody in this test opened is still an observed effect (U06, U24). The
        # claim here is about the rewrite: after the diff, none of its three clauses is owed.
        self.assertEqual({}, self._act("git diff", live=False)[0])
        after = self.denied(self._hook(hook_event_name="PreToolUse", tool_name="Bash",
                                       tool_input={"command": "echo next"}))
        for paid in ("U12", "U13", "U19"):
            self.assertNotIn(paid, after, f"{paid} was not paid by the diff: {after}")

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red
        """Stop attaching the delta after the act: no effect is ever observed, no demand is
        raised, and the next call after a rewrite passes -- the cell above goes red."""
        smoke_replace(
            self, PLUGIN / "keel" / "dispatch.py",
            b'        elif moment == "after":',
            b'        elif moment == "after-disarmed":',
            "tests.test_effects.TheDispatcherEnforcesAnEffect."
            "test_a_rewrite_nobody_looked_at_refuses_the_next_call_until_the_diff_is_seen",
            "U12",
        )


if __name__ == "__main__":
    unittest.main()
