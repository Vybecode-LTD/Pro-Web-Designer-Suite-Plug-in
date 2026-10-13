"""tw_probe.mjs (SB-C3): the project's own Tailwind v4, asked which classes
its theme generates.

The theme's claims ("`--*: initial` removed `p-4`", "the theme gives
`bg-surface`") are silent when false: Tailwind writes no CSS for a class it
does not know. These tests compile the starter's own Tailwind wiring with the
tooling's tailwindcss, found as a project finds it (NODE_PATH stands in for
the project's node_modules), and break it the ways a project does.
"""
from __future__ import annotations

import json
import subprocess
import unittest

from wds_support import NODE, SKILLS, TOOLING_V3, TempDirTest, env, output, tool_modules

SCRIPT = SKILLS / "web-design-studio" / "scripts" / "tw_probe.mjs"
CONFIGS = SKILLS / "web-design-studio" / "assets" / "configs"
STARTER = SKILLS / "web-design-studio" / "assets" / "starter" / "styles"
TAILWIND = tool_modules("WDS_TAILWIND_MODULES", "tailwindcss")
TAILWIND_V3 = tool_modules("WDS_TAILWIND_V3_MODULES", "tailwindcss", default=TOOLING_V3)


@unittest.skipUnless(NODE and TAILWIND, "set WDS_TAILWIND_MODULES to a node_modules with tailwindcss 4")
class TheProbe(TempDirTest):

    def setUp(self):
        super().setUp()
        self.write("src/styles/index.css", (CONFIGS / "index.tailwind.css").read_bytes().decode("utf-8"))
        self.write("src/styles/theme.css", (CONFIGS / "theme.css").read_bytes().decode("utf-8"))
        for name in ("tokens.css", "base.css", "layout.css"):
            self.write(f"src/styles/{name}", (STARTER / name).read_bytes().decode("utf-8"))

    def probe(self, *args, modules=None):
        return subprocess.run([NODE, str(SCRIPT), *args], cwd=self.tmp, capture_output=True, timeout=300,
                              env=env(NODE_PATH=modules or TAILWIND))

    def report(self, *args) -> dict:
        proc = self.probe("--json", *args)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return json.loads(proc.stdout)

    def add_theme(self, css: str):
        self.write("src/styles/index.css",
                   (self.tmp / "src/styles/index.css").read_bytes().decode("utf-8") + css)

    def test_the_starters_theme_passes(self):
        """Every role it declares gives its class, and no stock class survives."""
        proc = self.probe()
        self.assertEqual(0, proc.returncode, output(proc))
        report = self.report()
        self.assertGreater(len(report["roles"]), 50)
        self.assertEqual([], [r for r in report["roles"] if not r["generates"]])
        self.assertTrue(report["stock"])
        self.assertEqual([], [s for s in report["stock"] if s["generates"]])
        self.assertEqual("pass", report["verdict"])

    def test_each_namespace_gives_its_class(self):
        roles = {r["variable"]: r["class"] for r in self.report()["roles"]}
        for variable, cls in (("--color-surface", "bg-surface"), ("--spacing-card", "p-card"),
                              ("--breakpoint-md", "md:block")):
            with self.subTest(variable=variable):
                self.assertEqual(cls, roles.get(variable))

    def test_a_kept_spacing_multiplier_brings_the_numbers_back(self):
        """LC-B5: `--spacing` alone keeps `p-4`, `w-4` and `leading-7`."""
        self.add_theme("@theme { --spacing: 0.25rem; }\n")
        proc = self.probe()
        self.assertEqual(1, proc.returncode, output(proc))
        failing = {s["class"] for s in self.report()["stock"] if s["generates"]}
        self.assertTrue({"p-4", "w-4", "leading-7"} <= failing, failing)
        self.assertIn("--spacing: initial", output(proc))

    def test_tailwinds_own_theme_fails_the_stock_check(self):
        self.write("src/styles/index.css", '@import "tailwindcss";\n')
        report = self.report()
        self.assertEqual("fail", report["verdict"])
        self.assertIn("bg-neutral-800", {s["class"] for s in report["stock"] if s["generates"]})

    def test_named_classes_are_reported_and_expectations_held(self):
        report = self.report("p-card", "p-4", "stack", "md:p-card", "bg-surface/50")
        found = {p["class"]: p["generates"] for p in report["probe"]}
        self.assertEqual({"p-card": True, "p-4": False, "md:p-card": True, "bg-surface/50": True,
                          # layout.css's own class is the stylesheet's, not Tailwind's
                          "stack": False}, found)
        self.assertEqual("pass", report["verdict"])
        proc = self.probe("--expect", "bg-surfce", "--refuse", "p-card")
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn("bg-surfce: expected", output(proc))
        self.assertIn("p-card: refused", output(proc))

    def test_a_container_size_gives_its_query_variant(self):
        self.add_theme("@theme { --container-card: 40rem; }\n")
        report = self.report("@card:p-card")
        self.assertIn({"variable": "--container-card", "class": "@card:block", "generates": True}, report["roles"])
        self.assertEqual([{"class": "@card:p-card", "generates": True}], report["probe"])

    def test_a_namespace_cleared_after_its_variables_drops_them(self):
        self.add_theme("@theme { --radius-*: initial; }\n")
        roles = {r["variable"] for r in self.report()["roles"]}
        self.assertFalse([v for v in roles if v.startswith("--radius-")])
        self.assertTrue([v for v in roles if v.startswith("--color-")])

    def test_what_it_cannot_run_on_exits_2(self):
        for args, modules, message in (
                (("--entry", "src/missing.css"), None, "no entry stylesheet"),
                ((), str(self.tmp / "nowhere"), "cannot find tailwindcss"),
                (("--frobnicate",), None, "unknown option")):
            with self.subTest(message=message):
                proc = self.probe(*args, modules=modules)
                self.assertEqual(2, proc.returncode, output(proc))
                self.assertIn(message, output(proc))
        self.write("src/styles/index.css", '@import "./gone.css";\n')
        proc = self.probe()
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertIn("gone.css", output(proc))

    @unittest.skipUnless(TAILWIND_V3, "set WDS_TAILWIND_V3_MODULES to a node_modules with tailwindcss 3")
    def test_tailwind_3_is_sent_to_the_lint_plugin(self):
        proc = self.probe(modules=TAILWIND_V3)
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertIn("tailwindConfig", output(proc))


if __name__ == "__main__":
    unittest.main()
