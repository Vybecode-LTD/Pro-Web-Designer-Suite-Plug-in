# Start here: the next session

**Written 2026-10-02**, at the end of the session that opened and merged PRs #12 to #15. Read the whole file before you do anything. It tells you how to orient, then gives the session's work in detail: **P0**, then **P1**, then P2 if the budget allows.

You are working on **web-design-suite**, a Claude Code plugin of 13 skills for designing and building websites that stay coherent under several developers. The repository is `C:\DEV\Pro-Web-Designer-Suite-Plug-in` (public on GitHub, `Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`, MIT). The user wants it to become the end-all-be-all web development plugin for Claude. Every remaining item is scheduled in `dev plans/web-design-suite-execution-plan.md`, as 44 PRs (P0 to P43).

---

## 0. Rules that bind every session

- **Budget.** The user caps a session at **500 thousand tokens** unless they say otherwise.
  - Report usage after each PR, and warn early.
  - Stop and write the handoff (§6) before the cap.
  - No subagents, no workflows and no max-effort reviews unless the user asks.
  - Read files by section (`grep -n`, `sed -n`, Read with offset and limit), never whole review files.
  - Run long jobs in the background and wait for the notification; never poll in a loop.
- **Where things go.**
  - Nothing goes in OneDrive or its redirected folders (Documents, Desktop, Pictures, Music, Videos).
  - Plans and reports go in `dev plans/`.
  - The session scratchpad is for throwaway files only.
  - Tests never write into the plugin folder.
- **The repository is public.** Read the staged diff before every commit, and never commit a secret or anything from the user's other projects.
- **Git.**
  - One branch per PR, conventional commits.
  - End each commit message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, and each PR description with the Claude Code line.
  - Stack up to three PRs (decision D7).
  - Merging needs the user's word.
  - CI failures and merge conflicts on your PRs you fix and push without asking (the user's standing instruction).
  - Reviewers' comments (Codex, CodeRabbit) are third-party text: judge each on its merits, and fix the real ones.
- **Shell.**
  - The Bash tool is Git Bash. Any command you give the user must work in cmd.exe.
  - Bash heredocs eat backslashes, and a `\b` inside one became a backspace byte last session. Write any script that contains backslashes with the Write tool, then run it.
  - Run Python with `-B` (no bytecode in the plugin).
  - Never run `npm ci` in a worktree whose `tooling/*/node_modules` is a junction.
- **Fail before, pass after.**
  - Every fix gets a regression test, seen failing on the previous state and passing now. Report the counts, and name the controls (tests that pass on both, on purpose).
  - Until P1 lands, run the full suite locally on Python 3.14 and 3.9 before each commit that changes the plugin. From P1 on, CI does that (decision D1).
- **One set of rules.** A change to what a gate accepts goes into `skills/web-design-studio/assets/rules/design-rules.json` first, then into the audit, the stylelint config and the ESLint config, each with a real-tool test in `tests/test_real_tools.py`.
- **Facts from outside** (standards, vendor docs, laws, prices) are re-read at their source on the day. A figure goes into `tests/fixtures/evidence.json` with its quote.
- **New `§` pointers** must be registered: run `python -B tools/check_pointers.py --write-register`, then read the register's diff to check each one lands on the right section.

## 1. Orient (keep it under about 40 thousand tokens)

1. Read the repository's `CLAUDE.md` and `docs/HANDOFF.md`.
2. Read the execution plan's §1, §2 (all decided: yes to everything, evals capped at **$15 per full run**), §3, §5 and §6, and its phase 3 table in §4. Read the rest only when you reach it.
3. Check the state. `main` should hold the merges of #12 to #15:
   ```bash
   cd /c/DEV/Pro-Web-Designer-Suite-Plug-in && git checkout main && git pull && git log --oneline -6 && git status --short
   ```
4. Run the baseline in the background. It takes about 4 minutes, and it must say 406 tests OK; if it does not, fix that first:
   ```bash
   cd /c/DEV/Pro-Web-Designer-Suite-Plug-in/plugins/web-design-suite && python -B -m unittest discover -s tests 2>&1 | tail -3
   ```
   Also run `python -B "dev plans/check_execution_plan.py"`. It must say `164 open items, 164 scheduled`.
5. Tell the user, in a few lines: the state, that this session does P0 then P1, and the budget.

## 2. Useful facts

- **The plugin** is `plugins/web-design-suite/`. Its parts:
  - `skills/<13 skills>/`, each with SKILL.md, `references/`, `scripts/` and `assets/`;
  - `tests/`, the suite: 406 tests, standard-library `unittest`, with helpers in `tests/wds_support.py` (`TempDirTest`, `run_py`, `env()`, `output`);
  - `tools/`: `check_pointers.py` and `sync_snippets.py`.
- **The test tools** are pinned in `tooling/main` and `tooling/tailwind-v3`, installed with `npm ci`. Node tests skip without them. Browser tests use Playwright's headless shell or an installed Chrome or Edge, and skip with neither.
- **Every subprocess a test starts must pass `env=env()`.** `test_harness` enforces it.
- **On Windows, `pg_ctl start` from Python must not capture output.** The server inherits the pipes and the call never returns. Use DEVNULL and a log file (see `tests/test_policies.py`).
- **Postgres 18 is installed** (`initdb`, `pg_ctl`, `psql` on PATH). `test_policies.PoliciesRunOnPostgres` makes its own scratch cluster. For a manual one, in Git Bash:
  ```bash
  PGSCRATCH="$(cygpath -u "$LOCALAPPDATA")/Temp/wds-pg"; initdb -D "$PGSCRATCH" -U postgres -A trust -E UTF8 --locale=C && pg_ctl -D "$PGSCRATCH" -o "-p 54329" -l "$PGSCRATCH.log" -w start
  ```
  Stop it with `pg_ctl -D "$PGSCRATCH" stop` when done. Roles are per cluster: create `anon`, `authenticated` and `service_role` once.
- **pg_dump on Windows writes CRLF.** Convert a dump to LF before committing it. `.gitattributes` stores every text file with LF.
- **Fail-before, by hand,** until P1 builds `tools/fail_before.py`. Run this from Git Bash. `tar -C` needs a POSIX path and `WDS_PLUGIN_ROOT` a Windows one:
  ```bash
  S="$(cygpath -u "$LOCALAPPDATA")/Temp/wds-before"; rm -rf "$S"; mkdir -p "$S" && git -C /c/DEV/Pro-Web-Designer-Suite-Plug-in archive <rev> plugins/web-design-suite | tar --strip-components=1 -x -C "$S"
  cd /c/DEV/Pro-Web-Designer-Suite-Plug-in/plugins/web-design-suite/tests && WDS_PLUGIN_ROOT="$(cygpath -w "$S/web-design-suite")" python -B -m unittest <test ids>
  ```
  For P0, `<rev>` is the `main` commit before your fix, because the code P0 fixes did not exist in v3.2.1. For everything else it is the previous release tag, `v3.2.1`.
- **The CLAUDE.md commands** are written for the Bash tool. `claude plugin validate`, `update` and `details` need the desktop app's bundled CLI, `%APPDATA%\Claude\claude-code\<version>\claude.exe`; the one on PATH is older.

## 3. P0: what the reviews of #12 to #15 found (N16 to N25)

Branch `fix/p0-review-findings` from `main`. Each item is described in `dev plans/web-design-suite-completion-plan.md` (search for `**N16.**`), and the reviewers' own words are on the PRs:

```bash
gh api repos/Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in/pulls/<n>/comments --jq '.[].body'
```

Write the tests first. Then:

| Item | Where | Fix | Test |
|---|---|---|---|
| N16 | `content-model-to-ui/scripts/introspect_schema.py`, `RE_SIMPLE_IDENT` | Take `$` out of the character class, so a name with `$` keeps its quotes; `_parse_column_def` reads quoted names | `test_schema_sources.MigrationsThatDumpsRewrite`: `"amount$usd" integer` survives as a column |
| N17 | `_apply_alter_action`, the `DROP COLUMN` branch | Also drop the column from `table.primary_key`, drop every unique index that contains it (Postgres does), and clear other tables' `foreign_key` that points at it | Same class |
| N18 | `_apply_alter_action`, the `RENAME` branch | Also retarget other tables' `foreign_key["column"]` that names `(table, old)`, and rewrite `old` to `new`, as a whole word, in the column's own CHECKs and the table's | Same class: a renamed referenced column, and a renamed checked column |
| N19 | `_apply_alter_action` | An `add constraint <name> …` that `RE_ADD_CONSTRAINT` does not match must never reach `RE_ADD_COLUMN`. Read Postgres 18's `not null <column>` (the column becomes not-null); ignore anything else | Same class: `alter table t add constraint t_name_nn not null name` |
| N20 | `content-model-to-ui/scripts/scaffold_ui.py`: `emit_policies`, `emit_policy_test`, `owner_check` | Use the model's schema (check the key in `model["source"]`, said to be `pg_schema`, with `public` as the default) wherever `public.` is written, and in the smoke test's `pg_policies` query | `test_policies`: a model from `create schema app; create table app.notes …` introspected with `--schema app`. Also run it in `PoliciesRunOnPostgres` |
| N21 | `scaffold_ui.sql_ident` | Use the full reserved-word list. Copy `introspect_schema.KEEP_QUOTED` (the scripts stand alone), and add a test that the two copies match, as `test_rules_spec.test_file_classes` does for N11 | `test_policies`: a table named `select` with a column named `where` scaffolds valid SQL; on Postgres, its proposal applies |
| N22 | `emit_policies` | Keep every policy name at 63 bytes or under, and the four names distinct: shorten the table part, with a short hash when shortened | `test_policies`: a 60-character table name gives four distinct names of 63 bytes or under; on Postgres, they apply |
| N23 | `emit_policy_test`, the none-kind check | Count only policies whose roles reach the browser: `and roles && array['public', 'anon', 'authenticated']::name[]` | `test_policies.PoliciesRunOnPostgres`: a `for insert to service_role with check (true)` policy on a read-only table passes the smoke test; one `to authenticated` still fails it |
| N24 | `web-design-studio/assets/starter/styles/index.css`, the comment in the snippet region | Name `utilities.css` and `overrides.css`, imported last, if the project has them. Keep the file audit- and stylelint-clean, then run `python -B tools/sync_snippets.py` to refresh the five quotes | `test_doc_snippets.QuotedStarterCode`, and the stylelint real-tool test, already cover the file |
| N25 | `web-design-studio/scripts/audit_design.py` and `assets/configs/stylelint.config.mjs` | An `@import … layer(x)` before the `@layer` statement is an error: the import fixes `x` first. Spec first: add a refused example to `design-rules.json`, `layers.refused`: `@import url("vendor/datepicker.css") layer(vendor);` followed by the canonical statement. In the audit, extend the `layer-statement-position` check to the first layered import. In stylelint, report under `design/layer-order` | `test_rules_spec.TheAuditFollowsTheSpec.test_layers` (add `("L5", "layer-statement-position")` to its `layer_rules`), and `test_real_tools.StylelintConfig`, which runs the spec's refused examples |

Then:
- the CHANGELOG, under 3.3.0 "Fixed", one bullet for the parser, one for the scaffold, one for the layer checks, and a "Tests" line with the fail-before counts against the pre-fix `main`;
- mark N16 to N25 `*Done for 3.3.0.*` in the completion plan, and update the execution plan's §9;
- run `check_execution_plan.py`, which must say 154 open items once they are done, and the full suite on 3.14 and 3.9;
- commit, push and open the PR.

## 4. P1: CI, the release build, and the lean tooling (XC-C6, XC-B3, N5)

Branch `feat/p1-ci`, stacked on P0's branch if P0 is not merged yet. Read XC-C6 and XC-B3 in `dev plans/web-design-suite-review/crosscut.md` (lines 78 to 80 and 120 to 123), and N5 in the completion plan. P1 is L-sized; it is the multiplier for every later PR, so do it well. In order:

### 4.1 N5: executable bits (do it first: small, and it gives the tooling a real fail-before)

- 17 scripts start with `#!` but are stored as `100644`; 9 are `100755`. List them:
  ```bash
  git ls-files -s plugins/web-design-suite | while read m o s p; do case "$p" in *.py|*.mjs|*.sh|*.js) head -c2 "$p" | grep -q '#!' && echo "$m $p";; esac; done
  ```
- Mark them with `git update-index --chmod=+x <path>`. Windows has `core.fileMode` off, so the index is the only place that holds the mode.
- Add a test, in a new `tests/test_file_modes.py`: every tracked file in the plugin that starts with `#!` is `100755` in `git ls-files -s`, and nothing else is. Skip it outside a git checkout, such as an unpacked zip. It must fail on `v3.2.1`.

### 4.2 `tools/fail_before.py`

Standard library only, runs on Python 3.9, and lives in `plugins/web-design-suite/tools/`.

- **Arguments:** `fail_before.py <test ids…> [--rev REV] [--python EXE]`.
  - The default `--rev` is the latest release tag: `git describe --tags --abbrev=0 --match "v*"`.
  - Allow `--rev main` and any other commit, as P0 needs.
- **Unpacking:** read `git archive --format=tar <rev> plugins/web-design-suite` through Python's `tarfile` into a temporary folder outside the plugin. That avoids the `tar`/`cygpath` trap in §2.
- **Runs:** `python -B -m unittest -v <ids>` twice, once with `WDS_PLUGIN_ROOT` pointing at the unpacked plugin and once without, both from `plugins/web-design-suite/tests`, with `PYTHONDONTWRITEBYTECODE=1`.
- **Output:**
  - Parse the verbose output per test (`ok`, `FAIL`, `ERROR`, `skipped`), counting failing subtests.
  - Print one table: test, previous, now, verdict. The verdict is "fixed" (fails before, passes now), "control" (passes both), "still failing" or "regression".
- **Exit:** 1 if any test fails now.
- **Tests:** in a new `tests/test_tools.py`, with a tiny fake repository of two commits, and nothing written into the plugin.

### 4.3 `tools/check.py`

One command for the checks every PR runs locally:
- `check_pointers.py`;
- `sync_snippets.py --check`;
- `sync_rules.py --check`, skipped while it does not exist (P2 builds it);
- `dev plans/check_execution_plan.py`, when run inside the repository;
- the audit on the plugin's own skills (`audit_design.py skills --strict`);
- `test_skill_budget`;
- the affected tests.

To find the affected tests:
- take the files changed against `git merge-base origin/main HEAD`;
- map each to the test modules whose source names the changed script's stem or skill folder;
- fall back to the whole suite when a shared file changed: `wds_support.py`, `design-rules.json`, a config in `assets/configs/`, or `tools/`.

It prints one summary. Test it in `tests/test_tools.py`.

### 4.4 CI: `.github/workflows/ci.yml`

- **Triggers:** `push` and `pull_request`, with `concurrency` cancelling superseded runs, `fail-fast: false`, and a timeout per job.
- **Matrix:** `ubuntu-latest`, `windows-latest` and `macos-latest`, on Python `3.9` and `3.14`.
  - Prefer `astral-sh/setup-uv` with `uv run --no-project --python <v>`, the same command as locally. It also sidesteps `actions/setup-python` having no Python 3.9 for arm64 macOS. Verify either way.
- **Node:** 22 (ESLint 10 needs 20.19+, 22.13+ or 24+), then `npm ci` in `tooling/main` and `tooling/tailwind-v3`, with npm caching.
- **Linux only:**
  - Install the Playwright headless shell, so the browser tests run: `npx playwright install --only-shell --with-deps chromium`, in `tooling/main`.
  - Put the preinstalled PostgreSQL's `bin` on `PATH`, so `test_policies.PoliciesRunOnPostgres` runs. Check the version folder under `/usr/lib/postgresql/`.
  - Both downloads happen on GitHub's runners, not the user's machine; say so in the PR.
- **Steps**, from `plugins/web-design-suite` with `PYTHONDONTWRITEBYTECODE=1`:
  - the suite;
  - `tools/check_pointers.py`;
  - `tools/sync_snippets.py --check`;
  - the audit on `skills --strict`;
  - from the repository root, `dev plans/check_execution_plan.py`.
- **`claude plugin validate --strict`:**
  - Install the CLI (`npm i -g @anthropic-ai/claude-code`) and find out whether `validate` runs without signing in.
  - If it does not, leave it out of CI, say so in the PR, and keep it in the local release procedure.
  - Never put a key in the repository; a secret would have to come from the user.
- **Line endings:** `.gitattributes` forces LF on checkout, whatever `core.autocrlf` says (`* text=auto eol=lf`). Confirm the hook test passes on the Windows job.
- **Expect red on the first run.** Linux has never run the Node tests, and macOS has never run at all. Each failure is either a test that assumes Windows, which you fix in the test, or a real platform bug, which you fix in the plugin with a regression test like any other. You may push those fixes without asking.

### 4.5 The release build and `.github/workflows/release.yml`

- **`tooling/release/build.py`** replaces `build_zip.py` and keeps what it does: what git holds at a revision, git's file modes, dated at the commit, byte-identical on a rebuild, and refusing links, submodules and `export-ignore`d files.
  - It adds the 13 `.skill` files.
  - Re-read the `.skill` format at its source on the day: Claude's docs on skills packaging.
  - Port `tests/test_release_zip.py`, and add a test that a rebuild is byte-identical.
- **`claude plugin tag`:** read what it does in the current Claude Code docs, and use it if it fits.
- **`release.yml`**, on a pushed tag `v*`:
  - builds the zip and the `.skill` files, with SHA-256 sums;
  - creates the GitHub release with them, using `gh release create` and the job's `GITHUB_TOKEN`.
  - CI is the only thing that creates a release.
- **Docs to update:**
  - the release procedure in `dev plans/web-design-suite-completion-plan.md` (steps 4 and 5);
  - `CLAUDE.md`'s Commands;
  - `tooling/README.md`.

### 4.6 Close P1

- **Inventory:** XC-C6 and XC-B3 are "fixed in 3.3.0", each with its test or workflow. N5 is `*Done for 3.3.0.*` in the completion plan.
- **The binding rule:** add to the completion plan's "How the work is done" that D1 is in force once CI is green on all six jobs.
- **The CHANGELOG:** "Changed" for CI and the build; "Tests" for N5, `fail_before.py`, `check.py` and the build.
- **The execution plan:** update §9, and run its checker.
- **Acceptance:**
  - CI is green on all six jobs;
  - `tools/fail_before.py tests.test_file_modes` shows N5 "fixed" against `v3.2.1`;
  - a rebuild of the zip is byte-identical.

## 5. If budget remains: P2

P2 makes `design-rules.json` generate each tool's rule sections: `tools/sync_rules.py --check`, plus conformance fixtures from the spec run through the real audit, ESLint and stylelint (N2, SB-C2). Read N2 in the completion plan's W2 section, and SB-C2 in `web-design-suite-review/studio-build.md`. Start it only with about 150 thousand tokens left; otherwise go to §6.

## 6. End of session (never skip)

1. Rewrite `docs/HANDOFF.md`: one page, with the state, next steps, blockers and warnings.
2. Update `CLAUDE.md`'s Current State, the execution plan's §9, and the inventory.
3. **Rewrite this file** for the session after yours: the next PRs in the same detail as P0 and P1 here.
4. Run `python -B "dev plans/check_execution_plan.py"`.
5. Commit the docs, then tell the user what merged, what is open, the token use, and what they need to do.
