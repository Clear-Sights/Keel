"""keel.wire -- the byte boundary: raw hook stdin -> a str the clause table can be run on.

PORTED BY SHAPE from the sibling plugins, not imported. These three ship and version
independently; a shared runtime import would make one plugin's install failure the whole bench's
outage.

WHY THIS EXISTS, IN KEEL'S OWN TERMS
`main()` opened with `sys.stdin.read()`. A hook subprocess inherits no LANG, so CPython enables
UTF-8 mode and gives stdin the `surrogateescape` handler: a host byte that is not valid UTF-8
enters as a lone surrogate rather than raising or being replaced. Nothing rejects it, and it flows
into `_subject`, which hands it to `derive_id` -> `_canon(...).encode()` -> **UnicodeEncodeError**.

That raise lands inside `pre_tool_use`'s per-clause `except Exception: continue`. So the clause
does not deny, does not pass, and does not record anything -- it SILENTLY ABSTAINS, on a command
whose operand happens to carry one bad byte. The isolation is correct in itself (one clause must
never suppress the other twenty-five) but it was never meant to swallow a whole-payload defect
twenty-six times in a row and call the event clean.

Measured, same input, across the bench: Ward hard-denied a benign file citing a parse failure that
was not real, and Makoto failed open with every check skipped. Three plugins, one bad byte, three
different verdicts, none of them about the pending action. Hence a boundary in each.

ONE GUARANTEE: no surrogate code point survives this module.
"""
from __future__ import annotations

import re
import sys

REPLACEMENT = "�"

# The whole surrogate range. The byte decode below routes its own surrogates back through here;
# this regex also closes the other door -- valid UTF-8 whose JSON TEXT carries an unpaired `\ud89d` escape,
# which `json.loads` faithfully turns into a real lone surrogate.
_SURROGATE_RX = re.compile("[\ud800-\udfff]")


def scrub_text(text: str):
    """Return (text with every surrogate code point replaced, number replaced)."""
    if not _SURROGATE_RX.search(text):
        return text, 0
    # `subn` returns (result, count) from ONE pass. The earlier form ran `sub` and then
    # `findall`, scanning the damaged text twice and building a throwaway list of every
    # match to get a number `subn` already had. Measured 2.0x on the repair path.
    return _SURROGATE_RX.subn(REPLACEMENT, text)


def scrub(value):
    """Recursively scrub every str in a parsed JSON value; return (value, total replaced).

    Keys as well as values -- a surrogate in a key reaches the same encoder. Containers are rebuilt
    only when something below them changed, so a clean event comes back as the objects it went in
    as.
    """
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, dict):
        out, total = {}, 0
        for k, v in value.items():
            if isinstance(k, str):
                k, n = scrub_text(k)
                total += n
                if n and (k in out or k in value):
                    # Scrubbing is NOT injective on keys: every surrogate becomes the same U+FFFD,
                    # so two genuinely different damaged keys collapse onto one name and the plain
                    # assignment below dropped the earlier one's VALUE on the floor without a word.
                    # `wire.scrub({"\ud800": 1, "\ud801": 2})` returned `({'\ufffd': 2}, 2)` -- a
                    # count of 2 repairs next to a dict that had lost a field. This module's one
                    # promise is that repair is on the record; silently deleting a field is the
                    # opposite of that, and the field could be `tool_input`. The suffix keeps both
                    # values reachable and keeps the collision visible in the persisted row.
                    # Tested against `value` as well as `out` so a CLEAN key later in the dict
                    # keeps its own name rather than being overwritten by a repaired one.
                    suffix = 2
                    while f"{k}~{suffix}" in out or f"{k}~{suffix}" in value:
                        suffix += 1
                    k = f"{k}~{suffix}"
            v, n = scrub(v)
            total += n
            out[k] = v
        return (out, total) if total else (value, 0)
    if isinstance(value, list):
        items, total = [], 0
        for item in value:
            item, n = scrub(item)
            total += n
            items.append(item)
        return (items, total) if total else (value, 0)
    return value, 0


def read_stdin():
    """Read the hook envelope as BYTES and decode it to a surrogate-free str; (text, repaired).

    Reading `.buffer` is the load-bearing part: it takes the decode away from whatever error
    handler the ambient locale installed and puts it under this module's own control, where every
    surrogate it produces is scrubbed before the value is returned.
    """
    buffer = getattr(sys.stdin, "buffer", None)
    if buffer is not None:
        try:
            data = buffer.read()
        except (AttributeError, ValueError, OSError):
            data = None
        if data is not None:
            return _decode_counting(data)
    return scrub_text(sys.stdin.read() or "")


def _decode_counting(data: bytes):
    """Decode `data` as UTF-8, returning (text, number of undecodable BYTES repaired).

    Strict first, on purpose: a clean payload reports zero repairs by construction, so the count can
    never be inflated by a U+FFFD the host legitimately sent. A number that cries wolf gets ignored,
    and takes the next real one with it.
    """
    # "utf-8-sig", not "utf-8": a UTF-8 BOM (b"\xef\xbb\xbf") on the envelope strict-decodes
    # to a leading U+FEFF that json.loads then REFUSES ("Unexpected UTF-8 BOM (decode using
    # utf-8-sig)"), so a structurally perfect payload took `main`'s unreadable_event path --
    # NOT-EVALUABLE, the whole clause table skipped for that call, the action allowed, and the
    # recorded reason ("unreadable event") false of the payload. Reproduced two-sided against
    # a BOM-prefixed PreToolUse envelope: makoto parses, keel refused. Makoto fixed this
    # at the wire layer and Ward at its dispatch layer (`raw.lstrip("﻿")`); keel was
    # the one door in the family that never got it. A BOM is a legitimate encoding artifact,
    # not damage, so it does not count as a repair.
    try:
        return scrub_text(data.decode("utf-8-sig"))
    except UnicodeDecodeError:
        pass
    # `surrogateescape`, then scrub -- NOT `errors="replace"`.
    #
    # `replace` emits ONE U+FFFD per malformed RUN, so a truncated three-byte sequence like
    # b"\xe2\x82" (two undecodable bytes) reported 1, and the field is called "bytes repaired".
    # An observability number whose name does not match its arithmetic is the kind of thing that
    # gets trusted right up until someone reconciles two counts and cannot.
    #
    # `surrogateescape` maps each undecodable BYTE to exactly one lone surrogate, so counting the
    # surrogates counts bytes -- which is what the field says. Scrubbing them immediately is what
    # keeps the module's one guarantee: no surrogate leaves here. It also retires the
    # `data.count(b"\xef\xbf\xbd")` correction entirely, since surrogateescape never touches a
    # U+FFFD the host legitimately sent.
    return scrub_text(data.decode("utf-8-sig", errors="surrogateescape"))
