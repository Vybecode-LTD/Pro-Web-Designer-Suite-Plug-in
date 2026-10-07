"""The project contract (P24 part 1: XC-C8, LC-C1, LC-B3).

A project could tell the scripts where its tokens were only flag by flag, and
only figma_audit and extract_system took a flag. `.design-suite.json` names a
project's token files, component globs, stack, budgets and baselines once, and
shared/project_config.py reads it for every script, with a copy in each skill
that uses it. extract_system writes a `contract.json`, the token system's
default values by tier, which figma_audit's `--tokens` reads as it reads a
tokens.css.
"""
from __future__ import annotations

import json
import re
import unittest

from test_figma_sync import PROJECT_ACCENT, STEPS
from wds_support import PLUGIN, SKILLS, TempDirTest, load_script, output, run_py

MASTER = PLUGIN / "shared" / "project_config.py"
TOKENS = ("@layer tokens {\n  :root {\n" + "".join(f"    --accent-{s}: {h};\n" for s, h in zip(STEPS, PROJECT_ACCENT))
          + "    --space-4: 1rem;\n    --bp-md: 48rem;\n    --bg-accent: var(--accent-600);\n  }\n}\n")


class TheCopiesAreTheMaster(unittest.TestCase):
    """A skill installed alone has only its own folder, so each skill whose
    scripts read the config keeps a byte-identical copy of the master."""

    def test_every_reader_has_the_master_copy_beside_it(self):
        readers = sorted({p.parent for p in SKILLS.glob("*/scripts/*.py")
                          if re.search(r"^\s*from \.?project_config import", p.read_text(encoding="utf-8"), re.M)})
        self.assertEqual(["design-system-docs", "figma-variables-sync"], [r.parent.name for r in readers])
        copies = sorted(p.parent for p in SKILLS.glob("*/scripts/project_config.py"))
        self.assertEqual(readers, copies)
        master = MASTER.read_bytes()
        self.assertEqual([], [str(c.relative_to(PLUGIN)) for c in copies
                              if (c / "project_config.py").read_bytes() != master],
                         "copy shared/project_config.py over these")


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

    def test_the_config_names_the_tokens_and_a_flag_beats_it(self):
        self.write(".design-suite.json", '{"schema": 1, "tokens": "contract.json"}')
        self.assertEqual([], self.off_ramp())
        self.write("other.css", ":root { --accent-500: #ff0000; }\n")
        self.assertTrue(self.off_ramp("--tokens", "other.css"))           # the flag's ramp, not the config's
