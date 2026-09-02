"""The committed hooks.json must be a file the HOST will actually load.

This gate exists because its absence already shipped. `hooks.json` carried the event names at
the top level, where the host expects them nested under a "hooks" key, so the plugin reported

    Status: x failed to load
    Error: Hook load failed: [{"expected":"record","code":"invalid_type","path":["hooks"],
                              "message":"Invalid input: expected record, received undefined"}]

and registered ZERO hooks for the life of the project. Every green in this repo was over a gate
the host had declined to install, and nothing here could see it -- measured, not inferred:
replacing the committed hooks.json with `{}` leaves `tools/gates.sh` at exit 0 with all five
gates PASS, and the file's sha256 unchanged afterwards (the suite does not regenerate it; it
simply never looks).

So this reads the COMMITTED bytes via `git show`, not the working tree. A gate that reads the
working tree can be satisfied by a regeneration that never gets committed, and what the host
loads is what is committed.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from tests.plant_support import REPO

CLAUDE = "plugin/hooks/hooks.json"
CODEX = "plugin/hooks/hooks.codex.json"
SHIM = "dispatch.sh"


def committed(path: str) -> dict:
    shown = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=REPO,
                           capture_output=True, text=True, check=True)
    return json.loads(shown.stdout)


def host_shape_findings(body: dict) -> list[str]:
    """Everything about `body` that would stop the host loading it, as strings."""
    found: list[str] = []
    if not isinstance(body.get("hooks"), dict):
        found.append("hooks: expected record, received "
                     f"{type(body.get('hooks')).__name__}")
        return found  # nothing further is checkable
    events = body["hooks"]
    if not events:
        found.append("hooks: registers zero events -- a plugin that cannot deny")
    for name, rows in events.items():
        if not isinstance(rows, list) or not rows:
            found.append(f"{name}: expected a non-empty list of matcher entries")
            continue
        for row in rows:
            handlers = row.get("hooks") if isinstance(row, dict) else None
            if not isinstance(handlers, list) or not handlers:
                found.append(f"{name}: matcher entry carries no hooks list")
                continue
            for handler in handlers:
                command = handler.get("command", "")
                if not command.endswith(SHIM):
                    found.append(f"{name}: command does not point at the shim: {command!r}")
    for name in events:
        if name.startswith("_"):
            found.append(f"{name}: metadata key inside the event map")
    return found


# See `timeout_findings` for the condition this holds under and what happens when a handler
# exceeds it. Named rather than inlined so the number has one home and the reason sits beside it.
HOOK_TIMEOUT_CEILING_SECONDS = 60

def timeout_findings(body: dict) -> list[str]:
    """Every registered handler must bound its own hang.

    A command hook with no `timeout` defaults to 600 seconds, and a hook that reaches its timeout
    is canceled with its output discarded -- it renders NO decision. On a deny row that is an
    allow, reached after stalling the user for ten minutes: the fail direction inverted by a hang,
    which no per-row `open` flag can express because the row never got to speak.

    THE CEILING IS A POLICY, and it is written down here rather than left as a number in the
    comparison. A hook stalls the user for as long as it runs, so the bound is the longest an
    advisory gate may hold up a turn before the gate costs more than the deny is worth. Sixty
    seconds is a judgement, not a derivation -- there is no input that computes it -- and it is
    declared as one. What a hook may NOT do is exceed it silently: on a timeout above the ceiling
    this reports the handler by name and the tree is red until someone argues the new number.

    The lower bound is not a policy. A timeout of zero or less bounds nothing, and the handler it
    describes reaches its limit before it can render a decision, which is the fail-open above
    arriving instantly instead of after ten minutes.
    """
    found: list[str] = []
    hooks = body.get("hooks")
    if not isinstance(hooks, dict):
        return [f"hooks: expected record, received {type(hooks).__name__}"]
    if not hooks:
        return ["hooks: registers zero events -- timeout policy has no handlers to inspect"]
    for name, rows in hooks.items():
        if not isinstance(rows, list) or not rows:
            found.append(f"{name}: expected a non-empty list of matcher entries")
            continue
        for row in rows:
            for handler in (row.get("hooks") or []) if isinstance(row, dict) else []:
                seconds = handler.get("timeout")
                if not isinstance(seconds, int) or isinstance(seconds, bool):
                    found.append(f"{name}: no timeout -- defaults to 600s, a hang is an allow")
                elif not 0 < seconds <= HOOK_TIMEOUT_CEILING_SECONDS:
                    found.append(
                        f"{name}: timeout {seconds}s is outside 1..{HOOK_TIMEOUT_CEILING_SECONDS}, "
                        "the longest an advisory gate may stall a turn")
    return found


class CommittedHooksLoadOnTheHost(unittest.TestCase):
    def test_TEETH_claude_variant_has_the_shape_the_host_accepts(self) -> None:
        self.assertEqual([], host_shape_findings(committed(CLAUDE)))

    def test_TEETH_codex_variant_has_the_shape_the_host_accepts(self) -> None:
        self.assertEqual([], host_shape_findings(committed(CODEX)))

    def test_TEETH_both_variants_register_the_same_events(self) -> None:
        self.assertEqual(set(committed(CLAUDE)["hooks"]), set(committed(CODEX)["hooks"]),
                         "the two hosts must register the same event set")

    def test_TEETH_every_registered_hook_bounds_its_own_hang(self) -> None:
        for path in (CLAUDE, CODEX):
            with self.subTest(variant=path):
                self.assertEqual([], timeout_findings(committed(path)))

    def test_the_timeout_check_can_fail(self) -> None:
        """MAGNET: the check deliberately reads ``git show HEAD``, not the worktree.

        A smoke plant would have to create and then erase a commit while the suite is running.
        Rewriting the caller's branch is not a failure-safe mutation, so this remains explicit
        synthetic coverage rather than pretending a worktree edit reaches the detector.
        """
        missing = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": f"x/{SHIM}"}]}]}}
        self.assertTrue(timeout_findings(missing), "missed a handler with no timeout")
        absurd = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": f"x/{SHIM}",
                                                 "timeout": 600}]}]}}
        self.assertTrue(timeout_findings(absurd), "missed an unbounded timeout")
        # 600 is also the value a handler with NO timeout defaults to, so on its own it cannot
        # tell "the ceiling is enforced" from "that number is rejected for some other reason".
        # One second over the ceiling makes the ceiling itself the subject.
        over = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": f"x/{SHIM}",
                                               "timeout": HOOK_TIMEOUT_CEILING_SECONDS + 1}]}]}}
        self.assertTrue(timeout_findings(over),
                        f"a timeout one second over {HOOK_TIMEOUT_CEILING_SECONDS} was accepted")
        at = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": f"x/{SHIM}",
                                             "timeout": HOOK_TIMEOUT_CEILING_SECONDS}]}]}}
        self.assertEqual([], timeout_findings(at),
                         "a timeout AT the ceiling was refused, so the bound is off by one")
        self.assertTrue(timeout_findings({}), "missed the absence of a hooks record")
        self.assertTrue(timeout_findings({"hooks": "nope"}),
                        "malformed hooks must be a finding, not a detector crash")

    def test_the_check_can_fail(self) -> None:
        """MAGNET: the production check reads committed bytes via ``git show HEAD``.

        Mutating hooks.json in the worktree would not enter the detector's aperture; making a
        temporary commit would rewrite the user's branch and cannot be made safe on abrupt test
        termination. This therefore remains a documented magnet. Without it, `findings == []` is equally consistent with a correct file
        and a detector that matches nothing -- absence reading as green, which is the whole
        failure this file exists to refuse.

        The three shapes planted are the three that actually shipped or were measured: the
        pre-78ab4e0 flat map, an empty object (which passes gates.sh today), and a row whose
        command no longer reaches the shim.
        """
        flat = {"PreToolUse": [{"hooks": [{"type": "command", "command": f"x/{SHIM}"}]}],
                "_provenance": {"as_of": "sha256:0"}}
        self.assertTrue(host_shape_findings(flat), "missed the flat map that shipped")

        self.assertTrue(host_shape_findings({}), "missed the empty object gates.sh accepts")

        self.assertTrue(host_shape_findings({"hooks": {}}),
                        "missed a plugin registering zero events")

        wrong_shim = {"hooks": {"Stop": [{"hooks": [{"type": "command",
                                                     "command": "/usr/bin/true"}]}]}}
        self.assertTrue(host_shape_findings(wrong_shim), "missed a command that skips the shim")

        metadata_inside = {"hooks": {"_provenance": {}}}
        self.assertTrue(host_shape_findings(metadata_inside),
                        "missed a metadata key inside the event map")


class MatchersAreAuthoredPerHostDialect(unittest.TestCase):
    """The same tool set, written two ways, because the two hosts read the string differently.

    Claude Code: "Only letters, digits, `_`, `-`, spaces, `,`, and `|` are treated as exact
    string, or list of exact strings separated by `|` or `,`" -- so the bare alternation already
    matches whole tool names, and the reference calls that form preferred.

    Codex: matchers are regexes, tested for a match ANYWHERE in the value. A bare `Read|Task`
    would match any future tool merely containing those names -- over-firing, which costs a
    process per call and erodes the interruption budget the whole gate is priced against.

    "One generator, so inter-host drift is unrepresentable" is only true if the generator KNOWS
    they differ. A single shared string would have meant two different things.
    """

    def test_TEETH_claude_uses_the_exact_list_form(self) -> None:
        matcher = committed(CLAUDE)["hooks"]["PreToolUse"][0]["matcher"]
        self.assertRegex(matcher, r"^[A-Za-z0-9_\-, |]+$",
                         "any other character puts this on the unanchored regex path")

    def test_TEETH_codex_anchors_its_regex(self) -> None:
        matcher = committed(CODEX)["hooks"]["PreToolUse"][0]["matcher"]
        self.assertTrue(matcher.startswith("^(") and matcher.endswith(")$"),
                        f"an unanchored codex matcher over-fires: {matcher!r}")

    def test_TEETH_both_hosts_watch_the_same_tools(self) -> None:
        import re as _re
        claude = set(committed(CLAUDE)["hooks"]["PreToolUse"][0]["matcher"].split("|"))
        codex = set(_re.fullmatch(r"\^\((.*)\)\$",
                                  committed(CODEX)["hooks"]["PreToolUse"][0]["matcher"]
                                  ).group(1).split("|"))
        self.assertEqual(claude, codex, "the dialects differ; the tool set must not")


if __name__ == "__main__":
    unittest.main()
