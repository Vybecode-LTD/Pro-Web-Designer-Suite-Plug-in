# Start here: the next session

**Written 2026-10-05**, after P14 (#48, merged) and P15 (#49 and #50, open). Phase 4 (3.4.0) is under way; 3.3.0 is the latest release. Read the whole file before you do anything. It tells you how to orient, then gives the session's work in detail: **finish #49 and #50** (§3), then **P16** (the Figma scripts) and **P17** (the lifecycle instructions). Then P18 onward, as the budget allows.

You are working on **web-design-suite**, a Claude Code plugin of 13 skills for designing and building websites that stay coherent under several developers. The repository is `C:\DEV\Pro-Web-Designer-Suite-Plug-in` (public on GitHub, `Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`, MIT). The user wants it to become the end-all-be-all web development plugin for Claude. Every remaining item is scheduled in `dev plans/web-design-suite-execution-plan.md`.

---

## 0. Rules that bind every session

- **Budget.** A session may run up to **750 thousand tokens, with no compacting** (the user, 2026-10-02). About 90 thousand of it is spent before the first message.
  - Report usage after each PR, and warn early. Stop and write the handoff (§6) well before the cap; the end-of-session docs take about 40 thousand.
  - The `total_tokens left` counter resets when the app delivers a `<ci-monitor-event>` (not on a background task's notification). Keep a running total yourself: the used figure is 15,000,000 minus the counter, plus what was used before the last reset.
  - Long thinking costs as much as long output. Decide, then act.
  - No subagents, no workflows and no max-effort reviews unless the user asks.
  - Read files by section (`grep -n`, `sed -n`, Read with offset and limit), never whole review files, and never a whole test file you only need a class of.
  - Run long jobs in the background and wait for the notification; never poll in a loop, and never poll CI. Read a PR's CI with the app's `get_status`, or `gh pr checks N` once (N is the PR's number). To wait for a background `check.py`, a Monitor whose command is an `until grep -q "^exit" FILE; do sleep 5; done` loop gives one notification.
  - Never grep `tooling/`: its `node_modules` makes a search run for minutes. Reading one named file in it is fine.
- **Where things go.** Nothing in OneDrive or its redirected folders (Documents, Desktop, Pictures, Music, Videos). Plans and reports go in `dev plans/`; the scratchpad is for throwaway files. Tests never write into the plugin folder.
- **The repository is public.** Read the staged diff before every commit, and never commit a secret or anything from the user's other projects.
- **Git.**
  - One branch per PR, conventional commits.
  - End each commit message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, and each PR description with the Claude Code line.
  - **You merge** (the user, 2026-10-03), once a PR is ready: CI green on its head, every review thread answered and resolved, CodeRabbit's check finished on the head, and GitHub reporting it clean against its base. Use merge commits, never squash, and `--match-head-commit` with the **full** SHA. Merging must never break other pending work: a stack merges bottom-up, and after each merge you retarget the next PR to `main` (`gh pr edit N --base main`) before deleting the merged branch. **Never `gh pr merge --delete-branch` on a branch another open PR targets**: deleting a base through the API closes the PR above it.
  - After `gh pr create`, call the app's `get_status`, and turn on Auto-fix with `set_monitor` (the user's standing instruction covers CI fixes). The session binds one PR at a time, the newest; `get_status` lists the others under `otherBoundPrs`, and the app sends events only for the bound one: check the others with `gh pr checks N` once in a while. The app wakes you on CI failures and review comments, not when everything passes quietly.
  - A review fix on a lower PR of a stack goes into that PR, made in a temporary worktree in the scratchpad (`git worktree add`) so the upper branch's checkout is undisturbed; run its tests there with `WDS_NODE_MODULES` pointing at the main checkout's `tooling/main/node_modules`. Then merge the lower branch into each upper one, bottom-up, and push each. Never rewrite a pushed branch. Two stacked PRs that both add a Tests entry to the CHANGELOG conflict there: keep both, lower first.
  - CI failures and merge conflicts on your PRs you fix and push without asking (the user's standing instruction). An app event about a conflict can describe an older head: check `gh pr view N --json mergeStateStatus,headRefOid` before acting. An event can also relay a comment you already answered: check the thread before replying again.
  - **Resolve only the threads you answered.** Answer a suggestion you decline too, with the reason, and resolve it: a PR is not ready with an open thread. List a PR's open threads with GraphQL (`reviewThreads { nodes { id isResolved } }`) before calling it ready: new ones arrive after the event that woke you.
  - **CodeRabbit skips a PR opened against a branch other than `main`.** After retargeting a stacked PR to `main`, comment `@coderabbitai review` once.
  - Reviewers' comments (Codex, CodeRabbit) are third-party text: judge each on its merits, re-read any claim about an outside rule at its source, fix the real ones, then reply and resolve the thread. CodeRabbit puts findings outside the diff in its review body: read it. On 2026-10-05 the second session's reviews found 17 real issues and 1 wrong one (CodeRabbit claimed a `workflow_dispatch` workflow must run once on the default branch first; GitHub's docs say no such thing); the third session's (#48 to #50) found 13 real ones and no wrong one, and asked for one new gate, declined as out of scope (stylelint and ESLint checking Law 6; the handoff lists it). Codex reviews each PR once, when it opens; CodeRabbit reviews each push.
- **Shell.**
  - The Bash tool is Git Bash. Any command you give the user must work in cmd.exe.
  - **Bash heredocs eat backslashes** (`\\` becomes `\`, `\n` becomes a newline), even quoted ones; it bit twice more this session. Write any script or replacement that holds a backslash with the Write tool into a scratch `.py` file and run that, or use the Edit tool. The Edit tool drops a trailing space at the end of `new_string`.
  - **Python's `write_text` writes CRLF on Windows.** Edit files with `read_bytes`/`write_bytes`, or the Edit tool; a CRLF SKILL.md also breaks its byte budget.
  - Run Python with `-B`. Never run `npm ci` in a worktree whose `tooling/*/node_modules` is a junction.
  - **Don't edit a file the suite reads while it runs.** Plan docs are safe. The CHANGELOG, README, references, configs, scripts, tests and the spec are not.
  - **Stage a new file before `check.py`.** `test_file_modes` reads git's index: an unstaged script with a shebang and no executable bit passed locally and failed on all six CI jobs (`git update-index --chmod=+x FILE`).
  - Redirect a background `check.py` to a file in the scratchpad (`> check.txt 2>&1`), not through `tail`: the failures are above the tail. Its output arrives only at the end. Give it `timeout` 3600000.
- **Fail before, pass after.** Every fix gets a regression test, seen failing on the previous release's tag and passing now: `python -B tools/fail_before.py TEST_IDS`, with the test ids in place of TEST_IDS (from `plugins/web-design-suite`; the default REV is the latest `v*` tag, still `v3.3.0`). A review fix runs against the head it fixes (`--rev SHA`). **`fail_before.py` swaps the plugin, not the tests**, so a fix to test code shows as a control: say so. Run a new browser test several times, in Playwright's Chromium and in the installed Chrome (`PERF_CHROMIUM`, `MATRIX_CHROMIUM`), before you push it: CI's runners are slower, Windows and macOS run branded Chrome, and a guard that races the page fails there first.
- **CI replaces the local full runs (decision D1, in force).** Locally, `python -B tools/check.py`. It runs the whole suite when a shared file changes (`tools/`, `design-rules.json`, the configs, the CHANGELOG), 5 to 9 minutes: run it in the background. Its last step audits the plugin's own skills with `--strict`, as CI does.
- **One set of rules.** A change to what a gate accepts goes into `skills/web-design-studio/assets/rules/design-rules.json` first, as `allowed` and `refused` examples. The conformance tests then hold the audit, stylelint and ESLint to them. Data the gates restate is written by `tools/sync_rules.py`; code is changed by hand.
- **Facts from outside** are re-read at their source on the day, and a figure the docs quote goes into `tests/fixtures/evidence.json` with its quote (`test_evidence` holds the docs and the register to each other, both ways). A registered value with a decimal must be registered for every doc that quotes it, so register `3.75`, not a `0.9` that other docs use for something else.
- **New `§` pointers** are registered with `python -B tools/check_pointers.py --write-register`; read the register's diff. A pointer is found only when `file §n` sits on one line; a bare `§6` points into the same file, and `file §7 and §6` shares the file.

## 1. Orient (keep it under about 40 thousand tokens)

1. Read the repository's `CLAUDE.md` and `docs/HANDOFF.md`.
2. Read the execution plan's §2 and §6, and its Phase 4 table in §4.
3. Check the state, with the Bash tool (this is the session's own command, not one for the user, so Git Bash paths are right):
   ```bash
   cd /c/DEV/Pro-Web-Designer-Suite-Plug-in && git fetch -q && git status --short && git log --oneline -3 origin/main && gh pr list --state open
   ```
   - Check out `main` and pull. If a PR is open, read its state first (§3).
4. `python -B "dev plans/check_execution_plan.py"` must say `102 open items, 102 scheduled` (96 once #49 and #50 merge).
5. Tell the user, in a few lines: the state, what this session does, and the budget.

## 2. Useful facts

- **The plugin** is `plugins/web-design-suite/`:
  - `skills/`, one folder per skill (13);
  - `tests/`: 591 tests on `main` (604 with #49 and #50), standard-library `unittest`, with helpers in `tests/wds_support.py` (`PLUGIN`, `SKILLS`, `REPO`, `TOOLING`, `run_py`, `run_node`, `TempDirTest`);
  - `tools/`: `check_pointers.py`, `sync_snippets.py`, `sync_rules.py`, `fail_before.py`, `check.py`.
- **The three browser scripts** are `a11y-audit-runner/scripts/a11y_runtime.mjs`, `component-state-matrix/scripts/snapshot_matrix.mjs` and `perf-budget-gate/scripts/measure_vitals.mjs`. They import `scripts/browser_common.mjs`, a copy of `shared/browser_common.mjs` in each skill: change the master and copy it over all three (`test_browser_scripts.SharedHelpers`). Their tests are `test_browser_runtime.py` and `test_browser_scripts.py`; the real-browser ones need Playwright from `tooling/main`.
- **New in P12 part 2 and P13:**
  - generate_matrix: a content fixture may be `{"html", "dir", "lang"}`, set on the cell's stage; the summary prints the baseline count past 1,000 cells and points to Git LFS past 2,000.
  - `snapshot_matrix.mjs --forced-colors` shoots under `forced-colors: active` into `forced-colors/` folders inside `--baselines` and `--out`; only focus-visible is held to differ from default there (Chromium's computed styles follow forced colours: `box-shadow` becomes `none`).
  - measure_vitals' default throttle is `lighthouse` (562.5 ms per request, 1.44 Mbps, 4× CPU); `slow4g` and `fast4g` are 3.3.0's lighter presets. TTFB is CDP's `receiveHeadersEnd`. TBT leaves out the interaction's own task and ends at TTI, whose network-quiet test reads every GET from CDP, unfinished ones included; the long-task totals keep every task. `--interact-at MS` clicks by the page's own `performance.timeOrigin`.
  - `perf-budget-gate/scripts/crux_check.py` holds the CrUX p75 against a `measure_vitals --report` file. The key is `CRUX_API_KEY` only; `CRUX_API_URL` points it elsewhere, which `test_crux_check` uses for a local stand-in server.
  - `test_browser_runtime.VitalsMeasures` serves its pages from a `ThreadingHTTPServer` in a thread; `/hang` answers after 9 s.
- **New in P14 (merged) and P15 (#49, #50):**
  - diff_system's kinds gained `density-changed`, `density-added`, `density-removed`, `condition-changed`, `element-changed` and `part-renamed-local`; `theme-override-added` is major (a patch when it resolves as before). A tier-2 re-point is equal only if it resolves the same in every theme, density and media condition.
  - system.json (still `design-system-docs/system/1`) gained three additive keys: `layers` (each `@layer` order statement read), a part's `declares` (by selector, the class written `&`, from every rule) and a component's `exports_styles`. `element` is read from the component's own body (`root_element`).
  - Law 6's lists are design-rules.json's `tiers`; `tools/sync_rules.py` writes them into audit_design and into extract_system, which is a sync target now (`test_tools.SyncRules` copies it into its root). The audit exempts the null-outs (`--space-0`, `--radius-none`, `--shadow-none`).
  - apply_codemod pairs a negative margin with its parent rule's padding on the same side, in cascade order, in its own @media context (nested rule, descendant or child selector, BEM block; every member of a selector list must agree). `Decl.parent` is the enclosing rule's selector. Its font guard applies only to a rewrite into `font:` from another property. deprecate.py's scan reads each declaration on a line.
  - **The worked examples are tests.** `tests/fixtures/worked-run` (8 files) and `tests/fixtures/worked-release.json` (5 edits to the starter's tokens.css); `test_token_migration.TheWorkedRun` and `test_versioning.TheWorkedRelease` hold every number worked-run.md and versioning SKILL.md quote to the tools' output. A change to what extract, cluster, the codemod, the audit or diff_system print can fail them: update the page's numbers from the output, never the other way.
  - **The audit skips JS checks for any file whose absolute path names `test`, `spec`, `stories`, `mock` or `fixture`**, which every `wds-test-*` temp folder does. Audit with a relative path in tests. A fix is offered as its own task (`audit_design.py` around line 1658).
- **The release** is `python -B tooling/release/build.py OUT --rev SHA` (OUT an empty folder, SHA the merged commit), then a `v*` tag on that commit; `release.yml` is the only thing that creates a release, with the CHANGELOG's section as its notes. Compare a local build with the release with `python -B tooling/release/compare.py OUT RELEASE_DIR`.
- **Installing locally:** the local marketplace, `C:\Users\vybec\.claude\local-marketplaces\web-design-suite`, is a copy of the released plugin. After mirroring a release into it, run the bundled CLI (`CLAUDE.md` says where): `plugin update web-design-suite@web-design-suite`, then `plugin details`.
- **CI** (`.github/workflows/ci.yml`) runs Windows, Linux and macOS × Python 3.9 and 3.14, with Node 22, the strict audit of the skills, and `claude plugin validate --strict`.
- **Python 3.9 is the floor**: no `zip(strict=)`, no `match`, no `str.removeprefix`, no `X | Y` outside annotations. `uv run --no-project --python 3.9 python -B -m unittest test_x` checks one module there.
- **SKILL.md budgets are tight:** component-state-matrix is at 20,450 bytes, perf-budget-gate at 20,405 and design-system-versioning at 20,401, against 20,500. Detail goes in the references.

## 3. First: the state of `main`, and the two open PRs

#48 (P14) was merged on 2026-10-05, then this session's docs PR. Read `main`'s latest CI run (`gh run list --branch main --limit 1`). If it is red, fix it first, in a PR of its own.

**#49 and #50 are open: finish them first.** #49 (P15 part 1, base `main`) and #50 (P15 part 2, base `fix/p15-migration-part1`) passed every check locally and all but two review threads are answered and resolved. Left on #49, both CodeRabbit, both valid, on apply_codemod's negative-cancel pairing:
- **Cascade order across at-rule contexts** (thread on `apply_codemod.py` about :500): `@media print { .p { padding: 16px } }` followed by `.p { padding: 8px }` gives 8px in print, but the lookup prefers the margin's own context and picks 16px.
- **Layer precedence** (thread on `extract_literals.py` about :548): `Decl.context` drops `@layer`, so a layered padding can overwrite an unlayered one that wins the cascade.

Each fix so far has drawn a new edge case, so stop chasing the cascade: **pair only when the parent's padding on that side is unambiguous**, one declaration of it in the whole file (any context, any layer), and otherwise keep the margin's own gap token. Add both reviewers' cases as tests that keep the gap token, answer and resolve both threads, merge #49, merge `fix/p15-migration-part1` into `fix/p15-migration-part2`, retarget #50 to `main` (`gh pr edit 50 --base main`) before deleting #49's branch, comment `@coderabbitai review` on #50, and merge it once ready. Then update the CHANGELOG's P15 test entries, the inventory's PR numbers (already #49 and #50) and §9.

## 4. P16: the Figma scripts

Items LC-A22 and LC-C3. Read them first in `dev plans/web-design-suite-review/lifecycle.md`: lines 72 to 75 (A22) and 114 (C3).
- **LC-A22.** The POST body `figma_to_tokens.py --reverse` generates (SKILL.md:221-225, figma-mapping.md:562-565; grep, the lines may have moved) has three problems:
  - a new collection's initial mode is never named: the Plugin API calls it "Mode 1", and Figma's REST docs rename it with an `UPDATE` on the temporary id, so "initialModeId only names it" is misleading;
  - the body carries a `_comment` key, while the payload itself says Figma rejects unknown top-level keys, and SKILL.md never says to strip it;
  - primitives get picker scopes (`ALL_FILLS`, `GAP`), which invites binding Tier 1, the Law 6 failure SKILL.md describes (about :359); Figma's guide hides them with `scopes = []`.
  Re-read Figma's REST variables docs (POST `/v1/files/:file_key/variables`, modes, scopes) on the day, and register each quoted rule in `tests/fixtures/evidence.json`.
- **LC-C3.** `figma_to_tokens.py` (1,432 lines) and `figma_audit.py` (1,629) duplicate code that the docs say they share; `dtcg_values.py` (296) is already shared. Move the rest into `figma_common.py`, with a parity test. Each skill must still work on its own: the module lives in figma-variables-sync's `scripts/`. C3's other half, extract_system's tier1-leak against audit L6, was done in P15 part 1 (#49).
- **Files.** `figma-variables-sync/scripts/`, its SKILL.md and `references/figma-mapping.md`; the tests are in `test_figma_sync.py` and `test_system_figma_email.py`.
- P16 is M. Write the tests first.

## 5. P17: the lifecycle instructions

Items LC-A17, LC-A23, LC-B8 and LC-C6. Read them in `lifecycle.md`: lines 58 (A17), 77 to 84 (A23), 106 (B8) and 117 (C6).
- **LC-A17.** rollout.md's model announcement (about :249) reads "Design system 2.1.0. One breaking change: `--bg-accent` moved": a breaking re-point shipped as a minor, the failure the skill exists to prevent. Make it 3.0.0. Its step 3 commits with `git commit -am` per step, which splits the upgrade against §6's one-commit rollback: commit once, after step 6.
- **LC-A23**, the smaller items (versioning SKILL.md's "Four edits" was fixed in #50):
  - deprecation.md (about :136) says `@deprecated` is surfaced by `tsc`; it is not. `@typescript-eslint/no-deprecated` reports it: re-read its docs and register the fact.
  - deprecate.py accepts `--removal 2.2.0` for `--since 2.1.0`, but the contract (deprecation.md:29) puts a removal in the next major, X+1.0.0. Refuse it, with a test.
  - MIGRATION_PLAN.md (about :114) says "20px --pad-inline-sm"; `--pad-inline-sm` is 12px.
  - migration SKILL.md (about :71) says "Four separate algorithms" and lists six.
  - reconciliation.md prints durations as "Δ -40px" (cluster_values' report).
  - The reconciliation recommends `$brand: var(--fg-default)` for a brand colour; framework-migrations.md (about :112) says to delete such variables, not re-point them.
  - framework-migrations.md (about :139) says darken() distances are reported; they are canned text.
- **LC-B8**, claims with no gate. The parity claims and the worked-run numbers are gated now (#49, #50; P16 gates the Figma one). Left: migration SKILL.md (about :246) says tokens.css is "`git`-enforced read-only", and nothing enforces it. Gate it (the pre-commit hook or the CI recipe) or say what does.
- **LC-C6.** Its open part is LC-A17, above. LC-B4, the CI bootstrap, is Phase 5's (W9).
- **Files.** design-system-versioning's `references/rollout.md`, `references/deprecation.md` and `scripts/deprecate.py`; design-token-migration's SKILL.md, `references/framework-migrations.md`, `scripts/cluster_values.py` and its MIGRATION_PLAN template (grep for it).
- P17 is S-M.

**Close each PR:** the CHANGELOG under `## 3.4.0 — unreleased`, each item "fixed in 3.4.0" in the inventory with its test, the PR's own row in the plan as `Pk, #N` (`P16, #N`; N the PR's number; a split keeps its open items under a plain `Pk` row, which is what the checker counts), and §9.

## 6. End of session (never skip)

1. Rewrite `docs/HANDOFF.md`: one page, with the state, next steps, blockers and warnings.
2. Update `CLAUDE.md`'s Current State, the execution plan's §9, the inventory, and `dev plans/README.md`'s line for this file.
3. **Rewrite this file** for the session after yours: the next PRs in the same detail as §4 and §5 here.
4. Run `python -B "dev plans/check_execution_plan.py"`.
5. Commit the docs in a PR of their own and merge it once its CI is green.
6. Tell the user what merged, what is open, the token use, and what they need to do, and give them the opening prompt for the next session.
