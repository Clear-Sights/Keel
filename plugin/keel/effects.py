"""What an act DID, observed without knowing what it was called.

Coverings.v Theorem 3: a name-agnostic covering over the command string cannot separate two
acts that differ only in which program is invoked. So an occasion that must not depend on the
name cannot be read from the command at all. It is read from the world: the worktree, the refs,
the process table, the network counters, and the output the act produced. A file is gone whether
`rm`, `shred`, `find -delete` or a Python one-liner removed it; a remote ref advanced whether
`git`, `gh` or a raw HTTP call moved it; a process is gone whether `kill`, `pkill` or a signal
from inside an interpreter ended it. None of these observations mention a program.

Two moments. `snapshot()` runs at PreToolUse, before the act, and records the world. `delta()`
runs at PostToolUse, after it, and states what changed. The worktree snapshot is a git tree
object built through a private index, so every pre-image blob is retained in the object store:
a file the act destroyed can be recovered from the snapshot's tree, which is what turns a
destructive effect from irreversible into recoverable.

EVERY EFFECT NAME IS IN `EFFECTS`, and a clause may name nothing else. The set is closed here,
in one place, so the loader can refuse a name this module does not measure, and the proof can
instantiate exactly this set.

NOT-EVALUABLE IS ITS OWN VALUE. An observer that cannot run (no repository, no /proc, no
snapshot to compare against) returns None for the effects it could not measure, never False.
The dispatcher treats None as the occasion being live, because "could not see the effect" is
not "there was no effect".
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import time
from typing import Any

# name -> one sentence saying what the observation is. Closed. Read by the loader, the proof
# renderer and the README; a clause naming anything else is refused at load.
EFFECTS: dict[str, str] = {
    "files_changed": "a file has different content after the act, or exists after it and did not before",
    "files_removed": "a file that had content before the act has none after it, or does not exist",
    "head_moved": "HEAD names a different commit after the act",
    "head_switched": "HEAD moved to a commit that already existed before the act: a switch or checkout, not a commit",
    "head_reset": "HEAD moved to an ancestor of where it was, and the worktree changed with it",
    "commit_signed": "the act created the commit HEAD now names, and that commit carries a signature",
    "remote_ref_moved": "a remote-tracking ref names a different commit after the act",
    "remote_landed": "every remote head this session moved is equal to a local ref (measured at the remote)",
    "pids_gone": "a process of this session (its tree, or one it launched and orphaned) that was running before the act is not running after it",
    "pids_spawned": "a process that did not exist before the act is still running after it, assigned to this session by lineage: in its tree, or in one of its process sessions",
    "pids_spawned_again": "pids_spawned, and this session had already spawned one before",
    "net_out": "the act opened an outbound connection; NOT-EVALUABLE when the host's counter moved while no act of this session was running, because then its movement cannot be assigned to the act",
    "report_null": "the act printed a null datum, or nothing, while reading a structured file",
    "report_pass": "the act printed a test-report datum with no failures",
    "report_clean": "the act printed a scanner-report datum with no findings",
    "report_fail": "the act printed a report datum with failures or findings",
    # The guard side. A guard is discharged by what the guard act DID -- a datum the trace can
    # check, or a report shape where no trace exists -- never by what it was called.
    "report_ref": "an act that changed no file, ref or process printed a ref name or commit id the ref snapshot holds",
    "report_paths": "an act that changed no file, ref or process printed a path the worktree snapshot holds",
    "named_paths": "the worktree paths that report named, in full: what a demand keyed on a changed path is paid by",
    "named_pids": "the live pids that report named: what a demand keyed on a gone pid is paid by",
    "report_pids": "the act printed at least two pids that were alive at the snapshot",
    "report_self": "the act's output contains a whole segment of its own command: a listing that listed itself",
    "report_structured": "the act printed a JSON datum that is not null",
    "report_signature": "the act printed a signature block or a verified-signature datum",
    "report_nowarn": "report_pass, and the report carries no warning line",
    "net_read": "net_out, and the act changed no file, moved no ref, left no process, and reported no failure: a read of the network. Stated limit (K13): the host counter cannot say what was reached, so a quiet connect to a closed port is a read; the trace refuses a mention, not a wasted call",
    "report_after_change": "report_pass on an act that ran after a file changed since the last spawn",
    "report_listing": "report_pids, and the output holds no segment of the act's own command: a listing that excluded the observer",
    "observed_read": "the host Read tool returned Keel's own worktree measurement (observed.json), as written",
    "remote_read": "the host Read tool returned Keel's own remote measurement (remote.json), with tips present",
}

# Guard-side report shapes: a signature datum, and the line a warning leaves in a report.
REPORT_SIGNATURE = re.compile(
    r"-----BEGIN (?:PGP|SSH) SIGNATURE-----|\bGood signature\b|\bgpgsig\b")
WARNING_LINE = re.compile(r"(?mi)^[^\n]*\bwarning[s]?\b")
# Fewest distinct live pids a listing must claim: one number that happens to be a live pid is
# any number; two are a listing.
LISTING_FLOOR = 2
# Shortest hex prefix accepted as a commit id, git's own abbreviation floor.
ABBREV_FLOOR = 7
# Seconds between attempts to list a remote that could not be listed: each attempt costs up to
# GIT_TIMEOUT inside a hook, so an offline host is asked once a minute, not once per act.
REMOTE_RETRY_S = 60.0
# The artifacts Keel writes for the operator to observe through the host enum.
OBSERVED = "observed.json"
REMOTE = "remote.json"

# The report shapes. A closed set of DATUM shapes read off the act's own output, not of program
# names: `pytest`, `go test`, `cargo test` and a hand-written runner all print one of these, and
# a runner printing none of them is not a report, so it raises no obligation. This is the
# vocabulary the output side carries, stated where it lives.
REPORT_PASS = re.compile(
    r"(?m)(?:^|\b)(?:(\d+) passed\b(?![^\n]*\b[1-9]\d* (?:failed|error))|OK(?: \(skipped=\d+\))?$"
    r"|ok\s+\S+\s+[\d.]+s|test result: ok|0 failed|Tests:\s+\d+ passed, \d+ total|PASS\b)")
REPORT_CLEAN = re.compile(
    r"(?mi)\b(?:0|no|zero)\s+(?:findings?|issues?|problems?|vulnerabilit(?:y|ies)|violations?"
    r"|warnings?|errors?|matches)\b|\bclean\b|\ball checks passed\b")
REPORT_FAIL = re.compile(
    r"(?m)(?:\b[1-9]\d* (?:failed|errors?|findings?|issues?|problems?|vulnerabilit(?:y|ies)|"
    r"violations?)\b|^FAILED\b|\bFAIL\b|^E\s+|Traceback \(most recent call last\)|test result: FAILED"
    r"|\bAssertionError\b)")

# The non-repository fallback stats every file under cwd. Stopping at this many entries and
# reporting NOT-EVALUABLE keeps the walk under the hook's budget on a large tree: measured at
# roughly 20 000 lstat calls per second here, this is about one second of the 20 the hook has.
WALK_CAP = 20000
# Per git call. Four git calls run per snapshot and four per delta; at this ceiling the worst
# case stays inside the hook's 20 s, and a git that takes longer is a repository the observer
# cannot see, which it reports as None rather than waits on.
GIT_TIMEOUT = 5.0
# In /proc/<pid>/stat, after the ')' that closes comm, the start-time field is the 20th
# (field 22 of the whole line). A reused pid with a different start time is a new process.
_STARTTIME_AFTER_COMM = 19
# Same line, the process session id is the 4th field after the ')' (field 6 of the whole
# line: state, ppid, pgrp, session). It is what a daemonized worker keeps after it is reparented
# out of this session's tree, so it is the lineage that assigns such a worker to the session.
_SID_AFTER_COMM = 3
# Ancestors walked before giving up on a pid: a process tree deeper than this is a cycle in a
# stale /proc read, not a real ancestry, so the walk stops rather than spinning.
_ANCESTRY_CAP = 64


def _git(cwd: str, *args: str, env: dict | None = None) -> str | None:
    try:
        done = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True,
                              timeout=GIT_TIMEOUT, encoding="utf-8", errors="replace",
                              env={**os.environ, "GIT_OPTIONAL_LOCKS": "0", **(env or {})})
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        return None
    return done.stdout


# ---- the world, in pieces ---------------------------------------------------------------------

def _repo_root(cwd: str) -> str | None:
    out = _git(cwd, "rev-parse", "--show-toplevel")
    return out.strip() if out else None


def worktree_tree(root: str, index: pathlib.Path) -> str | None:
    """The tree object of the ENTIRE worktree, untracked files included, via a private index.

    `git add -A` into an EMPTY private index, then `write-tree`: the real index is untouched,
    and every blob is now in the object store, so a later `git show <tree>:<path>` recovers the
    pre-image of anything the act changed or removed. The index starts empty on purpose. A copy
    of the real one carries its stat cache, and any look (`git diff`, `git status`) refreshes
    that cache: a modified, unstaged file is then cached as clean against its stale blob, and a
    copy made after the look reported the old content, so the look itself read as a rewrite.
    Nothing cached, nothing trusted: every file is hashed at every snapshot.
    """
    try:
        index.parent.mkdir(parents=True, exist_ok=True)
        index.unlink(missing_ok=True)
    except OSError:
        return None
    env = {"GIT_INDEX_FILE": str(index)}
    if _git(root, "add", "-A", "--", ".", env=env) is None:
        return None
    out = _git(root, "write-tree", env=env)
    return out.strip() if out else None


def walk_tree(cwd: str) -> dict[str, tuple[int, int]] | None:
    """Fallback outside a repository: (size, mtime_ns) per file, capped. No pre-image kept."""
    seen: dict[str, tuple[int, int]] = {}
    try:
        for dirpath, dirnames, filenames in os.walk(cwd):
            dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", "__pycache__")]
            for name in filenames:
                path = os.path.join(dirpath, name)
                try:
                    st = os.lstat(path)
                except OSError:
                    continue
                seen[os.path.relpath(path, cwd)] = (st.st_size, st.st_mtime_ns)
                if len(seen) > WALK_CAP:
                    return None
    except OSError:
        return None
    return seen


def refs(root: str) -> dict[str, str] | None:
    out = _git(root, "for-each-ref", "--format=%(refname) %(objectname)")
    if out is None:
        return None
    table: dict[str, str] = {}
    for line in out.splitlines():
        name, _, sha = line.partition(" ")
        if name and sha:
            table[name] = sha
    head = _git(root, "rev-parse", "--verify", "-q", "HEAD")
    table["HEAD"] = head.strip() if head else ""
    return table


def _stat_fields(pid: int) -> list[str] | None:
    try:
        stat = pathlib.Path(f"/proc/{pid}/stat").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    # the comm field may contain spaces and parentheses, so split after the LAST ')'.
    return stat.rsplit(")", 1)[-1].split()


def proc_table() -> dict[int, tuple[str, int, int]] | None:
    """ONE pass over /proc: pid -> (start time, parent, process session), for what is running.

    Every caller wants a different projection of the same read -- the session's subtree, the
    whole host, a pid's session -- and a function per projection re-read every process's stat
    line two and three times per act. The start time is what makes a reused pid a new process.
    A zombie is not running: it has ended and nobody has reaped it yet, and an orphaned worker
    under a pid 1 that does not reap stays in /proc as one, so "still in /proc" is not "alive".
    """
    proc = pathlib.Path("/proc")
    if not proc.is_dir():
        return None
    table: dict[int, tuple[str, int, int]] = {}
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        fields = _stat_fields(int(entry.name))
        if not fields or len(fields) <= _STARTTIME_AFTER_COMM or fields[0] == "Z":
            continue
        table[int(entry.name)] = (fields[_STARTTIME_AFTER_COMM], int(fields[1]),
                                  int(fields[_SID_AFTER_COMM]) if fields[_SID_AFTER_COMM].isdigit() else 0)
    return table


def under(root: int, table: dict[int, tuple[str, int, int]]) -> dict[int, str]:
    """pid -> start time for the processes of `table` whose ancestry reaches `root`."""
    kin: dict[int, str] = {}
    for pid, (start, _, _) in table.items():
        cursor, hops = pid, 0
        while cursor > 1 and hops < _ANCESTRY_CAP:
            if cursor == root:
                kin[pid] = start
                break
            cursor, hops = (table[cursor][1] if cursor in table else 1), hops + 1
    return kin


def _ancestry(hops: int) -> list[int]:
    """This process and up to `hops` ancestors, nearest first. One walk, read two ways."""
    chain, pid = [], os.getpid()
    for _ in range(hops + 1):
        chain.append(pid)
        fields = _stat_fields(pid)
        if not fields or len(fields) < 2 or int(fields[1]) <= 1:
            break
        pid = int(fields[1])
    return chain


def session_root() -> int:
    """The process this hook serves: the hook's grandparent.

    The hook is `python -m keel.dispatch` under the `dispatch.sh` shim under the host, so the
    host is two levels up. Its subtree is the session: every Bash call, every background job,
    every worker the session launches. The process table is read WITHIN that subtree, not
    host-wide -- measured, host-wide observation attributed to the act every process that
    happened to end during it, and on a busy machine that is every act. A process outside the
    tree that the session ends is therefore unobserved; that boundary is the price of an
    observation that says something, and it is stated on the effect.
    """
    return _ancestry(2)[-1]


def _own_chain() -> set[int]:
    """This process and its ancestors: they are alive at one snapshot and gone at the next by
    construction, and they are never the act's doing."""
    return set(_ancestry(7))


def net_active_opens() -> int | None:
    """TCP connections this host has actively opened, ever. The DELTA across an act is the act's
    connections: measured, ambient traffic on this host adds 0 in three seconds while one `curl`
    adds 2 and one `git ls-remote` adds 3. Transmitted BYTES were tried first and rejected --
    background keepalives moved them by a kilobyte a second, so a byte floor attributed the
    host's own chatter to whatever act happened to be running."""
    try:
        lines = pathlib.Path("/proc/net/snmp").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for index, line in enumerate(lines[:-1]):
        head = line.split()
        if head and head[0] == "Tcp:" and "ActiveOpens" in head:
            values = lines[index + 1].split()
            try:
                return int(values[head.index("ActiveOpens")])
            except (ValueError, IndexError):
                return None
    return None


# ---- assignment ------------------------------------------------------------------------------
#
# AN OBSERVATION IS THE ACT'S ONLY IF IT IS ASSIGNED TO THE ACT. Every channel below assigns by
# one rule, and the tests derive their expectations from the same rule rather than carving out
# the host's behaviour case by case (three such carve-outs landed in one afternoon before this
# existed, one per red CI run, each defined where it was noticed and owned by nothing).
#
#   * A process is assigned by lineage: it is in the session's process tree, or it belongs to
#     a process session the tree held before the act, or to a process session born during the
#     act (a worker that called setsid). A process of another lineage is not this act's, even
#     if it started during it -- on a shared host, something always did.
#   * A counter with no lineage (the host's TCP ActiveOpens) is assigned by the IDLE GAP: the
#     stretch between the previous act's end and this act's start, during which nothing of this
#     session ran. A counter that moved in that gap moves on its own, so its movement across the
#     act cannot be assigned, and the effect is NOT-EVALUABLE -- which Keel treats as live, so the
#     cost of a host that opens connections by itself is one demand per session, never a miss.


def assigned_process(pid: int, sid: int, in_tree: dict[int, str], sids_then: set[int]) -> bool:
    if pid in in_tree:
        return True
    if not sid:  # kernel threads carry session 0: no lineage, never this session's
        return False
    return sid in sids_then


def assigned_counter(before: dict[str, Any], now: int | None) -> bool | None:
    then = before.get("net")
    if before.get("net_ambient") or then is None or now is None:
        return None
    return now > then


# ---- snapshot and delta -----------------------------------------------------------------------

def _slot(state: pathlib.Path, session: str, agent: str) -> pathlib.Path:
    key = hashlib.sha256(f"{session}\x00{agent}".encode()).hexdigest()[:16]
    return state / f"effects-{key}"


def snapshot(state: pathlib.Path, session: str, agent: str, cwd: str,
             opens_act: bool = True) -> dict[str, Any]:
    """Record the world before the act. Written under the state dir for `delta` to read.

    `opens_act=False` is the session start: the SAME measurement, written for the operator to
    Read, leaving no pre-image behind -- there is no act for a `delta` to describe yet, and a
    snapshot left there would let a PostToolUse with no PreToolUse report a clean act instead
    of NOT-EVALUABLE.
    """
    slot = _slot(state, session, agent)
    slot.mkdir(parents=True, exist_ok=True)
    root = _repo_root(cwd) if os.path.isdir(cwd) else None
    memory = _memory(slot)
    if root and not memory.get("remote_measured") and (
            time.time() - float(memory.get("remote_tried", 0)) >= REMOTE_RETRY_S):
        # Measured BEFORE this act's counter is read, and the idle-gap mark moved past it, so
        # the hook's own connection is neither the act's nor ambient noise. A remote that
        # could not be listed is tried again later, never more often than REMOTE_RETRY_S.
        memory["remote_measured"] = observe_remote(state, root) is not None
        memory["remote_tried"] = time.time()
        memory["net_after"] = net_active_opens()
        _remember(slot, memory)
    net_now = net_active_opens()
    net_after = memory.get("net_after")
    snap: dict[str, Any] = {"t": time.time(), "cwd": cwd, "root": root,
                            "tree": None, "walk": None, "refs": None, "session_root": session_root(),
                            "pids": None, "sids": None, "alive": None, "net": net_now,
                            "net_ambient": (net_after is not None and net_now is not None
                                            and net_now != net_after)}
    if root:
        snap["tree"] = worktree_tree(root, slot / "index")
        snap["refs"] = refs(root)
    elif os.path.isdir(cwd):
        snap["walk"] = walk_tree(cwd)
    table = proc_table()
    if table is not None:
        own = _own_chain()
        kin = under(snap["session_root"], table)
        snap["pids"] = {str(p): s for p, s in kin.items() if p not in own}
        # Workers this session launched and orphaned (a daemon is reparented to pid 1 and
        # leaves the tree) stay this session's processes: remembered when spawned, watched
        # while they live.
        for pid, start in (memory.get("spawned") or {}).items():
            if int(pid) in table and table[int(pid)][0] == start:
                snap["pids"][pid] = start
        sids = {table[p][2] for p in kin} | {table[snap["session_root"]][2]
                                              if snap["session_root"] in table else 0}
        snap["sids"] = sorted(x for x in sids if x)
        snap["alive"] = sorted(table)
    if opens_act:
        (slot / "before.json").write_text(json.dumps(snap), encoding="utf-8")
    write_observed(state, root, snap)
    return snap


def observe(state: pathlib.Path, session: str, agent: str, cwd: str) -> None:
    """Write the artifacts without opening an act: the session start, before anything runs."""
    snapshot(state, session, agent, cwd, opens_act=False)


def _memory(slot: pathlib.Path) -> dict[str, Any]:
    path = slot / "session.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"spawns": 0, "net_out": False}


def _remember(slot: pathlib.Path, memory: dict[str, Any]) -> None:
    try:
        (slot / "session.json").write_text(json.dumps(memory), encoding="utf-8")
    except OSError:
        pass


EMPTY_BLOB = "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"


def _tree_delta(root: str, before: str | None, after: str | None) -> tuple[list | None, list | None]:
    if not before or not after:
        return None, None
    if before == after:
        return [], []
    out = _git(root, "diff-tree", "-r", "--raw", "--no-renames", before, after)
    if out is None:
        return None, None
    changed, removed = [], []
    for line in out.splitlines():
        meta, _, path = line.partition("\t")
        fields = meta.split()  # :mode mode sha_before sha_after status
        if len(fields) < 5:
            continue
        status, was, now = fields[4][:1], fields[2], fields[3]
        # A file emptied is a file whose content is gone (K17): the same loss as a deletion,
        # under a different name, so it is observed as one.
        if status == "D" or (status in ("M", "T") and now == EMPTY_BLOB and was != EMPTY_BLOB):
            removed.append(path)
        elif status in ("M", "T", "A"):
            changed.append(path)
    return changed, removed


def _walk_delta(before: dict | None, after: dict | None) -> tuple[list | None, list | None]:
    if before is None or after is None:
        return None, None
    emptied = {p for p, sig in after.items() if p in before and sig[0] == 0 and before[p][0] != 0}
    changed = sorted(p for p, sig in after.items()
                     if p not in emptied and (p not in before or tuple(sig) != tuple(before[p])))
    removed = sorted(set(p for p in before if p not in after) | emptied)
    return changed, removed


def report_effects(stdout: Any, command: Any) -> dict[str, bool]:
    text = stdout if isinstance(stdout, str) else ""
    stripped = text.strip()
    operands = command.split() if isinstance(command, str) else []
    reads_structured = any(op.endswith((".json", ".yaml", ".yml", ".toml")) for op in operands)
    passed = bool(REPORT_PASS.search(text)) and not REPORT_FAIL.search(text)
    return {
        "report_null": stripped == "null" or (stripped == "" and reads_structured),
        "report_pass": passed,
        "report_clean": bool(REPORT_CLEAN.search(text)) and not REPORT_FAIL.search(text),
        "report_fail": bool(REPORT_FAIL.search(text)),
        "report_nowarn": passed and not WARNING_LINE.search(text),
        "report_signature": bool(REPORT_SIGNATURE.search(text)),
        "report_structured": _is_structured(stripped),
        "report_self": _lists_itself(text, command),
    }


def _is_structured(stripped: str) -> bool:
    if not stripped or stripped[0] not in "[{\"0123456789-tf":
        return False
    try:
        return json.loads(stripped) is not None
    except ValueError:
        return False


_SEGMENT_SPLIT = re.compile(r"\|\||&&|[|;\n]")


def _lists_itself(text: str, command: Any) -> bool:
    """A whole segment of the act's own command appears in its output.

    `ps aux | grep worker` prints its own `grep worker` line: the checker counted itself.
    `pgrep -f worker` prints pids only. `echo hi` prints `hi`, not `echo hi`. Compared as
    text the shell already expanded: `grep -v $$` prints `grep -v 4242`, which this misses --
    the stated limit, and it is the direction the old topology guard accepted too.
    """
    if not isinstance(command, str) or not text:
        return False
    for segment in _SEGMENT_SPLIT.split(command):
        segment = segment.strip()
        if len(segment) >= 3 and segment in text:
            return True
    return False


_TOKEN = re.compile(r"[A-Za-z0-9_./-]+")


def trace_effects(text: str, before: dict[str, Any], root: str | None, quiet: bool,
                  listed_self: bool = False) -> dict[str, Any]:
    """The guard effects a trace can check: a datum the report states equals one the world holds."""
    tokens = set(_TOKEN.findall(text or ""))
    out: dict[str, Any] = {"report_ref": None, "report_paths": None, "report_pids": None,
                           "named_paths": None, "named_pids": None}
    refs_then = before.get("refs")
    if refs_then is not None:
        names = {n.split("/", 2)[-1] for n in refs_then if n.startswith(("refs/heads/", "refs/remotes/"))}
        shas = [v for v in refs_then.values() if v]
        out["report_ref"] = quiet and any(
            t in names or (len(t) >= ABBREV_FLOOR and all(c in "0123456789abcdef" for c in t)
                           and any(sha.startswith(t) for sha in shas))
            for t in tokens)
    paths = None
    if root and before.get("tree"):
        listing = _git(root, "ls-tree", "-r", "--name-only", before["tree"])
        paths = listing.split("\n") if listing is not None else None
    elif before.get("walk") is not None:
        paths = list(before["walk"])
    if paths is not None:
        held = set()
        for path in paths:
            if not path:
                continue
            held.add(path)
            held.add(path.rsplit("/", 1)[-1])
            parts = path.split("/")
            for i in range(1, len(parts)):
                held.add("/".join(parts[:i]))
        # The named paths are kept in FULL, resolved from a basename or a prefix the report
        # printed, so a demand keyed on `src/main.py` is paid by `git diff` printing
        # `a/src/main.py` and by `ls src` printing `main.py`, and by nothing that printed
        # neither (AG-10: a constant payload must not pay a keyed demand).
        named = set()
        for t in tokens:
            t = t.removeprefix("./").rstrip("/")
            base = t.rsplit("/", 1)[-1]
            for path in paths:
                if path and (path == t or path.endswith("/" + t) or path.rsplit("/", 1)[-1] == base
                             or (t and path.startswith(t + "/"))):
                    named.add(path)
        out["named_paths"] = sorted(named) if quiet else []
        out["report_paths"] = quiet and bool(named)
    alive = before.get("alive")
    if alive is not None:
        live = set(alive)
        claimed = {int(t) for t in tokens if t.isdigit() and int(t) in live}
        out["named_pids"] = sorted(claimed)
        out["report_pids"] = len(claimed) >= LISTING_FLOOR
        out["report_listing"] = out["report_pids"] and not listed_self
    return out


def observe_remote(state: pathlib.Path, root: str) -> dict[str, Any] | None:
    """Measure the remote tips once and write them for the operator to Read (A03's datum).

    Returns the tips, or None when the remote could not be listed -- then no artifact is
    written, so a Read of it cannot happen and the demand stays owed: fails closed.
    """
    remotes = _git(root, "remote")
    if remotes is None:
        return None
    tips: dict[str, str] = {}
    if remotes.strip():
        listing = _git(root, "ls-remote", "--heads", "origin")
        if listing is None:
            return None
        for line in listing.splitlines():
            sha, _, name = line.partition("\t")
            if sha and name:
                tips[name] = sha
    try:
        (state / REMOTE).write_text(json.dumps({"root": root, "t": time.time(), "tips": tips},
                                               indent=1), encoding="utf-8")
    except OSError:
        return None
    return tips


def write_observed(state: pathlib.Path, root: str | None, snap: dict[str, Any]) -> None:
    """Keel's own worktree measurement, written for the operator to Read (A01/A02/T01's datum)."""
    doc: dict[str, Any] = {"root": root, "t": snap.get("t"), "head": None, "branch": None,
                           "tree": snap.get("tree"), "dirty": None, "paths": None,
                           "refs": snap.get("refs"),
                           "pids": sorted(int(p) for p in (snap.get("pids") or {}))}
    if root and snap.get("refs") is not None:
        doc["head"] = snap["refs"].get("HEAD")
        branch = _git(root, "symbolic-ref", "-q", "--short", "HEAD")
        doc["branch"] = branch.strip() if branch else None
        if doc["head"] and snap.get("tree"):
            diff = _git(root, "diff-tree", "-r", "--name-status", "--no-renames",
                        doc["head"], snap["tree"])
            doc["dirty"] = sorted(line.partition("\t")[2] for line in diff.splitlines()
                                  if line) if diff is not None else None
    elif snap.get("walk") is not None:
        doc["paths"] = sorted(snap["walk"])
    try:
        (state / OBSERVED).write_text(json.dumps(doc, indent=1), encoding="utf-8")
    except OSError:
        pass


def _artifact_read(state: pathlib.Path, event: dict[str, Any], name: str) -> bool:
    tool_input = event.get("tool_input") if isinstance(event.get("tool_input"), dict) else {}
    path = tool_input.get("file_path")
    if not isinstance(path, str) or not path:
        return False
    target = state / name
    try:
        if pathlib.Path(path).resolve() != target.resolve() or not target.is_file():
            return False
        doc = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if name == REMOTE:
        return isinstance(doc.get("tips"), dict)
    return isinstance(doc, dict) and "head" in doc


def read_delta(state: pathlib.Path, event: dict[str, Any]) -> dict[str, Any]:
    """The record for a host Read: it did nothing to the world, and it may have observed Keel's own datum."""
    out: dict[str, Any] = {name: False for name in EFFECTS}
    for name in ("files_changed", "files_removed", "remote_ref_moved", "pids_gone", "pids_spawned",
                 "named_paths", "named_pids"):
        out[name] = []
    out["observed_read"] = _artifact_read(state, event, OBSERVED)
    out["remote_read"] = _artifact_read(state, event, REMOTE)
    return out


def delta(state: pathlib.Path, session: str, agent: str, event: dict[str, Any]) -> dict[str, Any]:
    """What the act did. Every key in EFFECTS is present: a value, or None for NOT-EVALUABLE."""
    slot = _slot(state, session, agent)
    out: dict[str, Any] = {name: None for name in EFFECTS}
    tool_input = event.get("tool_input") if isinstance(event.get("tool_input"), dict) else {}
    response = event.get("tool_response") if isinstance(event.get("tool_response"), dict) else {}
    out.update(report_effects(response.get("stdout"), tool_input.get("command")))
    try:
        before = json.loads((slot / "before.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        out["not_evaluable"] = "no pre-act snapshot"
        return out
    try:
        (slot / "before.json").unlink()
    except OSError:
        pass
    memory = _memory(slot)
    root = before.get("root")
    if root:
        after_tree = worktree_tree(root, slot / "index")
        changed, removed = _tree_delta(root, before.get("tree"), after_tree)
        out["pre_image"] = before.get("tree")
        after_refs = refs(root)
        before_refs = before.get("refs")
        if after_refs is not None and before_refs is not None:
            old_head, new_head = before_refs.get("HEAD", ""), after_refs.get("HEAD", "")
            out["head_moved"] = old_head != new_head
            out["remote_ref_moved"] = sorted(
                name for name in set(before_refs) | set(after_refs)
                if name.startswith("refs/remotes/") and before_refs.get(name) != after_refs.get(name))
            out["head_reset"] = False
            out["commit_signed"] = False
            out["head_switched"] = False
            if out["head_moved"] and old_head and new_head:
                ancestor = _git(root, "merge-base", "--is-ancestor", new_head, old_head)
                out["head_reset"] = ancestor is not None and bool(changed or removed)
                body = _git(root, "cat-file", "commit", new_head) or ""
                # A commit reachable from a ref that existed before the act is being SWITCHED
                # to; one that is not was CREATED. Reachability is read from the pre-act refs,
                # never from the commit's own timestamp: a committer date is whatever the act
                # says it is (`GIT_COMMITTER_DATE`), so a backdated commit read as a switch and
                # its signature was never examined (K11). Stated limit: a checkout of a commit
                # no pre-act ref reached (a dangling or reflog-only commit) reads as created.
                existed = any(_git(root, "merge-base", "--is-ancestor", new_head, tip) is not None
                              for tip in set(before_refs.values()) if tip)
                out["head_switched"] = existed
                out["commit_signed"] = (not existed) and "\ngpgsig " in body
    else:
        changed, removed = _walk_delta(before.get("walk"), walk_tree(before["cwd"])
                                       if os.path.isdir(before.get("cwd", "")) else None)
    out["files_changed"], out["files_removed"] = changed, removed
    table = proc_table()
    then = before.get("pids")
    if table is not None and then is not None:
        own = _own_chain()
        in_tree = under(before.get("session_root") or 0, table)
        out["pids_gone"] = sorted(int(p) for p, s in then.items()
                                  if int(p) not in table or table[int(p)][0] != s)
        # New on the HOST (not merely absent from the tree's snapshot), alive, and assigned.
        alive_then, sids_then = set(before.get("alive") or []), set(before.get("sids") or [])
        spawned = sorted(
            p for p, (start, _, sid) in table.items()
            if p not in own
            and (p not in alive_then or (str(p) in then and then[str(p)] != start))
            and assigned_process(p, sid, in_tree, sids_then))
        out["pids_spawned"] = spawned
        out["pids_spawned_again"] = bool(spawned) and memory.get("spawns", 0) > 0
        if spawned:
            memory["spawns"] = memory.get("spawns", 0) + 1
            remembered = dict(memory.get("spawned") or {})
            for p in spawned:
                remembered[str(p)] = table[p][0]
            memory["spawned"] = remembered
    net_now = net_active_opens()
    out["net_out"] = assigned_counter(before, net_now)
    # Three states the ending reads: True (this session transmitted), False (every act was
    # measured and none did), None (some act could not be measured). None used to collapse into
    # False, so a session whose network was unmeasurable ended as "nothing transmitted, the push
    # landed" -- the fail-open direction, on the one clause that measures the remote.
    if out["net_out"]:
        memory["net_out"] = True
    elif out["net_out"] is None and memory.get("net_out") is not True:
        memory["net_out"] = None
    memory["net_after"] = net_now  # the next idle gap starts here
    # THE GUARD SIDE, read from the same trace. A quiet act changed nothing and left nothing.
    spawned = out.get("pids_spawned") or []
    # A LOOK IS AN ACT THAT CHANGED NOTHING IT COULD HAVE PRINTED: no file, no ref. The
    # network is not in that set -- a connection changes nothing the worktree or the refs hold,
    # and the host's counter is the one channel that moves on its own. Neither is a spawned
    # process: the printed datum is cross-checked against files and refs, and a process born
    # in the session tree during the act is as often a sibling's (a runner worker, a
    # concurrent agent) as the act's own. Measured: `git diff` beside a sibling spawn read as
    # loud on 3 of 15 CI jobs, while the spawn itself fires U01 on its own effect.
    still = changed == [] and removed == [] and not out.get("head_moved")
    out.update(trace_effects(response.get("stdout") if isinstance(response.get("stdout"), str) else "",
                             before, root, still, out["report_self"]))
    out["net_read"] = (None if out["net_out"] is None else
                       bool(out["net_out"]) and still and not out["report_fail"])
    out["report_after_change"] = bool(out["report_pass"]) and bool(memory.get("changed_since_spawn"))
    if changed:
        memory["changed_since_spawn"] = True
    if spawned:
        memory["changed_since_spawn"] = False
    out["observed_read"] = False
    out["remote_read"] = False
    _remember(slot, memory)
    return out


def at_stop(state: pathlib.Path, session: str, agent: str, cwd: str) -> dict[str, Any]:
    """The remote, measured once at the ending, and only when this session used the network.

    A session that transmitted nothing cannot have moved a remote ref, so the remote is not
    asked. A session that did is asked directly: `ls-remote` is the observation, and it is
    compared to the LOCAL refs -- a remote head equal to some local ref is a push that landed,
    whatever program pushed it; a remote head equal to nothing local is a push that did not,
    or a foreign one, and either way the ending is not clean.
    """
    slot = _slot(state, session, agent)
    memory = _memory(slot)
    out: dict[str, Any] = {"remote_ref_moved": None, "remote_landed": None}
    if memory.get("net_out") is False:
        # Measured: no act of this session transmitted, so no remote ref can have moved.
        out["remote_ref_moved"], out["remote_landed"] = [], True
        return out
    # Transmitted, or could not tell: ask the remote rather than assume.
    root = _repo_root(cwd) if os.path.isdir(cwd) else None
    if not root:
        return out
    remotes = _git(root, "remote")
    if remotes is not None and not remotes.strip():
        # A repository with no remote has no remote ref to have moved.
        out["remote_ref_moved"], out["remote_landed"] = [], True
        return out
    local = refs(root)
    listing = _git(root, "ls-remote", "--heads", "origin")
    if local is None or listing is None:
        out["not_evaluable"] = "the remote could not be listed"
        return out
    local_shas = set(local.values())
    moved, unlanded = [], []
    for line in listing.splitlines():
        sha, _, name = line.partition("\t")
        tracking = local.get("refs/remotes/origin/" + name.removeprefix("refs/heads/"))
        if tracking is not None and tracking != sha:
            moved.append(name)
            if sha not in local_shas:
                unlanded.append(name)
    out["remote_ref_moved"] = moved
    out["remote_landed"] = not unlanded
    return out
