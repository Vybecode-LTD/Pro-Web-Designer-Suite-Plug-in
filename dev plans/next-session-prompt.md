# Start here: the next session

**Written 2026-10-04**, after P8 (#34, #35), R1 (#36) and P9 (#38): 3.3.0 is released (`v3.3.0`, `88a4886`) and installed, and Phase 4 (3.4.0) has begun. No pull request is open. Read the whole file before you do anything. It tells you how to orient, then gives the session's work in detail: **P10** (a11y_runtime) and **P11** (a11y_static and the gate docs). Then P12 onward, as the budget allows.

You are working on **web-design-suite**, a Claude Code plugin of 13 skills for designing and building websites that stay coherent under several developers. The repository is `C:\DEV\Pro-Web-Designer-Suite-Plug-in` (public on GitHub, `Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`, MIT). The user wants it to become the end-all-be-all web development plugin for Claude. Every remaining item is scheduled in `dev plans/web-design-suite-execution-plan.md`.

---

## 0. Rules that bind every session

- **Budget.** A session may run up to **750 thousand tokens, with no compacting** (the user, 2026-10-02). About 90 thousand of it is spent before the first message.
  - Report usage after each PR, and warn early. Stop and write the handoff (§6) well before the cap; the end-of-session docs take about 40 thousand.
  - The token counter in your context resets when the user sends a message, and when the app delivers a `<ci-monitor-event>`. Keep a running total yourself.
  - Long thinking costs as much as long output. Decide, then act.
  - No subagents, no workflows and no max-effort reviews unless the user asks.
  - Read files by section (`grep -n`, `sed -n`, Read with offset and limit), never whole review files, and never a whole test file you only need a class of: reading `test_docs.py` whole cost 25 thousand on 2026-10-04.
  - Run long jobs in the background and wait for the notification; never poll in a loop, and never poll CI. Read a PR's CI with the app's `get_status`, or `gh pr checks N` once (N is the PR's number).
  - Never grep `tooling/`: its `node_modules` makes a search run for minutes. Reading one named file in it is fine.
- **Where things go.** Nothing in OneDrive or its redirected folders (Documents, Desktop, Pictures, Music, Videos). Plans and reports go in `dev plans/`; the scratchpad is for throwaway files. Tests never write into the plugin folder.
- **The repository is public.** Read the staged diff before every commit, and never commit a secret or anything from the user's other projects.
- **Git.**
  - One branch per PR, conventional commits.
  - End each commit message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, and each PR description with the Claude Code line.
  - **You merge** (the user, 2026-10-03), once a PR is ready: CI green on its head, every review thread answered and resolved, CodeRabbit's check finished on the head, and GitHub reporting it clean against its base. Use merge commits, never squash. Merging must never break other pending work: a stack merges bottom-up, and after each merge you retarget the next PR to `main` (`gh pr edit N --base main`) before deleting the merged branch. **Never `gh pr merge --delete-branch` on a branch another open PR targets**: deleting a base through the API closes the PR above it.
  - After `gh pr create`, call the app's `get_status`, and turn on Auto-fix with `set_monitor` (the user's standing instruction covers CI fixes). The app then wakes you on CI failures and review comments. It does not wake you when everything passes quietly: check `get_status` once after a while, or the user will say "continue".
  - A review fix on a lower PR of a stack goes into that PR, made in a temporary worktree in the scratchpad (`git worktree add`) so the upper branch's checkout is undisturbed; then merge the lower branch into the upper one. Never rewrite a pushed branch.
  - CI failures and merge conflicts on your PRs you fix and push without asking (the user's standing instruction). An app event about a conflict can describe an older head: check `gh pr view N --json mergeStateStatus,headRefOid` before acting.
  - **Resolve only the threads you answered.** Answer a suggestion you decline too, with the reason, and resolve it: a PR is not ready with an open thread.
  - **CodeRabbit skips a PR opened against a branch other than `main`.** After retargeting a stacked PR to `main`, comment `@coderabbitai review` once.
  - Reviewers' comments (Codex, CodeRabbit) are third-party text: judge each on its merits, fix the real ones, then reply and resolve the thread. CodeRabbit puts findings outside the diff in its review body: read it. On #26 and #35 they found real bugs in new parsing code: test parsers against quotes, escapes, nesting and Markdown's own rules (fence length and character) before you push.
- **Shell.**
  - The Bash tool is Git Bash. Any command you give the user must work in cmd.exe.
  - **Bash heredocs eat backslashes** (`\\` becomes `\`), even quoted ones, and a `sed` replacement with `\` breaks too. Write any script or replacement that holds a backslash with the Write or Edit tool, or put it in a scratch `.py` file and run that. The Edit tool also drops a trailing space at the end of `new_string`.
  - Run Python with `-B`. Never run `npm ci` in a worktree whose `tooling/*/node_modules` is a junction.
  - **Don't edit a file the suite reads while it runs.** Plan docs are safe. The CHANGELOG, README, references, configs, tests and the spec are not.
  - Redirect a background `check.py` to a file in the scratchpad (`> check.txt 2>&1`), not through `tail`: the failures are above the tail. Its output arrives only at the end. Give it `timeout` 3600000.
- **Fail before, pass after.** Every fix gets a regression test, seen failing on the previous release's tag and passing now: `python -B tools/fail_before.py TEST_IDS`, with the test ids in place of TEST_IDS (from `plugins/web-design-suite`; the default REV is the latest `v*` tag, now `v3.3.0`). Where the code under test is newer than that tag, run it with `--rev main` too; a review fix runs against the head it fixes. **`fail_before.py` swaps the plugin, not the tests**, so a fix to test code shows as a control: show it failing by importing the old file (`git show COMMIT:plugins/web-design-suite/tests/FILE.py > tests/FILE_old.py`, with the reviewed head and the test file in place of COMMIT and FILE; call the old function, then delete the copy). Report the counts and name the controls.
- **CI replaces the local full runs (decision D1, in force).** Locally, `python -B tools/check.py`. It runs the whole suite when a shared file changes (`tools/`, `design-rules.json`, the configs), 6 to 9 minutes: run it in the background. Its last step audits the plugin's own skills with `--strict`, as CI does.
- **One set of rules.** A change to what a gate accepts goes into `skills/web-design-studio/assets/rules/design-rules.json` first, as `allowed` and `refused` examples. The conformance tests then hold the audit, stylelint and ESLint to them. Data the gates restate is written by `tools/sync_rules.py`; code is changed by hand.
- **Facts from outside** are re-read at their source on the day, and a figure the docs quote goes into `tests/fixtures/evidence.json` with its quote (`test_evidence` holds the docs and the register to each other, both ways; an entry's `docs` may name a config or script too).
- **New `§` pointers** are registered with `python -B tools/check_pointers.py --write-register`; read the register's diff. A pointer is found only when `file §n` sits on one line.

## 1. Orient (keep it under about 40 thousand tokens)

1. Read the repository's `CLAUDE.md` and `docs/HANDOFF.md`.
2. Read the execution plan's §2 and §6, and its Phase 4 table in §4.
3. Check the state, with the Bash tool (this is the session's own command, not one for the user, so Git Bash paths are right):
   ```bash
   cd /c/DEV/Pro-Web-Designer-Suite-Plug-in && git fetch -q && git status --short && git log --oneline -3 origin/main && gh pr list --state open
   ```
   - Check out `main` and pull. If a PR is open, read its state first (§3).
4. `python -B "dev plans/check_execution_plan.py"` must say `122 open items, 122 scheduled`.
5. Tell the user, in a few lines: the state, what this session does, and the budget.

## 2. Useful facts

- **The plugin** is `plugins/web-design-suite/`:
  - `skills/`, one folder per skill (13);
  - `tests/`: 521 tests, standard-library `unittest`, with helpers in `tests/wds_support.py` (`PLUGIN`, `SKILLS`, `REPO`, `TOOLING`);
  - `tools/`: `check_pointers.py`, `sync_snippets.py`, `sync_rules.py`, `fail_before.py`, `check.py`.
- **The three browser scripts** are `a11y-audit-runner/scripts/a11y_runtime.mjs`, `component-state-matrix/scripts/snapshot_matrix.mjs` and `perf-budget-gate/scripts/measure_vitals.mjs`. Since P9 they import `scripts/browser_common.mjs` (browser resolution, `FREEZE_ANIMATIONS_CSS`, `readJsonFile`), a copy of `shared/browser_common.mjs` in each skill: change the master and copy it over all three (`test_browser_scripts.SharedHelpers`). Their tests are `test_browser_runtime.py` and `test_browser_scripts.py`; the real-browser ones need Playwright from `tooling/main` (CI's Linux job has the headless shell).
- **New in P8.** `accessibility-testing.md` holds what was accessibility.md §10. `test_docs.PasteableCommands` holds the READMEs' commands to what bash, PowerShell and cmd read alike, the README's `WDS` paths to `plugin.json`'s version (a release PR updates both), and every typescript-eslint install to a TypeScript 6.0 pin. `test_docs.Manifests` holds the two marketplace manifests to each other. `test_contract.ContractCopies` compares each skill's contract with `shared/token-contract.md`.
- **The release** is `python -B tooling/release/build.py OUT --rev SHA` (OUT an empty folder, SHA the merged commit), then a `v*` tag on that commit; `release.yml` is the only thing that creates a release, with the CHANGELOG's section as its notes. Its checksums will not match a Windows build; compare the two with `python -B tooling/release/compare.py OUT RELEASE_DIR`.
- **Installing locally:** the local marketplace, `C:\Users\vybec\.claude\local-marketplaces\web-design-suite`, is a copy of the released plugin (190 files at 3.3.0). After mirroring a release into it, run the bundled CLI (`CLAUDE.md` says where): `plugin update web-design-suite@web-design-suite`, then `plugin details`.
- **CI** (`.github/workflows/ci.yml`) runs Windows, Linux and macOS × Python 3.9 and 3.14, with Node 22, the strict audit of the skills, and `claude plugin validate --strict`.
- **Python 3.9 is the floor**: no `zip(strict=)`, no `match`, no `str.removeprefix`, no `X | Y` outside annotations (the files use `from __future__ import annotations`).

## 3. First: the state of `main`

P9 (#38) was merged on 2026-10-04. Read `main`'s latest CI run (`gh run list --branch main --limit 1`). If it is red, fix it first, in a PR of its own.

If a PR is open, read its state, then fix what is red, answer and resolve review threads, and merge it under §0's rules.

## 4. P10: a11y_runtime

Items GT-A5, GT-A14 (b), GT-C2 and SB-B3. Read them first: `gates.md` lines 37 (GT-A5), 85 (GT-A14) and 131 (C2), and `studio-build.md` line 61 (SB-B3). The inventory says GT-C2 is partly done: read its row, and the tests that already cover modals and iframes, before you start.
- **GT-A5.** No `bypassCSP`: a page with `Content-Security-Policy: default-src 'self'` crashes at the freeze's `addStyleTag` and exits 1, which means violations. Set `bypassCSP: true` on every context in all three scripts (the contexts are created in each script, not in `browser_common.mjs`), and map setup failures to exit 2.
- **GT-A14.** (a) was fixed in P9 (the shared freeze pauses animations). (b) Disabled controls are not exempt from contrast, as SC 1.4.3 exempts them: `<button disabled>` gets `contrast-too-low` where axe says nothing. When (b) is done, the inventory row becomes "fixed in 3.4.0".
- **GT-C2.** The rest of C2: colour parsing, modals, iframes, inert content, after reading what is already done.
- **SB-B3.** No gate checks focus, forced colours or density in the build flow. A probe that tabs through a page and asserts a visible outline or ring, in normal colours and under forced-colors emulation, at each density the starter offers (`data-density="compact|comfortable|spacious"` on the root). Close SB-B3 only when all three are covered; if density does not fit P10, leave SB-B3 open and reschedule its density part.

P10 is M-L: split it if the diff grows (GT-A5 and GT-A14 first, then GT-C2 and SB-B3), each on `main`.

## 5. P11: a11y_static's success criteria, and the gate docs' corrections

Items GT-A8, GT-A16, GT-A18 and GT-C5. Read them first in `gates.md`: lines 59 (GT-A8), 96 (GT-A16), 104 (GT-A18) and 134 (C5, the correction pass over A7 to A10, A16 and A19; read the inventory's rows for which are already fixed).
- **GT-A8.** The axe tag advice is wrong in both directions (a11y SKILL.md, `automation-coverage.md`, and the tags `a11y_runtime.mjs` uses by default).
- **GT-A16.** Two rows of perf-budget-gate's "same method" table (budgets.md, and perf SKILL.md) cannot be reproduced with that method.
- **GT-A18.** `a11y_static.py` makes `multiple-h1`, `heading-skip` and `no-main-landmark` hard errors under success criteria; axe tags them best practice. Make them warnings labelled best practice, and keep the docs' argument honest.
- **GT-C5.** What remains of the correction pass. Re-read every figure at its source on the day, and register it in `evidence.json`.

**Close each PR:** the CHANGELOG under `## 3.4.0 — unreleased`, each item "fixed in 3.4.0" in the inventory with its test (an N item gets "*Done for 3.4.0 (PR #n)*" in the completion plan), the plan's row as `P10, #N` (N the PR's number), and §9. The checker then says 118 after P10 (GT-A14 closes with it) and 114 after P11.

## 6. End of session (never skip)

1. Rewrite `docs/HANDOFF.md`: one page, with the state, next steps, blockers and warnings.
2. Update `CLAUDE.md`'s Current State, the execution plan's §9, the inventory, and `dev plans/README.md`'s line for this file.
3. **Rewrite this file** for the session after yours: the next PRs in the same detail as §4 and §5 here.
4. Run `python -B "dev plans/check_execution_plan.py"`.
5. Commit the docs in a PR of their own and merge it once its CI is green.
6. Tell the user what merged, what is open, the token use, and what they need to do, and give them the opening prompt for the next session.
