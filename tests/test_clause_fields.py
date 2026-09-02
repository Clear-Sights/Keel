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

import ast
import json
import re
import tempfile
import unittest
from pathlib import Path

from tests.plant_support import PLUGIN, REPO, dispatch_event, record, smoke_replace

CLAUSES = PLUGIN / "keel" / "clauses.json"


def _code_only(source: str) -> str:
    """`source` with comments and DOCSTRINGS blanked -- not every string literal.

    `_mentions` looks for a field as a QUOTED literal, and `_sources` handed it whole files, so a
    field named only in a runtime comment counted as read by the dispatcher. That is the one
    exemption this module must never grant: it is how a field nothing consumes gets treated as
    consumed, and the rule below then permits a test to reason from it.

    ONLY comments and docstrings are removed, and the distinction is the whole point. A first
    draft blanked every string constant and broke the check: `costly`, `waiver`, `window` and
    `occasion` are read as `data.get("costly")` -- quoted literals in live code, which is exactly
    the form `_mentions` is built to find. Blanking those made four fields look unread and
    reddened four tests. A docstring is a string that stands alone as a statement; a dict key is
    not, and stays.

    THE LIMIT THIS LEAVES, stated because it errs toward a silent pass rather than a noisy one.
    Blanking prose still leaves code that is compiled but UNREACHABLE: `if False:
    row.get("costly")` is code, so a field named only there counts as read by the dispatcher.
    Reachability is not a question a source scan answers. What bounds it is that the shipped
    runtime contains no such branch -- `test_no_dead_branch_hides_a_field_read` asserts that, so
    the gap is measured rather than assumed empty, and reddens the moment one appears.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source
    lines = source.splitlines(keepends=True)
    starts = [0]
    for line in lines:
        starts.append(starts[-1] + len(line))
    out = list(source)
    for node in ast.walk(tree):
        # A bare string expression: a docstring, or prose parked as a statement.
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str) \
                and getattr(node.value, "end_lineno", None) is not None:
            begin = starts[node.value.lineno - 1] + node.value.col_offset
            finish = min(starts[node.value.end_lineno - 1] + node.value.end_col_offset, len(out))
            for index in range(begin, finish):
                if out[index] != "\n":
                    out[index] = " "
    blanked = "".join(out)
    kept = []
    for line in blanked.splitlines(keepends=True):
        hash_at = line.find("#")
        kept.append(line[:hash_at] + "\n" if hash_at != -1 else line)
    return "".join(kept)


def _sources(root: Path) -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(root.rglob("*.py"))
                     if "__pycache__" not in p.parts)


ANNOTATION_ONLY_RECORD = Path(__file__).resolve().parent / "annotation-only-fields.tsv"


def annotation_only_fields() -> list[str]:
    """The clause fields no code reads, declared with a reason each.

    DELIBERATELY NOT A PYTHON LITERAL. `_sources` reads every `*.py` under tests/, and
    `_mentions` looks for the field as a quoted literal -- so writing this list in a test module
    would make every name on it "mentioned by the suite" and empty the very set it declares. The
    record is a TSV for that reason, and the reason is here so nobody helpfully inlines it.
    """
    rows = [line.split("\t") for line in
            ANNOTATION_ONLY_RECORD.read_text(encoding="utf-8").strip().splitlines()]
    assert rows and rows[0][0] == "FIELD", f"header changed: {rows[:1]}"
    assert all(len(r) == 2 and r[1].strip() for r in rows[1:]), (
        "every annotation-only field carries the reason it is prose")
    return sorted(row[0] for row in rows[1:])


def _mentions(body: str, field: str) -> bool:
    """The field as a QUOTED literal, never a bare substring.

    A bare substring reports `_activation` as read because a module mentions the FILENAME
    `test_c08_activation.py`. That false positive would have exempted a dead field from the rule
    below, which is the one thing this must not do.
    """
    return re.search(r"""["']%s["']""" % re.escape(field), body) is not None



def _denying_clause(command: str, session: str, state: str) -> str | None:
    """The clause id that denied this command through the REAL dispatcher, or None."""
    body = dispatch_event({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                           "session_id": session, "cwd": "/tmp",
                           "tool_input": {"command": command}}, state)
    reason = (body.get("hookSpecificOutput") or {}).get("permissionDecisionReason") or ""
    found = re.search(r"\[([A-Z]\d\d(?:-[a-z-]+)?)\]", reason)
    return found.group(1) if found else None



def _drive_event(event: dict, session: str, state: str) -> dict:
    return dispatch_event({**event, "session_id": session, "cwd": "/tmp"}, state)


def _clauses_at_stop(session: str, state: str, keel_effect: dict | None = None) -> set:
    """EVERY clause id named in this session's Stop block, through the REAL dispatcher.

    A set, not the first match: one Stop can report several undischarged demands, and reading
    only the first makes the answer depend on which clause happens to sort earliest. `git push`
    raises A01's demand as well as arming T02, so a first-match reading of the armed session
    returns A01 and says nothing about the clause under test.
    """
    stop = {"hook_event_name": "Stop", "session_id": session, "cwd": "/tmp",
            "last_assistant_message": "done"}
    if keel_effect is not None:
        stop["keel_effect"] = keel_effect
    reason = dispatch_event(stop, state).get("reason") or ""
    return set(re.findall(r"\[([A-Z]\d\d(?:-[a-z-]+)?)\]", reason))


def _fields() -> list[str]:
    rows = json.loads(CLAUSES.read_text(encoding="utf-8"))
    return sorted({key for row in rows for key in row})


class NoTestAssertsFromWhatTheProductIgnores(unittest.TestCase):
    def setUp(self) -> None:
        self.fields = _fields()
        self.runtime = _code_only(_sources(PLUGIN))
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

    # The clause fields no code reads. Authored prose beside a row is legitimate -- this is the
    # list of what is allowed to be prose, and adding to it is a decision someone states here.
    ANNOTATION_ONLY = annotation_only_fields()

    def test_no_dead_branch_hides_a_field_read(self) -> None:
        """The bound on `_code_only`'s remaining limit, measured rather than assumed.

        A clause field named only inside `if False:` would count as read by the dispatcher, and
        no source scan can tell the difference. What CAN be established is that the runtime holds
        no statically dead branch at all, which is what makes that gap empty here.
        """
        dead = []
        for path in sorted(PLUGIN.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if not isinstance(node, (ast.If, ast.While)):
                    continue
                test = node.test
                if (isinstance(test, ast.Constant) and not test.value) or (
                        isinstance(test, ast.Name) and test.id == "False"):
                    dead.append(f"{path.relative_to(PLUGIN)}:{node.lineno}")
        self.assertEqual(
            [], dead,
            f"the runtime carries a statically dead branch: {dead}. A clause field named only "
            f"inside one is counted as read by the dispatcher by the rule above, and no source "
            f"scan can tell the difference. Either remove the branch, or rewrite the limit "
            f"stated on `_code_only`, which says this set is empty.")

    def test_the_fields_nothing_reads_are_named(self) -> None:
        """Authored prose beside a row is legitimate. Being unable to list it is not.

        This asserted `assertIsInstance(prose, list)` over a value built by `sorted(...)`, which
        returns a list always: it could not fail, and the naming it is named for happened only in
        a print nobody reads. So a new field that no code touches -- the exact shape that let
        `_quarantine_reason` keep a live double-denial green -- was admitted silently.

        The list is now DECLARED, and both directions fail: a new unread field is not on it, and
        a field that gains a reader must come off it. Neither is a defect; both are decisions
        that have to be stated rather than absorbed.
        """
        prose = sorted(f for f in self.fields
                       if not _mentions(self.runtime, f) and not _mentions(self.suite, f))
        print(f"\nDENOMINATOR subject=clause-fields total={len(self.fields)} "
              f"annotation-only={len(prose)} {prose}")
        self.assertEqual(
            sorted(self.ANNOTATION_ONLY), prose,
            "the set of clause fields no code reads has changed. A field that appeared here is "
            "read by nothing -- name it in tests/annotation-only-fields.tsv with its reason, or "
            "give it a reader. A field that disappeared now has one, so take it off the list.")

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

    def test_activation_is_observed_and_not_merely_declared(self) -> None:
        """Drive a session with and without the activating occasion, and watch the difference.

        The rule above compares two DECLARED JSON fields against a tuple this class writes, and
        its sibling searches dispatch.py for a guard string. Neither sends an activation event or
        observes a demand appearing, so `activated_by` could be ignored by the runtime entirely
        and all of them stay green -- in a class whose docstring is about a field that LIES.

        T02 is driven here because its activation is a plain observable: a remote ref that
        MOVED arms it -- whatever program moved it -- and a Stop after which no ref moved must
        not raise its demand. Two sessions, identical but for the moved ref, must differ -- and
        the assertion runs in BOTH directions, so a dispatcher that raises the demand always, or
        never, fails.
        """
        moved = {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                 "tool_input": {"command": "git push origin main"},
                 "keel_effect": record(remote_ref_moved=["refs/remotes/origin/main"])}
        unlanded = {"remote_ref_moved": ["main"], "remote_landed": False}
        quiet = {"remote_ref_moved": [], "remote_landed": True}

        with tempfile.TemporaryDirectory(prefix="keel-activation-") as state:
            _drive_event({"hook_event_name": "PostToolUse", "tool_name": "Bash",
                          "tool_input": {"command": "echo hello"}, "keel_effect": record()},
                         "activation-unarmed", state)
            unarmed = _clauses_at_stop("activation-unarmed", state, keel_effect=quiet)
            _drive_event(moved, "activation-armed", state)
            armed = _clauses_at_stop("activation-armed", state, keel_effect=unlanded)

        self.assertNotIn(
            "T02", unarmed,
            "a Stop with no activating occasion raised T02's demand anyway, so `activated_by` "
            f"is not being honoured: the clause fires at every ending rather than after a "
            f"remote ref moved. Stop named {sorted(unarmed)}")
        self.assertIn(
            "T02", armed,
            f"a Stop after a remote ref moved did not raise T02's demand (Stop named "
            f"{sorted(armed)}), so the activation this clause declares never arms it")

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
