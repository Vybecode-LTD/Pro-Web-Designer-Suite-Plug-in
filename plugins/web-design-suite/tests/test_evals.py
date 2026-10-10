"""The eval suite (P29: XC-C1, XC-B2).

evals/ holds `claude plugin eval` cases, one directory per case: a prompt.md
and graders/*.md, the layout `claude plugin eval init` writes
(claude-code-capabilities.md §1). evals/routing/ has a case for each skill;
evals/boundaries/ has, for each pair of sibling skills, a prompt for one that
must not load the other, in both directions.

These tests cost nothing. They hold each case to the fields the evals page
documents, check that every skill has its routing case and every pair its
boundary cases, run each grader's pattern as the JavaScript regex the grader
runs, and run the plugin's own router on every prompt, since the router hook
runs inside each eval session too. The cases themselves run only through
`claude plugin eval`, where every run is a real model call.
"""
from __future__ import annotations

import json
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

from wds_support import NODE, PLUGIN, REPO, SKILLS, TempDirTest, env, output, tool_modules

EVALS = PLUGIN / "evals"
ROUTER = PLUGIN / "hooks" / "design_hooks.mjs"
YAML_MODULES = tool_modules("WDS_NODE_MODULES", "js-yaml")
needs_yaml = unittest.skipUnless(NODE and YAML_MODULES, "node and js-yaml (tooling/main) are not installed")
LOAD_ALL = ("const yaml = require(require('path').join(process.argv[1], 'js-yaml'));"
            "const texts = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
            "process.stdout.write(JSON.stringify(texts.map((t) => yaml.load(t))));")
TEST_ALL = ("const { patterns, inputs } = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
            "process.stdout.write(JSON.stringify(patterns.map((p) => inputs.map((i) => new RegExp(p).test(i)))));")

# The evals page: prompt.md's fields ("An unknown key is an error"), the
# read-only tools a case may list, and each grader type's options.
PROMPT_FIELDS = {"schema_version", "name", "description", "tags", "plugins", "runs", "expected_outcome", "model",
                 "max_turns", "timeout_seconds", "allowed_tools", "append_system_prompt", "env"}
READ_ONLY = {"Read", "Glob", "Grep", "NotebookRead", "Skill", "AskUserQuestion", "Agent", "TodoWrite",
             "TaskCreate", "TaskGet", "TaskList", "TaskUpdate", "TaskStop"}
GRADER_OPTIONS = {"regex": {"pattern", "flags", "match", "target"},
                  "tool_used": {"tool", "input_match", "min", "max"},
                  "tool_order": {"before", "after"},
                  "file_exists": {"path", "exists"},
                  "llm": {"criteria", "focus"},
                  "baseline": {"baseline_file", "criteria"}}
# XC-B2: the sibling skills a prompt for one could wrongly load the other for.
PAIRS = [("a11y-audit-runner", "design-critique-gate"),
         ("design-system-docs", "design-system-versioning"),
         ("design-token-migration", "figma-variables-sync"),
         ("web-design-studio", "landing-page-conversion"),
         ("component-state-matrix", "a11y-audit-runner")]
SKILL_NAMES = sorted(p.parent.name for p in SKILLS.glob("*/SKILL.md"))
COMMAND_NAMES = sorted(p.parent.name for p in (PLUGIN / "workflow-commands").glob("*/SKILL.md"))
# The grader the evals page gives for "the skill fired", by its bare or its
# plugin:skill name.
FIRES = '"skill"\\s*:\\s*"(?:[\\w-]+:)?{}"'


def node(script: str, data, *args):
    proc = subprocess.run([NODE, "-e", script, *args], input=json.dumps(data).encode("utf-8"), env=env(),
                          capture_output=True, timeout=120)
    assert proc.returncode == 0, output(proc)
    return json.loads(proc.stdout)


def split_front(path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), path
    head, body = text[4:].split("\n---\n", 1)
    return head, body.strip()


class Suite:
    """Every case, parsed once: {relative dir: (fields, body, {grader: fields})}."""
    _cases = None

    @classmethod
    def cases(cls) -> dict:
        if cls._cases is None:
            files = sorted(EVALS.rglob("prompt.md"))
            graders = {f: sorted((f.parent / "graders").glob("*.md")) for f in files}
            heads = [split_front(f)[0] for f in files] + [split_front(g)[0] for f in files for g in graders[f]]
            parsed = iter(node(LOAD_ALL, heads, YAML_MODULES))
            fields = {f: next(parsed) for f in files}
            cls._cases = {f.parent.relative_to(EVALS).as_posix(): (
                fields[f], split_front(f)[1], {g.stem: next(parsed) for g in graders[f]}) for f in files}
        return cls._cases


def skill_graders(graders: dict) -> dict:
    """{skill name: grader fields} for each tool_used grader on the Skill tool;
    a pattern not of the FIRES form is keyed by itself."""
    prefix, named = FIRES.format("")[:-1], {}
    for grader in graders.values():
        if grader.get("type") == "tool_used" and grader.get("tool") == "Skill":
            pattern = grader["input_match"]
            fires = pattern.startswith(prefix) and pattern.endswith('"')
            named[pattern[len(prefix):-1] if fires else pattern] = grader
    return named


@needs_yaml
class TheCaseFiles(unittest.TestCase):
    """Each case holds only what the evals page documents, so none fails to
    load; its prompt reads as a user would type it."""

    def test_the_suite_has_cases(self):
        tags = [fields["tags"][0] for fields, _, _ in Suite.cases().values()]
        self.assertEqual(23, tags.count("routing"))        # 13 routing cases, 10 boundary cases
        self.assertEqual(11, tags.count("outcome"))        # P30: six areas
        self.assertEqual(len(tags), tags.count("routing") + tags.count("outcome"))

    def test_each_prompt_has_the_documented_fields(self):
        for case, (fields, body, graders) in Suite.cases().items():
            with self.subTest(case=case):
                self.assertLessEqual(set(fields), PROMPT_FIELDS)
                self.assertTrue(1 <= fields.get("max_turns", 10) <= 200)
                self.assertTrue(1 <= fields.get("timeout_seconds", 300) <= 3600)
                self.assertLessEqual(set(fields["allowed_tools"]), READ_ONLY)
                if fields["tags"][0] == "routing":
                    # The listing decides the route before any other tool, and Skill
                    # alone ran at $0.09 a run against $0.21 with Read, Glob and Grep.
                    self.assertEqual(["Skill"], fields["allowed_tools"])
                else:                                      # Write, Edit and the gates come from --allow-tools
                    self.assertEqual(["Read", "Glob", "Grep", "Skill"], fields["allowed_tools"])
                self.assertTrue(body)
                self.assertNotIn("web-design-suite", body)
                for name in SKILL_NAMES:                   # phrased as a user would, never naming the skill
                    self.assertNotIn(name, body)
                self.assertTrue(graders)                   # a case with no grader fails to load

    def test_each_grader_has_its_type_options(self):
        for case, (_, _, graders) in Suite.cases().items():
            for name, grader in graders.items():
                with self.subTest(case=case, grader=name):
                    self.assertIn(grader["type"], GRADER_OPTIONS)
                    self.assertLessEqual(set(grader) - {"type", "weight", "arm"}, GRADER_OPTIONS[grader["type"]])
                    self.assertIn(grader.get("arm", "both"), {"with-only", "both"})

    def test_the_case_names_are_unique(self):
        names = [case.rsplit("/", 1)[-1] for case in Suite.cases()]
        self.assertEqual(len(names), len(set(names)))      # --case and the report key on the name

    @unittest.skipUnless(REPO, "not in the repository")
    def test_the_results_stay_out_of_git(self):
        self.assertIn("plugins/web-design-suite/evals/results/",
                      (REPO / ".gitignore").read_text(encoding="utf-8").splitlines())


@needs_yaml
class TheRoutingCases(unittest.TestCase):
    """XC-C1: every skill has a case that should load it. XC-B2: every pair of
    siblings has a case each way that loads one and never the other."""

    def test_the_routing_cases_carry_their_tag(self):
        for case, (fields, _, _) in Suite.cases().items():
            if case.startswith(("routing/", "boundaries/")):
                with self.subTest(case=case):
                    self.assertEqual("routing", fields["tags"][0])

    def test_every_skill_has_a_routing_case(self):
        routed = {}
        for case, (_, _, graders) in Suite.cases().items():
            if case.startswith("routing/"):
                routed[case[len("routing/"):]] = skill_graders(graders)
        self.assertEqual(SKILL_NAMES, sorted(routed))
        for skill, named in routed.items():
            with self.subTest(skill=skill):
                self.assertEqual([skill], list(named))
                self.assertNotIn("max", named[skill])      # at least once, the default min of 1
                self.assertEqual("both", named[skill]["arm"])   # scored in --ablation none and two-arm alike

    def test_every_pair_has_a_boundary_case_each_way(self):
        expected = {f"boundaries/{a}-not-{b}": (a, b) for pair in PAIRS for a, b in (pair, pair[::-1])}
        cases = Suite.cases()
        self.assertEqual(sorted(expected), sorted(c for c in cases if c.startswith("boundaries/")))
        for case, (skill, sibling) in expected.items():
            with self.subTest(case=case):
                fields, _, graders = cases[case]
                self.assertIn("boundary", fields["tags"])
                named = skill_graders(graders)
                self.assertEqual({skill, sibling}, set(named))
                self.assertNotIn("max", named[skill])
                # "To assert a tool was never called, set both min: 0 and max: 0";
                # arm: both keeps it in the score of a two-arm run.
                self.assertEqual((0, 0, "both"), (named[sibling].get("min"), named[sibling].get("max"),
                                                  named[sibling].get("arm")))

    def test_each_pattern_matches_its_skill_alone(self):
        """The patterns are JavaScript regexes over the Skill tool's
        JSON-encoded input, so node runs them, on the bare and the plugin:skill
        name, against every skill and workflow command."""
        names = SKILL_NAMES + COMMAND_NAMES
        inputs = [json.dumps({"skill": f"{prefix}{name}", "args": "x"}, separators=sep)
                  for name in names for prefix in ("", "web-design-suite:") for sep in ((",", ":"), (", ", ": "))]
        graders = [g for _, _, gs in Suite.cases().values() for g in skill_graders(gs).values()]
        self.assertTrue(graders)
        verdicts = node(TEST_ALL, {"patterns": [g["input_match"] for g in graders], "inputs": inputs})
        for grader, hits in zip(graders, verdicts):
            with self.subTest(pattern=grader["input_match"]):
                matched = {names[i // 4] for i, hit in enumerate(hits) if hit}
                self.assertEqual(1, len(matched), matched)
                self.assertEqual(4, sum(hits))             # both names, both spacings
                self.assertEqual(FIRES.format(matched.pop()), grader["input_match"])


@unittest.skipUnless(NODE and YAML_MODULES, "node and js-yaml (tooling/main) are not installed")
class TheRouterAgrees(TempDirTest):
    """The router hook runs in every eval session. It must never name the
    sibling a boundary case forbids, and when it names anything for a case's
    prompt, it names the skill the case expects."""

    def routed(self, prompt):
        event = {"hook_event_name": "UserPromptSubmit", "prompt": prompt, "cwd": str(self.tmp)}
        proc = subprocess.run([NODE, str(ROUTER), "route"], input=json.dumps(event).encode(), cwd=self.tmp,
                              env=env(), capture_output=True, timeout=60)
        self.assertEqual(0, proc.returncode, output(proc))
        return re.findall(r"/web-design-suite:([\w-]+)", proc.stdout.decode("utf-8"))

    def test_the_router_points_each_prompt_at_its_skill(self):
        self.assertTrue(Suite.cases())                     # no vacuous pass
        for case, (_, body, graders) in Suite.cases().items():
            with self.subTest(case=case):
                named = skill_graders(graders)
                expected = [s for s, g in named.items() if "max" not in g]
                forbidden = [s for s, g in named.items() if g.get("max") == 0]
                heard = self.routed(body)
                for skill in forbidden:
                    self.assertNotIn(skill, heard)
                if heard:
                    self.assertIn(expected[0], heard)


BASH = shutil.which("bash")
BASH = None if BASH and "system32" in BASH.lower() else BASH   # WSL's launcher is not a bash

# P30: the outcome cases, a folder per area, each tagged [outcome, <area>].
AREAS = ("build", "systems", "gates", "lifecycle", "persuasion", "delivery")
TEST_FLAGGED = ("const checks = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
                "process.stdout.write(JSON.stringify(checks.map(([p, f, inputs]) =>"
                " inputs.map((i) => new RegExp(p, f).test(i)))));")


def mcp_result(tool, code, verdict):
    """A gate's reply as the trace holds it: the MCP server's JSON, as the text
    of a tool result, inside the trace's own JSON (seen in the first run, §11)."""
    reply = json.dumps({"tool": tool, "exit": code, "verdict": verdict, "report": []}, separators=(",", ":"))
    return json.dumps({"type": "tool_result", "content": [{"type": "text", "text": reply}]}, separators=(",", ":"))


def tool_input(path, **more):
    return json.dumps({"file_path": path, **more})


# What each grader's pattern must match and must not, by grader name. A
# not_contains grader fails on a match, so its first list is the faults.
SAMPLES = {
    "no-raw-colour": (["color: #333;", "border-color: #A0b1C2ff;", "background: rgb(0 0 0 / .5);",
                       "fill: oklch(60% 0.1 250);", "color: HSL(10 50% 50%)"],
                      ["color: var(--fg-default);", "background: color-mix(in oklch, var(--bg-accent), transparent);",
                       "grid-template-columns: repeat(3, 1fr);"]),
    "no-raw-spacing": (["  padding: 24px;", ".x{margin-top:1.5rem}", "gap: 0 1em;", "row-gap: 2px;"],
                       ["padding: var(--pad-card);", "margin: 0 auto;", "@media (min-width: 48rem) {",
                        "max-width: 60ch;", "border-radius: 8px;", "scroll-padding: 4px;"]),
    "no-tier1": (["gap: var(--space-4);", "color: var( --neutral-700 );", "background: var(--blue-600);"],
                 ["gap: var(--gap-related);", "padding: var(--pad-card);", "color: var(--fg-default);"]),
    "layered": (["@layer components {\n  .card {}", "@layer components.pricing{"],
                ["@layer reset, base;", ".card { color: var(--fg-default); }"]),
    "audit-clean": ([mcp_result("audit_design", 0, "pass")],
                    [mcp_result("audit_design", 1, "fail"), "a verdict: pass (0), fail (1)"]),
    "contrast-pass": ([mcp_result("check_roles", 0, "pass")],
                      [mcp_result("check_roles", 1, "fail"), mcp_result("audit_design", 0, "pass")]),
    "one-link": (['<a href="/posts/1">'], ["<article>", "<abbr>"]),
    "link-in-heading": (['<h2 class="card__title"><a href="/p">', '<h3>\n  <a href="#">'],
                        ['<a href="/p"><h2>', "<h2>Title</h2>\n<a href=\"/p\">"]),
    "stretched": ([".card__link::after { content: \"\"; position: absolute; inset: 0; }",
                   ".x:after{position:absolute;top:0;left:0;right:0;bottom:0}"],
                  [".card__link::after { content: \"\"; }\n.card { inset: 0; }"]),
    "vendor-layer": (['@import url("../vendor/datepicker.css") layer(vendor);',
                      "@import '../vendor/datepicker.css' layer(vendor);",
                      "@import url(../vendor/datepicker.css) layer( vendor );"],
                     ['@import url("../vendor/datepicker.css");',
                      '@import url("../vendor/datepicker.css") layer(components);']),
    "order-first": (["@layer reset, vendor, tokens, base, layout, components, utilities, overrides;\n\n"
                     '@import url("tokens.css");\n@import url("../vendor/datepicker.css") layer(vendor);'],
                    ['@import url("../vendor/datepicker.css") layer(vendor);\n'
                     "@layer reset, vendor, tokens, base, layout, components, utilities, overrides;",
                     "@layer reset, tokens, base, layout, components, utilities, overrides, vendor;\n"
                     '@import url("../vendor/datepicker.css") layer(vendor);']),
    "vendor-not-edited": ([tool_input(str(pathlib.PureWindowsPath("/ws/vendor/datepicker.css")), old_string=".dp {"),
                           tool_input("/ws/vendor/datepicker.css", old_string=".dp {")],
                          [tool_input(str(pathlib.PureWindowsPath("/ws/styles/index.css")),
                                      new_string='@import url("../vendor/datepicker.css") layer(vendor);')]),
    "focus-visible": (['className="focus-visible:focus-ring"'], ['className="focus:ring"']),
    "keeps-outline": (["focus:outline-none", "outline-none focus-visible:ring"], ["outline-hidden"]),
    "announces-busy": (["aria-busy={loading}"], ["aria-disabled={disabled}"]),
    "no-arbitrary": (["bg-[#2563eb]", "p-[13px]", "hover:bg-[var(--x)]"],
                     ["bg-accent px-inline-sm", "aria-[busy=true]:cursor-wait", "data-[state=open]:block",
                      "const first = items[0];"]),
    "no-space-xy": (["space-x-2", "md:space-y-4"], ["gap-related", "aria-busy"]),
    "no-literal-values": (["duration-150", "focus-visible:ring-2", "border-2", "z-50", "outline-offset-2"],
                          ["motion-hover", "focus-visible:focus-ring", "border-stroke", "rounded-control",
                           "text-ui"]),
    "brand-kept": (["--orange-600: #E8440A;", "--orange-600: oklch(62.06% 0.2084 36.04);",
                    "--brand: oklch(0.6206 0.2084 36.04);"],
                   ["--orange-600: #e8440b;", "--orange-600: oklch(62% 0.15 36);"]),
    "dark-theme": (['[data-theme="dark"] {', "@media (prefers-color-scheme: dark) {", "[data-theme=dark]"],
                   ["[data-theme=\"light\"] {", "@media (prefers-reduced-motion: reduce)"]),
    "roles-alias": (["--bg-surface: var(--neutral-0);", "--fg-default:var(--orange-900)"],
                    ["--bg-surface: #fff;", "--orange-500: oklch(70% 0.18 36);"]),
    "typed": (['"$type": "color"'], ['"$type": "dimension"']),
    "colour-objects": (['"$value": {"colorSpace": "oklch", "components": [0.62, 0.21, 36]}'],
                       ['"$value": "oklch(62% 0.21 36)"']),
    "aliases": (['"$value": "{color.blue.600}"'], ['"$value": "#2563eb"']),
    "no-python-repr": (["{'colorSpace': 'oklch'}"], ['{"colorSpace": "oklch"}']),
    "outlook": (["<!--[if mso]>", "<!--[if gte mso 9]>"], ["<!-- note -->", "<!--[if !mso]><!-->"]),
    "dark-mode": (["@media (prefers-color-scheme: dark) {", '<meta name="color-scheme" content="light dark">'],
                  ["@media (max-width: 600px) {"]),
    "presentation-tables": (['<table role="presentation" width="100%">'], ["<table width=\"100%\">"]),
}
SAMPLES["vendor-not-rewritten"] = SAMPLES["vendor-not-edited"]


def outcome_cases() -> dict:
    return {case: entry for case, entry in Suite.cases().items() if entry[0]["tags"][0] == "outcome"}


def graded_files(grader) -> list:
    """The workspace files a grader reads through {source: file, path: …}."""
    return [where["path"] for where in (grader.get("target"), grader.get("focus"))
            if isinstance(where, dict) and where.get("source") == "file"]


@needs_yaml
class TheOutcomeCases(unittest.TestCase):
    """P30 (SS-C7, SB-C6, GT-C10, LC-C10, PS-C7, DL-C7): each case grades its
    result in both arms, so Δ measures the plugin, and its steps in the
    with-plugin arm alone; every pattern is run on what it must and must not
    match; every scaffold runs."""

    def test_every_area_has_cases_tagged_with_it(self):
        cases = outcome_cases()
        self.assertEqual(set(AREAS), {case.split("/")[0] for case in cases})
        for case, (fields, _, _) in cases.items():
            with self.subTest(case=case):
                self.assertEqual(["outcome", case.split("/")[0]], fields["tags"])
                self.assertEqual(2, case.count("/") + 1)

    def test_each_case_grades_the_result_and_the_steps(self):
        for case, (_, _, graders) in outcome_cases().items():
            with self.subTest(case=case):
                result = [n for n, g in graders.items() if g.get("arm") == "both"]
                steps = [n for n, g in graders.items() if g.get("arm") == "with-only"]
                self.assertTrue(result)                    # scored in both arms: Δ measures the plugin
                self.assertEqual(set(graders), set(result) | set(steps))   # every grader says which
                # The skill a case is about fired, in the with-plugin arm alone:
                # it can never pass without the plugin.
                fired = skill_graders(graders)
                self.assertEqual(1, len(fired))
                self.assertIn(list(fired)[0], SKILL_NAMES)
                self.assertEqual("with-only", list(fired.values())[0]["arm"])

    def test_each_file_a_grader_reads_is_one_the_prompt_names(self):
        for case, (_, body, graders) in outcome_cases().items():
            for name, grader in graders.items():
                for path in graded_files(grader):
                    with self.subTest(case=case, grader=name):
                        self.assertIn(f"`{path}`", body)

    def test_each_judge_has_a_pass_and_a_fail(self):
        judges = [(case, name) for case, (_, _, graders) in outcome_cases().items()
                  for name, grader in graders.items() if grader["type"] == "llm"]
        self.assertTrue(judges)
        for case, name in judges:
            with self.subTest(case=case, grader=name):
                rubric = split_front(EVALS / case / "graders" / f"{name}.md")[1]
                self.assertRegex(rubric, r"(?m)^PASS if ")
                self.assertRegex(rubric, r"(?m)^FAIL if ")

    def test_each_pattern_matches_its_samples(self):
        """The graders are JavaScript regexes, so node runs them, with their
        flags, on what each must match and must not."""
        checks, names = [], []
        for case, (_, _, graders) in outcome_cases().items():
            for name, grader in graders.items():
                pattern = grader.get("pattern", grader.get("input_match"))
                if pattern is None or (grader["type"] == "tool_used" and grader["tool"] == "Skill"):
                    continue
                self.assertIn(name, SAMPLES, f"{case}: {name} has no samples")
                hits, misses = SAMPLES[name]
                checks.append([pattern, grader.get("flags", ""), hits + misses])
                names.append((case, name, len(hits)))
        self.assertTrue(checks)
        for (case, name, hits), verdicts in zip(names, node(TEST_FLAGGED, checks)):
            with self.subTest(case=case, grader=name):
                self.assertEqual([True] * hits + [False] * (len(verdicts) - hits), verdicts)

    def test_the_case_yaml_names_only_the_scaffold(self):
        for case in outcome_cases():
            folder = EVALS / case
            with self.subTest(case=case):
                has_files = (folder / "files").is_dir()
                self.assertEqual(has_files, (folder / "case.yaml").is_file())
                if not has_files:
                    continue
                [fields] = node(LOAD_ALL, [(folder / "case.yaml").read_text(encoding="utf-8")], YAML_MODULES)
                self.assertEqual({"schema_version": "1.1", "name": folder.name,
                                  "context": {"scaffold_script": "scaffold.sh"}}, fields)

    @unittest.skipUnless(BASH, "needs bash")
    def test_each_scaffold_copies_its_project(self):
        """A scaffold runs only with --scaffold, in the empty workspace, as the
        user; each here copies its case's files/ there, as the first run showed
        it does on Windows (§11)."""
        scaffolds = sorted(EVALS.glob("*/*/scaffold.sh"))
        self.assertTrue(scaffolds)
        for script in scaffolds:
            with self.subTest(case=script.parent.relative_to(EVALS).as_posix()):
                syntax = subprocess.run([BASH, "-n", script.as_posix()], env=env(), capture_output=True, timeout=60)
                self.assertEqual(0, syntax.returncode, output(syntax))
                with tempfile.TemporaryDirectory() as workspace:
                    proc = subprocess.run([BASH, script.as_posix()], cwd=workspace, env=env(),
                                          capture_output=True, timeout=120)
                    self.assertEqual(0, proc.returncode, output(proc))
                    fixture = script.parent / "files"
                    expected = sorted(p.relative_to(fixture).as_posix() for p in fixture.rglob("*") if p.is_file())
                    copied = sorted(p.relative_to(workspace).as_posix()
                                    for p in pathlib.Path(workspace).rglob("*") if p.is_file())
                    self.assertTrue(expected)
                    self.assertEqual(expected, copied)
                    for name in expected:
                        self.assertEqual((fixture / name).read_bytes(), (pathlib.Path(workspace) / name).read_bytes())

    def test_each_project_starts_clean(self):
        """A failing gate in a run is the run's own: every fixture's stylesheets
        pass the audit, under the fixture's own .design-suite.json."""
        projects = sorted(p.parent for p in EVALS.glob("*/*/files/.design-suite.json"))
        self.assertTrue(projects)
        audit = SKILLS / "web-design-studio" / "scripts" / "audit_design.py"
        for project in projects:
            styles = [p for p in ("styles", "src") if (project / p).is_dir()]
            if not styles:
                continue
            with self.subTest(case=project.parent.relative_to(EVALS).as_posix()):
                proc = subprocess.run([sys.executable, "-B", str(audit), "--strict", *styles], cwd=project,
                                      env=env(), capture_output=True, timeout=120)
                self.assertEqual(0, proc.returncode, output(proc))

    def test_the_gate_graders_name_the_plugins_server(self):
        """The verdict graders read the MCP server's replies, and the CI job
        grants its tools by the server's name."""
        servers = json.loads((PLUGIN / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]
        self.assertIn("gates", servers)
WORKFLOW = REPO / ".github" / "workflows" / "evals.yml" if REPO else None
# Stand-ins the step's script calls by name: shell functions, so no PATH entry
# (a drive letter's colon splits PATH in Git Bash). The stand-in claude records
# each call's arguments in claude-args-<n> and writes a result whose cost is
# STAND_IN_COST to its --json path, unless STAND_IN_COST is "none".
STAND_INS = ('claude() {{\n'
             '  [ "$1" = --version ] && return\n'
             '  calls=$((calls + 1)); printf "%s\\n" "$@" > "$RUNNER_TEMP/claude-args-$calls"\n'
             '  local prev=""\n'
             '  for a in "$@"; do\n'
             '    if [ "$prev" = --json ] && [ "${{STAND_IN_COST:-4.5}}" != none ]; then\n'
             '      printf \'{{"costUsd": %s}}\' "${{STAND_IN_COST:-4.5}}" > "$a"\n'
             '    fi\n'
             '    prev=$a\n'
             '  done\n'
             '}}\n'
             'python3() {{ "{python}" "$@"; }}\n')


@unittest.skipUnless(WORKFLOW and NODE and YAML_MODULES and BASH, "needs the repository, node, js-yaml and bash")
class TheWorkflow(TempDirTest):
    """The CI job spends the API key, so it runs only when a maintainer starts
    it or a release is tagged, with the CLI and the models pinned and the
    ceiling under D5's $15. Its steps run here under bash, with a stand-in
    `claude` on PATH that records its arguments."""

    def setUp(self):
        super().setUp()
        self.doc = node(LOAD_ALL, [WORKFLOW.read_text(encoding="utf-8")], YAML_MODULES)[0]
        self.steps = {s.get("name", s.get("uses", "").split("@")[0]): s for s in self.doc["jobs"]["evals"]["steps"]}

    def run_step(self, name, cwd, **values):
        values.setdefault("RUNNER_TEMP", self.tmp.as_posix())
        script = STAND_INS.format(python=pathlib.Path(sys.executable).as_posix())
        script += "".join(f"export {k}={shlex.quote(v)}\n" for k, v in values.items())
        return subprocess.run([BASH, "-c", script + self.steps[name]["run"]], cwd=cwd, env=env(),
                              capture_output=True, timeout=60)

    def test_it_never_runs_on_a_pull_request(self):
        self.assertEqual({"workflow_dispatch", "push"}, set(self.doc["on"]))
        self.assertEqual({"tags": ["v*"]}, self.doc["on"]["push"])
        self.assertEqual({"contents": "read"}, self.doc["permissions"])
        self.assertIs(False, self.steps["actions/checkout"]["with"]["persist-credentials"])
        self.assertIs(False, self.steps["actions/setup-node"]["with"]["package-manager-cache"])
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(1, text.count("${{ secrets."))
        for step in self.steps.values():                  # inputs reach a script through env only
            self.assertNotIn("${{", step.get("run", ""))

    def test_every_action_is_pinned_to_a_commit(self):
        """A moved tag would run new code in a job that holds the key
        (CodeRabbit on #95)."""
        actions = [s["uses"] for s in self.steps.values() if "uses" in s]
        self.assertEqual(3, len(actions))
        for uses in actions:
            with self.subTest(uses=uses):
                self.assertRegex(uses, r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}$")

    def test_the_cli_is_pinned_past_the_git_check(self):
        pin = re.fullmatch(r"npm install --global @anthropic-ai/claude-code@(\d+)\.(\d+)\.(\d+)",
                           self.steps["Install the Claude Code CLI"]["run"].strip())
        self.assertIsNotNone(pin)
        self.assertGreaterEqual(tuple(map(int, pin.groups())), (2, 1, 283))   # git 2.31 is checked from 2.1.283

    def calls(self):
        """Each call the stand-in claude recorded: (its arguments, {option: the value after it})."""
        found = []
        for n in range(1, 10):
            path = self.tmp / f"claude-args-{n}"
            if not path.exists():
                break
            args = path.read_text(encoding="utf-8").split("\n")[:-1]
            found.append((args, {a: args[i + 1] for i, a in enumerate(args[:-1]) if a.startswith("--")}))
        return found

    def clear_calls(self):
        for stale in self.tmp.glob("claude-args-*"):
            stale.unlink()

    def assert_pinned(self, args, value, tag, ablation):
        self.assertEqual(["plugin", "eval", "."], args[:3])     # the target before --tag and --json
        self.assertLessEqual({"--trust-plugin", "--no-publish", "--json", "--model", "--judge-model",
                              "--max-cost-usd", "--ablation", "--tag", "--runs"}, set(args))
        self.assertEqual((tag, "3", ablation), (value["--tag"], value["--runs"], value["--ablation"]))
        # A case's score is the mean of its runs, so below 1.0 a boundary case
        # passes with its forbidden skill loaded in one run of three (Codex on #95).
        self.assertEqual(1.0, float(value["--threshold"]))
        self.assertTrue(value["--json"].endswith(f"{tag}.json"))
        self.assertRegex(value["--model"], r"^claude-[a-z]+-\d")   # an ID, not an alias
        self.assertRegex(value["--judge-model"], r"^claude-[a-z]+-\d")

    def test_the_routing_set_grants_nothing(self):
        proc = self.run_step("Run the suite", PLUGIN, ANTHROPIC_API_KEY="k", TAG="routing", RUNS="3")
        self.assertEqual(0, proc.returncode, output(proc))
        [(args, value)] = self.calls()
        self.assert_pinned(args, value, "routing", "none")   # it cannot pass without the plugin
        self.assertEqual(14, float(value["--max-cost-usd"]))
        self.assertFalse({"--allow-tools", "--scaffold", "--allow-real-servers", "--mocks"} & set(args))

    def test_the_outcome_set_grants_writes_and_the_gates_alone(self):
        """No shell: Bash needs an OS sandbox the runner does not have, and
        the gates run through the plugin's MCP server (§11)."""
        proc = self.run_step("Run the suite", PLUGIN, ANTHROPIC_API_KEY="k", TAG="outcome", RUNS="3")
        self.assertEqual(0, proc.returncode, output(proc))
        [(args, value)] = self.calls()
        self.assert_pinned(args, value, "outcome", "with-without")   # Δ is what it measures
        self.assertEqual(14, float(value["--max-cost-usd"]))
        self.assertLessEqual({"--scaffold", "--allow-real-servers"}, set(args))
        self.assertEqual(["Write", "Edit", "mcp__plugin_web-design-suite_gates__*"],
                         args[args.index("--allow-tools") + 1:])   # the last option: it takes the rest

    def test_a_release_runs_both_under_one_ceiling(self):
        """On a tag, routing runs first and the outcome set gets what it left:
        one $15 for both (the owner, 2026-10-10)."""
        self.assertEqual("${{ inputs.tag || 'all' }}", self.steps["Run the suite"]["env"]["TAG"])
        proc = self.run_step("Run the suite", PLUGIN, ANTHROPIC_API_KEY="k", TAG="all", RUNS="3",
                             STAND_IN_COST="4.25")
        self.assertEqual(0, proc.returncode, output(proc))
        (routing, first), (outcome, second) = self.calls()
        self.assert_pinned(routing, first, "routing", "none")
        self.assert_pinned(outcome, second, "outcome", "with-without")
        self.assertEqual((14, 9.75), (float(first["--max-cost-usd"]), float(second["--max-cost-usd"])))

    def test_the_outcome_set_waits_for_what_routing_spent(self):
        for cost, message in (("none", "Routing left $0.00"), ("13.5", "Routing left $0.50")):
            with self.subTest(cost=cost):
                self.clear_calls()
                proc = self.run_step("Run the suite", PLUGIN, ANTHROPIC_API_KEY="k", TAG="all", RUNS="3",
                                     STAND_IN_COST=cost)
                self.assertEqual(1, proc.returncode, output(proc))
                self.assertIn(message, output(proc))
                self.assertEqual(["routing"], [value["--tag"] for _, value in self.calls()])

    def test_the_inputs_are_checked_before_any_run(self):
        for changes, message in (({"ANTHROPIC_API_KEY": ""}, "secret is not set"),
                                 ({"TAG": "routing; rm -rf ~"}, "The tag must"),
                                 ({"TAG": "--case"}, "The tag must"),
                                 ({"TAG": "boundary"}, "The tag must"),
                                 ({"RUNS": "0"}, "Runs must"), ({"RUNS": "51"}, "Runs must"),
                                 ({"RUNS": "3 --allow-tools Bash"}, "Runs must")):
            with self.subTest(changes=changes):
                self.clear_calls()
                values = {"ANTHROPIC_API_KEY": "k", "TAG": "routing", "RUNS": "3", **changes}
                proc = self.run_step("Run the suite", PLUGIN, **values)
                self.assertEqual(1, proc.returncode, output(proc))
                self.assertIn(message, output(proc))
                self.assertEqual([], self.calls())

    def test_the_summary_reads_each_result(self):
        evals = self.tmp / "evals"
        evals.mkdir()
        (evals / "routing.json").write_text(json.dumps({
            "aggregates": {"casesPassed": 22, "casesTotal": 23, "overallScore": 0.97}, "costUsd": 4.2,
            "claudeVersion": "2.1.293", "partial": False,
            "cases": [{"name": "web-design-studio", "aggregates": {"score": 1}}]}), encoding="utf-8")
        (evals / "outcome.json").write_text(json.dumps({
            "aggregates": {"casesPassed": 11, "casesTotal": 11, "overallScore": 1}, "costUsd": 6.1,
            "claudeVersion": "2.1.293", "partial": True, "partialReason": "cost_ceiling",
            "cases": [{"name": "pricing-section", "aggregates": {"score": 1}}]}), encoding="utf-8")
        summary = self.tmp / "summary.md"
        proc = self.run_step("Summarise", self.tmp, GITHUB_STEP_SUMMARY=summary.as_posix())
        self.assertEqual(0, proc.returncode, output(proc))
        text = summary.read_text(encoding="utf-8")
        self.assertIn("**routing: 22 of 23 cases passed**, score 0.97, about $4.2, Claude Code 2.1.293", text)
        self.assertIn("| web-design-studio | 1 |", text)
        self.assertIn("**outcome: 11 of 11 cases passed**, score 1, about $6.1, Claude Code 2.1.293, "
                      "partial: cost_ceiling", text)
        self.assertLess(text.index("routing:"), text.index("outcome:"))

    def test_the_summary_is_empty_without_a_result(self):
        summary = self.tmp / "summary.md"
        proc = self.run_step("Summarise", self.tmp, GITHUB_STEP_SUMMARY=summary.as_posix())
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertEqual("", summary.read_text(encoding="utf-8") if summary.exists() else "")


if __name__ == "__main__":
    unittest.main()
