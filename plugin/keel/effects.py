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
import shutil
import subprocess
import time
from typing import Any

# name -> one sentence saying what the observation is. Closed. Read by the loader, the proof
# renderer and the README; a clause naming anything else is refused at load.
EFFECTS: dict[str, str] = {
    "files_changed": "a file that existed before the act has different content after it",
    "files_removed": "a file that existed before the act does not exist after it",
    "head_moved": "HEAD names a different commit after the act",
    "head_switched": "HEAD moved to a commit that already existed before the act: a switch or checkout, not a commit",
    "head_reset": "HEAD moved to an ancestor of where it was, and the worktree changed with it",
    "commit_signed": "the act created the commit HEAD now names, and that commit carries a signature",
    "remote_ref_moved": "a remote-tracking ref names a different commit after the act",
    "remote_landed": "every remote head this session moved is equal to a local ref (measured at the remote)",
    "pids_gone": "a process of this session (its tree, or one it launched and orphaned) that was running before the act is not running after it",
    "pids_spawned": "a process that did not exist before the act is still running after it: in this session's tree, or orphaned and started during the act",
    "pids_spawned_again": "pids_spawned, and this session had already spawned one before",
    "net_out": "the act opened an outbound connection",
    "report_null": "the act printed a null datum, or nothing, while reading a structured file",
    "report_pass": "the act printed a test-report datum with no failures",
    "report_clean": "the act printed a scanner-report datum with no findings",
    "report_fail": "the act printed a report datum with failures or findings",
}

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

    `git add -A` into a copy of the real index, then `write-tree`: the real index is untouched,
    and every blob is now in the object store, so a later `git show <tree>:<path>` recovers the
    pre-image of anything the act changed or removed.
    """
    located = _git(root, "rev-parse", "--git-path", "index")
    real = pathlib.Path(root, located.strip()) if located else pathlib.Path("")
    try:
        index.parent.mkdir(parents=True, exist_ok=True)
        if real.is_file():
            shutil.copyfile(real, index)
        elif index.exists():
            index.unlink()
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
    pid = os.getpid()
    for _ in range(2):
        fields = _stat_fields(pid)
        if not fields or len(fields) < 2:
            break
        parent = int(fields[1])
        if parent <= 1:
            break
        pid = parent
    return pid


def pids(root: int | None = None) -> dict[int, str] | None:
    """pid -> start time for every process under `root`, from /proc. The start time is what
    makes a reused pid a new process."""
    proc = pathlib.Path("/proc")
    if not proc.is_dir():
        return None
    parents: dict[int, int] = {}
    starts: dict[int, str] = {}
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        fields = _stat_fields(int(entry.name))
        if not fields or len(fields) <= _STARTTIME_AFTER_COMM:
            continue
        if fields[0] == "Z":
            # A zombie is not running: it has ended and nobody has reaped it yet. An orphaned
            # worker under a pid 1 that does not reap stays in /proc as one, so "still in
            # /proc" is not "alive".
            continue
        parents[int(entry.name)] = int(fields[1])
        starts[int(entry.name)] = fields[_STARTTIME_AFTER_COMM]
    if root is None:
        return starts
    under: dict[int, str] = {}
    for pid in starts:
        cursor, hops = pid, 0
        while cursor > 1 and hops < _ANCESTRY_CAP:
            if cursor == root:
                under[pid] = starts[pid]
                break
            cursor, hops = parents.get(cursor, 1), hops + 1
    return under


def _own_chain() -> set[int]:
    """This process and its ancestors: they are alive at one snapshot and gone at the next by
    construction, and they are never the act's doing."""
    chain, pid = set(), os.getpid()
    for _ in range(8):
        chain.add(pid)
        try:
            stat = pathlib.Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
            pid = int(stat.rsplit(")", 1)[-1].split()[1])
        except (OSError, ValueError, IndexError):
            break
        if pid <= 1:
            break
    return chain


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


# ---- snapshot and delta -----------------------------------------------------------------------

def _slot(state: pathlib.Path, session: str, agent: str) -> pathlib.Path:
    key = hashlib.sha256(f"{session}\x00{agent}".encode()).hexdigest()[:16]
    return state / f"effects-{key}"


def snapshot(state: pathlib.Path, session: str, agent: str, cwd: str) -> dict[str, Any]:
    """Record the world before the act. Written under the state dir for `delta` to read."""
    slot = _slot(state, session, agent)
    slot.mkdir(parents=True, exist_ok=True)
    root = _repo_root(cwd) if os.path.isdir(cwd) else None
    own_fields = _stat_fields(os.getpid()) or []
    snap: dict[str, Any] = {"t": time.time(), "cwd": cwd, "root": root,
                            "tree": None, "walk": None, "refs": None, "session_root": session_root(),
                            "tick": own_fields[_STARTTIME_AFTER_COMM] if len(own_fields) > _STARTTIME_AFTER_COMM else None,
                            "pids": None, "net": net_active_opens()}
    if root:
        snap["tree"] = worktree_tree(root, slot / "index.before")
        snap["refs"] = refs(root)
    elif os.path.isdir(cwd):
        snap["walk"] = walk_tree(cwd)
    table = pids(snap["session_root"])
    if table is not None:
        own = _own_chain()
        snap["pids"] = {str(p): s for p, s in table.items() if p not in own}
        # Workers this session launched and orphaned (a daemon is reparented to pid 1 and
        # leaves the tree) stay this session's processes: remembered when spawned, watched
        # while they live.
        everyone = pids()
        for pid, start in (_memory(slot).get("spawned") or {}).items():
            if everyone is not None and everyone.get(int(pid)) == start:
                snap["pids"][pid] = start
    (slot / "before.json").write_text(json.dumps(snap), encoding="utf-8")
    return snap


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


def _tree_delta(root: str, before: str | None, after: str | None) -> tuple[list | None, list | None]:
    if not before or not after:
        return None, None
    if before == after:
        return [], []
    out = _git(root, "diff-tree", "-r", "--name-status", "--no-renames", before, after)
    if out is None:
        return None, None
    changed, removed = [], []
    for line in out.splitlines():
        status, _, path = line.partition("\t")
        if status.startswith("M") or status.startswith("T"):
            changed.append(path)
        elif status.startswith("D"):
            removed.append(path)
    return changed, removed


def _walk_delta(before: dict | None, after: dict | None) -> tuple[list | None, list | None]:
    if before is None or after is None:
        return None, None
    changed = sorted(p for p, sig in before.items() if p in after and after[p] != tuple(sig))
    removed = sorted(p for p in before if p not in after)
    return changed, removed


def report_effects(stdout: Any, command: Any) -> dict[str, bool]:
    text = stdout if isinstance(stdout, str) else ""
    stripped = text.strip()
    operands = command.split() if isinstance(command, str) else []
    reads_structured = any(op.endswith((".json", ".yaml", ".yml", ".toml")) for op in operands)
    return {
        "report_null": stripped == "null" or (stripped == "" and reads_structured),
        "report_pass": bool(REPORT_PASS.search(text)) and not REPORT_FAIL.search(text),
        "report_clean": bool(REPORT_CLEAN.search(text)) and not REPORT_FAIL.search(text),
        "report_fail": bool(REPORT_FAIL.search(text)),
    }


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
        after_tree = worktree_tree(root, slot / "index.after")
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
                # A commit that existed before the act -- a ref pointed at it, or it was made
                # before the snapshot -- is being SWITCHED to. One that did not was CREATED.
                made = _git(root, "log", "-1", "--format=%ct", new_head)
                existed = (new_head in before_refs.values()
                           or (made is not None and made.strip().isdigit()
                               and int(made.strip()) < int(before.get("t", 0))))
                out["head_switched"] = existed
                out["commit_signed"] = (not existed) and "\ngpgsig " in body
    else:
        changed, removed = _walk_delta(before.get("walk"), walk_tree(before["cwd"])
                                       if os.path.isdir(before.get("cwd", "")) else None)
    out["files_changed"], out["files_removed"] = changed, removed
    everyone = pids()
    then = before.get("pids")
    if everyone is not None and then is not None:
        own = _own_chain()
        in_tree = pids(before.get("session_root")) or {}
        tick = before.get("tick")
        out["pids_gone"] = sorted(int(p) for p, s in then.items()
                                  if everyone.get(int(p)) != s)
        # New and still alive: in the session's tree, or anywhere if it started after the
        # act began -- that is a worker the act daemonized. Ambient starts elsewhere on the
        # host during the act are counted too; the cost is one demand per session.
        spawned = sorted(
            p for p, s in everyone.items()
            if p not in own and then.get(str(p)) != s
            and (p in in_tree or (tick is not None and s.isdigit() and int(s) > int(tick))))
        out["pids_spawned"] = spawned
        out["pids_spawned_again"] = bool(spawned) and memory.get("spawns", 0) > 0
        if spawned:
            memory["spawns"] = memory.get("spawns", 0) + 1
            remembered = dict(memory.get("spawned") or {})
            for p in spawned:
                remembered[str(p)] = everyone[p]
            memory["spawned"] = remembered
    net_then, net_now = before.get("net"), net_active_opens()
    if net_then is not None and net_now is not None:
        out["net_out"] = net_now > net_then
        if out["net_out"]:
            memory["net_out"] = True
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
    if not memory.get("net_out"):
        out["remote_ref_moved"], out["remote_landed"] = [], True
        return out
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
