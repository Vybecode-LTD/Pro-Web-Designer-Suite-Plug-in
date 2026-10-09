"""The subagents (P27 part 1: PS-C4, XC-C4, GT-C9, DL-C7, SS-C6, LC-C9).

agents/*.md are plugin subagents: each critiques, audits or reviews in its own
context and returns only what the main conversation needs. The frontmatter goes
through js-yaml, a real YAML parser, from the suite's tooling, and may hold
only the fields a plugin subagent honours: plugin agents ignore `hooks`,
`mcpServers` and `permissionMode`, and `initialPrompt` (sub-agents page,
re-read 2026-10-09, claude-code-capabilities.md §8).
"""
from __future__ import annotations

import re
import unittest

from test_commands import COMMANDS, front, needs_yaml
from wds_support import PLUGIN, SKILLS

AGENTS = PLUGIN / "agents"
NAMES = ["a11y-auditor", "codemod-batch-reviewer", "design-auditor", "design-critic", "gate-runner",
         "supabase-security-reviewer"]
# The sub-agents page's frontmatter table, less the four a plugin agent ignores.
HONOURED = {"name", "description", "tools", "disallowedTools", "model", "effort", "maxTurns", "skills", "memory",
            "background", "omitClaudeMd", "isolation", "color", "experimental"}
IGNORED = {"hooks", "mcpServers", "permissionMode", "initialPrompt"}
TOOLS = {"Read", "Grep", "Glob", "Bash", "Edit", "Write", "NotebookEdit", "WebFetch", "WebSearch", "Skill"}
WRITES = {"Edit", "Write", "NotebookEdit"}
COLORS = {"red", "blue", "green", "yellow", "purple", "orange", "pink", "cyan"}


class TheAgentFiles(unittest.TestCase):

    def test_the_six_agents_are_in_the_default_folder(self):
        self.assertEqual(NAMES, sorted(p.stem for p in AGENTS.glob("*.md")))
        self.assertEqual([], [p.name for p in AGENTS.rglob("*") if p.is_dir()])   # a subfolder renames them

    @needs_yaml
    def test_each_agent_has_only_the_fields_a_plugin_agent_honours(self):
        agents = sorted(AGENTS.glob("*.md"))
        self.assertTrue(agents)                                       # no vacuous pass
        for agent in agents:
            with self.subTest(agent=agent.stem):
                fields, body = front(agent)
                self.assertEqual(agent.stem, fields["name"])
                self.assertNotIn(":", fields["name"])
                self.assertTrue(0 < len(fields["description"]) <= 1024)
                self.assertEqual(set(), set(fields) - HONOURED, "a field Claude Code ignores, or a typo")
                self.assertFalse(set(fields) & IGNORED)
                self.assertIn(fields.get("color", "red"), COLORS)
                self.assertTrue(body.strip())

    @needs_yaml
    def test_each_agent_has_its_tools_and_none_edits_the_work(self):
        """PS-C4's critic has Read, Grep, Glob and Bash; every agent here
        reports and none may edit, so none has a writing tool."""
        for agent in sorted(AGENTS.glob("*.md")):
            with self.subTest(agent=agent.stem):
                fields, body = front(agent)
                tools = [t.strip() for t in fields["tools"].split(",")]
                self.assertTrue(set(tools) <= TOOLS, tools)
                self.assertFalse(set(tools) & WRITES)
                self.assertIn("Bash", tools)
        self.assertEqual("Read, Grep, Glob, Bash", front(AGENTS / "design-critic.md")[0]["tools"])
        self.assertIs(True, front(AGENTS / "design-critic.md")[0]["omitClaudeMd"])

    @needs_yaml
    def test_each_preloaded_skill_exists_and_can_be_preloaded(self):
        """`skills:` preloads a skill's full content; one with
        `disable-model-invocation: true` cannot be preloaded."""
        preloaded = []
        for agent in sorted(AGENTS.glob("*.md")):
            for skill in front(agent)[0].get("skills", []):
                with self.subTest(agent=agent.stem, skill=skill):
                    fields, _ = front(SKILLS / skill / "SKILL.md")
                    self.assertNotEqual(True, fields.get("disable-model-invocation"))
                    preloaded.append(skill)
        self.assertEqual(["a11y-audit-runner", "design-token-migration", "web-design-studio", "design-critique-gate",
                          "content-model-to-ui"], preloaded)

    def test_every_script_an_agent_or_command_names_exists(self):
        """The bodies run the skills' scripts by ${CLAUDE_PLUGIN_ROOT}, which
        Claude Code substitutes in agent and command content."""
        named = []
        for doc in [*AGENTS.glob("*.md"), *COMMANDS.glob("*/SKILL.md")]:
            for path in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+)", doc.read_text(encoding="utf-8")):
                with self.subTest(doc=doc.name, path=path):
                    self.assertTrue((PLUGIN / path).is_file())
                    named.append(path)
        self.assertGreater(len(named), 20)

    def test_each_agent_says_what_its_scripts_write_and_check(self):
        """Codex on #89: the matrix writes HTML, not JSON; the critic's
        snapshots write files, so it names their folder; and an update policy
        without WITH CHECK has its USING check the new row (Postgres)."""
        def text(name):
            return " ".join((AGENTS / f"{name}.md").read_text(encoding="utf-8").split())
        self.assertIn("design-reports/matrix/report/index.html", text("gate-runner"))
        self.assertIn("for the matrix, read the console's summary", text("gate-runner"))
        self.assertIn("critique_snapshots.mjs\" TARGET --out design-reports/critique/shots", text("design-critic"))
        self.assertIn("The one folder anything is written to is `design-reports/critique/`", text("design-critic"))
        self.assertIn("without one, its `USING`, which Postgres then applies to the new row too",
                      text("supabase-security-reviewer"))

    def test_the_critique_command_hands_the_work_to_the_critic(self):
        body = (COMMANDS / "critique" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("`web-design-suite:design-critic`", body)
        self.assertIn("Pass nothing else", body)
        self.assertIn("design-reports/critique/findings.json", body)
        self.assertIn("design-reports/critique/findings.json", (COMMANDS / "deck" / "SKILL.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
