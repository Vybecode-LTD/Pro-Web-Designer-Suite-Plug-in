# Changelog

## 3.1.0 — 2026-09-24

Phase 1 of the 3.0.1 review: the gates stop passing things they never checked, the
unsafe defaults go, and every documented command runs as written. Each fix has a
regression test that fails on 3.0.1 and passes here (`python -m unittest discover -s tests`).

### Upgrading: re-baseline

The design audit now finds things it used to miss, so a gate that was green may go red
on code that was always wrong:

- a literal beside a `var()` (`padding: var(--pad-sm) 13px`);
- spacing inside `@media` / `@container` / `@supports`;
- HTML, Vue, Svelte and Astro files: `<style>` blocks, `style=""`, class lists;
- literal Tailwind utilities (`duration-300`, `z-50`, `border-2`, `bg-accent/37`,
  `p-(--space-6)`, `space-y-related`).

Existing debt: `audit_design.py src/ --write-baseline .design-baseline.json`, as before.
Baseline keys are now relative to the baseline file, so a 3.0.1 baseline written from
the folder that holds it keeps matching.

### The gates

- **audit_design**:
  - A `var()` no longer hides a literal written beside it.
  - Spacing inside media, container and supports queries is checked.
  - HTML and single-file components are audited; HTML email is skipped and routed to `lint_email`.
  - A file named explicitly that is not CSS, JS or HTML is skipped and listed, not read as JavaScript.
  - A folder with nothing auditable in it exits 2 instead of reporting "clean".
  - Files saved with a UTF-8 BOM no longer fail as "unlayered".
  - The baseline matches however the path is spelled.
  - The clean message names the laws it checks (L1–L6).
- **a11y_runtime**:
  - Contrast is measured for colours in any syntax, including the suite's own OKLCH.
  - A modal `<dialog>` is no longer a "keyboard trap", and what sits behind it is not "unreachable" or "unnamed".
  - Focus inside a same-origin iframe is followed.
  - axe runs in every frame.
- **snapshot_matrix**:
  - The default per-pixel tolerance is 0.03 (was 0.10, coarser than the suite's own hover and pressed overlays).
  - Every hover, active and focus-visible cell must differ from its default cell, with no baseline needed.
- **a11y_static**:
  - Linear time on large pages: 4,000 rows took 46 s and now take 0.7 s.
  - Files it cannot audit are skipped, not parsed.
- **The pre-commit hook** runs `a11y_static` on staged files when `scripts/a11y_static.py` is vendored. The inline hook snippets in the docs are replaced by the shipped hook.

### Unsafe defaults

- **content-model-to-ui**:
  - Credential columns are matched by the documented patterns (`*_token`, `*_hash`, `*_secret`, `*_key`, …) and never displayed or editable.
  - Columns that carry authority (`role`, `is_admin`, `owner_id`, `org_id`, `plan`, `credits`, a profile id that references `auth.users`, …) are read-only by default, with their own question.
  - The Supabase guidance now describes how writes really fail under row-level security, and how to protect columns.
- **Starter CSS**:
  - Density and theme work on a subtree, not only on `<html>`.
  - Themes set `color-scheme`, so native fields stay readable.
  - `[hidden]` beats every layer.
  - Dark error text, `.inverse` sections and control borders meet WCAG AA.
  - Dialogs keep their viewport limit.
  - The focus ring is an outline, which no component `box-shadow` can remove. The same applies to the Tailwind `focus-ring` utility, which had `outline: none`.

### Honest output

- **The client deck**:
  - Claims "passes" only when the accessibility results say so, and "keyboard-tested" only when the decision log records it (`## Tested by hand`).
  - The performance slide's title follows the budget.
  - The audit is credited with the laws it checks.
- **The critique report**:
  - The defence sheet carries open confirmed defects and labels suspicions.
  - An audit rule is folded into a hand finding only when the finding claims it (`covers`, or the id in backticks).
  - Every merge is reported.

### Pipelines

- **Figma sync**:
  - Reads DTCG 2025.10: colour objects, `{value, unit}`, `$ref`, `$extends`, `$root` and group `$type`. Values it cannot express are reported, never written as Python.
  - Composed-colour opacity is a percentage.
  - `figma_audit --tokens` checks against the project's own ramps.
  - Output carries no clock time (`SOURCE_DATE_EPOCH` to stamp one).
- **Token migration**:
  - Focus rings map to `--elevation-focus` at review confidence.
  - `src/lib` is no longer treated as vendor code.
  - The codemod has `--include-vendor` and rewrites files named explicitly.
  - Minified CSS is extracted in linear time.

### Docs

- Every SKILL.md says how its scripts are run: by path, from the project root, via `${CLAUDE_SKILL_DIR}` and `${CLAUDE_PLUGIN_ROOT}`.
- The README quick start runs as written.
- The rebase recipe keeps the teammate's change; the before/after audit strands nothing in the stash.
- The handoff guide no longer describes a `build-tokens.mjs` that does not ship.
- The Tailwind v3 layer guidance matches what v3 emits.
- The Tailwind v4 "build error" claims are corrected.

### Also fixed

- **The migration's proposed `tokens.css`** now includes the starter's fixes: roles are declared where density and theme are set, the dark theme sets `color-scheme`, and there are `.inverse` roles, dark error text and control borders that meet AA.
- **The Supabase samples**:
  - The optimistic update throws on a rejected write (`throwOnError()`, and zero rows written), so the rollback and the message run.
  - The keyset sample validates the cursor before it goes into `.or()`.
- **The audit**: `url(icons.svg#add)` is no longer reported as a hardcoded colour.
- **Scripts run by path** no longer write `__pycache__` into the plugin.
- **The email quick start** copies a template into the project, not into the plugin.
- **The studio** writes into the repository when there is one, and makes a ZIP only when there is not.
- **The pattern examples** draw focus with an outline, not with `outline: none` and a box-shadow.

## 3.0.1 — 2026-09-21

38 bug fixes and the first regression suite (72 tests). See
`C:\DEV\dev plans\web-design-suite-bugfix-report.md` in the maintainer's workspace.
