"""P62 (N56): email-tokens.json, projected from the project's tokens.css.

email-template-system called its token file the email-safe projection of
tokens.css, and nothing projected it: the 4.0.0 live check's S13 and S14
each wrote one by hand, and the skill's own had drifted from the starter
(`--border-strong` on `--neutral-400` where the starter says `--neutral-500`,
and nine starter tokens neither kept nor dropped). sync_email_tokens.py keeps
an entry while its `from` is what tokens.css says, projects it again when its
source moves, and measures every contrast note again.
"""
from __future__ import annotations

import json
import re
import unittest

from wds_support import SKILLS, TempDirTest, load_script, output, run_py

EMAIL = SKILLS / "email-template-system"
SHIPPED = EMAIL / "assets" / "email-tokens.json"
RECEIPT = EMAIL / "assets" / "templates" / "transactional-receipt.html"
STARTER = SKILLS / "web-design-studio" / "assets" / "starter" / "styles" / "tokens.css"
BARE = re.compile(r"^var\((--[\w-]+)\)$")


def starter_css() -> str:
    return STARTER.read_text(encoding="utf-8")


def ratio(fg: str, bg: str) -> float:
    """WCAG 2's contrast ratio of two #rrggbb colours, written here again."""
    def lum(h: str) -> float:
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted((lum(fg), lum(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def hex_of(tokens: dict, name: str) -> str:
    value = tokens[name]["value"]
    while BARE.match(value):
        value = tokens[BARE.match(value).group(1)]["value"]
    return value


class TheSkillsFileFollowsTheStarter(unittest.TestCase):
    """The regression: both fail on v4.0.1 without the script."""

    @classmethod
    def setUpClass(cls):
        cls.css = load_script("email-template-system", "project_config").read_tokens([STARTER]).values()
        cls.doc = json.loads(SHIPPED.read_bytes())

    def test_every_role_points_where_the_starter_does(self):
        for name, entry in self.doc["tokens"].items():
            mine, theirs = BARE.match(str(entry["value"])), BARE.match(self.css.get(name, ""))
            if mine and theirs:
                with self.subTest(name=name):
                    self.assertEqual(theirs.group(1), mine.group(1))

    def test_every_starter_token_is_kept_or_dropped(self):
        placed = set(self.doc["tokens"]) | set(self.doc["dropped"])
        self.assertEqual([], sorted(set(self.css) - placed))


class Sync(TempDirTest):

    def sync(self, *args, cwd=None):
        return run_py("email-template-system", "sync_email_tokens", *args, cwd=cwd or self.tmp)

    def project(self, css: str, *args):
        """The projection of `css` onto the skill's file: the process, the
        file it wrote (None when it wrote none), and the JSON report."""
        tokens, out = self.write("styles/tokens.css", css), self.tmp / "emails" / "email-tokens.json"
        proc = self.sync("--tokens", tokens, "--out", out, "--format", "json", *args)
        doc = json.loads(out.read_bytes()) if out.is_file() else None
        report = json.loads(proc.stdout) if proc.returncode in (0, 1) else None
        return proc, doc, report


class TheSkillsFileIsItsOwnProjection(Sync):

    def test_the_check_finds_it_up_to_date(self):
        proc = self.sync("--tokens", STARTER, "--out", SHIPPED, "--check")
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertIn("up to date", output(proc))

    def test_projecting_it_again_writes_the_same_bytes(self):
        # On stdout `source` is relative to the working folder: the file's own.
        proc = self.sync("--tokens", STARTER, "--out", "-", cwd=SHIPPED.parent)
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertEqual(SHIPPED.read_bytes(), proc.stdout)


class AProjectsOwnTokens(Sync):

    def test_a_new_accent_reaches_every_step_its_contrast_and_the_build(self):
        css = re.sub(r"(--accent-\d+:\s*oklch\([^)]*?) 42\)", r"\1 250)", starter_css())
        proc, doc, report = self.project(css)
        self.assertEqual(0, proc.returncode, output(proc))
        shipped = json.loads(SHIPPED.read_bytes())["tokens"]
        tokens = doc["tokens"]
        for step in ("50", "300", "600", "700"):
            with self.subTest(step=step):
                self.assertNotEqual(shipped["--accent-" + step]["value"], tokens["--accent-" + step]["value"])
                self.assertTrue(tokens["--accent-" + step]["from"].endswith(" 250)"))
        link = tokens["--fg-link"]["contrast"]
        self.assertNotEqual(shipped["--fg-link"]["contrast"], link)
        for figure, bg in re.findall(r"(\d+\.\d+):1 on (--[\w-]+)", link):
            with self.subTest(bg=bg):
                self.assertAlmostEqual(ratio(hex_of(tokens, "--fg-link"), hex_of(tokens, bg)),
                                       float(figure), delta=0.006)
        self.assertIn("--accent-600", [a["name"] for a in report["again"]])
        self.assertIn("--fg-link", [c["name"] for c in report["contrast"]])
        built = self.tmp / "receipt.html"
        proc = run_py("email-template-system", "build_email", RECEIPT, "-o", built, "--tokens",
                      self.tmp / "emails" / "email-tokens.json", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        html = built.read_text(encoding="utf-8")
        self.assertIn(tokens["--accent-600"]["value"], html)
        self.assertNotIn(shipped["--accent-600"]["value"], html)

    def test_an_email_decision_survives_a_projection_that_changes_nothing_under_it(self):
        proc, doc, report = self.project(starter_css())
        self.assertEqual(0, proc.returncode, output(proc))
        h1 = doc["tokens"]["--type-h1-size"]
        self.assertEqual("32px", h1["value"])
        self.assertIn("own heading scale", h1["note"])
        self.assertEqual(([], [], []), (report["again"], report["added"], report["removed"]))

    def test_a_type_role_pointed_elsewhere_is_projected_again(self):
        css = starter_css().replace("--type-h1:       var(--weight-bold)     var(--text-4xl)/var(--leading-tight)",
                                    "--type-h1: var(--weight-semibold) var(--text-3xl)/var(--leading-snug)")
        proc, doc, report = self.project(css)
        self.assertEqual(0, proc.returncode, output(proc))
        tokens = doc["tokens"]
        self.assertEqual(("35px", "46px", "600"), tuple(tokens["--type-h1-" + p]["value"]
                                                        for p in ("size", "line", "weight")))
        self.assertEqual("600 2.1875rem/1.3", tokens["--type-h1-size"]["from"])
        self.assertNotIn("note", tokens["--type-h1-size"])          # it described the 32px
        self.assertEqual("24px", tokens["--type-h2-size"]["value"])   # control: h2 untouched

    def test_a_token_the_file_has_never_seen_takes_its_familys_treatment(self):
        css = starter_css() + "\n:root { --danger-300: oklch(80% 0.1 25); --dur-pulse: 1.2s; }\n"
        proc, doc, report = self.project(css)
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertRegex(doc["tokens"]["--danger-300"]["value"], r"^#[0-9a-f]{6}$")
        self.assertEqual(doc["dropped"]["--dur-base"]["reason"], doc["dropped"]["--dur-pulse"]["reason"])
        self.assertEqual({"--danger-300", "--dur-pulse"}, {a["name"] for a in report["added"]})

    def test_one_with_no_family_and_no_email_form_stops_the_run(self):
        css = starter_css() + "\n:root { --brand-glow: 0 0 4px oklch(60% 0.2 42); }\n"
        proc, doc, _ = self.project(css)
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertIsNone(doc)
        self.assertIn("--brand-glow", output(proc))

    def test_a_token_tokens_css_no_longer_declares_is_removed(self):
        css = re.sub(r"\n\s*--info-100:[^;]*;", "", starter_css())
        proc, doc, report = self.project(css)
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertNotIn("--info-100", doc["tokens"])
        self.assertEqual(["--info-100"], report["removed"])

    def test_an_email_role_left_pointing_at_nothing_stops_the_run(self):
        css = re.sub(r"\n\s*--accent-300:[^;]*;", "", starter_css())
        proc, doc, _ = self.project(css)
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertIsNone(doc)
        self.assertIn("--email-dark-link: it points at --accent-300", output(proc))

    def test_a_pair_under_the_floor_is_written_and_fails(self):
        css = starter_css().replace("--neutral-600: oklch(47.5% 0.009 75)", "--neutral-600: oklch(72% 0.009 75)")
        proc, doc, report = self.project(css)
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIsNotNone(doc)
        self.assertTrue(any(u.startswith("--fg-muted: ") and "under 4.5:1" in u for u in report["under"]),
                        report["under"])

    def test_a_web_font_becomes_the_websafe_stack(self):
        css = re.sub(r"--font-sans:[^;]*;", '--font-sans: "Inter", sans-serif;', starter_css())
        proc, doc, _ = self.project(css)
        self.assertEqual(0, proc.returncode, output(proc))
        font = doc["tokens"]["--font-sans"]
        self.assertEqual("-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, "
                         "sans-serif", font["value"])
        self.assertEqual(('"Inter", sans-serif', "webfont-to-stack"), (font["from"], font["reason"]))

    def test_the_config_names_both_files_and_the_check_finds_a_stale_one(self):
        self.write(".design-suite.json", json.dumps({"schema": 1, "tokens": ["styles/tokens.css"],
                                                     "emailTokens": "emails/email-tokens.json"}))
        self.write("styles/tokens.css", starter_css())
        proc = self.sync()
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertTrue((self.tmp / "emails" / "email-tokens.json").is_file())
        self.assertEqual(0, self.sync("--check").returncode)
        self.write("styles/tokens.css", starter_css().replace("--accent-500: oklch(64.5% 0.188 42)",
                                                              "--accent-500: oklch(64.5% 0.188 140)"))
        proc = self.sync("--check")
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertRegex(output(proc), r"STALE .*--accent-500")

    def test_it_will_not_write_over_a_token_file(self):
        tokens = self.write("styles/tokens.css", starter_css())
        proc = self.sync("--tokens", tokens, "--out", tokens)
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertEqual(starter_css(), tokens.read_text(encoding="utf-8"))


class TheConversions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = load_script("email-template-system", "sync_email_tokens")

    def test_colours_become_six_digit_hex(self):
        for given, want in (("#ffffff", ("#ffffff", None)), ("#ABC", ("#aabbcc", "colour-to-hex")),
                            ("#336699ff", ("#336699", "colour-to-hex")),
                            ("rgb(255 0 0)", ("#ff0000", "colour-to-hex")),
                            ("rgba(0, 128, 255, 1)", ("#0080ff", "colour-to-hex")),
                            ("hsl(120 100% 25%)", ("#008000", "colour-to-hex")),
                            ("oklch(100% 0 0)", ("#ffffff", "oklch-to-hex")),
                            ("oklch(64.5% 0.188 42)", ("#e75b12", "oklch-to-hex"))):
            with self.subTest(given=given):
                self.assertEqual(want, self.m.to_hex(given))

    def test_a_translucent_colour_has_no_email_form(self):
        for given in ("oklch(0% 0 0 / 0.6)", "#00000080", "rgba(0, 0, 0, .5)", "color-mix(in oklch, red, blue)"):
            with self.subTest(given=given), self.assertRaises(self.m.Unprojectable):
                self.m.to_hex(given)

    def test_lengths_become_px(self):
        for given, want in (("0.25rem", ("4px", "rem-to-px")), ("1px", ("1px", None)),
                            ("0.3rem", ("4.8px", "rem-to-px")),
                            ("calc(0.25rem * 1)", ("4px", "calc-removed")),
                            ("calc((1rem + 2px) * 2)", ("36px", "calc-removed")),
                            ("clamp(1rem, 0.8rem + 1vw, 2rem)", ("16px", "clamp-to-fixed"))):
            with self.subTest(given=given):
                self.assertEqual(want, self.m.length(given))
        for given in ("calc(1rem * 2px)", "50vw", "min(1rem, 2vw)"):
            with self.subTest(given=given), self.assertRaises(self.m.Unprojectable):
                self.m.length(given)

    def test_a_stack_keeps_its_websafe_families_in_order(self):
        for given, want in (('"Lora", Georgia, serif', "Georgia, 'Times New Roman', Times, serif"),
                            ('"Fira Code", ui-monospace, Menlo, monospace',
                             "Menlo, Consolas, 'SF Mono', Monaco, 'Courier New', monospace")):
            with self.subTest(given=given):
                self.assertEqual(want, self.m.font_stack(given))


if __name__ == "__main__":
    unittest.main()
