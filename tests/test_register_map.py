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


def test_vendored_register_matches_its_source_when_the_source_is_reachable():
    """Two copies of one rule is entry F2, so the drift is checked, not trusted.

    When the source is not on this machine the test skips: a missing source is
    not evidence the copy is current, and saying otherwise is entry C2.
    """
    import hashlib

    source = ROOT.parent / "measure-zero-dev" / "REGISTER.md"
    if not source.exists():
        import pytest
        pytest.skip("register source not on this machine; drift NOT-EVALUABLE here")
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest(ROOT / "docs" / "REGISTER.md") == digest(source)
