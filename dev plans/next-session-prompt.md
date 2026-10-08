# Start here: the next session

**Written 2026-10-08**, at the end of the session that:
- merged P24 part 2 (#78): the project's tokens in every script that compared against the starter's;
- merged P24 part 3 (#79): every key of `.design-suite.json` has its readers, with a Node reader (XC-C8 stays open for the hook and the commands);
- found N37 (CodeRabbit on #78): the project's config reaches the audit but not stylelint or ESLint.

Read the whole file before you do anything. It tells you how to orient, then gives the session's work in detail: **P24 part 4** (N37, §4) and **P25** (the hooks, §5). Phase 5 ends with R3; its other PRs are in the execution plan's §4.

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
    - Last session's reviews on #78 found 6 real issues, each fixed with a test failing on the head it reviewed. One was declined with the reason: the reader fallback for scripts that are never vendored alone. One became a scheduled item, N37.
    - **Codex reviews only the head each PR opened with**, not later pushes. Comment `@codex review` if a fix needs its eyes.
- **Shell.**
  - The Bash tool is Git Bash. Any command you give the user must work in cmd.exe.
  - **Bash heredocs eat backslashes** (`\\` becomes `\`, `\n` becomes a newline), even quoted ones. It bit twice last session: a test string got a real newline, and a heredoc with a `\u` escape failed to parse at all.
    - Write any script or test code that holds a backslash with the Write tool into a scratch `.py` file, and run that. Or use the Edit tool, which is safe.
    - The Edit tool drops a trailing space at the end of `new_string`.
  - **Python's `write_text` writes CRLF on Windows.** Edit files with `read_bytes`/`write_bytes`, or the Edit tool. A CRLF SKILL.md also breaks its byte budget.
  - Run Python with `-B`.
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

## 1. Orient (keep it under about 40 thousand tokens)

1. Read the repository's `CLAUDE.md` and `docs/HANDOFF.md`.
2. Read the execution plan's §2 and §6, and its Phase 5 table in §4.
3. Read `dev plans/web-design-suite-review/claude-code-capabilities.md` §2 and §5. §5 is a **partial** re-check from 2026-10-07, against the changelog and the manifest reference only.
   - Re-read the current hooks page (`code.claude.com/docs/en/hooks`) and the mods reference before P25, and update §2 and §5 with what changed.
   - Re-read the plugin-evals page before P29, and update §1. Read §1 (evals) only when you reach P29.
4. Check the state, with the Bash tool:
   ```bash
   cd /c/DEV/Pro-Web-Designer-Suite-Plug-in && git fetch -q && git status --short && git log --oneline -3 origin/main && gh pr list --state open && git worktree list
   ```
   - Check out `main` and pull. Remove any worktree left in the scratchpad (`git worktree remove PATH`, then `git branch -d` its merged branch).
5. `python -B "dev plans/check_execution_plan.py"` must say `53 open items, 53 scheduled`.
6. Tell the user, in a few lines: the state, what this session does, and the budget.

## 2. Useful facts

- **The plugin** is `plugins/web-design-suite/`:
  - `skills/`: 13 skills.
  - `tests/`: 799 tests, standard-library `unittest`. The helpers are in `tests/wds_support.py`: `PLUGIN`, `SKILLS`, `NODE`, `run_py`, `run_node`, `load_script`, `env`, `TempDirTest`.
  - `tools/`: `check_pointers.py`, `sync_snippets.py`, `sync_rules.py`, `fail_before.py`, `check.py`.
- **The project contract (P24, #76, #78, #79).** `references/project-contract.md` in web-design-studio is the user-facing account. In short:
  - **`.design-suite.json`.** `schema: 1` is required. The other keys are `tokens`, `emailTokens`, `components`, `stack`, `budgets` (`perf`, `a11y`) and `baselines` (`audit`, `a11y`, `perf`, `docs`, `snapshots`).
    - Found by walking up from the working directory, never past the folder that holds `.git`. Paths are relative to the file, normalised.
    - A flag beats it, and it beats the default. A mistake exits 2 with the key named.
  - **`shared/project_config.py`.** The API:
    - `find_config`, `load_config`, `project_config`, `config_path(config, section, key)`, `token_sources(flag)`;
    - `read_contract`, `read_tokens(paths)`, which returns a `ProjectTokens` in the contract's sections, from a contract.json or a tokens.css;
    - `ProjectConfig.is_component(path)` for the globs.

    It is copied beside the scripts of **ten** skills. `test_project_config.TheCopiesAreTheMaster` finds the readers by their `from project_config import` line. A tokens.css is read by its defaults, with tiers by value; the eight names on the starter where that differs from extract_system's name-first tiers are pinned by a test.
  - **`shared/browser_common.mjs`** has `findConfig`, `loadConfig` and `projectConfig`, which apply the same checks with the same messages on strict JSON. `TheNodeReaderAgrees` runs both readers on 19 configs. It is copied into five skills.
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
  - To install: unpack the zip's `web-design-suite/` over `C:\Users\vybec\.claude\local-marketplaces\web-design-suite`, then run `claude plugin update web-design-suite@web-design-suite` with the bundled CLI (`%APPDATA%\Claude\claude-code\2.1.288\36aa8c97bf86\claude.exe`).
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
  | web-design-studio | 20,303 |

- **Earlier phases' facts** are in the CHANGELOG under 3.4.0 and 3.3.0, and in the git log. The worked examples are tests (`TheWorkedRun`, `TheWorkedRelease`): a change to what the migration tools, the audit or diff_system print can fail them.

## 3. First: the state of `main`

Read `main`'s latest CI run (`gh run list --branch main --limit 1`). If it is red, fix it first, in a PR of its own. Then read `docs/HANDOFF.md`'s Warnings.

## 4. P24 part 4: the project's config in stylelint and ESLint (N37)

**The item:** N37 in `dev plans/web-design-suite-completion-plan.md` (found by CodeRabbit on #78).
- `audit_design.py` reads a project's `.design-suite.json`:
  - a token file it names is a token file wherever it sits;
  - its `components` globs add to the component files;
  - the ramps its tokens declare are Tier-1 colours with a role (Law 6).
- The stylelint config and the ESLint config still class files by the rule spec's globs and `tiers` alone. So for a project with a config, the gates disagree: a component under `src/widgets/` that reads `--brand-500` fails the audit and passes stylelint.

**Read first:**
- `skills/web-design-studio/assets/configs/`: how `stylelint.config.mjs` and `eslint.design.config.mjs` are installed in a project, and how they class component files and token files.
- `tests/test_real_tools.py`: how a real-tool test builds its temp project.
- P45's PR (#73) is the model for bringing one rule to both configs.

**What to decide:**
- **How the configs get the reader.**
  - The configs are copied into a project, so they need a copy of the Node reader beside them, as the browser scripts have `browser_common.mjs`.
  - Choose between copying `browser_common.mjs` into `assets/configs/` (a sixth copy, and `test_browser_scripts` must learn it) and a smaller `project_config.mjs` that `browser_common.mjs` re-exports. Either way, keep one master.
- **The token ramps.** The ESLint config and the stylelint plugin need the project's ramp steps.
  - Node has no `read_tokens`, so either port it (only the ramps: a tokens.css's `:root` defaults named `--<name>-<step>` with a literal colour, and a contract's `ramps`), or have the configs read `contract.json` only, and say so.
  - Prefer the smallest faithful port, with a parity test against `read_tokens` like `TheNodeReaderAgrees`.
- **The file classes.** The config's token files are token files for stylelint's token-file override, and its `components` globs join the component-file override.

**Tests:**
- Real-tool tests: stylelint and ESLint in a temp project with a `.design-suite.json`.
  - A component under a glob that reads a project ramp step is refused.
  - A token file the config names may hold literals.
  - Without the config, both pass as today.
- The spec's examples still pass through every gate (`test_rules_spec`).
- Fail-before against `v3.4.0`, and against `main`.

**Size:** M. **Files:** `assets/configs/*.mjs`, the reader's copy, `tests/test_real_tools.py`, `test_project_config.py`, the reference's §4 ("Not read by") and the CHANGELOG. Close N37 in the completion plan ("Done for 3.5.0"), and the row in the plan as `P24 part 4, #N`.

## 5. P25: the hooks

**Items:**
- XC-C2 (`crosscut.md`)
- LC-C8 (`lifecycle.md`)
- SS-C6 (`studio-systems.md`)
- XC-C8's hook part: the hook reads `.design-suite.json`. XC-C8 itself closes in P26, with the commands.

Read them by `grep -n`.

**What the plan asks for:**
- An opt-in design gate: PostToolUse on Edit and Write for CSS, SCSS, HTML, JSX and TSX runs `audit_design` on the changed file and returns the findings to Claude.
- A block on edits to generated files.
- `diff_system` after a tokens edit. It now takes the project's tokens as its candidate without `new`, so the hook can pass only the published snapshot.
- A `UserPromptSubmit` router that names the right skill when the listing has dropped the descriptions (`claude-code-capabilities.md`, "Implications").

**First: re-read the hooks page and the mods reference** (§1 step 3). The capabilities reference's §2 dates from 2026-09-23, and its §5 did not re-read either page.

**Then: weigh mods against command hooks.** Claude Mods (2.1.287) are plugin hooks modules of JavaScript function hooks (`tool.call`, `tool.check`, `prompt.submit`), tested with `claude plugin test`.
- Read the mods reference (capabilities §5 has the link), and check two things before choosing: that mods run on Windows, and that they run in `claude -p`, which the evals (P29) use.
- Command hooks (`hooks/hooks.json`, §2 of the capabilities reference) are the known route:
  - Use exec form, with `"command": "python"` and the script path in `args`. On Windows, exec form needs a real `.exe`.
  - Exit 2 on PostToolUse shows stderr to Claude.
  - `hookSpecificOutput.additionalContext` reaches Claude as a reminder. It is capped at 10,000 characters, and `<system-reminder>` tags in it are escaped (2.1.292).

**Opt-in:**
- The gate does nothing unless the project's `.design-suite.json` turns it on. That needs a new key (say `hooks: {"designGate": true}`) in `project_config.py` **and** the Node reader, with `TheNodeReaderAgrees` extended, so the two readers keep agreeing.
- A `userConfig` boolean turns it off globally. It reaches a hook as `CLAUDE_PLUGIN_OPTION_<KEY>`.
- The hook reads the config through the plugin's own copy of the reader (the hook's folder needs one, and `TheCopiesAreTheMaster` must find it).

**Tests:**
- Each hook script fed JSON on stdin from fixtures: the opted-out project, an opted-in clean file, an opted-in file with a finding, and a generated file.
- `claude plugin validate --strict` already runs in CI.

**Size:** M.

**Close each PR:**
- The CHANGELOG under `## 3.5.0 — unreleased`.
- Each item "fixed in 3.5.0" in the inventory, with its test.
- The PR's own row in the plan as `Pk, #N`, and §9.

## 6. End of session (never skip)

1. Rewrite `docs/HANDOFF.md`: one page, with the state, next steps, blockers and warnings.
2. Update `CLAUDE.md`'s Current State, the execution plan's §9, the inventory, and `dev plans/README.md`'s line for this file.
3. **Rewrite this file** and `next-session-opening-prompt.md` for the session after yours, with the next PRs in the same detail as §4 and §5 here.
4. Run `python -B "dev plans/check_execution_plan.py"`.
5. Commit the docs in a PR of their own. Merge it when it is ready, as §0 defines ready: CI green on its head, every thread resolved, CodeRabbit finished, GitHub clean.
6. Tell the user what merged, what is open, the token use, and what they need to do. Give them the opening prompt for the next session.
