"""design-critique-gate: critique_snapshots.mjs (PS-B5, PS-C5).

The critique's checks that need a person (five seconds with someone else,
squinting, a real phone, a night's sleep) had no tool behind them, and
CRITIQUE_TEMPLATE.md offered only yes or no, so a check nobody ran read as
one that failed, or was ticked. critique_snapshots.mjs renders the files that
stand in for each (390 and 1440px, blur, greyscale, mirror, 25%, dark,
reduced motion) and a contrast table from computed styles; the template
records each check as run, run with a proxy, or "not run — needs a human".

The real-browser tests need node and Playwright (WDS_NODE_MODULES, or
tooling/main), and skip without them. Resolution, CSP and crash handling are
held with the other browser scripts in test_browser_scripts.
"""
from __future__ import annotations

import json
import re
import struct
import subprocess
import unittest
import zlib

from wds_support import NODE, SKILLS, class_temp_dir, env, no_browser, output, run_node, tool_modules

MODULES = tool_modules("WDS_NODE_MODULES", "playwright", node_path=True)
GATE = SKILLS / "design-critique-gate"

STYLE = """
:root { color-scheme: light dark; }
body { margin: 0; font: 16px/1.5 sans-serif; background: #ffffff; color: #1a1a1a; }
.hero { background: linear-gradient(#123, #456); color: #fff; padding: 40px; }
.band { background: rgba(0, 0, 0, 0.7); color: #fff; padding: 20px; }
h1 { font-size: 32px; color: #767676; }
@media (prefers-color-scheme: dark) { body { background: #111; color: #eee; } }
"""
BODY = """<div class="hero"><p>Over a gradient</p></div>
<h1>Large heading</h1><p>Body copy that reads well.</p>{extra}
<div class="band"><p>On a translucent band</p></div>"""
# The page's own CSP forbids every script and stylesheet but its inline
# style: nothing the run needs may be injected into it.
CSP = "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'\">"


def page(extra="", viewport=True, style=""):
    meta = '<meta name="viewport" content="width=device-width, initial-scale=1">' if viewport else ""
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8>{meta}{CSP}"
            f"<title>t</title><style>{STYLE}{style}</style></head>"
            f"<body>{BODY.format(extra=extra)}</body></html>")


def png_size(path):
    head = path.read_bytes()[:24]
    assert head.startswith(b"\x89PNG"), path
    return struct.unpack(">II", head[16:24])


@unittest.skipUnless(NODE and MODULES, "needs node plus WDS_NODE_MODULES pointing at playwright")
class CritiqueSnapshots(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = class_temp_dir(cls, "wds-snap-")
        cls.runs = {}
        pages = {
            "muted": page('<p class="muted">Muted small print</p>'
                          '<p class="faded">Faded print</p>'
                          '<input class="email" placeholder="Your email">'
                          '<p class="narrow">Only on a phone</p>',
                          style=".muted { color: #9a9a9a; } .faded { opacity: 0.4; } "
                                ".email::placeholder { color: #bbbbbb; } .narrow { display: none; } "
                                "@media (max-width: 600px) { .narrow { display: block; color: #aaaaaa; } } "
                                "@media (prefers-color-scheme: dark) { .muted { color: #444; } }"),
            "clean": page(viewport=False),
        }
        for name, html in pages.items():
            path = cls.tmp / f"{name}.html"
            path.write_text(html, encoding="utf-8")
            proc = run_node("design-critique-gate", "critique_snapshots.mjs", path, "--out",
                            cls.tmp / name, "--json", cwd=cls.tmp,
                            env_changes={"NODE_PATH": MODULES, "CRITIQUE_CHROMIUM": None}, timeout=300)
            cls.runs[name] = proc

    def run_of(self, name):
        proc = self.runs[name]
        if proc.returncode == 2 and b"no usable chromium" in proc.stderr:
            no_browser(self, output(proc)[-200:])
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return proc.returncode, json.loads(proc.stdout)

    def test_every_view_is_written(self):
        code, report = self.run_of("muted")
        expected = {"390.png", "390-dark.png", "390-reduced-motion.png", "1440.png", "1440-dark.png",
                    "1440-reduced-motion.png", "1440-blur.png", "1440-greyscale.png",
                    "1440-mirror.png", "1440-25.png"}
        self.assertEqual(expected, {s["name"] for s in report["shots"]})
        out = self.tmp / "muted"
        sizes = {name: png_size(out / name) for name in expected}
        self.assertEqual(1440, sizes["1440.png"][0])
        self.assertEqual(390, sizes["390.png"][0])
        self.assertEqual((360, sizes["1440.png"][1] // 4), sizes["1440-25.png"])
        for view in ("blur", "greyscale", "mirror"):
            with self.subTest(view=view):
                self.assertEqual(sizes["1440.png"], sizes[f"1440-{view}.png"])
                self.assertNotEqual((out / "1440.png").read_bytes(), (out / f"1440-{view}.png").read_bytes())
        self.assertNotEqual((out / "1440.png").read_bytes(), (out / "1440-dark.png").read_bytes(),
                            "the dark capture is the light one")
        self.assertTrue((out / "contrast.md").read_text(encoding="utf-8").startswith("# Contrast"))
        self.assertEqual([], report["warnings"])

    def test_the_contrast_table_measures_each_pair_against_its_floor(self):
        code, report = self.run_of("muted")
        self.assertEqual(1, code, "a pair below its floor exits 1")
        rows = {(r["view"], r["text"], r["background"]): r for r in report["contrast"]}
        muted = rows[("1440 light", "#9a9a9a", "#ffffff")]
        self.assertEqual((2.81, 4.5, False), (muted["ratio"], muted["floor"], muted["passes"]))
        self.assertIn("p.muted", muted["where"])
        heading = rows[("1440 light", "#767676", "#ffffff")]
        self.assertEqual((3, True), (heading["floor"], heading["passes"]))     # 32px is large text
        self.assertFalse(rows[("1440 dark", "#444444", "#111111")]["passes"])
        band = [r for r in report["contrast"] if r["view"] == "1440 light" and r["text"] == "#ffffff"
                and r["background"] not in (None, "an image or gradient")]
        self.assertEqual(1, len(band), report["contrast"])
        self.assertRegex(band[0]["background"], r"^#4[cd]4[cd]4[cd]$")          # 70% black on white
        self.assertIn(("1440 light", None, "an image or gradient"), rows)
        table = (self.tmp / "muted" / "contrast.md").read_text(encoding="utf-8")
        self.assertIn("| 1440 light | `#9a9a9a` | `#ffffff` | 2.81:1 | 4.5:1 | **below** |", table)
        self.assertIn("not measured: run a11y_runtime.mjs", table)

    def test_phone_only_text_form_text_and_faded_text_are_measured(self):
        """Codex on #71: only the 1440 layout was sampled, only text nodes,
        and an ancestor's opacity was ignored, so each of these passed unseen."""
        code, report = self.run_of("muted")

        def rows(name):
            return [r for r in report["contrast"] if name in r["where"]]

        faded = rows("p.faded")
        self.assertEqual({"390 light", "390 dark", "1440 light", "1440 dark"}, {r["view"] for r in faded})
        self.assertTrue(all(r["passes"] is False for r in faded), faded)     # #1a1a1a at 0.4 on white
        light = next(r for r in faded if r["view"] == "1440 light")
        self.assertRegex(light["text"], r"^#a[234]a[234]a[234]$")
        placeholder = rows("input.email::placeholder")
        self.assertTrue(placeholder and all(r["passes"] is False for r in placeholder
                                            if r["view"].endswith("light")), placeholder)
        narrow = rows("p.narrow")
        self.assertEqual({"390 light", "390 dark"}, {r["view"] for r in narrow})
        self.assertFalse(next(r for r in narrow if r["view"] == "390 light")["passes"])

    def test_a_clean_page_exits_0_and_a_missing_viewport_is_named(self):
        code, report = self.run_of("clean")
        self.assertEqual(0, code, report["contrast"])
        self.assertEqual(1, len(report["warnings"]), report["warnings"])
        self.assertIn('content="width=device-width"', report["warnings"][0])
        self.assertIn("390.png", report["warnings"][0])

    def test_each_human_check_names_its_proxy_and_overnight_has_none(self):
        code, report = self.run_of("muted")
        proxies = {p["check"]: p for p in report["proxies"]}
        self.assertEqual([], proxies["Leave it overnight"]["files"])
        self.assertIn("not run — needs a human", proxies["Leave it overnight"]["limit"])
        names = {s["name"] for s in report["shots"]}
        for p in report["proxies"]:
            with self.subTest(check=p["check"]):
                self.assertLessEqual(set(p["files"]), names)


class TheTemplateHasAThirdState(unittest.TestCase):
    """PS-B5: CRITIQUE_TEMPLATE offered only yes or no for a check a person runs."""

    def test_the_human_checks_can_be_not_run(self):
        template = (GATE / "assets" / "CRITIQUE_TEMPLATE.md").read_text(encoding="utf-8")
        section = template.split("## Checks a person runs", 1)[1].split("\n## ", 1)[0]
        for check in ("Five seconds with someone else", "Squint", "On an actual phone",
                      "Leave it overnight"):
            with self.subTest(check=check):
                row = next(line for line in section.splitlines() if line.startswith(f"| {check}"))
                self.assertIn("not run — needs a human", row)
        script = (GATE / "scripts" / "critique_snapshots.mjs").read_text(encoding="utf-8")
        listed = set(re.findall(r"check: '([^']+)'", script))
        self.assertLessEqual({"Five seconds with someone else", "On an actual phone", "Leave it overnight"},
                             listed)
        self.assertNotRegex(section, r"<yes/no>")


def png_pixels(data: bytes):
    """(width, height, rows of RGB) from an 8-bit, non-interlaced RGB or RGBA PNG,
    which is what Chromium writes."""
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    pos, idat, head = 8, b"", None
    while pos < len(data):
        size, kind = struct.unpack(">I4s", data[pos:pos + 8])
        if kind == b"IHDR":
            head = struct.unpack(">IIBBBBB", data[pos + 8:pos + 8 + size])
        elif kind == b"IDAT":
            idat += data[pos + 8:pos + 8 + size]
        pos += 12 + size
    width, height, depth, colour, _, _, interlace = head
    assert depth == 8 and colour in (2, 6) and not interlace, head
    bpp = 3 if colour == 2 else 4
    raw, stride, rows, prev = zlib.decompress(idat), width * bpp, [], bytearray(width * bpp)
    for y in range(height):
        kind = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b, c = prev[i], prev[i - bpp] if i >= bpp else 0
            if kind == 1:
                line[i] = (line[i] + a) & 255
            elif kind == 2:
                line[i] = (line[i] + b) & 255
            elif kind == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif kind == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(line)
        prev = line
    return width, height, [[tuple(r[x * bpp:x * bpp + 3]) for x in range(width)] for r in rows]


# A section 2,600 px down that an IntersectionObserver reveals, fading in, as
# landing pages do. Scripts run here: the CSP pages above allow none.
REVEAL = ("<!doctype html><html lang=en><head><meta charset=utf-8><title>r</title><style>"
          "body{margin:0;min-height:3200px;background:#fff;font:16px sans-serif}"
          "#late{position:absolute;top:2600px;left:0;right:0;height:300px;background:#fff;"
          "transition:background-color .6s}#late.shown{background:#c00}"
          "</style></head><body><h1>Top of the page</h1><div id=late></div><script>"
          "new IntersectionObserver((seen) => { for (const e of seen) if (e.isIntersecting) "
          "e.target.classList.add('shown'); }).observe(document.getElementById('late'));"
          "</script></body></html>")


@unittest.skipUnless(NODE and MODULES, "needs node plus WDS_NODE_MODULES pointing at playwright")
class TheCaptureIsOfThePageAsRead(unittest.TestCase):
    """P76 (the 2026-10-28 audit's JS-B)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = class_temp_dir(cls, "wds-reveal-")
        path = cls.tmp / "reveal.html"
        path.write_text(REVEAL, encoding="utf-8")
        cls.proc = run_node("design-critique-gate", "critique_snapshots.mjs", path, "--out", cls.tmp / "out",
                            "--json", cwd=cls.tmp, env_changes={"NODE_PATH": MODULES, "CRITIQUE_CHROMIUM": None},
                            timeout=300)

    def report(self):
        if self.proc.returncode == 2 and b"no usable chromium" in self.proc.stderr:
            no_browser(self, output(self.proc)[-200:])
        self.assertIn(self.proc.returncode, (0, 1), output(self.proc))
        return json.loads(self.proc.stdout)

    def test_a_section_revealed_on_scroll_is_captured_revealed(self):
        """JS-B-22: the full-page capture never scrolled, so a section an
        IntersectionObserver reveals below the fold was blank in every view
        the hierarchy is judged from."""
        self.report()
        # The 25% view, made from the 1440 capture: a quarter of its size, so
        # this pure-Python reader stays quick.
        width, height, rows = png_pixels((self.tmp / "out" / "1440-25.png").read_bytes())
        self.assertGreaterEqual(height, 2900 // 4)
        r, g, b = rows[2750 // 4][width // 2]
        self.assertTrue(r > 180 and g < 40 and b < 40, f"the revealed section is {(r, g, b)}, not red")
        top = rows[1][width // 2]
        self.assertTrue(all(v > 240 for v in top), f"the top of the page is {top}")      # the control

    def test_the_report_names_the_browser_and_its_build(self):
        """TEST-10: the report named a browser by its label alone."""
        report = self.report()
        self.assertTrue(report.get("browser"))
        self.assertRegex(report.get("browserVersion") or "", r"^\d+\.\d+")


# SCROLL_THROUGH on a fake page: its frames and pauses at once, its scrolls logged,
# clamped as a browser clamps them.
FAKE_PAGE = """
const scrolled = [];
globalThis.innerHeight = 900;
globalThis.window = { scrollTo: ({ top }) => { scrolled.push(Math.max(0, Math.min(top, 49 * 900))); } };
globalThis.document = { documentElement: { scrollHeight: 50 * 900 }, images: [], getAnimations: () => [] };
globalThis.requestAnimationFrame = (f) => setImmediate(f);
const wait = setTimeout;
globalThis.setTimeout = (f) => wait(f, 0);
const whole = await SCROLL_THROUGH([3000, 15000]);
const steps = scrolled.length;
const cut = await SCROLL_THROUGH([3000, -1]);
console.log(JSON.stringify({ scrolled: scrolled.slice(0, steps), whole, cut }));
"""


@unittest.skipUnless(NODE, "node is not installed")
class TheScrollGoesTheWholeWay(unittest.TestCase):

    def test_a_long_page_is_stepped_through_to_its_end(self):
        """CodeRabbit on #234: thirty steps and a jump to the end left the
        stretch between them unvisited on a page longer than thirty steps, so
        a reveal there stayed blank, and nothing said so. SCROLL_THROUGH is run
        on a fake page fifty viewports long."""
        source = (GATE / "scripts" / "critique_snapshots.mjs").read_text(encoding="utf-8")
        found = re.search(r"^const SCROLL_THROUGH = async .*?^};\n", source, re.S | re.M)
        self.assertIsNotNone(found, "critique_snapshots.mjs has no SCROLL_THROUGH")
        proc = subprocess.run([NODE, "--input-type=module", "-e", found.group(0) + FAKE_PAGE],
                              capture_output=True, timeout=60, env=env())
        self.assertEqual(proc.returncode, 0, output(proc))
        ran = json.loads(proc.stdout)
        *tops, back = ran["scrolled"]
        self.assertEqual(0, back, "it did not come back to the top")
        self.assertEqual(49 * 900, tops[-1], tops)
        gaps = [b - a for a, b in zip(tops, tops[1:])]
        self.assertLessEqual(max(gaps), 900, f"a stretch no viewport showed: {tops}")
        self.assertEqual(True, (ran["whole"] or {}).get("reached"), ran["whole"])
        # Out of time at once: it says how far it got, so the capture warns.
        self.assertEqual(False, (ran["cut"] or {}).get("reached"), ran["cut"])


if __name__ == "__main__":
    unittest.main()
