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
