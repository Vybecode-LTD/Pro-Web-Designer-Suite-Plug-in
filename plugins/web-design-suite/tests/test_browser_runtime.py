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
- GT-A3: the visual matrix's default per-pixel tolerance was coarser than the
  suite's own hover (4%) and pressed (8%) overlays, so deleting :hover or
  :active passed every cell.
"""
from __future__ import annotations

import json
import os
import pathlib
import unittest

from wds_support import NODE, TempDirTest, output, run_node


def node_modules() -> str | None:
    """A node_modules folder with playwright and axe-core, or None."""
    candidates = [os.environ.get("WDS_NODE_MODULES", "")]
    candidates += os.environ.get("NODE_PATH", "").split(os.pathsep)
    for c in candidates:
        if c and (pathlib.Path(c) / "playwright").is_dir() and (pathlib.Path(c) / "axe-core").is_dir():
            return c
    return None


MODULES = node_modules()


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
        errors = self.rules(self.runtime(html, "--only", "contrast"))
        self.assertIn("contrast-under-overlay", errors)
        self.assertIn("contrast-too-low", errors)

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
        errors = self.rules(self.runtime(html, "--only", "taborder", "--only", "names"))
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
        findings = self.runtime(html, "--only", "taborder", "--only", "axe")
        errors = self.rules(findings)
        self.assertNotIn("focus-stuck", errors)
        axe_rules = {f.get("rule") for f in findings if f.get("check") == "axe"}
        self.assertTrue({"label", "button-name"} & axe_rules, axe_rules)


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

    def test_a_subtle_fill_change_against_the_baseline_is_caught(self):
        proc = self.snapshot(self.sheet(hover="0.04"), "--update-baselines")
        self.assertEqual(proc.returncode, 0, output(proc))
        proc = self.snapshot(self.sheet(hover="0.08"))          # hover twice as dark
        self.assertEqual(proc.returncode, 1, output(proc))
        self.assertIn("st_hover", output(proc))


if __name__ == "__main__":
    unittest.main()
