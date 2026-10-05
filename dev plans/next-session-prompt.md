# Start here: the next session

**Written 2026-10-05**, after P12 part 2 (#44) and P13 (#45, #46). Phase 4 (3.4.0) is under way; 3.3.0 is the latest release. Read the whole file before you do anything. It tells you how to orient, then gives the session's work in detail: **P14** (diff_system's classification) and **P15** (the migration tools). Then P16 onward, as the budget allows.

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
  - Reviewers' comments (Codex, CodeRabbit) are third-party text: judge each on its merits, re-read any claim about an outside rule at its source, fix the real ones, then reply and resolve the thread. CodeRabbit puts findings outside the diff in its review body: read it. On 2026-10-05 the second session's reviews found 17 real issues and 1 wrong one (CodeRabbit claimed a `workflow_dispatch` workflow must run once on the default branch first; GitHub's docs say no such thing). Codex reviews again (it had run out of credit on #44).
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
4. `python -B "dev plans/check_execution_plan.py"` must say `105 open items, 105 scheduled`.
5. Tell the user, in a few lines: the state, what this session does, and the budget.

## 2. Useful facts

- **The plugin** is `plugins/web-design-suite/`:
  - `skills/`, one folder per skill (13);
  - `tests/`: 572 tests, standard-library `unittest`, with helpers in `tests/wds_support.py` (`PLUGIN`, `SKILLS`, `REPO`, `TOOLING`, `run_py`, `run_node`, `TempDirTest`);
  - `tools/`: `check_pointers.py`, `sync_snippets.py`, `sync_rules.py`, `fail_before.py`, `check.py`.
- **The three browser scripts** are `a11y-audit-runner/scripts/a11y_runtime.mjs`, `component-state-matrix/scripts/snapshot_matrix.mjs` and `perf-budget-gate/scripts/measure_vitals.mjs`. They import `scripts/browser_common.mjs`, a copy of `shared/browser_common.mjs` in each skill: change the master and copy it over all three (`test_browser_scripts.SharedHelpers`). Their tests are `test_browser_runtime.py` and `test_browser_scripts.py`; the real-browser ones need Playwright from `tooling/main`.
- **New in P12 part 2 and P13:**
  - generate_matrix: a content fixture may be `{"html", "dir", "lang"}`, set on the cell's stage; the summary prints the baseline count past 1,000 cells and points to Git LFS past 2,000.
  - `snapshot_matrix.mjs --forced-colors` shoots under `forced-colors: active` into `forced-colors/` folders inside `--baselines` and `--out`; only focus-visible is held to differ from default there (Chromium's computed styles follow forced colours: `box-shadow` becomes `none`).
  - measure_vitals' default throttle is `lighthouse` (562.5 ms per request, 1.44 Mbps, 4× CPU); `slow4g` and `fast4g` are 3.3.0's lighter presets. TTFB is CDP's `receiveHeadersEnd`. TBT leaves out the interaction's own task and ends at TTI, whose network-quiet test reads every GET from CDP, unfinished ones included; the long-task totals keep every task. `--interact-at MS` clicks by the page's own `performance.timeOrigin`.
  - `perf-budget-gate/scripts/crux_check.py` holds the CrUX p75 against a `measure_vitals --report` file. The key is `CRUX_API_KEY` only; `CRUX_API_URL` points it elsewhere, which `test_crux_check` uses for a local stand-in server.
  - `test_browser_runtime.VitalsMeasures` serves its pages from a `ThreadingHTTPServer` in a thread; `/hang` answers after 9 s.
- **The release** is `python -B tooling/release/build.py OUT --rev SHA` (OUT an empty folder, SHA the merged commit), then a `v*` tag on that commit; `release.yml` is the only thing that creates a release, with the CHANGELOG's section as its notes. Compare a local build with the release with `python -B tooling/release/compare.py OUT RELEASE_DIR`.
- **Installing locally:** the local marketplace, `C:\Users\vybec\.claude\local-marketplaces\web-design-suite`, is a copy of the released plugin. After mirroring a release into it, run the bundled CLI (`CLAUDE.md` says where): `plugin update web-design-suite@web-design-suite`, then `plugin details`.
- **CI** (`.github/workflows/ci.yml`) runs Windows, Linux and macOS × Python 3.9 and 3.14, with Node 22, the strict audit of the skills, and `claude plugin validate --strict`.
- **Python 3.9 is the floor**: no `zip(strict=)`, no `match`, no `str.removeprefix`, no `X | Y` outside annotations. `uv run --no-project --python 3.9 python -B -m unittest test_x` checks one module there.
- **SKILL.md budgets are tight:** component-state-matrix is at 20,450 bytes and perf-budget-gate at 20,405, against 20,500. Detail goes in the references.

## 3. First: the state of `main`

#44 to #46 were merged on 2026-10-05, bottom-up, then this session's docs PR; `main` was at `a47eba5` before it. Read `main`'s latest CI run (`gh run list --branch main --limit 1`). If it is red, fix it first, in a PR of its own.

If a PR is open, read its state, then fix what is red, answer and resolve review threads, and merge it under §0's rules.

## 4. P14: diff_system's classification

Items LC-A8, LC-A9 and LC-C5. Read them first in `dev plans/web-design-suite-review/lifecycle.md`: lines 30 (A8), 32 to 35 (A9) and 116 (C5). The review's repro fixtures are in `dev plans/web-design-suite-review/fixtures/lifecycle/fx/ver` (`v1` to `v4`, each with its `system.json`).
- **LC-A8.** change-classification.md:165 and 203-204 say a density-scale change, a reduced-motion change and a root-element change are "major · auto-detect yes". `fx/ver` v1 to v3 changes only `--density: 0.875→0.8`, reduced-motion `1ms→0.01ms` and `<div>`→`<section>`, and `diff_system.py` reports **`RECOMMENDED BUMP PATCH … because nothing changed`**, although system.json records all three (`density/compact 21px→19.2px`, `overrides`, `element`). Compare the density environments, the condition overrides and `element`.
- **LC-A9.** `theme-override-added` is classified minor, but it changes rendering in that theme, which is major by the file's own §11 Q2. v1 to v4: a new dark override takes `--fg-muted` from 3.27:1 to 1.83:1 ("CROSSED 3.0:1 DOWNWARD"), and the tool says MINOR and the gate PASS. "Add a part: minor" contradicts §11 Q3 (a DOM change is major). And a CSS Modules class rename, which the doc calls a patch, is reported as `part-removed` (major) with a FAIL (`Card.module.css`, `card__title`→`card__heading`).
- **LC-C5.** Cover density, conditions, `element` and CSS Modules; record `@layer` in system.json (that is design-system-docs' `extract_system.py`, schema `design-system-docs/system/1`: a schema change reaches the docs skill, so keep it additive); make an added override major when an existing value moves.
- **Files.** `design-system-versioning/scripts/diff_system.py` (2,197 lines: `Snapshot` at about :672, the `Kind` table from :909, `contrast_deltas` at :1229), `references/change-classification.md` (rows :72-78, :161-168, :198-206; §11 from :299, the kind table at :327), and `design-system-docs/scripts/extract_system.py`.
- P14 is M. Write the tests from `fx/ver` first (copied into the test as small fixtures; tests never read `dev plans/`).

## 5. P15: the migration tools

Items LC-A11, LC-A12, LC-A14, LC-A19, LC-C4 and LC-C12. Read them in `lifecycle.md`: lines 41 (A11), 43 (A12), 47 (A14), 66 (A19), 115 (C4) and 123 (C12). C4's A2, A5 and A10 were fixed in 3.1.0; its open part is A11, A12 and A14.
- **LC-A11.** A negative cancel must point at the same token as the padding it cancels (extraction-and-clustering.md:352-357, SKILL.md:117), but `padding:16px` becomes `var(--pad-well)` and `margin:-16px` becomes `calc(var(--gap-grouped) * -1)` (`fx/mig2`).
- **LC-A12.** "15px becomes 16, text does not shrink" (SKILL.md:77, extraction-and-clustering.md:246-248), but when 14px is more frequent the tool maps 15px to 14px, with the note "snapped UP to 14px" and a delta of -1.0. Break ties upward for type, or document that frequency comes first, and make the note true.
- **LC-A14.** deprecate.py's codemod refuses a colour rename beside a `font-weight` ("`font: var(--fg-faint)` would reset font-weight"): apply the font guard only when the replacement starts with `font:`. And `scan` labels single-line rules `[manual]`, so its count depends on whitespace (`fx/dep/client`: "0 codemod · 9 manual", where the codemod rewrites 7).
- **LC-A19.** audit_design's L6 and extract_system disagree on `var(--space-0)` and `var(--shadow-none)` in a `.module.css` file (`fx/l6`): move the prefix and exception lists into one shared module, with a parity test.
- **LC-C12.** Ship the 8-file migration fixture and the five-edit release as test fixtures, and have CI regenerate the SKILL.md numbers from them.
- P15 is L: split it (A11, A12 and A19 first; then A14, C4 and C12).

**Close each PR:** the CHANGELOG under `## 3.4.0 — unreleased`, each item "fixed in 3.4.0" in the inventory with its test, the PR's own row in the plan as `Pk, #N` (`P14, #N` for P14, `P15 part 1, #N` for P15's first half; N the PR's number; a split keeps its open items under a plain `Pk` row, which is what the checker counts), and §9.

## 6. End of session (never skip)

1. Rewrite `docs/HANDOFF.md`: one page, with the state, next steps, blockers and warnings.
2. Update `CLAUDE.md`'s Current State, the execution plan's §9, the inventory, and `dev plans/README.md`'s line for this file.
3. **Rewrite this file** for the session after yours: the next PRs in the same detail as §4 and §5 here.
4. Run `python -B "dev plans/check_execution_plan.py"`.
5. Commit the docs in a PR of their own and merge it once its CI is green.
6. Tell the user what merged, what is open, the token use, and what they need to do, and give them the opening prompt for the next session.
