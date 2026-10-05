"""crux_check.py: the field p75 against the lab median (GT-B5, GT-C11).

perf-budget-gate's SKILL.md gives the trigger for re-deriving the lab
profile, "field p75 more than 1.5x your lab median", and nothing measured
it. These tests never touch the network: they read a response in the shape
the CrUX API documents, from a file or from a local server that stands in for
the API and records what it was sent.
"""
from __future__ import annotations

import http.server
import json
import threading
import unittest
import urllib.parse

from wds_support import TempDirTest, output, run_py

# The documented response shape: p75 per metric, CLS as a string.
RESPONSE = {"record": {
    "key": {"formFactor": "PHONE", "origin": "https://shop.example"},
    "metrics": {
        "largest_contentful_paint": {"percentiles": {"p75": 4200}},
        "cumulative_layout_shift": {"percentiles": {"p75": "0.05"}},
        "first_contentful_paint": {"percentiles": {"p75": 1800}},
        "experimental_time_to_first_byte": {"percentiles": {"p75": 900}},
        "interaction_to_next_paint": {"percentiles": {"p75": 180}},
    },
    "collectionPeriod": {"firstDate": {"year": 2026, "month": 9, "day": 6},
                         "lastDate": {"year": 2026, "month": 10, "day": 3}},
}}
# A measure_vitals --report: no INP, since nothing interacted.
LAB = {"throttle": "lighthouse", "stats": {
    "lcp": {"median": 2400}, "cls": {"median": 0.04}, "fcp": {"median": 1500},
    "ttfb": {"median": 700}, "tbt": {"median": 120}, "inp": None}}
KEY = "k-test-not-a-real-key-123"


class FakeCrux(http.server.BaseHTTPRequestHandler):
    status = 200
    body = RESPONSE
    seen: list = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        type(self).seen.append((self.path, json.loads(self.rfile.read(length))))
        payload = json.dumps(self.body).encode("utf-8")
        self.send_response(self.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


class CruxCheck(TempDirTest):

    def setUp(self):
        super().setUp()
        self.write("vitals.json", json.dumps(LAB))
        self.write("crux.json", json.dumps(RESPONSE))

    def check(self, *args, env=None):
        return run_py("perf-budget-gate", "crux_check", "--origin", "https://shop.example",
                      "--lab", "vitals.json", *args, cwd=self.tmp,
                      env_changes={"CRUX_API_KEY": None, "CRUX_API_URL": None, **(env or {})})

    def serve(self, status, body):
        handler = type("Handler", (FakeCrux,), {"status": status, "body": body, "seen": []})
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        url = f"http://127.0.0.1:{server.server_address[1]}/v1/records:queryRecord"
        return handler, {"CRUX_API_KEY": KEY, "CRUX_API_URL": url}

    def test_a_field_p75_past_the_ratio_fails(self):
        proc = self.check("--response", "crux.json")
        self.assertEqual(proc.returncode, 1, output(proc))
        self.assertRegex(output(proc), r"LCP\s+field\s+4200ms\s+lab\s+2400ms\s+1\.75x\s+above")
        self.assertRegex(output(proc), r"CLS\s+field\s+0\.050\s+lab\s+0\.040\s+1\.25x\s+within")
        self.assertNotIn("INP", output(proc))                 # no lab INP to compare
        self.assertNotIn("TBT", output(proc))                 # no field TBT

    def test_within_the_ratio_passes(self):
        proc = self.check("--response", "crux.json", "--ratio", "2", "--json")
        self.assertEqual(proc.returncode, 0, output(proc))
        report = json.loads(proc.stdout)
        self.assertEqual(report["above"], [])
        self.assertEqual({r["metric"] for r in report["rows"]}, {"lcp", "cls", "fcp", "ttfb"})

    def test_the_query_sends_the_key_and_never_prints_it(self):
        handler, env = self.serve(200, RESPONSE)
        proc = self.check(env=env)
        self.assertEqual(proc.returncode, 1, output(proc))
        path, body = handler.seen[0]
        self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlsplit(path).query)["key"], [KEY])
        self.assertEqual(body["origin"], "https://shop.example")
        self.assertEqual(body["formFactor"], "PHONE")
        self.assertIn("largest_contentful_paint", body["metrics"])
        self.assertNotIn(KEY, output(proc))

    def test_a_refusal_and_no_data_exit_2_without_the_key(self):
        for status, body, needle in (
                (403, {"error": {"code": 403, "message": "API key not valid."}}, "API key not valid"),
                (404, {"error": {"code": 404, "message": "chrome ux report data not found"}},
                 "holds no data")):
            with self.subTest(status=status):
                _, env = self.serve(status, body)
                proc = self.check(env=env)
                self.assertEqual(proc.returncode, 2, output(proc))
                self.assertIn(needle, output(proc))
                self.assertNotIn(KEY, output(proc))

    def test_the_key_comes_from_the_environment_only(self):
        proc = self.check()
        self.assertEqual(proc.returncode, 2, output(proc))
        self.assertIn("CRUX_API_KEY", output(proc))
        for args in (("--key", KEY), ("--api-key=" + KEY,)):
            with self.subTest(args=args[0][:9]):
                proc = self.check(*args)
                self.assertEqual(proc.returncode, 2, output(proc))
                self.assertIn("never from an argument", output(proc))
                self.assertNotIn(KEY, output(proc))


if __name__ == "__main__":
    unittest.main()
