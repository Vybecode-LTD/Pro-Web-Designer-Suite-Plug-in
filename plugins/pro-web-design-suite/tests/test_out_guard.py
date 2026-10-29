"""An output never replaces an input (the owner's audit of 2026-10-14, class 5).

V7, E9 and G4: `--out` equal to the input replaced a Figma export with its
audit report, a published snapshot with its diff, an email's source with its
build, the findings with their critique, and an audited page with its JSON
report, each with exit 0. `--emit-css DIR` wrote DIR/tokens.css over the
project's own. One helper decides, project_config.py's refuse_overwrite() (in
Node, browser_common.mjs's refuseOverwrite()), and every writer calls it before
it writes anything: exit 2, the input untouched.

The 2026-10-28 audit's class 1: each script called it with a list written by
hand, which missed a fourth output (cluster_values' tokens.json, PY-B-1) and a
second flag (build_email's --text, PY-E-1; deprecate add's --mapping, PY-C-7),
and never held two outputs apart (extract_system's --out and --contract,
PY-C-18). Every Python script now calls guard_outputs() once with every path
it writes and every path it reads, and EveryWriteIsGuarded ties each write in
the shipped scripts to that call.
"""
from __future__ import annotations

import ast
import copy
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
    "brief_to_log --into": ("landing-page-conversion", "brief_to_log.py", {"MESSAGE_BRIEF.md": "# A brief\n"},
                            ["MESSAGE_BRIEF.md", "--into", "MESSAGE_BRIEF.md"]),
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


class Refusals(TempDirTest):
    """Stage the files, run the writer, see exit 2 and every file as it was."""

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
            with self.subTest(name=name, before=before):
                self.assertEqual((self.tmp / name).read_bytes(), before, name)

    def reset(self):
        for child in self.tmp.iterdir():
            shutil.rmtree(child) if child.is_dir() else child.unlink()


class EveryWriterRefusesItsInput(Refusals):

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


class EveryOutputIsGuarded(Refusals):
    """The 2026-10-28 audit's class 1: an output the hand-written list left
    out, and two outputs that are one file. Each run exits 2, before anything
    is written."""

    def refused(self, proc, written, *never):
        self.check(proc, written)
        for name in never:
            with self.subTest(never=name):
                self.assertFalse((self.tmp / name).exists(), f"{name} was written")

    def test_cluster_values_never_replaces_a_dtcg_tokens_json(self):
        # PY-B-1: the guard named tokens.css, mapping.json and
        # reconciliation.md, and the script writes tokens.json too.
        self.write(".git/HEAD", "x\n")
        self.write("src/a.css", ".a { margin: 13px; }\n")
        self.write("styles/tokens.css", STARTER.read_text(encoding="utf-8"))
        proc = run_py("design-token-migration", "extract_literals", "src", "--format", "json",
                      "-o", "literals.json", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        proc = run_py("design-token-migration", "cluster_values", "literals.json", "--tokens",
                      "styles/tokens.css", "-o", "first", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertIn('"$value"', (self.tmp / "first" / "tokens.json").read_text(encoding="utf-8"))
        written = self.stage({"tokens.json": self.tmp / "first" / "tokens.json"})
        proc = run_py("design-token-migration", "cluster_values", "literals.json", "--tokens",
                      "tokens.json", "-o", ".", cwd=self.tmp)
        self.refused(proc, written, "tokens.css", "mapping.json", "reconciliation.md")

    def test_build_email_text_never_replaces_the_source(self):
        # PY-E-1: --out was checked, --text was not.
        written = self.stage({".git/HEAD": "x\n", "email.html": EMAIL})
        proc = run_py("email-template-system", "build_email", "email.html", "--out", "out.html",
                      "--text", "email.html", "-q", cwd=self.tmp)
        self.refused(proc, written, "out.html")

    def test_build_email_out_and_text_are_two_files(self):
        written = self.stage({".git/HEAD": "x\n", "email.html": EMAIL})
        proc = run_py("email-template-system", "build_email", "email.html", "--out", "same.html",
                      "--text", "same.html", "-q", cwd=self.tmp)
        self.refused(proc, written, "same.html")

    def test_deprecate_add_mapping_never_replaces_a_source_or_the_ledger(self):
        # PY-C-7: `add --mapping` wrote with no check; `mapping -o` had one.
        for mapping in ("a.css", "ledger.json"):
            with self.subTest(mapping=mapping):
                self.reset()
                written = self.stage({".git/HEAD": "x\n", "ledger.json": json.dumps(
                                          {"schema": "design-system-versioning/deprecations@1", "deprecations": []}),
                                      "a.css": ":root { --old: 1px; --new: 2px; }\n"})
                proc = run_py("design-system-versioning", "deprecate", "--ledger", "ledger.json", "add",
                              "--name", "--old", "--kind", "token", "--since", "1.0.0", "--removal", "2.0.0",
                              "--replacement", "--new", "--source", "a.css", "--mapping", mapping,
                              "--date", "2026-10-29", cwd=self.tmp)
                self.check(proc, written)

    def test_extract_system_out_and_contract_are_two_files(self):
        # PY-C-18: each was checked against the inputs, not against the other.
        written = self.stage({".git/HEAD": "x\n", "tokens.css": STARTER})
        proc = run_py("design-system-docs", "extract_system", "tokens.css", "--out", "same.json",
                      "--contract", "same.json", cwd=self.tmp)
        self.refused(proc, written, "same.json")

    def test_the_writers_the_audit_did_not_name(self):
        # The same class where no guard stood (a baseline, the deck's
        # reports) or two outputs were checked one at a time.
        sheet = json.loads(MATRIX)                       # a sheet that builds, so both outputs are written
        sheet["components"][0]["template"] = '<button class="chip" {attrs}>{content}</button>'
        cases = {
            "a11y_static --write-baseline": ("a11y-audit-runner", "a11y_static", {"page.html": EMAIL},
                                             ["page.html", "--write-baseline", "page.html"], []),
            "perf_audit --write-baseline, a page": ("perf-budget-gate", "perf_audit",
                                                    {"dist/index.html": EMAIL, "budget.json": "{}"},
                                                    ["dist", "--budget", "budget.json",
                                                     "--write-baseline", "dist/index.html"], []),
            "perf_audit --write-baseline, the budget": ("perf-budget-gate", "perf_audit",
                                                        {"dist/index.html": EMAIL, "budget.json": "{}"},
                                                        ["dist", "--budget", "budget.json",
                                                         "--write-baseline", "budget.json"], []),
            "audit_design --write-baseline": ("web-design-studio", "audit_design",
                                              {"styles/a.css": ".a { color: var(--fg-default); }\n"},
                                              ["styles", "--write-baseline", "styles/a.css"], []),
            "introspect_schema -o and --answers-template": (
                "content-model-to-ui", "introspect_schema",
                {"schema.sql": "create table t (id int primary key, title text);\n"},
                ["schema.sql", "-o", "same.json", "--answers-template", "same.json"], ["same.json"]),
            "build_presentation -o and --notes": ("client-presentation-builder", "build_presentation",
                                                  {"DECISION_LOG.md": DECISIONS},
                                                  ["DECISION_LOG.md", "-o", "same.html", "--notes", "same.html"],
                                                  ["same.html"]),
            "generate_matrix --out and --emit-css": ("component-state-matrix", "generate_matrix",
                                                     {"matrix.json": json.dumps(sheet),
                                                      "chip.css": ".chip { color: red; }\n"},
                                                     ["matrix.json", "--out", "same.html", "--emit-css", "same.html"],
                                                     ["same.html"]),
        }
        for case, (skill, script, files, args, never) in cases.items():
            with self.subTest(case=case):
                self.reset()
                written = self.stage({".git/HEAD": "x\n", **files})
                self.refused(run_py(skill, script, *args, cwd=self.tmp), written, *never)

    def test_a_baseline_still_refreshes_in_place(self):
        # The control: the baseline a run reads is the one it may replace,
        # even inside a folder perf_audit measures.
        for skill, script, args in (
                ("perf-budget-gate", "perf_audit", [".", "--budget", "budget.json",
                                                    "--write-baseline", ".perf-baseline.json"]),
                ("web-design-studio", "audit_design", ["styles", "--write-baseline", ".design-baseline.json"]),
                ("a11y-audit-runner", "a11y_static", [".", "--write-baseline", ".a11y-baseline.json"])):
            with self.subTest(script=script):
                self.reset()
                self.stage({".git/HEAD": "x\n", "index.html": EMAIL, "budget.json": "{}",
                            "styles/a.css": ".a { color: var(--fg-default); }\n", ".perf-baseline.json": "{}",
                            ".design-baseline.json": "[]", ".a11y-baseline.json": "[]"})
                proc = run_py(skill, script, *args, cwd=self.tmp)
                self.assertEqual(proc.returncode, 0, output(proc))
                self.assertIn("baseline", output(proc))

    def test_the_deck_never_clears_away_its_findings(self):
        # deck.py deleted last run's audit.json from --out before it wrote a
        # new one, and the findings were that file.
        written = self.stage({".git/HEAD": "x\n", "DECISION_LOG.md": DECISIONS, "audit.json": "[]\n"})
        proc = subprocess.run([sys.executable, "-B", str(PLUGIN / "workflow-commands" / "deck" / "scripts" / "deck.py"),
                               "DECISION_LOG.md", "--findings", "audit.json", "--out", "."],
                              cwd=self.tmp, capture_output=True, env=env(), timeout=300)
        self.assertTrue((self.tmp / "audit.json").is_file(), "deck.py deleted the findings: " + output(proc))
        self.refused(proc, written, "deck.html")


# The shipped Python scripts, less the two libraries every skill copies.
WRITERS = sorted(p for p in (*SKILLS.glob("*/scripts/*.py"), *(PLUGIN / "workflow-commands").glob("*/scripts/*.py"))
                 if p.name not in ("project_config.py", "dtcg.py"))
COPIES = {("os", "replace"), ("os", "rename"), ("shutil", "copy"), ("shutil", "copy2"),
          ("shutil", "copyfile"), ("shutil", "move"), ("shutil", "copytree")}
# The writes the check cannot tie to a guard_outputs() call in their own
# function, by (script, function), with why each is safe. A write that is
# neither fails the check.
DECLARED = {
    ("skills/client-presentation-builder/scripts/build_presentation.py", "emit_css"):
        "--emit-css's two files, which main() guards as `emitted`",
    ("skills/figma-variables-sync/scripts/figma_to_tokens.py", "write_out"):
        "--out, or the file --out-dir receives, which main() guards",
    ("workflow-commands/deck/scripts/deck.py", "capture"):
        "a report in --out, which main() guards as REPORTS",
    ("skills/design-system-versioning/scripts/deprecate.py", "save_ledger"):
        "the ledger, which add, scan and remove update in place",
    ("skills/design-system-versioning/scripts/deprecate.py", "_write_as_read"):
        "the marker in a --source file, written in place in the file's own codec",
    ("skills/design-token-migration/scripts/apply_codemod.py", "write_atomically"):
        "--apply rewrites the sources it reads, in place, by design",
    ("workflow-commands/install-gate/scripts/install_gate.py", "main"):
        "the gate's own files: one it did not write, or that changed since it did, stops the run",
    ("skills/design-system-docs/scripts/build_docs.py", "build"): "no guard yet: PY-C-24, P82",
    ("skills/design-system-docs/scripts/build_docs.py", "copy_sources"): "no guard yet: PY-C-24, P82",
}


def _mode(call: ast.Call, position: int) -> str:
    for keyword in call.keywords:
        if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
            return str(keyword.value.value)
    if len(call.args) > position and isinstance(call.args[position], ast.Constant):
        return str(call.args[position].value)
    return "r"


def written_path(call: ast.Call):
    """The path a call writes, or None when it writes none."""
    f = call.func
    writes = set("wax+").intersection
    if isinstance(f, ast.Attribute) and f.attr in ("write_text", "write_bytes"):
        return f.value
    if isinstance(f, ast.Name) and f.id == "open":
        return call.args[0] if writes(_mode(call, 1)) else None
    if isinstance(f, ast.Attribute) and f.attr == "open":
        if isinstance(f.value, ast.Name) and f.value.id in ("io", "codecs"):
            return call.args[0] if writes(_mode(call, 1)) else None
        return f.value if writes(_mode(call, 0)) else None
    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and (f.value.id, f.attr) in COPIES:
        return call.args[1]
    return None


class Scope:
    """One function: a name assigned once in it stands for its value, and
    Path(x) for x, so `out_path = Path(args.out)` and `args.out` read alike."""

    def __init__(self, node):
        self.node = node
        self.values: dict = {}
        for sub in ast.walk(node):
            if isinstance(sub, ast.Assign) and len(sub.targets) == 1 and isinstance(sub.targets[0], ast.Name):
                self.values.setdefault(sub.targets[0].id, []).append(sub.value)
                continue
            if isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Name) and sub.value is not None:
                self.values.setdefault(sub.target.id, []).append(sub.value)
                continue
            targets = (sub.targets if isinstance(sub, ast.Assign) else
                       [sub.target] if isinstance(sub, (ast.For, ast.comprehension, ast.AugAssign, ast.NamedExpr))
                       else [item.optional_vars for item in sub.items if item.optional_vars]
                       if isinstance(sub, ast.With) else [])
            for target in targets:
                for name in ast.walk(target):
                    if isinstance(name, ast.Name):
                        self.values.setdefault(name.id, []).append(None)    # never stands for one value

    def value(self, name: str, seen: tuple):
        values = self.values.get(name, [])
        return values[0] if len(values) == 1 and values[0] is not None and name not in seen else None

    def norm(self, node, seen: tuple = ()) -> str:
        scope = self

        class Substitute(ast.NodeTransformer):
            def visit_Name(self, name):
                value = scope.value(name.id, seen)
                return ast.parse(scope.norm(value, (*seen, name.id)), mode="eval").body if value else name

            def visit_Call(self, call):
                self.generic_visit(call)
                if isinstance(call.func, ast.Name) and call.func.id == "Path" and len(call.args) == 1 \
                        and not call.keywords:
                    return call.args[0]
                return call

        return ast.unparse(Substitute().visit(copy.deepcopy(node)))

    def elements(self, node, seen: tuple = ()):
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            return [each for elt in node.elts
                    for each in (self.elements(elt.value, seen) if isinstance(elt, ast.Starred) else [elt])]
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            return [node.elt]
        if isinstance(node, ast.IfExp):
            return self.elements(node.body, seen) + self.elements(node.orelse, seen)
        if isinstance(node, ast.Name) and self.value(node.id, seen) is not None:
            return self.elements(self.value(node.id, seen), (*seen, node.id))
        return [node]

    def guarded(self) -> set:
        """Every output a guard_outputs() call in the function names."""
        return {self.norm(elt) for sub in ast.walk(self.node)
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                and sub.func.id == "guard_outputs" and sub.args
                for elt in self.elements(sub.args[0])}


class EveryWriteIsGuarded(unittest.TestCase):
    """Each write a shipped Python script makes names a path its own
    function's guard_outputs() call names, or is declared with its reason."""

    def sites(self):
        for path in WRITERS:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            owner = {}
            for function in sorted(functions, key=lambda n: n.lineno):   # the innermost wins
                for sub in ast.walk(function):
                    owner[sub] = function
            for call in ast.walk(tree):
                if isinstance(call, ast.Call) and written_path(call) is not None:
                    yield path.relative_to(PLUGIN).as_posix(), owner.get(call), call

    def test_every_write_is_in_its_functions_guard(self):
        unguarded, declared, count = [], set(), 0
        for rel, function, call in self.sites():
            count += 1
            key = (rel, function.name if function else "<module>")
            if key in DECLARED:
                declared.add(key)
                continue
            scope = Scope(function) if function else None
            target = written_path(call)
            if scope is None or scope.norm(target) not in scope.guarded():
                unguarded.append(f"{rel}:{call.lineno} {key[1]}() writes {ast.unparse(target)}, which "
                                 f"no guard_outputs() call in it names")
        self.assertGreater(count, 30, "the check found too few writes to prove anything")
        self.assertEqual(unguarded, [])
        self.assertEqual(sorted(set(DECLARED) - declared), [], "declared writes that are gone")

    def test_the_check_sees_a_write_the_guard_leaves_out(self):
        # The positive control: PY-B-1's shape, and PY-E-1's.
        def unguarded(source):
            function = ast.parse(source).body[0]
            scope = Scope(function)
            return [ast.unparse(written_path(c)) for c in ast.walk(function)
                    if isinstance(c, ast.Call) and written_path(c) is not None
                    and scope.norm(written_path(c)) not in scope.guarded()]
        self.assertEqual(unguarded(
            "def main(args):\n"
            "    for dest in ('tokens.css', 'mapping.json'):\n"
            "        clash = guard_outputs([Path(args.output) / dest], [args.literals])\n"
            "    out = Path(args.output)\n"
            "    (out / 'tokens.css').write_text('')\n"
            "    (out / 'tokens.json').write_text('')\n"), ["out / 'tokens.css'", "out / 'tokens.json'"])
        self.assertEqual(unguarded(
            "def main(args):\n"
            "    clash = guard_outputs([args.out], [args.source])\n"
            "    out_path = Path(args.out)\n"
            "    out_path.write_text('')\n"
            "    text_path = Path(args.text)\n"
            "    with open(text_path, 'w') as fh:\n"
            "        fh.write('')\n"), ["text_path"])
        self.assertEqual(unguarded(
            "def main(args):\n"
            "    clash = guard_outputs([args.out, args.text], [args.source])\n"
            "    Path(args.out).write_text('')\n"
            "    Path(args.text).write_bytes(b'')\n"), [])


class TheGuardIsShared(TempDirTest):
    """One helper decides. The two skills with no copy of the reader carry
    the master's function verbatim, and the Node helper agrees with it."""

    def master(self):
        text = (SHARED / "project_config.py").read_text(encoding="utf-8")
        found = re.search(r"\ndef refuse_overwrite\(.*?\n    return None\n\n\ndef guard_outputs\(.*?\n    return None\n",
                          text, re.S)
        self.assertIsNotNone(found, "the master holds refuse_overwrite() and then guard_outputs()")
        return found.group(0)

    def test_the_verbatim_copies_are_the_masters(self):
        for path in (SKILLS / "design-critique-gate" / "scripts" / "critique_report.py",
                     SKILLS / "landing-page-conversion" / "scripts" / "brief_to_log.py",
                     SKILLS / "component-state-matrix" / "scripts" / "generate_matrix.py"):
            with self.subTest(script=path.name):
                self.assertIn(self.master(), path.read_text(encoding="utf-8"))

    def test_every_writer_calls_it(self):
        for skill, script, _files, _args in [*CASES.values(), *NODE_CASES.values()]:
            with self.subTest(script=script):
                text = (SKILLS / skill / "scripts" / script).read_text(encoding="utf-8")
                self.assertRegex(text, r"\bguard_outputs\(" if script.endswith(".py") else r"\brefuseOverwrite\(")

    def test_the_helper_compares_files_not_spellings(self):
        guard = load_script("design-token-migration", "project_config").refuse_overwrite
        a = self.write("dir/a.css", "x")
        self.assertIsNotNone(guard(self.tmp / "dir" / ".." / "dir" / "a.css", a))   # one file, spelled twice
        self.assertIsNotNone(guard(str(a).upper() if self.case_folds() else a, a))
        self.assertIsNone(guard(self.tmp / "dir" / "b.css", a))
        self.assertIsNone(guard("-", "-"))                                    # stdout is no file
        self.assertIsNone(guard(None, a))
        self.assertIsNotNone(guard(self.tmp / "new.css", self.tmp / "new.css"))   # neither exists yet

    def test_guard_outputs_holds_each_output_apart(self):
        guard = getattr(load_script("design-token-migration", "project_config"), "guard_outputs", None)
        self.assertIsNotNone(guard, "project_config.py has no guard_outputs()")
        a, b = self.write("a.css", "x"), self.write("b.css", "y")
        self.assertIsNone(guard([self.tmp / "out.json", self.tmp / "out.md"], [a, b]))
        self.assertIn("is the input", guard([self.tmp / "out.json", b], [a, b]))
        self.assertIn("is also the output", guard([self.tmp / "out.json", self.tmp / "x" / ".." / "out.json"], [a]))
        self.assertIsNone(guard(["-", "-", None, ""], [a]))                  # stdout twice is no file
        self.assertIsNotNone(guard(iter([a]), (p for p in [a])))               # any iterable, read once
        self.assertIsNone(guard([], [a]))

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
