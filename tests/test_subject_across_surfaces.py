"""U10's guard reaches the host `Read`, and its SUBJECT travels with it.

U10 demands that a JSON document be looked at before it is traversed, and its guard named one
program: `jq`. A guard that names programs is monotone in vocabulary (Coverings.v, Thm 5) --
it is defeated by doing the same act any other way, and looking at a file is the act with the
most ways. The host's own `Read` is that act, and `tool_name` is a CLOSED enum, so composing
over it RETIRES a vocabulary rather than widening one. This is the move U12 and U19 already
made to `Grep`.

What is new here is the subject. U12's subject is `session_id`, so its composed guard needed
no key. U10 keys per FILE, and the two surfaces carry the file in different fields: a jq
traversal in `tool_input.command`, a Read in `tool_input.file_path`. With a single-field
subject the composed guard extracts "" and discharges nothing -- the guard would be composed
over two surfaces while the subject stayed on one, and the whole change would silently do
nothing while reading as done. So `subject.on` may name several surfaces, read in order by
`clauses.subject_fields`, which is the ONE reading of that field: `_fixture_event`, `_admit`
and `dispatch._subject` all call it rather than spelling the rule three times.

The cell that matters most is `test_TEETH_a_read_of_another_file_does_not_license`: it is what
separates "the subject crossed surfaces" from "the guard went vacuous", and both of those show
up as a green allow on the happy path.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.plant_support import PLUGIN, REPO, smoke_replace
from keel import clauses as C

HOOK = PLUGIN / "hooks" / "dispatch.sh"


def u10() -> C.Clause:
    for clause in C.load_default():
        if clause.id == "U10":
            return clause
    raise AssertionError("U10 is not in the shipped clause table")


class SubjectCrossesSurfaces(unittest.TestCase):
    def setUp(self) -> None:
        self.state = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.state, True)

    def send(self, payload: dict, session: str) -> str:
        """Drive the SHIPPED hook as a subprocess -- not `_predicate`, which is a second
        spelling of what the dispatcher does and cannot see the ledger the discharge flows
        through."""
        event = dict(payload)
        event.setdefault("hook_event_name", "PreToolUse")
        event["session_id"] = session
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.state, HOME=self.state)
        result = subprocess.run(["bash", str(HOOK)], input=json.dumps(event), text=True,
                                capture_output=True, env=env, cwd=str(REPO))
        return (result.stdout or "").strip()

    @staticmethod
    def denied(out: str) -> bool:
        # `{}` IS the allow envelope. Reading empty output as "still denied" is a misreading
        # this suite has made before, so the test asks for the deny token explicitly.
        return "permissionDecision" in out or '"deny"' in out

    TRAVERSE = {"tool_name": "Bash",
                "tool_input": {"command": "jq '.items[0].name' response.json"}}

    def read(self, path: str) -> dict:
        return {"tool_name": "Read", "tool_input": {"file_path": path}}

    def test_NON_VACUITY_traversal_with_nothing_on_record_is_denied(self) -> None:
        """The control. Without it every cell below could pass on a clause that never fires."""
        self.assertTrue(self.denied(self.send(self.TRAVERSE, "s1")))

    def test_TEETH_a_host_read_of_the_same_file_licenses_the_traversal(self) -> None:
        self.send(self.read("response.json"), "s2")
        self.assertFalse(self.denied(self.send(self.TRAVERSE, "s2")),
                         "reading the file IS looking at its structure")

    def test_TEETH_a_read_of_another_file_does_not_license(self) -> None:
        """Separates a subject that crossed surfaces from a guard that went vacuous."""
        self.send(self.read("other.json"), "s3")
        self.assertTrue(self.denied(self.send(self.TRAVERSE, "s3")))

    def test_TEETH_writing_the_file_is_not_looking_at_it(self) -> None:
        self.send({"tool_name": "Write",
                   "tool_input": {"file_path": "response.json", "content": "{}"}}, "s4")
        self.assertTrue(self.denied(self.send(self.TRAVERSE, "s4")))

    def test_TEETH_the_original_jq_guard_still_discharges(self) -> None:
        """Composition must not cost the covering it composed with."""
        self.send({"tool_name": "Bash",
                   "tool_input": {"command": "jq 'keys' response.json"}}, "s5")
        self.assertFalse(self.denied(self.send(self.TRAVERSE, "s5")))

    def test_the_subject_reading_has_exactly_one_owner(self) -> None:
        """`subject.on` is interpreted in one place. Three call sites needed it and each was a
        candidate to spell the rule again; a second spelling is how the writer and the checker
        drift apart."""
        text = (PLUGIN / "keel" / "clauses.py").read_text(encoding="utf-8")
        dispatch = (PLUGIN / "keel" / "dispatch.py").read_text(encoding="utf-8")
        self.assertEqual(text.count("def subject_fields"), 1)
        self.assertIn("C.subject_fields(spec)", dispatch)

    def test_the_check_can_fail(self) -> None:
        """Disarm the multi-surface subject: the guard still matches on the Read, but the key
        it derives is no longer the file, so the discharge lands on a different row and the
        traversal is denied again. That is the exact silent failure this change exists to
        avoid, and it is what the cell above would NOT have caught on its own.
        """
        smoke_replace(
            self, PLUGIN / "keel" / "clauses.py",
            b'    if isinstance(on, str):\n        return [on] if on else []\n'
            b'    return [f for f in on if isinstance(f, str) and f]',
            b'    if isinstance(on, str):\n        return [on] if on else []\n'
            b'    return [f for f in on if isinstance(f, str) and f][:1]',
            "tests.test_subject_across_surfaces.SubjectCrossesSurfaces."
            "test_TEETH_a_host_read_of_the_same_file_licenses_the_traversal",
            "reading the file IS looking at its structure",
        )


if __name__ == "__main__":
    unittest.main()
