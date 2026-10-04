"""The token contract, its copies and everything that reads it agree (3.2.0).

token-contract.md is the one list of Tier-2 roles. Before 3.2.0 nothing
checked the tools that enumerate roles against it, and they had drifted: the
Figma importer did not know --elevation-focus or --motion-loop, the migration's
proposed tokens.css had no --motion-loop, and the email token map accounted for
neither. Nothing checked that the 14 copies of the contract, or the deck's copy
of the starter tokens, were still copies.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import unittest

from wds_support import PLUGIN, SKILLS, load_script

STUDIO = SKILLS / "web-design-studio"
CONTRACT = STUDIO / "references" / "token-contract.md"
TOKENS = STUDIO / "assets" / "starter" / "styles" / "tokens.css"


def contract_roles() -> set[str]:
    """Every Tier-2 role name the contract lists, shorthand expanded
    (`--pad-inline-xs/-sm/-md` is three roles)."""
    text = CONTRACT.read_text(encoding="utf-8")
    section = text.split("## Tier-2 roles", 1)[1].split("\n## ", 1)[0]
    section = re.sub(r"Primitives with \*\*no\*\* Tier-2 equivalent.*?(\n\n|$)", "", section, flags=re.S)
    names = set()
    for code in re.findall(r"`([^`]+)`", section):
        for word in code.replace(",", " ").split():
            if not word.startswith("--") or "*" in word:
                continue
            head, *more = word.split("/")
            names.add(head)
            names.update(head.rsplit("-", 1)[0] + suffix for suffix in more)
    return names


def declared(css: str) -> set[str]:
    return set(re.findall(r"(?m)^\s*(--[a-z][\w-]*)\s*:", re.sub(r"/\*.*?\*/", " ", css, flags=re.S)))


def sha(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class InvalidFieldsLookInvalid(unittest.TestCase):
    """P7 (SB-B4): accessibility.md drew an invalid field in --border-focus, so
    it looked focused, and the scaffold drew it in --border-accent."""

    def test_every_invalid_field_rule_reads_the_invalid_role(self):
        files = [SKILLS / "web-design-studio" / "references" / "accessibility.md",
                 SKILLS / "content-model-to-ui" / "scripts" / "scaffold_ui.py"]
        seen = 0
        for path in files:
            for line in path.read_text(encoding="utf-8").splitlines():
                if '[aria-invalid="true"]' in line and "border" in line and "{" in line:
                    seen += 1
                    with self.subTest(file=path.name, rule=line.strip()):
                        self.assertIn("var(--border-invalid)", line)
        self.assertGreaterEqual(seen, 3)


class StatusFillsCarryTheirInk(unittest.TestCase):
    """Codex on #31: the filled danger and success variants kept
    --fg-on-accent, which is near-black in dark (4.38:1 on --bg-danger) and
    3.41:1 white on the success fill; the state matrix put --fg-on-inverse on
    the warning fill."""

    FILES = [SKILLS / "content-model-to-ui" / "scripts" / "scaffold_ui.py",
             SKILLS / "component-state-matrix" / "scripts" / "generate_matrix.py",
             SKILLS / "web-design-studio" / "references" / "stack-css-modules.md",
             SKILLS / "web-design-studio" / "references" / "stack-vanilla-css.md",
             SKILLS / "web-design-studio" / "references" / "stack-tailwind.md"]

    def test_an_ink_on_a_status_fill_is_that_fills_ink(self):
        seen = 0
        for path in self.FILES:
            lines = path.read_text(encoding="utf-8").splitlines()
            for i, line in enumerate(lines):
                for intent in re.findall(r"var\(--bg-(success|warning|danger)\)", line):
                    for ink in re.findall(r"var\(--fg-on-([a-z]+)\)", " ".join(lines[i:i + 3])):
                        seen += 1
                        with self.subTest(file=path.name, line=i + 1):
                            self.assertEqual(ink, intent)
                for intent, ink in re.findall(r"\bbg-(success|warning|danger)\b[^'\"]*\btext-on-([a-z]+)", line):
                    seen += 1
                    with self.subTest(file=path.name, line=i + 1):
                        self.assertEqual(ink, intent)
        self.assertGreaterEqual(seen, 7)

    def test_travel_distances_cross_to_figma_and_invalid_borders_are_versioned_on_sunken(self):
        figma = load_script("figma-variables-sync", "figma_to_tokens")
        self.assertFalse({n for n in figma.COMPOSITE_ONLY if n.startswith("motion-travel-")})
        diff = load_script("design-system-versioning", "diff_system")
        self.assertIn("--border-invalid", diff.UI_ROLES)
        self.assertIn("--bg-sunken", diff.UI_SURFACES)


class ContractCopies(unittest.TestCase):

    def test_the_fourteen_contract_copies_are_identical(self):
        copies = [PLUGIN / "shared" / "token-contract.md", *SKILLS.glob("*/references/token-contract.md")]
        self.assertEqual(len(copies), 14)
        self.assertEqual(len({sha(p) for p in copies}), 1,
                         {p.relative_to(PLUGIN).as_posix(): sha(p)[:12] for p in copies})

    def test_the_decks_tokens_are_the_starters_tokens(self):
        deck = SKILLS / "client-presentation-builder" / "assets" / "deck-tokens.css"
        self.assertEqual(sha(deck), sha(TOKENS))


class EveryConsumerKnowsEveryRole(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.roles = contract_roles()

    def test_the_contract_lists_the_roles_it_should(self):
        self.assertGreater(len(self.roles), 80)
        for role in ("--gap-related", "--pad-block-sm", "--bg-scrim", "--motion-instant", "--z-modal"):
            self.assertIn(role, self.roles)

    def test_the_starter_declares_every_role(self):
        self.assertEqual(set(), self.roles - declared(TOKENS.read_text(encoding="utf-8")))

    def test_the_figma_importer_knows_every_role(self):
        source = (SKILLS / "figma-variables-sync" / "scripts" / "figma_to_tokens.py").read_text(encoding="utf-8")
        tier2 = next(ast.literal_eval(node.value) for node in ast.parse(source).body
                     if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "TIER2")
        self.assertEqual(set(), self.roles - {"--" + name for name in tier2})

    def test_the_email_token_map_accounts_for_every_role(self):
        data = json.loads((SKILLS / "email-template-system" / "assets" / "email-tokens.json")
                          .read_text(encoding="utf-8"))
        keys = set()

        def walk(node):
            if isinstance(node, dict):
                keys.update(k for k in node if k.startswith("--"))
                for value in node.values():
                    walk(value)
        walk(data)
        self.assertEqual(set(), self.roles - keys)          # kept, or dropped with a reason

    def test_the_migrations_proposal_declares_every_role(self):
        from test_token_migration import proposed_tokens_css
        self.assertEqual(set(), self.roles - declared(proposed_tokens_css()))


if __name__ == "__main__":
    unittest.main()
