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
        self.assertEqual(23, len(Suite.cases()))           # 13 routing cases, 10 boundary cases

    def test_each_prompt_has_the_documented_fields(self):
        for case, (fields, body, graders) in Suite.cases().items():
            with self.subTest(case=case):
                self.assertLessEqual(set(fields), PROMPT_FIELDS)
                self.assertTrue(1 <= fields.get("max_turns", 10) <= 200)
                self.assertLessEqual(set(fields["allowed_tools"]), READ_ONLY)
                self.assertIn("Skill", fields["allowed_tools"])
                self.assertIn("routing", fields["tags"])
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
WORKFLOW = REPO / ".github" / "workflows" / "evals.yml" if REPO else None
# Stand-ins the step's script calls by name: shell functions, so no PATH entry
# (a drive letter's colon splits PATH in Git Bash).
STAND_INS = ('claude() {{ [ "$1" = --version ] && return; printf "%s\\n" "$@" > "$RUNNER_TEMP/claude-args"; }}\n'
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
        self.steps = {s.get("name", s.get("uses")): s for s in self.doc["jobs"]["evals"]["steps"]}

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
        self.assertIs(False, self.steps["actions/checkout@v7"]["with"]["persist-credentials"])
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(1, text.count("${{ secrets."))
        for step in self.steps.values():                  # inputs reach a script through env only
            self.assertNotIn("${{", step.get("run", ""))

    def test_the_cli_is_pinned_past_the_git_check(self):
        pin = re.fullmatch(r"npm install --global @anthropic-ai/claude-code@(\d+)\.(\d+)\.(\d+)",
                           self.steps["Install the Claude Code CLI"]["run"].strip())
        self.assertIsNotNone(pin)
        self.assertGreaterEqual(tuple(map(int, pin.groups())), (2, 1, 283))   # git 2.31 is checked from 2.1.283

    def test_the_suite_runs_with_its_pins_and_ceiling(self):
        proc = self.run_step("Run the suite", PLUGIN, ANTHROPIC_API_KEY="k", TAG="routing", RUNS="3")
        self.assertEqual(0, proc.returncode, output(proc))
        args = (self.tmp / "claude-args").read_text(encoding="utf-8").split("\n")[:-1]
        self.assertEqual(["plugin", "eval", "."], args[:3])     # the target before --tag and --json
        flags = {a for a in args if a.startswith("--")}
        self.assertLessEqual({"--trust-plugin", "--no-publish", "--json", "--model", "--judge-model",
                              "--max-cost-usd", "--ablation", "--tag", "--runs"}, flags)
        value = {a: args[i + 1] for i, a in enumerate(args[:-1]) if a.startswith("--")}
        self.assertEqual(("routing", "3", "none"), (value["--tag"], value["--runs"], value["--ablation"]))
        self.assertTrue(value["--json"].endswith(".json"))
        self.assertRegex(value["--model"], r"^claude-[a-z]+-\d")   # an ID, not an alias
        self.assertRegex(value["--judge-model"], r"^claude-[a-z]+-\d")
        self.assertLessEqual(float(value["--max-cost-usd"]), 14)

    def test_the_inputs_are_checked_before_any_run(self):
        for changes, message in (({"ANTHROPIC_API_KEY": ""}, "secret is not set"),
                                 ({"TAG": "routing; rm -rf ~"}, "The tag must"),
                                 ({"TAG": "--case"}, "The tag must"),
                                 ({"RUNS": "0"}, "Runs must"), ({"RUNS": "51"}, "Runs must"),
                                 ({"RUNS": "3 --allow-tools Bash"}, "Runs must")):
            with self.subTest(changes=changes):
                values = {"ANTHROPIC_API_KEY": "k", "TAG": "routing", "RUNS": "3", **changes}
                proc = self.run_step("Run the suite", PLUGIN, **values)
                self.assertEqual(1, proc.returncode, output(proc))
                self.assertIn(message, output(proc))
                self.assertFalse((self.tmp / "claude-args").exists())

    def test_the_summary_reads_the_result(self):
        evals = self.tmp / "evals"
        evals.mkdir()
        (evals / "results.json").write_text(json.dumps({
            "aggregates": {"casesPassed": 22, "casesTotal": 23, "overallScore": 0.97}, "costUsd": 4.2,
            "claudeVersion": "2.1.293", "partial": False,
            "cases": [{"name": "web-design-studio", "aggregates": {"score": 1}}]}), encoding="utf-8")
        summary = self.tmp / "summary.md"
        proc = self.run_step("Summarise", self.tmp, GITHUB_STEP_SUMMARY=summary.as_posix())
        self.assertEqual(0, proc.returncode, output(proc))
        text = summary.read_text(encoding="utf-8")
        self.assertIn("**22 of 23 cases passed**, score 0.97, about $4.2, Claude Code 2.1.293", text)
        self.assertIn("| web-design-studio | 1 |", text)


if __name__ == "__main__":
    unittest.main()
