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

CI installs the engines on Linux, where one that will not start fails. Their
system packages come from the Actions cache when it has them (P61, N55).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from unittest import mock

from test_browser_runtime import MODULES
from wds_support import NODE, REPO, TempDirTest, env, output, run_node

GIT = shutil.which("git")

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
            # CI installs the engines on Linux and sets WDS_REQUIRE_ENGINES, so a
            # broken install fails there instead of passing as a skip.
            if os.environ.get("WDS_REQUIRE_ENGINES"):
                self.fail("WDS_REQUIRE_ENGINES is set and the engine did not start: " +
                          output(proc)[-400:])
            self.skipTest("engine not installed or not startable here: " + output(proc)[-240:])
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return json.loads(proc.stdout)

    def rules(self, report):
        return {f["rule"] for f in report["findings"]}

    def shared_checks(self, engine):
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

    def test_firefox_runs_the_three_shared_checks(self):
        self.shared_checks("firefox")

    def test_webkit_runs_the_three_shared_checks(self):
        self.shared_checks("webkit")

    def test_an_engine_that_skips_bare_links_is_read_not_assumed(self):
        """WebKit's Windows and macOS builds pass over a link with no tabindex,
        as Safari does by default; its Linux build does not (CI on #183). The
        run reads which: links all reached and no note, or none reached and
        `engine-skips-links`. Never `unreachable-control` either way, and a
        link with tabindex=0 is a stop on both."""
        report = self.runtime("--engine", "webkit")
        self.assertNotIn("unreachable-control", self.rules(report), report["findings"])
        stops = {s["sel"] for s in report["tabOrder"]}
        self.assertIn("html > body > main > a:nth-of-type(2)", stops)
        bare = "html > body > main > a:nth-of-type(1)" in stops
        self.assertEqual(not bare, "engine-skips-links" in self.rules(report), report["findings"])

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


def ci_workflow() -> str | None:
    """ci.yml as the revision under test has it: at WDS_PLUGIN_REV when
    tools/fail_before.py names one, else in the checkout around the tests."""
    rev = os.environ.get("WDS_PLUGIN_REV")
    if rev:
        if not (REPO and GIT):
            return None
        proc = subprocess.run([GIT, "show", f"{rev}:.github/workflows/ci.yml"], cwd=REPO,
                              capture_output=True, env=env())
        return proc.stdout.decode("utf-8") if proc.returncode == 0 else None
    path = REPO / ".github" / "workflows" / "ci.yml" if REPO else None
    return path.read_text(encoding="utf-8") if path and path.is_file() else None


class CiKeepsTheEnginesPackages(unittest.TestCase):
    """P61 (N55): the engines' system libraries are about 120 MB of .deb
    files, and the runners' apt mirror sometimes sent them at 50 kB/s, so two
    Ubuntu jobs ran into the 45-minute timeout. apt keeps them in a folder the
    Actions cache restores before the install and saves after it, under a key
    named by the files, so a run downloads only the packages that changed."""

    @classmethod
    def setUpClass(cls):
        text = ci_workflow()
        if text is None:
            raise unittest.SkipTest("the repository's workflows are not here")
        cls.steps = text.split("\n  validate:\n", 1)[0].split("\n      - ")

    def step(self, needle):
        found = [i for i, s in enumerate(self.steps) if needle in s]
        self.assertEqual(1, len(found), f"one step of the suite job holds {needle!r}")
        return found[0], self.steps[found[0]]

    def test_apt_keeps_its_packages_where_the_cache_restores_and_saves_them(self):
        at, config = self.step("Dir::Cache::Archives")
        folder = re.search(r'Dir::Cache::Archives "([^"]+?)/?"', config).group(1)
        restore_at, restore = self.step("id: debs-restored")
        install_at, _ = self.step("install --only-shell --with-deps")
        name_at, _ = self.step("apt-get autoclean")
        save_at, save = self.step("steps.debs.outputs.key }}")
        self.assertEqual([at, restore_at, install_at, name_at, save_at],
                         sorted([at, restore_at, install_at, name_at, save_at]))
        for step, text in (("restore", restore), ("save", save)):
            with self.subTest(step=step):
                self.assertRegex(text, rf"(?m)^\s+path: {re.escape(folder)}/\*\.deb$")
        for step, text in (("config", config), ("restore", restore), ("save", save),
                           ("name", self.steps[name_at])):
            with self.subTest(step=step):
                self.assertRegex(text, r"(?m)^\s+if: runner\.os == 'Linux'")

    def test_a_run_saves_only_when_the_packages_changed(self):
        _, restore = self.step("id: debs-restored")
        name_at, name = self.step("apt-get autoclean")
        _, save = self.step("steps.debs.outputs.key }}")
        restore_id = re.search(r"(?m)^\s+id: (\S+)$", restore).group(1)
        name_id = re.search(r"(?m)^\s+id: (\S+)$", name).group(1)
        key = re.search(r"(?m)^\s+key: (.+)$", restore).group(1)
        self.assertRegex(restore, rf"(?m)^\s+restore-keys: {re.escape(key)}-$")
        self.assertRegex(name, r'echo "key=\$WDS_DEBS-\$\(')
        self.assertIn(f"key: ${{{{ steps.{name_id}.outputs.key }}}}", save)
        self.assertIn(f"steps.{name_id}.outputs.key != steps.{restore_id}.outputs.cache-matched-key",
                      save)

    def test_an_engine_that_will_not_start_still_fails_on_linux(self):
        _, install = self.step("install --only-shell --with-deps")
        self.assertIn("--with-deps chromium firefox webkit", install)
        _, suite = self.step("name: The suite")
        self.assertIn("WDS_REQUIRE_ENGINES: ${{ runner.os == 'Linux' && '1' || '' }}", suite)


class AnEngineThatWillNotStart(TempDirTest):
    """What EachEngine does with the runner's `no usable` exit, with no
    browser needed: a skip, unless WDS_REQUIRE_ENGINES is set, as CI sets it
    on Linux (P61; CodeRabbit on #208)."""

    runtime = EachEngine.runtime

    def refused(self):
        proc = subprocess.CompletedProcess([], 2, b"", b"a11y_runtime: no usable webkit build\n")
        return mock.patch.object(sys.modules[__name__], "run_node", return_value=proc)

    def test_it_fails_when_the_engines_are_required(self):
        # A skip raised here would report this test as skipped, not failed.
        with self.refused(), mock.patch.dict(os.environ, {"WDS_REQUIRE_ENGINES": "1"}):
            try:
                self.runtime("--engine", "webkit")
            except unittest.SkipTest as skip:
                self.fail(f"skipped while the engines are required: {skip}")
            except self.failureException as failure:
                self.assertIn("no usable webkit build", str(failure))
            else:
                self.fail("returned while the engine did not start")

    def test_it_is_skipped_otherwise(self):
        with self.refused(), mock.patch.dict(os.environ):
            os.environ.pop("WDS_REQUIRE_ENGINES", None)
            with self.assertRaises(unittest.SkipTest):
                self.runtime("--engine", "webkit")


if __name__ == "__main__":
    unittest.main()
