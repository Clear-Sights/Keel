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
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "plugin"))

from keel import clauses as C          # noqa: E402
from keel import dispatch              # noqa: E402

HOOK_FILES = ("hooks/hooks.json", "hooks/hooks.codex.json")


def _registered(name: str) -> set[str]:
    return set(json.loads((REPO / "plugin" / name).read_text())["hooks"].keys())


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

    def test_an_enforceable_event_is_admitted(self):
        """The other half of the control: _admit is not simply refusing everything."""
        proto = C.load_default()[0]
        admitted = C._admit(dataclasses.replace(proto, event=proto.event))
        self.assertEqual(admitted.event, proto.event)
        self.assertIn(proto.event, C._EVENTS)


if __name__ == "__main__":
    unittest.main()
