"""Capture the SHAPE of the payloads this host actually sends.

Keel makes a claim about the host in the one place it matters most: C08 is parked because
`tool_response` carries no exit status, and that waiver rests on 71 recorded PostToolUse
payloads in a sibling plugin's database. That database now holds six events and none of them
is a PostToolUse. The corpus is gone, and Keel cannot regenerate it -- it journals its own
DECISIONS and never the payloads it was given, and `eval/corpus/*.jsonl` are hand-authored
fixtures, which is a different kind of evidence entirely and has already been misread as this
one once. So the clause that is not enforced is parked on a measurement nobody can repeat,
with a date on it after which it enforces and, by its own numbers, blocks every ending.

This is the missing instrument. It records SHAPE, never content: which keys `tool_response`
carries, of what type, and whether each is truthy -- never a command, never stdout, never a
path. That is a design decision and not a redaction: the question C08 needs answered is a
question ABOUT the shape ("does any key carry an exit status"), so the instrument that answers
it has no reason to hold the values, and a shape corpus can be committed and published where a
payload corpus never could. A recorder that must be scrubbed before it can be read is one
scrub away from leaking.

OFF BY DEFAULT, and the default is the safe one: with `KEEL_RECORD_SHAPES` unset this writes
nothing at all. A capture that runs unasked would turn every user of the plugin into a subject.

Never raises. A recorder that can break the hook is worse than no recorder -- it would fail a
call in order to observe it.
"""
from __future__ import annotations

import json
import os
import pathlib
from datetime import datetime, timezone
from typing import Any

SHAPES_FILE = "payload_shapes.jsonl"
ENABLE_ENV = "KEEL_RECORD_SHAPES"

# Above this, a session's capture stops rather than growing without bound. A recorder that can
# fill a disk is a recorder that takes the session down, which is the same fault as raising.
MAX_ROWS = 20000


def enabled() -> bool:
    value = os.environ.get(ENABLE_ENV, "")
    return value.strip() not in ("", "0", "false", "no")


def _shape(value: Any) -> dict[str, Any]:
    """A description of `value` carrying no part of it.

    Strings report their length and nothing else. `truthy` is kept because it is the whole
    question for a status-like field -- an exit status of 0 and one of 2 are different facts
    and both are present -- and because a key that is always falsy is a key that says nothing.
    """
    described: dict[str, Any] = {"type": type(value).__name__}
    if isinstance(value, str):
        described["len"] = len(value)
    elif isinstance(value, (list, tuple, dict)):
        described["len"] = len(value)
    elif isinstance(value, bool):
        described["value"] = value
    elif isinstance(value, int):
        # An exit status IS an int and IS the subject. Ints are recorded verbatim because a
        # census that reported "an int was here" could not answer the question it exists for.
        described["value"] = value
    described["truthy"] = bool(value)
    return described


def describe(event: dict) -> dict[str, Any]:
    response = event.get("tool_response")
    row: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "hook_event": str(event.get("hook_event_name") or ""),
        "tool_name": str(event.get("tool_name") or ""),
        "response_type": type(response).__name__,
        # Present so a reader can tell "this event carries no tool_response" from "it carries
        # one with no keys". Those are different facts about the host and the second is the
        # one that would make C08 permanently undischargeable.
        "has_response": "tool_response" in event,
    }
    if isinstance(response, dict):
        row["keys"] = {str(k): _shape(v) for k, v in sorted(response.items())}
    elif isinstance(response, str):
        row["keys"] = {}
        row["response_len"] = len(response)
    else:
        row["keys"] = {}
    return row


def record(event: dict, root: Any = None) -> None:
    """Append one shape row. Silent when disabled, and silent on every failure."""
    try:
        if not enabled() or not isinstance(event, dict):
            return
        path = pathlib.Path(root) if root else _default_root()
        path.mkdir(parents=True, exist_ok=True)
        target = path / SHAPES_FILE
        if target.exists():
            with target.open("r", encoding="utf-8") as fh:
                if sum(1 for _ in fh) >= MAX_ROWS:
                    return
        with target.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(describe(event), separators=(",", ":"),
                                sort_keys=True, ensure_ascii=True) + "\n")
    except Exception:
        return


def _default_root() -> pathlib.Path:
    override = os.environ.get(ENABLE_ENV, "").strip()
    if override not in ("", "0", "false", "no", "1", "true", "yes"):
        return pathlib.Path(override)
    from .ledger import state_dir
    return state_dir()
