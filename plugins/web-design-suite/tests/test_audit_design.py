"""web-design-studio: audit_design.py, the suite's central gate.

Regressions covered:
- Law 2: a plain `margin-top: var(--space-16)` counted as the legal
  `calc(var(--t) * -1)` cancellation, because the check looked for the
  substring "-1" anywhere — so any token named *-1, *-10 … *-19 waved it through.
- Law 1: `font-weight: 700` was never flagged; the type check only looked for
  values with a unit.
- Law 1: a raw colour inside a border/outline shorthand other than plain
  `border` (`border-bottom: 1px solid #ccc`, `outline: 2px solid #000`) was
  never flagged, and a named colour in any shorthand (`border: 1px solid red`)
  was not either.
- Baselines: keys embedded the OS path separator, so a baseline written on
  Windows suppressed nothing on Linux CI, and vice versa.

3.1.0 (false passes found in the 3.0.1 review):
- SB-A3: any `var(--` anywhere in a value switched off every Law 1 check for
  that declaration, so `padding: var(--pad-sm) 13px` or
  `transition: opacity 300ms var(--ease-out)` passed.
- SB-A4: spacing inside @media / @container / @supports was never checked.
- PS-A4: HTML was never audited. A folder of pages passed as "clean", and an
  .html file named explicitly went to the JS checker, which ignores <style>.
  Unknown extensions (a staged README.md) were audited as JavaScript.
- A path with nothing auditable in it reported "clean" instead of saying so.
- SS-A19: a stylesheet saved with a UTF-8 BOM failed as "unlayered".
- XC-A9: baseline keys depended on how the path was spelled, so auditing
  `src/` by its absolute path resurrected every baselined finding.
- The clean message claimed "all nine laws hold"; the script checks L1–L6.
- `background: url(icons.svg#add)` was a "hardcoded colour": the fragment
  `#add` reads as hex.

3.3.0 (SB-A9, false passes that were still open):
- `//` was a comment in plain CSS, so `url(https://…)` lost its closing
  parenthesis and nothing after it was checked; a custom property holding an
  address hid the rest of its line.
- A rule after a closed @layer block was never reported as unlayered.
- A root-level components/ folder, the common Next.js layout, did not hold
  component files, so Law 2 was skipped.

3.3.0 (SB-A24, the audit on Sass):
- A partial holding only mixins failed as unlayered, because a mixin holds
  rules.
- A Sass variable holding a literal (`$card-padding: 24px`) passed.
- The braces of an interpolation (`.card-#{$name}`) closed the layer around
  them, so the next rule was unlayered.
- Indented Sass (.sass) has no braces to follow and was reported clean.
"""
from __future__ import annotations

import json
import re
import unittest

from wds_support import SKILLS, TempDirTest, output, run_py


class AuditDesign(TempDirTest):

    def audit(self, css, *args):
        path = self.write("src/components/card.css", "@layer components {\n" + css + "\n}\n")
        proc = run_py("web-design-studio", "audit_design", "src", "--json", *args, cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return path, json.loads(proc.stdout)

    def rules(self, css):
        return {(f["law"], f["rule"]) for f in self.audit(css)[1]}

    def test_law2_margin_with_a_token_named_like_minus_one_is_still_a_child_margin(self):
        for token in ("--space-1", "--space-10", "--space-16"):
            with self.subTest(token=token):
                self.assertIn(("L2", "child-margin"),
                              self.rules(f".card {{ margin-top: var({token}); }}"))

    def test_law2_real_token_cancellation_stays_legal(self):
        for value in ("calc(var(--space-4) * -1)", "calc(var(--space-16)*-1)",
                      "calc(-1 * var(--space-4))"):
            with self.subTest(value=value):
                self.assertNotIn(("L2", "child-margin"),
                                 self.rules(f".card {{ margin-top: {value}; }}"))

    def test_law1_numeric_font_weight_is_flagged(self):
        self.assertTrue(any(law == "L1" for law, _ in self.rules(".card { font-weight: 700; }")))
        self.assertEqual(self.rules(".card { font-weight: inherit; }"), set())

    def test_law1_colours_inside_border_and_outline_shorthands_are_flagged(self):
        cases = {
            "border-bottom: 1px solid #cccccc": "raw-color",
            "outline: 2px solid rgb(0 0 0)": "raw-color",
            "border-inline-start: 4px solid #333": "raw-color",
            "column-rule: 1px solid #ddd": "raw-color",
            "border: 1px solid red": "named-color",
            "outline: 2px solid navy": "named-color",
        }
        for decl, rule in cases.items():
            with self.subTest(decl=decl):
                self.assertIn(("L1", rule), self.rules(f".card {{ {decl}; }}"))

    def test_law1_tokenised_or_keyword_shorthands_stay_clean(self):
        for decl in ("border-bottom: 1px solid var(--border-default)",
                     "border: 1px solid transparent", "outline: none"):
            with self.subTest(decl=decl):
                found = {r for law, r in self.rules(f".card {{ {decl}; }}") if law == "L1"}
                self.assertFalse(found & {"raw-color", "named-color"}, decl)

    def test_a_baseline_works_whichever_os_wrote_it(self):
        css = ".card { padding: 13px; }"
        self.audit(css)                                   # creates the file
        baseline = self.tmp / "baseline.json"
        proc = run_py("web-design-studio", "audit_design", "src", "--write-baseline", baseline,
                      cwd=self.tmp)
        keys = json.loads(baseline.read_text(encoding="utf-8"))
        self.assertTrue(keys, output(proc))
        for sep in ("/", "\\"):                           # as Linux/macOS, as Windows
            with self.subTest(separator=sep):
                other = [k.split("|", 1)[0].replace("\\", "/").replace("/", sep) + "|" + k.split("|", 1)[1]
                         for k in keys]
                variant = self.write(f"baseline{ord(sep)}.json", json.dumps(other))
                proc = run_py("web-design-studio", "audit_design", "src", "--json",
                              "--baseline", variant, cwd=self.tmp)
                self.assertEqual(json.loads(proc.stdout), [], output(proc))
                self.assertEqual(proc.returncode, 0)


class AuditPrecision(TempDirTest):
    """A gate that says "clean" about code it never checked is worse than no gate."""

    audit = AuditDesign.audit
    rules = AuditDesign.rules

    def l1(self, css):
        return {r for law, r in self.rules(css) if law == "L1"}

    def test_a_var_reference_does_not_hide_a_literal_beside_it(self):
        cases = {
            "padding: var(--pad-block-sm) 13px": "raw-spacing",
            "transition: opacity 300ms var(--ease-out)": "raw-duration",
            "box-shadow: 0 1px 2px #000, var(--elevation-card)": "raw-shadow",
            "font: 600 14px/1.2 var(--font-sans)": "raw-type",
            "background: color-mix(in oklch, var(--bg-accent) 50%, #ff0000)": "raw-color",
            "border-radius: var(--radius-md) 4px": "raw-radius",
            "padding: calc(var(--pad-card) + 3px)": "raw-spacing",
        }
        for decl, rule in cases.items():
            with self.subTest(decl=decl):
                self.assertIn(rule, self.l1(f".card {{ {decl}; }}"))

    def test_fully_tokenised_values_stay_clean(self):
        for decl in ("padding: var(--pad-block-sm) var(--pad-inline-md)",
                     "padding: calc(var(--pad-card) * 2)",
                     "transition: opacity var(--motion-hover)",
                     "box-shadow: var(--elevation-focus), var(--elevation-card)",
                     "background: color-mix(in oklch, var(--bg-accent) 50%, transparent)",
                     "color: oklch(from var(--fg-default) l c h / 0.5)",
                     "color: var(--fg-muted, #666666)",
                     "border-radius: calc(var(--radius-lg) - var(--pad-card))"):
            with self.subTest(decl=decl):
                self.assertEqual(self.l1(f".card {{ {decl}; }}"), set())

    def test_spacing_inside_media_container_and_supports_is_checked(self):
        for wrapper in ("@media (width >= 48rem)", "@container (inline-size > 30rem)",
                        "@supports (display: grid)"):
            with self.subTest(wrapper=wrapper):
                self.assertIn("raw-spacing",
                              self.l1(f"{wrapper} {{ .card {{ padding: 7px 9px; }} }}"))

    def test_html_style_blocks_and_style_attributes_are_audited(self):
        page = ('<!doctype html><html lang="en"><head><title>t</title>\n'
                '<style>.hero{margin-top:37px;color:#ff0000;font-size:13px !important}\n'
                '#buy{padding:7px}</style></head>\n'
                '<body><main><p style="margin:13px;color:#f00">x</p></main></body></html>\n')
        self.write("site/index.html", page)
        for target in ("site", "site/index.html"):
            with self.subTest(target=target):
                proc = run_py("web-design-studio", "audit_design", target, "--json", cwd=self.tmp)
                rules = {(f["law"], f["rule"]) for f in json.loads(proc.stdout)}
                self.assertEqual(proc.returncode, 1, output(proc))
                for expected in (("L1", "raw-spacing"), ("L1", "raw-color"), ("L1", "raw-type"),
                                 ("L5", "important"), ("L5", "id-selector"),
                                 ("L4", "inline-style")):
                    self.assertIn(expected, rules)

    def test_single_file_component_styles_are_audited(self):
        for name in ("Card.vue", "Card.svelte", "Card.astro"):
            with self.subTest(name=name):
                self.write(f"sfc/{name}", "<template><div class='card'>x</div></template>\n"
                           "<style>\n@layer components {\n  .card { padding: 13px; }\n}\n</style>\n")
                proc = run_py("web-design-studio", "audit_design", f"sfc/{name}", "--json",
                              cwd=self.tmp)
                found = json.loads(proc.stdout)
                self.assertIn(("L1", "raw-spacing", 4),
                              {(f["law"], f["rule"], f["line"]) for f in found}, output(proc))

    def test_a_clean_page_and_an_html_email_pass(self):
        self.write("ok/index.html", "<!doctype html><html lang='en'><title>t</title><style>\n"
                   "@layer components { .hero { padding: var(--pad-card); } }\n</style>"
                   "<p style='--progress: 40%'>x</p></html>\n")
        self.write("ok/receipt.html", "<!doctype html><html xmlns:v='urn:schemas-microsoft-com:vml'>"
                   "<!--[if mso]><style>td{padding:13px}</style><![endif]-->"
                   "<td style='padding:24px;color:#333333'>x</td></html>\n")
        proc = run_py("web-design-studio", "audit_design", "ok", "--strict", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))

    def test_files_it_cannot_audit_are_skipped_not_misread(self):
        self.write("docs/guide.md", 'Bad: <div className="p-[13px]" style={{color: "#ff0000"}}>\n')
        proc = run_py("web-design-studio", "audit_design", "docs/guide.md", "--strict",
                      cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertIn("skipped", output(proc).lower())

    def test_a_folder_with_nothing_auditable_is_not_reported_clean(self):
        self.write("templates/page.twig", "<p style='margin:13px'>x</p>\n")
        proc = run_py("web-design-studio", "audit_design", "templates", cwd=self.tmp)
        self.assertEqual(proc.returncode, 2, output(proc))
        self.assertIn("0 files", output(proc))

    def test_a_stylesheet_saved_with_a_bom_is_not_unlayered(self):
        self.write("bom/a.css", "﻿@layer components {\n  .a { color: var(--fg-default); }\n}\n")
        proc = run_py("web-design-studio", "audit_design", "bom", "--strict", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))

    def test_a_baseline_matches_however_the_path_is_spelled(self):
        self.audit(".card { padding: 13px; }")
        proc = run_py("web-design-studio", "audit_design", "src/", "--write-baseline",
                      ".design-baseline.json", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        (self.tmp / "sub").mkdir()
        runs = {"absolute path": (str(self.tmp / "src"), self.tmp, []),
                "./src": ("./src", self.tmp, []),
                "from a subfolder": ("../src", self.tmp / "sub",
                                     ["--baseline", "../.design-baseline.json"])}
        for label, (target, cwd, extra) in runs.items():
            with self.subTest(label):
                proc = run_py("web-design-studio", "audit_design", target, "--json", *extra, cwd=cwd)
                self.assertEqual(json.loads(proc.stdout), [], output(proc))
                self.assertEqual(proc.returncode, 0)

    def test_a_named_baseline_that_does_not_exist_is_reported(self):
        self.audit(".card { padding: var(--pad-card); }")
        proc = run_py("web-design-studio", "audit_design", "src", "--baseline", "nope.json",
                      cwd=self.tmp)
        self.assertIn("nope.json", output(proc))

    def test_literal_tailwind_utilities_the_theme_cannot_remove_are_flagged(self):
        """SB-A5: these still generate with `--*: initial`, and nothing flagged them."""
        self.write("src/Holes.tsx",
                   'export const H = () => <div className="duration-300 delay-150 z-50 '
                   'border-2 ring-2 underline-offset-2 bg-accent/37 p-(--space-6) '
                   'space-y-related">x</div>;\n')
        proc = run_py("web-design-studio", "audit_design", "src/Holes.tsx", "--json", cwd=self.tmp)
        found = [f["message"] for f in json.loads(proc.stdout)]
        for cls in ("duration-300", "delay-150", "z-50", "border-2", "ring-2",
                    "underline-offset-2", "bg-accent/37", "(--space-6)", "space-y-related"):
            with self.subTest(cls=cls):
                self.assertTrue(any(cls in m for m in found), found)
        roles = self.write("src/Roles.tsx",
                           'export const R = () => <div className="motion-hover z-modal '
                           'border-stroke focus-ring p-card p-(--pad-card) bg-surface '
                           'w-1/2 gap-related">x</div>;\n')
        proc = run_py("web-design-studio", "audit_design", roles, "--json", cwd=self.tmp)
        self.assertEqual(json.loads(proc.stdout), [], output(proc))

    def test_the_eslint_config_bans_the_same_classes(self):
        """SB-A5: the design ESLint config has matching patterns (checked here as
        regexes, so the test needs no node_modules)."""
        import re
        config = (SKILLS / "web-design-studio" / "assets" / "configs" /
                  "eslint.design.config.mjs").read_text(encoding="utf-8")

        def pattern(name):
            m = re.search(rf"const {name} =\s*\n?\s*/(.+?)/;\n", config)
            self.assertIsNotNone(m, f"{name} is not declared")
            return re.compile(m.group(1))

        cases = {"LITERAL_UTILITY": ("duration-300", "z-50", "-z-10", "border-2", "ring-2",
                                     "outline-offset-2"),
                 "OPACITY_MODIFIER": ("bg-accent/37", "text-fg/80"),
                 "TIER1_SHORTHAND": ("p-(--space-6)", "bg-(--neutral-800)")}
        for name, bad in cases.items():
            rx = pattern(name)
            for cls in bad:
                with self.subTest(pattern=name, cls=cls):
                    self.assertTrue(rx.search(f" {cls} "))
            for good in ("motion-hover", "z-modal", "border-stroke", "w-1/2",
                         "p-(--pad-card)", "p-(--space-section)"):
                with self.subTest(pattern=name, good=good):
                    self.assertFalse(rx.search(f" {good} "))

    def test_the_clean_message_names_only_the_laws_it_checks(self):
        self.audit(".card { padding: var(--pad-card); }")
        proc = run_py("web-design-studio", "audit_design", "src", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertNotIn("nine laws", output(proc))
        self.assertIn("L1–L6", output(proc))

    def test_weight_primitives_may_be_read_directly(self):
        """SS-A10: the hierarchy method sets weight without changing size, and no
        --type-* shorthand can do that, so --weight-* has no role layer."""
        self.assertNotIn(("L6", "tier1-leak"), self.rules(".card { font-weight: var(--weight-semibold); }"))

    def test_a_zero_margin_claims_no_space(self):
        """SB-A14: a child resetting its margin to 0 asserts no space, and
        stylelint already allowed it; the audit called it an outer margin."""
        for value in ("0", "0px", "0 auto", "0 0 0 0"):
            with self.subTest(value=value):
                self.assertNotIn(("L2", "child-margin"),
                                 self.rules(f".card__media {{ margin-block-end: {value}; }}"))
        self.assertIn(("L2", "child-margin"),
                      self.rules(".card__media { margin-block-end: var(--gap-related); }"))

    def test_a_pragma_wrapped_over_two_lines_covers_the_next_declaration(self):
        """Comments were keyed by the line they START on, so a wrapped pragma
        ignored its own second line and the finding it argued stayed."""
        css = (".quote {\n"
               "  /* design-audit-ignore-next-line: L1 -- optical: the leading band,\n"
               "     trimmed until text-box-trim lands */\n"
               "  padding-block: calc(var(--pad-card) - 0.3em);\n"
               "}")
        self.assertNotIn("raw-spacing", self.l1(css))
        self.assertIn("raw-spacing", self.l1(css.replace("design-audit-ignore-next-line", "note")))

    def test_nesting_is_counted_below_the_top_level_rule(self):
        """SB-A14: the audit counted the top-level rule as depth 1, so the
        references' own `.card { & .title { &:hover {} } }` ("depth 2, the
        edge") failed; stylelint counts nesting below it."""
        for css in (".card { & .title { &:hover { color: var(--fg-strong); } } }",
                    ".card { & .title { & .icon { :hover { color: var(--fg-strong); } } } }"):
            with self.subTest(css=css):
                self.assertNotIn(("L5", "nesting-depth"), self.rules(css))
        self.assertIn(("L5", "nesting-depth"),
                      self.rules(".a { & .b { & .c { & .d { color: var(--fg-strong); } } } }"))

    def test_generated_content_may_space_itself_from_its_text(self):
        """A `::after` label's margin is decided in the component's own rule."""
        self.assertNotIn(("L2", "child-margin"), self.rules(
            '.preset__name::after { content: "held"; margin-inline-start: var(--gap-fused); }'))
        self.assertIn(("L2", "child-margin"),
                      self.rules(".preset__name { margin-inline-start: var(--gap-fused); }"))

    def test_motion_longhands_may_read_the_primitives(self):
        """A --motion-* pair only fits a shorthand. View transitions and
        scroll-driven animations must set the longhands, and were warned for it."""
        longhands = self.rules("::view-transition-old(hero) { animation-duration: var(--dur-slow); "
                               "animation-timing-function: var(--ease-in-out); }")
        self.assertNotIn(("L6", "tier1-motion"), longhands)
        self.assertIn(("L6", "tier1-motion"),
                      self.rules(".x { transition: opacity var(--dur-fast) var(--ease-out); }"))

    def test_a_url_fragment_is_not_a_colour(self):
        self.assertNotIn("raw-color", self.l1(".mask { mask-image: url(#fade); "
                                              "background: url(icons.svg#add) no-repeat; }"))

    def found(self, root: str) -> list[tuple[str, str, int]]:
        proc = run_py("web-design-studio", "audit_design", root, "--json", cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return sorted((f["law"], f["rule"], f["line"]) for f in json.loads(proc.stdout))

    def test_a_url_does_not_hide_the_rest_of_the_file(self):
        # SB-A9 (a): `//` was a comment in plain CSS, so `url(https://…)` lost
        # its closing parenthesis and the scanner read nothing after it, and a
        # custom property holding an address hid the rest of its line.
        for value in ("url(https://cdn.example.com/hero.svg)", "url( //cdn.example.com/hero.svg )",
                      'url("https://cdn.example.com/hero.svg")', "https://example.com/terms"):
            prop = "--terms" if value.startswith("https") else "background-image"
            with self.subTest(value=value):
                self.write("src/components/card.css",
                           "@layer components {\n"
                           f"  .hero {{ {prop}: {value}; z-index: 9999; }}\n"
                           "  .after-url { padding: 13px; color: #ff0000; }\n"
                           "}\n")
                self.assertEqual([("L1", "raw-color", 3), ("L1", "raw-spacing", 3), ("L1", "raw-z-index", 2)],
                                 self.found("src"))

    def test_line_comments_stay_comments_where_they_are_comments(self):
        # SB-A9 (a): in Sass, Less and a styled template, `//` still starts a
        # comment, except inside url().
        decls = ("    // padding: 13px;\n"
                 "    background-image: url(//cdn.example.com/card.svg);\n"
                 "    color: #ff0000;\n")
        self.write("scss/components/card.scss", "@layer components {\n  .card {\n" + decls + "  }\n}\n")
        self.write("less/components/card.less", "@layer components {\n  .card {\n" + decls + "  }\n}\n")
        self.write("tsx/components/Card.tsx", "import styled from 'styled-components';\n"
                                              "export const Card = styled.div`\n" + decls + "`;\n")
        for root in ("scss", "less", "tsx"):
            with self.subTest(root=root):
                self.assertEqual([("L1", "raw-color", 5)], self.found(root))

    def test_an_escaped_parenthesis_does_not_end_a_url(self):
        # `\)` inside an unquoted url() is part of the address, so a `//` after
        # it is not a Sass comment (CodeRabbit on PR #5).
        self.write("scss/components/card.scss",
                   "@layer components {\n"
                   "  .card { background: url(//cdn.example.com/a\\)//b.svg); color: #ff0000; }\n"
                   "}\n")
        self.assertEqual([("L1", "raw-color", 2)], self.found("scss"))

    def test_a_sass_expression_in_url_keeps_its_comments(self):
        # In Sass, url() may hold an expression rather than an address; a
        # comment in it is still a comment (CodeRabbit on PR #6).
        self.write("scss/components/card.scss",
                   '$asset: "hero.svg";\n'
                   "@layer components {\n"
                   '  .card { background: url($asset /* " */); color: #ff0000; }\n'
                   "}\n")
        self.assertEqual([("L1", "raw-color", 3)], self.found("scss"))

    def test_a_rule_after_a_closed_layer_is_unlayered(self):
        # SB-A9 (b): the audit never left a layer once it had entered one.
        self.write("src/components/card.css",
                   "@layer components {\n  .a { color: var(--fg-default); }\n}\n\n"
                   ".b { color: var(--fg-default); }\n")
        self.write("src/components/media.css",
                   "@layer components {\n  @media (width >= 48rem) { .c { color: var(--fg-default); } }\n}\n"
                   "@media (width >= 48rem) { .d { color: var(--fg-default); } }\n")
        self.assertEqual([("L5", "unlayered", 4), ("L5", "unlayered", 5)], self.found("src"))

    def test_keyframes_outside_a_layer_are_not_unlayered_rules(self):
        # A keyframe is not a style rule. The references and the scaffold keep
        # @keyframes beside the rules that use them, outside any layer.
        self.write("motion/components/spinner.css",
                   "@layer components {\n  .spinner { color: var(--fg-default); }\n}\n\n"
                   "@keyframes spin { to { rotate: 1turn; } }\n")
        self.write("motion/components/keyframes.css", "@-webkit-keyframes fade { from { opacity: 0; } }\n")
        self.assertEqual([], self.found("motion"))

    def test_a_root_level_components_folder_holds_components(self):
        # SB-A9 (c): `components/card.css` at the project root, the common
        # Next.js layout, was not a component file, so Law 2 was skipped.
        self.write("components/card.css",
                   "@layer components {\n  .card { margin-block-start: var(--gap-grouped); }\n}\n")
        self.assertEqual([("L2", "child-margin", 2)], self.found("components"))

    def test_the_references_sass_partial_passes(self):
        # SB-A24: `_mq.scss` from stack-css-modules §9 emits no CSS, and failed
        # as unlayered because its mixins hold rules.
        doc = (SKILLS / "web-design-studio" / "references" / "stack-css-modules.md").read_text(encoding="utf-8")
        partial = re.search(r"```scss\n(// src/styles/_mq\.scss.*?)```", doc, re.S)
        self.assertIsNotNone(partial, "§9 no longer shows _mq.scss")
        self.write("src/styles/_mq.scss", partial.group(1))
        self.assertEqual([], self.found("src"))

    def test_a_mixin_is_checked_where_it_is_included(self):
        # The control for the test above: a mixin's body is still read for
        # literals, and the rule that includes it still needs a layer.
        self.write("src/styles/_card.scss", "@mixin card {\n  & .title { padding: 13px; }\n}\n")
        self.write("src/styles/card.scss", "@use 'card' as *;\n.card { @include card; }\n")
        self.assertEqual([("L1", "raw-spacing", 2), ("L5", "unlayered", 2)], self.found("src"))

    def test_a_sass_variable_holding_a_literal_is_refused(self):
        # SB-A24: `$card-padding: 24px; … padding: $card-padding`, which §9
        # bans, passed clean.
        module = ("$card-padding: 24px;\n"
                  "$card-bg: #ffffff;\n"
                  "$card-fade: 200ms !default;\n"
                  "$bp-md: 48rem;\n"
                  "$columns: 12;\n"
                  "@layer components {\n"
                  "  .card { padding: $card-padding; background: $card-bg; transition: opacity $card-fade; }\n"
                  "}\n")
        self.write("src/components/Card.module.scss", module)
        self.write("src/styles/tokens.scss", module)         # the token file is where literals live
        self.assertEqual([("L1", "sass-literal", 1), ("L1", "sass-literal", 2), ("L1", "sass-literal", 3)],
                         self.found("src"))

    def test_sass_interpolation_opens_no_rule(self):
        # Found with SB-A24: the braces of `#{$name}` closed the layer around
        # them, so the next rule was unlayered; in a value they opened a rule
        # and the declaration was never read.
        self.write("src/components/card.scss",
                   "@layer components {\n"
                   "  @each $name in (sm, lg) {\n"
                   "    .card-#{$name} { padding: var(--pad-card); }\n"
                   "  }\n"
                   "  .card { inline-size: calc(100% - #{$gutter}); margin-inline: #{$gutter}; padding: 13px; }\n"
                   "}\n")
        self.assertEqual([("L1", "raw-spacing", 5), ("L2", "child-margin", 5)], self.found("src"))

    def test_a_brace_in_a_string_does_not_extend_an_interpolation(self):
        # CodeRabbit on PR #7: a quoted `{` inside `#{…}` was counted as
        # nesting, so the interpolation swallowed the rest of the file.
        self.write("src/components/card.scss",
                   "@layer components {\n"
                   '  #{map.get(("{": ".card"), "{")} {\n'
                   "    padding: 13px;\n"
                   "  }\n"
                   "}\n")
        self.assertEqual([("L1", "raw-spacing", 3)], self.found("src"))

    def test_a_zero_with_a_unit_does_not_hide_the_length_after_it(self):
        # CodeRabbit on PR #7, and older than Sass: only the first length in a
        # value was looked at, so `0px 13px` passed.
        self.write("src/components/card.css",
                   "@layer components {\n"
                   "  .card { padding: 0px 13px; }\n"
                   "  .card__media { padding: 0px 0rem; }\n"
                   "}\n")
        self.assertEqual([("L1", "raw-spacing", 2)], self.found("src"))

    def test_indented_sass_is_skipped_not_passed(self):
        # Found with SB-A24: the scanner follows braces and indented Sass has
        # none, so a .sass file full of literals was reported clean.
        self.write("ind/components/card.sass", ".card\n  padding: 24px\n  color: #ff0000\n")
        proc = run_py("web-design-studio", "audit_design", "ind", "--strict", cwd=self.tmp)
        self.assertEqual(proc.returncode, 2, output(proc))
        self.assertIn("indented Sass", output(proc))
        self.assertIn("0 files", output(proc))
        # Beside a file the audit does read, it is listed and the rest is audited.
        self.write("ind/components/card.scss", "@layer components {\n  .card { padding: var(--pad-card); }\n}\n")
        proc = run_py("web-design-studio", "audit_design", "ind", "--strict", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertIn("skipped 1 file(s) (indented Sass", output(proc))
        self.assertIn("across 1 file(s)", output(proc))


class JsxClassesAndCssInJs(TempDirTest):
    """SB-A10 (rest), 3.2.0: the audit read only `className="…"` strings, and
    exempted whole families of arbitrary values. A component whose classes
    all went through cn() or cva(), or whose styles lived in a
    styled-components template, passed as clean."""

    def findings(self, tsx: str):
        path = self.write("src/components/Thing.tsx", tsx)
        proc = run_py("web-design-studio", "audit_design", path.parent, "--json", cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        data = json.loads(proc.stdout)
        return data["findings"] if isinstance(data, dict) else data

    def rules(self, tsx: str):
        return [(f["rule"], f["line"]) for f in self.findings(tsx)]

    def test_class_helper_arguments_are_read(self):
        found = self.findings(
            "import { cva } from 'class-variance-authority';\n"
            "const button = cva('inline-flex p-[13px]', {\n"
            "  variants: { size: { sm: 'gap-[7px]', md: 'gap-related' } },\n"
            "});\n"
            "export const T = ({ on }) => (\n"
            "  <div className={cn('flex', on && 'm-[3px]', clsx({ 'h-[41px]': on }))} />\n"
            ");\n")
        flagged = {f["message"].split("`")[1] for f in found if f["rule"] == "tw-arbitrary"}
        self.assertEqual(flagged, {"p-[13px]", "gap-[7px]", "m-[3px]", "h-[41px]"})

    def test_every_arbitrary_value_is_refused_but_variants_and_images(self):
        refused = self.findings(
            'export const T = () => <div className="grid-cols-[1fr_2fr] aspect-[4/3] bg-[#e8440a]" />;\n')
        self.assertEqual({f["message"].split("`")[1] for f in refused if f["rule"] == "tw-arbitrary"},
                         {"grid-cols-[1fr_2fr]", "aspect-[4/3]", "bg-[#e8440a]"})
        allowed = self.findings(
            'export const T = () => <div className="data-[state=open]:bg-surface '
            "aria-[expanded=true]:bg-hover bg-[url(/hero.jpg)] before:content-[''] "
            'group-[.is-open]:p-card" />;\n')
        self.assertEqual([f for f in allowed if f["rule"] == "tw-arbitrary"], [])

    def test_an_arbitrary_property_is_refused(self):
        self.assertIn("tw-arbitrary-property", [r for r, _ in self.rules(
            'export const T = () => <span className="[padding:13px] [--gap:4px]" />;\n')])

    def test_the_v4_important_suffix_is_refused(self):
        self.assertIn("tw-important", [r for r, _ in self.rules(
            'export const T = () => <span className="p-card!" />;\n')])

    def test_a_styled_template_is_audited_as_component_css(self):
        found = self.rules(
            "import styled from 'styled-components';\n"
            "const Title = styled.h2`\n"
            "  color: #ff0000;\n"
            "  padding: ${(p) => p.pad};\n"
            "  margin-top: 13px;\n"
            "`;\n"
            "export const T = () => <Title>t</Title>;\n")
        lines = {rule: line for rule, line in found}
        self.assertEqual(lines.get("raw-color"), 3, found)
        self.assertTrue(any(line == 5 for _, line in found), found)      # the 13px margin
        self.assertFalse(any(line == 4 for _, line in found), found)     # an interpolation is not a literal

    def test_clean_helpers_and_templates_stay_clean(self):
        self.assertEqual(self.findings(
            "import styled from 'styled-components';\n"
            "const Box = styled.div`\n  padding: var(--pad-card);\n  color: var(--fg-default);\n`;\n"
            "export const T = ({ on }) => (\n"
            "  <Box className={cn('p-card', on && 'gap-related', { 'bg-surface': on })} />\n"
            ");\n"), [])


if __name__ == "__main__":
    unittest.main()
