"""The three event surfaces must agree, and every routed event must have a decision.

Keel names events in three places, and nothing held them together:

  * `plugin/hooks/hooks.json` -- what the host is asked to send.
  * `dispatch.HANDLERS`       -- what the dispatcher routes when it arrives.
  * `clauses._EVENTS`         -- what a clause is allowed to target.

The third is a strict subset of the other two and the gap was undeclared. Three events --
SubagentStart, UserPromptSubmit, PreCompact -- are registered and routed, but a clause naming
one is refused CLAUSE-EVENT-UNKNOWN. That refusal is not a quiet no-op: a single `_admit`
failure makes the whole table unloadable, and the dispatcher reports an unloadable table as a
deny, so such a clause would deny every tool call rather than simply never fire.

Verified by execution rather than by reading: constructing a clause with event
"SubagentStart" and passing it to `_admit` raises CLAUSE-EVENT-UNKNOWN.

So the gap now has to be a decision. An event that is routed but appears in neither
`_EVENTS` nor `_NON_ENFORCING` turns this red, which is what stops "unenforceable" from being
something a new handler becomes by default.
"""
from __future__ import annotations

import dataclasses
import json
import tempfile
import unittest

from tests.plant_support import PLUGIN, run_dispatcher

from keel import clauses as C          # noqa: E402
from keel import dispatch              # noqa: E402

HOOK_FILES = ("hooks/hooks.json", "hooks/hooks.codex.json")


def _registered(name: str) -> set[str]:
    return set(json.loads((PLUGIN / name).read_text())["hooks"].keys())


class EventSurface(unittest.TestCase):
    def test_every_registered_event_is_routed_and_every_routed_event_registered(self):
        """A hook the host sends nowhere, or a route nothing sends, is dead either way."""
        for name in HOOK_FILES:
            with self.subTest(hooks=name):
                self.assertEqual(
                    _registered(name), set(dispatch.HANDLERS),
                    f"{name} and dispatch.HANDLERS name different events; one of them is "
                    f"asking for or answering an event the other does not know about")

    def test_no_routed_event_is_left_undecided(self):
        """Every routed event either carries enforcement or says why it does not."""
        routed = set(dispatch.HANDLERS)
        decided = set(C._EVENTS) | set(C._NON_ENFORCING)
        undecided = sorted(routed - decided)
        self.assertFalse(
            undecided,
            f"these events are routed by the dispatcher but appear in neither clauses._EVENTS "
            f"nor clauses._NON_ENFORCING: {undecided}. A clause naming one is refused "
            f"CLAUSE-EVENT-UNKNOWN, which makes the table unloadable and denies every tool "
            f"call -- so this cannot be left to default. Either admit it to _EVENTS, or record "
            f"in _NON_ENFORCING why it is bookkeeping rather than an enforcement point.")
        self.assertFalse(
            sorted(decided - routed),
            "an event is declared enforceable or non-enforcing but the dispatcher does not "
            "route it, so the declaration is about nothing")

    def test_the_two_declarations_do_not_overlap(self):
        overlap = sorted(set(C._EVENTS) & set(C._NON_ENFORCING))
        self.assertFalse(overlap, f"{overlap} are declared both enforceable and non-enforcing")

    def test_every_non_enforcing_event_carries_a_reason(self):
        """A bare set would record the fact and lose the argument for it."""
        for event, reason in C._NON_ENFORCING.items():
            with self.subTest(event=event):
                self.assertIsInstance(reason, str)
                self.assertGreater(
                    len(reason.split()), 8,
                    f"{event} is declared non-enforcing without saying why")

    def test_a_clause_targeting_a_non_enforcing_event_is_actually_refused(self):
        """The non-vacuity control: the refusal this whole law is about must be real."""
        proto = C.load_default()[0]
        for event in sorted(C._NON_ENFORCING):
            with self.subTest(event=event):
                probe = dataclasses.replace(proto, id="ZZZ-probe", event=event)
                with self.assertRaises(C.ClauseError) as caught:
                    C._admit(probe)
                self.assertEqual(caught.exception.code, "CLAUSE-EVENT-UNKNOWN")

    def test_every_enforceable_event_is_admitted(self):
        """The other half of the control: _admit is not simply refusing everything.

        This used to build `dataclasses.replace(proto, event=proto.event)` -- which is `proto`
        -- and then assert `proto.event in C._EVENTS`. `proto` comes from `load_default()`,
        which has already put it through `_admit`, so both statements were guaranteed by the
        line that produced the value. It could not fail, and it covered exactly one event: the
        first row's.

        Every event in `_EVENTS` is now admitted, so the control is over the whole set rather
        than over whichever event happens to sort first."""
        proto = C.load_default()[0]
        self.assertTrue(C._EVENTS, "no event is enforceable; the refusal control is vacuous")
        for event in sorted(C._EVENTS):
            with self.subTest(event=event):
                admitted = C._admit(dataclasses.replace(proto, id="ZZZ-probe", event=event))
                self.assertEqual(admitted.event, event)

    def test_every_routed_event_actually_gets_a_decision(self):
        """The module docstring says "every routed event must have a decision". Nothing checked it.

        The two laws above compare DECLARATIONS -- hook-file keys against `HANDLERS` keys, and
        `_EVENTS` against `_NON_ENFORCING`. An event present in both places whose handler raises,
        hangs, or returns something the host cannot read passes all of them. And the dispatcher's
        contract is not "does not crash": it fails OPEN, so a handler that dies prints nothing and
        exits 0, which is indistinguishable from a clean allow unless the exit code and the
        payload are both read.

        Every registered event is therefore SENT, and each must come back with exit 0 and a body
        the host can parse -- `{}` for an allow is a decision; a traceback is not.
        """
        registered = sorted(set(dispatch.HANDLERS))
        self.assertTrue(registered, "no event is routed at all; this law is vacuous")
        with tempfile.TemporaryDirectory(prefix="keel-event-surface-") as state:
            for event in registered:
                with self.subTest(event=event):
                    payload = {"hook_event_name": event, "session_id": f"surface-{event}",
                               "cwd": "/tmp", "tool_name": "Bash",
                               "tool_input": {"command": "echo hello"},
                               "last_assistant_message": "done"}
                    done = run_dispatcher(json.dumps(payload), state, timeout=120)
                    self.assertEqual(0, done.returncode,
                                     f"{event}: dispatcher exited {done.returncode}\n"
                                     f"{done.stderr[-800:]}")
                    self.assertNotIn("Traceback", done.stderr,
                                     f"{event}: the handler raised; keel fails open, so this "
                                     f"reaches the host as a silent allow\n{done.stderr[-800:]}")
                    # `json.loads(done.stdout or "{}")` would turn EMPTY stdout into a valid
                    # empty decision, so a dispatcher that exits 0 and prints nothing at all
                    # satisfied every assertion below. Measured: all eight routed events emit a
                    # body, `{}` at minimum for an allow, so silence on stdout is a fault and
                    # not a shape any of them legitimately takes.
                    self.assertTrue(
                        done.stdout.strip(),
                        f"{event}: the dispatcher printed nothing. Every routed event emits a "
                        f"body -- `{{}}` for an allow -- so an empty stdout is a handler that "
                        f"rendered no decision, not a quiet allow.\n{done.stderr[-800:]}")
                    try:
                        body = json.loads(done.stdout)
                    except json.JSONDecodeError:
                        self.fail(f"{event}: the dispatcher printed something the host cannot "
                                  f"parse, so it rendered no decision: {done.stdout[:400]!r}")
                    # THE ACTUAL PROPERTY, and the reason exit code alone is not enough. Keel
                    # fails OPEN by design: a handler that raises still exits 0 and still prints
                    # a body. What it does NOT do quietly is pass the call -- it says so, in a
                    # systemMessage naming the event and the exception, and on stderr. So the
                    # law is that no routed event comes back UNCHECKED, and the notice keel
                    # already emits is what makes that observable.
                    self.assertNotIn(
                        "WITHOUT BEING CHECKED", json.dumps(body),
                        f"{event}: the handler did not render a decision; keel failed open and "
                        f"said so. This event is registered and routed, so a call arriving on it "
                        f"is passed unchecked.\n{done.stdout[:600]}")
                    self.assertNotIn(
                        "NOT-EVALUABLE, failing open", done.stderr,
                        f"{event}: the dispatcher reported NOT-EVALUABLE for a routed "
                        f"event\n{done.stderr[-800:]}")


if __name__ == "__main__":
    unittest.main()
