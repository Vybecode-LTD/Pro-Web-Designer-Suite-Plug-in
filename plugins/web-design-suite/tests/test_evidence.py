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
import pathlib
import re
import unittest

from wds_support import SKILLS

REGISTER = json.loads((pathlib.Path(__file__).resolve().parent / "fixtures" / "evidence.json")
                      .read_bytes())

# A sentence attributes a figure when it names a source, links out, or says
# where the number came from.
CUE = re.compile(r"WebAIM|Deque|\bGDS\b|Government Digital|Baymard|NN/g|Nielsen Norman|"
                 r"HTTP Archive|Web Almanac|CrUX|Chrome UX|caniemail|Litmus|Email on Acid|"
                 r"Akamai|Portent|Deloitte|Forrester|Gartner|McKinsey|Statista|Unbounce|HubSpot|"
                 r"\bCXL\b|Google|Microsoft|Apple|Cloudflare|\bstudy\b|\bstudies\b|\bsurvey\b|"
                 r"\breport(?:ed|s)?\b|\bresearch\b|\banalys[ie]s\b|\]\(https?://")
FIGURE = re.compile(
    r"(?<![\w.#(/-])("
    r"\d[\d,]*(?:\.\d+)?\s?[–-]\s?\d[\d,]*(?:\.\d+)?\s?%"          # a range: 37–41%
    r"|\d[\d,]*(?:\.\d+)?\s?%"                                      # a percentage
    r"|\d[\d,]*(?:\.\d+)?\+?\s(?:participants|respondents|pages|sites|audits|issues|users|"
    r"fixations|home pages|form fields|categories|tools|errors|people|studies))")


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


def registered_for(doc: str) -> set[str]:
    found = {norm(n["figure"]) for n in REGISTER["not_statistics"] if n["doc"] == doc}
    for entry in REGISTER["entries"]:
        if doc in entry["docs"]:
            found.update(values(entry))
    return found


class EvidenceRegister(unittest.TestCase):

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

    def test_no_entry_outlives_its_figure(self):
        for entry in REGISTER["entries"]:
            for doc in entry["docs"]:
                with self.subTest(figure=entry["figure"], doc=doc):
                    text = norm((SKILLS / doc).read_text(encoding="utf-8"))
                    self.assertTrue(any(v in text for v in values(entry)),
                                    "the doc no longer quotes it; update the register")


if __name__ == "__main__":
    unittest.main()
