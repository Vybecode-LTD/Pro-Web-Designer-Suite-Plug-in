"""A JSON value's type is checked where it is read (the owner's audit of
2026-10-14, class 6).

S1, V8, G3, G11, G15, E13, W6 and S10: a JSON file of the wrong shape was a
traceback (exit 1, the gates' "it fired" code) or, worse, read as something
else: a string `scopes` as letters, `bool("false")` as true, a string budget
limit as no limit. Every loader now checks the shape when it reads the file
and exits 2 naming the file or the key; a baseline it cannot use is read as
unreadable, as before (audit everything, named on stderr).

The table has one row per loader and per way of reaching it. Each row is fed
`[]`, a string, a number and its own wrong shapes, and must never print a
traceback.
"""
from __future__ import annotations

import json
import shutil
import unittest

from wds_support import NODE, SKILLS, TempDirTest, output, run_node, run_py

TOKENS = ":root {\n  --bg-canvas: #ffffff;\n  --fg-default: #111111;\n}\n"
EMAIL = '<!doctype html><html lang="en"><head><title>t</title></head><body><p>Hi</p></body></html>\n'
DECISIONS = ("# Test deck\n\n## Decisions\n\n### D1 — Tokens\n"
             "**Constraint:** Many developers touch the CSS.\n**Choice:** A closed token system.\n")
LEDGER = "design-system-versioning/deprecations@1"
SYSTEM = "design-system-docs/system/1"
STATS = {"tokens": 0, "components": 0, "sockets": 0}
LITERALS = "design-token-migration/literals@1"
FINDING = {"layer": "craft", "severity": "major", "title": "t"}
FILES = {"tokens.css": TOKENS, "src/a.css": ".a { color: var(--fg-default); }\n",
         "dist/index.html": EMAIL, "DECISION_LOG.md": DECISIONS, "a.html": EMAIL, "findings.json": "[]",
         "system.json": json.dumps({"schema": SYSTEM, "stats": STATS, "tokens": [], "components": []}),
         "export.tokens.json": json.dumps({"c": {"$type": "color", "$value": "#ffffff"}}), "axe.js": ""}
MODEL = "content-model-to-ui/model/1"
MAPPING = "design-token-migration/mapping@1"
TOP = ([], "x", 5)          # what every row is fed; a row adds the wrong shapes of its own keys
# The loaders that take a list, so `[]` is a valid file for them.
LISTS = {"check_roles --pairs", "audit_design --baseline", "a11y_static --baseline", "perf_audit --baseline",
         "critique_report findings", "critique_report --audit", "build_presentation --a11y",
         "build_presentation --audit", "a11y_runtime --steps"}
CODE = 2                    # exit 2, a bad invocation; BASELINE rows audit everything instead,
                            # and introspect_schema exits 1, "nothing usable found in the input"
BASELINE = (0, 1)

# label: (skill, script, its arguments with "BAD" for the file, the exit codes,
#         [(a payload of the right top level with a wrong key, what the message names)])
CASES = {
    "check_roles --pairs": ("web-design-studio", "check_roles", ["tokens.css", "--pairs", "BAD"], CODE, [
        ([{"fg": "--fg-default", "bg": "--bg-canvas", "min": "4.5"}], "`min`"),
        ([{"fg": "--fg-default", "bg": "--bg-canvas", "min": 4.5, "scopes": "light"}], "`scopes`"),
        ([{"fg": 5, "bg": "--bg-canvas", "min": 4.5}], "`fg`"),
        ([5], "pair 0"), ({"fg": "--fg-default"}, "the top level")]),
    "audit_design --baseline": ("web-design-studio", "audit_design", ["src", "--baseline", "BAD"], BASELINE, [
        ({"src/a.css|L1": 1}, "could not read baseline"), ([5], "could not read baseline")]),
    "a11y_static --baseline": ("a11y-audit-runner", "a11y_static", ["src", "--baseline", "BAD"], BASELINE, [
        ({"k": 1}, "could not read baseline"), ([5], "could not read baseline")]),
    "perf_audit --budget": ("perf-budget-gate", "perf_audit", ["dist", "--budget", "BAD"], CODE, [
        ({"defaults": {"bytes": {"css": "60KB"}}}, "`defaults.bytes.css`"),
        ({"defaults": {"requests": []}}, "`defaults.requests`"),
        ({"defaults": []}, "`defaults`"),
        ({"pages": []}, "`pages`"),
        ({"pages": {"home": {"largest_asset": {"js": True}}}}, "`pages.home.largest_asset.js`"),
        ({"growth": {"js_pct": "5"}}, "`growth.js_pct`"),
        ({"first_party_origins": "https://a.example"}, "`first_party_origins`"),
        ({"measure": 5}, "`measure`"),
        ({"defaults": {"bytes": {"total": float("inf")}}}, "`defaults.bytes.total`")]),   # Codex on #138: 1e400
    "perf_audit --baseline": ("perf-budget-gate", "perf_audit", ["dist", "--baseline", "BAD"], BASELINE, [
        ({"findings": 5}, "could not read baseline"),
        ({"totals": [1]}, "could not read baseline"),
        ({"totals": {"bytes": {"js": "x"}}}, "could not read baseline")]),
    "critique_report findings": ("design-critique-gate", "critique_report", ["BAD"], CODE, [
        ([{**FINDING, "count": "x"}], "'count'"),
        ([{**FINDING, "count": [1]}], "'count'"),
        ([{**FINDING, "is_taste": "maybe"}], "'is_taste'"),
        ([{**FINDING, "defend": 2}], "'defend'"),
        ({"findings": {}}, "'findings'"), ({"x": 1}, "'findings'")]),
    "critique_report --audit": ("design-critique-gate", "critique_report",
                                ["findings.json", "--audit", "BAD"], CODE, [([5], "BAD")]),
    "build_presentation --perf": ("client-presentation-builder", "build_presentation",
                                  ["DECISION_LOG.md", "--perf", "BAD", "--dry-run"], CODE, [
        ({"ledger": [1]}, "`ledger`"),
        ({"ledger": {"bytes": [1]}}, "`ledger.bytes`"),
        ({"ledger": {"assets": [5]}}, "`ledger.assets[0]`"),
        ({"ledger": {"assets": [{"transfer": "x"}]}}, "`ledger.assets[0].transfer`"),
        ({"ledger": {}, "budget": [1]}, "`budget`"),
        ({"ledger": {}, "findings": [5]}, "`findings[0]`"),
        ({"ledger": []}, "`ledger`"), ({"ledger": False}, "`ledger`"),                   # Codex on #138
        ({"ledger": {"assets": {}}}, "`ledger.assets`")]),
    "build_presentation --a11y": ("client-presentation-builder", "build_presentation",
                                  ["DECISION_LOG.md", "--a11y", "BAD", "--dry-run"], CODE, [
        ({"violations": 5}, "`violations`"),
        ({"violations": [5]}, "`violations[0]`"), ([5], "bad.json"),
        ({"tool": "a11y_runtime", "findings": [5]}, "`findings[0]`")]),               # Codex on #138
    "build_presentation --audit": ("client-presentation-builder", "build_presentation",
                                   ["DECISION_LOG.md", "--audit", "BAD", "--dry-run"], CODE, []),
    "build_docs system": ("design-system-docs", "build_docs", ["BAD", "--out", "site"], CODE, [
        ({"schema": SYSTEM, "tokens": {}}, "`tokens`"),
        ({"schema": SYSTEM, "components": [5]}, "`components`"),
        ({"schema": SYSTEM, "tokens": [], "components": []}, "`stats`"),             # CodeRabbit on #138
        ({"schema": SYSTEM, "stats": STATS, "tokens": [{"name": "--a"}]}, "`tokens[0]`"),
        ({"schema": SYSTEM, "stats": STATS, "components": [{"name": "c", "sockets": 5}]},
         "`components[0].sockets`")]),
    "build_docs --baseline": ("design-system-docs", "build_docs",
                              ["system.json", "--check", "--baseline", "BAD"], CODE, [
        ({"schema": SYSTEM, "tokens": [{"raw": "#fff"}]}, "`tokens`"),
        ({"schema": SYSTEM, "stats": STATS, "components": [],
          "tokens": [{"name": "--a", "raw": "#fff", "tier": 1, "contrast": [5]}]}, "`tokens[0].contrast`")]),
    "diff_system --deprecations": ("design-system-versioning", "diff_system",
                                   ["tokens.css", "tokens.css", "--deprecations", "BAD"], CODE, [
        ({"schema": LEDGER, "deprecations": {}}, "`deprecations`"),
        ({"schema": LEDGER, "deprecations": [{"kind": "token"}]}, "`name`")]),
    "deprecate --ledger": ("design-system-versioning", "deprecate", ["--ledger", "BAD", "status"], CODE, [
        ({"schema": LEDGER, "deprecations": "x"}, "`deprecations`"),
        ({"schema": LEDGER, "deprecations": [5]}, "`name`")]),
    "apply_codemod -m": ("design-token-migration", "apply_codemod", ["-m", "BAD", "src"], CODE, [
        ({"schema": MAPPING, "rules": {}}, "`rules`"),
        ({"schema": MAPPING, "rules": [5]}, "`rules[0]`"),
        ({"schema": MAPPING, "rules": [{"kind": "color", "replacement": "var(--x)", "match": "#fff"}]},
         "`rules[0].match`"),
        ({"schema": MAPPING, "rules": [{"kind": "color", "match": ["#fff"]}]}, "`rules[0].replacement`"),
        ({"schema": MAPPING, "rules": [{"kind": "color", "replacement": "x"}]}, "`rules[0].match`"),
        ({"schema": MAPPING, "rules": [{"kind": "color", "replacement": "x", "match": ["#fff"], "props": 0}]},
         "`rules[0].props`")]),
    "cluster_values": ("design-token-migration", "cluster_values", ["BAD", "--dry-run"], CODE, [
        ({"literals": {}}, "literals"),
        ({"schema": LITERALS, "literals": {}}, "`literals`"),                         # CodeRabbit on #138
        ({"schema": LITERALS, "literals": [{"kind": "color"}]}, "`literals`")]),
    "lint_email --tokens": ("email-template-system", "lint_email", ["--source", "--tokens", "BAD", "a.html"], CODE, [
        ({"tokens": []}, "tokens")]),
    "build_email --tokens": ("email-template-system", "build_email", ["a.html", "--tokens", "BAD"], CODE, []),
    "sync_email_tokens --base": ("email-template-system", "sync_email_tokens",              # P62
                                 ["--tokens", "tokens.css", "--base", "BAD", "--out", "o.json"], CODE, [
        ({"tokens": []}, "tokens"), ({"tokens": {"--a": "#fff"}}, "--a"),
        ({"tokens": {"--a": {"value": 5}}}, "--a"), ({"tokens": {}, "dropped": []}, "`dropped`")]),
    "sync_email_tokens --check": ("email-template-system", "sync_email_tokens",
                                  ["--tokens", "tokens.css", "--out", "BAD", "--check"], CODE, []),
    "figma_audit": ("figma-variables-sync", "figma_audit", ["BAD"], CODE, []),
    "figma_audit --styles": ("figma-variables-sync", "figma_audit", ["export.tokens.json", "--styles", "BAD"], CODE, []),
    "figma_to_tokens": ("figma-variables-sync", "figma_to_tokens", ["BAD"], CODE, []),
    "figma_to_tokens --reverse": ("figma-variables-sync", "figma_to_tokens", ["BAD", "--reverse"], CODE, []),
    "generate_matrix": ("component-state-matrix", "generate_matrix", ["BAD", "--out", "m"], CODE, [
        ({"$schema": "component-state-matrix/1", "components": {}}, "components")]),
    "scaffold_ui": ("content-model-to-ui", "scaffold_ui", ["BAD", "--dry-run"], CODE, [
        ({"$schema": MODEL, "tables": {"a": 1}}, "`tables`"),
        ({"$schema": MODEL, "tables": [5]}, "`tables`"),
        ({"$schema": MODEL, "tables": {}}, "`tables`")]),                              # CodeRabbit on #138
    "introspect_schema": ("content-model-to-ui", "introspect_schema", ["BAD", "--format", "json"], 1, [
        ({"tables": 5}, "`tables`"),
        ({"tables": {"a": 5}}, "`tables`"),
        ({"tables": [{"name": "a", "columns": 5}]}, "`tables[0].columns`"),
        ({"tables": [{"name": "a", "columns": [], "foreign_keys": [5]}]}, "`tables[0].foreign_keys`"),
        ({"enums": ["x"], "tables": [{"name": "a"}]}, "`enums`"),
        ({"columns": 5}, "`columns`"),
        ({"columns": [{"table_name": "a"}], "constraints": 5}, "`constraints`"),      # CodeRabbit on #138
        ({"tables": [{"name": "a", "columns": 0}]}, "`tables[0].columns`"),
        ({"enums": 0, "tables": [{"name": "a"}]}, "`enums`"),
        ({"tables": 0}, "`tables`")]),
    "crux_check --lab": ("perf-budget-gate", "crux_check",
                         ["--origin", "https://a.example", "--lab", "BAD", "--response", "BAD"], CODE, []),
}
NODE_CASES = {
    "measure_vitals --budget": ("perf-budget-gate", "measure_vitals.mjs",
                                ["http://127.0.0.1:9/", "--budget", "BAD"], CODE, [
        ({"defaults": {"lab": {"lcp_ms": "2500"}}}, "`defaults.lab.lcp_ms`"),
        ({"defaults": {"bytes": {"css": "60KB"}}}, "`defaults.bytes.css`"),
        ({"pages": {"home": {"lab": []}}}, "`pages.home.lab`")]),
    "a11y_runtime --budget": ("a11y-audit-runner", "a11y_runtime.mjs",
                              ["--url", "http://127.0.0.1:9/", "--axe", "axe.js", "--budget", "BAD"], CODE, [
        ({"defaults": {"contrast_failures": "0"}}, "`contrast_failures`"),
        ({"defaults": []}, "`defaults`")]),
    # browser_common.readNav(), which each gate that opens a URL calls (P34).
    "a11y_runtime --steps": ("a11y-audit-runner", "a11y_runtime.mjs",
                             ["--url", "http://127.0.0.1:9/", "--axe", "axe.js", "--steps", "BAD"], CODE, [
        ([{"click": 5}], "bad.json: step 1: click"),
        ([{"fill": "#q", "value": []}], "bad.json: step 1: value"),
        ([None], "bad.json: step 1 is not an object")]),
    "a11y_runtime --storage-state": ("a11y-audit-runner", "a11y_runtime.mjs",
                                     ["--url", "http://127.0.0.1:9/", "--axe", "axe.js", "--storage-state", "BAD"],
                                     CODE, [
        ({"cookies": {}}, "storageState"),
        ({"origins": 5}, "storageState")]),
}


class EveryLoaderChecksTheShape(TempDirTest):

    def run_case(self, case, run, skill, script, args, codes, extras):
        payloads = [(value, "bad.json") for value in TOP if not (value == [] and case in LISTS)] + extras
        for value, names in payloads:
            with self.subTest(payload=json.dumps(value)[:60]):
                self.reset()
                for name, text in FILES.items():
                    self.write(name, text)
                self.write("bad.json", json.dumps(value))
                proc = run(skill, script, *[a.replace("BAD", "bad.json") for a in args], cwd=self.tmp)
                text = output(proc)
                self.assertNotIn("Traceback", text)
                self.assertNotIn("    at ", text)                      # a Node stack
                if isinstance(codes, int):
                    self.assertEqual(codes, proc.returncode, text)
                else:
                    self.assertIn(proc.returncode, codes, text)
                self.assertIn(names.replace("BAD", "bad.json"), text)

    def reset(self):
        for child in list(self.tmp.iterdir()):
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

    def test_a_python_loader(self):
        for case, (skill, script, args, codes, extras) in CASES.items():
            with self.subTest(case=case):
                self.run_case(case, run_py, skill, script, args, codes, extras)

    @unittest.skipUnless(NODE, "node is not installed")
    def test_a_node_loader(self):
        for case, (skill, script, args, codes, extras) in NODE_CASES.items():
            with self.subTest(case=case):
                self.run_case(case, run_node, skill, script, args, codes, extras)

    def test_the_table_reaches_every_loader(self):
        """A loader added later gets a row: every script that reads JSON is in
        the table, or named here with the reason it needs none."""
        exempt = {"extract_literals",     # package.json, read with isinstance at every step
                  "extract_system", "tw_probe", "browser_common", "dtcg", "project_config",
                  "figma_common", "render_email", "snapshot_matrix", "critique_snapshots"}
        tested = {script.split(".")[0] for _, script, *_ in [*CASES.values(), *NODE_CASES.values()]}
        readers = {p.stem for p in SKILLS.glob("*/scripts/*") if p.suffix in (".py", ".mjs")
                   and ("json.loads(" in p.read_text(encoding="utf-8")
                        or "readJsonFile(" in p.read_text(encoding="utf-8"))}
        self.assertTrue(readers, "found no script that reads JSON")
        self.assertEqual(set(), readers - tested - exempt)


class TheAnswersFile(TempDirTest):
    """scaffold_ui --answers, on a model introspect_schema wrote (CodeRabbit on #138)."""

    def test_answers_must_be_an_object(self):
        dump = self.write("dump.json", json.dumps({"tables": [{"name": "posts", "primary_key": ["id"], "columns": [
            {"name": "id", "type": "uuid", "nullable": False}, {"name": "title", "type": "text"}]}]}))
        made = run_py("content-model-to-ui", "introspect_schema", dump, "-o", "model.json", cwd=self.tmp)
        self.assertEqual(0, made.returncode, output(made))
        for value in ([], "x", 5):
            with self.subTest(answers=value):
                self.write("answers.json", json.dumps(value))
                proc = run_py("content-model-to-ui", "scaffold_ui", "model.json", "--answers", "answers.json",
                              "--dry-run", cwd=self.tmp)
                self.assertNotIn("Traceback", output(proc))
                self.assertEqual(2, proc.returncode, output(proc))
                self.assertIn("answers.json must be an object of answers", output(proc))


class TheValuesMeanWhatTheySay(TempDirTest):
    """G11's second half: `"is_taste": "false"` made a major finding taste."""

    def test_false_as_text_is_false(self):
        findings = self.write("f.json", json.dumps([{**FINDING, "is_taste": "false", "count": "3"}]))
        proc = run_py("design-critique-gate", "critique_report", findings, "--fail-on", "never", cwd=self.tmp)
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertRegex(output(proc), r"1 findings?: 0 blocking . 1 major . 0 minor . 0 taste")

    def test_a_null_limit_still_lifts_a_default(self):
        """A control: `null` in `bytes` or `lab` lifts the default limit, as
        both perf gates read it (measure_vitals.mjs skips a null lab limit)."""
        self.write("dist/index.html", EMAIL)
        budget = self.write("b.json", json.dumps({"defaults": {"bytes": {"media": None},
                                                               "lab": {"inp_ms": None}}}))
        proc = run_py("perf-budget-gate", "perf_audit", "dist", "--budget", budget, cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        self.assertNotIn("must be", output(proc))


if __name__ == "__main__":
    unittest.main()
