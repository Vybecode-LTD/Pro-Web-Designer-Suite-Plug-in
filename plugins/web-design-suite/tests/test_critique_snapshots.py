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
import unittest

from wds_support import NODE, SKILLS, class_temp_dir, output, run_node, tool_modules

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
            "muted": page('<p class="muted">Muted small print</p>',
                          style=".muted { color: #9a9a9a; } "
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
            self.skipTest(output(proc)[-200:])
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
        rows = {(r["scheme"], r["text"], r["background"]): r for r in report["contrast"]}
        muted = rows[("light", "#9a9a9a", "#ffffff")]
        self.assertEqual((2.81, 4.5, False), (muted["ratio"], muted["floor"], muted["passes"]))
        self.assertIn("p.muted", muted["where"])
        heading = rows[("light", "#767676", "#ffffff")]
        self.assertEqual((3, True), (heading["floor"], heading["passes"]))     # 32px is large text
        self.assertFalse(rows[("dark", "#444444", "#111111")]["passes"])
        band = [r for r in report["contrast"] if r["scheme"] == "light" and r["text"] == "#ffffff"
                and r["background"] not in (None, "an image or gradient")]
        self.assertEqual(1, len(band), report["contrast"])
        self.assertRegex(band[0]["background"], r"^#4[cd]4[cd]4[cd]$")          # 70% black on white
        self.assertIn(("light", None, "an image or gradient"), rows)
        table = (self.tmp / "muted" / "contrast.md").read_text(encoding="utf-8")
        self.assertIn("| light | `#9a9a9a` | `#ffffff` | 2.81:1 | 4.5:1 | **below** |", table)
        self.assertIn("not measured: run a11y_runtime.mjs", table)

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


if __name__ == "__main__":
    unittest.main()
