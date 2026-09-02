"""U10's guard reaches the host `Read`, and its SUBJECT travels with it.

U10 demands that a JSON document be looked at once a traversal of it has printed null, and its
guard named one program: `jq`. A guard that names programs is monotone in vocabulary
(Coverings.v, Thm 5) -- it is defeated by doing the same act any other way, and looking at a
file is the act with the most ways. The host's own `Read` is that act, and `tool_name` is a
CLOSED enum, so composing over it RETIRES a vocabulary rather than widening one.

What is new here is the subject. U10 keys per FILE, and the two surfaces carry the file in
different fields: the traversal in `tool_input.command` of the PostToolUse event that observed
the null, a Read in `tool_input.file_path`. With a single-field subject the composed guard
extracts "" and discharges nothing -- the guard would be composed over two surfaces while the
subject stayed on one, and the whole change would silently do nothing while reading as done.
So `subject.on` may name several surfaces, read in order by `clauses.subject_fields`.

The occasion is an EFFECT (`report_null`, Theorem 8), observed after the act; the demand it
raises refuses the NEXT call until the guard is seen. So every cell here pays the session's
opening debt, drives the traversal's PostToolUse record, then the guard, then a following call
whose verdict is the answer. The cell that matters most is
`test_TEETH_a_read_of_another_file_does_not_license`: it is what separates "the subject crossed
surfaces" from "the guard went vacuous".
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest

from tests.plant_support import PLUGIN, REPO, smoke_replace
from keel import effects

HOOK = PLUGIN / "hooks" / "dispatch.sh"


def record(**eff) -> dict:
    rec = {n: [] if n in ("files_changed", "files_removed", "remote_ref_moved", "pids_gone",
                          "pids_spawned") else False for n in effects.EFFECTS}
    rec["remote_landed"] = None
    rec.update(eff)
    return rec


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
        env = dict(os.environ, KEEL_STATE_DIR=self.state, HOME=self.state)
        result = subprocess.run(["bash", str(HOOK)], input=json.dumps(event), text=True,
                                capture_output=True, env=env, cwd=str(REPO))
        return (result.stdout or "").strip()

    @staticmethod
    def denied(out: str) -> bool:
        return "permissionDecision" in out or '"deny"' in out

    def bash(self, command: str, session: str, **eff) -> str:
        """A Bash call: its PreToolUse verdict, then its PostToolUse record."""
        out = self.send({"tool_name": "Bash", "tool_input": {"command": command}}, session)
        self.send({"hook_event_name": "PostToolUse", "tool_name": "Bash",
                   "tool_input": {"command": command}, "keel_effect": record(**eff)}, session)
        return out

    def traverse(self, session: str) -> None:
        """The opening debt every session pays, then a traversal that printed null."""
        self.send({"hook_event_name": "SessionStart"}, session)
        for name in ("observed.json", "remote.json"):
            path = os.path.join(self.state, name)
            self.send(self.read(path), session)
            self.send({"hook_event_name": "PostToolUse", "tool_name": "Read",
                       "tool_input": {"file_path": path}}, session)
        self.bash("jq '.items[0].name' response.json", session, report_null=True)

    NEXT = {"tool_name": "Bash", "tool_input": {"command": "echo next"}}

    def read(self, path: str) -> dict:
        return {"tool_name": "Read", "tool_input": {"file_path": path}}

    def test_NON_VACUITY_a_null_traversal_refuses_the_next_call(self) -> None:
        """The control. Without it every cell below could pass on a clause that never fires."""
        self.traverse("s1")
        out = self.send(self.NEXT, "s1")
        self.assertTrue(self.denied(out))
        self.assertIn("U10", out)
        self.assertIn("`response.json`", out, "the refusal must name the file it is keyed on")

    def test_TEETH_a_host_read_of_the_same_file_licenses_the_traversal(self) -> None:
        self.traverse("s2")
        self.assertFalse(self.denied(self.send(self.read("response.json"), "s2")))
        self.assertFalse(self.denied(self.send(self.NEXT, "s2")),
                         "reading the file IS looking at its structure")

    def test_TEETH_a_read_of_another_file_does_not_license(self) -> None:
        """Separates a subject that crossed surfaces from a guard that went vacuous. The Read
        itself is never refused -- a host read cannot be the act -- but it pays nothing, so the
        next act is refused exactly as before."""
        self.traverse("s3")
        self.assertFalse(self.denied(self.send(self.read("other.json"), "s3")))
        self.assertTrue(self.denied(self.send(self.NEXT, "s3")))

    def test_TEETH_writing_the_file_is_not_looking_at_it(self) -> None:
        self.traverse("s4")
        self.assertTrue(self.denied(self.send(
            {"tool_name": "Write", "tool_input": {"file_path": "response.json", "content": "{}"}},
            "s4")))

    def test_TEETH_the_original_jq_guard_still_discharges(self) -> None:
        """Composition must not cost the covering it composed with: a query that printed a
        non-null JSON datum from the same file pays, committed and checked by its effect."""
        self.traverse("s5")
        self.assertFalse(self.denied(self.bash("# keel-guard: U10\njq 'keys' response.json", "s5",
                                               report_structured=True)))
        self.assertFalse(self.denied(self.send(self.NEXT, "s5")))

    def test_TEETH_a_committed_query_that_printed_nothing_structured_pays_nothing(self) -> None:
        self.traverse("s6")
        self.assertFalse(self.denied(self.bash("# keel-guard: U10\njq .name response.json", "s6",
                                               report_null=True)))
        self.assertTrue(self.denied(self.send(self.NEXT, "s6")), "a broken commitment spent nothing")

    def test_the_subject_reading_has_exactly_one_owner(self) -> None:
        """`subject.on` is interpreted in one place. Three call sites needed it and each was a
        candidate to spell the rule again; a second spelling is how the writer and the checker
        drift apart."""
        text = (PLUGIN / "keel" / "clauses.py").read_text(encoding="utf-8")
        dispatch = (PLUGIN / "keel" / "dispatch.py").read_text(encoding="utf-8")
        self.assertEqual(text.count("def subject_fields"), 1)
        self.assertIn("C.subject_fields(spec)", dispatch)

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red
        """Disarm the multi-surface subject: the guard still matches on the Read, but the key
        it derives is no longer the file, so the discharge lands on a different row and the
        next call is refused again. That is the exact silent failure this change exists to
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
