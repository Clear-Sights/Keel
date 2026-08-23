"""The persisted record, and the byte boundary that keeps a clause from abstaining in silence.

TWO DEFECTS.

1. NO LOG. Keel hooks six event families and wrote nothing down unless a demand was actually
   raised. `obligations.jsonl` is a LEDGER -- outstanding obligations only -- so a session where
   every clause passed left the state directory empty, and so did a session where the plugin never
   ran. "Did Keel catch anything?" had no file to consult: not "no", but UNANSWERABLE, which
   is indistinguishable from never-installed. This is the plugin's own "absence must never read as
   green" law, which it enforces against the session's clause table, finally applied to itself.

2. A LONE SURROGATE SILENCED CLAUSES. A host byte that is not valid UTF-8 arrived as a lone
   surrogate, `_subject` handed it to `derive_id`, and `_canon(...).encode()` raised -- inside
   `pre_tool_use`'s per-clause `except Exception: continue`. The clause did not deny, did not pass,
   and recorded nothing. The isolation is right in itself (one clause must never suppress the other
   twenty-five) but was never meant to swallow a whole-payload defect once per clause and call the
   event clean.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from tests.plant_support import PLUGIN, smoke_replace

PLUGIN_ROOT = PLUGIN


def run(raw: bytes, state_dir: Path) -> dict:
    env = os.environ.copy()
    env["KEEL_STATE_DIR"] = str(state_dir)
    proc = subprocess.run([sys.executable, "-m", "keel.dispatch"], input=raw,
                          capture_output=True, env=env, cwd=str(PLUGIN_ROOT))
    return json.loads(proc.stdout.decode() or "{}")


def rows(state_dir: Path) -> list:
    path = state_dir / "decisions.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


DESTRUCTIVE = (b'{"hook_event_name":"PreToolUse","tool_name":"Bash","session_id":"g-deny",'
               b'"tool_input":{"command":"rm -rf build/"}}')
# One byte 0x9D inside the operand a dict-subject clause extracts, so the surrogate lands squarely
# in `derive_id` -- the exact path that used to abstain in silence.
DESTRUCTIVE_BAD_BYTE = (b'{"hook_event_name":"PreToolUse","tool_name":"Bash","session_id":"g-bad",'
                        b'"tool_input":{"command":"rm -rf bui\x9dld/"}}')


class StateCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)


class TestTheRecord(StateCase):
    def test_session_row_proves_the_plugin_ran(self):
        """The liveness proof. Without it an empty log cannot be told apart from a plugin that was
        never installed -- and both look exactly like a clean session."""
        run(DESTRUCTIVE, self.state)
        sessions = [r for r in rows(self.state) if r["kind"] == "session"]
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["session_id"], "g-deny")
        self.assertGreater(sessions[0]["clauses"], 0,
                           "a session row saying 0 clauses is a gate that checked nothing")

    def test_session_row_written_once_not_per_call(self):
        for _ in range(3):
            run(DESTRUCTIVE, self.state)
        self.assertEqual(len([r for r in rows(self.state) if r["kind"] == "session"]), 1)

    def test_deny_row_names_clause_and_subject(self):
        run(DESTRUCTIVE, self.state)
        denies = [r for r in rows(self.state) if r["kind"] == "deny"]
        self.assertEqual(len(denies), 1)
        self.assertEqual(denies[0]["clause_id"], "A02")
        self.assertEqual(denies[0]["subject"], "build/")

    def test_subject_is_read_back_from_the_message_the_agent_saw(self):
        """Two derivations of one fact is two facts. The row parses the subject out of the rendered
        reason so the log can never disagree with what the agent was actually told."""
        body = run(DESTRUCTIVE, self.state)
        reason = body["hookSpecificOutput"]["permissionDecisionReason"]
        subject = [r for r in rows(self.state) if r["kind"] == "deny"][0]["subject"]
        self.assertIn(f"`{subject}`", reason)

    def test_every_row_names_its_plugin(self):
        """Three plugins register PreToolUse and the host does not say which one spoke."""
        run(DESTRUCTIVE, self.state)
        self.assertTrue(rows(self.state))
        for row in rows(self.state):
            self.assertEqual(row["plugin"], "keel")
            self.assertIn("session_id", row)
            self.assertIn("tool_name", row)
            self.assertIn("hook_event", row)

    def test_clean_terminal_is_recorded_as_a_positive_result(self):
        """A terminal that reconciled cleanly is the one outcome a fires-only log would erase,
        and it is exactly what distinguishes 'nothing owed' from 'never got there'."""
        run(b'{"hook_event_name":"PreToolUse","tool_name":"Bash","session_id":"g-clean",'
            b'"tool_input":{"command":"git status"}}', self.state)
        run(b'{"hook_event_name":"Stop","session_id":"g-clean"}', self.state)
        blocks = [r for r in rows(self.state) if r["kind"] == "block"]
        self.assertTrue(blocks)
        self.assertEqual(blocks[-1]["open_count"], 0)

    def test_terminal_block_records_the_clauses(self):
        run(b'{"hook_event_name":"Stop","session_id":"g-block"}', self.state)
        blocks = [r for r in rows(self.state) if r["kind"] == "block"]
        self.assertTrue(blocks and blocks[-1]["open_count"] >= 1)
        self.assertTrue(blocks[-1]["clause_ids"])

    def test_allowed_calls_write_no_decision_row(self):
        """Fires-only by design: a row per allowed call runs 99%+ noise and drowns the signal."""
        run(b'{"hook_event_name":"PreToolUse","tool_name":"Read","session_id":"g-quiet",'
            b'"tool_input":{"file_path":"/tmp/a"}}', self.state)
        self.assertEqual({r["kind"] for r in rows(self.state)}, {"session"})

    def _main_on(self, raw: bytes):
        """Drive `dispatch.main()` in-process on `raw`, returning (exit code, stdout).

        In-process and through MAIN, deliberately. `pre_tool_use` does not touch the journal at
        all -- every `note_*` call lives in `main()` -- so a test that broke the journal and then
        compared two `pre_tool_use` results would be comparing two calls that could not have
        differed, whatever the journal did. And the subprocess `run()` helper cannot be used
        either, because a monkeypatch here does not cross a process boundary.
        """
        import contextlib
        import io

        from keel import dispatch

        class FakeStdin:
            def __init__(self, data):
                self.buffer = io.BytesIO(data)

            def read(self):
                return self.buffer.read().decode()

        # A FRESH state dir per call, and it is load-bearing rather than tidiness. `note_session`
        # returns early when this session's marker already exists, so against a reused directory
        # the second call never reaches `_append` at all -- and a test that breaks `_append` would
        # then pass no matter what the journal did. Caught exactly that way: a planted
        # non-swallowing `note_session` failed the two neighbouring tests and left this one green.
        out, err = io.StringIO(), io.StringIO()
        state = tempfile.mkdtemp()
        real_stdin, sys.stdin = sys.stdin, FakeStdin(raw)
        real_state = os.environ.get("KEEL_STATE_DIR")
        os.environ["KEEL_STATE_DIR"] = state
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = dispatch.main()
        finally:
            sys.stdin = real_stdin
            if real_state is None:
                os.environ.pop("KEEL_STATE_DIR", None)
            else:
                os.environ["KEEL_STATE_DIR"] = real_state
        return code, out.getvalue()

    def test_journal_failure_never_changes_a_verdict(self):
        """Observability must never become policy: a gate that changed its answer because its
        logger could not write would be a worse bug than the missing log.

        Asserts the VERDICT ON THE WIRE, not merely that nothing raised. The earlier form called
        the five entry points with `_append` broken and stopped there, so it proved they swallow
        and proved nothing at all about the decision -- the half its own name claims. Makoto
        flagged it as hollow and was right to.

        The failure this guards is specific and live: `note_session` is called INSIDE `main`'s
        evaluation try, whose `except` hands the event to `_closed_not_evaluable`. So the moment
        any `note_*` stops swallowing, a journal write error stops being a missing row and becomes
        a NOT-EVALUABLE verdict on a call the clause table had already ruled on.

        Broken at `journal._append` specifically, NOT by making the state directory unwritable.
        Measured: an unwritable state dir takes the LEDGER down too, and the ledger is real policy
        input -- the verdict then legitimately becomes "could not evaluate", so that version of
        the test would assert the opposite of the property on a system behaving correctly.
        """
        from keel import journal

        healthy_code, healthy = self._main_on(DESTRUCTIVE)
        self.assertEqual(healthy_code, 0)
        self.assertIn("[A02]", healthy,
                      "the fixture must actually fire, or this test compares two nothings")

        original = journal._append
        journal._append = lambda *a, **k: (_ for _ in ()).throw(OSError("disk full"))
        self.addCleanup(setattr, journal, "_append", original)
        broken_code, broken = self._main_on(DESTRUCTIVE)

        self.assertEqual((broken_code, broken), (healthy_code, healthy),
                         "a journal that cannot write changed the decision on the wire")

    def test_every_journal_entry_point_swallows_its_own_failure(self):
        """The other half, kept separate so a raise is attributable to ONE entry point."""
        from keel import journal
        original = journal._append
        journal._append = lambda *a, **k: (_ for _ in ()).throw(OSError("disk full"))
        self.addCleanup(setattr, journal, "_append", original)
        for label, call in (
            ("note_deny", lambda: journal.note_deny({"session_id": "x"}, "A02", "build/", "r")),
            ("note_session", lambda: journal.note_session({"session_id": "x"}, 24)),
            ("note_block", lambda: journal.note_block({"session_id": "x"}, 1, ["T01"])),
            ("note_fault", lambda: journal.note_fault({"session_id": "x"}, "s", "d",
                                                      failed_closed=True)),
            ("note_repair", lambda: journal.note_repair({"session_id": "x"}, 1)),
        ):
            with self.subTest(entry_point=label):
                self.assertIsNone(call(), f"{label} must swallow and return None")


class TestAttribution(StateCase):
    def test_deny_names_the_plugin_on_the_wire(self):
        body = run(DESTRUCTIVE, self.state)
        reason = body["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertTrue(reason.startswith("keel: "), reason)

    def test_terminal_block_names_the_plugin_on_the_wire(self):
        body = run(b'{"hook_event_name":"Stop","session_id":"g-attr"}', self.state)
        self.assertTrue(body["reason"].startswith("keel: "), body)


class TestByteBoundary(StateCase):
    def test_bad_byte_no_longer_makes_a_clause_abstain(self):
        """The regression. The clause must still reach a verdict on the repaired operand."""
        body = run(DESTRUCTIVE_BAD_BYTE, self.state)
        self.assertEqual(
            body.get("hookSpecificOutput", {}).get("permissionDecision"), "deny",
            "a destructive command must not escape the clause table over one stray byte")

    def test_the_repair_is_recorded_and_is_not_a_fault(self):
        """The event WAS evaluated. Filing a repair as a fault would inflate the count of
        unevaluated calls, the one number this log exists to keep honest."""
        run(DESTRUCTIVE_BAD_BYTE, self.state)
        self.assertEqual([r for r in rows(self.state) if r["kind"] == "repair"][0]["repaired"], 1)
        self.assertEqual([r for r in rows(self.state) if r["kind"] == "fault"], [])

    def test_ledger_write_survives_a_surrogate_operand(self):
        """`derive_id` -> `_canon(...).encode()` was the raise site. The demand must land."""
        run(DESTRUCTIVE_BAD_BYTE, self.state)
        self.assertTrue((self.state / "obligations.jsonl").exists(),
                        "the demand must be persisted, not lost to an encode error")

    def test_unpaired_surrogate_escape_is_closed_too(self):
        """The other door: valid UTF-8 whose JSON text carries an unpaired \\uD8xx escape."""
        raw = (b'{"hook_event_name":"PreToolUse","tool_name":"Bash","session_id":"g-esc",'
               b'"tool_input":{"command":"rm -rf bu\\ud89dild/"}}')
        body = run(raw, self.state)
        self.assertEqual(body.get("hookSpecificOutput", {}).get("permissionDecision"), "deny")

    def test_a_bom_prefixed_envelope_still_reaches_the_clause_table(self):
        """The third door -- the one this family closed twice and missed once.

        A UTF-8 BOM is a legitimate encoding artifact, not damage. Strict-decoded as "utf-8" it
        survives as a leading U+FEFF that json.loads REFUSES, so a STRUCTURALLY PERFECT envelope
        took `main`'s unreadable_event path: NOT-EVALUABLE, the whole 24-clause table skipped for
        that call, the destructive command ALLOWED, and the recorded reason ("unreadable event")
        false of the payload. Makoto closed this at its wire layer and Ward at its dispatch layer;
        keel was the remaining door. Found by a cross-plugin duplicate index, not by a report.
        """
        body = run(b"\xef\xbb\xbf" + DESTRUCTIVE, self.state)
        self.assertEqual(
            body.get("hookSpecificOutput", {}).get("permissionDecision"), "deny",
            "a BOM on the envelope must not let a destructive command skip the clause table")
        self.assertEqual([r for r in rows(self.state) if r["kind"] == "fault"], [],
                         "a BOM is an encoding artifact, not a fault to be counted")

    def test_clean_payload_reports_no_repair(self):
        run(DESTRUCTIVE, self.state)
        self.assertEqual([r for r in rows(self.state) if r["kind"] == "repair"], [])

    def test_legitimate_replacement_char_is_not_damage(self):
        from keel import wire
        _text, n = wire._decode_counting("legit � char".encode("utf-8"))
        self.assertEqual(n, 0, "a payload that genuinely contains U+FFFD is clean, not damaged")

    def test_repair_count_is_bytes_not_malformed_runs(self):
        """Found by an independent review pass. `errors="replace"` emits ONE U+FFFD per malformed
        RUN, so a truncated three-byte sequence -- two undecodable bytes -- reported 1, under a
        field named "bytes repaired". `surrogateescape` maps each bad BYTE to one surrogate, so the
        count means what the field says."""
        from keel import wire
        self.assertEqual(wire._decode_counting(b"\xe2\x82")[1], 2)
        self.assertEqual(wire._decode_counting(b"x\x9dy")[1], 1)

    def test_scrub_counts_and_removes(self):
        from keel import wire
        text, n = wire.scrub_text("a\ud89db\udc9dc")
        self.assertEqual(n, 2)
        self.assertFalse(any("\ud800" <= c <= "\udfff" for c in text))

    def test_scrub_returns_clean_input_untouched(self):
        from keel import wire
        original = {"a": ["b", {"c": "d"}]}
        value, n = wire.scrub(original)
        self.assertEqual(n, 0)
        self.assertIs(value, original)


# --- regressions found by an independent high-effort review pass ------------------------------

class TestTheSubjectSurvivesTheRoundTrip(unittest.TestCase):
    """The journal reads the ledger key back out of the deny it showed the agent, so that the
    record can never disagree with what the agent was actually told. A backtick in the subject
    broke exactly that: the ledger keyed on the full operand, the wire showed the full operand,
    and the row recorded a shorter, different one."""

    def _round_trip(self, subject):
        sys.path.insert(0, str(PLUGIN_ROOT))
        from keel import dispatch

        class Clause:
            id = "A02"
            deny_reason = "list the set first"
            subject = {"extract": "path"}
            # Every loaded clause carries an anchor -- the loader refuses one that does not, so
            # a double without it stands in for a row that cannot exist. `_keyed_reason` appends
            # the pointer on every path, and the round trip has to read back past it.
            construction = "POINTS.md#a02"

        return dispatch._subject_of(dispatch._keyed_reason(Clause(), subject))

    def test_a_backtick_in_the_subject_does_not_truncate_the_row(self):
        self.assertEqual(self._round_trip("api`prod.example"), "api`prod.example")

    def test_several_backticks_do_not_truncate_the_row(self):
        self.assertEqual(self._round_trip("a`b`c"), "a`b`c")

    def test_an_ordinary_subject_is_unchanged(self):
        self.assertEqual(self._round_trip("build/"), "build/")

    def test_a_session_wide_deny_still_reads_as_session_wide(self):
        """The empty answer must stay reachable: a session-scoped clause names no subject, and
        reading one out of its message would point the session at its own id."""
        sys.path.insert(0, str(PLUGIN_ROOT))
        from keel import dispatch

        class SessionClause:
            id = "T01"
            deny_reason = "run git status first"
            subject = "session_id"
            construction = "POINTS.md#t01"

        self.assertEqual(
            dispatch._subject_of(dispatch._keyed_reason(SessionClause(), "drive")), "")

    def test_a_clause_whose_own_prose_says_keyed_on_does_not_hijack_the_row(self):
        """The suffix is APPENDED, so the renderer's copy is always the last one in the string.

        A forward search took the clause's own words instead, and the row then named an operand
        the agent was never shown -- the exact disagreement this class exists to rule out, reached
        from the one direction the backtick cases could not see.
        """
        sys.path.insert(0, str(PLUGIN_ROOT))
        from keel import dispatch

        class TalkativeClause:
            id = "X01"
            deny_reason = ("prerequisite keyed on `wrong`, so the guard must name `wrong` "
                           "too; spelled exactly as the renderer spells it")
            subject = {"extract": "path"}
            construction = "POINTS.md#x01"

        reason = dispatch._keyed_reason(TalkativeClause(), "real-target")
        self.assertIn("must name `real-target`", reason)
        self.assertEqual(dispatch._subject_of(reason), "real-target")

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red; a checker that cannot follow an imported helper reads this body as empty
        """Restore the backtick-terminated span and this class must go red.

        Each plant names the SPECIFIC wrong value it produces as `smoke_replace`'s `expected`,
        not merely "AssertionError" -- that substring is satisfied by any assertion failing
        anywhere in the target, including one the plant broke incidentally, so on its own it
        cannot show the plant reached the property under test.

        The two values are different failures, which is why both plants are needed. The backtick
        plant TRUNCATES the subject to the EMPTY string, and empty is not merely wrong here: it
        is the session-wide sentinel (see `test_a_session_wide_deny_still_reads_as_session_wide`),
        so that truncation silently widens a deny aimed at one operand into one aimed at the whole
        session. The forward-search plant HIJACKS the subject with the clause\'s own prose, which
        is the opposite direction and the one the backtick cases cannot reach.
        """
        smoke_replace(
            self, PLUGIN / "keel" / "dispatch.py",
            b'    r"keyed on `(.{1,2000}?)`, so the guard must name `(.{1,2000}?)` too; ", re.DOTALL)',
            b'    r"keyed on `([^`]{1,200})`, so the guard must name `([^`]{1,200})` too; ")',
            "tests.test_journal_and_wire.TestTheSubjectSurvivesTheRoundTrip"
            ".test_a_backtick_in_the_subject_does_not_truncate_the_row",
            "'' != 'api`prod.example'")
        # The other half of the same property, planted separately because it fails from the other
        # direction: reading the FIRST match instead of the last.
        smoke_replace(
            self, PLUGIN / "keel" / "dispatch.py",
            b'    for last in _KEYED_ON_RX.finditer(reason or ""):\n        pass\n',
            b'    last = _KEYED_ON_RX.search(reason or "")\n',
            "tests.test_journal_and_wire.TestTheSubjectSurvivesTheRoundTrip"
            ".test_a_clause_whose_own_prose_says_keyed_on_does_not_hijack_the_row",
            "'wrong' != 'real-target'")


class TestABlockRowSaysWhichBlockItWas(unittest.TestCase):
    """`open_count: 0, clause_ids: []` was emitted BOTH for a terminal that reconciled cleanly and
    for one blocked by an internal fault, because the count parser defaulted to 0 when the message
    stated none. Those are the two outcomes this log exists to tell apart, wearing one row."""

    def test_a_message_stating_no_count_reads_as_unknown_not_zero(self):
        sys.path.insert(0, str(PLUGIN_ROOT))
        from keel import dispatch
        self.assertIsNone(
            dispatch._stated_count("keel: RuntimeError -- NOT-EVALUABLE, failing closed"))

    def test_a_message_stating_a_count_still_reads_it(self):
        sys.path.insert(0, str(PLUGIN_ROOT))
        from keel import dispatch
        self.assertEqual(dispatch._stated_count("3 obligations still open [A02] [C08]"), 3)

    def test_the_clean_terminal_records_a_real_zero(self):
        """The clean terminal passes its 0 from its own call site, so it stays distinguishable
        from the unknown above."""
        sys.path.insert(0, str(PLUGIN_ROOT))
        from keel import journal
        journal.note_block({"session_id": "g-clean"}, 0, [], root=self.state_dir)
        journal.note_block({"session_id": "g-clean"}, None, [], root=self.state_dir)
        blocks = [r for r in rows(self.state_dir) if r["kind"] == "block"]
        self.assertEqual([b["open_count"] for b in blocks], [0, None])

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state_dir = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red; a checker that cannot follow an imported helper reads this body as empty
        """Restore the 0 default and the fault block becomes indistinguishable from a clean one."""
        smoke_replace(
            self, PLUGIN / "keel" / "dispatch.py",
            b"            return int(digits)\n    return None",
            b"            return int(digits)\n    return 0",
            "tests.test_journal_and_wire.TestABlockRowSaysWhichBlockItWas"
            ".test_a_message_stating_no_count_reads_as_unknown_not_zero", "0 is not None")


class TestTheSessionRowIsExactlyOnce(StateCase):
    """Three defects in one function, each costing the liveness row the journal exists for."""

    def test_ids_differing_only_in_punctuation_are_not_one_session(self):
        sys.path.insert(0, str(PLUGIN_ROOT))
        from keel import journal
        journal.note_session({"session_id": "a/b"}, 21, root=self.state)
        journal.note_session({"session_id": "a?b"}, 21, root=self.state)
        got = sorted(r["session_id"] for r in rows(self.state) if r["kind"] == "session")
        self.assertEqual(got, ["a/b", "a?b"])

    def test_a_failed_append_does_not_suppress_the_row_forever(self):
        sys.path.insert(0, str(PLUGIN_ROOT))
        from keel import journal
        original = journal._append
        journal._append = lambda *a, **k: (_ for _ in ()).throw(OSError("disk full"))
        self.addCleanup(setattr, journal, "_append", original)
        journal.note_session({"session_id": "s1"}, 21, root=self.state)
        journal._append = original
        journal.note_session({"session_id": "s1"}, 21, root=self.state)
        self.assertEqual(len([r for r in rows(self.state) if r["kind"] == "session"]), 1)

    def test_concurrent_processes_write_one_row_between_them(self):
        """A PIPE releases the children, not a flag file, and the burst is repeated.

        Measured against the unfixed code: no barrier caught the race 9 runs in 10, and polling a
        flag file was WORSE at 8 in 10, because each child notices the file on its own schedule.
        Blocking on one read and closing the write end hands the wakeup to the kernel. Rounds are
        independent trials, so a miss needs every round to miss.
        """
        sys.path.insert(0, str(PLUGIN_ROOT))
        from keel import journal
        for round_no in range(6):
            session = f"race-{round_no}"
            read_fd, write_fd = os.pipe()
            kids = []
            try:
                for _ in range(16):
                    pid = os.fork()
                    if pid == 0:
                        try:
                            os.close(write_fd)
                            os.read(read_fd, 1)
                            journal.note_session({"session_id": session}, 21, root=self.state)
                        finally:
                            os._exit(0)
                    kids.append(pid)
            finally:
                # Release and reap in `finally`: a fork() that fails part-way through the burst --
                # process-table exhaustion on a loaded machine -- must not leave the children it
                # DID create blocked on the pipe forever. Found by an independent review pass.
                os.close(write_fd)
                for pid in kids:
                    os.waitpid(pid, 0)
                os.close(read_fd)
            got = [r for r in rows(self.state)
                   if r["kind"] == "session" and r["session_id"] == session]
            self.assertEqual(len(got), 1, f"round {round_no}: {len(got)} rows for one session")

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red; a checker that cannot follow an imported helper reads this body as empty
        """Drop the digest and two differently-punctuated ids collide onto one marker again."""
        smoke_replace(
            self, PLUGIN / "keel" / "journal.py",
            b"    return f\"{safe}-{hashlib.sha256(session.encode('utf-8')).hexdigest()[:16]}\"",
            b"    return safe",
            "tests.test_journal_and_wire.TestTheSessionRowIsExactlyOnce"
            ".test_ids_differing_only_in_punctuation_are_not_one_session",
            "Lists differ: ['a/b'] != ['a/b', 'a?b']")


class TestRepairCountsMeanWhatTheyAreNamed(StateCase):
    """`repaired` counts undecodable BYTES. Summing the surrogate-ESCAPE count into it meant an
    envelope whose bytes were flawless could still report bytes repaired."""

    def test_an_escape_only_envelope_reports_zero_bytes_repaired(self):
        raw = (b'{"hook_event_name":"PreToolUse","tool_name":"Bash","session_id":"g-esc",'
               b'"tool_input":{"command":"rm -rf bu\\ud89dild/"}}')
        run(raw, self.state)
        repair = [r for r in rows(self.state) if r["kind"] == "repair"][0]
        self.assertEqual(repair["repaired"], 0, "no byte on that wire was undecodable")
        self.assertEqual(repair["escaped"], 1)

    def test_a_byte_damaged_envelope_reports_zero_escapes(self):
        run(DESTRUCTIVE_BAD_BYTE, self.state)
        repair = [r for r in rows(self.state) if r["kind"] == "repair"][0]
        self.assertEqual(repair["repaired"], 1)
        self.assertEqual(repair["escaped"], 0)

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red; a checker that cannot follow an imported helper reads this body as empty
        """Sum the escape count back into the byte count and the field stops meaning bytes."""
        smoke_replace(
            self, PLUGIN / "keel" / "dispatch.py",
            b"        event, escaped = wire.scrub(event)\n    except Exception as exc:",
            b"        event, escaped = wire.scrub(event)\n        repaired += escaped\n"
            b"    except Exception as exc:",
            "tests.test_journal_and_wire.TestRepairCountsMeanWhatTheyAreNamed"
            ".test_an_escape_only_envelope_reports_zero_bytes_repaired",
            "1 != 0 : no byte on that wire was undecodable")


if __name__ == "__main__":
    unittest.main()
