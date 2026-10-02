"""Every CSS, TSX and JSX block in the skills' markdown passes the design audit (3.2.0).

A reference that shows code is teaching someone to copy it, so the code has to
pass the gate the suite ships. Three kinds of block are not for copying and say
so with a marker in a comment inside the block:

    /* example: wrong */         a deliberate anti-pattern
    /* example: before */        the starting state of a migration
    /* example: illustration */  literal values shown to explain a measurement,
                                 or third-party code you do not own

How each block is audited. A CSS block is split into its top-level statements,
because references often show a token and the rule that uses it together:
- token content goes to `styles/tokens.css`: `@layer tokens`, a Tailwind
  `@theme`, and rules on the root, a theme, a density or `.inverse` that
  declare only custom properties;
- everything else is an excerpt of a component file, `components/snippet.css`,
  wrapped in `@layer components { … }` unless it declares its own layers;
- TSX and JSX are audited as `components/Snippet.tsx`;
- email CSS is left to email-template-system's own linter, `lint_email`.

Regressions covered: SS-A6 (the references' own CSS failed the gate), SS-A7
(code "quoted" from the starter read undeclared sockets and inline styles),
SB-C5 (canonical snippets such as the focus ring still used the box-shadow ring
3.1.0 replaced, and component examples read Tier-1 primitives).
"""
from __future__ import annotations

import importlib.util
import pathlib
import re
import sys
import unittest

from wds_support import PLUGIN, SKILLS, TempDirTest

FENCE = re.compile(r"^```(\w*)[^\n]*\n(.*?)^```", re.S | re.M)
NOT_FOR_COPYING = re.compile(r"example:\s*(wrong|before|illustration)\b", re.I)
DECLARATION = re.compile(r"(?:^|[{;])\s*(--)?[\w-]+\s*:(?!:)", re.M)


def load_audit():
    """audit_design as a module: one process for every snippet, and each
    snippet audited on its own, so the cross-file pass never sees two
    unrelated examples as one component with two homes."""
    spec = importlib.util.spec_from_file_location(
        "wds_audit_design", SKILLS / "web-design-studio" / "scripts" / "audit_design.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module                    # dataclasses look the module up
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


QUOTED = re.compile(r"<!--\s*snippet:[^>]*-->\s*$")


def snippets():
    """(doc, line, language, body) for every block the gate should pass. A block
    quoted from the starter (`<!-- snippet: … -->` above it) is checked by
    identity instead: tools/sync_snippets.py, and the starter's own audit."""
    for doc in sorted(SKILLS.rglob("*.md")):
        if doc.relative_to(SKILLS).parts[0] == "email-template-system":
            continue
        text = doc.read_text(encoding="utf-8")
        for m in FENCE.finditer(text):
            lang, body = m.group(1).lower(), m.group(2)
            if QUOTED.search(text[:m.start()].rstrip("\n").rsplit("\n", 1)[-1]):
                continue
            if lang in ("css", "tsx", "jsx") and not NOT_FOR_COPYING.search(body):
                yield doc, text.count("\n", 0, m.start()) + 1, lang, body


ROOT_LIKE = re.compile(r"^(?:\s*(?::root|html|:host|\.inverse|\[data-(?:theme|density)[^\]]*\])"
                       r"(?:\s+|\s*,\s*)?)+$")


def statements(css: str) -> list[str]:
    """Top-level statements, each with the comments (and pragmas) before it."""
    masked = re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), css, flags=re.S)
    out, depth, start = [], 0, 0
    for i, ch in enumerate(masked):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                out.append(css[start:i + 1])
                start = i + 1
        elif ch == ";" and depth == 0:
            out.append(css[start:i + 1])
            start = i + 1
    if css[start:].strip():
        out.append(css[start:])
    return out


def code_of(statement: str) -> str:
    return re.sub(r"/\*.*?\*/", " ", statement, flags=re.S).strip()


def is_bare_declaration(statement: str) -> bool:
    """`--x: value;` on its own: a line excerpted from a tokens file."""
    return bool(re.match(r"--[\w-]+\s*:", code_of(statement)))


def is_token_content(statement: str) -> bool:
    code = code_of(statement)
    if re.match(r"@(layer\s+tokens\b|theme\b)", code) or is_bare_declaration(statement):
        return True
    m = re.match(r"@(?:media|supports|container)\b[^{]*\{(.*)\}$", code, re.S)
    if m:                                   # e.g. reduced motion re-pointing durations
        inner = statements(m.group(1))
        return bool(inner) and all(is_token_content(s) for s in inner)
    m = re.match(r"([^{@]+)\{(.*)\}$", code, re.S)
    if not m or not ROOT_LIKE.match(m.group(1).strip()) or "{" in m.group(2):
        return False
    kinds = [bool(d.group(1)) for d in DECLARATION.finditer(m.group(2))]
    return bool(kinds) and all(kinds)


def as_files(lang: str, body: str) -> list[tuple[str, str]]:
    """Where the block's parts would live in a project, and their text there."""
    if lang in ("tsx", "jsx"):
        return [(f"components/Snippet.{lang}", body)]
    parts = statements(body)
    bare = "".join(p for p in parts if is_bare_declaration(p))
    tokens = (":root {\n" + bare + "\n}\n" if bare.strip() else "") + "".join(
        p for p in parts if is_token_content(p) and not is_bare_declaration(p))
    rest = "".join(p for p in parts if not is_token_content(p))
    files = [("styles/tokens.css", tokens)] if tokens.strip() else []
    if re.sub(r"/\*.*?\*/", "", rest, flags=re.S).strip():
        files.append(("components/snippet.css",
                      rest if "@layer" in rest else "@layer components {\n" + rest + "\n}\n"))
    return files


class ReferenceSnippetsPassTheGate(TempDirTest):
    maxDiff = None

    def test_every_snippet_meant_for_copying_passes_the_audit(self):
        audit = load_audit()
        blocks = list(snippets())
        self.assertGreater(len(blocks), 150)                   # the extraction still works
        for n, (doc, line, lang, body) in enumerate(blocks):
            with self.subTest(block=f"{doc.relative_to(SKILLS)}:{line}"):
                paths = []
                for name, text in as_files(lang, body):
                    path = self.tmp / f"b{n}" / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(text, encoding="utf-8")
                    paths.append(str(path))
                findings, audited, skipped = audit.audit_run(paths)
                self.assertEqual((audited, skipped), (len(paths), []))
                self.assertEqual([], [f"{f.law} {f.rule} ({f.severity}): {f.message}"
                                      for f in findings])      # --strict: warnings count too


def sync_tool(plugin: pathlib.Path = pathlib.Path(__file__).resolve().parents[1]):
    """tools/sync_snippets.py, by default from this suite's own plugin; the
    tree it checks is the one under test (WDS_PLUGIN_ROOT may point at an
    older copy)."""
    spec = importlib.util.spec_from_file_location("wds_sync_snippets", plugin / "tools" / "sync_snippets.py")
    sync = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sync)
    return sync


class QuotedStarterCode(unittest.TestCase):
    """SS-C4, SS-A7: code a reference says it quotes from the starter is the
    starter's code, and the starter passes its own gate."""

    def test_every_quote_matches_its_region_in_the_starter(self):
        sync = sync_tool()
        self.assertGreaterEqual(len(list(sync.quoted_blocks(SKILLS))), 4)
        self.assertEqual([], sync.sync(check=True, skills=SKILLS))

    def test_the_starter_passes_its_own_audit(self):
        styles = SKILLS / "web-design-studio" / "assets" / "starter" / "styles"
        findings, audited, _ = load_audit().audit_run([str(styles)])
        self.assertEqual(audited, 5)                    # reset, tokens, base, layout and index
        self.assertEqual([], [f"{f.file}:{f.line} {f.law} {f.rule}: {f.message}" for f in findings])


class SyncRewritesAStaleQuote(TempDirTest):
    """N6: without --check, sync_snippets.py rewrites a stale quote from its
    region, as UTF-8 with LF endings. It wrote with write_text(newline=""),
    which Python 3.9 does not accept."""

    def test_a_stale_quote_is_rewritten_byte_for_byte(self):
        skills = self.tmp / "skills"
        self.write("skills/web-design-studio/assets/starter/styles/layout.css",
                   "@layer layout {\n  /* @snippet flow */\n"
                   "  .flow > * + * { margin-block-start: var(--flow-space); } /* café */\n"
                   "  /* @end-snippet */\n}\n")
        doc = self.write("skills/demo/references/guide.md",
                         "# Guide — naïve\n\n<!-- snippet: layout.css#flow -->\n```css\n.flow { }\n```\n")
        # The tool under test is the plugin's own, so WDS_PLUGIN_ROOT runs an
        # older release's (3.2.1's fails on 3.9). Before 3.2.0 there was none.
        if not (PLUGIN / "tools" / "sync_snippets.py").is_file():
            self.skipTest("the plugin under test has no tools/sync_snippets.py")
        sync = sync_tool(PLUGIN)
        self.assertEqual(["demo/references/guide.md: layout.css#flow"], sync.sync(check=False, skills=skills))
        self.assertEqual(("# Guide — naïve\n\n<!-- snippet: layout.css#flow -->\n```css\n"
                          ".flow > * + * { margin-block-start: var(--flow-space); } /* café */\n```\n"
                          ).encode("utf-8"), doc.read_bytes())
        self.assertEqual([], sync.sync(check=True, skills=skills))


if __name__ == "__main__":
    unittest.main()
