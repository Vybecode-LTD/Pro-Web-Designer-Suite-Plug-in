"""P34 part 3 (GT-B4): the gates that open a URL run several pages and
viewports in one report.

A run covered one URL at one viewport, so a site's other templates went
unaudited, and a11y ran only at 1280x900, where a phone's menu button and
its target size are hidden. --urls takes a file of URLs, a JSON list (with a
perf page type for each) or a sitemap, and a11y_runtime's --viewports a list
of sizes; each run is the gate on one page at one size, in a child process,
and the report holds a row for each, its exit the worst of them.

A local server plays a clean page, one with an image with no alt, one whose
menu button has no name at a phone's width only, a sitemap, a sitemap index
and a missing page. The browser tests skip unless Node and Playwright are
available; the option checks need only Node.
"""
from __future__ import annotations

import http.server
import json
import subprocess
import threading
import time
import unittest

from test_browser_runtime import MODULES, only
from wds_support import NODE, TempDirTest, keep_evidence, no_browser, output, run_node

PAGE = ("<!doctype html><html lang=en><head><title>{title}</title>"
        "<meta name=viewport content='width=device-width'></head><body><main>"
        "<h1>{title}</h1>{body}</main></body></html>")
NAV = ("<style>.burger{display:none}@media (max-width:600px){.burger{display:inline-block}"
       ".links{display:none}}</style><nav aria-label=Site><button class=burger type=button>"
       "<svg width=24 height=24 aria-hidden=true></svg></button>"
       "<span class=links><a href='/about'>About us</a></span></nav>")


class Site(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, status, body, kind="text/html; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        base = f"http://127.0.0.1:{self.server.server_address[1]}"
        if path == "/clean.html":
            return self.send(200, PAGE.format(title="Clean", body="<p>Plain words on a plain page.</p>"))
        if path == "/broken.html":
            return self.send(200, PAGE.format(title="Broken", body=(
                "<img src='data:image/gif;base64,R0lGODlhAQABAAAAACw=' width=40 height=40>")))
        if path == "/nav.html":
            return self.send(200, PAGE.format(title="Nav", body=NAV))
        if path == "/twice.html":
            return self.send(200, PAGE.format(title="Twice", body=(
                "<p><a href='/a'>Read the pricing notes</a></p><p><a href='/b'>Read the pricing notes</a></p>")))
        if path == "/sitemap.xml":
            return self.send(200, "<?xml version='1.0' encoding='UTF-8'?>"
                                  "<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>"
                                  f"<url><loc>{base}/clean.html?a=1&amp;b=2</loc></url>"
                                  f"<url><loc>\n  {base}/broken.html\n</loc></url></urlset>",
                             "application/xml")
        if path == "/index.xml":
            return self.send(200, "<?xml version='1.0'?><sitemapindex><sitemap>"
                                  f"<loc>{base}/sitemap.xml</loc></sitemap></sitemapindex>",
                             "application/xml")
        if path == "/slow-font.html":
            return self.send(200, SLOW_FONT.format(font=f"{base}/never.woff2"))
        if path == "/lazy-frame.html":
            # A lazy iframe far below the fold has no document yet (L8's cause).
            return self.send(200, PAGE.format(title="Lazy frame", body=(
                "<p>Above the fold.</p><div style='height:6000px'></div>"
                "<iframe loading=lazy title='Below the fold' src='/clean.html'></iframe>")))
        if path == "/never.woff2":
            # Accepted and never answered, until the test ends: the font
            # request webawesome.com's phone layout left pending (L8).
            self.server.release.wait(120)
            return None
        return self.send(404, PAGE.format(title="Not found", body="<p>Nothing here.</p>"))


# A page whose load handler asks for a font the server never sends, so
# `load` fires and document.fonts.ready never settles (JS-B-1).
SLOW_FONT = ("<!doctype html><html lang=en><head><title>Slow font</title>"
             "<meta name=viewport content='width=device-width'>"
             "<style>@font-face{{font-family:Never;src:url({font}) format('woff2')}}</style></head>"
             "<body><main data-cell-id='link--st_default'><h1>Slow font</h1>"
             "<p><a href='/clean.html'>Read the clean page</a></p></main>"
             "<script>addEventListener('load', () => {{ document.body.style.fontFamily = 'Never, sans-serif';"
             " document.body.offsetWidth; }});</script></body></html>")


class Served(TempDirTest):

    def setUp(self):
        super().setUp()
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Site)
        server.release = threading.Event()
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.addCleanup(server.release.set)          # first: a held request lets go
        self.port = server.server_address[1]

    def url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    def node(self, skill, script, *args, codes=(0, 1)):
        try:
            proc = run_node(skill, script, *args, cwd=self.tmp, timeout=600,
                            env_changes={"NODE_PATH": MODULES})
        except subprocess.TimeoutExpired:
            # TEST-5: alone a run takes seconds; beside a build at 100 % CPU
            # one ran out the 600 s, and the error was only TimeoutExpired.
            self.fail(f"{script} timed out at 600 s: the machine was too busy to run it")
        if b"no usable chromium" in proc.stdout.lower() + proc.stderr.lower():
            no_browser(self, output(proc)[-200:])
        self.assertIn(proc.returncode, codes, output(proc))
        return proc

    def a11y(self, *args, codes=(0, 1)):
        proc = self.node("a11y-audit-runner", "a11y_runtime.mjs", "--json", *args, codes=codes)
        return proc.returncode, json.loads(proc.stdout)


def errors(run):
    return {f["rule"] for f in run["report"]["findings"] if f["severity"] == "error"}


@unittest.skipUnless(NODE and MODULES, "needs node plus WDS_NODE_MODULES pointing at playwright and axe-core")
class TheAuditRunsEveryPage(Served):

    def test_each_page_listed_runs_and_the_exit_is_the_worst(self):
        listed = self.write("urls.txt", f"# the templates\n{self.url('/clean.html')}\n\n"
                                        f"{self.url('/broken.html')}\n{self.url('/clean.html')}\n")
        code, out = self.a11y("--urls", str(listed), *only("axe"))
        self.assertEqual(1, code)
        self.assertEqual(1, out["exit"])
        self.assertEqual([(self.url("/clean.html"), 0), (self.url("/broken.html"), 1)],
                         [(r["url"], r["exit"]) for r in out["runs"]])
        self.assertEqual(set(), errors(out["runs"][0]))
        self.assertIn("image-alt", errors(out["runs"][1]))

    def test_a_phone_width_finds_what_the_desktop_hides(self):
        code, out = self.a11y("--url", self.url("/nav.html"), "--viewports", "390x844,1280x900",
                              *only("names"))
        self.assertEqual(["390x844", "1280x900"], [r["viewport"] for r in out["runs"]])
        phone, desktop = out["runs"]
        self.assertIn("no-accessible-name", errors(phone))
        self.assertEqual(set(), errors(desktop))
        self.assertEqual("390x844@1x", phone["report"]["viewport"])
        self.assertEqual(1, code)

    def test_a_sitemap_lists_the_pages(self):
        code, out = self.a11y("--urls", self.url("/sitemap.xml"), *only("axe"))
        self.assertEqual([self.url("/clean.html?a=1&b=2"), self.url("/broken.html")],
                         [r["url"] for r in out["runs"]])
        proc = self.node("a11y-audit-runner", "a11y_runtime.mjs", "--urls", self.url("/index.xml"),
                         codes=(2,))
        self.assertIn("sitemap index", output(proc))

    def test_a_page_that_cannot_be_reached_fails_its_own_row(self):
        listed = self.write("urls.json", json.dumps([self.url("/clean.html"), self.url("/missing.html")]))
        code, out = self.a11y("--urls", str(listed), *only("axe"), codes=(2,))
        self.assertEqual([0, 2], [r["exit"] for r in out["runs"]])
        self.assertIn("HTTP 404", out["runs"][1]["error"])
        self.assertEqual(2, out["exit"])

    def test_a_run_that_fails_on_its_budget_alone_says_why(self):
        """Codex on #166: a run that broke its budget with warnings alone
        exited 1 and printed nothing under its row."""
        budget = self.write("a11y-budget.json", json.dumps({"duplicate_names": 0}))
        proc = self.node("a11y-audit-runner", "a11y_runtime.mjs", "--url", self.url("/twice.html"),
                         "--viewports", "1280x900", "--budget", str(budget), *only("names"))
        self.assertEqual(1, proc.returncode)
        self.assertIn("budget duplicate_names: 1 > 0", proc.stdout.decode("utf-8"))

    def test_pages_past_the_cap_are_counted_not_dropped(self):
        listed = self.write("urls.txt", f"{self.url('/clean.html')}\n{self.url('/nav.html')}\n")
        proc = self.node("a11y-audit-runner", "a11y_runtime.mjs", "--urls", str(listed), "--max-urls", "1",
                         *only("axe"))
        text = proc.stdout.decode("utf-8")
        self.assertIn(self.url("/clean.html"), text)
        self.assertNotIn(self.url("/nav.html"), text)
        self.assertIn("1 more URL(s)", text)


@unittest.skipUnless(NODE and MODULES, "needs node plus WDS_NODE_MODULES pointing at playwright")
class EachPageHasItsTypesBudget(Served):

    def test_a_page_type_picks_the_budget_its_page_is_held_to(self):
        budget = self.write("perf-budget.json", json.dumps({
            "$schema": "perf-budget-gate/1", "defaults": {"lab": {"lcp_ms": 60000}},
            "pages": {"strict": {"lab": {"lcp_ms": 1}}}}))
        listed = self.write("urls.json", json.dumps([
            {"url": self.url("/clean.html"), "pageType": "home"},
            {"url": self.url("/nav.html"), "pageType": "strict"}]))
        proc = self.node("perf-budget-gate", "measure_vitals.mjs", "--urls", str(listed), "--budget",
                         str(budget), "--runs", "1", "--settle", "500", "--throttle", "off", "--json")
        out = json.loads(proc.stdout)
        keep_evidence(self, "vitals", out)
        runs = out["runs"]
        measured = [{k: r[k] for k in ("pageType", "lcp", "exit", "error")} for r in runs]
        self.assertTrue(all(r["report"] for r in runs), measured)
        # Each page is held to its own type's budget, read from its report, not
        # inferred from a breach: on macOS CI a run that recorded no LCP broke
        # no budget, and the strict page passed (TEST-5, P66).
        self.assertEqual([("home", {"lcp_ms": 60000}), ("strict", {"lcp_ms": 1})],
                         [(r["pageType"], r["report"]["budget"]) for r in runs], measured)
        for r in runs:
            with self.subTest(page=r["pageType"]):
                # A page that painted has an LCP: the run waits for one past
                # its settle (P66), so none here is the gate's failure.
                self.assertIsNotNone(r["lcp"], r["report"]["perRun"])
                # The verdict is the recorded number's, against that budget.
                breaks = r["lcp"] > r["report"]["budget"]["lcp_ms"]
                self.assertEqual(["lcp"] if breaks else [], [b["metric"] for b in r["breaches"]], measured)
                self.assertEqual(int(breaks), r["exit"], measured)
        self.assertEqual([0, 1], [r["exit"] for r in runs], measured)   # the strict one breaks, the home one not
        self.assertEqual(1, proc.returncode)


@unittest.skipUnless(NODE and MODULES, "needs node plus WDS_NODE_MODULES pointing at playwright and axe-core")
class TheGatesBoundTheirWaits(Served):
    """P74 (L8, JS-B-1, JS-B-2, JS-B-6): a font the server accepts and never
    sends kept document.fonts.ready pending, and each of the three gates that
    awaited it hung for ever after its `browser:` line; the focus check's
    screenshots then waited 30 s each and reported nothing. A run here gets 60
    s, and must end in 30 with the reason said."""

    LIMIT = 60

    def bounded(self, skill, script, *args, extra_env=None):
        started = time.monotonic()
        try:
            proc = run_node(skill, script, *args, cwd=self.tmp, timeout=self.LIMIT,
                            env_changes={"NODE_PATH": MODULES, **(extra_env or {})})
        except subprocess.TimeoutExpired:
            self.fail(f"{script} was still waiting after {self.LIMIT} s: an unbounded wait")
        if b"no usable chromium" in proc.stdout.lower() + proc.stderr.lower():
            no_browser(self, output(proc)[-200:])
        return proc, time.monotonic() - started

    def test_the_audit_goes_on_without_the_font_and_says_so(self):
        proc, took = self.bounded("a11y-audit-runner", "a11y_runtime.mjs", "--url", self.url("/slow-font.html"),
                                  "--json", *only("focus"))
        self.assertIn(proc.returncode, (0, 1), output(proc))
        out = json.loads(proc.stdout)
        self.assertIn("fonts-still-loading", [f["rule"] for f in out["findings"]])
        self.assertLess(took, 30)
        # The focus shots no longer wait for the font: the link was measured.
        self.assertTrue(out["focusTable"] and all(r["normal"] is not None for r in out["focusTable"]),
                        out["focusTable"])
        self.assertNotIn("focus-not-measured", [f["rule"] for f in out["findings"]])

    def test_the_critique_goes_on_without_the_font_and_says_so(self):
        proc, took = self.bounded("design-critique-gate", "critique_snapshots.mjs", self.url("/slow-font.html"),
                                  "--out", "shots", "--json")
        self.assertEqual(0, proc.returncode, output(proc))
        warnings = json.loads(proc.stdout)["warnings"]
        self.assertTrue(any("web fonts were still loading" in w for w in warnings), warnings)
        self.assertLess(took, 30)

    def test_the_matrix_goes_on_without_the_font_and_says_so(self):
        sheet = self.write("sheet.html", SLOW_FONT.format(font=self.url("/never.woff2")))
        proc, took = self.bounded("component-state-matrix", "snapshot_matrix.mjs", str(sheet), "--out", "report",
                                  "--baselines", "base", "--update-baselines")
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertIn("web fonts were still loading", proc.stdout.decode("utf-8"))
        self.assertIn("web fonts were still loading", (self.tmp / "report" / "index.html").read_text(encoding="utf-8"))
        self.assertLess(took, 30)

    def test_a_frame_with_no_document_yet_is_said_not_awaited(self):
        """L8's cause, found on webawesome.com at 390x844: axe's injection
        awaited addScriptTag in a lazy iframe that had no document, for ever."""
        proc, took = self.bounded("a11y-audit-runner", "a11y_runtime.mjs", "--url", self.url("/lazy-frame.html"),
                                  "--viewport", "390x844", "--json", *only("axe"))
        self.assertIn(proc.returncode, (0, 1), output(proc))
        found = [f for f in json.loads(proc.stdout)["findings"] if f["rule"] == "frames-not-audited"]
        self.assertEqual(1, len(found), output(proc))
        self.assertEqual(1, len(found[0]["frames"]))
        self.assertLess(took, 30)

    def test_a_focus_shot_that_fails_is_said_never_passed(self):
        """JS-B-2: each failed shot's error was kept on its row and dropped,
        so a check that measured nothing reported nothing."""
        proc, _ = self.bounded("a11y-audit-runner", "a11y_runtime.mjs", "--url", self.url("/twice.html"),
                               "--json", *only("focus"), extra_env={"A11Y_SHOT_TIMEOUT": "1"})
        self.assertIn(proc.returncode, (0, 1), output(proc))
        out = json.loads(proc.stdout)
        unmeasured = [f for f in out["findings"] if f["rule"] == "focus-not-measured"]
        self.assertEqual(1, len(unmeasured), out["findings"])
        self.assertEqual("warning", unmeasured[0]["severity"])
        self.assertEqual(2, unmeasured[0]["count"])
        self.assertEqual(2, out["counters"]["focus_not_measured"])
        self.assertEqual(0, out["counters"]["focus_invisible"])

    def test_a_proof_sheet_lists_only_the_checks_it_ran(self):
        """JS-B-6: `ran` named the page-only checks on a proof sheet, so a
        budget on them passed at 0 for checks that never ran."""
        sheet = self.write("sheet.html", "<!doctype html><html lang=en><title>Sheet</title><main>"
                                         "<div data-cell-id='button--st_default'><button>Go</button></div>"
                                         "</main></html>")
        proc, _ = self.bounded("a11y-audit-runner", "a11y_runtime.mjs", "--matrix", str(sheet), "--json",
                               "--skip", "axe", "--skip", "forced")
        self.assertIn(proc.returncode, (0, 1), output(proc))
        out = json.loads(proc.stdout)
        page_only = ["taborder", "reflow", "spacing", "obscured", "hover", "motion"]
        self.assertEqual([], [c for c in out["ran"] if c in page_only], out["ran"])
        self.assertEqual(page_only, out["notRun"]["checks"])
        self.assertIn("names", out["ran"])


@unittest.skipUnless(NODE, "node is not installed")
class TheListsAreReadFirst(TempDirTest):

    def refused(self, skill, script, *args):
        proc = run_node(skill, script, *args, cwd=self.tmp, timeout=60)
        self.assertEqual(2, proc.returncode, output(proc))
        return output(proc)

    def test_each_mistake_is_named(self):
        urls = self.write("urls.txt", "http://127.0.0.1:9/a.html\nnot a url\n")
        good = self.write("good.txt", "http://127.0.0.1:9/a.html\n")
        a11y = ("a11y-audit-runner", "a11y_runtime.mjs")
        cases = [
            (a11y, ("--urls", str(good), "--url", "http://127.0.0.1:9/b.html"), "instead of --url"),
            (a11y, ("--url", "http://127.0.0.1:9/", "--viewports", "390"), "390x844,1280x900"),
            (a11y, ("--url", "http://127.0.0.1:9/", "--viewports", "390x844", "--viewport", "1280x900"),
             "give one of them"),
            (a11y, ("--urls", str(urls)), '"not a url" is not an http(s) URL'),
            (a11y, ("--urls", str(self.tmp / "none.txt")), "no such file"),
            (a11y, ("--urls", str(good), "--max-urls", "0"), "--max-urls must be a whole number, at least 1"),
            (a11y, ("--urls", str(good), "--max-urls", "1.5"), "--max-urls must be a whole number, at least 1"),
            (("perf-budget-gate", "measure_vitals.mjs"), ("--urls", str(good), "--max-urls", "1.5"),
             "--max-urls must be a whole number, at least 1"),
            (("perf-budget-gate", "measure_vitals.mjs"), ("--urls", str(good), "http://127.0.0.1:9/"),
             "instead of a URL"),
        ]
        for (skill, script), args, said in cases:
            with self.subTest(args=args):
                self.assertIn(said, self.refused(skill, script, *args))

    def test_the_report_never_replaces_the_configured_budget(self):
        """Codex on #166: with no --budget, vitals' --urls checked its report
        against no budget, so a --report naming .design-suite.json's budget
        file overwrote it."""
        text = json.dumps({"$schema": "perf-budget-gate/1", "defaults": {"lab": {"lcp_ms": 2500}}})
        budget = self.write("perf-budget.json", text)
        self.write(".design-suite.json", json.dumps({"schema": 1, "budgets": {"perf": "perf-budget.json"}}))
        good = self.write("good.txt", "http://127.0.0.1:9/a.html\n")
        said = self.refused("perf-budget-gate", "measure_vitals.mjs", "--urls", str(good),
                            "--report", str(budget))
        self.assertIn("perf-budget.json", said)
        self.assertEqual(text, budget.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
