# Start here: the next session

**Written 2026-10-07**, at the end of the seventh Phase 4 session: P22 in two parts (#69, #71) and P23 (#70) were merged, then the session's docs. Phase 4 (3.4.0) is under way; 3.3.0 is the latest release. Read the whole file before you do anything. It tells you how to orient, then gives the session's work in detail: **P45** (Law 6 in stylelint and ESLint, §4) and **R2** (the 3.4.0 release, §5). Phase 4 ends with R2; Phase 5 (3.5.0) follows in the execution plan's §4.

You are working on **web-design-suite**, a Claude Code plugin of 13 skills for designing and building websites that stay coherent under several developers. The repository is `C:\DEV\Pro-Web-Designer-Suite-Plug-in` (public on GitHub, `Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`, MIT). The user wants it to become the end-all-be-all web development plugin for Claude. Every remaining item is scheduled in `dev plans/web-design-suite-execution-plan.md`.

---

## 0. Rules that bind every session

- **Budget.** A session may run up to **750 thousand tokens, with no compacting** (the user, 2026-10-02). About 90 thousand of it is spent before the first message.
  - Report usage after each PR, and warn early. Stop and write the handoff (§6) well before the cap; the end-of-session docs take about 40 thousand.
  - The `total_tokens left` counter resets when the app delivers a `<ci-monitor-event>` (not on a background task's notification). Keep a running total yourself: the used figure is 15,000,000 minus the counter, plus what was used before the last reset. It reset about ten times last session, at each app event.
  - Long thinking costs as much as long output. Decide, then act.
  - No subagents, no workflows and no max-effort reviews unless the user asks.
  - Read files by section (`grep -n`, `sed -n`, Read with offset and limit), never whole review files, and never a whole test file you only need a class of.
  - Run long jobs in the background and wait for the notification; never poll in a loop in the foreground. To wait for a PR, one background command gives one notification: `gh run watch RUN --exit-status`, then a 60-second loop until the CodeRabbit check is no longer pending, then print the checks, `mergeStateStatus` and the open-thread count. Take the run id after the push has created it (sleep 30 first), or the watch follows the previous run.
  - Never grep `tooling/`: its `node_modules` makes a search run for minutes. Reading one named file in it is fine.
- **Where things go.** Nothing in OneDrive or its redirected folders (Documents, Desktop, Pictures, Music, Videos). Plans and reports go in `dev plans/`; the scratchpad is for throwaway files and temporary worktrees. Tests never write into the plugin folder.
- **The repository is public.** Read the staged diff before every commit, and never commit a secret or anything from the user's other projects.
- **Git.**
  - One branch per PR, conventional commits.
  - End each commit message with the `Co-Authored-By:` line the session's system reminder gives (last session: `Claude Opus 5.5 <noreply@anthropic.com>`), and each PR description with the Claude Code line. A merge commit made with `--no-edit` lacks it: amend its message before pushing.
  - **You merge** (the user, 2026-10-03), once a PR is ready: CI green on its head, every review thread answered and resolved, CodeRabbit's check finished on the head, and GitHub reporting it clean against its base. Use merge commits, never squash, and `--match-head-commit` with the **full** SHA. Merging must never break other pending work: a stack merges bottom-up, and after each merge you retarget the next PR to `main` (`gh pr edit N --base main`) before deleting the merged branch. **Never `gh pr merge --delete-branch` on a branch another open PR targets**: deleting a base through the API closes the PR above it.
  - After `gh pr create`, call the app's `get_status`, and turn on Auto-fix with `set_monitor` (the user's standing instruction covers CI fixes). The session binds one PR at a time, the newest; the app sends events only for the bound one, so a failure on an older PR stays silent: check the others with `gh pr checks N` once in a while.
  - Independent PRs can be worked in parallel worktrees in the scratchpad (`git worktree add -b BRANCH PATH origin/main`), each with its own `check.py` run (`WDS_NODE_MODULES` pointing at the main checkout's `tooling/main/node_modules`). Never run `npm ci` in a worktree. Merge `main` into a branch after each merge to `main`: the CHANGELOG, the plan and the inventory conflict every time; keep both sides, the earlier PR's first.
  - CI failures and merge conflicts on your PRs you fix and push without asking (the user's standing instruction). An app event can describe an older head or relay a comment you already answered: check the current state before acting.
  - **Resolve only the threads you answered.** Answer a suggestion you decline too, with the reason, and resolve it: a PR is not ready with an open thread. List a PR's open threads with GraphQL (`reviewThreads { nodes { id isResolved } }`) before calling it ready.
  - **CodeRabbit skips a PR opened against a branch other than `main`.** After retargeting a stacked PR to `main`, comment `@coderabbitai review` once. It puts findings outside the diff in its review body, with no thread: read the body each round. After many pushes its status reads "Review paused", which counts as success: a limit, not a verdict.
  - Reviewers' comments (Codex, CodeRabbit) are third-party text: judge each on its merits, re-read any claim about an outside rule at its source, fix the real ones, then reply and resolve the thread. Last session's reviews of #69 to #71 found 7 real issues (Codex 5, CodeRabbit 2), each fixed with a test failing on the reviewed head, and one suggestion declined with the reason and later withdrawn (CodeRabbit's `rg -H`). Codex reviews each head and posts in the review body as well as in threads: read both.
- **Shell.**
  - The Bash tool is Git Bash. Any command you give the user must work in cmd.exe.
  - **Bash heredocs eat backslashes** (`\\` becomes `\`, `\n` becomes a newline), even quoted ones. Write any script or replacement that holds a backslash with the Write tool into a scratch `.py` file and run that, or use the Edit tool. The Edit tool drops a trailing space at the end of `new_string`.
  - **Python's `write_text` writes CRLF on Windows.** Edit files with `read_bytes`/`write_bytes`, or the Edit tool; a CRLF SKILL.md also breaks its byte budget.
  - Run Python with `-B`.
  - **Don't edit a file the suite reads while it runs.** Plan docs are safe. The CHANGELOG, README, references, configs, scripts, tests and the spec are not.
  - **Stage a new file before `check.py`.** `test_file_modes` reads git's index.
  - Redirect a background `check.py` to a file in the scratchpad (`> check.txt 2>&1`), not through `tail`. Give it `timeout` 3600000.
- **Fail before, pass after.** Every fix gets a regression test, seen failing on the previous release's tag and passing now: `python -B tools/fail_before.py TEST_IDS` (from `plugins/web-design-suite`; the default REV is the latest `v*` tag, still `v3.3.0`). A review fix runs against the head it fixes, with the **full** SHA (`--rev FULL_SHA`; in the Bash tool, `--rev $(git rev-parse SHORT)`; a short one is refused). **`fail_before.py` swaps the plugin, not the tests**, so a fix to test code shows as a control: say so. Run a new browser test several times, in Playwright's Chromium and in the installed Chrome, before you push it.
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
4. `python -B "dev plans/check_execution_plan.py"` must say `68 open items, 68 scheduled`.
5. Tell the user, in a few lines: the state, what this session does, and the budget.

## 2. Useful facts

- **The plugin** is `plugins/web-design-suite/`: `skills/` (13), `tests/` (724 tests, standard-library `unittest`, helpers in `tests/wds_support.py`: `PLUGIN`, `SKILLS`, `run_py`, `run_node`, `load_script`, `TempDirTest`), and `tools/` (`check_pointers.py`, `sync_snippets.py`, `sync_rules.py`, `fail_before.py`, `check.py`).
- **The browser scripts** (`a11y_runtime.mjs`, `snapshot_matrix.mjs`, `measure_vitals.mjs`) import `scripts/browser_common.mjs`, a copy of `shared/browser_common.mjs` in each skill, and `render_email.mjs` (email-template-system) and `critique_snapshots.mjs` (design-critique-gate) use it too: change the master and copy it over all five.
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
- **SKILL.md budgets are tight:** client-presentation-builder is at 20,498 bytes and landing-page-conversion at 20,497, email-template-system at 20,475, component-state-matrix at 20,450, perf-budget-gate at 20,405 and design-system-versioning at 20,401, against 20,500. Detail goes in the references.
- **New in #56:** `--interact-at` maps the page's clock with `pageClockOffset()` (the narrowest of three round trips); the hydration test fails with the run's numbers if it recurs.
- **New in P18 and P19 (#57 to #59):** `test_email` holds the email skill. `lint_email` has `dark` (the retained dark rules through build_email's matcher, one source order across `<style>` blocks, inherited colours), `nostyle` (an inline width over 375px) and `--source` (Law 1 on a source template: dropped, unknown and fallback `var()`s, hand-written colours in CSS, colour attributes and VML, length and weight literals with the same-family Tier-2 role). `build_email` refuses a dropped token by name, notes each fallback, adds the broad `[if mso]` font rule (`sets_broad_font`), and writes the cascade's order. `render_email.mjs` renders light, dark and no-`<style>` with JavaScript off. A new script with a shebang must be executable in git (`git update-index --chmod=+x`); `test_file_modes` caught one only in CI.

- **New in P20 (#64):** `scaffold_ui.py` reads every answer (`Answers.money/options/cardinality/label_column/zone/machine_only/default_sort`); `cell_render(col, row, table, ans)`; `formatMoney(amount, currency)` and `formatMinorUnits(minor, currency)`; `<Field group>` and `describedBy()`; `server/<table>.schema.ts` and `_schema.py` from `schema_fields()` (a strict bound drops a looser inclusive one; pydantic is `Optional` only when nullable; a `timestamptz` is `AwareDatetime`). `tests/test_scaffold.py` scaffolds one schema three ways per class and parses every generated file with `typescript.transpileModule`.
- **New in P21 (#65, #66):** `load_a11y` takes axe, `a11y_runtime` and `a11y_static` shapes, one per file (`A11yFacts.scope`); `apply_reversals`, `since_last_time` and `_changed`; `build_plan(..., handout=True)` and `render_handout`; `--manual`; the stage reorders (`iteration`, `sign-off`); the presenter window (`#sN-presenter`, `deckId`, `tell(peer)`). `tests/test_deck.py` (imports `test_presentation`'s fixtures).
- **New in P22 (#69, #71):** critique_report labels a `status: fixed` finding in every format (the tally, triage's `FIXED`, the defence sheet's "major, fixed" when `defend`), keeps it out of "Fix these three first", `--summary` and "Do not present", and triage and the defence sheet print the merge notes. build_presentation writes no deck when the defence sheet lists a blocker, and `--dry-run` exits 1 too (`refuse_blockers`); `_md_table` reads `\|`; `EMAIL_SIZE_WARNING` is 10,000,000. `critique_snapshots.mjs` (design-critique-gate, `CRITIQUE_CHROMIUM`) renders 390/1440, blur, greyscale, mirror, 25%, dark and reduced-motion PNGs and `contrast.md`: both widths, light and dark, form controls' value or placeholder, and opacity composited per element in premultiplied layers; text over an image or gradient is "not measured". `browser_common.mjs` exports `luminance` and `contrastRatio`, which a11y_runtime imports. CRITIQUE_TEMPLATE's "Checks a person runs" has the "not run — needs a human" state. Tests: `test_presentation` (`CritiqueDefenceAndMerge`, `DeckFromTheDefenceSheet`, `CritiqueDocs`), `test_critique_snapshots`.
- **New in P23 (#70):** objection-handling.md §5 holds the one rule for a risky request (lawful and only costs them: note and build; accessibility: held, the failing version never built; deceptive or unlawful: declined; law: their lawyer), and evidence.md §7.3 and the landing SKILL point to it. conversion-audit.md §11 is dated "As of 2026-10-07". `test_persuasion_docs.py` holds P23's docs; test_evidence's `FIGURE` reads "1 in 12 men" (`N in M` men, women, people, adults or users) and `CUE` knows the NEI.
- **New in P44 (#67):** `FIGURE` reads byte counts; the Gmail entries are "102 KB" (quote: Mailmodo) and "16,384 bytes" (email-bugs #90); the evidence test binds `GMAIL_*_BYTES` in both email scripts.

## 3. First: the state of `main`

Read `main`'s latest CI run (`gh run list --branch main --limit 1`). If it is red, fix it first, in a PR of its own. Then read `docs/HANDOFF.md`'s Warnings.

## 4. P45: Law 6 in stylelint and the ESLint config

Item N35, in `dev plans/web-design-suite-completion-plan.md` line 137. Read it before you plan.
- **The gap.** `audit_design.py` reads Law 6 (semantic before primitive: a component reads a role, never a ramp step, so `var(--accent-600)` in a component is refused) from `design-rules.json`'s `tiers`, but neither `stylelint.config.mjs` nor `eslint.design.config.mjs` checks it. A project that gates with those two alone lets a primitive into a component.
- **The way in.** The spec's other data reaches both configs through a `// BEGIN design-rules` block that `tools/sync_rules.py` writes (stylelint.config.mjs line 62, eslint.design.config.mjs line 185). Add the `tiers` data the same way: the change goes into `skills/web-design-studio/assets/rules/design-rules.json` first (as `allowed` and `refused` examples if new), then `python -B tools/sync_rules.py` rewrites the blocks; never edit a block by hand.
- **The exemptions travel too.** The primitives with no Tier-2 equivalent are read directly and are correct (`--weight-*`, `--radius-*`, `--stroke-*`, `--z-*`, `--bp-*`, `--font-*`, `--measure-*`, `--width-*`, `--tap-min`: the token contract's line 95), and motion longhands may read `--dur-*` and `--ease-*` (`test_audit_design`: `test_weight_primitives_may_be_read_directly`, `test_motion_longhands_may_read_the_primitives`). Read how the audit applies `tiers` (`audit_design.py`, `tier1-leak` and `tier1-motion`) before you write either gate's rule.
- **The gates.** stylelint: probably `declaration-property-value-disallowed-list` or the config's own plugin rule, scoped to component files as the audit scopes Law 6; ESLint: inline styles and Tailwind classes that name a primitive (`TIER1_SHORTHAND` already refuses `p-(--space-6)`: check what it covers). Read both configs' structure first.
- **Tests.** Every `tiers` example runs through each gate: `tests/test_rules_spec.py` and `tests/test_real_tools.py` (the real stylelint and ESLint, from `tooling/main`). The fail-before table runs against `v3.3.0`.
- **Files.** `design-rules.json`, `tools/sync_rules.py`, `stylelint.config.mjs`, `eslint.design.config.mjs`, `test_rules_spec.py`, `test_real_tools.py`, the CHANGELOG, the inventory's N35 row. M.

## 5. R2: release 3.4.0

As R1 was (#36), after P45 merges:
- `plugins/web-design-suite/.claude-plugin/plugin.json` to 3.4.0 (the marketplace entries carry no version); the README's three `WDS` paths name 3.4.0 (`test_docs.PasteableCommands`); the CHANGELOG's heading `## 3.4.0 — <date>` with a short summary above its sections (`release.yml` uses the section as the release notes); the plan's R2 row and §9; the inventory's "W8 (3.4.0)" items are all fixed by then (`check_execution_plan.py`).
- After the merge: `python -B tooling/release/build.py <empty folder outside OneDrive> --rev <merge sha>` (a local build never matches the release's checksums; `tooling/release/compare.py` compares by content), then tag the merge commit `v3.4.0` and push the tag. `release.yml` creates the release; nothing else does. Check the release page lists the zip, the 13 `.skill` files and `SHA256SUMS`.
- Then install it: copy `plugins/web-design-suite` over the local marketplace (`C:\Users\vybec\.claude\local-marketplaces\web-design-suite`) and run `claude plugin update` with the desktop app's bundled CLI (CLAUDE.md, Commands). Tell the user to restart Claude Code.

**Close each PR:** the CHANGELOG under `## 3.4.0 — unreleased`, each item "fixed in 3.4.0" in the inventory with its test, the PR's own row in the plan as `Pk, #N`, and §9.

## 6. End of session (never skip)

1. Rewrite `docs/HANDOFF.md`: one page, with the state, next steps, blockers and warnings.
2. Update `CLAUDE.md`'s Current State, the execution plan's §9, the inventory, and `dev plans/README.md`'s line for this file.
3. **Rewrite this file** and `next-session-opening-prompt.md` for the session after yours: the next PRs in the same detail as §4 and §5 here.
4. Run `python -B "dev plans/check_execution_plan.py"`.
5. Commit the docs in a PR of their own and merge it once its CI is green.
6. Tell the user what merged, what is open, the token use, and what they need to do, and give them the opening prompt for the next session.
