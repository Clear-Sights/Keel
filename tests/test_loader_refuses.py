"""Every refusal code the loader can raise, driven through the loader as a plant.

Each code is named by a `raise ClauseError("CLAUSE-...", ...)` somewhere in `keel/clauses.py`.
Nothing enforces that a code stays exercised: a check can be neutered (a mutation deletes the
`raise`, or the branch above it goes unreachable) and a suite that never plants that exact row
shape does not notice -- the table still loads, every other test stays green, and the
admissibility rule is gone in fact while its comment still reads as if it holds. The eleven
codes named in no test file before this one (found with
`grep -o 'CLAUSE-[A-Z-]*' plugin/keel/clauses.py | sort -u` against
`grep -rl <code> tests`) are the ones this suite adds a red run for; the rest already have a
plant elsewhere and are repeated here anyway so this file is a complete, self-checking census
rather than a partial one that silently trusts other files to cover the remainder.

`test_the_census_is_complete` is what keeps that true: it re-derives the code list from the
source with the same regex, and requires it to equal exactly the codes this file plants. A new
`CLAUSE-*` raised anywhere in `clauses.py` without an entry here fails that test, not by
omission -- by name.
"""
from __future__ import annotations

import json
import re
import tempfile
import unittest

from tests.plant_support import PLUGIN
from keel import clauses as C

CLAUSES_SRC = (PLUGIN / "keel" / "clauses.py").read_text(encoding="utf-8")


def base(clause_id: str, **overrides) -> dict:
    """The smallest row that loads clean. Every plant below is this, minus one thing."""
    row = dict(
        id=clause_id, event="PreToolUse", tools=["Bash"],
        occasion="x", costly="x", guard="x", subject="session_id",
        fingerprint={"kind": "tool", "on": "tool_name", "equals": "Bash"},
        window="session", deny_reason="x",
        fixtures_pos=["Bash"], fixtures_neg=["Read"],
        construction="POINTS.md#a01",
    )
    row.update(overrides)
    return row


# code -> a row (or a callable building a load call) that must be refused with exactly that code.
PLANTS: dict[str, dict] = {
    "CLAUSE-TEXT-COVERING": base(
        "Z-TEXT", fingerprint={"kind": "regex", "on": "tool_input.command", "pattern": "x"}),
    "CLAUSE-OCCASION-NOMINAL": base(
        "Z-OCC-NOM", fingerprint={"kind": "program", "on": "tool_input.command", "equals": "npm"}),
    "CLAUSE-GUARD-NOMINAL": base(
        "Z-GUARD-NOM",
        discharged_by={"kind": "program", "on": "tool_input.command", "equals": "npm"},
        fixtures_discharge=["x"], fixtures_no_discharge=["y"]),
    "CLAUSE-SIDE-UNCLASSIFIED": base("Z-UNCLASS", fingerprint={"kind": "bogus"}),
    "CLAUSE-GUARD-ALWAYS": base("Z-GUARD-ALWAYS", discharged_by={"kind": "always"}),
    "CLAUSE-NONZERO-NOT-RESPONSE": base(
        "Z-NONZERO", fingerprint={"kind": "nonzero", "on": "tool_input.command"},
        fixtures_pos=["1"], fixtures_neg=["0"]),
    "CLAUSE-NO-ACTIVATION-FIXTURES": base(
        "Z-NO-ACT-FIX", activated_by={"kind": "tool", "on": "tool_name", "equals": "Bash"}),
    "CLAUSE-ACTIVATION-FIXTURE-MISS": base(
        "Z-ACT-MISS", activated_by={"kind": "tool", "on": "tool_name", "equals": "Bash"},
        fixtures_activate=["Read"]),
    "CLAUSE-EVENT-UNKNOWN": base("Z-EVENT", event="BogusEvent"),
    "CLAUSE-NO-FIXTURES": base("Z-NO-FIX", fixtures_pos=[]),
    "CLAUSE-KEY-FROM-INVALID": base(
        "Z-KEY-FROM",
        fingerprint={"kind": "tool", "on": "tool_name", "equals": "Bash", "key_from": {}}),
    "CLAUSE-REGEX-INVALID": base(
        "Z-REGEX", fingerprint={"kind": "regex", "on": "tool_name", "pattern": "("}),
    "CLAUSE-PROBE-INVALID": base(
        "Z-PROBE-INVALID",
        fingerprint={"kind": "tool", "on": "tool_name", "equals": "Bash",
                     "probe": {"cmd": ["git", "status", "--porcelain"],
                               "timeout_ms": 99999, "expect": "empty"}}),
    "CLAUSE-PROBE-MUTATING": base(
        "Z-PROBE-MUT",
        fingerprint={"kind": "tool", "on": "tool_name", "equals": "Bash",
                     "probe": {"cmd": ["rm", "-rf", "/"], "timeout_ms": 1000, "expect": "empty"}}),
    "CLAUSE-EFFECT-UNKNOWN": base(
        "Z-EFFECT-UNK", fingerprint={"kind": "effect", "effect": "nonexistent_effect"}),
    "CLAUSE-EFFECT-EVENT": base(
        "Z-EFFECT-EVENT", event="PreToolUse",
        fingerprint={"kind": "effect", "effect": "files_changed"}),
    "CLAUSE-SUBJECT-UNKEYABLE-EFFECT": base("Z-SUBJ-UNKEY", subject={"effect": "bogus_effect"}),
    "CLAUSE-FIXTURE-POS-MISS": base("Z-POS-MISS", fixtures_pos=["Read"]),
    "CLAUSE-FIXTURE-POS-UNKEYABLE": base(
        "Z-POS-UNKEY",
        subject={"on": "tool_input.command", "pattern": "(--force)", "group": 1}),
    "CLAUSE-FIXTURE-NEG-HIT": base("Z-NEG-HIT", fixtures_neg=["Bash"]),
    "CLAUSE-NO-GUARD-FIXTURES": base(
        "Z-NO-GUARD-FIX", discharged_by={"kind": "tool", "on": "tool_name", "equals": "Read"}),
    "CLAUSE-GUARD-FIXTURE-MISS": base(
        "Z-GUARD-MISS", discharged_by={"kind": "tool", "on": "tool_name", "equals": "Read"},
        fixtures_discharge=["Bash"], fixtures_no_discharge=["Bash"]),
    "CLAUSE-GUARD-FIXTURE-HIT": base(
        "Z-GUARD-HIT", discharged_by={"kind": "tool", "on": "tool_name", "equals": "Read"},
        fixtures_discharge=["Read"], fixtures_no_discharge=["Read"]),
    "CLAUSE-CARRIES-AN-EXCUSE": {**base("Z-EXCUSE"), "waiver": "nope"},
}

# Codes raised by `load_bundle`/`_unique_sorted` rather than `_load_object`, so they need a
# temp file and a different call shape -- kept out of PLANTS (a single dict of rows) but still
# counted by the census below.
BUNDLE_CODES = {"CLAUSE-BUNDLE-INVALID", "CLAUSE-ID-DUPLICATE"}


class LoaderRefusesEveryCode(unittest.TestCase):
    def test_TEETH_each_plant_is_refused_with_exactly_its_code(self) -> None:
        for code, row in PLANTS.items():
            with self.subTest(code=code):
                with self.assertRaises(C.ClauseError) as ctx:
                    C._load_object(row)
                self.assertEqual(code, ctx.exception.code)

    def test_TEETH_a_non_list_bundle_is_refused(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fh:
            json.dump({"not": "a list"}, fh)
            path = fh.name
        with self.assertRaises(C.ClauseError) as ctx:
            C.load_bundle(path)
        self.assertEqual("CLAUSE-BUNDLE-INVALID", ctx.exception.code)

    def test_TEETH_a_duplicate_id_is_refused(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fh:
            json.dump([base("Z-DUP"), base("Z-DUP")], fh)
            path = fh.name
        with self.assertRaises(C.ClauseError) as ctx:
            C.load_bundle(path)
        self.assertEqual("CLAUSE-ID-DUPLICATE", ctx.exception.code)

    def test_the_census_is_complete(self) -> None:
        """Every code the source can raise has a plant above -- a new one is caught by name."""
        codes_in_source = set(re.findall(r"CLAUSE-[A-Z-]+", CLAUSES_SRC))
        codes_planted = set(PLANTS) | BUNDLE_CODES
        self.assertEqual(codes_in_source, codes_planted,
                          "a CLAUSE-* code was added to or removed from clauses.py without "
                          "updating the plant table in this file")


if __name__ == "__main__":
    unittest.main()
