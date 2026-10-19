"""P35 part 2 (GT-B9): the runtime gate in engines other than Chromium.

Focus heuristics, the accessibility tree and the tab order differ by engine,
and a11y_runtime.mjs ran in Chromium alone. `--engine firefox|webkit` runs
axe, the computed names and the real tab order in the build the locked
Playwright pins; the checks that measure pixels, emulate forced colours, read
closed roots through Chromium's DevTools protocol or were calibrated in
Chromium stay Chromium's, and the report says which did not run. WebKit's
Tab skips a link with no tabindex, as Safari does by default, so its tab
order expects none. An engine whose build is not installed (or, on Windows,
whose unsigned build the system will not start) is skipped.
"""
from __future__ import annotations

import json
import unittest

from test_browser_runtime import MODULES
from wds_support import NODE, TempDirTest, output, run_node

PAGE = ("<!doctype html><html lang=en><head><meta charset=utf-8><title>Engines</title></head>"
        "<body><main><h1>Engines</h1>"
        "<a href='#one'>One</a> <button type=button>Two</button> "
        "<input aria-label='Three'> <a href='#four' tabindex='0'>Four</a> "
        "<button type=button class=bare><svg width=16 height=16 aria-hidden=true></svg></button> "
        "<a href='#five' tabindex='3'>Five</a>"
        "</main></body></html>")
SHARED = ["axe", "names", "taborder"]


@unittest.skipUnless(NODE and MODULES, "needs node plus WDS_NODE_MODULES pointing at "
                                       "playwright and axe-core")
class EachEngine(TempDirTest):

    def runtime(self, *args):
        page = self.write("page.html", PAGE)
        proc = run_node("a11y-audit-runner", "a11y_runtime.mjs", "--file", page, "--json", *args,
                        cwd=self.tmp, env_changes={"NODE_PATH": MODULES}, timeout=300)
        if proc.returncode == 2 and b"no usable" in proc.stderr:
            self.skipTest("engine not installed or not startable here: " + output(proc)[-240:])
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return json.loads(proc.stdout)

    def rules(self, report):
        return {f["rule"] for f in report["findings"]}

    def test_firefox_and_webkit_run_the_three_shared_checks(self):
        for engine in ("firefox", "webkit"):
            with self.subTest(engine=engine):
                report = self.runtime("--engine", engine)
                self.assertEqual(engine, report["engine"])
                self.assertEqual(SHARED, report["ran"])
                rules = self.rules(report)
                self.assertTrue({"button-name", "no-accessible-name",
                                 "positive-tabindex-order"} <= rules, report["findings"])
                note = [f for f in report["findings"] if f["rule"] == "checks-run-in-chromium-only"]
                self.assertEqual(1, len(note))
                self.assertEqual("warning", note[0]["severity"])
                self.assertIn("focus", note[0]["checks"])
                self.assertNotIn("axe", note[0]["checks"])

    def test_webkit_expects_no_tab_stop_on_a_bare_link(self):
        """WebKit's Tab, like Safari's by default, passes over a link with no
        tabindex: not unreachable. A link with tabindex=0 is a stop there, and
        is reached."""
        report = self.runtime("--engine", "webkit")
        self.assertNotIn("unreachable-control", self.rules(report), report["findings"])
        stops = {s["sel"] for s in report["tabOrder"]}
        self.assertIn("html > body > main > a:nth-of-type(2)", stops)
        self.assertNotIn("html > body > main > a:nth-of-type(1)", stops)

    def test_chromium_is_the_default_and_says_nothing_of_engines(self):
        report = self.runtime("--skip", "forced", "--skip", "motion", "--skip", "hover")
        self.assertEqual("chromium", report["engine"])
        self.assertNotIn("checks-run-in-chromium-only", self.rules(report))
        self.assertIn("focus", report["ran"])
        # Chromium's Tab reaches every link.
        stops = {s["sel"] for s in report["tabOrder"]}
        self.assertIn("html > body > main > a:nth-of-type(1)", stops)


@unittest.skipUnless(NODE, "node is not installed")
class TheEngineIsNamed(TempDirTest):

    def test_an_unknown_engine_is_refused_before_a_browser_is_looked_for(self):
        page = self.write("page.html", PAGE)
        proc = run_node("a11y-audit-runner", "a11y_runtime.mjs", "--file", page, "--engine", "safari",
                        cwd=self.tmp)
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertIn("chromium, firefox, webkit", output(proc))


if __name__ == "__main__":
    unittest.main()
