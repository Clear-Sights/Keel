"""The bypass an author types parks ALL twenty-four clauses for one call.

`keel-allow:` is the one exemption Keel has left. There is no waiver: a clause that cannot be
discharged is a defect in its covering, and the covering is re-aimed or the row withdrawn --
never parked on a date with a paragraph of research. So this marker is the whole of the bypass
surface, and where it is allowed to appear IS its security: it has twice grown a hole big enough
for a command to exempt itself, and each class below is one of those holes kept shut.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import tempfile
import unittest
from unittest import mock

from tests.plant_support import PLUGIN, smoke_replace

from keel import clauses as C, dispatch
from keel import ledger as ledger_module
from keel.ledger import Ledger

PRE = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "session_id": "w", "agent_id": "",
       "tool_input": {"command": "python3 -m pytest -q tests/"}}
STOP = {"hook_event_name": "Stop", "session_id": "w", "agent_id": ""}


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
                      b"            return\n",
                      b"", "tests.test_bypass.TheAllowMarkerIsAHeaderNotAPayload."
                      "test_TEETH_a_marker_in_a_heredoc_body_does_not",
                      "the heredoc body exempted the call")


class TheRenameOwesTheOldNameASentence(unittest.TestCase):
    """A hard rename may strand a user; it may not strand them quietly.

    Renaming to `keel` stopped `GYROSCOPE_STATE_DIR` being read, so a session that still set it
    began from an empty ledger and looked clean. That is a NOTICE, and it stays: saying so costs
    one sentence and is never a way past a clause. Asserted in both directions -- the notice must
    appear when there is something to say, and must NOT appear when there is not, because a
    warning that is always on is a warning nobody reads.

    The rename's other casualty, the `gyroscope-allow:` exemption marker, is NOT handled by a
    notice: an exemption is a way past all 24 clauses, so it is retired outright rather than
    honoured with an apology. See `ThereIsExactlyOneExemptionSpelling`.
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

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red; a checker that cannot follow an imported helper reads this body as empty
        smoke_replace(self, PLUGIN / "keel" / "ledger.py",
                      b'    env = os.environ.get(LEGACY_STATE_ENV)\n    if env:\n'
                      b"        return pathlib.Path(env)\n",
                      b"", "tests.test_bypass.TheRenameOwesTheOldNameASentence."
                      "test_TEETH_the_old_variable_being_ignored_is_announced",
                      "the old variable was ignored silently")


class TheCutGetsItsPreserveListWithoutBeingAsked(unittest.TestCase):
    """A compaction is a report that gets cut, and the cut decides what survives.

    The pages already said so; nothing did anything about it. The preserve list was typed by hand
    into `/compact` every time it was wanted, which is the recurring guard this whole package
    exists to retire -- a guard that works exactly as often as somebody remembers it.

    WHY THIS HANGS OFF `UserPromptSubmit` AND NOT `PreCompact`. `PreCompact` is the obvious home
    and it cannot do the job: its `additionalContext` is documented as explicitly not affecting
    compaction, and its stdout goes to the debug log, so the only lever it holds is blocking.
    `UserPromptSubmit` is one of three events whose output becomes context the model acts on, and
    it sees the raw `/compact` before expansion. The earlier event is the one with the reach.

    Both directions are asserted, and the silences matter more than the speech: this hook fires on
    EVERY prompt, so a line it adds needlessly is paid on every turn of every session -- which is
    the recurring noise that gets a gate switched off.
    """

    def _submit(self, text: str) -> dict:
        return dispatch.user_prompt_submit(
            [], Ledger(), {"hook_event_name": "UserPromptSubmit", "session_id": "k",
                           "user_input": text})

    def test_TEETH_a_bare_compact_receives_the_preserve_list(self) -> None:
        out = self._submit("/compact")
        context = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertIn("Preserve verbatim", context, f"the cut got no preserve list: {out}")
        # THE VENDORED BYTES, READ HERE, not `dispatch._preserve_list()` -- which is the function
        # that produced `context` in the first place. That comparison was the function against
        # itself: MEASURED, with `return doc["preserve"]` changed to `return doc["preserve"][:40]`
        # the hook delivered 40 of the list's 475 bytes and the whole suite returned OK, because
        # both sides of the assertion had been truncated together. `_provenance.sha256` did not
        # catch it either: it pins compaction.json's `preserve` field against a digest of itself,
        # which is the file's internal consistency and says nothing about what is delivered.
        # Nothing in the repository pinned the compaction feature's actual output. This does.
        vendored = json.loads(
            (PLUGIN / "keel" / "compaction.json").read_text(encoding="utf-8"))["preserve"]
        self.assertEqual(vendored, context,
                         "the injected text is not the vendored list, byte for byte")

    def test_TEETH_an_authored_preserve_list_is_never_overridden(self) -> None:
        # Supplying a missing guard and overruling a present one are different acts. An author
        # who stated what to keep has decided; a default that replaced it would be the mandate
        # counterfeit, not a construction.
        self.assertEqual({}, self._submit("/compact keep only the shas and the error strings"))

    def test_TEETH_an_ordinary_prompt_is_untouched(self) -> None:
        for text in ("fix the parser", "compact", "please /compact later", "/compactify"):
            with self.subTest(prompt=text):
                self.assertEqual({}, self._submit(text), f"{text!r} drew a response")

    def test_TEETH_a_missing_vendored_list_does_not_eat_the_prompt(self) -> None:
        # Fails OPEN. The worst a broken vendored file may cost is the preserve list itself;
        # swallowing the user's `/compact` would be a wiring fault deciding a user's command.
        with mock.patch.object(dispatch, "_preserve_list", side_effect=OSError("gone")):
            self.assertEqual({}, self._submit("/compact"))

    def test_TEETH_an_automatic_cut_says_it_was_not_steered(self) -> None:
        out = dispatch.pre_compact([], Ledger(), {"hook_event_name": "PreCompact",
                                                  "compact_trigger": "auto"})
        self.assertIn("automatic compaction", out.get("systemMessage", ""),
                      f"an unsteered automatic cut passed silently: {out}")
        # And it must NOT block. An automatic cut happens because the window is full; refusing it
        # to protect a summary wedges the session, which is a worse fate than a worse summary.
        self.assertNotIn("hookSpecificOutput", out)
        self.assertNotIn("decision", out)

    def test_TEETH_a_manual_cut_is_not_reported_twice(self) -> None:
        self.assertEqual({}, dispatch.pre_compact([], Ledger(),
                         {"hook_event_name": "PreCompact", "compact_trigger": "manual"}))

    def test_TEETH_the_vendored_list_matches_its_own_digest(self) -> None:
        """The provenance is a digest of the bytes, not a coordinate into a frozen repository.

        A commit pin would name a tree this body no longer matches the moment the prompt set is
        edited, and nothing here could tell. A digest is checkable by this repository alone.
        """
        doc = json.loads((PLUGIN / "keel" / "compaction.json").read_text(encoding="utf-8"))
        self.assertEqual(doc["_provenance"]["sha256"],
                         hashlib.sha256(doc["preserve"].encode()).hexdigest(),
                         "the vendored preserve list no longer matches its recorded digest")

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red; a checker that cannot follow an imported helper reads this body as empty
        smoke_replace(self, PLUGIN / "keel" / "dispatch.py",
                      b'_BARE_COMPACT = re.compile(r"^\\s*/compact\\s*$")',
                      b'_BARE_COMPACT = re.compile(r"^\\s*/never-matches-this\\s*$")',
                      "tests.test_bypass.TheCutGetsItsPreserveListWithoutBeingAsked."
                      "test_TEETH_a_bare_compact_receives_the_preserve_list",
                      "the cut got no preserve list")

    def test_the_delivered_bytes_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red; a checker that cannot follow an imported helper reads this body as empty
        """Truncate the list AT DELIVERY, and the byte-for-byte assertion must go red.

        This is the plant the old assertion could not carry: it compared the hook's output to
        `dispatch._preserve_list()`, so this exact mutation moved both sides together and the
        suite stayed green with 40 of 475 bytes reaching the model.
        """
        smoke_replace(self, PLUGIN / "keel" / "dispatch.py",
                      b'    return doc["preserve"]',
                      b'    return doc["preserve"][:40]',
                      "tests.test_bypass.TheCutGetsItsPreserveListWithoutBeingAsked."
                      "test_TEETH_a_bare_compact_receives_the_preserve_list",
                      "the injected text is not the vendored list, byte for byte")


class ThereIsExactlyOneExemptionSpelling(unittest.TestCase):
    """`# gyroscope-allow:` was a second, undocumented spelling that exempted a Bash call from all
    24 clauses exactly as `# keel-allow:` does, while the README named only one. An exemption the
    pages do not name is one nobody can audit: a reader counting the ways a call can skip the table
    would have counted one and been wrong.

    It was kept on the argument that the plugin had shipped under the old name and removing it
    would strand exemptions already written in users' scripts. The owner settled the fact: the
    public repository is Keel, several tags carry that name, and there is no installed base to
    strand. So the argument was empty and the pattern is gone.

    This is the census that keeps it gone. A third spelling added later fails here rather than
    passing unnoticed."""

    def test_the_allow_pattern_is_the_whole_exemption_surface(self):
        exempting = {name for name, val in vars(dispatch).items()
                     if isinstance(val, re.Pattern) and "allow" in name.lower()}
        self.assertEqual(
            exempting, {"ALLOW"},
            f"a second exemption spelling exists: {sorted(exempting)}. Every way past the 24 "
            "clauses must be named in README.md's Manual bypass section, or it cannot be audited.")

    def test_the_retired_spelling_no_longer_exempts(self):
        event = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "session_id": "r",
                 "agent_id": "", "tool_input": {"command": "# gyroscope-allow: approved\nrm -rf b/"}}
        out = dispatch.pre_tool_use(C.load_default(), Ledger(), event)
        self.assertIn("hookSpecificOutput", out,
                      f"the retired spelling still exempted the call: {out}")
