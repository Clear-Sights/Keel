#!/usr/bin/env python3
"""Attempt each child-worker capability and report what actually happened.

    python3 "$CLAUDE_PLUGIN_ROOT/tools/probe_child_capability.py" \
        --writable-home --response-transport --result-write

    python3 "$CLAUDE_PLUGIN_ROOT/tools/probe_child_capability.py" \
        --target BRIEF --after-failure --require-change

WHY THIS FILE EXISTS. `U01` and `U02` deny a nested-worker launch until this command is on record.
It had never existed -- not in this repository, not in the development repository, not at any commit
in either history. Both clauses shipped for the whole life of the plugin discharging on a file
nobody had written, so firing either one denied the act and handed the operator a command that could
not run: no way forward but abandoning the work or switching the gate off. A guard with no runnable
remedy is worse than no guard, because the operator who hits it learns that the gate lies.

It is written rather than withdrawn because the occasion is real. A nested worker that cannot write
its home, cannot get a response back, or cannot leave a result behind fails silently and late --
after the expensive part -- and the parent inherits an empty success. That is exactly the state the
plugin exists to refuse: left alone it heals by neither time nor retry.

WHAT IT DOES, AND WHAT IT REFUSES TO DO. Every probe here ATTEMPTS the thing. None of them reads a
capability out of a config, an environment variable, or a version string and calls that a
measurement. That is the act this tool is named for: attempt the limit before recording it as one.
A probe that concluded "writable" by reading `os.access` would be an assumption wearing a
measurement's clothes -- `os.access` answers about permission bits, not about whether a write
succeeds on a full or read-only filesystem, and the difference is the whole point.

Each probe cleans up after itself and each is independent: one failing does not skip the rest, so a
single run names every missing capability instead of the first.

EXIT. 0 only when every requested probe passed. 1 when any failed, naming which. 2 on misuse.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import subprocess
import sys
import tempfile
import uuid

# The plugin's own store, imported rather than re-derived. `state_dir` already resolves
# KEEL_STATE_DIR, the codex home and the claude home in one place; a second copy of that logic here
# would be the two-writers defect `C14-one-path-one-writer` names, and it would drift the first time
# a host was added.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from keel.ledger import state_dir  # noqa: E402

# How long a spawned child may take before the probe calls it a failure. Not a preference: it is the
# bound above which a child that never returns is indistinguishable from one that cannot, and the
# probe must terminate to be usable in a hook-guarded flow. On exhaustion the probe reports FAIL for
# that capability rather than hanging or guessing.
CHILD_TIMEOUT_SECONDS = 30


def _spawn(code: str, *, extra_argv: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", code, *(extra_argv or [])],
        capture_output=True, text=True, timeout=CHILD_TIMEOUT_SECONDS,
    )


def probe_writable_home() -> tuple[bool, str]:
    """Write a file under HOME, read it back byte-identical, remove it.

    Read back rather than trusting the write: a filesystem that accepts a write and discards it --
    a full disk, an overlay that is silently read-only -- returns success from `write_text` and
    loses the bytes, which is the failure a nested worker hits at the end of its run.
    """
    token = uuid.uuid4().hex
    target = pathlib.Path.home() / f".keel-probe-{token}"
    try:
        target.write_text(token, encoding="utf-8")
        seen = target.read_text(encoding="utf-8")
    except OSError as error:
        return False, f"home is not writable: {error}"
    finally:
        try:
            target.unlink()
        except OSError:
            pass
    if seen != token:
        return False, f"home accepted a write and returned different bytes ({seen!r})"
    return True, f"wrote and read back {len(token)} bytes under {pathlib.Path.home()}"


def probe_response_transport() -> tuple[bool, str]:
    """Spawn a child and require its stdout to reach this process.

    This is the arm that fails on a host where subprocess output is swallowed. Nothing about the
    parent's own environment predicts it, so it is run rather than inferred.
    """
    token = uuid.uuid4().hex
    try:
        done = _spawn("import sys; sys.stdout.write(sys.argv[1])", extra_argv=[token])
    except (OSError, subprocess.SubprocessError) as error:
        return False, f"a child could not be spawned: {error}"
    if done.returncode != 0:
        return False, f"the child exited {done.returncode}: {(done.stderr or '').strip()[:120]}"
    if token not in done.stdout:
        return False, "the child ran but its stdout did not reach this process"
    return True, "a child's stdout reached this process intact"


def probe_result_write() -> tuple[bool, str]:
    """Spawn a child that writes a file, and require the parent to read those bytes back.

    Distinct from response transport: a host can carry stdout and still deny a child the filesystem,
    and a worker that reports through a file rather than a pipe fails only in that case.
    """
    token = uuid.uuid4().hex
    with tempfile.TemporaryDirectory() as directory:
        target = pathlib.Path(directory) / "result.txt"
        try:
            done = _spawn(
                "import pathlib, sys; pathlib.Path(sys.argv[1]).write_text(sys.argv[2])",
                extra_argv=[str(target), token],
            )
        except (OSError, subprocess.SubprocessError) as error:
            return False, f"a child could not be spawned: {error}"
        if done.returncode != 0:
            return False, f"the child exited {done.returncode}: {(done.stderr or '').strip()[:120]}"
        if not target.exists():
            return False, "the child reported success and wrote no file"
        if target.read_text(encoding="utf-8") != token:
            return False, "the child's file did not carry the bytes it was given"
    return True, "a child wrote a file this process read back intact"


def _fingerprint(target: str) -> str:
    """The target's content when it is a path, else the literal text. Hashed either way."""
    path = pathlib.Path(target)
    try:
        if path.is_file():
            return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        pass
    return hashlib.sha256(target.encode("utf-8")).hexdigest()


def _record_path(target: str) -> pathlib.Path:
    return state_dir() / "probe" / (hashlib.sha256(target.encode("utf-8")).hexdigest() + ".sha256")


def probe_require_change(target: str) -> tuple[bool, str]:
    """Refuse a re-launch that carries the same subject as the attempt that just failed.

    Re-running an identical brief after a failure spends the whole cost again to reach the same
    place. The prior art is `codex-herd`, which pins a brief by `git hash-object` so that rewriting
    it voids the receipt; the same idea, without requiring git: the subject is fingerprinted, and a
    fingerprint equal to the recorded one is the refusal.

    THE FIRST CALL CANNOT REFUSE, and says so rather than passing quietly. With nothing recorded
    there is no failed attempt to differ from, so the honest report is that the record was written,
    not that a change was observed.
    """
    record, now = _record_path(target), _fingerprint(target)
    try:
        record.parent.mkdir(parents=True, exist_ok=True)
        previous = record.read_text(encoding="utf-8").strip() if record.exists() else ""
        record.write_text(now, encoding="utf-8")
    except OSError as error:
        return False, f"the probe record under {state_dir()} is not usable: {error}"
    if not previous:
        return True, f"no prior failure recorded for this target; recorded {now[:12]}"
    if previous == now:
        return False, (
            f"the target is unchanged since the failed attempt ({now[:12]}); "
            "re-launching it spends the same cost to reach the same place"
        )
    return True, f"the target changed since the failed attempt ({previous[:12]} -> {now[:12]})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Attempt each child-worker capability and report what happened.")
    parser.add_argument("--writable-home", action="store_true")
    parser.add_argument("--response-transport", action="store_true")
    parser.add_argument("--result-write", action="store_true")
    parser.add_argument("--target")
    parser.add_argument("--after-failure", action="store_true")
    parser.add_argument("--require-change", action="store_true")
    args = parser.parse_args(argv)

    probes: list[tuple[str, tuple[bool, str]]] = []
    if args.writable_home:
        probes.append(("writable-home", probe_writable_home()))
    if args.response_transport:
        probes.append(("response-transport", probe_response_transport()))
    if args.result_write:
        probes.append(("result-write", probe_result_write()))
    if args.require_change:
        if not args.target:
            parser.error("--require-change needs --target naming the subject being re-launched")
        if not args.after_failure:
            parser.error("--require-change is a re-launch check and needs --after-failure")
        probes.append(("require-change", probe_require_change(args.target)))

    if not probes:
        parser.error("name at least one capability to probe; this tool asserts nothing on its own")

    for name, (ok, detail) in probes:
        print(f"PROBE {name}={'PASS' if ok else 'FAIL'} {detail}")
    failed = [name for name, (ok, _) in probes if not ok]
    print(f"DENOMINATOR subject=child-capability probed={len(probes)} failed={len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
