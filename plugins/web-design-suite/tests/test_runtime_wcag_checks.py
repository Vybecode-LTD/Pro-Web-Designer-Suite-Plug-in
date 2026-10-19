"""P35 part 1 (GT-B6): the checks the coverage table lists as drivable.

automation-coverage.md §3 named five mechanisms a tool can run that neither
gate ran: WCAG's text spacing injected and the clipping diffed (1.4.12); the
focused control against the fixed and sticky elements over it (2.4.11); a
description shown on hover or focus, held, hovered and dismissed (1.4.13);
the page with and without prefers-reduced-motion (the suite's policy,
runtime-checks.md §6); and text clipped at 200% and at 320px (1.4.4, 1.4.10).
a11y_runtime.mjs runs each now. Every check has a page that fails it and one
that passes, each run in the real browser; the browser tests skip unless
Node and Playwright are available.
"""
from __future__ import annotations

import json
import unittest

from test_browser_runtime import MODULES, only
from wds_support import NODE, PLUGIN, TempDirTest, output, run_node

HEAD = ("<!doctype html><html lang=en><head><meta charset=utf-8><title>Page</title>"
        "<style>body{{font:16px/1.2 sans-serif;color:#111;background:#fff}}{}</style></head>"
        "<body><main><h1>Page</h1>{}</main></body></html>")


def page(css: str, body: str) -> str:
    return HEAD.format(css, body)


@unittest.skipUnless(NODE and MODULES, "needs node plus WDS_NODE_MODULES pointing at "
                                       "playwright and axe-core")
class RuntimeCase(TempDirTest):

    def runtime(self, html: str, *checks: str) -> dict:
        path = self.write("page.html", html)
        proc = run_node("a11y-audit-runner", "a11y_runtime.mjs", "--file", path, "--json",
                        *only(*checks), cwd=self.tmp, env_changes={"NODE_PATH": MODULES},
                        timeout=300)
        if proc.returncode == 2 and b"browser" in proc.stderr.lower():
            self.skipTest("no usable browser: " + output(proc)[-200:])
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return json.loads(proc.stdout)

    def found(self, report: dict, rule: str) -> list:
        return [f for f in report["findings"] if f["rule"] == rule]


# Two lines at a line height of 1.2 fill a box 2.5em tall; at 1.5 they do not.
SUMMARY = "A card's summary<br>on two lines"
CARD = ".card{{width:15em;{}}}"


class TextSpacing(RuntimeCase):
    """1.4.12: the spacing a reader may set must not cut text off."""

    def test_a_fixed_height_box_that_hides_its_overflow_clips(self):
        report = self.runtime(page(CARD.format("height:2.5em;overflow:hidden"),
                                   f"<p class=card>{SUMMARY}</p>"), "spacing")
        clipped = self.found(report, "text-clipped-by-spacing")
        self.assertEqual(["html > body > main > p.card"], [f["selector"] for f in clipped], report["findings"])
        self.assertEqual(("1.4.12", "error"), (clipped[0]["sc"], clipped[0]["severity"]))
        self.assertIn("spacing", report["ran"])

    def test_a_fixed_height_box_that_shows_its_overflow_is_a_warning(self):
        report = self.runtime(page(CARD.format("height:2.5em"),
                                   f"<p class=card>{SUMMARY}</p>"), "spacing")
        self.assertFalse(self.found(report, "text-clipped-by-spacing"))
        spilt = self.found(report, "text-overflows-with-spacing")
        self.assertEqual(["warning"], [f["severity"] for f in spilt], report["findings"])

    def test_a_box_that_grows_and_a_box_clipped_already_pass(self):
        """A box that grows with its text loses nothing; one that clipped
        before the spacing (a visually hidden label, a carousel) is not the
        spacing's doing."""
        sr = ("<span style='position:absolute;width:1px;height:1px;overflow:hidden;"
              "clip:rect(0 0 0 0)'>Opens in a new tab</span>")
        already = ("<div style='width:10em;overflow:hidden;white-space:nowrap'>"
                   "A line far too long for its box before any spacing at all</div>")
        report = self.runtime(page(CARD.format("min-height:2.5em;overflow:hidden"),
                                   f"<p class=card>{SUMMARY}</p><p>Link{sr}</p>{already}"),
                              "spacing")
        self.assertEqual([], [f for f in report["findings"] if f["check"] == "spacing"])

    def test_the_spacing_is_taken_out_again(self):
        """The checks after it see the page as it was: reflow at 200% finds
        nothing on a page that fits."""
        report = self.runtime(page(CARD.format("height:2.5em;overflow:hidden"),
                                   f"<p class=card>{SUMMARY}</p>"), "spacing", "reflow")
        self.assertFalse([f for f in report["findings"] if f["check"] == "reflow"],
                         report["findings"])


# A nav row that fits at 1280px and wraps onto a hidden second row at 640px.
NAV = ("<ul class=nav>" + "".join(f"<li><a href='#{w}'>{w}</a></li>" for w in (
    "Products", "Pricing", "Customers", "Resources", "Company", "Careers", "Support",
    "Contact")) + "</ul>")
NAV_CSS = (".nav{{display:flex;flex-wrap:wrap;gap:1.5em;list-style:none;padding:0;"
           "margin:0;{}}}")


class ClippedAtZoom(RuntimeCase):
    """1.4.4 and 1.4.10: text cut off at 200% or at 320px is lost content."""

    def test_a_row_that_wraps_into_a_hidden_line_is_clipped(self):
        report = self.runtime(page(NAV_CSS.format("height:1.4em;overflow:hidden"), NAV), "reflow")
        at200 = self.found(report, "text-clipped-at-200-percent")
        at320 = self.found(report, "text-clipped-at-320px")
        self.assertEqual(["html > body > main > ul.nav"], [f["selector"] for f in at200], report["findings"])
        self.assertEqual(("1.4.4", "error"), (at200[0]["sc"], at200[0]["severity"]))
        self.assertEqual(["html > body > main > ul.nav"], [f["selector"] for f in at320])
        self.assertEqual("1.4.10", at320[0]["sc"])

    def test_a_row_that_grows_passes(self):
        report = self.runtime(page(NAV_CSS.format("min-height:1.4em;overflow:hidden"), NAV),
                              "reflow")
        self.assertEqual([], report["findings"])


STOPS = ("<header class=bar><a href='#home'>Home</a></header>"
         "<p><a href='#first'>First link</a></p>" +
         "".join(f"<p style='margin:300px 0'><a href='#m{i}'>Middle link {i}</a></p>"
                 for i in range(4)) +
         "<p><a href='#last'>Last link</a></p>"
         "<div class=banner>We use cookies. <button type=button>OK</button></div>")
STOPS_CSS = ("body{{margin:0;{}}} .bar{{position:fixed;top:0;left:0;right:0;height:160px;"
             "background:#222}} .bar a{{color:#fff}} .banner{{position:fixed;bottom:0;"
             "left:0;right:0;height:120px;background:#eee}} {}")


FIRST = "html > body > main > p:nth-of-type(1) > a"
LAST = "html > body > main > p:nth-of-type(6) > a"


class FocusNotObscured(RuntimeCase):
    """2.4.11: a fixed header or banner must not hide the whole focused control."""

    def test_the_first_and_last_links_are_hidden_under_the_bars(self):
        report = self.runtime(page(STOPS_CSS.format("", ""), STOPS), "obscured")
        hidden = {f["selector"]: f for f in self.found(report, "focus-obscured")}
        self.assertIn(FIRST, hidden, report["findings"])
        self.assertIn(LAST, hidden)
        self.assertEqual(("2.4.11", "error"), (hidden[FIRST]["sc"],
                                               hidden[FIRST]["severity"]))
        self.assertEqual(["html > body > main > header.bar"], hidden[FIRST]["covers"])
        self.assertEqual(["html > body > main > div.banner"], hidden[LAST]["covers"])
        # A control in the bar is the bar's own surface, never hidden by it.
        self.assertNotIn("html > body > main > header.bar > a", hidden)

    def test_a_cover_that_lets_the_pointer_through_still_paints_over(self):
        report = self.runtime(page(STOPS_CSS.format("", ".bar{pointer-events:none}"), STOPS),
                              "obscured")
        self.assertIn(FIRST,
                      [f["selector"] for f in self.found(report, "focus-obscured")],
                      report["findings"])

    def test_padding_and_scroll_padding_as_tall_as_the_bars_pass(self):
        report = self.runtime(page(STOPS_CSS.format(
            "padding:160px 0 120px", "html{scroll-padding:160px 0 120px}"), STOPS), "obscured")
        self.assertEqual([], [f for f in report["findings"] if f["check"] == "obscured"])


TIP_CSS = (".wrap{{position:relative;display:inline-block}} .tip{{display:none;"
           "position:absolute;left:0;top:{};width:16em;padding:.5em;background:#fff;border:1px solid;"
           "z-index:1}} {}")
TIP_BODY = ("<p>Delivery <span class=wrap><button type=button aria-describedby=tip>?</button>"
            "<span id=tip role=tooltip class=tip>Free on orders over fifty pounds</span>"
            "</span></p><p>The paragraph the description lies over when it shows.</p>{}")
# Shows while the pointer is over the wrapper or focus is inside it, and Esc
# hides it until the pointer leaves or focus moves on.
DISMISS = ("<script>document.addEventListener('keydown', (e) => { if (e.key === 'Escape') "
           "document.querySelectorAll('.wrap').forEach((w) => w.classList.add('dismissed')); });"
           "document.querySelectorAll('.wrap').forEach((w) => { "
           "w.addEventListener('mouseleave', () => w.classList.remove('dismissed'));"
           "w.addEventListener('focusout', () => w.classList.remove('dismissed')); });</script>")
GOOD = ".wrap:hover .tip,.wrap:focus-within .tip{display:block} .wrap.dismissed .tip{display:none}"


class ContentOnHoverOrFocus(RuntimeCase):
    """1.4.13: what appears on hover or focus is dismissible, hoverable and
    persistent."""

    def test_a_tip_shown_on_the_button_alone_across_a_gap_fails_twice(self):
        report = self.runtime(page(TIP_CSS.format(
            "calc(100% + 1.5em)", "button:hover+.tip,button:focus+.tip{display:block}"),
            TIP_BODY.format("")), "hover")
        rules = sorted(f["rule"] for f in report["findings"] if f["check"] == "hover")
        self.assertEqual(["hover-content-not-dismissible", "hover-content-not-hoverable"], rules,
                         report["findings"])
        self.assertEqual({("1.4.13", "error", "hover")},
                         {(f["sc"], f["severity"], f["trigger"]) for f in report["findings"]})

    def test_a_tip_that_times_out_is_not_persistent(self):
        timer = ("<script>const b = document.querySelector('button'), t = "
                 "document.getElementById('tip'); b.addEventListener('mouseenter', () => { "
                 "t.style.display = 'block'; setTimeout(() => { t.style.display = ''; }, 1000); "
                 "});</script>")
        report = self.runtime(page(TIP_CSS.format("100%", ""), TIP_BODY.format(timer)), "hover")
        self.assertEqual(["hover-content-not-persistent"],
                         [f["rule"] for f in report["findings"] if f["check"] == "hover"],
                         report["findings"])

    def test_a_tip_on_focus_only_must_close_on_esc(self):
        report = self.runtime(page(TIP_CSS.format(
            "100%", "button:focus+.tip{display:block}"), TIP_BODY.format("")), "hover")
        found = [(f["rule"], f["trigger"]) for f in report["findings"] if f["check"] == "hover"]
        self.assertEqual([("hover-content-not-dismissible", "focus")], found, report["findings"])

    def test_a_tip_on_the_wrapper_that_esc_closes_passes(self):
        report = self.runtime(page(TIP_CSS.format("100%", GOOD), TIP_BODY.format(DISMISS)),
                              "hover")
        self.assertEqual([], [f for f in report["findings"] if f["check"] == "hover"])

    def test_a_tip_that_covers_nothing_need_not_close(self):
        """Dismissible applies to content that covers something: a tip placed
        in empty space is exempt, as is the browser's own `title`."""
        report = self.runtime(page(TIP_CSS.format(
            "0", ".wrap:focus-within .tip{display:block;left:30em}"),
            TIP_BODY.format("<p title='A title'>Titled</p>")), "hover")
        self.assertEqual([], [f for f in report["findings"] if f["check"] == "hover"])


MOTION_CSS = ("@keyframes slide{{from{{transform:translateX(0)}}to{{transform:translateX(200px)}}}}"
              "@keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}"
              "@keyframes spin{{to{{transform:rotate(360deg)}}}}"
              ".slider{{animation:slide 2s ease-in-out infinite alternate}}"
              ".reveal{{opacity:0;animation:fade .3s forwards}}"
              ".spinner{{display:inline-block;width:20px;height:20px;border:3px solid #333;"
              "border-top-color:transparent;border-radius:50%;animation:spin 1s linear infinite}}"
              "@media (prefers-reduced-motion: reduce){{{}}}")
MOTION_BODY = ("<div class=slider>Sliding banner</div><p class=reveal>Revealed words</p>"
               "<div role=status aria-label=Loading><span class=spinner></span></div>")


class ReducedMotion(RuntimeCase):
    """The suite's policy (runtime-checks.md §6): motion reduced, nothing lost,
    and a busy loop still running."""

    def test_a_page_that_switches_off_the_wrong_things_fails_three_ways(self):
        report = self.runtime(page(MOTION_CSS.format(
            ".reveal{animation:none}.spinner{animation:none}"), MOTION_BODY), "motion")
        by = {f["rule"]: f for f in report["findings"] if f["check"] == "motion"}
        self.assertEqual({"motion-not-reduced", "content-hidden-under-reduced-motion",
                          "busy-indicator-stopped"}, set(by), report["findings"])
        self.assertIn("div.slider", by["motion-not-reduced"]["selector"])
        self.assertEqual("html > body > main > p.reveal", by["content-hidden-under-reduced-motion"]["selector"])
        self.assertIn("span.spinner", by["busy-indicator-stopped"]["selector"])
        self.assertEqual({"warning"}, {f["severity"] for f in by.values()})

    def test_a_page_that_reduces_motion_and_keeps_its_content_passes(self):
        report = self.runtime(page(MOTION_CSS.format(
            ".slider{animation:none}.reveal{animation:none;opacity:1}"), MOTION_BODY), "motion")
        self.assertEqual([], [f for f in report["findings"] if f["check"] == "motion"])

    def test_a_shorter_slide_counts_as_reduced(self):
        report = self.runtime(page(MOTION_CSS.format(
            ".slider{animation-duration:.6s}.reveal{animation:none;opacity:1}"), MOTION_BODY),
            "motion")
        self.assertEqual([], [f for f in report["findings"] if f["check"] == "motion"])


class TheChecksAreNamedAndCounted(TempDirTest):
    """Each check is skippable by name and counted by a budget key the
    references list."""

    def test_skip_names_and_budget_keys(self):
        script = (PLUGIN / "skills" / "a11y-audit-runner" / "scripts" / "a11y_runtime.mjs"
                  ).read_text(encoding="utf-8")
        scripts_md = (PLUGIN / "skills" / "a11y-audit-runner" / "references" / "scripts.md"
                      ).read_text(encoding="utf-8")
        for check in ("spacing", "obscured", "hover", "motion"):
            with self.subTest(check=check):
                self.assertIn(f"'{check}'", script.split("const ALL_CHECKS", 1)[1].split(";")[0])
                self.assertIn(f"`{check}`", scripts_md)
        for key in ("text_spacing_failures", "focus_obscured", "hover_content_failures",
                    "motion_not_reduced", "motion_content_hidden"):
            with self.subTest(key=key):
                self.assertIn(f"  {key}: ", script)
                self.assertIn(f"`{key}`", scripts_md)


if __name__ == "__main__":
    unittest.main()
