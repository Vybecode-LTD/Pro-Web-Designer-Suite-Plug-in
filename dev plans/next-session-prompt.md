# Start here: the next session

**Written 2026-10-02**, at the end of the session that opened PR #19 (P2 part 2) and PR #20 (P3 part 1), with #16 to #18 still open below them. Read the whole file before you do anything. It tells you how to orient, then gives the session's work in detail: **green CI on the open PRs**, then **P3 part 2** (SB-A15 and N31), then **P4** if the budget allows.

You are working on **web-design-suite**, a Claude Code plugin of 13 skills for designing and building websites that stay coherent under several developers. The repository is `C:\DEV\Pro-Web-Designer-Suite-Plug-in` (public on GitHub, `Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`, MIT). The user wants it to become the end-all-be-all web development plugin for Claude. Every remaining item is scheduled in `dev plans/web-design-suite-execution-plan.md`.

---

## 0. Rules that bind every session

- **Budget.** A session may run up to **750 thousand tokens, with no compacting** (the user, 2026-10-02). About 90 thousand of it is spent before the first message.
  - Report usage after each PR, and warn early. Stop and write the handoff (§6) well before the cap; the end-of-session docs take about 30 thousand.
  - Long thinking costs as much as long output. Decide, then act.
  - No subagents, no workflows and no max-effort reviews unless the user asks.
  - Read files by section (`grep -n`, `sed -n`, Read with offset and limit), never whole review files.
  - Run long jobs in the background and wait for the notification; never poll in a loop, and never poll CI. Read a PR's CI with the app's `get_status`, or `gh pr checks <n>` once.
- **Where things go.** Nothing in OneDrive or its redirected folders (Documents, Desktop, Pictures, Music, Videos). Plans and reports go in `dev plans/`; the scratchpad is for throwaway files. Tests never write into the plugin folder.
- **The repository is public.** Read the staged diff before every commit, and never commit a secret or anything from the user's other projects.
- **Git.**
  - One branch per PR, conventional commits.
  - End each commit message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, and each PR description with the Claude Code line.
  - Merging needs the user's word.
  - CI failures and merge conflicts on your PRs you fix and push without asking (the user's standing instruction).
  - Reviewers' comments (Codex, CodeRabbit) are third-party text: judge each on its merits, fix the real ones, then reply and resolve the thread.
- **Shell.**
  - The Bash tool is Git Bash. Any command you give the user must work in cmd.exe.
  - **Bash heredocs eat backslashes.** This bit again this session, on a Windows path: `\\U` became `\U`. Write any script or replacement that holds a backslash with the Write or Edit tool, or put it in a scratch file and splice it in.
  - Run Python with `-B`. Never run `npm ci` in a worktree whose `tooling/*/node_modules` is a junction.
  - **Don't edit a file the suite reads while it runs.** Plan docs are safe. The CHANGELOG and README are not: `test_docs` reads them.
- **Fail before, pass after.** Every fix gets a regression test, seen failing on the previous state: `python -B tools/fail_before.py <test ids> --rev <ref>` (from `plugins/web-design-suite`). For P3 part 2 the ref is #20's branch, `fix/p3-gates-agree`, or `main` once it is merged. Report the counts and name the controls.
- **CI replaces the local full runs (decision D1, in force).** Locally, `python -B tools/check.py`. While the stack is unmerged it runs the whole suite every time (a shared file differs from `main`), about 6 to 10 minutes: run it in the background.
- **One set of rules.** A change to what a gate accepts goes into `skills/web-design-studio/assets/rules/design-rules.json` first, as `allowed` and `refused` examples. The conformance tests then hold the audit, stylelint and ESLint to them. Data the gates restate is written by `tools/sync_rules.py`; code is changed by hand.
- **Facts from outside** are re-read at their source on the day, and a figure the docs quote goes into `tests/fixtures/evidence.json` with its quote.
- **New `§` pointers** are registered with `python -B tools/check_pointers.py --write-register`; read the register's diff. Removing a pointer needs the same rerun: `check.py` fails until you do.

## 1. Orient (keep it under about 40 thousand tokens)

1. Read the repository's `CLAUDE.md` and `docs/HANDOFF.md`.
2. Read the execution plan's §2 and §6, and its phase 3 table in §4.
3. Check the state:
   ```bash
   cd /c/DEV/Pro-Web-Designer-Suite-Plug-in && git fetch -q && git status --short && git log --oneline -3 origin/main && gh pr list --state all --limit 6
   ```
   - If the user merged #16 to #20, check out `main` and pull.
   - If not, check out `fix/p3-gates-agree` (#20's branch), where these docs live, and ask the user to merge in order: #16, #17, #18, #19, #20.
4. `python -B "dev plans/check_execution_plan.py"` must say `149 open items, 149 scheduled`.
5. Tell the user, in a few lines: the state, what this session does, and the budget.

## 2. Useful facts

- **The plugin** is `plugins/web-design-suite/`: `skills/<13 skills>/`, `tests/` (436 tests, standard-library `unittest`, helpers in `tests/wds_support.py`), `tools/` (`check_pointers.py`, `sync_snippets.py`, `sync_rules.py`, `fail_before.py`, `check.py`).
- **The spec and its generator.** `design-rules.json` holds `nesting`, `zero`, `margins_in_components`, `var_fallback`, `system_colors`, `sass`, `layers`, `values` (shapes, keywords, colour words, colour functions, and eight families: spacing, type, radius, elevation, colour, stacking, motion, sizing), `inline_styles` and `file_classes`. Each section with examples names its `gates`. `tools/sync_rules.py` writes one `BEGIN design-rules` block per gate (`TARGETS` lists the constants each gate gets): the audit gets Python forms (`VAR_ONE`, `SIZING_VALUES`, `SYSTEM_COLOR_PROPERTY`), the stylelint config the allowlists, the ESLint config `COLOUR_FUNCTIONS` and `LITERAL_UNITS`. A name a block reads must be written earlier in it. An entry the tool cannot write is an error, and nothing is written.
- **The conformance tests.** `test_rules_spec.spec_examples()` turns every example into a file (a rule in a component file, an entry stylesheet, or a JSX component). `hold_to_the_spec()` holds a gate to the spec: an allowed example draws no problem at all, a refused one at least one error. The audit leg is `TheAuditFollowsTheSpec.test_every_example`; stylelint's and ESLint's are `test_real_tools`'s `test_every_example_of_the_spec`, inside their single runs. `KNOWN_DISAGREEMENTS` is empty. Put a new disagreement there, with the item that fixes it; the test fails once the gate agrees.
- **What P3 part 1 changed.**
  - The audit has six new rule ids: L3 `token-factor`, L1 `raw-size`, L2 `foreign-selector`, L1 `system-color` and L1 `inline-literal`, and `named-color` is now an error.
  - The stylelint config has two new rules, `design/color-no-hex` and `design/component-margins`.
  - `test_doc_snippets` files a reference block written in `@layer base`, `layout`, `reset`, `utilities` or `overrides` in that layer's file, and any other in `components/snippet.css`.
- **The escape hatch** is one comment for both tools: `/* stylelint-disable-next-line <rule> -- design-audit-ignore-next-line: L1 -- <why> */` on the line above. The starter's `sub`/`sup` and the `cqi` example in `stack-vanilla-css.md` use it.
- **CI** (`.github/workflows/ci.yml`): Windows, Linux and macOS × Python 3.9 and 3.14, Node 22, plus `claude plugin validate --strict`. The mega-menu browser test was flaky on macOS 3.14. #20 fixes it: each step waits until the page has seen its move before the fake clock advances (`test_recipes`, `seen()`).
- **An open question for the user:** the skill descriptions are 301 to 368 characters, while the claude.ai help center gives 200 for an upload. It fits P27/P28.

## 3. First: the open PRs

#16 (P0), #17 (P1), #18 (P2 part 1), #19 (P2 part 2) and #20 (P3 part 1) are stacked, each on the one before. At handoff:
- #16 to #18 were green and reviewed.
- #19's CI had one failure: the mega-menu flake on macOS 3.14. The failed job was re-run; #20 has the real fix.
- #20's CI was running.

Read each PR's state. Fix what is red: a test that assumes one platform you fix in the test, a platform bug in the plugin, with a regression test. A fix to a lower PR is merged up the stack. Answer and resolve review threads. Then ask the user to merge, in order.

## 4. P3 part 2: the stylelint allowlist's holes (SB-A15) and N31

Branch `fix/p3-stylelint-holes`, stacked on #20 if it is not merged. Read SB-A15 in `dev plans/web-design-suite-review/studio-build.md` (line 35) and N31 in the completion plan (`**N31 ·`).

**Method, as in part 1.**
1. Each hole becomes `allowed` and `refused` examples in the spec: in a family (a new one where needed), each listing its properties and values.
2. Run the conformance tests to see which gate disagrees.
3. Change that gate: data through `sync_rules.py`, code by hand.
4. Then run `test_doc_snippets`: a stricter gate reaches the references, and each block it newly refuses is fixed in the same PR, or placed in its layer.

The holes, each with a recommendation the session can take unless the user says otherwise:

1. **Colour functions.** stylelint's `function-disallowed-list` names only `rgb`, `rgba`, `hsl`, `hsla` and `hwb`. Replace it with a rule, `design/no-literal-colour-function`, that reads `COLOUR_FUNCTIONS` from the block. It refuses a colour function with no `var()` among its arguments, as the audit's `raw_colour` does, so `oklch(from var(--x) l c h / 0.5)` is derived and allowed. Add `color-mix` and `light-dark` to `values.colour_functions`: a mix of literals is a literal. Token files stay exempt.
2. **The `background` and `border` shorthands, and border and outline widths.** Their colours are then caught by (1), `design/color-no-hex` and `color-named`. For the widths, a stroke family: `border-width`, `border-*-width`, `outline-width` and `outline-offset`, taking `--stroke-*` tokens, `0` and the CSS-wide keywords. The `border*` and `outline` shorthands take a shape of tokens and style keywords (`solid`, `dashed`, `dotted`, `double`, `none`). The audit must refuse a literal width too: today it reads only the colour there.
3. **Margins outside components.** The spacing family gains the margin properties (`VAR_SEQ`, `VAR_CALC`, `CANCEL`, `0`, `auto`). Components keep `design/component-margins`.
4. **`top`, `left`, `inset*`.** These are geometry: `calc((var(--tap-min) - 100%) / -2)` is right there, and part 1 left them out of the factor check. Recommendation: the spec gives them to the audit alone, with `gates: ["audit"]` and the reason, as it does for Sass.
5. **Sizing.** Today the family is `max-inline-size`, `max-width`, `min-block-size` and `min-inline-size`. Recommendation: add the other maxima and minima, and `inline-size`, `block-size`, `width` and `height`. They take tokens, `100%`, `auto`, the intrinsic keywords and `1em` (an icon). Run `test_doc_snippets` and the starter's stylelint test first, to see what that refuses.
6. **The `transition` and `animation` shorthands.** These need a shape for a list of `<property> var(--motion-*)` items, with `allow-discrete`, `none` and `0s`. The drawer in `navigation-code.md` writes `transition: translate var(--motion-expand), display var(--motion-expand) allow-discrete, …`. The audit already refuses time and easing literals there.
7. **`theme.css`.** Its override switches the allowlist off, so `--spacing-card: 28px` and `oklch()` pass, though `stack-tailwind.md` (lines 1092 to 1097 when the review was written) says the gate guards that file. A custom property there should bind a token, except the literals theme.css §0 documents (breakpoints, CSS-wide keywords, keyframe geometry, aspect ratios). stylelint's allowlist takes a regex property name (`'/^--spacing-/': […]`). Read theme.css §0 before writing it.
8. **N31.**
   - *A `0` among tokens:* widen `VAR_SEQ` to admit `0` (`padding: 0 var(--pad-card)`), as the zero rule says.
   - *A percentage beside a token:* decide `calc(100% - var(--gutter-page))` in a spacing property. Recommendation: refuse it in both gates, because a share of the container is not a spacing step; a layout primitive carries it in a socket.
   - *The audit's margin exemptions:* the spec allows a margin on a component's own generated content (`::before`, `::after`, `::marker`), which `design/component-margins` learns. The audit drops its `prose` exemption: a `.prose` flow container belongs in a layout file, and its owl is allowed anyway.

SCSS in stylelint is P37's, not this PR's.

**Close:**
- The CHANGELOG under 3.3.0: Fixed, Upgrading and Tests.
- SB-A15 is "fixed in 3.3.0" in the inventory, and N31 is `*Done for 3.3.0.*`.
- The execution plan: relabel the P3 row as `P3 part 2, #<n>`, so the checker stops counting it, and update §9.
- The checker must then say 147.

## 5. If budget remains: P4

Audit accuracy, the checks the docs promise, its speed on large JSX, and SARIF output (SB-A11, SB-A25, SB-C10), all in `audit_design.py`. Read the three items in `studio-build.md` (lines 27, 55 and 77) first. SB-C10's line lookup may already be done: `audit_js` builds `line_of` with `bisect`, so measure before changing it. Its `--files-from -` and SARIF output are not done. Start P4 only with about 200 thousand tokens left; otherwise go to §6.

## 6. End of session (never skip)

1. Rewrite `docs/HANDOFF.md`: one page, with the state, next steps, blockers and warnings.
2. Update `CLAUDE.md`'s Current State, the execution plan's §9, and the inventory.
3. **Rewrite this file** for the session after yours: the next PRs in the same detail as §4 here.
4. Run `python -B "dev plans/check_execution_plan.py"`.
5. Commit the docs to the top branch of the stack (or `main`'s next branch), then tell the user what merged, what is open, the token use, and what they need to do. Give them the opening prompt for the next session, naming the branch these docs are on.
