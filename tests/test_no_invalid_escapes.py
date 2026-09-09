"""A string literal with an unknown escape is a DeprecationWarning today and a SyntaxError
on the Python that ships next. test_fence.py carried `\\S` inside a plain docstring, which
made the whole file uncollectable under `-W error` -- the suite could not run at all, and
nothing in the suite said why. So the tree is scanned for the class, not the instance.
"""

import pathlib
import warnings

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_no_invalid_escape_sequences() -> None:
    bad: list[str] = []
    for path in sorted(ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                compile(source, str(path), "exec")
            except SyntaxError as exc:
                bad.append(f"{path.relative_to(ROOT)}: {exc}")
                continue
            for entry in caught:
                if "invalid escape" in str(entry.message):
                    bad.append(f"{path.relative_to(ROOT)}:{entry.lineno}: {entry.message}")
    assert not bad, "use a raw string (r\"\"\"...\"\"\") or double the backslash:\n" + "\n".join(bad)
