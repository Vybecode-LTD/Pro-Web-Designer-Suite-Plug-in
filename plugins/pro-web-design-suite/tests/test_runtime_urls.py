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
import threading
import unittest

from test_browser_runtime import MODULES, only
from wds_support import NODE, TempDirTest, output, run_node

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
        return self.send(404, PAGE.format(title="Not found", body="<p>Nothing here.</p>"))


class Served(TempDirTest):

    def setUp(self):
        super().setUp()
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Site)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.port = server.server_address[1]

    def url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    def node(self, skill, script, *args, codes=(0, 1)):
        proc = run_node(skill, script, *args, cwd=self.tmp, timeout=600,
                        env_changes={"NODE_PATH": MODULES})
        if b"no usable chromium" in proc.stdout.lower() + proc.stderr.lower():
            self.skipTest(output(proc)[-200:])
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
        # Each page against its own type: the strict one breaks its LCP limit,
        # the home page none. (A run with no LCP recorded also exits 1, as
        # macOS's headless shell did once in CI, so the breaches decide.)
        self.assertEqual([("home", []), ("strict", ["lcp"])],
                         [(r["pageType"], [b["metric"] for b in r["breaches"]]) for r in out["runs"]])
        self.assertEqual(1, out["runs"][1]["exit"])
        self.assertEqual(1, proc.returncode)


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
