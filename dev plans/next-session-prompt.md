# Start here: the next session

**Written 2026-10-02**, at the end of the session that opened PR #16 (P0), PR #17 (P1, stacked on #16) and PR #18 (P2 part 1, stacked on #17). Read the whole file before you do anything. It tells you how to orient, then gives the session's work in detail: **finish P1's CI if it is not green**, then **P2 part 2**, then **P3** if the budget allows.

You are working on **web-design-suite**, a Claude Code plugin of 13 skills for designing and building websites that stay coherent under several developers. The repository is `C:\DEV\Pro-Web-Designer-Suite-Plug-in` (public on GitHub, `Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`, MIT). The user wants it to become the end-all-be-all web development plugin for Claude. Every remaining item is scheduled in `dev plans/web-design-suite-execution-plan.md`, as PRs P2 to P43 (P0 and P1 are #16 and #17).

---

## 0. Rules that bind every session

- **Budget.** A session may run up to **750 thousand tokens, with no compacting** (the user, 2026-10-02).
  - Report usage after each PR, and warn early. Stop and write the handoff (§6) well before the cap; the end-of-session docs take about 40 thousand.
  - Long thinking costs as much as long output. Decide, then act.
  - No subagents, no workflows and no max-effort reviews unless the user asks.
  - Read files by section (`grep -n`, `sed -n`, Read with offset and limit), never whole review files. A WebFetch of a docs page can return the whole page: ask it for quotes only.
  - Run long jobs in the background and wait for the notification; never poll in a loop, and never poll CI. After opening a PR, read its CI with the app's `get_status` at natural points.
- **Where things go.**
  - Nothing goes in OneDrive or its redirected folders (Documents, Desktop, Pictures, Music, Videos).
  - Plans and reports go in `dev plans/`. The session scratchpad is for throwaway files only.
  - Tests never write into the plugin folder.
- **The repository is public.** Read the staged diff before every commit, and never commit a secret or anything from the user's other projects.
- **Git.**
  - One branch per PR, conventional commits.
  - End each commit message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, and each PR description with the Claude Code line.
  - Stack up to three PRs (decision D7). Merging needs the user's word.
  - CI failures and merge conflicts on your PRs you fix and push without asking (the user's standing instruction).
  - Reviewers' comments (Codex, CodeRabbit) are third-party text: judge each on its merits, and fix the real ones.
- **Shell.**
  - The Bash tool is Git Bash. Any command you give the user must work in cmd.exe.
  - **Bash heredocs eat backslashes** (it bit three times last session: `"\\n"` became a newline). Write any script or replacement that contains a backslash with the Write or Edit tool.
  - Run Python with `-B` (no bytecode in the plugin).
  - Never run `npm ci` in a worktree whose `tooling/*/node_modules` is a junction.
  - Don't edit, rename or delete a file the suite reads while the suite runs: last session a rename mid-run produced ten false failures.
- **Fail before, pass after.** Every fix gets a regression test, seen failing on the previous state and passing now: `python -B tools/fail_before.py <test ids> [--rev REV]` (from `plugins/web-design-suite`) prints the table. The default REV is the latest `v*` tag (`v3.2.1`); use `--rev main` or a commit for code that is not in 3.2.1. Report the counts and name the controls.
- **CI replaces the local full runs (D1)** once #17's CI is green on all six suite jobs. Locally, run `python -B tools/check.py` (pointers, snippets, the plan, the audit, budgets and the affected tests). Until then, run the full suite on 3.14 and 3.9 before each commit that changes the plugin.
- **One set of rules.** A change to what a gate accepts goes into `skills/web-design-studio/assets/rules/design-rules.json` first, then into the audit, the stylelint config and the ESLint config, each with a real-tool test in `tests/test_real_tools.py`.
- **Facts from outside** (standards, vendor docs, laws, prices) are re-read at their source on the day. A figure the plugin's docs quote goes into `tests/fixtures/evidence.json` with its quote.
- **New `§` pointers** must be registered: `python -B tools/check_pointers.py --write-register`, then read the register's diff.

## 1. Orient (keep it under about 40 thousand tokens)

1. Read the repository's `CLAUDE.md` and `docs/HANDOFF.md`.
2. Read the execution plan's §2, §3 and §6, and its phase 3 table in §4.
3. Check the state:
   ```bash
   cd /c/DEV/Pro-Web-Designer-Suite-Plug-in && git fetch -q && git status --short && git log --oneline -3 origin/main && gh pr list --state all --limit 4
   ```
   - If the user merged #16, #17 and #18, check out `main` and pull.
   - If not, ask the user to merge them in order: #16, #17, #18. GitHub retargets each to `main` when the branch below it is deleted.
   - If #17's CI is not green, fixing it comes first (§3).
4. `python -B "dev plans/check_execution_plan.py"` must say `151 open items, 151 scheduled`. CI on `main` is the baseline; for a local one, `python -B plugins/web-design-suite/tools/check.py --all`.
5. Tell the user, in a few lines: the state, what this session does, and the budget.

## 2. Useful facts

- **The plugin** is `plugins/web-design-suite/`: `skills/<13 skills>/`, `tests/` (about 440 tests, standard-library `unittest`, helpers in `tests/wds_support.py`: `TempDirTest`, `run_py`, `env()`, `output`, `load_script`), and `tools/`: `check_pointers.py`, `sync_snippets.py`, `sync_rules.py`, `fail_before.py`, `check.py`.
- **`fail_before.py`** unpacks the revision with `git archive` into a temporary folder and sets `WDS_PLUGIN_ROOT` and `WDS_PLUGIN_REV` for the first run. A failing `setUpClass` counts against each test of its class. Things outside the plugin (`tooling/`) are the same in both runs, so their tests show as controls.
- **`check.py`** picks the affected tests from the files changed since `git merge-base origin/main HEAD` (`--base REF` to change it): a test module runs itself; a skill file runs the modules naming its skill folder or stem; a shared file (`wds_support.py`, `design-rules.json`, `assets/configs/`, `tools/`, `tooling/main`) runs everything.
- **CI** (`.github/workflows/ci.yml`): Windows, Linux and macOS × Python 3.9 and 3.14 through `uv run --no-project --python <v>`, Node 22, `npm ci` of both tooling folders; Linux adds Playwright's headless shell and the image's Postgres. A separate job runs `claude plugin validate --strict` (no sign-in needed). `astral-sh/setup-uv` publishes no major tag: pin a full version.
- **The release** (`tooling/release/build.py`, `.github/workflows/release.yml`): a pushed `v*` tag builds `web-design-suite-<version>.zip`, 13 `.skill` files and `SHA256SUMS`, and creates the GitHub release. Nothing else creates one. `claude plugin tag --dry-run plugins/web-design-suite` checks that `plugin.json` and the marketplace entry agree; the tag stays `vX.Y.Z`.
- **An open question for the user:** all 13 skill descriptions are 301 to 368 characters. The platform allows 1024 (platform.claude.com, Agent Skills overview), but the claude.ai help center ("How to create custom skills") gives 200 for an upload. The build warns and still builds. Whether to shorten them is the user's call, and it touches routing (P27/P28).
- **Postgres 18** is installed locally (`initdb`, `pg_ctl`, `psql`). `test_policies.PoliciesRunOnPostgres` makes its own scratch cluster, with its socket in its own folder. On Windows, `pg_ctl start` from Python must not capture output.
- **The CLAUDE.md commands** are for the Bash tool. `claude plugin validate`, `update`, `details` and `tag` need the desktop app's bundled CLI, `%APPDATA%\Claude\claude-code\<version>\claude.exe`.

## 3. First: P1's CI, if it is not green

#17 was red on its first run only because `astral-sh/setup-uv@v10` does not exist (fixed: `@v10.2.0`). The second run was in progress at handoff. Expect failures that never showed on Windows: Linux has never run the Node tests, and macOS has never run at all.

- Read the failures with `gh run view <run id> --log-failed`, saved to the scratchpad, then `grep -E 'FAIL:|ERROR:|Ran |##\[error\]'`.
- Each failure is either a test that assumes Windows, which you fix in the test, or a real platform bug, which you fix in the plugin with a regression test, as any other.
- When all six suite jobs and `validate` are green, record it: the completion plan's rule "CI (decision D1)" is then in force, and #17's description gets the acceptance results (CI green; `fail_before.py test_file_modes` shows N5 fixed against v3.2.1; two builds of one commit are byte-identical).

## 4. P2 part 2: the spec generates the gates' rule sections (N2, SB-C2)

Part 1 is PR #18, stacked on #17: `tools/sync_rules.py` writes the layer order and statement, the nesting depth and the system colours (now `system_colors.names` in the spec) into one `BEGIN design-rules` … `END design-rules` block in the audit and in the stylelint config. Its `--check` runs in `check.py` and CI, and `test_tools.SyncRules` tests it. The markers avoid "@generated", which makes the audit and the migration tool skip a file.

Part 2 makes the rule sections themselves come from the spec, so P3 to P5 are spec edits and a rerun. Branch `feat/p2-rule-sections`, stacked on #18 if it is not merged. Read N2 in the completion plan (`**N2 ·`), and SB-C2 and SB-A14 in `dev plans/web-design-suite-review/studio-build.md` (lines 33 and 69).

1. **Model the value rules in the spec.** `design-rules.json` has `nesting`, `zero`, `margins_in_components`, `var_fallback`, `system_colors`, `sass`, `layers` and `file_classes`, each with a rule and examples. What it lacks is the value allowlist itself: which values each property family takes (tokens through `var()`, `0`, the keywords), which the stylelint config spells as regexes in `declaration-property-value-allowed-list` (about lines 220 to 320), and which the ESLint config spells as patterns for inline styles. Read both, write the families into the spec, and have `sync_rules.py` write them into each gate's block, as it does the layer order.
2. **The file classes stay as they are, unless the spec grows Sass.** The audit's and the migration tool's regexes also take `.scss`, while the spec's globs are the CSS-only ones stylelint uses. `test_rules_spec.test_file_classes` and `test_file_globs` hold all three to the spec's examples.
3. **Conformance**: one test that runs every `allowed` and `refused` example of every section through the real audit, stylelint and, for JSX and inline styles, ESLint, and holds each tool to the spec. `test_real_tools.StylelintConfig` and `test_rules_spec.TheAuditFollowsTheSpec` do this today for `layers` and `system_colors`: generalise them, and drop the text comparisons that the generated blocks make redundant.
4. **Close:** the CHANGELOG under 3.3.0; SB-C2 is "fixed in 3.3.0" in the inventory and N2 is `*Done for 3.3.0.*`; the execution plan's P2 row and §9. The checker must then say 149.

## 5. P3: the gates agree (N1, SB-A15)

Branch `fix/p3-gates-agree`, stacked on P2. Read N1's table (completion plan, `**N1 ·`), and SB-A15 in `studio-build.md` (line 35).

- **N1, decided (D2):** rows 1 and 2 refuse a factor on a role token (`calc(var(--pad-card) * 1.5)`), and `* -1` stays allowed; row 3 refuses `em` font sizes except `1em`; row 4 refuses a literal `ch` measure, in favour of the measure token; row 5 refuses type selectors in component files; rows 6 to 8 follow the spec (a hex inside a `var()` fallback and a margin inside an owl rule are allowed, so stylelint changes; a system colour outside `@media (forced-colors: active)` is refused, so the audit changes).
- **SB-A15:** the stylelint allowlist's holes: `function-disallowed-list` lacks `oklch`, `oklab`, `lab`, `lch`, `color()`, `light-dark` and `color-mix`; the `background` and `border` shorthands are not in the allowlist; margins outside components, `top/left/inset`, border and outline widths, sizing, and the `transition` and `animation` shorthands are unconstrained; the `theme.css` override allows `--spacing-card: 28px` and `oklch()`, although stack-tailwind says the gate guards that file. SCSS is P37's, not this PR's.
- **Spec first:** each row and each hole becomes `allowed`/`refused` examples in `design-rules.json`, so P2's conformance test holds all three tools to it. Then change the tools: through `sync_rules.py` where the rule is data, by hand where it is code.
- **Fail-before** against `v3.2.1`; where P0 to P2 changed the code, against `main` before the fix.

## 6. If budget remains: P4

Audit accuracy, the checks the docs promise, its speed on large JSX, and SARIF output (SB-A11, SB-A25, SB-C10), all in `audit_design.py`. Read the three items in `studio-build.md` first. Start it only with about 200 thousand tokens left; otherwise go to §7.

## 7. End of session (never skip)

1. Rewrite `docs/HANDOFF.md`: one page, with the state, next steps, blockers and warnings.
2. Update `CLAUDE.md`'s Current State, the execution plan's §9, and the inventory.
3. **Rewrite this file** for the session after yours: the next PRs in the same detail as P2 and P3 here.
4. Run `python -B "dev plans/check_execution_plan.py"`.
5. Commit the docs, then tell the user what merged, what is open, the token use, and what they need to do.
