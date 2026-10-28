"""P34 part 1 (GT-B1, GT-B2): the gates that open a URL reach a page that
needs a wait, steps, a session or a header (browser_common.mjs: --wait-for,
--steps, --storage-state and --header).

A local server plays each part: a page that renders its content late, one
behind a form, one that answers only a session cookie, one that answers only
a header, and a second origin that records what it was sent, so a header that
leaks to a third party is seen. The browser tests skip unless Node and
Playwright are available; the option checks need only Node.
"""
from __future__ import annotations

import http.server
import json
import threading
import unittest

from test_browser_runtime import MODULES, only
from wds_support import NODE, TempDirTest, no_browser, output, run_node

TOKEN = "s3cret-token"
# An image with no alt: axe's image-alt, so the audit says which page it read.
NO_ALT = "<img id=shot src=data:image/gif;base64,R0lGODlhAQABAAAAACw= width=40 height=40>"
PAGE = ("<!doctype html><html lang=en><head><title>{title}</title></head><body><main>"
        "<h1>{title}</h1>{body}</main></body></html>")
STATE = {"cookies": [{"name": "wds_session", "value": "ok", "domain": "127.0.0.1", "path": "/",
                      "expires": -1, "httpOnly": False, "secure": False, "sameSite": "Lax"}],
         "origins": []}


class Recorder(http.server.BaseHTTPRequestHandler):
    """The second origin: it answers anything, and records each request's
    headers."""
    seen: list = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        self.seen.append({k.lower(): v for k, v in self.headers.items()})
        self.send_response(200)
        self.send_header("Content-Type", "text/javascript")
        self.end_headers()
        self.wfile.write(b"window.probed = true;")


class Site(http.server.BaseHTTPRequestHandler):
    other = 0
    hits: list = []

    def log_message(self, *args):
        pass

    def page(self, status, html):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        session = "wds_session=ok" in (self.headers.get("Cookie") or "")
        self.hits.append((path, session))
        if path == "/late.html":
            # The content arrives four seconds after load, as a client-rendered app's does.
            script = ("<script>setTimeout(() => { document.getElementById('app').innerHTML ="
                      " `<p id=late style=\"font-size:72px\">Every plan, every price, on one page.</p>"
                      f"{NO_ALT}`; }}, 4000);</script>")
            return self.page(200, PAGE.format(title="Late", body="<div id=app></div>" + script))
        if path == "/form.html":
            script = ("<script>document.getElementById('go').addEventListener('click', () => {"
                      " if (document.getElementById('q').value === 'plans')"
                      f" document.getElementById('out').innerHTML = '{NO_ALT}'; }});</script>")
            body = ("<label>Search <input id=q></label> <button id=go>Show</button>"
                    "<div id=out></div>" + script)
            return self.page(200, PAGE.format(title="Form", body=body))
        if path == "/private.html":
            if not session:
                self.send_response(302)
                self.send_header("Location", "/login.html")
                self.end_headers()
                return None
            return self.page(200, PAGE.format(title="Account",
                                              body="<p id=account style='font-size:72px'>Your plans</p>" + NO_ALT))
        if path == "/login.html":
            return self.page(200, PAGE.format(title="Sign in", body="<p>Sign in to continue.</p>"))
        if path == "/staff.html":
            if self.headers.get("X-Wds-Token") != TOKEN:
                return self.page(401, PAGE.format(title="No", body="<p>Not for you.</p>"))
            probe = f"<script src='http://127.0.0.1:{self.other}/probe.js'></script>"
            return self.page(200, PAGE.format(title="Staff", body=NO_ALT + probe))
        return self.page(404, PAGE.format(title="Missing", body=""))


class Served(TempDirTest):
    """Two servers on two ports, so two origins."""

    def setUp(self):
        super().setUp()
        Recorder.seen = []
        Site.hits = []
        self.recorder = self.serve(Recorder)
        Site.other = self.recorder.server_address[1]
        self.site = self.serve(Site)

    def serve(self, handler):
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server

    def url(self, path):
        return f"http://127.0.0.1:{self.site.server_address[1]}{path}"

    def json(self, name, data):
        return str(self.write(name, json.dumps(data)))

    def node(self, skill, script, *args, env=None, codes=(0, 1)):
        proc = run_node(skill, script, *args, cwd=self.tmp, timeout=300,
                        env_changes={"NODE_PATH": MODULES, **(env or {})})
        if proc.returncode == 2 and b"no usable chromium" in proc.stderr.lower():
            no_browser(self, output(proc)[-200:])
        self.assertIn(proc.returncode, codes, output(proc))
        return proc

    def axe_rules(self, path, *args, env=None):
        proc = self.node("a11y-audit-runner", "a11y_runtime.mjs", "--url", self.url(path), "--json",
                         *only("axe"), *args, env=env)
        return {f["rule"] for f in json.loads(proc.stdout)["findings"] if f["severity"] == "error"}


@unittest.skipUnless(NODE and MODULES, "needs node plus WDS_NODE_MODULES pointing at playwright and axe-core")
class TheAuditReachesThePage(Served):

    def test_wait_for_audits_what_the_page_renders_late(self):
        """GT-B1: at `load` a client-rendered page is an empty shell."""
        self.assertNotIn("image-alt", self.axe_rules("/late.html"))           # the shell
        self.assertIn("image-alt", self.axe_rules("/late.html", "--wait-for", "#shot"))

    def test_steps_reach_a_state_behind_a_form(self):
        steps = [{"fill": "#q", "value": "plans"}, {"click": "#go"}, {"wait-for": "#out img"}]
        self.assertNotIn("image-alt", self.axe_rules("/form.html"))
        self.assertIn("image-alt", self.axe_rules("/form.html", "--steps", self.json("steps.json", steps)))
        # A value read from the environment, so a password stays out of the file.
        steps[0] = {"fill": "#q", "env": "WDS_TEST_QUERY"}
        self.assertIn("image-alt", self.axe_rules("/form.html", "--steps", self.json("env.json", steps),
                                                  env={"WDS_TEST_QUERY": "plans"}))

    def test_a_session_reaches_the_signed_in_page(self):
        """GT-B2: without the session the audit reads the sign-in page."""
        self.assertNotIn("image-alt", self.axe_rules("/private.html"))
        self.assertIn("image-alt", self.axe_rules("/private.html", "--storage-state",
                                                  self.json("state.json", STATE)))
        self.assertIn(("/private.html", True), Site.hits)

    def test_a_header_goes_to_the_pages_origin_only(self):
        """GT-B2: a staging host's header, never sent to a third party."""
        proc = self.node("a11y-audit-runner", "a11y_runtime.mjs", "--url", self.url("/staff.html"),
                         "--json", *only("axe"), codes=(2,))
        self.assertIn("HTTP 401", output(proc))
        rules = self.axe_rules("/staff.html", "--header", "X-Wds-Token: env:WDS_TEST_TOKEN",
                               env={"WDS_TEST_TOKEN": TOKEN})
        self.assertIn("image-alt", rules)
        self.assertTrue(Recorder.seen, "the page's third-party script was never requested")
        for seen in Recorder.seen:
            with self.subTest(seen=seen):
                self.assertNotIn("x-wds-token", seen)

    def test_a_step_that_cannot_run_stops_the_run(self):
        proc = self.node("a11y-audit-runner", "a11y_runtime.mjs", "--url", self.url("/form.html"), "--json",
                         *only("axe"), "--steps", self.json("steps.json", [{"click": "#missing"}]), codes=(2,))
        self.assertIn("step 1 (click #missing) failed", output(proc))


@unittest.skipUnless(NODE and MODULES, "needs node plus WDS_NODE_MODULES pointing at playwright")
class TheOtherGatesReachThePage(Served):

    def lcp(self, path, *args):
        proc = self.node("perf-budget-gate", "measure_vitals.mjs", self.url(path), "--runs", "1",
                         "--settle", "500", "--json", *args)
        return json.loads(proc.stdout)["lcpSelector"] or ""

    def test_vitals_measure_the_signed_in_page_and_the_late_content(self):
        self.assertNotIn("account", self.lcp("/private.html"))
        self.assertIn("account", self.lcp("/private.html", "--storage-state", self.json("state.json", STATE)))
        self.assertNotIn("late", self.lcp("/late.html"))
        self.assertIn("late", self.lcp("/late.html", "--wait-for", "#late"))

    def test_an_error_status_is_never_measured(self):
        """A session that has expired answers 401: vitals measured the error
        page, and the critique captured it, as if it were the page."""
        for skill, script, args in (("perf-budget-gate", "measure_vitals.mjs", ["--runs", "1"]),
                                    ("design-critique-gate", "critique_snapshots.mjs",
                                     ["--out", str(self.tmp / "shots")])):
            with self.subTest(script=script):
                proc = self.node(skill, script, self.url("/staff.html"), *args, codes=(2,))
                self.assertIn("HTTP 401", output(proc))

    def test_critique_captures_the_signed_in_page(self):
        out = self.tmp / "shots"
        self.node("design-critique-gate", "critique_snapshots.mjs", self.url("/private.html"), "--out",
                  str(out), "--storage-state", self.json("state.json", STATE), "--wait-for", "#account",
                  "--settle", "0")
        self.assertTrue((out / "1440.png").exists())
        served = [hit for hit in Site.hits if hit[0] in ("/private.html", "/login.html")]
        self.assertEqual(6, len(served), served)             # two widths, three modes
        self.assertTrue(all(hit == ("/private.html", True) for hit in served), served)


@unittest.skipUnless(NODE, "node is not installed")
class TheOptionsAreReadFirst(TempDirTest):
    """Every option is checked before a browser starts, each mistake named
    (exit 2), so a run never audits a page other than the one asked for."""

    def refused(self, skill, script, *args, env=None):
        proc = run_node(skill, script, *args, cwd=self.tmp, timeout=60, env_changes=env or {})
        self.assertEqual(2, proc.returncode, output(proc))
        return output(proc)

    def test_each_mistake_is_named(self):
        page = str(self.write("page.html", PAGE.format(title="p", body="")))
        cases = (
            ([{"click": "#a", "fill": "#b"}], "exactly one of"),
            ({"click": "#a"}, "a JSON list"),
            ([{"fill": "#q"}], "one of value and env"),
            ([{"fill": "#q", "env": "WDS_NOT_SET_ANYWHERE"}], "has no WDS_NOT_SET_ANYWHERE"),
            ([{"click": "#a", "timeout": "5"}], "does not take timeout"),
            ([{"goto": ""}], "not an empty one"),
            ([5], "is not an object"),
        )
        for steps, message in cases:
            with self.subTest(steps=steps):
                self.write("steps.json", json.dumps(steps))
                self.assertIn(message, self.refused("a11y-audit-runner", "a11y_runtime.mjs", "--file", page,
                                                    "--steps", "steps.json"))
        self.write("state.json", json.dumps({"cookies": {}}))
        self.assertIn("not Playwright's storageState",
                      self.refused("a11y-audit-runner", "a11y_runtime.mjs", "--file", page,
                                   "--storage-state", "state.json"))
        for args, message in ((("--header", "no colon"), 'takes "Name: value"'),
                              (("--header", "X-A: 1"), "needs an http(s) URL"),
                              (("--wait-for", "#a", "--wait-for", "#b"), "given twice"),
                              (("--header", "X-A: 1", "--header", "x-a: 2"), "given twice")):
            with self.subTest(args=args):
                self.assertIn(message, self.refused("a11y-audit-runner", "a11y_runtime.mjs", "--file", page, *args))
        self.assertIn("has no WDS_NOT_SET_ANYWHERE",
                      self.refused("a11y-audit-runner", "a11y_runtime.mjs", "--url", "http://127.0.0.1:9/",
                                   "--header", "X-A: env:WDS_NOT_SET_ANYWHERE"))

    def test_vitals_refuse_what_would_change_the_load_they_measure(self):
        self.write("steps.json", json.dumps([{"click": "#a"}]))
        self.assertIn("--storage-state", self.refused("perf-budget-gate", "measure_vitals.mjs",
                                                      "http://127.0.0.1:9/", "--steps", "steps.json"))
        self.assertIn("cache", self.refused("perf-budget-gate", "measure_vitals.mjs", "http://127.0.0.1:9/",
                                            "--header", "X-A: 1"))

    def test_critique_names_its_mistakes_too(self):
        page = str(self.write("page.html", PAGE.format(title="p", body="")))
        self.write("steps.json", json.dumps([{"press": "Enter", "on": ""}]))
        self.assertIn("not an empty one", self.refused("design-critique-gate", "critique_snapshots.mjs", page,
                                                       "--steps", "steps.json"))


if __name__ == "__main__":
    unittest.main()
