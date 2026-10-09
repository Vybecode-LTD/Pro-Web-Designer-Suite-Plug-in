# Start here: the next session

**Written 2026-10-09**, at the end of the session that:
- merged P25 part 2 (#84): the token diff, a hook that runs `diff_system` against the published snapshot (`baselines.system`) after an edit to a token file (LC-C8, closing P25);
- merged P26 part 1 (#85): the first workflow commands, `/gate` and `/install-gate`, in `workflow-commands/`, with the CI template (GT-C12, LC-B4, XC-C8);
- re-read the skills page and the manifest reference (`claude-code-capabilities.md` §7).

Read the whole file before you do anything. It tells you how to orient, then gives the session's work in detail: **P26 part 2** (the other workflow commands, §4) and **P27** (the subagents, §5). Phase 5 ends with R3; its other PRs are in the execution plan's §4.

You are working on **web-design-suite**, a Claude Code plugin of 13 skills for designing and building websites that stay coherent under several developers.
- **Repository:** `C:\DEV\Pro-Web-Designer-Suite-Plug-in`. It is public on GitHub as `Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`, under MIT.
- **The goal:** the user wants it to become the end-all-be-all web development plugin for Claude.
- **The plan:** every remaining item is scheduled in `dev plans/web-design-suite-execution-plan.md`.

---

## 0. Rules that bind every session

- **Budget.** A session may run up to **750 thousand tokens, with no compacting** (the user, 2026-10-02). About 95 thousand of it is spent before the first message.
  - Report usage after each PR, and warn early.
  - Stop and write the handoff (§6) well before the cap. The end-of-session docs take about 40 thousand.
  - **The `total_tokens left` counter resets** when the app delivers a `<ci-monitor-event>`, but not on a background task's notification. It reset about 15 times last session, on every review event, acknowledgements included.
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

    It is in the last two sessions' scratchpads; copy it into yours.
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
    - **Codex reviews only the head each PR opened with**, not later pushes. Comment `@codex review` if a fix needs its eyes.
- **Shell.**
  - The Bash tool is Git Bash. Any command you give the user must work in cmd.exe.
  - **Bash heredocs eat backslashes** (`\\` becomes `\`, `\n` becomes a newline), even quoted ones. It bit again last session: a replacement holding `\n` silently did not match.
    - Write any script or test code that holds a backslash with the Write tool into a scratch `.py` file, and run that. Or use the Edit tool, which is safe.
    - The Edit tool drops a trailing space at the end of `new_string`: an `old_string` ending in a space turned `new = (` into `new =(` last session. Read the staged diff.
  - **Python's `write_text` writes CRLF on Windows.** Edit files with `read_bytes`/`write_bytes`, or the Edit tool. A CRLF SKILL.md also breaks its byte budget.
  - Run Python with `-B`.
  - **`spawnSync` keeps 1 MiB of output by default.** Give a script whose output can grow a `maxBuffer`, and check `proc.error` before parsing (CodeRabbit on #82).
  - **Resolve a path before `path.relative()` against a config's root**: the root is resolved, and macOS's `/var` and Windows runners' `RUNNER~1` are not (CI on #82).
  - `_winapi.CreateJunction` needs the link's parent folder to exist.
  - **Don't edit a file the suite reads while it runs.** Plan docs are safe. The CHANGELOG, README, references, configs, scripts, tests and the spec are not. To change them mid-run, stop the run (`TaskStop`) and run it again.
  - **Stage a new file before `check.py`**: `test_file_modes` reads git's index. A new script with a shebang needs `git update-index --chmod=+x`.
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
3. Read `dev plans/web-design-suite-review/claude-code-capabilities.md` §2, §3 and §7. §7 is the 2026-10-09 re-read of the skills page and the manifest reference, with P26's choice of `workflow-commands/`.
   - Re-read the sub-agents page before P27, and update §2's agents bullet with what changed.
   - Re-read the plugin-evals page before P29, and update §1. Read §1 (evals) only when you reach P29.
4. Check the state, with the Bash tool:
   ```bash
   cd /c/DEV/Pro-Web-Designer-Suite-Plug-in && git fetch -q && git status --short && git log --oneline -3 origin/main && gh pr list --state open && git worktree list
   ```
   - Check out `main` and pull. Remove any worktree left in the scratchpad (`git worktree remove PATH`, then `git branch -d` its merged branch).
5. `python -B "dev plans/check_execution_plan.py"` must say `47 open items, 47 scheduled`.
6. Tell the user, in a few lines: the state, what this session does, and the budget.

## 2. Useful facts

- **The plugin** is `plugins/web-design-suite/`:
  - `skills/`: 13 skills.
  - `tests/`: 863 tests, standard-library `unittest`. The helpers are in `tests/wds_support.py`: `PLUGIN`, `SKILLS`, `NODE`, `run_py`, `run_node`, `load_script`, `env`, `TempDirTest`.
  - `tools/`: `check_pointers.py`, `sync_snippets.py`, `sync_rules.py`, `fail_before.py`, `check.py`.
- **The project contract (P24, #76, #78, #79, #81).** `references/project-contract.md` in web-design-studio is the user-facing account. In short:
  - **`.design-suite.json`.** `schema: 1` is required. The other keys are `tokens`, `emailTokens`, `components`, `stack`, `budgets` (`perf`, `a11y`) `baselines` (`audit`, `a11y`, `perf`, `docs`, `snapshots`) and `hooks` (`designGate`, `generatedFiles`, booleans; #82).
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
  - **Who reads what:** the reference's §3 (the token scripts) and §4 (the other keys).
  - **Vendored alone:** `audit_design.py` and `a11y_static.py` (the hook recipe copies them into a project's `scripts/`) run as before without the reader; the audit says the config is not read and refuses `--tokens`.
- **The workflow commands (#85)** are skills in `workflow-commands/<name>/SKILL.md`, which `plugin.json`'s `"skills": ["./workflow-commands/"]` adds to the scan. They stay out of `skills/` so the 13 skills, their tests and their `.skill` release files are unchanged (the reasons are in `claude-code-capabilities.md` §7).
  - Each has `disable-model-invocation: true` and an `allowed-tools` list of `Bash(python "${CLAUDE_SKILL_DIR}/scripts/X" *)` and its `python3` form. Every command its body runs must be one it allows (`test_commands.TheCommandFiles`, which parses the frontmatter with js-yaml from `tooling/main`).
  - `/gate` (`run_gates.py`): `audit_design --strict`, `a11y_static --strict`, `perf_audit` on `--dist` or `dist/`/`build/`, one verdict.
  - `/install-gate` (`install_gate.py`): vendors ten files from three skills into the project's `scripts/`, with `scripts/design-gates.json` (SHA-256s, the version), and writes `.github/workflows/design-gates.yml` from `templates/design-gates.yml`. The jobs are `gates` (Linux, `mcr.microsoft.com/playwright:v<project's pin>-noble`, `apt-get install python3`), `windows` (the static gates) and `baselines` (`workflow_dispatch`, `update-baselines`). `TESTED_PLAYWRIGHT` must equal `tooling/main`'s playwright (a test holds it).
  - **The commands have not run in a live session either**: before R3, invoke each from `claude --plugin-dir plugins/web-design-suite`.
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

## 4. P26 part 2: the other workflow commands

**Items:**
- XC-C3's rest (`crosscut.md`): `/new-system` (brand colour to ramp, type scale and starter styles). Its `/critique` needs the design-critic subagent, so it lands in P27.
- SS-C6's commands (`studio-systems.md`): `/wds:tokens` (the generators and the role check) and `/wds:contrast`. `/wds:audit` is `/gate`, done.
- LC-C9 (`lifecycle.md`): migrate-census, release-check (extract, diff, gate, changelog, guide), figma-handoff, docs-check. Its `codemod-batch-reviewer` agent is P27's.
- PS-C11 (`persuasion.md`): the audit-to-deck chain (audit, critique, defence, deck), stopping on blockers.
- DL-C7's two commands (`delivery.md`): schema-to-screens (introspect, questions, scaffold, audit, security checklist) and email-build (build, lint, render).
- GT-C9 (c) (`gates.md` C9): `gate-a11y`, `gate-perf` and `gate-matrix`, the runtime gates by hand.

Read each by `grep -n`.

**How, from part 1:**
- One folder per command in `workflow-commands/`, `disable-model-invocation: true`.
- A chain is a SKILL.md that runs the skills' own scripts by `${CLAUDE_PLUGIN_ROOT}/skills/<skill>/scripts/<script>`. Its `allowed-tools` pre-approves each command it runs: the skills page says `${CLAUDE_PLUGIN_ROOT}` is substituted in Bash rules there, as `${CLAUDE_SKILL_DIR}` is. Write a runner script only where a chain needs logic between steps, as `/gate` did for its verdict.
- **Extend `TheCommandFiles`:**
  - its rule regex accepts the `${CLAUDE_PLUGIN_ROOT}/skills/...` form, with the script checked against `PLUGIN`;
  - the manifest test's command list grows.

**Name the commands first.** LC-C9 says `/wds-release-check`, SS-C6 says `/wds:tokens`, and XC-C3 says `/new-system`; under the plugin they are all `/web-design-suite:<name>`. Pick short verbs (`new-system`, `contrast`, `migrate`, `release-check`, `figma-sync`, `docs-check`, `schema-to-screens`, `email-build`, `deck`, `gate-a11y`, `gate-perf`, `gate-matrix`) and say so in the PR.

**Split it.** About twelve commands:
- part 2: the systems and the lifecycle (new-system, contrast, migrate, release-check, figma-sync, docs-check);
- part 3: delivery, persuasion and the runtime gates (schema-to-screens, email-build, deck, gate-a11y, gate-perf, gate-matrix).

**Tests:**
- each command's frontmatter (`TheCommandFiles` covers a new one automatically);
- each chain's commands run in order on a fixture project with a `.design-suite.json`, as `TheGateCommand` does;
- a chain that must stop on a blocker, stopping.

**Close:**
- the inventory rows: XC-C3, SS-C6 and LC-C9 stay open after part 3, since their agents are P27's and P27's row lists them (write "the commands in #N, the agent in P27");
- the plan's `P26` row renamed per part, §9, the CHANGELOG and README's "The commands".

**Size:** M per part.

## 5. P27: the subagents, and the two hooks P25 left

**Re-read the sub-agents page first** (https://code.claude.com/docs/en/sub-agents), and update `claude-code-capabilities.md` §2's agents bullet. Its facts are from 2026-09-23. Plugin agents ignore `hooks`, `mcpServers` and `permissionMode`, and do not support `initialPrompt`.

**Items:**
- PS-C4 (`persuasion.md`): `agents/design-critic.md`, with `tools: Read, Grep, Glob, Bash`, `skills: [design-critique-gate]` and `omitClaudeMd: true`. It critiques in a fresh context and returns a `findings.json` the main thread does not edit. `/critique` (XC-C3) invokes it.
- GT-C9 (a) (`gates.md` C9): `agents/gate-runner.md` (Bash, Read). It runs the runtime scripts and returns only the findings and the JSON path, so 5 to 10 thousand tokens of output stay out of the main context.
- XC-C4 (`crosscut.md`): the a11y-auditor; SS-C6's read-only design-auditor.
- DL-C7: `supabase-security-reviewer`, read-only, after scaffolding.
- LC-C9: `codemod-batch-reviewer`, read-only, checking each batch against `reconciliation.md` and the known traps.
- **The two hooks P25 did not ship** (the plan said "in P25", and P25 closed without them; the docs PR of 2026-10-09 moved them here):
  - GT-C9 (b): an opt-in PostToolUse hook that runs `a11y_static.py` on the edited css/html/jsx/tsx file. It fits the `gate` mode beside the audit, behind a new `hooks.a11yGate`.
  - DL-C7's email-template hook: build and lint on an email-template edit, as `additionalContext`.

**Tests:**
- each agent's frontmatter parses, through js-yaml, with only the fields plugin agents honour;
- each `skills:` entry exists;
- the two hooks, as `test_hooks` does the others.

**Close:** GT-C9, DL-C7 (but for its evals, P30's), PS-C4 and XC-C4, and XC-C3, SS-C6 and LC-C9 with their agents. An agent's behaviour is P29 and P30's evals.

**Size:** M.

## 6. End of session (never skip)

1. Rewrite `docs/HANDOFF.md`: one page, with the state, next steps, blockers and warnings.
2. Update `CLAUDE.md`'s Current State, the execution plan's §9, the inventory, and `dev plans/README.md`'s line for this file.
3. **Rewrite this file** and `next-session-opening-prompt.md` for the session after yours, with the next PRs in the same detail as §4 and §5 here.
4. Run `python -B "dev plans/check_execution_plan.py"`.
5. Commit the docs in a PR of their own. Merge it when it is ready, as §0 defines ready: CI green on its head, every thread resolved, CodeRabbit finished, GitHub clean.
6. Tell the user what merged, what is open, the token use, and what they need to do. Give them the opening prompt for the next session.
