"""web-design-suite: every quoted figure is registered (phase 2, item 12).

tests/fixtures/evidence.json records each figure the docs quote from a study,
survey, vendor or regulator. For each one it holds what the figure measures,
the source and its URL, the date it was last checked, and the source's own
words. These tests keep the docs and the register in step. A figure cannot
enter the prose unregistered, and an entry cannot outlive its figure.

Regressions covered:
- C5, PS-C10: figures drifted with nothing to check them against. Baymard's
  "11.3 form fields against ~8" is not what its page says (14.88 against
  7-8). An Apple Mail Privacy Protection range ("15-20%") had no source at
  all.
"""
from __future__ import annotations

import json
import re
import unittest

from wds_support import PLUGIN, SKILLS

# The register of the plugin under test, beside the docs it describes, so a
# run against another copy (fail_before.py's WDS_PLUGIN_ROOT) reads its own
# (CodeRabbit on #154).
REGISTER = json.loads((PLUGIN / "tests" / "fixtures" / "evidence.json").read_bytes())

# A sentence attributes a figure when it names a source, links out, or says
# where the number came from.
CUE = re.compile(r"WebAIM|\bNEI\b|National Eye Institute|Deque|\bGDS\b|Government Digital|Baymard|NN/g|Nielsen Norman|"
                 r"HTTP Archive|Web Almanac|CrUX|Chrome UX|caniemail|Litmus|Email on Acid|"
                 r"Akamai|Portent|Deloitte|Forrester|Gartner|McKinsey|Statista|Unbounce|HubSpot|"
                 r"\bCXL\b|Google|Microsoft|Apple|Cloudflare|\bstudy\b|\bstudies\b|\bsurvey\b|"
                 r"\breport(?:ed|s)?\b|\bresearch\b|\banalys[ie]s\b|\]\(https?://")
FIGURE = re.compile(
    r"(?<![\w.#(/-])("
    r"\d[\d,]* in \d[\d,]*\s(?:men|women|people|adults|users)"  # a share: 1 in 12 men
    r"|\d[\d,]*(?:\.\d+)?\s?[–-]\s?\d[\d,]*(?:\.\d+)?\s?%"          # a range: 37–41%
    r"|\d[\d,]*(?:\.\d+)?\s?%"                                      # a percentage
    r"|\d[\d,]*(?:\.\d+)?\+?\s(?:participants|respondents|pages|sites|audits|issues|users|"
    r"fixations|home pages|form fields|categories|tools|errors|people|studies)"
    r"|\d[\d,]*(?:\.\d+)?\s?(?:bytes|KiB|KB|kB|kb|MB)\b"                 # a byte count: 102,400 bytes
    r"|\d[\d,]*-byte\b)")                                               # 16,384-byte
# A browser version, as the references quote support (D6): "Chrome 111",
# "Chrome/Edge 111+", "Chrome and Edge 117", "Safari on iOS 18.3",
# "Firefox from 144".
BROWSER_VERSION = re.compile(r"\b(?:Chrome|Chromium|Edge|Firefox|Safari|Opera|Samsung Internet)"
                             r"(?:/Edge| and Edge| on iOS)?\s(?:from\s)?\d+(?:\.\d+)?\+?")
WEB_FEATURES = "https://github.com/web-platform-dx/web-features/blob/main/features/"


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("–", "-").replace("—", "-")).strip()


def prose(text: str) -> str:
    """Markdown without code: fenced blocks and inline code are not prose."""
    text = re.sub(r"^```.*?^```", "", text, flags=re.S | re.M)
    return re.sub(r"`[^`\n]*`", "", text)


def docs():
    for md in sorted(SKILLS.glob("*/SKILL.md")) + sorted(SKILLS.glob("*/references/*.md")):
        if md.name != "token-contract.md":
            yield md.relative_to(SKILLS).as_posix(), md.read_text(encoding="utf-8")


def sentences(text: str):
    for para in re.split(r"\n\s*\n", prose(text)):
        yield from re.split(r"(?<=[.!?])\s+(?=[A-Z*(])|\n(?=\|)|\n(?=- )", para)


def values(entry) -> list[str]:
    return [norm(v) for v in [entry["figure"], *entry.get("also", [])]]


def numbers(value: str) -> list[str]:
    return [n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", value)]


def quoted(value: str, text: str) -> bool:
    """The value stands on its own in the text: "41%" is not quoted by
    "37-41%", nor "143" by "1,143", "143.5", "143%", "143-200" or "1/143",
    with or without spaces round the `-` or `/` (Codex on #154, twice)."""
    for m in re.finditer(rf"(?<![\w.,/-]){re.escape(value)}(?!\w|[.,]\d|\s?%|\s*[-/]\s*\d)", text):
        if not re.search(r"\d\s*[-/]\s*$", text[max(0, m.start() - 16):m.start()]):
            return True
    return False


def spellings(entry) -> list[str]:
    """The figure, and each `also` value that carries its numbers:
    "16,384-byte" spells "16,384 bytes". A companion figure from the same
    source ("19 categories" beside "143") is not a spelling of it."""
    figure, *also = values(entry)
    return [figure] + [v for v in also if numbers(v) == numbers(figure)]


def registered_for(doc: str) -> set[str]:
    found = {norm(n["figure"]) for n in REGISTER["not_statistics"] if n["doc"] == doc}
    for entry in REGISTER["entries"]:
        if doc in entry["docs"]:
            found.update(values(entry))
    return found


class EvidenceRegister(unittest.TestCase):

    def test_byte_counts_are_figures_and_gmails_limits_are_registered(self):
        """N36 (CodeRabbit on #59): the email docs quoted Gmail's 102,400-byte
        clipping threshold and its 16,384-byte <style> ceiling, FIGURE did not
        recognise a byte count, and neither figure was in the register."""
        for text, figure in (("clips at 102,400 bytes of HTML", "102,400 bytes"),
                             ("the 16,384-byte ceiling", "16,384-byte"),
                             ("limits <style> to 16 kB", "16 kB"),
                             ("adds 54 KB of HTML", "54 KB"),
                             ("more than 102kb, then Gmail", "102kb")):
            with self.subTest(text=text, figure=figure):
                self.assertEqual(FIGURE.findall(text), [figure], text)
        self.assertEqual(FIGURE.findall("a 48px-tall button, 100 × 1024, 4.5:1"), [])
        registered = {v for e in REGISTER["entries"] for v in values(e)}
        self.assertIn(norm("102 KB"), registered)
        self.assertIn(norm("16,384 bytes"), registered)
        for doc in ("email-template-system/SKILL.md",
                    "email-template-system/references/email-client-matrix.md",
                    "email-template-system/references/email-architecture.md",
                    "email-template-system/references/email-workflow.md"):
            with self.subTest(doc=doc):
                self.assertIn(norm("16,384-byte"), registered_for(doc))
                self.assertIn(norm("102 KB"), registered_for(doc))
                # The docs call the threshold what the sources call it, 102 KB,
                # and say the byte-exact figure is measured.
                text = (SKILLS / doc).read_text(encoding="utf-8")
                self.assertIn("102 KB", text, doc)
                self.assertRegex(text, r"measured[:,]? ?(?:at )?102,400 bytes|102,400 bytes is the measured value|\(102,400 bytes, measured\)", doc)
        # The scripts enforce what the register records: the <style> ceiling
        # is the registered figure, and the clipping constant is the measured
        # 102,400 the docs name beside the ESPs' 102 KB.
        style_entry = next(e for e in REGISTER["entries"] if e["figure"] == "16,384 bytes")
        style_bytes = int(re.sub(r"\D", "", style_entry["figure"]))
        for script in ("build_email", "lint_email"):
            with self.subTest(script=script):
                source = (SKILLS / "email-template-system" / "scripts" / f"{script}.py").read_text(encoding="utf-8")
                constants = dict(re.findall(r"^(GMAIL_\w+_BYTES) = ([\d_]+)", source, re.M))
                self.assertEqual(int(constants["GMAIL_STYLE_BYTES"].replace("_", "")), style_bytes, script)
                self.assertEqual(int(constants["GMAIL_CLIP_BYTES"].replace("_", "")), 102_400, script)

    def test_every_attributed_figure_is_registered(self):
        seen = 0
        for doc, text in docs():
            known = registered_for(doc)
            for sentence in sentences(text):
                if not CUE.search(sentence):
                    continue
                for figure in FIGURE.findall(sentence):
                    seen += 1
                    with self.subTest(doc=doc, figure=figure):
                        self.assertIn(norm(figure), known,
                                      "register it in tests/fixtures/evidence.json with its "
                                      "source, or list it under not_statistics: "
                                      + re.sub(r"\s+", " ", sentence)[:160])
        self.assertGreater(seen, 30)

    def test_a_registered_figure_is_registered_wherever_it_is_quoted(self):
        """Distinctive values (a decimal, a thousands comma, a "+") are
        recognised even where the sentence does not name the source."""
        distinctive = {}
        for entry in REGISTER["entries"]:
            for value in values(entry):
                if re.search(r"\d[.,]\d|\+", value):
                    distinctive.setdefault(value, set()).update(entry["docs"])
        for doc, text in docs():
            body = norm(prose(text))
            for value, where in distinctive.items():
                if re.search(rf"(?<![\w.]){re.escape(value)}(?![\w])", body):
                    with self.subTest(doc=doc, figure=value):
                        self.assertIn(doc, where)

    def test_every_entry_is_complete_and_its_quote_carries_its_numbers(self):
        for entry in REGISTER["entries"]:
            with self.subTest(figure=entry["figure"]):
                for field in ("claim", "source", "url", "checked", "quote", "docs"):
                    self.assertTrue(entry.get(field), field)
                self.assertRegex(entry["checked"], r"^\d{4}-\d{2}-\d{2}$")
                self.assertTrue(entry["url"].startswith("https://"))
                quote = entry["quote"].replace(",", "")
                for value in values(entry):
                    for number in re.findall(r"\d[\d,]*(?:\.\d+)?", value):
                        self.assertIn(number.replace(",", ""), quote)

    def test_a_figure_is_quoted_only_on_its_own(self):
        """The control for the two tests below: the old check, any value as
        a substring, kept "19 categories" alive on a bare "143"."""
        self.assertTrue(quoted("41%", norm("found **41%** of them")))
        self.assertTrue(quoted("13,000", "across ~13,000 pages."))
        self.assertTrue(quoted("143", norm("the page – 143 planted failures")))   # a dash, not a range
        for value, text in (("41%", "found 37–41% of them"), ("143", "1,143 issues"),
                            ("143", "143.5 issues"), ("143", "1430 issues"), ("143", "143% of it"),
                            ("143", "143 % of it"), ("143", "143-200 failures"), ("143", "143/200"),
                            ("143", "1/143 of it"), ("143", "a 2-143 range"), ("41%", "41%-43%"),
                            ("143", "143 - 200 failures"), ("143", "143 / 200"), ("143", "1 / 143"),
                            ("143", "a 2 – 143 range"), ("41%", "41% – 43%")):
            with self.subTest(value=value, text=text):
                self.assertFalse(quoted(value, norm(text)), text)
        entry = {"figure": "16,384 bytes", "also": ["16,384-byte", "16384 bytes", "16 kB"]}
        self.assertEqual(spellings(entry), ["16,384 bytes", "16,384-byte", "16384 bytes"])
        old = {"figure": "19 categories", "also": ["143"]}
        text = norm("the best single tool found 41% of 143 planted barriers")
        self.assertTrue(any(v in text for v in values(old)))
        self.assertFalse(any(quoted(v, text) for v in spellings(old)))

    def test_no_entry_outlives_its_figure(self):
        """T1 (audit, 2026-10-14): a companion number kept an entry alive.
        "19 categories" stayed listed for three docs that quote only "143",
        "37–41%" for three that quote "41%" or the range's ends apart, and
        "2,000+ audits" for a script that quotes only "13,000". Each doc
        must quote the figure itself, or a spelling of it."""
        for entry in REGISTER["entries"]:
            forms = spellings(entry)
            for doc in entry["docs"]:
                with self.subTest(figure=entry["figure"], doc=doc):
                    text = norm((SKILLS / doc).read_text(encoding="utf-8"))
                    self.assertTrue(any(quoted(v, text) for v in forms),
                                    "the doc no longer quotes the figure; take the doc "
                                    "off its list, and register what it does quote")

    def test_the_core_web_vitals_and_the_evals_floor_are_registered(self):
        """D6 (audit, 2026-10-14): budgets.md quoted the thresholds "verified
        against web.dev" and the README "Claude Code 2.1.269 or later" with no
        entry, and FIGURE reads no duration. Each is registered with its quote,
        so the entry tests above hold every doc that quotes it."""
        # Each from the page its url names (CodeRabbit on #160): the good
        # thresholds in the Web Vitals article's words, the poor in its table's.
        vitals, table = "https://web.dev/articles/vitals", "https://web.dev/articles/defining-core-web-vitals-thresholds"
        wanted = {"2.5 s": vitals, "200 ms": vitals, "≤ 0.1": vitals, "75th percentile": vitals,
                  "4 s": table, "500 ms": table, "> 0.25": table}
        for figure, url in wanted.items():
            with self.subTest(figure=figure):
                entry = next((e for e in REGISTER["entries"] if e["figure"] == figure), None)
                self.assertIsNotNone(entry)
                self.assertIn("perf-budget-gate/references/budgets.md", entry["docs"])
                self.assertEqual(url, entry["url"])
        floor = next((e for e in REGISTER["entries"] if e["figure"] == "2.1.269"), None)
        self.assertIsNotNone(floor)
        self.assertEqual(["../README.md"], floor["docs"])

    def test_every_browser_version_is_registered(self):
        """D6's rest (audit, 2026-10-14): the references quoted Baseline
        browser versions ("Chrome 111, Firefox 113, Safari 16.2") with no
        entry, and FIGURE reads no version. Each version a doc quotes stands
        inside a figure registered for that doc, re-read at web-features, or
        one listed under not_statistics."""
        self.assertEqual(BROWSER_VERSION.findall("Chrome/Edge 111+, Safari 15.4+, Firefox from 144, "
                                                 "Safari on iOS 18.3, Chrome and Edge 117"),
                         ["Chrome/Edge 111+", "Safari 15.4+", "Firefox from 144",
                          "Safari on iOS 18.3", "Chrome and Edge 117"])
        seen = 0
        for doc, text in docs():
            body = norm(prose(text))
            spans = [m.span() for value in registered_for(doc) for m in re.finditer(re.escape(value), body)]
            for m in BROWSER_VERSION.finditer(body):
                seen += 1
                with self.subTest(doc=doc, version=m.group()):
                    self.assertTrue(any(a <= m.start() and m.end() <= b for a, b in spans),
                                    "register the support line in tests/fixtures/evidence.json, re-read at "
                                    "web-features, or list it under not_statistics: "
                                    + body[max(0, m.start() - 80):m.end() + 40])
        self.assertGreater(seen, 40)
        # A support figure's source is web-features' own file for the feature.
        for entry in REGISTER["entries"]:
            if BROWSER_VERSION.search(entry["figure"]):
                with self.subTest(figure=entry["figure"]):
                    self.assertTrue(entry["url"].startswith(WEB_FEATURES), entry["url"])

    def test_no_companion_outlives_its_figure(self):
        """An `also` value is quoted, on its own, in at least one of its
        entry's docs."""
        for entry in REGISTER["entries"]:
            texts = [norm((SKILLS / doc).read_text(encoding="utf-8")) for doc in entry["docs"]]
            for value in values(entry)[1:]:
                with self.subTest(figure=entry["figure"], also=value):
                    self.assertTrue(any(quoted(value, text) for text in texts),
                                    "no listed doc quotes it; drop it from also")


if __name__ == "__main__":
    unittest.main()
