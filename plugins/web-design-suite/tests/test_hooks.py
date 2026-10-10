"""The plugin's hooks (P25: XC-C2, LC-C8, SS-C6, XC-C8's hook part; P27: GT-C9, DL-C7).

hooks/hooks.json runs hooks/design_hooks.mjs under node with the event's
JSON on stdin, as Claude Code does:
- `guard` (PreToolUse on Edit|Write) refuses an edit to a generated file;
- `gate` (PostToolUse on Edit|Write) runs audit_design.py and a11y_static.py
  on the changed file and returns their findings as additionalContext; after
  an edit to a token file, diff_system.py against the published snapshot; and
  after an edit to an email template, lint_email.py, build_email.py and
  lint_email.py again;
- `route` (UserPromptSubmit) names the skill a prompt needs.

The guard, the gates, the token diff and the email build act only in a project whose
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

    def test_the_a11y_gate_reads_what_a11y_static_reads(self):
        a11y = load_script("a11y-audit-runner", "a11y_static")
        text = SCRIPT.read_text(encoding="utf-8")
        found = re.findall(r"'([^']+)'", re.search(r"const A11Y_READ = \[(.*?)\];", text, re.S).group(1))
        self.assertEqual(sorted(a11y.AUDITABLE_EXT), sorted(found))


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


PAGE = '<!doctype html>\n<html lang="en">\n<head><title>Home</title></head>\n<body>\n<main>\n{}\n</main>\n</body>\n</html>\n'


class TheA11yGate(HookTest):
    """GT-C9 (b): a11y_static's findings on the file Claude edited, behind
    `hooks.a11yGate`, in the same additionalContext as the audit's."""

    def context(self, rel, **changes):
        out = self.run_hook("gate", self.edit(rel), **changes)
        return out and out["hookSpecificOutput"]["additionalContext"]

    def test_an_opted_in_project_hears_of_a_missing_alt(self):
        self.config(a11yGate=True)
        self.write("index.html", PAGE.format('<img src="hero.png">'))
        text = self.context("index.html")
        self.assertIn("a11y gate: a11y_static.py found 1 problem in index.html", text)
        self.assertIn("line 6, img-no-alt, WCAG 1.1.1 (error)", text)
        self.write("index.html", PAGE.format('<img src="hero.png" alt="The harbour at dawn">'))
        self.assertIsNone(self.context("index.html"))                         # a clean file says nothing

    def test_without_the_key_nothing_runs(self):
        self.write("index.html", PAGE.format('<img src="hero.png">'))
        self.assertIsNone(self.context("index.html"))                         # no config
        self.config(designGate=True)
        self.assertIsNone(self.context("index.html"))                         # the audit alone: a clean page for it
        self.config(a11yGate=False)
        self.assertIsNone(self.context("index.html"))
        self.config(a11yGate=True)
        self.assertIsNone(self.context("index.html", CLAUDE_PLUGIN_OPTION_DESIGN_HOOKS="false"))

    def test_only_the_files_a11y_static_reads(self):
        """A template the audit does not read (.php) is checked too, and a
        Markdown file is not."""
        self.config(a11yGate=True)
        self.write("views/home.php", PAGE.format('<img src="hero.png">'))
        self.assertIn("img-no-alt", self.context("views/home.php"))
        self.write("notes.md", '<img src="hero.png">\n')
        self.assertIsNone(self.context("notes.md"))

    def test_an_email_template_is_left_to_the_email_build(self):
        """R3's live check: the plugin's own receipt template drew a page's
        findings (no <main>, an outline reset on img). The email build checks
        a template; the a11y gate still checks a page beside it."""
        receipt = PLUGIN / "skills" / "email-template-system" / "assets" / "templates" / "transactional-receipt.html"
        self.config(a11yGate=True)
        self.write("emails/receipt.html", receipt.read_text(encoding="utf-8"))
        self.assertIsNone(self.context("emails/receipt.html"))
        self.write("receipt.html", receipt.read_text(encoding="utf-8"))   # not a template by `emails`
        self.assertIn("a11y gate: a11y_static.py found", self.context("receipt.html"))

    def test_the_projects_a11y_baseline_applies(self):
        self.config(a11yGate=True)
        self.write("index.html", PAGE.format('<img src="hero.png">'))
        proc = run_py("a11y-audit-runner", "a11y_static", "index.html", "--write-baseline", ".a11y-baseline.json",
                      cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertIsNone(self.context("index.html"))

    def test_the_audit_and_the_a11y_gate_share_the_cap(self):
        """Claude Code caps additionalContext at 10,000 characters, so the two
        reports share LIMIT, each counting what it left out."""
        self.config(designGate=True, a11yGate=True)
        rules = "".join(f".c{n}:focus {{ outline: none; color: var(--neutral-700); }}\n" for n in range(3000))
        self.write("src/components/many.css", rules)      # a11y_static reads a rule at the top level
        text = self.context("src/components/many.css")
        self.assertRegex(text, r"audit_design.py found 300[01] problems")     # and the file is unlayered
        self.assertIn("a11y_static.py found 3000 problems", text)
        self.assertIn("more: run audit_design.py on the file", text)
        self.assertIn("more: run a11y_static.py on the file", text)
        self.assertLess(text.index("audit_design.py"), text.index("a11y_static.py"))
        self.assertLessEqual(len(text), 10000)

    def test_a_key_that_is_not_a_boolean_is_said(self):
        self.write(".design-suite.json", '{"schema": 1, "hooks": {"a11yGate": "yes"}}')
        self.write("index.html", PAGE.format('<img src="hero.png">'))
        self.assertIn('"hooks.a11yGate" must be true or false', self.context("index.html"))
        self.write("views/home.php", PAGE.format(""))                          # a file only a11y_static reads
        self.assertIn('"hooks.a11yGate" must be true or false', self.context("views/home.php"))


NEWSLETTER = (PLUGIN / "skills" / "email-template-system" / "assets" / "templates" / "newsletter.html")
UNSUBSCRIBE = ' or <a href="https://example.com/unsubscribe?e={{email_hash}}">unsubscribe</a>'


class TheEmailBuild(HookTest):
    """DL-C7: after an edit to an email template, the source is linted, built
    into a temporary folder and the build linted, behind `hooks.emailBuild`;
    the errors reach Claude. A template is a file `emails` matches,
    `emails/**/*.html` by default."""

    def setUp(self):
        super().setUp()
        self.letter = NEWSLETTER.read_text(encoding="utf-8")
        self.assertIn(UNSUBSCRIBE, self.letter)

    def context(self, rel, **changes):
        out = self.run_hook("gate", self.edit(rel), **changes)
        return out and out["hookSpecificOutput"]["additionalContext"]

    def test_the_starters_newsletter_is_silent(self):
        """It has warnings (values off the email scale), which /email-build
        shows; the hook names only errors."""
        self.config(emailBuild=True)
        self.write("emails/newsletter.html", self.letter)
        self.assertIsNone(self.context("emails/newsletter.html"))

    def test_a_missing_unsubscribe_link_is_an_error_in_the_build(self):
        self.config(emailBuild=True)
        self.write("emails/newsletter.html", self.letter.replace(UNSUBSCRIBE, ""))
        # a temporary root of its own, so anything this run leaves is seen,
        # whatever its name (CodeRabbit on #91)
        temp = self.tmp / "temp"
        temp.mkdir()
        roots = {"TEMP": str(temp), "TMP": str(temp), "TMPDIR": str(temp)}
        text = self.context("emails/newsletter.html", **roots)
        self.assertIn("email build: emails/newsletter.html has 1 error and 6 warnings", text)
        self.assertIn("- the build, links: no unsubscribe link found", text)
        self.assertEqual([], list(temp.iterdir()))                           # the build's folder removed
        roots = {name: str(self.tmp / "no-temp") for name in roots}           # the control: the build is made there
        self.assertIsNone(self.context("emails/newsletter.html", **roots))

    def test_an_unknown_token_stops_the_build(self):
        self.config(emailBuild=True)
        self.write("emails/newsletter.html", self.letter.replace('class="legal"', 'class="legal" style="color:var(--no-such-ink);"', 1))
        text = self.context("emails/newsletter.html")
        self.assertIn("- the build stopped (exit 2)", text)
        self.assertIn("--no-such-ink", text)

    def test_a_build_past_gmails_clip_is_an_error(self):
        self.config(emailBuild=True)
        filler = "<p>" + "Wharf Road news. " * 7000 + "</p>\n"
        self.write("emails/newsletter.html", self.letter.replace("</body>", filler + "</body>", 1))
        text = self.context("emails/newsletter.html")
        self.assertIn("- the build, size: ", text)                            # the lint of the build says it
        self.assertIn("exceeds Gmail's 102,400-byte clipping threshold", text)

    def test_only_the_templates_emails_names(self):
        broken = self.letter.replace(UNSUBSCRIBE, "")
        self.config(emailBuild=True)
        self.write("src/pages/newsletter.html", broken)
        self.assertIsNone(self.context("src/pages/newsletter.html"))          # not under emails/
        self.write(".design-suite.json", json.dumps({"schema": 1, "hooks": {"emailBuild": True},
                                                     "emails": ["src/pages/*.html"]}))
        self.assertIn("no unsubscribe link found", self.context("src/pages/newsletter.html"))
        self.write("emails/newsletter.html", broken)
        self.assertIsNone(self.context("emails/newsletter.html"))             # the default no longer applies

    def test_without_the_key_nothing_runs(self):
        self.write("emails/newsletter.html", self.letter.replace(UNSUBSCRIBE, ""))
        self.assertIsNone(self.context("emails/newsletter.html"))             # no config
        self.config(emailBuild=False, a11yGate=False)
        self.assertIsNone(self.context("emails/newsletter.html"))
        self.write(".design-suite.json", '{"schema": 1, "hooks": {"emailBuild": 1}}')
        self.assertIn('"hooks.emailBuild" must be true or false', self.context("emails/newsletter.html"))


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
                 "Check the form's screen-reader labels": ["a11y-audit-runner"],      # the eval run on #95
                 "Sync our Figma variables into tokens.css": ["figma-variables-sync"],
                 "Critique this design system's docs site": ["design-system-docs", "design-critique-gate"],
                 "Generate the token reference and prop tables": ["design-system-docs"],
                 "We need a documentation site for our design system": ["design-system-docs", "web-design-studio"],
                 "Does our pricing page look professional?": ["landing-page-conversion", "design-critique-gate"],
                 "Build the welcome HTML email": ["email-template-system"],
                 "Our LCP is 4s, set a performance budget": ["perf-budget-gate"],
                 "Replace the hardcoded colors with tokens": ["design-token-migration"],
                 "Make admin screens from the Supabase schema": ["content-model-to-ui"],
                 "Write a landing page with one CTA": ["landing-page-conversion"],
                 "Set up a spacing scale and cascade layers": ["web-design-studio"],
                 # P30's eval: the file name's dot ends the sentence before the question
                 "We re-pointed --bg-accent in tokens.css. Can we ship it as a patch release?":
                     ["design-system-versioning"],
                 "Is a renamed design token a major version?": ["design-system-versioning", "web-design-studio"]}
        for prompt, skills in cases.items():
            with self.subTest(prompt=prompt):
                self.assertEqual(skills, self.routed(prompt))

    def test_other_prompts_and_named_skills_hear_nothing(self):
        for prompt in ("Fix the login bug", "Rename the class in utils.ts",
                       "Add prop tables to our React library's README",     # library docs (Codex on #95)
                       "Can this login fix ship as a patch release?",       # a release with no tokens in it
                       # an API's token is not a design token (Codex on #97)
                       "We changed authentication token handling in the API. Can we ship this as a patch release?",
                       "Use /web-design-suite:a11y-audit-runner on the checkout"):
            with self.subTest(prompt=prompt):
                self.assertEqual([], self.routed(prompt))

    def test_the_option_turns_it_off(self):
        self.assertEqual([], self.routed("Run an axe audit", CLAUDE_PLUGIN_OPTION_DESIGN_HOOKS="false"))


if __name__ == "__main__":
    unittest.main()
