"""The fence: the pages the plugin ships beside its clause table, joined to that table.

The dispatcher's own suite proves the deny half. What rots silently if nothing watches it is the
positive half shipped beside it -- the skill page and its supporting pages -- and the joins
between them and `keel/clauses.json`:

  (a) whether every clause's `construction` anchor resolves to a real heading in POINTS.md, and
      every POINTS.md entry belongs to a real clause -- no point silently dropped, none invented;
  (b) whether the seven acts in ACTS.md are still exactly the seven, and every point ACTS.md
      cites is a clause that exists;
  (c) whether every generated tabular view still matches the table it renders;
  (d) whether the vendored vocabulary still matches its pinned provenance, and the pages still
      speak it;
  (e) whether the pages have acquired the vocabulary of obligation -- the pages advise, only the
      hooks deny.

Standard library only, `unittest` discovery, like the rest of the suite.
"""
from pathlib import Path
import json
import re
import subprocess
import sys
import unittest


REPO = Path(__file__).resolve().parent.parent
PLUGIN = REPO / "plugin"
SKILL = PLUGIN / "SKILL.md"
POINTS_MD = PLUGIN / "POINTS.md"
ACTS_MD = PLUGIN / "ACTS.md"
VOCABULARY = PLUGIN / "vocabulary.json"
CLAUSES = PLUGIN / "keel" / "clauses.json"

PAGES = (SKILL, POINTS_MD, ACTS_MD)

SKILL_NAME = "keel"

# The seven acts. This literal is the fence's half of the single-home rule: ACTS.md's headings
# are the one place the list lives as content, and this pin is what makes losing or inventing
# one a red run instead of a quiet fork. The names originate in the development repository's
# register (Gyroscope-Dev, frozen); moving this set is a deliberate re-vendoring, so the pin
# moves by hand, like a sha.
SEVEN_ACTS = (
    "accept_report",
    "choose_spend",
    "delete",
    "dispatch_work",
    "finalize_plan",
    "push",
    "write_default_rule",
)

# RFC 2119 / RFC 8174: these ten words carry normative force, and ONLY in their all-capital
# forms. Lower-case "should" is ordinary English carrying none of BCP 14's defined force, which
# is what keeps this check from firing on prose. Sourced from
# https://www.rfc-editor.org/rfc/rfc2119.html (read 2026-08-20); RFC 8174 restricts the force to
# the capitalised spelling.
NORMATIVE = (
    "MUST NOT", "MUST", "REQUIRED", "SHALL NOT", "SHALL",
    "SHOULD NOT", "SHOULD", "RECOMMENDED", "MAY", "OPTIONAL",
)
NORMATIVE_RX = re.compile(r"\b(?:%s)\b" % "|".join(NORMATIVE))

CLAUSE_ID_RX = re.compile(r"`([A-Z]\d{2}(?:-[a-z-]+)?)`")


def _load(path: Path) -> str:
    """Read, and make an absent input LOUD rather than a skip.

    A fence whose subject has gone missing has not passed; it has stopped being a fence.
    Returning empty text or skipping here would turn deletion of any of these files into a green
    run, which is the one result this file exists to make impossible.
    """
    if not path.is_file():
        raise AssertionError(
            f"{path.relative_to(REPO)} is absent, so nothing was checked. An absent input is a "
            f"failure here, never a skip: without it this suite cannot tell a correct skill "
            f"from a deleted one."
        )
    return path.read_text(encoding="utf-8")


def _clause_rows() -> list:
    rows = json.loads(_load(CLAUSES))
    assert isinstance(rows, list) and rows, "clauses.json is not a non-empty list"
    return rows


class TheConstructionJoin(unittest.TestCase):
    """Every negative followed by its true positive, as a checked property of the tree.

    The loader already pins each row's anchor SHAPE to its id (see clauses._admit). This half
    resolves the anchors against the page they point into, in both directions: an anchor into a
    heading that is gone, an entry belonging to no clause, and a clause whose entry was silently
    dropped are all red here, not a thing a reader must catch.
    """

    def setUp(self) -> None:
        self.rows = _clause_rows()
        self.ids = [row["id"] for row in self.rows]
        self.points_md = _load(POINTS_MD)

    def test_the_table_still_holds_twenty_four_clauses(self) -> None:
        """Pinned literally: the prose says twenty-four across every page, so a coherently
        reduced or grown table must land here first and force the prose sweep, not pass
        quietly."""
        self.assertEqual(len(self.ids), 24, "the table moved; every spelled-out count moves with it")
        self.assertEqual(len(set(self.ids)), len(self.ids), "duplicate id in clauses.json")

    def test_no_entry_is_duplicated_or_empty(self) -> None:
        """What POINTS.md owes on its own, independent of which rows point at it.

        The clause-to-section map used to be asserted here as set equality AND again in
        `test_every_construction_anchor_resolves`. Two writers of one claim, and set equality is
        now the wrong claim besides: rows may share a section, so P02 has no heading of its own.
        The map lives entirely in the anchor test, in both directions. What is left here is what
        that test cannot see -- a heading that appears twice, and a heading over nothing.
        """
        headings = [h for h in re.findall(r"^## (\S+)$", self.points_md, re.MULTILINE)
                    if h != "Contents"]
        # A list, not a set: two entries under one id would survive set equality, and one entry
        # per heading is the claim being checked.
        self.assertEqual(len(headings), len(set(headings)), f"duplicate entry heading: {headings}")
        # A heading over an empty section resolves perfectly well while covering nothing, so the
        # anchor test would pass on it.
        for chunk in re.split(r"^## ", self.points_md, flags=re.MULTILINE)[1:]:
            name, _, body = chunk.partition("\n")
            if name.strip() != "Contents":
                self.assertTrue(
                    body.strip(), f"the {name.strip()} entry is an empty section under a heading"
                )

    def test_every_construction_anchor_resolves(self) -> None:
        """An anchor that does not resolve does not ship -- the product's own rule, applied to
        itself. The loader checks anchor SHAPE and nothing more; this owns the page, so it
        resolves every fragment against the actual headings and, in the other direction, refuses
        a section no row claims. Rows may share a section -- P01 and P02 are one plan point split
        by which ground a step is missing -- so this is a total map both ways, never a bijection.
        """
        headings = {h.lower() for h in re.findall(r"^## (\S+)$", self.points_md, re.MULTILINE)}
        headings.discard("contents")
        claimed = set()
        for row in self.rows:
            anchor = row.get("construction")
            self.assertTrue(anchor, f"{row['id']}: no construction anchor")
            self.assertNotIn("why_none", row,
                             f"{row['id']}: why_none is gone from the schema; this row kept one")
            page, _, fragment = anchor.partition("#")
            self.assertEqual(page, "POINTS.md", f"{row['id']}: anchor into the wrong page")
            self.assertIn(
                fragment, headings,
                f"{row['id']}: construction anchor #{fragment} resolves to no heading in "
                f"POINTS.md -- a pairing that does not resolve does not ship",
            )
            claimed.add(fragment)
        # The other direction. Without this, deleting a row silently orphans its section and the
        # page keeps prose nothing enforces -- the exact rot the generated-view comparison exists
        # to catch, one document over.
        self.assertEqual(
            headings - claimed, set(),
            f"POINTS.md sections no clause row anchors to: {sorted(headings - claimed)}",
        )

    def test_the_contents_table_reaches_every_entry(self) -> None:
        """POINTS.md is past 100 lines, so a partial read has to still show what is in it."""
        contents = re.search(r"^## Contents\n(.*?)^---$", self.points_md,
                             re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(contents, "POINTS.md has no Contents section")
        table_rows = [l for l in contents.group(1).splitlines() if l.startswith("|")]
        self.assertTrue(table_rows, "the Contents section carries no table rows at all")
        # Label and target separately, because they are no longer the same claim. Every clause
        # must be LISTED (its own id is the label a reader scans for), but a listed clause may
        # link to a section it shares -- P02 is listed under its own name and points at #p01.
        links = re.findall(r"\[([A-Za-z0-9-]+)\]\(#([a-z0-9-]+)\)", "\n".join(table_rows))
        # A label may be a clause's full id or its short form -- the table lists `C03` for
        # `C03-verify-what-returns` so the row fits. A short form counts only when it resolves
        # to exactly ONE shipped clause; an ambiguous one names nothing in particular.
        labelled = set()
        for label, _ in links:
            hits = [i for i in self.ids if i == label or i.startswith(f"{label}-")]
            self.assertEqual(len(hits), 1,
                             f"contents label {label!r} resolves to {sorted(hits)}, not one clause")
            labelled.add(hits[0])
        expected = set(self.ids)
        self.assertEqual(
            labelled, expected,
            f"the contents table and the entries disagree: "
            f"listed but absent {sorted(labelled - expected)}, "
            f"present but unlisted {sorted(expected - labelled)}",
        )
        # And every one of those links has to land somewhere. A row listing a clause and
        # pointing at nothing reads as coverage from the table of contents alone.
        headings = {h.lower() for h in re.findall(r"^## (\S+)$", self.points_md, re.MULTILINE)}
        for label, target in links:
            self.assertIn(target, headings,
                          f"contents row {label} links to #{target}, which is no heading")


class TheSevenActs(unittest.TestCase):
    """ACTS.md's headings are the single home of the act list, held to the pinned seven."""

    def setUp(self) -> None:
        self.acts = _load(ACTS_MD)

    def test_the_act_headings_are_exactly_the_seven(self) -> None:
        """Set equality both directions, so neither an invented act nor a dropped one passes.

        Every heading, not a word-shaped subset: a heading the pattern cannot see is a heading
        the equality never judges. And a list, not a set -- a duplicated section is two homes
        for one act, and sets erase exactly that.
        """
        indexed = re.findall(r"^## (.+)$", self.acts, re.MULTILINE)
        self.assertEqual(len(indexed), len(set(indexed)), f"duplicate act heading: {indexed}")
        self.assertEqual(
            set(indexed), set(SEVEN_ACTS),
            f"ACTS.md and the pinned act list disagree: "
            f"only in ACTS.md {sorted(set(indexed) - set(SEVEN_ACTS))}, "
            f"only in the pin {sorted(set(SEVEN_ACTS) - set(indexed))}",
        )

    def test_every_point_cited_anywhere_is_a_clause(self) -> None:
        """The pages speak about the points by id; an id a page invents, or one that outlived
        its clause, points a reader at a moment that does not exist. A short form (`C08`) is
        accepted exactly when it resolves to ONE shipped clause -- prose stays readable, and an
        ambiguous or orphaned citation is still red."""
        ids = {row["id"] for row in _clause_rows()}
        for page in PAGES:
            cited = set(CLAUSE_ID_RX.findall(_load(page)))
            self.assertTrue(cited,
                            f"{page.name} cites no point ids at all, so this join checks nothing")
            orphans = sorted(
                c for c in cited
                if len([i for i in ids if i == c or i.startswith(c + "-")]) != 1
            )
            self.assertEqual(
                orphans, [],
                f"{page.name} cites point ids that resolve to no single shipped clause",
            )


class GeneratedViewsMatch(unittest.TestCase):
    """Every tabular appearance of the clause facts is a rendering of clauses.json.

    One writer, byte-compared: the incident this exists for is a shipped generated page listing
    seven clauses that no longer existed and missing eight that did, silently, for weeks.
    """

    def test_the_committed_views_match_a_fresh_rendering(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(REPO / "tools" / "render_views.py"), "--check"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(
            completed.returncode, 0,
            f"generated views drifted from clauses.json:\n{completed.stdout}{completed.stderr}",
        )


class SharedVocabulary(unittest.TestCase):
    """The definition and the shapes are vendored from the development repository's register.

    That repository is a frozen archive -- the pins are stable by fiat -- but a pin still has to
    name a source, and the pages still have to speak the vendored words rather than a paraphrase
    of them: a paraphrase is how one taxonomy silently becomes two.
    """

    def setUp(self) -> None:
        self.vocabulary = json.loads(_load(VOCABULARY))
        self.skill = _load(SKILL)

    def test_every_vendored_list_has_exactly_one_supplying_source(self) -> None:
        vendored = {k for k in self.vocabulary if not k.startswith("_") and k != "provenance"}
        sources = self.vocabulary["provenance"]["sources"]
        self.assertTrue(sources, "provenance lists no sources, so coverage would hold vacuously")
        supplied = [s["supplies"] for s in sources]
        self.assertEqual(sorted(supplied), sorted(set(supplied)),
                         "two sources claim the same list")
        self.assertEqual(
            set(supplied), vendored,
            f"vendored lists and supplying sources disagree: "
            f"unsupplied {sorted(vendored - set(supplied))}, "
            f"supplying nothing vendored {sorted(set(supplied) - vendored)}",
        )
        provenance = self.vocabulary["provenance"]
        self.assertRegex(
            provenance.get("commit", ""), r"^[0-9a-f]{40}$",
            "provenance carries no full commit sha, so the snapshot has no identity",
        )
        for s in sources:
            self.assertRegex(
                s.get("blob", ""), r"^[0-9a-f]{40}$",
                f"source {s.get('path')!r} carries no full blob sha, so it cannot be re-resolved",
            )
            self.assertTrue(s.get("path"), "a source without a path cannot be re-resolved")
            self.assertIn(
                s["path"], provenance.get("refresh_with", ""),
                f"the refresh command no longer touches {s['path']!r}, so running it would "
                f"report a refresh that silently skipped this source",
            )

    def test_the_definition_is_quoted_verbatim(self) -> None:
        """Both halves rest on one sentence; a drift of a word makes two ideas that resemble
        each other, and nothing downstream would report it."""
        definition = self.vocabulary["definition"]
        self.assertTrue(definition,
                        "vocabulary.json carries an empty definition, which every page would 'quote'")
        self.assertIn(
            f"\n> {definition}\n", self.skill,
            f"SKILL.md does not carry the definition as its quoted line. A copy in passing "
            f"prose is not the displayed authority. Expected exactly:\n  > {definition}",
        )

    def test_every_shape_has_its_own_row_in_the_shapes_table(self) -> None:
        """Anchored to the table row, NOT to the word appearing somewhere in the document: a
        renamed row once passed green because the word survived in prose further down (the CI
        plant appends a distractor to keep that regression catchable)."""
        self.assertTrue(self.vocabulary["shapes"],
                        "vocabulary.json declares no shapes, so this loop would assert nothing")
        section = re.search(r"^## The four shapes\n(.*?)(?=^## |\Z)", self.skill,
                            re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(section, "SKILL.md has no shapes section")
        rows = re.findall(r"^\| \*\*(.+?)\*\* \|", section.group(1), re.MULTILINE)
        self.assertCountEqual(
            rows, self.vocabulary["shapes"],
            f"the shapes table and vocabulary.json disagree: table rows {rows}",
        )


class AdvisoryByConstruction(unittest.TestCase):
    """The pages advise; only the hooks deny.

    A deny is backed by the ledger; a page has no such machinery, so a mandate in its prose
    would be strength running ahead of the mechanism. That control is measured failing when it
    is procedural (advisory aviation circulars acquiring regulatory force; 96 of 151 strong
    clinical recommendations discordant with their evidence), so it is a test here, not a
    sentence promising restraint.
    """

    def test_no_page_carries_normative_force(self) -> None:
        """Refuse the ten RFC 2119 key words, across every shipped prose page. Only the
        all-capital spellings carry force, so ordinary prose is untouched and this cannot fire
        on a lookalike -- a check firing on innocent text is itself the unhealing failure: the
        noise does not heal, the check gets switched off, and the coverage dies silently."""
        offences = [
            (page.name, number, line.strip())
            for page in PAGES
            for number, line in enumerate(_load(page).splitlines(), start=1)
            if NORMATIVE_RX.search(line)
        ]
        self.assertEqual(
            offences, [],
            "a page uses the vocabulary of obligation. The pages advise and the hooks deny, so "
            "prose does not get to issue requirements: rewrite in lower case, as guidance.\n"
            + "\n".join(f"  {name} line {n}: {text}" for name, n, text in offences),
        )


class ConstructionCodeParses(unittest.TestCase):
    """U14's own guard, applied to the product's pages: run the block in parse-only mode.

    A construction whose example cannot parse is advice that fails the person who takes it, at
    the moment they take it -- and nothing else would report it, because prose is never
    executed. Only language-tagged fences are judged: the untagged before/after illustrations
    are annotated fragments, not programs, and pretending to parse them would be coverage
    theatre.
    """

    # Blocks sit indented inside list entries, so the fence markers carry leading space and the
    # code carries the list's indentation -- dedent before parsing, or an indented python block
    # is a SyntaxError about markdown, not about the example.
    FENCE_RX = re.compile(r"^[ \t]*```(\w+)\n(.*?)^[ \t]*```$", re.MULTILINE | re.DOTALL)

    def test_every_tagged_code_block_parses(self) -> None:
        import tempfile
        import textwrap
        found = 0
        for page in PAGES:
            for lang, code in self.FENCE_RX.findall(_load(page)):
                code = textwrap.dedent(code)
                found += 1
                if lang in ("sh", "bash"):
                    with tempfile.NamedTemporaryFile("w", suffix=".sh") as handle:
                        handle.write(code)
                        handle.flush()
                        done = subprocess.run(["bash", "-n", handle.name],
                                              capture_output=True, text=True, check=False)
                    self.assertEqual(
                        done.returncode, 0,
                        f"{page.name}: a {lang} construction block does not parse:\n"
                        f"{code}\n{done.stderr}",
                    )
                elif lang in ("python", "py"):
                    try:
                        compile(code, f"{page.name}:{lang}-block", "exec")
                    except SyntaxError as exc:
                        self.fail(f"{page.name}: a python construction block does not parse: "
                                  f"{exc}\n{code}")
                elif lang == "toml":
                    import tomllib
                    try:
                        tomllib.loads(code)
                    except tomllib.TOMLDecodeError as exc:
                        self.fail(f"{page.name}: a toml construction block does not parse: "
                                  f"{exc}\n{code}")
                else:
                    self.fail(f"{page.name}: tagged block language {lang!r} has no parser "
                              f"here; add one rather than shipping an unchecked example")
        self.assertGreater(found, 0, "no tagged construction blocks found, so nothing was checked")


class SkillIsLoadable(unittest.TestCase):
    """A skill that the host cannot parse never fires, and never says why."""

    def test_frontmatter_declares_a_name_and_a_trigger(self) -> None:
        text = _load(SKILL)
        match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        self.assertIsNotNone(match, "SKILL.md has no YAML frontmatter block")
        block = match.group(1)
        name = re.search(r"^name:\s*(.+?)\s*$", block, re.MULTILINE)
        self.assertIsNotNone(name, "frontmatter declares no name")
        self.assertEqual(name.group(1), SKILL_NAME, "the whole value, not its first token")
        description = re.search(r"^description:\s*>-\n((?:\s+\S.*(?:\n|$))+)", block, re.MULTILINE)
        self.assertIsNotNone(description, "frontmatter declares no description block")
        # Length is judged on the folded value the host parses, not the indented block source.
        folded = " ".join(line.strip() for line in description.group(1).splitlines())
        # The description is the trigger: it decides when the skill fires. The floor is this
        # repository's own bar for a discriminating trigger, not a host rule.
        self.assertGreater(
            len(folded.split()), 40,
            "the description is what decides when this skill fires; this repository holds it "
            "above 40 words so the trigger names its moments instead of gesturing at them",
        )
        # The host rejects a description longer than 1024 characters; 1024 itself loads.
        self.assertLessEqual(len(folded), 1024, "description exceeds the 1024-char limit")

    def test_the_body_stays_inside_the_progressive_disclosure_budget(self) -> None:
        """Past ~500 lines the body stops being an index and starts being the thing it points
        at."""
        self.assertLess(
            len(_load(SKILL).splitlines()), 500,
            "SKILL.md is past 500 lines; move detail one hop down rather than growing the index",
        )

    def test_every_page_the_skill_points_at_actually_exists(self) -> None:
        """Progressive disclosure is only as good as its links: a broken reference does not
        announce itself -- the skill still loads, still reads as complete, and silently degrades
        to whatever the index alone says."""
        targets = re.findall(r"\]\((?!https?:)([^)#]+)(?:#[^)]*)?\)", _load(SKILL))
        self.assertTrue(targets, "SKILL.md references no detail pages at all")
        missing = [t for t in targets if not (PLUGIN / t).is_file()]
        self.assertEqual(missing, [], f"SKILL.md points at files that do not exist: {missing}")


if __name__ == "__main__":
    unittest.main()
