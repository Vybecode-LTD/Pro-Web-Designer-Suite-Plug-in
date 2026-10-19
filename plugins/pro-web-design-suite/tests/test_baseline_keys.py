"""N38: a11y_static's and perf_audit's baseline keys held the path as given,
with the platform's separator. /install-gate's CI template records the
baselines on Linux and runs the static gates on Windows too, so there every
baselined finding came back (`src\\page.html` against `src/page.html`), and a
baseline recorded on Windows failed Linux CI. audit_design fixed the same for
its own keys in 3.1.x; these two now write `/` and read either.
"""
from __future__ import annotations

import json
import os
import unittest

from wds_support import TempDirTest, output, run_py

PAGE = '<!doctype html>\n<html lang="en">\n<head><title>Home</title></head>\n<body>\n<main>\n{}\n</main>\n</body>\n</html>\n'
BUILT = ('<!doctype html><html lang="en"><head><title>Home</title><script src="app.js"></script></head>'
         '<body><img src="hero.png"></body></html>\n')


def with_sep(key, sep):
    """`key` as the platform with `sep` wrote it: only its path, before the
    first `|`, changes, whichever separator it was recorded with."""
    path, bar, rest = key.partition("|")
    return path.replace("\\", "/").replace("/", sep) + bar + rest


class A11yStaticKeys(TempDirTest):
    def setUp(self):
        super().setUp()
        self.write("src/pages/home.html", PAGE.format('<img src="hero.png">'))

    def run_a11y(self, *args):
        return run_py("a11y-audit-runner", "a11y_static", *args, cwd=self.tmp)

    def recorded(self):
        proc = self.run_a11y("src", "--write-baseline", "baseline.json")
        self.assertEqual(0, proc.returncode, output(proc))
        keys = json.loads((self.tmp / "baseline.json").read_text(encoding="utf-8"))
        self.assertTrue(keys)
        return keys

    def test_a_recorded_key_uses_slashes(self):
        self.assertEqual(["src/pages/home.html"], sorted({k.split("|")[0] for k in self.recorded()}))

    def test_a_baseline_from_either_platform_holds(self):
        """Keys as Windows wrote them, and as Linux did: each suppresses the
        finding here, whatever this platform is."""
        keys = self.recorded()
        for sep in ("\\", "/"):
            with self.subTest(sep=sep):
                written = [with_sep(k, sep) for k in keys]
                (self.tmp / "baseline.json").write_text(json.dumps(written), encoding="utf-8")
                proc = self.run_a11y("src", "--baseline", "baseline.json", "--strict")
                self.assertEqual(0, proc.returncode, output(proc))

    def test_a_path_with_dot_slash_matches(self):
        self.recorded()
        proc = self.run_a11y("./src", "--baseline", "baseline.json", "--strict")
        self.assertEqual(0, proc.returncode, output(proc))


class PerfAuditKeys(TempDirTest):
    def setUp(self):
        super().setUp()
        self.write("dist/shop/index.html", BUILT)
        self.write("dist/shop/app.js", "console.log(1);\n")

    def run_perf(self, *args):
        return run_py("perf-budget-gate", "perf_audit", *args, "--no-ledger", cwd=self.tmp)

    def recorded(self):
        proc = self.run_perf("dist", "--write-baseline", "baseline.json")
        self.assertEqual(0, proc.returncode, output(proc))
        data = json.loads((self.tmp / "baseline.json").read_text(encoding="utf-8"))
        self.assertTrue(data["findings"])
        return data

    def test_a_recorded_key_uses_slashes(self):
        self.assertEqual(["dist/shop/index.html"], sorted({k.split("|")[0] for k in self.recorded()["findings"]}))

    def test_a_baseline_from_either_platform_holds(self):
        data = self.recorded()
        for sep in ("\\", "/"):
            with self.subTest(sep=sep):
                written = {**data, "findings": [with_sep(k, sep) for k in data["findings"]]}
                (self.tmp / "baseline.json").write_text(json.dumps(written), encoding="utf-8")
                proc = self.run_perf("dist", "--baseline", "baseline.json", "--strict")
                self.assertEqual(0, proc.returncode, output(proc))

    def test_the_plain_list_form_too(self):
        """A plain list of keys, audit_design's form, is read the same way."""
        keys = [with_sep(k, "/" if os.sep == "\\" else "\\") for k in self.recorded()["findings"]]   # the other platform's
        (self.tmp / "baseline.json").write_text(json.dumps(keys), encoding="utf-8")
        proc = self.run_perf("dist", "--baseline", "baseline.json", "--strict")
        self.assertEqual(0, proc.returncode, output(proc))


if __name__ == "__main__":
    unittest.main()
