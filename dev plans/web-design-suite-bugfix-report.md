# web-design-suite — bug-fix report (3.0.0 → 3.0.1)

Completed 2026-09-21. Released version: **3.0.0** (`C:\Users\vybec\Downloads\web-design-suite-plugin.zip`).
Installed, fixed version: **3.0.1** at `C:\Users\vybec\.claude\local-marketplaces\web-design-suite`.
Patch from the original zip to 3.0.1: `C:\Users\vybec\.claude\local-marketplaces\web-design-suite-3.0.0-to-3.0.1.patch`
(44 files: 33 changed, 11 new test files). Apply from your source's plugin root with
`git -c core.autocrlf=false apply <patch>` — the `-c` keeps Git for Windows from turning the LF files into CRLF.

Rebuilt package: `C:\Users\vybec\Downloads\web-design-suite-plugin-3.0.1.zip` (SHA256 `88011C3C…A5FA94`) —
the original zip with the patch applied, laid out like the original (one `web-design-suite/` folder,
190 entries); unpacked it is identical to the install, validates, and passes all 72 tests.
The original `web-design-suite-plugin.zip` is unchanged (SHA256 `58E07F13…27FAAC`).

Regression tests: `tests/` in the plugin, standard library only — from the plugin root,
`python -m unittest discover -s tests -v`. Set `WDS_PLUGIN_ROOT` to run them against another copy.

Raw findings from the six bug-hunt passes: `web-design-suite-bughunt/`.

## Result

**38 bugs fixed**, each with a regression test that fails on 3.0.0 and passes on 3.0.1, plus a
few guard tests that pin documented behaviour. Three findings were judged not to be bugs (below).

## How the hunt was run

1. Static pass over all 21 Python scripts: syntax warnings, undefined names, duplicate
   definitions, suspicious comparisons, text I/O without an encoding, subprocess use.
2. All 271 documented script invocations in the markdown checked against the real CLI of their
   script; every `§` section pointer, token and class named in the docs resolved.
3. Six agents exercised every skill end to end on realistic fixtures, on Windows and in WSL, with
   real Playwright/axe runs against browsers already on the machine (nothing downloaded).
4. Each confirmed bug: failing test first, then the fix, then proof on both versions. Two further
   agents implemented 13 of the fixes under the same rule; every diff was reviewed and every test
   re-run independently before it was accepted.

## Fixed

| ID | Severity | Where | Bug |
|---|---|---|---|
| 1 | wrong-result | design-token-migration/SKILL.md | Unquoted YAML: ` #3a3a3a` began a comment, so Claude saw 221 of 945 description characters |
| 2 | broken-doc | landing-page-conversion | Audit command hardcoded the claude.ai sandbox path `/home/claude/...` |
| 3 | portability | a11y_runtime / measure_vitals / snapshot_matrix | Playwright never found in the project under test; `npm root -g` crashed (ENOENT) on Windows |
| 3b | portability | same + 2 SKILL.md | Default browser `/opt/pw-browsers/chromium` exists only in the claude.ai sandbox |
| 3c | portability | same | A browser that exists but will not start (this machine's Playwright Chromium) ended the run; an explicit one crashed instead of exit 2 |
| 4 | **data-loss** | apply_codemod.py | Uncommitted-changes guard missed non-ASCII file names (any OS) and crashed or switched off under a non-ASCII repo folder — `--apply` overwrote uncommitted work |
| 5 | crash | all 21 Python scripts | Outside Claude Code on Windows (terminal pipe, git hook, CI) →, Δ, ⚠ or emoji in output raised UnicodeEncodeError |
| 6 | portability | 17 Python readers + 2 Node | JSON written by PowerShell (`> file`: UTF-16 or BOM) rejected — every documented `--json > x.json` pipeline broke on Windows |
| STUDIO-1 | **crash** | pre-commit-design-gate.sh | Hook passed `--staged`, which audit_design lacks: **every commit refused** |
| HOOK-2 | portability | pre-commit-design-gate.sh | Default `python3` is the Microsoft Store placeholder on many Windows machines — gate failed every commit |
| HOOK-3 | wrong-result | pre-commit-design-gate.sh | `DESIGN_GATE_AUDIT_MODULE` override silently skipped the audit |
| HOOK-4 | broken-doc | pre-commit-design-gate.sh | Comment promised checks audit_design does not do |
| STUDIO-2 | wrong-result | audit_design.py | Law 2: any token named `*-1` … `*-19` passed as the `calc(var(--t) * -1)` exception |
| STUDIO-5 | wrong-result | audit_design.py | Law 1: `font-weight: 700` never flagged (now `raw-weight`) |
| STUDIO-6 | wrong-result | audit_design.py | Law 1: raw colours in `border-bottom`/`outline`/`column-rule`/… never flagged; named colours in any shorthand not flagged |
| STUDIO-7 | portability | audit_design.py | Baseline from Windows suppressed nothing on Linux CI (path separators); old baselines still read |
| STUDIO-9 | cosmetic | audit_design.py | Comment said three classes; code, message and stylelint use four |
| MIG-2 | wrong-result | cluster_values.py | Tailwind `max-w-[16px]` rewritten to the non-existent `max-w-grouped` |
| MIG-3 | wrong-result | extract_literals.py | Hex colours in JSX `style={{…}}` counted twice |
| MIG-4 | wrong-result | cluster_values.py | Inline styles counted as "mechanically replaceable" though the codemod never rewrites them |
| MIG-6 | wrong-result | apply_codemod.py | Bad mapping.json exited 1 ("skipped") instead of 2 |
| MIG-7 | broken-doc | cluster_values.py | "an 7-rung ladder" against the contract's eight (wording; algorithm correct) |
| PRES-4 | crash | build_presentation.py | Write errors on `-o`/`--notes`/`--emit-css` were tracebacks, not exit 2; `--notes` did not create folders |
| PRES-5 | cosmetic | build_presentation.py | Keyboard-help answers squeezed to 32–67px / up to 7 lines → 178px / ≤2 lines (measured in Chromium) |
| PRES-6 | wrong-result | build_presentation.py | Duplicate decision ids rendered identically; auto-numbering could reuse a taken id |
| GATE-1 | wrong-result | a11y_static.py | JSX spread `{...props}` treated as "no attributes" → false no-label / no-alt / empty-control errors |
| GATE-3 | cosmetic | a11y_runtime.mjs | axe fix text cut mid-word at 300 characters and run into the URL |
| GATE-6 | wrong-result | lint_email.py | Preheader hidden with `display:none;opacity:0` → false "no preheader found" error |
| CONT-1 | wrong-result | introspect_schema.py | `NOT NULL` inside a CHECK made a nullable column required, with a spurious rule |
| CONT-2 | wrong-result | introspect_schema.py | Every cascade-deleted child with a name of its own (users, products…) embedded in the parent's form |
| CONT-3 | broken-doc | scaffold_ui.py | Fresh css-modules scaffold failed `audit_design --strict` (reduced-motion spinner) |
| CSM-1 | wrong-result | generate_matrix.py | Template without `{attrs}` accepted — every cell identical while coverage said all was fine |
| SYS-1 | portability | extract_system.py | system.json embedded the machine's absolute path (username) and `\` separators |
| SYS-2 | wrong-result | deprecate.py | `retire` of a never-scanned deprecation went through without `--force` |
| SYS-4 | wrong-result | build_docs.py | `--check` never validated `.example.html` overrides |
| FIGMA-1 | wrong-result | figma_to_tokens.py | Records-shape Light/Dark rows both emitted under `:root` — dark silently won |
| FIGMA-3 | wrong-result | figma_to_tokens.py | `--reverse` dropped `--font-sans`/`--font-mono` as "composites" |
| FIGMA-4 | wrong-result | figma_audit.py | Missing-dark-mode check ignored border-* semantic roles |

Covered by the fixes above, each a different command the hunt caught failing the same way:
fix 5 — PRES-2/3, STUDIO-8, MIG-1, SYS-3, GATE-2, GATE-4, FIGMA-2; fix 4 — MIG-5;
fix 6 — PRES-1, GATE-5; GATE-1 — CONT-4 (the generated inputs spread their props).

Docs changed with the behaviour: two SKILL.md browser-default lines, component-state-matrix
SKILL.md (`{attrs}` required), field-mapping.md §6.2 (owned children), the README (font weights
in L1; a "Regression tests" section) and the audit's own help text. Version 3.0.0 → 3.0.1.

## Judged not to be bugs

- **STUDIO-3** — `*-tokens.css` files count as token files: deliberate; real names like
  `design-system-tokens.css` depend on it. Dodging the gate needs a misleading file name, which
  review sees.
- **STUDIO-4** — no check that `var(--x)` names a real token: never promised by audit_design
  (only by the hook's comment, now corrected). A reliable version needs the token files even when
  only staged files are audited — worth building as a feature; the dead `declared_props` variable
  in audit_design.py marks where.
- `npx --no-install` refusing when stylelint is not installed: a loud failure of a gate whose
  tool is missing, which is defensible.

## Commands run and results

| Check | Result |
|---|---|
| `python -m unittest discover -s tests` on 3.0.1 | **Ran 72 tests — OK** |
| same with `WDS_PLUGIN_ROOT` = original 3.0.0 | FAILED (failures=100, errors=6) — the fail-before proof |
| `claude plugin validate --strict` (plugin.json, marketplace.json) | both passed |
| `claude plugin update web-design-suite@web-design-suite` | 3.0.0 → 3.0.1; cached copy identical to source (137 files) |
| fresh session, Claude Code 2.1.275, cwd outside C:\DEV | plugin 3.0.1 loaded, 13 skills registered |
| patch applied to a fresh extract of the original zip | `git apply --check` and apply OK; 137/137 files identical to the install |
| `a11y_runtime.mjs --file bad.html`, no `--browser`, real Playwright + axe | picked Playwright's own Chromium; 4 violations; exit 1; fix text ends on a word |
| static scan / 271 documented commands / § pointers, re-run on final code | nothing new |
| shipped CSS (starter styles, theme.css, page-sections.css, deck-tokens.css) | `audit_design --strict` clean |
| generated output (matrix chrome, docs chrome + examples, both scaffolds, deck) | `audit_design --strict` clean (now guard tests) |
| three email templates: build then lint | 0 errors, 0 warnings each |

## Could not test

- macOS (no Mac here): the browser-path list for darwin is untested.
- Printing the deck to PDF; Figma's live REST API (Enterprise-gated); the claude.ai sandbox itself.
- Identical screenshots across machines that auto-pick different browsers — the docs now say to
  pin `--browser` / `MATRIX_CHROMIUM` for shared baselines.
- A model invoking a skill in a fresh session outside the app (not signed in there); skills were
  invoked for real in the desktop session earlier.
