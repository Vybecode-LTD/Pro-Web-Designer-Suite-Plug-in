# web-design-suite: full audit, 2026-10-14

**Status, 2026-10-28:** all 114 findings closed in 4.0.0, as N41 to N47 of the completion plan (PRs #130 to #162); none was declined or left. This file is the record; it carries no per-finding status.

**Audited:** `origin/main` at `9391774` (the merge of #128), read from a scratch worktree. Line numbers are from that revision. The in-flight branch `feat/tailwind-v4-census` (#129) was not audited; the two findings it already replaces are noted where they occur.

**Purpose:** one exhaustive pass, in the style of the Codex and CodeRabbit reviews on #105 to #129, so the next PRs stop collecting new findings one at a time. Every finding below was verified against the code, and all but a handful were demonstrated by running the script on a crafted input (the fixtures are listed in §9). Severity: **critical** = silently wrong output or a crash in a tool that rewrites user files; **high** = wrong result or crash on a valid, documented input; **medium** = wrong on a plausible input, a doc/code mismatch, or a missing guard; **low** = nit, dead code, hygiene.

**Totals:** 114 findings. 2 critical, 15 high, 49 medium, 48 low. Baseline: the full suite on `main` passes here (1,121 tests, 65 skipped locally); the project's own checks (`check_pointers`, `sync_snippets --check`, `sync_rules --check`, `audit_design skills --strict`, `check_execution_plan.py`) are all clean; every copy of the four masters is byte-equal; no BOM or CRLF in the tree; every script compiles under Python 3.9.

**How to use this:** work the §1 and §2 items first, each with a fail-before test on `v3.6.0`, then §3 by skill. §8 turns the recurring reviewer patterns into checks that can be automated, which is what actually ends the cycle.

---

## 1. Critical

### C1. The Tailwind codemod matches a class inside a longer class name
- **Where:** `plugins/web-design-suite/skills/design-token-migration/scripts/apply_codemod.py:758` (`plan_classes`), overlap guard at `:952-957`.
- **What:** `re.finditer(re.escape(tok) + r"(?![\w\[-])", group)` has a right boundary and no left one. A rule for `p-[16px]` matches inside `top-[16px]`, `gap-[16px]`, `sp-[16px]` and `-p-[16px]`, so the codemod rewrites classes the census never counted (`top-well`, `sp-well`, `-p-well`), and when `gap-[16px]` has its own rule the two edits overlap and the whole file is skipped ("two rules want the same text"). Same shape for `m-`/`mt-` inside `-m-`/`-mt-`, and `w-`/`h-` inside `min-w-`/`max-w-`/`min-h-`/`max-h-`. Demonstrated. The in-flight branch changes only the numeric-class path; this `[`-path is unchanged.
- **Fix:** anchor on the left as the census's `TW_ARBITRARY_RE` does (`(?<![\w:./-])` plus the optional variant chain), or reuse that regex and compare the whole match against the rule. Test: a file with `p-[16px]` beside `top-[16px]`, `gap-[16px]` and `-p-[16px]`; only `p-[16px]` changes and no file is skipped.

### C2. `apply_codemod --apply` converts every CRLF line ending to LF, and the dry run does not show it
- **Where:** `apply_codemod.py:930` (`fp.read_text(encoding="utf-8")`, universal newlines) and `:977` (`write_atomically`, `newline=""`).
- **What:** a CRLF stylesheet (any Windows checkout without `.gitattributes`) comes back LF on every line; git then shows the whole file changed and the "read the 40-file diff" discipline in SKILL.md is defeated. The dry-run diff is computed on the translated text, so it shows only the token lines. BOM is preserved. Demonstrated (7 CRLF lines to 0).
- **Fix:** read with `newline=""` (the scanners already treat `\r` as whitespace) and keep writing with `newline=""`. Test: after `--apply`, untouched lines still hold `\r\n`.

The same bug, one tier down because it touches one file at a time: **V1** (`deprecate add --source`).

## 2. High

### H1. `deprecate add --source` rewrites every line ending of the token file it marks
- **Where:** `design-system-versioning/scripts/deprecate.py:217-236` (`inject_marker`): `read_text` then `write_text` (platform newline).
- **What:** on Windows an LF file comes back CRLF throughout; on Linux a CRLF file comes back LF. One marker line becomes a whole-file diff. No test covers marker injection. Demonstrated.
- **Fix:** `open(..., newline="")` both ways, keep the file's dominant ending. Test: inject into an LF and a CRLF file; exactly one line added.

### H2. `figma_to_tokens --reverse` drops a theme's alias to an undeclared token, silently, saying "already reported"
- **Where:** `figma-variables-sync/scripts/figma_to_tokens.py:1269-1278` (`reverse_body` pass 3, `continue  # already reported`); pass 2 at `:1215-1229` iterates base entries only.
- **What:** `[data-theme="dark"] { --fg-link: var(--accent-300) }` with `--accent-300` undeclared: the Dark value is left out of the POST body, Figma shows the Light alias in Dark, exit 0, stderr empty. Demonstrated.
- **Fix:** evaluate theme entries in pass 2, or append `Problem("dropped", f"{token} [{theme}]", terr)` in pass 3 so the exit is 1 and the mode is named.

### H3. A UTF-8 BOM on `tokens.css` makes `extract_system` file every `:root` token as theme-only
- **Where:** `design-system-docs/scripts/extract_system.py:1529` (`read_text(encoding="utf-8")`); same in `design-system-versioning/scripts/diff_system.py:834` and `:851`. The shared reader uses `utf-8-sig` (`shared/project_config.py:473`).
- **What:** the selector becomes `\ufeff:root`, nothing matches `ROOT_SEL`, every token is `theme-only-token` and `unresolved`, the contract is empty, and `diff_system` reports everything removed and added. Demonstrated (6 tokens, 10 gaps).
- **Fix:** `utf-8-sig` in `CssFile`'s callers, `build_docs.forced_state_css`, and the two `diff_system` readers. Test: a BOM-prefixed starter extracts the same `system.json`.

### H4. `a11y_static` never sees `outline: none` inside `@layer`, `@media` or `@supports`
- **Where:** `a11y-audit-runner/scripts/a11y_static.py:1432-1469` (`audit_css`), decision at `:1471-1496`.
- **What:** blocks split at brace depth 0 only, so an at-rule is one block whose declarations are pooled: any `box-shadow` in a sibling rule inside the same `@layer` counts as the replacement, and `FOCUS_SEL` tests the at-rule prelude, never the nested selector. The starter's own `base.css` wraps everything in `@layer base`, and planting `.btn:focus-visible { outline: none }` inside it audits clean. The comment at `:1430-1431` describes behaviour the code does not have. Demonstrated.
- **Fix:** recursive block reader carrying the at-rule stack (as `generate_matrix.parse_css` does) and evaluate per leaf rule. Test: `outline: none` inside `@layer` and inside `@media (hover: hover)` is reported; fail-before on `v3.6.0`.

### H5. `generate_matrix` drops `:hover`/`:focus-visible` inside `:is()`/`:where()` and nested `&:hover`, while reporting the state as covered
- **Where:** `component-state-matrix/scripts/generate_matrix.py:316-336` (`transpose_part`, depth-0 only), `:343-351` (`build_force_shim.walk` loses the parent selector: `&` mirrors as root), `:452-472` (`detect_states`, substring match).
- **What:** `.btn:is(:hover, :focus-visible)` gets no mirror rule; `.chip { &:hover {…} }` mirrors as `&[data-force-state~="hover"]`, which matches nothing. The summary still says "every declared state has a matching rule", the sheet renders hover identical to default, and `--update-baselines` records it. `SKILL.md:182` says only `:not()` is left alone. Demonstrated (snapshot_matrix then fails 8 cells "computes the same style as default").
- **Fix:** rewrite forceable pseudo-classes inside `:is()`/`:where()`; prefix nested selectors with the parent when walking; make `detect_states` share the transposition so "covered" means "a mirror was emitted".

### H6. `a11y_static` audits `.vue` files but does not know `:attr` / `v-bind:attr`
- **Where:** `a11y_static.py:101-103` (`.vue` in `MARKUP_EXT`), `:383` (`ATTR_NAME` accepts a leading `:`), `:501-503` (only `className`/`htmlFor` normalised).
- **What:** `<img :alt="d">` is `img-no-alt`; `<input :id :aria-label>` is `control-no-label` and `missing-autocomplete`; `<button :aria-label>` is `empty-control`. A Vue project with the pre-commit hook is blocked on every bound attribute. Svelte's `alt={d}` works. Demonstrated.
- **Fix:** normalise `:name`, `v-bind:name` (and Angular `[name]`) to `name` with value `EXPR`. Test with a positive control (`<img :src>` with no alt at all still fails).

### H7. The pre-commit hook's `DESIGN_GATE_INDEX=1` audits without the project's config or baseline
- **Where:** `web-design-studio/assets/configs/pre-commit-design-gate.sh:221-235`; `audit_design.py:2500` (config found by walking up from cwd), `:2537` (baseline relative to cwd).
- **What:** `git checkout-index` copies only the staged files into the scratch tree; `.design-suite.json` and `.design-baseline.json` are not staged, so the audit runs with no token files, no component globs and no baseline, and every baselined finding refuses the commit. Demonstrated (same repo: plain hook exit 0, index mode exit 1).
- **Fix:** materialise the config and the baseline into `AUDIT_ROOT` (from HEAD when not staged), or pass `--baseline` from the repo root and run from a cwd that finds the config.

### H8. The audit reads a ternary inside an inline `style` custom property as a visual property
- **Where:** `web-design-studio/scripts/audit_design.py:1778-1780` (`_audit_jsx_styles` key regex).
- **What:** `style={{ '--progress': open ? '1' : '0' }}`: the quoted consequent `'1' :` matches the "quoted key" branch, so the gate reports "Inline style sets visual property: 1" and exits 1. The ESLint rule passes the same code. This is the one inline use the spec allows. Demonstrated.
- **Fix:** blank string literals before extracting keys; take quoted keys only after `{` or a depth-0 `,`.

### H9. `introspect_schema` ignores `ALTER TYPE … ADD VALUE`
- **Where:** `content-model-to-ui/scripts/introspect_schema.py:871-969` (`parse_ddl`); only `RE_CREATE_ENUM` (`:633`) feeds `model.enums`.
- **What:** every Supabase migration set extends enums this way; the scaffold writes `z.enum(["pending","paid"])` and `Literal['pending','paid']`, so a row with `shipped` is refused by the server draft and cannot be chosen in the form. Demonstrated.
- **Fix:** a branch for `ADD VALUE [IF NOT EXISTS] 'v' [BEFORE|AFTER 'w']` and `RENAME VALUE`.

### H10. `CREATE TABLE … ) PARTITION BY` / `WITH (…)` / `INHERITS (…)` tails parse into the last column
- **Where:** `introspect_schema.py:1001-1002` (`_parse_create_table`, `body_end = stmt.rindex(")")`).
- **What:** the last column's default becomes `now() ) PARTITION BY RANGE (created_at`; a trailing table-level CHECK is dropped. Demonstrated.
- **Fix:** use `_balanced_slice` (already in the file) for the column list.

### H11. The proposal silently drops colours it cannot parse and px letter-spacing
- **Where:** `design-token-migration/scripts/cluster_values.py:654-658` (`except ColorError: continue`), `:1609-1611` (non-`em` tracking `continue`).
- **What:** the census counts `oklch()`, `hwb()`, `lab()`, `lch()`, `color()`, `hsl(0.5turn …)` and `letter-spacing: 1px`; the proposal puts them in neither `rules` nor `unmapped`, so the reconciliation no longer accounts for the inventory. Demonstrated.
- **Fix:** emit an `Unmapped` row for each. Test: every census literal is in a rule or an unmapped row.

### H12. Rules the codemod can never apply are counted as "mechanically replaceable"
- **Where:** `apply_codemod.py:250-253` (`is_color_slot`: hex or functional only); rules emitted at `cluster_values.py:1829-1838`; census counts a hex inside `color-mix()` at `extract_literals.py:858-859` before the span is claimed at `:867-869`.
- **What:** `color: white` gets a rule that never fires; a hex inside `color-mix()` is counted and gets a rule the codemod cannot apply. The estimate put "in front of a client" overstates. Demonstrated.
- **Fix:** accept `NAMED_COLORS` in `is_color_slot`; claim the `color-mix` span before the hex pass or recurse into it.

### H13. The width-token path in the proposal is unreachable; every length over 195px gets "Decide between 192px and 192px"
- **Where:** `cluster_values.py:1120-1130`, `:1137-1141` (`size` branch after the 4px snap, which ends at 192), `:1198-1200` (`_spacing_recommendation`).
- **What:** `max-width: 1152px` never maps to `--width-content`; the recommendation names 192 twice. Demonstrated.
- **Fix:** test `klass == "size"` against `WIDTH_STEPS` before the 4px snap; say "above the scale" past `SPACE_PX[-1]`.

### H14. The documented rebase-conflict recipe cannot work: the codemod refuses a staged file
- **Where:** `design-token-migration/references/migration-strategies.md:373-379` vs `apply_codemod.py:844-872` (`dirty_files` adds every porcelain entry) and `:1069-1074`.
- **What:** the recipe does `git add f.css` then runs the codemod, which SKIPs the staged file and exits 1. Demonstrated.
- **Fix:** have the recipe pass `--force` and say why it is safe, or treat a fully staged file (`M `, `A `) as clean.

### H15. Two tests cannot do what they claim (test suite)
- `tests/test_utf8_output.py:29-35` `test_every_script_writes_utf8_to_a_pipe`: decodes `--help` with the UTF-8 env vars unset, but no script's help holds a non-ASCII byte, so cp1252 and UTF-8 are identical and 32 of 33 scripts are untested. Verified: `scripts whose --help holds a non-ASCII byte: []`. Fix: a positive control (assert the source calls the reconfigure helper, with a bad stub proving the scan fires) and cover `workflow-commands/*/scripts`.
- `tests/test_scaffold.py:393-396`: the only test that imports pydantic skips on every CI cell (`ci.yml:66` runs `uv run --no-project`, no pydantic). The generated `orders_schema.py` is never executed by Pydantic in CI. Fix: `--with pydantic` for that class, pin the major.

## 3. Medium and low, by area

### 3.1 Shared readers, hooks, MCP (`shared/`, `hooks/`, `mcp/`)
All copies byte-equal. Python and Node readers agree on 28 odd `.design-suite.json` shapes and on every DTCG/resolver rule tested except the three below.

- **S1 medium.** `shared/dtcg.py:214` `convert`: `(kind or "").lower()` with a non-string group `$type` (`5`, `["color"]`, `true`) over an object value is an `AttributeError` traceback (not `ConfigError`) in `read_tokens` and every gate above it; Node reads the file. Guard with `isinstance`, report a problem. Parity test.
- **S2 medium.** `shared/project_config.py:539` (`_dtcg_tokens`) and `:561` (`read_deprecations`) discard every problem `dtcg.tokens()` reports. A resolver with 16 problems (sources outside the folder, a junction, a URL, bad pointers, a set cycle, a list `default`) reads silently; `audit_design.py:380` and `diff_system.py:899` print nothing. Carry `problems` on `ProjectTokens`; gates print them as warnings.
- **S3 medium.** `hooks/design_hooks.mjs:74` (versioning, `deprecat\w*…tokens?`) and `:71` (migration, `migrat\w*…tokens?`) lack the design-token anchor the patch-release pattern got on #97 (`:78`): "deprecate the old JWT tokens" routes to design-system-versioning, "migrate the session tokens to Redis" to design-token-migration. Also: "critique my essay" (`:87`), "every state in the US" (`:82`), "the lighthouse keeper story needs a hero section" (`:68`), "token reference docs for the OAuth API" (`:81`). `test_hooks.py:591-600` guards only the patch-release form.
- **S4 medium.** `shared/dtcg.py:1280` `css_colour`: `if fn in ("rgba","hsla") and len(args)==4`: the legacy comma form with alpha, `rgb(255, 0, 0, 0.5)` and `hsl(0, 100%, 50%, 0.5)` (valid CSS Color 4 aliases), becomes `UNSUPPORTED`/`notWritten`. Include `rgb`/`hsl`.
- **S5 low.** `dtcg.py:209-211` strips before testing `{…}`; `project_config.mjs:1062` does not: `" {a.b} "` is a reference in Python, a literal in Node.
- **S6 low.** `dtcg.py:608` `MATH_TOKEN`, `:1172` `NUMBER`, `:714`, `:166` accept Unicode digits (`٥`); Node is ASCII-only; `project_config.py:375` already fixed `RAMP_STEP` for this. Use `[0-9]`.
- **S7 low.** `dtcg.py:119` iterates a `components` dict as its keys (`#ffffff`); Node (`mjs:565`) refuses.
- **S8 low.** `project_config.py:473` and `mjs:441` decode CSS as UTF-8 only: a UTF-16LE `tokens.css` (PowerShell 5.1 `>`) reads as zero tokens with no diagnostic, so every `var(--x)` is "unknown". Decode by BOM or raise `ConfigError`.
- **S9 low (policy).** `mcp/design_gates.mjs:46`, `:190`, `:220-237`: no path containment; `..` and absolute paths outside the project are audited and their lines returned in `snippet`; `perf_audit budget: C:/Windows/win.ini` is read. Reject paths outside `project()` with `-32602`.
- **S10 low.** `dtcg.py:563`, `:338-340`: `$deprecated` of any JSON type (dict, list, int) is carried as the reason; consumers guard today.

### 3.2 web-design-studio (audit, roles, ramp, tw_probe, configs, hook)
- **W1 medium.** `generate_color_ramp.py:253`, `:266-269` accept `#rrggbbaa`/`#rgba` and drop the alpha; `check_roles.py:237`/`:240`: the translucency guard tests `/ a)` after `parse_color` already rejected it (no alpha group), so it is unreachable. `--fg-default: #00000080` on `#fafafa` measures 20.12, ok. The docstring (`:23-25`) says translucent roles are refused. Demonstrated.
- **W2 medium (the HANDOFF open item, now quantified).** `generate_color_ramp.py:421-430` `contrast_ratio_oklch` clips channels and is what `check_roles.py:261`, `:295` and `check_pair` (`:746`) use; `worst_contrast` (`:443-448`, the worse of clip vs chroma-map) is used only by `contrast_report`. Searching L 0.35-0.80, C 0.20-0.35, all hues: 1,454 triples pass 4.5:1 clipped but fail chroma-mapped; `oklch(59% 0.35 273)` on white is 6.49 vs 4.40. The starter's accent is inside sRGB (unaffected). Fix: call `worst_contrast` from `check()`, `table()` and `check_pair()`.
- **W3 medium.** `tw_probe.mjs:193-194` clears every key under a `--ns-*: initial`, but Tailwind 4.3.3's `clearNamespace` keeps `--font-weight-*` and `--font-size-*` under `--font`, `--inset-shadow`/`--inset-ring` under `--inset`, six `--text-*` subkeys, and grid-column/row: a theme with `--font-weight-bold` then `--font-*: initial` gets a false "font-bold … survived" FAIL and loses its weight roles. Demonstrated. Mirror the ignore map.
- **W4 medium.** `stylelint.config.mjs:338-365` `design/layer-order` refuses a layer statement that inserts an unknown layer (`…, overrides, print`); `audit_design.py:1227-1232` and `design-rules.json` `layers.rule` allow insertion. Demonstrated. Order-check only `LAYER_ORDER` names in statements; add the example to `design-rules.json` so `test_rules_spec` pins both gates.
- **W5 medium.** `audit_design.py:449-454` `TW_ARBITRARY_OK` exempts `bg-[url(…)]` and `content-['x']` "as the ESLint config also rules"; `eslint.design.config.mjs:99-100` `ARBITRARY_VALUE` has no such exemption. ESLint 1 error, audit clean. Pick one, add the example to the spec.
- **W6 medium.** `check_roles.py:249` iterates a string `scopes` as characters (`bad pairs file: 'l'`); `:266` `min: "4.5"` is a `TypeError` traceback (`:329` catches only OSError/ValueError/KeyError). Validate each pair, exit 2.
- **W7 medium.** `check_roles.py:321` `read_text(utf-8-sig)` on a UTF-16 `tokens.css` is a `UnicodeDecodeError` traceback, exit 1 (documented 2); `:327` reads the pairs file as bytes for exactly this case.
- **W8 low.** `check_roles.py:116` skips a block wholesale when it contains `{`: `:root { --fg-default: …; @media (…) {…} }` (native nesting) gives "--fg-default is not declared", exit 2.
- **W9 low.** `audit_design.py:1381` `"!important" in value.lower()` flags `content: "!important"`; stylelint reads the flag.
- **W10 low.** `tw_probe.mjs:271` refuses an extensionless relative `@import "./theme"` (ENOENT, exit 2); `@tailwindcss/node` resolves with `extensions: [".css"]` and compiles it.
- **W11 low.** `eslint.design.config.mjs:25` "fixtures run this config on 10.4.0"; tooling pins 10.11.0 (`test_recipes.py:483`).
- **W12 low.** `stylelint.config.mjs:864` and `:1053` are the same `custom-property-pattern`; the comment at `:1051-1052` describes a relaxation that does not exist.
- **W13 low.** `pre-commit-design-gate.sh:365` token-file grep `(^|/)([^/]*-)?tokens\.css$` misses `design.tokens.css` and `src/tokens/colour.css`, which `design-rules.json` `token_files.globs` name.
- **W14 low.** `check_roles.py:238` and `tools/fail_before.py:196`, `test_mcp.py:132`, `test_schema_sources.py:117`, `install_gate.py:63`, `release_check.py:41`: unused `noqa` directives (a reviewer with ruff enabled flags these).

### 3.3 design-token-migration (census, proposal, codemod)
C1, C2, H11 to H14 above, plus:
- **M1 medium.** `cluster_values.py:1422-1442` `cluster_motion` emits `mo-NNN-pair` and `mo-NNN` each with `occurrences=len(css_items)`; `render_reconciliation` (`:2396`) and `main` (`:2710`) sum both: "Mechanically replaceable 4 | 100%" plus "Needs a decision 2 | 50%". Count once.
- **M2 medium.** `extract_literals.py:238` `TW_ARBITRARY_RE`: variant chain `(?:[a-z]+:)*` and lookbehind `(?<![\w:./-])` miss `-mt-[13px]`, `2xl:p-[13px]`, `group-hover:`, `peer-focus:`, `data-[state=open]:`, `aria-checked:`, `max-md:` (never counted, so never rewritten), while `md:hover:p-[13px]` works. Variant atom `(?:[\w-]+(?:\[[^\]]*\])?:)*`, optional leading `-`.
- **M3 medium.** `extract_literals.py:730-741` `classify_length` final `return "length"`: `font: 700 14px/1.5` size, `transform: translateY(13px)`, `filter: blur(4px)`, `grid-template-columns: 200px` all become spacing lengths, inflating the "distinct spacing values" headline; contradicts `extraction-and-clustering.md:135`.
- **M4 medium.** `cluster_values.py:1553-1572` `cluster_z`: `z-index: -1` ranks onto rung 0 and the codemod rewrites it to `var(--z-raised)` (10): the sign flips. Route negatives to `Unmapped`.
- **M5 medium.** `references/extraction-and-clustering.md:229-243` §6 role table disagrees with `role_for` (`cluster_values.py:843-898`) in three cells: neutral-100 colour (code `--fg-on-inverse`, table none), neutral-800 background (table `--bg-inverse`, code none), accent-600 background (table says both `--bg-accent` and `--bg-accent-hover`; code 600 → `--bg-accent`, 700 → hover). Verified by running `role_for`.
- **M6 medium.** `cluster_values.py:1142-1150`, `:1225-1227` vs `:1638-1660`: `$gutter: 24px` gets "Add a Tier-2 role for `other`" while `$brand: #hex` gets "delete the variable" (`framework-migrations.md` §2 says delete).
- **M7 low.** `extract_literals.py:567-569` `@apply p-[13px]` in a stylesheet is not swept (statement without `:` dropped); `:247-249`/`:1040` Svelte/Astro `class={expr}` and `class:list={[…]}` not swept while the same expression in `.jsx` is.
- **M8 low.** `apply_codemod.py:974-981` `mkstemp` (0600) + `os.replace`: POSIX file mode becomes 0600 after `--apply`. `shutil.copymode` before replace.
- **M9 low.** `apply_codemod.py:934-935` a `GENERATED_MARKERS` hit in `text[:800]` drops the file with no `Skip` row, against "every skip explains itself".
- Already replaced in the in-flight #129 (not reported): the ΔE-only ramp choice; `size-*` classed as padding.

### 3.4 design-system-versioning, design-system-docs, figma-variables-sync
H1 to H3 above, plus:
- **V2 medium.** `diff_system.py:912-917` `_snapshot_from_contract`: with several DTCG files, a later file's `notWritten` value loses to an earlier file's written value (`if name not in held`); the docs promise last-wins. Demonstrated (false MAJOR `tier1-value-changed`). Walk the files once, in order, as `read_tokens` does.
- **V3 medium.** `deprecate.py:655` `cmd_import` reads `read_deprecations` only; the `$deprecated` marks in `$extensions` (not-written tokens) that `diff_system.py:1441-1477` honours are never imported, so `status`/`scan`/`mapping` never see them; `scripts.md:27` says they do. Do it once in the shared `read_deprecations`.
- **V4 medium.** `deprecate.py:449-450` `SCAN_EXT` includes `.json`/`.md`/`.mdx`, `:527-533` labels every non-CSS hit manual: the emitted `mapping.json` (its rules contain `"var(--fg-faint)"`) scans as 22 manual hits, "NOT SAFE to remove", forever. Skip files whose JSON `schema` is the migration mapping or the ledger.
- **V5 medium.** `deprecate.py:557-586` `cmd_add` never looks up `--replacement`: a replacement that is itself deprecated (or undeclared in `--source`) is accepted and `mapping.json` rewrites one deprecated name onto another.
- **V6 medium.** `build_docs.py:1117`/`:521` inline the search-index JSON into `<script>` unescaped: a `</script>` in a token note or JSDoc ends the script. Replace `</` with `<\/`.
- **V7 medium.** `--out` may equal the input: `figma_audit.py:1213-1217`, `diff_system.py:2733-2736`, `figma_to_tokens.py:1517-1521` (`write_out`); `release_check.py:93` already guards this. Demonstrated (the export replaced by its report; the published snapshot replaced by the diff). Same class: **G7**, **E9** below.
- **V8 medium.** A non-object JSON top level (`[]`) tracebacks: `diff_system.py:2069` `load_ledger` (exit 1, the gate's code), `deprecate.py:147`, `build_docs.py:1409` and `:1445` (baseline never shape-checked); `load_snapshot` at `:1024` guards.
- **V9 medium.** `design-system-versioning/references/scripts.md:9` and the `diff_system.py:2547-2550` help say "a `contract.json`, or a directory containing one"; `load_snapshot` (`:1007-1018`) searches a directory for `system.json`/`tokens.css`/`theme.css` only, exit 2.
- **V10 medium.** The "copy the scripts into your own `scripts/`" headers in `design-system-versioning/SKILL.md:16-19`, `design-system-docs/SKILL.md:16-19`, `figma-variables-sync/SKILL.md:16-19` name only the command scripts, not the `project_config.py`/`dtcg.py`/`figma_common.py` they import, and `install_gate.py:51-53` vendors none of them: `ModuleNotFoundError`. Demonstrated.
- **V11 medium.** `figma_common.py:135-138` `oklch_to_rgb` clamps out-of-sRGB channels silently in `--reverse` (`oklch(70% 0.3 150)` → `r 0, g 0.797, b 0`, exit 0); the forward direction refuses a P3 token without `hex` and names it. Report a `clamped` problem.
- **V12 low.** `figma_to_tokens.py:1613-1617` and `figma_audit.py:1163-1170`: an input whose only tokens are unsupported exits 2 "contains no variables … pass --shape", hiding `doc.unsupported`/`doc.unread`.
- **V13 low.** `figma_to_tokens.py:420-436` `css_value` FLOAT branch: a `$type: duration` token not named `dur-*` writes correct CSS but `"unresolved": true` in `tokens.json`.
- **V14 low.** `diff_system.py:1029` accepts any `design-system-docs` schema version (`DOCS_SCHEMA` at `:91` is unused); `build_docs.py:1409` requires the exact one.
- **V15 low.** Doc/code nits: `change-classification.md:336-337` says `theme-override-changed/removed` are major, `diff_system.py:1797`/`:1207` give patch when the resolved value is unchanged (demonstrated); `:345` lists `component-renamed`, never emitted; figma `references/scripts.md:8-11` omits the `resolver` shape and `-o/--out`; `figma_audit.py:273` `CODE_TITLES["TIER_VIOLATION"]` has no emitter; docs `references/scripts.md:7-20` omits `--no-color-impl`; `figma_to_tokens.py:1626-1629` `--format all` without `--out-dir` writes into cwd and ignores `--out` silently.
- **V16 low.** `workflow-commands/figma-sync/SKILL.md:5` argument hint omits the `resolver` shape both scripts accept.

### 3.5 content-model-to-ui, client-presentation-builder, email-template-system
H9, H10 above, plus:
- **E1 medium.** `introspect_schema.py:2058-2090` `_temporal`: `system` (computed at `:2059`) is used in the `date` and `timestamptz` branches, not the fall-through at `:2085`: naive `timestamp` `created_at`/`updated_at` (every Prisma `DateTime @default(now())`, Drizzle `timestamp()` without `withTimezone`) become an editable datetime-picker placed L D F. `field-mapping.md:56`, `:103-104` and the worked example disagree with each other on this.
- **E2 medium.** `scaffold_ui.py:3446-3484` `build_files` and `:3606-3612` `main`: a table name goes into output paths unsanitised; `../evil` writes above `features/`, `../../evil` leaves `--out`. Demonstrated. Refuse `/`, `\`, `..`, NUL, or slug the folder name.
- **E3 medium.** `scaffold_ui.py:1992-1995` `control_jsx` (`errors.{name}`, `fieldId('{name}')`), `:1296` `emit_types` (`| '{w}'`), `:3404-3409` pydantic attr: a column `"2fa"` gives a TSX syntax error and a Python `SyntaxError`; `"it's"` an unterminated string in `order.types.ts`. `class`, `default`, `from`, `display-name`, `naïve` all work (the siblings were fixed). Use `json.dumps` for names, `errors[…]` when `prop_key` differs, `_` prefix for a leading digit. Demonstrated with the TS parser and `py_compile`.
- **E4 medium.** `introspect_schema.py:734-746` `_pinned_to_caller` misses `auth.uid()::text = owner_id::text`, `(auth.jwt() ->> 'sub')::uuid = user_id` and `auth.uid() = "userId"` (quoted camelCase: every Prisma-created database), giving false `authority-writable` warnings; the mirror spellings pass. Compare operands with casts stripped and use `_names()` for the column.
- **E5 medium.** `introspect_schema.py:3193` `detect_format` tests `"pgTable(" in text` while `parse_drizzle` (`:3045`) accepts `pgTable.withRLS(`: a withRLS-only schema is routed to `parse_gen_types` with a misleading error, exit 1.
- **E6 medium.** `build_email.py:1064` `minify_html` `re.sub(r">\s+<", "><")` joins words across inline siblings (`<strong>Hello</strong> <em>world</em>` renders "Helloworld"); the docstring says it never joins two words. Collapse to one space, or strip only between block/table tags.
- **E7 medium.** `email-client-matrix.md:275` says the three templates retain "600–750 bytes" of `<style>`; the build measures 751, 919 and 830.
- **E8 medium.** `assets/templates/newsletter.html` (6 warnings), `product-announcement.html` (6, one a plain token miss: `line-height: 28px is a literal; --type-lead-line holds it`), `transactional-receipt.html` (1) do not pass `lint_email --source`; `SKILL.md:58-66` says they "already compile clean" and `--strict` fails the untouched template. The built outputs lint 0/0.
- **E9 medium.** `build_email.py:1325-1379` and `lint_email.py:1206-1243`: `--out`/`-o` equal to the input overwrites the token-authored source (exit 0) or replaces the email with the lint report; `build_presentation.py:2699-2707` `emit_css` writes `DIR/tokens.css` over a `--tokens` file in that `DIR` (traced).
- **E10 medium.** `build_presentation.py:1312-1333` `_cover` and `:169-175` `Decision.placeholders`: header placeholders `<company>`, `<your name>`, `<YYYY-MM-DD>`, `<stage>` reach the cover slide and footer with no gap reported (only "no date" is checked, and a placeholder date counts as present).
- **E11 low.** `lint_email.py:1006-1010` `source_declarations` yields the `<style>` element's line for every rule: every finding says "(line 19)".
- **E12 low.** `introspect_schema.py:2887-2909` `parse_prisma`: `Unsupported("geometry")` becomes type `unsupported` with a text-input instead of unwrapping to `geometry`.
- **E13 low.** `build_presentation.py:450-451` `load_perf` and `:551-558` `load_a11y` call `.get` on list items with no `isinstance` guard (`load_audit` has one): `AttributeError` instead of `BuildError`.
- **E14 low.** `email-template-system/SKILL.md:58-78` quick start is bash-only (`mkdir -p`, `cp`, `cat`) against the cmd.exe rule.
- Noted, not reported: `ADD CONSTRAINT … NOT VALID` and `CREATE UNIQUE INDEX … INCLUDE/NULLS NOT DISTINCT` silently drop the constraint; `pgSchema('auth').table(…)` is skipped silently; the client-matrix version claims (Samsung 6.1, Thunderbird 68/78/91, caniemail dates) are unregistered in `evidence.json`.

### 3.6 a11y-audit-runner, perf-budget-gate, component-state-matrix, design-critique-gate
H4 to H6 above, plus:
- **G1 medium.** `a11y_static.py:903-908` `aria-hidden-focusable` counts descendants that cannot take focus (`<input type="hidden">`, `hidden`, `inert`, `tabindex="-1"`; the `inert` pairing is what the rule's own fix text recommends) and, through `build_tree` (`:544`, `:549`), only direct children, so `<div aria-hidden="true"><ul><li><a href>` is never reported. Demonstrated.
- **G2 medium.** `a11y_static.py:1329-1347` `_has_name` looks one level deep and has no case for a capitalised component child: `<button><span><img alt="Close"></span></button>` and `<button><Icon/></button>` are both `empty-control`; by the file's own rule (`:385-388`) the second must be "cannot tell".
- **G3 medium.** Budget values are not type-checked: `perf_audit.py:1088-1092`, `:1109-1111`, `:1136-1138`, `:1150`, `:1162`, `:1218`, `:1056`, `:1085` (`"css": "60KB"` is a `TypeError` traceback, exit 1; a list section an `AttributeError`); `measure_vitals.mjs:877-880` and `a11y_runtime.mjs:2256-2257`, `:1753-1760` silently pass a string limit ("every metric inside its limit", exit 0): a typo disables the gate without a word. Validate at load in all three, exit 2 naming the key.
- **G4 medium.** `critique_report.py:871-873`, `a11y_runtime.mjs:2281-2283`, `measure_vitals.mjs:924-926`: `--out`/`--report` overwrite their own input (findings replaced by the critique; the audited page replaced by the JSON report). Same class as V7/E9.
- **G5 medium.** `a11y_runtime.mjs:1196-1197` `forcedColorsSurvey`: the unanchored `/button|a|summary/` matches `main`, `nav`, `span`, `table`, `label`, `header`, `aside`, `article`, `textarea`, `dialog`: `fillOnly` is inflated by every filled layout element. Demonstrated (6 for 1 button). Anchor it.
- **G6 medium (the macOS TBT flake, with a cause).** `tests/test_browser_runtime.py:356-378`: the control click lands at `load + 500 ms` while the fixture's 3-second busy task starts at 1500 ms on the page clock; on a slow runner load finishes after about 1 s, the click lands inside the task, and `inp < during/2` fails. Deterministic in page-load time, not noise. Fix in the test: `--interact-at 5000` (the task ends at 4.5 s) and assert on `clickedAt`. No product change.
- **G7 medium.** `references/automation-coverage.md` §3 reads as this suite's coverage, but several named mechanisms exist in neither gate: 1.3.4 (`:70`, one of the seven "Full" rows: no orientation check, and axe's `css-orientation-lock` is `experimental`, excluded by the default tag set); 2.4.11 (`:90`), 3.3.8 (`:106`), 1.4.12 (`:80`), 1.4.13 (`:81`), 2.1.4 (`:84`), 2.2.2 (`:87`), 3.2.1/3.2.2 (`:101-102`), 3.3.1 (`:104`), 4.1.3 (`:113`). `SKILL.md:26`, `:49` and `a11y_runtime.mjs:18-20` quote "7 of the 55". Add a "this suite" column or re-word the intro; `test_docs` can assert every "Full" row names an existing check.
- **G8 low.** `perf_audit.py:117-120` `NOT_SHIPPED` skips any `report.html`/`stats.html` silently (a real page of that name is never weighed or scanned).
- **G9 low.** `a11y_static.py:1011`, `:1016-1017`: the `EXPR` sentinel leaks as `type="\x00expr\x00"` into messages and JSON; `:303` `r"job[_-]?title|^title$&"` (the trailing `&` makes `^title$` unmatchable); `:304` `apartment|suite|unit` fires on `name="units"` with `type="number"` (`number` missing from `INPUT_NOT_PERSONAL`, `:166-167`).
- **G10 low.** `a11y_static.py:1526` `focus-ring-transition` flags `transition: outline-color` although its own fix text allows transitioning the colour.
- **G11 low.** `critique_report.py:341` `int(raw.get("count"))` outside `CritiqueError` (a `ValueError` traceback, exit 1); `:318` `bool("false")` is true, demoting a major finding to taste.
- **G12 low.** `a11y_runtime.mjs:535-536` `/^wcag\d{3}$/`: axe's `wcag1412` (`avoid-inline-spacing`) is not turned into `1.4.12`.
- **G13 low.** `design-critique-gate/SKILL.md:210` `python -m scripts.audit_design <path> --json > audit.json` fails in cmd.exe (`<path>` is a redirection).
- **G14 low.** `perf_audit.py:27-28` header claims a "missing srcset" check no rule implements; `SKILL.md:181` does not claim it.
- **G15 low.** `a11y_static.py:1764` a baseline whose JSON is not a list (`5`) is a `TypeError` traceback; `perf_audit.load_baseline` (`:1189`) crashes the same way on a scalar.
- **G16 low.** `perf_audit.py:856` `families` is computed and never used (ruff F841): either a dead remnant or an intended "font-family with no @font-face" check that was never written.
- Characterised, no code change needed: the "unbundled `@import` chain" open item is not a miscount. `perf_audit` weighs every sheet as a request, so the starter's seven sheets are `requests-css 7 > 4` plus six `css-import` errors; nothing is double-counted. The fix is the starter's build step or a documented `requests.css`. `test_critique_snapshots` passes here (6 tests, Playwright Chromium); the only fragility is the full-page capture retry at `critique_snapshots.mjs:270-281`. The MCP size cap (`design_gates.mjs:140-172`) trims nested lists at any depth correctly.

### 3.7 Docs, CI, release, workflow commands
- **D1 medium.** `docs/HANDOFF.md:51` lists "a local build never matches the release's checksums" as open and `tooling/README.md:9` says "byte-identical on a rebuild"; `tooling/release/build.py:9-13` explains the real cause: Windows Python 3.14 deflates with zlib-ng (`1.3.1.zlib-ng` here), CI's Linux with zlib; `tooling/release/compare.py` compares by content. Reword both docs; the item is closed.
- **D2 medium.** `.github/workflows/release.yml:23`, `:27` pin `actions/checkout@v7` and `astral-sh/setup-uv@v10.2.0` by tag while the job holds `contents: write` and `GH_TOKEN`, and `checkout` keeps `persist-credentials: true`; `evals.yml:43-51` follows the SHA rule from CodeRabbit on #95. Pin both to SHAs, `persist-credentials: false`.
- **D3 medium.** `plugins/web-design-suite/README.md:194-195` "the three browser scripts need Node"; there are six `.mjs` entry scripts (five browser gates plus `tw_probe.mjs`).
- **D4 low.** `CLAUDE.md:44` has an unquoted `<ids>` in a cmd.exe command (cmd: "The syntax of the command is incorrect"); `dev plans/next-session-prompt.md:300` has `--plugin-dir <export>/plugins/…` inside a bash block. Same class as G13.
- **D5 low.** `CLAUDE.md:93` "evals.yml (the routing evals)" vs `:20` (both, by hand); `:90` lists two of the five `tools/` files.
- **D6 low.** `perf-budget-gate/references/budgets.md:274-280` quotes the Core Web Vitals thresholds "verified against web.dev" with no `evidence.json` entry; `test_evidence.FIGURE` (`:34-40`) never matches "2.5 s", so the test cannot enforce it. Also unregistered: `README.md:289` "Claude Code 2.1.269 or later" and the Baseline browser versions.
- **D7 low.** `tools/check_pointers.py:27-28`, `:103` walk `skills/` only: four `§` pointers in `agents/supabase-security-reviewer.md:10`, `workflow-commands/schema-to-screens/SKILL.md:39`, `email-build/SKILL.md:39`, `tw-probe/SKILL.md:22` are unguarded (all resolve today).
- **D8 low.** `dev plans/next-session-prompt.md:336` byte table: landing-page-conversion 20,497 vs 20,496 on disk.
- **D9 low.** Unused imports and f-strings (ruff F401/F541) a reviewer with lint enabled will list: `figma_audit.py:47`, `figma_to_tokens.py:55`, `generate_matrix.py:51`, `:56`, `introspect_schema.py:70`, `:75`, `build_email.py:69`, `:83`, `extract_system.py:59`, `deprecate.py:66`, `diff_system.py:76`, `apply_codemod.py:73`, `cluster_values.py:73`, `figma_audit.py:49`, `tests/test_scaffold.py:17`, `:19`, `:24`, `tests/test_tools.py:14`; F541 at `a11y_static.py:938`, `build_presentation.py:1007`, `introspect_schema.py:3311`, `scaffold_ui.py:3062-3069`, `diff_system.py:2267-2268`, `:2397`, `cluster_values.py:1223-1224`, `figma_to_tokens.py:597`, `tooling/release/build.py:118`. B904 (`raise … from`) at twelve `except` sites. The B023 closure-in-loop hits are all invoked inside the same iteration and are not bugs.

### 3.8 Test suite (beyond H15)
- **T1 medium.** `tests/test_evidence.py:155-161` `test_no_entry_outlives_its_figure` passes if the figure OR any `also` substring is in the doc; "19 categories" is kept alive by the bare "143", "37–41%" by "41%", "2,000+ audits" by "13,000"; their main figures are already absent from the listed docs. Require the figure itself, word-bound the `also` values, then fix the register.
- **T2 medium.** Wall-clock thresholds on shared runners: `tests/test_content_and_a11y.py:828-832` absolute `assertLess(large, 20)` seconds; `test_browser_runtime.py:334-343` TBT median `< 50` then `>= 150` ms; `test_token_migration.py:507-509`. Keep the ratio bounds, drop the absolute ones, assert on timestamps relative to TTI.
- **T3 low.** `tests/test_powershell_json.py:107-121` `NoFragileJsonReads`: no positive control for either regex, scans only `skills/*/scripts`; a named import `JSON.parse(readFileSync(` passes.
- **T4 low.** `tests/test_facts.py:139-144` asserts only behind two conditionals; a rewording of `runtime-checks.md`'s intro disarms it silently.
- **T5 low.** `tests/test_docs.py:823` `PythonFloor` and `:870-874` omit `workflow-commands/*/scripts` and `shared/`.
- **T6 low.** `tests/test_mcp.py:52-53` `test_claude_plugin_validate_strict_passes` skips on every CI cell; the `validate` job is the real guard.
- **T7 low.** `tests/test_doc_snippets.py:53` flips `sys.dont_write_bytecode` process-wide; `wds_support.load_script` (`:140-146`) writes `__pycache__` into the plugin on a hand run without `-B`, depending on module order. Set it once in `wds_support`.
- **T8 low.** 66 assertion loops without `subTest` (`test_numbers.py:187`, `test_policies.py:170`, `test_figma_sync.py:70`, `test_scaffold.py:223`, `test_tools.py:260`, …).
- **T9 low.** DTCG fixtures mostly use the pre-2025.10 string-hex colour form (`test_project_config.py:693-699`, `:777`; `test_dtcg.py:345-408`; `test_figma_sync.py`), relying on `dtcg.py:212` passing any string through.
- **T10 low.** `ResourceWarning: unclosed file` at `tests/test_versioning.py:293` and one more `json.loads(open(...).read())` site in the same module (seen in the baseline run).
- **Coverage, for planning:** scripts with a single test module: `crux_check.py`, `generate_type_scale.py`, `sync_snippets.py`, `design_gates.mjs`. CLI flags no test passes: `a11y_static --category --no-color`; `build_presentation --max-decisions`; `generate_matrix --profile --themes`; `introspect_schema --questions`; `critique_report --layer --min-severity --no-taste`; `build_docs --no-examples --project`; `extract_system --check-color-impl --color-impl --no-color-impl --props --root-font-size`; `deprecate --codemod --fail-on-usage --limit --mapping`; `diff_system --check-color-impl --color-impl --mapping --project`; `apply_codemod --no-diff`; `cluster_values --*-tolerance`; `extract_literals --include-tokens --min-count --top`; `build_email --keep-comments --minify --no-inline --no-mso --text-only --width`; `lint_email --ignore --verbose`; `figma_audit --collection --deadline --no-color --shape --styles`; `figma_to_tokens --collection --flat --shape --unit`; `perf_audit --category --include-maps --no-color --page-type`; `audit_design --no-color`; `generate_color_ramp --chroma-scale`; `generate_type_scale --preview --tracking-model`; `fail_before --python`; `release_check --project --published`. `mcp/design_gates.mjs:116` `process.cwd()` fallback is never exercised. No test guards `perf_audit` + unbundled `@import` or the `check_roles` gamut clamp (W2).

---

## 4. The in-flight branch (#129), for the record only
CI on its head failed at 12:10 today on all six suite cells with one failure: `test_real_tools.StylelintConfig.test_the_references_css_snippets_pass_the_config`, snippet `design-token-migration/references/framework-migrations.md:347`, `no-invalid-position-at-import-rule`. Not audited further; the working agent owns it. C1 above still applies to that branch's `[`-path.

## 5. What was checked and found clean
Full lists are in each slice's notes (§9). In brief: all 40 copies of the four masters; Python/Node reader parity on 28 odd configs and the whole DTCG and resolver rule set (except S1, S4 to S7); JSON encodings UTF-8/16/32 with and without BOM; the hooks on every malformed input; the MCP server's validation, batching and error shapes; the audit's CSS scanner edge cases, specificity, Tier-1 advice through prefixes and renames, CSS-in-JS detection, exit codes and SARIF; `check_roles` `@supports`, `var()`, inheritance and both preferences; the ramp generator's OKLab, sRGB and P3 matrices on known values; the type scale; `tw_probe` on prefixes, `@source`, `url()` imports, `@theme inline`/`reference`, `--*: initial`, Windows paths; the ESLint shorthand regexes and scopes; the stylelint rules against the audit (except W4); the hook's POSIX-ness; `install_gate` and `new_system`; the census's value normalisation, masking and Sass claim order; the codemod's negative-cancel, direction guard, idempotence, tripwires and exclusions; proposal determinism; `diff_system`'s change kinds, bump rules, renames, contrast deltas and `notWritten` restore (except V2); `deprecate`'s window, marker idempotence and codemod rules; `extract_system`'s parser and contexts; `build_docs` escaping of every cell; the Figma REST mapping, mode handling, selectors with spaces and escapes, alias chains, alpha forms and mode-limit refusal; the SQL, Prisma and Drizzle parsers on the full edge-case list (except H9, H10, E1, E4, E5, E12); the scaffold's TS output (118 files parse) and the audit on its output; presentation escaping and slide orders; the email builder and linter on the built templates; the a11y scanner on JSX, Svelte, roles, labels, ids, dialogs; the runtime gates' arguments, axe injection, tab order, focus, densities, contrast, reflow, exit codes; `browser_common` resolution and messages; `perf_audit`'s weighing, gzip rule, render-blocking, LCP, fonts, growth, JSONC budgets; `measure_vitals`'s throttles, CLS windows, TBT, thresholds; `crux_check`'s key handling; the matrix manifest, cell ids, escaping, shim and comparator; the critique schema against the critic agent; every `${CLAUDE_SKILL_DIR}`/`${CLAUDE_PLUGIN_ROOT}` path and every documented flag (173 command lines) against `--help`; SKILL.md budgets and descriptions; agents' frontmatter; cross-doc numbers (3.6.0 at `d91a146`, 21/21 open items, 1,121 tests, 23+11 evals, 16 commands, 6 agents, 5 MCP tools, release order, Node range, CodeRabbit policy); `check.py`, `fail_before.py`, `build.py`; `ci.yml`, `evals.yml`; the eval cases; README, LICENSE, manifests; the evidence register's 35 entries.

Not read line by line: the prose of the 18 web-design-studio references and landing-page-conversion's references beyond the mechanical checks (pointers, snippets, rules, flags, sizes, registered facts).

## 6. Order of work (recommended)
1. **C1, C2, H1** (file-rewriting tools), each with a fail-before test on `v3.6.0`.
2. **H4, H5, H6, H7, H8** (gates that pass what they should fail, or fail what they should pass).
3. **H2, H3, H9, H10** (silent wrong output in sync, docs and scaffold).
4. **H11 to H14** (the migration proposal's arithmetic and the recipe).
5. **The cross-cutting classes** in §8, as one PR each: the `--out` guard (V7, E9, G4), the JSON type guards (S1, V8, G3, G11, G15, E13, W6), the encoding readers (H3, S8, W7, C2, H1), the "diagnostics discarded" set (S2, H2, V11, V12, M9), the cmd.exe placeholders (D4, G13, E14).
6. Then the per-skill mediums, then the lows and the docs.

## 7. Prevention: the classes behind the findings
The 114 findings fall into eleven classes. Each has a check that would have caught it before a reviewer did.

1. **A regex with one boundary** (C1, M2, G5, G9). Rule: every token-matching regex gets both boundaries and a test with the token embedded in a longer word.
2. **One path fixed, its sibling not** (H3, S3, S6, E1, E4, V3, G2, W1, W5/W4, E3). Rule: when fixing a finding, grep for the same construct across the plugin before closing it; the review notes already say this and it keeps recurring.
3. **`read_text`/`write_text` on files the tool rewrites** (C2, H1). Rule: a script that writes back a user's file opens it with `newline=""` both ways; a test asserts CRLF survives.
4. **Encoding by assumption** (H3, S8, W7). Rule: every file read goes through one shared reader that sniffs the BOM; `grep -n 'read_text(encoding="utf-8")'` should return nothing in the scripts.
5. **`--out` equal to an input** (V7, E9, G4). Rule: one shared `refuse_overwrite(out, *inputs)` helper, called in every `main`.
6. **A JSON value's type assumed** (S1, V8, G3, G11, G15, E13, W6, S10). Rule: validate at load, exit 2 naming the key; a test per loader with `[]`, a string and a list where an object is expected.
7. **Diagnostics discarded** (S2, H2, V11, V12, M9, H11). Rule: no `_problems`, no `[0]` on a `(result, problems)` tuple, no bare `continue` on an error; every dropped item gets a named row.
8. **Doc claims the code does not make** (H5's coverage table, G7, G14, V9, V10, V15, M5, E7, E8, D1, D3, D5, W11, W12). Rule: generate tables from code where possible (the role table from `role_for`, the coverage table from the rule lists); a test that each "Full" row and each "writes X" claim names something that exists.
9. **Commands that fail in cmd.exe** (D4, G13, E14). Rule: extend `test_docs.PasteableCommands` to every fenced block and inline command in `CLAUDE.md`, the SKILL.md files and the plans; placeholders in capitals, never `<…>`.
10. **Gates that cannot fail** (H15, T1, T3, T4). Rule: every scan test has a positive control that proves the scan fires.
11. **Wall-clock assertions** (T2, G6). Rule: assert on ratios or on page-clock timestamps, never on seconds.

## 8. Method
Eight read-only audit passes over `origin/main` in a scratch worktree, one per area, each briefed with the lens distilled from the 104 Codex and CodeRabbit inline comments on PRs #105 to #129; each finding was traced in the source and, wherever a script could be run on a crafted input, demonstrated and the output quoted. The orchestrating pass then re-read the source at every critical and high finding and a sample of the mediums before accepting them. Static tooling: ruff (F, E9, B0xx, B904, PLE), `node --check` on every `.mjs`, `compileall` under Python 3.9, the project's own five consistency tools, byte comparison of all copies, a BOM/CRLF scan, and the full suite (1,121 tests, 18.5 minutes, all passing).

## 9. Where the evidence is
Fixtures and outputs for every demonstrated finding are under the session scratchpad, `%LOCALAPPDATA%\Temp\claude\C--DEV-Pro-Web-Designer-Suite-Plug-in\3985bfd1-4280-462b-8333-0e682826a220\scratchpad\`: `migration\fx1..fx7`, `studio\`, `shared\fx`, `versioning-docs-figma\`, `content-presentation-email\`, `gates\`, the slice notes `findings-*.md`, the review-comment corpus `review-comments.txt`, and the baseline run `suite.log`. Storage Sense empties `%TEMP%` when the disk runs low, so copy any fixture worth keeping into `tests/` with its regression test, not into `dev plans/`.
