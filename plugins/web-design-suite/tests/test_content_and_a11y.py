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
"""
from __future__ import annotations

import json
import unittest

from wds_support import TempDirTest, output, run_py


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


if __name__ == "__main__":
    unittest.main()
