# Changelog

## 3.3.0 — unreleased

### Fixed

- **The audit passed three kinds of file as clean** (SB-A9):
  - It read `//` as a comment in plain CSS, so `url(https://cdn…/hero.svg)` hid every
    declaration after it, and a custom property holding an address (`--terms:
    https://…`) hid the rest of its line. `//` is now a comment only in Sass, Less,
    styled templates and single-file components, and never inside an unquoted address
    in `url()`, where an escaped `\)` does not end it. A Sass `url()` that holds an
    expression instead (`url($asset)`) is read as code, so its comments still count.
  - A rule after a closed `@layer` block was never reported as unlayered. The finding
    now points at the first unlayered rule. A `@keyframes` block outside a layer, as
    the references and the scaffold write it, is not unlayered CSS: a keyframe is not
    a style rule. 3.2.1 flagged a file that held only keyframes.
  - A root-level `components/` or `ui/` folder, the common Next.js layout, was not a
    component file, so Law 2 was skipped there. `mycomponents.css` no longer counts
    as `components.css`. The spec's file-class examples now include both cases.
- **The token migration tool's file classes** had drifted from the audit's (N11): it
  missed `brand-tokens.css`, `design.tokens.css`, files in `tokens/` and
  `dark-theme.css` as token files, so its inventory listed their literals and the
  codemod did not skip them, and it shared the `components/` bug above. It now uses
  the audit's patterns, and the spec test holds both copies.
- **The token migration tool had the same `//` bug** (N12). After `url(https://…)` in
  plain CSS its census filed every literal to the end of the file under `background`,
  so clustering saw the wrong property, and the codemod rewrote none of them. It now
  reads comments as the audit does.
- **A singular `token.css` or `brand-token.css` was a token file** to the audit, so it
  was never checked; the spec's globs and stylelint name only `tokens`. Both copies of
  the test now follow the spec, and its examples include the two names.
- **The audit misread Sass** (SB-A24). The rules are in `design-rules.json` under
  `sass`; the audit is the only gate that reads Sass.
  - A partial holding only mixins, such as the references' own `_mq.scss`, failed as
    unlayered, because a mixin holds rules. A `@mixin` or `@function` body emits
    nothing where it is written, so the layer is now checked where it is included.
    A mixin that holds a whole rule and is included at the root of its own file,
    directly or through another mixin, is unlayered there; a mixin defined in another
    file is not followed.
  - A Sass variable holding a literal passed (`$card-padding: 24px`, then
    `padding: $card-padding`). Outside a token file, a variable that holds a length,
    a hex or functional colour, a duration or an easing curve now fails as
    `sass-literal`, in a map as in a single value. A breakpoint (`$bp`, `$bp-*`,
    `$breakpoint*`) and a variable local to a `@function` are left alone, and a
    quoted string is text whatever it spells.
  - The braces of an interpolation closed the layer around them, so after
    `.card-#{$name} { … }` the next rule was unlayered, and a declaration whose value
    was an interpolation (`margin-inline: #{$gutter}`) was never read. A brace inside
    a string in an interpolation is text too.
  - Indented Sass (`.sass`) was reported clean whatever it held: the audit follows
    braces and that syntax has none. A `.sass` file is now listed as skipped, and a
    folder holding nothing else is the "0 files audited" error.
- **A zero with a unit hid the length after it.** The audit looked at the first
  length in a value only, so `padding: 0px 13px` passed, in CSS as in Sass. It now
  reads every length (CodeRabbit on PR #7).
- **Two more scripts passed indented Sass** (N13). On a `.sass` file full of literals
  the migration census reported "no hardcoded design values found", and
  `a11y_static` reported clean for `outline: none`. Both now say which `.sass` files
  they did not read. The census prints its notes when it finds nothing, too; they
  used to appear only beside a result.

### Changed

- **Python 3.9 or newer**, down from 3.10. The scripts already ran on 3.9, the Python
  macOS still ships; now the tests do too. The harness no longer uses
  `TemporaryDirectory(ignore_cleanup_errors=)`, `write_text(newline=)` or a slice of
  `Path.parents`, all 3.10+, and the README states the new floor.

### Tests

- SB-A9 and N11: six `AuditPrecision` tests and `test_rules_spec`'s file classes.
  Against 3.2.1 all seven fail; a quoted `url("https://…")` passes on both, as the
  control.
- N12: `test_token_migration.AddressesAreNotComments`, the census and the codemod.
  Against 3.2.1 both fail, in five subtests.
- SB-A24: seven `AuditPrecision` tests and `test_rules_spec.test_sass`, which runs the
  spec's Sass examples through the audit. Against 3.2.1 seven fail, `test_sass` in
  eleven subtests; the eighth, a brace in a string inside an interpolation, guards a bug
  that existed only while this fix was in review. Its example of an interpolation inside a layer passes there, because
  3.2.1 never reported a rule after a closed block; it fails on `5fd068e`, the commit
  before this fix. `test_sass_is_left_to_the_audit` holds the spec's statement that
  the stylelint config reads no Sass, and passes on both.
- N13: `test_token_migration` and `test_content_and_a11y` each hold a `.sass` file.
  Against 3.2.1 both fail; a `.scss` file with the same rule is the control.
- `test_docs` runs `test_harness` on the floor interpreter, and `test_harness` checks
  the temporary folders and `TempDirTest.write` there. On 3.9, 3.2.1's harness errored
  in 181 tests.
- `tools/check_pointers.py --write-register` and `tools/sync_snippets.py` (without
  `--check`) are tested writing a file: UTF-8, LF, byte for byte. With 3.2.1's tools
  both tests error on 3.9, where `write_text` has no `newline`.
- The budget test passes `maxsplit` to `re.split` by keyword, as Python 3.13 asks.

## 3.2.1 — 2026-09-25

Ready to distribute. The stylelint config and both Tailwind blocks of the ESLint config
now run through the real tools in the tests, and what that found is fixed. A review of
this release before it shipped found more, and that is fixed too. Every fix has a
regression test that fails on 3.2.0, or on the release candidate for what the review
found (`python -B -m unittest discover -s tests`: 339 tests).

### Upgrading

- **Tailwind v3 with Part 5 of the ESLint config:** give `settings.tailwindcss.config` an
  absolute path anchored at your project, not at the folder ESLint runs in. Copy the v3
  block as it stands now: it looks up from the config file (`import.meta.dirname`) to
  the nearest `package.json`. eslint-plugin-tailwindcss 3.18 stops ESLint with "Could
  not resolve tailwindcss" when the path is relative, and ESLint 10 loads a config from
  whichever folder it lints, so a path resolved from the working folder broke a run from
  a monorepo root.
- **Tailwind, both lines:** Part 5 now whitelists the starter's own classes (`stack`,
  `cluster--tight`, `u-*`) in `ownClasses`; add your components' blocks there before
  you make `no-custom-classname` an error, or it reports every one of them.
- **stylelint:** the config now accepts the starter as shipped; it used to refuse it 32
  times. If you copied the starter, take its new comments with it: the
  `stylelint-disable` comments in reset.css, base.css, tokens.css and layout.css, and
  layout.css's sockets (`--center-box`, `--imposter-max`, `--reel-bleed-pad`) and
  `.imposter--bottom` shorthand.
- **Node:** the lint configs need a Node both stylelint 17 and ESLint 10 support: 20.19+,
  22.13+ or 24+.

### Fixed

- The stylelint config, run on stylelint 17.15 with stylelint-config-standard 40.0:
  - The CSS system colours (`Canvas`, `ButtonText`, `Highlight`…) are allowed only inside
    `@media (forced-colors: active)`, in any case; a new rule,
    `design/system-colors-in-forced-colors`, refuses them anywhere else, shorthands
    included.
  - `100svb`, `100svh` and `100dvb` are allowed for `min-block-size`.
  - `import-notation` is off. The references spell imports both ways, and the
    standard config's `url()` notation refused the documented Tailwind entry.
  - The single-line-declarations rule is off: formatting is Prettier's job, as the
    config already said.
  - The file-class overrides are still the documented four. A fifth, for layout
    primitives, was tried and removed: placed after the component block, it took Law 2
    from any component in a `layout/` folder, and its regex hung on a long number.
- The starter:
  - It marks its documented one-offs with a `stylelint-disable` comment and a reason: the
    `[hidden]` override, iOS text-size-adjust, the second `html` rule, the sub/sup
    ratio, the focus ring's gap, the two repeated `:root` blocks in tokens.css, and in
    layout.css the switcher's quantity queries and the file's `> *` child rules.
  - layout.css derives its three computed boxes through sockets, as it already did
    elsewhere, and `.imposter--bottom` uses the `inset-block` shorthand. Nothing renders
    differently.
- The ESLint config's Part 5:
  - The v3 block anchors its config path at the project.
  - Both blocks whitelist the starter's own classes; the v3 block no longer whitelists
    the utilities the plugin already learns from the config, which hid their typos.
  - Both blocks and the header give `p-card p-card-lg` as the contradiction.
    `p-card px-inline-md` is not one: the longhand always follows the shorthand, in
    v4 and in v3.
- The 3.0.1 entry below named a report by a path on the maintainer's machine.
- The README states the floors: Python 3.10 or newer (the suite runs on 3.10 to 3.14),
  and Node 20.19+, 22.13+ or 24+ for the lint configs.
- The rule spec, `design-rules.json`, records the system-colour rule, and that a
  component in a `layout/` folder is a component.

### Tests

- `test_real_tools` runs stylelint over the starter, the documented entries and fixtures
  for each law and for everything the review found. It runs both Part 5 blocks through
  the real plugin (4.4 with Tailwind 4.3, 3.18 with Tailwind 3.4) from the folder above
  the project, over role classes, the starter's own classes and typos of both; the
  contradiction fixtures are the examples the blocks' own comments give.
- `test_docs` checks that no shipped file names a folder on the author's machine
  (including as JSON escapes it and WSL paths), that the README states the Python
  floor, and that every script compiles, and every shipped script's `--help` runs, on
  the floor interpreter itself (`WDS_FLOOR_PYTHON`, else uv's).
- Inside the plugin's repository, `npm ci` in `tooling/main` and `tooling/tailwind-v3`
  installs every tool the tests use but the browser, at pinned versions, and the tests
  find them without any variable set; `off` switches a group of tests off.
- Every subprocess the tests start gets the harness's environment, without the variables
  that tie git to one repository (`GIT_DIR`, `GIT_INDEX_FILE` and the rest), and a test
  holds every call to it. Run from a git hook, the hook tests staged their fixtures into
  the hook's repository.

## 3.2.0 — 2026-09-25

Phase 2 of the 3.0.1 review: the docs are tied to the code. Tests now read the
commands, configs, code blocks, figures and pointers out of the docs and check them
against the scripts, a real browser and the real tools, and the fixes followed from
what they found. Every fix has a regression test that fails on 3.1.0 and passes here
(`python -m unittest discover -s tests`: 296 tests).

### Upgrading

- **The pre-commit hook fails when a stage cannot run.** A missing stylelint config,
  audit script or Python used to print SKIPPED and let the commit through. Set
  `DESIGN_GATE_ALLOW_SKIP=1` while a stage is being adopted. Configs are now found at
  the repo root first (`stylelint.config.*`, `.stylelintrc*`, a `stylelint` object in
  package.json), then in `assets/configs/`.
- **Install the hook twice**, as `pre-commit` and as `commit-msg`: a bypass
  (`DESIGN_GATE_BYPASS=1 DESIGN_GATE_BYPASS_REASON="why"`) now leaves a
  `Design-Gate-Bypass:` trailer in the commit as well as a line in the log.
- **Re-baseline the design audit.** It now reads class strings inside `cn()`, `clsx()`,
  `cva()` and the other class helpers, refuses every Tailwind arbitrary value except
  arbitrary variants, image URLs and pseudo-element content, flags arbitrary properties
  (`[padding:13px]`) and the v4 `!` suffix, and audits styled-components and emotion
  template bodies as CSS.
- **Renames and moves.** Tailwind's width utility `border-default` is now
  `border-stroke` (it also painted the border colour). `.prose` moved from base.css to
  layout.css. The navigation code moved from `navigation-patterns.md` §6 to
  `navigation-code.md`.
- **New roles** in all 14 contracts, the starter, both Tailwind configs, the migration
  template, the Figma importer and the email map: `--motion-instant` (press, toggle,
  check) and `--bg-scrim`. Components may read `--weight-*` directly.
- **design-system-docs.** The drift baseline is `docs/system.json`, extracted from
  `styles/ src/components/` in every step. `build_docs --check --baseline FILE` exits 2
  when FILE does not exist; it used to check prose only and pass.
- **Versions.** stylelint `^17` with stylelint-config-standard `^40`; ESLint `^10` with
  a package.json `overrides` entry for eslint-plugin-jsx-a11y; eslint-plugin-tailwindcss
  4.x for Tailwind v4 (`cssConfigPath`), pinned to 3.x on v3. CI actions on their
  Node 24 majors (checkout@v5, setup-node@v5, setup-python@v6, cache@v5,
  upload-artifact@v6).

### Tests on the gap between docs and code

- Every CSS, TSX and JSX block in the references passes the audit; deliberate bad
  examples say so with `example: wrong | before | illustration`.
- Quoted starter code is kept identical to its region in the starter
  (`tools/sync_snippets.py --check`).
- Every "Verified n:1" is recomputed and every `clamp()` anchor solved.
- Every documented flag is one the script's own parser accepts.
- Every § pointer resolves, and each cross-file pointer lands on the heading it was
  checked against (`tools/check_pointers.py`, 300 registered).
- Real tools where they are installed: ESLint (on 9 and 10), a Tailwind v4 compile of
  theme.css, tailwind-merge with the documented config, and Chromium for the focus-ring
  caveat, the navigation code, container queries, subgrid, layer order and more.
- `check_roles.py` checks role pairs in light, dark, `.inverse` and dark `.inverse`, as
  an opt-in hook stage, and generates color-system.md §6.
- One rule spec, `assets/rules/design-rules.json`, that the audit, the stylelint config
  and the docs are tested against.

### Recipes that run as written

- The drift gate: one baseline, one set of inputs.
- Performance budgets are JSONC, and `measure_vitals` reads the budget before it starts
  a browser.
- The CI workflows: `shell: bash`, the server waited for in the step that uses it, the
  lockfile's Chromium installed and cached, nothing installed ad hoc, a readable report
  in the log (`--report FILE`, new in `measure_vitals` and `a11y_runtime`), and a PR
  comment with its number, token and permission.
- Navigation code: the safe triangle holds, a click keeps a hovered panel open, the
  drawer's light dismiss ignores its own padding, and `--nav-offset` is registered as a
  `<length>`.
- The `@property` recipe uses a px initial value and a socket only the root reads.

### Docs that are true

- The accessibility skill's runtime promises (keys, reduced motion, budget keys, 200%
  zoom as a warning), its coverage figures (a tool fully decides 7 of the 55 A and AA
  criteria and part of 31 more), and "Not Evaluated" for AAA only.
- Container queries, subgrid, SC levels, legal baselines (EU EN 301 549 v3.2.1, ADA
  Title II WCAG 2.1 AA, Section 508), colour-science numbers, email-client support per
  caniemail, Gmail's style ceiling (and the build now splits retained CSS over it),
  classic Outlook's support dates, Figma plans and styles, Bootstrap's !important
  utilities, MUI native colour, and the README's standalone claim.
- An evidence register, `tests/fixtures/evidence.json`: each quoted figure with its
  source, date checked and the source's own words. Baymard's checkout figures were
  corrected on the way.

### Leaner skills

- Every SKILL.md fits in what Claude Code keeps after compaction (about 5,000 tokens);
  large sections moved verbatim into references. Landing-page-conversion's ethics and
  evidence rules come first.
- Descriptions are 301–368 characters, lead with a sentence that stands alone, and say
  what each skill is not for.

### Not verified by execution

stylelint 17 and eslint-plugin-tailwindcss 4.x are not installed here, so their config
text is checked against the registry and their READMEs, not run.

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

38 bug fixes and the first regression suite (72 tests). The report is
`dev plans/web-design-suite-bugfix-report.md` in the project repository.
