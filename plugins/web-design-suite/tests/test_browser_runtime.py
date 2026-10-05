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
"""
from __future__ import annotations

import json
import unittest

from test_browser_scripts import installed_browsers
from wds_support import NODE, TempDirTest, output, run_node, tool_modules


def node_modules() -> str | None:
    """A node_modules folder with playwright and axe-core, or None."""
    return tool_modules("WDS_NODE_MODULES", "playwright", "axe-core", node_path=True)


MODULES = node_modules()
# What a server's `Content-Security-Policy: default-src 'self'` header does,
# in a file: no inline style or script, so no injected one either.
CSP_META = "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'self'\">"
CHECKS = ("axe", "names", "taborder", "focus", "forced", "contrast", "keys", "reflow")


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
            self.skipTest("no usable browser: " + output(proc)[-200:])
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
            self.skipTest("no usable browser: " + output(proc)[-200:])
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
        skips = [arg for check in ("axe", "names", "focus", "forced", "contrast", "keys", "reflow")
                 for arg in ("--skip", check)]
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
            self.skipTest("no usable browser: " + output(proc)[-200:])
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
            " document.body.insertAdjacentHTML('afterbegin', '<div style=\"height:400px\">Banner</div>'),"
            " 200); }}).observe({{ type: 'paint', buffered: true }});</script></body></html>")

    def cls(self, head):
        page = self.write("page.html", self.PAGE.format(head))
        proc = run_node("perf-budget-gate", "measure_vitals.mjs", page, "--runs", "1",
                        "--settle", "1500", "--json", cwd=self.tmp,
                        env_changes={"NODE_PATH": MODULES}, timeout=240)
        if proc.returncode == 2 and b"no usable chromium" in proc.stderr:
            self.skipTest(output(proc)[-200:])
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return json.loads(proc.stdout)["stats"]["cls"]["median"]

    def test_a_script_the_csp_blocks_stays_blocked(self):
        self.assertGreater(self.cls(""), 0.1)            # the shift is measured when it runs
        self.assertLess(self.cls(CSP_META), 0.01)


@unittest.skipUnless(NODE and MODULES, "needs node plus WDS_NODE_MODULES pointing at playwright")
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
            self.skipTest("no usable browser: " + output(proc)[-200:])
        return proc

    def test_a_state_cell_identical_to_its_default_fails_without_a_baseline(self):
        proc = self.snapshot(self.sheet(styled=False), "--allow-new")
        self.assertEqual(proc.returncode, 1, output(proc))
        self.assertIn("st_hover", output(proc))
        self.assertIn("no visible style", output(proc))

    def test_a_sheet_with_a_strict_csp_is_captured(self):
        """GT-A5, in snapshot_matrix: the freeze stylesheet was refused there too."""
        sheet = self.sheet()
        html = sheet.read_text(encoding="utf-8").replace("<title>matrix</title>",
                                                         "<title>matrix</title>" + CSP_META)
        sheet.write_text(html, encoding="utf-8")
        proc = self.snapshot(sheet, "--update-baselines")
        self.assertEqual(proc.returncode, 0, output(proc))

    def test_a_subtle_fill_change_against_the_baseline_is_caught(self):
        proc = self.snapshot(self.sheet(hover="0.04"), "--update-baselines")
        self.assertEqual(proc.returncode, 0, output(proc))
        proc = self.snapshot(self.sheet(hover="0.08"))          # hover twice as dark
        self.assertEqual(proc.returncode, 1, output(proc))
        self.assertIn("st_hover", output(proc))


if __name__ == "__main__":
    unittest.main()
