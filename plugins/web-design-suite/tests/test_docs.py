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

import ast
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import unittest

from wds_support import NODE, OFF, PLUGIN, SKILLS, TempDirTest, env, output

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

    def test_the_access_boundary_is_stated(self):
        """DL-B1 and DL-A5 (W1): nothing said which key goes where, the
        permission RPC was a `security definer` function in the exposed schema
        with no search_path, the JWT's claims were trusted whole, and the fix
        offered for Realtime deletes does not work on a table with RLS."""
        text = (SKILLS / "content-model-to-ui" / "references" /
                "supabase-integration.md").read_text(encoding="utf-8")
        for wrong in ("returns boolean security definer`",           # in public, no search_path
                      "The JWT's claims, or",                         # user_metadata is user-writable
                      "REPLICA IDENTITY FULL` gives you the old row"):  # not under RLS
            with self.subTest(wrong=wrong):
                self.assertNotIn(wrong, text)
        for right in ("## 9. Who talks to the database", "sb_publishable_", "sb_secret_", "bypassrls",
                      "Every `VITE_` variable is public", '"apikey": SUPABASE_PUBLISHABLE_KEY',
                      "security definer set search_path = ''", "revoke execute on function private.",
                      "Never `user_metadata`", "A claim is as old as the token",
                      "not on `DELETE`", "the `old` record still holds only the key",
                      "A public bucket is world-readable"):
            with self.subTest(right=right):
                self.assertIn(right, text)
        # The secret key never appears in browser code: no VITE_ name holds it.
        self.assertNotRegex(text, r"VITE_\w*(SECRET|SERVICE)")


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
        proc = subprocess.run([NODE, str(harness), str(doc)], capture_output=True, timeout=60, env=env())
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


def frontmatter(skill_md) -> dict[str, str]:
    """The SKILL.md frontmatter's top-level `key: value` lines (all one-line)."""
    text = skill_md.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{skill_md}: no frontmatter"
    block = text[4:text.index("\n---\n", 4)]
    return dict(re.match(r"([\w-]+):\s?(.*)", line).groups() for line in block.splitlines()
                if re.match(r"[\w-]+:", line))


class SkillFrontmatter(unittest.TestCase):
    """XC-C5: every description parses as YAML and stays inside Claude Code's
    1,024-character limit. An unquoted value with ": " is a YAML error; one
    with " #" is silently cut at the #, which the first install hit."""

    def test_every_skill_has_a_name_and_a_description_that_parse(self):
        skills = sorted(SKILLS.glob("*/SKILL.md"))
        self.assertEqual(len(skills), 13)
        for skill_md in skills:
            with self.subTest(skill=skill_md.parent.name):
                fields = frontmatter(skill_md)
                self.assertEqual(fields.get("name"), skill_md.parent.name)
                description = fields.get("description", "")
                self.assertTrue(description)
                if description[:1] not in "\"'":
                    self.assertNotIn(": ", description)
                    self.assertNotIn(" #", description)
                    self.assertNotIn(description[:1], "[]{}>|*&!%@`,?")
                self.assertLessEqual(len(description), 1024)


SHIPPED = sorted({p.stem for p in SKILLS.glob("*/scripts/*") if p.suffix in {".py", ".mjs"}},
                 key=len, reverse=True)
# A suite script however a doc spells its path: -m scripts.x, scripts/x.py,
# "${CLAUDE_SKILL_DIR}/scripts/x.py", "$WDS/x.py", <skill>/scripts/x.mjs.
SCRIPT_CALL = re.compile(r"\bscripts\.({0})\b|\b({0})\.(?:py|mjs)\b".format("|".join(SHIPPED)))
NOT_SHELL = {"css", "scss", "tsx", "jsx", "ts", "js", "json", "html", "yaml", "yml", "sql", "mjs"}


def documented_calls():
    """(doc, script, flag, command) for every flag written after a suite script
    in a shell block or an inline code span."""
    for doc in doc_files():
        text = doc.read_text(encoding="utf-8")
        chunks = [body for lang, body in re.findall(r"^```(\w*)[^\n]*\n(.*?)^```", text, re.S | re.M)
                  if lang.lower() not in NOT_SHELL]
        chunks += [span for span in re.findall(r"`([^`\n]+)`", text) if SCRIPT_CALL.search(span)]
        for chunk in chunks:
            for line in re.sub(r"\\\n\s*", " ", chunk).splitlines():
                for part in re.split(r"&&|\|\||[|;]", line.split(" #", 1)[0]):
                    m = SCRIPT_CALL.search(part)
                    if m:
                        for flag in re.findall(r"(?<![\w-])(--[a-z][a-z0-9-]*)", part[m.end():]):
                            yield doc, m.group(1) or m.group(2), flag, part.strip()


class DocumentedFlags(unittest.TestCase):
    """XC-C5, GT-A10: every flag a doc passes to a suite script is one that
    script's own parser accepts (read from its --help)."""

    def accepted(self) -> dict[str, set[str]]:
        flags = {}
        for script in sorted(SKILLS.glob("*/scripts/*")):
            if script.suffix == ".py" and script.stem != "dtcg_values":
                argv = [sys.executable, str(script), "--help"]
            elif script.suffix == ".mjs" and NODE:
                argv = [NODE, str(script), "--help"]
            else:
                continue
            help_text = output(subprocess.run(argv, capture_output=True, timeout=60, env=env()))
            subcommands = re.search(r"\{([a-z][\w,-]*)\}", help_text)
            for sub in subcommands.group(1).split(",") if subcommands else ():
                help_text += output(subprocess.run(argv[:-1] + [sub, "--help"], capture_output=True,
                                                   timeout=60, env=env()))
            flags[script.stem] = set(re.findall(r"--[a-z][a-z0-9-]*", help_text)) | {"--help"}
        return flags

    def test_every_documented_flag_exists(self):
        accepted = self.accepted()
        calls = list(documented_calls())
        self.assertGreater(len(calls), 50)
        for doc, script, flag, command in calls:
            if script not in accepted:
                continue                                    # a module, or node is absent
            with self.subTest(doc=str(doc.relative_to(PLUGIN)), flag=flag, command=command[:90]):
                self.assertIn(flag, accepted[script])


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


# A drive-letter path two folders deep, also as JSON and source code write it
# (with doubled backslashes), except the `C:\path\to\…` placeholder; a WSL or
# Git Bash drive mount; a home folder on Linux or macOS, or root's.
MACHINE_PATH = re.compile(r"\b[A-Za-z]:(?!(?:\\\\|[\\/])path(?:\\\\|[\\/])to\b)"
                          r"(?:\\\\|[\\/])[\w .()-]+(?:\\\\|[\\/])[\w .()-]+"
                          r"|(?<![\w.])/mnt/[a-z]/[\w.-]+|(?<![\w.:])/[a-z]/(?:DEV|Users|dev|home)\b"
                          r"|/home/[A-Za-z][\w-]*|/Users/[A-Za-z][\w-]*|/root/\.")
SHIPPED_TEXT = {".md", ".py", ".mjs", ".js", ".json", ".css", ".html", ".sh", ".ts", ".tsx",
                ".jsx", ".yml", ".yaml", ".txt", ""}


class NoMachinePaths(unittest.TestCase):
    """3.2.1: the 3.0.1 CHANGELOG entry named a report by its folder in the
    maintainer's workspace, a path no user has (3.0.0 did the same with the
    sandbox's home folder). Nothing shipped may point at a machine."""

    def test_no_shipped_file_names_a_folder_on_the_authors_machine(self):
        found = []
        for path in sorted(PLUGIN.rglob("*")):
            if path.is_file() and path.suffix in SHIPPED_TEXT and "__pycache__" not in path.parts:
                text = path.read_text(encoding="utf-8", errors="replace")
                found += [f"{path.relative_to(PLUGIN).as_posix()}:{text.count(chr(10), 0, m.start()) + 1}: "
                          f"{m.group(0)}" for m in MACHINE_PATH.finditer(text)]
        self.assertEqual([], found)

    def test_the_pattern_sees_every_way_a_path_is_written(self):
        """3.2.1 review: the pattern missed a Windows path as JSON and source
        code store it, and WSL paths, which the release procedure uses."""
        # Assembled from pieces, so this file does not name a machine itself.
        bs, sl = "\\", "/"
        for text in ("see C:" + bs + "DEV" + bs + "dev plans" + bs + "report.md",
                     '"report": "C:' + bs * 2 + "Users" + bs * 2 + "vybec" + bs * 2 + 'notes.md"',
                     "C:" + sl + "Users" + sl + "vybec" + sl + "AppData",
                     "cd " + sl.join(["", "mnt", "c", "DEV", "Pro-Web-Designer-Suite-Plug-in"]),
                     "cd " + sl.join(["", "c", "DEV", "Pro-Web-Designer-Suite-Plug-in"]),
                     sl.join(["", "home", "claude", "wds"]), sl.join(["", "Users", "haas", "site"]),
                     sl.join(["", "root", ".claude", "x"])):
            with self.subTest(text=text):
                self.assertTrue(MACHINE_PATH.search(text))
        for text in ("https://github.com/Vybecode-LTD/x", "a:hover", "url(/img/a.png)", "~/project",
                     "$HOME/.claude", "src/components/card.css", "python -m http.server",
                     "set WDS_NODE_MODULES=C:" + bs * 2 + "path" + bs * 2 + "to" + bs * 2 + "project",
                     "/opt/pw-browsers/chromium", r"re.sub(r'\\\n\s*', ' ', chunk)"):
            with self.subTest(clean=text):
                self.assertIsNone(MACHINE_PATH.search(text))


PYTHON_FLOOR = (3, 9)
SCRIPTS = sorted(p for folder in ("skills", "tests", "tools") for p in (PLUGIN / folder).rglob("*.py"))


def floor_python() -> str | None:
    """An interpreter at the floor: WDS_FLOOR_PYTHON (a value in OFF switches
    the check off), else the one `uv python find` gives."""
    named = os.environ.get("WDS_FLOOR_PYTHON")
    if named is not None:
        return None if named.strip().lower() in OFF else named
    uv = shutil.which("uv")
    if not uv:
        return None
    proc = subprocess.run([uv, "python", "find", "%d.%d" % PYTHON_FLOOR], capture_output=True, text=True, env=env())
    return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else None


FLOOR_PYTHON = floor_python()


class PythonFloor(unittest.TestCase):
    """3.2.1 stated a floor of Python 3.10, because the test harness used calls
    only 3.10 has (`ignore_cleanup_errors`, `write_text(newline=)`, slicing
    `Path.parents`). The Python macOS still ships is 3.9, so 3.3.0 supports
    it: the harness no longer needs 3.10, and the README says 3.9.

    Parsing with the floor's grammar is a quick first check, and only that:
    `ast.parse(feature_version=)` on a newer Python accepts, for one, a PEP 701
    f-string the floor refuses, and it cannot see a library call the floor
    lacks. The floor interpreter itself compiles every script and runs every
    shipped script's --help; running the whole suite on the floor is the full
    check (release procedure, step 2)."""

    def test_the_readme_states_the_floor(self):
        phrase = "Python %d.%d or newer" % PYTHON_FLOOR
        self.assertTrue(phrase in (PLUGIN / "README.md").read_text(encoding="utf-8"),
                        f"the README does not say {phrase!r}")

    def test_every_script_parses_with_the_floors_grammar(self):
        self.assertGreater(len(SCRIPTS), 40)
        for path in SCRIPTS:
            with self.subTest(script=path.relative_to(PLUGIN).as_posix()):
                ast.parse(path.read_bytes(), feature_version=PYTHON_FLOOR)

    @unittest.skipUnless(FLOOR_PYTHON, "set WDS_FLOOR_PYTHON, or install uv, to run the scripts on the floor")
    def test_every_script_runs_on_the_floor_interpreter(self):
        probe = subprocess.run([FLOOR_PYTHON, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
                               capture_output=True, text=True, env=env(), timeout=60)
        self.assertEqual("%d.%d" % PYTHON_FLOOR, probe.stdout.strip(), output(probe) if probe.returncode else "")
        compiled = subprocess.run([FLOOR_PYTHON, "-c",
                                   "import sys\nfor p in sys.argv[1:]:\n"
                                   "    compile(open(p, 'rb').read(), p, 'exec')\n", *map(str, SCRIPTS)],
                                  capture_output=True, env=env(), timeout=120)
        self.assertEqual(0, compiled.returncode, output(compiled))
        for script in sorted(SKILLS.glob("*/scripts/*.py")):
            with self.subTest(script=script.relative_to(PLUGIN).as_posix()):
                proc = subprocess.run([FLOOR_PYTHON, str(script), "--help"], capture_output=True,
                                      env=env(), timeout=60)
                self.assertEqual(0, proc.returncode, output(proc))

    @unittest.skipUnless(FLOOR_PYTHON, "set WDS_FLOOR_PYTHON, or install uv, to run the harness on the floor")
    def test_the_harness_runs_on_the_floor_interpreter(self):
        """On 3.9, 3.2.1's harness errored in 181 tests, on
        `TemporaryDirectory(ignore_cleanup_errors=)`; past that, in 192, on
        `write_text(newline=)`. test_harness exercises both."""
        proc = subprocess.run([FLOOR_PYTHON, "-B", "-m", "unittest", "test_harness"], cwd=PLUGIN / "tests",
                              capture_output=True, env=env(), timeout=120)
        self.assertEqual(0, proc.returncode, output(proc))


if __name__ == "__main__":
    unittest.main()
