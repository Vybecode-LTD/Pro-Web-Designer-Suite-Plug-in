"""tools/sync_caniemail.py (DL-C9): the email client matrix and the clients
lint_email.py blames are caniemail.com's data, so a client that changes is a
diff rather than drift.

Regressions covered: A15's corrections were made by hand, and the hand copies
drifted again. Against caniemail's data of 2026-09-16 the matrix had some 60
cells that differ from its latest results (Thunderbird's `@media`, Gmail's
custom properties, Outlook for Mac's `<svg>` and web fonts among them), and
the linter said that no client supports `gap`, that Gmail drops `object-fit`,
and that Samsung Email and Thunderbird have no custom properties, where
caniemail records the opposite. Errors for `float`, `box-shadow` and eight
more traced to no row of the matrix.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import unittest

from wds_support import PLUGIN, SKILLS, TempDirTest, env, load_script, output, run_py

TOOL = PLUGIN / "tools" / "sync_caniemail.py"
MATRIX = "skills/email-template-system/references/email-client-matrix.md"
LINT = "skills/email-template-system/scripts/lint_email.py"
PINNED = "tests/fixtures/caniemail.json"
NOT_GANGA = "Partial. Not supported with non Google accounts."
ONLY_GANGA = "Partial. Only supported with non Google accounts."


def tool():
    spec = importlib.util.spec_from_file_location("wds_sync_caniemail", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(*args, root=None) -> subprocess.CompletedProcess:
    extra = ["--root", str(root)] if root else []
    return subprocess.run([sys.executable, "-B", str(TOOL), *extra, *map(str, args)],
                          capture_output=True, env=env(), timeout=60)


class TheBlocksAreCaniemails(unittest.TestCase):

    def test_the_matrix_and_the_linter_are_in_step_with_the_pinned_data(self):
        proc = run("--check")
        self.assertEqual(0, proc.returncode, output(proc))

    def test_every_row_links_caniemails_page_and_its_test_date(self):
        text = (PLUGIN / MATRIX).read_text(encoding="utf-8")
        rows = re.findall(r"^\| \[(.+?)\]\((\S+)\) \| (\S+) \|", text, re.M)
        self.assertEqual(len(tool().ROWS), len(rows))
        for label, url, tested in rows:
            with self.subTest(row=label):
                self.assertRegex(url, r"^https://www\.caniemail\.com/features/[a-z0-9-]+/$")
                self.assertRegex(tested, r"^\d{4}-\d{2}-\d{2}$")

    def test_every_feature_the_linter_names_is_a_row_of_the_matrix(self):
        lint = load_script("email-template-system", "lint_email")
        rows = {slug for _, slug in tool().ROWS}
        named = [e[0] for e in lint.UNSUPPORTED_PROPS.values() if isinstance(e, tuple)]
        named += [e[0] for d in lint.UNSUPPORTED_PROPS.values() if isinstance(d, dict) for e in d.values()]
        errors = [s for s in named if s]
        named = errors + [e[0] for e in lint.PARTIAL_PROPS.values() if e]
        self.assertGreater(len(named), 20)
        for slug in named:
            with self.subTest(slug=slug):
                self.assertIn(slug, rows)
                self.assertIn(slug, lint.CANIEMAIL)
        for slug in errors:            # an error needs a client that drops the feature
            with self.subTest(error=slug):
                self.assertTrue(lint.CANIEMAIL[slug][1], slug)


class Cells(unittest.TestCase):
    """The rules a cell is read by, on caniemail's own shapes."""

    def cell(self, column, stats, notes=None):
        mod = tool()
        header, _, _, pairs = next(c for c in mod.COLUMNS if c[0] == column)
        return mod.cell(header, pairs, stats, notes or {}, "test")

    def test_the_last_version_listed_is_the_latest(self):
        # caniemail lists Outlook for Mac's 16.80 after its 2016; a numeric sort
        # would read 2016 as the newer.
        self.assertEqual(("y", []), self.cell("Outlook Mac", {"outlook": {"macos": {"2016": "n", "16.80": "y"}}}))
        self.assertEqual(("n", []), self.cell("Outlook Mac", {"outlook": {"macos": {"16.80": "y", "2016": "n"}}}))

    def test_platforms_that_differ_make_a_partial_cell(self):
        stats = {"apple-mail": {"macos": {"16": "y"}, "ios": {"17": "n #2"}}}
        self.assertEqual(("a", ["2"]), self.cell("Apple Mail", stats))
        self.assertEqual(("", []), self.cell("Samsung", stats))       # untested

    def test_the_gmail_apps_accounts_are_read_from_caniemails_notes(self):
        app = {"gmail": {"ios": {"2023-01": "a #1"}, "android": {"2023-01": "a #1"}}}
        self.assertEqual(("y", []), self.cell("Gmail app", app, {"1": NOT_GANGA}))
        self.assertEqual(("n", ["1"]), self.cell("GANGA", app, {"1": NOT_GANGA}))
        # box-shadow's note is the other way round.
        self.assertEqual(("n", ["1"]), self.cell("Gmail app", app, {"1": ONLY_GANGA}))
        self.assertEqual(("y", ["1"]), self.cell("GANGA", app, {"1": ONLY_GANGA}))
        # A partial for another reason stays partial for a Google account.
        both = {"gmail": {"ios": {"2023-01": "a #1 #2"}, "android": {"2023-01": "a #1 #2"}}}
        notes = {"1": "Partial. Not supported inside the `<body>`.", "2": NOT_GANGA}
        self.assertEqual(("a", ["1"]), self.cell("Gmail app", both, notes))
        self.assertEqual(("n", ["2"]), self.cell("GANGA", both, notes))
        # Gmail on the web is not the app: the note does not move it.
        web = {"gmail": {"desktop-webmail": {"2023-01": "a #1"}}}
        self.assertEqual(("a", ["1"]), self.cell("Gmail web", web, {"1": NOT_GANGA}))


class Refresh(TempDirTest):
    """A copy of the two files and the pinned data in a temporary folder."""

    def setUp(self):
        super().setUp()
        self.root = self.tmp / "plugin"
        for rel in (MATRIX, LINT, PINNED):
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(PLUGIN / rel, self.root / rel)
        self.data = json.loads((self.root / PINNED).read_bytes())

    def feature(self, data, slug):
        return next(f for f in data["data"] if f["slug"] == slug)

    def download(self, change=None):
        """The pinned data as caniemail serves it: more families, more features."""
        data = json.loads(json.dumps(self.data))
        for f in data["data"]:
            f["stats"]["orange"] = {"desktop-webmail": {"2024-04": "n"}}
        data["data"].insert(0, {"slug": "amp", "title": "AMP for Email", "stats": {}})
        data["nicenames"] = {"family": {}}
        if change:
            change(data)
        return self.write("data.json", json.dumps(data))

    def test_a_client_that_changes_is_a_diff(self):
        def thunderbird_media(data):
            self.feature(data, "css-at-media")["stats"]["thunderbird"]["macos"]["115.0"] = "y"
        proc = run("--data", self.download(thunderbird_media), "--check", root=self.root)
        self.assertEqual(2, proc.returncode, output(proc))        # --check reads the pinned data only
        proc = run("--data", self.download(thunderbird_media), root=self.root)
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertIn(f"rewrote: {MATRIX}", output(proc))
        self.assertIn(f"rewrote: {LINT}", output(proc))
        matrix = (self.root / MATRIX).read_bytes().decode("utf-8")
        row = next(line for line in matrix.splitlines() if "/css-at-media/)" in line)
        self.assertTrue(row.rstrip().endswith("| ✅ |"), row)       # Thunderbird is the last column
        lint = (self.root / LINT).read_bytes()
        self.assertIn(b'"css-at-media": ("2023-12-13", "word ganga",', lint)
        self.assertNotIn(b"\r\n", lint + matrix.encode("utf-8"))
        self.assertEqual(0, run("--check", root=self.root).returncode)

    def test_the_pin_keeps_only_what_the_matrix_reads_in_caniemails_order(self):
        def reorder(data):
            self.feature(data, "css-display-flex")["stats"]["outlook"]["macos"] = {"2016": "n", "16.80": "y"}
        self.assertEqual(0, run("--data", self.download(reorder), root=self.root).returncode)
        pinned = json.loads((self.root / PINNED).read_bytes())
        self.assertEqual([slug for _, slug in tool().ROWS], [f["slug"] for f in pinned["data"]])
        flex = self.feature(pinned, "css-display-flex")
        self.assertNotIn("orange", flex["stats"])
        self.assertEqual(["2016", "16.80"], list(flex["stats"]["outlook"]["macos"]))
        self.assertIn("MIT", pinned["licence"])
        self.assertEqual("https://www.caniemail.com/api/data.json", pinned["source"])

    def test_a_stale_block_fails_the_check_and_names_the_file(self):
        self.feature(self.data, "css-gap")["stats"]["yahoo"]["desktop-webmail"]["2026-01"] = "y"
        (self.root / PINNED).write_bytes(json.dumps(self.data).encode("utf-8"))
        proc = run("--check", root=self.root)
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn(f"stale: {MATRIX}", output(proc))
        self.assertIn(f"stale: {LINT}", output(proc))

    def test_data_it_cannot_read_writes_nothing(self):
        before = [(self.root / rel).read_bytes() for rel in (MATRIX, LINT, PINNED)]

        def result(data):
            self.feature(data, "css-gap")["stats"]["yahoo"]["ios"]["2026-01"] = "maybe"

        def gone(data):
            data["data"] = [f for f in data["data"] if f["slug"] != "html-dir"]

        def url(data):
            self.feature(data, "css-gap")["url"] = "https://example.com/css-gap/"

        def stats(data):
            self.feature(data, "css-gap")["stats"] = ["y"]

        def note(data):
            self.feature(data, "css-gap")["notes_by_num"] = {}

        for change in (result, gone, url, stats, note):
            with self.subTest(change=change.__name__):
                proc = run("--data", self.download(change), root=self.root)
                self.assertEqual(2, proc.returncode, output(proc))
                self.assertIn("sync_caniemail:", output(proc))
                self.assertEqual(before, [(self.root / rel).read_bytes() for rel in (MATRIX, LINT, PINNED)])

    def test_a_file_without_its_block_is_reported(self):
        lint = self.root / LINT
        lint.write_bytes(lint.read_bytes().replace(b"# END caniemail", b"# END"))
        proc = run(root=self.root)
        self.assertEqual(1, proc.returncode, output(proc))
        self.assertIn(f"{LINT}: 0 caniemail blocks, not one", output(proc))


class TheLinterBlamesCaniemailsClients(TempDirTest):

    def lint(self, style: str) -> list[dict]:
        page = self.write("mail.html", '<!doctype html><html lang="en"><head><meta charset="utf-8">'
                                       '<title>t</title></head><body>'
                                       '<table role="presentation"><tr><td style="%s">Hi</td></tr></table>'
                                       '</body></html>' % style)
        proc = run_py("email-template-system", "lint_email", page, "--format", "json", cwd=self.tmp)
        self.assertIn(proc.returncode, (0, 1), output(proc))
        return json.loads(proc.stdout.decode("utf-8"))["files"][str(page)]["findings"]

    def detail(self, style: str, check: str) -> str:
        found = [f for f in self.lint(style) if f["check"] == check]
        self.assertEqual(1, len(found), found)
        return found[0]["detail"]

    def test_flex_names_the_two_clients_that_drop_it(self):
        detail = self.detail("display:flex", "css")
        self.assertEqual("not supported in classic Outlook for Windows (Word engine) and the Gmail app with "
                         "a non-Google account (caniemail.com, tested 2021-11-02)", detail)

    def test_gap_and_object_fit_name_what_caniemail_records(self):
        gap = self.detail("gap:8px", "css")
        self.assertNotIn("no client", gap)
        self.assertIn("not supported in classic Outlook for Windows (Word engine) and Yahoo Mail", gap)
        fit = self.detail("object-fit:cover", "css")
        self.assertNotIn("Gmail on the web", fit)                # Gmail on the web supports it

    def test_a_partial_property_names_its_clients(self):
        detail = self.detail("background-size:cover", "css-partial")
        self.assertIn("the Gmail app with a non-Google account", detail)
        self.assertNotIn("not supported in Gmail.", detail)

    def test_an_unresolved_token_names_who_lacks_custom_properties(self):
        page = self.write("mail.html", '<!doctype html><html lang="en"><head><title>t</title></head>'
                                       '<body><p style="color:var(--fg)">Hi</p></body></html>')
        proc = run_py("email-template-system", "lint_email", page, "--format", "json", cwd=self.tmp)
        found = [f for f in json.loads(proc.stdout.decode("utf-8"))["files"][str(page)]["findings"]
                 if f["check"] == "tokens"]
        self.assertEqual(1, len(found), output(proc))
        self.assertNotIn("Samsung", found[0]["detail"])           # Samsung Email 9.0 supports them
        self.assertIn("(caniemail.com, tested 2020-02-25)", found[0]["detail"])


class TheMatrixSaysWhatItsCellsSay(unittest.TestCase):
    """The matrix's own notes, against its generated cells."""

    def test_stale_claims_are_gone(self):
        text = (SKILLS / "email-template-system" / "references" / "email-client-matrix.md").read_text(encoding="utf-8")
        stale = re.compile(r"Yahoo, Samsung and Thunderbird have no support|"
                           r"listed as \*partial\* on `caniemail\.com`: Gmail recognises|"
                           r"no nested, no height-based|"
                           r"`background-size` as a standalone property is not supported|"
                           r"Gmail does not support it except in webmail|"
                           r"absent on `div`s in Samsung Mail")
        self.assertNotRegex(text, stale)


if __name__ == "__main__":
    unittest.main()
