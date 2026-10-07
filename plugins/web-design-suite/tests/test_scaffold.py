"""content-model-to-ui's scaffold: the interview's answers reach the output,
the forms carry the accessibility wiring screen-patterns.md promises, and the
server gets a schema that mirrors the constraints the form reads (DL-A8,
DL-A9, DL-B2).

One schema, scaffolded once per class with the answers and once without, on
both stacks. The generated TypeScript is parsed by the real compiler
(`typescript.transpileModule`, syntax only: the kit has no React types to
check against), the pydantic file by `ast`, and by pydantic itself where it is
installed.
"""

from __future__ import annotations

import ast
import json
import os
import pathlib
import re
import subprocess
import sys
import unittest

from wds_support import SKILLS, TempDirTest, class_temp_dir, env, load_script, output, run_py, tool_modules

DDL = """\
CREATE TYPE priority AS ENUM ('low', 'normal', 'high');
CREATE TABLE suppliers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  contact_email text
);
CREATE TABLE orders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_id uuid NOT NULL REFERENCES suppliers(id),
  reference text NOT NULL CHECK (char_length(reference) <= 24),
  category text NOT NULL,
  priority priority NOT NULL DEFAULT 'normal',
  total_cents integer NOT NULL CHECK (total_cents >= 0),
  deposit numeric(10,2),
  discount numeric(4,3) CHECK (discount > 0 AND discount < 1),
  is_rush boolean NOT NULL DEFAULT false,
  notes text,
  metadata jsonb,
  placed_at timestamptz NOT NULL DEFAULT now(),
  ships_at timestamptz
);
"""

ANSWERS = {
    "orders.total_cents.money": {"currency": "JPY", "storage": "minor-units"},
    "orders.deposit.money": {"currency": "EUR", "storage": "decimal"},
    "orders.discount.money": {"currency": "EUR", "storage": "decimal"},
    "orders.supplier_id.cardinality": "under-20",
    "orders.supplier_id.label_column": "name",
    "orders.category.options": ["retail", "wholesale"],
    "orders.ships_at.zone": "record",
    "orders.placed_at.zone": "fixed-utc",
    "orders.metadata.shape": {"keys": ["source"], "user_editable": False},
    "orders.default_sort": "placed_at desc",
}

TS_CHECK = """\
const ts = require('typescript');
const fs = require('fs');
let bad = 0;
for (const f of process.argv.slice(2)) {
  const r = ts.transpileModule(fs.readFileSync(f, 'utf8'), {
    reportDiagnostics: true, fileName: f,
    compilerOptions: { jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 },
  });
  for (const d of r.diagnostics || []) {
    bad += 1;
    console.log(f + ': ' + ts.flattenDiagnosticMessageText(d.messageText, ' '));
  }
}
process.exit(bad ? 1 : 0);
"""


def scaffold(tmp: pathlib.Path, out: str, *args: str, answers: dict | None = None) -> pathlib.Path:
    (tmp / "schema.sql").write_bytes(DDL.encode())
    proc = run_py("content-model-to-ui", "introspect_schema", "schema.sql", "-o", "model.json", cwd=tmp)
    assert proc.returncode == 0, output(proc)
    extra = list(args)
    if answers is not None:
        (tmp / f"{out}-answers.json").write_bytes(json.dumps(answers).encode())
        extra += ["--answers", f"{out}-answers.json"]
    proc = run_py("content-model-to-ui", "scaffold_ui", "model.json", "--out", out, *extra, cwd=tmp)
    assert proc.returncode == 0, output(proc)
    return tmp / out


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


class Answered(unittest.TestCase):
    """The schema scaffolded with the answers (css-modules and tailwind) and
    without them, once for the class."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = class_temp_dir(cls, "wds-scaffold-")
        cls.src = scaffold(cls.tmp, "src", answers=ANSWERS)
        cls.tw = scaffold(cls.tmp, "tw", "--stack", "tailwind", answers=ANSWERS)
        cls.plain = scaffold(cls.tmp, "plain")

    def orders(self, src: pathlib.Path, name: str) -> str:
        return read(src / "features" / "orders" / name)


class TheAnswersReachTheOutput(Answered):
    """DL-A8: `.money`, `.cardinality`, `.label_column`, `.options`, `.zone`,
    `.shape` and `.default_sort` were asked and never read."""

    def test_money_is_formatted_in_the_answered_currency_at_its_own_scale(self):
        for src in (self.src, self.tw):
            lst = self.orders(src, "OrdersList.tsx")
            detail = self.orders(src, "OrderDetail.tsx")
            self.assertIn('formatMinorUnits(row.total_cents, "JPY")', lst)
            self.assertIn('formatMoney(row.deposit, "EUR")', lst)
            self.assertIn('formatMinorUnits(record.total_cents, "JPY")', detail)
            for text in (lst, detail):
                self.assertNotIn("/ 100", text, "the scale is the currency's, never a literal 100")
                self.assertNotIn("USD", text)
        fmt = read(self.src / "lib" / "format.ts")
        self.assertIn("export function minorUnitScale(currency: string)", fmt)
        self.assertIn("resolvedOptions().maximumFractionDigits", fmt)
        self.assertIn("formatMinorUnits(minor: number | null, currency: string)", fmt)
        self.assertNotIn("currency: 'USD'", fmt)

    def test_an_unanswered_currency_is_marked_not_assumed(self):
        lst = self.orders(self.plain, "OrdersList.tsx")
        self.assertIn("'USD' /* TODO(answers): the currency, from `orders.total_cents.money` */", lst)
        self.assertIn("formatMinorUnits(row.total_cents, 'USD' /* TODO(answers)", lst)

    def test_the_form_notes_the_storage_the_answer_gave(self):
        form = self.orders(self.src, "OrderForm.tsx")
        self.assertIn("TODO(money): stored in minor units of JPY", form)
        self.assertIn('minorUnitScale("JPY")', form)
        self.assertIn("TODO(money): a decimal amount in EUR", form)
        self.assertRegex(form, r'step="any"[\s\S]{0,400}TODO\(money\): a decimal amount in EUR')
        plain = self.orders(self.plain, "OrderForm.tsx")
        self.assertIn("TODO(money): stored in minor units of the currency", plain)

    def test_cardinality_picks_the_control_and_the_label_column_names_the_option(self):
        form = self.orders(self.src, "OrderForm.tsx")
        self.assertRegex(form, r"<Select\s+id=\{fieldId\('supplier_id'\)\}")
        self.assertIn("TODO(options): one <option> per parent row, showing `name`", form)
        fields = self.orders(self.src, "orders.fields.ts")
        self.assertIn('labelColumn: "name"', fields)
        self.assertIn('money: {"currency": "JPY", "storage": "minor-units"}', fields)

    def test_the_label_column_names_the_join_in_the_cells(self):
        self.assertIn("{row.supplier_id /* TODO(join): show `suppliers.name` */}",
                      self.orders(self.src, "OrdersList.tsx"))
        self.assertIn("{record.supplier_id /* TODO(join): show `suppliers.name` */}",
                      self.orders(self.src, "OrderDetail.tsx"))
        self.assertIn("TODO(join): show the suppliers label; answer `orders.supplier_id.label_column`",
                      self.orders(self.plain, "OrdersList.tsx"))

    def test_an_unbounded_parent_is_a_picker(self):
        answers = dict(ANSWERS, **{"orders.supplier_id.cardinality": "unbounded"})
        src = scaffold(self.tmp, "picker", answers=answers)
        form = read(src / "features" / "orders" / "OrderForm.tsx")
        self.assertIn('<ControlStub control="record-picker"', form)
        self.assertIn("it shows `name`", form)

    def test_the_options_answer_is_the_closed_set(self):
        form = self.orders(self.src, "OrderForm.tsx")
        self.assertRegex(form, r'<option key=\{"retail"\} value=\{"retail"\}>\{"retail"\}</option>\s*'
                               r'<option key=\{"wholesale"\} value=\{"wholesale"\}>\{"wholesale"\}</option>')

    def test_an_option_with_a_quote_or_markup_is_still_one_expression(self):
        """Review of #64 (Codex): an option went into a double-quoted attribute
        and raw JSX text as it was."""
        mod = load_script("content-model-to-ui", "scaffold_ui")
        jsx = mod.control_jsx({"name": "size", "label": "Size", "control": "select",
                               "required": True, "options": ['XL "tall"', "<S>"]})
        self.assertIn('<option key={"XL \\"tall\\""} value={"XL \\"tall\\""}>{"XL \\"tall\\""}</option>', jsx)
        self.assertIn('<option key={"<S>"} value={"<S>"}>{"<S>"}</option>', jsx)
        self.assertNotIn('value="', jsx)
        self.assertIn("<Badge tone={toneFor(record.category)}>", self.orders(self.src, "OrderDetail.tsx"))
        self.assertNotIn("<Badge tone={toneFor(record.category)}>", self.orders(self.plain, "OrderDetail.tsx"))

    def test_the_zone_answer_reaches_format_instant(self):
        detail = self.orders(self.src, "OrderDetail.tsx")
        self.assertIn("formatInstant(record.placed_at, 'UTC')", detail)
        self.assertIn("formatInstant(record.ships_at, undefined /* TODO(zone): this record's own zone "
                      "column, per `orders.ships_at.zone` */)", detail)
        plain = self.orders(self.plain, "OrderDetail.tsx")
        self.assertIn("formatInstant(record.placed_at)}", plain)

    def test_a_machine_only_json_column_leaves_the_form(self):
        self.assertNotIn("metadata", self.orders(self.src, "OrderForm.tsx"))
        self.assertNotIn("'metadata'", self.orders(self.src, "orders.types.ts"))
        self.assertIn("metadata", self.orders(self.plain, "OrderForm.tsx"))

    def test_the_default_sort_is_a_constant_the_query_applies(self):
        fields = self.orders(self.src, "orders.fields.ts")
        self.assertIn('export const ordersDefaultSort = {"column": "placed_at", "direction": "desc"} as const;',
                      fields)
        self.assertIn(".order('placed_at', { ascending: false })", fields)
        model = json.loads(read(self.tmp / "model.json"))
        proposed = next(t for t in model["tables"] if t["name"] == "orders")["screens"]["default_sort"]
        self.assertIn(json.dumps({"column": proposed["column"], "direction": proposed["direction"]}),
                      self.orders(self.plain, "orders.fields.ts"))


class TheFormsAreWired(Answered):
    """DL-A9: the ids went to a wrapper's `data-describedby`, the radio group's
    `labelledBy` named nothing, every error was a live region, and nothing
    focused the summary."""

    def test_the_control_carries_the_ids_the_field_gives_the_error(self):
        for src in (self.src, self.tw):
            form = self.orders(src, "OrderForm.tsx")
            field = read(src / "ui" / "Field" / "Field.tsx")
            self.assertNotIn("data-describedby", field)
            self.assertNotIn("data-describedby", form)
            self.assertIn("const errorId = error ? `${id}-error` : undefined;", field)
            for name in ("reference", "notes", "total_cents"):
                self.assertIn(f"aria-describedby={{errors.{name} ? fieldId('{name}') + '-error' : undefined}}",
                              form)
                self.assertIn(f"aria-invalid={{Boolean(errors.{name}) || undefined}}", form)
        kit = read(self.src / "ui" / "index.ts")
        self.assertIn("export { Field, describedBy } from './Field/Field';", kit)

    def test_the_radio_group_is_a_fieldset_whose_legend_has_the_id_it_names(self):
        form = self.orders(self.src, "OrderForm.tsx")
        field = read(self.src / "ui" / "Field" / "Field.tsx")
        self.assertRegex(form, r"<Field\s+id=\{fieldId\('priority'\)\}[\s\S]*?disabled=\{disabled\}\s+group\s*>")
        self.assertIn("labelledBy={fieldId('priority') + '-label'}", form)
        self.assertIn("describedBy={errors.priority ? fieldId('priority') + '-error' : undefined}", form)
        self.assertIn("invalid={Boolean(errors.priority)}", form)
        self.assertIn("const Root = group ? 'fieldset' : 'div';", field)
        self.assertIn("<legend className={cn(styles.label, styles.groupLabel)} id={`${id}-label`}>", field)
        control = read(self.src / "ui" / "Control" / "Control.tsx")
        self.assertIn("aria-describedby={describedBy}", control)
        self.assertIn("aria-invalid={invalid || undefined}", control)

    def test_the_summary_is_the_one_live_region_and_takes_focus(self):
        form = self.orders(self.src, "OrderForm.tsx")
        field = read(self.src / "ui" / "Field" / "Field.tsx")
        self.assertNotIn('role="alert"', field)
        self.assertEqual(form.count('role="alert"'), 2, "the summary and the form-level error")
        self.assertIn('role="alert" tabIndex={-1} ref={summaryRef}', form)
        self.assertIn("summaryRef.current?.focus();", form)
        self.assertIn("import { useEffect, useRef, useState } from 'react';", form)

    def test_the_summary_focuses_once_per_attempt_whatever_the_count_does(self):
        """Review of #64 (Codex, CodeRabbit): the effect watched only the error
        count, so a second submit with the same number of errors, or with the
        errors already showing, moved nothing; and a clean save left the flag
        set for a later blur error to steal focus."""
        form = self.orders(self.src, "OrderForm.tsx")
        self.assertIn("const [attempt, setAttempt] = useState(0);", form)
        self.assertIn("setAttempt((n) => n + 1);\n        onSubmit();", form)
        self.assertIn("if (attempt > focusedFor.current && invalid.length > 0) {", form)
        self.assertIn("}, [attempt, invalid.length]);", form)
        self.assertIn("if (!submitting && invalid.length === 0) focusedFor.current = attempt;", form)
        self.assertNotIn("focusSummary", form)

    def test_a_boolean_control_carries_its_error_too(self):
        """Review of #64 (Codex): the switch and checkbox branch skipped Field
        and the common attributes, so a boolean field's error was neither
        shown nor referenced."""
        for src in (self.src, self.tw):
            form = self.orders(src, "OrderForm.tsx")
            self.assertRegex(form, r"<Toggle\s+id=\{fieldId\('is_rush'\)\}[\s\S]*?"
                                   r"aria-invalid=\{Boolean\(errors\.is_rush\) \|\| undefined\}\s+"
                                   r"aria-describedby=\{errors\.is_rush \? fieldId\('is_rush'\) \+ '-error' : undefined\}")
            self.assertIn("id={fieldId('is_rush') + '-error'}", form)
            self.assertIn("{errors.is_rush}", form)
            self.assertIn("data-state={errors.is_rush ? 'error' : undefined}", form)
        self.assertIn(".fieldError {", read(self.src / "features" / "orders" / "OrderForm.module.css"))
        self.assertIn("text-danger-fg", self.orders(self.tw, "OrderForm.tsx"))

    def test_the_reference_says_where_each_attribute_goes(self):
        """Review of #64 (CodeRabbit): "assistive tech ignores them on a
        wrapper" overstated it; aria-describedby describes its own element."""
        text = read(SKILLS / "content-model-to-ui" / "references" / "screen-patterns.md")
        self.assertNotIn("assistive tech ignores them on a wrapper", text)
        self.assertIn("`aria-describedby` describes the element that carries it and does not reach its "
                      "descendants", text)

    def test_both_stacks_pass_the_audit_and_the_static_a11y_check(self):
        proc = run_py("web-design-studio", "audit_design", "src", "tw", "plain", "--strict", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        for src in ("src", "tw"):
            proc = run_py("a11y-audit-runner", "a11y_static", f"{src}/ui", f"{src}/features", "--json",
                          cwd=self.tmp)
            report = json.loads(proc.stdout)
            self.assertEqual(report["errors"], 0, f"{output(proc)}\n{json.dumps(report, indent=2)}")


class TheServerSchemaMirrorsTheConstraints(Answered):
    """DL-B2's remainder: a zod and a pydantic schema of the Draft, from the
    same rules the form reads, with the mapper's inventions marked."""

    def zod(self, src=None):
        return read((src or self.src) / "server" / "orders.schema.ts")

    def pydantic(self, src=None):
        return read((src or self.src) / "server" / "orders_schema.py")

    def test_the_zod_schema_is_the_drafts_columns_with_their_constraints(self):
        zod = self.zod()
        self.assertIn("import { z } from 'zod';", zod)
        self.assertIn("export const orderDraftSchema = z.object({", zod)
        self.assertIn("  reference: z.string().trim().min(1).max(24),", zod)
        self.assertIn('  category: z.enum(["retail", "wholesale"]),', zod)
        self.assertIn('  priority: z.enum(["low", "normal", "high"]).optional(),', zod)
        self.assertIn("  total_cents: z.number().int().min(0),\n", zod)
        self.assertIn("  deposit: z.number().min(0).nullable().optional(), // invented: min", zod)
        self.assertIn("  placed_at: z.string().datetime({ offset: true }).optional(),", zod)
        self.assertIn("  ships_at: z.string().datetime({ offset: true }).nullable().optional(),", zod)
        self.assertIn("}).strict();", zod)
        self.assertIn("export type OrderDraftInput = z.infer<typeof orderDraftSchema>;", zod)
        self.assertIn("  supplier_id: z.string().uuid(),", zod)
        for absent in ("metadata", "  id:"):
            self.assertNotIn(absent, zod, "machine-only columns and the key are not the draft's")

    def test_the_check_makes_the_money_minimum_a_mirror_not_an_invention(self):
        self.assertNotIn("total_cents: z.number().int().min(0), //", self.zod())
        self.assertIn("deposit: Optional[Decimal] = Field(None, ge=0)  # invented: min", self.pydantic())

    def test_the_pydantic_schema_parses_and_matches(self):
        py = self.pydantic()
        ast.parse(py)
        self.assertIn("class OrderDraft(BaseModel):", py)
        self.assertIn("model_config = ConfigDict(extra='forbid')", py)
        self.assertIn("reference: str = Field(..., min_length=1, max_length=24)", py)
        self.assertIn("category: Literal['retail', 'wholesale'] = Field(...)", py)
        self.assertIn("priority: Literal['low', 'normal', 'high'] = Field(None)", py)
        self.assertIn("total_cents: int = Field(..., ge=0)\n", py)
        self.assertIn("placed_at: AwareDatetime = Field(None)", py)
        self.assertIn("ships_at: Optional[AwareDatetime] = Field(None)", py)
        self.assertIn("from pydantic import AwareDatetime, BaseModel, ConfigDict, Field", py)
        self.assertNotIn("from datetime import", py)
        self.assertIn("from uuid import UUID", py)

    def test_an_omittable_not_null_column_refuses_null_and_an_instant_needs_its_offset(self):
        """Review of #64 (Codex, CodeRabbit): a NOT NULL column with a default
        became `Optional[...]`, so pydantic took an explicit null the database
        refuses and the zod schema rejects; and a `timestamptz` was a plain
        `datetime`, which takes a wall time with no offset."""
        py = self.pydantic()
        self.assertIn("priority: Literal['low', 'normal', 'high'] = Field(None)", py)
        self.assertIn("is_rush: bool = Field(None)", py)
        self.assertNotIn("Optional[Literal", py)
        zod = self.zod()
        self.assertIn("priority: z.enum([\"low\", \"normal\", \"high\"]).optional(),", zod)
        self.assertIn("is_rush: z.boolean().optional(),", zod)

    def test_an_exclusive_check_bound_is_a_strict_bound_in_both_schemas(self):
        """Review of #64 (Codex): `CHECK (col > n)` became `exclusiveMin` in the
        model and was dropped before either emitter ran."""
        self.assertIn("discount: z.number().gt(0).lt(1).nullable().optional(),", self.zod())
        self.assertIn("discount: Optional[Decimal] = Field(None, gt=0, lt=1)", self.pydantic())
        fields = self.orders(self.src, "orders.fields.ts")
        self.assertIn("exclusiveMin: 0,", fields)
        self.assertIn("exclusiveMax: 1,", fields)
        py = self.pydantic()
        self.assertIn("supplier_id: UUID = Field(...)", py)
        self.assertNotIn("metadata", py)

    def test_the_unanswered_money_column_is_an_integer_only_when_the_type_says_so(self):
        plain = self.zod(self.plain)
        self.assertIn("total_cents: z.number().int().min(0)", plain)
        self.assertIn("deposit: z.number().min(0).nullable().optional()", plain)

    def test_a_reserved_column_name_is_aliased_in_pydantic(self):
        mod = load_script("content-model-to-ui", "scaffold_ui")
        table = {"name": "rows", "primary_key": ["id"], "screens": {}, "relationships": [],
                 "columns": [{"name": "class", "type": "text", "nullable": False,
                              "ui": {"control": "text-input", "placement": {"form": True},
                                     "validation": [{"rule": "required", "value": True, "mirror": True}]}}]}
        py = mod.emit_schema_pydantic(table, {"enums": {}}, mod.Answers(None))
        self.assertIn("class_: str = Field(..., min_length=1, alias='class')", py)
        ast.parse(py)

    def test_an_email_column_gets_the_format_both_sides(self):
        src = self.src
        zod = read(src / "server" / "suppliers.schema.ts")
        self.assertIn("contact_email: z.string().email().nullable().optional(), // invented: format", zod)
        py = read(src / "server" / "suppliers_schema.py")
        self.assertRegex(py, r"contact_email: Optional\[str\] = Field\(None, pattern=r'\^\[\^@\\s\]\+@")
        self.assertIn("# invented: format", py)

    def test_pydantic_itself_accepts_a_draft_the_database_would(self):
        try:
            import pydantic  # noqa: F401
        except ImportError:
            self.skipTest("pydantic is not installed here")
        script = (
            "import sys; sys.path.insert(0, 'src/server')\n"
            "from pydantic import ValidationError\n"
            "from orders_schema import OrderDraft\n"
            "SID = '0f6b3a52-4c0e-4e4e-9c1e-6a8d2b6f0a11'\n"
            "OrderDraft(supplier_id=SID, reference='A-1', category='retail', total_cents=0)\n"
            "OrderDraft(supplier_id=SID, reference='A-1', category='retail', total_cents=0,\n"
            "           placed_at='2026-10-07T10:00:00+02:00', discount='0.250')\n"
            "for bad in ({'reference': 'x' * 25, 'category': 'retail', 'total_cents': 1},\n"
            "            {'reference': 'A', 'category': 'retail', 'total_cents': -1},\n"
            "            {'reference': 'A', 'category': 'bulk', 'total_cents': 1},\n"
            "            {'reference': 'A', 'category': 'retail', 'total_cents': 1, 'supplier_id': 'x'},\n"
            "            {'reference': 'A', 'category': 'retail', 'total_cents': 1, 'metadata': {}},\n"
            "            {'reference': 'A', 'category': 'retail', 'total_cents': 1, 'placed_at': None},\n"
            "            {'reference': 'A', 'category': 'retail', 'total_cents': 1, 'is_rush': None},\n"
            "            {'reference': 'A', 'category': 'retail', 'total_cents': 1,\n"
            "             'placed_at': '2026-10-07T10:00:00'},\n"
            "            {'reference': 'A', 'category': 'retail', 'total_cents': 1, 'discount': 1},\n"
            "            {'reference': 'A', 'category': 'retail', 'total_cents': 1, 'discount': 0}):\n"
            "    bad.setdefault('supplier_id', SID)\n"
            "    try:\n        OrderDraft(**bad)\n    except ValidationError:\n        pass\n"
            "    else:\n        raise SystemExit('accepted ' + repr(bad))\n"
            "print('ok')\n")
        proc = subprocess.run([sys.executable, "-B", "-c", script], cwd=self.tmp, capture_output=True,
                              env=env())
        self.assertEqual(proc.returncode, 0, output(proc))


class TheGeneratedTypeScriptParses(Answered):
    """The real compiler reads every generated .ts and .tsx (syntax: the kit
    is React, and no React types are installed with the tooling)."""

    def test_every_generated_file_is_valid_typescript(self):
        root = tool_modules("WDS_NODE_MODULES", "typescript")
        if root is None:
            self.skipTest("typescript is not installed (tooling/main) or WDS_NODE_MODULES is off")
        (self.tmp / "tscheck.js").write_bytes(TS_CHECK.encode())
        files = sorted(str(p.relative_to(self.tmp)) for out in ("src", "tw", "plain")
                       for p in (self.tmp / out).rglob("*.ts*"))
        self.assertGreater(len(files), 30)
        proc = subprocess.run(["node", "tscheck.js", *files], cwd=self.tmp, capture_output=True,
                              env=env(NODE_PATH=root))
        self.assertEqual(proc.returncode, 0, output(proc))


if __name__ == "__main__":
    unittest.main()
