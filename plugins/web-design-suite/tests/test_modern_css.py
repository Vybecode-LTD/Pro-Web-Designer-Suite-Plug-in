"""The modern CSS web-design-studio's references teach, run in a browser (3.6.0).

Each test takes the CSS a reference shows, as written, puts it on the
starter's tokens, and checks in Chromium that it does what the prose says.
The audit already holds every snippet to the gate (test_doc_snippets); this
holds the claims to the browser.

Regressions covered:
- SS-B4 (P38): accessibility.md gave a modal dialog `z-index: var(--z-modal)`
  and a toast `--z-toast`, as if the ladder reached the top layer. A toast
  at z-index 500 renders under an open modal. A popover shown after the
  dialog renders over it, but only one inside the dialog can be clicked
  and reached by a screen reader: the modal makes the rest inert. And the
  field's error state used only
  `aria-invalid`: `:user-invalid` marks the browser's own checks once the
  user has touched the field, not on load.
"""
from __future__ import annotations

import json
import re
import subprocess
import unittest

from wds_support import NODE, PLUGIN, SKILLS, TempDirTest, env, output, tool_modules

STUDIO = SKILLS / "web-design-studio"
TOKENS = STUDIO / "assets" / "starter" / "styles" / "tokens.css"
MODULES = tool_modules("WDS_NODE_MODULES", "playwright", node_path=True)

# Opens the page and runs one scenario; each prints the facts it measured.
PROBE_JS = """
import { readFileSync } from 'node:fs';
const common = await import(process.argv[2]);
const { chromium } = await common.loadPlaywright((m) => { console.error(m); process.exit(2); }, '');
const launched = await common.launchBrowser(chromium);
if (!launched.browser) { console.error('no usable chromium: ' + launched.tried.join('; ')); process.exit(3); }
const page = await launched.browser.newPage({ viewport: { width: 1000, height: 700 } });
await page.setContent(readFileSync(process.argv[3], 'utf8'));
const hitAt = (sel) => page.evaluate((s) => {
  const r = document.querySelector(s).getBoundingClientRect();
  const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  return hit ? (hit.id || hit.tagName) : null;
}, sel);
const colour = (sel, prop) => page.evaluate(([s, p]) => getComputedStyle(document.querySelector(s))[p], [sel, prop]);
const out = {};
if (process.argv[4] === 'top-layer') {
  out.before = await hitAt('#ztoast');
  await page.evaluate(() => document.getElementById('dialog').showModal());
  out.underModal = await hitAt('#ztoast');
  await page.evaluate(() => { for (const id of ['outside', 'inside']) document.getElementById(id).showPopover(); });
  await page.waitForTimeout(400);
  out.outside = await hitAt('#outside');
  out.inside = await hitAt('#inside');
  out.open = await page.evaluate(() => ['outside', 'inside'].map((id) => document.getElementById(id).matches(':popover-open')));
  out.rect = await page.evaluate(() => {
    const r = document.getElementById('inside').getBoundingClientRect();
    return { right: innerWidth - r.right, bottom: innerHeight - r.bottom, left: r.left, top: r.top };
  });
  // Chromium's own accessibility tree: what a screen reader can reach.
  const cdp = await page.context().newCDPSession(page);
  const { nodes } = await cdp.send('Accessibility.getFullAXTree');
  out.heard = nodes.filter((n) => !n.ignored && n.name && /^Saved (inside|outside)$/.test(n.name.value))
    .map((n) => n.name.value);
} else {
  const read = async () => ({ border: await colour('#email', 'borderTopColor'), help: await colour('.field-help', 'color') });
  out.want = { border: await colour('#want-border', 'color'), help: await colour('#want-help', 'color') };
  out.onLoad = await read();
  await page.click('#email');
  await page.keyboard.type('not an address');
  await page.click('#after');
  out.touched = await read();
}
await launched.browser.close();
console.log(JSON.stringify(out));
"""


def reference_block(name: str, needle: str) -> str:
    """The ```css block in a web-design-studio reference that holds `needle`."""
    text = (STUDIO / "references" / name).read_text(encoding="utf-8")
    blocks = [b for b in re.findall(r"```css\n(.*?)```", text, flags=re.S) if needle in b]
    if len(blocks) != 1:
        raise AssertionError(f"{name}: {len(blocks)} css blocks hold {needle!r}")
    return blocks[0]


@unittest.skipUnless(NODE and MODULES, "needs node plus WDS_NODE_MODULES pointing at playwright")
class TheReferencesInABrowser(TempDirTest):

    def run_probe(self, body: str, css: str, scenario: str) -> dict:
        html = (f"<!doctype html><style>{TOKENS.read_text(encoding='utf-8')}\n{css}</style>{body}")
        page = self.write("page.html", html)
        probe = self.write("probe.mjs", PROBE_JS)
        proc = subprocess.run([NODE, probe, (PLUGIN / "shared" / "browser_common.mjs").as_uri(), page, scenario],
                              cwd=self.tmp, env=env(NODE_PATH=MODULES), capture_output=True, timeout=180)
        if proc.returncode == 3:
            self.skipTest(output(proc))
        self.assertEqual(proc.returncode, 0, output(proc))
        return json.loads(proc.stdout)

    def test_a_toast_on_the_ladder_sits_under_a_modal_and_a_popover_does_not(self):
        css = reference_block("accessibility.md", ".toast {") + (
            "\n#ztoast { position: fixed; inset: auto 0 0 auto; inline-size: 12rem; block-size: 4rem;"
            " z-index: var(--z-toast); background: var(--bg-raised); }"
            "\n#dialog { inline-size: 90vw; block-size: 90vh; max-inline-size: none; max-block-size: none; }"
            "\n#outside { inset: var(--gutter-page) auto auto var(--gutter-page); }")   # apart from the other
        body = ("<div id='ztoast'>z-index toast</div>"
                "<dialog id='dialog'>Delete?<div id='inside' class='toast' popover='manual'>Saved inside</div></dialog>"
                "<div id='outside' class='toast' popover='manual'>Saved outside</div>")
        seen = self.run_probe(body, css, "top-layer")
        self.assertEqual(seen["before"], "ztoast", seen)                 # control: on the page, the ladder works
        self.assertEqual(seen["underModal"], "dialog", seen)             # --z-toast is under the modal
        self.assertEqual(seen["open"], [True, True], seen)
        # Both popovers are in the top layer, above the dialog, but the one
        # outside it is inert: a click reaches the dialog, a screen reader nothing.
        self.assertEqual(seen["outside"], "dialog", seen)
        self.assertEqual(seen["inside"], "inside", seen)
        self.assertEqual(set(seen["heard"]), {"Saved inside"}, seen)     # the box and its text
        rect = seen["rect"]                                              # placed by inset, not centred
        self.assertLess(rect["right"], 64, rect)
        self.assertLess(rect["bottom"], 64, rect)
        self.assertGreater(rect["left"], 500, rect)

    def test_user_invalid_marks_a_field_only_once_it_is_touched(self):
        css = reference_block("accessibility.md", ":user-invalid") + (
            "\n.input { border: var(--stroke-1, 1px) solid var(--border-default); }"
            "\n#want-border { color: var(--border-invalid); } #want-help { color: var(--fg-danger); }")
        body = ("<div class='field'><label for='email'>Email address</label>"
                "<input id='email' class='input' type='email' required>"
                "<p class='field-help'>We only use this for receipts.</p></div>"
                "<button id='after'>Next</button><i id='want-border'></i><i id='want-help'></i>")
        seen = self.run_probe(body, css, "user-invalid")
        want = seen["want"]
        self.assertNotEqual(seen["onLoad"]["border"], want["border"], seen)   # empty and required, not yet red
        self.assertNotEqual(seen["onLoad"]["help"], want["help"], seen)
        self.assertEqual(seen["touched"], want, seen)                          # typed and left: both follow


if __name__ == "__main__":
    unittest.main()
