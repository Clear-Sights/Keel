"""The probe `U01` and `U02` deny against must exist, run, and be able to refuse.

WHY THIS EXISTS. `U01` and `U02` shipped for the whole life of this plugin discharging only on

    python3 tools/probe_child_capability.py ...

and that file did not exist -- not here, not in the development repository, not at any commit in
either history. Firing either clause denied a nested-worker launch and handed the operator a command
that could not run. The remedy was unrunnable, so the only ways out were abandoning the work or
switching the gate off, and an operator who hits that once learns the gate lies.

The tool is written rather than the clauses withdrawn, because the occasion is real: a nested worker
that cannot write its home, cannot return a response, or cannot leave a result behind fails after
the expensive part, and the parent inherits an empty success.

WHAT IS OBSERVED HERE, and how. Every probe is driven as a subprocess, the way a discharging
operator drives it, and each is required to go RED on a real fault before its green is trusted:

  writable-home     HOME under a path that is not a directory. Chosen because it beats root --
                    the first attempt at this used `chmod 500` and PASSED, correctly, since root
                    bypasses permission bits. The check was right and the fault injection was
                    wrong, which is why the fault here is ENOTDIR rather than a mode.
  require-change    the same target twice, and an unusable record store.
  spawn failures    response-transport and result-write are driven through a stubbed `_spawn`,
                    stated plainly rather than dressed up: this host CAN spawn children, so their
                    failure branch cannot be reached by a real host fault here. The branch is
                    executed; the host condition is not reproduced.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from tests.plant_support import PLUGIN, REPO, smoke_replace

PROBE = PLUGIN / "tools" / "probe_child_capability.py"

sys.path.insert(0, str(PLUGIN))
import tools.probe_child_capability as probe_module  # noqa: E402


def run(*argv: str, home: str | None = None, state: str | None = None):
    environment = {"PATH": "/usr/bin:/bin", "KEEL_STATE_DIR": state or "/tmp/keel-probe-test"}
    if home is not None:
        environment["HOME"] = home
    return subprocess.run([sys.executable, str(PROBE), *argv],
                          capture_output=True, text=True, env=environment)


class TheProbeExists(unittest.TestCase):
    def test_the_file_the_clauses_name_is_shipped(self) -> None:
        """The whole defect in one assertion: the discharge named a file nobody had written."""
        self.assertTrue(PROBE.is_file(), f"{PROBE} is what U01 and U02 discharge on")

    def test_it_ships_inside_the_plugin(self) -> None:
        """It must install with the plugin, not sit in the development tree only.

        `plugin/` is exactly what the marketplace installs, which is why `tests/` lives outside it.
        A probe kept anywhere else would be unrunnable for every installing user -- the same defect
        in a new location.
        """
        # NOT `PROBE.parent.parent == PLUGIN`. PROBE is DEFINED as
        # `PLUGIN / "tools" / "probe_child_capability.py"`, so that equality is arithmetic on a
        # path this module built, true whatever is or is not on disk -- it would pass with the
        # probe deleted, or moved, or never written. The claim is that the file SHIPS: it exists,
        # inside the subtree the marketplace installs, and not in the development tree beside it.
        installed = REPO / "plugin"
        self.assertTrue((installed / ".claude-plugin" / "plugin.json").is_file(),
                        f"{installed} is not the installed plugin subtree, so locating the probe "
                        f"inside it proves nothing")
        found = sorted(installed.rglob("probe_child_capability.py"))
        self.assertEqual(
            [PROBE], found,
            f"the probe is not where the plugin installs it. Found {found}; expected exactly "
            f"{PROBE}. A probe kept outside `plugin/` is unrunnable for every installing user.")
        self.assertEqual(
            [], sorted((REPO / "tests").rglob("probe_child_capability.py")),
            "a copy of the probe lives under tests/, which is not installed; the shipped one is "
            "then not the one being exercised")


class TheProbeRuns(unittest.TestCase):
    def test_the_three_capability_arms_pass_on_a_working_host(self) -> None:
        done = run("--writable-home", "--response-transport", "--result-write")
        self.assertEqual(0, done.returncode, done.stdout + done.stderr)
        self.assertEqual(3, done.stdout.count("=PASS"), done.stdout)

    def test_naming_no_capability_is_refused_rather_than_passed(self) -> None:
        """A probe invoked with nothing to probe must not report success.

        This is the shape that would let the discharge be satisfied by a command that measures
        nothing, which is the hole the clause exists to close.
        """
        self.assertNotEqual(0, run().returncode)

    def test_require_change_needs_its_subject(self) -> None:
        self.assertNotEqual(0, run("--require-change", "--after-failure").returncode)


class EveryGuardIsRunnable(unittest.TestCase):
    """Generalised from the defect, so the next one fails here instead of in a user's session.

    `U01` and `U02` were found by reading. Two mechanical properties would have caught them on the
    day they landed, and neither existed:

      (a) a file a guard tells the operator to run must be shipped;
      (b) the command a guard tells the operator to run must satisfy that clause's OWN discharge
          pattern -- otherwise the operator obeys the instruction exactly and is denied again.

    (b) is the sharper one. A guard and its `discharged_by` are written at different times by
    different hands, and nothing compared them: the instruction could drift from the pattern and the
    only symptom would be a user following directions and getting refused, with no way to tell
    whether they had typed it wrong.
    """

    @staticmethod
    def _clauses():
        return json.loads((PLUGIN / "keel" / "clauses.json").read_text(encoding="utf-8"))

    def test_every_file_a_guard_names_is_shipped(self) -> None:
        missing = []
        for row in self._clauses():
            text = " ".join(str(row.get(k, "")) for k in ("guard", "deny_reason"))
            for name in re.findall(r"[\w./$${}-]+\.(?:py|sh)\b", text):
                relative = name.replace("$CLAUDE_PLUGIN_ROOT/", "").replace('"', "")
                if not (PLUGIN / relative).exists():
                    missing.append(f"{row['id']} -> {name}")
        self.assertEqual([], sorted(missing),
                         "a guard tells the operator to run a file this plugin does not ship, so "
                         "firing it denies the act with no remedy that can be run")

    def test_every_guard_satisfies_its_own_discharge(self) -> None:
        """Obeying the instruction literally must clear the clause that gave it."""
        unsatisfied = []
        for row in self._clauses():
            discharge = row.get("discharged_by") or {}
            if discharge.get("kind") != "regex" or discharge.get("on") != "tool_input.command":
                continue
            quoted = re.findall(r"`([^`]+)`", row.get("guard", ""))
            if not quoted:
                continue
            if not any(re.search(discharge["pattern"], command) for command in quoted):
                unsatisfied.append(f"{row['id']}: {quoted} vs /{discharge['pattern']}/")
        self.assertEqual([], sorted(unsatisfied),
                         "a clause's guard names a command that does not satisfy that clause's own "
                         "discharge pattern; an operator obeying it exactly is denied again")

    def test_the_check_has_a_subject(self) -> None:
        """Report an empty subject rather than passing over one."""
        commands = [r for r in self._clauses()
                    if (r.get("discharged_by") or {}).get("on") == "tool_input.command"
                    and re.findall(r"`([^`]+)`", r.get("guard", ""))]
        self.assertTrue(commands, "no clause pairs a quoted guard command with a command discharge")


class TheProbeCanRefuse(unittest.TestCase):
    """Each arm seen RED on a fault, because a probe that has only ever passed is a claim."""

    def test_writable_home_refuses_a_home_it_cannot_write(self) -> None:
        done = run("--writable-home", home="/etc/hostname/nope")
        self.assertEqual(1, done.returncode, done.stdout)
        self.assertIn("writable-home=FAIL", done.stdout)

    def test_one_failing_arm_does_not_skip_the_others(self) -> None:
        """A single run names every missing capability, not the first one."""
        done = run("--writable-home", "--response-transport", "--result-write",
                   home="/etc/hostname/nope")
        self.assertEqual(1, done.returncode, done.stdout)
        self.assertIn("writable-home=FAIL", done.stdout)
        self.assertEqual(2, done.stdout.count("=PASS"), done.stdout)

    def test_require_change_refuses_an_unchanged_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            brief = Path(directory) / "brief.txt"
            brief.write_text("one draft", encoding="utf-8")
            state = str(Path(directory) / "state")
            first = run("--target", str(brief), "--after-failure", "--require-change", state=state)
            self.assertEqual(0, first.returncode, first.stdout)
            self.assertIn("no prior failure recorded", first.stdout)

            again = run("--target", str(brief), "--after-failure", "--require-change", state=state)
            self.assertEqual(1, again.returncode, again.stdout)
            self.assertIn("unchanged since the failed attempt", again.stdout)

            brief.write_text("a different draft", encoding="utf-8")
            changed = run("--target", str(brief), "--after-failure", "--require-change", state=state)
            self.assertEqual(0, changed.returncode, changed.stdout)
            self.assertIn("changed since the failed attempt", changed.stdout)

    def test_require_change_refuses_an_unusable_record_store(self) -> None:
        done = run("--target", "/tmp/x", "--after-failure", "--require-change",
                   state="/etc/hostname/nope")
        self.assertEqual(1, done.returncode, done.stdout)
        self.assertIn("not usable", done.stdout)

    def test_the_spawning_arms_refuse_when_a_child_cannot_be_spawned(self) -> None:
        """Branch executed through a stub; the host condition is not reproduced. See the docstring."""
        with unittest.mock.patch.object(probe_module, "_spawn", side_effect=OSError("no fork")):
            for arm in (probe_module.probe_response_transport, probe_module.probe_result_write):
                ok, detail = arm()
                self.assertFalse(ok, arm.__name__)
                self.assertIn("could not be spawned", detail)

    def test_the_spawning_arms_refuse_a_child_that_returns_nothing(self) -> None:
        silent = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with unittest.mock.patch.object(probe_module, "_spawn", return_value=silent):
            ok, detail = probe_module.probe_response_transport()
            self.assertFalse(ok)
            self.assertIn("did not reach this process", detail)
            ok, detail = probe_module.probe_result_write()
            self.assertFalse(ok)
            self.assertIn("wrote no file", detail)

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red
        """Report the failed write as a success, and the arm stops being able to refuse.

        The first plant tried here neutered the write-back comparison, and the target stayed GREEN
        -- correctly, because that test reaches its red through the OSError arm and never through
        the comparison. The plant was aimed at a seam its target does not exercise, which is the
        inert-plant failure this family exists to catch, caught on itself. The seam below is the one
        that test does run: a probe that swallows the error and calls the write a success is the
        exact defect the whole file was written against.
        """
        smoke_replace(
            self, PROBE,
            b'        return False, f"home is not writable: {error}"',
            b'        return True, f"home is not writable: {error}"',
            "tests.test_probe_child_capability.TheProbeCanRefuse."
            "test_writable_home_refuses_a_home_it_cannot_write",
            # What the RED says, not what the green one does: with the fault planted the probe
            # prints PASS beside the errno that proves the write never happened, and that pairing
            # is the defect's signature.
            "writable-home=PASS home is not writable",
        )


if __name__ == "__main__":
    unittest.main()
