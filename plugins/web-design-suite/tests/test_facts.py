"""web-design-suite: the docs say only what is true (phase 2, item 11).

Each test checks a claim against the code it describes, a browser, or a
recorded fact with its source and the date it was read.

Regressions covered:
- GT-A10: the a11y docs promised runtime behaviour the code does not have.
  They said incompletes fail "under --strict", a flag the runtime lacks. They
  said the key check drives Space, Home/End and Tab, which it never presses.
  They listed reduced motion among the implemented techniques. They left the
  budget's 13 keys undocumented. And the code filed horizontal scroll at 200%
  zoom as a 1.4.4 error, which it is not.
- GT-A7: the coverage sources were misdescribed. Deque's 57% is fully
  automated testing, not guided testing with a human. GDS counted barriers
  found, not criteria. The coverage table missed 7 of WCAG 2.2's 55 A/AA
  criteria, and its own count was not "roughly a third Full".
- GT-A9: "Not Evaluated" was recommended for any criterion. VPAT 2.5 allows
  it for Level AAA only.
- SS-A11: container queries were said to apply layout containment, and
  readers were told to portal fixed modals out. The CSSWG dropped that in
  2024. The gotcha that remains is the new formatting context.
- SS-A16: a subgrid may set its own gap. Safari was not last to ship subgrid.
  1.4.4 is Level AA, not A. The 2.4.13 row carried 1.4.11's adjacent-colour
  clause. Large text is 18pt, or 14pt bold. APCA is no longer WCAG 3's
  candidate. And sRGB's chroma ceiling and yellow's hue were misquoted.
- SB-A21 (b, c): WCAG 2.2 was called the EU and ADA legal baseline, which it
  is not yet. And a 200% zoom check was labelled 1.4.10.
- GT-A19: smaller errors. A contents list was numbered against the wrong
  headings. `transition: width` was said to fail both gates, and the runtime
  gate to split time by origin. A density example gave two numbers for one
  value. A class-swapped state was blamed on Law 8, the keyboard law, and
  large text was filed under 1.4.11. The screen-reader pairing contradicted
  WebAIM's survey. And the generated proof sheet's own marks failed 4.5:1.
- LC-A16 (rest): Bootstrap's !important utilities beat every layer above
  them, which the layer advice never said. The MUI example needs native
  colour to read a var().
- XC-A3: the README said any single `.skill` file works standalone.
- DL-A15: the email matrix contradicted its own source, caniemail. flex and
  grid work in Thunderbird, Samsung and Outlook for Mac, and dark-mode
  queries work across the Outlook apps but not in Thunderbird 78 or 91. Two
  Yahoo quirks no longer reproduce.
- DL-A16: Gmail removes every <style> element that crosses its 16 KB
  ceiling, and the ones after, not "the excess". The build emitted one
  block, so going over lost all of it.
- DL-A17: classic Outlook was said to end in October 2026 (that is Office
  2021). The top test target was an Outlook leaving support. Transactional
  mail was told it needs one-click headers. "Read more" was cited under
  2.4.4, which context satisfies. And Postmark was given {{#if}}.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import unittest

from wds_support import NODE, SKILLS, TempDirTest, env, output, run_node, tool_modules

A11Y = SKILLS / "a11y-audit-runner"
RUNTIME = A11Y / "scripts" / "a11y_runtime.mjs"


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


# WCAG 2.2's Level A and AA success criteria (w3.org/TR/WCAG22; 4.1.1 was
# removed in 2.2): 31 at A and 24 at AA.
WCAG22_A_AA = {
    "1.1.1", "1.2.1", "1.2.2", "1.2.3", "1.2.4", "1.2.5", "1.3.1", "1.3.2", "1.3.3", "1.3.4",
    "1.3.5", "1.4.1", "1.4.2", "1.4.3", "1.4.4", "1.4.5", "1.4.10", "1.4.11", "1.4.12",
    "1.4.13", "2.1.1", "2.1.2", "2.1.4", "2.2.1", "2.2.2", "2.3.1", "2.4.1", "2.4.2", "2.4.3",
    "2.4.4", "2.4.5", "2.4.6", "2.4.7", "2.4.11", "2.5.1", "2.5.2", "2.5.3", "2.5.4", "2.5.7",
    "2.5.8", "3.1.1", "3.1.2", "3.2.1", "3.2.2", "3.2.3", "3.2.4", "3.2.6", "3.3.1", "3.3.2",
    "3.3.3", "3.3.4", "3.3.7", "3.3.8", "4.1.2", "4.1.3",
}

# What checkKeymap() presses, per pattern (a11y_runtime.mjs, "Keyboard").
DRIVEN = {"dialog": {"Enter", "Escape"}, "menu": {"Enter", "ArrowDown", "Escape"},
          "combobox": {"ArrowDown"}, "disclosure": {"Enter"}, "tabs": {"ArrowRight"}}
KEY_WORDS = {"Enter": "Enter", "Space": "Space", "Esc": "Escape", "Escape": "Escape",
             "Tab": "Tab", "Home": "Home", "End": "End", "↓": "ArrowDown", "↑": "ArrowUp",
             "→": "ArrowRight", "←": "ArrowLeft", "Alt+↓": "Alt+ArrowDown",
             "Arrow": "Arrow*", "ArrowDown": "ArrowDown", "ArrowRight": "ArrowRight",
             "Down arrow": "ArrowDown", "Up arrow": "ArrowUp", "Right arrow": "ArrowRight",
             "Left arrow": "ArrowLeft", "Alt+Down arrow": "Alt+ArrowDown"}


def keys_named(text: str) -> set[str]:
    names = sorted(KEY_WORDS, key=len, reverse=True)
    pattern = "|".join(re.escape(n) for n in names)
    return {KEY_WORDS[m] for m in re.findall(rf"(?<![\w-])({pattern})(?![\w-])", text)}


def a11y_skill_text() -> str:
    """SKILL.md plus the script reference it points to (moved there in 3.2.0)."""
    scripts = A11Y / "references" / "scripts.md"
    return read(A11Y / "SKILL.md") + ("\n" + read(scripts) if scripts.exists() else "")


class RuntimePromises(unittest.TestCase):
    """GT-A10."""

    def test_the_code_still_presses_what_the_test_says(self):
        code = read(RUNTIME)
        for key in set().union(*DRIVEN.values()):
            self.assertRegex(code, rf"'{key}'")

    def test_the_keys_check_claims_only_the_keys_it_presses(self):
        row = next(line for line in a11y_skill_text().splitlines()
                   if line.startswith("| `keys` |"))
        driven = row.split("|")[2].split(";")[0]          # before "; ... are manual"
        self.assertLessEqual(keys_named(driven), set().union(*DRIVEN.values()), row)

    def test_each_driven_pattern_names_only_its_own_keys(self):
        text = read(A11Y / "references" / "runtime-checks.md")
        rows = re.findall(r"^\| \*\*(Dialog|Menu|Tabs|Disclosure|Combobox)\*\* \| ([^|]*) \|",
                          text, re.M)
        self.assertEqual(len(rows), 5)
        for pattern, driven in rows:
            with self.subTest(pattern=pattern):
                self.assertLessEqual(keys_named(driven), DRIVEN[pattern.lower()], driven)

    def test_incompletes_fail_through_the_budget_not_a_missing_flag(self):
        text = read(A11Y / "references" / "automation-coverage.md")
        self.assertNotIn("Under `--strict` they fail", text)
        self.assertIn("axe_incomplete", text)

    def test_the_budget_keys_are_documented(self):
        code = read(RUNTIME).split("const BUDGET_KEYS = {", 1)[1].split("\n};", 1)[0]
        keys = set(re.findall(r"^  (\w+): \(f\)", code, re.M))
        self.assertEqual(len(keys), 13)
        row = next(line for line in a11y_skill_text().splitlines()
                   if line.startswith("| `--budget FILE` |"))
        self.assertEqual(set(re.findall(r"`([a-z]+(?:_[a-z]+)+)`", row)), keys)

    def test_reduced_motion_is_not_listed_as_implemented(self):
        if "reducedMotion: 'no-preference'" not in read(RUNTIME):
            self.skipTest("the runtime now emulates reduced motion")
        intro = read(A11Y / "references" / "runtime-checks.md").split("\n\n", 2)[1]
        if "Every technique here is implemented" in intro:
            self.assertRegex(intro, r"except §6")


def a11y_modules():
    return tool_modules("WDS_NODE_MODULES", "playwright", "axe-core", node_path=True)


@unittest.skipUnless(NODE and a11y_modules(), "needs node plus WDS_NODE_MODULES pointing at "
                                               "playwright and axe-core")
class ZoomInABrowser(TempDirTest):
    """GT-A10: horizontal scroll at 200% zoom was filed as a 1.4.4 error."""

    def test_horizontal_scroll_at_200_percent_is_a_warning(self):
        page = self.write("wide.html", "<!doctype html><html lang=\"en\"><title>t</title><main>"
                                       "<h1>Wide</h1><div style=\"width: 900px\">wide</div></main>")
        proc = run_node("a11y-audit-runner", "a11y_runtime.mjs", "--file", page, "--json",
                        cwd=self.tmp, env_changes={"NODE_PATH": a11y_modules()}, timeout=300)
        if proc.returncode == 2 and b"browser" in proc.stderr.lower():
            self.skipTest("no usable browser: " + output(proc)[-200:])
        self.assertIn(proc.returncode, (0, 1), output(proc))
        reflow = [f for f in json.loads(proc.stdout)["findings"] if f["check"] == "reflow"]
        self.assertFalse([f for f in reflow if f["sc"] == "1.4.4" and f["severity"] == "error"],
                         reflow)
        self.assertTrue([f for f in reflow if f["sc"] == "1.4.10" and f["severity"] == "error"],
                        reflow)
        self.assertTrue([f for f in reflow if f["severity"] == "warning"], reflow)


# ---------------------------------------------------------------------------
# GT-A7, GT-A9 -- coverage and reporting
# ---------------------------------------------------------------------------

def coverage_table() -> dict[str, str]:
    """{criterion: Full | Partial | None} from automation-coverage.md §3."""
    text = read(A11Y / "references" / "automation-coverage.md")
    table = text.split("## 3. The coverage table", 1)[1].split("\n## ", 1)[0]
    verdicts = {}
    for first, auto in re.findall(r"^\| \*\*([\d./ ]+)\*\*[^|]*\| \**(Full|Partial|None)", table, re.M):
        for sc in re.findall(r"\d+\.\d+\.\d+", first):
            verdicts[sc] = auto
    return verdicts


def suite_docs():
    for md in sorted(SKILLS.glob("*/SKILL.md")) + sorted(SKILLS.glob("*/references/*.md")):
        yield md, read(md)


class CoverageFigures(unittest.TestCase):
    """GT-A7, GT-A9."""

    def test_the_table_covers_every_a_and_aa_criterion(self):
        self.assertEqual(set(coverage_table()), WCAG22_A_AA)

    def test_every_count_quoted_matches_the_table(self):
        verdicts = list(coverage_table().values())
        full, partial, none = (verdicts.count(v) for v in ("Full", "Partial", "None"))
        quoted = 0
        for md, text in list(suite_docs()) + [(RUNTIME, read(RUNTIME))]:
            for m in re.finditer(r"(\d+) of the 55\b", text):
                quoted += 1
                sentence = text[m.start(): text.find(".", m.end()) + 1]
                with self.subTest(doc=md.name, quote=sentence[:80]):
                    self.assertEqual(int(m.group(1)), full)
                    more = re.search(r"part of (\d+)", sentence)
                    if more:
                        self.assertEqual(int(more.group(1)), partial)
                    rest = re.search(r"(\d+) (?:need a person|it cannot decide)", sentence)
                    if rest:
                        self.assertEqual(int(rest.group(1)), none)
        self.assertGreaterEqual(quoted, 3)

    def test_no_doc_calls_automation_a_third_of_the_criteria(self):
        wrong = re.compile(r"(?i)(a|one) third of (the |WCAG )*(success )?criteria|"
                           r"\d+(?:–\d+)?% of (?:the |WCAG )*(?:success )?criteria|"
                           r"(roughly|about) a third of WCAG|catches about a third|"
                           r"a human answering questions|human-answered guided")
        for md, text in list(suite_docs()) + [(RUNTIME, read(RUNTIME))]:
            with self.subTest(doc=md.name):
                self.assertNotRegex(text, wrong)

    def test_not_evaluated_is_offered_for_aaa_only(self):
        for md, text in suite_docs():
            for m in re.finditer(r"Not Evaluated", text):
                paragraph = text[text.rfind("\n\n", 0, m.start()): text.find("\n\n", m.end())]
                with self.subTest(doc=md.name, at=paragraph.strip()[:70]):
                    self.assertIn("AAA", paragraph)


# ---------------------------------------------------------------------------
# SS-A11, SS-A16, SB-A21 (b, c) -- web-design-studio's facts
# ---------------------------------------------------------------------------

STUDIO = SKILLS / "web-design-studio"
LAYOUT_DOCS = (STUDIO / "references" / "layout-composition.md",
               STUDIO / "assets" / "starter" / "styles" / "layout.css")
LEVEL_A = {
    "1.1.1", "1.2.1", "1.2.2", "1.2.3", "1.3.1", "1.3.2", "1.3.3", "1.4.1", "1.4.2", "2.1.1",
    "2.1.2", "2.1.4", "2.2.1", "2.2.2", "2.3.1", "2.4.1", "2.4.2", "2.4.3", "2.4.4", "2.5.1",
    "2.5.2", "2.5.3", "2.5.4", "3.1.1", "3.2.1", "3.2.2", "3.2.6", "3.3.1", "3.3.2", "3.3.7",
    "4.1.2",
}
LEVEL_AAA = {
    "1.2.6", "1.2.7", "1.2.8", "1.2.9", "1.3.6", "1.4.6", "1.4.7", "1.4.8", "1.4.9", "2.1.3",
    "2.2.3", "2.2.4", "2.2.5", "2.2.6", "2.3.2", "2.3.3", "2.4.8", "2.4.9", "2.4.10", "2.4.12",
    "2.4.13", "2.5.5", "2.5.6", "3.1.3", "3.1.4", "3.1.5", "3.1.6", "3.2.5", "3.3.5", "3.3.6",
    "3.3.9",
}


def level(sc: str) -> str | None:
    if sc in LEVEL_A:
        return "A"
    if sc in WCAG22_A_AA:
        return "AA"
    return "AAA" if sc in LEVEL_AAA else None


def all_texts():
    for path in sorted(SKILLS.rglob("*")):
        if path.suffix in (".md", ".css", ".py", ".mjs") and path.is_file():
            yield path, read(path)


class StudioFacts(unittest.TestCase):

    def test_containers_are_not_said_to_contain_layout(self):
        """SS-A11: container-type stopped applying layout containment (CSSWG,
        2024-07-24; shipped everywhere). It makes a new formatting context."""
        for path in LAYOUT_DOCS:
            text = read(path)
            with self.subTest(doc=path.name):
                self.assertNotRegex(text, r"(?i)applies `contain: layout|portal such things")
                self.assertRegex(text, r"formatting context")

    def test_a_subgrid_may_set_its_own_gap(self):
        for path in LAYOUT_DOCS:
            with self.subTest(doc=path.name):
                self.assertNotRegex(read(path), r"(?i)set no gap of its own|Safari was last in")

    def test_every_level_quoted_is_the_criterions_level(self):
        tight = re.compile(r"\b(\d\.\d\.\d{1,2})\b,? \(?(?:Level )?(AAA|AA|A)\b")
        checked = 0
        for path, text in all_texts():
            for sc, said in tight.findall(text):
                if level(sc):
                    checked += 1
                    with self.subTest(doc=path.name, sc=sc, said=said):
                        self.assertEqual(said, level(sc))
        self.assertGreater(checked, 5)

    def test_the_2_4_13_row_holds_only_what_2_4_13_asks(self):
        row = next(line for line in read(STUDIO / "references" / "color-system.md").splitlines()
                   if "| 2.4.13 Focus Appearance" in line)
        self.assertNotIn("adjacent background", row)      # that is 1.4.11
        self.assertNotIn("--shadow-focus", row)           # the ring is an outline now

    def test_large_text_and_apca_are_stated_correctly(self):
        text = read(STUDIO / "references" / "color-system.md")
        self.assertNotIn("18.66px/14px", text)            # 18pt, or 14pt bold
        self.assertNotIn("the candidate algorithm for WCAG 3", text)

    def test_the_colour_space_numbers_are_what_the_maths_gives(self):
        from test_starter_css import _load_generator
        gen = _load_generator()
        steps = [i / 32 for i in range(33)]
        chroma = 0.0
        for fixed in (0.0, 1.0):
            for u in steps:
                for v in steps:
                    for rgb in ((fixed, u, v), (u, fixed, v), (u, v, fixed)):
                        lab = gen.linear_srgb_to_oklab(*(gen.srgb_to_linear(c) for c in rgb))
                        chroma = max(chroma, gen.oklab_to_oklch(*lab)[1])
        yellow = gen.hex_to_oklch("#ffff00")[2]
        text = read(STUDIO / "references" / "color-system.md")
        said = re.search(r"\*\*C \(0 → ~([\d.]+) in sRGB\)\*\*", text)
        self.assertIsNotNone(said)
        self.assertAlmostEqual(float(said.group(1)), chroma, delta=0.005)
        hue = re.search(r"\*\*(\d+)\*\* yellow", text)
        self.assertAlmostEqual(int(hue.group(1)), yellow, delta=3)

    def test_wcag_2_2_is_not_called_the_legal_baseline(self):
        """SB-A21 (b), read 2026-09-25. EU: the cited harmonised standard is
        EN 301 549 v3.2.1 (WCAG 2.1); v4.1.1 (WCAG 2.2) was published
        2026-09-02 and is not yet cited in the Official Journal (ETSI; EC
        digital-strategy). ADA Title II: WCAG 2.1 AA from 2027-04-26 and
        2028-04-26 (ada.gov, interim final rule of April 2026). Section 508:
        WCAG 2.0 AA."""
        intro = read(STUDIO / "references" / "accessibility.md").split("\n\n", 2)[1]
        self.assertNotRegex(intro, r"(?i)2\.2[^.]*legal baseline|legal baseline[^.]*2\.2")
        for fact in ("EN 301 549 v3.2.1", "WCAG 2.1", "v4.1.1", "Section 508", "WCAG 2.0",
                     "2027-04-26", "2028-04-26"):
            self.assertIn(fact, intro)

    def test_200_percent_zoom_is_never_labelled_reflow(self):
        """SB-A21 (c): reflow (1.4.10) is 320 CSS px, which is 400% zoom."""
        for md, text in suite_docs():
            for line in text.splitlines():
                if "200%" in line and "1.4.10" in line and not re.search(r"400%|320", line):
                    with self.subTest(doc=md.name, line=line[:90]):
                        self.fail("200% zoom is 1.4.4; reflow (1.4.10) is a 320px viewport")


# ---------------------------------------------------------------------------
# GT-A19 -- smaller errors
# ---------------------------------------------------------------------------

def slug(heading: str) -> str:
    """GitHub's anchor for a heading."""
    return re.sub(r"\s", "-", re.sub(r"[^\w\s-]", "", heading.strip().lower()))


HEADING = re.compile(r"^#{2,6} (.+)$", re.M)
NUMBERED = re.compile(r"^(\d+(?:\.\d+)*)\.?\s")


class SmallFacts(unittest.TestCase):

    def test_every_contents_list_matches_its_headings(self):
        checked = 0
        for md, text in suite_docs():
            if "## Contents" not in text:
                continue
            headings = {}
            for h in HEADING.findall(text):
                num = NUMBERED.match(h)
                headings[slug(h)] = (num.group(1) if num else None, NUMBERED.sub("", h).strip())
            titles = {title.lower(): num for num, title in headings.values()}
            toc = text.split("## Contents", 1)[1].split("\n## ", 1)[0]
            for line in toc.splitlines():
                m = (re.match(r"^(\d+)\.\s+\[(.+?)\]\(#([^)]+)\)", line) or
                     re.match(r"^-\s+\[(\d+(?:\.\d+)*)\.?\s+(.+?)\]\(#([^)]+)\)", line))
                bare = re.match(r"^(\d+)\.\s+([^\[].*)$", line)
                if m:
                    checked += 1
                    shown, anchor = m.group(1), m.group(3)
                    with self.subTest(doc=md.name, item=line[:70]):
                        self.assertIn(anchor, headings, "the link lands on no heading")
                        self.assertEqual(headings[anchor][0], shown)
                elif bare and bare.group(2).strip().lower() in titles:
                    checked += 1
                    with self.subTest(doc=md.name, item=line[:70]):
                        self.assertEqual(titles[bare.group(2).strip().lower()], bare.group(1))
        self.assertGreater(checked, 50)

    def test_the_design_audit_is_not_said_to_catch_a_width_transition(self):
        self.assertNotRegex(read(SKILLS / "perf-budget-gate" / "SKILL.md"),
                            r"`transition: width` is a design violation")

    def test_the_runtime_gate_is_not_said_to_split_by_origin(self):
        self.assertNotIn("main-thread time by origin",
                         read(SKILLS / "perf-budget-gate" / "references" / "budgets.md"))

    def test_the_density_example_gives_one_number(self):
        text = read(SKILLS / "component-state-matrix" / "SKILL.md")
        at_root = re.search(r"resolves `--pad-card` to (\d+)px", text).group(1)
        below = re.search(r"yields the unchanged (\d+)px", text).group(1)
        self.assertEqual(at_root, below)

    def test_rules_are_cited_under_their_own_numbers(self):
        coverage = read(SKILLS / "component-state-matrix" / "references" / "state-coverage.md")
        self.assertNotIn("Law-8 problem", coverage)            # Law 8 is the keyboard
        contract = read(STUDIO / "references" / "token-contract.md")
        self.assertNotIn("3:1 large text and UI components (SC 1.4.11)", contract)   # 1.4.3

    def test_the_screen_reader_pairing_matches_webaim(self):
        """WebAIM survey #10 (Dec 2023 - Jan 2024): JAWS + Chrome 24.7%,
        NVDA + Chrome 21.3%, NVDA + Firefox 10.0%."""
        text = read(A11Y / "references" / "manual-protocol.md")
        self.assertNotIn("closest to what a large share of users run", text)
        self.assertRegex(text, r"\*\*NVDA \+ Chrome\*\*[^|]*\|[^|]*21\.3%")

    def test_the_proof_sheet_marks_are_legible(self):
        """The generated sheet set white on --bg-success: 3.24:1 at 12px."""
        import importlib.util
        import sys
        own = pathlib.Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "wds_facts_check_roles", own / "skills" / "web-design-studio" / "scripts" / "check_roles.py")
        roles = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = roles
        spec.loader.exec_module(roles)
        source = read(SKILLS / "component-state-matrix" / "scripts" / "generate_matrix.py")
        marks = re.findall(r"\.msheet__mark--(\w+)\s*\{\s*background:\s*var\((--[\w-]+)\);\s*"
                           r"color:\s*var\((--[\w-]+)\);", source)
        self.assertEqual(len(marks), 3)
        pairs = [{"fg": fg, "bg": bg, "min": 4.5, "scopes": ["light", "dark"]}
                 for _, bg, fg in marks]
        tokens = read(STUDIO / "assets" / "starter" / "styles" / "tokens.css")
        for result in roles.check(tokens, pairs):
            with self.subTest(fg=result["fg"], bg=result["bg"], scope=result["scope"]):
                self.assertTrue(result["ok"], result)


LAYOUT_SCENARIO = r"""
const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
await page.goto(pathToFileURL(process.argv[2]).href);
const result = await page.evaluate(() => {
  const r = (id) => document.getElementById(id).getBoundingClientRect();
  return {
    fixedAt: [r('fixed').left, r('fixed').top],
    marginInside: r('child').top - r('box').top,
    subgridGap: r('b').top - r('a').bottom,
    important: ['imp', 'imp2'].map((id) => getComputedStyle(document.getElementById(id)).color),
  };
});
console.log(JSON.stringify(result));
await browser.close();
"""


@unittest.skipUnless(NODE and a11y_modules(), "needs node plus WDS_NODE_MODULES pointing at "
                                               "playwright")
class LayoutInABrowser(TempDirTest):
    """SS-A11 and SS-A16, measured."""

    def test_containers_and_subgrids_behave_as_the_docs_now_say(self):
        from test_starter_css import PROBE
        import subprocess
        from wds_support import env
        page = self.write("layout.html", """<!doctype html><title>t</title>
<body style="margin:0">
<div style="container-type:inline-size; margin:100px; width:300px">
  <div id="fixed" style="position:fixed; top:0; left:0; width:10px; height:10px"></div></div>
<div style="padding-top:1px"><div id="box" style="container-type:inline-size">
  <p id="child" style="margin:20px 0 0">x</p></div></div>
<div style="display:grid; grid-template-rows:repeat(3, auto); row-gap:40px">
  <div style="display:grid; grid-template-rows:subgrid; grid-row:span 3; row-gap:8px">
    <div id="a">a</div><div id="b">b</div><div>c</div></div></div>
<style>@layer vendor, components;
@layer vendor { #imp, #imp2 { color: rgb(255, 0, 0) !important; } }
@layer components { #imp { color: rgb(0, 0, 255) !important; } #imp2 { color: rgb(0, 0, 255); } }</style>
<p id="imp">x</p><p id="imp2">y</p>
</body>""")
        probe = self.write("layout.mjs", PROBE.split("const page =")[0] + LAYOUT_SCENARIO)
        proc = subprocess.run([NODE, str(probe), str(page)], capture_output=True, timeout=240,
                              env=env(NODE_PATH=a11y_modules()))
        if proc.returncode == 3:
            self.skipTest(output(proc))
        self.assertEqual(proc.returncode, 0, output(proc))
        seen = json.loads(proc.stdout.decode("utf-8").strip().splitlines()[-1])
        self.assertEqual(seen["fixedAt"], [0, 0], "a fixed child is placed against the viewport")
        self.assertEqual(seen["marginInside"], 20, "a container stops margin collapse")
        self.assertEqual(seen["subgridGap"], 8, "a subgrid's own row-gap applies")
        # LC-A16: an !important in the lowest layer beats everything above it.
        self.assertEqual(seen["important"], ["rgb(255, 0, 0)", "rgb(255, 0, 0)"])


class GmailStyleCeiling(TempDirTest):
    """DL-A16: Gmail counts every <style> element together and removes each
    element that crosses 16,384 bytes, and every one after it
    (hteumeuleu/email-bugs#90). The build emitted one block, so a retained
    block over the ceiling lost all of its CSS, not "the excess"."""

    CEILING = 16_384

    def test_a_retained_block_over_the_ceiling_is_split_in_order(self):
        from wds_support import run_py
        n = 700
        css = "".join(f"@media (max-width: 600px) {{ .c{i} {{ padding-top: 4px !important; }} }}\n"
                      for i in range(n))
        cells = "".join(f'<td class="c{i}">x</td>' for i in range(n))
        src = self.write("big.html", '<!doctype html><html lang="en"><head><title>t</title>'
                                     f'<style>{css}</style></head><body><table role="presentation">'
                                     f'<tr>{cells}</tr></table></body></html>')
        proc = run_py("email-template-system", "build_email", src, "-o", self.tmp / "out.html",
                      "-q", cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        html = (self.tmp / "out.html").read_text(encoding="utf-8")
        blocks = [b.encode("utf-8") for b in re.findall(r"<style[^>]*>(.*?)</style>", html, re.S)]
        self.assertGreater(sum(map(len, blocks)), self.CEILING, "the fixture must cross it")
        kept, total = [], 0
        for block in blocks:                       # what Gmail keeps: whole elements
            total += len(block)
            if total > self.CEILING:
                break
            kept.append(block)
        kept = b"".join(kept).replace(b" ", b"")
        self.assertIn(b".c0{", kept, "the first authored rules must survive")
        self.assertGreater(len(kept), self.CEILING // 2)

    def test_the_linter_says_what_gmail_removes(self):
        from wds_support import run_py
        style = "<style>" + "".join(f".c{i}{{color:#333333}}" for i in range(1200)) + "</style>"
        page = self.write("lint.html", '<!doctype html><html lang="en"><head><title>t</title>'
                                       f'{style}</head><body><p>hi</p></body></html>')
        proc = run_py("email-template-system", "lint_email", page, cwd=self.tmp)
        out = output(proc)
        self.assertNotIn("discards the excess wholesale", out)
        self.assertRegex(out, r"removes every <style> element")

    def test_no_doc_says_the_excess_is_what_goes(self):
        for md, text in suite_docs():
            with self.subTest(doc=md.name):
                self.assertNotRegex(text, r"(?i)(discards|drops) the excess wholesale|"
                                          r"excess is discarded wholesale")


EMAIL = SKILLS / "email-template-system"


class EmailClientFacts(TempDirTest):
    """DL-A15, DL-A17. caniemail's raw data (github.com/hteumeuleu/caniemail,
    _features/*.md), read 2026-09-25, latest tested entry per client:
    display:flex yes in Outlook for Mac 16.80, Gmail (Google accounts),
    Samsung 5.0, Thunderbird 60.5; no in classic Outlook and GANGA.
    display:grid yes in Outlook.com (2024-01), Gmail web (2026-03), Yahoo,
    Samsung, Thunderbird; no in classic Outlook and GANGA.
    prefers-color-scheme (2023-03-08) yes in Apple Mail, Outlook.com, Mac,
    iOS, Android, Samsung 6.1; no in Gmail, Yahoo, classic Outlook,
    Thunderbird 78.5 and 91.13."""

    CANIEMAIL = {
        ("`display:flex`", "Outlook Mac"): "✅", ("`display:flex`", "Samsung"): "✅",
        ("`display:flex`", "Thunderbird"): "✅", ("`display:flex`", "Gmail web"): "✅",
        ("`display:flex`", "GANGA"): "❌", ("`display:flex`", "Outlook Win (Word)"): "❌",
        ("`display:grid`", "Outlook Web"): "✅", ("`display:grid`", "Samsung"): "✅",
        ("`display:grid`", "Thunderbird"): "✅", ("`display:grid`", "GANGA"): "❌",
        ("`@media (prefers-color-scheme)`", "Outlook Web"): "✅",
        ("`@media (prefers-color-scheme)`", "Thunderbird"): "❌",
        ("`@media (prefers-color-scheme)`", "Gmail web"): "❌",
        ("`@media (prefers-color-scheme)`", "Apple Mail"): "✅",
    }

    def matrix(self):
        text = read(EMAIL / "references" / "email-client-matrix.md")
        header = next(line for line in text.splitlines() if line.startswith("| Feature |"))
        columns = [c.strip().strip("*") for c in header.strip("|").split("|")][1:]
        rows = {}
        for line in text.splitlines():
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) == len(columns) + 1 and cells[0].startswith("`"):
                rows[cells[0]] = {col: cell[:1] for col, cell in zip(columns, cells[1:])}
        return rows

    def test_the_matrix_agrees_with_caniemail(self):
        rows = self.matrix()
        for (feature, column), mark in self.CANIEMAIL.items():
            with self.subTest(feature=feature, client=column):
                self.assertEqual(rows[feature][column], mark[:1])

    def test_the_linter_blames_only_the_clients_that_drop_flex(self):
        source = read(EMAIL / "scripts" / "lint_email.py")
        props = source.split("UNSUPPORTED_PROPS = {", 1)[1].split("\n}", 1)[0]
        for value in ("flex", "grid"):
            blamed = re.search(rf'"{value}": \(((?:"[^"]*"\s*)+),', props).group(1)
            with self.subTest(value=value):
                self.assertNotRegex(blamed, r"Outlook Mac|Samsung|Thunderbird")

    def test_gone_quirks_and_dark_mode_claims_are_not_repeated(self):
        gone = re.compile(r"Thunderbird is Gecko and respects|respect \(Apple Mail, Thunderbird\)|"
                          r"Apple Mail, Thunderbird, Outlook Mac|three clients honour it|"
                          r"CSS rules after a comment are ignored on desktop webmail;|"
                          r"The Android app strips the first `<head>`")
        for md, text in suite_docs():
            with self.subTest(doc=md.name):
                self.assertNotRegex(text, gone)

    def test_outlook_dates_and_targets_are_current(self):
        """Microsoft: classic Outlook supported until at least 2029
        (learn.microsoft.com, updated 2026-02-23); Office 2021 retires
        2026-10-13, Office 2019 retired October 2025."""
        matrix = read(EMAIL / "references" / "email-client-matrix.md")
        self.assertNotIn("running the Word rendering engine in **October 2026**", matrix)
        self.assertIn("at least 2029", matrix)
        workflow = read(EMAIL / "references" / "email-workflow.md")
        self.assertNotIn("**Outlook 2019/2021, Windows", workflow)
        postmark = next(line for line in workflow.splitlines() if line.startswith("| **Postmark**"))
        self.assertNotIn("{{#if}}", postmark.split("no `{{#if}}`")[0])   # Mustachio has none

    def test_the_linter_cites_what_the_rules_say(self):
        from wds_support import run_py
        page = self.write("mail.html", '<!doctype html><html lang="en"><head><title>t</title>'
                                       '<meta name="viewport" content="width=device-width">'
                                       '</head><body><div style="display:none">Preheader</div>'
                                       '<table role="presentation"><tr><td>'
                                       '<a href="https://example.com/a">Read more</a>'
                                       '</td></tr></table></body></html>')
        out = output(run_py("email-template-system", "lint_email", page, "--transactional",
                            cwd=self.tmp))
        self.assertNotIn("SC 2.4.4, Level A", out)          # context passes 2.4.4
        self.assertIn("2.4.9", out)
        self.assertNotIn("still needs List-Unsubscribe headers", out)   # transactional: exempt


class FigmaFacts(unittest.TestCase):
    """LC-A7, read 2026-09-25 (developers.figma.com, help.figma.com,
    github.com/figma/mcp-server-guide). The Variables REST API is
    Enterprise-only. The Plugin API is not, and Figma's MCP server offers
    get_variable_defs, search_design_system and use_figma, which runs Plugin
    API code such as figma.variables.createVariableCollection. And
    GET /v1/files/:key/styles needs library_content:read, on any plan, and
    returns published styles only."""

    FIGMA = SKILLS / "figma-variables-sync"
    DOCS = (FIGMA / "SKILL.md", FIGMA / "references" / "figma-mapping.md")

    def test_scripting_is_not_said_to_need_enterprise(self):
        for path in self.DOCS:
            text = read(path)
            with self.subTest(doc=path.name):
                self.assertNotRegex(text, r"no scripting\s+(?:>\s*)?workaround|exactly two ways to get")
                self.assertIn("use_figma", text)
                self.assertIn("Plugin API", text)

    def test_the_styles_endpoint_is_published_only_and_ungated(self):
        for path in self.DOCS:
            text = re.sub(r"\s*\n>?\s*", " ", read(path))
            with self.subTest(doc=path.name):
                self.assertRegex(text, r"\*\*published\*\* styles only|published styles only")
                self.assertIn("library_content:read", text)


class FrameworkAndPackagingFacts(unittest.TestCase):
    """LC-A16 (rest), XC-A3."""

    def section(self):
        text = read(SKILLS / "design-token-migration" / "references" / "framework-migrations.md")
        return text.split("## 6. Bootstrap", 1)[1].split("\n## ", 1)[0]

    def test_the_layer_advice_warns_that_important_inverts_it(self):
        self.assertRegex(self.section(), r"inverts layer order")

    def test_an_mui_palette_of_custom_properties_turns_on_native_color(self):
        theme = re.search(r"createTheme\(\{(.*?)\}\);", self.section(), re.S).group(1)
        if "var(--" in theme:
            self.assertIn("nativeColor: true", theme)

    def test_no_skill_is_said_to_work_standalone(self):
        readme = read(SKILLS.parent / "README.md")
        self.assertNotRegex(readme, r"`\.skill` file works standalone")


class AxeTagAdvice(unittest.TestCase):
    """GT-A8: the docs recommended `--tags wcag2a,wcag2aa,wcag22aa`, which drops
    every WCAG 2.1 rule. Every tag list the a11y docs give that names a WCAG
    2.0 tag names 2.1's too, and the rules the docs say 2.1 holds carry those
    tags in the pinned axe-core."""

    def test_no_tag_list_drops_wcag_2_1(self):
        for path in sorted(A11Y.rglob("*")):
            if path.suffix not in (".md", ".mjs", ".py"):
                continue
            for tags in re.findall(r"--tags (\S+)", path.read_text(encoding="utf-8")):
                tags = set(tags.strip("`,.").split(","))
                if "wcag2a" in tags:
                    with self.subTest(file=path.name, tags=sorted(tags)):
                        self.assertLessEqual({"wcag21a", "wcag21aa"}, tags)

    @unittest.skipUnless(NODE and tool_modules("WDS_NODE_MODULES", "axe-core", node_path=True),
                         "needs node and axe-core")
    def test_the_rules_the_docs_name_carry_the_wcag_2_1_tags(self):
        doc = (A11Y / "references" / "automation-coverage.md").read_text(encoding="utf-8")
        named = {"autocomplete-valid": "wcag21aa", "avoid-inline-spacing": "wcag21aa",
                 "label-content-name-mismatch": "wcag21a", "css-orientation-lock": "wcag21aa"}
        for rule in named:
            self.assertIn(f"`{rule}`", doc)
        modules = tool_modules("WDS_NODE_MODULES", "axe-core", node_path=True)
        proc = run_node_script(
            "const axe = require('axe-core'); process.stdout.write(JSON.stringify("
            "Object.fromEntries(axe.getRules().map((r) => [r.ruleId, r.tags]))));", modules)
        tags = json.loads(proc.stdout)
        for rule, tag in named.items():
            with self.subTest(rule=rule):
                self.assertIn(tag, tags[rule])
        self.assertIn("experimental", tags["label-content-name-mismatch"])
        self.assertIn("experimental", tags["css-orientation-lock"])


def run_node_script(js, node_path):
    return subprocess.run([NODE, "-e", js], capture_output=True, check=True,
                          env=env(NODE_PATH=node_path))


if __name__ == "__main__":
    unittest.main()
