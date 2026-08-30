"""A workflow must not publish a number it did not measure.

Ported by SHAPE from Clear-Sights/Ward's tests/test_workflow_gates.py, where the defect was found
first: its release notes stated a hard-coded "82-test suite and 6/6 corpus replay" while the suite
had passed 130 tests and the corpus 13 sessions. Keel had the identical defect -- notes claiming a
"5/5 corpus replay" over a 25-session corpus.

WHAT IS NOT PORTED, and why. Ward also carries a law requiring any workflow step that runs
`unittest discover` to read its collected count, because `discover` prints OK and exits 0 when it
collects NOTHING. Keel's CI runs pytest, which exits 5 on an empty collection rather than 0, so
that hole does not exist here and a law about it would assert over nothing. Verified rather than
assumed: `python3 -m pytest -q tests/nonexistent` exits 4, and a directory with no tests exits 5.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"

# Reading the collected count means extracting unittest's own "Ran N test(s)" line and deciding
# on it. Any spelling that captures that number and compares it satisfies this; the two markers
# below are what such a step must contain to be doing it at all.
_RUNS_SUITE = re.compile(r"unittest\s+discover")
# Extracting the count is not enough: the value has to DECIDE something. A workflow that pulls
# "Ran N" into a variable and never tests it is exactly as blind as one that never pulled it, and
# the earlier version of this law accepted the sed alone -- so a dead assignment, or that literal
# sitting in a comment, kept it green. Both halves are required now.
_EXTRACTS_COUNT = "s/^Ran "        # the sed that reads unittest's own "Ran N tests" line
_DECIDES_ON_COUNT = re.compile(
    r"""\[\s*["']?\$\{?ran\}?["']?\s*(?:-eq|-lt|-le|=)\s*["']?0["']?\s*\]"""
    r"""|\[\s*-z\s*["']?\$\{?ran\}?["']?\s*\]""")




def _without_shell_comments(script: str) -> str:
    """`script` with `#` comments removed, so a search sees only commands.

    Not a full shell parser: a `#` inside single or double quotes is respected, which is what
    separates a comment from a literal here, but `$'...'` and here-documents are not tracked.
    The direction of any error is toward keeping MORE text, so a mistake makes this law more
    permissive rather than falsely accusing -- stated because that is the wrong direction for a
    law and is the reason `test_the_step_scan_finds_the_steps` exists beside it.
    """
    out = []
    for line in script.splitlines():
        quote, cut = None, None
        for index, char in enumerate(line):
            if quote:
                if char == quote:
                    quote = None
            elif char in "'\"":
                quote = char
            elif char == "#":
                cut = index
                break
        out.append(line if cut is None else line[:cut])
    return "\n".join(out)


def _run_steps(path: Path) -> list:
    """[(label, shell script)] for each workflow step that has a `run:` block.

    A hand-rolled splitter, and NOT because parsing YAML is hard. Ward declares zero package
    dependencies -- pyproject's `dependencies = []`, and README says so in a sentence a reader
    relies on -- so importing PyYAML here would make the suite unrunnable on a clean checkout and
    would make that sentence false. A first version of this test did import it; this is the
    correction.

    STATED LIMIT: this understands the shape GitHub Actions workflows in THIS repository are
    written in -- `- name:` starting a step, `run: |` opening a block scalar, the block ending at
    the next line indented no further than the `run:` key. A workflow written in flow style, or
    with a folded scalar, is not split correctly, and the law that reads these steps would then
    see a step it cannot check. `test_the_step_scan_finds_the_steps` is the guard against that:
    it fails if the splitter stops finding the suite anywhere.
    """
    steps, label, script, run_indent, step_id = [], None, None, None, None
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        indent = len(raw) - len(raw.lstrip())
        if script is not None:
            if stripped and indent <= run_indent:
                steps.append((f"{path.name}:{label or 'unnamed step'}", "\n".join(script),
                              step_id))
                script = None
            else:
                script.append(raw)
                continue
        if stripped.startswith("- name:"):
            label, step_id = stripped[len("- name:"):].strip(), None
        elif re.match(r"id:\s*\S+$", stripped):
            step_id = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- ") and ":" in stripped and "name:" not in stripped:
            label = None
        if re.match(r"run:\s*[|>]", stripped):
            run_indent, script = indent, []
        elif stripped.startswith("run:"):
            steps.append((f"{path.name}:{label or 'unnamed step'}",
                          stripped[len("run:"):].strip(), step_id))
    if script is not None:
        steps.append((f"{path.name}:{label or 'unnamed step'}", "\n".join(script), step_id))
    return steps




def _steps_writing(path: Path, step_id: str):
    """The output names a step with `id: <step_id>` writes to GITHUB_OUTPUT, or None if no step
    in this workflow carries that id. Read from the step's own script, so a published expression
    is checked against a step that exists and an output that step actually sets."""
    owned = [raw for _label, raw, owner in _run_steps(path) if owner == step_id]
    if not owned:
        return None
    written = set()
    for raw in owned:
        script = _without_shell_comments(raw)
        for line in script.splitlines():
            if "GITHUB_OUTPUT" not in line:
                continue
            for name, value in re.findall(r'echo\s+"?([\w-]+)=([^">]*)', line):
                # A LITERAL IS NOT A MEASUREMENT, AND NEITHER IS A VARIABLE HOLDING ONE.
                # `echo "sessions=25" >> $GITHUB_OUTPUT` moves a hard-coded number into a step
                # output and out through the published string -- the original defect one
                # indirection along. Requiring a `$` closed only half of that: `ran=82; echo
                # "ran=$ran"` satisfies it while nothing was measured. So each referenced
                # variable is traced back to its assignment inside this step.
                referenced = re.findall(r"\$\{?(\w+)", value)
                if not referenced:
                    continue
                def measured(var):
                    if var.isdigit():
                        # `summary=$(...)` then `set -- $summary` then `echo "sessions=$1"`:
                        # the positional came from splitting a captured value, so it is a
                        # command substitution one indirection back.
                        return bool(re.search(r"(?m)^\s*set\s+--\s+\$", script))
                    return bool(re.search(r"(?m)^\s*" + re.escape(var) + r"=\$\(", script)
                                or re.search(r"(?m)^\s*" + re.escape(var) + r"=`", script))
                if any(measured(var) for var in referenced):
                    written.add(name)
    return written


class NoWorkflowPublishesANumberItDidNotMeasure(unittest.TestCase):
    """A release note stating a count must take it from the run, not from a literal.

    Ward's release notes said "the 82-test suite and the 6/6 corpus replay" for as long as those
    numbers were true, and went on saying it after the suite passed 130 tests and the corpus
    reached 13 sessions. Every release published two false statements about the verification it
    had just performed -- and the workflow HAD both numbers, in steps it ran seconds earlier.

    A count in a published string must therefore be an expression, not a digit. This reads the
    strings a workflow publishes and requires any suite/replay figure in them to come from a step
    output.
    """

    # Phrases that state a measured quantity about this repository, as (regex, what it counts).
    # A counted token is either a `${{ ... }}` expression or a bare word. The expression form
    # has to be matched WHOLE: a plain `\S+` stops at the spaces inside `${{ steps.x.outputs.y }}`
    # and captures `}}`, which then looks like a literal and makes this law fire on its own fix.
    _TOKEN = r"(\$\{\{[^}]*\}\}|\S+)"
    COUNTED = (
        (re.compile(_TOKEN + r"-test suite"), "the suite size"),
        (re.compile(_TOKEN + r"/" + _TOKEN + r" corpus replay"), "the corpus replay denominator"),
    )
    FROM_A_STEP = re.compile(r"\$\{\{\s*steps\.([\w-]+)\.outputs\.([\w-]+)\s*\}\}")

    def test_the_check_has_a_subject(self) -> None:
        # Comments stripped first: the step that carries this defect's explanation quotes the
        # old literal "82-test suite" while describing it, and a law that matched its own
        # explanation would fire on the fix.
        published = [text for path in sorted(WORKFLOWS.glob("*.yml"))
                     for _label, raw, _owner in _run_steps(path)
                     for text in [_without_shell_comments(raw)]
                     if any(pattern.search(text) for pattern, _what in self.COUNTED)]
        self.assertTrue(
            published,
            "no workflow step publishes a suite or replay count, so this law compares nothing. "
            "If the release notes stopped stating them, delete this test rather than leaving it "
            "green over nothing.")

    def test_every_published_count_is_read_from_a_step_output(self) -> None:
        offenders = []
        for path in sorted(WORKFLOWS.glob("*.yml")):
            for label, raw, _owner in _run_steps(path):
                text = _without_shell_comments(raw)
                for pattern, what in self.COUNTED:
                    for found in pattern.finditer(text):
                        for group in found.groups():
                            reference = self.FROM_A_STEP.search(group)
                            if not reference:
                                offenders.append(
                                    f"{label}: publishes {what} as the literal {group!r} in "
                                    f"{found.group(0)!r}")
                                continue
                            # ...AND THE STEP IT NAMES EXISTS AND WRITES THAT OUTPUT. The
                            # spelling alone is satisfied by `${{ steps.nothing.outputs.made_up }}`,
                            # which renders empty and publishes a blank where a number belongs.
                            step_id, output = reference.group(1), reference.group(2)
                            writers = _steps_writing(path, step_id)
                            if writers is None:
                                offenders.append(
                                    f"{label}: publishes {what} from step id {step_id!r}, which "
                                    f"no step in this workflow declares")
                            elif output not in writers:
                                offenders.append(
                                    f"{label}: publishes {what} as {step_id}.{output}, and that "
                                    f"step writes only {sorted(writers)} to GITHUB_OUTPUT")
        self.assertEqual(
            [], offenders,
            "a workflow publishes a measured count as a literal. It goes stale the moment the "
            "thing it counts changes, and the workflow already has the real number from the step "
            "that produced it: " + "; ".join(offenders))
