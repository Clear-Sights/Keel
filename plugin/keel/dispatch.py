"""One entrypoint, every event. A capability is a row, never a module.

Adding an event is adding a row to HANDLERS, never another branch in main(). An event with no row
is answered NOT-EVALUABLE, loudly, and can neither raise nor discharge a demand: the old wildcard
default let an unknown event pay a guard for free.

WIRE FORMAT is identical on Claude Code and codex, verified against both specs:
  PreToolUse deny  -> {"hookSpecificOutput": {..., "permissionDecision": "deny", ...}}
  Stop block       -> {"decision": "block", "reason": ...}
  SessionStart     -> {"hookSpecificOutput": {..., "additionalContext": ...}}
A decision is a JSON decision, not an exit code. Blocks exit 0 with JSON on stdout.

FAIL DIRECTION IS SPLIT, and the split is the point. Carriage -- unreadable stdin, a missing
interpreter, any fault that means the hook could not be reached -- fails OPEN with exit 0 + {},
because carriage that blocks is worse than carriage that is absent. A DECISION that could not be
computed fails CLOSED via _closed_not_evaluable(), which emits the event's own deny/block wire.
An event with no closed wire falls back to carriage rather than inventing one.

EXIT 2 IS NOT USED HERE. Not because it means something unusual -- verified against the hooks
reference, "exit 2 blocks whether or not you print JSON", on BOTH hosts -- but precisely because
it does: a dispatcher bug that exited 2 would deny every tool call for the rest of the session,
healing only by uninstalling the gate.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import time
from pathlib import Path

from . import clauses as C
from . import effects, journal, wire
from .ledger import Demand, Ledger, derive_id, legacy_state, state_dir

# A HEADER ON THE COMMAND, and nowhere else. The exemption is the one thing that turns the whole
# fence off for a call, so where it is allowed to appear is the whole of its security.
#
# It has been narrowed twice, both times because the wider form let the command supply its own
# exemption. First it searched the entire serialized tool_input, so a Write whose CONTENT quoted
# the documentation disabled every clause for that call. Then it searched anywhere in the command
# string, which is the same hole with one more step: append a heredoc and the command carries its
# own licence in its payload. That was not theoretical --
#
#     rm -rf build/                                    -> deny
#     rm -rf build/ ; cat > note.md <<'EOF'
#     keel-allow: whatever
#     EOF                                              -> {}   (all 24 clauses skipped)
#
# -- and every command that can write a file could do it. So the marker is now read only from the
# command's LEADING COMMENT BLOCK: the scan starts at the first line and stops dead at the first
# line that is not blank and not a comment. A heredoc body, a quoted string, an appended segment
# -- all of them live after command text has begun, which is after the scan has already stopped.
# An exemption is something an author types at the top, above the command, on purpose.
#
# `#` only. The older pattern also accepted `//` and `--`, from when this was matched against
# arbitrary tool_input; the field is a shell command and `#` is the only comment introducer a
# shell has. `--` was worse than redundant, because `--force-with-lease` on its own line reads as
# a comment to a pattern that accepts `--`.
ALLOW = re.compile(r"^#\s*keel-allow:\s*(\S.*)$")



# A COMMITMENT, not an exemption. A guard that is itself a Bash act cannot be recognised before
# it runs -- its effect is what discharges, and the effect exists only after. So under an open
# demand a Bash call passes on a leading `# keel-guard: <clause ids>` line naming what it will
# pay, and is CHECKED after it ran: a committed call whose effect did not pay is a broken
# commitment, recorded in the journal, and the demand stays open. The marker names a clause,
# never a program; what it claims is verified by the observer, so a mention cannot spend it.
GUARD = re.compile(r"^#\s*keel-guard:\s*([A-Za-z0-9_,\s-]+)$")


def _header(command):
    """The leading comment lines of a command, where a marker may appear -- spelled once for
    both markers. The scan stops dead at the first line that is not blank and not a comment;
    a missing command is an empty header, said here rather than at each call site."""
    if not isinstance(command, str):
        return
    for line in command.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith("#"):
            # Command text. Everything from here on is payload, not preamble.
            return
        yield stripped


def _guard_marker(command) -> set[str]:
    """The clause ids a Bash call commits to pay, from its leading comment header."""
    for line in _header(command):
        found = GUARD.match(line)
        if found:
            return {p for p in re.split(r"[,\s]+", found.group(1)) if p}
    return set()


def _allow_marker(command: str):
    """The exemption's stated reason, from the command's leading comment header, or None.

    The reason is the auditable half: an exemption without one is not an exemption, and the
    pattern refuses a marker with nothing after it. There is exactly ONE spelling; a second,
    undocumented one is a way past all 24 clauses that no page names and no reader can count.
    """
    for line in _header(command):
        found = ALLOW.match(line)
        if found:
            return found.group(1)
    return None


def _get(event: dict, path: str):
    cur = event
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _ids(event: dict) -> tuple[str, str]:
    """Per-thread, never pooled. A main-thread Stop is structurally agentless; an ambiguous
    agent id contributes nothing rather than borrowing a sibling's demands."""
    return str(event.get("session_id") or ""), str(event.get("agent_id") or "")


# A DEMAND KEYED ON WHAT THE ACT DID. An effect clause's subject may be the datum its effect
# produced -- `{"effect": "files_changed"}` -- so a rewrite of two files raises two demands,
# each keyed on its path, and a guard pays exactly the one it names: a Read of `config.txt`,
# a `git diff` whose output names `config.txt`, a Grep aimed at it. Before this the subject
# was the session, so any look at any path paid every rewrite (AG-10: a constant payload paid
# a trace-checked guard, 29 of 30 targets). `observed.json` is Keel's own measurement of the
# dirty paths and pids, so a Read of it names them all -- that is what the artifact is for.
_NAMED_BY = {"files_changed": "named_paths", "files_removed": "named_paths", "pids_gone": "named_pids"}


def _effect_keyed(clause) -> str | None:
    spec = clause.subject
    return spec.get("effect") if isinstance(spec, dict) and "effect" in spec else None


def _subjects(clause, event: dict) -> list[str]:
    """Every key this event raises for the clause: one per datum for an effect subject."""
    effect = _effect_keyed(clause)
    if effect is None:
        return [_subject(clause, event)]
    record = event.get("keel_effect") if isinstance(event.get("keel_effect"), dict) else {}
    data = record.get(effect)
    return [str(d)[:200] for d in data] if isinstance(data, list) else []


def _names(clause, event: dict, subject: str) -> bool:
    """Does this guard event name the datum a demand is keyed on?"""
    effect = _effect_keyed(clause)
    record = event.get("keel_effect") if isinstance(event.get("keel_effect"), dict) else {}
    if record.get("observed_read") is True:
        return True
    named = record.get(_NAMED_BY.get(effect, ""))
    if isinstance(named, list) and subject in {str(n) for n in named}:
        return True
    for field in ("tool_input.file_path", "tool_input.path", "tool_input.notebook_path"):
        value = _get(event, field)
        if isinstance(value, str) and value and (value == subject or value.endswith("/" + subject)):
            return True
    return False


def _pay(clause, ledger: Ledger, event: dict, session: str, agent: str, *, only_open: bool,
         how: str, within: set | None = None) -> bool:
    """Discharge what this guard event pays for the clause; True if it paid anything.

    A session-keyed or extractor-keyed clause pays the one demand its subject derives; an
    effect-keyed clause pays every open demand of its own whose datum this event names.
    `within` bounds what may be paid to the demands open BEFORE this act: an act cannot be
    its own guard, or a quiet connection pays the canary its own connection owed (EFF-12)."""
    if _effect_keyed(clause) is not None:
        rows = [row for row in ledger.open_demands(session, agent)
                if row.get("clause_id") == clause.id and _names(clause, event, row.get("subject") or "")
                and (within is None or row["id"] in within)]
        for row in rows:
            ledger.discharge(session, agent, row["id"], how)
        return bool(rows)
    did = derive_id(session, agent, clause.id, _subject(clause, event))
    if only_open and did not in (ledger.open_ids(session, agent) if within is None else within):
        return False
    ledger.discharge(session, agent, did, how)
    return True


def _subject(clause, event: dict) -> str:
    """The ledger key. It must yield the SAME value for the costly act and for its guard.

    A whole-field key cannot do that when both arrive as commands: `rm -rf build/` and
    `ls -la build/` are different strings, so keying on tool_input.command would give the guard a
    different key from the demand it is meant to license, and nothing would ever discharge. The
    shared thing is the operand -- `build/` -- so a subject may also be an EXTRACTOR that pulls
    the same operand out of both commands.

    A dict subject with no match yields "" and the caller treats that as unkeyable; an empty key
    would silently merge every demand for the clause, which is worse than a coarse honest one.
    """
    spec = clause.subject
    if isinstance(spec, dict):
        # `on` may name SEVERAL fields, tried in order. One act and its guard do not always
        # arrive through the same surface: a jq traversal carries its file in the command,
        # while the host `Read` that inspects the same file carries it in `tool_input.file_path`.
        # With a single field the guard yields no key at all, so it can never discharge the
        # demand it plainly satisfies -- the guard would be composed over two surfaces while the
        # SUBJECT stayed nominal, and the composition would silently do nothing.
        raw = ""
        for field in C.subject_fields(spec):
            candidate = _get(event, field)
            if isinstance(candidate, str) and candidate:
                raw = candidate
                break
        m = re.search(spec.get("pattern") or "", raw) if raw else None
        if not m:
            return ""
        try:
            return str(m.group(spec.get("group", 1)) or "")[:200]
        except IndexError:
            return ""
    return str(_get(event, spec) or "")[:200]


# THE AUTHOR OF A DENY MUST BE ON THE DENY. Ward, Keel and Makoto all register PreToolUse and
# all three can refuse a call; the host shows the user a reason, not a source. With three
# unattributed reasons in play, "which plugin blocked this?" was answerable only by guessing from
# wording -- and after the fact, not at all. Both siblings already prefix their own name; this is
# the third. It costs one word and makes every refusal in the transcript joinable to the row in
# `decisions.jsonl` that recorded it.
_PREFIX = "keel"


def _deny(reason: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                   "permissionDecision": "deny",
                                   "permissionDecisionReason": f"{_PREFIX}: {reason}"}}


# A deny that does not name what it is keyed on is an unhealing loop, not an interruption.
#
# The ledger discharges on the SUBJECT -- the operand shared by the act and its guard. So
# `realpath build/` does not license `touch newfile`: different subject, different key. Measured:
# `touch newfile` denied 12 times out of 12 while the session ran the guard on the wrong path, and
# the reason it was shown said only "run `realpath` on the target first". That loop does not heal
# by being forgotten (it fires on every attempt) and it does not heal by being noticed (the message
# withholds the one fact that would end it), so it heals only by restart.
#
# Naming the subject is the whole repair, and it is a reversal rather than an addition: the same
# two fates stay reachable and nothing new is demanded of the session -- the correct one simply
# stops being hidden.
# Two scopes exist and they discharge differently, so one sentence cannot serve both. A dict
# subject is an EXTRACTOR: it pulls an operand out of the command, and only a guard naming that
# same operand discharges it. A plain `session_id` subject is SESSION-WIDE: any guard call clears
# it once, for everything. Saying "keyed on `drive`" for the session case -- which is what naming
# the raw subject produced -- is worse than silence, because it points the session at its own id.
def _keyed_reason(clause, subject: str) -> str:
    base = f"[{clause.id}] {clause.deny_reason}"
    if _effect_keyed(clause) is not None:
        return (f"{base} -- keyed on `{subject}`, so the guard must name `{subject}`: Read it, "
                f"Grep it, or print it from the worktree; a look at another target does not "
                f"discharge this." + _construction(clause))
    if isinstance(clause.subject, dict):
        if not subject:
            return base + _construction(clause)
        return (f"{base} -- keyed on `{subject}`, so the guard must name `{subject}` too; "
                f"the same guard on another target does not discharge this."
                + _construction(clause))
    return f"{base} -- discharges once per session, for every target.{_construction(clause)}"


# The deny names the guard that buys THIS session; the pointer names what to build so the guard
# is never needed again. A pointer, never an inlined command: the construction is authored prose
# with its own caveats, and a one-line paraphrase here would be a second writer of that fact.
# Composed at render time from the clause's own `construction` field, so the pointer cannot
# drift from the table -- one writer, read twice.
#
# AN ABSENT OR MISSHAPEN ANCHOR COSTS THIS SENTENCE, AND NOTHING ELSE. The loader used to refuse
# such a row, which meant a mistyped documentation pointer took the entire clause table down and
# denied every tool call. The refusal now lives in the fence, where a bad anchor is a red build;
# here, the worst a bad anchor can do is omit one sentence from one deny message. The deny itself
# -- the load-bearing half -- is never withheld because its footnote is malformed.
def _construction(clause) -> str:
    anchor = clause.construction or ""
    if not C.CONSTRUCTION_ANCHOR.fullmatch(anchor):
        return ""
    return f" Construction: {anchor}."


def _block(reason: str) -> dict:
    return {"decision": "block", "reason": f"{_PREFIX}: {reason}"}


def _context(text: str, event_name: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": event_name, "additionalContext": text}}


def _open_not_evaluable(detail: str) -> dict:
    """The LOUD half of a fail-open. Its whole job is to reach a seat that can act.

    `systemMessage` is the universal output field the host actually surfaces. Everything else a
    hook can say on exit 0 -- stderr above all -- goes to the debug log, so a fail-open written
    only to stderr is, from every seat, byte-identical to a clean pass. That is not a hypothesis:
    `docs/FAIL-DIRECTION.md` §3 records 30 such allows in one day going unnoticed, and says of
    itself that the rule "was written down and still not true in practice."

    It was still not true here. The three fail-open exits below printed a bare `{}`, and the
    unreadable-event one runs BEFORE the event name is known -- so an unparseable `PreToolUse`
    was allowed with no user-visible trace at all. The rule was already implemented one layer
    out, in the shim, and asserted by `tests/test_shim_visibility.py`; one boundary had it and
    the next did not.

    One helper rather than three call sites, because three spellings of one rule is how the next
    fail-open gets added without this one.
    """
    return {"systemMessage": f"{_PREFIX}: this call was ALLOWED WITHOUT BEING CHECKED -- "
                             f"{detail}. NOT-EVALUABLE, not a pass."}


def _closed_not_evaluable(event: dict, detail: str) -> dict | None:
    """Return the closed wire for a known event; None means only exit status can express it."""
    reason = f"keel could not evaluate this event: {detail} -- NOT-EVALUABLE, not a pass"
    name = event.get("hook_event_name")
    if name == "PreToolUse":
        return _deny(reason)
    if name in ("Stop", "SubagentStop"):
        return _block(reason)
    return None


def _effect_record(ledger: Ledger, event: dict, moment: str) -> None:
    """Observe the world around a call and attach what changed as `event["keel_effect"]`.

    A record already on the event is a RECORDED session (the corpus) and is kept as-is; a live
    event never carries one, because the host builds the event and `keel_effect` is not a field
    it knows. `moment` is "before" (snapshot only), "after" (delta) or "stop" (the remote).
    Observation never raises into the decision: a failed observation is a None in the record,
    which the predicates read as NOT-EVALUABLE.
    """
    if isinstance(event.get("keel_effect"), dict):
        return
    session, agent = _ids(event)
    cwd = str(event.get("cwd") or os.getcwd())
    try:
        # EVERY TOOL THAT CAN CHANGE THE WORLD IS OBSERVED, not only Bash. With Bash alone,
        # the host's own Write/Edit/MultiEdit/NotebookEdit calls were outside the observer, so
        # every file-mutation point was covered on one surface and bypassed on the other
        # (measured: 30 of 31 targets under that angle). The observer reads the world, not the
        # tool, so the same snapshot/delta serves them all; host reads are the exception because
        # they change nothing and Read alone carries a datum (Keel's own artifacts).
        tool = event.get("tool_name")
        if moment == "before":
            if tool not in HOST_READS:
                act = event.get("tool_use_id")
                effects.snapshot(ledger.root, session, agent, cwd,
                                 act=act if isinstance(act, str) else None)
        elif moment == "after":
            if tool not in HOST_READS:
                event["keel_effect"] = effects.delta(ledger.root, session, agent, event)
            elif tool == "Read":
                # A Read does nothing to the world; what it can do is observe Keel's own
                # measurement, and that observation is the datum three guards are paid by.
                event["keel_effect"] = effects.read_delta(ledger.root, event)
        elif moment == "stop":
            event["keel_effect"] = effects.at_stop(ledger.root, session, agent, cwd)
    except Exception as exc:
        event["keel_effect"] = {name: None for name in effects.EFFECTS}
        event["keel_effect"]["not_evaluable"] = type(exc).__name__


def _open_effect_denial(table, ledger: Ledger, event: dict, session: str, agent: str):
    """A demand an effect raised at PostToolUse denies the NEXT call, unless that call is its guard.

    The act has already happened, so the deny cannot land on it; it lands on whatever the
    session tries next, and the only call that passes is one discharging an open demand. That
    is what makes an after-the-fact occasion fail CLOSED: the session cannot proceed past a
    destructive effect it never looked at.
    """
    open_rows = ledger.open_demands(session, agent)
    if not open_rows:
        return None, False
    by_id = {cl.id: cl for cl in table}
    owed, progress = [], False
    committed = _guard_marker(_get(event, "tool_input.command"))
    for row in open_rows:
        cl = by_id.get(row.get("clause_id"))
        # A terminal clause's debt is settled at the ending, by `reconcile`; it does not
        # refuse the acts before it, or a checker's PASS would refuse the failing run that
        # pays for it.
        if cl is None or cl.event in ("Stop", "SubagentStop"):
            continue
        if cl.id in committed:
            progress = True
            continue
        # The guard must name what the demand is keyed on: a Read of `other.json` does not pay
        # for the traversal of `payload.json`. Session-wide subjects agree trivially.
        if C.discharges(cl, event) and (
                _names(cl, event, row.get("subject") or "") if _effect_keyed(cl) is not None
                else derive_id(session, agent, cl.id, _subject(cl, event)) == row["id"]):
            ledger.discharge(session, agent, row["id"], "guard call observed")
            progress = True
            continue
        owed.append(_keyed_reason(cl, row.get("subject") or ""))
    # A call that pays ANY open demand passes, or two open demands could never both be paid:
    # each guard would be refused for the other's debt. What is refused is a call that pays
    # nothing while something is owed -- and the refusal names everything owed, at once, so the
    # session learns the whole debt in one interruption rather than one clause per attempt.
    if not owed or progress:
        return None, progress
    # A HOST READ IS NEVER THE ACT. An open demand refuses the next act; a Read, Grep or Glob
    # cannot change the world, and a Read is how the observation-shaped guards are paid --
    # its effect record exists only after it ran. Refusing the read would refuse the guard.
    if event.get("tool_name") in HOST_READS or event.get("tool_name") in NON_ACTS:
        return None, progress
    return _deny("; ".join(owed) + COMMIT_HINT), progress


# The host tools that read and cannot act. Closed by the host, listed here once.
HOST_READS = frozenset({"Read", "Grep", "Glob"})
# Host tools that neither read nor act on the world: a question to the operator and the plan
# door. An open demand refuses the next ACT; refusing these left a refused push blocking the
# very question that would resolve it (DL-14, P-23). `Task` stays an act: it spawns a worker.
NON_ACTS = frozenset({"AskUserQuestion", "ExitPlanMode"})
COMMIT_HINT = (" -- a guard that is itself a Bash act passes on a leading `# keel-guard: <clause id>` "
               "line and is checked by its effect after it runs")


def _applies(cl, event: dict) -> bool:
    """Does this clause declare this event and this tool? Asked of one clause where the answer
    is used, not pre-walked into a set of `id()`s: the caller already loops the table."""
    if cl.event != event.get("hook_event_name"):
        return False
    return not cl.tools or cl.tools == ["*"] or event.get("tool_name") in cl.tools


def pre_tool_use(table, ledger: Ledger, event: dict) -> dict:
    """FAIL CLOSED per row is wrong here and right at Stop: a deny that cannot be computed is
    not a deny. But a clause that raises must never suppress the other twenty-five, so each is
    isolated -- that is a different axis from the row's fail direction."""
    session, agent = _ids(event)
    bypass = _get(event, "tool_input.command")
    # Read straight from the one field, rather than looping a one-element list of field paths:
    # `_allow_marker` scans for SHELL comments, so the field it may be applied to is not a
    # configuration choice -- it is the command, and a list implied there could be others.
    marker = _allow_marker(bypass) if isinstance(bypass, str) else None
    if marker is not None:
        return {}
    _watch_standing(table, ledger, event, session, agent)
    held, progress = _open_effect_denial(table, ledger, event, session, agent)
    if held is not None:
        return held
    _effect_record(ledger, event, "before")
    denials = []
    for cl in table:
        try:
            # A GUARD IS READ ON EVERY EVENT, whatever event the clause fires on: a Glob licenses
            # A02 before the first act although A02 fires on Bash, exactly as a Read pays U12
            # after a rewrite although U12 fires at PostToolUse. Terminal clauses are watched
            # by `_watch_standing`, under their own subject.
            if cl.event not in ("Stop", "SubagentStop") and C.discharges(cl, event):
                # An effect clause is discharged only against a demand its effect raised (the
                # rule `post_tool_use` states); a pre-act clause is licensed in advance.
                if _pay(cl, ledger, event, session, agent, how="guard call observed",
                        only_open=C.classify_side(cl.fingerprint) == "effect"):
                    progress = True
                continue
            if not _applies(cl, event):
                continue
            if C.match(cl, event):
                subject = _subject(cl, event)
                # THE EXTRACTOR FINDING NO OPERAND IS NOT A PASS. This used to abstain, which
                # made the subject regex a covering: an act spelled outside the extractor's
                # vocabulary proceeded unguarded (L2). The demand is raised under the empty
                # key instead -- session-wide, coarse, honest -- and any guard for the clause
                # that names no operand pays it.
                did = derive_id(session, agent, cl.id, subject)
                # The licence must be an OBSERVED discharge, never merely an absent demand.
                if ledger.is_licensed(session, agent, did):
                    continue
                denials.append((cl, subject, did))
        except Exception:
            continue
    # ONE REFUSAL NAMES EVERY CLAUSE REFUSING. Three clauses fire on every first act of a
    # session (their occasion is `always`: before the act, Theorem 3 leaves nothing else to
    # read), and returning at the first would cost one interruption per clause to learn a debt
    # that could have been stated once.
    #
    # A GUARD CALL PASSES THE `always` OCCASIONS. Three clauses fire on every act, and each is
    # discharged by a different guard, so without this the first guard would be refused by
    # the other two and no session could ever begin. A call that discharged some clause on
    # this event is progress toward the debt and is not refused by an occasion that fires on
    # everything; it is still refused by an occasion that selects (a host tool enum), because
    # those do not owe the session an opening move.
    # The demand is recorded only for a refusal that stands: a waived one would leave a row
    # open at Stop for an act that was allowed.
    if progress:
        denials = [d for d in denials if (d[0].fingerprint or {}).get("kind") != "always"]
    if not denials:
        return {}
    for cl, subject, did in denials:
        ledger.demand(Demand(session, agent, cl.id, subject, cl.deny_reason))
    return _deny("; ".join(_keyed_reason(cl, subject) for cl, subject, _ in denials))


def post_tool_use(table, ledger: Ledger, event: dict) -> dict:
    session, agent = _ids(event)
    _effect_record(ledger, event, "after")
    _watch_standing(table, ledger, event, session, agent)
    # What was owed BEFORE this act is all this act may pay: its own demands are raised below.
    open_before = ledger.open_ids(session, agent)
    for cl in table:
        try:
            after_the_act = C.classify_side(cl.fingerprint) == "effect"
            # EVERY GUARD IS READ OFF THE RECORD, whatever event the clause itself fires on:
            # a guard is an observed effect of the guard act, and the act's record exists
            # only here. So A01's guard (a Read of the worktree measurement) pays A01's
            # PreToolUse demand from this event, and T01's standing guard the same.
            if cl.event not in ("Stop", "SubagentStop") and C.discharges(cl, event):
                # AN EFFECT'S GUARD IS "LOOK AT WHAT YOU JUST DID", and that cannot be done
                # in advance. A pre-act clause is licensed by a guard seen before the act; an
                # effect clause is discharged only against a demand its effect has raised.
                # Otherwise the suite run every session opens with would license the deletion
                # that comes an hour later -- measured: U20 never fired once a `pytest` had
                # run earlier in the session.
                _pay(cl, ledger, event, session, agent, how="guard call completed",
                     only_open=after_the_act, within=open_before if after_the_act else None)
                if not after_the_act:
                    continue
                # An effect clause whose guard this act also satisfies still has its OCCASION
                # read: `continue` here let a quiet connection be its own canary, so U06 never
                # fired on the exfiltration shape (EFF-12). Stated limit: any LATER quiet
                # connection pays it -- the canary is a report shape (owner row 3).
            if not _applies(cl, event):
                continue
            # AN EFFECT IS THE OCCASION, OBSERVED AFTER THE ACT. The demand is raised here and
            # the next call pays it (`_open_effect_denial`); this event itself cannot be
            # refused, the act is done. `match` fails closed on an unmeasured effect.
            if after_the_act and C.match(cl, event):
                for subject in _subjects(cl, event):
                    did = derive_id(session, agent, cl.id, subject)
                    if not ledger.is_licensed(session, agent, did):
                        ledger.demand(Demand(session, agent, cl.id, subject, cl.deny_reason))
        except Exception:
            continue
    committed = _guard_marker(_get(event, "tool_input.command"))
    if committed:
        still = {row["clause_id"] for row in ledger.open_demands(session, agent)}
        broken = sorted(committed & still)
        if broken:
            # The call passed on its word and its effect did not pay. Recorded where the
            # unevaluated events are, because it is the same fact: a decision that rested on
            # something the observer did not see. The demand is still open, so the next act
            # is refused again; nothing was spent.
            journal.note_fault(event, "broken_commitment", ",".join(broken), failed_closed=True,
                               root=ledger.root)
            print(f"keel: committed guard for {broken} paid nothing -- still owed", file=sys.stderr)
    return {}


def _watch_standing(table, ledger: Ledger, event: dict, session: str, agent: str) -> None:
    """A terminal clause's guard is not a Stop event -- it is an ordinary call made earlier.

    So Stop clauses must be watched on EVERY event, not only on events whose name matches the
    clause's own. Without this a terminal clause could never be discharged and would block every
    Stop, which is the false-block failure that makes a gate get switched off.
    """
    for cl in table:
        if cl.event not in ("Stop", "SubagentStop"):
            continue
        try:
            # Activation is observed on ordinary events, exactly as a standing guard is, and is
            # recorded through the same demand/discharge pair under a distinct subject -- so the
            # ledger needs no new row shape to carry "the occasion happened".
            if cl.activated_by is not None and C._predicate(cl.activated_by, event):
                key = C.event_key(cl.activated_by, event)
                if cl.activated_by.get("key_from") is not None:
                    if not key:
                        continue
                    subject = f"standing:{key}"
                    did = derive_id(session, agent, cl.id, subject)
                    ledger.demand(Demand(session, agent, cl.id, subject, cl.deny_reason))
                    # NO `continue` HERE, and the reason is the whole shape of a keyed standing
                    # clause: ONE ACT CAN BE BOTH THE OCCASION AND THE GUARD. C08 is the case --
                    # running a checker's own can-fail plant both produces a PASS that could be
                    # cited AND observes that checker failing. Skipping the discharge branch
                    # after demanding made such an act raise an obligation it had already
                    # satisfied, so proving a checker can fail left the ending blocked by the
                    # very clause the proof answers. Both sides key on `standing:{key}`, so the
                    # discharge below lands on the row just raised and the pair nets clean.
                    #
                    # This is NOT the self-licence a shipped clause would need to be refused
                    # from. That refusal is STRUCTURAL, not a segment-order check: every shipped
                    # `discharged_by` reads either a host enum naming a DIFFERENT tool than the
                    # clause's own occasion tools, or an effect that a PreToolUse event never
                    # carries, so no PreToolUse event can satisfy a clause's occasion and its
                    # discharge at once (tests.test_self_licence, over the whole table). Here
                    # there are not two acts: the plant IS the observation, so there is no
                    # order for it to be in. An ordinary run of the same checker still demands
                    # and does not discharge, because the guard requires the fault-proving form.
                else:
                    # The UNKEYED shape only. Dropping the `continue` above to let one act both
                    # raise and satisfy a keyed obligation also dropped the keyed branch into
                    # this pair, so every keyed activation wrote a demand and its immediate
                    # discharge under the subject "activated" -- rows that net to zero and mean
                    # nothing, in the journal whose whole job is saying what was owed. Benign to
                    # the verdict, junk to a reader, and two shapes wearing one code path.
                    # ONE row: a demand written and discharged on the next line netted to zero
                    # in the journal whose whole job is saying what was owed; `reconcile` asks
                    # `is_licensed`, so only the discharge was ever read.
                    ledger.discharge(session, agent, derive_id(session, agent, cl.id, "activated"),
                                     "occasion observed")
            if C.discharges(cl, event):
                key = C.event_key(cl.discharged_by, event)
                if cl.discharged_by.get("key_from") is not None and not key:
                    continue
                subject = f"standing:{key}" if key else "standing"
                did = derive_id(session, agent, cl.id, subject)
                ledger.discharge(session, agent, did, "standing guard observed")
        except Exception:
            continue


# Refusals of one ending before it is allowed LOUDLY (DL-04). Three: one refusal states the
# debt, a second proves it was read and ignored, a third is the last before the host's own
# stop-hook loop cap would fail open in silence; exhausted, the ending passes with a fault row
# and a systemMessage, and the rows stay open for the next ending.
STOP_ROUNDS = 3


def _pending_dir(root: pathlib.Path) -> pathlib.Path:
    return pathlib.Path(root) / "pending"


def _pending_mark(root: pathlib.Path, event: dict) -> pathlib.Path | None:
    """Leave a marker for the duration of an observed event; `main` removes it on answer."""
    if event.get("hook_event_name") not in ("PreToolUse", "PostToolUse"):
        return None
    session, _ = _ids(event)
    try:
        d = _pending_dir(root)
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{session}-{os.getpid()}.json"
        cmd = _get(event, "tool_input.command") or _get(event, "tool_input.file_path") or ""
        path.write_text(json.dumps({"event": event.get("hook_event_name"), "tool": event.get("tool_name"),
                                    "act": str(cmd)[:200], "t": time.time()}), encoding="utf-8")
        return path
    except OSError:
        return None


def _pending_lost(root: pathlib.Path, session: str) -> list[str]:
    """Markers of this session whose hook process is gone: evaluations that never answered."""
    lost = []
    try:
        for path in sorted(_pending_dir(root).glob(f"{session}-*.json")):
            pid = path.stem.rsplit("-", 1)[-1]
            try:
                os.kill(int(pid), 0)
                continue  # still running: a concurrent hook, not a dead one
            except (ValueError, ProcessLookupError, PermissionError):
                pass
            try:
                row = json.loads(path.read_text(encoding="utf-8"))
                lost.append(f"{row.get('event')} {row.get('tool')} {row.get('act')!r}")
            except (OSError, ValueError):
                lost.append(path.name)
            path.unlink(missing_ok=True)
    except OSError:
        pass
    return lost


def reconcile(table, ledger: Ledger, event: dict) -> dict:
    """Terminal reconciliation. Fails CLOSED: a gate that cannot decide has not decided, and
    reporting success by default is the one failure this whole loop exists to refuse."""
    session, agent = _ids(event)
    # THE ENDING IS REFUSED UNTIL IT IS RECONCILED, and the host's `stop_hook_active` flag does
    # not end that. It used to: the Stop after our own block returned {} unconditionally, so
    # every refusal was a one-round obstacle -- continue once, do nothing, stop, and the
    # session ended with the destruction unreconciled (DL-04). The rows are evaluated again on
    # every ending; what is bounded is the number of refusals, STOP_ROUNDS, after which the
    # ending is ALLOWED LOUDLY (a fault row and a systemMessage) rather than spent silently
    # against the host's own loop cap. Stated limit: a session that ignores three refusals ends.
    slot = effects._slot(ledger.root, session, agent)
    memory = effects._memory(slot)
    rounds = int(memory.get("stop_rounds") or 0) if event.get("stop_hook_active") is True else 0
    if rounds >= STOP_ROUNDS:
        journal.note_fault(event, "stop_rounds", f"{rounds} refused endings, obligations still open",
                           failed_closed=False, root=ledger.root)
        memory["stop_rounds"] = 0
        effects._remember(slot, memory)
        return {"systemMessage": f"keel: this ending was refused {rounds} times and its obligations "
                                 "are STILL OPEN; it is now allowed without reconciliation so the "
                                 "host's loop cap is not spent in silence. The rows stay in the ledger."}
    _effect_record(ledger, event, "stop")
    _watch_standing(table, ledger, event, session, agent)
    try:
        open_rows = ledger.open_demands(session, agent)
    except Exception as exc:
        return _block(f"keel could not read its ledger: {type(exc).__name__} "
                      "-- NOT-EVALUABLE, not a pass")
    undischarged = []
    event_name = event.get("hook_event_name", "Stop")
    for cl in table:
        # Enforce a clause only at the event it DECLARES. This read `not in (Stop, SubagentStop)`,
        # so a clause declaring Stop was also enforced at SubagentStop -- under a different agent's
        # ledger key, where its guard could not have been recorded. Measured: a subagent that only
        # read files was blocked demanding `git status` and `git fetch` under its own agent_id.
        # A clause that fires where it did not declare is the false-block that gets a gate switched
        # off, and a switched-off gate has zero coverage.
        # An ending is an ending: a clause declaring Stop is reconciled at SubagentStop too, under
        # that agent's OWN ledger key (its guards were recorded there, its artifacts are its own).
        # The earlier scoping to the exact event let a subagent push and end unreconciled (30 of
        # 31 targets under that angle); the false block it was written against was T02 demanding a
        # fetch of a session that never pushed, which is now excluded below by its occasion.
        if cl.event not in ("Stop", "SubagentStop") or event_name not in ("Stop", "SubagentStop"):
            if cl.event != event_name:
                continue
        # Keyed activations materialize their own per-key demand rows as the occasions arrive.
        # They need no synthetic session-wide standing row; open_demands above reconciles them.
        if cl.activated_by is not None and cl.activated_by.get("key_from") is not None:
            continue
        # A demand that never had its occasion is not an unmet obligation. T02's fingerprint is
        # `always`, so before this a read-only session that never pushed was blocked at Stop for a
        # fetch it had no reason to run -- a cost paid at every single ending.
        if cl.activated_by is not None and not ledger.is_licensed(
                session, agent, derive_id(session, agent, cl.id, "activated")):
            continue
        did = derive_id(session, agent, cl.id, "standing")
        if not ledger.is_licensed(session, agent, did):
            undischarged.append({"clause_id": cl.id, "reason": cl.deny_reason})

    # A HOOK THE HOST KILLED EVALUATED NOTHING. Every PreToolUse/PostToolUse leaves a marker
    # while it runs and removes it when it answers; a marker whose process is gone is an act
    # that was allowed unchecked with no trace (DL-09: the shim dies with its child, so its
    # fail-open message never prints). Named here, once, then cleared: the ending is refused
    # for it one time and the fault row is permanent.
    lost = _pending_lost(ledger.root, session)
    if lost:
        journal.note_fault(event, "hook_killed", "; ".join(lost)[:400], failed_closed=True,
                           root=ledger.root)
        undischarged.append({"clause_id": "keel", "reason": f"{len(lost)} hook evaluation(s) never "
                             f"completed, so the act(s) were allowed unchecked: {'; '.join(lost)}"})
    open_rows = list(open_rows) + undischarged
    memory["stop_rounds"] = 0 if not open_rows else rounds + 1
    effects._remember(slot, memory)
    if not open_rows:
        return {}
    # Every open row is named: the count says N and the text used to show five of them, so a
    # replay reading the names could not see the sixth, and neither could the operator.
    lines = "; ".join(f"[{r['clause_id']}] {r['reason']}" for r in open_rows)
    return _block(f"{len(open_rows)} unreconciled obligation(s): {lines}")


def session_start(table, ledger: Ledger, event: dict) -> dict:
    """Fails OPEN: a hook that cannot read its own map must not stop the session.

    Also the one place a stranded pre-rename store can be reported. It is said BOTH ways on
    purpose: in `additionalContext`, so the agent knows the ledger it is reading is not the one
    that was there yesterday, and in `systemMessage`, so the person who has to move the directory
    actually sees it. Neither costs a deny.
    """
    try:
        # The artifacts the first guards are paid by exist before the first act, so the
        # operator can observe the worktree and the remote without first being refused.
        session, agent = _ids(event)
        try:
            effects.observe(ledger.root, session, agent, str(event.get("cwd") or os.getcwd()))
        except Exception:
            pass
        try:
            # BEFORE compact: compaction rewrites every kept row's `prev`/`hash` (ledger.py
            # `compact`), so a divergence in the chain compact is about to erase must be read
            # first or it is destroyed unread. Carriage, not a decision -- `failed_closed=False`
            # -- because a session must not be blocked by a corruption check on its own log.
            divergent = ledger.verify_chain()
            if divergent is not None:
                journal.note_fault(event, "chain_divergent", f"row hash {divergent}",
                                    failed_closed=False, root=ledger.root)
        except Exception:
            pass
        try:
            ledger.compact(session)
        except Exception:
            pass
        rows = " | ".join(f"{c.id}: {c.guard}" for c in table)
        event_name = event.get("hook_event_name", "SessionStart")
        stranded = legacy_state()
        notice = "" if stranded is None else (
            f"keel: the state directory was renamed. This session reads {state_dir()}; the "
            f"pre-rename store at {stranded} is NOT being read, so obligations recorded there "
            f"are not visible here. Move or merge it, or point KEEL_STATE_DIR at it. ")
        out = _context(f"{notice}keel active, {len(table)} clauses. {rows}", event_name)
        if notice:
            out["systemMessage"] = notice.strip()
        return out
    except Exception:
        return {}


def _preserve_list() -> str:
    """The vendored preserve list, and the digest that says it is the vendored one."""
    path = Path(__file__).resolve().with_name("compaction.json")
    doc = json.loads(path.read_text(encoding="utf-8"))
    return doc["preserve"]


# A BARE `/compact`, and nothing else. `\S` after the command means the author typed their own
# preserve list, and an author who stated one is not to be overridden by a default -- that is the
# whole difference between supplying a missing guard and overruling a present one.
_BARE_COMPACT = re.compile(r"^\s*/compact\s*$")


def user_prompt_submit(table, ledger: Ledger, event: dict) -> dict:
    """Supply the preserve list when a compaction is asked for without one.

    THE ONLY EVENT THAT CAN REACH THE SUMMARIZER. `PreCompact` fires closer to the cut and is the
    obvious place to put this, and it does not work: its `additionalContext` is documented as
    explicitly NOT affecting compaction, and its stdout goes to the debug log. `UserPromptSubmit`
    is one of three events whose output becomes context the model acts on, and it sees the raw
    `/compact` before expansion. So the earlier event is the one with the reach.

    This fires on EVERY prompt, which makes silence the load-bearing behaviour: a line added to
    every turn is the recurring noise that gets a gate switched off. It speaks only when the
    prompt is a bare `/compact`.
    """
    text = event.get("user_input")
    if not isinstance(text, str) or not _BARE_COMPACT.match(text):
        return {}
    try:
        return _context(_preserve_list(), "UserPromptSubmit")
    except Exception:
        # A missing or unreadable vendored list must not eat the user's `/compact`.
        return {}


def pre_compact(table, ledger: Ledger, event: dict) -> dict:
    """Report an automatic cut that no preserve list steered. It cannot do more than report.

    An automatic compaction submits no prompt, so `user_prompt_submit` never runs, and this event
    cannot supply instructions to the summarizer -- the documented behaviour is that context added
    here does not affect the compaction. Blocking is the one lever it does have, and it is the
    wrong one: an automatic cut happens because the window is full, so refusing it wedges the
    session to protect a summary.

    What is left is making the loss non-silent, which is the second tier and is stated as such:
    the manual path gets the construction, the automatic path gets a sentence saying it did not.
    """
    if event.get("compact_trigger") != "auto":
        return {}
    return {"systemMessage":
            "keel: automatic compaction -- the preserve list was not applied, because this event "
            "cannot instruct the summarizer. Run `/compact` yourself to cut with it."}


HANDLERS = {
    "PreToolUse": pre_tool_use,
    "UserPromptSubmit": user_prompt_submit,
    "PreCompact": pre_compact,
    "PostToolUse": post_tool_use,
    "Stop": reconcile,
    "SubagentStop": reconcile,
    "SessionStart": session_start,
    "SubagentStart": session_start,
}


def _record(event: dict, out: dict) -> None:
    """Write the persisted trace of THIS event's outcome. Never raises, never alters `out`.

    The decision has already been made by the time this runs, and nothing here can change it -- see
    `journal`'s module docstring for why the log is deliberately powerless. What it buys is that
    "did Keel catch anything this session?" stops being unanswerable.
    """
    try:
        hook = event.get("hook_event_name")
        wire_out = out.get("hookSpecificOutput") if isinstance(out, dict) else None
        if isinstance(wire_out, dict) and wire_out.get("permissionDecision") == "deny":
            reason = str(wire_out.get("permissionDecisionReason") or "")
            named = _bracketed_ids(reason)  # one parser for the ids a message names
            journal.note_deny(event, named[0] if named else "", _subject_of(reason), reason)
        elif isinstance(out, dict) and out.get("decision") == "block":
            reason = str(out.get("reason") or "")
            journal.note_block(event, _stated_count(reason), _bracketed_ids(reason))
        elif hook in ("Stop", "SubagentStop") and not out:
            # A terminal that reconciled cleanly is a POSITIVE result, not an absence, and it is
            # the one outcome a fires-only log would erase. Recording it is what lets a reader
            # distinguish "reconciled, nothing owed" from "never reached the terminal".
            journal.note_block(event, 0, [])
    except Exception:
        pass


# `_keyed_reason` renders the ledger key into the deny the agent is shown, as "keyed on `X`".
# The row reads it back out of that rendered text rather than recomputing it, so the log can never
# disagree with what the agent was actually told -- two derivations of one fact is two facts.
#
# Anchored on the TRAILING SENTENCE, not on the closing backtick, and that is what makes the
# parse-back actually deliver the property it is here for. `[^`]{1,200}` stopped at the first
# backtick INSIDE the subject: a subject of ``api`prod.example`` renders as
# "keyed on `api`prod.example`, so the guard must name ..." and the old pattern captured `api`.
# The ledger keyed on the full operand, the wire told the agent the full operand, and the journal
# recorded a shorter, different one -- precisely the disagreement between record and reality that
# reading the fact back out of the prose exists to make impossible. A lazy span closed by the
# fixed sentence that always follows cannot be ended early by a character in the subject.
# The bound is generous rather than tight for the same reason: a subject longer than the bound
# fails to match, and a failed match reads as "session-wide", which is a WRONG fact, not a missing
# one. `journal.note_deny` truncates for storage; this must not truncate for meaning.
# BOTH halves of the rendered suffix, and the LAST match rather than the first. `_keyed_reason`
# APPENDS this suffix to the clause's own `deny_reason`, so any earlier occurrence of the phrase
# came out of the clause TEXT, not out of the renderer. A forward search found that one: a clause
# whose prose happens to contain "keyed on `x`, so the guard must name " made the journal row name
# a different operand than the message did. Reproduced -- message rendered for `real-target`, row
# recorded `wrong` -- and that single disagreement is the entire thing this recovery exists to
# make impossible. No shipped clause contains the phrase today, so this was latent; a latent hole
# in the one property the design is built on is still the hole.
_KEYED_ON_RX = re.compile(
    r"keyed on `(.{1,2000}?)`, so the guard must name `(.{1,2000}?)` too; ", re.DOTALL)


def _subject_of(reason: str) -> str:
    """The operand a deny is keyed on, as named in the message itself; "" when session-wide."""
    last = None
    for last in _KEYED_ON_RX.finditer(reason or ""):
        pass
    if last is None:
        return ""
    # The renderer writes the subject into both halves identically, so these agree by
    # construction. Group 2 is the one the sentence instructs the agent to name, and if a future
    # renderer ever let them drift, the row should follow the instruction the agent was given.
    return last.group(2)


def _stated_count(text: str):
    """The obligation count the block message states, or None when it states none.

    None, NOT 0, and the difference is a row that lies. A terminal that reconciled cleanly and a
    terminal blocked by an internal fault both reached `note_block` with nothing countable in
    hand, and a `0` default rendered them as the SAME row -- `open_count: 0, clause_ids: []` --
    which reads as "reconciled, nothing owed" for both. That is the one reading the fault case
    must never get: it is the not-evaluable outcome wearing the clean one's clothes, in the log
    whose whole purpose is telling those two apart. The clean terminal passes its 0 literally
    from its own call site; everything that merely FAILED to find a count now says so.
    """
    head = text.split(" ", 2)
    for part in head:
        # ASCII only, because `str.isdigit` and `int` DISAGREE and this loop had one of each.
        # `'\u00b2'.isdigit()` is True and `int('\u00b2')` raises ValueError, so a superscript in
        # the first three words selected a "digit" that could not be converted. The raise landed
        # in `note_block`'s blanket except and the row was dropped -- silently, in the log whose
        # stated purpose is telling "reconciled, nothing owed" apart from "never reached the
        # terminal". One predicate for both steps is what makes that unreachable rather than
        # merely unlikely.
        digits = "".join(ch for ch in part if ch in "0123456789")
        if digits:
            return int(digits)
    return None


def _bracketed_ids(text: str) -> list:
    return re.findall(r"\[([A-Za-z0-9._-]{1,40})\]", text or "")


def main() -> int:
    try:
        raw, repaired = wire.read_stdin()
        if not raw.strip():
            # A closed or broken stdin. This used to parse as {} and answer {} with no row and
            # no message: the one unreadable envelope that was SILENT (DL-08).
            raise ValueError("empty envelope")
        event = json.loads(raw)
        if not isinstance(event, dict):
            raise ValueError("event is not an object")
        # The other surrogate door: valid UTF-8 bytes whose JSON text carried an unpaired \uD8xx
        # escape, which json.loads materializes as a real lone surrogate. `read_stdin` cannot see
        # that one -- the escape is plain ASCII in the raw text -- so the parsed object is scrubbed
        # too. Both doors end at the same `derive_id` raise, and a raise there is swallowed by the
        # per-clause isolation as a SILENT ABSTENTION. See `keel.wire`.
        # Counted SEPARATELY, never summed into `repaired`: one counts undecodable bytes, the
        # other counts surrogate escapes that were valid ASCII on the wire. See `note_repair`.
        event, escaped = wire.scrub(event)
    except Exception as exc:
        print(f"keel: unreadable event ({type(exc).__name__}) -- NOT-EVALUABLE", file=sys.stderr)
        journal.note_fault({}, "unreadable_event", type(exc).__name__, failed_closed=False)
        print(json.dumps(_open_not_evaluable(f"the event could not be read "
                                             f"({type(exc).__name__})")))
        return 0
    if repaired or escaped:
        # Recorded, and NOT a fault: the event WAS evaluated, on a repaired payload. Conflating the
        # two would inflate the count of unevaluated calls, which is the one number the log exists
        # to keep honest.
        journal.note_repair(event, repaired, escaped=escaped)
    # One event, one set of probe measurements. Free in production (fresh process per event);
    # explicit here so a host that ever reuses a process cannot inherit stale answers.
    C.reset_probe_cache()
    try:
        table = C.load_default()
        journal.note_session(event, len(table))
        # Absence must never read as green. Found by removing the input: with the clause directory
        # empty, `rm -rf build/` was ALLOWED and Stop returned {} -- a clean bill of health from a
        # gate that checked nothing, while everyone believes it is on. Loading is this function's
        # domain, so the floor lives here and not in reconcile(), which owns reconciliation and is
        # legitimately handed an empty table by callers isolating the ledger.
        if not table:
            print("keel: 0 clauses loaded from "
                  f"{C.default_bundle()} -- NOT-EVALUABLE, nothing was checked", file=sys.stderr)
            # The strongest "nothing was checked" signal there is, and previously it existed only
            # as a stderr line -- i.e. in the debug log, where a hook that exits 0 sends output
            # nobody reads. The session row already says `clauses: 0`; this says it happened on
            # this event too.
            journal.note_fault(event, "zero_clauses", f"0 clauses from {C.default_bundle()}",
                               failed_closed=event.get("hook_event_name") in ("Stop", "SubagentStop"))
            if event.get("hook_event_name") in ("Stop", "SubagentStop"):
                print(json.dumps(_block(
                    "keel loaded 0 clauses -- NOT-EVALUABLE, not a pass. Nothing was checked "
                    "this session, so this is not a clean run.")))
                return 0
        handler = HANDLERS.get(event.get("hook_event_name"))
        if handler is None:
            # AN EVENT KEEL HAS NEVER HEARD OF EVALUATES NOTHING AND PAYS NOTHING. The wildcard
            # default used to route it through pre_tool_use, where it could not raise a demand
            # (no clause declares it) but could discharge one: a free guard (DL-13).
            journal.note_fault(event, "unknown_event", str(event.get("hook_event_name"))[:80],
                               failed_closed=False)
            print(json.dumps(_open_not_evaluable(
                f"unknown event {event.get('hook_event_name')!r}; nothing was evaluated and "
                "nothing was discharged")))
            return 0
        ledger = Ledger()
        marker = _pending_mark(ledger.root, event)
        try:
            out = handler(table, ledger, event)
        finally:
            if marker is not None:
                marker.unlink(missing_ok=True)
    except Exception as exc:
        out = _closed_not_evaluable(event, type(exc).__name__)
        print(f"keel: {type(exc).__name__} -- NOT-EVALUABLE, failing "
              f"{'closed' if out is not None else 'open'}", file=sys.stderr)
        journal.note_fault(event, "evaluation", type(exc).__name__, failed_closed=out is not None)
        if out is None:
            print(json.dumps(_open_not_evaluable(
                f"{event.get('hook_event_name') or 'this event'} raised "
                f"{type(exc).__name__} and has no deny wire")))
            return 0
    try:
        encoded = json.dumps(out)
    except Exception as exc:
        closed = _closed_not_evaluable(event, f"serialization {type(exc).__name__}")
        print(f"keel: {type(exc).__name__} while serializing -- NOT-EVALUABLE, failing "
              f"{'closed' if closed is not None else 'open'}", file=sys.stderr)
        journal.note_fault(event, "serialization", type(exc).__name__,
                           failed_closed=closed is not None)
        if closed is None:
            print(json.dumps(_open_not_evaluable(
                f"the verdict could not be serialized ({type(exc).__name__}) and "
                f"{event.get('hook_event_name') or 'this event'} has no deny wire")))
            return 0
        encoded = json.dumps(closed)
    _record(event, out if isinstance(out, dict) else {})
    print(encoded)
    return 0


if __name__ == "__main__":
    sys.exit(main())
