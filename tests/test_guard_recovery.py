"""First-act recovery, checked commitments, and shell scope at the host boundary."""
from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest import mock

from tests.plant_support import PLUGIN, record
from keel import clauses as C, dispatch, effects
from keel.ledger import Demand, Ledger


class ReconcileRecovery(unittest.TestCase):
    """Recorded post-act obligations: missing is retired, never proof of a guard."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="keel-reconcile-")
        self.addCleanup(tmp.cleanup)
        self.cwd = Path(tmp.name) / "work"
        self.cwd.mkdir()
        self.ledger = Ledger(Path(tmp.name) / "state")
        self.table = [cl for cl in C.load_default() if cl.id in {"U12", "U13", "U19"}]
        self.event = {"hook_event_name": "Stop", "session_id": "reconcile", "agent_id": "",
                      "cwd": str(self.cwd), "keel_effect": record()}

    def demand(self, clause_id, subject, agent=""):
        cl = next(cl for cl in C.load_default() if cl.id == clause_id)
        demand = Demand("reconcile", agent, cl.id, str(subject), cl.deny_reason)
        self.ledger.demand(demand)
        return demand

    def stop(self, **extra):
        event = {**self.event, **extra}
        out = dispatch.reconcile(self.table, self.ledger, event)
        with mock.patch.dict(os.environ, {"KEEL_STATE_DIR": str(self.ledger.root)}):
            dispatch._record(event, out)
        return out

    def journal(self):
        path = self.ledger.root / "decisions.jsonl"
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    def test_deleted_recorded_bash_targets_retire_without_a_licence(self):
        target = self.cwd / "ephemeral.txt"
        target.write_text("changed then removed\n")
        # Replay the observed files_changed event, then the fixture cleanup. A net-zero
        # create/delete alone is outside the current observer's before/after resolution.
        event = {**self.event, "hook_event_name": "PostToolUse", "tool_name": "Bash",
                 "tool_input": {"command": "fixture write; fixture cleanup"},
                 "keel_effect": record(files_changed=[str(target)])}
        dispatch.post_tool_use(self.table, self.ledger, event)
        original = self.ledger.open_demands("reconcile", "")
        self.assertEqual({"U12", "U13", "U19"}, {r["clause_id"] for r in original})
        target.unlink()
        self.assertEqual({}, self.stop())
        self.assertEqual(original, self.ledger.open_demands("reconcile", ""))
        for row in original:
            self.assertFalse(self.ledger.is_licensed("reconcile", "", row["id"]))
        retired = [r for r in self.journal() if r["kind"] == "retired_missing"]
        self.assertEqual(original, [r["demand"] for r in retired])
        self.assertIsNone(self.ledger.verify_chain())
        self.assertEqual({}, self.stop())
        self.assertEqual(6, len([r for r in self.journal() if r["kind"] == "retired_missing"]))
        target.write_text("a new incarnation\n")
        dispatch.post_tool_use(self.table, self.ledger, event)
        self.assertEqual(3, len(self.ledger.open_demands("reconcile", "")))
        self.assertEqual("block", self.stop()["decision"])

    def test_forty_rows_group_reason_and_keep_every_audit_row(self):
        for i in range(40):
            path = self.cwd / f"file-{i:02d}.txt"
            path.write_text("still exists\n")
            self.demand("U12", path)
        original = self.ledger.open_demands("reconcile", "")
        out = self.stop()
        self.assertEqual({"decision", "reason"}, set(out))  # host wire shape unchanged
        self.assertEqual("block", out["decision"])
        self.assertIn("40 unreconciled obligation(s)", out["reason"])
        self.assertIn("[U12] x40", out["reason"])
        self.assertEqual(1, out["reason"].count(original[0]["reason"]))
        for row in original[:5]:
            self.assertIn(row["subject"], out["reason"])
        for row in original[5:]:
            self.assertNotIn(row["subject"], out["reason"])
        self.assertIn("+35 more", out["reason"])
        self.assertEqual(original, self.ledger.open_demands("reconcile", ""))
        block = [row for row in self.journal() if row["kind"] == "block"][-1]
        self.assertEqual(original, block["rows"])
        self.assertEqual(["U12"] * 40, block["clause_ids"])
        self.assertEqual(40, block["open_count"])

    def test_existing_targets_other_clauses_and_other_agents_still_owe(self):
        present = self.cwd / "present.txt"
        present.write_text("present\n")
        kept = self.demand("U12", present)
        other_clause = self.demand("U20", self.cwd / "absent-other.txt")
        other_agent = self.demand("U13", self.cwd / "absent-child.txt", agent="child")
        retired = self.demand("U19", self.cwd / "absent-main.txt")
        out = self.stop()
        self.assertEqual("block", out["decision"])
        self.assertEqual({kept.id, other_clause.id, retired.id}, self.ledger.open_ids("reconcile", ""))
        self.assertIn("2 unreconciled obligation(s)", out["reason"])
        self.assertNotIn(retired.subject, out["reason"])
        self.assertEqual({other_agent.id}, self.ledger.open_ids("reconcile", "child"))
        self.assertFalse(self.ledger.is_licensed("reconcile", "", retired.id))
        self.assertEqual(1, len([r for r in self.journal() if r["kind"] == "retired_missing"]))

    def test_uncertain_stat_error_is_not_absence(self):
        target = self.cwd / "unreadable.txt"
        demand = self.demand("U12", target)
        original_stat = Path.lstat

        def stat(path, *args, **kwargs):
            if path == target:
                raise PermissionError("cannot determine whether the target exists")
            return original_stat(path, *args, **kwargs)

        with mock.patch.object(Path, "lstat", stat):
            self.assertEqual("block", self.stop()["decision"])
        self.assertEqual({demand.id}, self.ledger.open_ids("reconcile", ""))
        self.assertFalse(any(r["kind"] == "retired_missing" for r in self.journal()))

    def test_ambiguous_relative_and_truncated_subjects_are_not_retired(self):
        relative = self.demand("U12", "relative-with-no-origin.txt")
        truncated = self.demand("U13", (str(self.cwd) + "/" + "x" * 200)[:200])
        self.assertEqual("block", self.stop()["decision"])
        self.assertEqual({relative.id, truncated.id}, self.ledger.open_ids("reconcile", ""))
        self.assertFalse(any(r["kind"] == "retired_missing" for r in self.journal()))

    def test_terminal_retirement_keeps_evidence_and_a_returning_target_still_owes(self):
        target = self.cwd / "gone.txt"
        demand = self.demand("U12", target)
        original = self.ledger.path.read_bytes()
        self.assertEqual({}, self.stop())
        self.assertEqual(original, self.ledger.path.read_bytes())
        self.assertFalse(self.ledger.is_licensed("reconcile", "", demand.id))
        self.assertFalse(self.ledger.demand(demand))  # the same immutable demand is still present
        self.assertEqual({demand.id}, self.ledger.open_ids("reconcile", ""))
        with mock.patch.object(Ledger, "COMPACT_AT", 0):
            self.assertEqual(0, self.ledger.compact("another-session"))
        target.write_text("the path returned\n")
        self.assertEqual("block", self.stop()["decision"])
        self.assertEqual({demand.id}, self.ledger.open_ids("reconcile", ""))
        self.assertIsNone(self.ledger.verify_chain())


class SignatureDatumGuidance(unittest.TestCase):
    def test_u08_guidance_names_the_supported_signature_data(self):
        clause = next(cl for cl in C.load_default() if cl.id == "U08")
        self.assertNotIn("any signer", clause.deny_reason)
        for token in ("PGP", "SSH", "Good signature", "gpgsig"):
            self.assertIn(token, clause.deny_reason)
            self.assertIn(token, clause.guard)
        for output in ("-----BEGIN PGP SIGNATURE-----", "-----BEGIN SSH SIGNATURE-----",
                       "gpg: Good signature from test", "gpgsig signed-commit-data"):
            with self.subTest(output=output):
                self.assertTrue(effects.report_effects(output, "print signature")["report_signature"])
        for output in ("custom signer: signed successfully", "signature verified", ""):
            with self.subTest(output=output):
                self.assertFalse(effects.report_effects(output, "print signature")["report_signature"])


class GuardRecovery(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory(prefix="keel-recovery-")
        self.addCleanup(tmp.cleanup)
        self.cwd = Path(tmp.name) / "plain"
        self.cwd.mkdir()
        self.state = Path(tmp.name) / "state"
        self.ledger = Ledger(self.state)
        self.table = C.load_default()

    def event(self, tool="Bash", command="true", **extra):
        return {"hook_event_name": "PreToolUse", "session_id": "recovery", "agent_id": "",
                "cwd": str(self.cwd), "tool_name": tool,
                "tool_input": {"command": command}, **extra}

    def pre(self, event=None):
        return dispatch.pre_tool_use(self.table, self.ledger, event or self.event())

    def owed(self):
        return {row["clause_id"] for row in self.ledger.open_demands("recovery", "")}

    def read(self, name):
        path = self.state / name
        event = self.event("Read", tool_input={"file_path": str(path)})
        self.assertEqual({}, self.pre(event))
        event.update(hook_event_name="PostToolUse", tool_response=path.read_text())
        dispatch.post_tool_use(self.table, self.ledger, event)
        return event["keel_effect"]

    def test_non_git_remote_read_discharges_first_bash_a03_demand(self):
        self.assertIsNone(effects._repo_root(str(self.cwd)))
        denied = self.pre()
        self.assertEqual("deny", denied["hookSpecificOutput"]["permissionDecision"])
        self.assertEqual({"A01", "A02", "A03"}, self.owed())
        remote = json.loads((self.state / effects.REMOTE).read_text())
        self.assertIsNone(remote["root"])
        self.assertEqual({}, remote["tips"])
        self.assertIs(remote["checked"], True)
        self.assertIsInstance(remote["t"], (float, int))
        self.assertTrue(self.read(effects.REMOTE)["remote_read"])
        self.assertEqual({"A01", "A02"}, self.owed())

    def test_non_git_observed_read_discharges_a01_and_a02(self):
        (self.cwd / "payload.txt").write_text("present\n")
        self.pre()
        observed = json.loads((self.state / effects.OBSERVED).read_text())
        self.assertIsNone(observed["head"])
        self.assertIsNone(observed["root"])
        self.assertIn("payload.txt", observed["paths"])
        self.assertTrue(self.read(effects.OBSERVED)["observed_read"])
        self.assertEqual({"A03"}, self.owed())
        self.read(effects.REMOTE)
        self.assertEqual(set(), self.owed())
        self.assertEqual({}, self.pre())

    def test_always_denial_ends_with_commit_hint(self):
        reason = self.pre()["hookSpecificOutput"]["permissionDecisionReason"]
        for clause in ("A01", "A02", "A03"):
            self.assertIn(clause, reason)
        self.assertTrue(reason.endswith(dispatch.COMMIT_HINT), reason)

    def test_first_call_records_all_commitments_and_unpaid_effect_blocks_next_act(self):
        event = self.event(command="# keel-guard: A01, A02, A03\ntrue")
        self.assertEqual(set(), self.owed())
        self.assertEqual({}, self.pre(event))
        self.assertEqual({"A01", "A02", "A03"}, self.owed())
        subprocess.run(["bash", "-c", event["tool_input"]["command"]],
                       cwd=self.cwd, check=True)
        # Isolate the committed clauses from unrelated post-act demands.
        table = [cl for cl in self.table if cl.id in self.owed()]
        with mock.patch.object(dispatch.journal, "note_fault") as fault:
            dispatch.post_tool_use(table, self.ledger, {
                **event, "hook_event_name": "PostToolUse", "tool_response": {"stdout": ""}})
        fault.assert_called_once()
        self.assertEqual(("broken_commitment", "A01,A02,A03"), fault.call_args.args[1:3])
        self.assertEqual({"A01", "A02", "A03"}, self.owed())
        denied = self.pre()["hookSpecificOutput"]
        self.assertEqual("deny", denied["permissionDecision"])
        for clause in ("A01", "A02", "A03"):
            self.assertIn(clause, denied["permissionDecisionReason"])

    def test_lowercase_a03_matches_uppercase_for_first_and_existing_demands(self):
        self.table = [cl for cl in self.table if cl.id == "A03"]
        for marker in ("A03", "a03"):
            with self.subTest(marker=marker):
                self.ledger = Ledger(self.state / marker)
                event = self.event(command=f"# keel-guard: {marker}\ntrue", keel_effect=record())
                self.assertEqual({}, self.pre(event))
                self.assertEqual({"A03"}, self.owed())
                with mock.patch.object(dispatch.journal, "note_fault") as fault:
                    dispatch.post_tool_use(self.table, self.ledger, {
                        **event, "hook_event_name": "PostToolUse"})
                self.assertEqual(("broken_commitment", "A03"), fault.call_args.args[1:3])
                self.assertEqual("deny", self.pre()["hookSpecificOutput"]["permissionDecision"])
                self.assertEqual({}, self.pre(event))
                dispatch.post_tool_use(self.table, self.ledger, {
                    **event, "hook_event_name": "PostToolUse", "keel_effect": record(remote_read=True)})
                self.assertEqual(set(), self.owed())
                self.assertEqual({}, self.pre())

    def test_bash_scoped_clause_gates_powershell_identically(self):
        self.table = [cl for cl in self.table if cl.id == "A03"]
        self.assertEqual(["Bash"], self.table[0].tools)
        decisions = []
        for tool in ("Bash", "PowerShell"):
            with self.subTest(tool=tool):
                self.ledger = Ledger(self.state / tool)
                decisions.append(self.pre(self.event(tool, keel_effect=record())))
                self.assertEqual({"A03"}, self.owed())
        self.assertEqual(decisions[0], decisions[1])
        self.assertEqual("deny", decisions[1]["hookSpecificOutput"]["permissionDecision"])

    def test_no_repo_remote_still_requires_shape_path_and_successful_read(self):
        self.pre()
        path = self.state / effects.REMOTE
        good = json.loads(path.read_text())
        event = self.event("Read", tool_input={"file_path": str(path)}, tool_response="ok")
        for bad in ({**good, "tips": None}, {**good, "tips": []},
                    {**good, "checked": False}, {"tips": {}}, []):
            with self.subTest(doc=bad):
                path.write_text(json.dumps(bad))
                self.assertFalse(effects.read_delta(self.state, event)["remote_read"])
        path.write_text(json.dumps(good))
        self.assertTrue(effects.read_delta(self.state, event)["remote_read"])
        alias = self.state / "alias.json"
        alias.symlink_to(path)
        self.assertTrue(effects.read_delta(self.state, {
            **event, "tool_input": {"file_path": str(alias)}})["remote_read"])
        other = self.state / "other.json"
        other.write_text(path.read_text())
        self.assertFalse(effects.read_delta(self.state, {
            **event, "tool_input": {"file_path": str(other)}})["remote_read"])
        self.assertFalse(effects.read_delta(self.state, {
            **event, "tool_response": {"error": "read failed"}})["remote_read"])

    def test_remote_scope_and_cache_survive_leaving_and_reentering_git(self):
        repo = self.cwd.parent / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
        event = self.event("Read", tool_input={"file_path": str(self.state / effects.REMOTE)})
        effects.snapshot(self.state, "recovery", "", str(repo))
        self.assertFalse(effects.read_delta(self.state, event)["remote_read"])
        effects.snapshot(self.state, "recovery", "", str(self.cwd))
        self.assertTrue(effects.read_delta(self.state, event)["remote_read"])
        repo_read = {**event, "cwd": str(repo)}
        self.assertFalse(effects.read_delta(self.state, repo_read)["remote_read"])
        effects.snapshot(self.state, "recovery", "", str(repo))
        self.assertTrue(effects.read_delta(self.state, repo_read)["remote_read"])
        self.assertEqual(str(repo), json.loads((self.state / effects.REMOTE).read_text())["root"])

    def test_first_lowercase_commitment_is_checked_and_unpaid_debt_blocks_next_act(self):
        self.table = [cl for cl in self.table if cl.id in {"A01", "A02", "A03"}]
        event = self.event(command="# keel-guard: a01\ntrue")
        self.assertEqual(set(), self.owed())
        self.assertEqual({}, self.pre(event))
        self.assertEqual({"A01"}, self.owed())
        subprocess.run(["bash", "-c", event["tool_input"]["command"]], cwd=self.cwd, check=True)
        post = {**event, "hook_event_name": "PostToolUse", "tool_response": {"stdout": ""}}
        with mock.patch.object(dispatch.journal, "note_fault") as fault:
            dispatch.post_tool_use(self.table, self.ledger, post)
        self.assertTrue(any(call.args[1:3] == ("broken_commitment", "A01")
                            for call in fault.call_args_list))
        self.assertIn("A01", self.owed())
        self.assertEqual("deny", self.pre()["hookSpecificOutput"]["permissionDecision"])
        # The same lowercase marker also works once debt already exists.
        self.assertEqual({}, self.pre(self.event(command="# keel-guard: a01\ntrue")))
        self.read(effects.OBSERVED)
        self.read(effects.REMOTE)
        self.assertEqual({}, self.pre())

    def test_a_first_commitment_paid_by_its_real_effect_leaves_no_debt(self):
        # A report-shaped guard can actually be paid by a shell act. Keep the shipped
        # always occasion, but use this guard to exercise the successful commitment path.
        cl = replace(self.table[0], id="X01-Mixed-Case",
                     discharged_by={"kind": "effect", "effect": "report_structured"})
        self.table = [cl]
        event = self.event(command="# keel-guard: x01-mixed-case\nprintf '{\"ok\": true}'")
        self.assertEqual({}, self.pre(event))
        self.assertEqual({cl.id}, self.owed())
        done = subprocess.run(["bash", "-c", event["tool_input"]["command"]],
                              cwd=self.cwd, check=True, capture_output=True, text=True)
        with mock.patch.object(dispatch.journal, "note_fault") as fault:
            dispatch.post_tool_use(self.table, self.ledger, {
                **event, "hook_event_name": "PostToolUse", "tool_response": {"stdout": done.stdout}})
        fault.assert_not_called()
        self.assertEqual(set(), self.owed())
        self.assertEqual({}, self.pre())

    def test_mixed_case_clause_id_is_checked_when_existing_commitment_is_broken(self):
        self.table = [replace(self.table[0], id="X01-Mixed-Case")]
        self.assertTrue(self.pre())
        event = self.event(command="# keel-guard: x01-MIXED-case\ntrue", keel_effect=record())
        self.assertEqual({}, self.pre(event))
        with mock.patch.object(dispatch.journal, "note_fault") as fault:
            dispatch.post_tool_use(self.table, self.ledger, {
                **event, "hook_event_name": "PostToolUse"})
        self.assertEqual("X01-MIXED-CASE", fault.call_args.args[2])
        self.assertEqual({"X01-Mixed-Case"}, self.owed())

    def test_unknown_and_payload_markers_cannot_admit_the_first_call(self):
        for index, command in enumerate(("# keel-guard: z99\ntrue", "true\n# keel-guard: a01",
                                         "cat <<'EOF'\n# keel-guard: a01\nEOF")):
            with self.subTest(command=command):
                self.assertEqual("deny", self.pre(self.event(command=command, session_id=str(index)))[
                    "hookSpecificOutput"]["permissionDecision"])


class ShellToolCoverage(unittest.TestCase):
    def test_hook_manifest_matchers_do_not_drift(self):
        matchers = []
        for name in ("hooks.json", "hooks.codex.json"):
            hooks = json.loads((PLUGIN / "hooks" / name).read_text())["hooks"]
            normalized = {}
            for moment, rows in hooks.items():
                normalized[moment] = []
                for row in rows:
                    matcher = row.get("matcher", "")
                    # Codex anchors the same alternation that Claude matches directly.
                    if matcher.startswith("^(") and matcher.endswith(")$"):
                        matcher = matcher[2:-2]
                    normalized[moment].append(tuple(sorted(matcher.split("|"))))
                normalized[moment].sort()
            matchers.append(normalized)
        self.assertEqual(matchers[0], matchers[1])

    def test_both_manifests_observe_both_moments_for_confirmed_shell_tools(self):
        self.assertEqual({"Bash", "PowerShell"}, dispatch.SHELL_TOOLS)
        for name in ("hooks.json", "hooks.codex.json"):
            hooks = json.loads((PLUGIN / "hooks" / name).read_text())["hooks"]
            for moment in ("PreToolUse", "PostToolUse"):
                for tool in dispatch.SHELL_TOOLS:
                    with self.subTest(manifest=name, moment=moment, tool=tool):
                        self.assertTrue(any(re.fullmatch(row["matcher"], tool)
                                            for row in hooks[moment]))

    def test_exact_bash_scopes_cover_powershell_without_changing_other_scopes(self):
        rows = C.load_default()
        shells = [cl for cl in rows if cl.tools == ["Bash"]]
        self.assertTrue(shells)
        for cl in rows:
            for tool in ("Bash", "PowerShell", "Read", "Grep", "Glob", "Agent", "Task",
                         "ExitPlanMode", "AskUserQuestion", "cmd", "UnknownShell"):
                with self.subTest(clause=cl.id, tool=tool):
                    expected = (tool in {"Bash", "PowerShell"} if cl.tools == ["Bash"]
                                else not cl.tools or cl.tools == ["*"] or tool in cl.tools)
                    self.assertEqual(expected, dispatch._applies(cl, {
                        "hook_event_name": cl.event, "tool_name": tool}))

    def test_powershell_is_denied_then_recovers_through_artifact_reads(self):
        with tempfile.TemporaryDirectory(prefix="keel-powershell-") as tmp:
            state = Path(tmp) / "state"
            cwd = Path(tmp) / "plain"
            cwd.mkdir()
            env = {**os.environ, "KEEL_STATE_DIR": str(state),
                   "CLAUDE_PLUGIN_ROOT": str(PLUGIN)}

            def send(moment, tool, tool_input, **extra):
                event = {"hook_event_name": moment, "tool_name": tool, "tool_input": tool_input,
                         "session_id": "powershell", "cwd": str(cwd), **extra}
                done = subprocess.run(["bash", str(PLUGIN / "hooks" / "dispatch.sh")],
                                      input=json.dumps(event), capture_output=True, text=True,
                                      check=True, env=env)
                return json.loads(done.stdout)

            command = {"command": "Get-ChildItem"}
            denied = send("PreToolUse", "PowerShell", command)
            reason = denied["hookSpecificOutput"]["permissionDecisionReason"]
            for clause in ("A01", "A02", "A03"):
                self.assertIn(clause, reason)
            for name in (effects.OBSERVED, effects.REMOTE):
                path = state / name
                self.assertEqual({}, send("PreToolUse", "Read", {"file_path": str(path)}))
                send("PostToolUse", "Read", {"file_path": str(path)}, tool_response=path.read_text())
            self.assertEqual({}, send("PreToolUse", "PowerShell", command))
            # A recorded PowerShell rewrite is observed by the same after-act fence.
            send("PostToolUse", "PowerShell", command,
                 keel_effect=record(files_changed=["config.txt"]))
            self.assertIn("U19", str(send("PreToolUse", "PowerShell", command)))
