"""The fence: the pages the plugin ships beside its clause table, joined to that table.

The dispatcher's own suite proves the deny half. What rots silently if nothing watches it is the
positive half shipped beside it -- the skill page and its supporting pages -- and the joins
between them and `keel/clauses.json`:

  (a) whether every clause's `construction` anchor resolves to a real heading in POINTS.md, and
      every POINTS.md entry belongs to a real clause -- no point silently dropped, none invented;
  (b) whether the ten acts in ACTS.md are still exactly the ten, and every point ACTS.md
      cites is a clause that exists;
  (c) whether every generated tabular view still matches the table it renders;
  (d) whether the vendored vocabulary still matches its pinned provenance, and the pages still
      speak it;
  (e) whether the pages have acquired the vocabulary of obligation -- the pages advise, only the
      hooks deny;
  (f) whether the rendered images still match the size of the SVGs they are rendered from.

Standard library only, `unittest` discovery, like the rest of the suite.
"""
from pathlib import Path
import json
import re
import struct
import subprocess
import sys
import unittest


# The roots are IMPORTED, not re-derived. This module used to open with
# `REPO = Path(__file__).resolve().parent.parent`, which is precisely the line `plant_support`
# exists to have deleted: it names a DIFFERENT directory in each of the two layouts these bytes
# run from, so the copy that was supposed to be portable was the one file pinning itself to one
# layout. One derivation, one home, and its docstring is where the reasoning lives.
from tests.plant_support import PLUGIN, REPO, smoke_replace
from keel import clauses as C_MOD

SKILL = PLUGIN / "SKILL.md"
POINTS_MD = PLUGIN / "POINTS.md"
ACTS_MD = PLUGIN / "ACTS.md"
VOCABULARY = PLUGIN / "vocabulary.json"
CLAUSES = PLUGIN / "keel" / "clauses.json"

PAGES = (SKILL, POINTS_MD, ACTS_MD)


def _headings(text: str) -> list[str]:
    """Every `## ` heading in a page, in order.

    `(.+)`, never `(\S+)`, and the difference is not cosmetic. Three scanners in this module
    matched word-shaped headings only, so a heading with a space in it was INVISIBLE to them: it
    could be duplicated, it could sit over an empty section, a contents row could link to it, and
    every one of those checks passed by never seeing it. A heading the pattern cannot see is a
    heading the assertion never judges. `TheActList` already knew this and wrote it down -- it
    was the one of the four copies that got it right, which is what four copies of one job
    produce. There is one copy now, and it is the right one.
    """
    return [h.strip() for h in re.findall(r"^## (.+)$", text, re.MULTILINE)]

SKILL_NAME = "keel"

# The ten acts. This literal is the fence's half of the single-home rule: ACTS.md's headings
# are the one place the list lives as content, and this pin is what makes losing or inventing
# one a red run instead of a quiet fork. Seven of the names originate in the development
# repository's register (Gyroscope-Dev, frozen); moving this set is a deliberate re-vendoring, so
# the pin moves by hand, like a sha.
#
# `compact`, `probe` and `research` were added by hand and do NOT come from that register. They
# come from the directive set it feeds, where each cleared the recurrence cut over independent
# sources and no act here carried them. The register was deliberately left alone: its act list is
# a MEASURED structure -- every act in it resolves to clauses that route to it -- and adding three
# names with no clauses would have made it assert a routing nobody measured.
TEN_ACTS = (
    "accept_report",
    "choose_spend",
    "compact",
    "delete",
    "dispatch_work",
    "finalize_plan",
    "probe",
    "push",
    "research",
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

    The loader checks each row's anchor SHAPE and stops there (see clauses._admit), because rows
    may legitimately share a point. This half owns the page and resolves the anchors against it in
    both directions: an anchor into a heading that is gone, a heading no row claims, and a clause
    whose entry was silently dropped are all red here, not a thing a reader must catch.
    """

    def setUp(self) -> None:
        self.rows = _clause_rows()
        self.ids = [row["id"] for row in self.rows]
        self.points_md = _load(POINTS_MD)

    def test_no_clause_id_is_duplicated(self) -> None:
        """Two rows under one id is one row the other checks never judge.

        This method used to open by pinning the table to a literal 24, and said why in its own
        words: the prose spells twenty-four, so a changed table "must land here first and force
        the prose sweep". The sweep was a person. `SpelledCountsMatchWhatTheyCount` now joins
        every spelled total to its source, so the pages themselves are the acknowledgement and a
        third copy of the number here would be one more writer to keep in step. What is left is
        the part no join can see: the table disagreeing with itself.
        """
        self.assertEqual(len(set(self.ids)), len(self.ids), "duplicate id in clauses.json")

    def test_no_entry_is_duplicated_or_empty(self) -> None:
        """What POINTS.md owes on its own, independent of which rows point at it.

        The clause-to-section map used to be asserted here as set equality AND again in
        `test_every_construction_anchor_resolves`. Two writers of one claim, and set equality is
        now the wrong claim besides: rows may share a section, so P02 has no heading of its own.
        The map lives entirely in the anchor test, in both directions. What is left here is what
        that test cannot see -- a heading that appears twice, and a heading over nothing.
        """
        headings = [h for h in _headings(self.points_md) if h != "Contents"]
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
        itself. This is now the ONLY place the rule is enforced, and that move is deliberate: the
        loader used to check anchor shape too, at dispatch time, where one row's typo made the
        whole table unloadable and denied every tool call in the session. A documentation pointer
        cannot change between the build and the call, so the build is the only boundary that
        needs to judge it -- and this test judges more than the loader did, resolving every
        fragment against a real heading and, in the other direction, refusing a section no row
        claims. Rows may share a section -- P01 and P02 are one plan point split by which ground
        a step is missing -- so this is a total map both ways, never a bijection.
        """
        headings = {h.lower() for h in _headings(self.points_md)}
        headings.discard("contents")
        claimed = set()
        for row in self.rows:
            anchor = row.get("construction")
            self.assertTrue(anchor, f"{row['id']}: no construction anchor")
            # The shape assertion the loader gave up, held against the pattern the loader still
            # owns -- so "what an anchor looks like" keeps one definition even though the check
            # moved to the other end of the build.
            # `fullmatch`, not `assertRegex`: the pattern carries no anchors of its own, so a
            # search would accept `see POINTS.md#a01 for details` as an anchor. The loader used
            # fullmatch; moving the check must not weaken it.
            self.assertTrue(C_MOD.CONSTRUCTION_ANCHOR.fullmatch(anchor),
                            f"{row['id']}: {anchor!r} is not an anchor shape")
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
        headings = {h.lower() for h in _headings(self.points_md)}
        for label, target in links:
            self.assertIn(target, headings,
                          f"contents row {label} links to #{target}, which is no heading")


class TheActList(unittest.TestCase):
    """ACTS.md's headings are the single home of the act list, held to the pinned ten."""

    def setUp(self) -> None:
        self.acts = _load(ACTS_MD)

    def test_the_act_headings_are_exactly_the_ten(self) -> None:
        """Set equality both directions, so neither an invented act nor a dropped one passes.

        Every heading, not a word-shaped subset: a heading the pattern cannot see is a heading
        the equality never judges. And a list, not a set -- a duplicated section is two homes
        for one act, and sets erase exactly that.
        """
        indexed = _headings(self.acts)
        self.assertEqual(len(indexed), len(set(indexed)), f"duplicate act heading: {indexed}")
        self.assertEqual(
            set(indexed), set(TEN_ACTS),
            f"ACTS.md and the pinned act list disagree: "
            f"only in ACTS.md {sorted(set(indexed) - set(TEN_ACTS))}, "
            f"only in the pin {sorted(set(TEN_ACTS) - set(indexed))}",
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
    """Every generated appearance of the clause facts is a rendering of clauses.json.

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
        self._assert_both_occasions(folded)

    # The two occasions this package fires on, each pinned by a literal. This plugin carries two
    # halves of one sentence -- "asymmetry is where the DEFAULT is the unhealing issue" read for
    # harm, and read for benefit -- and the description is the applicability predicate for both:
    # it is what a model reads to decide whether this page is relevant at all.
    #
    # THE MERGE DROPPED ONE OF THEM, AND NOTHING NOTICED. Swale's description led with the
    # repetition occasion -- "Use when a guard has just been run by hand and will be needed
    # again" -- and the merged description opened with the costly-act list instead. Measured: that
    # phrase occurred zero times in this file. Every construction survived the merge (all 24
    # clauses carry an anchor) and the OCCASION did not, so the positive half could only be
    # reached through a denial: a session repeating a guard by hand while tripping no clause --
    # exactly what the positive half is for -- got nothing.
    #
    # Length checks could not see it. A description can be 158 words, well-formed, under budget,
    # and silently half a trigger.
    OCCASIONS = (
        ("the repetition occasion", ("run by hand", "needed again")),
        ("the costly-act occasion", ("decides what the rest of the run inherits",)),
    )

    def _assert_both_occasions(self, folded: str) -> None:
        for label, phrases in self.OCCASIONS:
            missing = [p for p in phrases if p not in folded]
            self.assertEqual(
                [], missing,
                f"the description no longer names {label} (missing {missing}). This page serves "
                f"both halves of one sentence; a description that names only one of them makes "
                f"the other reachable only by accident.")

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red
        """Drop the repetition occasion the way the merge did, and the fence must name it.

        The planted edit is deliberately the merge's own edit: the leading clause removed, the
        rest of the description left well-formed, still long, still under budget. That is what
        the regression actually looked like, and it is what every check on this description
        except this one still passes.
        """
        smoke_replace(
            self, PLUGIN / "SKILL.md",
            b'  Use when a guard has just been run by hand and will be needed again '
            b'\xe2\x80\x94 the same check, the same\n  "remember to" \xe2\x80\x94 and before a '
            b'call that decides what the rest of the run inherits: pushing,\n',
            b'  Use before a call that decides what the rest of the run inherits: pushing,\n',
            "tests.test_fence.SkillIsLoadable.test_frontmatter_declares_a_name_and_a_trigger",
            "the repetition occasion")

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


class RenderedImagesTrackTheirSource(unittest.TestCase):
    """The README shows PNGs; `tools/render_readme_images.py` renders them from the SVGs beside
    them. That is a generated view like any other, and it was the only one in this tree with no
    mechanical consumer joining it to its source -- exactly the shape that let a "GENERATED, do
    not edit" page rot unnoticed, one file type over.

    WHAT THIS CHECKS, AND WHAT IT DOES NOT. Dimensions only. It catches an SVG resized without
    its PNGs re-rendered; it does NOT catch a colour or wording change inside an unchanged
    viewBox. The obvious stronger check -- re-render and byte-compare -- is not here on purpose:
    rendering goes through a headless browser, and the same bytes on two different runners is
    unproven. A check that can go red without a defect teaches people to ignore it, which costs
    more than the coverage it would add. Stated rather than left for a reader to discover, so
    this cannot be mistaken for "the images are verified".
    """

    def _scale(self) -> int:
        # Read from the renderer, never retyped here. A second copy of this number is a second
        # writer of one fact, and it would drift silently in the direction that makes this test
        # agree with a stale rendering.
        sys.path.insert(0, str(REPO / "tools"))
        import render_readme_images
        return render_readme_images.SCALE

    def _png_size(self, path: Path) -> tuple[int, int]:
        # IHDR is the first chunk and its width/height are big-endian at a fixed offset, so the
        # header alone answers this -- no imaging library, and none in CI.
        header = path.read_bytes()[:24]
        self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n", f"{path.name} is not a PNG")
        return struct.unpack(">II", header[16:24])

    def test_every_svg_has_both_renderings_at_the_declared_scale(self) -> None:
        sources = sorted((REPO / "docs" / "img").glob("*.svg"))
        self.assertTrue(sources, "no SVG sources found, so this checked nothing")
        for svg in sources:
            box = re.search(r'viewBox="([\d.\s-]+)"', svg.read_text(encoding="utf-8"))
            self.assertIsNotNone(box, f"{svg.name} has no viewBox to compare against")
            _, _, width, height = (float(n) for n in box.group(1).split())
            scale = self._scale()
            for variant in ("light", "dark"):
                png = svg.with_name(f"{svg.stem}-{variant}.png")
                self.assertTrue(png.is_file(),
                                f"{svg.name} has no {variant} rendering at {png.name}")
                self.assertEqual(
                    self._png_size(png), (int(width * scale), int(height * scale)),
                    f"{png.name} does not match {svg.name}'s viewBox at {scale}x -- the source "
                    f"was resized and the rendering was not regenerated",
                )


if __name__ == "__main__":
    unittest.main()


class TheShippedFilesNameOnlyThingsThatExist(unittest.TestCase):
    """A pointer nothing resolves is how three dead references survived a whole rename.

    `plugin/hooks/hooks.json` carried a `_provenance` block for a year of edits after the thing it
    described stopped existing:

        "live_source_of_truth": "plugin/clauses/"        no such directory in this repository
        "recompute_with": "python3 -m gyroscope.generate" no such module, under either name
        "as_of": "sha256:78e84e3333284c96"               a digest of the above, so of nothing

    Nothing read any of it, which is exactly why nothing noticed. The block is gone -- these hooks
    are authored here, not generated, so a provenance claim about a generator was false as well as
    stale -- and this class is what stops the next one. It resolves the pointers the shipped files
    DO make, and refuses the pre-rename identifiers outright: `gyroscope` names nothing in this
    tree any more, so any occurrence of it in a shipped file is a reference to something that is
    not there.
    """

    SHIPPED = ("hooks/hooks.json", "hooks/hooks.codex.json", "hooks/dispatch.sh",
               ".claude-plugin/plugin.json")

    def test_TEETH_no_shipped_file_names_the_pre_rename_package(self) -> None:
        for name in self.SHIPPED:
            path = PLUGIN / name
            with self.subTest(file=name):
                self.assertTrue(path.is_file(), f"{name} is not where this test expects it")
                text = path.read_text(encoding="utf-8")
                self.assertNotIn(
                    "gyroscope", text.lower(),
                    f"{name} still names the pre-rename package -- a pointer to nothing")

    def test_TEETH_every_hook_command_reaches_a_file_that_exists(self) -> None:
        seen = 0
        for name in ("hooks/hooks.json", "hooks/hooks.codex.json"):
            data = json.loads((PLUGIN / name).read_text(encoding="utf-8"))
            for event, entries in (data.get("hooks") or {}).items():
                for entry in entries:
                    for hook in entry.get("hooks") or []:
                        command = hook.get("command", "")
                        # Both spellings of "beside this plugin": the host substitutes the
                        # variable, and the codex file uses a relative path from the plugin root.
                        relative = re.sub(r"^\$\{[A-Z_]+\}/|^\./", "", command)
                        seen += 1
                        self.assertTrue(
                            (PLUGIN / relative).is_file(),
                            f"{name} {event}: command {command!r} names no file in the plugin")
        self.assertGreater(seen, 5, f"only {seen} hook commands reached the assertion")


# The English number words these pages actually use to state a total, and their values. Derived
# from the spelling, not from a table of allowed totals: `twenty-four` is `20 + four`, so the map
# cannot go stale when a count moves. Nothing above twenty-nine has ever appeared here; a larger
# total would simply not be seen, which is why the check reports its omissions below.
_ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
         "fifteen sixteen seventeen eighteen nineteen twenty").split()
NUMBER_WORDS = {word: value for value, word in enumerate(_ONES)}
NUMBER_WORDS.update({f"twenty-{w}": 20 + v for v, w in enumerate(_ONES[1:10], 1)})

# A TOTAL claim in these pages is written with a determiner: "the ten acts", "these ten acts".
# Without one the same words are ordinary prose that counts nothing -- "overruling a stated one
# are different acts", "They are not two points" -- and both are in the shipped text today. The
# determiner is what separates them, so it is required rather than a list of phrases to skip.
# Up to two words may sit between the number and its noun ("the seven coarser acts"), which is
# the form the defect this class exists for was written in.
# Digits as well as words. No page writes a total in digits today, so this alternative matches
# nothing at the moment -- which is the reason to add it now rather than after "the 24 points"
# has been written and quietly missed. A check whose coverage depends on a house style nothing
# enforces is a check with a hole in the shape of that style.
SPELLED_TOTAL_RX = re.compile(
    r"\b(?:the|these|those|all)\s+(\d{1,3}|%s)\s+((?:[\w-]+\s+){0,2}?)([a-z]+s)\b"
    % "|".join(sorted(NUMBER_WORDS, key=len, reverse=True)),
    re.IGNORECASE,
)


# Spelled totals no source can settle. Each is ORDINARY ENGLISH that SPELLED_TOTAL_RX reads as a
# counted noun phrase -- "the one thing", "the two rows" -- not a claim about a quantity anything
# computes. They are named here rather than left in a printed residue nobody reads, so a genuinely
# unbacked total cannot hide among them.
UNJOINABLE_TOTALS = (
    "POINTS.md:173 'the one thing this'",   # "...which is the one thing this mechanism refuses"
    "POINTS.md:179 'the two rows'",         # "the two rows above key on" -- a back-reference
    "SKILL.md:129 'The one test defines'",  # "do not define. The one test defines."
)


class SpelledCountsMatchWhatTheyCount(unittest.TestCase):
    """Every spelled-out total on a shipped page, joined to the thing it counts.

    WHY THIS EXISTS. The pages state counts in words -- "the ten acts", "the twenty-four points"
    -- and nothing held those words to the tables they describe. The relation was true when
    written and drifted in silence, because the only thing carrying it was a person remembering
    to sweep. `test_the_table_still_holds_twenty_four_clauses` said so in its own docstring: it
    pinned the number on one side and asked the prose sweep to happen on the other.

    It drifted. Raising ACTS.md from seven acts to ten updated the headings and the pinned list
    and left SKILL.md's index entry reading "the seven coarser acts", and the whole fence stayed
    green. Planting the reverse -- retitling ACTS.md "The nine acts" with ten headings present --
    was also green. Both are joined here now.

    WHAT IT DOES NOT SEE, and says so rather than passing over it. The scope is swept from the
    pages, but only nouns whose count can be COMPUTED from a single source can be judged; the
    rest are reported by `test_the_check_reports_what_it_cannot_join` instead of being silently
    dropped. A total written without a determiner is not seen at all -- that is the price of not
    firing on ordinary prose, and it is paid knowingly.
    """

    def counted(self) -> dict[str, int]:
        """noun -> the count computed from the ONE place that fact lives.

        Never from another page's prose: a count read out of the text would make the check agree
        with whatever was written, which is the failure it exists to end.
        """
        skill = _load(SKILL)
        constructions = re.findall(r"^\*\*(\d+)\.\s", skill, re.MULTILINE)
        shapes = json.loads(_load(VOCABULARY))["shapes"]
        clauses = _clause_rows()
        return {
            "acts": len(_headings(_load(ACTS_MD))),
            "points": len(clauses),
            "moments": len(clauses),
            "constructions": len(constructions),
            "shapes": len(shapes),
            "tiers": len(re.findall(r"^### Tier ", skill, re.MULTILINE)),
        }

    def occurrences(self):
        """(page, line number, value, noun, phrase) for every spelled total on every page."""
        for page in PAGES:
            for number, line in enumerate(_load(page).splitlines(), 1):
                for found in SPELLED_TOTAL_RX.finditer(line):
                    token = found.group(1).lower()
                    value = int(token) if token.isdigit() else NUMBER_WORDS[token]
                    yield page, number, value, found.group(3).lower(), found.group(0)

    def test_every_spelled_total_equals_what_it_counts(self) -> None:
        counted = self.counted()
        self.assertTrue(all(counted.values()), f"a computed count came out empty: {counted}")
        wrong = [
            f"{page.name}:{line} says {phrase!r} but there are {counted[noun]} {noun}"
            for page, line, value, noun, phrase in self.occurrences()
            if noun in counted and value != counted[noun]
        ]
        self.assertEqual([], wrong, "a page states a count that its own source contradicts")

    def test_the_check_has_a_subject(self) -> None:
        """An empty subject is reported, not passed over.

        A sweep that matches nothing returns no mismatches and looks identical to a clean one.
        Every count in this suite that can be green over nothing is required to say so instead.
        """
        counted = self.counted()
        joined = [o for o in self.occurrences() if o[3] in counted]
        self.assertGreater(
            len(joined), len(counted),
            f"only {len(joined)} spelled totals resolve to a computed count; the sweep has "
            "stopped seeing the pages it is supposed to be reading")

    def test_the_check_reports_what_it_cannot_join(self) -> None:
        """Name the totals no source can settle, so the residue is visible rather than assumed."""
        counted = self.counted()
        occurrences = list(self.occurrences())
        unjoined = sorted({
            f"{page.name}:{line} {phrase!r}"
            for page, line, _, noun, phrase in occurrences if noun not in counted
        })
        # THE DENOMINATOR IS OCCURRENCES, NOT DEFINITIONS. This printed
        # `joined={len(counted)}` -- the number of noun-to-count definitions available, which
        # includes definitions that matched no occurrence at all. The number that belongs beside
        # `unjoined` is how many occurrences were actually settled, and those two can differ
        # without anything noticing.
        joined = [o for o in occurrences if o[3] in counted]
        print(f"\nDENOMINATOR subject=spelled-totals occurrences={len(occurrences)} "
              f"joined={len(joined)} unjoined={len(unjoined)} definitions={len(counted)}")
        self.assertEqual(
            len(occurrences), len(joined) + len(unjoined),
            "an occurrence is either joined to a computed count or named as unjoined; it cannot "
            "be both or neither")
        # `assertIsInstance(unjoined, list)` stood here, over a value built by `sorted(...)`,
        # which returns a list always: it could not fail, and the residue this test is named for
        # was only printed. The residue is DECLARED instead, so a new spelled total that no
        # source can settle has to be named rather than absorbed into a number nobody reads.
        self.assertEqual(
            sorted(UNJOINABLE_TOTALS), unjoined,
            "the set of spelled totals no source can settle has changed. A new one means a page "
            "states a number nothing computes -- give it a source, or name it in "
            "UNJOINABLE_TOTALS with the reason. One that disappeared now has a source, so take "
            "it off the list.")

    def test_the_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red
        """Retitle ACTS.md against its own headings, and this must go red.

        This exact edit -- a spelled total moved while the headings stayed -- was made by hand
        against the fence before this class existed and the whole suite returned OK.
        """
        smoke_replace(
            self, ACTS_MD, b"# The ten acts", b"# The nine acts",
            "tests.test_fence.SpelledCountsMatchWhatTheyCount."
            "test_every_spelled_total_equals_what_it_counts",
            "says 'The nine acts' but there are 10 acts",
        )

    def test_the_subject_check_can_fail(self) -> None:  # makoto-allow: teeth are in smoke_replace, which runs the target green, plants the fault, then requires red
        """Blind the sweep, and the empty subject must be reported rather than pass.

        Planted in the pattern rather than in a page, because that is where the failure would
        really come from: a regex that stops matching turns every mismatch test in this class
        green at once, and only this method can tell that from a clean tree.
        """
        smoke_replace(
            self, Path(__file__), b'r"\\b(?:the|these|those|all)\\s+', b'r"\\bNOTHINGMATCHESTHIS\\s+',
            "tests.test_fence.SpelledCountsMatchWhatTheyCount.test_the_check_has_a_subject",
            "stopped seeing the pages",
        )
