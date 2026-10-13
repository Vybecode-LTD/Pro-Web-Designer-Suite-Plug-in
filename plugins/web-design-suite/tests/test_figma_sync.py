"""figma-variables-sync: figma_to_tokens.py and figma_audit.py (3.1.0).

Regressions covered:
- LC-A1: a DTCG 2025.10 export — the format's first stable version, where a
  colour is {colorSpace, components, alpha, hex}, a dimension or duration is
  {value, unit}, a token can be a JSON Pointer ($ref), a group can inherit
  ($extends) and carry its own token ($root), and $type is inherited from the
  group — was written out as Python dict reprs (`--space-6: {'value': 24,
  'unit': 'px'};`) with exit 0, and the audit passed it with 0 findings.
- LC-A2: a composed colour's opacity (Figma: a percentage, 0-100) was used as
  a 0-1 alpha, so every translucent hover became opaque; with an alias in the
  colour channel the value was written out as a Python dict.
- LC-A3: figma_audit.py compared every colour with the studio's own ramps,
  with no way to supply the project's, so a client's brand ramp failed as 11
  OFF_RAMP_COLOR errors.
- LC-A4: every generated tokens.css/json carried the current time, so the
  documented CI drift check failed on an unchanged export.
- LC-C3 (3.4.0): the two scripts' readers were copies that had drifted apart.
- LC-A22 (3.4.0): the `--reverse` body carried a `_comment` key, never named a
  collection's first mode, and offered primitives in the pickers.
- LC-B1, LC-C7 (3.6.0): the only route into Figma was the REST body, which
  needs an Enterprise plan; `--reverse --format plugin-script` writes the same
  variables as Plugin API code for use_figma or a plugin.
- the 3.6.0 live check: `--reverse` read a DTCG file as a flat map, its groups
  and a resolver's keys made variables, with exit 0; and a tokens.css had no
  route into Figma at all.
"""
from __future__ import annotations

import ast
import json
import subprocess
import unittest
from datetime import datetime, timedelta, timezone

from wds_support import NODE, SKILLS, TempDirTest, env, load_script, output, run_py

DTCG_2025 = {
    "neutral": {"$type": "color",
                "500": {"$value": {"colorSpace": "srgb", "components": [0.4196, 0.4196, 0.4196],
                                   "alpha": 1, "hex": "#6b6b6b"}},
                "0": {"$value": {"colorSpace": "srgb", "components": [1, 1, 1],
                                 "alpha": 1, "hex": "#ffffff"}}},
    "accent": {"$type": "color",
               "600": {"$value": {"colorSpace": "oklch", "components": [0.565, 0.176, 42]}}},
    "space": {"$type": "dimension",
              "6": {"$value": {"value": 24, "unit": "px"}},
              "7": {"$value": {"value": 28, "unit": "px"}}},
    "dur": {"$type": "duration", "base": {"$value": {"value": 0.22, "unit": "s"}}},
    "bg": {"$type": "color", "surface": {"$value": "{neutral.0}"}},
    "fg": {"$type": "color", "muted": {"$value": "{neutral.500}"},
           "subtle": {"$ref": "#/neutral/500"}},
}


class Dtcg2025(TempDirTest):
    """LC-A1."""

    def tokens(self, data, *args):
        src = self.write("export.tokens.json", json.dumps(data))
        proc = run_py("figma-variables-sync", "figma_to_tokens", src, "--format", "css", *args,
                      cwd=self.tmp)
        return proc, proc.stdout.decode("utf-8")

    def test_object_values_and_references_become_real_css(self):
        clean = json.loads(json.dumps(DTCG_2025))
        del clean["space"]["7"]                          # 28px is not a contract name
        proc, css = self.tokens(clean)
        self.assertNotIn("{'", css)
        for decl in ("--space-6: 1.5rem;", "--dur-base: 220ms;",
                     "--bg-surface: var(--neutral-0);", "--fg-muted: var(--neutral-500);",
                     "--fg-subtle: var(--neutral-500);", "--accent-600: oklch(56.5% 0.176 42);"):
            self.assertIn(decl, css)
        self.assertRegex(css, r"--neutral-500: oklch\([\d.]+% [\d.]+ [\d.]+\);")
        self.assertEqual(proc.returncode, 0, output(proc))

    def test_root_tokens_and_extended_groups_are_read(self):
        data = {"ink": {"$type": "color", "fg": {"$value": "#111111"},
                        "bg": {"$value": "#ffffff"}},
                "print": {"$extends": "{ink}", "fg": {"$value": "#000000"}},
                "brand": {"$type": "color", "$root": {"$value": "#e8440a"},
                          "hover": {"$value": "#c63a08"}}}
        proc, css = self.tokens(data, "--color-format", "hex")
        self.assertIn("--print-bg: #ffffff;", css)       # inherited from ink
        self.assertIn("--print-fg: #000000;", css)       # overridden
        self.assertIn("--brand: #e8440a;", css)          # the group's own $root token
        self.assertIn("--brand-hover: #c63a08;", css)
        self.assertNotIn("$root", css)

    def test_a_value_it_cannot_express_is_reported_never_written_as_python(self):
        data = dict(DTCG_2025, type={"body": {"$type": "typography", "$value": {
            "fontFamily": "Inter", "fontSize": {"value": 16, "unit": "px"}}}})
        proc, css = self.tokens(data)
        self.assertNotIn("{'", css)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("type/body", output(proc))

    def test_the_audit_reads_2025_10_values(self):
        src = self.write("export.tokens.json", json.dumps(DTCG_2025))
        proc = run_py("figma-variables-sync", "figma_audit", src, "--format", "json",
                      cwd=self.tmp)
        codes = {f["code"] for f in json.loads(proc.stdout)["findings"]}
        self.assertTrue({"OFF_SCALE_SPACING", "OFF_RAMP_COLOR"} <= codes
                        or ("OFF_RAMP_COLOR" in codes and any("SCALE" in c for c in codes)),
                        codes)
        self.assertEqual(proc.returncode, 1, output(proc))


REST_COMPOSED = {
    "status": 200, "error": False,
    "meta": {
        "variableCollections": {
            "VariableCollectionId:1:1": {"id": "VariableCollectionId:1:1", "name": "Primitives",
                                         "modes": [{"modeId": "1:0", "name": "Value"}],
                                         "defaultModeId": "1:0", "variableIds": ["VariableID:1:2"]},
            "VariableCollectionId:2:1": {"id": "VariableCollectionId:2:1", "name": "Semantic",
                                         "modes": [{"modeId": "2:0", "name": "Light"}],
                                         "defaultModeId": "2:0",
                                         "variableIds": ["VariableID:2:2", "VariableID:2:3"]}},
        "variables": {
            "VariableID:1:2": {"id": "VariableID:1:2", "name": "neutral/900",
                               "variableCollectionId": "VariableCollectionId:1:1",
                               "resolvedType": "COLOR", "scopes": [],
                               "valuesByMode": {"1:0": {"r": 0.12, "g": 0.11, "b": 0.1, "a": 1}}},
            "VariableID:2:2": {"id": "VariableID:2:2", "name": "bg/hover",
                               "variableCollectionId": "VariableCollectionId:2:1",
                               "resolvedType": "COLOR", "scopes": ["ALL_FILLS"],
                               "valuesByMode": {"2:0": {"color": {"type": "VARIABLE_ALIAS",
                                                                  "id": "VariableID:1:2"},
                                                        "opacity": 8}}},
            "VariableID:2:3": {"id": "VariableID:2:3", "name": "bg/active",
                               "variableCollectionId": "VariableCollectionId:2:1",
                               "resolvedType": "COLOR", "scopes": ["ALL_FILLS"],
                               "valuesByMode": {"2:0": {"color": {"r": 0.12, "g": 0.11, "b": 0.1,
                                                                  "a": 1},
                                                        "opacity": 12}}}}},
}


class ComposedColours(TempDirTest):
    """LC-A2."""

    def test_opacity_is_a_percentage_and_an_aliased_colour_keeps_its_link(self):
        src = self.write("composed.json", json.dumps(REST_COMPOSED))
        proc = run_py("figma-variables-sync", "figma_to_tokens", src, "--format", "css",
                      cwd=self.tmp)
        css = proc.stdout.decode("utf-8")
        self.assertIn("--bg-hover: color-mix(in oklch, var(--neutral-900) 8%, transparent);",
                      css, output(proc))
        self.assertRegex(css, r"--bg-active: oklch\([^)]*/ 0\.12\);")
        self.assertNotIn("{'", css)


PROJECT_ACCENT = ["#f0f6ff", "#deeaff", "#c2d9ff", "#9cc0ff", "#72a3ff", "#4d87ff",
                  "#356aea", "#2a51b8", "#203a89", "#172861", "#0b1538"]
STEPS = ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "950"]


class ProjectRamps(TempDirTest):
    """LC-A3."""

    def test_the_audit_checks_against_the_projects_own_ramps(self):
        records = [{"name": f"accent/{s}", "type": "COLOR", "value": h}
                   for s, h in zip(STEPS, PROJECT_ACCENT)]
        src = self.write("export.json", json.dumps(records))
        tokens = self.write("src/styles/tokens.css", "@layer tokens {\n  :root {\n" + "".join(
            f"    --accent-{s}: {h};\n" for s, h in zip(STEPS, PROJECT_ACCENT)) + "  }\n}\n")

        def off_ramp(*extra):
            proc = run_py("figma-variables-sync", "figma_audit", src, "--format", "json", *extra,
                          cwd=self.tmp)
            self.assertIn(proc.returncode, (0, 1), output(proc))
            return [f for f in json.loads(proc.stdout)["findings"] if f["code"] == "OFF_RAMP_COLOR"]

        self.assertEqual(len(off_ramp()), 11)                     # the studio's ramps: all off
        self.assertEqual(off_ramp("--tokens", tokens), [])       # the project's ramps: all on


class DeterministicOutput(TempDirTest):
    """LC-A4."""

    def test_generated_files_carry_no_clock_time(self):
        src = self.write("export.tokens.json", json.dumps(DTCG_2025))
        now = datetime.now(timezone.utc)
        days = {(now + timedelta(days=d)).strftime("%Y-%m-%d") for d in (-1, 0, 1)}
        for fmt in ("css", "json"):
            with self.subTest(fmt=fmt):
                proc = run_py("figma-variables-sync", "figma_to_tokens", src, "--format", fmt,
                              cwd=self.tmp)
                text = proc.stdout.decode("utf-8")
                self.assertTrue(text.strip(), output(proc))
                self.assertFalse([d for d in days if d in text], text[:400])

    def test_the_drift_check_passes_a_generated_file_and_fails_a_hand_edit(self):
        """LC-B8: SKILL.md says the CI drift check is what keeps tokens.css
        read-only. Its recipe diffs the generator's stdout against the file
        step 3 wrote with --out."""
        src = self.write("export.tokens.json", json.dumps(DTCG_2025))
        tokens = self.tmp / "src" / "styles" / "tokens.css"
        run_py("figma-variables-sync", "figma_to_tokens", src, "--format", "css",
               "--out", tokens, cwd=self.tmp)

        def drift():
            proc = run_py("figma-variables-sync", "figma_to_tokens", src, "--format", "css",
                          cwd=self.tmp)
            return proc.stdout != tokens.read_bytes()

        self.assertFalse(drift(), "an untouched generated file reads as drift")
        css = tokens.read_bytes()
        start = css.index(b"--space-6:")
        tokens.write_bytes(css[:start] + b"--space-6: 26px" + css[css.index(b";", start):])
        self.assertTrue(drift(), "a hand edit passes the drift check")

    def test_source_date_epoch_is_honoured_when_a_date_is_wanted(self):
        src = self.write("export.tokens.json", json.dumps(DTCG_2025))
        proc = run_py("figma-variables-sync", "figma_to_tokens", src, "--format", "css",
                      cwd=self.tmp, env_changes={"SOURCE_DATE_EPOCH": "0"})
        self.assertIn("1970-01-01", proc.stdout.decode("utf-8"))


class StatusInks(TempDirTest):
    """P7 (SS-B2): text on a status fill is measured on that fill. It was
    measured on the canvas, so a white --fg-on-danger failed on a white page
    and passed on any fill."""

    def contrast_failures(self, fill: str) -> list:
        data = {"fg": {"$type": "color", "on-danger": {"$value": "#ffffff"}},
                "bg": {"$type": "color", "canvas": {"$value": "#ffffff"},
                       "danger": {"$value": fill}}}
        src = self.write("export.tokens.json", json.dumps(data))
        proc = run_py("figma-variables-sync", "figma_audit", src, "--format", "json", cwd=self.tmp)
        return [f for f in json.loads(proc.stdout)["findings"]
                if f["code"] == "CONTRAST_FAIL" and "on-danger" in json.dumps(f)]

    def audit(self, data) -> list:
        src = self.write("export.tokens.json", json.dumps(data))
        proc = run_py("figma-variables-sync", "figma_audit", src, "--format", "json", cwd=self.tmp)
        return json.loads(proc.stdout)["findings"]

    def test_an_ink_with_no_fill_in_the_file_is_measured_on_the_systems_fill(self):
        """CodeRabbit on #31: with no bg/danger, the ink was not measured at all."""
        findings = self.audit({"fg": {"$type": "color", "on-danger": {"$value": "#ff8080"}},
                               "bg": {"$type": "color", "canvas": {"$value": "#ffffff"}}})
        self.assertTrue([f for f in findings
                         if f["code"] == "CONTRAST_FAIL" and "on-danger" in json.dumps(f)], findings)

    def test_a_travel_distance_is_audited_as_spacing(self):
        """CodeRabbit on #31: motion-travel-sm = 8 was read as 8ms."""
        findings = self.audit({"motion": {"$type": "number", "travel": {
            "xs": {"$value": 4}, "sm": {"$value": 8}, "md": {"$value": 16}}}})
        self.assertFalse([f for f in findings if "DURATION" in f["code"]], findings)

    def test_an_on_status_ink_is_measured_on_its_fill(self):
        self.assertEqual(self.contrast_failures("#d92f35"), [])      # 4.76:1 on the fill
        self.assertEqual(len(self.contrast_failures("#ff9999")), 1)  # 2.07:1 on the fill


PLUGIN_EXPORT = {"collections": [{"name": "semantic", "modes": [
    {"name": "Light", "variables": [{"name": "bg/surface", "type": "COLOR", "value": "#ffffff"}]},
    {"name": "Dark", "variables": [{"name": "bg/surface", "type": "COLOR", "value": "#111111"}]}]}]}
PLUGIN_FLAT = {"collections": [{"name": "semantic", "defaultModeId": "1:0",
                                "modes": [{"modeId": "1:0", "name": "Light"},
                                          {"modeId": "1:1", "name": "Dark"}],
                                "variables": [{"name": "bg/surface", "type": "COLOR", "valuesByMode": {
                                    "1:0": "#ffffff", "1:1": "#111111"}}]}]}
RECORDS_EXPORT = [
    {"name": "bg/surface", "type": "COLOR", "value": "#ffffff", "collection": "semantic", "mode": "Light"},
    {"name": "bg/surface", "type": "COLOR", "value": "#111111", "collection": "semantic", "mode": "Dark"},
    {"name": "space/4", "type": "FLOAT", "value": 16}]
REST_ORPHAN = {"meta": {"variableCollections": {}, "variables": {"VariableID:9:9": {
    "id": "VariableID:9:9", "name": "space/4", "variableCollectionId": "VariableCollectionId:9:1",
    "resolvedType": "FLOAT", "valuesByMode": {"9:0": 16}}}}}


class FigmaCommon(TempDirTest):
    """LC-C3: the two scripts said they share their readers and did not. Copied
    apart, they drifted: the audit split a records export's modes into one
    variable each, which figma_to_tokens had stopped doing."""

    def read(self, module, data):
        doc = module.load_document(self.write("export.json", json.dumps(data)), None, "tokens")
        return (doc.shape,
                {n: (c.modes, c.default_mode) for n, c in sorted(doc.collections.items())},
                sorted((v.name, v.collection, v.resolved_type, json.dumps(v.values, sort_keys=True))
                       for v in doc.variables))

    def test_both_scripts_read_every_shape_the_same_way(self):
        to_tokens = load_script("figma-variables-sync", "figma_to_tokens")
        audit = load_script("figma-variables-sync", "figma_audit")
        for shape, data in (("rest", REST_COMPOSED), ("rest", REST_ORPHAN), ("plugin", PLUGIN_EXPORT),
                            ("plugin", PLUGIN_FLAT),
                            ("records", RECORDS_EXPORT), ("dtcg", DTCG_2025)):
            with self.subTest(shape=shape):
                read = self.read(to_tokens, data)
                self.assertEqual(read[0], shape)
                self.assertEqual(self.read(audit, data), read)

    def test_a_flat_plugin_export_reads_its_values_by_mode_name(self):
        # CodeRabbit on #53: valuesByMode is keyed by mode id, the modes by name.
        read = self.read(load_script("figma-variables-sync", "figma_common"), PLUGIN_FLAT)
        self.assertEqual(read[1], {"semantic": (["Light", "Dark"], "Light")})
        self.assertEqual(json.loads(read[2][0][3]), {"Dark": "#111111", "Light": "#ffffff"})

    def test_neither_script_defines_what_figma_common_does(self):
        scripts = SKILLS / "figma-variables-sync" / "scripts"

        def defined(path):
            names = set()
            for node in ast.parse(path.read_text(encoding="utf-8")).body:
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    names.add(node.name)
                elif isinstance(node, ast.Assign):
                    names |= {t.id for t in node.targets if isinstance(t, ast.Name)}
            return names

        common = defined(scripts / "figma_common.py")
        self.assertTrue({"load_document", "as_color", "FDoc"} <= common, common)
        for script in ("figma_to_tokens.py", "figma_audit.py"):
            with self.subTest(script=script):
                self.assertEqual(defined(scripts / script) & common, set())


class ReverseBody(TempDirTest):
    """LC-A22: the body `--reverse` writes is the one Figma's REST API takes."""

    def body(self):
        forward = run_py("figma-variables-sync", "figma_to_tokens",
                         self.write("export.tokens.json", json.dumps(DTCG_2025)),
                         "--format", "json", cwd=self.tmp)
        tokens = self.write("tokens.json", forward.stdout.decode("utf-8"))
        proc = run_py("figma-variables-sync", "figma_to_tokens", tokens, "--reverse", cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return json.loads(proc.stdout)

    def test_a_duration_crosses_as_milliseconds(self):
        # CodeRabbit on #53: `--dur-base: 220ms` was dropped, having no px value.
        body = self.body()
        dur = next((v for v in body["variables"] if v["codeSyntax"]["WEB"] == "var(--dur-base)"),
                   None)
        self.assertIsNotNone(dur, body["variables"])
        self.assertIn(220, [m["value"] for m in body["variableModeValues"]
                            if m["variableId"] == dur["id"]])

    def test_the_body_has_only_the_four_arrays(self):
        self.assertEqual(set(self.body()), {"variableCollections", "variableModes", "variables",
                                            "variableModeValues"})

    def test_each_collections_first_mode_is_named_by_an_update(self):
        body = self.body()
        modes = {m["id"]: m for m in body["variableModes"]}
        for collection in body["variableCollections"]:
            with self.subTest(collection=collection["name"]):
                first = modes.get(collection["initialModeId"])
                self.assertIsNotNone(first, body["variableModes"])
                self.assertEqual((first["action"], first["variableCollectionId"]),
                                 ("UPDATE", collection["id"]))
                self.assertTrue(first["name"])

    def test_the_first_mode_takes_a_name_no_theme_has(self):
        # A dark `:root` has a `light` theme; Codex on #53: and a `default` one.
        for themes, first in ((["light"], "Default"), (["light", "default"], "Base")):
            with self.subTest(themes=themes):
                tokens = self.write("tokens.json", json.dumps({
                    "semantic": {"bg-surface": {"value": "#111111"}},
                    "themes": {t: {"bg-surface": {"value": "#ffffff"}} for t in themes}}))
                proc = run_py("figma-variables-sync", "figma_to_tokens", tokens, "--reverse",
                              cwd=self.tmp)
                modes = json.loads(proc.stdout)["variableModes"]
                self.assertEqual(modes[0]["name"], first, output(proc))
                self.assertEqual(len({m["name"].lower() for m in modes}), len(themes) + 1, modes)
                self.assertEqual(len({m["id"] for m in modes}), len(themes) + 1, modes)

    def test_primitives_are_offered_in_no_picker(self):
        body = self.body()
        tier = {c["id"]: c["name"] for c in body["variableCollections"]}
        scopes = {v["name"]: (tier[v["variableCollectionId"]], v["scopes"]) for v in body["variables"]}
        self.assertEqual(scopes["neutral/500"], ("primitive", []))
        self.assertEqual(scopes["bg/surface"], ("semantic", ["FRAME_FILL", "SHAPE_FILL"]))


# A stand-in for the Plugin API's `figma.variables`, as its reference pages
# give it: collections with `modes`, `defaultModeId`, `renameMode` and
# `addMode` (which throws past the plan's cap), variables with `scopes`,
# `codeSyntax`, `setVariableCodeSyntax`, `valuesByMode` and `setValueForMode`.
# The script runs as use_figma runs it, inside an async function, twice, so the
# second run shows what a re-run changes. Every call is recorded.
FIGMA_STUB = """
import { readFileSync } from 'node:fs';
const code = readFileSync(process.argv[2], 'utf8');
const modeCap = Number(process.argv[3]);
const calls = [];
const collections = [];
const variables = [];
let next = 1;
function collection(name) {
  const c = {
    id: 'VariableCollectionId:' + next++, name,
    modes: [{ modeId: 'mode:' + next++, name: 'Mode 1' }],
    get defaultModeId() { return this.modes[0].modeId; },
    renameMode(id, to) {
      calls.push(['renameMode', name, id === this.defaultModeId ? 'default' : id, to]);
      this.modes.find((m) => m.modeId === id).name = to;
    },
    addMode(to) {
      if (this.modes.length >= modeCap) throw new Error('in addMode: Limited to ' + modeCap + ' modes only');
      const id = 'mode:' + next++;
      this.modes.push({ modeId: id, name: to });
      calls.push(['addMode', name, to]);
      return id;
    },
  };
  collections.push(c);
  return c;
}
function variable(name, col, type) {
  let scopes = ['ALL_SCOPES'];
  const codeSyntax = {};
  const v = {
    id: 'VariableID:' + next++, name, variableCollectionId: col.id, resolvedType: type,
    description: '', valuesByMode: {}, codeSyntax,
    get scopes() { return scopes.slice(); },
    set scopes(s) { calls.push(['scopes', name, s]); scopes = s.slice(); },
    setVariableCodeSyntax(platform, value) { calls.push(['codeSyntax', name, platform, value]); codeSyntax[platform] = value; },
    setValueForMode(modeId, value) {
      if (!col.modes.some((m) => m.modeId === modeId)) throw new Error('no such mode');
      calls.push(['setValueForMode', name, modeId, value]);
      this.valuesByMode[modeId] = value;
    },
  };
  variables.push(v);
  return v;
}
const figma = { variables: {
  async getLocalVariableCollectionsAsync() { return collections.slice(); },
  async getLocalVariablesAsync() { return variables.slice(); },
  createVariableCollection(name) { calls.push(['createVariableCollection', name]); return collection(name); },
  createVariable(name, col, type) {
    if (typeof col !== 'object') throw new Error('createVariable takes the collection itself');
    calls.push(['createVariable', name, col.name, type]);
    return variable(name, col, type);
  },
  createVariableAlias(v) { return { type: 'VARIABLE_ALIAS', id: v.id }; },
} };
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const run = new AsyncFunction('figma', code);
const first = await run(figma);
const firstCalls = calls.splice(0);
const second = await run(figma);
console.log(JSON.stringify({
  first, second, calls: firstCalls, rerunCalls: calls,
  collections: collections.map((c) => ({ name: c.name, modes: c.modes })),
  variables: variables.map((v) => ({ id: v.id, name: v.name, scopes: v.scopes,
                                     codeSyntax: v.codeSyntax, valuesByMode: v.valuesByMode })),
}));
"""


@unittest.skipUnless(NODE, "node is not on PATH")
class PluginScript(TempDirTest):
    """LC-B1, LC-C7 (P32): `--reverse --format plugin-script` writes the
    variables as Plugin API code, which use_figma runs on any plan."""

    THEMED = {"semantic": {"bg-surface": {"value": "var(--neutral-0)"},
                           "fg-muted": {"value": "var(--neutral-500)"}},
              "primitive": {"neutral-0": {"value": "#ffffff"},
                            "neutral-500": {"value": "#6b6b6b"},
                            "neutral-900": {"value": "#1a1a1a"}},
              "themes": {"dark": {"bg-surface": {"value": "var(--neutral-900)"}}}}

    def script(self, tokens=None):
        path = self.write("tokens.json", json.dumps(tokens or self.THEMED))
        proc = run_py("figma-variables-sync", "figma_to_tokens", path, "--reverse",
                      "--format", "plugin-script", cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        return proc.stdout.decode("utf-8")

    def run_stub(self, script, mode_cap=10):
        code = self.write("figma-variables.js", script)
        stub = self.write("stub.mjs", FIGMA_STUB)
        proc = subprocess.run([NODE, stub, code, str(mode_cap)], cwd=self.tmp, env=env(),
                              capture_output=True, timeout=60)
        self.assertEqual(proc.returncode, 0, output(proc))
        return json.loads(proc.stdout)

    def test_the_script_runs_as_use_figma_runs_it(self):
        ran = self.run_stub(self.script())
        self.assertEqual(ran["first"]["errorCount"], 0, ran["first"])
        self.assertEqual(ran["first"]["collections"], {"created": 2, "found": 0})
        self.assertEqual(ran["first"]["variables"]["created"], 5)

    def test_it_renames_mode_1_and_adds_the_themes(self):
        ran = self.run_stub(self.script())
        modes = {c["name"]: [m["name"] for m in c["modes"]] for c in ran["collections"]}
        self.assertEqual(modes, {"primitive": ["Value"], "semantic": ["Light", "Dark"]})
        self.assertIn(["renameMode", "semantic", "default", "Light"], ran["calls"])
        self.assertNotIn("Mode 1", json.dumps(ran["collections"]))

    def test_primitives_are_scoped_out_and_every_variable_has_its_css_name(self):
        ran = self.run_stub(self.script())
        by_name = {v["name"]: v for v in ran["variables"]}
        self.assertEqual(by_name["neutral/500"]["scopes"], [])
        self.assertEqual(by_name["bg/surface"]["scopes"], ["FRAME_FILL", "SHAPE_FILL"])
        for name, v in by_name.items():
            with self.subTest(name=name):
                self.assertEqual(v["codeSyntax"], {"WEB": f"var(--{name.replace('/', '-')})"})

    def test_aliases_stay_aliases_in_every_mode(self):
        ran = self.run_stub(self.script())
        by_name = {v["name"]: v for v in ran["variables"]}
        modes = {m["name"]: m["modeId"] for c in ran["collections"] for m in c["modes"]}
        surface = by_name["bg/surface"]["valuesByMode"]
        self.assertEqual(surface[modes["Light"]], {"type": "VARIABLE_ALIAS", "id": by_name["neutral/0"]["id"]})
        self.assertEqual(surface[modes["Dark"]], {"type": "VARIABLE_ALIAS", "id": by_name["neutral/900"]["id"]})
        self.assertEqual(by_name["neutral/0"]["valuesByMode"][modes["Value"]], {"r": 1, "g": 1, "b": 1, "a": 1})

    def test_a_second_run_changes_nothing(self):
        ran = self.run_stub(self.script())
        self.assertEqual(ran["rerunCalls"], [])
        self.assertEqual(ran["second"]["collections"], {"created": 0, "found": 2})
        self.assertEqual(ran["second"]["variables"], {"created": 0, "updated": 0, "unchanged": 5})
        self.assertEqual(ran["second"]["modes"], {"created": 0, "renamed": 0, "found": 3})

    def test_a_plan_that_caps_the_modes_is_reported_and_the_rest_is_written(self):
        # Starter: "Anyone on Education, Professional, Organization, and
        # Enterprise plans can create and use modes for variables."
        ran = self.run_stub(self.script(), mode_cap=1)
        self.assertEqual(ran["first"]["errorCount"], 1, ran["first"])
        self.assertIn('mode "Dark" in "semantic": in addMode: Limited to 1 modes only',
                      ran["first"]["errors"])
        self.assertEqual(ran["first"]["variables"]["created"], 5)

    def resync(self, old, new):
        """The new tokens' script runs against the file the old one wrote, as a re-sync does."""
        code = self.write("figma-variables.js", self.script(new))
        state = self.write("rerun.mjs", FIGMA_STUB.replace(
            "const first = await run(figma);",
            "await new AsyncFunction('figma', readFileSync(process.argv[4], 'utf8'))(figma);\n"
            "calls.splice(0);\nconst first = await run(figma);"))
        proc = subprocess.run([NODE, state, code, "10", self.write("old.js", self.script(old))],
                              cwd=self.tmp, env=env(), capture_output=True, timeout=60)
        self.assertEqual(proc.returncode, 0, output(proc))
        return json.loads(proc.stdout)

    def test_a_changed_token_is_updated_in_place(self):
        changed = json.loads(json.dumps(self.THEMED))
        changed["primitive"]["neutral-500"]["value"] = "#5a5a5a"
        again = self.resync(self.THEMED, changed)
        self.assertEqual(again["first"]["variables"], {"created": 0, "updated": 1, "unchanged": 4})
        self.assertEqual([c[:2] for c in again["calls"]], [["setValueForMode", "neutral/500"]])

    def test_the_default_values_go_to_the_default_mode_whatever_the_names(self):
        # Codex on #109: `light` and `dark` themes, then `dark` alone. The old
        # default is `Default`, beside a `Light` theme, and the new body names
        # the default `Light`: its values must not land on the old theme.
        old = {"semantic": {"bg-surface": {"value": "#eeeeee"}},
               "themes": {"light": {"bg-surface": {"value": "#ffffff"}},
                          "dark": {"bg-surface": {"value": "#111111"}}}}
        new = {"semantic": {"bg-surface": {"value": "#fafafa"}},
               "themes": {"dark": {"bg-surface": {"value": "#000000"}}}}
        ran = self.resync(old, new)
        semantic = next(c for c in ran["collections"] if c["name"] == "semantic")
        modes = {m["name"]: m["modeId"] for m in semantic["modes"]}
        self.assertEqual(list(modes), ["Default", "Dark", "Light"])
        surface = next(v for v in ran["variables"] if v["name"] == "bg/surface")["valuesByMode"]
        self.assertAlmostEqual(surface[modes["Default"]]["r"], 250 / 255, places=4)
        self.assertAlmostEqual(surface[modes["Dark"]]["r"], 0, places=4)
        self.assertAlmostEqual(surface[modes["Light"]]["r"], 1, places=4)    # the old theme, untouched
        self.assertEqual(ran["first"]["errorCount"], 1, ran["first"])
        self.assertIn('another mode has the name, so the default mode keeps "Default"', ran["first"]["errors"][0])

    def test_a_plan_that_cannot_hold_the_themes_is_reported_before_the_run(self):
        # LC-B6: the plan from the flag, else from the project's config.
        path = self.write("tokens.json", json.dumps(self.THEMED))
        self.write(".git/HEAD", "x\n")
        for args, config, code in ((["--plan", "starter"], None, 1), (["--plan", "professional"], None, 0),
                                   ([], {"plan": "starter"}, 1), (["--plan", "enterprise"], {"plan": "starter"}, 0)):
            with self.subTest(args=args, config=config):
                if config:
                    self.write(".design-suite.json", json.dumps({"schema": 1, "figma": config}))
                proc = run_py("figma-variables-sync", "figma_to_tokens", path, "--reverse",
                              "--format", "plugin-script", *args, cwd=self.tmp)
                self.assertEqual(proc.returncode, code, output(proc))
                self.assertEqual("mode-limit" in output(proc), code == 1, output(proc))
                if code:
                    self.assertIn("`semantic` needs 2 modes, and Starter has no modes beyond", output(proc))
                    self.assertIn("const BODY", proc.stdout.decode("utf-8"))   # written all the same

    def test_plugin_script_needs_reverse(self):
        path = self.write("tokens.json", json.dumps(self.THEMED))
        proc = run_py("figma-variables-sync", "figma_to_tokens", path, "--format", "plugin-script",
                      cwd=self.tmp)
        self.assertEqual(proc.returncode, 2, output(proc))
        self.assertIn("--reverse", output(proc))


class PlanLimits(TempDirTest):
    """LC-B6 (P32): each Figma plan caps a collection's modes. Figma's plan
    comparison gives Professional "Up to 10 modes per collection" and
    Organization "Up to 20"; the REST page, "Each collection can have a
    maximum of 40 modes"; and modes go to "Education, Professional,
    Organization, and Enterprise plans", so Starter keeps the first."""

    def records(self, modes, roles=("bg/surface", "fg/default", "border/subtle")):
        return self.write(f"records-{len(modes)}.json", json.dumps([
            {"name": role, "type": "COLOR", "value": "#ffffff",
             "collection": "semantic", "mode": mode} for role in roles for mode in modes]))

    def audit(self, path, *args):
        proc = run_py("figma-variables-sync", "figma_audit", path, "--format", "json", "--fail-on", "never",
                      *args, cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        return [f for f in json.loads(proc.stdout)["findings"]
                if f["code"] in ("MODE_LIMIT", "MISSING_DARK_MODE")]

    def test_each_plan_caps_the_modes_per_collection(self):
        eleven = self.records([f"Theme {n}" for n in range(1, 11)] + ["Dark"])
        two = self.records(["Light", "Dark"])
        for path, plan, fires in ((eleven, "professional", True), (eleven, "organization", False),
                                  (two, "starter", True), (two, "professional", False),
                                  (self.records([f"T{n}" for n in range(21)]), "organization", True),
                                  (self.records([f"T{n}" for n in range(40)]), "enterprise", False)):
            with self.subTest(plan=plan, path=path.name):
                found = [f for f in self.audit(path, "--plan", plan) if f["code"] == "MODE_LIMIT"]
                self.assertEqual(bool(found), fires, found)
                if fires:
                    self.assertEqual((found[0]["severity"], found[0]["collection"]), ("error", "semantic"))

    def test_without_a_plan_nothing_is_capped(self):
        self.assertEqual(self.audit(self.records([f"T{n}" for n in range(41)] + ["Dark"])), [])

    def test_no_dark_mode_is_asked_of_starter(self):
        one = self.records(["Light"])
        self.assertEqual([f["code"] for f in self.audit(one)], ["MISSING_DARK_MODE"])      # control
        self.assertEqual(self.audit(one, "--plan", "starter"), [])
        self.assertEqual([f["code"] for f in self.audit(one, "--plan", "professional")], ["MISSING_DARK_MODE"])

    def test_the_config_names_the_plan_and_the_flag_beats_it(self):
        self.write(".git/HEAD", "x\n")
        self.write(".design-suite.json", json.dumps({"schema": 1, "figma": {"plan": "starter"}}))
        two = self.records(["Light", "Dark"])
        self.assertEqual([f["code"] for f in self.audit(two)], ["MODE_LIMIT"])
        self.assertEqual(self.audit(two, "--plan", "professional"), [])
        self.write(".design-suite.json", json.dumps({"schema": 1, "figma": {"plan": "free"}}))
        proc = run_py("figma-variables-sync", "figma_audit", two, cwd=self.tmp)
        self.assertEqual(proc.returncode, 2, output(proc))
        self.assertIn('"figma.plan" must be one of starter, professional, organization, enterprise', output(proc))

    def test_the_rest_body_keeps_to_the_endpoints_cap(self):
        tokens = {"semantic": {"bg-surface": {"value": "#ffffff"}},
                  "themes": {f"t{n}": {"bg-surface": {"value": "#000000"}} for n in range(40)}}
        out = self.tmp / "payload.json"
        proc = run_py("figma-variables-sync", "figma_to_tokens", self.write("tokens.json", json.dumps(tokens)),
                      "--reverse", "--out", out, cwd=self.tmp)
        self.assertEqual(proc.returncode, 2, output(proc))
        self.assertIn("`semantic` needs 41 modes, and the REST API allows 40 per collection.", output(proc))
        self.assertFalse(out.exists(), "a body Figma refuses whole is written")   # CodeRabbit on #111
        del tokens["themes"]["t0"]
        proc = run_py("figma-variables-sync", "figma_to_tokens", self.write("tokens.json", json.dumps(tokens)),
                      "--reverse", "--out", out, cwd=self.tmp)
        self.assertEqual(proc.returncode, 0, output(proc))
        self.assertEqual(len(json.loads(out.read_bytes())["variableModes"]), 40)

    def test_the_plans_are_the_configs(self):
        common = load_script("figma-variables-sync", "figma_common")
        config = load_script("figma-variables-sync", "project_config")
        self.assertEqual(tuple(common.PLAN_MODES), config.FIGMA_PLANS)


class ReverseReadsEveryTokenFormat(TempDirTest):
    """The 3.6.0 live check: asked to put a project's tokens.css into Figma
    with its light and dark themes, a session found no route. `--reverse`
    refused the CSS, and given the DTCG files `--format dtcg --out-dir` writes
    it made variables of a document's groups and a resolver's own keys
    (`sets`, `resolutionOrder`), with exit 0 and no Dark mode."""

    STARTER = SKILLS / "web-design-studio" / "assets" / "starter" / "styles" / "tokens.css"

    def body(self, src):
        proc = run_py("figma-variables-sync", "figma_to_tokens", src, "--reverse", "--out", "body.json",
                      cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        body = json.loads((self.tmp / "body.json").read_bytes())
        names = {v["name"]: v["id"] for v in body["variables"]}
        modes = {m["id"]: m["name"] for m in body["variableModes"]}
        values = {(modes[m["modeId"]], m["variableId"]): m["value"] for m in body["variableModeValues"]}
        return names, values, output(proc)

    def published(self):
        proc = run_py("figma-variables-sync", "figma_to_tokens", str(self.STARTER), "--format", "dtcg",
                      "--out-dir", "dtcg", "--quiet", cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))

    def assert_themed(self, names, values):
        surface = names["bg/surface"]
        self.assertEqual("tmp_var_neutral_0", values[("Light", surface)]["id"])
        self.assertEqual("tmp_var_neutral_950", values[("Dark", surface)]["id"])   # [data-theme="dark"]

    def test_a_tokens_css_goes_in_with_its_themes_as_modes(self):
        names, values, out = self.body(str(self.STARTER))
        self.assert_themed(names, values)
        self.assertIn('[data-density="compact"]: 1 token(s) left out', out)

    def test_a_resolver_s_theme_contexts_are_modes(self):
        self.published()
        names, values, out = self.body("dtcg/tokens.resolver.json")
        self.assert_themed(names, values)
        self.assertFalse({"sets", "resolutionOrder", "modifiers", "version"} & set(names), sorted(names)[:10])
        self.assertIn("modifier `density` left out", out)

    def test_a_dtcg_document_s_groups_are_not_variables(self):
        self.published()
        names, values, _out = self.body("dtcg/tokens.json")
        self.assertIn("bg/surface", names)
        self.assertFalse({"bg", "accent", "neutral", "$description"} & set(names))
        self.assertEqual("tmp_var_neutral_0", values[("Value", names["bg/surface"])]["id"])


if __name__ == "__main__":
    unittest.main()
