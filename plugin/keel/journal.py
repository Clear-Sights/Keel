"""keel.journal -- the persisted record: what Keel did, per session, per tool.

WHY THIS EXISTS. Keel hooks PreToolUse, PostToolUse, Stop, SessionStart, SubagentStart and
SubagentStop -- six event families, every one of them evaluated against the clause table -- and
wrote nothing down unless a demand was actually raised. `obligations.jsonl` is a LEDGER, not a log:
it records outstanding obligations, so a session in which every clause passed leaves the state
directory empty, and so does a session in which the plugin never ran at all.

That means the question "did Keel catch anything this session?" had no answer. Not "no" --
UNANSWERABLE, which is strictly worse, because absence-of-record is exactly what a healthy session,
a mis-wired plugin, and an uninstalled plugin all look like. This module's whole job is to make
those three distinguishable.

It is the same law this plugin already applies to its own clause table -- "absence must never read
as green", the reason `dispatch.main` refuses a zero-clause load -- turned around and applied to
the plugin itself. A gate that will not accept an unexplained silence from the session should not
be producing one about itself.

FOUR ROW KINDS, deliberately not five:

  * `session` -- ONE row the first time a session is seen, carrying the clause count. The liveness
    proof, and the reason the log answers "did it run" separately from "did it find anything". A
    row saying `clauses: 0` is a Keel that checked nothing while everyone believes it is on.
  * `deny`    -- a PreToolUse refusal, naming the clause and the subject it is keyed on.
  * `block`   -- a Stop/SubagentStop reconciliation block, naming the unreconciled count.
  * `fault`   -- an event that could not be evaluated, and which way it fell.

There is deliberately NO row per allowed call: a sibling plugin measured that policy and found the
log ran 99%+ noise. A log nobody can read is a log nobody reads.

EVERY ROW NAMES ITS PLUGIN. Ward, Keel and Makoto all register PreToolUse and all three can
deny; the host does not tell the user which one spoke. `plugin` is that name, and the deny reason
on the wire carries the same `keel` prefix, so transcript and log can be joined afterwards.

FAILURE POSTURE: observability, never policy. Every entry point swallows everything. A gate that
denied because its logger could not write would be a worse defect than the missing log.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import time
from datetime import datetime, timezone

PLUGIN = "keel"


def _root(root=None) -> pathlib.Path:
    if root:
        return pathlib.Path(root)
    from .ledger import state_dir
    return state_dir()


def _append(row: dict, root=None) -> None:
    """Append one compact JSON line to `decisions.jsonl`.

    POSIX guarantees atomicity for short append-mode writes (<= PIPE_BUF); a row is far under, so
    concurrent hook processes cannot interleave. `ensure_ascii=True` deliberately -- unlike the
    ledger's canonical form, this writer must never be able to become the encoding failure it
    exists to record.
    """
    path = _root(root)
    path.mkdir(parents=True, exist_ok=True)
    with (path / "decisions.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n")


def _row(event: dict, kind: str, **extra) -> dict:
    return {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "plugin": PLUGIN,
        "kind": kind,
        "session_id": str(event.get("session_id") or ""),
        "agent_id": str(event.get("agent_id") or ""),
        "tool_name": str(event.get("tool_name") or ""),
        "hook_event": str(event.get("hook_event_name") or ""),
        **extra,
    }


def _marker_name(session: str) -> str:
    """A per-session marker filename unique to the session id, not merely derived from it.

    The sanitizer alone was NOT injective: every character outside `[A-Za-z0-9-_]` mapped to `_`,
    so `a/b` and `a?b` -- two different sessions -- produced the same marker, and whichever ran
    second was recorded as already-noted. Its liveness row was lost, which is precisely the row
    this journal exists to guarantee. The digest is taken over the FULL id, so distinct ids cannot
    collide however they were spelled; the readable prefix is kept so a human listing the directory
    can still tell which session a marker belongs to.
    """
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session)[:64]
    return f"{safe}-{hashlib.sha256(session.encode('utf-8')).hexdigest()[:16]}"


_STALE_CLAIM_SECONDS = 60


def _committed(marker: pathlib.Path) -> bool:
    """True iff this marker stands for a row that actually LANDED.

    A marker is created empty and only given a byte once `_append` has returned, so size is the
    difference between "somebody is writing this row" and "this row is on record". Treating the
    bare existence of the marker as proof is what made a failed append permanent: the row never
    landed, the marker outlived it, and every later call short-circuited on it.
    """
    try:
        return marker.stat().st_size > 0
    except OSError:
        return False


def _steal_if_stale(marker: pathlib.Path) -> bool:
    """Take over an UNCOMMITTED claim nobody finished. False if committed, or freshly claimed.

    The recovery path unlinks its marker when `_append` raises -- but `unlink` can itself fail, and
    a process can be killed between the claim and the row. Either way the marker survives with no
    row behind it, and without this the session's liveness row is lost for good. That is silence,
    and this module's contract is that it degrades to RE-NOTING, never to silence.

    The age window is what keeps that recovery from undoing the race fix. Concurrent hook processes
    claim within milliseconds of each other, so a marker younger than the window belongs to a
    sibling that is still working and must be left alone; only one long past that can have been
    abandoned. Re-stamping on takeover keeps two late arrivals from both stealing it.
    """
    try:
        st = marker.stat()
    except OSError:
        return False
    if st.st_size > 0 or (time.time() - st.st_mtime) < _STALE_CLAIM_SECONDS:
        return False
    try:
        os.utime(marker)
    except OSError:
        return False
    return True


def _commit(marker: pathlib.Path) -> None:
    """Mark the claim as standing for a row that landed. Best-effort: an uncommitted marker costs
    one duplicate row a minute from now, which is the cheap direction."""
    try:
        marker.write_text("1")
    except OSError:
        pass


def _claim(marker: pathlib.Path) -> bool:
    """Atomically claim the right to write this session's row. True iff THIS process won it.

    `O_CREAT | O_EXCL`, not `exists()` followed by a write: the latter is a check-then-act race,
    and concurrent hook processes are the NORMAL condition here, not an edge case -- several tool
    calls are in flight at once. Every process that lost that race had still passed the check and
    still appended a row. Measured: 12 concurrent processes produced 12 "once per session" rows.
    The kernel settles it in one syscall instead.

    The directory is created only on the miss, so the common path stays at a single syscall.
    """
    try:
        fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return _steal_if_stale(marker)
    except FileNotFoundError:
        marker.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            return _steal_if_stale(marker)
    os.close(fd)
    return True


def note_session(event: dict, clause_count: int, root=None) -> None:
    """Record ONCE per session that Keel was live, and with how many clauses.

    A marker file per session id is the whole mechanism. An unwritable marker degrades to
    re-noting -- noisy, still correct -- never to silence and never to raising.
    """
    try:
        session = str(event.get("session_id") or "")
        if not session:
            return
        path = _root(root)
        marker = path / "sessions" / _marker_name(session)
        # The stat comes FIRST: the overwhelmingly common case is a session already noted, and
        # that path should cost one syscall -- not an exclusive create on every tool call of
        # every session. `_claim` then settles the genuine first-sighting atomically.
        if _committed(marker):
            return
        if not _claim(marker):
            return
        try:
            _append(_row(event, "session", clauses=int(clause_count)), root=root)
        except Exception:
            # The claim is only worth holding if the row it stands for actually landed. Releasing
            # it on a failed append is what stops one transient write error from permanently
            # suppressing this session's liveness row -- the single row that tells "ran and found
            # nothing" apart from "never installed". Committing the marker first, as this did,
            # made that suppression permanent and silent. Degrading to re-noting on the next call
            # is noisy and still correct, which is the trade this module already declares.
            try:
                marker.unlink()
            except OSError:
                pass
            raise
        # Only now does the marker stand for a row that LANDED. See `_committed`.
        _commit(marker)
    except Exception:
        pass


def note_deny(event: dict, clause_id: str, subject: str, reason: str, root=None) -> None:
    """Record a PreToolUse refusal, naming the clause and the subject it discharges on."""
    try:
        _append(_row(event, "deny", clause_id=clause_id, subject=subject[:200],
                     reason=reason[:400]), root=root)
    except Exception:
        pass


def note_block(event: dict, open_count, clause_ids, root=None) -> None:
    """Record a terminal reconciliation block.

    `open_count` is `None` when the block message stated no count -- which is what an internal
    fault's block looks like. Recorded as `null` rather than coerced to `0`, because `0` is
    already the clean terminal's own answer and the two outcomes must not share a row shape. See
    `dispatch._stated_count`.
    """
    try:
        _append(_row(event, "block",
                     open_count=None if open_count is None else int(open_count),
                     clause_ids=[str(c) for c in list(clause_ids)[:10]]), root=root)
    except Exception:
        pass


def note_fault(event: dict, stage: str, detail: str, *, failed_closed: bool, root=None) -> None:
    """Record an event that could not be evaluated, and which way it fell.

    `failed_closed` is not decoration: it is what makes the suite's fail-direction policy auditable
    rather than merely documented. Keel's answer is split by design -- carriage open, decision
    closed -- and this field is where that split becomes a fact somebody can count.
    """
    try:
        _append(_row(event, "fault", stage=stage, detail=detail[:400],
                     failed_closed=bool(failed_closed)), root=root)
    except Exception:
        pass


def note_repair(event: dict, repaired: int, *, escaped: int = 0, root=None) -> None:
    """Record that the envelope had to be repaired before it could be read.
    KEYWORD-ONLY, and that is not style. `escaped` was inserted as the third POSITIONAL parameter,
    where `root` had been: every existing `note_repair(event, n, some_path)` call silently began
    reading the path as a count, `int(Path(...))` raised inside the swallowed handler, and the
    repair row vanished with no error anywhere. An audit row that disappears because a signature
    changed under it is the exact failure this journal exists to prevent.

    TWO COUNTS, NOT ONE SUM, because they count different things. `repaired` is UNDECODABLE BYTES
    -- host bytes that were not valid UTF-8. `escaped` is UNPAIRED SURROGATE ESCAPES -- `\\uD8xx`
    sequences that were perfectly valid ASCII on the wire and became lone surrogates only when
    `json.loads` decoded them. The caller used to add them together and file the total under a
    field named for bytes, so an envelope whose bytes were flawless could still report "3 bytes
    repaired". `wire._decode_counting` goes to real trouble to make the byte count mean bytes;
    adding a code-point count to it downstream gave that back.

    Distinct from `fault`: the event WAS evaluated, on a repaired payload. Conflating them would
    inflate the count of unevaluated calls, the one number this log exists to keep honest.
    """
    try:
        _append(_row(event, "repair", repaired=int(repaired), escaped=int(escaped)), root=root)
    except Exception:
        pass
