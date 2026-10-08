# Start here: the next session

**Written 2026-10-08**, at the end of the session that:
- merged P24 part 4 (#81): stylelint and the ESLint config read the project's `.design-suite.json`, through a new Node reader, `shared/project_config.mjs` (N37);
- merged P25 part 1 (#82): the plugin's first hooks, an opt-in design gate, an opt-in generated-file guard and a skill router, run by `node` (XC-C2);
- re-read the hooks page and the mods reference, and chose command hooks over a mod (`claude-code-capabilities.md` §6).

Read the whole file before you do anything. It tells you how to orient, then gives the session's work in detail: **P25 part 2** (the token diff, §4) and **P26** (the commands and the CI bootstrap, §5). Phase 5 ends with R3; its other PRs are in the execution plan's §4.

You are working on **web-design-suite**, a Claude Code plugin of 13 skills for designing and building websites that stay coherent under several developers.
- **Repository:** `C:\DEV\Pro-Web-Designer-Suite-Plug-in`. It is public on GitHub as `Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`, under MIT.
- **The goal:** the user wants it to become the end-all-be-all web development plugin for Claude.
- **The plan:** every remaining item is scheduled in `dev plans/web-design-suite-execution-plan.md`.

---

## 0. Rules that bind every session

- **Budget.** A session may run up to **750 thousand tokens, with no compacting** (the user, 2026-10-02). About 95 thousand of it is spent before the first message.
  - Report usage after each PR, and warn early.
  - Stop and write the handoff (§6) well before the cap. The end-of-session docs take about 40 thousand.
  - **The `total_tokens left` counter resets** when the app delivers a `<ci-monitor-event>`, but not on a background task's notification. It reset nine times last session, and once on a message from the user.
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
    - After a fix lands below, merge that branch into the stacked one. **Copy `shared/project_config.py` over every copy again afterwards**: git merges each copy separately, so the copies only the upper branch has keep the old reader (it happened twice on #79).
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
    - Last session's reviews and CI found 7 real issues, each fixed, the six in code with a test failing on the head it reviewed. On #81: CodeRabbit twice (stylelint's globs must name every spelling of the project's folder, and of a token file), Codex once (JSON in every encoding Python's `json` reads). On #82: Codex once (the guard's 800 characters are code points). CI on #82 found one more: a path named from the unresolved file on macOS (`/var`) and Windows (an 8.3 TEMP name). CodeRabbit on #82: `spawnSync`'s 1 MiB `maxBuffer` cut a long report short; and the README called the router opt-in.
    - **Codex reviews only the head each PR opened with**, not later pushes. Comment `@codex review` if a fix needs its eyes.
- **Shell.**
  - The Bash tool is Git Bash. Any command you give the user must work in cmd.exe.
  - **Bash heredocs eat backslashes** (`\\` becomes `\`, `\n` becomes a newline), even quoted ones. It bit twice last session: a test string got a real newline, and a heredoc with a `\u` escape failed to parse at all.
    - Write any script or test code that holds a backslash with the Write tool into a scratch `.py` file, and run that. Or use the Edit tool, which is safe.
    - The Edit tool drops a trailing space at the end of `new_string`.
  - **Python's `write_text` writes CRLF on Windows.** Edit files with `read_bytes`/`write_bytes`, or the Edit tool. A CRLF SKILL.md also breaks its byte budget.
  - Run Python with `-B`.
  - **`spawnSync` keeps 1 MiB of output by default.** Give a script whose output can grow a `maxBuffer`, and check `proc.error` before parsing (CodeRabbit on #82).
  - **Resolve a path before `path.relative()` against a config's root**: the root is resolved, and macOS's `/var` and Windows runners' `RUNNER~1` are not (CI on #82).
  - `_winapi.CreateJunction` needs the link's parent folder to exist.
  - **Don't edit a file the suite reads while it runs.** Plan docs are safe. The CHANGELOG, README, references, configs, scripts, tests and the spec are not. To change them mid-run, stop the run (`TaskStop`) and run it again.
  - **Stage a new file before `check.py`**: `test_file_modes` reads git's index.
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
3. Read `dev plans/web-design-suite-review/claude-code-capabilities.md` §2, §5 and §6. §6 is the 2026-10-08 re-read of the hooks page and the mods pages, with P25's choice of command hooks run by node.
   - Re-read the skills page before P26, and update §3 with what changed.
   - Re-read the plugin-evals page before P29, and update §1. Read §1 (evals) only when you reach P29.
4. Check the state, with the Bash tool:
   ```bash
   cd /c/DEV/Pro-Web-Designer-Suite-Plug-in && git fetch -q && git status --short && git log --oneline -3 origin/main && gh pr list --state open && git worktree list
   ```
   - Check out `main` and pull. Remove any worktree left in the scratchpad (`git worktree remove PATH`, then `git branch -d` its merged branch).
5. `python -B "dev plans/check_execution_plan.py"` must say `51 open items, 51 scheduled`.
6. Tell the user, in a few lines: the state, what this session does, and the budget.

## 2. Useful facts

- **The plugin** is `plugins/web-design-suite/`:
  - `skills/`: 13 skills.
  - `tests/`: 828 tests, standard-library `unittest`. The helpers are in `tests/wds_support.py`: `PLUGIN`, `SKILLS`, `NODE`, `run_py`, `run_node`, `load_script`, `env`, `TempDirTest`.
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
  - **Who reads what:** the reference's §3 (the token scripts) and §4 (the other keys).
  - **Vendored alone:** `audit_design.py` and `a11y_static.py` (the hook recipe copies them into a project's `scripts/`) run as before without the reader; the audit says the config is not read and refuses `--tokens`.
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

## 4. P25 part 2: the token diff after a token-file edit (LC-C8)

**The item:** LC-C8 in `lifecycle.md` (`grep -n "LC-C8"`). Its guard half shipped in #82; this is the rest: after Claude edits a token file, run `diff_system` against the published snapshot and return the bump and any contrast crossings as context.

**Read first:**
- `hooks/design_hooks.mjs` (the `gate` mode is the model: opt-in, find Python, run a script in the config's folder, cap the text) and `tests/test_hooks.py`.
- design-system-versioning's SKILL.md and `diff_system.py --help`: `old` is the published snapshot (by convention `published/system.json`, or a tokens.css or contract.json); without `new`, the candidate is the project's token files (#78). `--format json` gives the bump and the changes; contrast is checked unless `--no-contrast`.

**What to decide:**
- **Where the published snapshot is named.** Recommended: a new `baselines.system` path in `.design-suite.json` (both readers, `TheNodeReaderAgrees` extended), and a new boolean `hooks.tokenDiff`. Without a snapshot, the hook stays silent.
- **Which edits trigger it.** A file is a token file when the config's `tokens` names it or the spec's globs (`design-rules.json`: `file_classes.token_files`) match it. Run it from the PostToolUse `gate` call, or as a fourth mode on the same matcher; one node process per edit is the cheaper.
- **What Claude hears.** The bump (`major`, `minor`, `patch`), the removed or renamed names, and the contrast pairs that crossed a floor, capped like the gate's text.

**Tests (`test_hooks.py`):** an opted-in token edit with a removed name (a major bump), one with a contrast crossing, a clean one (silent), no snapshot (silent), opted out (silent). Fail-before against `v3.4.0` and `main`.

**Close:** LC-C8 "fixed in 3.5.0" in the inventory, the plan's `P25` row as `P25 part 2, #N`, §9, the CHANGELOG, README's "The hooks", and `project-contract.md`'s `hooks` and `baselines` rows. **Size:** S-M.

## 5. P26: workflow commands and the CI bootstrap

**Items** (the plan's §4 row): XC-C3 (`crosscut.md`), LC-C9 (`lifecycle.md`), PS-C11 (`persuasion.md`), LC-B4, GT-C12 (`gates.md`), XC-C8 (closes here: the commands read `.design-suite.json`), and SS-C6's commands (`studio-systems.md`; its subagent is P27's). Read each by `grep -n`.

**What the plan asks for:** user-invoked workflow skills, each `skills/<name>/SKILL.md` with `disable-model-invocation: true`, so they stay out of the crowded listing: gate (design, perf and a11y static in one run), install-gate (writes the CI template for all three gates in a pinned Playwright container, with a baseline-update job and a tested Windows variant), new-system, critique, migrate, release-check (extract, diff, gate, changelog, guide), figma-sync, and the audit-to-deck chain.

**First:** re-read the skills page's frontmatter and substitutions (`claude-code-capabilities.md` §3 dates from 2026-09-23): `disable-model-invocation`, `allowed-tools` with `${CLAUDE_SKILL_DIR}` and `${CLAUDE_PLUGIN_ROOT}`, `arguments`. The skill-budget test (`test_skill_budget.py`) and the listing tests will see the new skills: check how they count them.

**Split it.** It is M-L. Suggested: part 1, the gate and install-gate commands with the CI template (GT-C12, LC-B4, XC-C8); part 2, the lifecycle chains (LC-C9, PS-C11, XC-C3's rest, SS-C6's commands).

**Tests:** each command's SKILL.md frontmatter (`disable-model-invocation: true`, valid `allowed-tools`), the CI template run through a YAML parser and its pinned image named, and each script the command calls run on a fixture project with a `.design-suite.json`.

## 6. End of session (never skip)

1. Rewrite `docs/HANDOFF.md`: one page, with the state, next steps, blockers and warnings.
2. Update `CLAUDE.md`'s Current State, the execution plan's §9, the inventory, and `dev plans/README.md`'s line for this file.
3. **Rewrite this file** and `next-session-opening-prompt.md` for the session after yours, with the next PRs in the same detail as §4 and §5 here.
4. Run `python -B "dev plans/check_execution_plan.py"`.
5. Commit the docs in a PR of their own. Merge it when it is ready, as §0 defines ready: CI green on its head, every thread resolved, CodeRabbit finished, GitHub clean.
6. Tell the user what merged, what is open, the token use, and what they need to do. Give them the opening prompt for the next session.
