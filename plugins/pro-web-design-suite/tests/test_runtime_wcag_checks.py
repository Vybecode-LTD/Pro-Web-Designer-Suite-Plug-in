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
from wds_support import NODE, PLUGIN, TempDirTest, no_browser, output, run_node

HEAD = ("<!doctype html><html lang=en><head><meta charset=utf-8><title>Page</title>"
        "<style>body{{font:16px/1.2 sans-serif;color:#111;background:#fff}}{}</style></head>"
        "<body><main><h1>Page</h1>{}</main></body></html>")


def page(css: str, body: str) -> str:
    return HEAD.format(css, body)


@unittest.skipUnless(NODE and MODULES, "needs node plus WDS_NODE_MODULES pointing at "
                                       "playwright and axe-core")
class RuntimeCase(TempDirTest):

    def runtime(self, html: str, *checks: str, extra: tuple = ()) -> dict:
        path = self.write("page.html", html)
        proc = run_node("a11y-audit-runner", "a11y_runtime.mjs", "--file", path, "--json",
                        *only(*checks), *extra, cwd=self.tmp, env_changes={"NODE_PATH": MODULES},
                        timeout=300)
        if proc.returncode == 2 and b"browser" in proc.stderr.lower():
            no_browser(self, "no usable browser: " + output(proc)[-200:])
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

    def test_a_box_that_spilt_and_now_hides_its_overflow_is_clipped(self):
        """Codex on #179: a box that let two lines spill at full width and
        hides its overflow in a narrow layout has lost the line it showed."""
        report = self.runtime(page(
            ".promo{height:1.3em;width:12em}"
            "@media (max-width:700px){.promo{overflow:hidden}}",
            "<p class=promo>First line<br>Second line</p>"), "reflow")
        self.assertEqual(["html > body > main > p.promo"],
                         [f["selector"] for f in self.found(report, "text-clipped-at-200-percent")],
                         report["findings"])

    def test_a_decoration_wider_than_the_box_is_no_clipped_text(self):
        """Codex on #179: the box's scroll size counts a decoration 900px wide
        that a narrow layout cuts off, and no text is lost. The text is
        measured, not the box."""
        report = self.runtime(page(
            ".hero{position:relative;overflow:hidden}"
            ".deco{position:absolute;top:0;left:0;width:900px;height:8px;background:#ccc}",
            "<div class=hero><p>Short words</p><div class=deco></div></div>"), "reflow")
        self.assertEqual([], [f for f in report["findings"] if "clipped" in f["rule"]],
                         report["findings"])

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

    def test_a_transparent_layer_over_the_page_hides_nothing(self):
        """Codex on #179: a toast region spread over the whole viewport is hit
        at every point and paints only its toast. What a cover paints counts,
        not what it is hit for; a toast that is over a link still hides it."""
        portal = ("<div class=portal><div class=toast>Saved</div></div>")
        css = ("html{scroll-padding:160px 0 120px}"
               ".portal{position:fixed;inset:0;pointer-events:none}"
               ".toast{position:absolute;right:0;top:0;background:#222;color:#fff;"
               "padding:8px 16px}")
        clear = self.runtime(page(STOPS_CSS.format("padding:160px 0 120px", css),
                                  STOPS + portal), "obscured")
        self.assertEqual([], [f for f in clear["findings"] if f["check"] == "obscured"])
        over = self.runtime(page(STOPS_CSS.format(
            "padding:160px 0 120px", css + ".toast{left:0;bottom:0}"), STOPS + portal),
            "obscured")
        covers = {c for f in self.found(over, "focus-obscured") for c in f["covers"]}
        self.assertTrue(covers and all("div.portal" in c for c in covers), over["findings"])

    def test_a_cover_painted_by_its_pseudo_element_hides(self):
        """Codex on #179: a transparent bar whose ::before draws its backdrop
        still covers the link under it."""
        report = self.runtime(page(STOPS_CSS.format(
            "", ".bar{background:none}.bar::before{content:'';position:absolute;inset:0;"
                "background:#222;z-index:-1}"), STOPS), "obscured")
        self.assertIn(FIRST, [f["selector"] for f in self.found(report, "focus-obscured")],
                      report["findings"])

    def test_a_black_or_red_bar_paints(self):
        """CodeRabbit on #179: `rgb(0, 0, 0)` ends in `, 0)`, and was read as
        a transparent colour, so a black bar hid nothing. So was any colour
        with no blue; a fully transparent one still hides nothing."""
        for colour, hides in (("#000", True), ("#f00", True), ("rgba(0, 0, 0, 0)", False)):
            with self.subTest(colour=colour):
                report = self.runtime(page(STOPS_CSS.format(
                    "", f".bar{{background:{colour}}}.bar a{{color:transparent}}"), STOPS),
                    "obscured")
                self.assertEqual(hides, FIRST in [
                    f["selector"] for f in self.found(report, "focus-obscured")],
                    report["findings"])

    def test_a_cover_drawn_by_its_border_hides(self):
        """Codex on #179: a transparent bar drawn by a border 160px thick still
        covers the link under it."""
        report = self.runtime(page(STOPS_CSS.format(
            "", ".bar{background:none;height:0;border-top:160px solid #222}"), STOPS),
            "obscured")
        self.assertIn(FIRST, [f["selector"] for f in self.found(report, "focus-obscured")],
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

    def test_travel_is_measured_between_keyframes_and_by_element(self):
        """Codex on #179: -200px to 200px is 400px of travel, not the 0
        between two equal distances from the origin, so a variant of -20px to
        20px, under keyframes of its own name, is reduced. The same travel
        under a new name is not."""
        css = ("@keyframes sway{{from{{transform:translateX(-200px)}}to{{transform:translateX(200px)}}}}"
               "@keyframes {name}{{from{{transform:translateX(-{px}px)}}to{{transform:translateX({px}px)}}}}"
               ".sway{{animation:sway 2s ease-in-out infinite alternate}}"
               "@media (prefers-reduced-motion: reduce){{.sway{{animation-name:{name}}}}}")
        body = "<div class=sway>Swaying banner</div>"
        small = self.runtime(page(css.format(name="nudge", px=20), body), "motion")
        self.assertEqual([], [f for f in small["findings"] if f["check"] == "motion"])
        same = self.runtime(page(css.format(name="sway2", px=200), body), "motion")
        self.assertEqual(["motion-not-reduced"],
                         [f["rule"] for f in same["findings"] if f["check"] == "motion"],
                         same["findings"])

    def test_travel_by_left_is_measured(self):
        """Codex on #179: `left` is motion, so its travel is measured too: 0 to
        20px in place of 0 to 200px is reduced; 0 to 200px again is not."""
        css = ("@keyframes drift{{from{{left:0}}to{{left:200px}}}}"
               "@keyframes {name}{{from{{left:0}}to{{left:{px}px}}}}"
               ".drift{{position:relative;animation:drift 2s infinite alternate}}"
               "@media (prefers-reduced-motion: reduce){{.drift{{animation-name:{name}}}}}")
        body = "<div class=drift>Drifting banner</div>"
        small = self.runtime(page(css.format(name="edge", px=20), body), "motion")
        self.assertEqual([], [f for f in small["findings"] if f["check"] == "motion"])
        same = self.runtime(page(css.format(name="drift2", px=200), body), "motion")
        self.assertEqual(["motion-not-reduced"],
                         [f["rule"] for f in same["findings"] if f["check"] == "motion"])

    def test_a_stopped_busy_loop_breaks_its_budget(self):
        """Codex on #179: no counter held `busy-indicator-stopped`, so a budget
        of zero on every motion key let it pass."""
        budget = self.write("budget.json", json.dumps({"motion_busy_stopped": 0}))
        report = self.runtime(page(MOTION_CSS.format(
            ".slider{animation:none}.reveal{animation:none;opacity:1}.spinner{animation:none}"),
            MOTION_BODY), "motion", extra=("--budget", budget))
        self.assertEqual([("motion_busy_stopped", 1, 0)],
                         [(b["key"], b["actual"], b["limit"]) for b in report["breaches"]])

    def test_a_renamed_animation_is_paired_with_what_it_replaced(self):
        """Codex on #179: a renamed translation on an element that also turns
        was measured against the turn, and its zero turn read as reduced."""
        css = ("@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}"
               "@keyframes sway{from{transform:translateX(-200px)}to{transform:translateX(200px)}}"
               "@keyframes sway2{from{transform:translateX(-200px)}to{transform:translateX(200px)}}"
               ".both{animation:spin 3s linear infinite,sway 2s ease-in-out infinite alternate}"
               "@media (prefers-reduced-motion: reduce){.both{animation-name:spin,sway2}}")
        report = self.runtime(page(css, "<div class=both>Busy banner</div>"), "motion")
        self.assertIn("sway2", [f["animation"] for f in self.found(report, "motion-not-reduced")],
                      report["findings"])

    def test_a_one_off_pulse_in_place_of_the_spinner_stops_it(self):
        """Codex on #179: a finite pulse on the spinner ends, and the status
        reads as hung all the same."""
        report = self.runtime(page(MOTION_CSS.format(
            ".slider{animation:none}.reveal{animation:none;opacity:1}"
            ".spinner{animation:fade 1s 1}"), MOTION_BODY), "motion")
        self.assertEqual(["busy-indicator-stopped"],
                         [f["rule"] for f in report["findings"] if f["check"] == "motion"],
                         report["findings"])

    def test_the_end_of_a_long_page_is_reached(self):
        """Codex on #179: a reveal thirty viewports down, started on scroll,
        was never reached, so the text it leaves hidden went unreported."""
        css = (".late{opacity:0}.late.in{animation:show .3s forwards}"
               "@keyframes show{from{opacity:0}to{opacity:1}}"
               "@media (prefers-reduced-motion: reduce){.late.in{animation:none}}")
        body = ("<div style='height:30000px'></div><p class=late>Late words</p>"
                "<script>new IntersectionObserver((es) => es.forEach((e) => "
                "e.isIntersecting && e.target.classList.add('in')))"
                ".observe(document.querySelector('.late'));</script>")
        report = self.runtime(page(css, body), "motion")
        self.assertEqual(["html > body > main > p.late.in"],
                         [f["selector"] for f in self.found(
                             report, "content-hidden-under-reduced-motion")],
                         report["findings"])

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
                    "motion_not_reduced", "motion_content_hidden", "motion_busy_stopped"):
            with self.subTest(key=key):
                self.assertIn(f"  {key}: ", script)
                self.assertIn(f"`{key}`", scripts_md)


if __name__ == "__main__":
    unittest.main()
