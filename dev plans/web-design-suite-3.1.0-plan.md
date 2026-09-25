# web-design-suite 3.1.0: phase 1 work plan

Phase 1 of [web-design-suite-review.md](web-design-suite-review.md) does three things:
- stops the false passes;
- removes the unsafe defaults;
- makes every documented command runnable.

Each fix gets a regression test that is **seen failing on 3.0.1 and passing on 3.1.0**. Fail-before runs use `WDS_PLUGIN_ROOT` pointed at the pristine 3.0.1 copy in the session scratchpad (`wds-3.0.1\web-design-suite`). That copy can be rebuilt from `Downloads\web-design-suite-plugin-3.0.1.zip`.

The status column is updated at milestones. `[x]` = fixed, tested, and seen failing before.

| # | IDs | Fix | Files | Status |
|---|---|---|---|---|
| 1 | SB-A3, SB-A4, PS-A4, SS-A19, XC-A9 | audit_design precision: tokenise `var()`, check spacing inside `@media`/`@container`, audit HTML `<style>`/`style=""` and single-file components, read files as `utf-8-sig`, make baseline keys relative to the baseline file, fail when 0 files were audited, say "L1–L6" | audit_design.py | [x] |
| 2 | XC-A6, GT-A4 (part) | a11y_static: remove the quadratic work; filter explicit arguments by extension | a11y_static.py | [x] |
| 3 | XC-A7, LC-A10 | extract_literals: newline index + bisect; `lib/` is no longer treated as vendor; codemod `--include-vendor` | extract_literals.py, apply_codemod.py | [x] |
| 4 | LC-A5 | cluster_values: focus rings stay focus rings | cluster_values.py | [x] |
| 5 | LC-A1, LC-A2, LC-A3, LC-A4 | figma: DTCG 2025.10 values, composed colours, `--tokens` project ramps, no timestamps | figma_to_tokens.py, figma_audit.py | [x] |
| 6 | PS-A2, PS-A3 | critique_report: carry open confirmed defects; merge only on an explicit rule id | critique_report.py, CRITIQUE_TEMPLATE.md | [x] |
| 7 | PS-A1 | build_presentation: wording chosen from the data; "L1–L6" | build_presentation.py | [x] |
| 8 | DL-A1, DL-A2 | introspect_schema: secret patterns; authority columns read-only by default | introspect_schema.py | [x] |
| 9 | GT-A1, GT-A2 | a11y_runtime: resolve any colour syntax; modal/inert/iframe handling | a11y_runtime.mjs | [x] |
| 10 | GT-A3 | snapshot_matrix: hover/active/focus cells must differ from default | snapshot_matrix.mjs | [x] |
| 11 | SS-A1–A5, SB-A1, SB-A2 | starter CSS and Tailwind focus utility | tokens.css, reset.css, stack docs, theme.css, tailwind.config.ts | [x] |
| 12 | SB-A5, SB-A6, SB-A7, LC-A6, LC-A13, DL-A3, GT-A4, XC-A1 | doc corrections and recipes | references, SKILL.md, README | [x] |
| 13 | XC-A8 | `${CLAUDE_SKILL_DIR}` invocation in every SKILL.md | 13 × SKILL.md | [x] |
| 14 | — | version 3.1.0, CHANGELOG (re-baseline note), patch, zip, report, memory | plugin root, dev plans | [x] |

**Done 2026-09-24.** Results are in [web-design-suite-3.1.0-report.md](web-design-suite-3.1.0-report.md). Beyond this table, the following were fixed, each with a fail-before test:
- in full: SB-A12, SS-A14, DL-A4 and XC-A4;
- in part: SS-A6, SB-A10 and SB-A16 (a);
- three problems the review did not list: the `url()` colour false positive, the email quick start writing into the plugin, and the migration's proposed tokens.css.
