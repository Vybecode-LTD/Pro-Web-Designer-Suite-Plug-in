# web-design-suite: every review item, and where it stands

The status of all 265 items in the [review](web-design-suite-review.md) after 3.2.1. It replaces the review's own ✔ marks, which stopped being kept up to date. The [completion plan](web-design-suite-completion-plan.md) says what each workstream (W1–W14) does. When an item is fixed, change its row here: *fixed in* the release, and the test that holds it.

| ID | Severity or size | Status | What is wrong or missing |
|---|---|---|---|
| XC-A1 | medium | fixed in 3.1.0 | "Quick start on an inherited codebase" fails as |
| XC-A2 | low | fixed in 3.3.0: `test_docs.PasteableCommands` (PR #35) | The README's install instructions use a placeholder. |
| XC-A3 | medium | fixed in 3.2.0 | "any single `.skill` file works standalone" and "each |
| XC-A4 | low | fixed in 3.1.0 | Packaging: running a script the documented way (`python -m scripts.X`) writes bytecode into the plugin. |
| XC-A5 | low | fixed in 3.3.0: `test_contract.ContractCopies` (PR #34) | `shared/token-contract.md` is referenced by nothing, and its role as the master copy is not stated. |
| XC-A6 | medium | fixed in 3.1.0 | a11y_static is quadratic on large inputs. |
| XC-A7 | medium | fixed in 3.1.0 | super-linear on long lines, which is what minified CSS looks like: 96 KB on one line 1.5 s, |
| XC-A8 | medium | fixed in 3.1.0 | the invocation contract is ambiguous. |
| XC-A9 | medium | fixed in 3.1.0 | Audit baseline keys stop matching when the same folder is spelled differently. |
| XC-B1 | — | W9 (3.5.0) | The plugin ships only skills: no agents, hooks, commands or MCP/LSP servers, so Law 9 is never applied to Claude's own edits. |
| XC-B2 | — | W9 (3.5.0) | No eval suite, so nothing shows the skills fire on the right prompts or beat the no-plugin baseline. |
| XC-B3 | — | fixed in 3.3.0: `.github/workflows/ci.yml` runs the suite and the static checks on Windows, Linux and macOS, at Python 3.9 and 3.14, with Node (PR #17); the floor is declared since PR #4 | The tests are regression and guard tests only: no smoke test per documented command, no CI, no declared minimum Python. |
| XC-B4 | — | fixed in 3.1.0 (CHANGELOG) and 3.2.1 (CLAUDE.md for contributors) | no CHANGELOG (the suite teaches semver and changelogs for design systems but keeps |
| XC-B5 | — | fixed in 3.3.0 for what a person pastes, the READMEs; the skills' docs stay bash, which Claude Code runs them in: `test_docs.PasteableCommands` (PR #35) | The docs are bash-first (backslash continuations, `&&`, `/tmp/`, `$(…)`, `python3`): fine through Git Bash, broken when pasted into cmd or PowerShell 5.1. |
| XC-B6 | — | fixed in 3.2.0 | discoverability in a heavy environment: in this machine's sessions the 13 skills |
| XC-C1 | L · high | W9 (3.5.0) | An eval suite (`evals/`): per-skill triggering cases and outcome graders, run with ablation, in CI with a cost ceiling. |
| XC-C2 | M · high | W9 (3.5.0) | An opt-in design-gate hook: PostToolUse on Edit/Write runs `audit_design` on the changed file and returns the findings to Claude. |
| XC-C3 | M · high | W9 (3.5.0) | User-invocable workflows as skills with `disable-model-invocation: true`: /gate, /install-gate, /critique, /new-system and more. |
| XC-C4 | M · medium | W9 (3.5.0) | Subagents (design-critic, a11y-auditor), so heavy references load in an isolated context. |
| XC-C5 | S · high | fixed in 3.2.0 | promote this review's harnesses to permanent tests: every documented |
| XC-C6 | M · medium | fixed in 3.3.0: `tooling/release/build.py` (`test_release_build`), `.github/workflows/ci.yml` and `release.yml` (PR #17). The evals join CI with P29 | Build and release: a build tool for the zip and the 13 `.skill` files, `claude plugin tag`, and a CI matrix of Windows/Linux/macOS × Python 3.9–3.14 with Node. |
| XC-C7 | M · medium | fixed in 3.2.0 | token efficiency: SKILL.md files are 17–28 KB (≈4.4–6.9k tokens per |
| XC-C8 | M · medium | W9 (3.5.0) | One project config file, `.design-suite.json`, read by every script, the hook and the commands. |
| XC-C9 | S · low | fixed in 3.3.0: `WDS` in bash, PowerShell and cmd forms, one-line commands (`test_docs.PasteableCommands`, PR #35) | Cross-platform docs: PowerShell/cmd equivalents for the few shell-only recipes, or one `python -m scripts.gate` entry point. |
| XC-C10 | S · high | fixed in 3.1.0 (the review's C6) | fixes XC-A8: write every documented command as |
| SS-A1 | high | fixed in 3.1.0 | Law 7 (density) does nothing on a subtree, which is how every doc uses it. |
| SS-A2 | high | fixed in 3.1.0 | Where: reset.css:110 (`color-scheme: light`); tokens.css:425-471 (the dark block never sets `color-scheme`); tokens.css:473-480 (the OS media query flips the scheme but no tokens). |
| SS-A3 | high | fixed in 3.1.0 | The `hidden` attribute loses to every layout primitive. |
| SS-A4 | high | fixed in 3.1.0 | Shipped role pairs fail WCAG 2.2 AA, and no gate checks them. |
| SS-A5 | medium | fixed in 3.1.0 | Where: reset.css:452-453 (`dialog { max-inline-size: none; max-block-size: none }`). |
| SS-A6 | medium | fixed in 3.1.0 | The references' own CSS examples fail the plugin's gate. |
| SS-A7 | medium | fixed in 3.2.0 | Gap after a heading: 8px (spacing-system.md:454), 12px (typography.md:170), 16px (base.css:414-416), 12px (layout.css:264 .flow). |
| SS-A8 | medium | fixed in 3.2.0 | Role table (:280-295) vs tokens: light --bg-accent 500 (tokens: 600); dark --fg-muted 400 (300), dark --fg-subtle 500 (400), dark --border-focus 400 (never re-pointed, so 600). |
| SS-A9 | medium | fixed in 3.3.0: `test_numbers.TypeScale`, `ColourRamps` | Type: generate_type_scale.py:26-30 says --snap-px --fluid 380 1440 --fluid-steps 2 reproduces tokens.css "approximately". |
| SS-A10 | medium | fixed in 3.2.0 | The weight axis of the hierarchy method is illegal under L6. |
| SS-A11 | medium | fixed in 3.2.0 | The container-query containment facts are out of date. |
| SS-A12 | medium | fixed in 3.2.0 | style-architecture.md:361-366 uses initial-value: 1.5rem. |
| SS-A13 | medium | fixed in 3.2.0 | The colour-blindness safety claim is false. |
| SS-A14 | medium | fixed in 3.1.0 | Every command is python -m scripts.X (SKILL.md:66-72, :159-173; :58 even omits the path). |
| SS-A15 | low | fixed in 3.2.0 | The fluid spacing anchors aren't what the comments say, and typography's "sanity check" is stale. |
| SS-A16 | low | fixed in 3.2.0 | Factual slips (all verified). |
| SS-A17 | low | fixed in 3.3.0: `test_contract.TheStarterKeepsItsWord` | tokens.css:9 says components never read Tier 1, but the contract allows some primitives (token-contract.md:95). |
| SS-A18 | low | fixed in 3.3.0: `test_contract.TheStarterKeepsItsWord` | 374-384 says `html:has(:target)` limits smooth scrolling to anchor clicks. |
| SS-A19 | medium | fixed in 3.1.0 | Cause: audit_design.py:1040 reads utf-8 rather than utf-8-sig, so ﻿@layer counts as an unlayered rule. |
| SS-B1 | — | fixed in 3.2.0 | There is no gate for role-pair contrast. |
| SS-B2 | — | fixed in 3.3.0: `test_check_roles`, `test_figma_sync.StatusInks`, `test_contract.TheStarterKeepsItsWord` | Tier-2 roles and starter files are missing. |
| SS-B3 | — | W10 (3.6.0+) | Theming without JavaScript. |
| SS-B4 | — | W12 (3.6.0+) | Modern CSS the systems references should teach: `@starting-style`, the top layer against the z-index ladder, `cqi`, `font-size-adjust`, `color-mix()`. |
| SS-B5 | — | fixed in 3.3.0: `test_numbers.FluidTypeZoom`, `TypeScale.test_a_fluid_span_over_2_5_times_is_refused` | Fluid type and zoom (SC 1.4.4) is only half taught. |
| SS-B6 | — | fixed in 3.3.0: `test_numbers.ColourRamps` (`test_anchor_seed_*`, `test_the_report_gives_the_seeds_distance_from_500`) | The brand's exact colour isn't preserved. |
| SS-B7 | — | fixed in 3.3.0: `test_numbers.TypeScale`, `FluidTypeZoom`, `ColourRamps` | Nothing tests docs, tokens and generators against each other. |
| SS-C1 | — | fixed in 3.1.0, with SS-A1 to SS-A4 | Fix token resolution and test it in a browser (effort S–M, P0). |
| SS-C2 | — | fixed in 3.2.0 | As in SS-B1, wired into the audit and the pre-commit hook. |
| SS-C3 | — | fixed in 3.2.0 | Make the docs part of the test suite (S–M, P1). |
| SS-C4 | — | fixed in 3.2.0 | One source for shared CSS (M, P1). |
| SS-C5 | — | fixed in 3.3.0: `--preset studio`, the 11px refusal, `--fluid-space`, `--anchor-seed`, `--neutral-hue`, `--gamut p3` (`test_numbers.TypeScale`, `ColourRamps`) | Generator upgrades (M, P1). |
| SS-C6 | — | W9 (3.5.0) | Use Claude Code plugin features (M, P1). |
| SS-C7 | — | W9 (3.5.0) | An eval suite of script-graded cases, run against a no-plugin baseline. |
| SS-C8 | — | fixed in 3.2.0 | Size: 17.7 KB / 2,616 words ≈ 4.4k tokens. |
| SS-C9 | — | fixed in 3.3.0: `test_contract.TheStarterKeepsItsWord` | Ship what the starter refers to (S, P1). |
| SB-A1 | high | fixed in 3.1.0 | The canonical Button shows no focus ring when reached by keyboard. |
| SB-A2 | high | fixed in 3.1.0 | `@utility focus-ring { outline: none; box-shadow: var(--shadow-focus) }` takes away the forced-colors fallback. |
| SB-A3 | high | fixed in 3.1.0 | Any `var(` anywhere in a value turns off every L1 check for that declaration. |
| SB-A4 | high | fixed in 3.1.0 | `if prop in SPACING_PROPS and not in_query_prelude(d.at_rules)` skips every declaration inside `@media`, `@container` or `@supports`, not just the prelude. |
| SB-A5 | high | fixed in 3.1.0 | The v4 theme leaves literal values available that no gate stops, while the docs say they are gone or lint-banned. |
| SB-A6 | high | fixed in 3.1.0 | The handoff describes a token pipeline the suite does not ship. |
| SB-A7 | high | fixed in 3.1.0 | The claim "v3 emits into three native cascade layers" is false. |
| SB-A8 | medium | fixed in 3.3.0: `test_rules_spec` (`test_layers`, `TheDocsStateTheSpecsOrder`), `test_real_tools.StylelintConfig` | The canonical `index.css` puts third-party CSS on top of every layer. |
| SB-A9 | medium | fixed in 3.3.0: (a) to (c) by `test_audit_design.AuditPrecision` (`test_a_url_does_not_hide_the_rest_of_the_file`, `test_line_comments_stay_comments_where_they_are_comments`, `test_a_rule_after_a_closed_layer_is_unlayered`, `test_a_root_level_components_folder_holds_components`) and `test_rules_spec` `test_file_classes`; (d) is SS-A19, fixed in 3.1.0 | The scanner has bugs that hide violations. |
| SB-A10 | medium | fixed in 3.1.0 | The Tailwind and JSX checks date from v3 and catch less than ESLint. |
| SB-A11 | medium | fixed in 3.3.0: the audit diffs the breakpoints (L1 `breakpoint-drift`), and every other promise is corrected (`test_audit_design.ThePromisedChecks`), PR #24 | Docs promise checks that don't exist; for example, the audit does not diff `--breakpoint-*` against `--bp-*`. |
| SB-A12 | medium | fixed in 3.1.0 | "Off-scale classes … the build errors on them" and "`p-7` is a build error" are false. |
| SB-A13 | medium | fixed in 3.2.0 | `style-prop-custom-properties-only` rejects the legal pattern that the references document. |
| SB-A14 | medium | fixed in 3.2.0 | the three gates disagree about the laws |
| SB-A15 | medium | fixed in 3.3.0: every hole is examples in the spec, run through the audit and stylelint (`test_rules_spec.TheAuditFollowsTheSpec.test_every_example`, `test_real_tools.StylelintConfig.test_every_example_of_the_spec`, `test_theme_css_passes_the_override_that_guards_it`), PR #23. SCSS in stylelint is P37's (D3) | The stylelint allowlist has holes. |
| SB-A16 | medium | fixed in 3.1.0 | Five hook failures, all run in a scratch repo. |
| SB-A17 | medium | fixed in 3.2.0 | Several version facts are out of date (registry, 2026-09-23). |
| SB-A18 | medium | fixed in 3.2.0 | The documented tailwind-merge config drops classes. |
| SB-A19 | medium | fixed in 3.2.0 | `@utility border-default` collides with `--color-default`. |
| SB-A20 | medium | fixed in 3.2.0 | Defects in the reference code. |
| SB-A21 | medium | fixed in 3.2.0 | Stale or wrong facts. |
| SB-A22 | medium | fixed in 3.2.0, item 1 | the references' snippets fail the suite's own audit |
| SB-A23 | low-medium | fixed in 3.3.0: the canonical entries, quoted (`test_doc_snippets.QuotedStarterCode`) | The files disagree on how to wrap imports in layers. |
| SB-A24 | low-medium | fixed in 3.3.0: `test_audit_design.AuditPrecision` (`test_the_references_sass_partial_passes`, `test_a_mixin_is_checked_where_it_is_included`, `test_a_sass_variable_holding_a_literal_is_refused`, `test_sass_interpolation_opens_no_rule`, `test_indented_sass_is_skipped_not_passed`) and `test_rules_spec.test_sass` | SCSS: a `@mixin`-only partial fails L5, while `$card-padding: 24px` passes. |
| SB-A25 | low | fixed in 3.3.0: points 1, 3 and 4 by 3.2.1 (guarded by `test_audit_design`), 5 by PR #23, and the rest by PR #24 (`ThePromisedChecks`, `TheAuditInCi.test_where_adds_no_specificity`) | Smaller accuracy points: `url(#fade)` false positive, a zero-specificity warning, a pragma inside a multi-line comment. |
| SB-B1 | — | fixed in 3.1.0, with PS-A4 | templates aren't audited. |
| SB-B2 | — | fixed in 3.2.0 and 3.2.1 (real-tool tests) | no executable tests for the configs. |
| SB-B3 | — | fixed in 3.4.0: `test_browser_runtime.test_the_focus_ring_is_measured_at_each_density_the_page_declares` (PR #40) | focus, forced-colors and density aren't checked by any gate in the build flow. |
| SB-B4 | — | fixed in 3.3.0: `--border-invalid` (`test_contract.InvalidFieldsLookInvalid`, `test_check_roles`); translucency needs no role, since the ESLint config refuses `/NN` and names the roles | the contract is missing roles the references need. |
| SB-B5 | — | W12 (3.6.0+) | parts of Tailwind v4 aren't covered. |
| SB-B6 | — | W12 (3.6.0+) | SCSS and other stacks. |
| SB-C1 | S-M | fixed: 3.1.0 did SB-A3, A4 and A10, and 3.3.0 did SB-A9 and A24 | Fix the audit's precision (SB-A3, A4, A9, A10, A24) before wiring the PostToolUse hook. |
| SB-C2 | M · high | fixed in 3.3.0 (N2: PRs #18 and #19; `test_rules_spec`, `test_real_tools`, `test_tools.SyncRules`) | Write one machine-readable rule spec plus conformance fixtures, shared by audit_design, stylelint and ESLint. |
| SB-C3 | S-M · high | W12 (3.6.0+) | Ship a `tw_probe` script and a `/tw-probe` skill command. |
| SB-C4 | S · high | W12 (3.6.0+) | Replace Part 5 with eslint-plugin-better-tailwindcss 4.7 (peers ESLint 7–10 and Tailwind 3.3/4.1). |
| SB-C5 | S · high | fixed in 3.2.0 | Add doc-snippet CI: extract ```css/```tsx blocks, run audit + ESLint, and allow a `/* anti-example */` marker (extends XC-C5 and SS-C3). |
| SB-C6 | M · medium | W9 (3.5.0) | Add build-half cases to the XC-C1 eval suite: "Tailwind button with loading state", "vanilla card with stretched link", "mega menu", "add a vendor datepicker stylesheet". |
| SB-C7 | S · medium | fixed in 3.2.0 | Harden the hook: filter by extension; fail instead of skipping when a config is missing unless `DESIGN_GATE_ALLOW_SKIP=1`; resolve configs at the repo root with fallbacks; pass `--no-warn-ignored`; use `git rev-parse --g |
| SB-C8 | S · medium | fixed in 3.2.0 | Improve token efficiency (with XC-C7). |
| SB-C9 | S · medium | fixed in 3.3.0: `starter/styles/index.css` (vanilla and CSS Modules), `configs/index.tailwind.css` and `configs/index.tailwind-v3.css`, each quoted by the references (`sync_snippets.py`) and linted by `StylelintConfig.test_the_canonical_entries_pass` | Keep one canonical `index.css` per stack (vanilla, modules, Tailwind v4, Tailwind v3) in a single file that every reference points to, with the vendor layer and the forced-colors focus rule built in. |
| SB-C10 | S · low | fixed in 3.3.0: the line lookup was already a bisect; `--files-from` and `--sarif` (`test_audit_design.TheAuditInCi`), PR #24 | In `audit_js`, `line_of()` costs O(n) per finding: a 1 MB JSX file with 20k findings took 12.6 s, against 5.1 s for 0.9 MB of CSS with 40k findings. |
| LC-A1 | high | fixed in 3.1.0 | The docs say that if Figma's native DTCG export is live, "it works today". |
| LC-A2 | high | fixed in 3.1.0 | The docs say "Both scripts read" `VariableComposedColor`. |
| LC-A3 | high | fixed in 3.1.0 | The audit and the generator compare every file against the studio's own ramps, and no flag accepts the project's `tokens.css`. |
| LC-A4 | high | fixed in 3.1.0 | Generated `tokens.css` and `tokens.json` embed `generated <UTC minute>` and an ISO timestamp, so the documented CI drift check fails on an **unchanged** export. |
| LC-A5 | high | fixed in 3.1.0 | The reference says a `0 0 0 3px rgba()` focus ring "belongs to `--shadow-focus` … the classifier will get it wrong, so check for it". |
| LC-A6 | high | fixed in 3.1.0 | "Rebase daily, never merge", then resolve conflicts with `git checkout --theirs file` and re-run the codemod. |
| LC-A7 | medium | fixed in 3.2.0 | Two claims are out of date. |
| LC-A8 | medium | fixed in 3.4.0: `test_versioning.DiffSystemClassifiesWhatSystemJsonRecords` (PR #48) | The doc says density-scale changes, reduced-motion changes and root-element changes are "major · auto-detect yes". |
| LC-A9 | medium | fixed in 3.4.0: `test_versioning.DiffSystemClassifiesWhatSystemJsonRecords` (PR #48) | theme-override-added is classified minor, but it changes rendering in that theme, which is major by the file's own test (§11 Q2: "any theme"). |
| LC-A10 | medium | fixed in 3.1.0 | SvelteKit's `src/lib` is where its components live, and it is silently treated as vendor. |
| LC-A11 | medium | fixed in 3.4.0: `test_token_migration.MigrationPipeline.test_a_negative_cancel_points_at_its_parents_padding_token` (PR #49) | The reference says a negative cancel must "point at the **same token** the padding uses… Never" point elsewhere. |
| LC-A12 | medium | fixed in 3.4.0: `test_token_migration.MigrationPipeline.test_a_type_tie_snaps_up_even_when_the_smaller_step_is_commoner` (PR #49) | The docs say "15px … becomes 16 (`--type-body`), not 14. |
| LC-A13 | medium | fixed in 3.1.0 | `git stash && audit_design … > /tmp/before.json && git stash pop`: the audit exits 1 on any legacy code, so `pop` never runs. |
| LC-A14 | medium | fixed in 3.4.0: `test_versioning.DeprecateRewritesAndCountsAColourRename` (PR #50) | deprecate.py emits a colour rename. |
| LC-A15 | medium | fixed in 3.1.0, as SB-A12 | The doc says that after replacing the Tailwind theme, "an off-scale class does not exist and the build errors on it". |
| LC-A16 | medium | fixed in 3.2.0 | Re-pointing --bs-primary does not reach .btn-primary, which sets --bs-btn-bg: #0d6efd literally ([bootstrap.css](https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.css)), or .bg-primary and .text-primary, wh |
| LC-A17 | medium | fixed in 3.4.0: docs only, rollout.md's example and procedure (PR #54) | The model announcement reads "**Design system 2.1.0.** One breaking change: `--bg-accent` moved…". |
| LC-A18 | medium | fixed in 3.2.0 | The baseline is extracted from styles/ src/components/, but CI extracts from styles/ src/. |
| LC-A19 | medium | fixed in 3.4.0: `test_rules_spec.TheTierListsAgree` (PR #49) | The doc says "tier1-leak … agree[s] by construction" with audit_design L6. |
| LC-A20 | medium | fixed in 3.1.0, as XC-A8 | "Run them from this skill's root" combined with cwd-relative defaults writes project artifacts (literals.json, proposal/, the deprecation ledger) into the plugin install, which a plugin update replaces. |
| LC-A21 | medium | fixed in 3.1.0, as XC-A1 | `extract_literals --format report` writes no literals.json, so `cluster_values literals.json` fails with "no such file", exit 2. |
| LC-A22 | low | fixed in 3.4.0: `test_figma_sync.ReverseBody` (PR #53) | Three problems with the POST body `--reverse` generates. |
| LC-A23 | low | fixed in 3.4.0: `test_versioning.DeprecateKeepsRemovalsInAMajor`, `test_token_migration.MigrationPipeline` (the report's ms delta and held-colour advice); the rest docs only (PR #54; versioning's "Four edits" in #50) | Smaller accuracy and consistency items. |
| LC-B1 | — | W10 (3.6.0+) | no non-Enterprise route into Figma. |
| LC-B2 | — | W10 (3.6.0+) | Style Dictionary, Tokens Studio and Terrazzo teams get nothing. |
| LC-B3 | — | W9 (3.5.0) | no way to supply a project contract. |
| LC-B4 | — | W9 (3.5.0) | no CI bootstrap. |
| LC-B5 | — | W12 (3.6.0+) | migration coverage. |
| LC-B6 | — | W10 (3.6.0+) | Figma plan realities. |
| LC-B7 | — | W12 (3.6.0+) | rollout gaps. |
| LC-B8 | — | fixed in 3.4.0: the parity and worked-run claims gated in #49, #50 and #53; `tokens.css`'s read-only claim names the CI drift check, held by `test_figma_sync.DeterministicOutput` (PR #54) | claims with no gate. |
| LC-C1 | — | W9 (3.5.0) | Add `contract.json`, emitted by extract_system from the project's tokens.css and read through `--tokens` by figma_audit, figma_to_tokens, cluster_values, audit_design and diff_system. |
| LC-C2 | — | W10 (3.6.0+) | Add a shared `dtcg.py` for 2025.10 read and write, Tokens Studio sets and themes, and `$deprecated` → ledger, plus a `--format dtcg` output. |
| LC-C3 | — | fixed in 3.4.0: `test_figma_sync.FigmaCommon` (PR #53); the tier-list half, `test_rules_spec.TheTierListsAgree` (PR #49) | Move the two figma scripts' shared code into `figma_common.py`, and add a parity test for extract_system tier1-leak vs audit_design L6. |
| LC-C4 | — | fixed in 3.4.0: A11, A12 and A14 with P15 (PR #49, #50), the rest in 3.1.0 | Add regression tests for LC-A5, A10, A11, A12, A14 and A2, then fix each one: focus-ring detection, the vendor rule, negative-cancel pairing, the type-tie note, the font guard scope, and composed opacity. |
| LC-C5 | — | fixed in 3.4.0: `test_versioning.DiffSystemClassifiesWhatSystemJsonRecords` (PR #48) | diff_system: cover density, conditions, `element` and CSS Modules; record `@layer` in system.json; make an added override major when an existing value moves. |
| LC-C6 | — | fixed in 3.4.0: its last open part, LC-A17 (PR #54); LC-B4 is W9's | Instruction fixes: the rebase recipe (LC-A6), a worktree-based before/after audit (LC-A13), the `${CLAUDE_SKILL_DIR}` invocation (LC-A20), one snapshot path with its inputs in config (LC-A18), the README (LC-A21), the ro |
| LC-C7 | — | W10 (3.6.0+) | A Figma MCP route: a SKILL.md routing row that says "if `get_variable_defs` is available, read with it"; a `--reverse --format plugin-script` output for `use_figma` that renames "Mode 1", sets `scopes: []` on primitives  |
| LC-C8 | — | W9 (3.5.0) | Hooks: block edits to files headed "GENERATED — DO NOT EDIT", and on a tokens.css edit run diff_system and return the bump and any contrast crossings. |
| LC-C9 | — | W9 (3.5.0) | User-invocable workflow skills (`disable-model-invocation: true`): `/wds-migrate-census`, `/wds-release-check` (extract → diff → gate → changelog → guide), `/wds-figma-handoff`, `/wds-docs-check`, each with `allowed-tool |
| LC-C10 | — | W9 (3.5.0) | A `claude plugin eval` suite, with a `scaffold_script` for each fixture. |
| LC-C11 | — | fixed in 3.2.0 | Descriptions and token budget. |
| LC-C12 | — | fixed in 3.4.0: `tests/fixtures/worked-run` and `worked-release.json`, held by `test_token_migration.TheWorkedRun` and `test_versioning.TheWorkedRelease` (PR #50) | Ship the 8-file migration fixture and the five-edit release as test fixtures, and have CI regenerate the SKILL.md numbers from them. |
| GT-A1 | high | fixed in 3.1.0 | the runtime contrast check silently skips any colour that is not serialised as `rgb()`/`rgba()`. |
| GT-A2 | high | fixed in 3.1.0 | the runtime reports false Level-A errors on two page shapes that are everyday. |
| GT-A3 | high | fixed in 3.1.0 | the visual gate is blind to the regressions the matrix exists to catch. |
| GT-A4 | high | fixed in 3.1.0 | the pre-commit snippet ("one hook, three checks", which shows two) has four faults. |
| GT-A5 | medium | fixed in 3.4.0: `test_browser_scripts.BrowserScriptResolution.test_contexts_bypass_csp_where_they_inject_and_a_crash_exits_2`, `ContextOptions`, `test_browser_runtime.VitalsUnderCsp`, `test_browser_runtime.test_a_page_with_a_strict_csp_is_audited`, `test_a_sheet_with_a_strict_csp_is_captured` and `test_a_page_with_one_tab_stop_is_not_a_trap` (PR #39) | no `bypassCSP`. |
| GT-A6 | medium | fixed in 3.4.0: `test_browser_runtime.VitalsMeasures` (PR #45) | the throttle presets are not Lighthouse's, and TTFB is never throttled. |
| GT-A7 | medium | fixed in 3.2.0 | the coverage sources are misstated. |
| GT-A8 | medium | fixed in 3.4.0: `test_facts.AxeTagAdvice`, `test_browser_runtime.test_a_best_practice_rule_is_a_warning` (PR #41) | the axe tag advice is wrong in both directions. |
| GT-A9 | medium | fixed in 3.2.0 | the docs recommend "Not Evaluated" as a legitimate ACR entry. |
| GT-A10 | medium | fixed in 3.2.0 | the docs promise runtime behaviour that the code does not have. |
| GT-A11 | medium | fixed in 3.2.0 | the docs say to put the device and network "in a comment" in `perf-budget.json`, and the examples are JSONC. |
| GT-A12 | medium | fixed in 3.4.0: `test_content_and_a11y.MatrixStates` (PR #42) | rules written with `:focus` or `:focus-within` are mirrored to `[data-force-state~="focus"]`. |
| GT-A13 | medium | fixed in 3.4.0: `test_content_and_a11y.MatrixStates` (PR #42) | only the seven fixed states are allowed. |
| GT-A14 | medium | fixed in 3.4.0: (a) `test_browser_runtime.test_a_spinner_is_not_a_focus_ring` (PR #38); (b) `test_browser_runtime.test_disabled_controls_are_exempt_from_contrast` (PR #39) | two measurements give false results (fixture `$W\e11\probes.html`). |
| GT-A15 | medium | fixed in 3.2.0 | none of the CI recipes (a11y SKILL.md:285-311; ci-integration.md:53-110; visual-regression.md:191-237) runs as written in every case. |
| GT-A16 | low-medium | fixed in 3.4.0: `test_numbers.ByteBudgets` (PR #41) | two rows of the "same method" table cannot be reproduced with that method (TTFB = 4·RTT + 200 ms, minus 300 + 150 ms). |
| GT-A17 | low-medium | fixed in 3.4.0: `test_browser_runtime.VitalsMeasures` (PR #45) | `--interact` adds the interaction's own handler to TBT. |
| GT-A18 | low-medium | fixed in 3.4.0: `test_content_and_a11y.StaticBestPractice` (PR #41) | `multiple-h1`, `heading-skip` and `no-main-landmark` are hard errors attributed to SCs 1.3.1, 2.4.6 and 2.4.1. |
| GT-A19 | low | fixed in 3.2.0 | smaller errors in the docs. |
| GT-B1 | — | W11 (3.6.0+) | SPA and dynamic states. |
| GT-B2 | — | W11 (3.6.0+) | Authenticated pages. |
| GT-B3 | — | W11 (3.6.0+) | Shadow DOM. |
| GT-B4 | — | W11 (3.6.0+) | Multiple URLs and viewports. |
| GT-B5 | — | fixed in 3.4.0: `scripts/crux_check.py` (`test_crux_check`, PR #46) | The field-data loop. |
| GT-B6 | — | W11 (3.6.0+) | Checks the coverage table lists as automatable but that don't exist. |
| GT-B7 | — | fixed in 3.4.0: custom states and combinations in PR #42; a fixture's `dir` and `lang`, the `--forced-colors` pass, and what interaction states need, in PR #44 (`test_content_and_a11y.MatrixModel`, `test_browser_runtime.MatrixSeesStateChanges`) | The matrix model. |
| GT-B8 | — | fixed in 3.4.0: the `workflow_dispatch` recording job and Git LFS past the line, in visual-regression.md §6 and §7; the generator says when a sheet nears it (`test_content_and_a11y.MatrixModel`, PR #44) | The baseline lifecycle. |
| GT-B9 | — | W11 (3.6.0+) | Chromium only. |
| GT-C1 | M · P0 | fixed in 3.1.0 and 3.2.0 (browser tests) | A test suite that uses a real browser, skipped when none is available. |
| GT-C2 | S–M · P0 | fixed in 3.4.0: colours, modals, iframes and inert content in 3.1.0 (GT-A1, GT-A2), pausing in PR #38 (GT-A14 (a)), `bypassCSP` and the disabled-control exemption in PR #39 (GT-A5, GT-A14 (b)) | Fix colour parsing, modals, iframes, inert content, `bypassCSP`, animation pausing and the disabled-control exemption. |
| GT-C3 | M · P0 | fixed in 3.4.0: the differs-from-default gate and the tolerance in 3.1.0, focus mirroring, custom states and the error attributes in PR #42 | Matrix: the within-run "differs from default" gate, a tuned tolerance, focus mirroring, custom states, `data-state="error"` on non-form templates. |
| GT-C4 | S · P0 | fixed in 3.1.0, with GT-A4 | One shipped hook with opt-in stages in place of the inline snippets. |
| GT-C5 | S · P0 | fixed in 3.4.0: A7, A9, A10 and A19 in 3.2.0, A8 and A16 in PR #41 | A correction pass on the docs (A7–A10, A16, A19). |
| GT-C6 | S · P1 | fixed in 3.1.0 (the review's C6) | Write SKILL.md commands with `${CLAUDE_SKILL_DIR}` and pre-approve them with `allowed-tools`. |
| GT-C7 | S · P1 | fixed in 3.2.0, item 13 | SKILL.md size: 5k tokens or less. |
| GT-C8 | S · P1 | fixed in 3.2.0, item 13 | Descriptions with a standalone first sentence and a "not for" line. |
| GT-C9 | M · P1 | W9 (3.5.0) | Plugin components: a `gate-runner` agent, an opt-in PostToolUse hook running a11y_static, user-invoked gate skills. |
| GT-C10 | M · P1 | W9 (3.5.0) | A `claude plugin eval` suite for the gates, run under WSL2. |
| GT-C11 | M · P2 | fixed in 3.4.0: the `lighthouse` preset, TTFB from CDP and `--interact-at` in PR #45 (`test_browser_runtime.VitalsMeasures`), `crux_check.py` in PR #46 (`test_crux_check`) | A `lighthouse` throttle preset, TTFB from CDP, `--interact-at MS`, and `crux_check.py`. |
| GT-C12 | M · P1 | W9 (3.5.0) | One CI template for all three gates in a pinned Playwright container, with a baseline-update job and a tested Windows variant. |
| GT-C13 | S · P2 | fixed in 3.4.0: `test_browser_scripts.SharedHelpers` (PR #38) | Vendor the shared runtime helpers into each skill as identical copies, with a test that they match. |
| PS-A1 | high | fixed in 3.1.0 | The deck asserts claims that its own inputs contradict. |
| PS-A2 | high | fixed in 3.1.0 | The defence sheet presents suspicions as known flaws and drops confirmed defects. |
| PS-A3 | high | fixed in 3.1.0 | The audit merge silently deletes whole rule groups. |
| PS-A4 | high | fixed in 3.1.0 | The design gate passes HTML without auditing it. |
| PS-A5 | medium | W8 (3.4.0) | `--a11y` rejects the suite's own accessibility JSON. |
| PS-A6 | medium | W8 (3.4.0) | The printed deck sends every presenter note to the client. |
| PS-A7 | medium | W8 (3.4.0) | A reversed decision is presented as current. |
| PS-A8 | medium | W8 (3.4.0) | The skills give opposite instructions for a risky client request. |
| PS-A9 | medium | W8 (3.4.0) | Two legal statements are wrong. |
| PS-A10 | medium | W8 (3.4.0) | The "Say this" lines break the skill's own rule on numbers. |
| PS-A11 | medium | fixed in 3.2.0 | The ethics section falls outside what survives compaction. |
| PS-A12 | low-medium | W8 (3.4.0) | The markup breaks the skill's own full-bleed rule. |
| PS-A13 | low-medium | W8 (3.4.0) | Flaw timing and deck structures contradict the method. |
| PS-A14 | low-medium | W8 (3.4.0) | The NN/g five-user rule is misapplied to five-second tests. |
| PS-A15 | low | W8 (3.4.0) | The colour-blindness figure is about half the standard one. |
| PS-A16 | low-medium | W8 (3.4.0) | Three pieces of reference advice fail on their own terms. |
| PS-A17 | low | W8 (3.4.0) | The rule to stop at the first blocking finding is too broad. |
| PS-A18 | low | W8 (3.4.0) | The media accessibility advice is incomplete. |
| PS-A19 | low-medium | W8 (3.4.0) | The meeting record overstates its legal effect. |
| PS-A20 | low | W8 (3.4.0) | Counts and structure in design-critique-gate are wrong. |
| PS-A21 | low | W8 (3.4.0) | Smaller mismatches between docs and behaviour. |
| PS-A22 | low | W8 (3.4.0) | The header says "SEVEN SECTION SHELLS" but lists eight (:7-13). |
| PS-B1 | — | W14 (3.6.0+) | Accessibility of persuasive patterns. |
| PS-B2 | — | W14 (3.6.0+) | Consumer law beyond the EU/US basics. |
| PS-B3 | — | W14 (3.6.0+) | Price experiments. |
| PS-B4 | — | W14 (3.6.0+) | Page types and audiences. |
| PS-B5 | — | W8 (3.4.0) | Checks Claude can't honestly run. |
| PS-B6 | — | W14 (3.6.0+) | No claims layer, and siblings don't route to each other. |
| PS-B7 | — | W8 (3.4.0) | Presenting in practice. |
| PS-B8 | — | W14 (3.6.0+) | Consent for tracking. |
| PS-C1 | — | W8 (3.4.0) | Make the deck honest by construction: wording from the data, manual-test evidence as input, `--handout`, a presenter window. |
| PS-C2 | — | W8 (3.4.0) | Fix critique_report: a `covers` field for merges, merge notes in every format, a `status` field. |
| PS-C3 | — | fixed in 3.1.0, with PS-A4 | Close the HTML blind spot with web-design-studio: audit `<style>` and `style=""`; fail when zero files were audited. |
| PS-C4 | — | W9 (3.5.0) | Add an adversarial critic subagent, `agents/design-critic.md`, that returns `findings.json` from a fresh context. |
| PS-C5 | — | W14 (3.6.0+) | Add `critique_snapshots.mjs`: PNGs at 390 and 1440px plus blur, greyscale, mirror, 25%, dark and reduced-motion variants. |
| PS-C6 | — | W14 (3.6.0+) | Add `lint_claims.py`: load-time countdowns, fake scarcity, pre-checked opt-ins, unsourced percentages and the like. |
| PS-C7 | — | W9 (3.5.0) | Add an eval suite in `evals/`, scored against a no-plugin baseline. |
| PS-C8 | — | fixed in 3.2.0 | Put landing-page-conversion on a token diet. |
| PS-C9 | — | fixed in 3.2.0 | Rewrite the descriptions. |
| PS-C10 | — | fixed in 3.2.0 | Add an evidence register: each figure's value, URL, date verified and exact quote, with a test. |
| PS-C11 | — | W9 (3.5.0) | Add a user-invocable chain skill: audit → critique → defence → deck, stopping on blockers. |
| PS-C12 | — | W14 (3.6.0+) | Bridge MESSAGE_BRIEF to DECISION_LOG. |
| DL-A1 | high | fixed in 3.1.0 | secret columns are shown and editable. |
| DL-A2 | high | fixed in 3.1.0 | authorization columns are editable by default. |
| DL-A3 | high | fixed in 3.1.0 | the RLS write-failure model is wrong. |
| DL-A4 | medium | fixed in 3.1.0 | two samples are buggy. |
| DL-A5 | medium | fixed in 3.3.0: `test_docs.SupabaseGuidance.test_the_access_boundary_is_stated` | unsafe or stale guidance. |
| DL-A6 | medium | fixed in 3.3.0: `test_content_and_a11y.SchemaSecurityPass` | the tool cannot see RLS. |
| DL-A7 | medium | fixed in 3.3.0: `test_schema_sources` | Supabase's own schema outputs are silently misread. |
| DL-A8 | medium | W7 (3.4.0) | interview answers are ignored. |
| DL-A9 | medium | W7 (3.4.0) | generated forms lack promised a11y wiring |
| DL-A10 | medium | W7 (3.4.0) | dark mode breaks the call-to-action. |
| DL-A11 | medium | W7 (3.4.0) | the Outlook font rule is never added. |
| DL-A12 | medium | W7 (3.4.0) | the receipt isn't fluid. |
| DL-A13 | medium | W7 (3.4.0) | nothing enforces "Law 1 holds at build time". |
| DL-A14 | low | W7 (3.4.0) | the inliner isn't "the real cascade" when shorthand and longhand mix. |
| DL-A15 | low | fixed in 3.2.0 | cells contradict the cited caniemail raw data |
| DL-A16 | low | fixed in 3.2.0 | Gmail's 16 KB rule is mis-described. |
| DL-A17 | low | fixed in 3.2.0 | dated or wrong facts. |
| DL-A18 | low | fixed in 3.2.0 | ten section pointers point at the wrong section |
| DL-A19 | low | fixed in 3.1.0, as XC-A4 and XC-A8 | Invocation and Windows portability (instances of XC-A4 and XC-A8). |
| DL-A20 | low | W7 (3.4.0) | authoring notes ship in the email. |
| DL-A21 | low | W7 (3.4.0) | Consistency: "same 18 steps" and the email tokens' weight note are wrong. |
| DL-B1 | high | fixed in 3.3.0: the reference's §9 (`test_docs.SupabaseGuidance.test_the_access_boundary_is_stated`) and the generated `lib/supabase.ts` (`test_policies`) | no data-access boundary. |
| DL-B2 | high | partly done (3.3.0: per-table policies, column grants and a smoke test, `test_policies`); a server-side schema (pydantic or zod) mirroring the constraints is left | authorization and server validation belong to nobody. |
| DL-B3 | medium | W13 (3.6.0+) | stacks the description implies but doesn't serve. |
| DL-B4 | medium | W13 (3.6.0+) | email frameworks. |
| DL-B5 | medium | W13 (3.6.0+) | email translation and RTL. |
| DL-B6 | medium | W7 (3.4.0) | Checks the docs promise but nothing runs: email dark-mode contrast, the MSO font block, the no-`<style>` layout, source literals, generated-form ARIA. |
| DL-B7 | low | W7 (3.4.0) | deliverability is dated. |
| DL-B8 | low | fixed in 3.3.0: `test_schema_sources.TheWorkedExampleIsTheFixture`, `GeneratedTypesAgreeOnStructure` | unverifiable claims. |
| DL-C1 | M | fixed: 3.1.0 classified the sensitive columns (DL-A1, DL-A2); 3.3.0 parses RLS and policies and prints the SECURITY block (`test_content_and_a11y.SchemaSecurityPass`) | A security pass in `introspect_schema`: classify sensitive columns, parse RLS and policies, print a SECURITY block first. |
| DL-C2 | M | done in 3.3.0: `test_schema_sources` | A sturdier schema parser, tested on real `db pull` and `gen types` files. |
| DL-C3 | M | W7 (3.4.0) | Email: fix A10–A12, then add a dark pass and a no-`<style>` check to `lint_email`, and `render_email.py`. |
| DL-C4 | S | fixed in 3.3.0, with DL-A5 and DL-B1's reference | rewrite supabase-integration.md §2/§4/§6 |
| DL-C5 | S | W7 (3.4.0) | `lint_email --source`: flag literals, `var()` fallbacks and dropped tokens. |
| DL-C6 | S | fixed in 3.2.0 | pointer and command hygiene; the detail file lists them. |
| DL-C7 | M | W9 (3.5.0) | plugin features for these skills. |
| DL-C8 | S | fixed in 3.2.0 | slimmer SKILL.md, sharper descriptions. |
| DL-C9 | M | W13 (3.6.0+) | Keep the email client matrix honest: regenerate its cells from caniemail's data, with test dates. |
