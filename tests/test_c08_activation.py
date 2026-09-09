"""C08's occasion is a PASS the act PRINTED, keyed on the checker that printed it.

The occasion used to be a checker INVOCATION matched by name (`pytest`, `unittest`, `*check*.py`),
and a shell variable assignment satisfied it: `F=plugin/makoto/checks/writeThrashRevert.py`
contains "check" and ends `.py`, so it both activated the clause AND became the obligation's
key. Nothing can ever discharge such a row, because it names no checker that can be run.
Measured in one live session before the fix: 114 C08 demand rows, of which 19 were keyed on a
token containing `=`, spread over 18 distinct never-dischargeable subjects.

The occasion is now name-agnostic: a `report_pass` datum in the call's output (Theorem 8), so a
checker under any name activates it and an assignment that prints nothing cannot. The KEY is
still read from the command, because a PASS and the failing run that pays for it must pair on
the checker's identity. The first plausible invocation owns the key, past environment prefixes
and shell wrappers. Output plumbing and control words yield no key -- and a keyed activation
with no key is skipped by the dispatcher rather than recorded under an empty subject.
"""
from __future__ import annotations

import tempfile
import unittest

from tests.plant_support import PLUGIN, record, smoke_replace
from keel import clauses as C
from keel.dispatch import _watch_standing
from keel.ledger import Ledger

INVOCATIONS = [
    "python3 -m pytest -q tests/",
    "pytest -q",
    "python3 -m unittest tests.test_engine",
    "python3 tools/check_schema.py",
    "./verify.sh",
    "python3 $SP/check_equiv.py",
    "export PYTHONPATH=/x; python3 -m pytest tests/",
    "PYTHONWARNINGS=error pytest -q",
]
LOOKALIKES = [
    "F=plugin/makoto/checks/writeThrashRevert.py",
    "M=$SP/plugin_mut/makoto/checks/verifierExitMasking.py",
    "T=plugin/makoto/checks/canonFingerprints.py",
    "F=tools/check_schema.py",
]


def c08() -> C.Clause:
    for clause in C.load_default():
        if clause.id.startswith("C08"):
            return clause
    raise AssertionError("C08 is not in the shipped clause table")


def passed(command: str) -> dict:
    """A PostToolUse event whose act printed a passing report, as the observer records it."""
    return {"hook_event_name": "PostToolUse", "tool_name": "Bash",
            "tool_input": {"command": command}, "keel_effect": record(report_pass=True)}


class OccasionIsAPrintedPass(unittest.TestCase):
    def _activates(self, command: str) -> bool:
        return C._base_predicate(c08().activated_by, passed(command)) is True

    def test_TEETH_a_printed_pass_activates_under_any_name(self) -> None:
        for command in INVOCATIONS:
            with self.subTest(command=command):
                self.assertTrue(self._activates(command))
                self.assertTrue(C.event_key(c08().activated_by, passed(command)),
                                "a real checker run must yield a key to pair its failing run on")

    def test_NON_VACUITY_a_run_that_printed_no_pass_does_not_activate(self) -> None:
        event = passed("pytest -q")
        event["keel_effect"]["report_pass"] = False
        self.assertFalse(C._base_predicate(c08().activated_by, event))

    def test_TEETH_the_key_never_captures_an_assignment(self) -> None:
        """Activation and keying are separate; the key is what an assignment used to poison."""
        for spec in (c08().activated_by["key_from"], c08().discharged_by["key_from"]):
            for command in LOOKALIKES:
                with self.subTest(command=command, on=spec["on"]):
                    self.assertEqual("", C.event_key({"key_from": spec},
                                                     {"tool_input": {"command": command}}))
                    self.assertEqual("pytest", C.event_key({"key_from": spec}, passed("X=1 pytest -q")))

    def test_the_key_is_the_checker_past_its_environment(self) -> None:
        spec = {"key_from": c08().activated_by["key_from"]}
        for command, key in (("PYTHONWARNINGS=error pytest -q", "pytest"),
                             ("export PYTHONPATH=/x; python3 -m pytest tests/", "pytest"),
                             ("python3 tools/check_schema.py", "tools/check_schema.py")):
            self.assertEqual(key, C.event_key(spec, {"tool_input": {"command": command}}))

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red
        """Reverse shell order again, and the first-checker regression must go red."""
        smoke_replace(
            self, PLUGIN / "keel" / "clauses.py",
            b'for segment in _effects._segments(command):',
            b'for segment in reversed(_effects._segments(command)):',
            "tests.test_c08_activation.OccasionIsAPrintedPass."
            "test_TEETH_first_plausible_checker_owns_both_keys",
            "first checker lost its identity",
        )

    def test_TEETH_first_plausible_checker_owns_both_keys(self) -> None:
        cases = [
            ('for r in a b c; do git -C "$r" status; done', ""),
            ("pytest -q | tail -3", "pytest"),
            ("grep x file | head", ""),
            ("pytest -q", "pytest"),
            ("python3 -m pytest -q", "pytest"),
            ("FOO=1 pytest -q", "pytest"),
            ("npm run test:unit", "npm run"),
            ("make check", "make check"),
            ("pytest -q; ./verify.sh", "pytest"),
            ("echo PASS; pytest -q | tail -3", "pytest"),
            ("bash -lc 'FOO=1 python3 -m pytest -q | tail -3'", "pytest"),
            ('sh -c "pytest -q"', "pytest"),
            ("FOO='two words' pytest -q", "pytest"),
            ("for r in a b; do pytest -q; done", "pytest"),
            ("pytest -k 'one; two | three' | tail -3", "pytest"),
            ("echo 'PASS; pytest -q' | tail -3", ""),
            ("bash -c 'grep x file | head'", ""),
            ("python3 -c 'print(\"PASS\")'", ""),
        ]
        clause = c08()
        for predicate in (clause.activated_by, clause.discharged_by):
            for command, key in cases:
                with self.subTest(command=command, effect=predicate["effect"]):
                    self.assertEqual(key, C.event_key(predicate, passed(command)),
                                     "first checker lost its identity")

    def test_runner_subcommands_keep_their_identity(self) -> None:
        for runner in "npm yarn pnpm uv make poetry pipenv cargo go bundle rake gem composer gradle mvn".split():
            with self.subTest(runner=runner):
                self.assertEqual(f"{runner} test", C.event_key(c08().activated_by,
                                 passed(f"{runner} test | tail -3")))

    def test_TEETH_plumbing_never_activates_a_demand(self) -> None:
        commands = """
            done fi esac then else do elif tail head cat sort uniq wc tee less more tr cut
            awk sed grep rg echo printf jq ls true false
        """.split() + ["grep x file | head", 'for r in a b c; do git -C "$r" status; done']
        clause = c08()
        with tempfile.TemporaryDirectory() as root:
            ledger = Ledger(root)
            for command in commands:
                with self.subTest(command=command):
                    self.assertEqual("", C.event_key(clause.activated_by, passed(command)))
                    _watch_standing([clause], ledger, passed(command), "c08", "")
                    self.assertEqual([], ledger.open_demands("c08", ""),
                                     "plumbing became a checker obligation")

    def test_pipeline_pass_can_be_paid_by_the_same_checker_without_the_filter(self) -> None:
        clause = c08()
        with tempfile.TemporaryDirectory() as root:
            ledger = Ledger(root)
            _watch_standing([clause], ledger, passed("pytest -q | tail -3"), "c08", "")
            self.assertEqual(["standing:pytest"],
                             [row["subject"] for row in ledger.open_demands("c08", "")])
            failed = passed("./verify.sh")
            failed["keel_effect"] = record(report_fail=True)
            _watch_standing([clause], ledger, failed, "c08", "")
            self.assertEqual(1, len(ledger.open_demands("c08", "")))
            failed["tool_input"]["command"] = "FOO=bad python3 -m pytest -q"
            _watch_standing([clause], ledger, failed, "c08", "")
            self.assertEqual([], ledger.open_demands("c08", ""))

    def test_existing_activation_fixtures_have_payable_keys(self) -> None:
        clause = c08()
        for event in clause.fixtures_activate:
            with self.subTest(event=event):
                self.assertTrue(C._predicate(clause.activated_by, event))
                key = C.event_key(clause.activated_by, event)
                self.assertTrue(key)
                self.assertEqual(key, C.event_key(clause.discharged_by, event))

    def test_invalid_extractors_are_refused(self) -> None:
        for spec in ({"extractor": "unknown"}, {"extractor": None},
                     {"extractor": "checker", "pattern": ".*"},
                     {"extractor": "checker", "group": 1}):
            with self.subTest(spec=spec):
                with self.assertRaises(C.ClauseError) as caught:
                    C._compile({"kind": "effect", "effect": "report_pass",
                                "key_from": {"on": C.COMMAND_FIELD, **spec}}, "C08")
                self.assertEqual("CLAUSE-KEY-FROM-INVALID", caught.exception.code)


if __name__ == "__main__":
    unittest.main()
