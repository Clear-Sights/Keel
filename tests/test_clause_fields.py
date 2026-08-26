"""No test may assert from a clause-table field the shipped dispatcher ignores.

WHY THIS EXISTS. `plugin/keel/clauses.json` carried `_quarantine_reason` on 9 of its 24 rows. It
read as a control -- a clause parked, not firing -- and `tests/test_occasion_algebra.py` reasoned
from it exactly that way, deriving a method named `_live` and asserting that only one declared
overlap had both clauses live.

No code under `plugin/` has ever read that field. Every one of the nine fired. Driven through
`keel.dispatch`, a force-push denied `A01` and then, once its remedy was obeyed, `A03` -- the pair
the table said could not double-deny. The suite was green the whole time, because it was asserting
a property of a field instead of a property of the product.

THE RULE. A field the runtime ignores may exist -- JSON has no comment syntax, and several rows
carry authored prose that belongs beside the row it explains. What it may NOT do is become the
grounds for an assertion. The moment a test reads a field the dispatcher does not, the suite has
started describing a plugin that does not exist, and nothing else in this repository can notice.

WHAT THIS CANNOT SEE, stated rather than left implied. Fields are matched as quoted string
literals in source. A field reached through a variable -- iterating keys, `getattr`, a name built
at runtime -- is invisible here, so this measures the ordinary spelling and says so.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from tests.plant_support import PLUGIN, REPO, smoke_replace

CLAUSES = PLUGIN / "keel" / "clauses.json"


def _sources(root: Path) -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(root.rglob("*.py"))
                     if "__pycache__" not in p.parts)


def _mentions(body: str, field: str) -> bool:
    """The field as a QUOTED literal, never a bare substring.

    A bare substring reports `_activation` as read because a module mentions the FILENAME
    `test_c08_activation.py`. That false positive would have exempted a dead field from the rule
    below, which is the one thing this must not do.
    """
    return re.search(r"""["']%s["']""" % re.escape(field), body) is not None


def _fields() -> list[str]:
    rows = json.loads(CLAUSES.read_text(encoding="utf-8"))
    return sorted({key for row in rows for key in row})


class NoTestAssertsFromWhatTheProductIgnores(unittest.TestCase):
    def setUp(self) -> None:
        self.fields = _fields()
        self.runtime = _sources(PLUGIN)
        self.suite = _sources(REPO / "tests")

    def test_the_check_has_a_subject(self) -> None:
        """An empty table, or a sweep that reads no source, makes every rule below vacuous."""
        self.assertGreater(len(self.fields), 10, f"only {len(self.fields)} clause fields found")
        self.assertTrue(self.runtime.strip(), "no runtime source was read")
        self.assertTrue(self.suite.strip(), "no test source was read")
        read_by_runtime = [f for f in self.fields if _mentions(self.runtime, f)]
        self.assertGreater(
            len(read_by_runtime), 5,
            f"only {len(read_by_runtime)} clause fields are read by the runtime; the sweep has "
            "stopped seeing the dispatcher it is supposed to be comparing against")

    def test_no_field_is_read_by_the_suite_alone(self) -> None:
        stolen = sorted(f for f in self.fields
                        if _mentions(self.suite, f) and not _mentions(self.runtime, f))
        self.assertEqual(
            [], stolen,
            "a test reasons from a clause field the shipped dispatcher never reads, so the suite "
            "is asserting a property of the table instead of a property of the plugin; this is "
            "how `_quarantine_reason` kept a live double-denial green")

    def test_the_fields_nothing_reads_are_named(self) -> None:
        """Authored prose beside a row is legitimate. Being unable to list it is not."""
        prose = sorted(f for f in self.fields
                       if not _mentions(self.runtime, f) and not _mentions(self.suite, f))
        self.assertIsInstance(prose, list)
        print(f"\nDENOMINATOR subject=clause-fields total={len(self.fields)} "
              f"annotation-only={len(prose)} {prose}")

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red
        """Make the suite reason from an annotation, and this must go red naming the rule.

        `_note` is authored prose no code reads. Quoting it in a test module is the whole defect
        in one line: the assertion below would then rest on a field the dispatcher never sees,
        which is exactly what `_quarantine_reason` did for nine clauses.
        """
        smoke_replace(
            self, Path(__file__),
            b'CLAUSES = PLUGIN / "keel" / "clauses.json"',
            # Split so this module never itself contains the quoted field name. Spelling it whole
            # here would make the file trip its own rule, and the plant would have no green run to
            # start from -- the inert-plant failure, arriving through the payload.
            b'CLAUSES = PLUGIN / "keel" / "clauses.json"\nSTOLEN = "_no' + b'te"',
            "tests.test_clause_fields.NoTestAssertsFromWhatTheProductIgnores."
            "test_no_field_is_read_by_the_suite_alone",
            "asserting a property of the table",
        )


class OneClauseDecliningAnotherStaysInStep(unittest.TestCase):
    """U20 declines exactly what A02 claims, and the two spellings must not drift apart.

    `rm -rf ./build` used to raise A02 and then, once its remedy was obeyed, U20 -- one act, two
    unrelated remedies (list what you are deleting; run the test suite). U20 now carries an
    `unless` holding A02's fingerprint, so the bulk deletes A02 owns are no longer U20's occasion,
    while a plain `rm file`, `rm -r dir` and `git reset --hard` still are: the overlap goes, no
    coverage does.

    `clauses.json` is data and cannot reference another row, so that pattern is a COPY -- the
    two-writer shape this repository keeps finding. The copy is legal only because this holds it
    in step: change A02's fingerprint without mirroring it and the overlap silently re-opens,
    which is the failure that got the pair recorded in the first place.
    """

    def test_u20_declines_exactly_what_a02_claims(self) -> None:
        rows = {r["id"]: r for r in json.loads(CLAUSES.read_text(encoding="utf-8"))}
        a02 = rows["A02"]["fingerprint"]["pattern"]
        declined = rows["U20"]["fingerprint"].get("unless") or []
        self.assertIn(
            a02, declined,
            "U20 no longer declines A02's occasion verbatim, so a bulk delete raises both again: "
            "one command, two remedies with nothing in common")


class ActivationIsOnlyDeclaredWhereItIsHonoured(unittest.TestCase):
    """`activated_by` on a clause the dispatcher will never activate does nothing, silently.

    The activation loop in `keel/dispatch.py` opens by skipping every clause whose event is not
    `Stop` or `SubagentStop`. So the field arms a terminal clause -- "the run is ending AFTER a
    push" -- and on any other event it is inert: the loader admits it, no runtime reads it, and
    the clause behaves exactly as if it were absent.

    This was nearly written into U02. Its occasion says the trace is about to RE-LAUNCH a target,
    it has no way to tell a re-launch from a first launch, and `activated_by` says precisely that
    -- arm only once the occasion has already been seen. Declaring it on a `PreToolUse` clause
    would have read like a fix, changed nothing, and left a field that lies, which is the defect
    this file exists for. The check is the difference between finding that out here and finding
    it out from a user.
    """

    ACTIVATABLE = ("Stop", "SubagentStop")

    def test_activation_is_declared_only_on_clauses_that_can_be_activated(self) -> None:
        rows = json.loads(CLAUSES.read_text(encoding="utf-8"))
        inert = sorted(f"{r['id']} (event {r['event']})" for r in rows
                       if r.get("activated_by") and r.get("event") not in self.ACTIVATABLE)
        self.assertEqual(
            [], inert,
            "a clause declares `activated_by` on an event the dispatcher never activates on, so "
            f"the field does nothing; only {list(self.ACTIVATABLE)} are honoured")

    def test_the_check_has_a_subject(self) -> None:
        """Nothing declaring activation makes the rule above vacuous."""
        rows = json.loads(CLAUSES.read_text(encoding="utf-8"))
        declared = [r["id"] for r in rows if r.get("activated_by")]
        self.assertTrue(declared, "no clause declares `activated_by`; nothing was checked")

    def test_the_events_match_the_dispatcher(self) -> None:
        """Read the guard out of the dispatcher rather than trusting this copy of it.

        The tuple above is a second writer for a condition `dispatch.py` already states. It is
        held to the source so that widening activation there without updating here is red, not a
        check quietly enforcing last year's rule.
        """
        source = (PLUGIN / "keel" / "dispatch.py").read_text(encoding="utf-8")
        self.assertIn(
            'if cl.event not in ("Stop", "SubagentStop"):', source,
            "the dispatcher no longer skips non-terminal clauses in its activation loop the way "
            "this module assumes; the set of activatable events has moved")


if __name__ == "__main__":
    unittest.main()
