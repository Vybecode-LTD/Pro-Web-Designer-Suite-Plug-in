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
import subprocess
import sys
import unittest

from wds_support import REPO, SKILLS, TempDirTest, class_temp_dir, env, load_script, output, run_py, tool_modules

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
            with self.subTest(src=src):
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
        # The primary key is the tiebreak, in the constant and the query
        # (CodeRabbit on #210): equal times would page with a skip or a repeat.
        self.assertIn('export const ordersDefaultSort = '
                      '{"column": "placed_at", "direction": "desc", "tiebreak": "id"} as const;', fields)
        self.assertIn(".order('placed_at', { ascending: false }).order('id', { ascending: false })",
                      fields)
        model = json.loads(read(self.tmp / "model.json"))
        proposed = next(t for t in model["tables"] if t["name"] == "orders")["screens"]["default_sort"]
        self.assertIn(json.dumps({"column": proposed["column"], "direction": proposed["direction"],
                                  "tiebreak": proposed["tiebreak"]}),
                      self.orders(self.plain, "orders.fields.ts"))


class TheFormsAreWired(Answered):
    """DL-A9: the ids went to a wrapper's `data-describedby`, the radio group's
    `labelledBy` named nothing, every error was a live region, and nothing
    focused the summary."""

    def test_the_control_carries_the_ids_the_field_gives_the_error(self):
        for src in (self.src, self.tw):
            with self.subTest(src=src):
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
            with self.subTest(src=src):
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
            with self.subTest(src=src):
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
            with self.subTest(absent=absent):
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
            # CI runs this test once more with pydantic, and fails it there
            # rather than skipping (H15: it skipped on every CI cell).
            if os.environ.get("WDS_REQUIRE_PYDANTIC"):
                self.fail("WDS_REQUIRE_PYDANTIC is set, and pydantic is not installed")
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

    def test_ci_runs_the_pydantic_test_with_pydantic(self):
        """H15 (the owner's audit of 2026-10-14): the suite runs under `uv run
        --no-project`, which has no pydantic, so the test above skipped on every
        CI cell. A step of its own runs it with Pydantic 2, the major the
        scaffold writes for."""
        ci = REPO / ".github" / "workflows" / "ci.yml" if REPO else None
        if not (ci and ci.is_file()):
            self.skipTest("the repository's workflows are not here")
        steps = ci.read_text(encoding="utf-8").split("\n      - ")
        test = f"test_scaffold.{type(self).__name__}.test_pydantic_itself_accepts_a_draft_the_database_would"
        step = next((s for s in steps if test in s), "")
        self.assertIn('--with "pydantic>=2,<3"', step)
        self.assertIn('WDS_REQUIRE_PYDANTIC: "1"', step)
        self.assertIn("--python ${{ matrix.python }}", step)


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


class TheAuditsContentMediums(TempDirTest):
    """P54 part 6, the audit of 2026-10-14's §3.5: E1 to E5, the schema
    reader and the scaffold."""

    def introspect(self, name, text, *args):
        self.write(name, text)
        proc = run_py("content-model-to-ui", "introspect_schema", name, "-o", "model.json", *args, cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        return json.loads((self.tmp / "model.json").read_bytes())

    def column(self, model, table, name):
        return next(c for t in model["tables"] if t["name"] == table for c in t["columns"] if c["name"] == name)

    def test_a_naive_system_timestamp_is_read_only(self):
        """E1: `system` was read in the `date` and `timestamptz` branches only, so
        a naive `created_at` (every Prisma `DateTime @default(now())`) became an
        editable datetime-picker in the form."""
        model = self.introspect("schema.sql", "CREATE TABLE notes (\n  id uuid PRIMARY KEY,\n"
                                "  created_at timestamp NOT NULL DEFAULT now(),\n"
                                "  remind_at timestamp,\n  seen_at timestamptz NOT NULL DEFAULT now()\n);\n")
        created = self.column(model, "notes", "created_at")["ui"]
        self.assertEqual(("readonly-timestamp", False, False),
                         (created["control"], created["editable"], created["placement"]["form"]))
        self.assertEqual("ambiguous", created["temporal"]["timezone"])          # the warning stays
        self.assertIn("notes.created_at.naive_timestamp", {q["id"] for q in model["questions"]})
        remind = self.column(model, "notes", "remind_at")["ui"]                  # the control: a user's own
        self.assertEqual(("datetime-picker", True), (remind["control"], remind["placement"]["form"]))
        prisma = self.introspect("schema.prisma", "model Note {\n  id String @id @default(uuid())\n"
                                 "  createdAt DateTime @default(now())\n}\n")
        self.assertEqual("readonly-timestamp", self.column(prisma, "Note", "createdAt")["ui"]["control"])

    def test_a_table_name_cannot_leave_the_output_folder(self):
        """E2: a table's name went into the output paths as it was, so `../evil`
        wrote above `features/` and `../../evil` left `--out`."""
        for name in ("../evil", "..\\evil", "../../evil", "a/b"):
            with self.subTest(name=name):
                model = self.introspect("schema.sql", f'CREATE TABLE "{name}" (\n  id uuid PRIMARY KEY,\n  title text\n);\n')
                proc = run_py("content-model-to-ui", "scaffold_ui", "model.json", "--out", "out/src", cwd=self.tmp)
                self.assertEqual(2, proc.returncode, output(proc))
                self.assertIn("cannot name a file", output(proc))
                self.assertFalse((self.tmp / "out").exists())
                self.assertEqual(name, model["tables"][0]["name"])
        self.introspect("schema.sql", "CREATE TABLE posts (\n  id uuid PRIMARY KEY,\n  title text\n);\n")   # the control
        proc = run_py("content-model-to-ui", "scaffold_ui", "model.json", "--out", "out/src", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertTrue((self.tmp / "out" / "src" / "features" / "posts").is_dir())

    def test_an_odd_column_name_is_still_valid_code(self):
        """E3: a column `2fa` gave a TSX and a Python syntax error, and `it's`
        an unterminated string in the types file. `class`, `default`, `from`,
        `display-name` and `naïve` already worked: they are the controls."""
        names = ["2fa", "it's", "class", "default", "from", "display-name", "naïve"]
        ddl = ("CREATE TABLE odd (\n  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),\n"
               + "".join(f'  "{n}" text NOT NULL,\n' for n in names) + "  title text\n);\n")
        self.introspect("schema.sql", ddl)
        proc = run_py("content-model-to-ui", "scaffold_ui", "model.json", "--out", "src", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        for py in (self.tmp / "src").rglob("*.py"):
            compile(py.read_bytes(), str(py), "exec")
        form = (self.tmp / "src" / "features" / "odd" / "OddForm.tsx").read_bytes().decode("utf-8")
        self.assertIn("errors['2fa']", form)
        self.assertIn("fieldId('it\\'s')", form)
        root = tool_modules("WDS_NODE_MODULES", "typescript")
        if root is None:
            self.skipTest("typescript is not installed (tooling/main) or WDS_NODE_MODULES is off")
        self.write("tscheck.js", TS_CHECK)
        files = sorted(str(p.relative_to(self.tmp)) for p in (self.tmp / "src").rglob("*.ts*"))
        self.assertGreater(len(files), 10)
        proc = subprocess.run(["node", "tscheck.js", *files], cwd=self.tmp, capture_output=True,
                              env=env(NODE_PATH=root))
        self.assertEqual(0, proc.returncode, output(proc))

    def test_casts_claims_and_quoted_names_pin_the_column(self):
        """E4: `auth.uid()::text = owner_id::text`, `(auth.jwt() ->> 'sub')::uuid
        = owner_id` and `auth.uid() = "ownerId"` pin the column, but were read as
        leaving it writable. A string or an array is still no pin."""
        table = ('CREATE TABLE posts (\n  id uuid PRIMARY KEY,\n  owner_id uuid NOT NULL,\n'
                 '  "ownerId" uuid,\n  title text\n);\nALTER TABLE posts ENABLE ROW LEVEL SECURITY;\n')
        cases = (("auth.uid()::text = owner_id::text AND auth.uid() = \"ownerId\"", False),
                 ("(auth.jwt() ->> 'sub')::uuid = owner_id AND \"ownerId\"::text = (select auth.uid())::text", False),
                 ("owner_id = 'auth.uid()' AND auth.uid() = \"ownerId\"", True),            # a string calls nothing
                 ("auth.uid() = any(array[owner_id]) AND auth.uid() = \"ownerId\"", True))   # nor is it the column
        for check, warned in cases:
            with self.subTest(check=check):
                model = self.introspect("schema.sql", table + "CREATE POLICY p ON posts FOR UPDATE TO "
                                        f"authenticated USING ({check});\n")
                codes = {f["code"] for f in model["security"]["findings"]}
                self.assertEqual(warned, "authority-writable" in codes, model["security"]["findings"])

    def test_a_with_rls_table_is_drizzle(self):
        """E5: `detect_format` looked for `pgTable(` while the Drizzle reader
        accepts `pgTable.withRLS(`, so such a schema went to the generated-types
        reader and failed."""
        model = self.introspect("schema.ts", 'import { pgTable, uuid, text } from "drizzle-orm/pg-core";\n'
                                'export const posts = pgTable.withRLS("posts", {\n'
                                '  id: uuid("id").primaryKey(),\n  title: text("title"),\n});\n')
        self.assertEqual(["posts"], [t["name"] for t in model["tables"]])


# P73 (N67), the audit of 2026-10-28's PY-A findings in the scaffold: tables
# with no textual column, a naive and an aware timestamp, a radio group, a
# state word with no closed set, a reference with no label answer, a key that
# is no identifier, and copy and labels with quotes and markup in them.
EDGE_DDL = """\
CREATE TABLE sensors (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL
);
CREATE TABLE readings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  sensor_id uuid NOT NULL REFERENCES sensors(id),
  value numeric NOT NULL,
  taken_at timestamp NOT NULL,
  checked_at timestamptz
);
CREATE TABLE shows (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL,
  size text NOT NULL CHECK (size IN ('s', 'm', 'l')),
  status text NOT NULL,
  is_live boolean NOT NULL DEFAULT false
);
CREATE TABLE line_items (
  "order-id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  qty integer NOT NULL
);
"""

EDGE_ANSWERS = {
    "shows.empty_state": {"headline": 'No "shows" yet', "body": "Book one & sell it", "action": "Add {one}"},
    "shows.field_groups": [{"legend": "Size <and> status", "fields": ["title", "size", "status", "is_live"]}],
}

# Labels a person wrote into model.json by hand.
EDGE_LABELS = {"shows.title": 'Title "working"', "shows.is_live": 'Live & "public"'}

# lib/format.ts's converters, each call in argv[3] ([name, ...args]) run in
# the zone the test sets, and its result printed.
FORMAT_RUN = r"""
const ts = require('typescript');
const fs = require('fs');
const js = ts.transpileModule(fs.readFileSync(process.argv[2], 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const mod = { exports: {} };
new Function('module', 'exports', js)(mod, mod.exports);
console.log(JSON.stringify(JSON.parse(process.argv[3]).map(([name, ...args]) => mod.exports[name](...args))));
"""


def scaffold_edges(tmp: pathlib.Path, out: str, *args: str) -> pathlib.Path:
    """EDGE_DDL scaffolded into `out`, with EDGE_ANSWERS and EDGE_LABELS."""
    (tmp / "edges.sql").write_bytes(EDGE_DDL.encode())
    proc = run_py("content-model-to-ui", "introspect_schema", "edges.sql", "-o", "edges.json", cwd=tmp)
    assert proc.returncode == 0, output(proc)
    model = json.loads((tmp / "edges.json").read_bytes())
    for table in model["tables"]:
        for col in table["columns"]:
            col["ui"]["label"] = EDGE_LABELS.get(f"{table['name']}.{col['name']}", col["ui"].get("label"))
    (tmp / "edges.json").write_bytes(json.dumps(model).encode())
    (tmp / "edges-answers.json").write_bytes(json.dumps(EDGE_ANSWERS).encode())
    proc = run_py("content-model-to-ui", "scaffold_ui", "edges.json", "--out", out,
                  "--answers", "edges-answers.json", *args, cwd=tmp)
    assert proc.returncode == 0, output(proc)
    return tmp / out


class TheScaffoldsEdgeCases(unittest.TestCase):
    """P73: EDGE_DDL in React, as the form edits a draft and as it posts to
    the server's actions."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = class_temp_dir(cls, "wds-edges-")
        cls.src = scaffold_edges(cls.tmp, "src")
        cls.posted = scaffold_edges(cls.tmp, "posted", "--server-actions")

    def feature(self, table: str, name: str, src: pathlib.Path | None = None) -> str:
        return read((src or self.src) / "features" / table / name)

    def test_a_table_with_no_title_still_links_each_row_to_its_detail(self):
        """PY-A-6: the link sat on the title's cell alone, and a placeholder
        key is never listed, so the rows of a table with no textual column
        could not be opened."""
        for table, first in (("readings", "sensor_id"), ("line_items", "qty")):
            with self.subTest(table=table):
                listing = self.feature(table, f"{''.join(p.title() for p in table.split('_'))}List.tsx")
                body = listing.split("<tbody>")[1]
                self.assertEqual(1, body.count("<a "), body)
                self.assertRegex(body, r"<td className=\{cn\([^)]*styles\.sticky\)\}><a className=\{styles\.link\} "
                                       rf"href=\{{'/{table}/' \+ String\([^)]*\)\}}>\{{row\.{first}\b")
                self.assertIn('<th className={cn(styles.th, styles.sticky)} scope="col">', listing)
        # The control: a listed title keeps the link.
        shows = self.feature("shows", "ShowsList.tsx").split("<tbody>")[1]
        self.assertIn("href={'/shows/' + String(row.id)}>{row.title}</a>", shows)

    def test_a_naive_timestamp_takes_a_wall_time_and_an_aware_one_its_instant(self):
        """PY-A-10: zod wanted an offset on every instant, which a naive
        `timestamp` cannot carry and a `datetime-local` input never sends, so
        neither column's draft could pass; pydantic took the naive one."""
        zod = read(self.src / "server" / "readings.schema.ts")
        self.assertIn("  taken_at: z.string().datetime({ offset: true, local: true }),", zod)
        self.assertIn("  checked_at: z.string().datetime({ offset: true }).nullable().optional(),", zod)
        py = read(self.src / "server" / "readings_schema.py")
        self.assertIn("    taken_at: datetime = Field(...)", py)
        self.assertIn("    checked_at: Optional[AwareDatetime] = Field(None)", py)
        form = self.feature("readings", "ReadingForm.tsx")
        self.assertIn("import { fromLocalInput, toLocalInput } from '../../lib/format';", form)
        self.assertIn("value={toLocalInput(values.checked_at)}", form)
        self.assertIn("onChange={(e) => onChange('checked_at', fromLocalInput(e.target.value, values.checked_at))}", form)
        self.assertIn("value={String(values.taken_at ?? '')}", form, "a wall time goes as typed")
        posted = self.feature("readings", "ReadingForm.tsx", self.posted)
        self.assertIn("<input type=\"hidden\" name=\"checked_at\" value={String(values.checked_at ?? '')} />",
                      posted)
        self.assertEqual(1, posted.count('name="checked_at"'), "the input the user types in posts nothing")
        self.assertNotIn("TODO(time zone)", read(self.posted / "server" / "readings.actions.ts"))
        self.assertNotIn("lib/format", self.feature("shows", "ShowForm.tsx"), "a form with no instant imports none")
        self.assertEqual(["2026-10-28T13:00:00.000Z", "2026-12-01T14:00:00.000Z", "2026-10-28T09:00", None, "", ""],
                         self.converters(["fromLocalInput", "2026-10-28T09:00"], ["fromLocalInput", "2026-12-01T09:00"],
                                         ["toLocalInput", "2026-10-28T13:00:00.000Z"], ["fromLocalInput", ""],
                                         ["toLocalInput", None], ["toLocalInput", "soon"]),
                         "the offset is the browser's, on the day typed")

    def converters(self, *calls):
        """lib/format.ts's converters, called in New York."""
        root = tool_modules("WDS_NODE_MODULES", "typescript")
        if root is None:
            self.skipTest("typescript is not installed (tooling/main) or WDS_NODE_MODULES is off")
        (self.tmp / "format_run.cjs").write_bytes(FORMAT_RUN.encode())
        proc = subprocess.run(["node", "format_run.cjs", str(self.src / "lib" / "format.ts"), json.dumps(calls)],
                              cwd=self.tmp, capture_output=True, env=env(NODE_PATH=root, TZ="America/New_York"))
        self.assertEqual(0, proc.returncode, output(proc))
        return json.loads(proc.stdout)

    def test_a_wall_time_the_clocks_skip_or_repeat_keeps_its_instant(self):
        """CodeRabbit on #230: New York skips 02:00 to 03:00 on 2026-03-08 and
        repeats 01:00 to 02:00 on 2026-11-01. Date read a skipped 02:30 as
        03:30 and a repeated 01:30 as its first occurrence, so either saved
        another instant than the one meant, without a word."""
        self.assertIn("onChange={(e) => onChange('checked_at', fromLocalInput(e.target.value, values.checked_at))}",
                      self.feature("readings", "ReadingForm.tsx"), "the draft's own instant goes with the edit")
        self.assertEqual(
            ["2026-03-08T02:30", "2026-03-08T02:30",
             "2026-11-01T05:30:00.000Z", "2026-11-01T06:30:00.000Z", "2026-11-01T05:30:00.000Z",
             "2026-11-01T06:30:00.000Z"],
            self.converters(["fromLocalInput", "2026-03-08T02:30"],        # skipped: kept as typed, so refused
                            ["toLocalInput", "2026-03-08T02:30"],          # and shown as typed
                            ["fromLocalInput", "2026-11-01T01:30"],        # repeated, nothing held: the first
                            ["fromLocalInput", "2026-11-01T01:30", "2026-11-01T06:10:00.000Z"],   # held in EST
                            ["fromLocalInput", "2026-11-01T01:30", "2026-11-01T05:10:00.000Z"],   # held in EDT
                            ["fromLocalInput", "2026-11-01T01:30", "2026-11-01T06:30:00+00:00"]))

    def test_the_error_summary_can_reach_a_radio_group(self):
        """PY-A-11: the summary links each entry to its field's id, and no
        element of a radio group had it: the fieldset took none, the legend
        `-label`."""
        field = read(self.src / "ui" / "Field" / "Field.tsx")
        self.assertRegex(field, r"<Root\s+className=\{[^}]*\}\s+id=\{group \? id : undefined\}")
        form = self.feature("shows", "ShowForm.tsx")
        self.assertRegex(form, r"<Field\s+id=\{fieldId\('size'\)\}[\s\S]*?\s+group\s*>\s*<RadioGroup")
        self.assertIn("href={'#' + fieldId(name)}", form)

    def test_a_state_word_with_no_closed_set_is_a_text_box_with_a_note(self):
        """PY-A-14: a select with no options at all shipped for every `status`
        with no CHECK, no enum and no `.options` answer."""
        form = self.feature("shows", "ShowForm.tsx")
        at = form.index("<Field\n          id={fieldId('status')}")
        block = form[at:form.index("</Field>", at)]
        self.assertIn('<TextInput\n            type="text"', block)
        self.assertNotIn("<Select", form)
        self.assertNotIn("Select", form.split("\n")[1], "the kit import")
        self.assertIn("no closed set is known, so this is a text box: answer the `.options` question",
                      form[:at].rsplit("{/* review: ", 1)[1])
        self.assertRegex(self.feature("shows", "shows.fields.ts"),
                         r'name: "status",\s+label: "[^"]*",\s+control: "text-input",')
        # A reference's options are its parent's rows, answered or not.
        readings = self.feature("readings", "ReadingForm.tsx")
        self.assertIn("{/* TODO(options): one <option> per `sensors` row; answer the `.label_column` question",
                      readings)

    def test_a_key_that_is_no_identifier_is_bracketed_in_react_too(self):
        """PY-A-16: React wrote `row.<key>` where Vue and Svelte bracket a
        name like `order-id`, which reads as a subtraction."""
        listing = self.feature("line_items", "LineItemsList.tsx")
        self.assertIn("key={String(row['order-id'])}", listing)
        self.assertIn("href={'/line_items/' + String(row['order-id'])}", listing)
        detail = self.feature("line_items", "LineItemDetail.tsx")
        self.assertIn("{record['order-id']}", detail)
        for name, text in (("list", listing), ("detail", detail)):
            with self.subTest(file=name):
                self.assertNotIn(".order-id", text)

    def test_quoted_copy_and_labels_stay_one_attribute(self):
        """PY-A-17: answers and labels went into JSX attributes and text as
        they were, so a quote ended the attribute and a `{` began code."""
        states = self.feature("shows", "ShowsStates.tsx")
        self.assertIn('headline={"No \\"shows\\" yet"}', states)
        self.assertIn('body={"Book one & sell it"}', states)
        self.assertIn('{"Add {one}"}', states)
        form = self.feature("shows", "ShowForm.tsx")
        self.assertIn('label={"Title \\"working\\""}', form)
        self.assertIn('label={"Live & \\"public\\""}', form)
        self.assertIn('<legend className={styles.legend}>{"Size <and> status"}</legend>', form)
        self.assertIn('label="Size"', form, "plain text stays a plain attribute")

    def test_the_output_parses_and_passes_the_gates(self):
        proc = run_py("web-design-studio", "audit_design", "src", "posted", "--strict", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        for src in ("src", "posted"):
            with self.subTest(src=src):
                proc = run_py("a11y-audit-runner", "a11y_static", f"{src}/ui", f"{src}/features", "--json",
                              cwd=self.tmp)
                self.assertEqual(json.loads(proc.stdout)["errors"], 0, output(proc))
        root = tool_modules("WDS_NODE_MODULES", "typescript")
        if root is None:
            self.skipTest("typescript is not installed (tooling/main) or WDS_NODE_MODULES is off")
        (self.tmp / "tscheck.js").write_bytes(TS_CHECK.encode())
        files = sorted(str(p.relative_to(self.tmp)) for out in ("src", "posted")
                       for p in (self.tmp / out).rglob("*.ts*"))
        self.assertGreater(len(files), 40)
        proc = subprocess.run(["node", "tscheck.js", *files], cwd=self.tmp, capture_output=True,
                              env=env(NODE_PATH=root))
        self.assertEqual(proc.returncode, 0, output(proc))


# The generated actions, run in Node against stand-ins for Next.js, the
# server's Supabase client and the zod schema: the schema accepts a draft with a
# reference and refuses one without, as the real one does for that column.
ACTION_RUN = r"""
const ts = require('typescript');
const fs = require('fs');
const calls = [];
const source = fs.readFileSync(process.argv[2], 'utf8');
const js = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const stubs = {
  'next/cache': { revalidatePath: (path) => calls.push(['revalidate', path]) },
  '../lib/supabase.server': {
    createClient: async () => ({
      from: (table) => ({
        insert: async (row) => (calls.push(['insert', table, row]), { error: null }),
        update: (row) => ({
          eq: async (column, key) => (calls.push(['update', table, row, column, key]), { error: null }),
        }),
      }),
    }),
  },
  './orders.schema': {
    orderDraftSchema: {
      safeParse: (v) => v.reference
        ? { success: true, data: v }
        : { success: false, error: { issues: [{ path: ['reference'], message: 'Required' }] } },
    },
  },
};
const mod = { exports: {} };
new Function('require', 'module', 'exports', js)((name) => stubs[name], mod, mod.exports);
const { createOrder, updateOrder } = mod.exports;
const initial = { values: {}, errors: {}, submitError: null };
(async () => {
  const form = new FormData();
  form.set('supplier_id', 's-1');
  form.set('reference', 'PO-7');
  form.set('total_cents', '1250');
  form.set('deposit', '');
  form.set('is_rush', 'on');
  form.set('notes', '');
  const created = await createOrder(initial, form);
  const refused = await createOrder(initial, new FormData());
  const updated = await updateOrder('o-1', initial, form);
  console.log(JSON.stringify({ created, refused, updated, calls }));
})();
"""


class TheServerActions(unittest.TestCase):
    """--server-actions (P37 part 4, DL-B3): the form posts its FormData to a
    'use server' function through React 19's <form action>, useActionState
    holds the result and useFormStatus the button's pending state."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = class_temp_dir(cls, "wds-actions-")
        cls.src = scaffold(cls.tmp, "src", "--server-actions", answers=ANSWERS)
        cls.tw = scaffold(cls.tmp, "tw", "--server-actions", "--stack", "tailwind", answers=ANSWERS)
        cls.plain = scaffold(cls.tmp, "plain", answers=ANSWERS)

    def test_the_flag_writes_the_actions_and_the_next_clients(self):
        for name in ("features/orders/OrderActionForm.tsx", "server/orders.actions.ts",
                     "server/suppliers.actions.ts", "lib/supabase.server.ts"):
            with self.subTest(file=name):
                self.assertTrue((self.src / name).is_file())
                self.assertFalse((self.plain / name).exists())
        self.assertIn("export { OrderActionForm } from './OrderActionForm';",
                      read(self.src / "features" / "orders" / "index.ts"))
        browser = read(self.src / "lib" / "supabase.ts")
        self.assertIn("createBrowserClient<Database>(url, publishableKey)", browser)
        self.assertIn("process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", browser)
        self.assertNotIn("import.meta.env", browser)
        server = read(self.src / "lib" / "supabase.server.ts")
        self.assertIn("createServerClient<Database>(", server)
        self.assertIn("const cookieStore = await cookies();", server)
        self.assertIn("import.meta.env.VITE_SUPABASE_URL", read(self.plain / "lib" / "supabase.ts"))

    def test_the_form_posts_to_the_action(self):
        for src in (self.src, self.tw):
            with self.subTest(src=src.name):
                form = read(src / "features" / "orders" / "OrderForm.tsx")
                self.assertTrue(form.startswith("'use client';\n"))
                self.assertIn("import { useFormStatus } from 'react-dom';", form)
                self.assertIn("const { pending } = useFormStatus();", form)
                self.assertIn("noValidate action={action}>", form)
                self.assertNotIn("onSubmit", form)
                # A control with no name is not posted: the toggle has one too.
                self.assertIn('id={fieldId(\'is_rush\')}\n            name="is_rush"', form)
        wrapper = read(self.src / "features" / "orders" / "OrderActionForm.tsx")
        self.assertIn("import { useActionState, useEffect, useState } from 'react';", wrapper)
        self.assertIn("const save = row ? updateOrder.bind(null, row.id) : createOrder;", wrapper)
        self.assertIn("useActionState(save, initial)", wrapper)

    def test_without_the_flag_the_form_is_unchanged(self):
        form = read(self.plain / "features" / "orders" / "OrderForm.tsx")
        self.assertTrue(form.startswith("import { useEffect, useRef, useState } from 'react';"))
        self.assertIn("onSubmit();", form)
        self.assertNotIn("useFormStatus", form)
        self.assertNotIn('name="is_rush"', form)

    def test_the_action_reads_each_field_by_its_type_validates_and_writes(self):
        root = tool_modules("WDS_NODE_MODULES", "typescript")
        if root is None:
            self.skipTest("typescript is not installed (tooling/main) or WDS_NODE_MODULES is off")
        (self.tmp / "action_run.cjs").write_bytes(ACTION_RUN.encode())
        proc = subprocess.run(["node", "action_run.cjs", str(self.src / "server" / "orders.actions.ts")],
                              cwd=self.tmp, capture_output=True, env=env(NODE_PATH=root))
        self.assertEqual(proc.returncode, 0, output(proc))
        got = json.loads(proc.stdout)
        draft = {"supplier_id": "s-1", "reference": "PO-7", "total_cents": 1250, "deposit": None,
                 "discount": None, "is_rush": True, "notes": None, "ships_at": None}
        self.assertEqual(got["created"], {"values": {}, "errors": {}, "submitError": None})
        self.assertEqual(got["refused"]["errors"], {"reference": "Required"})
        self.assertEqual(got["updated"]["values"], draft)
        self.assertEqual(got["calls"], [["insert", "orders", draft], ["revalidate", "/orders"],
                                        ["update", "orders", draft, "id", "o-1"], ["revalidate", "/orders"]])

    def test_the_output_parses_and_passes_the_gates(self):
        root = tool_modules("WDS_NODE_MODULES", "typescript")
        if root is not None:
            (self.tmp / "tscheck.js").write_bytes(TS_CHECK.encode())
            files = sorted(str(p.relative_to(self.tmp)) for out in ("src", "tw")
                           for p in (self.tmp / out).rglob("*.ts*"))
            proc = subprocess.run(["node", "tscheck.js", *files], cwd=self.tmp, capture_output=True,
                                  env=env(NODE_PATH=root))
            self.assertEqual(proc.returncode, 0, output(proc))
        proc = run_py("web-design-studio", "audit_design", "src", "tw", "--strict", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        for src in ("src", "tw"):
            with self.subTest(src=src):
                proc = run_py("a11y-audit-runner", "a11y_static", f"{src}/ui", f"{src}/features", "--json",
                              cwd=self.tmp)
                self.assertEqual(json.loads(proc.stdout)["errors"], 0, output(proc))


if __name__ == "__main__":
    unittest.main()
