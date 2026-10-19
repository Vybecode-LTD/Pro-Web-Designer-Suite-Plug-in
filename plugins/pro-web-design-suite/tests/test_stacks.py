"""The stacks stack-frameworks.md teaches: Next.js App Router, Vue, SvelteKit
and Astro (P37 part 3, SB-B6). Standard library unittest only.

Each fixture in tests/fixtures/stacks is a small project with the starter's
styles copied in. The audit, a11y_static and the census must run clean on it,
and each must find what is planted in the stack's own place for it. Running
them first found three gaps, fixed here:
- a11y_static read a framework's document shell (a Next.js root layout, a
  Vite index.html, SvelteKit's app.html, an Astro layout) as a whole page, so
  the page's <main>, and with Next.js and SvelteKit the title, were missing;
- a11y_static read a <slot> in a link as no content, so `<a href><slot/></a>`
  had no name, where a component's content is "cannot tell";
- the census blanks `var(--name` before its whole-value shadow check, so the
  `)` left of `box-shadow: var(--shadow-xs)` was a shadow literal, three of
  them in the starter's own stylesheets.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import unittest

from wds_support import SKILLS, TempDirTest, output, run_py

# The fixtures are the tests' inputs, read beside the tests, so fail_before.py
# runs an older release's gates on them.
STACKS = pathlib.Path(__file__).resolve().parent / "fixtures" / "stacks"
STARTER = SKILLS / "web-design-studio" / "assets" / "starter" / "styles"

# Each stack: the folder its config names for the starter's styles, then what
# is planted (the file, the text replaced, its replacement) and what finds it.
STACK = {
    "next-app": {
        "styles": "app/styles",
        "literal": ("components/Button.module.css", "color: var(--btn-fg);", "color: #c0ffee;"),
        "rule": "raw-color",
        "context": "css-decl",
        "markup": ("components/Button.tsx", "{children}", '<img src="/arrow.svg" />{children}'),
    },
    "vue": {
        "styles": "src/styles",
        "literal": ("src/components/AppButton.vue", ':href="href"\n',
                    ':href="href"\n    :style="{ color: \'#c0ffee\' }"\n'),
        "rule": "inline-style",
        "context": "inline-style",
        "markup": ("src/components/AppButton.vue", "<slot />", '<img src="/arrow.svg"><slot />'),
    },
    "svelte": {
        "styles": "src/styles",
        "literal": ("src/lib/components/Button.svelte", '<a class="btn" {href}',
                    '<a class="btn" {href} style:color="#c0ffee"'),
        "rule": "inline-style",
        "context": "inline-style",
        "markup": ("src/lib/components/Button.svelte", "{@render children()}",
                   '<img src="/arrow.svg">{@render children()}'),
    },
    "astro": {
        "styles": "src/styles",
        "literal": ("src/components/Button.astro", "color: var(--btn-fg);", "color: #c0ffee;"),
        "rule": "raw-color",
        "context": "css-decl",
        "markup": ("src/components/Button.astro", "<slot />", '<img src="/arrow.svg"><slot />'),
    },
}


class StackTest(TempDirTest):
    def project(self, stack: str, plant: tuple[str, str, str] | None = None):
        """A copy of the stack's fixture with the starter's styles where its
        config names them, and one planted change."""
        root = self.tmp / stack
        shutil.copytree(STACKS / stack, root)
        shutil.copytree(STARTER, root / STACK[stack]["styles"])
        if plant:
            rel, old, new = plant
            path = root / rel
            text = path.read_bytes().decode("utf-8")
            self.assertIn(old, text, f"{stack}: the plant's anchor moved in {rel}")
            path.write_bytes(text.replace(old, new, 1).encode("utf-8"))
        return root

    def audit(self, root):
        proc = run_py("web-design-studio", "audit_design", ".", "--strict", "--json", cwd=root)
        return proc, json.loads(proc.stdout or b"[]")

    def a11y(self, root):
        proc = run_py("a11y-audit-runner", "a11y_static", ".", "--strict", "--json", cwd=root)
        return proc, json.loads(proc.stdout or b"{}").get("findings", [])

    def census(self, root, stack: str):
        """The census's literals outside the starter's own styles."""
        proc = run_py("design-token-migration", "extract_literals", ".", "--format", "json", cwd=root)
        styles = STACK[stack]["styles"] + "/"
        found = json.loads(proc.stdout or b"{}").get("literals", [])
        return proc, found, [lit for lit in found if not lit["file"].startswith(styles)]


class TheStacksRunClean(StackTest):
    def test_every_stack_has_a_fixture(self):
        self.assertEqual(sorted(p.name for p in STACKS.iterdir() if p.is_dir()), sorted(STACK))

    def test_the_audit_is_clean(self):
        for stack in STACK:
            with self.subTest(stack=stack):
                proc, findings = self.audit(self.project(stack))
                self.assertEqual((proc.returncode, findings), (0, []), output(proc))

    def test_a11y_static_is_clean(self):
        for stack in STACK:
            with self.subTest(stack=stack):
                proc, findings = self.a11y(self.project(stack))
                self.assertEqual(proc.returncode, 0, output(proc))
                self.assertEqual(findings, [])

    def test_the_census_finds_no_literal_in_the_stacks_files(self):
        for stack in STACK:
            with self.subTest(stack=stack):
                proc, found, own = self.census(self.project(stack), stack)
                self.assertEqual(proc.returncode, 0, output(proc))
                self.assertTrue(found, "the starter's own em ratios are counted")
                self.assertEqual(own, [])


class TheStacksFindWhatIsPlanted(StackTest):
    def test_the_audit_finds_the_literal(self):
        for stack, case in STACK.items():
            with self.subTest(stack=stack):
                proc, findings = self.audit(self.project(stack, case["literal"]))
                self.assertEqual(proc.returncode, 1, output(proc))
                self.assertEqual([(f["file"].replace("\\", "/"), f["rule"]) for f in findings],
                                 [(case["literal"][0], case["rule"])])

    def test_the_census_finds_the_literal(self):
        for stack, case in STACK.items():
            with self.subTest(stack=stack):
                _, _, own = self.census(self.project(stack, case["literal"]), stack)
                self.assertEqual([(lit["file"], lit["raw"], lit["context"]) for lit in own],
                                 [(case["literal"][0], "#c0ffee", case["context"])])

    def test_a11y_static_finds_the_image_without_alt(self):
        for stack, case in STACK.items():
            with self.subTest(stack=stack):
                proc, findings = self.a11y(self.project(stack, case["markup"]))
                self.assertEqual(proc.returncode, 1, output(proc))
                self.assertEqual([(f["file"].replace("\\", "/"), f["rule"]) for f in findings],
                                 [(case["markup"][0], "img-no-alt")])


class TheShellsRenderTheirPagesElsewhere(TempDirTest):
    """a11y_static's document checks on a framework's shell: the page's <main>
    comes through the outlet, and with Next.js and SvelteKit the title too."""

    def rules(self, name: str, text: str) -> list[str]:
        self.write(name, text)
        proc = run_py("a11y-audit-runner", "a11y_static", name, "--json", cwd=self.tmp)
        return sorted(f["rule"] for f in json.loads(proc.stdout)["findings"])

    def test_a_shell_with_an_outlet_leaves_main_to_its_pages(self):
        shells = {
            "app/layout.tsx": "export default function L({ children }) {\n"
                              "  return (<html lang=\"en\"><body>{children}</body></html>);\n}\n",
            "index.html": "<!doctype html><html lang=\"en\"><head><title>A</title>"
                          "<script type=\"module\" src=\"/src/main.ts\"></script></head>"
                          "<body><div id=\"app\"></div></body></html>\n",
            "src/app.html": "<!doctype html><html lang=\"en\"><head>%sveltekit.head%</head>"
                            "<body><div>%sveltekit.body%</div></body></html>\n",
            "src/layouts/Base.astro": "---\nconst { title } = Astro.props;\n---\n"
                                      "<html lang=\"en\"><head><title>{title}</title></head>"
                                      "<body><slot /></body></html>\n",
            # The attributes in either order, and the children through props (Codex on #172).
            "vite/index.html": "<!doctype html><html lang=\"en\"><head><title>A</title>"
                               "<script src=\"/src/main.ts\" type=\"module\"></script></head>"
                               "<body><div id=\"root\"></div></body></html>\n",
            "app/blog/layout.jsx": "export default function L(props) {\n"
                                "  return (<html lang=\"en\"><body>{props.children}</body></html>);\n}\n",
        }
        for name, text in shells.items():
            with self.subTest(shell=name):
                self.assertEqual(self.rules(name, text), [])

    def test_a_document_with_no_outlet_still_needs_main_and_a_title(self):
        pages = {
            "page.html": "<!doctype html><html lang=\"en\"><head></head><body><p>Hi</p></body></html>\n",
            "empty-div.html": "<!doctype html><html lang=\"en\"><head></head>"
                              "<body><div id=\"app\"></div></body></html>\n",
            "Doc.tsx": "export default function D() {\n"
                       "  return (<html lang=\"en\"><body><p>Hi</p></body></html>);\n}\n",
            "entity.html": "<!doctype html><html lang=\"en\"><head></head>"
                           "<body><p>Tom &amp; Jerry</p></body></html>\n",
            # An expression of the page's own is no outlet (Codex on #172).
            "Hello.tsx": "export default function H() {\n"
                         "  return (<html lang=\"en\"><body><p>{'hello'}</p></body></html>);\n}\n",
            "hello.astro": "<html lang=\"en\"><head></head><body><p>{'hello'}</p></body></html>\n",
            # A static page with a module script and an empty element is no mount point (Codex on #172).
            "modal.html": "<!doctype html><html lang=\"en\"><head><script type=\"module\" src=\"/a.js\">"
                          "</script></head><body><p>Hi</p><div id=\"modal\"></div></body></html>\n",
        }
        for name, text in pages.items():
            with self.subTest(page=name):
                self.assertEqual(self.rules(name, text), ["no-main-landmark", "no-title"])

    def test_a_component_or_a_named_slot_beside_the_page_is_no_outlet(self):
        # Part of the page, not the page (CodeRabbit on #172).
        pages = {
            "Shell.tsx": "export default function S() {\n"
                         "  return (<html lang=\"en\"><head><title>A</title></head>"
                         "<body><SiteHeader /><p>Welcome</p></body></html>);\n}\n",
            "named.astro": "<html lang=\"en\"><head><title>A</title></head>"
                           "<body><p>Hi</p><slot name=\"footer\" /></body></html>\n",
        }
        for name, text in pages.items():
            with self.subTest(page=name):
                self.assertEqual(self.rules(name, text), ["no-main-landmark"])

    def test_a_layout_outside_app_needs_its_title(self):
        # Only the App Router's `app/` makes `layout` a Next.js layout (Codex on #172).
        text = ("export default function L() {\n"
                "  return (<html lang=\"en\"><head></head><body><main><h1>A</h1></main></body></html>);\n}\n")
        self.assertEqual(self.rules("src/layout.tsx", text), ["no-title"])
        self.assertEqual(self.rules("app/layout.tsx", text), [])

    def test_the_metadata_api_writes_the_title(self):
        text = ("export const metadata = { title: 'A' };\n"
                "export default function P() {\n"
                "  return (<html lang=\"en\"><body><main><h1>A</h1></main></body></html>);\n}\n")
        self.assertEqual(self.rules("Root.tsx", text), [])

    def test_a_slot_names_the_link_it_fills(self):
        for name, text in {"Button.vue": "<template><a href=\"/x\"><slot /></a></template>\n",
                           "Button.astro": "<a href=\"/x\"><slot /></a>\n"}.items():
            with self.subTest(file=name):
                self.assertEqual(self.rules(name, text), [])

    def test_an_empty_link_is_still_empty(self):
        self.assertEqual(self.rules("Button.vue", "<template><a href=\"/x\"></a></template>\n"),
                         ["empty-control"])


class TheCensusReadsAShadowToken(TempDirTest):
    def literals(self, css: str) -> list[tuple[str, str]]:
        self.write("a.css", css)
        proc = run_py("design-token-migration", "extract_literals", "a.css", "--format", "json", cwd=self.tmp)
        return [(lit["raw"], lit["kind"]) for lit in json.loads(proc.stdout)["literals"]]

    def test_a_shadow_token_is_no_literal(self):
        self.assertEqual(self.literals(".a { box-shadow: var(--shadow-xs); text-shadow: var(--t); }\n"), [])

    def test_a_fallback_and_a_second_layer_are_read_part_by_part(self):
        self.assertEqual(self.literals(".a { box-shadow: var(--shadow-xs, 0 1px 2px #000); }\n"),
                         [("1px", "other-length"), ("2px", "other-length"), ("#000", "color")])
        self.assertEqual(self.literals(".a { box-shadow: var(--shadow-xs), 0 0 0 1px #f00; }\n"),
                         [("1px", "other-length"), ("#f00", "color")])

    def test_a_written_out_shadow_is_still_one_literal(self):
        self.assertEqual(self.literals(".a { box-shadow: 0 1px 2px #000; }\n"),
                         [("0 1px 2px #000", "shadow")])


if __name__ == "__main__":
    unittest.main()
