# Start here: the next session

**Written 2026-10-05**, after P10 (#39, #40), P11 (#41) and P12 part 1 (#42). Phase 4 (3.4.0) is under way; 3.3.0 is the latest release. Read the whole file before you do anything. It tells you how to orient, then gives the session's work in detail: **P12 part 2** (the matrix model and its baseline lifecycle) and **P13** (measure_vitals). Then P14 onward, as the budget allows.

You are working on **web-design-suite**, a Claude Code plugin of 13 skills for designing and building websites that stay coherent under several developers. The repository is `C:\DEV\Pro-Web-Designer-Suite-Plug-in` (public on GitHub, `Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`, MIT). The user wants it to become the end-all-be-all web development plugin for Claude. Every remaining item is scheduled in `dev plans/web-design-suite-execution-plan.md`.

---

## 0. Rules that bind every session

- **Budget.** A session may run up to **750 thousand tokens, with no compacting** (the user, 2026-10-02). About 90 thousand of it is spent before the first message.
  - Report usage after each PR, and warn early. Stop and write the handoff (§6) well before the cap; the end-of-session docs take about 40 thousand.
  - The token counter in your context resets when the user sends a message, and when the app delivers a `<ci-monitor-event>`. Keep a running total yourself.
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
  - **You merge** (the user, 2026-10-03), once a PR is ready: CI green on its head, every review thread answered and resolved, CodeRabbit's check finished on the head, and GitHub reporting it clean against its base. Use merge commits, never squash. Merging must never break other pending work: a stack merges bottom-up, and after each merge you retarget the next PR to `main` (`gh pr edit N --base main`) before deleting the merged branch. **Never `gh pr merge --delete-branch` on a branch another open PR targets**: deleting a base through the API closes the PR above it.
  - After `gh pr create`, call the app's `get_status`, and turn on Auto-fix with `set_monitor` (the user's standing instruction covers CI fixes). The session binds one PR at a time; `get_status` lists the others under `otherBoundPrs`. The app wakes you on CI failures and review comments, not when everything passes quietly: check once after a while, or the user will say "continue".
  - A review fix on a lower PR of a stack goes into that PR, made in a temporary worktree in the scratchpad (`git worktree add`) so the upper branch's checkout is undisturbed; run its tests there with `WDS_NODE_MODULES` pointing at the main checkout's `tooling/main/node_modules`. Then merge the lower branch into each upper one, bottom-up, and push each. Never rewrite a pushed branch.
  - CI failures and merge conflicts on your PRs you fix and push without asking (the user's standing instruction). An app event about a conflict can describe an older head: check `gh pr view N --json mergeStateStatus,headRefOid` before acting.
  - **Resolve only the threads you answered.** Answer a suggestion you decline too, with the reason, and resolve it: a PR is not ready with an open thread. List a PR's open threads with GraphQL (`reviewThreads { nodes { id isResolved } }`) before calling it ready: new ones arrive after the event that woke you.
  - **CodeRabbit skips a PR opened against a branch other than `main`.** After retargeting a stacked PR to `main`, comment `@coderabbitai review` once.
  - Reviewers' comments (Codex, CodeRabbit) are third-party text: judge each on its merits, fix the real ones, then reply and resolve the thread. CodeRabbit puts findings outside the diff in its review body: read it. On 2026-10-05 they found 17 real issues in four PRs, and CodeRabbit reviews every push again: expect two or three rounds per PR, about 15 thousand tokens a round.
- **Shell.**
  - The Bash tool is Git Bash. Any command you give the user must work in cmd.exe.
  - **Bash heredocs eat backslashes** (`\\` becomes `\`, `\n` becomes a newline), even quoted ones; it bit four times this session. Write any script or replacement that holds a backslash with the Write tool into a scratch `.py` file and run that, or use the Edit tool. The Edit tool drops a trailing space at the end of `new_string`.
  - Run Python with `-B`. Never run `npm ci` in a worktree whose `tooling/*/node_modules` is a junction.
  - **Don't edit a file the suite reads while it runs.** Plan docs are safe. The CHANGELOG, README, references, configs, tests and the spec are not.
  - Redirect a background `check.py` to a file in the scratchpad (`> check.txt 2>&1`), not through `tail`: the failures are above the tail. Its output arrives only at the end. Give it `timeout` 3600000.
- **Fail before, pass after.** Every fix gets a regression test, seen failing on the previous release's tag and passing now: `python -B tools/fail_before.py TEST_IDS`, with the test ids in place of TEST_IDS (from `plugins/web-design-suite`; the default REV is the latest `v*` tag, still `v3.3.0`). A review fix runs against the head it fixes (`--rev SHA`). **`fail_before.py` swaps the plugin, not the tests**, so a fix to test code shows as a control: say so. Run a new browser test several times before you push it: CI's runners are slower, and a guard that races the page fails there first.
- **CI replaces the local full runs (decision D1, in force).** Locally, `python -B tools/check.py`. It runs the whole suite when a shared file changes (`tools/`, `design-rules.json`, the configs), 6 to 9 minutes: run it in the background. Its last step audits the plugin's own skills with `--strict`, as CI does.
- **One set of rules.** A change to what a gate accepts goes into `skills/web-design-studio/assets/rules/design-rules.json` first, as `allowed` and `refused` examples. The conformance tests then hold the audit, stylelint and ESLint to them. Data the gates restate is written by `tools/sync_rules.py`; code is changed by hand.
- **Facts from outside** are re-read at their source on the day, and a figure the docs quote goes into `tests/fixtures/evidence.json` with its quote (`test_evidence` holds the docs and the register to each other, both ways).
- **New `§` pointers** are registered with `python -B tools/check_pointers.py --write-register`; read the register's diff. A pointer is found only when `file §n` sits on one line.

## 1. Orient (keep it under about 40 thousand tokens)

1. Read the repository's `CLAUDE.md` and `docs/HANDOFF.md`.
2. Read the execution plan's §2 and §6, and its Phase 4 table in §4.
3. Check the state, with the Bash tool (this is the session's own command, not one for the user, so Git Bash paths are right):
   ```bash
   cd /c/DEV/Pro-Web-Designer-Suite-Plug-in && git fetch -q && git status --short && git log --oneline -3 origin/main && gh pr list --state open
   ```
   - Check out `main` and pull. If a PR is open, read its state first (§3).
4. `python -B "dev plans/check_execution_plan.py"` must say `111 open items, 111 scheduled`.
5. Tell the user, in a few lines: the state, what this session does, and the budget.

## 2. Useful facts

- **The plugin** is `plugins/web-design-suite/`:
  - `skills/`, one folder per skill (13);
  - `tests/`: 550 tests, standard-library `unittest`, with helpers in `tests/wds_support.py` (`PLUGIN`, `SKILLS`, `REPO`, `TOOLING`);
  - `tools/`: `check_pointers.py`, `sync_snippets.py`, `sync_rules.py`, `fail_before.py`, `check.py`.
- **The three browser scripts** are `a11y-audit-runner/scripts/a11y_runtime.mjs`, `component-state-matrix/scripts/snapshot_matrix.mjs` and `perf-budget-gate/scripts/measure_vitals.mjs`. They import `scripts/browser_common.mjs`, a copy of `shared/browser_common.mjs` in each skill: change the master and copy it over all three (`test_browser_scripts.SharedHelpers`). Their tests are `test_browser_runtime.py` and `test_browser_scripts.py`; the real-browser ones need Playwright from `tooling/main`.
- **New in P10 to P12:**
  - a11y_runtime and snapshot_matrix bypass a page's CSP; measure_vitals deliberately does not (`test_browser_scripts.ContextOptions`). A crash in any of the three exits 2.
  - **Branded Chrome is not the headless shell.** It wraps Tab from the last stop to the first inside the page, where the shell leaves to the document. CI's Windows and macOS jobs run an installed Chrome; Linux runs the shell. A tab-order test that matters runs in both (`test_a_page_with_one_tab_stop_is_not_a_trap` uses `installed_browsers()`).
  - `--only` narrows a proof sheet's cells; on a page it is refused. The runtime tests use `only(...)`, which expands to `--skip` for the other checks.
  - a11y_runtime measures focus at each `data-density` the page's stylesheets name (`--densities`), turning the outermost marker.
  - Best-practice findings (axe's and a11y_static's outline and landmark checks) are warnings labelled `best practice`; they never fail a run without `--strict`.
  - generate_matrix takes `custom_states` and `a+b` combinations; the focus-visible cell carries `focus-visible focus focus-within`.
- **The release** is `python -B tooling/release/build.py OUT --rev SHA` (OUT an empty folder, SHA the merged commit), then a `v*` tag on that commit; `release.yml` is the only thing that creates a release, with the CHANGELOG's section as its notes. Compare a local build with the release with `python -B tooling/release/compare.py OUT RELEASE_DIR`.
- **Installing locally:** the local marketplace, `C:\Users\vybec\.claude\local-marketplaces\web-design-suite`, is a copy of the released plugin. After mirroring a release into it, run the bundled CLI (`CLAUDE.md` says where): `plugin update web-design-suite@web-design-suite`, then `plugin details`.
- **CI** (`.github/workflows/ci.yml`) runs Windows, Linux and macOS × Python 3.9 and 3.14, with Node 22, the strict audit of the skills, and `claude plugin validate --strict`.
- **Python 3.9 is the floor**: no `zip(strict=)`, no `match`, no `str.removeprefix`, no `X | Y` outside annotations.

## 3. First: the state of `main`

#39 to #42 were merged on 2026-10-05, bottom-up; `main` is at `a88d6a6`. Read `main`'s latest CI run (`gh run list --branch main --limit 1`). If it is red, fix it first, in a PR of its own.

If a PR is open, read its state, then fix what is red, answer and resolve review threads, and merge it under §0's rules.

## 4. P12 part 2: the matrix model and its baseline lifecycle

Items GT-B7 and GT-B8. Read them first: `gates.md` lines 125 (B7) and 126 (B8). Custom states and combinations (B7's first part) were done in P12 part 1 (#42); what is left:
- **GT-B7.** RTL: fixtures are inner HTML only, so nothing sets `dir` (state-coverage.md lists RTL). Add a per-fixture `dir`, or a `dirs` axis in the manifest, rendered on the cell's stage. A forced-colors snapshot pass: `snapshot_matrix.mjs --forced-colors` shoots every cell under `forcedColors: 'active'` with its own baselines. States that need interaction (an open select, a tooltip): decide whether a custom state with the right attributes covers them, and document what does not.
- **GT-B8.** Baselines are recorded locally (Windows fonts) and compared on Linux CI. Add a `workflow_dispatch` recipe that records them in the CI container (visual-regression.md), and Git LFS by default above a set component count: the pruned sheet gives 108 cells per component, so 19 components pass the 2,000-baseline limit (visual-regression.md:181-183). Re-read any GitHub or LFS limit at its source and register it.

## 5. P13: measure_vitals

Items GT-A6, GT-A17, GT-C11 and GT-B5. Read them first in `gates.md`: lines 39 (A6), 102 (A17), 123 (B5) and 152 (C11).
- **GT-A6.** CDP throttling is per request, so the presets are not Lighthouse's, and TTFB never sees the emulated latency (`--throttle slow4g` reports a median TTFB of 5 ms). Document that, add a `lighthouse` preset (562.5 ms latency, 1.44 Mbps, which is Lighthouse's DevTools equivalent of 150 ms RTT at 1.6 Mbps), and take TTFB from the CDP `Network.responseReceived` timing, or drop it while emulating. Re-read Lighthouse's throttling constants at their source and register them.
- **GT-A17.** `--interact` adds the interaction's own handler to TBT (0 → 107 ms on a slow page, with INP 168 ms): read TBT before the click. The TBT window has no TTI bound either.
- **GT-C11.** Also `--interact-at MS`, to click during hydration (diagnosis.md §8 names hydration as the biggest INP source).
- **GT-B5.** `crux_check.py`: the field p75 against 1.5× the lab median (perf SKILL.md), with the CrUX API key from an environment variable, never an argument. Tests use a recorded response, never the network.

P13 is M. Split it if the diff grows (A6 and A17 first, then C11 and B5).

**Close each PR:** the CHANGELOG under `## 3.4.0 — unreleased`, each item "fixed in 3.4.0" in the inventory with its test (an N item gets "*Done for 3.4.0 (PR #n)*" in the completion plan), the plan's row as `P13, #N` (N the PR's number), and §9.

## 6. End of session (never skip)

1. Rewrite `docs/HANDOFF.md`: one page, with the state, next steps, blockers and warnings.
2. Update `CLAUDE.md`'s Current State, the execution plan's §9, the inventory, and `dev plans/README.md`'s line for this file.
3. **Rewrite this file** for the session after yours: the next PRs in the same detail as §4 and §5 here.
4. Run `python -B "dev plans/check_execution_plan.py"`.
5. Commit the docs in a PR of their own and merge it once its CI is green.
6. Tell the user what merged, what is open, the token use, and what they need to do, and give them the opening prompt for the next session.
