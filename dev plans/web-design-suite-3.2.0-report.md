# web-design-suite 3.2.0: phase 2 report

**2026-09-25.** Phase 2 of the [review](web-design-suite-review.md), carried out to the [plan](web-design-suite-3.2.0-plan.md). The plugin installed on this machine is now 3.2.0.

## Summary

- **Scope.** Phase 2 is complete: all 15 plan items. Phase 2 ties the docs to the code. Tests now take the commands, configs, code blocks, figures and § pointers out of the docs themselves, and check them against the scripts, a real browser and the real tools. The fixes followed from what those tests found.
- **Tests.** The suite grew from 151 to **296 tests**. Every new test was run against the unchanged 3.1.0 plugin. 121 of the 145 new tests fail there and pass here. The other 24 are controls and guards, listed under Evidence; they pass on both versions by design.
- **Facts re-checked at the source.** Every fact the docs now state from outside the plugin was read at its source on 2026-09-25, and the test that holds it records the source and the date. That includes regulations, standards, surveys, registries, browser data and vendor docs. Where the review was wrong, the doc says what was measured instead.

## Where everything is

| What | Where |
|---|---|
| The installed plugin. Sessions load it from this folder, so it must stay here. | `C:\Users\vybec\.claude\local-marketplaces\web-design-suite` |
| Patch, 3.1.0 → 3.2.0 | `C:\Users\vybec\.claude\local-marketplaces\web-design-suite-3.1.0-to-3.2.0.patch`: 122 files (26 of them new, none deleted), 819,500 bytes, SHA-256 `4fc06ce6078a76b6a80de03af3932eec7cb1159a46ab3ed28597150130d2fc5f` |
| Package | `C:\Users\vybec\Downloads\web-design-suite-plugin-3.2.0.zip`: 225 entries (3.1.0 had 196), 1,559,731 bytes, SHA-256 `0c116bd3bfaf4a4637ecde59f8e19b5bc4fa0bb48d6d5eb68e31d4413860a263` |
| Release notes | `CHANGELOG.md` in the plugin |
| Plan, with status and notes on what was done along the way | [web-design-suite-3.2.0-plan.md](web-design-suite-3.2.0-plan.md) |

## Before you use it

1. **Open a new Claude Code session.** A session that is already running keeps the 3.1.0 skill text it loaded.
2. **Reinstall the pre-commit hook, as two hooks.** Where you copied it before, copy it again, to `.git/hooks/pre-commit` and to `.git/hooks/commit-msg`. The hook now **fails** when a stage cannot run, where it used to skip:
   - no stylelint config;
   - no `scripts/audit_design.py`;
   - no Python.

   Set `DESIGN_GATE_ALLOW_SKIP=1` while you adopt a stage. Configs are looked for at the repo root first.
3. **Re-baseline projects that use the design gate.** The audit now reads:
   - class strings inside `cn()`, `clsx()`, `cva()` and the other class helpers;
   - every Tailwind arbitrary value, except variants, image URLs and content strings;
   - arbitrary properties and the v4 `!` suffix;
   - styled-components and emotion templates.

   To freeze the existing debt, run this from the project root:

   ```bash
   python C:\Users\vybec\.claude\local-marketplaces\web-design-suite\skills\web-design-studio\scripts\audit_design.py src --write-baseline .design-baseline.json
   ```

4. **Rename in Tailwind projects.** The width utility `border-default` is now `border-stroke`. The old one also painted the border colour.
5. **The claude.ai source may still be 3.0.0.** A zip built there would lose all three rounds of fixes. Diff it against the three patches first.

To upgrade another copy of 3.1.0, run this from the folder that holds `.claude-plugin`:

```bash
git -c core.autocrlf=false apply C:\Users\vybec\.claude\local-marketplaces\web-design-suite-3.1.0-to-3.2.0.patch
```

## What was done

Item by item. The plan's "Done along the way" notes have the detail, and each test file's docstring lists its regressions by review ID.

| # | Work | Tests |
|---|---|---|
| 1 | Every CSS, TSX and JSX block in the references passes the audit, or says why not (`example: wrong / before / illustration`) | `test_doc_snippets` |
| 2 | Quoted starter code stays identical to its region in the starter (`tools/sync_snippets.py`) | `test_doc_snippets.QuotedStarterCode` |
| 3 | Every "Verified n:1" is recomputed and every `clamp()` anchor solved | `test_numbers` |
| 4 | Every documented flag exists in its script's own parser | `test_docs.DocumentedFlags` |
| 5 | Every § pointer resolves. The 300 cross-file pointers land on the heading they were checked against (`tools/check_pointers.py`) | `test_pointers` |
| 6 | The 14 token-contract copies are identical, and every consumer knows every role | `test_contract` |
| 7 | Real tools: ESLint on 9.39.5 and 10.4.0, a Tailwind v4 compile, tailwind-merge, and Chromium for the focus-ring caveat | `test_real_tools`, `test_starter_css` |
| 8 | `check_roles.py`: role-pair contrast in four themes, an opt-in hook stage, and the generator of color-system.md §6 | `test_check_roles` |
| 9 | One rule spec, `assets/rules/design-rules.json` | `test_rules_spec` |
| 10 | Recipes that run as written: the drift gate, JSONC budgets, the CI workflows, the navigation code, `@property`, versions | `test_recipes` |
| 11 | Docs that are true: the a11y runtime and coverage, VPAT, container queries, subgrid, SC levels, legal baselines, colour science, email clients, Gmail's ceiling, Outlook dates, Figma, Bootstrap, MUI, README | `test_facts` |
| 12 | The evidence register, `tests/fixtures/evidence.json` | `test_evidence` |
| 13 | Every SKILL.md fits after compaction; references fit one Read; descriptions of 301–368 characters with "Not for" | `test_skill_budget` |
| 14 | Hook hardening, and the audit reads class helpers, v4 syntax and CSS-in-JS | `test_precommit_hook`, `test_audit_design.JsxClassesAndCssInJs` |
| 15 | Version, CHANGELOG, patch, zip, this report | this file |

### Where the work departed from the plan, or from the review

- **Item 9 shipped as a spec plus tests, not a generator.** The plan named a `tools/sync_rules.py --check` that would generate config sections from the spec. What shipped is `test_rules_spec.py`: it holds the audit's behaviour, the stylelint config's patterns and globs, and the docs to the spec. There is no ESLint conformance class; ESLint's style rules are covered by `test_real_tools`.
- **The review was wrong once.** It said a hand-set `aria-expanded` on a popover invoker overrides the browser's. In Chromium 153 the browser's state wins, even after light dismiss, so the doc says what was measured.
- **Left out because they could not be confirmed:** the Figma MCP "Starter: 6 calls a month" limit, and a March 2027 enterprise date for new Outlook.
- **Found beyond the review, and fixed:**
  - `build_docs --check` passed silently when the named baseline was missing, so the documented drift gate compared nothing;
  - all three proof-sheet marks failed contrast, where the review had found one;
  - a second "30–40% of the criteria" claim;
  - Baymard's checkout figures;
  - the Apple MPP range, which had no source;
  - the Read tool truncating navigation-patterns.md.

## Evidence

### Test runs

Each run was from the plugin root, with `PYTHONDONTWRITEBYTECODE=1` and these tool roots, all read-only:
- `WDS_NODE_MODULES`: Playwright 1.63 and axe-core 4.13 from `C:\DEV\audio-promptmonster\frontend\node_modules`;
- `WDS_ESLINT_MODULES`: ESLint 10.4.0 from ActiveAura, then jsx-a11y and typescript-eslint from LaunchOps;
- `WDS_TAILWIND_MODULES`: Tailwind 4.3.0 from ActiveAura.

Nothing was installed or downloaded.

| Command | Python | Result |
|---|---|---|
| `py -3.14 -m unittest discover -s tests` | 3.14.5 | Ran 296 tests in 138.2 s: **OK** |
| `py -3.12 -m unittest discover -s tests` | 3.12.10 | Ran 296 tests in 161.6 s: **OK** |
| The same suite with `WDS_PLUGIN_ROOT` set to an unpacked 3.1.0 | 3.14.5 | Ran 296 tests in 129.7 s: **FAILED (failures=287, errors=4)**, as intended |

The last two ran side by side. No test was skipped in any run.

After the release, the suite also ran on Linux: WSL2 Ubuntu, Python 3.14.4, with dash as `/bin/sh`.
- Result: 296 tests in 93.4 s, **OK**, with 37 skipped.
- Every skip is a browser, Node or real-tool test, because that Linux has no Node.
- All the hook's tests ran.

Against 3.1.0:
- 121 of the 145 new tests fail: 287 failures and 4 errors, counting sub-tests. The errors come from files 3.1.0 does not have. Three tests read `references/navigation-code.md`, and one calls `perf_audit.read_jsonc`.
- None of 3.1.0's own 151 tests fails.
- The other 24 new tests pass on both versions by design; see "Controls and guards" below.

### Controls and guards

24 of the 145 new tests pass on 3.1.0, and are meant to.

**9 controls.** Each is the other half of a test that fails on 3.1.0. It shows that a fix does not overreach, or that a scan found something to check:
- `JsxClassesAndCssInJs.test_clean_helpers_and_templates_stay_clean`: clean class helpers and CSS-in-JS templates produce no findings.
- `PerfBudgetFile.test_the_documented_budget_parses_before_the_browser_starts`: a valid JSONC budget still reaches the browser. It passes on 3.1.0 only because 3.1.0 started the browser before it read the budget at all. Its partner, `test_the_lab_budget_is_read_before_any_browser_starts`, fails there.
- `PreCommitHook.test_the_role_stage_is_opt_in` and `test_the_starters_palette_passes_the_role_stage`: the new role stage runs only when asked, and the starter's palette passes it. 3.1.0 has no role stage, so both pass there trivially.
- These four show that each scan finds what it checks, so the other checks cannot pass on nothing:
  - `SectionPointers.test_the_tool_still_finds_the_pointers`;
  - `CiRecipes.test_the_docs_ship_workflows`;
  - `PropertyRecipe.test_the_recipe_registers_something`;
  - `RuntimePromises.test_the_code_still_presses_what_the_test_says`.
- `EvidenceRegister.test_every_entry_is_complete_and_its_quote_carries_its_numbers`: this checks the register itself, which lives in `tests/`.

**15 guards.** Each holds a property that 3.1.0 already had:
- `test_contract` (3): the 14 contract copies are identical, the deck's tokens are the starter's, and the starter declares every role.
- `QuotedStarterCode`: the starter passes its own audit.
- `DocumentedFlags`: every documented flag exists. It was shown to fail by mutation.
- `SkillFrontmatter`: every SKILL.md frontmatter parses.
- `LayoutInABrowser`: container queries and subgrid behave in Chromium as the docs now say.
- `DesignEslintConfig` (3): the ESLint config refuses plain style properties and literal utilities, and jsx-a11y runs under ESLint 10.
- `TailwindTheme` (3): role classes generate, off-scale classes generate nothing, and literal utilities still generate.
- `CiRecipes`: every CI run step passes `bash -n`.
- `StylelintFollowsTheSpec`: the nesting limit matches the spec.

Two more guard assertions sit inside tests that do fail on 3.1.0: the browser half of the popover test, and the sideways-switch check in the navigation code.

### Other checks

- `audit_design.py skills --strict` on the plugin's own CSS and JS: clean, L1–L6, across 13 files. The 3 email templates are skipped with a pointer to `lint_email`.
- `claude plugin validate --strict` (bundled CLI 2.1.281) passed for the marketplace, and separately for `plugin.json`.
- **Patch.** Built from pristine 3.1.0 and the 3.2.0 tree. Applied with `git -c core.autocrlf=false apply` to a fresh extraction of the 3.1.0 zip; `diff -r` against the installed plugin shows no differences.
- **Zip.** Built with the 3.1.0 zip's layout; `testzip` OK. Extracted, then `diff -r` against the installed plugin: no differences.
- **Install.** `claude plugin update` reports the plugin already at 3.2.0: the version was bumped and updated earlier the same day. `claude plugin details` lists 13 skills.
  - About 1,181 tokens are always on.
  - Each skill costs 4.4k–5.0k tokens when invoked. design-system-docs is the smallest, and three are at about 5k: design-system-versioning, email-template-system and landing-page-conversion.
  - landing-page-conversion was about 6.6k at 3.1.0.
- **The plugin cache is out of date.** The copy under `~/.claude/plugins/cache/web-design-suite/web-design-suite/3.2.0` was taken before the last trim, and 10 files differ. Sessions load the plugin from `local-marketplaces`, not from that copy. The next version bump refreshes it.

## What was not tested

- **stylelint.** Not installed anywhere on this machine. The stylelint 17 config text is checked against the registry and the migration guide, not run, and the rule-spec conformance for stylelint reads the config's patterns rather than linting fixtures.
- **eslint-plugin-tailwindcss 4.x.** Not installed. The Part 5 blocks are checked against its 4.4.0 README.
- **GitHub Actions.** The workflows are checked statically: actions on Node 24 majors, bash, a waited-for server, the pinned browser, and every step passing `bash -n`. None was run on a runner.
- **Email clients.** No live Outlook or Gmail. The client matrix follows caniemail's raw data as read on 2026-09-25.
- **Other browsers and systems.**
  - The browser tests ran in Chromium on Windows 11 only.
  - The rest of the suite also ran on Linux. Nothing ran on macOS.
  - Firefox and Safari behaviour in the docs comes from their vendors' and caniemail's data.
- **Python versions.** Only 3.12 and 3.14 ran. The README asks for "Python 3" without a minimum.
- **Token counts.** Read and compaction limits are estimated from two measured points, not from the tokenizer. `accessibility.md`, at 60.1 KB, is within about 2% of where navigation-patterns.md was truncated; split it before it grows.

## Next: phase 3 (3.3.0)

The roadmap's phase 3 makes it a full Claude Code plugin: the opt-in hook, workflow commands, subagents, the project contract, evals and release tooling (C6–C13). The evidence register and the pointer register are the fixtures an eval suite can build on.

Carried over from phase 2:
- Run stylelint 17 and eslint-plugin-tailwindcss 4.x for real. That needs your permission, because installing them is a download.
- Item 9's generator, `tools/sync_rules.py`, and ESLint conformance fixtures.
- Split `accessibility.md` before it passes the Read limit.

Still open from the review:
- **64 of its 138 issues:** 37 medium and 27 low, none high. No phase of the roadmap covers them.
- **The review's ✔ marks are out of date.** GT-A2 and SB-A7 were fixed in 3.1.0 but never ticked, and phase 2's fixes have no ticks at all. The counts above come from the two plans and the 3.1.0 report, not from the ticks.
