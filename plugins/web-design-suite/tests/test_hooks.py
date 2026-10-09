"""The plugin's hooks (P25: XC-C2, LC-C8, SS-C6, XC-C8's hook part).

hooks/hooks.json runs hooks/design_hooks.mjs under node with the event's
JSON on stdin, as Claude Code does:
- `guard` (PreToolUse on Edit|Write) refuses an edit to a generated file;
- `gate` (PostToolUse on Edit|Write) runs audit_design.py on the changed
  file and returns its findings as additionalContext, and after an edit to a
  token file, diff_system.py against the published snapshot;
- `route` (UserPromptSubmit) names the skill a prompt needs.

The guard, the gate and the token diff act only in a project whose
.design-suite.json turns them on (`hooks`), and the plugin's `design_hooks`
option turns them all off.
Each case here is the JSON Claude Code sends, from a fixture.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from wds_support import NODE, PLUGIN, TempDirTest, env, load_script, output, run_py

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

    def test_the_file_is_named_from_its_project_through_a_link(self):
        """CI on #82: the config's folder is resolved and the edited path was
        not, so through /var on macOS, a short 8.3 name on Windows or any link
        the file was named from outside its project (`../../var/...`)."""
        self.config(designGate=True)
        self.write("src/components/card.css", LEAK)
        outside = pathlib.Path(tempfile.mkdtemp(prefix="wds-hook-link-"))
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        link = outside / "project"
        if os.name == "nt":
            import _winapi
            _winapi.CreateJunction(str(self.tmp), str(link))
            self.addCleanup(os.rmdir, link)              # the junction, never the project
        else:
            link.symlink_to(self.tmp, target_is_directory=True)
            self.addCleanup(link.unlink)
        event = {**self.edit("src/components/card.css"), "cwd": str(link),
                 "tool_input": {"file_path": str(link / "src" / "components" / "card.css")}}
        text = self.run_hook("gate", event)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("audit_design.py found 1 problem in src/components/card.css.", text)

    def test_a_report_past_a_mebibyte_reaches_claude(self):
        """CodeRabbit on #82: spawnSync keeps 1 MiB of output, so a long report
        was cut short and told Claude the audit had stopped."""
        self.config(designGate=True)
        rules = "".join(f"  .c{n} {{ color: var(--neutral-700); }}\n" for n in range(6000))
        self.write("src/components/many.css", "@layer components {\n" + rules + "}\n")
        text = self.context("src/components/many.css")
        self.assertIn("audit_design.py found 6000 problems in src/components/many.css", text)
        self.assertIn("more: run audit_design.py on the file", text)
        self.assertLessEqual(len(text), 10000)

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


TOKENS = """\
@layer tokens {
  :root {
    --neutral-0: oklch(100% 0 0);
    --neutral-500: NEUTRAL;
    --neutral-900: oklch(23% 0.005 75);
    --bg-surface: var(--neutral-0);
    --fg-default: var(--neutral-900);
    --fg-muted: var(--neutral-500);SPACE
  }
}
"""


def tokens(neutral="oklch(53.5% 0.009 75)", space="\n    --space-4: 1rem;"):
    return TOKENS.replace("NEUTRAL", neutral).replace("SPACE", space)


class TheTokenDiff(HookTest):
    """LC-C8: after an edit to a token file, Claude hears what the edit costs
    a consumer, against the published snapshot, while it can still undo it."""

    def setUp(self):
        super().setUp()
        self.write("published/tokens.css", tokens())

    def config(self, snapshot="published/tokens.css", **hooks):
        data = {"schema": 1, "tokens": "src/tokens.css", "hooks": hooks or {"tokenDiff": True}}
        if snapshot:
            data["baselines"] = {"system": snapshot}
        self.write(".design-suite.json", json.dumps(data))

    def context(self, rel="src/tokens.css", **changes):
        out = self.run_hook("gate", self.edit(rel), **changes)
        return out and out["hookSpecificOutput"]["additionalContext"]

    def test_a_removed_name_is_a_major_release(self):
        self.config()
        self.write("src/tokens.css", tokens(space=""))
        text = self.context()
        self.assertIn("web-design-suite token diff: after this edit to src/tokens.css", text)
        self.assertIn("(published/tokens.css) make a major release, tier-1 primitive removed: --space-4", text)
        self.assertIn("\n- tier1-removed: --space-4, 16px → none", text)

    def test_a_contrast_crossing_is_named(self):
        self.config()
        self.write("src/tokens.css", tokens(neutral="oklch(70% 0.009 75)"))
        text = self.context()
        self.assertIn("\n- tier1-value-changed: --neutral-500, #706d68 → #a29e98", text)
        self.assertIn("\n- contrast, light theme: --fg-muted on --bg-surface, 5.17:1 → 2.67:1, "
                      "below 4.5:1 (body text (SC 1.4.3)) and below 3:1 (large text (SC 1.4.3)), "
                      "through --fg-muted, --neutral-500", text)

    def test_an_unchanged_or_additive_edit_is_silent(self):
        """Only a breaking change or a crossing is worth a turn: a minor
        release breaks nothing, and the diff runs on every token edit."""
        self.config()
        self.write("src/tokens.css", tokens())
        self.assertIsNone(self.context())
        self.write("src/tokens.css", tokens(space="\n    --space-4: 1rem;\n    --space-5: 1.25rem;"))
        self.assertIsNone(self.context())

    def test_without_a_published_snapshot_nothing_runs(self):
        """Before the first release there is nothing to compare against."""
        self.write("src/tokens.css", tokens(space=""))
        self.config(snapshot=None)
        self.assertIsNone(self.context())
        self.config(snapshot="published/system.json")                     # named, not yet written
        self.assertIsNone(self.context())

    def test_without_the_opt_in_nothing_runs(self):
        self.write("src/tokens.css", tokens(space=""))
        self.config(designGate=True)                                      # a gate, not the diff
        self.assertIsNone(self.context())
        self.config(tokenDiff=False)
        self.assertIsNone(self.context())
        self.config()
        self.assertIsNone(self.context(CLAUDE_PLUGIN_OPTION_DESIGN_HOOKS="false"))

    def test_only_the_projects_token_files(self):
        self.config()
        self.write("src/tokens.css", tokens(space=""))
        self.write("src/theme.css", tokens(space=""))           # a token file by name, not the project's
        self.assertIsNone(self.context("src/theme.css"))
        self.config(designGate=True, tokenDiff=True)
        self.write("src/components/card.css", LEAK)
        text = self.context("src/components/card.css")
        self.assertIn("audit_design.py found 1 problem", text)
        self.assertNotIn("token diff", text)

    def test_with_the_gate_on_the_diff_still_speaks(self):
        self.config(designGate=True, tokenDiff=True)
        self.write("src/tokens.css", tokens(space=""))
        text = self.context()
        self.assertIn("tier1-removed: --space-4", text)
        self.assertNotIn("design gate", text)                   # a token file's literals are its job

    def test_a_published_system_json_with_components(self):
        """CodeRabbit on #84: the snapshot the docs publish, a system.json with
        components, against the token files, which carry none, read every
        component as removed: a major release on every token edit."""
        self.write("src/tokens.css", tokens())
        self.write("src/components/card.css", "@layer components {\n  .card {\n    --card-bg: var(--bg-surface);\n"
                                              "    background: var(--card-bg);\n  }\n}\n")
        proc = run_py("design-system-docs", "extract_system", "src", "--out", "published/system.json", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertTrue(json.loads((self.tmp / "published" / "system.json").read_bytes())["components"])
        self.config(snapshot="published/system.json")
        self.assertIsNone(self.context())
        self.write("src/tokens.css", tokens(space=""))
        text = self.context()
        self.assertIn("tier1-removed: --space-4", text)
        self.assertNotIn("component-removed", text)

    def test_a_token_file_outside_the_project(self):
        """Codex on #84: a config may name `../shared/tokens.css`. Walking up
        from that file finds no config, so the session's project names it."""
        self.write("app/published/tokens.css", tokens())
        self.write("app/.design-suite.json", json.dumps({
            "schema": 1, "tokens": "../shared/tokens.css", "baselines": {"system": "published/tokens.css"},
            "hooks": {"tokenDiff": True}}))
        self.write("shared/tokens.css", tokens(space=""))
        event = {**self.edit("shared/tokens.css"), "cwd": str(self.tmp / "app")}
        text = self.run_hook("gate", event)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("after this edit to ../shared/tokens.css", text)
        self.assertIn("tier1-removed: --space-4", text)

    def test_a_broken_config_is_said_for_a_contract_it_names(self):
        """Codex on #84: a contract.json is no file the audit reads, so a
        config that failed its checks went unsaid."""
        self.write(".design-suite.json", json.dumps({"schema": 1, "tokens": "src/contract.json",
                                                     "baselines": {"system": "published/tokens.css"},
                                                     "hooks": {"tokenDiff": "yes"}}))
        self.write("src/contract.json", '{"schema": "web-design-suite/contract/1"}')
        self.write("src/other.json", "{}")
        text = self.context("src/contract.json")
        self.assertIn("web-design-suite token diff: .design-suite.json could not be read, so the token diff did "
                      "not run", text)
        self.assertIn('"hooks.tokenDiff" must be true or false', text)
        self.assertIsNone(self.context("src/other.json"))               # a file it does not name

    def test_a_broken_config_in_utf_16_or_32_is_said_too(self):
        """CodeRabbit on #84: the readers take a config in UTF-16 and UTF-32
        (Codex on #81), but the hook read a broken one as UTF-8 only, so the
        token file it names went unsaid."""
        self.write("src/contract.json", '{"schema": "web-design-suite/contract/1"}')
        data = json.dumps({"schema": 1, "tokens": "src/contract.json", "hooks": {"tokenDiff": "yes"}})
        for encoding in ("utf-16", "utf-32"):
            with self.subTest(encoding=encoding):
                self.write(".design-suite.json", data.encode(encoding))
                self.assertIn('"hooks.tokenDiff" must be true or false', self.context("src/contract.json"))

    def test_a_diff_that_cannot_run_is_said(self):
        self.write(".design-suite.json", json.dumps({
            "schema": 1, "tokens": ["src/tokens.css", "src/missing.css"],
            "baselines": {"system": "published/tokens.css"}, "hooks": {"tokenDiff": True}}))
        self.write("src/tokens.css", tokens())
        text = self.context()
        self.assertIn("web-design-suite token diff: diff_system.py stopped (exit 2)", text)
        self.assertIn("missing.css", text)


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

    def test_the_window_is_800_characters_as_the_audit_counts_them(self):
        """Codex on #82: the guard counted UTF-16 units, so 400 emoji pushed a
        marker out of its window and left it in the audit's."""
        self.config(generatedFiles=True)
        self.write("src/emoji.css", "/* " + "\U0001F600" * 400 + " DO NOT EDIT */\n")
        self.assertEqual("deny", self.decision("src/emoji.css")["permissionDecision"])

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
