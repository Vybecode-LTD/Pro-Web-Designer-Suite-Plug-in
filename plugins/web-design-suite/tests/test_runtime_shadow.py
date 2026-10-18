"""P34 part 2 (GT-B3): the runtime checks read through shadow roots.

querySelectorAll and a TreeWalker stop at a shadow root, so the names,
contrast, tab-stop and focus checks never saw a web component's controls:
only axe, which reads open roots itself, did. browser_common's DEEP_DOM walks
the composed tree, through every open root and every closed one the page
kept (a script's, through its wrapped attachShadow; the parser's, through
the DevTools protocol), and cssPath() names an element inside one host by
host with ' >> '.

The fixture holds each kind of root: an open one with an unnamed button,
faint text and a link with no focus ring; a component inside a component; a
closed root a script attaches; a closed root the HTML declares; a link
slotted onto a dark background that only the shadow tree paints; and a
disclosure inside a root, driven by a keymap that names it through the
boundary. The browser tests skip unless Node and Playwright are available.
"""
from __future__ import annotations

import json
import subprocess
import unittest

from test_browser_runtime import MODULES, only
from wds_support import NODE, PLUGIN, TempDirTest, env, output, run_node

ICON = "<svg width=16 height=16 aria-hidden=true></svg>"
PAGE = (
    "<!doctype html><html lang=en><head><title>Components</title>"
    "<style>body{font:16px sans-serif;background:#fff;color:#111}</style></head><body><main>"
    "<h1>Components</h1>"
    "<x-card></x-card>"
    "<x-outer></x-outer>"
    "<x-locked></x-locked>"
    "<x-decl><template shadowrootmode=closed><style>button{font:16px sans-serif}</style>"
    f"<button class=declared>{ICON}</button>"
    "<p style='color:#c8c8c8'>Declared faint words</p></template></x-decl>"
    "<x-slotbox><a href='#slotted'>Slotted link text</a></x-slotbox>"
    "<x-disc></x-disc>"
    "<script>"
    "const card = document.querySelector('x-card').attachShadow({mode: 'open'});"
    "card.innerHTML = '<style>.faint{color:#bbb}a.bare:focus{outline:none}"
    "button{font:16px sans-serif}</style><p class=faint>Faint card words here</p>"
    f"<button class=icon>{ICON}</button> <a class=bare href=\"#bare\">Card link</a>';"
    "const outer = document.querySelector('x-outer').attachShadow({mode: 'open'});"
    "outer.innerHTML = '<div class=frame><x-inner></x-inner></div>';"
    "outer.querySelector('x-inner').attachShadow({mode: 'open'}).innerHTML ="
    f" '<button class=deep>{ICON}</button>';"
    "document.querySelector('x-locked').attachShadow({mode: 'closed'}).innerHTML ="
    f" '<button class=locked>{ICON}</button><p style=\"color:#c0c0c0\">Locked faint words</p>';"
    "document.querySelector('x-slotbox').attachShadow({mode: 'open'}).innerHTML ="
    " '<style>::slotted(a){color:#fff}</style><div style=\"background:#111;padding:8px\">"
    "<slot></slot></div>';"
    "const disc = document.querySelector('x-disc').attachShadow({mode: 'open'});"
    "disc.innerHTML = '<button aria-expanded=false>More</button><p hidden>Details</p>';"
    "disc.querySelector('button').addEventListener('click', (e) => {"
    " const open = e.currentTarget.getAttribute('aria-expanded') === 'true';"
    " e.currentTarget.setAttribute('aria-expanded', String(!open));"
    " disc.querySelector('p').hidden = open; });"
    "</script></main></body></html>")


@unittest.skipUnless(NODE and MODULES, "needs node plus WDS_NODE_MODULES pointing at "
                                       "playwright and axe-core")
class TheChecksReadThroughShadowRoots(TempDirTest):

    def runtime(self, *args):
        page = self.write("components.html", PAGE)
        proc = run_node("a11y-audit-runner", "a11y_runtime.mjs", "--file", page, "--json", *args,
                        cwd=self.tmp, env_changes={"NODE_PATH": MODULES}, timeout=300)
        if proc.returncode == 2 and b"browser" in proc.stderr.lower():
            self.skipTest("no usable browser: " + output(proc)[-200:])
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return json.loads(proc.stdout)

    def where(self, report, rule):
        return [f.get("selector") or "" for f in report["findings"] if f["rule"] == rule]

    def test_an_unnamed_button_in_any_root_is_named_by_its_path(self):
        unnamed = self.where(self.runtime(*only("names")), "no-accessible-name")
        for path in ("x-card >> button.icon", "x-outer >> div.frame > x-inner >> button.deep",
                     "x-locked >> button.locked", "x-decl >> button.declared"):
            with self.subTest(path=path):
                self.assertTrue(any(s.endswith(path) for s in unnamed), unnamed)

    def test_faint_text_in_a_root_is_measured_on_the_background_the_tree_paints(self):
        report = self.runtime(*only("contrast"))
        low = [f["message"] for f in report["findings"] if f["rule"] == "contrast-too-low"]
        for words in ("Faint card words here", "Locked faint words", "Declared faint words"):
            with self.subTest(words=words):
                self.assertTrue(any(words in m for m in low), low)
        # White text slotted onto the shadow tree's dark band: measured on the
        # band, not on the white page behind the host.
        self.assertFalse(any("Slotted link text" in m for m in low), low)

    def test_tab_order_and_focus_reach_into_each_root(self):
        report = self.runtime(*only("taborder", "focus"))
        errors = [f for f in report["findings"] if f["severity"] == "error"]
        self.assertEqual(["no-visible-focus-indicator"], [f["rule"] for f in errors], errors)
        self.assertTrue(errors[0]["selector"].endswith("x-card >> a.bare"), errors)
        stops = [s["sel"] for s in report["tabOrder"]]
        for path in ("x-card >> a.bare", "x-locked >> button.locked", "x-decl >> button.declared",
                     "x-slotbox > a"):
            with self.subTest(path=path):
                self.assertTrue(any(s.endswith(path) for s in stops), stops)
        self.assertEqual([], self.where(report, "focus-order-jump"))

    def test_a_host_that_delegates_focus_is_not_a_stop_of_its_own(self):
        """Codex on #165: a tabindex="0" host whose root delegates focus was
        an expected stop that Tab never lands on, so the reachable button
        inside it read as an unreachable control."""
        page = self.write("delegates.html", (
            "<!doctype html><html lang=en><head><title>Delegates</title></head><body><main>"
            "<h1>Delegates</h1><x-field tabindex=0></x-field><a href='#after'>After</a>"
            "<script>document.querySelector('x-field').attachShadow({mode: 'open', delegatesFocus: true})"
            ".innerHTML = '<button>Choose a date</button>';</script></main></body></html>"))
        proc = run_node("a11y-audit-runner", "a11y_runtime.mjs", "--file", page, "--json",
                        *only("taborder"), cwd=self.tmp, env_changes={"NODE_PATH": MODULES}, timeout=300)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        report = json.loads(proc.stdout)
        self.assertEqual([], [f for f in report["findings"] if f["severity"] == "error"])
        stops = [s["sel"] for s in report["tabOrder"]]
        self.assertTrue(any(s.endswith("x-field >> button") for s in stops), stops)

    def test_a_keymap_names_a_control_through_the_boundary(self):
        keymap = self.write("keymap.json", json.dumps({"patterns": [
            {"name": "More", "pattern": "disclosure", "trigger": "x-disc >> button"}]}))
        report = self.runtime(*only("keys"), "--keymap", str(keymap))
        self.assertEqual([], report["findings"], report["findings"])

    def test_the_report_counts_the_roots_and_none_is_left_unread(self):
        report = self.runtime(*only("names"))
        self.assertEqual({"open": 5, "closed": 2, "unread": 0}, report["shadowRoots"])
        self.assertEqual([], self.where(report, "closed-shadow-roots-unread"))


# keepClosedRoots() on a page with no DEEP_DOM to keep its root, and on a
# page whose browser offers no DevTools protocol; then what unreadRoots()
# says of each, and of a page whose roots were all kept.
UNREAD_JS = """
const common = await import(process.argv[2]);
const { chromium } = await common.loadPlaywright((m) => { console.error(m); process.exit(2); }, '');
const launched = await common.launchBrowser(chromium);
if (!launched.browser) { console.error('no usable chromium: ' + launched.tried.join('; ')); process.exit(3); }
const page = await launched.browser.newPage();
await page.setContent('<x-decl><template shadowrootmode=closed><button>Go</button></template></x-decl>');
const missed = await common.keepClosedRoots(page);
const noProtocol = { context: () => ({ newCDPSession: async () => { throw new Error('no protocol'); } }) };
const none = await common.keepClosedRoots(noProtocol);
await launched.browser.close();
console.log(JSON.stringify({ missed, none, notes: [common.unreadRoots(missed), common.unreadRoots(none),
                                                   common.unreadRoots({ closed: 2, kept: 2 })] }));
"""


@unittest.skipUnless(NODE and MODULES, "needs node plus WDS_NODE_MODULES pointing at playwright")
class ARootNoCheckReadIsSaid(TempDirTest):

    def test_a_closed_root_not_kept_and_a_browser_without_the_protocol_are_named(self):
        probe = self.write("unread.mjs", UNREAD_JS)
        proc = subprocess.run([NODE, probe, (PLUGIN / "shared" / "browser_common.mjs").as_uri()],
                              cwd=self.tmp, env=env(NODE_PATH=MODULES), capture_output=True, timeout=180)
        if proc.returncode == 3:
            self.skipTest(output(proc))
        self.assertEqual(proc.returncode, 0, output(proc))
        seen = json.loads(proc.stdout)
        self.assertEqual({"closed": 1, "kept": 0}, seen["missed"])
        self.assertIsNone(seen["none"])
        missed, none, kept = seen["notes"]
        self.assertEqual("1 closed shadow root(s) could not be read", missed)
        self.assertIn("could not be listed", none)
        self.assertIsNone(kept)


@unittest.skipUnless(NODE and MODULES, "needs node plus WDS_NODE_MODULES pointing at playwright")
class TheCritiqueReadsThroughShadowRoots(TempDirTest):

    def test_the_contrast_table_holds_text_in_every_root(self):
        page = self.write("components.html", PAGE)
        out = self.tmp / "shots"
        proc = run_node("design-critique-gate", "critique_snapshots.mjs", str(page), "--out", str(out),
                        "--settle", "0", "--json", cwd=self.tmp, env_changes={"NODE_PATH": MODULES},
                        timeout=300)
        if proc.returncode == 2 and b"chromium" in proc.stderr.lower():
            self.skipTest(output(proc)[-200:])
        self.assertIn(proc.returncode, (0, 1), output(proc))
        report = json.loads(proc.stdout)
        below = {(r["text"], r["background"]) for r in report["contrast"] if r["passes"] is False}
        for fg in ("#bbbbbb", "#c0c0c0", "#c8c8c8"):
            with self.subTest(fg=fg):
                self.assertIn((fg, "#ffffff"), below)
        self.assertNotIn(("#ffffff", "#ffffff"), below)
        self.assertEqual([], [w for w in report["warnings"] if "shadow" in w])


if __name__ == "__main__":
    unittest.main()
