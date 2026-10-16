"""Regression tests for confirmed bugs in content-model-to-ui, a11y-audit-runner
and component-state-matrix. Standard library unittest only.

Regressions covered:
- CONT-1: introspect_schema.py's nullable check was a substring test over the
  whole column-modifier text, so a `NOT NULL` written inside an inline CHECK
  expression (not a top-level modifier) wrongly made a nullable column required.
- CONT-2: introspect_schema.py picked `inline-subtable` for a one-to-many
  relationship from `ON DELETE CASCADE` alone. SKILL.md defines an owned child
  as CASCADE *and* no title of its own, so a named cascade child (e.g. `users`
  under `organizations`) wrongly got embedded instead of linking to its own
  screens.
- CONT-3: the scaffolded Button.module.css read `var(--dur-slower)` directly
  inside `prefers-reduced-motion`, which web-design-studio's audit_design.py
  --strict flags as L6 tier1-motion, contradicting SKILL.md's "the scaffold is
  built to exit clean on a fresh run".
- GATE-1: a11y_static.py recorded that a JSX spread ({...props}) was present
  but never consulted it, so it raised control-no-label / img-no-alt /
  empty-control on elements whose spread could plausibly supply the missing
  attribute — contradicting the documented "present but unknowable" treatment
  of dynamic JSX attributes.
- CONT-4: the scaffolded shared ui/Control.tsx primitives spread props onto
  their native elements, so a11y_static's false positives on those primitives
  are resolved by the GATE-1 fix; verified end-to-end here rather than by a
  separate code change.
- CSM-1: generate_matrix.py's manifest guard accepted a template with
  `{content}` but no `{attrs}`, so every state/variant/size cell rendered
  identically while the coverage line reported nothing wrong.

3.1.0:
- XC-A6: a11y_static recomputed every control's ancestors and the page's
  label-for ids for EACH form control, and counted each tag's line from the
  top of the file, so a 4,000-row page took ~46 s and a 2.8 MB page did not
  finish.
- GT-A4: a file named explicitly was audited as markup whatever it was, so a
  hook that passes every staged file failed commits on README.md or render.py.
- DL-A1: the credential rule matched a short list of exact names, although the
  docs promise `*_token`, `*_hash`, `*_secret` patterns — so `api_token`,
  `reset_token`, `webhook_secret` and `token_hash` were displayed and editable.
- DL-A2: columns that carry authority (`role`, `is_admin`, `credits`,
  `org_id`, `owner_id`, `plan`, and a profile's `id` that references
  auth.users) were editable by default and in the generated Draft type, so a
  profile form wired to `.update(draft)` let users promote themselves.
"""
from __future__ import annotations

import json
import re
import time
import unittest

from wds_support import SKILLS, TempDirTest, output, run_py


class NullableFromTopLevelNotNull(TempDirTest):
    """CONT-1: only a top-level NOT NULL should make a column required."""

    def model(self, ddl):
        self.write("schema.sql", ddl)
        proc = run_py("content-model-to-ui", "introspect_schema",
                      "schema.sql", "-o", "model.json", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        return json.loads((self.tmp / "model.json").read_text(encoding="utf-8"))

    def column(self, model, table, name):
        t = next(t for t in model["tables"] if t["name"] == table)
        return next(c for c in t["columns"] if c["name"] == name)

    def test_not_null_inside_a_check_expression_does_not_make_column_required(self):
        model = self.model(
            "CREATE TABLE posts (\n"
            "    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),\n"
            "    status text NOT NULL DEFAULT 'draft',\n"
            "    published_at timestamptz CHECK "
            "(published_at IS NOT NULL OR status = 'draft')\n"
            ");\n")
        self.assertTrue(self.column(model, "posts", "published_at")["nullable"])

    def test_a_real_top_level_not_null_is_still_required(self):
        """Guard: the common case must keep working after the fix."""
        model = self.model(
            "CREATE TABLE posts (\n"
            "    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),\n"
            "    status text NOT NULL DEFAULT 'draft'\n"
            ");\n")
        self.assertFalse(self.column(model, "posts", "status")["nullable"])

    def test_top_level_not_null_after_a_check_clause_is_still_required(self):
        """Guard: NOT NULL genuinely outside the CHECK's parens still counts."""
        model = self.model(
            "CREATE TABLE posts (\n"
            "    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),\n"
            "    slug text CHECK (slug <> '') NOT NULL\n"
            ");\n")
        self.assertFalse(self.column(model, "posts", "slug")["nullable"])


class OwnedChildNeedsNoTitleToo(TempDirTest):
    """CONT-2: a one-to-many child is "owned" (inline-subtable) only when it
    is ALSO title-less; ON DELETE CASCADE alone is not enough."""

    def model(self, ddl):
        self.write("schema.sql", ddl)
        proc = run_py("content-model-to-ui", "introspect_schema",
                      "schema.sql", "-o", "model.json", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        return json.loads((self.tmp / "model.json").read_text(encoding="utf-8"))

    def one_to_many_control(self, model, parent, child):
        t = next(t for t in model["tables"] if t["name"] == parent)
        rel = next(r for r in t["relationships"]
                  if r["kind"] == "one-to-many" and r["to"] == child)
        return rel["control"]

    def test_cascade_child_with_a_name_of_its_own_is_not_embedded(self):
        model = self.model(
            "CREATE TABLE organizations (\n"
            "    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),\n"
            "    name text NOT NULL\n"
            ");\n"
            "CREATE TABLE users (\n"
            "    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),\n"
            "    organization_id uuid NOT NULL REFERENCES organizations(id) "
            "ON DELETE CASCADE,\n"
            "    full_name text,\n"
            "    email text\n"
            ");\n")
        control = self.one_to_many_control(model, "organizations", "users")
        self.assertNotEqual(control, "inline-subtable")
        self.assertEqual(control, "linked-list")

    def test_cascade_child_with_no_title_stays_embedded(self):
        """Guard: a genuinely owned child (no title) keeps its inline control."""
        model = self.model(
            "CREATE TABLE orders (\n"
            "    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),\n"
            "    total_cents integer NOT NULL\n"
            ");\n"
            "CREATE TABLE order_items (\n"
            "    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),\n"
            "    order_id uuid NOT NULL REFERENCES orders(id) ON DELETE CASCADE,\n"
            "    quantity integer NOT NULL,\n"
            "    unit_price_cents integer NOT NULL\n"
            ");\n")
        control = self.one_to_many_control(model, "orders", "order_items")
        self.assertEqual(control, "inline-subtable")


class ScaffoldAuditsClean(TempDirTest):
    """CONT-3 + CONT-4: a fresh scaffold (default css-modules stack) must
    exit clean on both downstream gates, per SKILL.md's "the scaffold is
    built to exit clean on a fresh run"."""

    def setUp(self):
        super().setUp()
        self.write(
            "schema.sql",
            "CREATE TABLE posts (\n"
            "    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),\n"
            "    title text NOT NULL,\n"
            "    body text,\n"
            "    is_featured boolean NOT NULL DEFAULT false,\n"
            "    created_at timestamptz NOT NULL DEFAULT now()\n"
            ");\n")
        proc = run_py("content-model-to-ui", "introspect_schema",
                      "schema.sql", "-o", "model.json", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        proc = run_py("content-model-to-ui", "scaffold_ui",
                      "model.json", "--out", "src", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))

    def test_audit_design_strict_is_clean(self):
        """CONT-3: no L6 tier1-motion (or any other) finding on the scaffold."""
        proc = run_py("web-design-studio", "audit_design", "src", "--strict",
                      "--json", cwd=self.tmp)
        findings = json.loads(proc.stdout)
        self.assertEqual(proc.returncode, 0,
                         f"{output(proc)}\n{json.dumps(findings, indent=2)}")

    def test_a11y_static_ui_kit_is_clean(self):
        """CONT-4: the shared ui/ primitives (which spread props) raise no
        control-no-label / img-no-alt / empty-control false positives."""
        proc = run_py("a11y-audit-runner", "a11y_static", "src/ui", "--json",
                      cwd=self.tmp)
        report = json.loads(proc.stdout)
        self.assertEqual(report["errors"], 0,
                         f"{output(proc)}\n{json.dumps(report, indent=2)}")


class JsxSpreadIsPresentButUnknowable(TempDirTest):
    """GATE-1: a spread may supply any attribute, so the absence-based
    findings must not fire on an element that carries one — while still
    firing normally when there is no spread to explain the absence."""

    def findings(self, jsx):
        self.write("Widget.tsx", jsx)
        proc = run_py("a11y-audit-runner", "a11y_static", "Widget.tsx",
                      "--json", cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return {f["rule"] for f in json.loads(proc.stdout)["findings"]}

    def test_spread_input_is_not_flagged_control_no_label(self):
        found = self.findings(
            "export function W(props) { return <input {...props} />; }\n")
        self.assertNotIn("control-no-label", found)

    def test_input_without_spread_is_still_flagged_control_no_label(self):
        found = self.findings("export function W() { return <input />; }\n")
        self.assertIn("control-no-label", found)

    def test_spread_img_is_not_flagged_img_no_alt(self):
        found = self.findings(
            "export function W(props) { return <img {...props} />; }\n")
        self.assertNotIn("img-no-alt", found)

    def test_img_without_spread_is_still_flagged_img_no_alt(self):
        found = self.findings(
            "export function W() { return <img src=\"x.png\" />; }\n")
        self.assertIn("img-no-alt", found)

    def test_spread_button_is_not_flagged_empty_control(self):
        found = self.findings(
            "export function W(props) { return <button {...props} />; }\n")
        self.assertNotIn("empty-control", found)

    def test_button_without_spread_is_still_flagged_empty_control(self):
        found = self.findings("export function W() { return <button />; }\n")
        self.assertIn("empty-control", found)


class ComponentMatrixRequiresAttrs(TempDirTest):
    """CSM-1: a template needs `{attrs}`; `{content}` alone must not satisfy
    the guard, or every state/variant/size cell renders identically."""

    def generate(self, template):
        self.write("badge.css", ".badge { display: inline-block; }\n")
        self.write("matrix.json", json.dumps({
            "$schema": "component-state-matrix/1",
            "components": [{
                "name": "badge",
                "css": "badge.css",
                "template": template,
            }],
        }))
        return run_py("component-state-matrix", "generate_matrix",
                      "matrix.json", "--out", "sheet.html", cwd=self.tmp)

    def test_content_only_template_is_refused(self):
        proc = self.generate("<span class=\"badge\">{content}</span>")
        self.assertEqual(proc.returncode, 2, output(proc))
        self.assertIn("{attrs}", output(proc))

    def test_template_with_attrs_and_content_is_accepted(self):
        """Guard: the documented, correct shape still works."""
        proc = self.generate("<span class=\"badge\" {attrs}>{content}</span>")
        self.assertEqual(proc.returncode, 0, output(proc))

    def test_attrs_without_content_is_accepted(self):
        """Guard: {content} is optional (a void element like <input> has
        none) — only {attrs} is mandatory."""
        proc = self.generate("<input class=\"badge\" {attrs} />")
        self.assertEqual(proc.returncode, 0, output(proc))


class MatrixStates(TempDirTest):
    """GT-A12: a ring written as `.chip:focus` was mirrored to
    `[data-force-state~="focus"]`, but the focus-visible cell carried
    "focus-visible" alone, so the ring never rendered while the coverage line
    said the state was covered. GT-A13: only the seven states were allowed, so
    selected, current or open could not be rendered, nor "selected + hover";
    and the error state stamped `aria-invalid` on buttons and spans, where
    ARIA 1.2 deprecated it as a global attribute."""

    def generate(self, css, template, states, custom=None):
        self.write("chip.css", css)
        comp = {"name": "chip", "css": "chip.css", "template": template, "states": states}
        if custom is not None:
            comp["custom_states"] = custom
        self.write("matrix.json", json.dumps({"$schema": "component-state-matrix/1",
                                              "themes": ["light"], "densities": ["comfortable"],
                                              "components": [comp]}))
        proc = run_py("component-state-matrix", "generate_matrix", "matrix.json",
                      "--out", "sheet.html", cwd=self.tmp)
        sheet = (self.tmp / "sheet.html").read_text(encoding="utf-8") if proc.returncode == 0 else ""
        return proc, sheet

    @staticmethod
    def cells(sheet, tag):
        return re.findall(rf'<{tag} class="chip"([^>]*)>', sheet)

    def state_cells(self, template, tag, state):
        css = '.chip {}\n.chip[data-state="error"] { color: #b00; }\n.chip:disabled { opacity: .5; }\n'
        proc, sheet = self.generate(css, template, ["default", state])
        self.assertEqual(proc.returncode, 0, output(proc))
        marker = 'data-state="error"' if state == "error" else "disabled"
        cells = [a for a in self.cells(sheet, tag) if marker in a]
        self.assertTrue(cells, sheet[-400:])
        return cells

    def test_a_focus_ring_renders_in_the_focus_visible_cell(self):
        proc, sheet = self.generate(".chip { color: #222; }\n.chip:focus { outline: 2px solid #222; }\n",
                                    '<span class="chip" tabindex="0" {attrs}>{content}</span>',
                                    ["default", "focus-visible"])
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertIn('.chip[data-force-state~="focus"]', sheet)
        forced = [re.search(r'data-force-state="([^"]*)"', a) for a in self.cells(sheet, "span")]
        values = [m.group(1).split() for m in forced if m]
        self.assertTrue(values, sheet[-500:])
        self.assertTrue(all({"focus-visible", "focus", "focus-within"} <= set(v) for v in values), values)

    def test_a_custom_state_and_a_combination_render(self):
        custom = {"selected": {"attrs": {"aria-selected": "true"}}}
        states = ["default", "hover", "selected", "selected+hover"]
        css = ".chip { color: #222; }\n.chip:hover { color: #000; }\n"
        proc, sheet = self.generate(css, '<span class="chip" {attrs}>{content}</span>', states, custom)
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertIn("chip:selected", output(proc))                 # declared, no rule yet
        attrs = self.cells(sheet, "span")
        self.assertTrue(any('aria-selected="true"' in a and 'data-force-state="hover"' in a for a in attrs))
        self.assertTrue(any('aria-selected="true"' in a and "data-force-state" not in a for a in attrs))
        proc, sheet = self.generate(css + '.chip[aria-selected="true"] { font-weight: 700; }\n',
                                    '<span class="chip" {attrs}>{content}</span>', states, custom)
        self.assertNotIn("chip:selected", output(proc))              # the rule is found

    COVERED = "every declared state has a matching rule"

    def test_states_inside_is_and_where_are_mirrored(self):
        # Audit H5: only depth-0 pseudo-classes were rewritten, so these got
        # no mirror, rendered as default, and the summary still said covered.
        css = (".chip { color: #222; }\n.chip:is(:hover, :focus-visible) { color: #000; }\n"
               ":where(.chip:active) { color: #444; }\n")
        proc, sheet = self.generate(css, '<span class="chip" tabindex="0" {attrs}>{content}</span>',
                                    ["default", "hover", "focus-visible", "active"])
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertIn('.chip:is([data-force-state~="hover"], [data-force-state~="focus-visible"])', sheet)
        self.assertIn(':where(.chip[data-force-state~="active"])', sheet)
        self.assertIn(self.COVERED, output(proc))

    def test_a_nested_state_is_mirrored_with_its_parent(self):
        css = (".chip {\n  color: #222;\n  &:hover { color: #000; }\n"
               "  @media (hover: hover) { &:active { color: #444; } }\n}\n")
        proc, sheet = self.generate(css, '<span class="chip" {attrs}>{content}</span>',
                                    ["default", "hover", "active"])
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertIn('.chip[data-force-state~="hover"] {', sheet)
        self.assertRegex(sheet, r'@media \(hover: hover\) \{\s*\.chip\[data-force-state~="active"\] \{')
        self.assertNotIn('&[data-force-state', sheet)
        self.assertIn(self.COVERED, output(proc))

    def test_a_guard_or_an_empty_rule_covers_nothing(self):
        css = ".chip { color: #222; }\n.chip:not(:hover) { color: #000; }\n.chip:active {}\n"
        proc, sheet = self.generate(css, '<span class="chip" {attrs}>{content}</span>',
                                    ["default", "hover", "active"])
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertNotIn(self.COVERED, output(proc))
        self.assertIn("chip:hover", output(proc))
        self.assertIn("chip:active", output(proc))
        self.assertIn(":not(:hover)", sheet)                       # the guard is left alone
        proc, _ = self.generate(".chip:hover { color: #000; }\n.chip:active { color: #444; }\n",
                                '<span class="chip" {attrs}>{content}</span>', ["default", "hover", "active"])
        self.assertIn(self.COVERED, output(proc))                   # the control

    def test_an_unforced_arm_of_a_group_never_matches_in_the_mirror(self):
        # Codex on #132: `.danger` kept live re-applied the hover styles to every
        # danger chip, after the component's rules; `:not(*)` keeps its specificity.
        css = ".chip { color: #222; }\n.chip:is(:hover, .danger) { color: #000; }\n"
        proc, sheet = self.generate(css, '<span class="chip" {attrs}>{content}</span>', ["default", "hover"])
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertIn('.chip:is([data-force-state~="hover"], .danger:not(*)) {', sheet)
        self.assertNotIn('"hover"], .danger)', sheet)

    def test_a_focus_within_ring_covers_the_focus_visible_cell(self):
        # CodeRabbit on #132: the cell carries focus-within, so its mirror renders.
        proc, _ = self.generate(".chip { color: #222; }\n.chip:focus-within { outline: 2px solid #222; }\n",
                                '<span class="chip" {attrs}>{content}</span>', ["default", "focus-visible"])
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertIn(self.COVERED, output(proc))

    def test_an_undeclared_state_names_the_way_to_declare_it(self):
        proc, _ = self.generate(".chip {}\n", '<span class="chip" {attrs}>{content}</span>',
                                ["default", "selected"])
        self.assertEqual(proc.returncode, 2, output(proc))
        self.assertIn("custom_states", output(proc))

    def test_the_error_state_puts_aria_invalid_on_form_controls_only(self):
        """A button takes no aria-invalid, and a wrapper around an input is not
        the input: the element carrying {attrs} decides (Codex on #42)."""
        for template, tag, invalid in (('<span class="chip" {attrs}>{content}</span>', "span", False),
                                       ('<input class="chip" {attrs}>', "input", True),
                                       ('<button class="chip" {attrs}>{content}</button>', "button", False),
                                       ('<div class="chip" {attrs}><input></div>', "div", False)):
            with self.subTest(tag=tag):
                errors = self.state_cells(template, tag, "error")
                self.assertEqual([invalid] * len(errors), ['aria-invalid="true"' in a for a in errors])

    def test_a_wrapper_around_a_form_control_is_not_disabled_by_attribute(self):
        """Codex on #42: a <div {attrs}> holding an <input> got a `disabled`
        attribute, which a div cannot have."""
        for template, tag, real in (('<div class="chip" {attrs}><input></div>', "div", False),
                                    ('<button class="chip" {attrs}>{content}</button>', "button", True)):
            with self.subTest(tag=tag):
                cells = [a for a in self.state_cells(template, tag, "disabled") if "aria-disabled" in a]
                self.assertTrue(cells)
                self.assertEqual([real] * len(cells), [bool(re.search(r"(?:^|\s)disabled(?:\s|$)", a)) for a in cells])

    def test_a_combination_whose_states_set_one_attribute_twice_is_refused(self):
        """Codex on #42: loading+error kept only data-state="error", while the
        coverage line counted both rules."""
        proc, _ = self.generate(".chip {}\n", '<span class="chip" {attrs}>{content}</span>',
                                ["default", "loading+error"])
        self.assertEqual(proc.returncode, 2, output(proc))
        self.assertIn("data-state", output(proc))

    def test_a_quoted_bracket_before_attrs_keeps_the_tag(self):
        """CodeRabbit on #42: `[^<>]*` stopped at a `<` inside a quoted value,
        so an input with one was not read as a form control."""
        template = '<input class="chip" data-hint="1<2" {attrs}>'
        self.assertTrue(all('aria-invalid="true"' in a for a in self.state_cells(template, "input", "error")))
        self.assertTrue(all(re.search(r"(?:^|\s)disabled(?:\s|$)", a)
                            for a in self.state_cells(template, "input", "disabled") if "aria-disabled" in a))

    def test_a_conflict_is_judged_on_the_element_that_renders_it(self):
        """CodeRabbit on #42: error + a state setting aria-invalid="false"
        conflicts on an input, where error sets aria-invalid, and not on a span."""
        custom = {"valid": {"attrs": {"aria-invalid": "false"}}}
        for template, refused in (('<input class="chip" {attrs}>', True),
                                  ('<span class="chip" {attrs}>{content}</span>', False)):
            with self.subTest(refused=refused):
                proc, _ = self.generate(".chip {}\n", template, ["default", "error+valid"], custom)
                self.assertEqual(proc.returncode, 2 if refused else 0, output(proc))

    def test_form_control_true_keeps_aria_invalid_off_a_div(self):
        """CodeRabbit on #42: `form_control: true` bypassed error's form tags."""
        self.write("chip.css", '.chip {}\n.chip[data-state="error"] { color: #b00; }\n')
        self.write("matrix.json", json.dumps({"$schema": "component-state-matrix/1",
                                              "themes": ["light"], "densities": ["comfortable"],
                                              "components": [{"name": "chip", "css": "chip.css",
                                                              "template": '<div class="chip" {attrs}>x</div>',
                                                              "states": ["default", "error", "disabled"],
                                                              "form_control": True}]}))
        proc = run_py("component-state-matrix", "generate_matrix", "matrix.json", "--out", "sheet.html",
                      cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        cells = self.cells((self.tmp / "sheet.html").read_text(encoding="utf-8"), "div")
        self.assertFalse([a for a in cells if "aria-invalid" in a])
        self.assertTrue([a for a in cells if re.search(r"(?:^|\s)disabled(?:\s|$)", a)])

    def test_the_coverage_table_has_a_column_per_state(self):
        """Codex on #42: the grid had seven state tracks, so a custom state's
        column wrapped onto a row of its own."""
        proc, sheet = self.generate(".chip {}\n", '<span class="chip" {attrs}>{content}</span>',
                                    ["default", "selected"],
                                    {"selected": {"attrs": {"aria-selected": "true"}}})
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertIn('class="msheet__table" role="table" style="--msheet-states: 8"', sheet)
        self.assertIn("repeat(var(--msheet-states, 7), 1fr)", sheet)


class MatrixModel(TempDirTest):
    """GT-B7: fixtures were inner HTML only, so nothing could set `dir`, and
    the RTL fixture state-coverage.md asks for could not be rendered. GT-B8:
    nothing said when the baselines outgrow the repository."""

    def generate(self, content, variants=("default",), themes=("light",),
                 densities=("comfortable",)):
        self.write("chip.css", ".chip {}\n")
        self.write("matrix.json", json.dumps({
            "$schema": "component-state-matrix/1", "themes": list(themes),
            "densities": list(densities),
            "components": [{"name": "chip", "css": "chip.css", "variants": list(variants),
                            "template": '<span class="chip" {attrs}>{content}</span>',
                            "content": content}]}))
        proc = run_py("component-state-matrix", "generate_matrix", "matrix.json",
                      "--out", "sheet.html", cwd=self.tmp)
        sheet = (self.tmp / "sheet.html").read_text(encoding="utf-8") if proc.returncode == 0 else ""
        return proc, sheet

    def test_a_fixture_sets_dir_and_lang_on_its_stage(self):
        proc, sheet = self.generate({"label": "Save",
                                     "arabic": {"html": "حفظ", "dir": "rtl", "lang": "ar"}})
        self.assertEqual(proc.returncode, 0, output(proc))
        stages = re.findall(r'<div class="msheet__stage"[^>]*>', sheet)
        rtl = [s for s in stages if "--f_arabic--" in s]
        ltr = [s for s in stages if "--f_label--" in s]
        self.assertTrue(rtl and ltr, stages[:3])
        for stage in rtl:
            self.assertIn(' dir="rtl" lang="ar"', stage)
        for stage in ltr:
            self.assertNotIn(" dir=", stage)
        self.assertIn(">حفظ</span>", sheet)

    def test_a_fixture_with_a_bad_direction_or_key_is_refused(self):
        for fixture, needle in (({"html": "x", "dir": "right"}, "ltr, rtl or auto"),
                                ({"html": "x", "lang": "arabic script"}, "language tag"),
                                ({"html": "x", "direction": "rtl"}, "unknown key"),
                                ({"dir": "rtl"}, "`html` required")):
            with self.subTest(fixture=fixture):
                proc, _ = self.generate({"label": "Save", "odd": fixture})
                self.assertEqual(proc.returncode, 2, output(proc))
                self.assertIn(needle, output(proc))

    def test_a_sheet_near_the_lfs_line_says_so(self):
        proc, _ = self.generate("Save")
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertNotIn("Git LFS", output(proc))
        # 60 variants: 7 states x 60 x 2 themes, plus 3 densities x 60 x 2.
        proc, _ = self.generate("Save", variants=[f"v{i}" for i in range(60)],
                                themes=("light", "dark"),
                                densities=("compact", "comfortable", "spacious"))
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertIn("1,200 cells, 2,400 with the forced-colors pass", output(proc))
        self.assertIn("Git LFS", output(proc))


SAAS_DDL = """\
CREATE TABLE organizations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    plan text NOT NULL DEFAULT 'free'
);
CREATE TABLE profiles (
    id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name text NOT NULL,
    role text NOT NULL DEFAULT 'member',
    is_admin boolean NOT NULL DEFAULT false,
    credits integer NOT NULL DEFAULT 0,
    org_id uuid REFERENCES organizations(id),
    api_token text,
    reset_token text,
    webhook_secret text,
    token_hash text
);
CREATE TABLE projects (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    owner_id uuid NOT NULL REFERENCES profiles(id)
);
"""


class SupabaseSecurityDefaults(TempDirTest):
    """DL-A1 and DL-A2."""

    def setUp(self):
        super().setUp()
        self.write("schema.sql", SAAS_DDL)
        proc = run_py("content-model-to-ui", "introspect_schema", "schema.sql", "-o", "model.json",
                      cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        self.model = json.loads((self.tmp / "model.json").read_text(encoding="utf-8"))

    def col(self, table, name):
        t = next(t for t in self.model["tables"] if t["name"] == table)
        return next(c for c in t["columns"] if c["name"] == name)

    def test_secret_columns_are_never_displayed_or_editable(self):
        for name in ("api_token", "reset_token", "webhook_secret", "token_hash"):
            with self.subTest(column=name):
                ui = self.col("profiles", name)["ui"]
                self.assertTrue(ui.get("never_display"), ui)
                self.assertFalse(ui["placement"]["detail"])
                self.assertFalse(ui["placement"]["form"])

    def test_authority_columns_are_read_only_by_default(self):
        for table, name in (("profiles", "id"), ("profiles", "role"), ("profiles", "is_admin"),
                            ("profiles", "credits"), ("profiles", "org_id"),
                            ("organizations", "plan"), ("projects", "owner_id")):
            with self.subTest(column=f"{table}.{name}"):
                self.assertFalse(self.col(table, name)["ui"]["placement"]["form"])
        self.assertTrue(self.col("profiles", "display_name")["ui"]["placement"]["form"])

    def test_the_draft_type_leaves_authority_and_secrets_out(self):
        proc = run_py("content-model-to-ui", "scaffold_ui", "model.json", "--out", "src",
                      cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        types = next((self.tmp / "src").rglob("profile*.types.ts")).read_text(encoding="utf-8")
        draft = types.split("export type ProfileDraft", 1)[1].split(">;", 1)[0]
        self.assertIn("'display_name'", draft)
        for name in ("role", "is_admin", "credits", "org_id", "api_token", "reset_token"):
            self.assertNotIn(f"'{name}'", draft)

    def test_a_human_can_release_an_authority_column(self):
        answers = self.write("answers.json", json.dumps(
            {"profiles.authority_columns": ["id", "role", "is_admin", "credits"]}))
        proc = run_py("content-model-to-ui", "scaffold_ui", "model.json", "--out", "src",
                      "--answers", answers, cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        types = next((self.tmp / "src").rglob("profile*.types.ts")).read_text(encoding="utf-8")
        draft = types.split("export type ProfileDraft", 1)[1].split(">;", 1)[0]
        self.assertIn("'org_id'", draft)                  # released
        self.assertNotIn("'role'", draft)                 # still protected


RLS_DDL = SAAS_DDL + """\
CREATE TABLE notes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    body text NOT NULL,
    owner_id uuid NOT NULL REFERENCES profiles(id)
);
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE ONLY public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE notes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own profile" ON public.profiles FOR ALL TO authenticated
    USING ((id = (select auth.uid())));
CREATE POLICY notes_read ON notes FOR SELECT USING (true);
CREATE POLICY notes_write ON notes AS PERMISSIVE FOR UPDATE TO authenticated
    USING (true) WITH CHECK ((owner_id = auth.uid()));
CREATE POLICY notes_insert ON notes FOR INSERT TO authenticated WITH CHECK (owner_id = auth.uid());
CREATE POLICY org_service ON organizations FOR ALL TO service_role USING (true);
"""

GEN_TYPES = """\
export type Database = {
  public: {
    Tables: {
      notes: {
        Row: { id: string; body: string }
        Insert: { id?: string; body: string }
        Update: { id?: string; body?: string }
        Relationships: []
      }
    }
    Enums: {}
  }
}
"""


class SchemaSecurityPass(TempDirTest):
    """DL-A6 and DL-C1: the parser skipped `ENABLE ROW LEVEL SECURITY` and
    `CREATE POLICY`, listed "RLS policies" as missing from DDL that held them,
    and assumed RLS was on everywhere."""

    def introspect(self, ddl, name="schema.sql", *args):
        self.write(name, ddl)
        proc = run_py("content-model-to-ui", "introspect_schema", name, "-o", "model.json",
                      "--summary", *args, cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        return proc, json.loads((self.tmp / "model.json").read_text(encoding="utf-8"))

    def found(self, model):
        return sorted((f["table"], f["level"], f["code"]) for f in model["security"]["findings"])

    def test_rls_and_policies_are_read_from_the_ddl(self):
        _, model = self.introspect(RLS_DDL)
        tables = {t["name"]: t for t in model["tables"]}
        self.assertEqual({"organizations": True, "profiles": True, "projects": False, "notes": True},
                         {name: t["rls"] for name, t in tables.items()})
        own = tables["profiles"]["policies"][0]
        self.assertEqual(("own profile", "all", ["authenticated"], "(id = (select auth.uid()))", None),
                         (own["name"], own["command"], own["roles"], own["using"], own["with_check"]))
        write = next(p for p in tables["notes"]["policies"] if p["name"] == "notes_write")
        self.assertEqual(("update", "true", "(owner_id = auth.uid())"),
                         (write["command"], write["using"], write["with_check"]))
        self.assertEqual(["public"], tables["notes"]["policies"][0]["roles"])      # no TO: everyone
        self.assertIn("row-level security", model["fidelity"]["carries"])
        self.assertNotIn("RLS policies", model["fidelity"]["missing"])

    def test_the_findings_name_the_holes_and_only_the_holes(self):
        _, model = self.introspect(RLS_DDL)
        self.assertEqual([("notes", "block", "open-write"),           # UPDATE ... USING (true)
                          ("organizations", "warn", "no-policy"),     # its one policy is the service's
                          ("profiles", "warn", "authority-writable"),
                          ("projects", "block", "rls-off")], self.found(model))
        # Not holes: a public read, a policy for the service role, and an
        # owner check that names the authority column.
        message = next(f["message"] for f in model["security"]["findings"] if f["code"] == "open-write")
        self.assertIn("notes_write", message)
        self.assertNotIn("notes_read", json.dumps(model["security"]))

    def test_only_a_table_revoke_takes_a_column_away(self):
        # CodeRabbit on PR #9, and Postgres: a column-level revoke has no
        # effect while the table-level grant stands, which is Supabase's default.
        column = "REVOKE UPDATE (role, is_admin, credits, org_id) ON profiles FROM authenticated;\n"
        _, model = self.introspect(RLS_DDL + column)
        warning = next(f["message"] for f in model["security"]["findings"]
                       if f["code"] == "authority-writable")
        self.assertIn("has no effect while the table-level grant stands", warning)
        self.assertIn("revoke update on profiles from authenticated; grant update (display_name)", warning)
        table = ("REVOKE UPDATE ON profiles FROM authenticated;\n"
                 "GRANT UPDATE (display_name) ON profiles TO authenticated;\n")
        _, model = self.introspect(RLS_DDL + table)
        self.assertNotIn(("profiles", "warn", "authority-writable"), self.found(model))
        # Granted back, the column is exposed again; revoked from anon alone, nothing changed.
        _, model = self.introspect(RLS_DDL + table + "GRANT UPDATE (role) ON profiles TO authenticated;\n")
        self.assertIn(("profiles", "warn", "authority-writable"), self.found(model))
        _, model = self.introspect(RLS_DDL + "REVOKE UPDATE ON profiles FROM anon;\n")
        self.assertIn(("profiles", "warn", "authority-writable"), self.found(model))

    def test_naming_an_authority_column_is_not_pinning_it(self):
        # Codex on PR #9: `role in ('member', 'admin')` names the column and
        # lets a member choose admin.
        base = SAAS_DDL + "ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;\n"
        named = ("CREATE POLICY p ON profiles FOR UPDATE TO authenticated USING (id = auth.uid()) "
                 "WITH CHECK (id = auth.uid() AND role IN ('member', 'admin'));\n")
        _, model = self.introspect(base + named)
        warning = next(f["message"] for f in model["security"]["findings"]
                       if f["code"] == "authority-writable")
        self.assertIn("role", warning)
        self.assertNotIn("change id,", warning)             # `id = auth.uid()` does pin id
        pinned = ("CREATE POLICY p ON projects FOR UPDATE TO authenticated "
                  "USING (owner_id = (select auth.uid()));\n")
        _, model = self.introspect(SAAS_DDL + "ALTER TABLE projects ENABLE ROW LEVEL SECURITY;\n" + pinned)
        self.assertNotIn(("projects", "warn", "authority-writable"), self.found(model))

    def test_a_restrictive_policy_narrows_and_never_grants(self):
        # Codex and CodeRabbit on PR #9: Postgres ANDs a restrictive policy
        # with the permissive ones, and one alone lets nothing through.
        base = SAAS_DDL + "ALTER TABLE projects ENABLE ROW LEVEL SECURITY;\n"
        open_write = "CREATE POLICY anyone ON projects FOR UPDATE TO authenticated USING (true);\n"
        narrow = ("CREATE POLICY mine ON projects AS RESTRICTIVE FOR UPDATE TO authenticated "
                  "USING (owner_id = auth.uid());\n")
        _, model = self.introspect(base + open_write)
        self.assertIn(("projects", "block", "open-write"), self.found(model))
        _, model = self.introspect(base + open_write + narrow)
        self.assertNotIn("open-write", {f["code"] for f in model["security"]["findings"]})
        _, model = self.introspect(base + narrow)
        self.assertIn(("projects", "warn", "no-policy"), self.found(model))

    def test_a_dropped_policy_is_gone(self):
        # Codex and CodeRabbit on PR #9: migrations are replayed in order.
        base = SAAS_DDL + "ALTER TABLE projects ENABLE ROW LEVEL SECURITY;\n"
        history = ("CREATE POLICY \"open\" ON projects FOR ALL TO authenticated USING (true);\n"
                   "DROP POLICY IF EXISTS \"open\" ON public.projects;\n"
                   "CREATE POLICY mine ON projects FOR ALL TO authenticated USING (owner_id = auth.uid());\n")
        _, model = self.introspect(base + history)
        projects = next(t for t in model["tables"] if t["name"] == "projects")
        self.assertEqual(["mine"], [p["name"] for p in projects["policies"]])
        self.assertNotIn("open-write", {f["code"] for f in model["security"]["findings"]})

    def test_the_summary_opens_with_the_security_block(self):
        proc, _ = self.introspect(RLS_DDL)
        lines = proc.stdout.decode("utf-8").splitlines()
        self.assertTrue(lines[0].startswith("SECURITY"), lines[:3])
        block = "\n".join(lines[:lines.index("")])
        self.assertRegex(block, r"BLOCK\s+projects\s+row-level security is off")
        self.assertRegex(block, r"BLOCK\s+notes\s+policy \"notes_write\"")
        self.assertIn("2 blocking", block)

    def test_ddl_with_no_rls_statement_says_so(self):
        proc, model = self.introspect(SAAS_DDL)
        self.assertIn("no row-level security statement at all", proc.stdout.decode("utf-8"))
        self.assertEqual({"rls-off"}, {f["code"] for f in model["security"]["findings"]})

    def test_a_source_that_cannot_say_is_reported_as_unknown(self):
        proc, model = self.introspect(GEN_TYPES, "database.types.ts")
        self.assertTrue(proc.stdout.decode("utf-8").startswith("SECURITY    unknown"), output(proc))
        self.assertEqual([], model["security"]["findings"])
        self.assertIsNone(model["tables"][0]["rls"])
        self.assertIn("RLS policies", model["fidelity"]["missing"])

    def test_several_migration_files_are_one_schema(self):
        # The skill's own command passes `supabase/migrations/*.sql`, which the
        # tool refused as soon as there were two files; and the policies are
        # usually in a later migration than the table.
        self.write("migrations/001_tables.sql", SAAS_DDL.rstrip().rstrip(";"))    # no final `;`
        self.write("migrations/002_rls.sql", "ALTER TABLE projects ENABLE ROW LEVEL SECURITY;\n"
                   "CREATE POLICY own ON projects FOR ALL TO authenticated USING (owner_id = auth.uid());\n")
        proc = run_py("content-model-to-ui", "introspect_schema", "migrations/001_tables.sql",
                      "migrations/002_rls.sql", "-o", "model.json", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        model = json.loads((self.tmp / "model.json").read_text(encoding="utf-8"))
        self.assertEqual({"organizations": False, "profiles": False, "projects": True},
                         {t["name"]: t["rls"] for t in model["tables"]})
        # Only DDL is read together.
        self.write("database.types.ts", GEN_TYPES)
        proc = run_py("content-model-to-ui", "introspect_schema", "migrations/001_tables.sql",
                      "database.types.ts", cwd=self.tmp)
        self.assertEqual(proc.returncode, 2, output(proc))
        self.assertIn("database.types.ts alone", output(proc))
        # cmd.exe hands the pattern over as written (CodeRabbit on PR #9).
        proc = run_py("content-model-to-ui", "introspect_schema", "migrations/*.sql", "-o", "glob.json",
                      cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        globbed = json.loads((self.tmp / "glob.json").read_text(encoding="utf-8"))
        self.assertTrue(next(t for t in globbed["tables"] if t["name"] == "projects")["rls"])

    def test_the_rls_question_defaults_from_the_ddl(self):
        def default(model):
            return next(q for q in model["questions"] if q["id"] == "app.rls_enabled")

        _, model = self.introspect(RLS_DDL)
        self.assertIs(default(model)["default"], False)
        self.assertIn("off on projects", default(model)["why"])
        _, model = self.introspect(RLS_DDL + "ALTER TABLE projects ENABLE ROW LEVEL SECURITY;\n")
        self.assertIs(default(model)["default"], True)
        _, model = self.introspect(GEN_TYPES, "database.types.ts")
        self.assertIs(default(model)["default"], True)
        self.assertIn("cannot say", default(model)["why"])

    def test_the_scaffold_names_the_blocking_findings_and_follows_each_table(self):
        self.introspect(RLS_DDL)
        proc = run_py("content-model-to-ui", "scaffold_ui", "model.json", "--out", "src", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertIn("SECURITY projects: row-level security is off", output(proc))
        self.assertIn("2 blocking security finding(s)", output(proc))

        def states(entity):
            return next((self.tmp / "src").rglob(f"{entity}States.tsx")).read_text(encoding="utf-8")

        self.assertIn("RLS was reported as off", states("Projects"))
        self.assertIn("Row-level security is on for this table", states("Profiles"))
        # --strict refuses, for CI; a table with no blocking finding still passes it.
        proc = run_py("content-model-to-ui", "scaffold_ui", "model.json", "--out", "strict", "--strict",
                      cwd=self.tmp)
        self.assertEqual(proc.returncode, 1, output(proc))
        self.assertIn("nothing written", output(proc))
        self.assertFalse((self.tmp / "strict").exists())
        proc = run_py("content-model-to-ui", "scaffold_ui", "model.json", "--out", "strict", "--strict",
                      "--entity", "profiles", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        # Codex on PR #9: the pre-filled answer is "no" for a mixed schema, and
        # one answer for the whole application must not overrule a table's fact.
        answers = self.write("answers.json", json.dumps({"app.rls_enabled": False}))
        proc = run_py("content-model-to-ui", "scaffold_ui", "model.json", "--out", "src", "--force",
                      "--answers", answers, cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertIn("Row-level security is on for this table", states("Profiles"))
        self.assertIn("RLS was reported as off", states("Projects"))


class A11yStaticLeavesEmails(TempDirTest):
    """R3's live check: /gate failed a project on the plugin's own receipt
    template (no <main>, an outline reset on img), rules for a page, not a
    letter. A folder's email templates, by the config's `emails`, are left to
    lint_email.py; one named on its own is still read."""

    RECEIPT = SKILLS / "email-template-system" / "assets" / "templates" / "transactional-receipt.html"
    PAGE = ('<!doctype html><html lang="en"><head><title>Home</title></head>'
            "<body><main><h1>Home</h1></main></body></html>\n")

    def setUp(self):
        super().setUp()
        self.write("emails/receipt.html", self.RECEIPT.read_text(encoding="utf-8"))
        self.write("index.html", self.PAGE)

    def run_static(self, *args):
        return run_py("a11y-audit-runner", "a11y_static", *args, "--json", cwd=self.tmp)

    def test_a_projects_folder_leaves_its_templates_to_the_email_lint(self):
        self.write(".design-suite.json", json.dumps({"schema": 1}))
        proc = self.run_static(".")
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertEqual([], json.loads(proc.stdout)["findings"])
        self.assertIn("1 file(s) that are email templates, which lint_email.py checks", output(proc))

    def test_the_configs_emails_say_which(self):
        self.write(".design-suite.json", json.dumps({"schema": 1, "emails": ["mail/**/*.html"]}))
        proc = self.run_static(".")                              # emails/ is a page folder here
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn("outline-none-no-replacement", {f["rule"] for f in json.loads(proc.stdout)["findings"]})

    def test_a_template_named_on_its_own_is_read(self):
        self.write(".design-suite.json", json.dumps({"schema": 1}))
        proc = self.run_static("emails/receipt.html")
        self.assertEqual(1, proc.returncode, output(proc))      # the control: the receipt has findings
        self.assertTrue(json.loads(proc.stdout)["findings"])

    def test_without_a_config_nothing_is_left_out(self):
        proc = self.run_static(".")
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertNotIn("email templates", output(proc))


class A11yStaticScaleAndScope(TempDirTest):
    """XC-A6 and GT-A4."""

    def page(self, rows):
        body = "".join(f'<div class="r"><img src="i{i}.png" alt=""><button>Go {i}</button>'
                       f'<label>Name {i} <input type="text"></label></div>\n'
                       for i in range(rows))
        return self.write(f"page{rows}.html", '<!doctype html><html lang="en"><title>t</title>'
                          f"<main><h1>t</h1>{body}</main></html>\n")

    def timed(self, path):
        start = time.perf_counter()
        proc = run_py("a11y-audit-runner", "a11y_static", path, "--json", cwd=self.tmp,
                      timeout=600)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return time.perf_counter() - start

    def test_a_large_page_is_audited_in_roughly_linear_time(self):
        small, large = self.timed(self.page(1000)), self.timed(self.page(4000))
        # Four times the rows: linear work takes ~4x, quadratic ~16x.
        self.assertLess(large / small, 8, f"1,000 rows {small:.1f}s, 4,000 rows {large:.1f}s")
        self.assertLess(large, 20)

    def test_files_named_explicitly_that_are_not_markup_are_skipped(self):
        self.write("README.md", "Use <img src='x.png'> and <button></button>\n")
        self.write("render.py", "html = '<input type=\"text\">'\n")
        self.write("notes.txt", "<a href='#'></a>\n")
        proc = run_py("a11y-audit-runner", "a11y_static", "README.md", "render.py",
                      "notes.txt", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertIn("skipped", output(proc).lower())

    def test_indented_sass_is_skipped_not_passed(self):
        # N13: the CSS checks follow braces and indented Sass has none, so
        # `outline: none` in a .sass file was reported clean without a word.
        self.write("src/card.sass", ".card:focus\n  outline: none\n")
        self.write("src/card.scss", ".card:focus { outline: none; }\n")
        proc = run_py("a11y-audit-runner", "a11y_static", "src", cwd=self.tmp)
        self.assertIn("skipped 1 file(s) of indented Sass", output(proc))
        report = proc.stdout.decode("utf-8")
        self.assertIn("card.scss", report, output(proc))           # the control: braces are read
        self.assertNotIn("card.sass", report)


class StaticBestPractice(TempDirTest):
    """GT-A18: a11y_static made `multiple-h1`, `heading-skip` and
    `no-main-landmark` errors under success criteria, where axe tags the same
    checks best-practice only. They are warnings now, labelled best practice,
    and a page with nothing else wrong passes."""

    def test_the_outline_and_landmark_checks_are_best_practice_warnings(self):
        page = self.write("page.html", '<!doctype html><html lang="en"><title>t</title><body>'
                                       "<h1>One</h1><h3>Skipped</h3><h1>Two</h1></body></html>\n")
        proc = run_py("a11y-audit-runner", "a11y_static", page, "--json", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        found = {f["rule"]: (f["severity"], f["sc"]) for f in json.loads(proc.stdout)["findings"]}
        for rule in ("multiple-h1", "heading-skip", "no-main-landmark"):
            with self.subTest(rule=rule):
                self.assertEqual(("warning", "best practice"), found.get(rule))
        proc = run_py("a11y-audit-runner", "a11y_static", page, "--strict", cwd=self.tmp)
        self.assertEqual(proc.returncode, 1, output(proc))          # --strict still fails on them


class A11yStaticReadsNestedRules(TempDirTest):
    """Audit H4: the CSS check split blocks at depth 0 only, so a rule inside
    `@layer`, `@media` or `@supports`, or nested with `&`, was never read on
    its own. Its declarations were pooled with its siblings' (any
    `box-shadow` nearby counted as the ring), and the focus selector was
    tested on the at-rule's prelude. The starter's base.css is all `@layer
    base`, so a reset planted there audited clean."""

    def findings(self, css, name="style.css"):
        self.write(name, css)
        proc = run_py("a11y-audit-runner", "a11y_static", name, "--json", cwd=self.tmp)
        return proc, json.loads(proc.stdout)["findings"]

    def rules(self, css):
        return [(f["rule"], f["line"]) for f in self.findings(css)[1]]

    def test_a_reset_inside_the_starters_layer_is_reported_on_its_line(self):
        base = (SKILLS / "web-design-studio" / "assets" / "starter" / "styles" / "base.css").read_text(encoding="utf-8")
        planted, n = re.subn(r"^@layer base \{\n", "@layer base {\n  .btn:focus-visible { outline: none; }\n",
                             base, count=1, flags=re.M)
        self.assertEqual(1, n)
        line = planted[:planted.index(".btn:focus-visible")].count("\n") + 1
        self.assertGreater(line, 20)                    # below the header comment's lines
        self.assertEqual([], self.rules(base))          # the control: the starter is clean
        proc, found = self.findings(planted)
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertEqual([("outline-none-no-replacement", line)], [(f["rule"], f["line"]) for f in found])

    def test_a_reset_inside_a_condition_is_read_apart_from_its_siblings(self):
        for at in ("@media (hover: hover)", "@supports (display: grid)", "@layer components",
                   "@container card (width > 30rem)"):
            with self.subTest(at=at):
                css = f"{at} {{\n  .card {{ box-shadow: 0 0 0 2px red; }}\n  .btn:focus {{ outline: none; }}\n}}\n"
                self.assertEqual([("outline-none-no-replacement", 3)], self.rules(css))

    def test_a_shadow_only_ring_inside_a_layer_is_reported(self):
        css = "@layer components {\n  .btn:focus-visible {\n    outline: none;\n    box-shadow: 0 0 0 2px red;\n  }\n}\n"
        self.assertEqual([("focus-ring-shadow-only", 4)], self.rules(css))

    def test_a_condition_nested_in_a_rule_keeps_the_rules_declarations(self):
        # Codex on #132: the rule's border still applies under the condition.
        css = ".btn:focus {\n  border: 2px solid;\n  @media (forced-colors: active) { outline: none; }\n}\n"
        self.assertEqual([], self.rules(css))
        # The rule's own reset, read again under each condition, is reported once.
        css = ".btn:focus {\n  outline: none;\n  @media (x) { color: red; }\n  @media (y) { color: blue; }\n}\n"
        self.assertEqual([("outline-none-no-replacement", 2)], self.rules(css))

    def test_a_nested_focus_rule_is_resolved_against_its_parent(self):
        css = ".btn {\n  box-shadow: 0 1px 2px black;\n  &:focus-visible { outline: none; }\n}\n"
        found = self.findings(css)[1]
        self.assertEqual([("outline-none-no-replacement", 3)], [(f["rule"], f["line"]) for f in found])
        self.assertIn("`.btn:focus-visible`", found[0]["message"])
        css = ".btn {\n  &:focus-visible {\n    @media (hover: hover) { outline: none; }\n  }\n}\n"
        self.assertEqual([("outline-none-no-replacement", 3)], self.rules(css))
        # CodeRabbit on #132: a comma inside :is() is not the list's.
        css = ".a, .b {\n  &:is(:hover, :focus-visible) { outline: none; box-shadow: 0 0 0 2px red; }\n}\n"
        found = self.findings(css)[1]
        self.assertEqual([("focus-ring-shadow-only", 2)], [(f["rule"], f["line"]) for f in found])
        self.assertIn("`:is(.a, .b):is(:hover, :focus-visible)`", found[0]["message"])

    def test_the_controls(self):
        self.assertEqual([("outline-none-no-replacement", 1)], self.rules(".btn:focus { outline: none; }\n"))
        self.assertEqual([], self.rules("@layer base {\n  :focus-visible { outline: 2px solid; }\n}\n"))
        self.assertEqual([], self.rules('@font-face { font-family: "X}"; src: url(x.woff2); }\n'
                                        '.a::after { content: "{"; }\n'))
        self.assertEqual([("focus-rule-invisible", 1)], self.rules(".skip:focus-visible { cursor: pointer; }\n"))

    def test_a_skip_link_moved_on_screen_is_visible(self):
        # Reading the starter's layers found its skip link called invisible:
        # moved on-screen on focus, not ringed.
        for decl in ("translate: 0 0", "inset-block-start: 0", "clip-path: none", "opacity: 1"):
            with self.subTest(decl=decl):
                self.assertEqual([], self.rules(f".skip:focus-visible {{ {decl}; }}\n"))

    def test_a_style_block_in_markup_is_read_the_same(self):
        page = ('<!doctype html><html lang="en"><title>t</title><style>\n@layer base {\n'
                "  .a { box-shadow: 0 0 0 1px red; }\n  .btn:focus { outline: none; }\n}\n</style>"
                "<main><h1>t</h1></main></html>\n")
        self.assertEqual([("outline-none-no-replacement", 4)],
                         [(f["rule"], f["line"]) for f in self.findings(page, "page.html")[1]])


class A11yStaticReadsBoundAttributes(TempDirTest):
    """Audit H6: `.vue` files were audited, but `:alt` and `v-bind:alt` were
    not read as `alt`, so `<img :alt="d">` had no alt and a bound label was no
    label; a Vue project with the pre-commit hook was blocked on every bound
    attribute. Angular's `[alt]` and `[attr.aria-label]`, and the event
    bindings (`@click`, `v-on:click`, `on:click`, `(click)`), are the same
    construct."""

    def rules(self, body, name="c.vue"):
        self.write(name, f"<template>\n<main><h1>t</h1>\n{body}\n</main>\n</template>\n")
        proc = run_py("a11y-audit-runner", "a11y_static", name, "--json", cwd=self.tmp)
        return sorted(f["rule"] for f in json.loads(proc.stdout)["findings"])

    def test_a_bound_attribute_is_the_attribute(self):
        for body in ('<img :alt="d" src="x.png">', '<img v-bind:alt="d" src="x.png">',
                     '<img :alt.attr="d" src="x.png">', '<img [alt]="d" src="x.png">',
                     '<img alt="" :src="s">', '<input :id="i" :aria-label="lbl" :autocomplete="ac">',
                     '<input [attr.aria-label]="lbl" [autocomplete]="ac">',
                     '<button :aria-label="lbl"></button>', '<button v-bind:aria-label="lbl"></button>'):
            with self.subTest(body=body):
                self.assertEqual([], self.rules(body))

    def test_a_bound_string_literal_is_read_as_its_text(self):
        self.assertEqual([], self.rules('<img :alt="\'Company name\'" src="x.png">'))
        self.assertEqual(["alt-placeholder"], self.rules('<img :alt="\'image\'" src="x.png">'))

    def test_the_controls(self):
        self.assertEqual(["img-no-alt"], self.rules('<img :src="s">'))
        self.assertEqual(["img-no-alt"], self.rules('<img [src]="s">'))
        self.assertEqual(["img-no-alt"], self.rules('<img [class.wide]="w" src="x.png">'))
        self.assertIn("empty-control", self.rules('<button :class="c"></button>'))

    def test_an_event_binding_is_a_handler(self):
        for body in ('<div @click="go">x</div>', '<div v-on:click.prevent="go">x</div>',
                     '<div on:click={go}>x</div>', '<div (click)="go()">x</div>'):
            with self.subTest(body=body):
                self.assertEqual(["handler-on-noninteractive"], self.rules(body))
        self.assertEqual([], self.rules('<button @click="go">Go</button>'))     # the control


class TheAuditsRuntimeMediums(TempDirTest):
    """P54 part 7, the audit of 2026-10-14's §3.6: G1 and G2, a11y_static's
    reading of what is nested in an element."""

    def rules(self, name, text):
        self.write(name, text)
        proc = run_py("a11y-audit-runner", "a11y_static", name, "--json", cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return [f["rule"] for f in json.loads(proc.stdout)["findings"]]

    def test_aria_hidden_counts_the_tab_stops_at_any_depth(self):
        """G1: only direct children were read, so a link two levels down was
        missed, and a child that takes no focus (`type="hidden"`, `hidden`,
        `inert`, `tabindex="-1"`) was counted."""
        cases = {
            '<div aria-hidden="true"><ul><li><a href="/x">x</a></li></ul></div>': 1,
            '<div aria-hidden="true"><p><span tabindex="0">x</span></p></div>': 1,
            '<div aria-hidden="true"><input type="hidden" name="t"></div>': 0,
            '<div aria-hidden="true"><a href="/x" tabindex="-1">x</a></div>': 0,
            '<div aria-hidden="true"><div hidden><button>x</button></div></div>': 0,
            '<div aria-hidden="true" inert><a href="/x">x</a></div>': 0,
            '<div aria-hidden="true"><section inert><a href="/x">x</a></section></div>': 0,
            '<div aria-hidden="true"><div hidden="false"><button>x</button></div></div>': 0,   # boolean:
            '<div aria-hidden="true"><div inert="false"><a href="/x">x</a></div></div>': 0,    # present is on
        }
        bound = {                                                # Codex on #151: a bound value may be false
            '<div aria-hidden="true"><button hidden={open}>x</button></div>': 1,
            '<div aria-hidden="true"><section inert={busy}><a href="/x">x</a></section></div>': 1,
        }
        for jsx, want in bound.items():
            with self.subTest(jsx=jsx):
                got = self.rules("Widget.tsx", f"export function W() {{ return {jsx}; }}\n")
                self.assertEqual(want, got.count("aria-hidden-focusable"))
        for html, want in cases.items():
            with self.subTest(html=html):
                got = self.rules("page.html", f"<!doctype html><html lang=\"en\"><title>t</title><main>{html}</main></html>")
                self.assertEqual(want, got.count("aria-hidden-focusable"))

    def test_a_control_named_inside_or_by_a_component_is_not_empty(self):
        """G2: the name was looked for one level deep, and a component child
        (`<Icon/>`) read as nothing, though the file's own rule says what a
        component renders cannot be told."""
        cases = {
            "<button><span><img src=\"x.png\" alt=\"Close\" /></span></button>": False,
            "<button><Icon name=\"close\" /></button>": False,
            "<button><span><span aria-label=\"Close\"></span></span></button>": False,
            "<button><span><img src=\"x.png\" alt=\"\" /></span></button>": True,   # the control
            "<button><span aria-hidden=\"true\"><img src=\"x.png\" alt=\"Close\" /></span></button>": True,
            "<button><span aria-hidden=\"true\"><Icon name=\"close\" /></span></button>": True,   # Codex on #151
        }
        for jsx, empty in cases.items():
            with self.subTest(jsx=jsx):
                got = self.rules("Widget.tsx", f"export function W() {{ return {jsx}; }}\n")
                self.assertEqual(empty, "empty-control" in got)

    def test_the_coverage_table_says_what_this_suite_runs(self):
        """G7: automation-coverage.md §3 read as this suite's coverage, but the
        mechanism of 1.3.4 (a "Full" row), 2.4.11, 3.3.8 and nine more is in
        neither gate, though SKILL.md read as if it caught all 7. A Full row names
        a check one of the two gates runs, or says it is not in this suite; a
        marked row's criterion is in neither gate; the count is the table's."""
        skill = SKILLS / "a11y-audit-runner"
        doc = (skill / "references" / "automation-coverage.md").read_bytes().decode("utf-8")
        table = doc[doc.index("## 3. The coverage table"):doc.index("## 4. ")]
        gates = "".join((skill / "scripts" / n).read_bytes().decode("utf-8")
                        for n in ("a11y_static.py", "a11y_runtime.mjs"))
        rows = re.findall(r"^\| \*\*([^*]+)\*\*[^|]*\|([^|]*)\|(.*)$", table, re.M)
        self.assertEqual(len([line for line in table.splitlines() if line.startswith("| **")]), len(rows))
        self.assertGreater(len(rows), 50)
        decided = 0
        for named, auto, rest in rows:                  # `3.2.3 / 3.2.4 / 3.2.6` too (CodeRabbit on #151)
            criteria = re.findall(r"\d\.\d+\.\d+", named)
            with self.subTest(sc=named):
                self.assertTrue(criteria)
                in_a_gate = any(re.search(rf"(?<![\d.]){re.escape(sc)}(?!\d)", gates) for sc in criteria)
                marked = "*Not in this suite.*" in rest
                if marked:
                    self.assertFalse(in_a_gate, "marked, but a gate names it")
                elif "Full" in auto:
                    self.assertTrue(in_a_gate, "a Full row this suite does not run")
                    decided += 1
        self.assertIn(f"(this suite runs {decided} of them)", (skill / "SKILL.md").read_bytes().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
