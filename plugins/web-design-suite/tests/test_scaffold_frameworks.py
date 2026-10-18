"""content-model-to-ui's scaffold in the other frameworks (P37 parts 5 and 6,
DL-B3): `--framework vue` writes the kit and every entity's screens as Vue 3.5
single-file components.

The schema and the answers are test_scaffold.py's. Each component is compiled
by the real compiler (`vue/compiler-sfc`: the template, the script with its
types resolved, and every style block), the form is rendered on the server
to read the ids and the aria wiring it really produces, and its summary's
focus is driven through the runtime with a minimal renderer: once per failed
attempt, never for a later blur. The output passes the audit (`--strict`) and
`a11y_static` with no error, as the React scaffold does.
"""

from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import unittest

from test_scaffold import ANSWERS, scaffold
from wds_support import class_temp_dir, env, load_script, output, run_py, tool_modules

# The Node side. `.vue` and `.ts` load through the compilers, so the
# components run as Vite would build them; `compile` reports every error the
# compilers give, `render` renders the form and drives its focus.
VUE_RUN = r"""
const fs = require('fs');
const path = require('path');
const Module = require('module');
const ts = require('typescript');
const sfc = require('vue/compiler-sfc');
sfc.registerTS(() => ts);

const problems = [];
const tsOptions = { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 };
const fsHost = { fileExists: fs.existsSync, readFile: (f) => fs.readFileSync(f, 'utf8'),
                 realpath: fs.realpathSync };

function transpile(code, file) {
  const out = ts.transpileModule(code, { reportDiagnostics: true, fileName: file + '.ts',
                                         compilerOptions: tsOptions });
  for (const d of out.diagnostics || []) {
    problems.push(file + ': ' + ts.flattenDiagnosticMessageText(d.messageText, ' '));
  }
  return out.outputText;
}

function compileVue(file) {
  const source = fs.readFileSync(file, 'utf8');
  const { descriptor, errors } = sfc.parse(source, { filename: file });
  for (const e of errors) problems.push(file + ': ' + (e.message || e));
  const id = 'v' + require('crypto').createHash('sha1').update(file).digest('hex').slice(0, 8);
  let script;
  try {
    script = sfc.compileScript(descriptor, { id, inlineTemplate: true, fs: fsHost });
  } catch (e) {
    problems.push(file + ': ' + e.message);
    return '';
  }
  for (const style of descriptor.styles) {
    const css = style.src ? fs.readFileSync(path.resolve(path.dirname(file), style.src), 'utf8')
                          : style.content;
    const out = sfc.compileStyle({ source: css, filename: file, id: 'data-v-' + id, scoped: style.scoped });
    for (const e of out.errors) problems.push(file + ' <style>: ' + (e.message || e));
  }
  return transpile(script.content, file);
}

Module._extensions['.vue'] = (module, file) => module._compile(compileVue(file), file);
Module._extensions['.ts'] = (module, file) => module._compile(transpile(fs.readFileSync(file, 'utf8'), file), file);

async function render(root) {
  const vue = require('vue');
  const { renderToString } = require('vue/server-renderer');
  const Form = require(path.join(root, 'features/orders/OrderForm.vue')).default;
  const errors = { reference: 'Required', priority: 'Choose one', is_rush: 'Rush is closed' };
  const html = await renderToString(vue.createSSRApp(Form, { values: { reference: '' }, errors }));

  // The focus, through the runtime. The kit is stubbed: the form's own
  // template holds the summary, its ref and the submit handler.
  const kit = new Proxy({}, { get: (_, name) => vue.defineComponent({
    name: String(name), inheritAttrs: false,
    setup: (_, { slots }) => () => vue.h('div', null, slots.default ? slots.default() : []) }) });
  const real = Module.prototype.require;
  Module.prototype.require = function (request) {
    return request === '../../ui' ? kit : real.apply(this, arguments);
  };
  delete require.cache[path.join(root, 'features/orders/OrderForm.vue')];
  const Stubbed = require(path.join(root, 'features/orders/OrderForm.vue')).default;
  Module.prototype.require = real;

  const focused = [];
  const node = (tag) => ({ tag, attrs: {}, on: {}, children: [], parent: null,
                           focus() { focused.push(this.attrs.class); } });
  const detach = (n) => { if (n.parent) n.parent.children.splice(n.parent.children.indexOf(n), 1); n.parent = null; };
  const { createApp } = vue.createRenderer({
    createElement: node,
    createText: (text) => ({ text, parent: null }),
    createComment: (text) => ({ comment: text, parent: null }),
    setText: (n, text) => { n.text = text; },
    setElementText: (n, text) => { n.children = [{ text, parent: n }]; },
    insert: (child, parent, anchor) => {
      detach(child);
      const at = anchor ? parent.children.indexOf(anchor) : -1;
      if (at < 0) parent.children.push(child); else parent.children.splice(at, 0, child);
      child.parent = parent;
    },
    remove: detach,
    parentNode: (n) => n.parent,
    nextSibling: (n) => (n.parent && n.parent.children[n.parent.children.indexOf(n) + 1]) || null,
    patchProp: (n, key, _prev, next) => {
      if (/^on[A-Z]/.test(key)) n.on[key.slice(2).toLowerCase()] = next;
      else if (next == null || next === false) delete n.attrs[key];
      else n.attrs[key] = next;
    },
  });
  const state = vue.reactive({ errors: {}, submitting: false, onSubmit: () => {} });
  const host = node('host');
  createApp({ render: () => vue.h(Stubbed, { values: {}, errors: state.errors, submitting: state.submitting,
                                              onSubmit: () => state.onSubmit() }) }).mount(host);
  const find = (n, tag) => n.tag === tag ? n : (n.children || []).map((c) => find(c, tag)).find(Boolean);
  const submit = async (then) => {
    state.onSubmit = then;
    find(host, 'form').on.submit({ preventDefault() {} });
    await vue.nextTick();
    return focused.length;
  };
  const steps = {};
  steps.failed = await submit(() => { state.errors = { reference: 'Required' }; });
  steps.again = await submit(() => {});
  steps.fixed = await submit(() => { state.errors = {}; });
  state.errors = { notes: 'Too long' };
  await vue.nextTick();
  steps.blur = focused.length;
  steps.pending = await submit(() => { state.submitting = true; state.errors = {}; });
  state.errors = { reference: 'Taken' };
  state.submitting = false;
  await vue.nextTick();
  steps.async = focused.length;
  return { html, steps, focused };
}

const [mode, ...rest] = process.argv.slice(2);
(async () => {
  let result = {};
  if (mode === 'compile') rest.forEach(compileVue);
  else if (mode === 'ssr') {
    // One component, with its props.
    const vue = require('vue');
    const { renderToString } = require('vue/server-renderer');
    const props = JSON.parse(rest[1]);
    const Comp = require(path.resolve(rest[0])).default;

    result = { html: await renderToString(vue.createSSRApp({ render: () => vue.h(Comp, props) })) };
  } else result = await render(path.resolve(rest[0]));
  console.log(JSON.stringify({ problems, ...result }));
  process.exit(problems.length ? 1 : 0);
})().catch((e) => { console.log(JSON.stringify({ problems: [String(e.stack || e)] })); process.exit(1); });
"""

ODD_DDL = """\
CREATE TABLE odd (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "2fa" boolean NOT NULL DEFAULT false,
  "it's" text NOT NULL,
  size text NOT NULL,
  title text
);
"""


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


class VueOutput(unittest.TestCase):
    """The schema scaffolded as Vue with the answers (css-modules and
    tailwind) and without them, once for the class."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = class_temp_dir(cls, "wds-vue-")
        cls.src = scaffold(cls.tmp, "src", "--framework", "vue", answers=ANSWERS)
        cls.tw = scaffold(cls.tmp, "tw", "--framework", "vue", "--stack", "tailwind", answers=ANSWERS)
        cls.plain = scaffold(cls.tmp, "plain", "--framework", "vue")

    def orders(self, src: pathlib.Path, name: str) -> str:
        return read(src / "features" / "orders" / name)

    def node(self, *args: str, ok: bool = True) -> dict:
        root = tool_modules("WDS_NODE_MODULES", "typescript", "vue")
        if root is None:
            self.skipTest("vue and typescript are not installed (tooling/main) or WDS_NODE_MODULES is off")
        (self.tmp / "vue_run.cjs").write_bytes(VUE_RUN.encode())
        proc = subprocess.run(["node", "vue_run.cjs", *args], cwd=self.tmp, capture_output=True,
                              env=env(NODE_PATH=root))
        self.assertEqual(proc.returncode == 0, ok, output(proc))
        return json.loads(proc.stdout)


class TheVueScaffold(VueOutput):

    def test_the_kit_and_the_screens_are_single_file_components(self):
        kit = ["Button/Button", "Field/Field", "Badge/Badge", "Skeleton/Skeleton", "StateBlock/StateBlock"] + [
            f"Control/{c}" for c in ("TextInput", "NumberInput", "TextArea", "Select", "Toggle",
                                     "RadioGroup", "ControlStub")]
        screens = ["OrdersList", "OrderDetail", "OrderForm"] + [
            f"Orders{s}" for s in ("Empty", "FilteredEmpty", "Loading", "Error", "Forbidden", "Stale")]
        for src in (self.src, self.tw):
            with self.subTest(src=src.name):
                self.assertEqual([], sorted(str(p.relative_to(src)) for p in src.rglob("*.tsx")))
                self.assertEqual([], sorted(str(p.relative_to(src)) for p in src.rglob("*.module.css")))
                files = [src / "ui" / f"{k}.vue" for k in kit] + [
                    src / "features" / "orders" / f"{s}.vue" for s in screens]
                for f in files:
                    self.assertTrue(read(f).startswith('<script setup lang="ts">\n'), f)
                for name in ("orders.types.ts", "orders.fields.ts", "index.ts"):
                    self.assertTrue((src / "features" / "orders" / name).is_file())
        index = read(self.src / "features" / "orders" / "index.ts")
        self.assertIn("export { default as OrderForm } from './OrderForm.vue';", index)
        self.assertIn("OrderDetailState } from './orders.types';", index)
        self.assertIn("export type OrderDetailState =", self.orders(self.src, "orders.types.ts"))
        self.assertIn("export { default as TextInput } from './Control/TextInput.vue';",
                      read(self.src / "ui" / "index.ts"))
        self.assertTrue((self.tw / "styles" / "scaffold.css").is_file())
        self.assertFalse((self.src / "styles" / "scaffold.css").exists())

    def test_each_style_block_is_scoped_inside_the_components_layer(self):
        """stack-frameworks.md §1 and §3: an unlayered scoped style beats
        every layer; and Vue puts a parent's scope on a child's root, so no
        root is a bare `.root`."""
        for f in [*self.src.rglob("*.vue")]:
            text = read(f)
            with self.subTest(file=f.name):
                styles = re.findall(r"<style([^>]*)>([\s\S]*?)</style>", text)
                for attrs, body in styles:
                    self.assertIn("scoped", attrs)
                    if 'src="./Control.css"' in attrs:
                        body = read(f.parent / "Control.css")
                    self.assertTrue(body.lstrip().startswith("@layer components {"), body[:80])
                    self.assertNotRegex(body, r"\.root(?![\w-])")
        self.assertIn('class="ui-button"', read(self.src / "ui" / "Button" / "Button.vue"))
        self.assertIn(".ui-button[data-variant=\"primary\"]", read(self.src / "ui" / "Button" / "Button.vue"))
        self.assertIn('<style scoped src="./Control.css"></style>',
                      read(self.src / "ui" / "Control" / "TextInput.vue"))
        self.assertIn(".ui-control:focus-visible", read(self.src / "ui" / "Control" / "Control.css"))
        for f in self.tw.rglob("*.vue"):
            with self.subTest(tailwind=f.name):
                self.assertNotIn("<style", read(f))
        self.assertIn('class="scaffold-root inline-flex', read(self.tw / "ui" / "Button" / "Button.vue"))
        self.assertIn('class="text-label text-danger-fg"', self.orders(self.tw, "OrderForm.vue"))

    def test_the_props_and_the_events_are_reacts(self):
        form = self.orders(self.src, "OrderForm.vue")
        self.assertIn("change: [name: keyof OrderDraft, value: unknown];\n  submit: [];\n  cancel: [];", form)
        self.assertIn("values: Partial<OrderDraft>;", form)
        self.assertIn('<form class="stack stack--separate" novalidate @submit.prevent="submit">', form)
        self.assertIn("@click=\"emit('cancel')\"", form)
        lst = self.orders(self.src, "OrdersList.vue")
        self.assertIn("defineProps<{ state: OrderListState }>();", lst)
        self.assertIn("@clear-filters=\"emit('clearFilters')\"", lst)
        self.assertIn(":error=\"state.error\" @retry=\"state.retry()\"", lst)
        radio = read(self.src / "ui" / "Control" / "RadioGroup.vue")
        self.assertIn("const model = defineModel<string | null>({ default: null });", radio)
        self.assertIn('<div v-if="$slots.action" class="action"><slot name="action" /></div>',
                      read(self.src / "ui" / "StateBlock" / "StateBlock.vue"))
        self.assertIn('<span class="label"><slot /></span>', read(self.src / "ui" / "Button" / "Button.vue"))

    def test_the_form_carries_the_ids_the_field_gives_the_error(self):
        """TheFormsAreWired's checks, in Vue's syntax: the control holds the
        error's id and the invalid flag, the radio group is a fieldset whose
        legend has the id the group names, and a toggle's error is wired."""
        for src in (self.src, self.tw):
            with self.subTest(src=src.name):
                form = self.orders(src, "OrderForm.vue")
                for name in ("reference", "notes", "total_cents"):
                    self.assertIn(f":aria-describedby=\"errors.{name} ? fieldId('{name}') + '-error' : undefined\"",
                                  form)
                    self.assertIn(f':aria-invalid="Boolean(errors.{name}) || undefined"', form)
                self.assertRegex(form, r"<Field\s+:id=\"fieldId\('priority'\)\"[\s\S]*?:disabled=\"disabled\"\s+group\s*>")
                self.assertIn(":labelled-by=\"fieldId('priority') + '-label'\"", form)
                self.assertRegex(form, r"<Toggle\s+:id=\"fieldId\('is_rush'\)\"[\s\S]*?"
                                       r":aria-describedby=\"errors\.is_rush \? fieldId\('is_rush'\) \+ '-error' : undefined\"")
                self.assertIn('<p v-if="errors.is_rush" :id="fieldId(\'is_rush\') + \'-error\'"', form)
                self.assertEqual(2, form.count('role="alert"'), "the summary and the form-level error")
        field = read(self.src / "ui" / "Field" / "Field.vue")
        self.assertIn("<legend v-if=\"group\" :id=\"id + '-label'\" class=\"label groupLabel\">", field)
        self.assertIn("<p v-if=\"error\" :id=\"id + '-error'\" class=\"error\">", field)
        self.assertNotIn('role="alert"', field)
        self.assertIn("describedBy } from './Field/describedBy';", read(self.src / "ui" / "index.ts"))

    def test_the_summary_focuses_once_per_attempt(self):
        form = self.orders(self.src, "OrderForm.vue")
        self.assertIn('ref="summary" class="summary" role="alert" tabindex="-1"', form)
        self.assertIn("const summary = useTemplateRef<HTMLDivElement>('summary');", form)
        self.assertIn("{ flush: 'post' },", form)
        got = self.node("render", "src")
        self.assertEqual({"failed": 1, "again": 2, "fixed": 2, "blur": 2, "pending": 2, "async": 3},
                         got["steps"], "a failed attempt focuses once, a clean one and a blur never")
        self.assertEqual(["summary"] * 3, [c.split()[0] for c in got["focused"]])
        # The control: run before the update, the watcher reads the errors the
        # parent has not passed down yet, and the failed attempt never focuses.
        pre = self.tmp / "pre"
        if not pre.exists():
            shutil.copytree(self.src, pre)
            form = pre / "features" / "orders" / "OrderForm.vue"
            form.write_bytes(read(form).replace("{ flush: 'post' }", "{ flush: 'pre' }").encode())
        self.assertNotEqual(got["steps"], self.node("render", "pre")["steps"])

    def test_the_rendered_form_holds_the_ids_it_names(self):
        """The server's render: every id an aria attribute names exists, on
        the element the attribute promises."""
        html = self.node("render", "src")["html"]
        for name, message in (("reference", "Required"), ("priority", "Choose one"), ("is_rush", "Rush is closed")):
            with self.subTest(name=name):
                self.assertRegex(html, rf'<p id="orders-{name}-error" class="(error|fieldError)"[^>]*>\s*{message}\s*</p>')
                self.assertRegex(html, rf'<a class="summaryLink" href="#orders-{name}"')
        self.assertRegex(html, r'<input[^>]*id="orders-reference"[^>]*aria-invalid="true"'
                               r'[^>]*aria-describedby="orders-reference-error"')
        self.assertRegex(html, r'<label for="orders-reference" class="label"')
        self.assertRegex(html, r'<fieldset class="ui-field stack stack--tight"[^>]*>\s*'
                               r'<legend id="orders-priority-label"')
        self.assertRegex(html, r'role="radiogroup" aria-labelledby="orders-priority-label" '
                               r'aria-describedby="orders-priority-error" aria-invalid="true"')
        self.assertRegex(html, r'<input id="orders-is_rush" type="checkbox"[^>]*aria-describedby="orders-is_rush-error"')
        self.assertRegex(html, r'<div class="summary"[^>]*role="alert" tabindex="-1"')

    def test_every_component_compiles(self):
        files = sorted(str(p.relative_to(self.tmp)) for out in (self.src, self.tw, self.plain)
                       for p in out.rglob("*.vue"))
        self.assertGreater(len(files), 60)
        self.assertEqual([], self.node("compile", *files)["problems"])
        # The control: the compilers report a template, a script and a style.
        (self.tmp / "broken.vue").write_bytes(
            b'<script setup lang="ts">\nconst n: = 1;\n</script>\n\n<template>\n  <div><p></div>\n'
            b'</template>\n\n<style scoped>\n.a { color: red\n</style>\n')
        problems = self.node("compile", "broken.vue", ok=False)["problems"]
        self.assertGreaterEqual(len(problems), 2, problems)

    def test_an_odd_name_and_an_option_with_markup_still_compile(self):
        """E3's names and #64's options, in a template: a quote ends a
        double-quoted directive, and markup or `{{` in text is markup."""
        odd = self.tmp / "odd"
        odd.mkdir(exist_ok=True)
        (odd / "schema.sql").write_bytes(ODD_DDL.encode())
        proc = run_py("content-model-to-ui", "introspect_schema", "schema.sql", "-o", "model.json", cwd=odd)
        self.assertEqual(0, proc.returncode, output(proc))
        proc = run_py("content-model-to-ui", "scaffold_ui", "model.json", "--out", "src", "--framework", "vue",
                      cwd=odd)
        self.assertEqual(0, proc.returncode, output(proc))
        out = odd / "src"
        form = read(out / "features" / "odd" / "OddForm.vue")
        self.assertIn(":aria-invalid=\"Boolean(errors['2fa']) || undefined\"", form)
        self.assertIn("fieldId('it\\'s')", form)
        mod = load_script("content-model-to-ui", "scaffold_ui")
        select = mod.vue_control({"name": 'say "hi"', "label": "Size", "control": "select", "required": True,
                                  "options": ['XL "tall"', "<S>", "{{x}}"]})
        self.assertIn('<option value="XL &quot;tall&quot;">XL "tall"</option>', select)
        self.assertIn('<option value="&lt;S&gt;">&lt;S&gt;</option>', select)
        self.assertIn('<option value="&#123;&#123;x}}">&#123;&#123;x}}</option>', select)
        self.assertIn('name="say &quot;hi&quot;"', select)
        (out / "features" / "odd" / "Options.vue").write_bytes(mod.vue_sfc(
            "import { Select } from '../../ui';\n\nconst values: Record<string, unknown> = {};\n"
            "const errors: Record<string, string> = {};\nconst disabled = false;\n"
            "const fieldId = (name: string) => name;\n"
            "const emit = defineEmits<{ change: [name: string, value: unknown] }>();\n",
            select).encode())
        files = sorted(str(p.relative_to(self.tmp)) for p in out.rglob("*.vue"))
        self.assertEqual([], self.node("compile", *files)["problems"])

    def test_it_passes_the_audit_and_the_static_a11y_check(self):
        # One project at a time: Control.css is a plain stylesheet, so two
        # projects audited together hold two homes for `.ui-control`.
        for src in ("src", "tw", "plain"):
            with self.subTest(src=src):
                proc = run_py("web-design-studio", "audit_design", src, "--strict", cwd=self.tmp)
                self.assertEqual(proc.returncode, 0, output(proc))
                proc = run_py("a11y-audit-runner", "a11y_static", f"{src}/ui", f"{src}/features", "--json",
                              cwd=self.tmp)
                report = json.loads(proc.stdout)
                self.assertEqual(report["errors"], 0, json.dumps(report, indent=2))

    def test_arrays_nulls_and_required_survive_the_controls(self):
        """Review of #176 (Codex, 4; CodeRabbit, 1), in React and Vue alike: a
        multiple select bound a string, an emptied number sent NaN, tags and
        JSON went through `String()`, a required radio group said so only
        with its asterisk, and a state's copy that began with `:` became a
        directive."""
        mod = load_script("content-model-to-ui", "scaffold_ui")
        multi = {"name": "tags", "label": "Tags", "control": "multi-select", "required": True,
                 "options": ["red", "green", "blue"]}
        self.assertIn("value={values.tags ?? []}", mod.control_jsx(multi))
        self.assertIn("Array.from(e.target.selectedOptions, (option) => option.value)", mod.control_jsx(multi))
        self.assertIn(':model-value="values.tags ?? []"', mod.vue_control(multi))
        number = {"name": "qty", "label": "Qty", "control": "number-input", "required": False}
        self.assertIn("Number.isNaN(e.target.valueAsNumber) ? null : e.target.valueAsNumber",
                      mod.control_jsx(number))
        self.assertIn("model.value = Number.isNaN(value) ? null : value;",
                      read(self.src / "ui" / "Control" / "NumberInput.vue"))
        for control in ("tag-input", "json-editor"):
            spec = {"name": "x", "label": "X", "control": control, "required": False}
            with self.subTest(control=control):
                self.assertIn(f'<ControlStub control="{control}"', mod.control_jsx(spec))
                self.assertIn(f'<ControlStub control="{control}"', mod.vue_control(spec))
        json_col = {"name": "meta", "type": "jsonb", "ui": {"control": "json-editor"}}
        self.assertEqual("JSON.stringify(row.meta ?? null)", mod.cell_render(json_col)["jsx"])
        self.assertIn("required={true}", mod.control_jsx({**multi, "control": "radio-group"}))
        self.assertIn("aria-required={required || undefined}", mod.CONTROL_TSX)
        self.assertIn("required={required}", mod.CONTROL_TSX)
        self.assertIn('    :required="true"\n', self.orders(self.src, "OrderForm.vue").split("<RadioGroup")[1])
        # Rendered: the group and each radio are required. (A select's slotted
        # options are selected by the runtime's v-model, which a server
        # render does not run.)
        ui = self.src / "ui" / "Control"
        html = self.node("ssr", str(ui / "RadioGroup.vue"), json.dumps(
            {"name": "p", "options": ["a", "b"], "modelValue": None, "required": True}))["html"]
        self.assertIn('aria-required="true"', html)
        self.assertEqual(2, len(re.findall(r'<input[^>]* required[^>]*>', html)), html)
        # The answers' copy is text, whatever it begins with.
        out = scaffold(self.tmp, "colon", "--framework", "vue",
                       answers={**ANSWERS, "orders.empty_state": {"body": ": nothing yet"}})
        empty = out / "features" / "orders" / "OrdersEmpty.vue"
        self.assertIn('    body=": nothing yet"\n', read(empty))
        self.assertIn(":body=\"error?.message\"", read(out / "features" / "orders" / "OrdersError.vue"))
        self.assertIn(": nothing yet</p>", self.node("ssr", str(empty), "{}")["html"])

    def test_server_actions_are_reacts_alone(self):
        proc = run_py("content-model-to-ui", "scaffold_ui", "model.json", "--out", "sa", "--framework", "vue",
                      "--server-actions", cwd=self.tmp)
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertIn("--server-actions is Next.js's", output(proc))
        self.assertFalse((self.tmp / "sa").exists())

    def test_the_database_side_is_the_react_scaffolds(self):
        for name in ("lib/supabase.ts", "db/policies/orders.policies.todo.sql", "server/orders.schema.ts",
                     "server/orders_schema.py", "lib/format.ts"):
            with self.subTest(file=name):
                self.assertTrue((self.src / name).is_file())
        self.assertIn("import.meta.env.VITE_SUPABASE_URL", read(self.src / "lib" / "supabase.ts"))


if __name__ == "__main__":
    unittest.main()
