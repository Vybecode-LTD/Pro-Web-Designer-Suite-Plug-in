"""An output never replaces an input (the owner's audit of 2026-10-14, class 5).

V7, E9 and G4: `--out` equal to the input replaced a Figma export with its
audit report, a published snapshot with its diff, an email's source with its
build, the findings with their critique, and an audited page with its JSON
report, each with exit 0. `--emit-css DIR` wrote DIR/tokens.css over the
project's own. One helper decides, project_config.py's refuse_overwrite() (in
Node, browser_common.mjs's refuseOverwrite()), and every writer calls it before
it writes anything: exit 2, the input untouched.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import unittest

from wds_support import NODE, PLUGIN, SKILLS, TempDirTest, env, load_script, output, run_node, run_py

SHARED = PLUGIN / "shared"
STARTER = SKILLS / "web-design-studio" / "assets" / "starter" / "styles" / "tokens.css"
EMAIL = '<!doctype html><html lang="en"><head><title>t</title></head><body><p>Hi</p></body></html>\n'
DECISIONS = ("# Test deck\n\n## Decisions\n\n### D1 — Tokens\n"
             "**Constraint:** Many developers touch the CSS.\n**Choice:** A closed token system.\n")
MATRIX = json.dumps({"$schema": "component-state-matrix/1", "themes": ["light"],
                     "densities": ["comfortable"],
                     "components": [{"name": "chip", "css": "chip.css",
                                     "template": '<button class="chip">Chip</button>',
                                     "states": ["default", "hover"]}]})

# (skill, script, the files the case writes, its arguments). Each argument
# list names an input as the output.
CASES = {
    "figma_audit": ("figma-variables-sync", "figma_audit.py", {"export.json": "{}"},
                    ["export.json", "--out", "export.json"]),
    "figma_to_tokens --out": ("figma-variables-sync", "figma_to_tokens.py", {"export.json": "{}"},
                              ["export.json", "--format", "css", "--out", "export.json"]),
    "figma_to_tokens --out-dir": ("figma-variables-sync", "figma_to_tokens.py", {"d/tokens.json": "{}"},
                                  ["d/tokens.json", "--format", "dtcg", "--out-dir", "d"]),
    "diff_system": ("design-system-versioning", "diff_system.py", {"old.css": STARTER, "new.css": STARTER},
                    ["old.css", "new.css", "--out", "old.css"]),
    "deprecate mapping": ("design-system-versioning", "deprecate.py", {"ledger.json": '{"deprecations": []}'},
                          ["--ledger", "ledger.json", "mapping", "-o", "ledger.json"]),
    "build_email": ("email-template-system", "build_email.py", {"email.html": EMAIL},
                    ["email.html", "--out", "email.html"]),
    "lint_email": ("email-template-system", "lint_email.py", {"email.html": EMAIL},
                   ["email.html", "-o", "email.html"]),
    "build_presentation -o": ("client-presentation-builder", "build_presentation.py",
                              {"DECISION_LOG.md": DECISIONS}, ["DECISION_LOG.md", "-o", "DECISION_LOG.md"]),
    "build_presentation --emit-css": ("client-presentation-builder", "build_presentation.py",
                                      {"DECISION_LOG.md": DECISIONS, "styles/tokens.css": STARTER},
                                      ["DECISION_LOG.md", "--tokens", "styles/tokens.css", "--emit-css", "styles"]),
    "critique_report": ("design-critique-gate", "critique_report.py", {"findings.json": "[]"},
                        ["findings.json", "-o", "findings.json"]),
    "extract_system": ("design-system-docs", "extract_system.py", {"tokens.css": STARTER},
                       ["tokens.css", "--out", "tokens.css"]),
    "extract_literals": ("design-token-migration", "extract_literals.py", {"a.css": ".a { margin: 13px; }\n"},
                         ["a.css", "-o", "a.css"]),
    "introspect_schema": ("content-model-to-ui", "introspect_schema.py",
                          {"schema.sql": "create table t (id int primary key);\n"},
                          ["schema.sql", "-o", "schema.sql"]),
    "generate_matrix": ("component-state-matrix", "generate_matrix.py",
                        {"matrix.json": MATRIX, "chip.css": ".chip { color: red; }\n"},
                        ["matrix.json", "--out", "chip.css"]),
    # Codex on #136: the files an input stands for, not its spelling.
    "introspect_schema, a glob": ("content-model-to-ui", "introspect_schema.py",
                                  {"m/001.sql": "create table t (id int primary key);\n"},
                                  ["m/*.sql", "-o", "m/001.sql"]),
    "extract_literals, a folder": ("design-token-migration", "extract_literals.py",
                                   {"src/a.css": ".a { margin: 13px; }\n"}, ["src", "-o", "src/a.css"]),
    "diff_system, a snapshot's second file": ("design-system-versioning", "diff_system.py",
                                              {"old/tokens.css": STARTER, "old/theme.css": ":root { }\n",
                                               "new.css": STARTER},
                                              ["old", "new.css", "--out", "old/theme.css"]),
    "diff_system, a snapshot's other file": ("design-system-versioning", "diff_system.py",
                                             {"old/tokens.css": STARTER, "old/theme.css": ":root { }\n",
                                              "new.css": STARTER},
                                             ["old", "new.css", "--out", "old/tokens.css"]),
    "build_presentation, a screenshot": ("client-presentation-builder", "build_presentation.py",
                                         {"DECISION_LOG.md": DECISIONS, "shots/home.png": "png"},
                                         ["DECISION_LOG.md", "--screenshots", "shots", "-o", "shots/home.png"]),
    "figma_audit, the config's tokens": ("figma-variables-sync", "figma_audit.py",
                                         {".git/HEAD": "x\n", "export.json": json.dumps(
                                             {"collections": [{"name": "semantic", "modes": [{"name": "Light", "variables": [
                                                 {"name": "bg/surface", "type": "COLOR", "value": "#ffffff"}]}]}]}),
                                          "tokens.css": STARTER, ".design-suite.json": '{"schema": 1, "tokens": "tokens.css"}'},
                                         ["export.json", "--out", "tokens.css"]),
    # Codex on #136, round 2: every output, and every input read.
    "extract_system --contract": ("design-system-docs", "extract_system.py", {"tokens.css": STARTER},
                                  ["tokens.css", "--contract", "tokens.css"]),
    "extract_system, the prose": ("design-system-docs", "extract_system.py",
                                  {"tokens.css": STARTER, "docs/a.md": "# A\n"},
                                  ["tokens.css", "--prose", "docs", "--out", "docs/a.md"]),
    "generate_matrix, its templates": ("component-state-matrix", "generate_matrix.py",
                                       {"matrix.json": MATRIX.replace('"densities"', '"templates": "t.html", "densities"'),
                                        "chip.css": ".chip { color: red; }\n",
                                        "t.html": '<template id="chip"><button class="chip">Chip</button></template>\n'},
                                       ["matrix.json", "--out", "t.html"]),
    "lint_email, the config's tokens": ("email-template-system", "lint_email.py",
                                        {".git/HEAD": "x\n", "email.html": EMAIL, "t.json": "{}",
                                         ".design-suite.json": '{"schema": 1, "emailTokens": "t.json"}'},
                                        ["email.html", "--source", "-o", "t.json"]),
}
NODE_CASES = {
    "a11y_runtime": ("a11y-audit-runner", "a11y_runtime.mjs", {"page.html": EMAIL},
                     ["--file", "page.html", "--report", "page.html"]),
    "measure_vitals": ("perf-budget-gate", "measure_vitals.mjs", {"page.html": EMAIL},
                       ["page.html", "--report", "page.html"]),
    # Codex on #136: the budget the project's config names, read after parsing.
    "measure_vitals, the config's budget": ("perf-budget-gate", "measure_vitals.mjs",
                                            {".git/HEAD": "x\n", "page.html": EMAIL, "budget.json": "{}",
                                             ".design-suite.json": '{"schema": 1, "budgets": {"perf": "budget.json"}}'},
                                            ["page.html", "--report", "budget.json"]),
    "a11y_runtime, the config's budget": ("a11y-audit-runner", "a11y_runtime.mjs",
                                          {".git/HEAD": "x\n", "page.html": EMAIL, "budget.json": "{}",
                                           ".design-suite.json": '{"schema": 1, "budgets": {"a11y": "budget.json"}}'},
                                          ["--file", "page.html", "--report", "budget.json"]),
}


class EveryWriterRefusesItsInput(TempDirTest):

    def stage(self, files):
        written = {}
        for name, content in files.items():
            if hasattr(content, "read_bytes"):
                (self.tmp / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(content, self.tmp / name)
            else:
                self.write(name, content)
            written[name] = (self.tmp / name).read_bytes()
        return written

    def check(self, proc, written):
        self.assertEqual(proc.returncode, 2, output(proc))
        self.assertIn("writing there would replace it", output(proc))
        for name, before in written.items():
            self.assertEqual((self.tmp / name).read_bytes(), before, name)

    def test_a_python_writer_refuses(self):
        for case, (skill, script, files, args) in CASES.items():
            with self.subTest(case=case):
                self.reset()
                written = self.stage(files)
                proc = run_py(skill, script[:-3], *args, cwd=self.tmp)
                self.check(proc, written)

    @unittest.skipUnless(NODE, "node is not installed")
    def test_a_node_writer_refuses(self):
        for case, (skill, script, files, args) in NODE_CASES.items():
            with self.subTest(case=case):
                self.reset()
                written = self.stage(files)
                proc = run_node(skill, script, *args, cwd=self.tmp)
                self.check(proc, written)

    @unittest.skipUnless(NODE, "node is not installed")
    def test_a_file_url_is_its_file(self):
        # Codex on #136: `--url file:///…/page.html` named the page by URL, so
        # a report at the page's path passed the guard.
        for skill, script, flag in (("a11y-audit-runner", "a11y_runtime.mjs", ["--url"]),
                                    ("perf-budget-gate", "measure_vitals.mjs", [])):
            with self.subTest(script=script):
                self.reset()
                written = self.stage({"page.html": EMAIL})
                proc = run_node(skill, script, *flag, (self.tmp / "page.html").as_uri(),
                                "--report", "page.html", cwd=self.tmp)
                self.check(proc, written)

    def test_the_deck_never_lands_on_its_bundled_tokens(self):
        # Codex on #136, round 2: with no --tokens and no config, the deck reads
        # the skill's own assets/deck-tokens.css. A copy of the skill runs here,
        # so a failure cannot touch the plugin.
        skill = self.tmp / "skill"
        shutil.copytree(SKILLS / "client-presentation-builder", skill,
                        ignore=shutil.ignore_patterns("__pycache__"))
        self.write(".git/HEAD", "x\n")
        written = self.stage({"DECISION_LOG.md": DECISIONS})
        bundled = skill / "assets" / "deck-tokens.css"
        written[bundled.relative_to(self.tmp).as_posix()] = bundled.read_bytes()
        proc = subprocess.run([sys.executable, "-B", str(skill / "scripts" / "build_presentation.py"),
                               "DECISION_LOG.md", "-o", str(bundled)], cwd=self.tmp, capture_output=True,
                              env=env(), timeout=120)
        self.check(proc, written)

    def test_the_cluster_values_proposal_never_lands_on_the_projects_tokens(self):
        self.write("src/a.css", ".a { margin: 13px; }\n")
        proc = run_py("design-token-migration", "extract_literals", "src", "--format", "json",
                      "-o", "literals.json", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        written = self.stage({"styles/tokens.css": STARTER})
        proc = run_py("design-token-migration", "cluster_values", "literals.json", "--tokens",
                      "styles/tokens.css", "-o", "styles", cwd=self.tmp)
        self.check(proc, written)

    def reset(self):
        for child in self.tmp.iterdir():
            shutil.rmtree(child) if child.is_dir() else child.unlink()


class TheGuardIsShared(TempDirTest):
    """One helper decides. The two skills with no copy of the reader carry
    the master's function verbatim, and the Node helper agrees with it."""

    def master(self):
        text = (SHARED / "project_config.py").read_text(encoding="utf-8")
        return re.search(r"\ndef refuse_overwrite\(.*?\n    return None\n", text, re.S).group(0)

    def test_the_verbatim_copies_are_the_masters(self):
        for path in (SKILLS / "design-critique-gate" / "scripts" / "critique_report.py",
                     SKILLS / "component-state-matrix" / "scripts" / "generate_matrix.py"):
            with self.subTest(script=path.name):
                self.assertIn(self.master(), path.read_text(encoding="utf-8"))

    def test_every_writer_calls_it(self):
        for skill, script, _files, _args in [*CASES.values(), *NODE_CASES.values()]:
            with self.subTest(script=script):
                text = (SKILLS / skill / "scripts" / script).read_text(encoding="utf-8")
                self.assertRegex(text, r"\brefuse_?[oO]verwrite\(")

    def test_the_helper_compares_files_not_spellings(self):
        guard = load_script("design-token-migration", "project_config").refuse_overwrite
        a = self.write("dir/a.css", "x")
        self.assertIsNotNone(guard(self.tmp / "dir" / ".." / "dir" / "a.css", a))   # one file, spelled twice
        self.assertIsNotNone(guard(str(a).upper() if self.case_folds() else a, a))
        self.assertIsNone(guard(self.tmp / "dir" / "b.css", a))
        self.assertIsNone(guard("-", "-"))                                    # stdout is no file
        self.assertIsNone(guard(None, a))
        self.assertIsNotNone(guard(self.tmp / "new.css", self.tmp / "new.css"))   # neither exists yet

    @unittest.skipUnless(NODE, "node is not installed")
    def test_node_agrees(self):
        a = self.write("dir/a.css", "x")
        pairs = [(str(self.tmp / "dir" / ".." / "dir" / "a.css"), str(a)), (str(self.tmp / "dir" / "b.css"), str(a)),
                 ("-", "-"),
                 (str(self.tmp / "new.css"), str(self.tmp / "new.css"))]
        guard = load_script("design-token-migration", "project_config").refuse_overwrite
        script = self.write("probe.mjs", (
            "import { refuseOverwrite } from " + json.dumps((SHARED / "browser_common.mjs").as_uri()) + ";\n"
            "const pairs = JSON.parse(process.argv[2]);\n"
            "console.log(JSON.stringify(pairs.map(([o, i]) => refuseOverwrite(o, i) !== null)));\n"))
        proc = subprocess.run([NODE, str(script), json.dumps(pairs)], cwd=self.tmp, capture_output=True,
                              env=env(), timeout=60)
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertEqual(json.loads(proc.stdout), [guard(o, i) is not None for o, i in pairs])

    def case_folds(self):
        probe = self.write("Case.txt", "x")
        return (self.tmp / "case.txt").exists() and probe.exists()


if __name__ == "__main__":
    unittest.main()
