"""The timing bounds in the code, joined to the hook timeouts they are bounds against.

WHY THIS EXISTS. Two constants in this plugin are only correct because of a number declared
somewhere else, and nothing carried the relation:

  `clauses.PROBE_TIMEOUT_CEILING_MS`  a probe runs inside the hook. A hook that reaches its own
                                      timeout is canceled with its output discarded, so it renders
                                      no decision and a deny row becomes an allow. A probe allowed
                                      to outlive its hook is a guaranteed fail-open.
  `journal._STALE_CLAIM_SECONDS`      a claim marker younger than the longest a hook may run can
                                      still belong to a live writer. Taking it over loses the
                                      liveness row the journal exists to guarantee.

Both relations were true when written. Neither was checked. `tests/test_probe_cache.py` even spells
the first one out in prose -- "at the 5000 ms per-probe cap that is 80 seconds against a 20 second
hook timeout" -- in a different file from either number, which is how a relation survives as a
sentence and dies as a property. Lowering the hook timeout would have left both constants stale and
every test green.

WHAT IS READ. The WORKTREE `hooks.json`, not `git show HEAD:` -- `tests/test_host_shape.py` reads
the committed copy on purpose, because its subject is what was committed. The subject here is the
tree under test, and a bound that cannot see an uncommitted edit cannot be planted against either.

Standard library only, `unittest` discovery, like the rest of the suite.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests.plant_support import PLUGIN, smoke_replace
from keel.clauses import PROBE_TIMEOUT_CEILING_MS
from keel.journal import _STALE_CLAIM_SECONDS

HOOK_FILES = ("hooks/hooks.json", "hooks/hooks.codex.json")


def hook_timeouts() -> list[int]:
    """Every handler timeout declared by every shipped hook file, in seconds.

    Swept from the files rather than listed here: a list would be a second writer for a number
    these files already state, and it would go stale the first time an event is added.
    """
    seconds: list[int] = []
    for name in HOOK_FILES:
        body = json.loads((PLUGIN / name).read_text(encoding="utf-8"))
        for rows in (body.get("hooks") or {}).values():
            for row in rows if isinstance(rows, list) else []:
                for handler in (row.get("hooks") or []) if isinstance(row, dict) else []:
                    value = handler.get("timeout")
                    if isinstance(value, int) and not isinstance(value, bool):
                        seconds.append(value)
    return seconds


class TimingBoundsAreJoinedToTheHookTimeout(unittest.TestCase):
    def setUp(self) -> None:
        self.seconds = hook_timeouts()

    def test_the_check_has_a_subject(self) -> None:
        """No declared timeout means nothing to join, and that is reported, not passed.

        Both assertions below are vacuously true over an empty sweep -- `max` and `min` are never
        reached -- so without this method a hooks file that stopped declaring timeouts would turn
        this whole class green at the moment it became most wrong.
        """
        self.assertGreaterEqual(
            len(self.seconds), len(HOOK_FILES),
            f"only {len(self.seconds)} hook timeouts found across {HOOK_FILES}; the sweep has "
            "stopped seeing the declarations it is supposed to be joining against")

    def test_a_probe_cannot_be_allowed_to_outlive_its_hook(self) -> None:
        shortest = min(self.seconds)
        self.assertLessEqual(
            PROBE_TIMEOUT_CEILING_MS, shortest * 1000,
            f"a clause may declare a probe of up to {PROBE_TIMEOUT_CEILING_MS} ms inside a hook "
            f"bounded at {shortest} s, so the hook is canceled, renders no decision, and the deny "
            "row fails OPEN through the hang")

    def test_a_claim_younger_than_a_live_hook_is_never_stolen(self) -> None:
        longest = max(self.seconds)
        self.assertGreater(
            _STALE_CLAIM_SECONDS, longest,
            f"a claim is treated as abandoned after {_STALE_CLAIM_SECONDS} s while a hook may "
            f"still be running at {longest} s, so a marker belonging to a live writer is taken "
            "over and the liveness row this journal guarantees is lost")


class TheseBoundsCanFail(unittest.TestCase):
    """Each join seen red on a planted fault, because a bound that has only ever held is a claim."""

    def test_the_probe_ceiling_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red
        """Shorten the hook, and the ceiling that was fine must stop being fine."""
        smoke_replace(
            self, PLUGIN / "hooks" / "hooks.json", b'"timeout": 20', b'"timeout": 3',
            "tests.test_bounds.TimingBoundsAreJoinedToTheHookTimeout."
            "test_a_probe_cannot_be_allowed_to_outlive_its_hook",
            "fails OPEN through the hang",
        )

    def test_the_stale_claim_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red
        """Drop the window under the hook bound, and live claims become stealable."""
        smoke_replace(
            self, PLUGIN / "keel" / "journal.py",
            b"_STALE_CLAIM_SECONDS = 60", b"_STALE_CLAIM_SECONDS = 10",
            "tests.test_bounds.TimingBoundsAreJoinedToTheHookTimeout."
            "test_a_claim_younger_than_a_live_hook_is_never_stolen",
            "the liveness row this journal guarantees is lost",
        )

    def test_the_subject_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red
        """Blind the sweep, and the empty subject must be reported rather than pass."""
        smoke_replace(
            self, Path(__file__), b'value = handler.get("timeout")',
            b'value = handler.get("timeout-that-is-not-declared")',
            "tests.test_bounds.TimingBoundsAreJoinedToTheHookTimeout.test_the_check_has_a_subject",
            "stopped seeing the declarations",
        )


if __name__ == "__main__":
    unittest.main()
