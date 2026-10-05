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
"""
from __future__ import annotations

import ast
import json
import unittest
from datetime import datetime, timedelta, timezone

from wds_support import SKILLS, TempDirTest, load_script, output, run_py

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
                            ("records", RECORDS_EXPORT), ("dtcg", DTCG_2025)):
            with self.subTest(shape=shape):
                read = self.read(to_tokens, data)
                self.assertEqual(read[0], shape)
                self.assertEqual(self.read(audit, data), read)

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

    def test_a_dark_root_with_a_light_theme_gets_two_mode_names(self):
        tokens = self.write("tokens.json", json.dumps({
            "semantic": {"bg-surface": {"value": "#111111"}},
            "themes": {"light": {"bg-surface": {"value": "#ffffff"}}}}))
        proc = run_py("figma-variables-sync", "figma_to_tokens", tokens, "--reverse", cwd=self.tmp)
        names = [m["name"] for m in json.loads(proc.stdout)["variableModes"]]
        self.assertEqual(sorted(names), ["Default", "Light"], output(proc))

    def test_primitives_are_offered_in_no_picker(self):
        body = self.body()
        tier = {c["id"]: c["name"] for c in body["variableCollections"]}
        scopes = {v["name"]: (tier[v["variableCollectionId"]], v["scopes"]) for v in body["variables"]}
        self.assertEqual(scopes["neutral/500"], ("primitive", []))
        self.assertEqual(scopes["bg/surface"], ("semantic", ["FRAME_FILL", "SHAPE_FILL"]))


if __name__ == "__main__":
    unittest.main()
