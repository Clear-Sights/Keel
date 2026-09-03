"""The plant harness, and the two roots every plant needs to find.

WHY THE ROOTS ARE SEARCHED FOR RATHER THAN COUNTED. These exact bytes run from two different
places. In the development repository the suite sits at `plugin/tests/`, beside the `keel`
package. Here it sits at `tests/`, at the repository root and OUTSIDE `plugin/` -- because
`plugin/` is precisely what the marketplace installs (`git-subdir`, `path: "plugin"`), so a test
file inside it is a test file on every user's machine. Every module in this suite used to open
with `root = Path(__file__).resolve().parents[1]`, which names a DIFFERENT directory in each of
those two layouts; deriving the roots by looking for the package instead is what lets the two
copies stay byte-identical across the move, and is the reason that line is now written once.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# The directory `tests/` sits in: `plugin/` in development, the repository root when shipped.
# A child running `python3 -m unittest tests.…` needs this as its cwd for the target to resolve.
TESTS_CWD = Path(__file__).resolve().parents[1]

# The directory holding the `keel` package. The same directory in both layouts, reached
# differently: it IS `TESTS_CWD` in development, and `TESTS_CWD / "plugin"` when shipped.
PLUGIN = TESTS_CWD if (TESTS_CWD / "keel").is_dir() else TESTS_CWD / "plugin"

# The repository root, for the gates that read COMMITTED bytes through `git show`.
REPO = PLUGIN.parent

if str(PLUGIN) not in sys.path:
    # So `import keel` does not depend on which directory the runner was started from.
    sys.path.insert(0, str(PLUGIN))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# Where a plant records that a source file is CURRENTLY mutated. Outside the repository, because
# it must not be committed or shipped; outside this process, because the thing it guards against
# is this process dying; keyed on the checkout path, so two checkouts on one machine cannot adopt
# each other's wreckage.
PLANT_STATE = Path(tempfile.gettempdir()) / f"keel-plants-{_sha(str(REPO).encode())[:12]}"

# Set by `smoke_replace` in the child it runs, and inherited by anything the child spawns. A
# process running INSIDE a plant must never recover it: the mutation is the point, and undoing it
# mid-flight would make every plant report green for the wrong reason.
PLANT_ACTIVE_ENV = "KEEL_PLANT_ACTIVE"


def recover_stale_plants(state: Path | None = None) -> list[str]:
    """Undo any mutation a killed plant left behind, and say where. Returns what it recovered.

    A plant mutates a source file, runs a child against it, and restores. Restore is registered
    with `addCleanup` and called again inline -- and a SIGKILL skips both, so an interrupt or a
    timeout while the child runs leaves the working tree carrying the planted fault.

    MEASURED, and it cost a false diagnosis: a run killed at a ten-minute timeout left
    `plugin/keel/ledger.py` missing the two lines one plant removes. The next suite reported a
    missing dedup guard in a file nobody had edited, and the comment describing that guard was
    still sitting above the hole -- which reads exactly like a real defect. `git diff` is what
    told the two apart, and nothing in the suite pointed at it.

    So the reversal is made to outlive the process that made it: the marker is written before the
    mutation and deleted after the restore, and whatever finds a marker later does the restore
    the dead process could not. This is the resting-state repair rather than a warning, because a
    warning still leaves the next run measuring a tree that is not the tree under test.

    RECOVERY IS REFUSED, NEVER GUESSED, when the file no longer holds what the plant wrote:
    someone has edited it since, and silently overwriting their work with a backup would be a
    worse failure than the one being repaired.
    """
    state = PLANT_STATE if state is None else Path(state)
    if os.environ.get(PLANT_ACTIVE_ENV) or not state.is_dir():
        return []
    recovered = []
    for marker in sorted(state.glob("*.json")):
        record = json.loads(marker.read_text(encoding="utf-8"))
        target, backup = Path(record["path"]), Path(record["backup"])
        current = target.read_bytes() if target.exists() else b""
        if _sha(current) == record["original"]:
            marker.unlink()  # the restore ran and only the marker leaked; nothing to undo
            continue
        if _sha(current) != record["mutated"]:
            raise RuntimeError(
                f"a plant died leaving {target} mutated (pid {record.get('pid')}), and the file "
                f"has been edited since -- this cannot be undone without discarding that edit. "
                f"The bytes from before the plant are at {backup}; compare, then delete "
                f"{marker} to clear this.")
        if not backup.exists():
            raise RuntimeError(
                f"a plant died leaving {target} mutated (pid {record.get('pid')}) and its backup "
                f"{backup} is gone. Restore that file from git, then delete {marker}.")
        target.write_bytes(backup.read_bytes())
        backup.unlink()
        marker.unlink()
        recovered.append(str(target))
    if recovered:
        # stderr, and unconditional: a repair nobody is told about is how the same kill becomes a
        # mystery twice. The suite's own output is the seat that reads this.
        print(f"plant_support: restored {len(recovered)} file(s) left mutated by a killed plant: "
              + ", ".join(recovered), file=sys.stderr)
    return recovered


recover_stale_plants()


def record(**eff) -> dict:
    """A full observation record for an act that changed nothing in the world, plus `eff`.

    DERIVED, not restated. Seven test modules carried their own copy of one dict comprehension
    that re-listed which effect names are list-valued -- a rule with seven homes, each of which
    goes quiet the day `EFFECTS` gains a list. `read_delta` is the observer's OWN answer for an
    act that touched nothing (the host Read path), so the shape here is the shape the dispatcher
    receives in production. Its `state` and `event` are never read for an event naming no file.

    `remote_landed` is NOT-EVALUABLE: nothing was pushed, so nothing landed, and False would
    claim a measurement that was not made.
    """
    from keel import effects
    rec = effects.read_delta(PLUGIN, {})
    rec["remote_landed"] = None
    rec.update(eff)
    return rec


def hook_decision(payload: dict, state, *, timeout=60) -> dict:
    """One event through the SHIPPED shim, as the single decision object it printed.

    `hooks/dispatch.sh` is the carriage the host actually invokes, so driving it rather than
    `keel.dispatch` is what makes a cell cover the wiring as well as the rule. Two modules wrote
    this call out identically; `{}` IS the allow envelope, and reading an empty-looking body as
    "still denied" is a misreading this suite has made before.
    """
    done = subprocess.run(["bash", str(PLUGIN / "hooks" / "dispatch.sh")],
                          input=json.dumps(payload), capture_output=True, text=True,
                          timeout=timeout,
                          env={**os.environ, "KEEL_STATE_DIR": str(state),
                               "CLAUDE_PLUGIN_ROOT": str(PLUGIN)})
    return json.loads(done.stdout.strip() or "{}")


def run_dispatcher(payload, state, *, cwd=None, timeout=None) -> subprocess.CompletedProcess:
    """The SHIPPED dispatcher as a child process, in the environment it needs -- one spelling.

    Six call sites across four modules each wrote this `subprocess.run` out in full, so the two
    variables that decide whether `keel` resolves at all had six writers. Returned raw, because
    the surface tests read the exit code and stderr as well as the body.
    """
    return subprocess.run(
        [sys.executable, "-m", "keel.dispatch"], input=payload,
        text=not isinstance(payload, bytes), capture_output=True, timeout=timeout,
        cwd=None if cwd is None else str(cwd),
        env={**os.environ, "KEEL_STATE_DIR": str(state),
             "CLAUDE_PLUGIN_ROOT": str(PLUGIN), "PYTHONPATH": str(PLUGIN)})


def dispatch_event(event, state, **kwargs) -> dict:
    """One event through `run_dispatcher`, as the single decision object it printed.

    `{}` IS the allow envelope. Reading an empty-looking body as "still denied" is a misreading
    this suite has made before; callers assert on the parsed object, never on emptiness.
    """
    payload = event if isinstance(event, (str, bytes)) else json.dumps(event)
    done = run_dispatcher(payload, state, **kwargs)
    out = done.stdout if isinstance(done.stdout, str) else done.stdout.decode()
    return json.loads(out or "{}")


def _drop_bytecode(path: Path) -> None:
    """Delete any cached bytecode for `path`, so the next import reads the bytes on disk.

    WHY, and it is not hygiene. CPython treats a `.pyc` as current when the source's mtime AND
    size match what the cache recorded, and mtime is stored to the second. A plant that swaps one
    equal-length run of bytes -- `60` for `10`, `+ 1` for `+ 0`, both live in this suite -- changes
    neither, so a mutation landing in the same second as the last compile is INVISIBLE to the next
    interpreter: it loads the stale bytecode and runs the unmutated code.

    That breaks a plant in both directions, and the quiet direction is the dangerous one. The
    child can miss the fault and report the target green, which `smoke_replace` correctly calls an
    inert plant -- a false alarm costing an investigation. Or the restore can be the write that
    collides, leaving a LATER process reading the mutant long after the file on disk is correct;
    that one was observed twice as a suite failure naming a value no file contained.

    Both writes below are followed by this call, so the window never opens.
    """
    cache = path.parent / "__pycache__"
    if not cache.is_dir():
        return
    for stale in cache.glob(path.stem + ".*.pyc"):
        try:
            stale.unlink()
        except OSError:
            pass


# Targets already observed green on the UNMUTATED tree in this process. Being green without the
# fault is a property of the TARGET, and every plant restores (and asserts the restore) before it
# returns, so the tree those runs measure is one tree: two plants naming one target need one run
# of it, not two. MEASURED: `test_measured` plants twice on
# `test_every_row_recomputes_to_the_value_it_claims`, whose sweep re-runs the 26-session corpus
# replay -- 17 s of a 238 s suite spent proving the same target green a second time.
_GREEN_ALREADY: set[str] = set()


def smoke_replace(case: unittest.TestCase, path: Path, old: bytes, new: bytes,
                  target: str, expected: str) -> str:
    """Mutate one seam, prove the NAMED test goes red because of it, restore, return the output.

    The child's environment is set explicitly rather than inherited, because the two directories
    it needs are no longer the same one: `TESTS_CWD` is where `tests.…` resolves from, `PLUGIN` is
    where `keel` resolves from, and in the shipped layout those are parent and child. A plant
    that ran only when the parent happened to be launched from the right directory would report a
    green seam for the wrong reason.

    The child's combined output is RETURNED so a caller can assert a property of its OWN on it.

    THE TARGET IS RUN GREEN FIRST, and that run is the point (once per target -- see
    `_GREEN_ALREADY`). A plant that only shows the target
    RED with the fault is satisfied by a target that is red ALWAYS -- one already broken, or one
    whose `expected` string went stale when the code moved underneath it. That is not
    hypothetical: a plant in this family kept asserting a count that had changed, and stayed
    "passing" because red-with-fault was all it ever checked. So the target must be observed GREEN
    on the unmutated file first; only then does the red run below carry information.

    That property lives HERE rather than in each caller, because it is the same property at every
    plant site and a rule with two homes drifts apart at the first edit. It also means a caller's
    body need not re-assert anything to be a real test: `target` names a single test METHOD at
    every plant site, so the child runs exactly one test and the green-then-red pair already
    proves THAT test went red BECAUSE of this seam. Ceremony is not the same as teeth.
    """
    original = path.read_bytes()
    case.assertIn(old, original, f"plant seam changed in {path}")
    mutated = original.replace(old, new, 1)
    backup = tempfile.NamedTemporaryFile(prefix=path.name + ".", delete=False)
    backup_path = Path(backup.name)
    backup.write(original)
    backup.close()
    # The marker `recover_stale_plants` reads if this process is killed while the file is
    # mutated. Named after the backup, so one plant's wreckage is one marker naming one backup.
    marker = PLANT_STATE / (backup_path.name + ".json")
    def restore() -> None:
        if backup_path.exists():
            path.write_bytes(backup_path.read_bytes())
            _drop_bytecode(path)
            backup_path.unlink()
        # After the file, never before: a kill in between leaves a marker whose target already
        # matches `original`, which recovery reads as "the restore ran" and simply clears.
        marker.unlink(missing_ok=True)
    case.addCleanup(restore)
    def run() -> subprocess.CompletedProcess:
        return subprocess.run(["python3", "-m", "unittest", target], cwd=TESTS_CWD,
                              text=True, capture_output=True, check=False,
                              env={**os.environ, "PYTHONPATH": str(PLUGIN),
                                   PLANT_ACTIVE_ENV: marker.name})

    if target not in _GREEN_ALREADY:
        before = run()
        case.assertEqual(0, before.returncode,
                         f"{target} is not green BEFORE the seam is mutated, so the red run below "
                         f"would prove nothing:\n{before.stdout}{before.stderr}")
        _GREEN_ALREADY.add(target)
    PLANT_STATE.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"path": str(path), "backup": str(backup_path), "pid": os.getpid(),
                                  "original": _sha(original), "mutated": _sha(mutated)}),
                      encoding="utf-8")
    path.write_bytes(mutated)
    _drop_bytecode(path)
    done = run()
    output = done.stdout + done.stderr
    case.assertNotEqual(0, done.returncode, output)
    case.assertIn(expected, output)
    restore()
    case.assertEqual(original, path.read_bytes(), f"restore differs from backup: {path}")
    return output
