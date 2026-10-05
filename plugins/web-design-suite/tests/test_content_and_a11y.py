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

    def test_the_coverage_table_has_a_column_per_state(self):
        """Codex on #42: the grid had seven state tracks, so a custom state's
        column wrapped onto a row of its own."""
        proc, sheet = self.generate(".chip {}\n", '<span class="chip" {attrs}>{content}</span>',
                                    ["default", "selected"],
                                    {"selected": {"attrs": {"aria-selected": "true"}}})
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertIn('class="msheet__table" role="table" style="--msheet-states: 8"', sheet)
        self.assertIn("repeat(var(--msheet-states, 7), 1fr)", sheet)


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


if __name__ == "__main__":
    unittest.main()
