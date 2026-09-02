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
import re
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock

from tests.plant_support import PLUGIN, smoke_replace
from keel import clauses as C
from keel import effects
from keel.ledger import Ledger

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

    def observe(self, command: str, stdout: str | None = None) -> dict:
        """The act observed live; its output is the real output unless a shape is planted."""
        effects.snapshot(self.state, "s", "", self.repo)
        done = subprocess.run(command, shell=True, cwd=self.repo, capture_output=True, text=True)
        return effects.delta(self.state, "s", "", {"tool_input": {"command": command},
                                                    "tool_response": {"stdout": done.stdout if stdout is None else stdout}})


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
        self.assertEqual(16, sum(v == "effect" for v in classes.values()))

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

    def _gap(self, moved: bool) -> None:
        """Plant the idle gap: the counter the previous act ended on, equal to now (quiet) or
        behind it (the host moved on its own while nothing of this session ran)."""
        slot = effects._slot(self.state, "s", "")
        slot.mkdir(parents=True, exist_ok=True)
        now = effects.net_active_opens()
        self.assertIsNotNone(now, "no counter on this host: the channel is NOT-EVALUABLE")
        (slot / "session.json").write_text(json.dumps({"net_after": now - (1 if moved else 0),
                                                       "remote_measured": True}),
                                           encoding="utf-8")

    def test_a_connection_is_assigned_by_the_idle_gap(self) -> None:
        """One rule, both directions. A counter that moved while nothing of this session ran
        cannot assign its movement to the act: NOT-EVALUABLE, not the act's, not clean."""
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        self.addCleanup(listener.close)
        connect = (f"python3 -c \"import socket; "
                   f"socket.create_connection(('127.0.0.1', {listener.getsockname()[1]}))\"")
        self._gap(moved=True)
        self.assertIsNone(self.observe(connect)["net_out"])
        self._gap(moved=False)
        self.assertTrue(self.observe(connect)["net_out"])
        # The quiet half of the rule, on a scripted counter so the host cannot vote: the
        # counter the act started on is the counter it ended on.
        with unittest.mock.patch.object(effects, "net_active_opens", return_value=1000):
            self._gap(moved=False)
            self.assertFalse(self.observe("git status")["net_out"])

    def test_a_process_of_another_lineage_is_not_assigned(self) -> None:
        """Born DURING the act, alive after it, and not this session's: a child of a process
        session this session never held. Newness alone would admit it; lineage refuses it."""
        # A process session of its own, OUTSIDE the tree before the snapshot (its launcher
        # exits at once, so it is reparented away), that starts a worker during the act.
        pidfile = pathlib.Path(self.tmp, "foreign.pid")
        subprocess.run(["sh", "-c", f"setsid sh -c 'echo $$ > {pidfile}; sleep 0.3; "
                                    f"sleep 60 & exit 0' & exit 0"])
        for _ in range(50):
            if pidfile.exists() and pidfile.read_text().strip():
                break
            time.sleep(0.02)
        foreign = int(pidfile.read_text())
        self.addCleanup(lambda: subprocess.run(["pkill", "-9", "-s", str(foreign)]))
        time.sleep(0.1)
        effects.snapshot(self.state, "s", "", self.repo)
        time.sleep(0.6)  # the act; the foreign session starts its worker meanwhile
        d = effects.delta(self.state, "s", "", {})
        born = [p for p in effects.pids() or {} if effects.process_session(p) == foreign]
        self.assertTrue(born, "the foreign session left nothing alive to judge")
        self.assertFalse(set(born) & set(d["pids_spawned"]), f"assigned a foreign lineage: {born}")

    # ---- the guard side: what the guard act DID, and its mention doing nothing ----------------

    def test_a_printed_ref_is_the_one_the_snapshot_holds(self) -> None:
        self.assertTrue(self.observe("git status")["report_ref"], "`On branch main` names the branch")
        self.assertTrue(self.observe("git rev-parse HEAD")["report_ref"])
        self.assertFalse(self.observe("echo 'git rev-parse HEAD'")["report_ref"], "a mention prints no ref")
        self.assertFalse(self.observe("echo 0123456789abcdef")["report_ref"], "hex the snapshot does not hold")

    def test_a_printed_path_is_one_the_snapshot_holds(self) -> None:
        self.assertTrue(self.observe("ls")["report_paths"])
        pathlib.Path(self.repo, "a.txt").write_text("two\n", encoding="utf-8")
        self.assertTrue(self.observe("git diff")["report_paths"], "`a/a.txt` names a.txt")
        self.assertFalse(self.observe("echo 'ls -la'")["report_paths"])
        # A loud act is not a look: it changed the file it printed.
        self.assertFalse(self.observe("printf three > a.txt && ls")["report_paths"])

    def test_a_listing_claims_live_pids_and_a_mention_claims_none(self) -> None:
        self.assertTrue(self.observe("ps -eo pid,comm")["report_pids"])
        self.assertFalse(self.observe("echo 'ps -eo pid,comm'")["report_pids"])

    def test_a_listing_that_lists_itself_is_seen_and_one_that_does_not_is_the_guard(self) -> None:
        listed = self.observe("ps -eo pid,args | grep 'pid,args'")
        self.assertTrue(listed["report_self"], "the grep printed its own line")
        self.assertFalse(listed["report_listing"])
        clean = self.observe("ps -eo pid,comm")
        self.assertFalse(clean["report_self"])
        self.assertTrue(clean["report_listing"])

    def test_a_structured_datum_and_a_null_are_told_apart(self) -> None:
        self.assertTrue(self.observe("python3 -c 'import json; print(json.dumps({\"a\": 1}))'")["report_structured"])
        self.assertFalse(self.observe("echo null")["report_structured"])
        self.assertFalse(self.observe("echo '{\"a\": 1}' > /dev/null")["report_structured"])

    def test_a_connection_that_changed_nothing_is_a_read(self) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        self.addCleanup(listener.close)
        port = listener.getsockname()[1]
        self._gap(moved=False)
        read = self.observe(f"python3 -c \"import socket; socket.create_connection(('127.0.0.1', {port}))\"")
        self.assertTrue(read["net_out"])
        self.assertTrue(read["net_read"])
        self._gap(moved=False)
        loud = self.observe(f"python3 -c \"import socket; socket.create_connection(('127.0.0.1', {port}))\" && printf x > a.txt")
        self.assertTrue(loud["net_out"])
        self.assertFalse(loud["net_read"], "a connection beside a rewrite is not a read")

    def test_the_operator_reads_keels_own_measurement(self) -> None:
        effects.observe(self.state, "s", "", self.repo)
        observed = self.state / "observed.json"
        remote = self.state / "remote.json"
        self.assertTrue(observed.is_file() and remote.is_file())
        doc = json.loads(observed.read_text(encoding="utf-8"))
        self.assertEqual(git(self.repo, "rev-parse", "HEAD").strip(), doc["head"])
        self.assertEqual("main", doc["branch"])
        def read(path):
            return effects.read_delta(self.state, {"tool_name": "Read", "tool_input": {"file_path": str(path)}})
        self.assertTrue(read(observed)["observed_read"])
        self.assertTrue(read(remote)["remote_read"])
        self.assertFalse(read(observed)["remote_read"])
        self.assertFalse(read(self.state / "other.json")["observed_read"])
        # A Read through a Bash `cat` is an act, not a host read: the record is the act's.
        self.assertFalse(self.observe(f"cat {observed}")["observed_read"])

    def test_the_remote_is_not_written_when_it_cannot_be_listed(self) -> None:
        git(self.repo, "remote", "add", "origin", os.path.join(self.tmp, "absent.git"))
        self.assertIsNone(effects.observe_remote(self.state, self.repo))
        self.assertFalse((self.state / "remote.json").exists(), "an unlisted remote leaves no artifact to Read")

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

    def _act(self, command: str, run: bool = True) -> tuple[dict, dict]:
        """A Bash call through the hook, the world observed live around it, its output real."""
        before = self._hook(hook_event_name="PreToolUse", tool_name="Bash",
                            tool_input={"command": command})
        stdout = ""
        if run and not before:
            done = subprocess.run(command, shell=True, cwd=self.repo, capture_output=True, text=True)
            stdout = done.stdout
        after = self._hook(hook_event_name="PostToolUse", tool_name="Bash",
                           tool_input={"command": command}, tool_response={"stdout": stdout})
        return before, after

    def _read(self, name: str) -> dict:
        """A host Read of one of Keel's own artifacts, its record measured live."""
        path = str(self.state / name)
        before = self._hook(hook_event_name="PreToolUse", tool_name="Read",
                            tool_input={"file_path": path})
        self._hook(hook_event_name="PostToolUse", tool_name="Read", tool_input={"file_path": path},
                   tool_response={"file": {"filePath": path}})
        return before

    @staticmethod
    def denied(out: dict) -> set[str]:
        reason = (out.get("hookSpecificOutput") or {}).get("permissionDecisionReason", "")
        return set(re.findall(r"\[([A-Z]\d\d[\w-]*)\]", reason))

    def owed(self) -> set[str]:
        """What the ledger holds open for this session: the one source the denial must equal."""
        return {row["clause_id"] for row in Ledger(self.state).open_demands("fx", "")}

    def refusal_matches_the_ledger(self) -> set[str]:
        owed = self.owed()
        refused = self.denied(self._hook(hook_event_name="PreToolUse", tool_name="Bash",
                                         tool_input={"command": "echo next"}))
        self.assertEqual(owed, refused, "the refusal names exactly what the ledger holds open")
        return owed

    def pay(self) -> None:
        """Discharge whatever is owed, by the TABLE: each open clause's own first discharge
        fixture, driven through the hook. What is owed on a given host is whatever its world
        did around the calls -- the ledger says which, the table says how it is paid."""
        table = {c.id: c for c in C.load_default()}
        for _ in range(len(table) + 1):
            owed = self.owed()
            if not owed:
                return
            fixture = table[sorted(owed)[0]].fixtures_discharge[0]
            event = (dict(fixture) if isinstance(fixture, dict) else
                     {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                      "tool_input": {"command": fixture}})
            self.assertEqual({}, self._hook(**event), f"the guard for {sorted(owed)[0]} was refused")
            # A recorded fixture is complete in itself; only a live PreToolUse Bash call has
            # a PostToolUse still to come, and its record is then measured live.
            if event.get("hook_event_name") == "PreToolUse" and event["tool_name"] == "Bash":
                self._hook(hook_event_name="PostToolUse", tool_name="Bash",
                           tool_input=event["tool_input"], tool_response={"stdout": ""})
        self.fail(f"still owed after paying every clause once: {self.owed()}")

    def test_a_rewrite_nobody_looked_at_refuses_the_next_call_until_the_diff_is_seen(self) -> None:
        # The session's opening debt, paid the way any session pays it: the artifacts exist
        # from the session start, and the operator Reads them -- measured live, nothing recorded.
        opened = self._hook(hook_event_name="SessionStart")
        self.assertNotIn("permissionDecision", json.dumps(opened), "the session start denied")
        self.assertTrue((self.state / "observed.json").is_file())
        self.assertTrue((self.state / "remote.json").is_file())
        self.assertEqual({}, self._read("observed.json"))
        self.assertEqual({}, self._read("remote.json"))
        self.assertFalse({"A01", "A02", "A03"} & self.owed(), "the reads paid the opening debt")
        self.pay()
        # The act itself is not refused: nothing before it could tell it from `cat`.
        before, _ = self._act("printf changed > a.txt")
        self.assertEqual({}, before, before)
        self.assertEqual("changed", pathlib.Path(self.repo, "a.txt").read_text())
        # The NEXT call is: the refusal equals the ledger, and the ledger holds the rewrite.
        owed = self.refusal_matches_the_ledger()
        self.assertLessEqual({"U12", "U13", "U19"}, owed)
        # The guard is a Bash act, so it passes on its commitment and pays by its effect: the
        # diff printed a path the snapshot holds. The refusal still equals the ledger.
        self.assertEqual({}, self._act("# keel-guard: U12 U13 U19\ngit diff")[0])
        owed = self.refusal_matches_the_ledger()
        self.assertFalse({"U12", "U13", "U19"} & owed, f"not paid by the diff: {owed}")

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red
        """Stop attaching the delta after a Bash act: no effect of the rewrite is observed, no
        demand is raised, and the next call after it passes -- the cell above goes red. The
        Read record is left armed, so the opening debt is still paid and the red is the
        rewrite's, not the session's."""
        smoke_replace(
            self, PLUGIN / "keel" / "dispatch.py",
            b'            if tool not in HOST_READS:\n'
            b'                event["keel_effect"] = effects.delta(',
            b'            if tool in HOST_READS:\n'
            b'                event["keel_effect"] = effects.delta(',
            "tests.test_effects.TheDispatcherEnforcesAnEffect."
            "test_a_rewrite_nobody_looked_at_refuses_the_next_call_until_the_diff_is_seen",
            "still owed",  # no delta for any tool: the guard acts pay nothing either, so every demand stands
        )


if __name__ == "__main__":
    unittest.main()
