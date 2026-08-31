"""A covering over the command string must be an INVOCATION, or say why it cannot be.

WHY THIS LAW EXISTS -- the defect it was written against, reproduced on THIS table before the
fix, driven through the production predicate:

    A01  LICENSES  "echo 'first; git status'"
    A03  LICENSES  "echo 'remember: ; git fetch origin'"
    T02  LICENSES  "grep -rn '; git ls-remote' notes.md"
    U13  LICENSES  "echo 'tip: ; git apply --check p.diff'"
    U09  LICENSES  'cat <<EOF\\n; git rev-parse --verify main\\nEOF'

Those are DISCHARGES. An agent that never ran `git status` but echoed the phrase was licensed to
push. A false discharge spends the guard; a false activation only interrupts -- so this is the
asymmetric direction. A MISSED activation belongs to the same expensive class, because the costly
act then proceeds with its guard removed: `bash -c 'git push origin main'` did not fire A01 while
the identical plain push did.

The cause was not a missing splitter. `segments()` was already quote-aware. The patterns carried
their own `(^|&&|;|\\|)` separator alternation -- a second spelling of the splitter's own job --
and that copy matched a `;` INSIDE a quoted string. `scope: "segment"` existed and was MEASURED
not to close it, because the duplicate lives in the pattern, not in the router.

So the rule is structural: what ran is decided by the invocation (`kind: program`, matching the
leading argv of a segment), and text may only narrow WHICH VARIANT matched (`then_matches`,
evaluated inside that segment alone). A clause that cannot be expressed that way is admissible,
but it must SAY SO in `why_no_program`, naming what was tried -- the shape the merged Swale
loader uses for a row carrying neither `construction` nor `why_none`.
"""
from __future__ import annotations

import json
import unittest

from tests.plant_support import PLUGIN, smoke_replace

from keel import clauses as C

CLAUSES_JSON = PLUGIN / "keel" / "clauses.json"


def _raw() -> list[dict]:
    return json.loads(CLAUSES_JSON.read_text(encoding="utf-8"))


def _event(command: str) -> dict:
    return {"tool_name": "Bash", "hook_event_name": "PreToolUse",
            "tool_input": {"command": command}, "session_id": "s"}


class EveryCommandCoveringIsAnInvocationOrSaysWhyNot(unittest.TestCase):
    def test_no_clause_reads_the_command_as_text_without_saying_why(self):
        undispositioned = []
        for clause in _raw():
            sides = (clause.get("fingerprint") or clause.get("activated_by") or {},
                     clause.get("discharged_by") or {})
            reads_text = any(s.get("kind") == "regex" and s.get("on") == "tool_input.command"
                             for s in sides)
            if reads_text and not clause.get("why_no_program"):
                undispositioned.append(clause["id"])
        self.assertEqual(undispositioned, [], "clauses matching the raw command as text with no "
                                              f"why_no_program: {undispositioned}")

    def test_why_no_program_is_an_argument_not_a_word(self):
        """An exemption with no reasoning is the suppression that ages silently."""
        exempt = [c for c in _raw() if c.get("why_no_program")]
        self.assertTrue(exempt, "no exemptions to grade -- this cell would pass over nothing")
        for clause in exempt:
            why = clause["why_no_program"]
            self.assertGreater(len(why), 120, f"{clause['id']}: too short to be an argument")
            self.assertIn("Tried", why, f"{clause['id']}: does not name what was tried")

    def test_TEETH_a_mention_never_discharges(self):
        """The five recorded false discharges, driven through the production predicate."""
        by = {c["id"]: c for c in _raw()}
        for cid, command in (("A01", "echo 'first; git status'"),
                             ("A03", "echo 'remember: ; git fetch origin'"),
                             ("T02", "grep -rn '; git ls-remote' notes.md"),
                             ("U13", "echo 'tip: ; git apply --check p.diff'"),
                             ("U09", "cat <<EOF\n; git rev-parse --verify main\nEOF")):
            got = C._predicate(by[cid].get("discharged_by") or {}, _event(command))
            self.assertIsNot(got, True, f"{cid} discharged on a MENTION: {command!r}")

    def test_NON_VACUITY_the_real_guards_still_discharge(self):
        """Refusing everything would satisfy the cell above and destroy the table."""
        by = {c["id"]: c for c in _raw()}
        for cid, command in (("A01", "git status --short"), ("A03", "git fetch origin"),
                             ("T02", "git ls-remote origin"),
                             ("U13", "git apply --check p.diff")):
            got = C._predicate(by[cid].get("discharged_by") or {}, _event(command))
            self.assertIs(got, True, f"{cid} refused a REAL guard: {command!r}")

    def test_a_missed_activation_is_the_expensive_direction_too(self):
        """Seven characters of prefix walked any command past the whole table."""
        by = {c["id"]: c for c in _raw()}
        self.assertIs(C._predicate(by["A01"]["fingerprint"],
                                   _event("bash -c 'git push origin main'")), True,
                      "a push through a shell escaped the fence")
        self.assertIs(C._predicate(by["A01"]["fingerprint"],
                                   _event("git push origin main")), True)
        self.assertIsNot(C._predicate(by["A01"]["fingerprint"],
                                      _event("echo 'git push'")), True,
                         "a MENTION fired: the shell branch must need a shell INVOKED with -c")

    def test_an_unclassifiable_option_refuses_rather_than_forging_a_subcommand(self):
        """`npm --prefix test install` read as ['npm', 'test'] -- a run that ran no tests."""
        for command in ("npm --prefix test install", "node --require test app.js",
                        "cargo --config test build", "deno --allow-read test serve.ts"):
            self.assertEqual(len(C.leading_argv(command)), 1,
                             f"forged a subcommand from an option value: {command!r}")
        for command, argv in (("npm test", ["npm", "test"]), ("cargo test", ["cargo", "test"]),
                              ("npm --silent test", ["npm", "test"]),
                              ("git --no-pager log", ["git", "log"]),
                              ("git -C /tmp status", ["git", "status"])):
            self.assertEqual(C.leading_argv(command), argv, command)

    def test_a_delegated_run_is_the_same_invocation_in_every_ecosystem(self):
        """`python3 -m pytest` normalised and `uv run pytest` did not -- one invocation, two
        readings, differing only in that one route happened to be CPython's."""
        for command in ("python3 -m pytest -q", "pytest -q", "uv run pytest",
                        "poetry run pytest -q", "pipenv run pytest"):
            self.assertEqual(C.leading_argv(command), ["pytest"], command)

    def test_a_heredoc_body_is_not_a_command(self):
        self.assertEqual(C.segments("cat <<EOF\n; git push\nEOF"), ["cat <<EOF"])
        self.assertEqual(C.segments("cat <<'EOF'\n; git push\nEOF\ngit status"),
                         ["cat <<'EOF'", "git status"])

    def test_the_subcommand_is_the_first_non_option_token(self):
        """`git commit -m push` must not read as `git push` -- that would be a false licence."""
        self.assertEqual(C.leading_argv("git commit -m push"), ["git", "commit"])
        self.assertEqual(C.leading_argv("git -C /tmp status"), ["git", "status"])
        self.assertEqual(C.leading_argv("git push -u origin main"), ["git", "push"])

    def test_the_check_can_fail(self) -> None:
        # The fault is the historical one this law closed, restored as a DATA edit to the table
        # the law reads -- not a special case wired to this test's own input. A01's discharge was
        # a regex over the raw command carrying its own `(^|&&|;|\|)` alternation, and that
        # alternation matched a `;` inside a quoted string, so `echo 'first; git status'`
        # DISCHARGED the push guard. Planting it back must reopen exactly this law.
        smoke_replace(
            self, CLAUSES_JSON,
            b'"discharged_by": {\n      "kind": "program",\n      "on": "tool_input.command",\n'
            b'      "argv": [\n        [\n          "git",\n          "status"\n        ]\n'
            b'      ]\n    }',
            b'"discharged_by": {\n      "kind": "regex",\n      "on": "tool_input.command",\n'
            b'      "pattern": "(^|&&|;|\\\\|)\\\\s*git\\\\s+status\\\\b"\n    }',
            "tests.test_invocation_coverings.EveryCommandCoveringIsAnInvocationOrSaysWhyNot."
            "test_no_clause_reads_the_command_as_text_without_saying_why",
            "with no why_no_program: ['A01']")


if __name__ == "__main__":
    unittest.main()
