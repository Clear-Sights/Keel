"""A waiver parks one clause; the WAIVER is what dies by default, never the clause.

C08 forced this. Its guard asks to observe a nonzero PostToolUse result, and this host sends no
exit status in any form -- measured over 71 recorded Bash PostToolUse payloads, whose
tool_response is a dict keyed (stdout, stderr, interrupted, isImage, noOutputExpected). So the
clause could be demanded and never discharged: 114 demand rows in one session, 0 discharges ever,
every Stop blocked. The end state of that is the whole gate being switched off, which costs all
24 clauses at once -- strictly worse than parking one.

The danger in any waiver is that it becomes a silent, permanent hole. Three properties stop that,
and each has a test below:

  * it LAPSES BY ITSELF. `until` is a plain date; the day after, the clause enforces again with
    no edit and no renewal. Doing nothing restores the check rather than retiring it.
  * an UNREADABLE waiver is already dead. Missing, non-string or unparseable `until` reads as
    expired, so a typo cannot buy silence.
  * it is NEVER SILENT. Stop announces a parked clause every ending, and announces an expired one
    loudly as it starts enforcing again.

The clause itself stays in the table -- loaded, admitted, fixture-checked -- so a waiver hides no
drift in the row it parks.

THE OTHER WAY ENFORCEMENT IS PARKED lives at the bottom of this module. A waiver parks one clause
for a dated interval; the `keel-allow:` marker parks ALL twenty-four for one call. It is the more
dangerous of the two by a wide margin and, until this class, it had no test at all -- which is how
it twice grew a hole big enough for a command to exempt itself.
"""

from __future__ import annotations

import contextlib
import dataclasses
import io
import os
import pathlib
import tempfile
import unittest
from datetime import date

from tests.plant_support import PLUGIN, smoke_replace

from keel import clauses as C, dispatch
from keel import ledger as ledger_module
from keel.ledger import Ledger

PRE = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "session_id": "w", "agent_id": "",
       "tool_input": {"command": "python3 -m pytest -q tests/"}}
STOP = {"hook_event_name": "Stop", "session_id": "w", "agent_id": ""}


def waived_clause() -> C.Clause:
    for clause in C.load_default():
        if clause.id.startswith("C08"):
            return clause
    raise AssertionError("C08 is not in the shipped clause table")


def drive(clause: C.Clause):
    """One PreToolUse then one Stop. Returns (decision, open row count, stderr)."""
    with tempfile.TemporaryDirectory() as state:
        ledger = Ledger(state)
        dispatch.pre_tool_use([clause], ledger, PRE)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            out = dispatch.reconcile([clause], ledger, STOP)
        return out.get("decision"), len(list(ledger.open_demands("w", ""))), err.getvalue()


class WaiverIsDefaultDead(unittest.TestCase):
    def test_TEETH_a_live_waiver_parks_the_clause(self) -> None:
        decision, rows, err = drive(waived_clause())
        self.assertIsNone(decision, "a parked clause must not block the ending")
        self.assertEqual(0, rows, "a parked clause must accrue no rows nothing can discharge")
        self.assertIn("PARKED", err, "a parked clause the operator cannot see is a silent hole")

    def test_TEETH_an_expired_waiver_enforces_again_by_itself(self) -> None:
        """The whole point: no edit, no renewal, and the check comes back."""
        stale = dataclasses.replace(waived_clause(),
                                    waiver={"until": "2020-01-01", "because": "long gone"})
        decision, rows, err = drive(stale)
        self.assertEqual("block", decision, "an expired waiver must not keep parking the clause")
        self.assertEqual(1, rows)
        self.assertIn("EXPIRED", err, "an expired waiver must never lapse quietly")

    def test_TEETH_an_unreadable_waiver_is_already_dead(self) -> None:
        for spelling in ({}, {"until": "soon"}, {"until": 20261120}, {"until": None}):
            with self.subTest(waiver=spelling):
                clause = dataclasses.replace(waived_clause(), waiver=spelling)
                self.assertEqual("expired", C.waiver_status(clause),
                                 "a waiver nobody can read must not buy silence")

    def test_TEETH_the_boundary_day_is_still_live(self) -> None:
        clause = waived_clause()
        until = date.fromisoformat(clause.waiver["until"])
        self.assertEqual("live", C.waiver_status(clause, until), "the last day is still covered")
        self.assertEqual("expired", C.waiver_status(clause, until.replace(day=until.day + 1)))

    def test_TEETH_the_parked_clause_is_still_in_the_table(self) -> None:
        """Parking enforcement is not deleting the row: it stays loaded and admitted."""
        table = C.load_default()
        self.assertEqual(24, len(table))
        self.assertIn("C08-check-can-fail", [c.id for c in table])

    def test_TEETH_a_clause_without_a_waiver_is_untouched(self) -> None:
        for clause in C.load_default():
            if not clause.id.startswith("C08"):
                with self.subTest(clause=clause.id):
                    self.assertEqual("none", C.waiver_status(clause))

    def test_the_check_can_fail(self) -> None:
        """Both directions come from the SAME driver, so neither assertion can be vacuous.

        If `waiver_status` were stubbed to one answer, or if dispatch ignored it, one of these two
        would go red -- they demand opposite outcomes from identical input.
        """
        live = drive(waived_clause())
        stale = drive(dataclasses.replace(waived_clause(),
                                          waiver={"until": "2020-01-01", "because": "x"}))
        self.assertNotEqual(live[0], stale[0], "the waiver date changed nothing about the verdict")
        self.assertNotEqual(live[1], stale[1], "the waiver date changed nothing about the ledger")


if __name__ == "__main__":
    unittest.main()


class TheAllowMarkerIsAHeaderNotAPayload(unittest.TestCase):
    """The bypass an author types, never one the command can supply for itself.

    `keel-allow:` parks every clause for one call, so where it is allowed to appear IS its whole
    security, and it has been narrowed twice for the same reason both times. First it was searched
    for anywhere in the serialized `tool_input`, so a Write whose CONTENT quoted the documentation
    turned the fence off. Then it was searched for anywhere in the command string, which is the
    same hole with one more step: a command that can write a file can carry its own licence in the
    payload it writes.

        rm -rf build/                                     deny
        rm -rf build/ ; cat > n.md <<'EOF'
        keel-allow: whatever
        EOF                                               {}  -- all 24 clauses skipped

    The scan now stops at the first line that is not blank and not a comment, so a heredoc body, a
    quoted string and an appended segment are all past the point where reading stopped. Both
    directions are asserted here: the exemption must still work when it is a header, and must not
    work anywhere else. A test that only proved the bypass was refused would be satisfied by a
    marker that never works at all.
    """

    @staticmethod
    def _event(command: str) -> dict:
        return {"hook_event_name": "PreToolUse", "tool_name": "Bash", "session_id": "am",
                "agent_id": "", "tool_input": {"command": command}}

    def _decision(self, command: str) -> dict:
        return dispatch.pre_tool_use(C.load_default(), Ledger(), self._event(command))

    def test_TEETH_a_header_comment_exempts_the_call(self) -> None:
        self.assertEqual({}, self._decision("# keel-allow: approved by the owner\nrm -rf build/"))

    def test_TEETH_a_marker_in_a_heredoc_body_does_not(self) -> None:
        # Comment-shaped, so the ONLY thing refusing it is that it sits after command text. The
        # bare-marker case below covers the other half separately; a test that both forms have to
        # fail cannot say which rule is holding the line.
        decision = self._decision(
            "rm -rf build/ ; cat > n.md <<'EOF'\n# keel-allow: whatever\nEOF")
        self.assertIn("A02", str(decision), f"the heredoc body exempted the call: {decision}")

    def test_TEETH_the_measured_bypass_stays_closed(self) -> None:
        # Verbatim the shape that was measured returning {} with all 24 clauses skipped.
        decision = self._decision(
            "rm -rf build/ ; cat > n.md <<'EOF'\nkeel-allow: whatever\nEOF")
        self.assertIn("A02", str(decision), f"the measured bypass is open again: {decision}")

    def test_TEETH_an_uncommented_first_line_is_not_a_marker(self) -> None:
        # The header rule alone would stop reading here and refuse anyway; the `#` requirement is
        # what makes a marker something an author WROTE as a comment rather than something a
        # command happened to print. `//` and `--` are gone with it: the field is a shell command.
        for first in ("keel-allow: bare", "// keel-allow: c-style", "-- keel-allow: sql-style"):
            with self.subTest(first=first):
                decision = self._decision(f"{first}\nrm -rf build/")
                self.assertIn("A02", str(decision),
                              f"{first!r} exempted the call: {decision}")

    def test_TEETH_a_trailing_comment_on_the_command_does_not(self) -> None:
        decision = self._decision("rm -rf build/ # keel-allow: sneaky")
        self.assertIn("A02", str(decision), f"a trailing comment exempted the call: {decision}")

    def test_TEETH_a_marker_below_the_command_does_not(self) -> None:
        # The line IS a comment and IS its own line -- the old rule's whole test -- but it comes
        # after command text, which is the only thing that distinguishes it from a header.
        decision = self._decision("rm -rf build/\n# keel-allow: after the fact")
        self.assertIn("A02", str(decision), f"a marker below the command exempted it: {decision}")

    def test_TEETH_a_marker_with_no_reason_is_not_a_marker(self) -> None:
        decision = self._decision("# keel-allow:\nrm -rf build/")
        self.assertIn("A02", str(decision), f"a reasonless marker exempted the call: {decision}")

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red; a checker that cannot follow an imported helper reads this body as empty
        # The seam is the one line that decides a header from a payload. Widen it back to a
        # whole-string search and the heredoc walks straight through.
        smoke_replace(self, PLUGIN / "keel" / "dispatch.py",
                      b'        if not stripped.startswith("#"):\n'
                      b'            # Command text. Everything from here on is payload, not preamble.\n'
                      b"            return None\n",
                      b"", "tests.test_waiver.TheAllowMarkerIsAHeaderNotAPayload."
                      "test_TEETH_a_marker_in_a_heredoc_body_does_not",
                      "the heredoc body exempted the call")


class TheRenameOwesTheOldNameASentence(unittest.TestCase):
    """A hard rename may strand a user; it may not strand them quietly.

    Renaming to `keel` broke two things that were already on people's machines, and broke both
    without a word. `GYROSCOPE_STATE_DIR` stopped being read, so a session that still set it began
    from an empty ledger and looked clean. `gyroscope-allow:` stopped parsing, so every exemption
    already written became an ordinary command and got denied with no hint that a rename was the
    cause. Both are asserted here in both directions -- the notice must appear when there is
    something to say, and must NOT appear when there is not, because a warning that is always on
    is a warning nobody reads.
    """

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.root = pathlib.Path(self._temp.name)
        for name in ("KEEL_STATE_DIR", "GYROSCOPE_STATE_DIR"):
            previous = os.environ.get(name)
            self.addCleanup(
                lambda n=name, p=previous: os.environ.pop(n, None)
                if p is None else os.environ.__setitem__(n, p))
            os.environ.pop(name, None)
        os.environ["KEEL_STATE_DIR"] = str(self.root / "keel_state")

    def _start(self) -> dict:
        return dispatch.session_start(C.load_default(), Ledger(),
                                      {"hook_event_name": "SessionStart", "session_id": "r"})

    def test_TEETH_the_old_variable_being_ignored_is_announced(self) -> None:
        os.environ["GYROSCOPE_STATE_DIR"] = str(self.root / "gyroscope_state")
        out = self._start()
        self.assertIn("systemMessage", out, "the old variable was ignored silently")
        self.assertIn("gyroscope_state", out["systemMessage"])
        self.assertIn("gyroscope_state", out["hookSpecificOutput"]["additionalContext"])

    def test_TEETH_a_legacy_directory_beside_the_new_one_is_announced(self) -> None:
        (self.root / "gyroscope_state").mkdir()
        out = self._start()
        self.assertIn("systemMessage", out, "the legacy directory was passed over silently")

    def test_TEETH_a_session_with_nothing_stranded_says_nothing(self) -> None:
        out = self._start()
        self.assertNotIn("systemMessage", out, "a notice fired with nothing to report")
        self.assertTrue(
            out["hookSpecificOutput"]["additionalContext"].startswith("keel active,"),
            out["hookSpecificOutput"]["additionalContext"][:80])

    def test_TEETH_a_written_store_makes_the_old_directory_history(self) -> None:
        # Once keel has a LEDGER of its own the old directory is not a surprise, and saying so
        # every session would be the always-on warning this class exists to avoid. The ledger
        # FILE, not the directory: `Ledger.__init__` creates the directory before any handler
        # runs, so a directory check reports nothing, ever.
        (self.root / "gyroscope_state").mkdir()
        (self.root / "keel_state").mkdir()
        (self.root / "keel_state" / ledger_module.LEDGER_FILE).write_text("{}\n")
        self.assertNotIn("systemMessage", self._start())

    def test_TEETH_the_pre_rename_marker_still_exempts_and_says_so(self) -> None:
        event = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "session_id": "r",
                 "agent_id": "", "tool_input": {"command": "# gyroscope-allow: approved\nrm -rf b/"}}
        out = dispatch.pre_tool_use(C.load_default(), Ledger(), event)
        self.assertNotIn("hookSpecificOutput", out, f"the old spelling was denied: {out}")
        self.assertIn("pre-rename", out.get("systemMessage", ""),
                      f"the old spelling worked but said nothing: {out}")

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red; a checker that cannot follow an imported helper reads this body as empty
        smoke_replace(self, PLUGIN / "keel" / "ledger.py",
                      b'    env = os.environ.get(LEGACY_STATE_ENV)\n    if env:\n'
                      b"        return pathlib.Path(env)\n",
                      b"", "tests.test_waiver.TheRenameOwesTheOldNameASentence."
                      "test_TEETH_the_old_variable_being_ignored_is_announced",
                      "the old variable was ignored silently")
