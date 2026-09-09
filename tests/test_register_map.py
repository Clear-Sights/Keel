"""The register map is bound to the suite.

A rule written and left to be run by hand is register entry B7, so this test is
the binding. It asserts both directions -- green on the tree as it stands, red
on a planted gap -- because a runner that has stopped deciding anything looks
exactly like a runner that agrees.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))


def test_register_map_is_green_and_every_clause_is_cited():
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "register_map.py")],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "every entry carried" in r.stdout
    assert "clauses cited   24 of 24" in r.stdout


def test_register_map_reddens_on_an_entry_with_no_row(tmp_path, monkeypatch):
    import register_map

    lines = register_map.MAP.read_text(encoding="utf-8").splitlines()
    planted = tmp_path / "REGISTER-MAP.tsv"
    planted.write_text("\n".join(ln for ln in lines if not ln.startswith("G1\t")) + "\n",
                       encoding="utf-8")
    monkeypatch.setattr(register_map, "MAP", planted)

    assert register_map.main() == 2


def test_register_map_reddens_on_a_clause_that_is_not_admitted(tmp_path, monkeypatch):
    import register_map

    lines = register_map.MAP.read_text(encoding="utf-8").splitlines()
    planted = tmp_path / "REGISTER-MAP.tsv"
    planted.write_text("\n".join(ln.replace("\tP02\t", "\tZ99\t") for ln in lines) + "\n",
                       encoding="utf-8")
    monkeypatch.setattr(register_map, "MAP", planted)

    assert register_map.main() == 2


# Digest of docs/REGISTER.md as vendored from measure-zero-dev. Re-pin deliberately
# when the register is re-vendored; that edit is the record that a copy moved.
REGISTER_DIGEST = "f262b53bcb839927ec045402522cff1ba64b6e9665cadf0d4734c858fd71ee69"


def test_vendored_register_matches_its_pinned_digest():
    """docs/REGISTER.md is a copy, and this fence pins it.

    Two copies of one rule is register entry F2. The fence compares the copy
    against its own pinned digest, never against the owner's live tree: a check
    that reads another repository only evaluates where that repository happens
    to sit, which is entry E7. This one evaluates everywhere.
    """
    import hashlib

    actual = hashlib.sha256((ROOT / "docs" / "REGISTER.md").read_bytes()).hexdigest()
    assert actual == REGISTER_DIGEST, (
        "docs/REGISTER.md moved without its pin being updated; re-vendor and re-pin"
    )
