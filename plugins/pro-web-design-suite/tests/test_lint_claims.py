"""lint_claims.py, the claims a page makes and the devices that press them (P43).

Gaps closed (4.0.0):
- PS-C6, PS-B6: the critique gate had no claims layer, and nothing read
  what a page says: a countdown that restarts on every visit, a newsletter
  box ticked in advance, a stock count made with Math.random() or an
  unsourced "47% faster" passed every gate in the suite.

Each rule fires on its case and is quiet on a control beside it, and the
worked example's page, the skill's own, reads clean.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import unittest

from wds_support import SKILLS, TempDirTest, output, run_py

LANDING = SKILLS / "landing-page-conversion"
GATE = SKILLS / "design-critique-gate"


def lint_module():
    spec = importlib.util.spec_from_file_location("wds_lint_claims", LANDING / "scripts" / "lint_claims.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module                    # a dataclass looks its module up while it is built
    spec.loader.exec_module(module)
    return module


def page(body: str, script: str = "") -> str:
    return (f'<!doctype html><html lang="en"><body><main>\n{body}\n</main>'
            + (f"\n<script>\n{script}\n</script>" if script else "") + "\n</body></html>\n")


class LintClaims(TempDirTest):

    def lint(self, text: str, *args, name: str = "page.html"):
        self.write(name, text)
        proc = run_py("landing-page-conversion", "lint_claims", name, "--json", *args, cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return proc.returncode, json.loads(proc.stdout)["findings"]

    def rules(self, text: str, name: str = "page.html") -> list[str]:
        return [f["rule"] for f in self.lint(text, name=name)[1]]

    def test_each_rule_fires_on_its_case_and_not_on_its_control(self):
        cases = {
            "pre-checked-opt-in": (
                '<label><input type="checkbox" name="newsletter" checked> Send me offers</label>',
                '<label><input type="checkbox" name="newsletter"> Send me offers</label>'
                '<label><input type="checkbox" name="remember" checked> Remember me</label>'),
            "load-time-countdown": (
                page("<p>Offer ends soon</p>", "const offerEnds = Date.now() + 15 * 60 * 1000;"),
                page("<p>Offer ends 31 October</p>",
                     'document.cookie = "a=1; expires=" + new Date(Date.now() + 864e5).toUTCString();')),
            "invented-scarcity": (
                page("<p id=v></p>", "const viewing = Math.floor(Math.random() * 20); // people viewing"),
                page("<p id=v></p>", "const id = Math.random().toString(36);")),
            "scarcity-claim": ("<p>Only 3 left at this price.</p>", "<p>Only {stock} left.</p>"),
            "unsourced-percentage": ("<p>It makes mixing 47% faster.</p>",
                                     '<p>It makes mixing 47% faster (<a href="/method">method</a>).</p>'
                                     "<p>Save 20% this week.</p>"),
            "struck-price": ("<p><s>£49</s> £29</p>", "<p><s>the old way</s> the new way</p>"),
            "autocomplete-off": ('<input type="email" name="email" autocomplete="off">',
                                 '<input type="search" name="q" autocomplete="off">'),
            "lazy-first-image": ('<img src="hero.avif" loading="lazy" alt="">',
                                 '<img src="hero.avif" alt=""><img src="b.avif" loading="lazy" alt="">'),
            "two-filled-ctas": (
                '<section class="hero"><a class="cta" href="/buy">Buy</a><a class="cta" href="/try">Try</a></section>',
                '<header><a class="cta" href="/login">Log in</a></header>'
                '<section class="hero"><a class="cta" href="/buy">Buy</a>'
                '<a class="cta cta--secondary" href="/try">Try</a></section>'),
            "mismatched-cta-labels": (
                '<a class="cta" href="/buy">Buy now</a><a class="cta" href="/buy">Get it now</a>',
                '<a class="cta" href="/buy">Buy now</a><a class="cta" href="/buy">Buy now</a>'),
        }
        for rule, (bad, good) in cases.items():
            with self.subTest(rule=rule):
                self.assertIn(rule, self.rules(bad if bad.startswith("<!doctype") else page(bad)))
                self.assertNotIn(rule, self.rules(good if good.startswith("<!doctype") else page(good)))

    def test_a_countdown_seeded_on_every_visit_is_one_too(self):
        script = "let secondsLeft = 900;\nsetInterval(() => { secondsLeft--; }, 1000);"
        self.assertIn("load-time-countdown", self.rules(page("<p id=t></p>", script)))
        self.assertNotIn("load-time-countdown", self.rules(page("<p id=t></p>", "let secondsLeft = 900;")))

    def test_jsx_vue_and_svelte_spell_a_ticked_box_their_own_way(self):
        for name, box in (("Form.jsx", '<input type="checkbox" name="marketing" defaultChecked />'),
                          ("Form.tsx", '<input type="checkbox" name="marketing" checked={true} />'),
                          ("Form.vue", '<template><input type="checkbox" name="marketing" :checked="true"></template>'),
                          ("Form.svelte", '<input type="checkbox" name="marketing" checked>'),
                          ("plain.html", '<input type="checkbox" name="marketing" checked="">')):
            with self.subTest(name=name):
                self.assertIn("pre-checked-opt-in", self.rules(box, name=name))
        self.assertNotIn("pre-checked-opt-in",
                         self.rules('<input type="checkbox" name="marketing" checked={false} />', name="Off.jsx"))

    def test_a_bound_box_is_ticked_only_by_a_literal_true(self):
        """Codex on #192: `checked={marketingEnabled}` and Vue's
        `:checked="isOptedIn"` are state the code sets, not a box ticked in
        advance; HTML's bare `checked` and a literal `true` binding are."""
        for name, box, ticked in (("State.jsx", 'checked={marketingEnabled}', False),
                                  ("Default.jsx", 'defaultChecked={optedIn}', False),
                                  ("State.vue", ':checked="isOptedIn"', False),
                                  ("Bind.vue", 'v-bind:checked="isOptedIn"', False),
                                  ("True.vue", ':checked="true"', True),
                                  ("True.jsx", 'checked={true}', True),
                                  ("plain.html", 'checked', True)):
            with self.subTest(name=name, box=box):
                markup = f'<input type="checkbox" name="marketing" {box}>'
                if name.endswith(".vue"):
                    markup = f"<template>{markup}</template>"
                self.assertEqual(ticked, "pre-checked-opt-in" in self.rules(markup, name=name))

    def test_only_a_decrement_the_interval_runs_is_a_countdown(self):
        """Codex on #192: an item count decremented when a row is removed,
        beside an unrelated refresh interval, is not a countdown; a named
        callback that decrements the seed is."""
        unrelated = ("let itemCount = 10;\nfunction remove() { itemCount--; }\n"
                     "setInterval(refresh, 60000);\nfunction refresh() { fetch('/s'); }")
        self.assertNotIn("load-time-countdown", self.rules(page("<p id=t></p>", unrelated)))
        named = "let secondsLeft = 900;\nfunction tick() { secondsLeft -= 1; }\nsetInterval(tick, 1000);"
        self.assertIn("load-time-countdown", self.rules(page("<p id=t></p>", named)))
        arrow = "let minutesLeft = 15;\nconst tick = () => { --minutesLeft; };\nsetInterval(tick, 60000);"
        self.assertIn("load-time-countdown", self.rules(page("<p id=t></p>", arrow)))

    def test_a_jsx_handler_does_not_leak_into_a_label(self):
        """Codex on #192: HTMLParser read the `>` of `=>` as the end of the
        tag, so `onClick={() => track('top')}` became the link's text, and
        two links both labelled "Buy" read as two labels for /buy."""
        jsx = ('<a className="cta" href="/buy" onClick={() => track(\'top\')}>Buy</a>\n'
               '<a className="cta cta--secondary" href="/buy" onClick={() => track(\'bottom\')}>Buy</a>')
        self.assertNotIn("mismatched-cta-labels", self.rules(jsx, name="Page.jsx"))
        renamed = jsx.replace(">Buy</a>\n", ">Buy now</a>\n", 1)
        self.assertIn("mismatched-cta-labels", self.rules(renamed, name="Page.jsx"))

    def test_a_static_class_survives_a_vue_binding(self):
        """CodeRabbit on #192: `:class` overwrote `class`, so a Vue call to
        action lost `cta` and the rules that read it went quiet."""
        labels = ('<template><a class="cta" href="/buy" :class="{ wide: isWide }">Buy now</a>'
                  '<a class="cta" href="/buy">Get it</a></template>')
        self.assertIn("mismatched-cta-labels", self.rules(labels, name="Page.vue"))
        hero = ('<template><section class="hero"><a class="cta" href="/a" :class="size">A</a>'
                '<a class="cta" href="/b">B</a></section></template>')
        self.assertIn("two-filled-ctas", self.rules(hero, name="Hero.vue"))

    def test_a_percentage_with_no_paragraph_round_it_is_read(self):
        """CodeRabbit on #192: a figure in a section with no paragraph, or at
        a component's root, passed up to the root and was dropped; and a
        call to action beside it is not its source."""
        for name, markup in (("band.html", page('<section class="stats"><strong>47%</strong> faster</section>')),
                             ("Stat.jsx", "<span>47% faster</span>"),
                             ("cta.html", page('<section><strong>47%</strong> faster '
                                               '<a class="cta" href="/buy">Buy</a></section>'))):
            with self.subTest(name=name):
                self.assertIn("unsourced-percentage", self.rules(markup, name=name))
        sourced = page('<section><strong>47%</strong> faster (<a href="/method">method</a>)</section>')
        self.assertNotIn("unsourced-percentage", self.rules(sourced))

    def test_errors_fail_the_run_and_warnings_only_under_strict(self):
        code, found = self.lint(page('<input type="checkbox" name="newsletter" checked>'))
        self.assertEqual(1, code)
        self.assertEqual(["error"], [f["severity"] for f in found])
        code, found = self.lint(page("<p>It is 47% faster.</p>"))
        self.assertEqual((0, ["warning"]), (code, [f["severity"] for f in found]))
        self.assertEqual(1, self.lint(page("<p>It is 47% faster.</p>"), "--strict")[0])
        self.assertEqual((0, []), self.lint(page("<p>Hear it on your own files.</p>")))

    def test_a_pragma_switches_a_rule_off_for_a_line_or_a_file(self):
        line = ("<!-- lint-claims-ignore-next-line: scarcity-claim -- the stock API's count -->\n"
                "<p>Only 3 left.</p>")
        self.assertNotIn("scarcity-claim", self.rules(page(line)))
        self.assertIn("scarcity-claim", self.rules(page("<!-- unrelated -->\n<p>Only 3 left.</p>")))
        whole = "<!-- lint-claims-ignore-file: unsourced-percentage -- sourced in /method -->\n<p>47% faster</p>"
        self.assertNotIn("unsourced-percentage", self.rules(page(whole)))

    def test_a_folder_is_walked_and_dependencies_are_left_alone(self):
        self.write("src/index.html", page('<input type="checkbox" name="newsletter" checked>'))
        self.write("src/node_modules/x/index.html", page('<input type="checkbox" name="newsletter" checked>'))
        self.write("src/notes.txt", "Only 3 left")
        proc = run_py("landing-page-conversion", "lint_claims", "src", "--json", cwd=self.tmp)
        report = json.loads(proc.stdout)
        self.assertEqual(1, report["files"])
        self.assertEqual(["src/index.html"], [f["file"] for f in report["findings"]])

    def test_a_missing_path_or_nothing_to_read_is_a_bad_invocation(self):
        self.assertEqual(2, run_py("landing-page-conversion", "lint_claims", "nope", cwd=self.tmp).returncode)
        self.write("empty/readme.txt", "nothing here")
        self.assertEqual(2, run_py("landing-page-conversion", "lint_claims", "empty", cwd=self.tmp).returncode)

    def test_the_worked_example_reads_clean(self):
        """The skill's own page: one filled call to action in the hero, one
        label for /download, every figure sourced or a mechanism."""
        doc = (LANDING / "references" / "worked-example.md").read_text(encoding="utf-8")
        markup = "\n".join(re.findall(r"```html\n(.*?)```", doc, re.S))
        self.assertIn('class="cta"', markup)
        code, found = self.lint(markup, "--strict")
        self.assertEqual((0, []), (code, found))


class TheLintIsWhereTheSkillsSayItIs(unittest.TestCase):
    """conversion-audit.md §13 lists the script's rules at the script's
    severities; landing's Phase 6 and the critique gate's layers 1 and 8 run it."""

    def test_the_table_is_the_scripts_rules_at_their_severities(self):
        module = lint_module()
        audit = (LANDING / "references" / "conversion-audit.md").read_text(encoding="utf-8")
        table = audit.split("## 13. The claims lint", 1)[1]
        rows = dict(re.findall(r"^\| `([a-z-]+)` \| [^|]+ \| (error|warning) \|", table, re.M))
        self.assertEqual(set(module.FIX), set(rows))
        for rule, severity in rows.items():
            with self.subTest(rule=rule):
                self.assertEqual(module.SEVERITY.get(rule, module.WARNING), severity)

    def test_landing_and_the_critique_gate_run_it(self):
        skill = " ".join((LANDING / "SKILL.md").read_text(encoding="utf-8").split())
        self.assertIn("python -m scripts.lint_claims PATH # references/conversion-audit.md §13", skill)
        gate = " ".join((GATE / "SKILL.md").read_text(encoding="utf-8").split())
        self.assertIn("Every claim the page makes, and every device pressing it: failure-catalog L1-4.", gate)
        catalog = (GATE / "references" / "failure-catalog.md").read_text(encoding="utf-8")
        entry = " ".join(catalog.split("### L1-4 ·", 1)[1].split("\n---", 1)[0].split())
        self.assertIn("`lint_claims.py` on the page (its `conversion-audit.md` §13)", entry)
        l86 = " ".join(catalog.split("### L8-6 ·", 1)[1].split("\n---", 1)[0].split())
        self.assertIn("`lint_claims.py` (L1-4) for the countdowns and the ticked boxes", l86)


if __name__ == "__main__":
    unittest.main()
