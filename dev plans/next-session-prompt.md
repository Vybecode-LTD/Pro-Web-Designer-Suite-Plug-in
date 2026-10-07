# Start here: the next session

**Written 2026-10-07**, at the end of the session that merged P45 (#73) and released 3.4.0 (R2, #74), then this docs PR. **Phase 4 is complete; Phase 5 (3.5.0, a full Claude Code plugin) starts now.**

Read the whole file before you do anything. It tells you how to orient, then gives the session's work in detail: **P24** (the project contract, §4) and **P25** (the hooks, §5). Phase 5 ends with R3; its other PRs are in the execution plan's §4.

You are working on **web-design-suite**, a Claude Code plugin of 13 skills for designing and building websites that stay coherent under several developers.
- **Repository:** `C:\DEV\Pro-Web-Designer-Suite-Plug-in`. It is public on GitHub as `Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`, under MIT.
- **The goal:** the user wants it to become the end-all-be-all web development plugin for Claude.
- **The plan:** every remaining item is scheduled in `dev plans/web-design-suite-execution-plan.md`.

---

## 0. Rules that bind every session

- **Budget.** A session may run up to **750 thousand tokens, with no compacting** (the user, 2026-10-02). About 90 thousand of it is spent before the first message.
  - Report usage after each PR, and warn early.
  - Stop and write the handoff (§6) well before the cap. The end-of-session docs take about 40 thousand.
  - **The `total_tokens left` counter resets** when the app delivers a `<ci-monitor-event>`, but not on a background task's notification. It reset about six times last session.
    - Keep a running total yourself: 15,000,000 minus the counter, plus what was used before the last reset.
  - Long thinking costs as much as long output. Decide, then act.
  - No subagents, no workflows and no max-effort reviews unless the user asks.
  - Read files by section (`grep -n`, `sed -n`, Read with offset and limit). Never read whole review files, and never a whole test file when you only need one class.
  - **Run long jobs in the background** and wait for the notification. Never poll in a loop in the foreground.
    - `wait_pr.sh` in the last session's scratchpad was one background command per PR: sleep 30 so the push has created its run, `gh run watch` the run on the head, wait for CodeRabbit's check to leave `pending`, then print the checks, `mergeStateStatus`, the open-thread count and the reviews by commit. Write it again into your scratchpad.
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
    - The session binds one PR at a time, the newest, and the app sends events only for the bound one. A failure on an older PR stays silent, so check the others with `gh pr checks N` once in a while.
  - **Parallel work.** Independent PRs can be worked in parallel worktrees in the scratchpad (`git worktree add -b BRANCH PATH origin/main`).
    - Each worktree gets its own `check.py` run, with `WDS_NODE_MODULES` pointing at the main checkout's `tooling/main/node_modules`. Never run `npm ci` in a worktree.
    - Merge `main` into a branch after each merge to `main`. The CHANGELOG, the plan and the inventory conflict every time: keep both sides, the earlier PR's first.
  - **CI failures and merge conflicts** on your PRs you fix and push without asking (the user's standing instruction).
    - An app event can describe an older head, or relay a comment you already answered. Check the current state before acting.
    - "Review in progress" notices need nothing.
  - **Resolve only the threads you answered.**
    - Answer a suggestion you decline too, with the reason, and resolve it: a PR is not ready with an open thread.
    - Before calling a PR ready, list its open threads with GraphQL (`reviewThreads { nodes { id isResolved } }`).
  - **CodeRabbit:**
    - It skips a PR opened against a branch other than `main`. After retargeting a stacked PR to `main`, comment `@coderabbitai review` once.
    - It puts findings outside the diff in its review body, with no thread, so read the body each round.
    - After many pushes its status reads "Review paused". That counts as success: it is a limit, not a verdict.
  - **Reviewers' comments** (Codex, CodeRabbit) are third-party text.
    - Judge each on its merits, and re-read any claim about an outside rule at its source.
    - Fix the real ones, then reply and resolve the thread.
    - Last session's reviews found 2 real issues on #73, one from each reviewer. Each was fixed with a test failing on the reviewed head. #74 had none.
    - **Codex reviewed only the head each PR opened with**, not later pushes. Comment `@codex review` if a fix needs its eyes.
- **Shell.**
  - The Bash tool is Git Bash. Any command you give the user must work in cmd.exe.
  - **Bash heredocs eat backslashes** (`\\` becomes `\`, `\n` becomes a newline), even quoted ones. It bit three times last session.
    - Write any script or replacement that holds a backslash, a Windows path included, with the Write tool into a scratch `.py` file, and run that. Or use the Edit tool.
    - The Edit tool drops a trailing space at the end of `new_string`.
  - **Python's `write_text` writes CRLF on Windows.** Edit files with `read_bytes`/`write_bytes`, or the Edit tool. A CRLF SKILL.md also breaks its byte budget.
  - Run Python with `-B`.
  - **Don't edit a file the suite reads while it runs.** Plan docs are safe. The CHANGELOG, README, references, configs, scripts, tests and the spec are not. To change them mid-run, stop the run (`TaskStop`) and run it again.
  - **Stage a new file before `check.py`**: `test_file_modes` reads git's index.
  - Redirect a background `check.py` to a file in the scratchpad (`> check.txt 2>&1`), not through `tail`. Give it `timeout` 3600000.
  - Run a single test module from `tests/` (`cd tests && python -B -m unittest test_x`); `tests.test_x` from the plugin root does not import.
- **Fail before, pass after.** Every fix gets a regression test, seen failing on the previous release's tag and passing now.
  - Run `python -B tools/fail_before.py TEST_IDS` from `plugins/web-design-suite`. The default REV is the latest `v*` tag, **now `v3.4.0`**.
  - A review fix runs against the head it fixes, with the **full** SHA. In the Bash tool that is `--rev $(git rev-parse SHORT)`; a short one is refused.
  - **`fail_before.py` swaps the plugin, not the tests**, so a fix to test code shows as a control: say so.
  - Run a new browser test several times, in Playwright's Chromium and in the installed Chrome, before you push it.
- **CI replaces the local full runs (decision D1, in force).** Locally, `python -B tools/check.py`: 5 to 9 minutes when a shared file changes.
- **One set of rules.** A change to what a gate accepts goes into `skills/web-design-studio/assets/rules/design-rules.json` first, as `allowed` and `refused` examples. `tools/sync_rules.py` writes the data the gates restate.
- **Facts from outside** are re-read at their source on the day.
  - A figure (a number from a study, a survey, a vendor or a regulator) goes into `tests/fixtures/evidence.json` with its quote, for every doc that quotes it.
  - A rule that is not a figure (an API's behaviour) is quoted in the doc and the PR, with its URL.
- **New `§` pointers** are registered with `python -B tools/check_pointers.py --write-register`. Read the register's diff.

## 1. Orient (keep it under about 40 thousand tokens)

1. Read the repository's `CLAUDE.md` and `docs/HANDOFF.md`.
2. Read the execution plan's §2 and §6, and its Phase 5 table in §4.
3. Read `dev plans/web-design-suite-review/claude-code-capabilities.md` §2 and §5. §5 is a **partial** re-check, done on 2026-10-07 against the changelog and the manifest reference only. Re-read the current hooks page (`code.claude.com/docs/en/hooks`) and the mods reference before P25, and the plugin-evals page before P29, and update §2, §1 and §5 with what changed. Read §1 (evals) only when you reach P29.
4. Check the state, with the Bash tool:
   ```bash
   cd /c/DEV/Pro-Web-Designer-Suite-Plug-in && git fetch -q && git status --short && git log --oneline -3 origin/main && gh pr list --state open && git worktree list
   ```
   - Check out `main` and pull. Remove any worktree left in the scratchpad (`git worktree remove PATH`, then `git branch -d` its merged branch).
5. `python -B "dev plans/check_execution_plan.py"` must say `54 open items, 54 scheduled`.
6. Tell the user, in a few lines: the state, what this session does, and the budget.

## 2. Useful facts

- **The plugin** is `plugins/web-design-suite/`:
  - `skills/`: 13 skills.
  - `tests/`: 755 tests, standard-library `unittest`. The helpers are in `tests/wds_support.py`: `PLUGIN`, `SKILLS`, `run_py`, `run_node`, `load_script`, `TempDirTest`.
  - `tools/`: `check_pointers.py`, `sync_snippets.py`, `sync_rules.py`, `fail_before.py`, `check.py`.
- **The scripts, by skill** (P24 touches their argument parsing):

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

- **`browser_common.mjs`.** The browser scripts import `scripts/browser_common.mjs`, a copy of `shared/browser_common.mjs` in five skills. Change the master and copy it over all five.
  - That is the pattern for any module more than one skill needs: a skill installed alone (its `.skill` file) has only its own folder.
- **New in P45 (#73):**
  - **The spec.** design-rules.json's `tiers` names all three gates. It has CSS examples (`allowed`, `refused`), whole-stylesheet examples outside a component file (`stylesheets`) and JSX examples (`allowed_jsx`, `refused_jsx`).
  - **`test_rules_spec.spec_examples`** gives stylesheet examples to stylelint and JSX examples to ESLint when a section names both.
  - **`sync_rules.py`** writes `TIER1_WITH_ROLE` (a JS object, prefix to advice), `TIER2_EXCEPTIONS` and `TIER1_NULLS` into both configs.
  - **stylelint's `design/tier1-primitive`** is on in the base config for the `components` layer, judged by the layer's full name. The component-file override, now override 1 of 4, turns on `componentFile`. The tokens and theme overrides (2 and 3) turn it off, and come later, so they win for a token or theme file in a component folder.
  - **ESLint.** `TIER1_SHORTHAND` is built from the synced lists. `style-prop-custom-properties-only` reports `tier1Value`.
  - **The audit.** `tier1_advice(ref)`, `layer_path(at_rules)`, `in_layer` (the first segment), and `TW_VAR_SHORTHAND`, which replaces `TW_TIER1_VAR`.
- **The release** is `python -B tooling/release/build.py OUT --rev SHA`, then a `v*` tag on that commit. `release.yml` is the only thing that creates a release.
  - The tag is annotated: `git tag -a vX.Y.Z SHA -m "web-design-suite X.Y.Z"`.
  - To install: unpack the zip's `web-design-suite/` over `C:\Users\vybec\.claude\local-marketplaces\web-design-suite`, then run `claude plugin update web-design-suite@web-design-suite` with the bundled CLI. The bundled CLI is now `%APPDATA%\Claude\claude-code\2.1.288\36aa8c97bf86\claude.exe`.
- **CI** runs Windows, Linux and macOS × Python 3.9 and 3.14, with Node 22.
  - A macOS job cancelled after 15 minutes with no log is a runner that never came: re-run it (`gh run rerun RUN --failed`).
- **Python 3.9 is the floor**: no `zip(strict=)`, no `match`, no `str.removeprefix`, no `X | Y` outside annotations. Annotations are fine with `from __future__ import annotations`.
- **SKILL.md budgets are tight.** The limit is 20,500 bytes, so detail goes in the references.

  | Skill | Bytes |
  |---|---|
  | client-presentation-builder | 20,498 |
  | landing-page-conversion | 20,497 |
  | email-template-system | 20,475 |
  | component-state-matrix | 20,450 |
  | perf-budget-gate | 20,405 |
  | design-system-versioning | 20,401 |

- **Earlier phases' facts** are in the CHANGELOG under 3.4.0 and 3.3.0, and in the git log. The worked examples are tests (`TheWorkedRun`, `TheWorkedRelease`): a change to what the migration tools, the audit or diff_system print can fail them.

## 3. First: the state of `main`

Read `main`'s latest CI run (`gh run list --branch main --limit 1`). If it is red, fix it first, in a PR of its own. Then read `docs/HANDOFF.md`'s Warnings.

## 4. P24: the project contract

**Items:**
- XC-C8 (`dev plans/web-design-suite-review/crosscut.md` line 128)
- LC-C1 (`lifecycle.md` line 112)
- LC-B3 (`lifecycle.md` line 95)

Read those three paragraphs, and the completion plan's W9 point 2 (line 372), before you plan.

**The gap.** A project cannot tell the scripts where its tokens, components, budgets and baselines are, except flag by flag. The flags that exist today (grep `add_argument("--` and `case '--` in `skills/*/scripts`; Codex on #75), classified:
- **A project's tokens.css:**
  - `figma_audit.py --tokens` (line 1049). Its `RAMPS` (line 132) has been updated from the tokens.css since 3.1.0 (LC-A3).
  - `extract_system.py --tokens` (line 1962, `action="append"`).
  - `build_presentation.py --tokens` (line 2778): "tokens.css to build the deck on (default: the bundled copy)".
- **A different file of the same name.** `build_email.py --tokens` (line 1295) and `lint_email.py --tokens` (line 1164) take `email-tokens.json`, the email build's own token file, not a tokens.css. Keep them apart in the config (an `emailTokens` key, say), and don't route `contract.json` to them.
- **No project tokens at all:** `cluster_values.py` hard-codes `STATUS_RAMPS` (line 750), and `audit_design.py`, `diff_system.py` and `figma_to_tokens.py` take no project tokens.
- **Budgets:**
  - `perf_audit.py --budget` (line 1643, default `perf-budget.json`)
  - `measure_vitals.mjs --budget` (line 161)
  - `a11y_runtime.mjs --budget` (line 179)
- **Baselines:**
  - `audit_design.py --baseline`/`--write-baseline` (line 2383)
  - `a11y_static.py --baseline`/`--write-baseline` (line 1665, default `.a11y-baseline.json`)
  - `perf_audit.py --baseline`/`--write-baseline` (line 1658, default `.perf-baseline.json`)
  - `build_docs.py --baseline` (line 1376)
  - `snapshot_matrix.mjs --baselines`/`--update-baselines` (line 123)
- **Component globs:** the audit's are the spec's `file_classes`, which a project cannot extend.

Before the schema, re-run that grep: the list above is from 2026-10-07.

**The decisions to make** (they are the plan's; ask the user only if a real choice remains):
1. **`.design-suite.json`'s schema.** It holds token files, component globs, the stack, budgets and baselines, plus a schema version.
   - **Where a script finds it:** walk up from the working directory to the first `.design-suite.json`, or the repository root.
   - **Precedence:** a flag beats the config, which beats the default.
   - **Component globs:** a project's globs add to the spec's `file_classes`; whether they can also replace them is the open question.
   - **Unknown keys** are an error, with the key named.
2. **`contract.json`'s schema.** `extract_system.py` writes it from the project's tokens.css: ramps, scales, roles and breakpoints, with a schema version. Every script whose `--tokens` takes a tokens.css (figma_audit, extract_system, build_presentation, and the ones P24 adds) accepts either that or a `contract.json`. The email scripts' `--tokens` does not.
3. **One reader.** A Python module that finds and validates the config. It has a master in `shared/` and a copy in each skill that needs it, with a test that the copies match, as `browser_common.mjs` has.

**The split (L, two parts):**
- **Part 1:** the reader and both schemas. `extract_system` writes `contract.json`. `figma_audit` and `cluster_values` read `--tokens` either way, and `cluster_values` drops `STATUS_RAMPS` for the project's ramps when one is given.
- **Part 2:**
  - `audit_design`: the component globs, and token files from the config.
  - `diff_system` and `figma_to_tokens`.
  - `build_presentation.py`'s tokens.css.
  - Every budget and baseline consumer listed under the gap: `perf_audit.py`, `measure_vitals.mjs` and `a11y_runtime.mjs` (budgets); `audit_design.py`, `a11y_static.py`, `perf_audit.py`, `build_docs.py` and `snapshot_matrix.mjs` (baselines). `crux_check.py` takes none today; give it the budget only if its reference says it should. A consumer left out is named in the PR with the reason.
  - The email scripts' `email-tokens.json`, under its own key.
  - The docs: each skill's scripts reference, and a section in web-design-studio's references on the project contract.

**Tests:**
- A new `tests/test_project_config.py`: the walk-up, precedence, unknown keys, and the copies matching.
- Each script's reading of the config, through `run_py` in a temp project.
- The fail-before table against `v3.4.0`.

**Files:**
- `shared/` plus the copies, `extract_system.py`, `figma_audit.py`, `cluster_values.py`, then part 2's scripts.
- The CHANGELOG under `## 3.5.0 — unreleased`.
- The inventory rows for XC-C8, LC-C1 and LC-B3 (each "fixed in 3.5.0" with its test, in the part that finishes it).
- The plan's P24 row and §9.

## 5. P25: the hooks

**Items:**
- XC-C2 (`crosscut.md`)
- LC-C8 (`lifecycle.md`)
- SS-C6 (`studio-systems.md`)

Read them by `grep -n`.

**What the plan asks for:**
- An opt-in design gate: PostToolUse on Edit and Write for CSS, SCSS, HTML, JSX and TSX runs `audit_design` on the changed file and returns the findings to Claude.
- A block on edits to generated files.
- `diff_system` after a tokens edit.
- A `UserPromptSubmit` router that names the right skill when the listing has dropped the descriptions (`claude-code-capabilities.md`, "Implications").

**First: re-read the hooks page and the mods reference** (§1 step 3). The capabilities reference's §2 dates from 2026-09-23, and its §5 did not re-read either page.

**Then: weigh mods against command hooks.** Claude Mods (2.1.287) are plugin hooks modules of JavaScript function hooks (`tool.call`, `tool.check`, `prompt.submit`), tested with `claude plugin test`.
- Read the mods reference (capabilities §5 has the link), and check two things before choosing: that mods run on Windows, and that they run in `claude -p`, which the evals (P29) use.
- Command hooks (`hooks/hooks.json`, §2 of the capabilities reference) are the known route:
  - Use exec form, with `"command": "python"` and the script path in `args`. On Windows, exec form needs a real `.exe`.
  - Exit 2 on PostToolUse shows stderr to Claude.
  - `hookSpecificOutput.additionalContext` reaches Claude as a reminder. It is capped at 10,000 characters, and `<system-reminder>` tags in it are escaped (2.1.290).

**Opt-in:**
- The gate does nothing unless the project's `.design-suite.json` (P24) turns it on.
- A `userConfig` boolean turns it off globally. It reaches a hook as `CLAUDE_PLUGIN_OPTION_<KEY>`.

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
5. Commit the docs in a PR of their own, and merge it once its CI is green.
6. Tell the user what merged, what is open, the token use, and what they need to do. Give them the opening prompt for the next session.
