"""The one mechanism: demand -> discharge -> reconciliation.

A PreToolUse deny records a DEMAND. A later call matching the clause's guard records a DISCHARGE.
At Stop, anything still open is unreconciled and blocks. That is the whole model; the nine things
that looked like separate Stop checks are one ledger read.

HONESTY BOUNDARY, stated where the mechanism is introduced rather than in a footnote: the ledger
is written by the same agent it constrains. The hash chain detects accidental corruption, a
truncated write, bit-rot. It does NOT detect deliberate forgery -- anyone who can append to
`closures.jsonl` can append a matching hash. This constrains an honest-but-forgetful agent, not a
forging one, and no mechanism inside this trust boundary can do better. Ventura's manifest records
the same limit for the same reason.

ABSENCE IS NOT A PASS. An empty ledger at Stop means nothing was recorded, which is not the same
as nothing being owed -- it is NOT-EVALUABLE. A shipped verifier once scored an absent check
better than an empty one, and that inversion is the defect this file refuses to repeat.

MEASURED SCOPING LIMIT (2026-08-14, observed, not theorised): a nested `claude -p` invocation
reported the SAME `session_id` as the session that launched it, with `agent_id` empty. Scope is
keyed on `(session_id, agent_id)`, so a nested run shares its parent's ledger and the parent can
be blocked at Stop by a demand the child raised. This is the pooling hazard a sibling plugin
already paid for; it fixed it by treating a main-thread Stop as structurally agentless and letting
an ambiguous id contribute nothing rather than borrow. The keying here is correct for the ids the
host supplies -- it cannot separate threads the host does not distinguish. Recorded rather than
papered over, because a scope that silently pools is worse than one that says it pools.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
from dataclasses import dataclass, asdict

# Obligations are UN-WINDOWED within a session: a promise does not expire because an hour passed.
# Events may be windowed for cost; demands never are.
# NO `state` FIELD, and this is the reason rather than an omission. Openness is COMPUTED from
# row kinds -- `open_ids` is the demand rows minus the discharge rows -- so a stored state would
# be a second source of truth for the same fact, and the two drift the moment a discharge row is
# appended without the earlier demand row being rewritten, which this append-only journal never
# does. `Demand` used to carry `state: str = OPEN`, serialized into every row by `asdict` and
# read by nothing: a discharged demand went on carrying `"state": "open"` on disk forever. A
# `DISCHARGED = "discharged"` constant sat beside it with no reference anywhere -- the state it
# named could not be reached, because nothing ever assigned the field.


def state_dir() -> pathlib.Path:
    """Own store, not a host-provided one -- no CLAUDE_PLUGIN_DATA equivalent exists on codex."""
    env = os.environ.get("KEEL_STATE_DIR")
    if env:
        return pathlib.Path(env)
    if os.environ.get("CODEX_PLUGIN_ROOT") or os.environ.get("CODEX_HOME"):
        return pathlib.Path.home() / ".codex" / "keel_state"
    return pathlib.Path.home() / ".claude" / "keel_state"


# The names the store had before the rename to `keel`. Kept here, beside `state_dir`, because
# "where the state is" and "where the state used to be" are one fact with two tenses, and a
# rename that puts them in different files is how the second one goes stale.
LEGACY_STATE_ENV = "GYROSCOPE_STATE_DIR"
LEGACY_STATE_DIR = "gyroscope_state"

# The ledger's file name, spelled once. `Ledger` opens it and `legacy_state` asks whether it is
# there yet; two spellings of one file name is how the second reader starts asking about a file
# nothing writes.
LEDGER_FILE = "obligations.jsonl"


def legacy_state() -> pathlib.Path | None:
    """The pre-rename store this session is NOT reading, when there is one.

    A HARD RENAME OWES THE OLD NAME A SENTENCE, and this one did not pay it. `state_dir` reads
    `KEEL_STATE_DIR`; a session that had `GYROSCOPE_STATE_DIR` set kept setting it, had it
    ignored without a word, and started from an empty ledger -- so every obligation the old store
    held was gone and the run looked clean. Measured: `GYROSCOPE_STATE_DIR=/tmp/oldstate` and
    `state_dir()` returns `~/.claude/keel_state`.

    The previous rename in this project's history knew better and refused to start:
    "STARTUP REFUSED: legacy state directory exists at ...; hard rename requires an explicit state
    migration". That refusal ran in a SessionStart shell script that could exit nonzero. The same
    duty lands here as a notice on the SessionStart context and a message to the user, which is
    the loudest thing this arm can do without denying a session outright -- and denying is the
    wrong price for state that may not matter to this run.

    Two ways to be stranded, both reported. The variable being SET is enough on its own: it is
    being ignored, and that is the fact worth saying, whether or not it points anywhere. A legacy
    directory sitting beside the current one counts only until keel has a ledger of its own --
    after that the old directory is history rather than a surprise.

    "Has a ledger of its own" is the LEDGER FILE, not the directory, and the difference is the
    whole test. `Ledger.__init__` creates the directory, and it is constructed before any handler
    runs -- so a check for the directory's existence was always looking at something this same
    process had just made, and reported nothing every time. The file is written when a row is
    written, which is the event actually being asked about.
    """
    env = os.environ.get(LEGACY_STATE_ENV)
    if env:
        return pathlib.Path(env)
    current = state_dir()
    beside = current.parent / LEGACY_STATE_DIR
    return beside if beside.is_dir() and not (current / LEDGER_FILE).exists() else None


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _chain_hash(prev: str, body: dict) -> str:
    """The chain rule, written ONCE. `_append` computes it and `verify_chain` re-derives it; two
    copies of one expression is exactly how a verifier starts reporting corruption on a sound
    ledger, so the writer and the checker are the same line of code or they are not the same rule.
    `body` must carry every field of the row EXCEPT `hash`.
    """
    return _digest(prev + _canon(body))


def derive_id(session: str, agent: str, clause_id: str, subject: str) -> str:
    """Content-addressed, so re-stating one demand does not duplicate it.

    `subject` is the normalized thing at risk (a path, a ref, a command head) -- not the whole
    command, or two spellings of one demand would read as two.
    """
    return _digest(_canon([session, agent, clause_id, subject]))


@dataclass(frozen=True)
class Demand:
    """`id` is DERIVED, never carried: every caller filled it by calling `derive_id` on the four
    fields below and handing the answer straight back -- one datum with two spellings, and
    nothing checked that they agreed."""
    session: str
    agent: str
    clause_id: str
    subject: str
    reason: str

    @property
    def id(self) -> str:
        return derive_id(self.session, self.agent, self.clause_id, self.subject)


class Ledger:
    """One path, one writer. Every append goes through `_append`; nothing else opens the file.

    Reconciliation is PER THREAD, never pooled: a main-thread Stop is structurally agentless, a
    subagent carries its own agent id, and an ambiguous id contributes nothing rather than
    borrowing another thread's demands. Pooling lets a sibling's dangling demand block every
    later Stop -- a measured defect in a sibling plugin, not a hypothetical.
    """

    def __init__(self, root: pathlib.Path | None = None):
        self.root = pathlib.Path(root) if root else state_dir()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / LEDGER_FILE

    def _rows(self):
        if not self.path.exists():
            return
        # errors="replace": a torn write can split a multi-byte UTF-8 sequence (`_canon` writes
        # ensure_ascii=False), and one undecodable byte must corrupt one row, not raise
        # UnicodeDecodeError out of every method for every session sharing this state dir.
        with self.path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    # A malformed row is skipped, never fatal: this plugin fails OPEN, and a
                    # corrupt ledger must not wedge every session behind it.
                    continue
                if not isinstance(row, dict):
                    # JSON-valid but not a row (`123`, `null`): same skip, or every consumer's
                    # `.get` raises and "skipped, never fatal" is a lie.
                    continue
                yield row

    def scope(self, session: str, agent: str):
        """ONE pass over the file, answering every question this ledger has: the OPEN demand rows
        by id, the ids a guard call has DISCHARGED, and the chain head the next row links to.

        DEMAND, DISCHARGE AND OPEN ARE NOT THREE CONCEPTS. They are one set difference,
        `demanded - discharged`, taken here and nowhere else -- and a licence is membership in
        the second set and NOTHING else. Deliberately not "absent from the first": a demand that
        was never raised is also not open, and reading that as a licence would let the costly act
        through on the strength of nothing ever having happened. `.get` throughout: a row missing
        `id`, `session` or `kind` is malformed and skipped, not a KeyError. First demand row per
        id wins; that IS the dedup. Three methods over three walks used to answer these.
        """
        demanded, closed, tail = {}, set(), ""
        for row in self._rows():
            tail = row.get("hash", "")
            rid = row.get("id")
            if rid is None or row.get("session") != session or row.get("agent") != agent:
                continue
            if row.get("kind") == "demand":
                demanded.setdefault(rid, row)
            elif row.get("kind") == "discharge":
                closed.add(rid)
        return {i: r for i, r in demanded.items() if i not in closed}, closed, tail

    def _append(self, row: dict) -> None:
        row = dict(row)
        prev = ""
        for r in self._rows():
            prev = r.get("hash", "")
        row["prev"] = prev
        row["hash"] = _chain_hash(prev, row)
        with self.path.open("a", encoding="utf-8") as fh:
            # A torn write (ENOSPC/EIO, a row killed between buffer flushes) can leave the file
            # ending mid-line. Appending straight onto that fragment merges two rows into one
            # unparseable line, so a discharge that LANDED reads back as never having happened
            # and Stop blocks on a false fact. Terminate the fragment first: the fragment stays
            # a skipped malformed row, and this row stays readable.
            fh.flush()
            if fh.tell() > 0:
                with self.path.open("rb") as tail:
                    tail.seek(-1, os.SEEK_END)
                    if tail.read(1) != b"\n":
                        fh.write("\n")
            fh.write(_canon(row) + "\n")

    def demand(self, d: Demand) -> bool:
        """Record a demand. Returns False if this exact demand is already open (idempotent)."""
        if d.id in self.open_ids(d.session, d.agent):
            return False
        self._append({"kind": "demand", "id": d.id, **asdict(d)})
        return True

    def discharge(self, session: str, agent: str, demand_id: str, how: str) -> None:
        # A licence is a state TRANSITION, not an event log. Re-observing the same guard in
        # the same scope changes nothing, so keeping every observation only makes every later
        # read scan duplicate history -- measured, 40 identical `git status` calls wrote 120
        # rows through the dispatcher, and reads are linear in what was written.
        if self.is_licensed(session, agent, demand_id):
            return
        self._append({"kind": "discharge", "session": session, "agent": agent,
                      "id": demand_id, "how": how})

    def is_licensed(self, session: str, agent: str, demand_id: str) -> bool:
        """True once the guard call for this exact subject has been observed (see `scope`)."""
        return demand_id in self.scope(session, agent)[1]

    def open_ids(self, session: str, agent: str) -> set[str]:
        return set(self.scope(session, agent)[0])

    def open_demands(self, session: str, agent: str) -> list[dict]:
        return list(self.scope(session, agent)[0].values())

    def verify_chain(self) -> str | None:
        """Re-derive the chain. Returns the first divergent hash, or None. Advisory only."""
        prev = ""
        for row in self._rows():
            body = {k: v for k, v in row.items() if k != "hash"}
            if _chain_hash(prev, body) != row.get("hash"):
                return row.get("hash") or "<missing>"
            prev = row["hash"]
        return None
