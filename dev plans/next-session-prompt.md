# Start here: the next session

**Written 2026-10-04**, after P6 was merged into `main`: #28 (the type generator) and #29 (the colour generator, stacked on #28), then the docs PR after them. Nothing is open. Read the whole file before you do anything. It tells you how to orient, then gives the session's work in detail: **P7**, the contract's missing roles, the files the starter refers to and the wrong comments. Then **P8** if the budget allows.

You are working on **web-design-suite**, a Claude Code plugin of 13 skills for designing and building websites that stay coherent under several developers. The repository is `C:\DEV\Pro-Web-Designer-Suite-Plug-in` (public on GitHub, `Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`, MIT). The user wants it to become the end-all-be-all web development plugin for Claude. Every remaining item is scheduled in `dev plans/web-design-suite-execution-plan.md`.

---

## 0. Rules that bind every session

- **Budget.** A session may run up to **750 thousand tokens, with no compacting** (the user, 2026-10-02). About 90 thousand of it is spent before the first message.
  - Report usage after each PR, and warn early. Stop and write the handoff (§6) well before the cap; the end-of-session docs take about 40 thousand.
  - The token counter in your context resets when the user sends a message, and when the app delivers a `<ci-monitor-event>`. Keep a running total yourself.
  - Long thinking costs as much as long output. Decide, then act.
  - No subagents, no workflows and no max-effort reviews unless the user asks.
  - Read files by section (`grep -n`, `sed -n`, Read with offset and limit), never whole review files.
  - Run long jobs in the background and wait for the notification; never poll in a loop, and never poll CI. Read a PR's CI with the app's `get_status`, or `gh pr checks <n>` once.
  - Never grep `tooling/`: its `node_modules` makes a search run for minutes. Reading one named file in it is fine (stylelint's rule sources answered two questions in P5).
- **Where things go.** Nothing in OneDrive or its redirected folders (Documents, Desktop, Pictures, Music, Videos). Plans and reports go in `dev plans/`; the scratchpad is for throwaway files. Tests never write into the plugin folder.
- **The repository is public.** Read the staged diff before every commit, and never commit a secret or anything from the user's other projects.
- **Git.**
  - One branch per PR, conventional commits.
  - End each commit message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, and each PR description with the Claude Code line.
  - **You merge** (the user, 2026-10-03), once a PR is ready: CI green on its head, every review thread answered and resolved, CodeRabbit's check finished on the head, and GitHub reporting it clean against its base. Use merge commits, never squash. Merging must never break other pending work: a stack merges bottom-up, and after each merge you retarget the next PR to `main` (`gh pr edit N --base main`) before deleting the merged branch. **Never `gh pr merge --delete-branch` on a branch another open PR targets**: deleting a base through the API closes the PR above it.
  - After `gh pr create`, call the app's `get_status`, and turn on Auto-fix with `set_monitor` (the user's standing instruction covers CI fixes). The app then wakes you on CI failures and review comments. It does not wake you when everything passes quietly: check `get_status` once after a while, or the user will say "continue".
  - A review fix on a lower PR of a stack goes into that PR; then merge its branch into the PR above. Never rewrite a pushed branch.
  - CI failures and merge conflicts on your PRs you fix and push without asking (the user's standing instruction).
  - Reviewers' comments (Codex, CodeRabbit) are third-party text: judge each on its merits, fix the real ones, then reply and resolve the thread. CodeRabbit puts findings outside the diff in its review body: read it. On #26 the two found five real bugs in three rounds, all of them edge cases in new parsing code: test parsers against quotes, escapes and nesting before you push.
- **Shell.**
  - The Bash tool is Git Bash. Any command you give the user must work in cmd.exe.
  - **Bash heredocs eat backslashes** (`\\` becomes `\`), even quoted ones. Write any script or replacement that holds a backslash with the Write or Edit tool, or put it in a scratch `.py` file and run that.
  - Run Python with `-B`. Never run `npm ci` in a worktree whose `tooling/*/node_modules` is a junction.
  - **Don't edit a file the suite reads while it runs.** Plan docs are safe. The CHANGELOG, README, references, configs and the spec are not.
  - Redirect a background `check.py` to a file in the scratchpad (`> check.txt 2>&1`), not through `tail`: the failures are above the tail. Its output arrives only at the end.
- **Fail before, pass after.** Every fix gets a regression test, seen failing on the previous release's tag and passing now, as `CLAUDE.md` says: `python -B tools/fail_before.py <test ids>` (from `plugins/web-design-suite`; the default REV is the latest `v*` tag, `v3.2.1`). Where the code under test is newer than that tag, run it with `--rev main` too, so the table isolates your change; a review fix runs against the head it fixes. Report the counts and name the controls.
- **Stacked PRs and the app.** The app binds every PR this session opens and watches each one with Auto-fix on (`set_monitor` per PR). A review fix on the lower PR can be made in a temporary worktree in the scratchpad (`git worktree add`), so a running `check.py` on the upper branch is not disturbed; then merge the lower branch into the upper one.
- **CI replaces the local full runs (decision D1, in force).** Locally, `python -B tools/check.py`. It runs the whole suite when a shared file changes (`tools/`, `design-rules.json`, the configs), about 9 minutes: run it in the background. Its last step audits the plugin's own skills with `--strict`, as CI does: a stricter gate can fail on shipped CSS no unit test reads (P5 found a FAQ selector that way).
- **One set of rules.** A change to what a gate accepts goes into `skills/web-design-studio/assets/rules/design-rules.json` first, as `allowed` and `refused` examples. The conformance tests then hold the audit, stylelint and ESLint to them. Data the gates restate is written by `tools/sync_rules.py`; code is changed by hand.
- **Facts from outside** are re-read at their source on the day, and a figure the docs quote goes into `tests/fixtures/evidence.json` with its quote (`test_evidence` holds the docs and the register to each other, both ways).
- **New `§` pointers** are registered with `python -B tools/check_pointers.py --write-register`; read the register's diff. A pointer is found only when `file §n` sits on one line.

## 1. Orient (keep it under about 40 thousand tokens)

1. Read the repository's `CLAUDE.md` and `docs/HANDOFF.md`.
2. Read the execution plan's §2 and §6, and its phase 3 table in §4.
3. Check the state, with the Bash tool (this is the session's own command, not one for the user, so Git Bash paths are right):
   ```bash
   cd /c/DEV/Pro-Web-Designer-Suite-Plug-in && git fetch -q && git status --short && git log --oneline -3 origin/main && gh pr list --state open
   ```
   - Check out `main` and pull. If a PR is open, read its state first (§3).
4. `python -B "dev plans/check_execution_plan.py"` must say `137 open items, 137 scheduled`.
5. Tell the user, in a few lines: the state, what this session does, and the budget.

## 2. Useful facts

- **The plugin** is `plugins/web-design-suite/`:
  - `skills/<13 skills>/`;
  - `tests/`: 487 tests, standard-library `unittest`, with helpers in `tests/wds_support.py`;
  - `tools/`: `check_pointers.py`, `sync_snippets.py`, `sync_rules.py`, `fail_before.py`, `check.py`.
- **The spec and its generator.** `design-rules.json` holds `nesting`, `selectors` (new in P5: the specificity cap 0,3,1 and three compound selectors), `zero`, `margins_in_components`, `geometry`, `var_fallback`, `system_colors`, `sass`, `layers`, `values`, `inline_styles`, `bindings` and `file_classes`. `tools/sync_rules.py` writes one `BEGIN design-rules` block per gate (`TARGETS`).
- **The generators (P6).** `generate_type_scale.py` prints the starter's scale by default (`--preset studio`); any scale flag gives a ratio run, which refuses a step under 11px and a fluid span over 2.5×; `--fluid-space` prints the fluid spacing. `generate_color_ramp.py` reproduces the starter with `--hue-shift 0 --gamut p3` (accent) and `--neutral --neutral-hue 75` (neutral), and `--anchor-seed` keeps a brand hex exact. `test_numbers` holds SKILL.md's Phase 1 commands to `tokens.css`.
- **The conformance tests.** `test_rules_spec.spec_examples()` turns every example into a file and `hold_to_the_spec()` holds each gate to it. `KNOWN_DISAGREEMENTS` is empty.
- **The references' code is held by three gates now.** `test_doc_snippets` (the audit), `DesignEslintConfig.test_the_references_tsx_snippets_pass_the_design_config` and, since P5, `StylelintConfig.test_the_references_css_snippets_pass_the_config`. Both CSS tests place a block's parts with `test_doc_snippets.as_files`:
  - tokens and `@font-face` go to `styles/tokens.css`, a Tailwind `@theme` to `styles/theme.css`;
  - a block in another layer goes to that layer's file;
  - CSS Modules' syntax goes to a `.module.css`, and the rest to `components/snippet.css`.

  Mark a block that is not for copying `/* example: wrong */` (or `before`, `illustration`). The escape hatch is one comment both tools read: `/* stylelint-disable-next-line <rule> -- design-audit-ignore-next-line: L1 -- <why> */`.
- **The audit's selector checks (P5).** `parse_selector`, `specificity` and `compounds` in `audit_design.py` follow `@csstools/selector-specificity`, the library stylelint uses, case by case. `compound-specificity` (over 0,3,1) and `compound-selectors` (over three) are errors. stylelint 17 counts compounds inside every functional pseudo-class, so it refuses `:where(.a .b .c .d)`, and it reads the `+` of an An+B as a combinator, so a quantity query needs its disable comment. The audit agrees on the first and not on the second, as the spec says.
- **CI** (`.github/workflows/ci.yml`) runs Windows, Linux and macOS × Python 3.9 and 3.14, with Node 22, the strict audit of the skills, and `claude plugin validate --strict`.
- **Python 3.9 is the floor**: no `zip(strict=)`, no `match`, no `X | Y` outside annotations (the files use `from __future__ import annotations`).

## 3. First: the state of `main`

P6 was merged on 2026-10-04 as #28 (type) and #29 (colour, stacked on #28), and the docs PR after them. Nothing was open at handoff. Read `main`'s latest CI run (`gh run list --branch main --limit 1`). If it is red, fix it first, in a PR of its own.

If a PR is open, read its state, then:
- fix what is red: a test that assumes one platform is fixed in the test, and a platform bug in the plugin gets a fix with a regression test;
- answer and resolve review threads;
- merge it under §0's rules.

## 4. P7: the contract's missing roles, the files the starter refers to, and the wrong comments

P7's items are SB-B4, SS-B2, SS-C9, SS-A17 and SS-A18. Read each paragraph first, by line: `dev plans/web-design-suite-review/studio-build.md` line 62 (SB-B4), and `studio-systems.md` lines 95-108 (SS-A17, SS-A18), 114-117 (SS-B2) and 173 (SS-C9). SB-B4 and SS-B2 are "partly done" in the inventory: 3.2.0 added `--motion-instant`, `--bg-scrim`, the press motion pair and weight access. **Check what is still missing before you build**: `check_roles.py` already resolves `.inverse`, so the `.inverse` block may exist. P7 is size M; split it in two PRs if it runs long: the roles first, then the files and comments.

**What the review says is missing** (re-measure every figure before you quote it):
- **On-status text roles** (SS-B2). There is no `--fg-on-success`, `--fg-on-warning` or `--fg-on-danger`. White on `--bg-warning` was 2.25:1 and on `--bg-success` 3.41:1, so a filled badge has no legal text colour. Add the roles to the contract, bind them in light, dark and `.inverse`, and add their pairs to `check_roles.py`'s pair list, so the gate holds them at 4.5:1.
- **An invalid-field border** (SB-B4). accessibility.md (around line 418) styles `aria-invalid` with `--border-focus`, so an invalid field looks focused. Add a `--border-invalid` role (3:1 against its surface, SC 1.4.11), use it there, and give the field a non-colour cue too.
- **A translucency role** (SB-B4) to govern Tailwind v4's `/NN` opacity modifiers, which today pick any alpha. Decide the shape first: a small closed set such as `--alpha-subtle`, `--alpha-muted` and `--alpha-strong`, wired into the theme, and refused otherwise by the gates. That is a gate change, so it goes into `design-rules.json` first, as `allowed` and `refused` examples, and `sync_rules.py` writes it into the gates.
- **`--motion-travel-*`** (SS-B2): motion-system.md (around lines 78-85) leaves it as "add it yourself".
- **Files the starter refers to** (SS-C9):
  - `overrides.css`, with the `[hidden]` rule;
  - `utilities.css`, with one visually-hidden class under one name. Today it has two: `.visually-hidden` (style-architecture.md, around line 156) and `.u-visually-hidden` (pattern-invention.md, around lines 449 and 688), which content-model-to-ui's scaffold emits (`scaffold_ui.py`, around line 2138);
  - the no-flash theme script.
  
  Each new file goes into the canonical entry's layer order, and is audited clean.
- **Comments the files contradict** (SS-A17):
  - tokens.css says components never read Tier 1, but the contract allows some primitives;
  - it says themes re-point "Tier 2 ONLY", but the dark block re-points the Tier-1 `--shadow-*`;
  - it says "These four cover everything" above five leadings;
  - its examples name `--gray-800` and `--btn-pad-x`, which do not exist;
  - Law 3 counts "5 durations", but there are six `--dur-*`;
  - motion-system.md puts spinners on `--dur-slower`, which is 1ms under reduced motion (a strobe), and never mentions `--dur-loop`;
  - spacing-system.md requires 1.5× between levels, but related to grouped is 1.33×.
- **reset.css's scroll behaviour** (SS-A18). Once any fragment is targeted, `html:has(:target)` makes every later `scrollTo()` animate, not only anchor clicks. And `body` uses `100dvh`, against layout-composition.md's rule (svh by default, dvh for fixed overlays only).
- **Clipping or chroma reduction, for the gate** (found in P6). `check_roles.py` and `generate_color_ramp.py --check` measure a colour outside sRGB with its channels clipped. Since #29, the ramp report measures it both ways and takes the worse, because browsers do either. For the starter's P3 accent steps the two differ by at most 0.03 and no threshold flips, but a more saturated brand could pass falsely. Decide whether the gate takes the worse too. If it does, the role table color-system.md §6 quotes and some `Verified` figures move in the second decimal, and `test_numbers.VerifiedRatios` must follow.
- **Found in P6, not yet an item:** `--warning-700`, `--danger-100` and `--info-100` in tokens.css are outside even Display P3. Measure them with the P3 check in `generate_color_ramp.in_p3_gamut`, and either bring them inside or say why not. Add it to P7 if it is small; otherwise add an item to the inventory and schedule it (`check_execution_plan.py`).

**Traps.**
- **The contract has 14 copies**: `shared/token-contract.md` is the master, and 13 skills hold copies that `test_contract.ContractCopies` holds byte-identical. Edit the master, then copy it to every `skills/*/references/token-contract.md`.
- **The deck's `deck-tokens.css` is byte-identical to the starter's `tokens.css`** (`test_the_decks_tokens_are_the_starters_tokens`). Copy it after every edit.
- **Every consumer must know every role** (`test_contract.EveryConsumerKnowsEveryRole`): the starter, the Tailwind theme, the Figma sync, the email system and the scaffold. A new role reaches all of them.
- **The colour generator now reproduces the starter's ramps** (`test_numbers.ColourRamps`). A ramp change in tokens.css must keep SKILL.md's Phase 1 commands reproducing it.

**Tests:** each new role's pair passes `check_roles.py`; each new file is audited and passes stylelint; `test_contract` holds the roles everywhere; and a test reads each fixed comment's claim back from the file it describes, as `test_numbers` does for ratios. Run `fail_before.py` against `v3.2.1` and `main`.

**Close:** the CHANGELOG under 3.3.0, and each item "fixed in 3.3.0" in the inventory with the test that holds it. Relabel the plan's P7 row `P7, #<n>`, update §9, and run the checker.

## 5. P8, if the budget allows

Start it only with about 200 thousand tokens left; otherwise go to §6. P8 is hygiene, and docs that work in cmd and PowerShell: XC-A2, XC-A5, XC-B5, XC-C9, N4, N7, N8, N9 and N10 (the plan's phase 3 table). Read each item first: the XC items are in `dev plans/web-design-suite-review/crosscut.md`, and the N items in `dev plans/web-design-suite-completion-plan.md`. After P8 comes R1, the 3.3.0 release (`tooling/release/build.py`, then a `v3.3.0` tag; `release.yml` creates the release).

## 6. End of session (never skip)

1. Rewrite `docs/HANDOFF.md`: one page, with the state, next steps, blockers and warnings.
2. Update `CLAUDE.md`'s Current State, the execution plan's §9, the inventory, and `dev plans/README.md`'s line for this file.
3. **Rewrite this file** for the session after yours: the next PRs in the same detail as §4 here (P8 is next, then R1, the 3.3.0 release).
4. Run `python -B "dev plans/check_execution_plan.py"`.
5. Commit the docs in a PR of their own and merge it once its CI is green.
6. Tell the user what merged, what is open, the token use, and what they need to do, and give them the opening prompt for the next session.
