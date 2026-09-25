"""Documented commands, run as written (3.1.0).

Regressions covered:
- XC-A1: the README's "Quick start on an inherited codebase" failed at step 2:
  step 1 wrote no literals.json, and the codemod lines passed the mapping as
  the path to rewrite and omitted -m, so argparse exited 2.
- LC-A6: the migration's rebase recipe resolved conflicts with
  `git checkout --theirs`, which during a rebase is YOUR commit: the
  teammate's change vanished and the codemod reported 0 replacements, exit 0.
- LC-A13: the before/after audit recipe chained
  `git stash && audit … && git stash pop`; the audit exits 1 on any legacy
  code, so `pop` never ran and the work was stranded in the stash.
- GT-A4: three docs taught their own pre-commit hook instead of the shipped
  one: a `git diff --cached` list word-split on spaces, every staged file
  handed to the audit, and in one no shebang and no `set -e`.
- SB-A2, SS-A6: the Tailwind focus-ring utility and three pattern examples
  set `outline: none`, so forced-colors users lost the focus indicator.
- SB-A12: six places said an off-scale Tailwind class "is a build error".
  Tailwind generates nothing for it, silently, so nobody went looking.
- SS-A14: the studio's default deliverable was a ZIP, even inside a repo.
- The email skill's first step copied a template into the installed plugin.
- XC-A4: a script run by path wrote __pycache__ into the plugin.
- DL-A4: the optimistic-update sample never threw (supabase-js returns
  errors), so a rejected write had no rollback and no message; the keyset
  sample pasted the cursor into `.or()` unchecked.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import unittest

from wds_support import NODE, PLUGIN, SKILLS, TempDirTest, env, output

GIT = shutil.which("git")
GIT_ENV = {"GIT_AUTHOR_NAME": "wds-test", "GIT_AUTHOR_EMAIL": "wds-test@example.invalid",
           "GIT_COMMITTER_NAME": "wds-test", "GIT_COMMITTER_EMAIL": "wds-test@example.invalid",
           "GIT_EDITOR": "true"}
MAPPING = {"schema": "design-token-migration/mapping@1",
           "rules": [{"id": "space-13", "kind": "spacing", "scope": "value",
                      "prop_classes": ["gap"], "match": ["13px"],
                      "replacement": "var(--gap-related)", "confidence": "snap"}]}


def code_blocks(path) -> list[str]:
    """Every fenced code block in a markdown file."""
    return re.findall(r"^```[^\n]*\n(.*?)^```", path.read_text(encoding="utf-8"), re.S | re.M)


def doc_files() -> list:
    return sorted([*SKILLS.rglob("*.md"), PLUGIN / "README.md"])


def sh_block(path, marker: str) -> list[str]:
    """The lines of the first ```sh block after `marker` in a doc file."""
    text = path.read_text(encoding="utf-8").split(marker, 1)[1]
    block = re.search(r"```sh\n(.*?)```", text, re.S).group(1)
    return [ln.strip() for ln in block.splitlines()
            if ln.strip() and not ln.strip().startswith("#")]


def run_recipe(lines, cwd, substitutions=()):
    """Run documented shell lines the way sh would, without needing sh:
    `a && b` stops at the first failure, separate lines always run, and
    `> file` redirects stdout. Returns [(command, returncode)]."""
    results = []
    for line in lines:
        for old, new in substitutions:
            line = line.replace(old, new)
        for part in line.split("&&"):
            part = part.split("  #", 1)[0].strip()
            target = None
            if " > " in part:
                part, target = (x.strip() for x in part.split(" > ", 1))
            argv = shlex.split(part, posix=True)
            extra = dict(GIT_ENV)
            if argv[0] == "git":
                argv[0] = GIT
            elif argv[0] == "python":
                argv[0] = sys.executable
                if argv[1] == "-m":
                    module = argv[2].split(".", 1)[1]
                    extra["PYTHONPATH"] = str(next(SKILLS.glob(f"*/scripts/{module}.py")).parent.parent)
            proc = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=300, env=env(**extra))
            if target:
                try:
                    (cwd / target).write_bytes(proc.stdout)
                except OSError:
                    pass
            results.append((part, proc.returncode))
            if proc.returncode != 0:
                break                      # `&&` stops; the next line still runs
    return results


def code_block_after(heading: str) -> list[str]:
    text = (PLUGIN / "README.md").read_text(encoding="utf-8")
    after = text.split(heading, 1)[1]
    block = re.search(r"```(?:bash)?\n(.*?)```", after, re.S).group(1)
    return [ln for ln in block.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]


def run_line(line: str, variables: dict, cwd) -> subprocess.CompletedProcess | None:
    """Run one documented shell line: variable assignments are recorded, the
    `python` lines are run with the variables expanded. `python -m scripts.X`
    gets the skill that holds scripts/X.py on PYTHONPATH, as the docs assume."""
    m = re.match(r'^(\w+)="([^"]*)"\s*$', line.strip())
    if m:
        variables[m.group(1)] = re.sub(r"\$(\w+)", lambda v: variables[v.group(1)], m.group(2))
        return None
    line = line.split("  #", 1)[0]
    line = re.sub(r"\$(\w+)", lambda v: variables[v.group(1)], line)
    argv = shlex.split(line, posix=True)
    assert argv[0] == "python", line
    extra_env = {}
    if argv[1] == "-m":
        module = argv[2].split(".", 1)[1]
        skill = next(p.parent.parent for p in SKILLS.glob(f"*/scripts/{module}.py"))
        extra_env["PYTHONPATH"] = str(skill)
    return subprocess.run([sys.executable, *argv[1:]], cwd=cwd, capture_output=True,
                          timeout=300, env=env(**extra_env))


class ReadmeQuickStart(TempDirTest):

    def test_the_inherited_codebase_quick_start_runs_as_written(self):
        self.write("src/card.css", ".card { padding: 13px; margin-block-end: 24px; "
                                   "color: #3a3a3a; }\n")
        variables = {"WDS": str(SKILLS), "HOME": os.path.expanduser("~")}
        for line in code_block_after("## Quick start on an inherited codebase"):
            with self.subTest(line=line):
                proc = run_line(line, variables, self.tmp)
                if proc is not None:
                    self.assertIn(proc.returncode, (0, 1), f"{line}\n{output(proc)}")
        self.assertTrue((self.tmp / "proposal" / "mapping.json").exists())
        self.assertTrue((self.tmp / ".design-baseline.json").exists())


class SupabaseGuidance(unittest.TestCase):
    """DL-A3: the documented model of how writes fail under RLS was wrong in
    the way that produces insecure code."""

    def test_the_rls_write_model_matches_postgres(self):
        text = (SKILLS / "content-model-to-ui" / "references" /
                "supabase-integration.md").read_text(encoding="utf-8")
        for wrong in ("a blocked write is loud", "often a parent the user cannot see",
                      "a rejected write returns `42501`, not a network error"):
            with self.subTest(wrong=wrong):
                self.assertNotIn(wrong, text)
        for right in ("bypass row security", "changes 0 rows and reports success",
                      "throwOnError", "revoke update (role, is_admin"):
            with self.subTest(right=right):
                self.assertIn(right, text)


# Runs the doc's two samples against a stand-in that behaves like supabase-js:
# a query resolves to { data, error } and rejects only after .throwOnError();
# .single() on zero rows is PGRST116.
SAMPLES_HARNESS = r"""
const fs = require('fs');
const md = fs.readFileSync(process.argv[2], 'utf8');
const blocks = [...md.matchAll(/```ts\n([\s\S]*?)```/g)].map((m) => m[1]);
const keyset = blocks.find((b) => b.includes('.or('));
const mutation = blocks.find((b) => b.includes('useMutation('));

function client(rows, error) {
  const calls = [];
  let throws = false;
  let single = false;
  const q = {
    throwOnError() { throws = true; return q; },
    single() { single = true; return q; },
    then(ok, bad) {
      let r = error ? { data: null, error } : { data: rows, error: null };
      if (!error && single) {
        r = rows.length === 1 ? { data: rows[0], error: null }
                              : { data: null, error: { code: 'PGRST116' } };
      }
      return (throws && r.error ? Promise.reject(r.error) : Promise.resolve(r)).then(ok, bad);
    },
  };
  for (const name of ['from', 'select', 'order', 'limit', 'update', 'eq', 'or', 'gt', 'lt']) {
    q[name] = (...args) => { calls.push([name, ...args]); return q; };
  }
  return { supabase: { from: (...args) => q.from(...args) }, calls };
}

function page(cursor) {
  const { supabase, calls } = client([], null);
  try {
    new Function('supabase', 'cursor', keyset)(supabase, cursor);
  } catch (e) {
    return { threw: String(e.message) };
  }
  return { or: calls.filter((c) => c[0] === 'or').map((c) => c[1]) };
}

async function write(rows, error) {
  const { supabase } = client(rows, error);
  const body = 'let options;\nuseMutation = (o) => { options = o; };\n' + mutation + '\nreturn options;';
  const options = new Function('supabase', 'qc', 'toast', 'useMutation', body)(supabase, {}, {}, null);
  try {
    await options.mutationFn({ id: 1, name: 'x' });
    return 'resolved';
  } catch {
    return 'rejected';
  }
}

(async () => {
  const id = '3f2c1d4e-5a6b-4c7d-8e9f-0a1b2c3d4e5f';
  console.log(JSON.stringify({
    hostile: [page({ created_at: '2026-01-01T00:00:00Z,id.gt.0', id }),
              page({ created_at: '2026-01-01T00:00:00Z', id: id + '),or(id.gt.0' })],
    valid: page({ created_at: '2026-01-01T00:00:00.000Z', id }),
    hidden: await write([], null),
    denied: await write(null, { code: '42501', message: 'permission denied' }),
    saved: await write([{ id: 1, name: 'x' }], null),
  }));
})();
"""


@unittest.skipUnless(NODE, "node is not installed")
class SupabaseSamples(TempDirTest):
    """DL-A4, by running the samples rather than reading them."""

    def test_the_samples_fail_loudly_and_check_the_cursor(self):
        harness = self.write("samples.cjs", SAMPLES_HARNESS)
        doc = SKILLS / "content-model-to-ui" / "references" / "supabase-integration.md"
        proc = subprocess.run([NODE, str(harness), str(doc)], capture_output=True, timeout=60)
        self.assertEqual(proc.returncode, 0, output(proc))
        got = json.loads(proc.stdout)
        for case in got["hostile"]:
            self.assertIn("threw", case)                   # never reaches .or()
        self.assertEqual(len(got["valid"].get("or", [])), 1, got["valid"])
        self.assertEqual(got["hidden"], "rejected")        # RLS hid the row: 0 rows, no error
        self.assertEqual(got["denied"], "rejected")        # 42501
        self.assertEqual(got["saved"], "resolved")


class HookGuidance(unittest.TestCase):
    """GT-A4: the docs point at the shipped hook instead of teaching their own."""

    def test_no_doc_hand_rolls_a_pre_commit_hook(self):
        for path in doc_files():
            for block in code_blocks(path):
                if "pre-commit" in block:
                    with self.subTest(doc=str(path.relative_to(PLUGIN))):
                        self.assertNotIn("git diff --cached", block)


class ScriptInvocation(TempDirTest):
    """XC-A8: the skills said `python -m scripts.X src/` and "run from the skill
    root" — `-m` needs the skill folder, `src/` means the project, and nothing
    said which wins, so outputs and baselines landed inside the plugin."""

    def test_every_skill_that_runs_a_script_says_how(self):
        for skill_md in sorted(SKILLS.glob("*/SKILL.md")):
            text = skill_md.read_text(encoding="utf-8")
            if not re.search(r"scripts[./]\w+", text):
                continue
            with self.subTest(skill=skill_md.parent.name):
                self.assertNotIn("skill root", text)
                head = text[:3000]                          # survives compaction
                self.assertIn("Running the scripts", head)
                paths = re.findall(r'"\$\{(CLAUDE_SKILL_DIR|CLAUDE_PLUGIN_ROOT)\}/([^"]+)"', head)
                self.assertTrue(paths)
                for var, rel in paths:
                    base = skill_md.parent if var == "CLAUDE_SKILL_DIR" else PLUGIN
                    self.assertTrue((base / rel).is_file(), f"{var}/{rel}")

    def test_the_email_quick_start_copies_the_template_into_the_project(self):
        text = (SKILLS / "email-template-system" / "SKILL.md").read_text(encoding="utf-8")
        copies = re.findall(r"^\s*cp\s+(\S+)\s+(\S+)", text, re.M)
        self.assertTrue(copies)
        for src, dst in copies:
            with self.subTest(dst=dst):
                self.assertIn("${CLAUDE_SKILL_DIR}", src)
                self.assertNotIn("assets/", dst)

    def test_running_a_script_by_path_leaves_no_bytecode_beside_it(self):
        for skill, script in (("figma-variables-sync", "figma_to_tokens.py"),
                              ("figma-variables-sync", "figma_audit.py"),
                              ("design-token-migration", "apply_codemod.py"),
                              ("design-system-docs", "build_docs.py")):
            with self.subTest(script=script):
                scripts = self.tmp / script / "scripts"             # one copy per script
                shutil.copytree(SKILLS / skill / "scripts", scripts,
                                ignore=shutil.ignore_patterns("__pycache__"))
                proc = subprocess.run([sys.executable, str(scripts / script), "--help"],
                                      cwd=self.tmp, capture_output=True, timeout=60,
                                      env=env(PYTHONDONTWRITEBYTECODE=None))
                self.assertEqual(proc.returncode, 0, output(proc))
                cache = scripts / "__pycache__"
                self.assertFalse(cache.exists(), cache.exists() and sorted(p.name for p in cache.iterdir()))


class StudioGuidance(unittest.TestCase):
    """SB-A6 and SB-A7: guidance that described tools and behaviour that do
    not exist. SB-A2/SS-A6, SB-A12 and SS-A14: guidance that did harm as written."""

    def read(self, rel):
        return (SKILLS / "web-design-studio" / rel).read_text(encoding="utf-8")

    def test_the_handoff_names_no_build_script_the_suite_does_not_ship(self):
        text = self.read("references/handoff-conventions.md")
        self.assertNotIn("build-tokens.mjs", text)
        self.assertFalse(list(SKILLS.rglob("build-tokens*")))
        self.assertIn("`src/styles/tokens.css`", text)

    def test_tailwind_v3_is_not_said_to_emit_native_layers(self):
        for rel in ("assets/configs/tailwind.config.ts", "references/stack-tailwind.md"):
            with self.subTest(file=rel):
                text = self.read(rel)
                self.assertNotIn("v3 emits into three", text)
                self.assertIn("unlayered", text.lower())

    def test_no_focus_style_removes_the_outline(self):
        """Forced-colors mode repaints outlines and drops box-shadows."""
        focus_rule = re.compile(r"(@utility\s+focus-ring|'\.focus-ring'\s*:|[^{};\n]*:focus[\w-]*[^{};\n]*)"
                                r"\s*\{([^{}]*)\}")
        no_outline = re.compile(r"""outline\s*:\s*['"]?(none|0)\b""")
        for path in sorted(p for p in SKILLS.rglob("*")
                           if p.suffix in {".css", ".ts", ".md", ".mjs", ".html"}):
            for m in focus_rule.finditer(path.read_text(encoding="utf-8")):
                with self.subTest(file=str(path.relative_to(SKILLS)), rule=m.group(0).strip()[:60]):
                    self.assertIsNone(no_outline.search(m.group(2)))

    def test_a_missing_tailwind_class_is_not_called_a_build_error(self):
        """Tailwind generates nothing for a class that does not exist, and says nothing."""
        for path in sorted(p for d in ("web-design-studio", "design-token-migration")
                           for p in (SKILLS / d).rglob("*") if p.suffix in {".md", ".ts", ".css", ".mjs"}):
            text = re.sub(r"\s*\n\s*(?:\*|//|>)?\s*", " ", path.read_text(encoding="utf-8"))
            for m in re.finditer(r"build (?:errors?|tells you)", text):
                with self.subTest(file=str(path.relative_to(SKILLS)), at=text[max(0, m.start() - 50):m.end()]):
                    # Only "not a build error" / "no build error" may stand.
                    self.assertRegex(text[max(0, m.start() - 12):m.start()], r"\b(not a|no|never a)\s+$")

    def test_inside_a_repository_the_deliverable_is_the_repository(self):
        text = self.read("SKILL.md")
        self.assertNotIn("finish by producing a ZIP", text)
        self.assertIn("write the files into the repo itself", text)


@unittest.skipUnless(GIT, "git is not installed")
class MigrationRecipes(TempDirTest):

    def git(self, *args, check=True):
        return subprocess.run([GIT, *args], cwd=self.repo, capture_output=True, check=check,
                              env=env(**GIT_ENV))

    def setUp(self):
        super().setUp()
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("checkout", "-q", "-b", "main")
        self.css = self.write("repo/src/a.css", ".card {\n  margin: 13px;\n  color: #333333;\n}\n")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "base")
        self.mapping = self.write("repo/proposal/mapping.json", json.dumps(MAPPING))

    def codemod(self):
        proc = subprocess.run([sys.executable, str(SKILLS / "design-token-migration" / "scripts" /
                                                   "apply_codemod.py"),
                               "src/a.css", "-m", str(self.mapping), "--apply"],
                              cwd=self.repo, capture_output=True, env=env())
        self.assertIn("var(--gap-related)", self.css.read_text(encoding="utf-8"), output(proc))

    def test_the_rebase_recipe_keeps_the_teammates_change(self):
        self.git("checkout", "-q", "-b", "migration")
        self.codemod()
        self.git("commit", "-q", "-am", "migrate spacing")
        self.git("checkout", "-q", "main")
        self.css.write_text(".card {\n  margin: 13px; font-style: italic;\n  color: #333333;\n}\n",
                            encoding="utf-8")
        self.git("commit", "-q", "-am", "teammate: italic cards")
        self.git("checkout", "-q", "migration")
        self.assertNotEqual(self.git("rebase", "main", check=False).returncode, 0)  # the conflict

        lines = sh_block(SKILLS / "design-token-migration" / "references" / "migration-strategies.md",
                         "Resolve every conflict by re-running")
        run_recipe(lines, self.repo, [("path/to/conflicted.css", "src/a.css")])
        text = self.css.read_text(encoding="utf-8")
        self.assertIn("font-style: italic", text)                 # the teammate's change
        self.assertIn("var(--gap-related)", text)                 # migrated
        self.assertFalse((self.repo / ".git" / "rebase-merge").exists(), "rebase left unfinished")

    def test_the_before_and_after_audit_recipe_strands_nothing(self):
        self.git("checkout", "-q", "-b", "migration")
        self.codemod()
        self.git("commit", "-q", "-am", "migrate spacing")
        self.css.write_text(self.css.read_text(encoding="utf-8") + ".wip { padding: 7px; }\n",
                            encoding="utf-8")
        wip = self.css.read_text(encoding="utf-8")

        lines = sh_block(SKILLS / "design-token-migration" / "SKILL.md", "### Phase 5 — Verify")
        run_recipe(lines, self.repo)
        self.assertEqual(self.css.read_text(encoding="utf-8"), wip, "the work in progress is gone")
        self.assertEqual(self.git("stash", "list").stdout, b"")
        for name in ("audit-before.json", "audit-after.json"):
            with self.subTest(report=name):
                json.loads((self.tmp / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
