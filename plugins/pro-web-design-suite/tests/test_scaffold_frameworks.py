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

from test_scaffold import ANSWERS, scaffold, scaffold_edges
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

    def test_the_error_summary_can_reach_the_radio_group(self):
        """PY-A-11, rendered: the summary's link names `#orders-priority`, and
        the radio group's fieldset is the element that has it."""
        html = self.node("render", "src")["html"]
        self.assertRegex(html, r'<a class="summaryLink" href="#orders-priority"')
        self.assertRegex(html, r'<fieldset class="ui-field stack stack--tight" id="orders-priority"[^>]*>\s*'
                               r'<legend id="orders-priority-label"')
        self.assertEqual(1, html.count('id="orders-priority"'))

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


class TheVueEdgeCases(VueOutput):
    """P73 (N67) in Vue: test_scaffold's EDGE_DDL."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = class_temp_dir(cls, "wds-vue-edges-")
        cls.src = scaffold_edges(cls.tmp, "src", "--framework", "vue")

    def feature(self, table: str, name: str) -> str:
        return read(self.src / "features" / table / name)

    def test_a_table_with_no_title_still_links_each_row_to_its_detail(self):
        """PY-A-6: no title among the columns, so no cell had the link."""
        body = self.feature("readings", "ReadingsList.vue").split("<tbody>")[1]
        self.assertEqual(1, body.count("<a "), body)
        self.assertIn('<td class="td truncate sticky"><a class="link" :href="\'/readings/\' + String(row.id)">'
                      "{{ row.sensor_id", body)
        self.assertIn("{{ state.record['order-id'] }}", self.feature("line_items", "LineItemDetail.vue"))

    def test_an_instant_is_shown_in_the_browsers_zone_and_a_wall_time_as_typed(self):
        """PY-A-10: the form sends a `timestamptz` as the instant."""
        form = self.feature("readings", "ReadingForm.vue")
        self.assertIn("import { fromLocalInput, toLocalInput } from '../../lib/format';", form)
        self.assertIn(':model-value="toLocalInput(values.checked_at)"', form)
        self.assertIn("@update:model-value=\"(value) => emit('change', 'checked_at', fromLocalInput(value, values.checked_at))\"", form)
        self.assertIn(":model-value=\"String(values.taken_at ?? '')\"", form)

    def test_a_state_word_with_no_closed_set_is_a_text_box(self):
        """PY-A-14: a select with no options."""
        form = self.feature("shows", "ShowForm.vue")
        at = re.search(r"<Field\s+:id=\"fieldId\('status'\)\"", form).start()
        block = form[at:form.index("</Field>", at)]
        self.assertIn("<TextInput", block)
        self.assertNotIn("<Select", form)
        self.assertIn("no closed set is known, so this is a text box", form[:at])
        self.assertIn("<!-- TODO(options): one <option> per `sensors` row; answer the `.label_column` question",
                      self.feature("readings", "ReadingForm.vue"))

    def test_every_component_compiles(self):
        files = sorted(str(p.relative_to(self.tmp)) for p in self.src.rglob("*.vue"))
        self.assertGreater(len(files), 40)
        self.assertEqual([], self.node("compile", *files)["problems"])


# Svelte's side. A component compiles for the client and for the server; the
# server renders the form, and jsdom runs the client so the real kit, the
# summary's binding and the effect all take part in the focus.
SVELTE_RUN = r"""
const fs = require('fs');
const path = require('path');
const Module = require('module');
const ts = require('typescript');
const { compile } = require('svelte/compiler');

const problems = [];
const warnings = [];
const generate = process.argv[2] === 'ssr' ? 'server' : 'client';

function transpile(code, file) {
  const out = ts.transpileModule(code, { reportDiagnostics: true, fileName: file + '.ts',
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } });
  for (const d of out.diagnostics || []) problems.push(file + ': ' + ts.flattenDiagnosticMessageText(d.messageText, ' '));
  return out.outputText;
}

function compileSvelte(file, mode) {
  try {
    const out = compile(fs.readFileSync(file, 'utf8'), { filename: file, generate: mode });
    for (const w of out.warnings) warnings.push(path.basename(file) + ': ' + w.code);
    return transpile(out.js.code, file);
  } catch (e) {
    problems.push(file + ': ' + e.message);
    return '';
  }
}

Module._extensions['.svelte'] = (module, file) => module._compile(compileSvelte(file, generate), file);
Module._extensions['.ts'] = (module, file) => module._compile(transpile(fs.readFileSync(file, 'utf8'), file), file);

async function focus(root) {
  const { JSDOM } = require('jsdom');
  const { window } = new JSDOM('<!doctype html><html><body></body></html>');
  const names = ['window', 'document', 'Node', 'Element', 'Text', 'Comment', 'DocumentFragment',
                 'MutationObserver', 'getComputedStyle', 'requestAnimationFrame'];
  for (const name of Object.getOwnPropertyNames(window)) if (/^(HTML|SVG)\w*Element$/.test(name)) names.push(name);
  for (const name of names) {
    Object.defineProperty(globalThis, name, { value: name === 'window' ? window : window[name],
                                              configurable: true, writable: true });
  }
  const focused = [];
  const real = window.HTMLElement.prototype.focus;
  window.HTMLElement.prototype.focus = function () { focused.push(this.className); return real.call(this); };
  const svelte = path.dirname(require.resolve('svelte/package.json'));
  const { mount } = require(path.join(svelte, 'src', 'index-client.js'));
  const { flush } = require('svelte/internal/client');
  const Harness = require(path.resolve('Harness.svelte')).default;
  const api = {};
  const target = window.document.body;
  mount(Harness, { target, props: { api } });
  flush();
  if (process.argv[2] === 'select') {               // a harness that renders a multiple select
    const picked = () => Array.from(target.querySelectorAll('option')).filter((o) => o.selected).map((o) => o.value);
    const first = picked();
    api.set(['green']);
    flush();
    return { picked: [first, picked()] };
  }
  const submit = (then) => {
    api.then(then);
    target.querySelector('form').dispatchEvent(new window.Event('submit', { cancelable: true, bubbles: true }));
    flush();
    return focused.length;
  };
  const steps = {};
  steps.failed = submit(() => api.set({ reference: 'Required' }, false));
  steps.again = submit(() => {});
  steps.fixed = submit(() => api.set({}, false));
  api.set({ notes: 'Too long' }, false);
  flush();
  steps.blur = focused.length;
  steps.pending = submit(() => api.set({}, true));
  api.set({ reference: 'Taken' }, false);
  flush();
  steps.async = focused.length;
  return { steps, focused };
}

async function ssr(root) {
  const { render } = require('svelte/server');
  if (rest[1]) {                                       // one component, with its props
    const Comp = require(path.join(root, rest[1])).default;
    return { html: render(Comp, { props: JSON.parse(rest[2] || '{}') }).body };
  }
  const Form = require(path.join(root, 'features/orders/OrderForm.svelte')).default;
  const errors = { reference: 'Required', priority: 'Choose one', is_rush: 'Rush is closed' };
  const out = render(Form, { props: { values: { reference: '' }, errors, onChange() {}, onSubmit() {} } });
  return { html: out.body };
}

const [mode, ...rest] = process.argv.slice(2);
(async () => {
  let result = {};
  if (mode === 'compile') rest.forEach((f) => { compileSvelte(f, 'client'); compileSvelte(f, 'server'); });
  else result = await (mode === 'ssr' ? ssr : focus)(path.resolve(rest[0]));
  console.log(JSON.stringify({ problems, warnings, ...result }));
  process.exit(problems.length ? 1 : 0);
})().catch((e) => { console.log(JSON.stringify({ problems: [String(e.stack || e)], warnings })); process.exit(1); });
"""

# The form's caller, for the focus run: it holds the errors and `submitting`
# as state, as an app would, and hands the test a way to set them.
SVELTE_HARNESS = """\
<script lang="ts">
  import OrderForm from './FORM';

  let { api }: { api: Record<string, unknown> } = $props();
  let errors = $state<Record<string, string>>({});
  let submitting = $state(false);
  let then: () => void = () => {};
  api.set = (next: Record<string, string>, busy: boolean) => { errors = next; submitting = busy; };
  api.then = (fn: () => void) => { then = fn; };
</script>

<OrderForm values={{}} {errors} {submitting} onChange={() => {}} onSubmit={() => then()} />
"""


class SvelteOutput(unittest.TestCase):
    """The schema scaffolded as Svelte with the answers (css-modules and
    tailwind) and without them, once for the class."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = class_temp_dir(cls, "wds-svelte-")
        cls.src = scaffold(cls.tmp, "src", "--framework", "svelte", answers=ANSWERS)
        cls.tw = scaffold(cls.tmp, "tw", "--framework", "svelte", "--stack", "tailwind", answers=ANSWERS)
        cls.plain = scaffold(cls.tmp, "plain", "--framework", "svelte")

    def orders(self, src: pathlib.Path, name: str) -> str:
        return read(src / "features" / "orders" / name)

    def node(self, *args: str, ok: bool = True) -> dict:
        root = tool_modules("WDS_NODE_MODULES", "typescript", "svelte", "jsdom")
        if root is None:
            self.skipTest("svelte, jsdom and typescript are not installed (tooling/main) or WDS_NODE_MODULES is off")
        (self.tmp / "svelte_run.cjs").write_bytes(SVELTE_RUN.encode())
        proc = subprocess.run(["node", "svelte_run.cjs", *args], cwd=self.tmp, capture_output=True,
                              env=env(NODE_PATH=root))
        self.assertEqual(proc.returncode == 0, ok, output(proc))
        return json.loads(proc.stdout)


class TheSvelteScaffold(SvelteOutput):

    def test_the_kit_and_the_screens_are_svelte_5_components(self):
        kit = ["Button/Button", "Field/Field", "Badge/Badge", "Skeleton/Skeleton", "StateBlock/StateBlock"] + [
            f"Control/{c}" for c in ("TextInput", "NumberInput", "TextArea", "Select", "Toggle",
                                     "RadioGroup", "ControlStub")]
        screens = ["OrdersList", "OrderDetail", "OrderForm"] + [
            f"Orders{s}" for s in ("Empty", "FilteredEmpty", "Loading", "Error", "Forbidden", "Stale")]
        for src in (self.src, self.tw):
            with self.subTest(src=src.name):
                self.assertEqual([], [p.name for p in src.rglob("*.tsx")] + [p.name for p in src.rglob("*.vue")])
                for f in [src / "ui" / f"{k}.svelte" for k in kit] + [
                        src / "features" / "orders" / f"{s}.svelte" for s in screens]:
                    text = read(f)
                    self.assertTrue(text.startswith('<script lang="ts">\n'), f)
                    if not f.name.endswith("Forbidden.svelte"):     # the one with no props
                        self.assertIn("$props()", text, f)
                    self.assertNotIn("export let", text, f)          # Svelte 4's props
        self.assertIn("export { default as OrderForm } from './OrderForm.svelte';",
                      self.orders(self.src, "index.ts"))
        self.assertIn("export { default as Select } from './Control/Select.svelte';",
                      read(self.src / "ui" / "index.ts"))
        self.assertFalse((self.src / "ui" / "Control" / "Control.css").exists())

    def test_runes_snippets_and_callbacks(self):
        button = read(self.src / "ui" / "Button" / "Button.svelte")
        self.assertIn('<span class="label">{@render children?.()}</span>', button)
        self.assertIn("  {...rest}\n>", button, "the caller's attributes come last, as React's ...rest")
        block = read(self.src / "ui" / "StateBlock" / "StateBlock.svelte")
        self.assertIn('<div class="action">{@render action()}</div>', block)
        empty = self.orders(self.src, "OrdersEmpty.svelte")
        self.assertIn("{#snippet action()}", empty)
        self.assertIn('<Button variant="primary" onclick={onCreate}>', empty)
        form = self.orders(self.src, "OrderForm.svelte")
        self.assertIn("onChange: (name: keyof OrderDraft, value: unknown) => void;", form)
        self.assertIn("oninput={(e) => onChange('reference', e.currentTarget.value)}", form)
        self.assertIn("onchange={(e) => onChange('is_rush', e.currentTarget.checked)}", form)
        self.assertIn('<form class="stack stack--separate" novalidate onsubmit={submit}>', form)
        skeleton = read(self.src / "ui" / "Skeleton" / "Skeleton.svelte")
        self.assertIn("style:--skeleton-width={String(width)}", skeleton)
        for f in self.src.rglob("*.svelte"):
            with self.subTest(file=f.name):
                for directive in re.findall(r"\bstyle:([\w-]+)", read(f)):
                    self.assertTrue(directive.startswith("--"), "style: sets only a custom property")
                self.assertNotRegex(read(f), r"\son:[a-z]+=", "Svelte 4's event directive")

    def test_each_style_is_inside_the_components_layer_and_matches_its_markup(self):
        for f in self.src.rglob("*.svelte"):
            with self.subTest(file=f.name):
                for body in re.findall(r"<style>([\s\S]*?)</style>", read(f)):
                    self.assertTrue(body.lstrip().startswith("@layer components {"), body[:80])
        number = read(self.src / "ui" / "Control" / "NumberInput.svelte")
        self.assertIn(".numeric {", number)
        self.assertNotIn(".toggle", number, "each control holds the rules its markup uses")
        self.assertIn(".loadingRow > :global(*)", self.orders(self.src, "OrdersLoading.svelte"))
        for f in self.tw.rglob("*.svelte"):
            with self.subTest(tailwind=f.name):
                self.assertNotIn("<style", read(f))
        self.assertIn("class={['scaffold-root inline-flex", read(self.tw / "ui" / "Button" / "Button.svelte"))

    def test_the_form_carries_the_ids_the_field_gives_the_error(self):
        for src in (self.src, self.tw):
            with self.subTest(src=src.name):
                form = self.orders(src, "OrderForm.svelte")
                for name in ("reference", "notes", "total_cents"):
                    self.assertIn(f"aria-describedby={{errors.{name} ? fieldId('{name}') + '-error' : undefined}}",
                                  form)
                    self.assertIn(f"aria-invalid={{Boolean(errors.{name}) || undefined}}", form)
                self.assertRegex(form, r"<Field\s+id=\{fieldId\('priority'\)\}[\s\S]*?disabled=\{disabled\}\s+group\s*>")
                self.assertIn("labelledBy={fieldId('priority') + '-label'}", form)
                self.assertIn("{#if errors.is_rush}", form)
                self.assertEqual(2, form.count('role="alert"'))
        field = read(self.src / "ui" / "Field" / "Field.svelte")
        self.assertIn("<legend class=\"label groupLabel\" id={id + '-label'}>", field)
        self.assertNotIn('role="alert"', field)

    def test_the_summary_focuses_once_per_attempt(self):
        form = self.orders(self.src, "OrderForm.svelte")
        self.assertIn('<div class="summary" role="alert" tabindex="-1" bind:this={summary}>', form)
        self.assertIn("$effect(() => {", form)
        harness = SVELTE_HARNESS.replace("./FORM", "./src/features/orders/OrderForm.svelte")
        (self.tmp / "Harness.svelte").write_bytes(harness.encode())
        got = self.node("focus", "src")
        self.assertEqual({"failed": 1, "again": 2, "fixed": 2, "blur": 2, "pending": 2, "async": 3},
                         got["steps"], "a failed attempt focuses once, a clean one and a blur never")
        self.assertEqual(["summary"] * 3, [c.split()[0] for c in got["focused"]])
        # The control: #64's first effect, which watched only the count, moves
        # nothing on a second attempt and pulls focus on a blur.
        naive = self.tmp / "naive"
        if not naive.exists():
            shutil.copytree(self.src, naive)
            f = naive / "features" / "orders" / "OrderForm.svelte"
            text = read(f)
            effect = text[text.index("  $effect(() => {"):text.index("  function submit")]
            f.write_bytes(text.replace(effect, "  $effect(() => {\n    if (invalid.length > 0) summary?.focus();\n"
                                               "  });\n\n").encode())
        (self.tmp / "Harness.svelte").write_bytes(
            SVELTE_HARNESS.replace("./FORM", "./naive/features/orders/OrderForm.svelte").encode())
        steps = self.node("focus", "naive")["steps"]
        self.assertLess(steps["again"], got["steps"]["again"], steps)
        self.assertGreater(steps["blur"], steps["fixed"], steps)

    def test_the_rendered_form_holds_the_ids_it_names(self):
        html = self.node("ssr", "src")["html"]
        for name, message in (("reference", "Required"), ("priority", "Choose one"), ("is_rush", "Rush is closed")):
            with self.subTest(name=name):
                self.assertRegex(html, rf'<p class="(error|fieldError)[^"]*" id="orders-{name}-error">\s*{message}\s*</p>')
                self.assertRegex(html, rf'<a class="summaryLink[^"]*" href="#orders-{name}"')
        self.assertRegex(html, r'<input[^>]*id="orders-reference"[^>]*aria-invalid="true"'
                               r'[^>]*aria-describedby="orders-reference-error"')
        self.assertRegex(html, r'<label class="label[^"]*" for="orders-reference"')
        self.assertRegex(html, r'<fieldset class="root stack stack--tight[^"]*"[^>]*>(\s|<!--[^>]*-->)*'
                               r'<legend class="label groupLabel[^"]*" id="orders-priority-label"')
        self.assertRegex(html, r'role="radiogroup" aria-labelledby="orders-priority-label" '
                               r'aria-describedby="orders-priority-error" aria-invalid="true"')
        self.assertRegex(html, r'<input id="orders-is_rush" type="checkbox"[^>]*aria-describedby="orders-is_rush-error"')
        self.assertRegex(html, r'<div class="summary[^"]*" role="alert" tabindex="-1"')

    def test_the_error_summary_can_reach_the_radio_group(self):
        """PY-A-11, rendered: the radio group's fieldset has the id the
        summary's link names."""
        html = self.node("ssr", "src")["html"]
        self.assertRegex(html, r'<a class="summaryLink[^"]*" href="#orders-priority"')
        self.assertRegex(html, r'<fieldset class="root stack stack--tight[^"]*" id="orders-priority"')
        self.assertEqual(1, html.count('id="orders-priority"'))

    def test_every_component_compiles_without_a_warning(self):
        files = sorted(str(p.relative_to(self.tmp)) for out in (self.src, self.tw, self.plain)
                       for p in out.rglob("*.svelte"))
        self.assertGreater(len(files), 60)
        got = self.node("compile", *files)
        self.assertEqual([], got["problems"])
        self.assertEqual([], got["warnings"], "an unused selector is dropped; an a11y warning is a finding")
        (self.tmp / "broken.svelte").write_bytes(
            b'<script lang="ts">\n  let n: = 1;\n</script>\n\n<div><p></div>\n')
        self.assertGreaterEqual(len(self.node("compile", "broken.svelte", ok=False)["problems"]), 1)
        (self.tmp / "unused.svelte").write_bytes(b"<p>x</p>\n\n<style>\n  .gone { color: red; }\n</style>\n")
        self.assertIn("unused.svelte: css_unused_selector", self.node("compile", "unused.svelte")["warnings"])

    def test_it_passes_the_audit_and_the_static_a11y_check(self):
        for src in ("src", "tw", "plain"):
            with self.subTest(src=src):
                proc = run_py("web-design-studio", "audit_design", src, "--strict", cwd=self.tmp)
                self.assertEqual(proc.returncode, 0, output(proc))
                proc = run_py("a11y-audit-runner", "a11y_static", f"{src}/ui", f"{src}/features", "--json",
                              cwd=self.tmp)
                report = json.loads(proc.stdout)
                self.assertEqual(report["errors"], 0, json.dumps(report, indent=2))

    def test_arrays_nulls_and_required_survive_the_controls(self):
        """The review of #176, in Svelte: the multiple select's array, null
        for an emptied number, the stubs, the required radio group, and copy
        that is always text, a `{` in it included."""
        mod = load_script("content-model-to-ui", "scaffold_ui")
        multi = {"name": "tags", "label": "Tags", "control": "multi-select", "required": True,
                 "options": ["red", "green", "blue"]}
        select = mod.svelte_control(multi)
        self.assertIn("value={values.tags ?? []}", select)
        self.assertIn("Array.from(e.currentTarget.selectedOptions, (option) => option.value)", select)
        # Codex on #177: does the spread's array reach a native multiple
        # select? Svelte's attribute effect calls `select_option`, which
        # selects each option in the array; mounted, and then updated:
        (self.tmp / "Harness.svelte").write_bytes(b"""\
<script lang="ts">
  import Select from './src/ui/Control/Select.svelte';

  let { api }: { api: Record<string, unknown> } = $props();
  let value = $state(['red', 'blue']);
  api.set = (next: string[]) => { value = next; };
</script>

<Select multiple {value}>
  <option value="red">red</option>
  <option value="green">green</option>
  <option value="blue">blue</option>
</Select>
""")
        self.assertEqual([["red", "blue"], ["green"]], self.node("select", "src")["picked"])
        self.assertIn("Number.isNaN(e.currentTarget.valueAsNumber) ? null : e.currentTarget.valueAsNumber",
                      mod.svelte_control({"name": "qty", "label": "Qty", "control": "number-input"}))
        for control in ("tag-input", "json-editor"):
            with self.subTest(control=control):
                self.assertIn(f'<ControlStub control="{control}"',
                              mod.svelte_control({"name": "x", "label": "X", "control": control}))
        self.assertIn("required={true}", mod.svelte_control({**multi, "control": "radio-group"}))
        html = self.node("ssr", "src", "ui/Control/RadioGroup.svelte", json.dumps(
            {"name": "p", "options": ["a", "b"], "value": None, "required": True}))["html"]
        self.assertIn('aria-required="true"', html)
        self.assertEqual(2, len(re.findall(r'<input[^>]* required[^>]*>', html)), html)
        out = scaffold(self.tmp, "brace", "--framework", "svelte",
                       answers={**ANSWERS, "orders.empty_state": {"body": "{soon} nothing yet"}})
        self.assertIn('body="&#123;soon&#125; nothing yet"', read(out / "features" / "orders" / "OrdersEmpty.svelte"))
        self.assertIn("body={error?.message}", read(out / "features" / "orders" / "OrdersError.svelte"))
        html = self.node("ssr", "brace", "features/orders/OrdersEmpty.svelte")["html"]
        self.assertIn("{soon} nothing yet", html)

    def test_server_actions_are_reacts_alone(self):
        proc = run_py("content-model-to-ui", "scaffold_ui", "model.json", "--out", "sa", "--framework", "svelte",
                      "--server-actions", cwd=self.tmp)
        self.assertEqual(2, proc.returncode, output(proc))
        self.assertFalse((self.tmp / "sa").exists())

    def test_an_odd_name_and_an_option_with_markup_still_compile(self):
        mod = load_script("content-model-to-ui", "scaffold_ui")
        select = mod.svelte_control({"name": 'say "hi"', "label": "Size {x}", "control": "select",
                                     "required": True, "options": ['XL "tall"', "<S>", "{{x}}"]})
        self.assertIn('<option value={"XL \\"tall\\""}>{"XL \\"tall\\""}</option>', select)
        self.assertIn('<option value={"<S>"}>{"<S>"}</option>', select)
        self.assertIn('name="say &quot;hi&quot;"', select)
        self.assertEqual("Size &#123;x&#125;", mod.svelte_static("Size {x}"))
        odd = self.tmp / "odd"
        odd.mkdir(exist_ok=True)
        (odd / "schema.sql").write_bytes(ODD_DDL.encode())
        for args in (("introspect_schema", "schema.sql", "-o", "model.json"),
                     ("scaffold_ui", "model.json", "--out", "src", "--framework", "svelte")):
            with self.subTest(script=args[0]):
                proc = run_py("content-model-to-ui", *args, cwd=odd)
                self.assertEqual(0, proc.returncode, output(proc))
        form = read(odd / "src" / "features" / "odd" / "OddForm.svelte")
        self.assertIn("aria-invalid={Boolean(errors['2fa']) || undefined}", form)
        (odd / "src" / "features" / "odd" / "Options.svelte").write_bytes(mod.svelte_sfc(
            "import { Select } from '../../ui';\n\nconst values: Record<string, unknown> = {};\n"
            "const errors: Record<string, string> = {};\nconst disabled = false;\n"
            "const fieldId = (name: string) => name;\n"
            "const onChange = (name: string, value: unknown) => [name, value];\n", select).encode())
        files = sorted(str(p.relative_to(self.tmp)) for p in (odd / "src").rglob("*.svelte"))
        self.assertEqual([], self.node("compile", *files)["problems"])


class TheSvelteEdgeCases(SvelteOutput):
    """P73 (N67) in Svelte: test_scaffold's EDGE_DDL."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = class_temp_dir(cls, "wds-svelte-edges-")
        cls.src = scaffold_edges(cls.tmp, "src", "--framework", "svelte")

    def feature(self, table: str, name: str) -> str:
        return read(self.src / "features" / table / name)

    def test_a_table_with_no_title_still_links_each_row_to_its_detail(self):
        """PY-A-6: no title among the columns, so no cell had the link."""
        body = self.feature("readings", "ReadingsList.svelte").split("<tbody>")[1]
        self.assertEqual(1, body.count("<a "), body)
        self.assertIn("<td class=\"td truncate sticky\"><a class=\"link\" href={'/readings/' + String(row.id)}>"
                      "{row.sensor_id", body)
        self.assertIn("{state.record['order-id']}", self.feature("line_items", "LineItemDetail.svelte"))

    def test_an_instant_is_shown_in_the_browsers_zone_and_a_wall_time_as_typed(self):
        """PY-A-10: the form sends a `timestamptz` as the instant."""
        form = self.feature("readings", "ReadingForm.svelte")
        self.assertIn("import { fromLocalInput, toLocalInput } from '../../lib/format';", form)
        self.assertIn("value={toLocalInput(values.checked_at)}", form)
        self.assertIn("oninput={(e) => onChange('checked_at', fromLocalInput(e.currentTarget.value, values.checked_at))}", form)
        self.assertIn("value={String(values.taken_at ?? '')}", form)

    def test_a_state_word_with_no_closed_set_is_a_text_box(self):
        """PY-A-14: a select with no options."""
        form = self.feature("shows", "ShowForm.svelte")
        at = re.search(r"<Field\s+id=\{fieldId\('status'\)\}", form).start()
        block = form[at:form.index("</Field>", at)]
        self.assertIn("<TextInput", block)
        self.assertNotIn("<Select", form)
        self.assertIn("no closed set is known, so this is a text box", form[:at])
        self.assertIn("<!-- TODO(options): one <option> per `sensors` row; answer the `.label_column` question",
                      self.feature("readings", "ReadingForm.svelte"))

    def test_every_component_compiles_without_a_warning(self):
        files = sorted(str(p.relative_to(self.tmp)) for p in self.src.rglob("*.svelte"))
        self.assertGreater(len(files), 40)
        got = self.node("compile", *files)
        self.assertEqual([], got["problems"])
        self.assertEqual([], got["warnings"])


if __name__ == "__main__":
    unittest.main()
