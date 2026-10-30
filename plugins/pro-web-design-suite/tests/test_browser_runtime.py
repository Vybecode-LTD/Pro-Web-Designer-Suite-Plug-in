"""a11y_runtime.mjs and snapshot_matrix.mjs in a REAL browser (3.1.0).

Skipped unless Node, Playwright and axe-core are available. Point
WDS_NODE_MODULES (or NODE_PATH) at a node_modules folder holding both, e.g.

    set WDS_NODE_MODULES=C:\\path\\to\\project\\node_modules

The tests never download anything; they use whatever browser the scripts
find (a Playwright-managed one, or an installed Chrome/Edge).

Regressions covered:
- GT-A1: the runtime contrast check parsed only rgb()/rgba(). Chromium reports
  colours authored in oklch() as oklch(…), so the suite's own token colours
  were never measured: no finding, no "unmeasurable" warning.
- GT-A2: a correct <dialog> opened with showModal() produced keyboard-trap,
  unreachable-control and no-accessible-name errors for everything behind it;
  focus inside a same-origin iframe was reported as focus-stuck, and axe ran
  in the top frame only.
- GT-A5: a page whose Content-Security-Policy refused the injected freeze
  stylesheet crashed the run, with exit 1.
- GT-A14 (b): the text of disabled controls was held to 1.4.3, which exempts it.
- GT-A3: the visual matrix's default per-pixel tolerance was coarser than the
  suite's own hover (4%) and pressed (8%) overlays, so deleting :hover or
  :active passed every cell.
- N59 (P65): the overlay probe asked about a point clamped to the viewport, so
  text below the fold took whatever sat at its edge as an overlay, a text the
  probe could not hit took everything beneath it, and a text clipped from its
  point took whatever was painted there.
"""
from __future__ import annotations

import functools
import http.server
import json
import re
import threading
import time
import unittest

from test_browser_scripts import installed_browsers
from wds_support import NODE, TempDirTest, keep_evidence, no_browser, output, run_node, run_py, tool_modules


def node_modules() -> str | None:
    """A node_modules folder with playwright and axe-core, or None."""
    return tool_modules("WDS_NODE_MODULES", "playwright", "axe-core", node_path=True)


MODULES = node_modules()
# What a server's `Content-Security-Policy: default-src 'self'` header does,
# in a file: no inline style or script, so no injected one either.
CSP_META = "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'self'\">"
CHECKS = ("axe", "names", "taborder", "focus", "forced", "contrast", "keys", "reflow",
          "spacing", "obscured", "hover", "motion")


def only(*checks):
    """The arguments that run just these checks: `--only` narrows a proof
    sheet's cells, and a page now refuses it (it used to ignore it)."""
    return [arg for c in CHECKS if c not in checks for arg in ("--skip", c)]


@unittest.skipUnless(NODE and MODULES, "needs node plus WDS_NODE_MODULES pointing at "
                                       "playwright and axe-core")
class RuntimeInABrowser(TempDirTest):

    def runtime(self, html, *args, name="page.html"):
        page = self.write(name, html)
        proc = run_node("a11y-audit-runner", "a11y_runtime.mjs", "--file", page, "--json", *args,
                        cwd=self.tmp, env_changes={"NODE_PATH": MODULES}, timeout=300)
        if proc.returncode == 2 and b"browser" in proc.stderr.lower():
            no_browser(self, "no usable browser: " + output(proc)[-200:])
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return json.loads(proc.stdout)["findings"]

    def rules(self, findings, severity="error"):
        return {f["rule"] for f in findings if f["severity"] == severity}

    def test_oklch_colours_are_measured(self):
        """GT-A1."""
        html = ("<!doctype html><html lang=en><head><title>o</title><style>"
                ".wrap{position:relative;background:#fff}.t{color:#595959}"
                ".scrim{position:absolute;inset:0;pointer-events:none;"
                "background:oklch(1 0 0 / 0.72)}.faint{color:oklch(0.75 0 0)}"
                "</style></head><body><main><h1>Overlay</h1><div class=wrap>"
                "<p class=t>This paragraph sits under a 72% white scrim.</p>"
                "<div class=scrim></div></div><p class=faint>Faint grey body text here.</p>"
                "</main></body></html>")
        errors = self.rules(self.runtime(html, *only("contrast")))
        self.assertIn("contrast-under-overlay", errors)
        self.assertIn("contrast-too-low", errors)

    def test_axe_reports_a_name_that_leaves_out_the_label(self):
        """P68: axe-core 4.14 runs label-content-name-mismatch (2.5.3) by
        default, so the gate's default tags report it with no rule enabled by
        name (CodeRabbit on #222). The control: a name that holds the label."""
        page = ("<!doctype html><html lang=en><head><title>n</title></head><body><main><h1>Order</h1>"
                "<button aria-label='{}'>Submit order</button></main></body></html>")
        found = [f for f in self.runtime(page.format("Close"), *only("axe")) if "label-content-name-mismatch" in f["rule"]]
        self.assertTrue(found, "the default tags reported no label-content-name-mismatch")
        self.assertEqual([], [f for f in self.runtime(page.format("Submit order now"), *only("axe"))
                              if "label-content-name-mismatch" in f["rule"]])

    def contrast_findings(self, body, style=""):
        html = ("<!doctype html><html lang=en><head><title>c</title><style>"
                "body{margin:0;font:16px sans-serif;color:#222;background:#fff}"
                "h1{margin:0;height:40px;font-size:24px}" + style +
                "</style></head><body><main><h1>Contrast</h1>" + body + "</main></body></html>")
        return [f for f in self.runtime(html, *only("contrast")) if f["rule"].startswith("contrast")]

    def contrast_rules(self, body, style=""):
        return {f["rule"] for f in self.contrast_findings(body, style)}

    def overlaid(self, layer):
        """A grey paragraph under a white layer, painted after it."""
        return self.contrast_findings(
            "<div class=wrap><p class=t>This paragraph sits under a white layer.</p>"
            "<div class=layer></div></div>",
            ".wrap{position:relative}.t{color:#595959}"
            ".layer{position:absolute;inset:0;background:#fff;" + layer + "}")

    def test_an_opaque_layer_over_text_is_unmeasurable_not_one_to_one(self):
        """N59 (P65): an opaque layer over the text was composited as a
        "translucent overlay", and the text measured 1.00:1. It hides the text,
        so the text's contrast cannot be computed: a warning says so."""
        self.assertEqual({"contrast-unmeasurable"}, {f["rule"] for f in self.overlaid("")})

    def test_a_layer_at_opacity_0_is_not_over_the_text(self):
        """N59 (P65): its opacity was not read, so an invisible panel counted as opaque."""
        self.assertEqual([], self.overlaid("opacity:0"))

    def test_a_layers_opacity_thins_what_it_paints(self):
        """N59 (P65): a white panel at opacity .72 measured 1.00:1; it paints
        what a 72% white scrim does."""
        scrim = [f["ratio"] for f in self.contrast_findings(
            "<div class=wrap><p class=t>This paragraph sits under a white layer.</p>"
            "<div class=layer></div></div>",
            ".wrap{position:relative}.t{color:#595959}"
            ".layer{position:absolute;inset:0;background:rgba(255,255,255,.72)}")]
        panel = [(f["rule"], f["ratio"]) for f in self.overlaid("opacity:.72")]
        self.assertEqual(1, len(scrim), scrim)
        self.assertEqual([("contrast-under-overlay", round(scrim[0], 1))],
                         [(rule, round(ratio, 1)) for rule, ratio in panel])

    def test_an_opaque_card_at_the_fold_is_not_over_the_text_below_it(self):
        """N59 (P65): the overlay probe clamped a text's middle to the viewport,
        so for text below the fold it asked what sat at the viewport's bottom
        edge. An opaque card there was composited over every text below it, and
        each measured 1.00:1: 21 to 147 false errors a page on webawesome.com."""
        rules = self.contrast_rules("<div class=fold></div><div class=card></div>"
                                    "<p>This paragraph sits well below the fold.</p>",
                                    ".fold{height:830px}.card{height:60px;background:#fff}")
        self.assertEqual(set(), rules)

    def test_a_scrim_below_the_fold_is_found(self):
        """N59 (P65): the same clamp missed a real scrim over text below the
        fold, since the point it asked about was not under the scrim."""
        rules = self.contrast_rules(
            "<div class=fold></div><div class=wrap>"
            "<p class=t>This paragraph sits under a 72% white scrim.</p><div class=scrim></div></div>",
            ".fold{height:1200px}.wrap{position:relative}.t{color:#595959}"
            ".scrim{position:absolute;inset:0;pointer-events:none;background:rgba(255,255,255,.72)}")
        self.assertEqual({"contrast-under-overlay"}, rules)

    def test_what_is_under_a_text_the_probe_cannot_hit_is_not_over_it(self):
        """N59 (P65): with the text's own box absent from elementsFromPoint
        (pointer-events: none), every element at the point counted as painted
        over it, the panel beneath it among them."""
        rules = self.contrast_rules(
            "<div class=box><div class=under></div><p class=t>This label passes no clicks through.</p></div>",
            ".box{position:relative;isolation:isolate}"
            ".under{position:absolute;inset:0;background:#fff;z-index:0}"
            ".t{position:relative;z-index:1;pointer-events:none}")
        self.assertEqual(set(), rules)

    def component(self, body, shadow, mode):
        """The page's `x-c` holds `shadow` in an open or closed shadow root."""
        return self.contrast_findings(
            body + "<script>customElements.define('x-c', class extends HTMLElement {"
            "constructor() { super(); this.attachShadow({mode: '" + mode + "'}).innerHTML = "
            + json.dumps(shadow) + "; } });</script>",
            ".wrap{position:relative}.t{color:#595959}")

    SCRIM = ".s{position:absolute;inset:0;pointer-events:none;background:rgba(255,255,255,.72)}"

    def test_a_scrim_inside_another_component_is_over_the_text(self):
        """P65, on #213 (Codex): the overlay probe asked the document what was at
        the text, and the document names a component's insides by its host. A
        scrim in the shadow root of a component laid over the text came back as
        that transparent host, and the text passed."""
        for mode in ("open", "closed"):
            with self.subTest(mode=mode):
                rules = {f["rule"] for f in self.component(
                    "<div class=wrap><p class=t>This paragraph sits under a 72% white scrim.</p>"
                    "<x-c></x-c></div>",
                    "<style>:host{position:absolute;inset:0}" + self.SCRIM + "</style><div class=s></div>",
                    mode)}
                self.assertEqual({"contrast-under-overlay"}, rules)

    def test_a_components_scrim_over_its_slotted_text_is_over_it(self):
        """P65, on #213: asked of the document, a component's own scrim over its
        slotted text is its host, listed after the text, so it did not count."""
        for mode in ("open", "closed"):
            with self.subTest(mode=mode):
                rules = {f["rule"] for f in self.component(
                    "<x-c><p class=t>This paragraph is slotted under a 72% white scrim.</p></x-c>",
                    "<style>:host{display:block;position:relative}" + self.SCRIM + "</style>"
                    "<slot></slot><div class=s></div>", mode)}
                self.assertEqual({"contrast-under-overlay"}, rules)

    def test_a_components_panel_behind_its_slotted_text_is_not_over_it(self):
        """The control: the component's own white panel holds the slot, so it is
        behind the text, and the text measures against it."""
        for mode in ("open", "closed"):
            with self.subTest(mode=mode):
                rules = {f["rule"] for f in self.component(
                    "<x-c><p>This dark paragraph is slotted onto a white panel.</p></x-c>",
                    "<style>.p{position:relative;background:#fff;padding:8px}</style>"
                    "<div class=p><slot></slot></div>", mode)}
                self.assertEqual(set(), rules)

    def test_a_text_clipped_from_its_point_has_nothing_over_it(self):
        """P65, on #213: a text clipped out of sight, as in a collapsed code
        block, is not at its own point, though the page that holds it is. The
        translucent code element painted there was counted over it, since it
        came before the page in the hit list: webawesome.com's button page
        reported its code samples' `wa-button` tokens at 3.46:1."""
        rules = self.contrast_rules(
            "<div class=clip><p class=t>This paragraph is clipped out of sight.</p></div>"
            "<p class=n><code class=c>A wide block of translucent code over the clipped line.</code></p>",
            ".clip{height:4px;overflow:hidden}.t,.n{margin:0}.t{color:#767676}"
            ".c{display:block;margin:0;background:rgba(128,128,128,.25)}")
        self.assertNotIn("contrast-under-overlay", rules)

    def test_a_scrim_over_text_scrolled_out_of_its_container_is_found(self):
        """P65, on #213 (CodeRabbit): the probe scrolled the page only, so a text
        scrolled out of view inside its own scroll container stayed clipped at
        its point, and the scrim over that container was not counted."""
        rules = self.contrast_rules(
            "<div class=wrap><div class=box><div class=gap></div>"
            "<p class=t>This paragraph is scrolled out of its box, under a scrim.</p></div>"
            "<div class=s></div></div>",
            ".wrap{position:relative}.box{height:60px;overflow:auto}.gap{height:300px}"
            ".t{color:#595959}"
            ".s{position:absolute;inset:0;pointer-events:none;background:rgba(255,255,255,.72)}")
        self.assertEqual({"contrast-under-overlay"}, rules)

    def test_a_spinner_is_not_a_focus_ring(self):
        """GT-A14 (a), fixed with GT-C13: the freeze shortened animations
        without pausing them, so a loading spinner inside a button with no
        focus ring changed pixels between the two shots and counted as one."""
        html = ("<!doctype html><html lang=en><head><title>s</title><style>"
                "button{font:16px sans-serif;padding:8px 12px;border:1px solid #333;background:#fff}"
                "button:focus{outline:none}"
                ".spin{display:inline-block;width:16px;height:16px;margin-right:6px;"
                "border:3px solid #333;border-top-color:transparent;border-radius:50%;"
                "animation:spin .4s linear infinite}"
                "@keyframes spin{to{transform:rotate(360deg)}}"
                "</style></head><body><main><h1>Save</h1>"
                "<button type=button><span class=spin></span>Saving</button>"
                "</main></body></html>")
        self.assertIn("no-visible-focus-indicator", self.rules(self.runtime(html, *only("focus"))))

    def test_a_page_with_a_strict_csp_is_audited(self):
        """GT-A5: `default-src 'self'` refused the freeze stylesheet the run
        injects, and the run crashed with exit 1."""
        page = self.write("csp.html", "<!doctype html><html lang=en><head><title>csp</title>"
                                      f"{CSP_META}</head><body><main><h1>Strict</h1>"
                                      "<button type=button>Save</button></main></body></html>")
        proc = run_node("a11y-audit-runner", "a11y_runtime.mjs", "--file", page, "--json",
                        *only("focus", "contrast"),
                        cwd=self.tmp, env_changes={"NODE_PATH": MODULES}, timeout=300)
        if proc.returncode == 2 and b"browser" in proc.stderr.lower():
            no_browser(self, "no usable browser: " + output(proc)[-200:])
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertEqual([], [f for f in json.loads(proc.stdout)["findings"] if f["severity"] == "error"])

    def test_disabled_controls_are_exempt_from_contrast(self):
        """GT-A14 (b): SC 1.4.3 exempts text that is part of an inactive
        component, as axe does; a control that only looks disabled is not."""
        faint = "color:#aaa;background:#fff"
        html = ("<!doctype html><html lang=en><head><title>d</title><style>"
                f".faint{{{faint}}}</style></head><body><main><h1>Plans</h1>"
                "<button class=faint disabled>Unavailable now</button>"
                "<button class=faint aria-disabled=true><span>Coming soon</span></button>"
                "<fieldset disabled><legend><button class=faint>Legend action</button></legend>"
                "<label class=faint for=card>Card number</label><input id=card></fieldset>"
                "<label class=faint for=promo>Promo code</label><input id=promo disabled>"
                "<button class=faint>Looks disabled</button>"
                "</main></body></html>")
        findings = self.runtime(html, *only("contrast"))
        flagged = sorted(f["message"].split('"')[1] for f in findings if f["rule"] == "contrast-too-low")
        # The first legend of a disabled fieldset stays enabled (Codex on #39).
        self.assertEqual(["Legend action", "Looks disabled"], flagged)

    ONE_STOP = ("<!doctype html><html lang=en><head><title>one</title></head><body><main>"
                "<h1>One</h1><button type=button>Save</button>{}</main></body></html>")

    def test_a_page_with_one_tab_stop_is_not_a_trap(self):
        """Chrome wraps Tab from the last stop to the first inside the page, so
        on a page with one stop, focus stays put: it was reported as
        `focus-stuck` (CI on #39). A page that cancels Tab still is one."""
        skips = only("taborder")
        trap = "<script>addEventListener('keydown', e => e.key === 'Tab' && e.target.matches('button') && e.preventDefault())</script>"
        for browser in [None] + installed_browsers()[:1]:
            extra = ["--browser", browser] if browser else []
            with self.subTest(browser=browser or "default"):
                errors = self.rules(self.runtime(self.ONE_STOP.format(""), *skips, *extra))
                self.assertNotIn("focus-stuck", errors)
                errors = self.rules(self.runtime(self.ONE_STOP.format(trap), *skips, *extra))
                self.assertIn("focus-stuck", errors)

    DENSITY_PAGE = ("<!doctype html><html lang=en><head><title>d</title><style>"
                    ":root{--density:1}[data-density=compact]{--density:0}[data-density=comfortable]{--density:1}"
                    "[data-density=spacious]{--density:1.5}"
                    ".bar{display:inline-flex;overflow:hidden;padding:calc(6px * var(--density))}"
                    "button{font:16px sans-serif;border:1px solid #333;background:#fff;color:#000}"
                    "button:focus-visible{outline:2px solid #000;outline-offset:2px}"
                    "[data-density=spacious] button:focus-visible{outline:none;box-shadow:0 0 0 3px #000}"
                    "</style></head><body><main><h1>Tools</h1>"
                    "<div class=bar><button type=button>Bold</button></div></main></body></html>")

    def test_the_focus_ring_is_measured_at_each_density_the_page_declares(self):
        """SB-B3: at compact the toolbar's padding is gone and its overflow
        clips the ring; at spacious the ring is a box-shadow, which forced
        colours discard. The default density has a ring in both modes. The dial
        is turned wherever the page keeps it: on the root, or on <body>, which
        a dial on the root alone could not reach (Codex on #40)."""
        # Two top regions at different densities have no one current value, so
        # none is skipped (CodeRabbit on #40).
        regions = "<header data-density=compact><p>Top</p></header><main data-density=comfortable>"
        for where, page in (("root", self.DENSITY_PAGE),
                            ("body", self.DENSITY_PAGE.replace("<body>", "<body data-density=comfortable>")),
                            ("regions", self.DENSITY_PAGE.replace("<main>", regions))):
            with self.subTest(dial=where):
                findings = self.runtime(page, *only("focus", "forced"))
                lost = {(f["rule"], f.get("density")) for f in findings
                        if f["severity"] == "error" and f["check"] in ("focus", "forced")}
                self.assertEqual({("no-visible-focus-indicator", "compact"),
                                  ("focus-ring-lost-in-forced-colors", "spacious")}, lost)
        findings = self.runtime(self.DENSITY_PAGE, *only("focus", "forced"), "--densities", "none")
        self.assertEqual([], [f for f in findings if f["severity"] == "error"])

    def test_a_best_practice_finding_does_not_breach_a_violation_budget(self):
        """Codex on #41: `axe_violations` counted the best-practice warnings,
        so `{"axe_violations": 0}` failed a page whose only finding was one."""
        page = self.write("bp.html", "<!doctype html><html lang=en><head><title>b</title></head><body>"
                                     "<main><h1>Order</h1><a href=#a tabindex=2>First</a></main></body></html>")
        budget = self.write("budget.json", '{"axe_violations": 0}')
        proc = run_node("a11y-audit-runner", "a11y_runtime.mjs", "--file", page, "--json",
                        "--budget", budget, *only("axe"),
                        cwd=self.tmp, env_changes={"NODE_PATH": MODULES}, timeout=300)
        if proc.returncode == 2 and b"browser" in proc.stderr.lower():
            no_browser(self, "no usable browser: " + output(proc)[-200:])
        report = json.loads(proc.stdout)
        self.assertIn("tabindex", {f["rule"] for f in report["findings"]})
        self.assertEqual((0, []), (proc.returncode, report["breaches"]), output(proc)[-400:])

    def test_a_best_practice_rule_is_a_warning(self):
        """GT-A8: axe rates `tabindex` (best-practice only) serious, and it
        failed the run as an error. It names no success criterion, so it is
        reported as a warning; a WCAG rule beside it is still an error."""
        html = ("<!doctype html><html lang=en><head><title>b</title></head><body><main>"
                "<h1>Order</h1><a href=#a tabindex=2>First</a><img src=chart.png></main></body></html>")
        axe = {f["rule"]: f for f in self.runtime(html, *only("axe")) if f["check"] == "axe"}
        self.assertEqual(("warning", "best practice"), (axe["tabindex"]["severity"], axe["tabindex"]["sc"]))
        self.assertEqual("error", axe["image-alt"]["severity"])

    def test_an_open_modal_dialog_is_not_a_trap(self):
        """GT-A2: a cookie banner built the recommended way."""
        html = ('<!doctype html><html lang="en"><head><title>Cookie consent</title></head><body>'
                '<header><a href="/">Home</a> <a href="/pricing">Pricing</a></header>'
                '<main><h1>Shop</h1><button type="button">Add to cart</button>'
                '<a href="/help">Help</a></main>'
                '<dialog id="consent" aria-labelledby="ct"><h2 id="ct">Cookies</h2>'
                '<button type="button">Accept</button><button type="button">Reject</button>'
                '</dialog><script>document.getElementById("consent").showModal();</script>'
                '</body></html>')
        errors = self.rules(self.runtime(html, *only("taborder", "names")))
        for rule in ("keyboard-trap", "unreachable-control", "no-accessible-name"):
            with self.subTest(rule=rule):
                self.assertNotIn(rule, errors)

    def test_focus_inside_an_iframe_moves_and_the_frame_is_audited(self):
        """GT-A2: a same-origin payment frame."""
        inner = ("&lt;form&gt;&lt;input type=text name=email&gt;"
                 "&lt;button type=submit&gt;&lt;/button&gt;&lt;/form&gt;")
        html = ("<!doctype html><html lang=en><head><title>outer</title></head><body><main>"
                "<h1>Checkout</h1><a href='#pay'>Pay</a>"
                f"<iframe title='Payment form' width=400 height=200 srcdoc=\"{inner}\"></iframe>"
                "<a href='#terms'>Terms</a></main></body></html>")
        findings = self.runtime(html, *only("taborder", "axe"))
        errors = self.rules(findings)
        self.assertNotIn("focus-stuck", errors)
        axe_rules = {f.get("rule") for f in findings if f.get("check") == "axe"}
        self.assertTrue({"label", "button-name"} & axe_rules, axe_rules)


@unittest.skipUnless(NODE and MODULES, "needs node plus WDS_NODE_MODULES pointing at playwright")
class VitalsUnderCsp(TempDirTest):
    """GT-A5, CodeRabbit on #39: measure_vitals injects only an init script,
    which CSP does not govern, so it measures the page with its CSP in force.
    A bypass would run what the CSP blocks: here, a script that shifts the
    page's content down after load."""

    PAGE = ("<!doctype html><html lang=en><head><title>v</title>{}</head><body><main>"
            "<h1>Prices</h1><p>Plans start at four pounds a month.</p></main><script>"
            # A shift before the first paint is not a layout shift, so it waits for one.
            "new PerformanceObserver((list, obs) => {{ obs.disconnect(); setTimeout(() =>"
            " document.body.insertAdjacentHTML('afterbegin', '<div id=\"banner\" style=\"height:400px\">"
            "Banner</div>'), 200); }}).observe({{ type: 'paint', buffered: true }});</script></body></html>")

    def vitals(self, head, *args):
        page = self.write("page.html", self.PAGE.format(head))
        proc = run_node("perf-budget-gate", "measure_vitals.mjs", page, "--runs", "1", "--json", *args,
                        cwd=self.tmp, env_changes={"NODE_PATH": MODULES}, timeout=240)
        if proc.returncode == 2 and b"no usable chromium" in proc.stderr:
            no_browser(self, output(proc)[-200:])
        self.assertIn(proc.returncode, (0, 1), output(proc))
        out = json.loads(proc.stdout)
        keep_evidence(self, "csp" if head else "no-csp", out)
        return out

    def test_a_script_the_csp_blocks_stays_blocked(self):
        """TEST-7 (P66): the shift is due 200 ms after the first paint, and
        each run read the page 1.5 s after load; on a slow macOS runner the
        paint came late enough that the shift landed after the reading, so
        the control measured nothing. The control now waits for the banner,
        and the blocked run is read late enough on its own clock that a
        shift that ran would have been seen."""
        shifted = self.vitals("", "--wait-for", "#banner", "--settle", "1500")
        self.assertGreater(shifted["stats"]["cls"]["median"], 0.1)     # the shift is measured when it runs
        blocked = self.vitals(CSP_META, "--settle", "3000")
        [run] = blocked["perRun"]
        self.assertIn("readAt", run, "each run says when it read the page")
        self.assertIsNotNone(run["fcp"], run)
        self.assertGreaterEqual(run["readAt"], run["fcp"] + 400, f"read before the shift was due: {run}")
        self.assertLess(blocked["stats"]["cls"]["median"], 0.01)


@unittest.skipUnless(NODE and MODULES, "needs node plus WDS_NODE_MODULES pointing at playwright")
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        """/hang answers after 9 seconds: a request still in flight when the
        run is read. /flaky.html is a blank page on the requests the server's
        `blank_on` numbers, and page.html's on the rest."""
        if self.path.startswith("/flaky"):
            self.server.hits = getattr(self.server, "hits", 0) + 1
            if self.server.hits in getattr(self.server, "blank_on", ()):
                body = b"<!doctype html><html lang=en><head><title>b</title></head><body></body></html>"
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return None
            self.path = "/page.html"
        if not self.path.startswith("/hang"):
            return super().do_GET()
        time.sleep(9)
        try:
            self.send_response(204)
            self.end_headers()
        except OSError:                   # the browser has gone
            pass


def the_task(out, after: float = 0) -> dict:
    """The fixture's 250 ms busy loop, as the run reports it: the longest
    task that starts at or after `after` ms on the page's clock. Codex on
    #154: a total less TBT could not tell it from a slow runner's own
    blocking before FCP; each task now says whether TBT counted it."""
    [run] = out["perRun"]
    found = [t for t in run["tasks"] if t["start"] >= after]
    if not found:
        raise AssertionError(f"no long task from {after} ms: {run['tasks']}")
    return max(found, key=lambda t: t["duration"])


@unittest.skipUnless(NODE and MODULES, "needs node plus WDS_NODE_MODULES pointing at playwright")
class VitalsMeasures(TempDirTest):
    """GT-A6: CDP adds its latency per request, and Navigation Timing's
    responseStart comes before it, so `--throttle slow4g` reported a TTFB of
    5 ms; and no preset was Lighthouse's. GT-A17: --interact counted the
    handler's own long task in TBT, and the TBT window had no TTI bound.
    GT-C11: nothing clicked while the page was still hydrating."""

    BUSY = "const t = performance.now(); while (performance.now() - t < {ms}) {{}}"

    def setUp(self):
        super().setUp()
        handler = functools.partial(QuietHandler, directory=str(self.tmp))
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def vitals(self, body, *args, path="/page.html"):
        self.write("page.html", "<!doctype html><html lang=en><head><title>v</title></head>"
                                "<body><main><h1>Plans</h1><p>From four pounds a month.</p>"
                                + body + "</main></body></html>")
        url = f"http://127.0.0.1:{self.server.server_address[1]}{path}"
        proc = run_node("perf-budget-gate", "measure_vitals.mjs", url, "--runs", "1", "--json",
                        *args, cwd=self.tmp, env_changes={"NODE_PATH": MODULES}, timeout=300)
        if proc.returncode == 2 and b"no usable chromium" in proc.stderr:
            no_browser(self, output(proc)[-200:])
        self.assertIn(proc.returncode, (0, 1), output(proc))
        self.stderr = proc.stderr.decode("utf-8", "replace")
        out = json.loads(proc.stdout)
        self.runs = getattr(self, "runs", 0) + 1
        keep_evidence(self, f"run{self.runs}", out)
        return out

    def test_ttfb_counts_the_emulated_latency(self):
        out = self.vitals("", "--throttle", "slow4g", "--settle", "300")
        self.assertGreaterEqual(out["stats"]["ttfb"]["median"], 140)
        out = self.vitals("", "--settle", "300")                       # the default
        self.assertEqual(out["throttle"], "lighthouse")
        self.assertIn("562.5ms per request", out["throttleDetail"])
        self.assertGreaterEqual(out["stats"]["ttfb"]["median"], 540)

    def test_an_interaction_is_not_counted_in_tbt(self):
        button = ("<button>Buy</button><script>document.querySelector('button')"
                  ".addEventListener('click', () => { " + self.BUSY.format(ms=250) + " });</script>")
        out = self.vitals(button, "--throttle", "off", "--settle", "500", "--interact", "button")
        self.assertGreaterEqual(out["stats"]["inp"]["median"], 200)
        # Codex on #45: the totals still count the handler's task.
        self.assertGreaterEqual(out["longTasks"]["count"], 1)
        self.assertGreaterEqual(out["longTasks"]["blockingTotal"], 150)
        # T2 (audit, 2026-10-14): TBT under 50 ms failed whenever a slow
        # runner's own loading made a long task. The handler's own task is
        # the one TBT leaves out, however slow the runner.
        [run] = out["perRun"]
        own = [t for t in run["tasks"] if t.get("leftOut") == "interaction"]
        self.assertTrue(own, run["tasks"])
        self.assertGreaterEqual(max(t["duration"] for t in own), 200)

    # The fixture's task, due AFTER ms past the first paint on the page's own
    # clock, and due again AFTER ms past any long task of the runner's own that
    # ends after the paint; #done shows once it has run, for --wait-for.
    QUIET = ("<p id=done hidden>Done</p><script>let due = null, timer, ran = false;"
             "const arm = (at) => { if (ran || (due != null && at <= due)) return; due = at;"
             " clearTimeout(timer); timer = setTimeout(() => { ran = true; " + BUSY.format(ms=250)
             + "; document.getElementById('done').hidden = false; }, Math.max(0, due - performance.now())); };"
             "let paint = null;"
             "new PerformanceObserver((list) => { for (const e of list.getEntries()) {"
             " if (e.name === 'first-contentful-paint') { paint = e.startTime; arm(paint + AFTER); } }"
             " }).observe({ type: 'paint', buffered: true });"
             "new PerformanceObserver((list) => { for (const e of list.getEntries()) {"
             " if (paint != null && e.startTime + e.duration > paint) arm(e.startTime + e.duration + AFTER); }"
             " }).observe({ type: 'longtask', buffered: true });</script>")

    def test_tbt_stops_at_tti(self):
        """A long task after five quiet seconds is after TTI; one before is not.
        T2 (audit, 2026-10-14): each run is read against its TTI, not against
        TBT under 50 ms, which a slow runner's own loading could pass: the
        fixture's task is found by its start, and its place against TTI
        decides whether TBT counted it. TEST-6 (P66): the task was due 6 s
        after the script ran, so a first paint after 1 s, or a long task of
        the runner's own, left it less than five quiet seconds and TTI came
        after it. It is now due on the page's own clock, 5.5 s past the first
        paint and past any such task, and the run waits until it has run."""
        out = self.vitals(self.QUIET.replace("AFTER", "5500"), "--throttle", "off",
                          "--wait-for", "#done", "--settle", "500")
        [run] = out["perRun"]
        self.assertIsNotNone(out["stats"]["tti"], run)
        task = the_task(out, after=run["fcp"] + 5000)
        self.assertGreaterEqual(task["start"], out["stats"]["tti"]["median"], run)   # after TTI
        self.assertEqual("after-tti", task.get("leftOut"), run)                       # so left out
        # Half a second past the paint, and read six seconds after it ran, so
        # its own quiet window fits in the run.
        out = self.vitals(self.QUIET.replace("AFTER", "500"), "--throttle", "off",
                          "--wait-for", "#done", "--settle", "6000")
        [run] = out["perRun"]
        task = the_task(out, after=run["fcp"])
        if out["stats"]["tti"]:
            self.assertLess(task["start"], out["stats"]["tti"]["median"], run)         # before TTI
        self.assertTrue(task["inTbt"], run)                                            # so counted
        self.assertGreaterEqual(out["stats"]["tbt"]["median"], task["duration"] - 50)

    def test_requests_in_flight_keep_the_network_busy(self):
        """Codex on #45: three fetches still in flight when the run was read
        had no Resource Timing entry, so the page looked quiet, TTI came
        early, and the task at 6 s fell out of TBT."""
        page = ("<script>for (let i = 0; i < 3; i++) fetch('/hang?' + i);"
                "setTimeout(() => { " + self.BUSY.format(ms=250) + " }, 6000);</script>")
        out = self.vitals(page, "--throttle", "off", "--settle", "7000")
        self.assertIsNone(out["stats"]["tti"])
        self.assertTrue(the_task(out, after=6000)["inTbt"])

    def test_interact_at_clicks_while_the_page_hydrates(self):
        """The click lands during a 3-second task: its wait is INP's, and the
        task stays in TBT, since it is the page's own work. The task starts
        1.5 s in, which leaves a slow runner time to find the button first
        (at 0.5 s, Windows CI found it only after the task, and missed).
        The task is due at 1.5 s on the page's clock, as the click is, not
        1.5 s after the script parses: on a slow runner the two drifted
        apart, the click came first, and INP was empty (#54's main run)."""
        page = ('<button id="buy">Buy</button><button id="after" hidden>Again</button>'
                "<script>setTimeout(() => { " + self.BUSY.format(ms=3000)
                + "; document.getElementById('after').hidden = false; }, "
                "Math.max(0, 1500 - performance.now()));</script>")
        out = self.vitals(page, "--throttle", "off", "--settle", "500", "--interact", "#buy",
                          "--interact-at", "2500")
        # TEST-8 (P66): the click has only to land during the task, with half a
        # second of it left for INP to wait behind; "by 2,800 ms" was a 300 ms
        # race a slow runner lost.
        [run] = out["perRun"]
        task = the_task(out, after=1000)
        self.assertGreaterEqual(task["duration"], 2900, run)
        self.assertGreaterEqual(run["clickedAt"], task["start"], f"the click came before the task: {run}")
        self.assertLessEqual(run["clickedAt"], task["start"] + task["duration"] - 500,
                             f"the click came with under 500 ms of the task left: {run}")
        self.assertIsNotNone(out["stats"]["inp"], "no interaction entry: %s" % out["perRun"])
        during = out["stats"]["inp"]["median"]
        self.assertGreaterEqual(during, 500)
        self.assertGreaterEqual(out["stats"]["tbt"]["median"], 1000)
        # The control clicks a button the task reveals as it ends, so the click
        # comes after the task however late the task started (CodeRabbit on
        # #151): an event under 16 ms is not reported at all, so INP may be
        # n/a. Held to half the hydrating click's. It clicked the first button
        # at load + 500 ms before, and on a slow macOS runner load came late
        # enough to put that click inside the task: the TBT flake had that
        # cause (the audit's G6).
        out = self.vitals(page, "--throttle", "off", "--settle", "500", "--interact", "#after")
        self.assertLess((out["stats"]["inp"] or {"median": 0})["median"], during / 2)
        self.assertNotIn("did not match", self.stderr)          # CodeRabbit on #45: it clicked

    def test_a_run_read_before_the_first_paint_waits_for_it(self):
        """P66 (N60): a run with no LCP at the end of its settle exited 1 for a
        page that had painted. At --settle 0 every run here read the page
        before its paint reached the observers, as macOS CI's runs did at
        --settle 500 (EachPageHasItsTypesBudget twice and
        TheOtherGatesReachThePage six times, 2026-10-19 to 28). The run now
        waits for the LCP, up to 5 s, and its notes say so. The content shows
        300 ms after load, so the run has to wait on any machine (CodeRabbit
        on #216)."""
        late = ("<style>main{visibility:hidden}</style><script>addEventListener('load', () => setTimeout(()"
                " => { document.querySelector('main').style.visibility = 'visible'; }, 300));</script>")
        out = self.vitals(late, "--throttle", "off", "--settle", "0")
        [run] = out["perRun"]
        self.assertIsNotNone(out["stats"]["lcp"], run)
        self.assertGreaterEqual(run["readAt"], run["lcp"], run)
        self.assertIsNotNone(run["lcpWait"], run)
        self.assertTrue([n for n in out["notes"] if "was waited for" in n], out["notes"])

    def test_a_page_that_never_paints_waits_five_seconds_and_has_no_lcp(self):
        """The wait has an end: a page with nothing to paint still exits 1
        with no LCP, after 5 s."""
        self.write("blank.html", "<!doctype html><html lang=en><head><title>v</title></head><body></body></html>")
        url = f"http://127.0.0.1:{self.server.server_address[1]}/blank.html"
        proc = run_node("perf-budget-gate", "measure_vitals.mjs", url, "--runs", "1", "--json", "--throttle",
                        "off", "--settle", "0", cwd=self.tmp, env_changes={"NODE_PATH": MODULES}, timeout=300)
        if proc.returncode == 2 and b"no usable chromium" in proc.stderr:
            no_browser(self, output(proc)[-200:])
        # Kept before anything is asserted, so a red run uploads it (CodeRabbit on #216).
        report = json.loads(proc.stdout) if proc.stdout.strip() else {"output": output(proc)}
        keep_evidence(self, "blank", report)
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn("no LCP was recorded in any run", output(proc))
        [run] = report["perRun"]
        self.assertIsNone(run["lcp"], run)
        self.assertIn("lcpWait", run, "each run says how long it waited for an LCP")
        self.assertGreaterEqual(run["lcpWait"], 4900, run)

    # P76 (the 2026-10-28 audit's JS-B). A hero that paints 1.5 s in, on the
    # page's clock, larger than anything before it.
    LATE_HERO = ("<button id=buy>Buy</button><script>setTimeout(() => {"
                 " const p = document.createElement('p'); p.id = 'hero';"
                 " p.style.cssText = 'font-size:72px;line-height:1.1;margin:0';"
                 " p.textContent = 'The largest paint on this page, by far';"
                 " document.querySelector('main').append(p); }, Math.max(0, 1500 - performance.now()));"
                 "</script>")

    def test_an_interact_at_runs_lcp_stops_at_the_click(self):
        """JS-B-10: a browser stops reporting LCP at the first input, so a
        click at 300 ms reported the heading's paint as the LCP, and it passed
        an lcp_ms of 1,000 that the hero at 1.5 s breaks. The run now says so,
        measures the page's LCP in one run without the click, and holds
        neither to lcp_ms."""
        budget = self.write("perf-budget.json", json.dumps({"defaults": {"lab": {"lcp_ms": 1000}}}))
        out = self.vitals(self.LATE_HERO, "--throttle", "off", "--settle", "2500", "--interact", "#buy",
                          "--interact-at", "300", "--budget", budget)
        self.assertIs(True, out.get("lcpBeforeClick"), out.get("notes"))
        self.assertGreaterEqual((out.get("unclicked") or {}).get("lcp") or 0, 1400, out.get("unclicked"))
        self.assertLess(out["stats"]["lcp"]["median"], 1400, out["perRun"])      # the heading, before the click
        self.assertEqual([], [b for b in out["breaches"] if b["metric"] == "lcp"])
        self.assertTrue(any("up to the click" in n for n in out["notes"]), out["notes"])

    def test_an_interact_at_target_that_never_shows_keeps_the_lcp_budget(self):
        """CodeRabbit on #234: a target that never showed clicked nothing, so
        the LCP was the page's own, and lcp_ms was still skipped: the hero at
        1.5 s passed a limit of 1,000."""
        budget = self.write("perf-budget.json", json.dumps({"defaults": {"lab": {"lcp_ms": 1000}}}))
        out = self.vitals(self.LATE_HERO, "--throttle", "off", "--settle", "2500", "--interact", "#missing",
                          "--interact-at", "300", "--budget", budget)
        self.assertIsNone(out["perRun"][0]["clickedAt"], out["perRun"])
        self.assertFalse(out.get("lcpBeforeClick"), out.get("notes"))
        self.assertEqual(["lcp"], [b["metric"] for b in out["breaches"]], out["breaches"])

    def test_a_metric_some_runs_lacked_is_said(self):
        """JS-B-15: one run of three with no LCP passed on the other two's
        median, and nothing said the median was of two."""
        self.server.blank_on = {2}                         # the second request is a blank page
        # Half a second's settle: 4.0.1, which has no grace for a late LCP,
        # read none in any run at 0.
        out = self.vitals("", "--runs", "3", "--throttle", "off", "--settle", "500", path="/flaky.html")
        self.assertEqual(2, (out["stats"]["lcp"] or {}).get("n"), out["perRun"])
        self.assertTrue(any(n.startswith("LCP was recorded in 2 of 3 runs") for n in out["notes"]), out["notes"])

    def test_several_pages_say_why_a_page_exits_1(self):
        """JS-B-14: a page with no LCP exits 1, and the --urls report showed
        a dash and exit 1 with no line under it."""
        self.write("blank.html", "<!doctype html><html lang=en><head><title>b</title></head><body></body></html>")
        urls = self.write("urls.txt", f"http://127.0.0.1:{self.server.server_address[1]}/blank.html\n")
        proc = run_node("perf-budget-gate", "measure_vitals.mjs", "--urls", urls, "--runs", "1",
                        "--throttle", "off", "--settle", "0", "--quiet", cwd=self.tmp,
                        env_changes={"NODE_PATH": MODULES}, timeout=300)
        if proc.returncode == 2 and b"no usable chromium" in proc.stderr:
            no_browser(self, output(proc)[-200:])
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn("blank.html: no LCP was recorded in any run", proc.stdout.decode("utf-8", "replace"))

    def test_several_pages_say_an_interact_at_lcp_stops_at_the_click(self):
        """Codex on #234: with --urls, the text report printed the clicked
        runs' LCP under a plain LCP heading, and said neither that it stops at
        the click nor that lcp_ms was not held to it, so a page whose hero
        breaks the budget read as a pass."""
        self.write("page.html", "<!doctype html><html lang=en><head><title>v</title></head>"
                                "<body><main><h1>Plans</h1><p>From four pounds a month.</p>"
                                + self.LATE_HERO + "</main></body></html>")
        urls = self.write("urls.txt", f"http://127.0.0.1:{self.server.server_address[1]}/page.html\n")
        budget = self.write("perf-budget.json", json.dumps({"defaults": {"lab": {"lcp_ms": 1000}}}))
        proc = run_node("perf-budget-gate", "measure_vitals.mjs", "--urls", urls, "--runs", "1",
                        "--throttle", "off", "--settle", "2500", "--interact", "#buy", "--interact-at", "300",
                        "--budget", budget, "--quiet", cwd=self.tmp, env_changes={"NODE_PATH": MODULES},
                        timeout=300)
        if proc.returncode == 2 and b"no usable chromium" in proc.stderr:
            no_browser(self, output(proc)[-200:])
        self.assertEqual(0, proc.returncode, output(proc))
        text = proc.stdout.decode("utf-8", "replace")
        self.assertIn("is up to the click at 300 ms", text)
        self.assertRegex(text, r"without the click, one run: (\d+)ms")
        self.assertGreaterEqual(int(re.search(r"without the click, one run: (\d+)ms", text).group(1)), 1400, text)
        self.assertIn("Neither is held to lcp_ms", text)

    def test_the_report_names_the_browser_and_its_build(self):
        """TEST-10: three CI legs tested three Chromiums and no report said
        which; each now names the build it launched."""
        out = self.vitals("", "--throttle", "off", "--settle", "300")
        self.assertTrue(out.get("browser"), out.keys())
        self.assertRegex(out.get("browserVersion") or "", r"^\d+\.\d+")


class MatrixSeesStateChanges(TempDirTest):
    """GT-A3."""

    ID = "button--p_base--f_label--v_primary--s_md--st_{}--d_comfortable--t_light"
    SHEET = """<!doctype html><html lang=en><head><title>matrix</title><style>
      body{{margin:0;background:#fff;font:16px/1.4 system-ui}}
      .cell{{display:inline-block;padding:16px}}
      .button{{display:inline-block;padding:8px 16px;background:#fff;color:#222;
              border:1px solid #ccc;border-radius:6px}}
      [data-force-state~="hover"] .button{{background:oklch(0% 0 0 / {hover})}}
      [data-force-state~="active"] .button{{background:oklch(0% 0 0 / 0.08)}}
    </style></head><body>
      <div class=cell data-cell-id="{d}"><span class=button>Save</span></div>
      <div class=cell data-cell-id="{h}" data-force-state="hover"><span class=button>Save</span></div>
      <div class=cell data-cell-id="{a}" data-force-state="active"><span class=button>Save</span></div>
    </body></html>"""

    def sheet(self, hover="0.04", styled=True):
        html = self.SHEET.format(hover=hover, d=self.ID.format("default"),
                                 h=self.ID.format("hover"), a=self.ID.format("active"))
        if not styled:                    # the :hover and :active rules deleted
            html = html.replace('[data-force-state~="hover"] .button', ".never")
            html = html.replace('[data-force-state~="active"] .button', ".never")
        return self.write("sheet.html", html)

    def snapshot(self, sheet, *args):
        proc = run_node("component-state-matrix", "snapshot_matrix.mjs", sheet,
                        "--baselines", self.tmp / "base", "--out", self.tmp / "report", *args,
                        cwd=self.tmp, env_changes={"NODE_PATH": MODULES}, timeout=300)
        if proc.returncode == 2 and b"browser" in proc.stderr.lower():
            no_browser(self, "no usable browser: " + output(proc)[-200:])
        return proc

    def test_the_run_names_the_browser_and_its_build(self):
        """TEST-10: the matrix named its browser only when it found one itself,
        and never its build; the log and the report now name both."""
        proc = self.snapshot(self.sheet(styled=True), "--allow-new")
        self.assertIn(proc.returncode, (0, 1), output(proc))
        line = re.search(r"(?m)^browser: (.+)$", output(proc))
        self.assertIsNotNone(line, output(proc))
        self.assertRegex(line.group(1), r" \d+\.\d+")
        self.assertIn(line.group(1), (self.tmp / "report" / "index.html").read_text(encoding="utf-8"))

    def test_a_state_cell_identical_to_its_default_fails_without_a_baseline(self):
        proc = self.snapshot(self.sheet(styled=False), "--allow-new")
        self.assertEqual(proc.returncode, 1, output(proc))
        self.assertIn("st_hover", output(proc))
        self.assertIn("no visible style", output(proc))

    def test_a_generated_sheet_renders_grouped_and_nested_states(self):
        """Audit H5, end to end: a hover inside `:is()` and a nested `&:active`
        got no mirror rule, so their cells rendered as default."""
        self.write("chip.css", ".chip { display: inline-block; padding: 8px 16px; background: #fff; color: #222; }\n"
                               ".chip:is(:hover) { background: #ddd; }\n"
                               ".chip { &:active { background: #999; } }\n")
        self.write("matrix.json", json.dumps({
            "$schema": "component-state-matrix/1", "themes": ["light"], "densities": ["comfortable"],
            "components": [{"name": "chip", "css": "chip.css", "states": ["default", "hover", "active"],
                            "template": '<span class="chip" {attrs}>{content}</span>'}]}))
        proc = run_py("component-state-matrix", "generate_matrix", "matrix.json", "--out", "sheet.html",
                      cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        proc = self.snapshot(self.tmp / "sheet.html", "--allow-new")
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertNotIn("no visible style", output(proc))

    def test_a_sheet_with_a_strict_csp_is_captured(self):
        """GT-A5, in snapshot_matrix: the freeze stylesheet was refused there too."""
        sheet = self.sheet()
        html = sheet.read_text(encoding="utf-8").replace("<title>matrix</title>",
                                                         "<title>matrix</title>" + CSP_META)
        sheet.write_text(html, encoding="utf-8")
        proc = self.snapshot(sheet, "--update-baselines")
        self.assertEqual(proc.returncode, 0, output(proc))

    FOCUS = """<!doctype html><html lang=en><head><title>focus</title><style>
      body{{margin:0;background:#fff;font:16px/1.4 system-ui}}
      .cell{{display:inline-block;padding:16px}}
      .button{{display:inline-block;padding:8px 16px;background:#fff;color:#222;
              border:1px solid #ccc;border-radius:6px}}
      [data-force-state~="hover"] .button{{box-shadow:0 2px 4px #0004}}
      [data-force-state~="focus-visible"] .button{{{ring}}}
    </style></head><body>
      <div class=cell data-cell-id="{d}"><span class=button>Save</span></div>
      <div class=cell data-cell-id="{h}" data-force-state="hover"><span class=button>Save</span></div>
      <div class=cell data-cell-id="{f}" data-force-state="focus-visible"><span class=button>Save</span></div>
    </body></html>"""

    def focus_sheet(self, ring):
        return self.write("focus.html", self.FOCUS.format(
            ring=ring, d=self.ID.format("default"), h=self.ID.format("hover"),
            f=self.ID.format("focus-visible")))

    def test_a_box_shadow_focus_ring_fails_under_forced_colours(self):
        """GT-B7: forced colours drop box-shadow, so that ring vanishes; a
        hover drawn with box-shadow may vanish there, and is not held to it."""
        sheet = self.focus_sheet("box-shadow:0 0 0 3px #1a5fb4")
        proc = self.snapshot(sheet, "--allow-new")
        self.assertEqual(proc.returncode, 0, output(proc))
        proc = self.snapshot(sheet, "--allow-new", "--forced-colors")
        self.assertEqual(proc.returncode, 1, output(proc))
        self.assertIn("st_focus-visible", output(proc))
        self.assertIn("does not survive", output(proc))
        self.assertNotIn("fail   " + self.ID.format("hover"), output(proc))
        proc = self.snapshot(self.focus_sheet("outline:2px solid #1a5fb4;outline-offset:2px"),
                             "--allow-new", "--forced-colors")
        self.assertEqual(proc.returncode, 0, output(proc))

    def test_the_forced_colours_pass_keeps_its_own_baselines(self):
        sheet = self.focus_sheet("outline:2px solid #1a5fb4")
        for args in (("--update-baselines",), ("--update-baselines", "--forced-colors"),
                     (), ("--forced-colors",)):
            with self.subTest(args=args):
                proc = self.snapshot(sheet, *args)
                self.assertEqual(proc.returncode, 0, output(proc))
        self.assertEqual(len(list((self.tmp / "base").glob("*.png"))), 3)
        self.assertEqual(len(list((self.tmp / "base" / "forced-colors").glob("*.png"))), 3)
        self.assertTrue((self.tmp / "report" / "forced-colors" / "index.html").is_file())
        self.assertIn("forced colours", (self.tmp / "report" / "forced-colors" / "index.html")
                      .read_text(encoding="utf-8"))

    def test_a_subtle_fill_change_against_the_baseline_is_caught(self):
        proc = self.snapshot(self.sheet(hover="0.04"), "--update-baselines")
        self.assertEqual(proc.returncode, 0, output(proc))
        proc = self.snapshot(self.sheet(hover="0.08"))          # hover twice as dark
        self.assertEqual(proc.returncode, 1, output(proc))
        self.assertIn("st_hover", output(proc))


@unittest.skipUnless(NODE and MODULES, "needs node plus WDS_NODE_MODULES pointing at "
                                       "playwright and axe-core")
class TheForcedColoursSurvey(TempDirTest):
    """P54 part 7, the audit of 2026-10-14's §3.6: G5. `/button|a|summary/`
    was unanchored, so every filled `main`, `nav`, `span` or `table` counted
    as a control distinguished by its fill alone."""

    def test_only_controls_count_as_fill_only(self):
        fill = "background:#dddddd;border:none"
        page = self.write("page.html", (
            "<!doctype html><html lang=\"en\"><title>t</title>"
            f"<nav style=\"{fill}\"><span style=\"{fill}\">n</span></nav>"
            f"<main style=\"{fill}\"><table style=\"{fill}\"><tr><td>x</td></tr></table>"
            f"<label style=\"{fill}\">l</label>"
            f"<button style=\"{fill}\">Buy</button></main></html>"))
        proc = run_node("a11y-audit-runner", "a11y_runtime.mjs", "--file", page, "--json",
                        cwd=self.tmp, env_changes={"NODE_PATH": MODULES}, timeout=300)
        if proc.returncode == 2 and b"browser" in proc.stderr.lower():
            no_browser(self, "no usable browser: " + output(proc)[-200:])
        self.assertIn(proc.returncode, (0, 1), output(proc))
        survey = json.loads(proc.stdout)["forcedSurvey"]
        self.assertEqual(1, survey["fillOnly"], survey)


if __name__ == "__main__":
    unittest.main()
