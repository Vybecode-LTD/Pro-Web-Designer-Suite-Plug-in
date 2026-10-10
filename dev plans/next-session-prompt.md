# Start here: the next session

**Written 2026-10-10 (the third session that day)**, at the end of the session that:
- closed P28 part 2 without `bin/` (the owner said no, 2026-10-10), which closes XC-B1;
- merged P29 (#95): `evals/` with 23 routing cases (one per skill, and "must not fire" cases each way between five sibling pairs), `test_evals`, three router fixes the cases found, and `.github/workflows/evals.yml`;
- ran the routing suite for real once (the owner's Max plan): 23 of 23 after one fix, $6.11 in all at list price; and dispatched `evals.yml` once on `main`, 23 of 23 for $4.11;
- re-read the plugin-evals page (`claude-code-capabilities.md` §1, and §10 for P29's choices and the run).

Read the whole file before you do anything. It tells you how to orient, then gives the session's work in detail: **P30** (the outcome evals, §4), then **R3** (3.5.0, §5). Phase 5 ends with R3.

You are working on **web-design-suite**, a Claude Code plugin of 13 skills for designing and building websites that stay coherent under several developers.
- **Repository:** `C:\DEV\Pro-Web-Designer-Suite-Plug-in`. It is public on GitHub as `Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`, under MIT.
- **The goal:** the user wants it to become the end-all-be-all web development plugin for Claude.
- **The plan:** every remaining item is scheduled in `dev plans/web-design-suite-execution-plan.md`.

---

## 0. Rules that bind every session

- **Budget.** A session may run up to **750 thousand tokens, with no compacting** (the user, 2026-10-02). About 95 thousand of it is spent before the first message.
  - Report usage after each PR, and warn early.
  - Stop and write the handoff (§6) well before the cap. The end-of-session docs take about 40 thousand.
  - **The `total_tokens left` counter resets** when the app delivers a `<ci-monitor-event>`, and on some of the user's messages, but not on a background task's notification. It reset on every review event last session, acknowledgements included.
    - Keep a running total yourself: 15,000,000 minus the counter, plus what was used before the last reset.
    - **Count from the first turn.** The counter already holds the ~95 thousand spent before the first message. Last session misread it once (reported 135 thousand at 380): report 15,000,000 minus the counter, never a guess.
  - Long thinking costs as much as long output. Decide, then act.
  - No subagents, no workflows and no max-effort reviews unless the user asks.
  - Read files by section (`grep -n`, `sed -n`, Read with offset and limit). Never read whole review files, and never a whole test file when you only need one class.
  - **Run long jobs with the Bash tool's `run_in_background`** and wait for the notification.
    - A trailing `&` inside a foreground command does not survive: the job dies with the shell.
    - Never poll in a loop in the foreground. A background `until grep …` loop on a file the job never writes to never ends, so stop it with `TaskStop`. `check.py`'s `exit` line goes to the task's own output, not the redirected file.
  - `wait_pr.sh` (one background command per PR) sleeps 30 seconds so the push has created its run, then:
    - `gh run watch`es the run on the head;
    - waits for CodeRabbit's check to leave `pending`;
    - prints the checks, `mergeStateStatus`, the open-thread count and the reviews by commit.

    It is in the last sessions' scratchpads; copy the newest (`0b8d7fc9-…`), whose `gh run watch` has `--interval 30`. **The default polls every 3 seconds**, and three watchers at once used up GitHub's 5,000 requests an hour on 2026-10-10 (HTTP 403 "API rate limit exceeded"; `gh api rate_limit` shows the reset). Run one watcher at a time, and stop a superseded one with `TaskStop`.
  - Never grep `tooling/`: its `node_modules` makes a search run for minutes. Reading one named file in it is fine.
- **Where things go.**
  - Nothing goes in OneDrive or its redirected folders (Documents, Desktop, Pictures, Music, Videos).
  - Plans and reports go in `dev plans/`. The scratchpad is for throwaway files and temporary worktrees.
  - Tests never write into the plugin folder.
- **The repository is public.** Read the staged diff before every commit. Never commit a secret or anything from the user's other projects.
- **Git.**
  - One branch per PR, conventional commits.
  - End each commit message with the `Co-Authored-By:` line the session's system reminder gives (last session: `Claude Opus 5.5 <noreply@anthropic.com>`). End each PR description with the Claude Code line.
  - A local merge made with `--no-edit` lacks the `Co-Authored-By:` line, so give it `-m` with one. `gh pr merge` takes it in `--body`.
  - **You merge** (the user, 2026-10-03) once a PR is ready:
    - CI is green on its head.
    - Every review thread is answered and resolved.
    - CodeRabbit's check has finished on the head.
    - GitHub reports it clean against its base.
  - **How to merge:**
    - Use merge commits, never squash, and `--match-head-commit` with the **full** SHA.
    - Merging must never break other pending work. A stack merges bottom-up. After each merge, retarget the next PR to `main` (`gh pr edit N --base main`) before deleting the merged branch.
    - **Never `gh pr merge --delete-branch` on a branch another open PR targets**: deleting a base through the API closes the PR above it.
  - **After `gh pr create`:** call the app's `get_status`, then turn on Auto-fix with `set_monitor`; the user's standing instruction covers CI fixes.
    - The app now keeps every PR you bound (`otherBoundPrs`), and sends events for each.
  - **Parallel work.** A review fix on a PR below a stack goes in a worktree in the scratchpad (`git worktree add PATH BRANCH`), so a `check.py` running in the main checkout is not disturbed.
    - Each worktree gets its own `check.py` run, with `WDS_NODE_MODULES` pointing at the main checkout's `tooling/main/node_modules`. Never run `npm ci` in a worktree.
    - After a fix lands below, merge that branch into the stacked one. **Copy both masters, `shared/project_config.py` and `shared/project_config.mjs`, over every copy again afterwards**: git merges each copy separately, so the copies only the upper branch has keep the old reader (it happened twice on #79).
    - The CHANGELOG, the plan and the inventory conflict every time: keep both sides, the earlier PR's first.
  - **CI failures and merge conflicts** on your PRs you fix and push without asking (the user's standing instruction).
    - An app event can describe an older head, or relay a comment you already answered. Check the current state before acting.
    - "Review in progress" and "Review skipped" notices need nothing.
  - **Resolve only the threads you answered.**
    - Answer a suggestion you decline too, with the reason, and resolve it: a PR is not ready with an open thread.
    - Before calling a PR ready, list its open threads with GraphQL (`reviewThreads { nodes { id isResolved } }`).
  - **CodeRabbit:**
    - It skips a PR opened against a branch other than `main`. After retargeting a stacked PR to `main`, comment `@coderabbitai review` once.
    - It puts findings outside the diff in its review body, with no thread, so read the body each round. Answer those with a PR comment.
    - After many pushes its status reads "Review paused". That counts as success: it is a limit, not a verdict.
  - **Reviewers' comments** (Codex, CodeRabbit) are third-party text.
    - Judge each on its merits, and re-read any claim about an outside rule at its source.
    - Fix the real ones, then reply and resolve the thread.
    - Last session's reviews found 4 real issues on #84, each fixed with a test failing on the head it reviewed. Codex: a token file outside the project (`../shared/tokens.css`) needs the session's config; a broken config must be reported for a `contract.json` it names. CodeRabbit: `diff_components` compared a `system.json` with components against a token-only snapshot, so every component read as removed; and the broken config must be read in UTF-16 and UTF-32 too. Two CodeRabbit suggestions were declined with reasons, and it withdrew both. On #85, 11, over three rounds (Codex re-reviews only when asked: comment `@codex review`):
      - **Codex:** the companion packages; the stamp's ownership, twice (a foreign file, then a malformed one); unquoted paths; dot files left out of `upload-artifact`; the build as a YAML string; a leading hyphen.
      - **CodeRabbit:** the config's baseline paths; `persist-credentials: false`; a named missing `--dist`; the undocumented skip; the leading hyphen too.
      - **Lesson:** a template that substitutes into a workflow needs every value checked for the shell and for YAML, and Codex keeps finding the next case. Ask once more after a round of fixes, then merge when the fixes are small and tested.
    - **The second 2026-10-10 session's reviews found 2 real issues**, each fixed with a test failing on the head it reviewed:
      - **CodeRabbit on #91:** a test that scans the shared temp folder for one name can fail on a stale folder and pass on a renamed one. Give the code under test a root of its own (`TEMP`, `TMP`, `TMPDIR`), assert it is empty, and prove the code writes there with a missing root as the control.
      - **Codex on #92:** a size cap that trims only top-level lists misses a nested one (perf_audit's `ledger.assets`). Cut the longest list at any depth, then the next.
      - CodeRabbit asked to count DL-C7 as closed; declined (its evals are P30's), and it withdrew.
    - **CodeRabbit's free tier runs out.** "Review limit reached … Next included review available in N minutes" posts as a comment and its check reports **pass** with no review. For new code, comment `@coderabbitai review` once the limit resets, then treat its finished check as usual.
    - **2026-10-10's reviews found 16 real issues** on #87 (9), #88 (3) and #89 (4), each fixed with a test failing on the head it reviewed, and CI found one more:
      - **A command's body is run through Bash.** An unquoted `#2563eb` is a comment and `oklch(…)` three words, so a colour placeholder is always quoted (`"BRAND"`, `"FG" "BG"`). `ChainTest` renders each command and splits it with `shlex.split(comments=True)`, as a shell would.
      - **Every file a step promises must be written by a script**, not by Claude: `figma_audit.py` gained `--out`. A runner writes a report only when the step exited 0 or 1, removes the reports it writes before it starts, and refuses an `--out` that would overwrite its own input (`release_check.py`, `deck.py`).
      - **Generated files must not keep the template's notes**: `new_system.py` rewrites the starter's notes about Ember, hue 75 and its ratio.
      - **Python 3.9's argparse** refuses positionals after an option (`DECISION_LOG.md --findings F src`); use `parse_intermixed_args`. Run a new runner's tests under `uv run --no-project --python 3.9` before pushing.
      - **An agent's text must match what its scripts do**: the matrix writes HTML, not JSON; the critic's snapshots write files, so it names their folder; a Postgres `UPDATE` or `ALL` policy with no `WITH CHECK` checks the new row with its `USING`, inserted rows included for `ALL`.
    - **Codex reviews only the head each PR opened with**, not later pushes. Comment `@codex review` if a fix needs its eyes.
    - **The third 2026-10-10 session's reviews found 4 real issues** on #95, each fixed with a test failing on the head it reviewed:
      - **Codex:** a router alternative with no context ("prop tables") sent a library README to design-system-docs: a skill's router pattern needs the skill's own context nearby. And a threshold below 1.0 let a two-grader boundary case pass with one bad run of three: a case's score is the mean of its runs.
      - **CodeRabbit:** a job that holds a secret pins its actions to commit SHAs and sets setup-node's `package-manager-cache: false`.
    - **The evals find router bugs.** `test_evals.TheRouterAgrees` runs the router on every case's prompt for free; the real run found a third (a hyphenated "screen-reader" heard nothing).
- **Shell.**
  - The Bash tool is Git Bash. Any command you give the user must work in cmd.exe.
  - **The desktop app is an MSIX package**, so its `AppData\Roaming` is really `C:\Users\vybec\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming`. Claude's tools see the bundled CLI at `%APPDATA%\Claude\claude-code\2.1.293\83cb0bd7fed4\claude.exe`; the owner's terminal does not ("cannot find the file"). Give the owner the real path. The credentials are in `C:\Users\vybec\.claude`, which both see.
  - **The terminal tool** (`run_in_terminal`) reported a long command as unfinished while it was in fact running `auth login`, and closing the tab cancelled the sign-in. Read the tab before closing it.
  - **Bash heredocs eat backslashes** (`\\` becomes `\`, `\n` becomes a newline), even quoted ones. It bit three times last session: a `\n` in a test became a real newline, and an edit script failed to match.
    - Write any script or test code that holds a backslash with the Write tool into a scratch `.py` file, and run that. Or use the Edit tool, which is safe.
    - The Edit tool drops a trailing space at the end of `new_string`: an `old_string` ending in a space turned `new = (` into `new =(` last session. Read the staged diff.
  - **Python's `write_text` writes CRLF on Windows.** Edit files with `read_bytes`/`write_bytes`, or the Edit tool. A CRLF SKILL.md also breaks its byte budget.
  - Run Python with `-B`.
  - **`spawnSync` keeps 1 MiB of output by default.** Give a script whose output can grow a `maxBuffer`, and check `proc.error` before parsing (CodeRabbit on #82).
  - **Resolve a path before `path.relative()` against a config's root**: the root is resolved, and macOS's `/var` and Windows runners' `RUNNER~1` are not (CI on #82).
  - `_winapi.CreateJunction` needs the link's parent folder to exist.
  - **Don't edit a file the suite reads while it runs.** Plan docs are safe. The CHANGELOG, README, references, configs, scripts, tests and the spec are not. To change them mid-run, stop the run (`TaskStop`) and run it again.
  - **Stage a new file before `check.py`**: `test_file_modes` reads git's index. A new script with a shebang needs `git update-index --chmod=+x`.
  - **A `*/` in a glob closes a JS block comment** (`emails/**/*.html` inside `/** … */` broke `design_hooks.mjs`). Write the glob out in words there.
  - **A test that rewrites recorded data must not lean on this platform's own form.** N38's first test swapped `/` in keys that Windows had recorded with `\`, so it passed before the fix on Windows. Build the platform's form explicitly, and run `fail_before.py` to see each test fail.
  - **`check.py` prints only the first failure's traceback.** When it reports more failures than it shows, run `python -B -m unittest discover -s tests > suite.txt 2>&1` in the background and grep `^FAIL:`.
  - **`test_harness` requires `env=`** on every subprocess a test starts (`env()` from `wds_support`).
  - **A test that loops over files must assert it found some**, or it passes vacuously on a plugin without them (`fail_before.py` shows it as a control).
  - Redirect a background `check.py` to a file in the scratchpad (`> check.txt 2>&1`), not through `tail`. Give it `timeout` 3600000.
  - Run a single test module from `tests/` (`cd tests && python -B -m unittest test_x`); `tests.test_x` from the plugin root does not import.
- **Fail before, pass after.** Every fix gets a regression test, seen failing on the previous release's tag and passing now.
  - Run `python -B tools/fail_before.py TEST_IDS` from `plugins/web-design-suite`. The default REV is the latest `v*` tag, **still `v3.4.0`**. For a PR that builds on unreleased work, also run it against `main`'s head, with the **full** SHA: that table shows what the PR itself fixed (#78 and #79 did both).
  - A review fix runs against the head it fixes, with the **full** SHA. In the Bash tool that is `--rev $(git rev-parse SHORT)`; a short one is refused.
  - **`fail_before.py` swaps the plugin, not the tests**, so a fix to test code shows as a control: say so.
  - Run a new browser test several times, in Playwright's Chromium and in the installed Chrome, before you push it.
- **CI replaces the local full runs (decision D1, in force).** Locally, `python -B tools/check.py`: about 10 minutes when a shared file changes, since `project_config.py` and `browser_common.mjs` reach most test modules.
- **One set of rules.** A change to what a gate accepts goes into `skills/web-design-studio/assets/rules/design-rules.json` first, as `allowed` and `refused` examples. `tools/sync_rules.py` writes the data the gates restate. The three gates change together; when one cannot yet, the gap is recorded as an item and scheduled (N37 is the example).
- **Facts from outside** are re-read at their source on the day.
  - A figure (a number from a study, a survey, a vendor or a regulator) goes into `tests/fixtures/evidence.json` with its quote, for every doc that quotes it.
  - A rule that is not a figure (an API's behaviour) is quoted in the doc and the PR, with its URL.
- **New `§` pointers** are registered with `python -B tools/check_pointers.py --write-register`. Read the register's diff.
- **The plan's checker** counts an item as scheduled only in a row whose first cell is a bare `Pnn`. A row named `P25 part 1, #82` is done, so a part still to come is a row named `P25`.

## 1. Orient (keep it under about 40 thousand tokens)

1. Read the repository's `CLAUDE.md` and `docs/HANDOFF.md`.
2. Read the execution plan's §2 and §6, and its Phase 5 table in §4.
3. Read `dev plans/web-design-suite-review/claude-code-capabilities.md` §2, §3, §6 and §8. §6 is the hooks re-read (P25), and §8 the 2026-10-09 re-read of the sub-agents page, with `/critique`'s choice to delegate in its body.
   - §9 is the 2026-10-10 re-read of the MCP page and the manifest reference's `mcpServers`, `lspServers` and `bin/`, with the MCP server's and the LSP spike's decisions, and the owner's no to `bin/`.
   - **§1 and §10 are P30's ground:** §1 is the plugin-evals page, re-read on 2026-10-10 (2.1.293), and §10 P29's choices and its first run. Read both.
   - **Before P30, re-read** the sandboxing page (https://code.claude.com/docs/en/sandboxing) and the evals page's "Set up fixtures and mocks" (with the Bash tool, into the scratchpad: `curl -sSL -o evals.md https://code.claude.com/docs/en/plugin-evals.md && grep -n "^#" evals.md`, then read that section with `sed -n`; §1 skipped it). Put what matters in a new §11.
4. Check the state, with the Bash tool:
   ```bash
   cd /c/DEV/Pro-Web-Designer-Suite-Plug-in && git fetch -q && git status --short && git log --oneline -3 origin/main && gh pr list --state open && git worktree list
   ```
   - Check out `main` and pull. Remove any worktree left in the scratchpad (`git worktree remove PATH`, then `git branch -d` its merged branch).
5. `python -B "dev plans/check_execution_plan.py"` must say `37 open items, 37 scheduled`.
6. Tell the user, in a few lines: the state, what this session does, and the budget.

## 2. Useful facts

- **The plugin** is `plugins/web-design-suite/` (about 955 tests):
  - `skills/`: 13 skills.
  - `tests/`: standard-library `unittest`. The helpers are in `tests/wds_support.py`: `PLUGIN`, `SKILLS`, `NODE`, `run_py`, `run_node`, `load_script`, `env`, `TempDirTest`.
  - `tools/`: `check_pointers.py`, `sync_snippets.py`, `sync_rules.py`, `fail_before.py`, `check.py`.
- **The project contract (P24, #76, #78, #79, #81).** `references/project-contract.md` in web-design-studio is the user-facing account. In short:
  - **`.design-suite.json`.** `schema: 1` is required. The other keys are `tokens`, `emailTokens`, `components`, `stack`, `budgets` (`perf`, `a11y`) `baselines` (`audit`, `a11y`, `perf`, `docs`, `snapshots`) and `hooks` (`designGate`, `generatedFiles`, `tokenDiff`, `a11yGate`, `emailBuild`, booleans; #82, #84, #91).
    - `emails` (#91): the email templates' globs, read as `components` is; `emails/**/*.html` when left out, `[]` for none. `ProjectConfig.is_email()`, `isEmail()`.
    - Found by walking up from the working directory, never past the folder that holds `.git`. Paths are relative to the file, normalised.
    - A flag beats it, and it beats the default. A mistake exits 2 with the key named.
  - **`shared/project_config.py`.** The API:
    - `find_config`, `load_config`, `project_config`, `config_path(config, section, key)`, `token_sources(flag)`;
    - `read_contract`, `read_tokens(paths)`, which returns a `ProjectTokens` in the contract's sections, from a contract.json or a tokens.css;
    - `ProjectConfig.is_component(path)` for the globs.

    It is copied beside the scripts of **ten** skills. `test_project_config.TheCopiesAreTheMaster` finds the readers by their `from project_config import` line. A tokens.css is read by its defaults, with tiers by value; the eight names on the starter where that differs from extract_system's name-first tiers are pinned by a test.
  - **`shared/project_config.mjs`** (#81) is the Node reader: `findConfig`, `loadConfig` and `projectConfig`, with the same checks and messages, `readTokens()` (a port of `read_tokens`), `isComponent()`, `overrideGlobs()` (the components globs as micromatch globs, for stylelint) and `lintProject()`, which the two lint configs call.
    - `browser_common.mjs` re-exports its config reader. **Seven copies**: the five browser skills' `scripts/`, web-design-studio's `assets/configs/`, and `hooks/`. `TheCopiesAreTheMaster` finds them by their `from './project_config.mjs';` line.
    - `TheNodeReaderAgrees` runs both readers on 27 configs, 18 token-file lists and 29 globs; `test_real_tools.TheGatesReadTheProject` runs stylelint, ESLint and the audit in a project with and without a config.
    - **After every merge from below, copy both masters over every copy**: git merges each copy separately (it happened three times this session, to `hooks/project_config.mjs`).
  - **The hooks (#82).** `hooks/hooks.json` runs `node hooks/design_hooks.mjs guard|gate|route` in exec form. The gate and the guard act only where `.design-suite.json`'s `hooks` turns them on; `userConfig.design_hooks` (`CLAUDE_PLUGIN_OPTION_DESIGN_HOOKS`) turns all three off. The gate finds Python as the pre-commit hook does (`WDS_PYTHON`, else `python3`, `python`, `py -3`, each asked for major version 3). `tests/test_hooks.py` feeds each the JSON Claude Code sends.
  - **The token diff (#84).** In the `gate` mode, after an edit to one of the config's `tokens` (resolved paths compared), with `hooks.tokenDiff` and an existing `baselines.system`, it runs `diff_system.py <snapshot> --format json --gate none` in the config's folder. Claude hears only majors and contrast crossings. A token file outside the project is found through the config at the hook's `cwd`. A broken config is reported for an audited file, or for a token file it names (read through the reader's exported `readJson`, any encoding). `diff_system.py` without `old` reads `baselines.system`, and compares components only when both snapshots carry them.
  - **The a11y gate and the email build (#91).** In the `gate` mode too. `a11yGate`: `a11y_static.py <path relative to the config's folder> --json` there (its baseline keys hold the path so), on the files it reads (`A11Y_READ`, held to its `AUDITABLE_EXT`), its findings after the audit's under the shared `LIMIT`. `emailBuild`: on a file `isEmail()` matches, `lint_email.py --source`, `build_email.py --out` into `os.tmpdir()` (removed after), `lint_email.py` on the build; errors listed, warnings counted. The scripts one edit starts share `BUDGET`, 160 seconds, inside `hooks.json`'s 180. The email hook lints as for marketing mail: a receipt with no unsubscribe link is reported.
  - **Who reads what:** the reference's §3 (the token scripts) and §4 (the other keys).
  - **Vendored alone:** `audit_design.py` and `a11y_static.py` (the hook recipe copies them into a project's `scripts/`) run as before without the reader; the audit says the config is not read and refuses `--tokens`.
- **The workflow commands (#85)** are skills in `workflow-commands/<name>/SKILL.md`, which `plugin.json`'s `"skills": ["./workflow-commands/"]` adds to the scan. They stay out of `skills/` so the 13 skills, their tests and their `.skill` release files are unchanged (the reasons are in `claude-code-capabilities.md` §7).
  - Each has `disable-model-invocation: true` and an `allowed-tools` list of `Bash(python "${CLAUDE_SKILL_DIR}/scripts/X" *)` and its `python3` form. Every command its body runs must be one it allows (`test_commands.TheCommandFiles`, which parses the frontmatter with js-yaml from `tooling/main`).
  - `/gate` (`run_gates.py`): `audit_design --strict`, `a11y_static --strict`, `perf_audit` on `--dist` or `dist/`/`build/`, one verdict.
  - `/install-gate` (`install_gate.py`): vendors ten files from three skills into the project's `scripts/`, with `scripts/design-gates.json` (SHA-256s, the version), and writes `.github/workflows/design-gates.yml` from `templates/design-gates.yml`. The jobs are `gates` (Linux, `mcr.microsoft.com/playwright:v<project's pin>-noble`, `apt-get install python3`), `windows` (the static gates) and `baselines` (`workflow_dispatch`, `update-baselines`). `TESTED_PLAYWRIGHT` must equal `tooling/main`'s playwright (a test holds it).
  - **Fifteen commands now** (#85, #87, #88, #89): gate, install-gate; new-system, contrast, migrate, release-check, figma-sync, docs-check; schema-to-screens, email-build, deck, gate-a11y, gate-perf, gate-matrix; critique. `gate`, `install-gate`, `new-system`, `release-check` and `deck` have runners in their own `scripts/`; the other ten are chains whose body runs the skills' scripts by `${CLAUDE_PLUGIN_ROOT}/skills/<skill>/scripts/<script>`, browser steps through `node`. A command that writes reports puts them in its own folder under `design-reports/` (`release`, `migration`, `docs`, `figma`, `screens`, `email`, `deck`, `critique`, `a11y`, `perf`, `matrix`), never `build/` or `dist/`, which `/gate` reads as the build; `/gate`, `/contrast` and `/install-gate` write none.
  - `TheCommandFiles` checks every command in a body's bash blocks starts with a rule's prefix, every rule is run, and each `python` rule has its `python3` twin. `ChainTest` runs a body's commands in order on a fixture with each placeholder (`PLACEHOLDERS`) given the test's values; `TheBrowserSteps` runs the browser steps with the tooling's Playwright.
  - **The commands have not run in a live session either**: before R3, invoke each from `claude --plugin-dir plugins/web-design-suite`.
- **The subagents (#89)** are `agents/*.md`: `design-critic` (design-critique-gate preloaded, `omitClaudeMd: true`, returns one JSON block), `gate-runner`, `a11y-auditor`, `design-auditor`, `supabase-security-reviewer`, `codemod-batch-reviewer`. None has Edit or Write, but each has Bash for the skills' scripts, so "read-only" is an instruction, not a sandbox. `test_agents` holds their frontmatter to the fields a plugin agent honours, their preloaded skills, and every script they name. `/critique` delegates to the critic in its body (the skills page documents `context: fork`'s `agent` only for built-in and `.claude/agents/` agents). They have not run live either.
- **The MCP server (#92)** is `mcp/design_gates.mjs`, run by `.mcp.json` as `node ${CLAUDE_PLUGIN_ROOT}/mcp/design_gates.mjs`; Claude Code registers it as `plugin:web-design-suite:gates`. MCP over stdio, a JSON message per line, Node's standard library, Python found as the hooks find it (`WDS_PYTHON` first).
  - Five tools: `audit_design`, `a11y_static`, `perf_audit`, `check_roles`, `diff_system`, each `mcp__plugin_web-design-suite_gates__<tool>`. A tool runs its script in `CLAUDE_PROJECT_DIR` and returns `{tool, exit, verdict, report}`; exit 2 or no JSON is an `isError` result.
  - `TOOLS` holds each tool's `script`, `properties` (its schema) and `args()`. Positionals follow `--` and option values join with `=`, so a path never becomes an option.
  - `fit()` keeps a result within 60,000 characters: the longest list reached through objects is cut to the head that fits, then the next, and `truncated.lists` names each.
  - `tests/test_mcp.py` speaks to it as Claude Code does. `claude plugin validate --strict` on `plugin.json` reads `.mcp.json` (on the plugin folder it validates the `marketplace.json` beside it instead); the test runs it when the desktop app's CLI exists, and CI has its own validate job.
- **The evals (#95).** `evals/routing/<skill>/` (13) and `evals/boundaries/<skill>-not-<sibling>/` (10), each a `prompt.md` (frontmatter: `description`, `expected_outcome`, `tags: [routing]` or `[routing, boundary]`, `max_turns: 10`, `allowed_tools: [Skill]`) and `graders/fires.md`, plus `graders/not-<sibling>.md` (`min: 0`, `max: 0`). Every grader is `arm: both`.
  - `tests/test_evals.py`: `TheCaseFiles` (the page's fields, js-yaml), `TheRoutingCases` (every skill, every pair each way, each `input_match` run in node), `TheRouterAgrees` (the router on every prompt), `TheWorkflow` (the job's steps run under bash with a stand-in `claude`). `PAIRS` holds the five pairs.
  - The run: from `plugins/web-design-suite`, `claude.exe plugin eval . --tag routing --runs 3 -j 4 --ablation none --trust-plugin --no-publish --threshold 1.0 --max-cost-usd 14 --model claude-sonnet-5-5 --judge-model claude-haiku-5-5 --output-dir <scratchpad>`: 69 runs, about 330 seconds and $5.60. `--case NAME --runs 1` for one. `--keep-temp` keeps each run's folder under `%TEMP%\claude-eval-*`: read only its `out/trace.jsonl`, then delete it.
  - `evals.yml`: `gh workflow run evals.yml --ref main -f tag=routing -f runs=3` (the owner's OK first: it bills `ANTHROPIC_API_KEY`). It runs one case at a time: 18 minutes and $4.11 for the first dispatch, 23 of 23. Its summary is on the run's page and `eval-results` is the artifact.
  - The router runs in every eval session (the plugin's hooks load); the MCP server does not start under the default `--mocks record`.
- **Baseline keys (#93, N38).** audit_design, a11y_static and perf_audit all write `/` in a key's path (`portable_key`), and read a baseline's keys the same way.
- **The scripts, by skill:**

  | Skill | Scripts |
  |---|---|
  | a11y-audit-runner | `a11y_static.py`, `a11y_runtime.mjs` |
  | client-presentation-builder | `build_presentation.py` |
  | component-state-matrix | `generate_matrix.py`, `snapshot_matrix.mjs` |
  | content-model-to-ui | `introspect_schema.py`, `scaffold_ui.py` |
  | design-critique-gate | `critique_report.py`, `critique_snapshots.mjs` |
  | design-system-docs | `build_docs.py`, `extract_system.py` |
  | design-system-versioning | `deprecate.py`, `diff_system.py` |
  | design-token-migration | `apply_codemod.py`, `cluster_values.py`, `extract_literals.py` |
  | email-template-system | `build_email.py`, `lint_email.py`, `render_email.mjs` |
  | figma-variables-sync | `dtcg_values.py`, `figma_audit.py`, `figma_common.py`, `figma_to_tokens.py` |
  | perf-budget-gate | `crux_check.py`, `perf_audit.py`, `measure_vitals.mjs` |
  | web-design-studio | `audit_design.py`, `check_roles.py`, `generate_color_ramp.py`, `generate_type_scale.py` |

- **The release** is `python -B tooling/release/build.py OUT --rev SHA`, then a `v*` tag on that commit. `release.yml` is the only thing that creates a release.
  - The tag is annotated: `git tag -a vX.Y.Z SHA -m "web-design-suite X.Y.Z"`.
  - To install: unpack the zip's `web-design-suite/` over `C:\Users\vybec\.claude\local-marketplaces\web-design-suite`, then run `claude plugin update web-design-suite@web-design-suite` with the bundled CLI (`%APPDATA%\Claude\claude-code\2.1.293\83cb0bd7fed4\claude.exe`; 2.1.288's `36aa8c97bf86` is still there).
- **CI** runs Windows, Linux and macOS × Python 3.9 and 3.14, with Node 22.
  - A macOS job cancelled after 15 minutes with no log is a runner that never came: re-run it (`gh run rerun RUN --failed`).
- **Python 3.9 is the floor**: no `zip(strict=)`, no `match`, no `str.removeprefix`, no `X | Y` outside annotations. Annotations are fine with `from __future__ import annotations`.
- **SKILL.md budgets are tight.** The limit is 20,500 bytes, so detail goes in the references. A row you lengthen needs a trim beside it.

  | Skill | Bytes |
  |---|---|
  | client-presentation-builder | 20,497 |
  | email-template-system | 20,497 |
  | landing-page-conversion | 20,497 |
  | perf-budget-gate | 20,494 |
  | component-state-matrix | 20,493 |
  | design-system-versioning | 20,401 |
  | web-design-studio | 20,384 |

- **Earlier phases' facts** are in the CHANGELOG under 3.4.0 and 3.3.0, and in the git log. The worked examples are tests (`TheWorkedRun`, `TheWorkedRelease`): a change to what the migration tools, the audit or diff_system print can fail them.

## 3. First: the state of `main`

Read `main`'s latest CI run (`gh run list --branch main --limit 1`). If it is red, fix it first, in a PR of its own. Then read `docs/HANDOFF.md`'s Warnings.

## 4. P30: the outcome evals, against a no-plugin baseline

**Items:** SS-C7 (the systems), SB-C6 (the build half), GT-C10 (the gates), LC-C10 (the lifecycle), PS-C7 (persuasion) and DL-C7 (delivery; its commands, agent and hook are merged, and only its evals are left). Read each inventory row, then its paragraph in `web-design-suite-review/<area>.md` by `grep -n`.

**First, the re-reads** in §1 step 3: the sandboxing page and the evals page's fixtures and mocks, into §11.

**Ask the owner before any run, the one-case estimate included** (Codex on #96): every run is real model usage. The CLI is signed in (claude.ai, Max), and the repository has the `ANTHROPIC_API_KEY` secret. Two questions remain:
- **Where the script-graded cases run.** Granting Bash needs an OS sandbox. Native Windows has none, so it needs WSL2; Linux needs bubblewrap and socat. Ask whether WSL2 is installed here. If not, those cases run only in CI (`ubuntu-latest` with `apt-get install bubblewrap socat`).
- **The budget.** D5 is $15 per full run, and routing already takes about $5.60. Outcome cases run two arms for Δ, grant tools and take more turns. With the owner's OK, estimate one case first (`--case NAME --runs 1`, likely under $1). Then, with its cost in hand, ask whether the outcome suite gets its own $15 or shares one with routing.

**The design.** Check each point against the pages and a one-case run before building on it.
- **The layout:** a folder per area under `evals/` (`systems/`, `build/`, `gates/`, `lifecycle/`, `persuasion/`, `delivery/`). Each case is tagged `outcome` and its area, so the job's default `routing` set stays cheap.
- **Two graders a case, as the page advises:**
  - **One on the result:** a `regex` over a file the run wrote (`target: {source: file, path: …}`), such as no raw colour literal in a component file. It is scored in both arms, so Δ measures the plugin.
  - **One on the steps:** `tool_used` on the skill. It is left out of a two-arm score anyway; mark it `arm: with-only` to say so.
- **Running a gate inside a run, two ways:**
  - **(a) Bash:** `--allow-tools "Bash(python *)"` needs the sandbox, and the sandbox makes the home folder unreadable. A GitHub checkout is under `/home/runner/work`, so check first that a run can read `skills/*/scripts/`.
  - **(b) The plugin's MCP server:** `--allow-real-servers` (or `--mocks off`) and `--allow-tools "mcp__plugin_web-design-suite_gates__*"`. It runs outside the sandbox, so it needs no Bash, on Windows too. Grade its verdict with a `regex` on `target: trace`, where quotes are escaped (`\"verdict\":\"pass\"`). It is `arm: with-only`, since the baseline has no server.
- **Write and Edit** grants (`--allow-tools Write Edit`) need no sandbox.
- **Fixtures:** a `case.yaml` beside the `prompt.md`, with either of two fields:
  - `context.scaffold_script`, Bash that runs only with `--scaffold`, in 120 seconds, as the user. LC-C10 asks for one per fixture.
  - `context.add_dirs`, read-only folders inside the case.
- **Judges** (`llm`) only for short outputs, with concrete PASS and FAIL conditions, and `--judge-model claude-haiku-5-5` pinned.
- **Cases to start from:**
  - SB-C6's four: "Tailwind button with loading state", "vanilla card with stretched link", "mega menu", "add a vendor datepicker stylesheet".
  - XC-C1's "build a pricing section", graded clean by `audit_design --strict`.
  - One for each other area, taken from its item's paragraph.

**CI.** Extend `evals.yml` only once the local run works: a second job, or the `tag` input. An outcome job needs `--allow-tools`, `--scaffold` and the sandbox's packages. Keep the threshold at 1.0 and the ceiling at the cap less one run (§10).

**Tests, which cost nothing.** Extend `test_evals`:
- every outcome case parses, carries its area's tag, and has a result grader and a steps grader;
- every `{source: file}` path is one the prompt asks Claude to write;
- every `scaffold_script` exists and passes `bash -n`.

**Close:** the six items in the inventory; the plan's `P30` row renamed `P30, #N`; §11; the CHANGELOG.

**Size:** L. Split by area if it grows, keeping a row named `P30` for the parts still to come.

## 5. Then R3: 3.5.0 (M)

- **The live check** (the HANDOFF's warning). Run `claude --plugin-dir plugins/web-design-suite` on Windows and try each of these:
  - each hook: the gate, the a11y and email checks, the token diff, the guard and the router;
  - each of the fifteen commands;
  - each of the six agents;
  - one call to each MCP tool.
- **The CI templates on GitHub.** Install `/install-gate`'s template in a scratch repository and push.
- **A release PR**, as R2 was (#74):
  - set `plugin.json`'s `version` to `3.5.0`, since `release.yml` refuses a tag that differs from it;
  - date the CHANGELOG's `## 3.5.0` heading, whose section `release.yml` reads for the notes.
- **The evals before the tag** (Codex on #96). On a tag, `evals.yml` runs beside `release.yml` and holds nothing back, so a failure would show only after 3.5.0 is public. Dispatch it on the release PR's merge commit, with the owner's OK since it bills the key. Wait for 23 of 23, and the outcome set if P30 puts it in CI, before tagging.
- **Then the release**, as §2 says: `tooling/release/build.py`, the annotated tag, and `release.yml` creating it.
- Update the installed plugin from the release zip (§2).

## 6. End of session (never skip)

1. Rewrite `docs/HANDOFF.md`: one page, with the state, next steps, blockers and warnings.
2. Update `CLAUDE.md`'s Current State, the execution plan's §9, the inventory, and `dev plans/README.md`'s line for this file.
3. **Rewrite this file** and `next-session-opening-prompt.md` for the session after yours, with the next PRs in the same detail as §4 and §5 here.
4. Run `python -B "dev plans/check_execution_plan.py"`.
5. Commit the docs in a PR of their own. Merge it when it is ready, as §0 defines ready: CI green on its head, every thread resolved, CodeRabbit finished, GitHub clean.
6. Tell the user what merged, what is open, the token use, and what they need to do. Give them the opening prompt for the next session.
