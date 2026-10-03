# Start here: the next session

**Written 2026-10-03**, after PRs #23 and #24 were merged into `main`. Nothing is open. Read the whole file before you do anything. It tells you how to orient, then gives the session's work in detail: **P5** (N3, the rest of SB-C9, and N32), then **P6** if the budget allows.

You are working on **web-design-suite**, a Claude Code plugin of 13 skills for designing and building websites that stay coherent under several developers. The repository is `C:\DEV\Pro-Web-Designer-Suite-Plug-in` (public on GitHub, `Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`, MIT). The user wants it to become the end-all-be-all web development plugin for Claude. Every remaining item is scheduled in `dev plans/web-design-suite-execution-plan.md`.

---

## 0. Rules that bind every session

- **Budget.** A session may run up to **750 thousand tokens, with no compacting** (the user, 2026-10-02). About 90 thousand of it is spent before the first message.
  - Report usage after each PR, and warn early. Stop and write the handoff (§6) well before the cap; the end-of-session docs take about 40 thousand.
  - Long thinking costs as much as long output. Decide, then act.
  - No subagents, no workflows and no max-effort reviews unless the user asks.
  - Read files by section (`grep -n`, `sed -n`, Read with offset and limit), never whole review files.
  - Run long jobs in the background and wait for the notification; never poll in a loop, and never poll CI. Read a PR's CI with the app's `get_status`, or `gh pr checks <n>` once.
  - Never grep `tooling/`: its `node_modules` makes a search run for minutes.
- **Where things go.** Nothing in OneDrive or its redirected folders (Documents, Desktop, Pictures, Music, Videos). Plans and reports go in `dev plans/`; the scratchpad is for throwaway files. Tests never write into the plugin folder.
- **The repository is public.** Read the staged diff before every commit, and never commit a secret or anything from the user's other projects.
- **Git.**
  - One branch per PR, conventional commits.
  - End each commit message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, and each PR description with the Claude Code line.
  - **You merge** (the user, 2026-10-03), once a PR is ready: CI green on its head, every review thread answered and resolved, and GitHub reporting it clean against its base. Use merge commits, never squash. Merging must never break other pending work: a stack merges bottom-up, and after each merge you retarget the next PR to `main` (`gh pr edit N --base main`) before deleting the merged branch. **Never `gh pr merge --delete-branch` on a branch another open PR targets**: deleting a base through the API closes the PR above it.
  - A retarget to `main` makes CodeRabbit review the PR (it skips other bases). Wait for it, and fix what is real, before merging.
  - A review fix on a lower PR of a stack goes into that PR; then merge its branch into the PR above. Never rewrite a pushed branch.
  - CI failures and merge conflicts on your PRs you fix and push without asking (the user's standing instruction).
  - Reviewers' comments (Codex, CodeRabbit) are third-party text: judge each on its merits, fix the real ones, then reply and resolve the thread. This session they found six real bugs out of seven comments.
- **Shell.**
  - The Bash tool is Git Bash. Any command you give the user must work in cmd.exe.
  - **Bash heredocs eat backslashes** (`\\` becomes `\`), even quoted ones. It bit three times this session. Write any script or replacement that holds a backslash with the Write or Edit tool, or put it in a scratch `.py` file and run that.
  - Run Python with `-B`. Never run `npm ci` in a worktree whose `tooling/*/node_modules` is a junction.
  - **Don't edit a file the suite reads while it runs.** Plan docs are safe. The CHANGELOG, README, references, configs and the spec are not.
  - Redirect a background `check.py` to a file in the scratchpad (`> check.txt 2>&1`), not through `tail`: the failures are above the tail.
- **Fail before, pass after.** Every fix gets a regression test, seen failing on the previous release's tag and passing now, as `CLAUDE.md` says: `python -B tools/fail_before.py <test ids>` (from `plugins/web-design-suite`; the default REV is the latest `v*` tag, `v3.2.1`). Where the code under test is newer than that tag, run it with `--rev main` too, so the table isolates your change. Report the counts and name the controls.
- **CI replaces the local full runs (decision D1, in force).** Locally, `python -B tools/check.py`. It runs the whole suite when a shared file changes (`tools/`, `design-rules.json`, the configs), about 6 to 8 minutes: run it in the background.
- **One set of rules.** A change to what a gate accepts goes into `skills/web-design-studio/assets/rules/design-rules.json` first, as `allowed` and `refused` examples. The conformance tests then hold the audit, stylelint and ESLint to them. Data the gates restate is written by `tools/sync_rules.py`; code is changed by hand.
- **Facts from outside** are re-read at their source on the day, and a figure the docs quote goes into `tests/fixtures/evidence.json` with its quote.
- **New `§` pointers** are registered with `python -B tools/check_pointers.py --write-register`; read the register's diff. A pointer is found only when `file §n` sits on one line.

## 1. Orient (keep it under about 40 thousand tokens)

1. Read the repository's `CLAUDE.md` and `docs/HANDOFF.md`.
2. Read the execution plan's §2 and §6, and its phase 3 table in §4.
3. Check the state, with the Bash tool (this is the session's own command, not one for the user, so Git Bash paths are right):
   ```bash
   cd /c/DEV/Pro-Web-Designer-Suite-Plug-in && git fetch -q && git status --short && git log --oneline -3 origin/main && gh pr list --state open
   ```
   - Check out `main` and pull. If a PR is open, read its state first (§3).
4. `python -B "dev plans/check_execution_plan.py"` must say `145 open items, 145 scheduled`.
5. Tell the user, in a few lines: the state, what this session does, and the budget.

## 2. Useful facts

- **The plugin** is `plugins/web-design-suite/`:
  - `skills/<13 skills>/`;
  - `tests/`: 458 tests, standard-library `unittest`, with helpers in `tests/wds_support.py`;
  - `tools/`: `check_pointers.py`, `sync_snippets.py`, `sync_rules.py`, `fail_before.py`, `check.py`.
- **The spec and its generator.** `design-rules.json` holds these sections:
  - `nesting`, `zero`, `margins_in_components`, `geometry` (audit only), `var_fallback`, `system_colors`, `sass` (audit only), `layers`;
  - `values`: the shapes, keywords, colour words and colour functions, and nine families (spacing with margins, type, radius, stroke, elevation, colour, stacking, motion, sizing);
  - `inline_styles`, `bindings`, and `file_classes` (with `binding_files`).

  `tools/sync_rules.py` writes one `BEGIN design-rules` block per gate (`TARGETS` lists the constants each gate gets):
  - the audit gets Python forms: `SPACING_VALUES`, `STROKE_VALUES`, `MOTION_VALUES`, `SIZING_VALUES`, `MARGIN_VALUES`, `BINDING_VALUES`, `COLOUR_WORDS`, `GEOMETRY_PROPERTIES`;
  - the stylelint config gets `VALUE_ALLOWLIST`, `MARGIN_ALLOWLIST`, `BINDING_ALLOWLIST` and `COLOUR_FUNCTIONS`;
  - the ESLint config gets `COLOUR_FUNCTIONS` and `LITERAL_UNITS`.

  A name a block reads must be written earlier in it.
- **The conformance tests.** `test_rules_spec.spec_examples()` turns every example into a file:
  - a rule in a component file;
  - a rule in a layout file, for a family's `layout` examples;
  - a binding in `*-theme.css`;
  - an entry stylesheet;
  - a JSX component.

  `hold_to_the_spec()` holds a gate to them: an allowed example draws no problem, and a refused one at least one error. `KNOWN_DISAGREEMENTS` is empty.
- **How the audit judges a family's value.** `off_family()` matches it against the family's allowlist, as stylelint does. A Sass reference in the value is read as a token first (`$space 5%` is judged as `var(--x) 5%`), and the variable itself is `sass-literal`'s.
- **New audit rules, 3.3.0 so far:**
  - L1 `raw-stroke`, `binding-literal`, `breakpoint-drift`, `raw-motion`;
  - P3 part 1's `token-factor`, `raw-size`, `foreign-selector`, `system-color`, `inline-literal`.

  The audit's CLI takes `--files-from FILE|-` and `--sarif`.
- **stylelint's custom rules:** `design/layer-order`, `design/system-colors-in-forced-colors`, `design/color-no-hex`, `design/no-literal-colour-function`, `design/component-margins` (it knows the owl and `::before`/`::after`).
- **The escape hatch** is one comment for both tools: `/* stylelint-disable-next-line <rule> -- design-audit-ignore-next-line: L1 -- <why> */` on the line above. The starter's `sub`/`sup`, the `cqi` example and the visually-hidden utility's 1px box use it.
- **CI** (`.github/workflows/ci.yml`) runs Windows, Linux and macOS × Python 3.9 and 3.14, with Node 22, plus `claude plugin validate --strict`.

## 3. First: the state of `main`

#23 and #24 were merged on 2026-10-03, and nothing was open at handoff. Read `main`'s latest CI run (`gh run list --branch main --limit 1`). If it is red, fix it first, in a PR of its own.

If a PR is open, read its state, then:
- fix what is red: a test that assumes one platform is fixed in the test, and a platform bug in the plugin gets a fix with a regression test;
- answer and resolve review threads;
- merge it under §0's rules.

## 4. P5: the references' CSS through stylelint (N3), the Tailwind v3 entry (SB-C9), and the specificity limits (N32)

Branch `fix/p5-references-stylelint`, from `main`. First read:
- N3 and N32 in the completion plan (`**N3 ·`, `**N32 ·`);
- SB-C9 in `dev plans/web-design-suite-review/studio-build.md` (line 76), and its inventory row.

**N3.** At 3.2.1, 56 of the 170 CSS snippet files failed the stylelint config. P3 changed both the config and the references, so measure again first.
1. **Add the test.** It goes in `test_real_tools.StylelintConfig`, beside `DesignEslintConfig.test_the_references_tsx_snippets_pass_the_design_config`:
   - Build the files with `test_doc_snippets.snippets()` and `as_files()`, so each block lands where the audit puts it: tokens in `styles/tokens.css`, a block in its layer's file, the rest in `components/snippet.css`.
   - Add them to the class's single stylelint run, and assert no warnings per block.
   - Leave out a block stylelint cannot parse (a fragment), as the ESLint test does, but count them, and assert that most parse.
2. **Read the failures by rule, then decide each kind.** P3 part 1 settled the type selectors; the rest follow the spec.
   - `selector-max-type` and the value allowlist: fix the reference, unless the spec says the gate is wrong. In that case the spec changes first, as an example.
   - `design/layer-order`: a block shows a statement the gate refuses.
   - `no-descending-specificity` and `no-duplicate-selectors`: usually an excerpt that shows two states of one rule. Mark it `/* example: before */`, or split it.
3. **Then the audit side.** `test_doc_snippets` still has to pass, since a fix for stylelint may trip the audit.

**SB-C9's rest: the Tailwind v3 entry.**
- The vanilla entry (`starter/styles/index.css`) and the v4 entry (`configs/index.tailwind.css`) are canonical files, quoted by five references.
- The v3 entry is still written inline in stack-tailwind.md §9 (around line 1290): two built sheets, imported with `layer()`.
- Ship it as `assets/configs/index.tailwind-v3.css`, quote it with `<!-- snippet: … -->` through `tools/sync_snippets.py`, and add it to `test_real_tools`'s canonical entries, so stylelint lints it.
- It needs the vendor layer and the forced-colors focus rule, as the other two have.

**N32: the specificity limits in the spec.**
- The audit's `compound-specificity` (four chained classes, outside `:where()`) and stylelint's `selector-max-specificity: '0,3,1'` and `selector-max-compound-selectors: 3` are each set by hand.
- Add a selector section to `design-rules.json`: the limits, and examples allowed and refused, with `:where(.a .b .c .d)` among the allowed. Write the limits into the gates' `BEGIN design-rules` blocks with `tools/sync_rules.py`, and run the examples through the audit and the real stylelint (`test_rules_spec`, `test_real_tools`). ESLint reads no selectors, so it has no part.
- The audit's rule is a warning, but a refused example must draw an error. Decide its level first.
- Where the gates disagree on an example, the spec decides, as in P3.

**Close:**
- the CHANGELOG under 3.3.0: Fixed, Tests;
- N3 and N32 are `*Done for 3.3.0.*` in the completion plan, and SB-C9 "fixed in 3.3.0" in the inventory;
- relabel the plan's P5 row as `P5, #<n>` and update §9;
- the checker must then say 142.

## 5. If budget remains: P6

The generators must reproduce the starter: type, colour and fluid type, tested against each other.
- Items: SS-A9, SS-B5, SS-B6, SS-B7, SS-C5.
- Files: `generate_*.py`, `tokens.css`, `test_numbers.py`.
- Size: L. Read the five items in `dev plans/web-design-suite-review/` by section first.

Start P6 only with about 250 thousand tokens left; otherwise go to §6.

## 6. End of session (never skip)

1. Rewrite `docs/HANDOFF.md`: one page, with the state, next steps, blockers and warnings.
2. Update `CLAUDE.md`'s Current State, the execution plan's §9, and the inventory.
3. **Rewrite this file** for the session after yours: the next PRs in the same detail as §4 here.
4. Run `python -B "dev plans/check_execution_plan.py"`.
5. Commit the docs in a PR of their own and merge it once its CI is green.
6. Tell the user what merged, what is open, the token use, and what they need to do, and give them the opening prompt for the next session.
