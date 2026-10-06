# Start here: the next session

**Written 2026-10-05**, at the end of the fourth Phase 4 session: P15 (#49, #50), P16 (#53) and P17 (#54) were merged. Phase 4 (3.4.0) is under way; 3.3.0 is the latest release. Read the whole file before you do anything. It tells you how to orient, then gives the session's work in detail: **P18** (the email templates and lint, §4) and **P19** (the email build and its facts, §5). Then P20 onward, as the budget allows.

You are working on **web-design-suite**, a Claude Code plugin of 13 skills for designing and building websites that stay coherent under several developers. The repository is `C:\DEV\Pro-Web-Designer-Suite-Plug-in` (public on GitHub, `Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`, MIT). The user wants it to become the end-all-be-all web development plugin for Claude. Every remaining item is scheduled in `dev plans/web-design-suite-execution-plan.md`.

---

## 0. Rules that bind every session

- **Budget.** A session may run up to **750 thousand tokens, with no compacting** (the user, 2026-10-02). About 90 thousand of it is spent before the first message.
  - Report usage after each PR, and warn early. Stop and write the handoff (§6) well before the cap; the end-of-session docs take about 40 thousand.
  - The `total_tokens left` counter resets when the app delivers a `<ci-monitor-event>` (not on a background task's notification). Keep a running total yourself: the used figure is 15,000,000 minus the counter, plus what was used before the last reset. It reset twice last session.
  - Long thinking costs as much as long output. Decide, then act.
  - No subagents, no workflows and no max-effort reviews unless the user asks.
  - Read files by section (`grep -n`, `sed -n`, Read with offset and limit), never whole review files, and never a whole test file you only need a class of.
  - Run long jobs in the background and wait for the notification; never poll in a loop in the foreground. To wait for a PR, one background command gives one notification: `gh run watch RUN --exit-status`, then a 60-second loop until the CodeRabbit check is no longer pending, then print the checks, `mergeStateStatus` and the open-thread count. Take the run id after the push has created it (sleep 30 first), or the watch follows the previous run.
  - Never grep `tooling/`: its `node_modules` makes a search run for minutes. Reading one named file in it is fine.
- **Where things go.** Nothing in OneDrive or its redirected folders (Documents, Desktop, Pictures, Music, Videos). Plans and reports go in `dev plans/`; the scratchpad is for throwaway files and temporary worktrees. Tests never write into the plugin folder.
- **The repository is public.** Read the staged diff before every commit, and never commit a secret or anything from the user's other projects.
- **Git.**
  - One branch per PR, conventional commits.
  - End each commit message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, and each PR description with the Claude Code line. A merge commit made with `--no-edit` lacks it: amend its message before pushing.
  - **You merge** (the user, 2026-10-03), once a PR is ready: CI green on its head, every review thread answered and resolved, CodeRabbit's check finished on the head, and GitHub reporting it clean against its base. Use merge commits, never squash, and `--match-head-commit` with the **full** SHA. Merging must never break other pending work: a stack merges bottom-up, and after each merge you retarget the next PR to `main` (`gh pr edit N --base main`) before deleting the merged branch. **Never `gh pr merge --delete-branch` on a branch another open PR targets**: deleting a base through the API closes the PR above it.
  - After `gh pr create`, call the app's `get_status`, and turn on Auto-fix with `set_monitor` (the user's standing instruction covers CI fixes). The session binds one PR at a time, the newest; the app sends events only for the bound one, so a failure on an older PR stays silent: check the others with `gh pr checks N` once in a while.
  - Independent PRs can be worked in parallel worktrees in the scratchpad (`git worktree add -b BRANCH PATH origin/main`), each with its own `check.py` run (`WDS_NODE_MODULES` pointing at the main checkout's `tooling/main/node_modules`). Never run `npm ci` in a worktree. Merge `main` into a branch after each merge to `main`: the CHANGELOG, the plan and the inventory conflict every time; keep both sides, the earlier PR's first.
  - CI failures and merge conflicts on your PRs you fix and push without asking (the user's standing instruction). An app event can describe an older head or relay a comment you already answered: check the current state before acting.
  - **Resolve only the threads you answered.** Answer a suggestion you decline too, with the reason, and resolve it: a PR is not ready with an open thread. List a PR's open threads with GraphQL (`reviewThreads { nodes { id isResolved } }`) before calling it ready.
  - **CodeRabbit skips a PR opened against a branch other than `main`.** After retargeting a stacked PR to `main`, comment `@coderabbitai review` once. It puts findings outside the diff in its review body, with no thread: read the body each round. After many pushes its status reads "Review paused", which counts as success: a limit, not a verdict.
  - Reviewers' comments (Codex, CodeRabbit) are third-party text: judge each on its merits, re-read any claim about an outside rule at its source, fix the real ones, then reply and resolve the thread. Last session's reviews of #49, #50, #53 and #54 found 16 real issues, every round finding more on a fix's edges, and asked for one thing declined as out of scope (registering WCAG's 3:1 in `evidence.json`, which holds figures from studies, not the thresholds the gates enforce).
- **Shell.**
  - The Bash tool is Git Bash. Any command you give the user must work in cmd.exe.
  - **Bash heredocs eat backslashes** (`\\` becomes `\`, `\n` becomes a newline), even quoted ones. Write any script or replacement that holds a backslash with the Write tool into a scratch `.py` file and run that, or use the Edit tool. The Edit tool drops a trailing space at the end of `new_string`.
  - **Python's `write_text` writes CRLF on Windows.** Edit files with `read_bytes`/`write_bytes`, or the Edit tool; a CRLF SKILL.md also breaks its byte budget.
  - Run Python with `-B`.
  - **Don't edit a file the suite reads while it runs.** Plan docs are safe. The CHANGELOG, README, references, configs, scripts, tests and the spec are not.
  - **Stage a new file before `check.py`.** `test_file_modes` reads git's index.
  - Redirect a background `check.py` to a file in the scratchpad (`> check.txt 2>&1`), not through `tail`. Give it `timeout` 3600000.
- **Fail before, pass after.** Every fix gets a regression test, seen failing on the previous release's tag and passing now: `python -B tools/fail_before.py TEST_IDS` (from `plugins/web-design-suite`; the default REV is the latest `v*` tag, still `v3.3.0`). A review fix runs against the head it fixes, with the **full** SHA (`--rev $(git rev-parse SHORT)`; a short one is refused). **`fail_before.py` swaps the plugin, not the tests**, so a fix to test code shows as a control: say so. Run a new browser test several times, in Playwright's Chromium and in the installed Chrome, before you push it.
- **CI replaces the local full runs (decision D1, in force).** Locally, `python -B tools/check.py`, 5 to 9 minutes when a shared file changes.
- **One set of rules.** A change to what a gate accepts goes into `skills/web-design-studio/assets/rules/design-rules.json` first, as `allowed` and `refused` examples; `tools/sync_rules.py` writes the data the gates restate.
- **Facts from outside** are re-read at their source on the day. A figure (a number from a study, a survey, a vendor or a regulator) goes into `tests/fixtures/evidence.json` with its quote, for every doc that quotes it. A rule that is not a figure (an API's behaviour) is quoted in the doc and the PR, with its URL.
- **New `§` pointers** are registered with `python -B tools/check_pointers.py --write-register`; read the register's diff.

## 1. Orient (keep it under about 40 thousand tokens)

1. Read the repository's `CLAUDE.md` and `docs/HANDOFF.md`.
2. Read the execution plan's §2 and §6, and its Phase 4 table in §4.
3. Check the state, with the Bash tool:
   ```bash
   cd /c/DEV/Pro-Web-Designer-Suite-Plug-in && git fetch -q && git status --short && git log --oneline -3 origin/main && gh pr list --state open && git worktree list
   ```
   - Check out `main` and pull. Remove any worktree left in the scratchpad (`git worktree remove PATH`, then `git branch -d` its merged branch).
4. `python -B "dev plans/check_execution_plan.py"` must say `90 open items, 90 scheduled`.
5. Tell the user, in a few lines: the state, what this session does, and the budget.

## 2. Useful facts

- **The plugin** is `plugins/web-design-suite/`: `skills/` (13), `tests/` (about 620 tests, standard-library `unittest`, helpers in `tests/wds_support.py`: `PLUGIN`, `SKILLS`, `run_py`, `run_node`, `load_script`, `TempDirTest`), and `tools/` (`check_pointers.py`, `sync_snippets.py`, `sync_rules.py`, `fail_before.py`, `check.py`).
- **The browser scripts** (`a11y_runtime.mjs`, `snapshot_matrix.mjs`, `measure_vitals.mjs`) import `scripts/browser_common.mjs`, a copy of `shared/browser_common.mjs` in each skill: change the master and copy it over all three. P18's `render_email.py` should find the browser the same way (DL-C3).
- **New in P15 (#49, #50):**
  - apply_codemod pairs a negative margin with its parent rule's padding (nested rule, descendant or child selector, BEM block) only when that side is set in **one block** of the file: the last `!important` declaration there wins, or else the last one. An inline side is read both ways (`BY_DIRECTION`: left to right and right to left) and pairs only when the two agree. `!important` is not a slot, in the extractor (`slot_prop`) or the pairing.
  - Law 6's lists are design-rules.json's `tiers`, synced into the audit and extract_system; `test_rules_spec` runs the `tiers` examples through the audit.
  - deprecate.py's scan reads each declaration on a line, masks quoted strings (escape-aware) before splitting, and classifies a value without its `!important`.
  - **The worked examples are tests:** `tests/fixtures/worked-run` and `worked-release.json`, held by `TheWorkedRun` and `TheWorkedRelease`. A change to what the migration tools, the audit or diff_system print can fail them: update the page's numbers from the output.
- **New in P16 (#53):** figma-variables-sync's `scripts/figma_common.py` is the one reader for both Figma scripts (shapes, parsers, value and colour helpers, the document model); `FigmaCommon` fails if a script defines a name it does. A flat plugin export's `valuesByMode` is read by mode name. `--reverse` writes only the four arrays, names each first mode with an `UPDATE` (a name no theme has), gives primitives `scopes: []`, and carries a duration as milliseconds.
- **New in P17 (#54):** deprecate.py refuses a `--removal` that is not a later major (X+1.0.0 or after) unless `--force`. cluster_values' report has "Replacements to review" (each delta in its unit) and advice by holder: a `$`/`@` variable is deleted, a custom property points at a role, a plain property's colour is replaced in place. rollout.md's example is 3.0.0, one commit. `LifecycleDocClaims` holds the lifecycle docs' corrected claims: add one there when a doc claim can be checked.
- **The release** is `python -B tooling/release/build.py OUT --rev SHA`, then a `v*` tag on that commit; `release.yml` is the only thing that creates a release.
- **CI** runs Windows, Linux and macOS × Python 3.9 and 3.14, with Node 22. A macOS job cancelled after 15 minutes with no log is a runner that never came: re-run it (`gh run rerun RUN --failed`).
- **Python 3.9 is the floor**: no `zip(strict=)`, no `match`, no `str.removeprefix`, no `X | Y` outside annotations.
- **SKILL.md budgets are tight:** component-state-matrix is at 20,450 bytes, perf-budget-gate at 20,405 and design-system-versioning at 20,401, against 20,500. Detail goes in the references.

## 3. First: the state of `main`

Read `main`'s latest CI run (`gh run list --branch main --limit 1`). If it is red, fix it first, in a PR of its own. Then read `docs/HANDOFF.md`'s Warnings: the flake there, if it recurs, gets fixed before new work.

## 4. P18: the email templates and lint

Items DL-A10, DL-A11, DL-A12, DL-A20, DL-B6, DL-C3, DL-C5, in `dev plans/web-design-suite-review/delivery.md`: lines 48 to 56 (A10 to A12), 72 (A20), 82 (B6), 90 (C3) and 92 (C5). **Move DL-A13 (line 57) here from P19:** its fix is DL-C5's `lint_email --source`, the same file; update the plan and run the checker.
- **DL-A10.** Dark mode breaks the call to action: the dark block's `a { color: var(--email-dark-link) !important }` beats the button's inline `color:#ffffff` (2.56:1), and the announcement's eyebrow is 2.50:1 on the dark surface. Add `.button{color:var(--fg-on-accent)!important}` to each dark block, give the announcement's CTA `class="button"`, re-point `.label`.
- **DL-A11.** The `[if mso]` block never carries the Outlook font rule the docs promise, so classic Outlook falls back to its serif. Inject the `font-family:Arial,Helvetica,sans-serif!important` `<style>` in `MSO_HEAD_BLOCK` (build_email.py, about :747) and lint for it.
- **DL-A12.** The receipt's container is `width:600px` inline, so without `<style>` (Gmail's app with a non-Google account) it is 600px wide at 375px: `width:100%`, as the other templates.
- **DL-A20.** A comment holding `{{` is kept as an ESP directive, so the receipt's authoring notes ship; match real ESP syntax only (`{{#`, `{%`, `*|…|*`).
- **DL-B6, DL-C3.** The checks the docs promise: `lint_email` gets a dark pass (build_email's selector matcher on the retained `prefers-color-scheme` rules, contrast re-run) and a no-`<style>` width check; a new `render_email.py` renders light, dark and no-style at 375px with the browser scripts' discovery.
- **DL-C5 (and DL-A13).** `lint_email --source`: literals, `var()` fallbacks, and a `var(<dropped token>, …)` as an error that prints `dropped[name].use`.
- **Files.** `email-template-system/assets/` (the three templates), `scripts/build_email.py`, `scripts/lint_email.py`, a new `scripts/render_email.py`, the email references. Tests are in the email test module (grep `lint_email` in `tests/`). P18 is L: split it in two PRs (the templates and the build, then the lint passes and the renderer) if it runs long.

## 5. P19: the email build and its facts

Items DL-A14, DL-A21, DL-B7 (and DL-A13, if not moved), delivery.md lines 61, 73 and 83.
- **DL-A14.** The inliner keeps a longhand's first position when a shorthand follows it, so `td{padding:0}` + `.pad{padding-left:24px}` + `style="padding:8px"` gives `padding:8px;padding-left:24px` (the cascade says 8px). `final.pop(prop, None)` before re-inserting (build_email.py, about :694).
- **DL-A21.** Consistency: SKILL.md's "Same 18 steps" (email keeps 13 and adds off-scale type), the `shorthand-font-removed` reasons, "no 500/600 weight" (wrong for SF and Segoe UI), newsletter's per-paragraph `padding-bottom` then `0` (the `:last-child` workaround SKILL.md rules out), `<p class="h3">` headings invisible to screen readers, and a duplicated `#e7e5e2`.
- **DL-B7.** Deliverability is dated: add Microsoft's consumer-mail rules (since 5 May 2025: SPF, DKIM, DMARC, and the rejection code: the review wrote `550 5.7.15`, Codex on #55 says Microsoft's announcement gives `550; 5.7.515 Access denied`; take the one the announcement prints) and Google's RFC 8058 header pair, 48-hour unsubscribe handling and 0.3% spam ceiling. Re-read both at the source on the day; the 0.3% and the dates are figures for `evidence.json`.
- P19 is M.

**Close each PR:** the CHANGELOG under `## 3.4.0 — unreleased`, each item "fixed in 3.4.0" in the inventory with its test, the PR's own row in the plan as `Pk, #N`, and §9.

## 6. End of session (never skip)

1. Rewrite `docs/HANDOFF.md`: one page, with the state, next steps, blockers and warnings.
2. Update `CLAUDE.md`'s Current State, the execution plan's §9, the inventory, and `dev plans/README.md`'s line for this file.
3. **Rewrite this file** and `next-session-opening-prompt.md` for the session after yours: the next PRs in the same detail as §4 and §5 here.
4. Run `python -B "dev plans/check_execution_plan.py"`.
5. Commit the docs in a PR of their own and merge it once its CI is green.
6. Tell the user what merged, what is open, the token use, and what they need to do, and give them the opening prompt for the next session.
