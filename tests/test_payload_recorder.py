"""Keel can capture what the host sends it, and cannot answer the question without doing so.

C08 is the one clause of 24 that does not enforce. It is parked because `tool_response` was
measured to carry no exit status -- over 71 PostToolUse payloads, in a sibling plugin's
database that now holds none. Keel could not have made that measurement itself and cannot
repeat it: it journals its own DECISIONS, never the payloads it was handed, and
`eval/corpus/*.jsonl` are hand-authored fixtures, a different kind of evidence that has
already been misread as this one once this session.

So the engine whose only parked clause turns on a fact about the host had no way to observe
the host. This module covers the instrument that fixes that, and the two properties that
decide whether it is worth having:

  * it records SHAPE and never content -- keys, types, lengths, truthiness. Not a redaction: a
    corpus that must be scrubbed before it can be read is one scrub away from leaking, and the
    question is about the shape anyway;
  * it is OFF unless asked. A capture that ran unasked would make every user of the plugin a
    subject of it.

And the census refuses to answer over an empty corpus, which is the property that matters
most. "No exit status found" computed over zero payloads is indistinguishable from the real
answer, and reporting it would recreate C08's own failure with a fresh date on it.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.plant_support import PLUGIN, REPO, smoke_replace
from keel import recorder

CENSUS = REPO / "tools" / "payload_census.py"
HOOK = PLUGIN / "hooks" / "dispatch.sh"

SECRET = "s3cret-token-value-do-not-record"

PAYLOAD = {
    "hook_event_name": "PostToolUse",
    "session_id": "recorder-cell",
    "tool_name": "Bash",
    "tool_input": {"command": f"echo {SECRET}"},
    "tool_response": {"stdout": SECRET, "stderr": "", "interrupted": False},
}


class TheRecorderCapturesShapeAndNothingElse(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.dir, True)
        self.shapes = Path(self.dir) / recorder.SHAPES_FILE
        # SET the precondition, never inherit it. These cells first passed only because the
        # runner happened to be invoked with KEEL_RECORD_SHAPES exported: under a bare
        # `unittest discover` the recorder is correctly off and every cell asserting a
        # PRESENCE would have failed, while the one asserting an absence would have passed for
        # the wrong reason -- a green bought from the environment rather than the subject.
        saved = os.environ.get(recorder.ENABLE_ENV)
        os.environ[recorder.ENABLE_ENV] = self.dir
        self.addCleanup(lambda: os.environ.__setitem__(recorder.ENABLE_ENV, saved)
                        if saved is not None
                        else os.environ.pop(recorder.ENABLE_ENV, None))

    def test_NON_VACUITY_it_writes_when_enabled(self) -> None:
        """Every cell that asserts an ABSENCE below needs this one to have shown a presence."""
        recorder.record(PAYLOAD, root=self.dir)
        self.assertTrue(self.shapes.exists())
        row = json.loads(self.shapes.read_text().splitlines()[0])
        self.assertEqual(sorted(row["keys"]), ["interrupted", "stderr", "stdout"])
        self.assertEqual(row["keys"]["stdout"]["len"], len(SECRET))

    def test_TEETH_no_content_reaches_the_corpus(self) -> None:
        """The property that lets the corpus be committed at all."""
        recorder.record(PAYLOAD, root=self.dir)
        written = self.shapes.read_text()
        self.assertNotIn(SECRET, written)
        self.assertNotIn("echo", written)

    def test_TEETH_it_is_off_unless_asked(self) -> None:
        saved = os.environ.pop(recorder.ENABLE_ENV, None)
        try:
            recorder.record(PAYLOAD, root=self.dir)
            self.assertFalse(self.shapes.exists(),
                             "a capture nobody asked for makes every user a subject")
        finally:
            if saved is not None:
                os.environ[recorder.ENABLE_ENV] = saved

    def test_TEETH_it_never_raises_on_a_malformed_event(self) -> None:
        """A recorder that can break the hook fails a call in order to observe it."""
        for junk in (None, [], "not-an-event", {"tool_response": object()}):
            with self.subTest(event=repr(junk)[:24]):
                recorder.record(junk, root=self.dir)

    def test_TEETH_the_shipped_hook_records(self) -> None:
        """Through `hooks/dispatch.sh` as a subprocess -- the recorder is only worth anything
        on the path the host actually calls."""
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.dir, HOME=self.dir,
                   KEEL_RECORD_SHAPES=self.dir)
        subprocess.run(["bash", str(HOOK)], input=json.dumps(PAYLOAD), text=True,
                       capture_output=True, env=env, cwd=str(REPO))
        self.assertTrue(self.shapes.exists(), "the shipped hook did not reach the recorder")
        self.assertNotIn(SECRET, self.shapes.read_text())


class TheCensusRefusesAnEmptyCorpus(unittest.TestCase):
    def census(self, path: str) -> subprocess.CompletedProcess:
        return subprocess.run(["python3", str(CENSUS), "--shapes", path],
                              text=True, capture_output=True, cwd=str(REPO))

    def test_TEETH_zero_payloads_is_not_evaluable_not_a_pass(self) -> None:
        """The cell this whole module is for. C08 was parked by a measurement nobody can
        repeat; an instrument that answered over nothing would do it again."""
        result = self.census("/tmp/keel-census-absent.jsonl")
        self.assertEqual(result.returncode, 2)
        self.assertIn("NOT-EVALUABLE", result.stderr)

    def test_TEETH_a_status_shaped_key_is_a_finding_not_a_pass(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
            fh.write(json.dumps({"hook_event": "PostToolUse", "keys": {
                "exit_code": {"type": "int", "value": 2, "truthy": True}}}) + "\n")
            path = fh.name
        result = self.census(path)
        self.assertEqual(result.returncode, 1)
        self.assertIn("CENSUS=FINDING", result.stdout)

    def test_TEETH_the_denominator_is_printed_with_the_verdict(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
            fh.write(json.dumps({"hook_event": "PostToolUse", "keys": {
                "stdout": {"type": "str", "len": 3, "truthy": True}}}) + "\n")
            path = fh.name
        result = self.census(path)
        self.assertEqual(result.returncode, 0)
        self.assertIn("post_tool_use=1", result.stdout)
        self.assertIn("no status-shaped key in 1 payloads", result.stdout)

    def test_the_check_can_fail(self) -> None:
        """Make the census answer over an empty corpus instead of refusing.

        This is the exact defect the tool exists to prevent, so it is what the plant restores:
        with the guard removed, a run that read NOTHING reports PASS, and 'no exit status'
        becomes indistinguishable from 'nothing was looked at'.
        """
        smoke_replace(
            self, CENSUS,
            b"    if not post:",
            b"    if False:",
            "tests.test_payload_recorder.TheCensusRefusesAnEmptyCorpus."
            "test_TEETH_zero_payloads_is_not_evaluable_not_a_pass",
            # The order is the assertion's, not the reader's: `assertEqual(returncode, 2)`
            # against a disarmed census reports "0 != 2". Written the other way round it read
            # like a plant that did not land, when it had.
            "0 != 2",
        )


if __name__ == "__main__":
    unittest.main()
