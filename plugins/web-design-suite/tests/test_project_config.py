"""The project contract (P24: XC-C8, LC-C1, LC-B3).

A project could tell the scripts where its tokens were only flag by flag, and
only figma_audit and extract_system took a flag. `.design-suite.json` names a
project's token files, component globs, stack, budgets and baselines once, and
shared/project_config.py reads it for every script, with a copy in each skill
that uses it. extract_system writes a `contract.json`, the token system's
default values by tier, which figma_audit's `--tokens` reads as it reads a
tokens.css.

Part 2: every script that compares against the starter's token system reads
the project's instead (read_tokens): audit_design (its token files, component
globs, ramps and baseline), figma_audit's scales, figma_to_tokens' names,
diff_system's snapshots and cluster_values' ramps. Each takes `--tokens`, or
the config's token files without it.

Part 4 (N37): shared/project_config.mjs is the Node reader, held to this one
on the config, the token files and the component globs; the stylelint and
ESLint configs read the project through it (test_real_tools).
"""
from __future__ import annotations

import dataclasses
import json
import pathlib
import re
import subprocess
import sys
import unittest

from test_figma_sync import PROJECT_ACCENT, STEPS
from wds_support import NODE, PLUGIN, SKILLS, TempDirTest, env, load_script, output, run_node, run_py

MASTER = PLUGIN / "shared" / "project_config.py"
NODE_MASTER = PLUGIN / "shared" / "project_config.mjs"
TOKENS = ("@layer tokens {\n  :root {\n" + "".join(f"    --accent-{s}: {h};\n" for s, h in zip(STEPS, PROJECT_ACCENT))
          + "    --space-4: 1rem;\n    --bp-md: 48rem;\n    --bg-accent: var(--accent-600);\n  }\n}\n")


class TheCopiesAreTheMaster(unittest.TestCase):
    """A skill installed alone has only its own folder, so each skill whose
    scripts read the config keeps a byte-identical copy of the master."""

    def test_every_reader_has_the_master_copy_beside_it(self):
        readers = sorted({p.parent for p in SKILLS.glob("*/scripts/*.py")
                          if re.search(r"^\s*from \.?project_config import", p.read_text(encoding="utf-8"), re.M)})
        self.assertEqual(["a11y-audit-runner", "client-presentation-builder", "content-model-to-ui",
                          "design-system-docs", "design-system-versioning", "design-token-migration",
                          "email-template-system", "figma-variables-sync", "perf-budget-gate",
                          "web-design-studio"], [r.parent.name for r in readers])
        copies = sorted(p.parent for p in SKILLS.glob("*/scripts/project_config.py"))
        self.assertEqual(readers, copies)
        master = MASTER.read_bytes()
        self.assertEqual([], [str(c.relative_to(PLUGIN)) for c in copies
                              if (c / "project_config.py").read_bytes() != master],
                         "copy shared/project_config.py over these")

    def test_every_node_reader_has_the_master_copy_beside_it(self):
        """N37: the lint configs read the project through project_config.mjs,
        and browser_common.mjs re-exports it, so each folder that imports it
        holds a byte-identical copy of shared/project_config.mjs."""
        importers = sorted({p.parent for p in PLUGIN.glob("*/**/*.mjs") if p.parent.name != "shared"
                            and "from './project_config.mjs';" in p.read_text(encoding="utf-8")})
        self.assertEqual(["hooks", "skills/a11y-audit-runner/scripts", "skills/component-state-matrix/scripts",
                          "skills/design-critique-gate/scripts", "skills/email-template-system/scripts",
                          "skills/perf-budget-gate/scripts", "skills/web-design-studio/assets/configs"],
                         [p.relative_to(PLUGIN).as_posix() for p in importers])
        self.assertEqual(importers, sorted(p.parent for p in PLUGIN.glob("*/**/project_config.mjs")
                                           if p.parent.name != "shared"))
        master = NODE_MASTER.read_bytes()
        self.assertEqual([], [p.relative_to(PLUGIN).as_posix() for p in importers
                              if (p / "project_config.mjs").read_bytes() != master],
                         "copy shared/project_config.mjs over these")


class TheReader(TempDirTest):
    def setUp(self):
        super().setUp()
        self.pc = load_script("figma-variables-sync", "project_config")

    def test_the_walk_up_stops_at_the_repository_root(self):
        self.write(".design-suite.json", '{"schema": 1}')
        self.write("repo/.git/HEAD", "ref: refs/heads/main\n")
        deep = self.tmp / "repo" / "src" / "app"
        deep.mkdir(parents=True)
        self.assertIsNone(self.pc.find_config(deep))       # the one above the repository is not its
        own = self.write("repo/.design-suite.json", '{"schema": 1}')
        self.assertEqual(own.resolve(), self.pc.find_config(deep))

    def test_paths_are_relative_to_the_file(self):
        path = self.write("site/.design-suite.json", json.dumps({
            "schema": 1, "tokens": "styles/tokens.css", "emailTokens": "emails/email-tokens.json",
            "components": "src/widgets/**/*.css", "stack": "tailwind-v4",
            "budgets": {"perf": "perf-budget.json"}, "baselines": {"audit": ".design-baseline.json"}}))
        config = self.pc.load_config(path)
        site = (self.tmp / "site").resolve()
        self.assertEqual([site / "styles" / "tokens.css"], config.tokens)
        self.assertEqual(site / "emails" / "email-tokens.json", config.email_tokens)
        self.assertEqual(["src/widgets/**/*.css"], config.components)
        self.assertEqual({"perf": site / "perf-budget.json"}, config.budgets)
        self.assertEqual({"audit": site / ".design-baseline.json"}, config.baselines)

    def test_a_mistake_is_named(self):
        cases = {'{"schema": 1, "token": "tokens.css"}': "unknown key 'token'",
                 '{"tokens": "tokens.css"}': '"schema" must be 1',
                 '{"schema": 1, "stack": "bootstrap"}': '"stack" must be one of',
                 '{"schema": 1, "budgets": {"lcp": "x.json"}}': "unknown key 'lcp' in \"budgets\"",
                 '{"schema": 1, "tokens": [3]}': '"tokens" must be a path',
                 '[1]': "the top level must be an object",
                 '{"schema": 1,}': "not JSON"}
        for n, (text, message) in enumerate(cases.items()):
            with self.subTest(config=text):
                with self.assertRaises(self.pc.ConfigError) as caught:
                    self.pc.load_config(self.write(f"c{n}/.design-suite.json", text))
                self.assertIn(message, str(caught.exception))

    def test_a_flag_beats_the_config(self):
        self.write("repo/.git/HEAD", "x\n")
        self.write("repo/.design-suite.json", '{"schema": 1, "tokens": ["a.css", "b.json"]}')
        repo = (self.tmp / "repo").resolve()
        self.assertEqual(([repo / "a.css", repo / "b.json"], repo / ".design-suite.json"),
                         self.pc.token_sources(None, repo))
        self.assertEqual(([self.tmp / "mine.css"], None), self.pc.token_sources(str(self.tmp / "mine.css"), repo))

    def test_a_contract_is_checked(self):
        bad = {"schema": "web-design-suite/contract/1", "ramps": {"accent": "#fff"}}
        with self.assertRaises(self.pc.ConfigError) as caught:
            self.pc.read_contract(self.write("bad.json", json.dumps(bad)))
        self.assertIn('"ramps.accent" must be an object of strings', str(caught.exception))
        with self.assertRaises(self.pc.ConfigError):
            self.pc.read_contract(self.write("system.json", json.dumps({"schema": "design-system-docs/system/1"})))

    def test_component_globs_are_read_from_the_configs_folder(self):
        config = self.pc.load_config(self.write("site/.design-suite.json",
                                                '{"schema": 1, "components": ["src/widgets/**/*.css", "*.tsx"]}'))
        site = self.tmp / "site"
        for rel, expected in (("src/widgets/card.css", True), ("src/widgets/a/b/card.css", True),
                              ("src/other/card.css", False), ("src/widgets/card.scss", False),
                              ("Card.tsx", True), ("src/Card.tsx", False)):
            with self.subTest(path=rel):
                self.assertEqual(expected, config.is_component(site / rel))
        self.assertFalse(config.is_component(self.tmp / "src" / "widgets" / "card.css"))   # outside the project

    def test_a_tokens_css_is_read_by_its_defaults(self):
        path = self.write("tokens.css", (
            "@layer reset, tokens;\n@layer tokens {\n  :root, [data-theme] {\n"
            "    --accent-600: oklch(56.5% 0.176 42);\n    --accent-50:  #fff7f0;\n"
            "    --icon: url(\"data:image/svg+xml;utf8,<svg/>\");\n    --bp-md: 48rem;\n"
            "    --bg-accent: var(--accent-600);\n    --density: 1;\n  }\n"
            "  [data-theme=\"dark\"] { --accent-990: #000000; --bg-accent: var(--accent-50); }\n"
            "  @media (prefers-reduced-motion: reduce) { :root { --dur-base: 1ms; } }\n}\n"
            "/* :root { --commented-out: 1px; } */\n"))
        tokens = self.pc.read_tokens([path])
        self.assertEqual({"accent": {"50": "#fff7f0", "600": "oklch(56.5% 0.176 42)"}}, tokens.ramps)
        self.assertEqual(["50", "600"], list(tokens.ramps["accent"]))                 # numeric order
        self.assertEqual({"--bg-accent": "var(--accent-600)"}, tokens.roles)        # the default, not dark's
        self.assertEqual({"md": "48rem"}, tokens.breakpoints)
        self.assertEqual({"--icon": 'url("data:image/svg+xml;utf8,<svg/>")', "--density": "1"},
                         tokens.constants)                                         # one declaration, `;` and all
        self.assertNotIn("--dur-base", tokens.values())
        self.assertNotIn("--commented-out", tokens.values())

    def test_a_tokens_css_and_its_contract_agree(self):
        """The starter's tokens.css, read here and through extract_system's
        contract: the same names, ramps and breakpoints. The tiers differ only
        where extract_system reads the name first, as the docstring says."""
        starter = SKILLS / "web-design-studio" / "assets" / "starter" / "styles" / "tokens.css"
        proc = run_py("design-system-docs", "extract_system", "--tokens", starter, "--out", "system.json",
                      "--contract", "contract.json", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        css, contract = self.pc.read_tokens([starter]), self.pc.read_tokens([self.tmp / "contract.json"])
        self.assertEqual(contract.values(), css.values())
        self.assertEqual(contract.ramps, css.ramps)
        self.assertEqual(contract.breakpoints, css.breakpoints)
        differ = sorted(n for n, tier in contract.tiers().items() if css.tiers()[n] != tier)
        self.assertEqual(["--bg-active", "--bg-hover", "--bg-scrim", "--shadow-focus", "--space-fluid-lg",
                          "--space-fluid-md", "--space-fluid-sm", "--space-fluid-xl"], differ)

    def test_a_later_file_moves_a_name(self):
        """Codex on #78: a name a later file filed in another section stayed
        in the earlier one, so a ramp step that became a role was still a ramp."""
        a = self.write("a.css", ":root { --brand-500: #ff0000; --brand-600: #cc0000; }\n")
        b = self.write("b.css", ":root { --brand-500: var(--accent-500); }\n")
        tokens = self.pc.read_tokens([a, b])
        self.assertEqual({"brand": {"600": "#cc0000"}}, tokens.ramps)
        self.assertEqual({"--brand-500": "var(--accent-500)"}, tokens.roles)

    def test_a_contracts_ramp_steps_are_numbers(self):
        """CodeRabbit on #78: a named step crashed every reader with a traceback."""
        for step in ("primary", "5²"):                                  # `²` is a digit to isdigit()
            with self.subTest(step=step):
                bad = {"schema": "web-design-suite/contract/1", "ramps": {"brand": {step: "#123456"}}}
                with self.assertRaises(self.pc.ConfigError) as caught:
                    self.pc.read_tokens([self.write("bad.json", json.dumps(bad))])
                self.assertIn(f'"ramps.brand.{step}" must be a numeric step', str(caught.exception))

    def test_a_missing_token_file_is_named(self):
        with self.assertRaises(self.pc.ConfigError) as caught:
            self.pc.read_tokens([self.tmp / "gone.css"])
        self.assertIn("gone.css", str(caught.exception))

    def test_a_tokens_css_ramp_step_is_ascii_digits(self):
        """N37: `\\d` took `٥٠٠` as a step, so a tokens.css could declare a ramp
        step that a contract.json refuses and the Node reader never sees."""
        tokens = self.pc.read_tokens([self.write("t.css", ":root { --brand-500: #fff; --brand-٥٠٠: #000; }\n")])
        self.assertEqual({"brand": {"500": "#fff"}}, tokens.ramps)
        self.assertEqual({"brand": {"٥٠٠": "#000"}}, tokens.scales)


class ExtractSystemWritesTheContract(TempDirTest):
    def test_the_contract_holds_the_systems_default_values_by_tier(self):
        self.write("src/styles/tokens.css", TOKENS)
        proc = run_py("design-system-docs", "extract_system", "--tokens", "src/styles/tokens.css",
                      "--out", "system.json", "--contract", "contract.json", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        contract = json.loads((self.tmp / "contract.json").read_bytes())
        self.assertEqual("web-design-suite/contract/1", contract["schema"])
        self.assertEqual(dict(zip(STEPS, PROJECT_ACCENT)), contract["ramps"]["accent"])
        self.assertEqual(STEPS, list(contract["ramps"]["accent"]))       # numeric order, not text
        self.assertEqual({"4": "1rem"}, contract["scales"]["space"])
        self.assertEqual({"md": "48rem"}, contract["breakpoints"])
        self.assertEqual({"--bg-accent": "var(--accent-600)"}, contract["roles"])
        self.assertEqual(b"\n", (self.tmp / "contract.json").read_bytes()[-1:])
        self.assertNotIn(b"\r\n", (self.tmp / "contract.json").read_bytes())
        self.pc = load_script("design-system-docs", "project_config")
        self.pc.read_contract(self.tmp / "contract.json")                  # its own reader accepts it

    def test_only_default_values_and_every_tier1_name(self):
        """Codex on #76: a token declared only in a theme was written as a
        default, and a one-segment Tier-1 name (`--density`) was dropped."""
        self.write("src/styles/tokens.css", TOKENS.replace("  }\n}\n", (
            "    --density: 1;\n  }\n  [data-theme=\"dark\"] {\n    --accent-990: #000000;\n"
            "    --glow-strong: 0 0 1rem var(--accent-500);\n  }\n}\n")))
        proc = run_py("design-system-docs", "extract_system", "--tokens", "src/styles/tokens.css",
                      "--out", "system.json", "--contract", "contract.json", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        contract = json.loads((self.tmp / "contract.json").read_bytes())
        self.assertEqual(STEPS, list(contract["ramps"]["accent"]))       # no dark-only 990
        self.assertNotIn("--glow-strong", contract["roles"])
        self.assertEqual({"--density": "1"}, contract["constants"])

    def test_without_tokens_it_reads_the_projects_config(self):
        self.write(".git/HEAD", "x\n")
        self.write("src/styles/tokens.css", TOKENS)
        self.write(".design-suite.json", '{"schema": 1, "tokens": ["src/styles/tokens.css"]}')
        proc = run_py("design-system-docs", "extract_system", "--out", "system.json", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertIn("tokens from", output(proc))
        names = {t["name"] for t in json.loads((self.tmp / "system.json").read_bytes())["tokens"]}
        self.assertIn("--accent-600", names)

    def test_a_broken_config_stops_the_run(self):
        self.write(".git/HEAD", "x\n")
        self.write(".design-suite.json", '{"schema": 1, "tokenz": []}')
        proc = run_py("design-system-docs", "extract_system", "--out", "system.json", cwd=self.tmp)
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertIn("unknown key 'tokenz'", output(proc))


class FigmaAuditReadsTheContract(TempDirTest):
    """LC-C1: the project's ramps from a contract.json, or from the config."""

    def off_ramp(self, *extra):
        proc = run_py("figma-variables-sync", "figma_audit", "export.json", "--format", "json", *extra,
                      cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return [f for f in json.loads(proc.stdout)["findings"] if f["code"] == "OFF_RAMP_COLOR"]

    def setUp(self):
        super().setUp()
        self.write(".git/HEAD", "x\n")
        self.write("export.json", json.dumps([{"name": f"accent/{s}", "type": "COLOR", "value": h}
                                              for s, h in zip(STEPS, PROJECT_ACCENT)]))
        self.write("src/styles/tokens.css", TOKENS)
        proc = run_py("design-system-docs", "extract_system", "--tokens", "src/styles/tokens.css",
                      "--out", "system.json", "--contract", "contract.json", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))

    def test_tokens_takes_a_contract(self):
        self.assertEqual(11, len(self.off_ramp()))                         # the studio's ramps
        self.assertEqual([], self.off_ramp("--tokens", "contract.json"))

    def test_two_token_files_merge_one_ramp(self):
        """Codex on #76: a second file's part of a ramp replaced the first's."""
        pairs = list(zip(STEPS, PROJECT_ACCENT))
        for name, part in (("a.css", pairs[:5]), ("b.css", pairs[5:])):
            self.write(name, ":root {\n" + "".join(f"  --accent-{s}: {h};\n" for s, h in part) + "}\n")
        self.write(".design-suite.json", '{"schema": 1, "tokens": ["a.css", "b.css"]}')
        self.assertEqual([], self.off_ramp())
        self.write(".design-suite.json", '{"schema": 1}')
        self.assertEqual([], self.off_ramp("--tokens", "a.css", "--tokens", "b.css"))   # CodeRabbit on #78

    def test_the_config_names_the_tokens_and_a_flag_beats_it(self):
        self.write(".design-suite.json", '{"schema": 1, "tokens": "contract.json"}')
        self.assertEqual([], self.off_ramp())
        self.write("other.css", ":root { --accent-500: #ff0000; }\n")
        self.assertTrue(self.off_ramp("--tokens", "other.css"))           # the flag's ramp, not the config's


FLOATS = [("spacing/on", 16), ("spacing/off", 18), ("radius/on", 8), ("radius/off", 10),
          ("font-size/on", 16), ("font-size/off", 17), ("font-size/fluid", 72), ("breakpoint/on", 768),
          ("breakpoint/off", 800), ("duration/on", 140), ("duration/off", 150), ("line-height/on", 1.6),
          ("line-height/off", 1.5), ("font-weight/on", 600), ("font-weight/off", 650), ("z-index/on", 400),
          ("z-index/off", 450), ("stroke/on", 2), ("stroke/off", 3)]


class FigmaAuditReadsTheScales(TempDirTest):
    """LC-C1, LC-B3: a project's scales and breakpoints, not only its ramps."""

    def off_scale(self, *extra):
        proc = run_py("figma-variables-sync", "figma_audit", "export.json", "--format", "json", *extra,
                      cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return sorted(f["name"] for f in json.loads(proc.stdout)["findings"] if f["code"].startswith("OFF_SCALE"))

    def setUp(self):
        super().setUp()
        self.write(".git/HEAD", "x\n")
        self.write("export.json", json.dumps([{"name": n, "type": "FLOAT", "value": v} for n, v in FLOATS]))

    def test_the_starters_own_tokens_change_nothing(self):
        """The control: the starter's scales, read from its tokens.css, are the
        studio's tables (and its --dur-loop)."""
        starter = SKILLS / "web-design-studio" / "assets" / "starter" / "styles" / "tokens.css"
        self.assertEqual(sorted(n for n, _ in FLOATS if n.endswith("/off")), self.off_scale())
        self.assertEqual(self.off_scale(), self.off_scale("--tokens", starter))

    def test_a_projects_scale_replaces_the_studios(self):
        self.write("tokens.css", ":root {\n  --space-sm: 1.125rem;\n  --bp-tablet: 50rem;\n"
                                 "  --dur-quick: 150ms;\n}\n")
        self.write(".design-suite.json", '{"schema": 1, "tokens": "tokens.css"}')
        off = self.off_scale()
        for name in ("spacing/off", "breakpoint/off", "duration/off"):
            self.assertNotIn(name, off)                                     # the project's steps
        for name in ("spacing/on", "breakpoint/on", "duration/on", "radius/off"):
            self.assertIn(name, off)                                        # not the studio's; radius untouched


class AuditReadsTheProject(TempDirTest):
    """LC-C1, XC-C8: audit_design's token files, component globs, ramps and
    baseline from the project's config, and --tokens beating it."""

    def setUp(self):
        super().setUp()
        self.write(".git/HEAD", "x\n")
        self.write("src/design/system.css", "@layer tokens {\n  :root {\n    --brand-500: oklch(55% 0.2 260);\n"
                                            "    --bg-brand: var(--brand-500);\n  }\n}\n")
        self.write("src/components/card.css", "@layer components {\n  .card { color: var(--brand-500); "
                                              "background: var(--bg-brand); }\n}\n")
        self.write("src/widgets/panel.css", "@layer base {\n  .panel { padding: var(--space-4); }\n}\n")

    def findings(self, *extra, code=1):
        proc = run_py("web-design-studio", "audit_design", "src", "--json", *extra, cwd=self.tmp)
        self.assertEqual(code, proc.returncode, output(proc))
        return sorted((f["file"].replace("\\", "/").split("src/")[-1], f["rule"]) for f in json.loads(proc.stdout))

    def config(self, **keys):
        self.write(".design-suite.json", json.dumps({"schema": 1, **keys}))

    def test_without_a_config_the_starters_rules_hold(self):
        self.assertEqual([("design/system.css", "socket-literal")], self.findings())

    def test_the_configs_tokens_and_components(self):
        self.config(tokens="src/design/system.css", components="src/widgets/**/*.css")
        self.assertEqual([("components/card.css", "tier1-leak"), ("widgets/panel.css", "tier1-leak")],
                         self.findings())

    def test_a_contract_names_the_ramps_too(self):
        proc = run_py("design-system-docs", "extract_system", "--tokens", "src/design/system.css",
                      "--out", "system.json", "--contract", "contract.json", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertIn(("components/card.css", "tier1-leak"), self.findings("--tokens", "contract.json"))

    def test_a_flag_beats_the_configs_tokens(self):
        self.config(tokens="src/design/system.css", components="src/widgets/**/*.css")
        self.write("other.css", ":root { --other-500: #ff0000; }\n")
        self.assertEqual([("design/system.css", "socket-literal"), ("widgets/panel.css", "tier1-leak")],
                         self.findings("--tokens", "other.css"))           # the globs still hold

    def test_the_configs_baseline(self):
        self.config(baselines={"audit": "ci/audit-baseline.json"})
        self.write("ci/.keep", "")
        proc = run_py("web-design-studio", "audit_design", "src", "--write-baseline", "ci/audit-baseline.json",
                      cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertEqual([], self.findings(code=0))                         # read without --baseline
        self.assertTrue(self.findings("--baseline", "elsewhere.json"))     # a flag beats it

    def test_a_broken_config_stops_the_run(self):
        self.config(tokens="src/design/missing.css")
        proc = run_py("web-design-studio", "audit_design", "src", cwd=self.tmp)
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertIn("missing.css", output(proc))

    def test_a_copy_vendored_alone_still_audits(self):
        """A project that copied audit_design.py into its scripts/ before 3.5.0
        has no project_config.py: the audit runs as it did, and says so."""
        self.config(tokens="src/design/system.css")
        self.write("scripts/audit_design.py", (SKILLS / "web-design-studio" / "scripts" / "audit_design.py").read_bytes())
        lone = [sys.executable, "-m", "scripts.audit_design", "src", "--json"]
        proc = subprocess.run(lone, cwd=self.tmp, env=env(), capture_output=True, timeout=120)
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn(".design-suite.json is not read", output(proc))
        self.assertIn("socket-literal", proc.stdout.decode("utf-8"))      # the config's token file is not one
        proc = subprocess.run(lone + ["--tokens", "x.css"], cwd=self.tmp, env=env(), capture_output=True, timeout=120)
        self.assertEqual(2, proc.returncode, output(proc))


class FigmaToTokensReadsTheNames(TempDirTest):
    """LC-B3: a project's own names come back recognised, in their tier."""

    def setUp(self):
        super().setUp()
        self.write(".git/HEAD", "x\n")
        self.write("export.json", json.dumps([{"name": "color/brand/500", "type": "COLOR", "value": "#1e5bd7"},
                                              {"name": "bg/brand", "type": "COLOR", "value": "#1e5bd7"}]))
        self.write("brand.css", ":root {\n  --brand-500: oklch(52.4% 0.19 262.1);\n  --bg-brand: var(--brand-500);\n}\n")

    def convert(self, *extra):
        proc = run_py("figma-variables-sync", "figma_to_tokens", "export.json", *extra, cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return proc.stdout.decode("utf-8"), output(proc)

    def test_the_configs_tokens_and_a_flag_beating_them(self):
        css, everything = self.convert()
        self.assertIn("--color-brand-500:", css)
        self.assertIn("`bg/brand` is not a name in the contract", everything)
        self.write(".design-suite.json", '{"schema": 1, "tokens": "brand.css"}')
        css, everything = self.convert()
        self.assertIn("--brand-500:", css)
        self.assertNotIn("--color-brand-500", css)
        self.assertNotIn("is not a name in the contract", everything)
        self.write("other.css", ":root { --other-1: 1px; }\n")
        self.assertIn("--color-brand-500:", self.convert("--tokens", "other.css")[0])


class DiffSystemReadsTheContract(TempDirTest):
    """LC-C1: diff_system takes a contract.json, and the project's tokens as
    the candidate when none is named."""

    def setUp(self):
        super().setUp()
        self.write(".git/HEAD", "x\n")
        self.write("src/styles/tokens.css", TOKENS)
        proc = run_py("design-system-docs", "extract_system", "--tokens", "src/styles/tokens.css",
                      "--out", "system.json", "--contract", "v1.json", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))

    def changes(self, *args, code=0):
        proc = run_py("design-system-versioning", "diff_system", *args, "--format", "json", "--gate", "none",
                      cwd=self.tmp)
        self.assertEqual(code, proc.returncode, output(proc))
        return sorted((c["kind"], c["subject"]) for c in json.loads(proc.stdout)["changes"]) if code == 0 else output(proc)

    def test_two_contracts(self):
        v2 = json.loads((self.tmp / "v1.json").read_bytes())
        v2["ramps"]["accent"]["600"] = "#123456"
        v2["roles"]["--bg-brand"] = "var(--accent-500)"
        self.write("v2.json", json.dumps(v2))
        self.assertEqual([("tier1-value-changed", "--accent-600"), ("tier2-added", "--bg-brand")],
                         self.changes("v1.json", "v2.json"))

    def test_a_contract_against_its_own_tokens_css_has_no_changes(self):
        self.assertEqual([], self.changes("v1.json", "src/styles/tokens.css"))

    def test_a_config_that_mixes_css_and_a_contract(self):
        """Codex on #78: with CSS in the list, its contracts were dropped, so a
        role only a contract held read as removed."""
        extra = {"schema": "web-design-suite/contract/1", "roles": {"--bg-extra": "var(--accent-500)"}}
        self.write("extra.json", json.dumps(extra))
        self.write(".design-suite.json", '{"schema": 1, "tokens": ["src/styles/tokens.css", "extra.json"]}')
        self.assertEqual([("tier2-added", "--bg-extra")], self.changes("v1.json"))

    def test_without_new_the_projects_tokens(self):
        self.assertIn("name the candidate snapshot", self.changes("v1.json", code=2))
        self.write(".design-suite.json", '{"schema": 1, "tokens": "src/styles/tokens.css"}')
        self.assertEqual([], self.changes("v1.json"))
        self.write("src/styles/tokens.css", TOKENS.replace("--space-4: 1rem", "--space-4: 1.25rem"))
        self.assertEqual([("tier1-value-changed", "--space-4")], self.changes("v1.json"))

    def test_without_old_the_published_snapshot_the_config_names(self):
        """P25: `baselines.system` names the published snapshot, for the token
        diff hook and for a run that names neither snapshot."""
        self.write(".design-suite.json", '{"schema": 1, "tokens": "src/styles/tokens.css"}')
        self.assertIn('name it in the project\'s .design-suite.json ("baselines": {"system"', self.changes(code=2))
        self.write(".design-suite.json", json.dumps({"schema": 1, "tokens": "src/styles/tokens.css",
                                                     "baselines": {"system": "v1.json"}}))
        self.assertEqual([], self.changes())
        self.write("src/styles/tokens.css", TOKENS.replace("--space-4: 1rem", "--space-4: 1.25rem"))
        self.assertEqual([("tier1-value-changed", "--space-4")], self.changes())
        self.assertEqual([], self.changes("src/styles/tokens.css"))              # a named one beats it


class ClusterValuesLandsOnTheProjectsRamps(TempDirTest):
    """LC-C1: a migration lands on the project's ramps, not ones it derives."""

    def setUp(self):
        super().setUp()
        self.write(".git/HEAD", "x\n")
        self.write("src/app.css", ".btn { background: #2f6df6; color: #ffffff; }\n.btn:hover { background: #2558c8; }\n")
        self.write("brand.css", ":root {\n  --accent-500: oklch(60% 0.2 150);\n  --accent-600: oklch(52% 0.19 150);\n"
                                "  --accent-450: oklch(64% 0.2 150);\n  --brand-500: #ff0000;\n}\n")
        proc = run_py("design-token-migration", "extract_literals", "src", "--format", "json",
                      "-o", "literals.json", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))

    def propose(self, *extra):
        proc = run_py("design-token-migration", "cluster_values", "literals.json", "-o", "out", *extra, cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        return (self.tmp / "out" / "tokens.css").read_bytes().decode("utf-8"), \
            (self.tmp / "out" / "reconciliation.md").read_bytes().decode("utf-8")

    def accent(self, css, step):
        return re.search(rf"--accent-{step}:\s*([^;]+);", css).group(1)

    def test_the_configs_ramps_and_a_flag_beating_them(self):
        derived, _ = self.propose()
        self.assertNotIn(" 150", self.accent(derived, 600))
        self.write(".design-suite.json", '{"schema": 1, "tokens": "brand.css"}')
        css, report = self.propose()
        self.assertEqual("oklch(52% 0.190 150)", self.accent(css, 600))
        self.assertRegex(self.accent(css, 900), r" 1[45]\d(\.\d)?\)$")       # a step it lacks, on its hue
        self.assertIn("Ramps from the project's tokens: accent (2 of 11 steps)", report)
        self.assertIn("`brand` ramp, which the contract has no roles for", report)
        self.assertNotIn("--accent-450", css)                                 # CodeRabbit on #78: not a contract step
        self.assertIn("steps the contract does not name (--accent-450)", report)
        self.write("off.css", ":root {\n  --accent-450: oklch(64% 0.2 150);\n}\n")
        _, report = self.propose("--tokens", "off.css")                      # nothing taken, so not said to be
        self.assertNotIn("Ramps from the project's tokens", report)
        self.assertIn("steps the contract does not name (--accent-450)", report)
        pinned, _ = self.propose("--accent", "#e8440a")                       # --accent beats the config
        self.assertNotIn(" 150", self.accent(pinned, 600))
        other, _ = self.propose("--tokens", "src/app.css")                    # so does --tokens
        self.assertEqual(self.accent(derived, 600), self.accent(other, 600))


# Part 3: the budgets, the other baselines, emailTokens, stack and the deck's
# tokens, and the Node reader the browser scripts share.

READER_JS = """
import { findConfig, loadConfig } from %s;
const [mode, ...files] = process.argv.slice(1);
const out = files.map((file) => {
  try { return { ok: mode === 'find' ? findConfig(file) : loadConfig(file) }; }
  catch (err) { return { error: err.message }; }
});
console.log(JSON.stringify(out));
"""

CONFIGS = {
    "full": json.dumps({"schema": 1, "tokens": ["src/tokens.css", "../shared/contract.json"],
                        "emailTokens": "emails/email-tokens.json", "components": "src/widgets/**/*.css",
                        "emails": "mail/**/*.html", "stack": "tailwind-v4", "budgets": {"perf": "perf.json", "a11y": "a11y.json"},
                        "baselines": {"audit": "b/audit.json", "snapshots": "snaps/",
                                      "system": "published/system.json"},
                        "hooks": {"designGate": True, "generatedFiles": False, "tokenDiff": True,
                                  "a11yGate": True, "emailBuild": False}}),
    "nulls": '{"schema": 1, "emailTokens": null, "stack": null}',
    "bom": "﻿" + '{"schema": 1, "tokens": "t.css"}',
    "unknown": '{"schema": 1, "token": "x.css", "budget": {}}',
    "no-schema": '{"tokens": "x.css"}',
    "schema-true": '{"schema": true}',
    "schema-text": '{"schema": "1"}',
    "stack": '{"schema": 1, "stack": "bootstrap"}',
    "budget-key": '{"schema": 1, "budgets": {"lcp": "x.json"}}',
    "baselines-null": '{"schema": 1, "baselines": null}',
    "baseline-empty": '{"schema": 1, "baselines": {"audit": " "}}',
    "tokens-number": '{"schema": 1, "tokens": [3]}',
    "tokens-null": '{"schema": 1, "tokens": null}',
    "components-empty": '{"schema": 1, "components": [""]}',
    "components-before-tokens": '{"schema": 1, "tokens": [3], "components": 7}',
    "array": "[1]",
    "trailing-comma": '{"schema": 1,}',
    "comment": '{"schema": 1 /* a comment */}',
    "hooks-key": '{"schema": 1, "hooks": {"designGate": true, "gate": true}}',
    "hooks-value": '{"schema": 1, "hooks": {"designGate": "yes"}}',
    "hooks-list": '{"schema": 1, "hooks": ["designGate"]}',
    "emails-none": '{"schema": 1, "emails": []}',
    "emails-empty": '{"schema": 1, "emails": [""]}',
    "emails-object": '{"schema": 1, "emails": {"mail": "*.html"}}',
    "emails-before-stack": '{"schema": 1, "emails": 3, "stack": "bootstrap"}',
    "hooks-a11y": '{"schema": 1, "hooks": {"a11yGate": "yes"}}',
    "hooks-email": '{"schema": 1, "hooks": {"emailBuild": 1}}',
}


TOKENS_JS = """
import { readTokens, loadConfig, isComponent, isEmail } from %s;
const [mode, ...args] = process.argv.slice(1);
let out;
if (mode === 'tokens') {
  out = JSON.parse(args[0]).map((files) => {
    try { return { ok: readTokens(files) }; } catch (err) { return { error: err.message }; }
  });
} else if (mode === 'emails') {
  const config = loadConfig(args[0]);
  out = JSON.parse(args[1]).map((file) => isEmail(config, file));
} else {
  const config = loadConfig(args[0]);
  const { globs, files } = JSON.parse(args[1]);
  out = globs.map((glob) => files.map((file) => isComponent({ ...config, components: [glob] }, file)));
}
console.log(JSON.stringify(out));
"""

CONTRACT = "web-design-suite/contract/1"
DTCG_EVERY_FORM = {
    "brand": {"$type": "color",
              "500": {"$value": {"colorSpace": "srgb", "components": [0.909804, 0.266667, 0.039216], "hex": "#e8440a"}},
              "600": {"$value": {"colorSpace": "srgb-linear", "components": [0.5, 0.2, 0.01]}},
              "700": {"$value": {"colorSpace": "hsl", "components": [-30, 80, 40]}},
              "800": {"$value": {"colorSpace": "hwb", "components": [400, 10, 20]}},
              "900": {"$value": {"colorSpace": "oklch", "components": [0.62, 0.19, "none"], "alpha": 0.5}},
              "950": {"$value": {"colorSpace": "oklab", "components": ["0.5", -0.1, 0.1]}},
              "960": {"$value": {"colorSpace": "lab", "components": [50, 40, 59.5]}},
              "970": {"$value": {"colorSpace": "lch", "components": [50, 30, 270], "alpha": 0.0078125}},
              "980": {"$value": {"colorSpace": "display-p3", "components": [1, 0, 0]}},
              "990": {"$value": {"colorSpace": "display-p3", "components": [1, 0, 0], "hex": "#ff0000"}},
              "991": {"$value": {"colorSpace": "rec2020", "components": [0.5, 0.5, 0.5], "alpha": 1}},
              "992": {"$value": {"colorSpace": "srgb", "components": [0.5, 0.5, 0.5], "alpha": 0.25}},
              "993": {"$value": {"colorSpace": "srgb", "components": "abc"}},
              "$root": {"$value": {"colorSpace": "srgb", "components": [1, 0, 0]}}},
    "bg": {"$type": "color", "brand": {"$value": "{brand.$root}"}, "pointer": {"$ref": "#/brand/$root"},
           "mid": {"$value": "{brand.500}"}, "deep": {"$ref": "#/brand/600/$value"},
           "bad": {"$ref": "#/brand/600/$value/components/0"}},
    "space": {"$type": "dimension", "4": {"$value": {"value": 1, "unit": "rem"}},
              "6": {"$value": {"value": 24, "unit": "px"}}, "big": {"$value": {"value": 1234567, "unit": "px"}},
              "neg": {"$value": {"value": -0.0000001, "unit": "px"}}},
    "dur": {"$type": "duration", "base": {"$value": {"value": 0.22, "unit": "s"}},
            "fast": {"$value": {"value": 140, "unit": "ms"}}},
    "density": {"$value": 1.5, "$type": "number"},
    "weight": {"bold": {"$value": 700, "$type": "fontWeight"}},
    "font": {"sans": {"$type": "fontFamily", "$value": ["Geist Sans", "system-ui", "sans-serif"]}},
    "ease": {"out": {"$type": "cubicBezier", "$value": [0, 0, 0.58, 1]}},
    "shadow": {"md": {"$type": "shadow", "$value": [
        {"color": "{brand.500}", "offsetX": {"value": 0, "unit": "px"}, "offsetY": {"value": 2, "unit": "px"},
         "blur": "{space.6}", "spread": {"value": 0, "unit": "px"}},
        {"color": {"colorSpace": "srgb", "components": [0, 0, 0], "alpha": 0.1}, "offsetX": {"value": 0, "unit": "px"},
         "offsetY": {"value": 6, "unit": "px"}, "blur": {"value": 12, "unit": "px"},
         "spread": {"value": 0, "unit": "px"}, "inset": True}]}},
    "border": {"focus": {"$type": "border", "$value": {"width": {"value": 2, "unit": "px"}, "style": "solid",
                                                       "color": "{brand.$root}"}}},
    "motion": {"hover": {"$type": "transition", "$value": {"duration": {"value": 140, "unit": "ms"},
                                                           "timingFunction": [0, 0, 0.58, 1]}}},
    "type": {"body": {"$type": "typography", "$value": {"fontFamily": "{font.sans}", "fontSize": "{space.4}"}}},
    "flag": {"on": {"$type": "boolean", "$value": True}},
    "legacy": {"$value": "16px", "$type": "dimension"},
}
STUDIO_LEGACY = {
    "global": {"neutral": {"0": {"value": "#ffffff", "type": "color"}, "900": {"value": "#1f1d1b", "type": "color"}},
               "space": {"base": {"value": "4", "type": "spacing"}, "6": {"value": "{space.base} * 6", "type": "spacing"},
                         "half": {"value": "({space.base} + 2) / 4", "type": "spacing"},
                         "neg": {"value": "-{space.base} - 1", "type": "spacing"},
                         "mixed": {"value": "{space.base} + 1rem", "type": "spacing"},
                         "zero": {"value": "{space.base} / 0", "type": "spacing"},
                         "lost": {"value": "{space.nowhere} * 2", "type": "spacing"},
                         "fluid": {"value": "calc(1rem + 2vw)", "type": "spacing"}},
               "opacity": {"hover": {"value": "0.08 * 2", "type": "opacity"}},
               "font": {"sans": {"value": "Inter, sans-serif", "type": "fontFamilies"},
                        "bold": {"value": "700", "type": "fontWeights"}}},
    "light": {"bg": {"surface": {"value": "{neutral.0}", "type": "color", "description": "the page"}}},
    "dark": {"bg": {"surface": {"value": "{neutral.900}", "type": "color"}}},
    "$themes": [{"id": "l", "name": "Light", "selectedTokenSets": {"global": "source", "light": "enabled"}},
                {"id": "d", "name": "Dark", "selectedTokenSets": {"global": "source", "dark": "enabled"}}],
    "$metadata": {"tokenSetOrder": ["global", "light", "dark"]},
}
STUDIO_GROUPS = {
    "core": {"$type": "color", "blue": {"$value": "#2f6df6"}, "red": {"$value": "#e5484d"},
             "size": {"$type": "sizing", "1": {"$value": 8}, "2": {"$value": "{size.1} * 2"}}},
    "brand/a": {"accent": {"$type": "color", "$value": "{blue}"}},
    "brand/b": {"accent": {"$type": "color", "$value": "{red}"}, "gone": {"$type": "color", "$value": "{core.red}"}},
    "mode/light": {"bg": {"$type": "color", "$value": "#ffffff"}},
    "mode/dark": {"bg": {"$type": "color", "$value": "#000000"}},
    "spare": {"unused": {"$type": "color", "$value": "#123456"}},
    "$themes": [{"name": "A", "group": "brand", "selectedTokenSets": {"core": "source", "brand/a": "enabled"}},
                {"name": "B", "group": "brand", "selectedTokenSets": {"core": "source", "brand/b": "enabled"}},
                {"name": "Light", "group": "mode", "selectedTokenSets": {"mode/light": "enabled", "spare": "disabled"}},
                {"name": "Dark", "group": "mode", "selectedTokenSets": {"mode/dark": "enabled"}}],
    "$metadata": {"tokenSetOrder": ["core", "mode/light", "mode/dark", "brand/a", "brand/b"]},
}
STUDIO_ORDER = {                                     # the source set comes later in the order
    "light": {"bg": {"surface": {"value": "#ffffff", "type": "color"}}},
    "base": {"bg": {"surface": {"value": "#eeeeee", "type": "color"}}, "neutral": {"0": {"value": "#fff", "type": "color"}}},
    "$themes": [{"name": "Light", "selectedTokenSets": {"light": "enabled", "base": "source"}}],
    "$metadata": {"tokenSetOrder": ["light", "base"]},
}
TOKEN_FILES = {
    "layers.css": (
        "@layer reset, tokens;\n@layer tokens {\n  :root, [data-theme] {\n"
        "    --accent-600: oklch(56.5% 0.176 42);\n    --accent-50:  #FFF7F0;\n"
        "    --icon: url(\"data:image/svg+xml;utf8,<svg/>\");\n    --bp-md: 48rem;\n"
        "    --bg-accent: var(--accent-600);\n    --density: 1;\n    --edge-: 2px;\n    ---odd: 1;\n"
        "    --p3-500: color(display-p3 1 0 0);\n    --quote: 'a;b}';\n  }\n"
        "  [data-theme=\"dark\"] { --accent-990: #000000; }\n  [data-density=compact] { --space-4: 0.75rem; }\n"
        "  @media (prefers-reduced-motion: reduce) { :root { --dur-base: 1ms; } }\n"
        "  html { --accent-600: #123456; }\n  :where(:root) { --space-4: 1rem; }\n  * { --star-1: #fff; }\n"
        "  :rooted { --nope-1: #fff; }\n}\n/* :root { --commented-out: 1px; } */\n"),
    "digits.css": ":root { --brand-500: #fff; --brand-٥٠٠: #000; }\n",
    "a.css": ":root { --brand-500: #ff0000; --brand-600: #cc0000; }\n",
    "b.css": ":root { --brand-500: var(--accent-500); --brand-700: #990000; }\n",
    "contract.json": json.dumps({"schema": CONTRACT, "ramps": {"brand": {"500": "#123456", "50": "#fff"},
                                                               "__proto__": {"1": "#000"}, "empty": {}},
                                 "scales": {"space": {"4": "1rem"}}, "roles": {"--bg-brand": "var(--brand-500)"},
                                 "breakpoints": {"md": "48rem"}, "constants": {"--density": "1"}}),
    "bad-schema.json": '{"schema": "x"}',
    "bad-ramps.json": json.dumps({"schema": CONTRACT, "ramps": []}),
    "bad-step.json": json.dumps({"schema": CONTRACT, "ramps": {"brand": {"5²": "#fff"}}}),
    "bad-scale.json": json.dumps({"schema": CONTRACT, "scales": {"space": "1rem"}}),
    "bad-role.json": json.dumps({"schema": CONTRACT, "roles": {"--x": 3}}),
    "not-json.json": "{",
    "utf16be.json": ("﻿" + json.dumps({"schema": CONTRACT, "ramps": {"brand": {"500": "#123456"}}})).encode("utf-16-be"),
    # P31: DTCG 2025.10 documents, every value form dtcg.py writes as CSS.
    "dtcg.tokens.json": json.dumps(DTCG_EVERY_FORM),
    "extends.tokens": json.dumps({"base": {"$type": "color", "fg": {"$value": "#111111"}, "bg": {"$value": "#ffffff"}},
                                  "print": {"$extends": "{base}", "fg": {"$value": "#000000"}},
                                  "loop": {"$extends": "{loop}", "x": {"$value": "#010101", "$type": "color"}}}),
    "legacy.json": json.dumps({"global": {"neutral": {"0": {"value": "#ffffff", "type": "color"}}}}),
    "schema-and-tokens.json": json.dumps({"schema": "x", "a": {"$value": "#fff", "$type": "color"}}),
    # P31 part 2: Tokens Studio exports, legacy and 2025.10 keys, themes, groups and math.
    "studio.json": json.dumps(STUDIO_LEGACY),
    "studio-groups.json": json.dumps(STUDIO_GROUPS),
    "studio-order.json": json.dumps(STUDIO_ORDER),
    "deep.tokens.json": json.dumps({"top": {"$type": "color", "$value": "#fff"}, "deep": json.loads(
        '{"g": ' * 70 + '{"$type": "color", "$value": "#000"}' + "}" * 70)}),
    "names.tokens.json": json.dumps({"Button background": {"$type": "color", "$value": "#ffffff"},
                                     "A/B (x)": {"$type": "color", "$value": "{Button background}"},
                                     "veil": {"$type": "color", "$value": {"colorSpace": "srgb", "components": [1, 0, 0],
                                                                           "alpha": 0.9995}},
                                     "loop": {"$extends": "{loop}", "x": {"$type": "color", "$value": "#010101"}},
                                     "p": {"$extends": "{q}", "x": {"$type": "color", "$value": "#020202"}},
                                     "q": {"$extends": "{p}", "y": {"$type": "color", "$value": "#030303"}}}),
}
TOKEN_CASES = [["layers.css"], ["digits.css"], ["a.css", "b.css"], ["b.css", "a.css"], ["contract.json"],
               ["contract.json", "a.css"], ["a.css", "contract.json"], ["bad-schema.json"], ["bad-ramps.json"],
               ["bad-step.json"], ["bad-scale.json"], ["bad-role.json"], ["not-json.json"], ["gone.css"],
               ["gone.json"], ["a.css", "gone.css"], [], ["utf16be.json"],
               ["dtcg.tokens.json"], ["extends.tokens"], ["a.css", "dtcg.tokens.json"], ["dtcg.tokens.json", "a.css"],
               ["legacy.json"], ["schema-and-tokens.json"], ["studio.json"], ["studio-groups.json"], ["studio-order.json"],
               ["deep.tokens.json"], ["names.tokens.json"]]

# The component globs, odd ones included, and the paths they are tried on
# (test_real_tools tries the same through stylelint's own matcher).
GLOBS = ["src/widgets/**", "src/widgets/**/*.css", "**/*.widget.css", "src/*/card.css", "src/w?dgets/*.css", "**",
         "*.css", "src/**.css", "src/a**b/*.css", "src/**x", "src/***/x.css", "src/****/x.css", "src/x**/y.css",
         "src/x**", "src/(legacy)/*.css", "src/[id]/*.css", "src/{a,b}/*.css", "src/a+b/*.css", "src/@scope/*.css",
         "src/!x/*.css", "/src/widgets/*.css", "src\\widgets\\*.css", "src/Components/*.css", "src/**/**/*.css",
         "src/**/*/**/x.css", ".hidden/**", "src/a?(b)/*.css", "src/*(x)/*.css", "src/a.b/*.css"]
GLOB_PATHS = ["src/widgets/card.css", "src/widgets/deep/card.css", "src/widgets/card.tsx", "src/card.widget.css",
              "card.widget.css", "src/other/card.css", "src/wodgets/a.css", "x.css", "src/x.css", "src/a/b/c.css",
              "src/ab/c.css", "src/axb/c.css", "src/a/y/b/c.css", "src/qx", "src/a/b/x", "src/a/x.css",
              "src/x/y.css", "src/xz/y.css", "src/x/z/y.css", "src/(legacy)/a.css", "src/l/a.css", "src/[id]/a.css",
              "src/i/a.css", "src/{a,b}/a.css", "src/a/a.css", "src/a+b/a.css", "src/aab/a.css",
              "src/@scope/a.css", "src/!x/a.css", "src/Components/a.css", "src/components/a.css",
              ".hidden/a.css", "src/.hidden.css", "src/ax(b)/a.css", "src/q(x)/a.css", "src/a.b/c.css"]


@unittest.skipUnless(NODE, "node is not installed")
class TheNodeReaderAgrees(TempDirTest):
    """XC-C8: the browser scripts read .design-suite.json through
    browser_common.mjs's projectConfig(), which must accept, refuse and
    resolve exactly what shared/project_config.py does."""

    def setUp(self):
        super().setUp()
        self.pc = load_script("design-system-docs", "project_config")

    def node(self, mode, files):
        script = READER_JS % json.dumps((PLUGIN / "shared" / "browser_common.mjs").as_uri())
        proc = subprocess.run([NODE, "--input-type=module", "-e", script, mode, *map(str, files)],
                              cwd=self.tmp, env=env(), capture_output=True, timeout=60)
        self.assertEqual(0, proc.returncode, output(proc))
        return json.loads(proc.stdout)

    def python(self, file):
        try:
            c = self.pc.load_config(file)
        except self.pc.ConfigError as exc:
            return {"error": str(exc)}
        return {"ok": {"path": str(c.path), "root": str(c.root), "tokens": [str(p) for p in c.tokens],
                       "emailTokens": str(c.email_tokens) if c.email_tokens else None,
                       "components": c.components, "emails": c.emails, "stack": c.stack,
                       "budgets": {k: str(v) for k, v in c.budgets.items()},
                       "baselines": {k: str(v) for k, v in c.baselines.items()}, "hooks": c.hooks}}

    def test_every_config_reads_the_same(self):
        files = [self.write(f"{name}/.design-suite.json", text) for name, text in CONFIGS.items()]
        text = '{"schema": 1, "stack": "css-modules"}'          # Codex on #81: every encoding json.loads finds
        encoded = {"utf16": text.encode("utf-16"), "utf16be": ("﻿" + text).encode("utf-16-be"),
                   "utf16le-bare": text.encode("utf-16-le"), "utf32": text.encode("utf-32"),
                   "utf32be-bare": text.encode("utf-32-be"), "utf8-broken": b'{"schema": 1, "stack": "\xff"}'}
        files += [self.write(f"{name}/.design-suite.json", data) for name, data in encoded.items()]

        def same(result):
            if "error" in result:
                return {"error": re.sub(r"not JSON \(.*\)$", "not JSON", result["error"])}
            return result

        for file, from_node in zip(files, self.node("load", files)):
            with self.subTest(config=file.parent.name):
                self.assertEqual(same(self.python(file)), same(from_node))
        self.assertIn("ok", self.python(files[0]))                           # the cases cover both
        self.assertIn("error", self.python(files[3]))

    def test_the_walk_up_is_the_same(self):
        self.write(".design-suite.json", '{"schema": 1}')
        self.write("repo/.git/HEAD", "x\n")
        deep = self.tmp / "repo" / "src" / "app"
        deep.mkdir(parents=True)
        self.assertEqual([{"ok": None}], self.node("find", [deep]))         # not the one above the repository
        own = self.write("repo/.design-suite.json", '{"schema": 1}')
        self.assertEqual(own.resolve(), self.pc.find_config(deep))
        self.assertEqual([{"ok": str(own.resolve())}], self.node("find", [deep]))

    def run_node(self, mode, *args):
        script = TOKENS_JS % json.dumps(NODE_MASTER.as_uri())
        proc = subprocess.run([NODE, "--input-type=module", "-e", script, mode, *args],
                              cwd=self.tmp, env=env(), capture_output=True, timeout=60)
        self.assertEqual(0, proc.returncode, output(proc))
        return json.loads(proc.stdout)

    def test_the_token_files_read_the_same(self):
        """N37: the lint configs take a project's ramps from readTokens(), a
        port of read_tokens(): the same sections, values, order of files and
        refusals, on a tokens.css, a contract.json and both together."""
        for name, text in TOKEN_FILES.items():
            self.write(name, text)
        cases = [[str(self.tmp / name) for name in case] for case in TOKEN_CASES]

        def python(files):
            try:
                t = self.pc.read_tokens(files)
            except self.pc.ConfigError as exc:
                return {"error": re.sub(r"not JSON \(.*\)$", "not JSON", str(exc))}
            return {"ok": {"ramps": t.ramps, "scales": t.scales, "roles": t.roles,
                           "breakpoints": t.breakpoints, "constants": t.constants}}

        for case, from_node in zip(cases, self.run_node("tokens", json.dumps(cases))):
            if "error" in from_node:
                from_node["error"] = re.sub(r"not JSON \(.*\)$", "not JSON", from_node["error"])
            with self.subTest(files=[pathlib.Path(f).name for f in case]):
                self.assertEqual(python(case), from_node)
                if "ok" in from_node:                    # ramp steps in numeric order, as Python's
                    self.assertEqual([list(s) for s in python(case)["ok"]["ramps"].values()],
                                     [list(s) for s in from_node["ok"]["ramps"].values()])
        self.assertIn("٥٠٠", python(cases[1])["ok"]["scales"]["brand"])           # not a ramp step
        dtcg_case = python(cases[TOKEN_CASES.index(["dtcg.tokens.json"])])["ok"]   # a DTCG file holds values (CodeRabbit)
        self.assertEqual("var(--brand)", dtcg_case["roles"]["--bg-brand"])
        self.assertEqual("lab(50 40 59.5)", dtcg_case["ramps"]["brand"]["960"])
        deep = python(cases[TOKEN_CASES.index(["deep.tokens.json"])])["ok"]
        self.assertEqual({}, deep["scales"])

    def test_the_component_globs_match_the_same(self):
        """N37: ESLint asks isComponent() which JSX files are components, as
        the audit asks is_component(): glob by glob, the same answer."""
        config = self.pc.load_config(self.write("site/.design-suite.json", '{"schema": 1}'))
        files = [str(self.tmp / "site" / rel) for rel in GLOB_PATHS] + [str(self.tmp / "src" / "widgets" / "a.css")]
        from_node = self.run_node("globs", str(config.path), json.dumps({"globs": GLOBS, "files": files}))
        for glob, answers in zip(GLOBS, from_node):
            one = dataclasses.replace(config, components=[glob])
            with self.subTest(glob=glob):
                self.assertEqual([one.is_component(f) for f in files], answers)
                self.assertFalse(answers[-1])                         # outside the project
        self.assertEqual(len(GLOBS), sum(1 for answers in from_node if any(answers)))   # each matches something

    def test_the_email_templates_are_the_same(self):
        """DL-C7: the hook asks isEmail() which file is an email template, by
        `emails`, which is `emails/**/*.html` when the config leaves it out."""
        rels = ["emails/welcome.html", "emails/2026/receipt.html", "emails/email-tokens.json",
                "mail/welcome.html", "src/emails/welcome.html"]
        for text, expected in (('{"schema": 1}', [True, True, False, False, False]),
                               ('{"schema": 1, "emails": ["mail/*.html", "src/**/emails/*.html"]}',
                                [False, False, False, True, True]),
                               ('{"schema": 1, "emails": []}', [False] * 5)):
            with self.subTest(config=text):
                config = self.pc.load_config(self.write("site/.design-suite.json", text))
                files = [str(self.tmp / "site" / rel) for rel in rels] + [str(self.tmp / "emails" / "a.html")]
                self.assertEqual(expected + [False], [config.is_email(f) for f in files])   # the last is outside
                self.assertEqual(expected + [False], self.run_node("emails", str(config.path), json.dumps(files)))


class TheConfigsFilesReachTheirScripts(TempDirTest):
    """XC-C8: each script that takes a budget, a baseline, the email tokens,
    the stack or the deck's tokens reads it from the config, and a flag beats
    it. A file the config names but that is missing or broken is named in the
    script's own message, which is how these tests see that it was read."""

    def setUp(self):
        super().setUp()
        self.write(".git/HEAD", "x\n")
        self.write("page.html", "<!doctype html><html lang=en><title>t</title><main>hi</main></html>\n")

    def config(self, **keys):
        self.write(".design-suite.json", json.dumps({"schema": 1, **keys}))

    def test_perf_audit_budget_and_baseline(self):
        self.config(budgets={"perf": "ci/perf-budget.json"}, baselines={"perf": "ci/perf-baseline.json"})
        self.write("ci/perf-baseline.json", "{not json")
        proc = run_py("perf-budget-gate", "perf_audit", "page.html", cwd=self.tmp)
        self.assertIn("perf-budget.json not found", output(proc))
        self.assertRegex(output(proc), r"could not read baseline .*perf-baseline\.json")
        proc = run_py("perf-budget-gate", "perf_audit", "page.html", "--budget", "mine.json",
                      "--baseline", "mine-baseline.json", cwd=self.tmp)
        self.assertIn("mine.json not found", output(proc))
        self.assertNotIn("could not read baseline", output(proc))

    def test_a11y_static_baseline(self):
        self.config(baselines={"a11y": "ci/a11y-baseline.json"})
        self.write("ci/a11y-baseline.json", "{not json")
        proc = run_py("a11y-audit-runner", "a11y_static", "page.html", cwd=self.tmp)
        self.assertRegex(output(proc), r"could not read baseline .*a11y-baseline\.json")
        proc = run_py("a11y-audit-runner", "a11y_static", "page.html", "--baseline", "none.json", cwd=self.tmp)
        self.assertNotIn("could not read baseline", output(proc))

    def test_a11y_static_vendored_alone(self):
        """Codex on #79: the hook recipe copies a11y_static.py alone into a
        project's scripts/, and without its reader every run raised NameError."""
        self.config(baselines={"a11y": "ci/a11y-baseline.json"})
        self.write("scripts/a11y_static.py", (SKILLS / "a11y-audit-runner" / "scripts" / "a11y_static.py").read_bytes())
        proc = subprocess.run([sys.executable, "-m", "scripts.a11y_static", "page.html", "--json"], cwd=self.tmp,
                              env=env(), capture_output=True, timeout=120)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        self.assertNotIn("Error", output(proc))
        self.assertEqual("a11y_static", json.loads(proc.stdout)["tool"])

    def test_build_docs_check_baseline(self):
        self.write("tokens.css", TOKENS)
        proc = run_py("design-system-docs", "extract_system", "--tokens", "tokens.css", "--out", "system.json",
                      cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        self.config(baselines={"docs": "docs/committed.json"})
        proc = run_py("design-system-docs", "build_docs", "system.json", "--out", "site", "--check", cwd=self.tmp)
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertIn("committed.json does not exist", output(proc))
        self.assertIn("correct baselines.docs", output(proc))                 # CodeRabbit on #79: not "--baseline"
        self.assertNotIn("--baseline", output(proc))
        proc = run_py("design-system-docs", "build_docs", "system.json", "--out", "site", "--check",
                      "--baseline", "mine.json", cwd=self.tmp)
        self.assertIn("--baseline mine.json does not exist", output(proc))     # a flag beats the config

    def test_the_email_scripts_read_email_tokens_not_tokens(self):
        bundled = SKILLS / "email-template-system" / "assets" / "email-tokens.json"
        template = SKILLS / "email-template-system" / "assets" / "templates" / "newsletter.html"
        self.config(tokens="site-tokens.css", emailTokens="emails/missing-tokens.json")
        for module, args in (("build_email", [template, "-o", "out.html"]), ("lint_email", ["--source", template])):
            with self.subTest(script=module):
                proc = run_py("email-template-system", module, *args, cwd=self.tmp)
                self.assertEqual(2, proc.returncode, output(proc))
                self.assertIn("missing-tokens.json", output(proc))
                self.assertNotIn("site-tokens.css", output(proc))
                proc = run_py("email-template-system", module, *args, "--tokens", bundled, cwd=self.tmp)
                self.assertNotIn("missing-tokens.json", output(proc))

    def test_the_deck_takes_the_configs_css(self):
        from test_deck import REVERSED_LOG
        self.write("DECISION_LOG.md", REVERSED_LOG)
        self.write("brand/tokens.css", (SKILLS / "client-presentation-builder" / "assets" / "deck-tokens.css").read_bytes())
        self.config(tokens=["brand/tokens.css", "brand/contract.json"])
        proc = run_py("client-presentation-builder", "build_presentation", "DECISION_LOG.md", cwd=self.tmp)
        self.assertRegex(output(proc), r"tokens: \S*brand.tokens\.css\s")   # the CSS, not the contract

    def test_scaffold_ui_stack(self):
        self.write("schema.sql", "CREATE TABLE posts (\n    id uuid PRIMARY KEY,\n    title text NOT NULL\n);\n")
        proc = run_py("content-model-to-ui", "introspect_schema", "schema.sql", "-o", "model.json", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        self.config(stack="tailwind-v4")
        proc = run_py("content-model-to-ui", "scaffold_ui", "model.json", "--out", "src", "--dry-run", cwd=self.tmp)
        self.assertIn("[tailwind]", output(proc))
        proc = run_py("content-model-to-ui", "scaffold_ui", "model.json", "--out", "src", "--dry-run",
                      "--stack", "css-modules", cwd=self.tmp)
        self.assertIn("[css-modules]", output(proc))

    @unittest.skipUnless(NODE, "node is not installed")
    def test_the_browser_scripts(self):
        self.config(budgets={"perf": "ci/perf.json", "a11y": "ci/a11y.json"})
        no_path = {"NODE_PATH": None}
        proc = run_node("perf-budget-gate", "measure_vitals.mjs", "page.html", cwd=self.tmp, env_changes=no_path)
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertRegex(output(proc), r"no such budget file: .*perf\.json")
        proc = run_node("perf-budget-gate", "measure_vitals.mjs", "page.html", "--budget", "mine.json",
                        cwd=self.tmp, env_changes=no_path)
        self.assertIn("no such budget file: mine.json", output(proc))
        proc = run_node("a11y-audit-runner", "a11y_runtime.mjs", "--file", "page.html", "--axe", "page.html",
                        cwd=self.tmp, env_changes=no_path)
        self.assertRegex(output(proc), r"no such budget file: .*a11y\.json")
        self.write(".design-suite.json", '{"schema": 1, "baseline": {}}')
        proc = run_node("component-state-matrix", "snapshot_matrix.mjs", "page.html", cwd=self.tmp,
                        env_changes=no_path)
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertIn("unknown key 'baseline'", output(proc))
