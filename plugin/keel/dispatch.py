"""One entrypoint, every event. A capability is a row, never a module.

Adding an event is adding a row to HANDLERS, never another branch in main(). The lookup's default
is the wildcard: an event with no specialist row is still held to the clause table, so newly wired
events cannot silently bypass evaluation.

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
import re
import sys
from pathlib import Path

from . import clauses as C
from . import journal, wire
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

# THE PRE-RENAME SPELLING, STILL HONOURED. The rename to `keel` changed the marker's name, so
# every exemption already written in a user's scripts and notes stopped working -- and stopped
# working SILENTLY, which is the part that matters: a marker that no longer parses is not a
# marker, so the call was simply denied with no hint that a rename was the reason. Measured:
# `ALLOW.search('# gyroscope-allow: approved')` returned False. Honouring the old spelling with a
# message that names the rename is strictly better than either alternative -- refusing it strands
# work for no gain, and honouring it quietly leaves the old name alive forever.
ALLOW_LEGACY = re.compile(r"^#\s*gyroscope-allow:\s*(\S.*)$")


def _allow_marker(command: str):
    """`(spelling, reason)` from the command's leading comment header, or None.

    The reason travels with it because it is the auditable half: an exemption without one is not
    an exemption, and both patterns refuse a marker with nothing after it. The spelling travels
    with it so the caller can say something about the old one.
    """
    for line in command.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith("#"):
            # Command text. Everything from here on is payload, not preamble.
            return None
        found = ALLOW.match(stripped)
        if found:
            return "keel", found.group(1)
        found = ALLOW_LEGACY.match(stripped)
        if found:
            return "gyroscope", found.group(1)
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


_MISSING_FIELD = None


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
        fields = C.subject_fields(spec)
        raw = _MISSING_FIELD
        for field in fields:
            candidate = _get(event, field)
            if isinstance(candidate, str) and candidate:
                raw = candidate
                break
        # A segment-scoped predicate matched ONE segment; the subject must be extracted
        # from that segment, not the whole string, or a two-command line keys the wrong
        # operand and the deny names something the guard cannot discharge.
        scoped = C.matching_segment(clause.fingerprint, event)
        if scoped is not None:
            raw = scoped
        if not isinstance(raw, str):
            return ""
        m = re.search(spec.get("pattern") or "", raw)
        if not m:
            return ""
        try:
            return str(m.group(spec.get("group", 1)) or "")[:200]
        except (IndexError, re.error):
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
    anchor = getattr(clause, "construction", "") or ""
    if not C.CONSTRUCTION_ANCHOR.fullmatch(anchor):
        return ""
    return f" Construction: {anchor}."


def _first_index(clause, event: dict, predicate, command: str) -> int:
    """Index of the first segment satisfying `predicate`, or -1.

    Whole-string matching cannot order a guard against the act it guards, which is how
    `git push origin main && git status` licensed its own push: `discharges()` was true of the
    string, so the push never reached the demand. Order is the entire question, so the answer has
    to be computed per segment.
    """
    # `C.segments` directly: the wrapper that used to stand here returned it unchanged and
    # carried a second copy of the segmentation rules in its docstring -- a copy that had already
    # gone stale, since it still listed `;` `&&` `||` `|` after a newline became a separator too.
    # One implementation, one description of it.
    for index, segment in enumerate(C.segments(command)):
        probe = dict(event)
        probe["tool_input"] = {**(event.get("tool_input") or {}), "command": segment}
        try:
            if predicate(clause, probe):
                return index
        except Exception:
            continue
    return -1


def _block(reason: str) -> dict:
    return {"decision": "block", "reason": f"{_PREFIX}: {reason}"}


def _context(text: str, event_name: str = "SessionStart") -> dict:
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


def _applicable(table, event: dict):
    name, tool = event.get("hook_event_name"), event.get("tool_name")
    for cl in table:
        if cl.event != name:
            continue
        if cl.tools and cl.tools != ["*"] and tool not in cl.tools:
            continue
        yield cl


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
        if marker[0] == "gyroscope":
            # An allow that says so. `systemMessage` reaches the user, which is where a rename
            # they have to act on belongs; the call itself is exempted exactly as before.
            return {"systemMessage": "keel: `gyroscope-allow:` is the pre-rename spelling of this "
                                     "marker. It still exempts the call; rename it to "
                                     "`keel-allow:`."}
        return {}
    _watch_standing(table, ledger, event, session, agent)
    command = _get(event, "tool_input.command")
    for cl in _applicable(table, event):
        try:
            if C.discharges(cl, event):
                # A guard only licenses acts that come AFTER it. When one string carries both, the
                # segment order decides: guard-then-act discharges, act-then-guard does not, and
                # `git push && git status` is the second. Handling it exactly as the match below
                # does is what turns the self-licence back into a deny.
                act_at = guard_at = -1
                if isinstance(command, str):
                    act_at = _first_index(cl, event, C.match, command)
                    guard_at = _first_index(cl, event, C.discharges, command)
                subject = _subject(cl, event)
                did = derive_id(session, agent, cl.id, subject)
                if act_at != -1 and guard_at > act_at:
                    if not ledger.is_licensed(session, agent, did):
                        ledger.demand(Demand(id=did, session=session, agent=agent,
                                             clause_id=cl.id, subject=subject,
                                             reason=cl.deny_reason))
                        return _deny(_keyed_reason(cl, subject))
                    continue
                ledger.discharge(session, agent, did, "guard call observed")
                continue
            if C.match(cl, event):
                subject = _subject(cl, event)
                if isinstance(cl.subject, dict) and not subject:
                    # The extractor found no operand, so this event cannot be keyed. Denying
                    # under the empty key would merge every demand for this clause into one
                    # bucket; passing would be absence-counts-as-pass. It is NOT-EVALUABLE, so
                    # the clause abstains on this event and says nothing about it.
                    continue
                did = derive_id(session, agent, cl.id, subject)
                # The licence must be an OBSERVED discharge, never merely an absent demand.
                if ledger.is_licensed(session, agent, did):
                    continue
                ledger.demand(Demand(id=did, session=session, agent=agent,
                                     clause_id=cl.id, subject=subject,
                                     reason=cl.deny_reason))
                return _deny(_keyed_reason(cl, subject))
        except Exception:
            continue
    return {}


def post_tool_use(table, ledger: Ledger, event: dict) -> dict:
    session, agent = _ids(event)
    _watch_standing(table, ledger, event, session, agent)
    for cl in _applicable(table, event):
        try:
            if C.discharges(cl, event):
                did = derive_id(session, agent, cl.id, _subject(cl, event))
                ledger.discharge(session, agent, did, "guard call completed")
        except Exception:
            continue
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
                    ledger.demand(Demand(id=did, session=session, agent=agent, clause_id=cl.id,
                                         subject=subject, reason=cl.deny_reason))
                    # NO `continue` HERE, and the reason is the whole shape of a keyed standing
                    # clause: ONE ACT CAN BE BOTH THE OCCASION AND THE GUARD. C08 is the case --
                    # running a checker's own can-fail plant both produces a PASS that could be
                    # cited AND observes that checker failing. Skipping the discharge branch
                    # after demanding made such an act raise an obligation it had already
                    # satisfied, so proving a checker can fail left the ending blocked by the
                    # very clause the proof answers. Both sides key on `standing:{key}`, so the
                    # discharge below lands on the row just raised and the pair nets clean.
                    #
                    # This is NOT the self-licence `pre_tool_use` refuses. That one is two
                    # SEGMENTS in one string with the act before the guard -- `git push && git
                    # status` -- where the guard arrives too late to have licensed anything.
                    # Here there are not two acts: the plant IS the observation, so there is no
                    # order for it to be in. An ordinary run of the same checker still demands
                    # and does not discharge, because the guard requires the fault-proving form.
                else:
                    # The UNKEYED shape only. Dropping the `continue` above to let one act both
                    # raise and satisfy a keyed obligation also dropped the keyed branch into
                    # this pair, so every keyed activation wrote a demand and its immediate
                    # discharge under the subject "activated" -- rows that net to zero and mean
                    # nothing, in the journal whose whole job is saying what was owed. Benign to
                    # the verdict, junk to a reader, and two shapes wearing one code path.
                    aid = derive_id(session, agent, cl.id, "activated")
                    ledger.demand(Demand(id=aid, session=session, agent=agent, clause_id=cl.id,
                                         subject="activated", reason="occasion observed"))
                    ledger.discharge(session, agent, aid, "occasion observed")
            if C.discharges(cl, event):
                key = C.event_key(cl.discharged_by, event)
                if cl.discharged_by.get("key_from") is not None and not key:
                    continue
                subject = f"standing:{key}" if key else "standing"
                did = derive_id(session, agent, cl.id, subject)
                ledger.discharge(session, agent, did, "standing guard observed")
        except Exception:
            continue


def reconcile(table, ledger: Ledger, event: dict) -> dict:
    """Terminal reconciliation. Fails CLOSED: a gate that cannot decide has not decided, and
    reporting success by default is the one failure this whole loop exists to refuse."""
    # Claude Code marks the Stop/SubagentStop caused by our own preceding block. Re-blocking that
    # event cannot discharge an obligation: it only spends another forced continuation until the
    # host's block cap fails open. Quarantine this repeated decision (not the clauses or ledger
    # rows); the named successor is the next non-active terminal event, which evaluates them again.
    if event.get("stop_hook_active") is True:
        return {}
    session, agent = _ids(event)
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

    open_rows = list(open_rows) + undischarged
    if not open_rows:
        return {}
    lines = "; ".join(f"[{r['clause_id']}] {r['reason']}" for r in open_rows[:5])
    return _block(f"{len(open_rows)} unreconciled obligation(s): {lines}")


def session_start(table, ledger: Ledger, event: dict) -> dict:
    """Fails OPEN: a hook that cannot read its own map must not stop the session.

    Also the one place a stranded pre-rename store can be reported. It is said BOTH ways on
    purpose: in `additionalContext`, so the agent knows the ledger it is reading is not the one
    that was there yesterday, and in `systemMessage`, so the person who has to move the directory
    actually sees it. Neither costs a deny.
    """
    try:
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
            clause_id = ""
            start = reason.find("[")
            end = reason.find("]", start)
            if start != -1 and end != -1:
                clause_id = reason[start + 1:end]
            journal.note_deny(event, clause_id, _subject_of(reason), reason)
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
    repaired = escaped = 0
    try:
        raw, repaired = wire.read_stdin()
        event = json.loads(raw or "{}")
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
        out = HANDLERS.get(event.get("hook_event_name"), pre_tool_use)(table, Ledger(), event)
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
