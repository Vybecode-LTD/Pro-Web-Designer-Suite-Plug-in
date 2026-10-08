"""The plugin's hooks (P25: XC-C2, LC-C8 in part, SS-C6, XC-C8's hook part).

hooks/hooks.json runs hooks/design_hooks.mjs under node with the event's
JSON on stdin, as Claude Code does:
- `guard` (PreToolUse on Edit|Write) refuses an edit to a generated file;
- `gate` (PostToolUse on Edit|Write) runs audit_design.py on the changed
  file and returns its findings as additionalContext;
- `route` (UserPromptSubmit) names the skill a prompt needs.

The guard and the gate act only in a project whose .design-suite.json turns
them on (`hooks`), and the plugin's `design_hooks` option turns all three off.
Each case here is the JSON Claude Code sends, from a fixture.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest

from wds_support import NODE, PLUGIN, TempDirTest, env, load_script, output

HOOKS = PLUGIN / "hooks"
SCRIPT = HOOKS / "design_hooks.mjs"
LEAK = "@layer components {\n  .card {\n    color: var(--neutral-700);\n  }\n}\n"
CLEAN = "@layer components {\n  .card {\n    color: var(--fg-default);\n  }\n}\n"


class TheHooksFile(unittest.TestCase):
    """hooks.json, read as Claude Code reads it."""

    def setUp(self):
        self.hooks = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))["hooks"]

    def test_each_event_runs_one_mode_in_exec_form(self):
        """Exec form, so Windows spawns node.exe itself with no shell between
        (claude-code-capabilities.md §2), and `node` because it is the one name
        node has on every system: Python is `python3` on macOS and `python` on
        Windows."""
        expected = {"PreToolUse": ("Edit|Write", "guard"), "PostToolUse": ("Edit|Write", "gate"),
                    "UserPromptSubmit": (None, "route")}
        self.assertEqual(sorted(expected), sorted(self.hooks))
        for event, (matcher, mode) in expected.items():
            with self.subTest(event=event):
                [group] = self.hooks[event]
                self.assertEqual(matcher, group.get("matcher"))
                [hook] = group["hooks"]
                self.assertEqual(("command", "node"), (hook["type"], hook["command"]))
                self.assertEqual(["${CLAUDE_PLUGIN_ROOT}/hooks/design_hooks.mjs", mode], hook["args"])

    def test_the_option_that_turns_them_off_is_declared(self):
        manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        option = manifest["userConfig"]["design_hooks"]
        self.assertEqual(("boolean", True), (option["type"], option["default"]))

    def test_the_gate_and_the_guard_read_what_the_audit_reads(self):
        """The file types and the generated-file markers are audit_design.py's."""
        audit = load_script("web-design-studio", "audit_design")
        text = SCRIPT.read_text(encoding="utf-8")

        def array(name):
            return re.findall(r"'([^']+)'", re.search(rf"const {name} = \[(.*?)\];", text, re.S).group(1))
        self.assertEqual(sorted(audit.CSS_EXT | audit.JS_EXT | audit.TEMPLATE_EXT), sorted(array("AUDITED")))
        self.assertEqual(list(audit.GENERATED_MARKERS), array("GENERATED"))


@unittest.skipUnless(NODE, "node is not installed")
class HookTest(TempDirTest):
    def setUp(self):
        super().setUp()
        self.write(".git/HEAD", "x\n")

    def config(self, **hooks):
        self.write(".design-suite.json", json.dumps({"schema": 1, "hooks": hooks}))

    def run_hook(self, mode, event, **changes):
        changes.setdefault("WDS_PYTHON", sys.executable)
        proc = subprocess.run([NODE, str(SCRIPT), mode], input=json.dumps(event).encode(), cwd=self.tmp,
                              env=env(**changes), capture_output=True, timeout=180)
        self.assertEqual(0, proc.returncode, output(proc))      # a hook never fails the tool call
        return json.loads(proc.stdout) if proc.stdout.strip() else None

    def edit(self, rel, tool="Edit"):
        return {"hook_event_name": "PostToolUse", "tool_name": tool, "cwd": str(self.tmp),
                "tool_input": {"file_path": str(self.tmp / rel)}}


class TheDesignGate(HookTest):
    """XC-C2, SS-C6: the audit's findings reach Claude at the edit, not at
    the commit."""

    def context(self, rel, **changes):
        out = self.run_hook("gate", self.edit(rel), **changes)
        return out and out["hookSpecificOutput"]["additionalContext"]

    def test_an_opted_in_project_hears_of_a_leak(self):
        self.config(designGate=True)
        self.write("src/components/card.css", LEAK)
        text = self.context("src/components/card.css")
        self.assertIn("audit_design.py found 1 problem in src/components/card.css", text)
        self.assertIn("L6 tier1-leak (error)", text)
        self.assertIn("--neutral-700", text)

    def test_a_clean_file_says_nothing(self):
        self.config(designGate=True)
        self.write("src/components/card.css", CLEAN)
        self.assertIsNone(self.context("src/components/card.css"))

    def test_without_the_opt_in_nothing_runs(self):
        self.write("src/components/card.css", LEAK)
        self.assertIsNone(self.context("src/components/card.css"))             # no config
        self.config(generatedFiles=True)
        self.assertIsNone(self.context("src/components/card.css"))             # the gate not named
        self.config(designGate=False)
        self.assertIsNone(self.context("src/components/card.css"))

    def test_the_option_turns_it_off(self):
        self.config(designGate=True)
        self.write("src/components/card.css", LEAK)
        for value in ("false", "0", "off"):
            with self.subTest(value=value):
                self.assertIsNone(self.context("src/components/card.css", CLAUDE_PLUGIN_OPTION_DESIGN_HOOKS=value))
        self.assertIsNotNone(self.context("src/components/card.css", CLAUDE_PLUGIN_OPTION_DESIGN_HOOKS="true"))

    def test_only_the_files_the_audit_reads(self):
        self.config(designGate=True)
        self.write("notes.md", "color: #fff\n")
        self.assertIsNone(self.context("notes.md"))

    def test_the_projects_own_config_reaches_the_audit(self):
        """The audit runs in the config's folder, so the project's components
        and ramps count (XC-C8's hook part)."""
        self.write(".design-suite.json", json.dumps({"schema": 1, "hooks": {"designGate": True},
                                                     "tokens": "src/brand/palette.css",
                                                     "components": ["src/widgets/**"]}))
        self.write("src/brand/palette.css", "@layer tokens {\n  :root {\n    --brand-500: #b4400a;\n  }\n}\n")
        self.write("src/widgets/card.css", "@layer layout {\n  .card {\n    color: var(--brand-500);\n  }\n}\n")
        self.assertIn("L6 tier1-leak", self.context("src/widgets/card.css"))

    def test_a_broken_config_or_no_python_is_said(self):
        self.write(".design-suite.json", '{"schema": 1, "hooks": {"designGate": "yes"}}')
        self.write("src/components/card.css", LEAK)
        self.assertIn('"hooks.designGate" must be true or false', self.context("src/components/card.css"))
        self.config(designGate=True)
        self.assertIn("needs Python 3", self.context("src/components/card.css",
                                                     WDS_PYTHON=str(self.tmp / "no-python")))


class TheGeneratedFileGuard(HookTest):
    """LC-C8: an edit to a file that says it is generated is lost at the next
    build, so Claude is sent to its source instead."""

    def decision(self, rel, tool="Edit"):
        out = self.run_hook("guard", {**self.edit(rel, tool), "hook_event_name": "PreToolUse"})
        return out and out["hookSpecificOutput"]

    def test_a_generated_file_is_refused_with_the_reason(self):
        self.config(generatedFiles=True)
        self.write("src/tokens.css", "/* GENERATED FILE -- DO NOT EDIT BY HAND. */\n:root { --x: 1px; }\n")
        for tool in ("Edit", "Write"):
            with self.subTest(tool=tool):
                out = self.decision("src/tokens.css", tool)
                self.assertEqual("deny", out["permissionDecision"])
                self.assertIn('src', out["permissionDecisionReason"])
                self.assertIn('"DO NOT EDIT"', out["permissionDecisionReason"])

    def test_an_ordinary_or_new_file_passes(self):
        self.config(generatedFiles=True)
        self.write("src/card.css", "/* The card. */\n.card { }\n")
        self.assertIsNone(self.decision("src/card.css"))
        self.assertIsNone(self.decision("src/new.css", "Write"))
        self.write("src/late.css", "x" * 900 + "DO NOT EDIT\n")          # past the first 800 characters
        self.assertIsNone(self.decision("src/late.css"))

    def test_without_the_opt_in_nothing_is_refused(self):
        self.write("src/tokens.css", "/* @generated */\n")
        self.assertIsNone(self.decision("src/tokens.css"))
        self.config(designGate=True)
        self.assertIsNone(self.decision("src/tokens.css"))


class TheRouter(HookTest):
    """When the skill listing has dropped the plugin's descriptions, a prompt
    that names a skill's work hears which skill it is
    (claude-code-capabilities.md, "Implications")."""

    def routed(self, prompt, **changes):
        out = self.run_hook("route", {"hook_event_name": "UserPromptSubmit", "prompt": prompt}, **changes)
        return re.findall(r"/web-design-suite:([\w-]+)", out["hookSpecificOutput"]["additionalContext"]) if out else []

    def test_a_prompt_hears_the_skill_for_its_work(self):
        cases = {"Run an axe audit of the checkout against WCAG 2.2": ["a11y-audit-runner"],
                 "Sync our Figma variables into tokens.css": ["figma-variables-sync"],
                 "Critique this design system's docs site": ["design-system-docs", "design-critique-gate"],
                 "Build the welcome HTML email": ["email-template-system"],
                 "Our LCP is 4s, set a performance budget": ["perf-budget-gate"],
                 "Replace the hardcoded colors with tokens": ["design-token-migration"],
                 "Make admin screens from the Supabase schema": ["content-model-to-ui"],
                 "Write a landing page with one CTA": ["landing-page-conversion"],
                 "Set up a spacing scale and cascade layers": ["web-design-studio"]}
        for prompt, skills in cases.items():
            with self.subTest(prompt=prompt):
                self.assertEqual(skills, self.routed(prompt))

    def test_other_prompts_and_named_skills_hear_nothing(self):
        for prompt in ("Fix the login bug", "Rename the class in utils.ts",
                       "Use /web-design-suite:a11y-audit-runner on the checkout"):
            with self.subTest(prompt=prompt):
                self.assertEqual([], self.routed(prompt))

    def test_the_option_turns_it_off(self):
        self.assertEqual([], self.routed("Run an axe audit", CLAUDE_PLUGIN_OPTION_DESIGN_HOOKS="false"))


if __name__ == "__main__":
    unittest.main()
