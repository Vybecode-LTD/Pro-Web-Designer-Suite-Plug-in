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
- SS-B4 (P38 part 2): typography.md said "use container queries" and never
  named `cqi`; the type is a token, and its rem term keeps it growing at
  200% zoom. `font-size-adjust` needs a measured number (`from-font` reads
  the fallback during a swap), cancels a face's `size-adjust`, and every
  `font:` shorthand resets it. An alpha variant derived on `:root` alone
  keeps the light theme's tint in a dark band. `interpolate-size` animates
  a disclosure to `auto`, and `visibility` keeps its closed links unreachable.
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
  out.status = nodes.filter((n) => !n.ignored && n.role && n.role.value === 'status')
    .map((n) => (n.name && n.name.value) || '');
} else if (process.argv[4] === 'cqi') {
  // Zoom at 200% halves the CSS viewport; on screen, a CSS pixel is then two.
  const sizes = () => page.evaluate(() => [...document.querySelectorAll('[data-probe]')].map(
    (el) => [el.dataset.probe, parseFloat(getComputedStyle(el).fontSize)]));
  await page.setViewportSize({ width: 1440, height: 900 });
  out.at100 = Object.fromEntries(await sizes());
  await page.setViewportSize({ width: 720, height: 900 });   // tall enough for no scrollbar
  out.at200 = Object.fromEntries(await sizes());
} else if (process.argv[4] === 'font-size-adjust') {
  await page.evaluate(() => document.fonts.ready);
  out.adjust = await page.evaluate(() => Object.fromEntries([...document.querySelectorAll('[id]')].map(
    (el) => [el.id, { adjust: getComputedStyle(el).fontSizeAdjust, width: el.getBoundingClientRect().width }])));
  out.faces = await page.evaluate(() => Object.fromEntries([...document.fonts].map((f) => [f.family, f.status])));
} else if (process.argv[4] === 'overlay') {
  out.colours = await page.evaluate(() => Object.fromEntries([...document.querySelectorAll('[data-probe]')].map(
    (el) => [el.dataset.probe, getComputedStyle(el)[el.dataset.prop]])));
} else if (process.argv[4] === 'expand') {
  const panel = '.disclosure__panel';
  const heard = async () => {
    const cdp = await page.context().newCDPSession(page);
    const { nodes } = await cdp.send('Accessibility.getFullAXTree');
    return nodes.some((n) => !n.ignored && n.name && n.name.value === 'Panel link');
  };
  out.supported = await page.evaluate(() => CSS.supports('interpolate-size', 'allow-keywords'));
  out.closed = await page.evaluate((s) => ({ height: document.querySelector(s).getBoundingClientRect().height,
    visible: document.querySelector(s).checkVisibility({ visibilityProperty: true }) }), panel);
  out.closedHeard = await heard();
  out.mid = await page.evaluate((s) => {
    document.querySelector('.disclosure__trigger').setAttribute('aria-expanded', 'true');
    getComputedStyle(document.querySelector(s)).blockSize;   // starts the transition
    // Chromium names the physical longhand a logical property's transition runs on.
    const runs = document.getAnimations().filter((a) => ['block-size', 'height'].includes(a.transitionProperty));
    for (const a of runs) { a.pause(); a.currentTime = a.effect.getComputedTiming().duration / 2; }
    return { runs: runs.length, height: document.querySelector(s).getBoundingClientRect().height };
  }, panel);
  out.open = await page.evaluate((s) => {
    for (const a of document.getAnimations()) a.finish();
    return { height: document.querySelector(s).getBoundingClientRect().height,
      visible: document.querySelector(s).checkVisibility({ visibilityProperty: true }) };
  }, panel);
  out.openHeard = await heard();
  const tabFromTrigger = async () => {
    await page.keyboard.press('Tab');
    return page.evaluate(() => document.activeElement.tagName);
  };
  await page.focus('.disclosure__trigger');
  out.openTab = await tabFromTrigger();
  out.closing = await page.evaluate((s) => {
    const trigger = document.querySelector('.disclosure__trigger');
    trigger.focus();
    trigger.click();                                    // the reference's own toggle closes it
    getComputedStyle(document.querySelector(s)).blockSize;
    const runs = document.getAnimations();              // visibility's transition too
    for (const a of runs) { a.pause(); a.currentTime = a.effect.getComputedTiming().duration / 2; }
    return { runs: runs.length, expanded: trigger.getAttribute('aria-expanded'),
      visible: document.querySelector(s).checkVisibility({ visibilityProperty: true }) };
  }, panel);
  out.closingTab = await tabFromTrigger();
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


def reference_block(name: str, needle: str, lang: str = "css") -> str:
    """The ```css (or `lang`) block in a web-design-studio reference that holds `needle`."""
    text = (STUDIO / "references" / name).read_text(encoding="utf-8")
    blocks = [b for b in re.findall(rf"```{lang}\n(.*?)```", text, flags=re.S) if needle in b]
    if len(blocks) != 1:
        raise AssertionError(f"{name}: {len(blocks)} {lang} blocks hold {needle!r}")
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
                "<dialog id='dialog'>Delete?<div id='inside' class='toast' popover='manual' role='status'>"
                "Saved inside</div></dialog>"
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
        self.assertEqual(len(seen["status"]), 1, seen)                   # one live region, reachable (Codex on #113)
        markup = re.search(r"```html\n(<dialog class=\"dialog\".*?)```",
                           (STUDIO / "references" / "accessibility.md").read_text(encoding="utf-8"), flags=re.S)
        self.assertIsNotNone(markup)
        self.assertIn('popover="manual" role="status"', markup.group(1))
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

    def test_cqi_type_follows_its_container_and_still_grows_with_zoom(self):
        css = reference_block("typography.md", "--text-fluid-card") + (
            "\nbody { margin: 0; } .pure { font-size: 3.0882cqi; }")
        card = "<div class='promo'{}><h2 class='promo__title{}' data-probe='{}'>Headline</h2></div>"
        body = "".join(card.format(f" style='inline-size: {w}px'", "", w) for w in (360, 700, 1040)) + (
            card.format("", "", "window") + card.format("", " pure", "pure"))
        seen = self.run_probe(body, css, "cqi")
        at100, at200 = seen["at100"], seen["at200"]
        # The worked example: 35px in a 360px card, 45.5px in 700, 56px in 1040.
        for width, size in (("360", 35), ("700", 45.5), ("1040", 56)):
            self.assertAlmostEqual(at100[width], size, delta=0.1, msg=seen)
            self.assertAlmostEqual(at200[width], size, delta=0.1, msg=seen)   # a fixed card ignores the window
        # In a card as wide as a 1440px window: on screen, 1.65x at 200%.
        self.assertAlmostEqual(2 * at200["window"] / at100["window"], 1.65, delta=0.01, msg=seen)
        self.assertAlmostEqual(2 * at200["pure"] / at100["pure"], 1.0, delta=0.01, msg=seen)   # control: no rem term

    def test_font_size_adjust_needs_a_number_and_a_place_after_the_shorthand(self):
        css = reference_block("typography.md", "--font-sans-aspect") + (
            '\n@font-face { font-family: "Geist Sans"; src: url(missing.woff2); }'   # the web font never arrives
            "\nh3 { font: var(--type-h3); }"                                           # control: no adjust after it
            '\n.probe { display: inline-block; white-space: nowrap; font: 20px "Geist Sans", sans-serif; }'
            "\n#none { font-size-adjust: none; } #number { font-size-adjust: var(--font-sans-aspect); }"
            "\n#from-font { font-size-adjust: from-font; }")
        body = ("<p id='para'>Body</p><h2 id='heading'>Two</h2><h3 id='control'>Three</h3>"
                + "".join(f"<br><span class='probe' id='{i}'>xxxxxxxxxxxxxxxxxxxx</span>"
                          for i in ("none", "number", "from-font")))
        seen = self.run_probe(body, css, "font-size-adjust")["adjust"]
        self.assertEqual(seen["para"]["adjust"], "0.53", seen)       # inherited from body
        self.assertEqual(seen["heading"]["adjust"], "0.53", seen)    # declared after h2's font:
        self.assertEqual(seen["control"]["adjust"], "none", seen)    # h3's font: reset it
        # from-font reads the fallback itself while the web font is missing: its
        # own ratio, so no change.
        own = float(seen["from-font"]["adjust"])
        self.assertAlmostEqual(seen["from-font"]["width"], seen["none"]["width"], delta=0.01, msg=seen)
        # The number scales the fallback by MDN's u = (m / m') s, m' its own
        # ratio, whatever system font it is (Linux's is close to 0.53).
        self.assertAlmostEqual(seen["number"]["width"] / seen["none"]["width"], 0.53 / own, delta=0.005, msg=seen)

    def test_font_size_adjust_cancels_a_fallback_faces_size_adjust(self):
        local = 'src: local("Arial"), local("Liberation Sans"), local("DejaVu Sans"), local("Helvetica");'
        css = reference_block("typography.md", "--font-sans-aspect") + (
            f'\n@font-face {{ font-family: "Plain"; {local} }}'
            f'\n@font-face {{ font-family: "Grown"; {local} size-adjust: 150%; }}'
            "\nspan { display: inline-block; white-space: nowrap; font-size: 20px; }"
            '\n#plain, #plain-adjusted { font-family: "Plain"; } #grown, #grown-adjusted { font-family: "Grown"; }'
            "\n#plain, #grown { font-size-adjust: none; }"   # body's would cancel the control's too
            "\n#plain-adjusted, #grown-adjusted { font-size-adjust: var(--font-sans-aspect); }")
        body = "".join(f"<span id='{i}'>xxxxxxxxxxxxxxxxxxxx</span><br>"
                       for i in ("plain", "grown", "plain-adjusted", "grown-adjusted"))
        seen = self.run_probe(body, css, "font-size-adjust")
        if seen["faces"] != {"Plain": "loaded", "Grown": "loaded"}:
            self.skipTest(f"no local Arial, Liberation Sans, DejaVu Sans or Helvetica: {seen['faces']}")
        width = {k: v["width"] for k, v in seen["adjust"].items()}
        self.assertAlmostEqual(width["grown"] / width["plain"], 1.5, delta=0.01, msg=width)   # control: it applies
        self.assertAlmostEqual(width["grown-adjusted"], width["plain-adjusted"], delta=0.01, msg=width)

    def test_an_alpha_variant_follows_its_role_into_a_themed_band(self):
        css = reference_block("color-system.md", "--bg-accent-subtle") + (
            "\n:root { --tint-root-only: color-mix(in oklch, var(--bg-accent) 12%, transparent); }"
            "\n.mix { background: var(--bg-accent-subtle); } .relative { background: var(--bg-danger-subtle); }"
            "\n.root-only { background: var(--tint-root-only); }"
            "\n.accent { color: var(--bg-accent); } .danger { color: var(--bg-danger); }")
        probes = (("mix", "backgroundColor"), ("relative", "backgroundColor"), ("root-only", "backgroundColor"),
                  ("accent", "color"), ("danger", "color"))
        def scope(name):
            return "".join(f"<i class='{c}' data-probe='{name}-{c}' data-prop='{p}'></i>" for c, p in probes)
        seen = self.run_probe(scope("page") + "<section data-theme='dark'>" + scope("band") + "</section>",
                              css, "overlay")["colours"]

        def channels(text):
            m = re.fullmatch(r"oklch\(([\d.]+) ([\d.]+) ([\d.]+)(?: / ([\d.]+))?\)", text)
            self.assertIsNotNone(m, f"{text!r} in {seen}")
            return [float(v) for v in m.groups(default="1")]

        for where in ("page", "band"):
            accent, danger = channels(seen[f"{where}-accent"]), channels(seen[f"{where}-danger"])
            for name, role in (("mix", accent), ("relative", danger)):
                got = channels(seen[f"{where}-{name}"])
                for a, b in zip(got, role[:3] + [0.12]):    # the role's colour, at alpha 0.12
                    self.assertAlmostEqual(a, b, delta=0.002, msg=f"{where}-{name}: {seen}")
        self.assertNotEqual(channels(seen["page-accent"]), channels(seen["band-accent"]), seen)   # the band re-points it
        # Control: derived on :root alone, the band keeps the page's tint.
        self.assertEqual(seen["band-root-only"], seen["page-root-only"], seen)
        self.assertNotEqual(seen["band-root-only"], seen["band-mix"], seen)

    def test_a_disclosure_animates_to_auto_and_hides_its_closed_panel(self):
        css = reference_block("motion-system.md", "interpolate-size")
        body = ("<div class='disclosure'><button class='disclosure__trigger' aria-expanded='false'>More</button>"
                "<div class='disclosure__panel'><p style='margin: 0; block-size: 200px'>Body</p>"
                "<a href='#x'>Panel link</a></div></div>"
                f"<script>{reference_block('motion-system.md', 'disclosure__trigger', 'js')}</script>")
        seen = self.run_probe(body, css, "expand")
        if not seen["supported"]:
            self.skipTest("this Chromium has no interpolate-size")
        self.assertEqual(seen["closed"], {"height": 0, "visible": False}, seen)
        self.assertFalse(seen["closedHeard"], seen)                       # closed: not reachable
        self.assertEqual(seen["mid"]["runs"], 1, seen)
        self.assertTrue(0 < seen["mid"]["height"] < seen["open"]["height"], seen)   # halfway, a height between
        self.assertGreater(seen["open"]["height"], 200, seen)
        self.assertTrue(seen["open"]["visible"], seen)
        self.assertTrue(seen["openHeard"], seen)
        # CodeRabbit on #115: closing, the panel stays visible until the
        # transition ends, so the toggle sets inert with the attribute.
        self.assertEqual(seen["openTab"], "A", seen)                     # control: Tab reaches it open
        self.assertEqual(seen["closing"]["expanded"], "false", seen)
        self.assertTrue(seen["closing"]["runs"] >= 1 and seen["closing"]["visible"], seen)   # mid-close
        self.assertNotEqual(seen["closingTab"], "A", seen)               # but not while it closes
        bare = body.replace("trigger.nextElementSibling.inert = !open;", "")
        self.assertNotEqual(bare, body)
        bare = self.run_probe(bare, css, "expand")
        self.assertEqual(bare["closingTab"], "A", bare)                  # control: without inert, it does
        # Control: without it, 0 to auto has no transition; the panel jumps open.
        jump = self.run_probe(body, css + "\n:root { interpolate-size: numeric-only; }", "expand")
        self.assertEqual(jump["mid"]["runs"], 0, jump)
        self.assertEqual(jump["mid"]["height"], jump["open"]["height"], jump)


class TheReferencesReadAlone(unittest.TestCase):

    def test_font_size_adjust_has_a_stack_without_a_re_metricked_face(self):
        """Codex on #115: applied to the stack whose first fallback is the
        re-metricked face, font-size-adjust switches that face's measured
        size-adjust off (test_font_size_adjust_cancels_a_fallback_faces_size_adjust),
        so the example declares a stack of its own without it."""
        text = (STUDIO / "references" / "typography.md").read_text(encoding="utf-8")
        metricked = set(re.findall(r'@font-face\s*\{[^}]*?font-family:\s*"([^"]+)";[^}]*?\bsize-adjust:', text))
        self.assertEqual(metricked, {"Geist Sans Fallback"})   # control: the face above is found
        block = reference_block("typography.md", "--font-sans-aspect")
        stack = re.search(r"--font-sans:\s*([^;]+);", block)
        self.assertIsNotNone(stack, "the example reads the stack above, whose fallback it cancels")
        self.assertFalse(metricked & set(re.findall(r'"([^"]+)"', stack.group(1))), stack.group(1))


if __name__ == "__main__":
    unittest.main()
