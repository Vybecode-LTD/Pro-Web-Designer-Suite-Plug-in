"""perf-budget-gate's static gate on a bundled site (N50 part 1, P56).

Building webdesignersuite.com (Astro, from /new-system and /install-gate) ran
`perf_audit dist --src src`, the command /install-gate's workflow runs, and it
failed or warned where nothing was wrong:
- F2: `css-import` failed the starter's own index.css, whose @imports Vite
  inlines; the built CSS had none. A fresh project failed its first CI run.
- F3: `font-not-preloaded` matched a preload by the source file's name, so
  the preload of the bundler's hashed file never counted.
- F4: `missing-preconnect` took the page's own canonical URL for a
  third-party origin.
Each test has a control that still fails, so the rule is narrowed, not gone.
"""
from __future__ import annotations

import json
import unittest

from wds_support import TempDirTest, output, run_py

ENTRY = """@layer reset, tokens, base;
@import url("reset.css");
@import url("tokens.css");
"""

FACE_SRC = """@font-face {
  font-family: "Geist Sans";
  font-display: swap;
  src: url("../assets/fonts/geist-latin-wght-normal.woff2") format("woff2");
}
"""


def page(head: str = "", body: str = "<p>hi</p>") -> str:
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>t</title>'
            f'{head}</head><body><main>{body}</main></body></html>\n')


class TheGateOnABundledSite(TempDirTest):

    def audit(self, *args: str) -> dict:
        proc = run_py("perf-budget-gate", "perf_audit", *args, "--json", cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return json.loads(proc.stdout)

    @staticmethod
    def rules(report: dict, rule: str) -> list[str]:
        return [f["file"].replace("\\", "/") for f in report["findings"] if f["rule"] == rule]

    def test_a_source_import_the_bundler_inlined_passes(self):
        """F2: the source's @import is the bundler's to inline; only a shipped one costs a round trip."""
        self.write("src/styles/index.css", ENTRY)
        self.write("src/styles/reset.css", "@layer reset { html { box-sizing: border-box; } }\n")
        self.write("dist/_astro/index.a1b2c3d4.css", "@layer reset{html{box-sizing:border-box}}\n")
        self.write("dist/index.html", page('<link rel="stylesheet" href="/_astro/index.a1b2c3d4.css">'))
        self.assertEqual([], self.rules(self.audit("dist", "--src", "src"), "css-import"))

    def test_a_shipped_import_still_fails(self):
        """The control: a built stylesheet that kept its @import, and a site served from its source."""
        self.write("dist/legacy.css", '@import url("more.css");\n')
        self.write("dist/more.css", "p{margin:0}\n")
        self.write("dist/index.html", page('<link rel="stylesheet" href="/legacy.css">'))
        self.write("src/styles/index.css", ENTRY)
        built = self.rules(self.audit("dist", "--src", "src"), "css-import")
        self.assertEqual(["dist/legacy.css"], built)
        served = self.rules(self.audit("src"), "css-import")
        self.assertEqual(["src/styles/index.css"] * 2, served)

    def test_a_preload_of_the_hashed_font_counts(self):
        """F3: Vite's `name.HASH.woff2` and Rollup's `name-HASH.woff2` are the source's file.
        A dashed hash must hold a digit, so a weight's name is never read as one."""
        self.write("src/styles/fonts.css", FACE_SRC)
        for hashed in ("geist-latin-wght-normal.BgDaEnEv.woff2", "geist-latin-wght-normal-B9CIFXIH.woff2"):
            with self.subTest(hashed=hashed):
                self.write("dist/index.html", page(
                    f'<link rel="preload" href="/_astro/{hashed}" as="font" type="font/woff2" crossorigin>'))
                self.assertEqual([], self.rules(self.audit("dist", "--src", "src"), "font-not-preloaded"))

    def test_a_font_with_no_preload_still_warns(self):
        """The control: no preload, or a preload of another face whose name only shares a prefix."""
        self.write("src/styles/fonts.css", FACE_SRC)
        for head in ("", '<link rel="preload" href="/_astro/geist-latin-wght-bold.BgDaEnEv.woff2" '
                         'as="font" type="font/woff2" crossorigin>'):
            with self.subTest(head=head):
                self.write("dist/index.html", page(head))
                self.assertEqual(["<cross-file>"],
                                 self.rules(self.audit("dist", "--src", "src"), "font-not-preloaded"))
        # A weight or style is not a hash, dashed or dotted (Codex on #185): preloading
        # Inter-SemiBold, Inter.SemiBold or Inter.BoldItalic leaves Inter unpreloaded.
        self.write("src/styles/fonts.css", FACE_SRC.replace("geist-latin-wght-normal", "Inter"))
        for other in ("Inter-SemiBold", "Inter.SemiBold", "Inter.BoldItalic", "Inter.ExtraLight",
                      "Inter.SemiBold-Italic", "Inter.Bold_Italic"):
            with self.subTest(preload=other):
                self.write("dist/index.html", page(f'<link rel="preload" href="/f/{other}.woff2" '
                                                   'as="font" type="font/woff2" crossorigin>'))
                self.assertEqual(["<cross-file>"],
                                 self.rules(self.audit("dist", "--src", "src"), "font-not-preloaded"))

    def test_the_pages_own_origin_is_first_party(self):
        """F4: the canonical URL names the page's own origin, and a link that fetches nothing is no origin."""
        head = ('<link rel="canonical" href="https://example.com/">'
                '<link rel="alternate" type="application/rss+xml" href="https://feeds.example.org/rss">'
                '<link rel="me" href="https://social.example.net/@us">')
        self.write("dist/index.html", page(head, '<img src="https://example.com/a.png" alt="" width="1" height="1">'))
        report = self.audit("dist")
        self.assertEqual([], report["third_party_origins"])
        self.assertEqual([], self.rules(report, "missing-preconnect"))

    def test_another_origin_is_still_third_party(self):
        """The control: an asset from another host, even beside a canonical, is counted and wants a preconnect."""
        self.write("dist/index.html", page(
            '<link rel="canonical" href="https://example.com/">'
            '<link rel="stylesheet" href="https://fonts.example.org/css">',
            '<img src="https://cdn.example.net/a.png" alt="" width="1" height="1">'))
        report = self.audit("dist")
        self.assertEqual(["cdn.example.net", "fonts.example.org"], report["third_party_origins"])
        self.assertEqual(["<cross-file>"] * 2, self.rules(report, "missing-preconnect"))


def face(family: str, file: str, extra: str = "") -> str:
    return (f'@font-face {{ font-family: "{family}"; font-display: swap; unicode-range: U+0000-00FF;'
            f' src: url("/fonts/{file}") format("woff2");{extra} }}\n')


INTER_FALLBACK = ('@font-face { font-family: "Inter Fallback"; src: local(Arial); size-adjust: 107%;'
                  ' ascent-override: 90%; descent-override: 22%; line-gap-override: 0%; }\n')


class TheGateAsksWhatItsAdviceSays(TempDirTest):
    """P80 (the audit of 2026-10-28, PY-D): each rule clears when the page
    does what its own fix text says."""

    def audit(self, *args: str) -> dict:
        return TheGateOnABundledSite.audit(self, *args)

    @staticmethod
    def findings(report: dict, rule: str) -> list[str]:
        return [f["message"] for f in report["findings"] if f["rule"] == rule]

    def test_each_family_without_a_metric_fallback_is_named(self):
        """PY-D-13: once one family had a metric-matched fallback, the rule
        stopped, so a display face with none passed."""
        self.write("dist/fonts.css", face("Inter", "inter.woff2") + INTER_FALLBACK
                   + face("Fraunces", "fraunces.woff2") + face("Fraunces", "fraunces-italic.woff2",
                                                               " font-style: italic;"))
        self.write("dist/index.html", page('<link rel="stylesheet" href="/fonts.css">'))
        found = self.findings(self.audit("dist"), "font-no-metric-fallback")
        self.assertEqual(1, len(found), found)
        self.assertIn("Fraunces", found[0])

    def test_one_preloaded_face_is_what_the_advice_asks(self):
        """PY-D-14: the fix says to preload the ONE face above the fold, and
        the rule warned for every other face, so the advice failed --strict."""
        self.write("dist/fonts.css", face("Inter", "inter.woff2") + face("Fraunces", "fraunces.woff2"))
        preload = '<link rel="preload" href="/fonts/inter.woff2" as="font" type="font/woff2" crossorigin>'
        self.write("dist/index.html", page(preload + '<link rel="stylesheet" href="/fonts.css">'))
        self.assertEqual([], self.findings(self.audit("dist"), "font-not-preloaded"))
        # The control: with no face preloaded, one warning names them all.
        self.write("dist/index.html", page('<link rel="stylesheet" href="/fonts.css">'))
        found = self.findings(self.audit("dist"), "font-not-preloaded")
        self.assertEqual(1, len(found), found)
        self.assertIn("Inter", found[0])
        self.assertIn("Fraunces", found[0])

    def test_an_aspect_ratio_in_css_reserves_the_box(self):
        """PY-D-15: the fix says the attributes or `aspect-ratio` in CSS, and
        only an inline style's counted."""
        self.write("dist/site.css", ".avatar { aspect-ratio: 1; width: 48px; }\n"
                                    "img.cover { aspect-ratio: 16 / 9; }\n.loose { aspect-ratio: auto; }\n")
        self.write("dist/index.html", page(
            '<link rel="stylesheet" href="/site.css">',
            '<img class="avatar" src="a.png" alt="" fetchpriority="high">'
            '<img class="cover" src="c.png" alt="">'
            '<img class="loose" src="l.png" alt=""><img class="other" src="o.png" alt="">'))
        found = self.findings(self.audit("dist"), "img-no-dimensions")
        self.assertEqual(["`<img>` has no width/height: l.png.", "`<img>` has no width/height: o.png."],
                         sorted(found))

    def test_a_ratio_the_static_pass_cannot_place_reserves_nothing(self):
        """Codex on #242: `.card img` read as every img, and `img:not(.logo)`
        as `.logo`, cleared the error for images no rule reaches. Only a
        selector of one compound counts, and every class it names."""
        self.write("dist/site.css", ".card img { aspect-ratio: 1; }\nimg:not(.logo) { aspect-ratio: 1; }\n"
                                    ".thumb:hover { aspect-ratio: 1; }\n.a.b { aspect-ratio: 1; }\n"
                                    "img[data-x] { aspect-ratio: 1; }\n.hero, #banner { aspect-ratio: 2; }\n")
        self.write("dist/index.html", page(
            '<link rel="stylesheet" href="/site.css">',
            '<img src="bare.png" alt=""><img class="logo" src="logo.png" alt="">'
            '<img class="thumb" src="thumb.png" alt=""><img class="a" src="a.png" alt="">'
            '<img class="a b" src="ab.png" alt=""><img class="hero" src="hero.png" alt="">'
            '<img id="banner" src="banner.png" alt=""><img class="banner" src="cls.png" alt="">'))
        found = sorted(m.rsplit(": ", 1)[1] for m in self.findings(self.audit("dist"), "img-no-dimensions"))
        self.assertEqual(["a.png.", "bare.png.", "cls.png.", "logo.png.", "thumb.png."], found)

    def test_a_category_empty_at_the_baseline_has_its_growth_checked(self):
        """PY-D-18: a category whose baseline was 0 was skipped, so the first
        font a change added could grow without limit."""
        self.write("perf-budget.json", json.dumps({"$schema": "perf-budget-gate/1",
                                                   "growth": {"font_pct": 10}}))
        self.write("baseline.json", json.dumps({"$schema": "perf-budget-gate/baseline/1", "findings": [],
                                                "totals": {"bytes": {"total": 500, "font": 0}, "requests": {}}}))
        self.write("dist/index.html", page())
        self.write("dist/fonts/new.woff2", b"wOF2" + bytes(2000))
        report = self.audit("dist", "--budget", "perf-budget.json", "--baseline", "baseline.json")
        found = self.findings(report, "growth-font")
        self.assertEqual(1, len(found), report["findings"])
        self.assertIn("from 0", found[0])


if __name__ == "__main__":
    unittest.main()
