"""The three Playwright scripts: finding Playwright, axe-core and a browser.

Regressions covered:
- Playwright installed in the project under test was never found: a bare
  import() only searches upward from the script, which lives in the plugin.
- `npm root -g` was run with execFileSync, which cannot start npm.cmd on
  Windows, so a global install was never found there either.
- With no --browser the scripts insisted on /opt/pw-browsers/chromium, a path
  that only exists in the claude.ai sandbox, instead of a browser the machine has.
- A browser that exists but will not start (Playwright's own Chromium on some
  Windows machines: "side-by-side configuration is incorrect") ended the run
  instead of the next browser being tried; an explicit one that would not start
  crashed instead of exiting 2 ("no usable browser").
- axe's fix text was cut at exactly 300 characters, mid-word, straight into the URL.
- GT-A5: no context bypassed the page's Content-Security-Policy, so a strict
  one refused the injected freeze stylesheet, and the crash exited 1, the code
  for violations.

A stub `playwright` module stands in for the real one: its launch() prints the
executable it was given and exits 42, or throws for the executables listed in
STUB_FAIL_LAUNCH ("default" = Playwright's own choice), so no browser is needed.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unittest

from wds_support import NODE, NPM, PLUGIN, SKILLS, TempDirTest, env, output, run_node

STUB_PLAYWRIGHT = """\
export const chromium = {
  executablePath() { return process.env.STUB_MANAGED_BROWSER || '/nonexistent/stub-chromium'; },
  async launch(opts) {
    const exe = opts.executablePath ?? null;
    const failing = (process.env.STUB_FAIL_LAUNCH || '').split('|');
    if (failing.includes(exe ?? 'default')) {
      throw new Error('side-by-side configuration is incorrect');
    }
    process.stdout.write('STUB-LAUNCH ' + JSON.stringify(exe) + '\\n');
    process.exit(42);
  },
};
export default { chromium };
"""

# A browser that starts, prints the options of each context it is asked for,
# and then fails the way an unexpected error inside the run does.
STUB_CRASHING_CONTEXT = """\
const crash = async () => { throw new Error('STUB-CRASH'); };
export const chromium = {
  executablePath() { return '/nonexistent/stub-chromium'; },
  async launch() {
    return {
      async newContext(opts) {
        process.stdout.write('STUB-CONTEXT ' + JSON.stringify(opts ?? {}) + '\\n');
        return { addInitScript: crash, newPage: crash, async close() {} };
      },
      async close() {},
    };
  },
};
export default { chromium };
"""

SCRIPTS = {
    "snapshot_matrix": ("component-state-matrix", "snapshot_matrix.mjs"),
    "measure_vitals": ("perf-budget-gate", "measure_vitals.mjs"),
    "a11y_runtime": ("a11y-audit-runner", "a11y_runtime.mjs"),
}
BROWSER_ENV = {"MATRIX_CHROMIUM": None, "PERF_CHROMIUM": None, "A11Y_CHROMIUM": None,
               "STUB_FAIL_LAUNCH": None}
SANDBOX_BROWSER = "/opt/pw-browsers/chromium"


def installed_browsers():
    """Mirror of installedBrowsers() in the scripts, filtered to what exists here."""
    if sys.platform == "win32":
        roots = [os.environ.get(k) for k in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")]
        paths = [os.path.join(r, *parts) for r in roots if r for parts in
                 (("Google", "Chrome", "Application", "chrome.exe"),
                  ("Microsoft", "Edge", "Application", "msedge.exe"))]
    elif sys.platform == "darwin":
        paths = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                 "/Applications/Chromium.app/Contents/MacOS/Chromium",
                 "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]
    else:
        paths = ["/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome",
                 "/usr/bin/google-chrome-stable", "/snap/bin/chromium", "/usr/bin/microsoft-edge"]
    return [p for p in paths if os.path.exists(p)]


@unittest.skipUnless(NODE, "node is not installed")
class BrowserScriptResolution(TempDirTest):

    def setUp(self):
        super().setUp()
        self.page = self.write("proj/page.html", "<!doctype html><title>t</title><main>hi</main>")
        self.fake_browser = self.write("fake-browser.exe", "not really a browser")
        self.empty_prefix = self.tmp / "empty-npm-prefix"
        self.empty_prefix.mkdir()

    def plant_stubs(self, node_modules):
        self.write(f"{node_modules}/playwright/index.mjs", STUB_PLAYWRIGHT)
        self.write(f"{node_modules}/axe-core/axe.min.js", "window.axe = {};")

    def args_for(self, name):
        if name == "snapshot_matrix":
            return [self.page, "--baselines", self.tmp / "baselines", "--out", self.tmp / "report"]
        if name == "measure_vitals":
            return [self.page]
        return ["--file", self.page]

    def run_script(self, name, *extra, cwd, env_changes):
        skill, script = SCRIPTS[name]
        return run_node(skill, script, *self.args_for(name), *extra, cwd=cwd,
                        env_changes={**BROWSER_ENV, **env_changes})

    @staticmethod
    def launched(proc):
        return json.loads(output(proc).split("STUB-LAUNCH ", 1)[1].splitlines()[0])

    def test_playwright_is_found_in_the_projects_node_modules(self):
        self.plant_stubs("proj/node_modules")
        (self.tmp / "proj" / "src").mkdir()
        for name in SCRIPTS:
            with self.subTest(script=name):
                proc = self.run_script(
                    name, "--browser", self.fake_browser, cwd=self.tmp / "proj" / "src",
                    env_changes={"NODE_PATH": None, "npm_config_prefix": str(self.empty_prefix)})
                self.assertEqual(proc.returncode, 42, output(proc))
                self.assertIn("STUB-LAUNCH", output(proc))

    def test_without_a_browser_playwrights_own_is_tried_first(self):
        self.plant_stubs("proj/node_modules")
        expected = SANDBOX_BROWSER if os.path.exists(SANDBOX_BROWSER) else None
        for name in SCRIPTS:
            with self.subTest(script=name):
                proc = self.run_script(
                    name, cwd=self.tmp / "proj",
                    env_changes={"NODE_PATH": str(self.tmp / "proj" / "node_modules")})
                self.assertEqual(proc.returncode, 42, output(proc))
                self.assertEqual(self.launched(proc), expected)

    @unittest.skipUnless(installed_browsers(), "no Chrome or Edge installed to fall back to")
    def test_a_browser_that_will_not_start_falls_back_to_chrome_or_edge(self):
        self.plant_stubs("proj/node_modules")
        for name in SCRIPTS:
            with self.subTest(script=name):
                proc = self.run_script(
                    name, cwd=self.tmp / "proj",
                    env_changes={"NODE_PATH": str(self.tmp / "proj" / "node_modules"),
                                 "STUB_MANAGED_BROWSER": str(self.fake_browser),
                                 "STUB_FAIL_LAUNCH": f"default|{self.fake_browser}"})
                self.assertEqual(proc.returncode, 42, output(proc))
                self.assertIn(self.launched(proc), installed_browsers())

    def test_an_explicit_browser_that_is_missing_or_will_not_start_exits_2(self):
        self.plant_stubs("proj/node_modules")
        cases = {"missing": (self.tmp / "no-such-browser.exe", ""),
                 "will not start": (self.fake_browser, str(self.fake_browser))}
        for name in SCRIPTS:
            for label, (browser, failing) in cases.items():
                with self.subTest(script=name, case=label):
                    proc = self.run_script(
                        name, "--browser", browser, cwd=self.tmp / "proj",
                        env_changes={"NODE_PATH": str(self.tmp / "proj" / "node_modules"),
                                     "STUB_FAIL_LAUNCH": failing})
                    self.assertEqual(proc.returncode, 2, output(proc))
                    self.assertIn(browser.name, output(proc))

    @unittest.skipUnless(NPM, "npm is not installed")
    def test_playwright_is_found_in_npms_global_folder(self):
        prefix = self.tmp / "npm-prefix"
        prefix.mkdir()
        global_root = subprocess.run("npm root -g", shell=True, capture_output=True, text=True,
                                     encoding="utf-8", env=env(npm_config_prefix=str(prefix))
                                     ).stdout.strip()
        self.assertTrue(global_root, "npm root -g printed nothing")
        rel = os.path.relpath(global_root, self.tmp)
        self.plant_stubs(rel)
        elsewhere = self.tmp / "unrelated-cwd"
        elsewhere.mkdir()
        for name in SCRIPTS:
            with self.subTest(script=name):
                extra = ["--browser", self.fake_browser]
                if name == "a11y_runtime":
                    extra += ["--axe", self.tmp / rel / "axe-core" / "axe.min.js"]
                proc = self.run_script(name, *extra, cwd=elsewhere,
                                       env_changes={"NODE_PATH": None, "npm_config_prefix": str(prefix)})
                self.assertEqual(proc.returncode, 42, output(proc))

    def test_every_context_bypasses_csp_and_a_crash_exits_2(self):
        """GT-A5: a page served with `Content-Security-Policy: default-src
        'self'` refused the injected freeze stylesheet, and the error left
        through the last-resort handler as exit 1, which means violations.
        Every context now bypasses the page's CSP, and a run that fails
        exits 2: a crash is never a finding."""
        self.write("proj/node_modules/playwright/index.mjs", STUB_CRASHING_CONTEXT)
        self.write("proj/node_modules/axe-core/axe.min.js", "window.axe = {};")
        for name in SCRIPTS:
            with self.subTest(script=name):
                proc = self.run_script(
                    name, "--browser", self.fake_browser, cwd=self.tmp / "proj",
                    env_changes={"NODE_PATH": str(self.tmp / "proj" / "node_modules")})
                self.assertEqual(proc.returncode, 2, output(proc))
                self.assertIn("STUB-CRASH", output(proc))
                contexts = [json.loads(line.split(" ", 1)[1])
                            for line in output(proc).splitlines() if line.startswith("STUB-CONTEXT ")]
                self.assertTrue(contexts, output(proc))
                self.assertEqual([], [c for c in contexts if c.get("bypassCSP") is not True])


class ContextOptions(unittest.TestCase):
    """GT-A5: the stub above sees only the contexts a script opens before it
    fails, so every `newContext(` call in the source is held to it too."""

    def test_every_new_context_bypasses_csp(self):
        for name, (skill, script) in SCRIPTS.items():
            text = (SKILLS / skill / "scripts" / script).read_text(encoding="utf-8")
            calls = re.findall(r"\.newContext\((\{.*?\})?\)", text, re.S)
            with self.subTest(script=name):
                self.assertTrue(calls)
                self.assertEqual([], [c or "(no options)" for c in calls
                                      if not re.search(r"\bbypassCSP: true\b", c)])


@unittest.skipUnless(NODE, "node is not installed")
class AxeFixText(unittest.TestCase):

    def test_long_fix_text_is_cut_at_a_word_and_marked(self):
        src = (SKILLS / "a11y-audit-runner" / "scripts" / "a11y_runtime.mjs").read_text(encoding="utf-8")
        helper = re.search(r"^function clip\(.*?^\}\n", src, re.S | re.M)
        self.assertIsNotNone(helper, "a11y_runtime.mjs has no clip() helper")
        js = helper.group(0) + (
            "console.log(JSON.stringify([clip('Element has no title attribute Element does "
            "not have text that is visible to screen readers', 40), clip('short', 40)]));")
        proc = subprocess.run([NODE, "-e", js], capture_output=True, env=env())
        clipped, short = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(clipped, "Element has no title attribute Element …")
        self.assertEqual(short, "short")


SHARED = PLUGIN / "shared" / "browser_common.mjs"
MOVED = ("loadPlaywright", "npmGlobalRoot", "nodeModulesAbove", "launchBrowser", "installedBrowsers",
         "readJsonFile")


class SharedHelpers(unittest.TestCase):
    """P9 (GT-C13): each browser script carried its own copy of the browser
    resolution, the freeze CSS and the JSON reader, and the copies drifted:
    a11y_runtime shortened animations without pausing them, and read no
    JSONC. Now each skill has a byte-identical copy of the master beside its
    script."""

    def scripts(self):
        return {name: (SKILLS / skill / "scripts" / script) for name, (skill, script) in SCRIPTS.items()}

    def test_every_skills_copy_is_the_master_copy(self):
        copies = sorted(SKILLS.glob("*/scripts/browser_common.mjs"))
        self.assertEqual(sorted(s.parent / "browser_common.mjs" for s in self.scripts().values()), copies)
        master = SHARED.read_bytes()
        self.assertEqual([], [p.relative_to(PLUGIN).as_posix() for p in copies if p.read_bytes() != master],
                         "copy shared/browser_common.mjs over these")

    def test_no_script_restates_a_shared_helper(self):
        for name, script in self.scripts().items():
            text = script.read_text(encoding="utf-8")
            with self.subTest(script=name):
                self.assertIn("from './browser_common.mjs';", text)
                self.assertEqual([], [f for f in MOVED if re.search(rf"^(?:async )?function {f}\(", text, re.M)])
                self.assertNotRegex(text, r"\bconst DEFAULT_BROWSER\b")
                self.assertNotRegex(text, r"animation-duration\s*:")

    def test_the_freeze_pauses_animations(self):
        """A shortened animation that still runs moves between two screenshots."""
        common = SHARED.read_text(encoding="utf-8")
        freeze = re.search(r"FREEZE_ANIMATIONS_CSS = `(.*?)`", common, re.S).group(1)
        self.assertIn("animation-play-state: paused !important", freeze)
        for name in ("a11y_runtime", "snapshot_matrix"):
            with self.subTest(script=name):
                self.assertIn("FREEZE_ANIMATIONS_CSS", self.scripts()[name].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
