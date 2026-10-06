# Changelog

## 3.4.0 — unreleased

### Added

- **The focus ring is measured at every density** (SB-B3). On a page, a11y_runtime
  measures the ring again at each `data-density` value the page's own stylesheets name,
  in normal colours and under forced colours, since the density dial rescales the
  padding that keeps a ring clear of an `overflow: hidden` toolbar. It turns the dial
  where the page keeps it: on the root, or on the outermost `data-density` below it, such
  as `<body>`; a region marked inside another keeps its own. A finding names its
  density; `--densities LIST` names them by hand, and `none` turns it off. web-design-
  studio's Phase 5 runs it on the built page, and review-checklist 8.2 and 8.9 say what
  it measures and what is still by eye.

- **Custom states and combinations in the matrix** (GT-A13). A component declares a state
  of its own (selected, readonly, current, open) in `custom_states`, by the attributes
  that put a cell in it, and joins two with `+` (`"selected+hover"`). Only the seven
  were allowed, so state-coverage.md's own procedure for adding a state, its
  per-archetype rows and its "selected + hover" row could not be rendered.
- **Right-to-left fixtures, and a forced-colours pass** (GT-B7). A content fixture may be
  `{"html": "…", "dir": "rtl", "lang": "ar"}`: the direction and language go on the
  cell's stage, so the whole component mirrors. Fixtures were inner HTML only, so the RTL
  fixture state-coverage.md asks for could not be rendered. `snapshot_matrix.mjs
  --forced-colors` shoots every cell under `forced-colors: active`, with its own baselines
  and report in `forced-colors/` folders, and fails a focus-visible cell that computes the
  same style as its default cell there: a ring drawn with `box-shadow` vanishes under
  forced colours. state-coverage.md says which interaction states an attribute renders
  (open menus, `<details>`, tooltips on hover or focus) and which need an interaction
  test (a native select's list, the top layer, `:user-invalid`).
- **Baselines recorded where the gate runs, and Git LFS past the line** (GT-B8). The
  workflow recorded baselines on the developer's machine, whose fonts never match a Linux
  runner's. visual-regression.md §7 adds a `workflow_dispatch` job that records them in
  the gate's runner and uploads them, and the gate's LFS checkout with a cache. §6 starts
  the baselines in Git LFS past about 2,000, which the pruned sheet reaches at 19
  components, or 10 with the forced-colours pass; `generate_matrix.py` prints the count
  once a sheet passes 1,000 cells. GitHub's LFS quota and size advice are registered in
  `evidence.json`.
- **`--interact-at MS`: an interaction during hydration** (GT-C11). measure_vitals'
  `--interact` clicks once the page has settled, the one moment hydration cannot delay,
  though diagnosis.md §8 names hydration as the biggest INP source. `--interact-at MS`
  clicks MS after navigation starts, by the page's own clock, through the browser's input
  pipeline, so the click queues behind the task that holds the main thread, as a user's
  does.
- **`crux_check.py`: the field against the lab** (GT-B5, GT-C11). perf-budget-gate's
  trigger for re-deriving a profile, a field p75 more than 1.5× the lab median, had no
  tool behind it. `crux_check.py` reads the p75 for an origin or a URL from the Chrome UX
  Report API and holds it against the median in a `measure_vitals.mjs --report` file:
  LCP, CLS, FCP, TTFB, and INP when the lab drove one. It exits 1 above the ratio and 2
  when CrUX holds no data. The key comes from `CRUX_API_KEY`, never an argument: `--key`
  is refused without echoing it, and the key is never printed. `--response FILE` reads a
  saved response.
- **system.json records the layer order** (LC-C5). `extract_system.py` writes each
  `@layer a, b, c;` statement it reads to a new `layers` list, from the entry stylesheet
  as well as the token files; the schema stays `design-system-docs/system/1`, since the
  key is additive. `diff_system.py` compares two snapshots' orders, where it could compare
  only two CSS inputs before, and says so when a snapshot predates 3.4.0.

### Fixed

- **TTFB never saw the emulated latency, and no preset was Lighthouse's** (GT-A6). CDP
  adds its latency once per request, and Navigation Timing's `responseStart` comes before
  it: `--throttle slow4g` reported a TTFB of 5 ms, which also skewed the LCP sub-parts.
  TTFB is now the network stack's (`receiveHeadersEnd` from CDP). A `lighthouse` preset
  applies what Lighthouse's own DevTools throttling does: 562.5 ms per request (150 ms ×
  3.75), 1.44 Mbps down, 675 Kbps up, 4× CPU. The comment that called `slow4g`
  "Lighthouse's mobile defaults" is gone; its 150 ms per request is a lighter load.
- **`--interact` counted the click's own work in TBT, and TBT had no TTI bound** (GT-A17).
  On the review's slow page, a click took TBT from 0 to 107 ms with INP at 168 ms, the
  same work counted twice. A long task that starts after an input and runs into its handlers is now left
  out; the task the input waited behind stays, since it is the page's. TBT also ends at
  TTI, the end of the last long task before five quiet seconds (no long task, two
  requests in flight at most), when such a window fits in the run.
- **A loading spinner counted as a focus ring** (GT-A14 (a)). a11y_runtime shortened
  animations before measuring the ring but did not pause them, so a spinner inside a
  button with `outline: none` kept turning between the two screenshots, and the button
  passed. It now uses the matrix's freeze, which pauses them.
- **a11y_runtime reads a JSONC budget or keymap**, with comments and trailing commas, as
  measure_vitals and perf_audit already did.
- **A page with a strict Content-Security-Policy crashed the run** (GT-A5). Under
  `default-src 'self'` the page refused the freeze stylesheet that a11y_runtime and
  snapshot_matrix inject, and the error left as exit 1, which means violations. Their
  contexts now bypass the page's CSP, and a run of any of the three browser scripts that
  fails exits 2: a crash is never a finding, a regression or a breach. measure_vitals
  keeps the page's CSP: it injects only an init script, which CSP does not govern, and a
  bypass would run what the CSP blocks, so it would measure a page no user gets.
- **Disabled controls were held to contrast** (GT-A14 (b)). SC 1.4.3 exempts the text of
  an inactive component, and axe skips it; a11y_runtime reported `<button disabled>` as
  `contrast-too-low`. It now skips a disabled control or fieldset and what it holds,
  anything inside `aria-disabled="true"`, and the label of a disabled control. What sits
  in the first legend of a disabled fieldset is still measured, since HTML leaves it
  enabled, and so is a control that only looks disabled. With GT-A5, this finishes GT-C2: 3.1.0
  did the colours, modals, iframes and inert content, and P9 the pausing.
- **A page with one tab stop was a keyboard trap in Chrome.** Chrome (not the headless
  shell) wraps Tab from the last stop to the first inside the page, so on a page with one
  stop, focus stayed put, and a11y_runtime reported `focus-stuck` (2.1.2) as an error.
  There, focus that stays put is a trap only if the page cancelled the key.
- **`--only` on a page was ignored.** It narrows a proof sheet's cells and never picked
  checks, so `a11y_runtime.mjs --file page.html --only contrast` ran every check. A page
  now refuses it, with exit 2 and a pointer to `--skip`.

- **The axe tag advice dropped WCAG 2.1, and best practice failed the run** (GT-A8). The
  docs recommended `--tags wcag2a,wcag2aa,wcag22aa`, which leaves out every 2.1 rule: in
  axe 4.13, `autocomplete-valid` (1.3.5) and `avoid-inline-spacing` (1.4.12), and two
  experimental ones. Every example now keeps `wcag21a,wcag21aa`. And the default set's
  best-practice rules (`tabindex`, `aria-dialog-name` and others axe rates serious)
  failed the run as errors, though they name no success criterion: a11y_runtime now
  reports them as warnings, labelled best practice, and no budget counts them. The report wording names the 2.0,
  2.1 and 2.2 A and AA rules.
- **a11y_static's outline and landmark checks are best practice** (GT-A18).
  `multiple-h1`, `heading-skip` and `no-main-landmark` were errors under 1.3.1, 2.4.6
  and 2.4.1; axe tags the same checks best-practice only. They are warnings now, labelled
  best practice; `--strict` still fails on them.
- **Two rows of perf-budget-gate's "same method" table did not follow the method**
  (GT-A16). Fast 4G gives 1.9 MB of critical path, not 1.5 (total 4.6 MB), and 3G
  12.5 KB, not 40 (total 30 KB); desktop cable is 1.1 MB, not 1.2. The table states its
  method and the Slow 4G profile, and budgets.md no longer says the 800 ms TTFB matches
  web.dev's 0.8 s "not by coincidence": web.dev calls that threshold a rough guide. With
  GT-A8, this finishes GT-C5's correction pass.

- **A `:focus` ring never rendered in the matrix** (GT-A12). Rules written with `:focus`
  or `:focus-within` were mirrored to their own `data-force-state` token, but the
  focus-visible cell carried `focus-visible` alone, so the ring never showed, the
  coverage line called the state covered, and a11y_runtime reported a ring users do see
  as missing. The cell now carries all three tokens.
- **The matrix's error state stamped `aria-invalid` on buttons and spans** (GT-A13).
  ARIA 1.2 deprecated it as a global attribute; an input, select or textarea gets it, and
  everything gets `data-state="error"`. Whether the cell is a form control is now read
  from the element that carries `{attrs}`, not the whole template, so a `<div>` wrapping
  an `<input>` no longer gets `disabled` or `aria-invalid`. With GT-A12 and GT-A13, this
  finishes GT-C3.
- **The audit dropped its JS colour check for a whole project in a folder named `test`.**
  It leaves test, story, mock and fixture files to the test tools, but matched the words
  anywhere in the absolute path, so a project inside a folder named `test` or `fixtures`, or a
  temporary `wds-test-*` folder, lost `js-raw-color` for every file. It reads the path below
  the folder being audited now, and plurals and `__mocks__` count, which they never did.
- **diff_system missed density, media-condition and root-element changes** (LC-A8).
  change-classification.md calls all three major and detected, and system.json records
  them, but the diff compared none: a release that changed only `--density` at compact,
  the reduced-motion duration and `<div>` to `<section>` was a patch "because nothing
  changed". They are `density-changed` (with the roles each moves, `--pad-card 21px ->
  19.2px`), `condition-changed` and `element-changed`, all major, and a density added or
  removed is minor or major, as a theme is. A re-point that resolves the same in the
  default theme but not in another theme or at a density was a patch; it is major.
- **An added theme override was minor** (LC-A9). It moves the role in that theme, which
  change-classification.md §11 calls major (Q2): a new dark `--fg-muted` that crossed 3:1
  downward recommended a minor bump. It is major now, and a patch when it resolves as
  before.
- **A class renamed under CSS Modules was a removed part** (LC-A9). The rendered class is
  hashed, so the doc calls the rename a patch, but the diff reported `part-removed`, major,
  and failed the gate. In a `.module.css` file, a part that went and one that came with the
  same declarations are `part-renamed-local`, a patch; in global CSS they stay major.
  change-classification.md §11 now says what an added part is: new surface (Q4), unless it
  wraps existing children (Q3).
- **A negative cancel pointed at a different token from its padding** (LC-A11). In the
  reference's own example, `.card { padding: 16px }` became `var(--pad-well)` while
  `.card__media { margin: -16px }` became `calc(var(--gap-grouped) * -1)`, since 16px in a
  margin clusters to a gap: the bleed breaks the day the padding changes. apply_codemod
  pairs each negative margin with the padding of its parent rule (the rule it is nested
  in, the left side of a descendant or child selector, or a BEM element's block) and
  reads that padding's token, when that padding is set in one block of the file; set in
  two (another `@media`, an `@layer`, the rule written twice), which one applies is not
  certain, and the margin keeps its gap token. extraction-and-clustering.md's example
  named `--pad-card`, 24px, for the 16px padding.
- **A type tie snapped down when the smaller size was commoner** (LC-A12). The docs promise
  "15px becomes 16, text does not shrink", but frequency settled the tie first, so with
  14px commoner 15px became `--type-ui`, with a note saying "snapped UP to 14px" and a
  delta of -1. Type ties now always snap up, and the note follows the real direction.
- **The audit and extract_system disagreed about Law 6** (LC-A19). extraction.md says the
  two agree by construction, but each kept its own lists: in a `.module.css` file the
  audit refused `var(--space-0)` and `var(--shadow-none)`, which extract_system exempts as
  null-outs, and extract_system flagged `--weight-*`, which the audit allows. The lists
  are now the rule spec's `tiers` section (prefixes with a role, the role exceptions, the
  null-outs), written into both by `tools/sync_rules.py`; the audit exempts the null-outs.
- **A colour rename beside a `font-weight` was refused** (LC-A14). apply_codemod's font
  guard, which stops a `font-size` rewrite into the `font` shorthand from resetting the
  weight beside it, refused every declaration-scope rewrite in such a rule: deprecate.py's
  `color: var(--fg-subtle)` to `--fg-faint` beside `font-weight: 600` came back as "`font:
  var(--fg-faint)` would reset font-weight". The guard applies only to a rewrite into
  `font:` from another property now.
- **deprecate.py's scan labelled a one-line rule `manual`** (LC-A14). It read a line as one
  declaration, so `.meta { color: var(--fg-subtle); }` was "not a plain declaration" and the
  review's client read "0 codemod · 9 manual" where the codemod rewrites 7; the same rules
  on several lines were labelled right. It reads each declaration on a line, and no longer
  predicts the font-guard skip, which a colour rename never meets.
- **A re-point listed every density and condition** when its default value moved, a side
  effect of P14's equality check, which needs them only when the default does not move.
- **figma_audit split a records export's modes** (LC-C3). A flat export lists one row per
  variable and mode. figma_to_tokens merged the rows into one variable with a value per
  mode; the audit's copy of the reader made each row a variable of its own, in a
  collection whose default mode, `Value`, no variable had. Both scripts now read through
  one module (Changed, below), so the audit merges them too. And a flat plugin export,
  whose `valuesByMode` is keyed by mode id while its modes are listed by name, kept the
  ids: in both scripts, a `Dark` mode came out as a theme named `1:1`. Both are read
  as the mode's name now.
- **`--reverse` wrote a body Figma would not take as written** (LC-A22). It carried a
  `_comment` key, though the body's own comment said Figma rejects unknown top-level keys,
  and SKILL.md never said to strip it. It never named a collection's first mode, which
  Figma creates under its own name; Figma's REST example names it with an `UPDATE` on the
  temporary id, which `--reverse` now sends (`Value`, or `Light` unless a theme has that
  name, then `Default` or `Base`, so two modes never share a name or a temporary id).
  And primitives were scoped to the pickers (`ALL_FILLS`, `GAP`), inviting a designer to
  bind Tier 1, the Law 6 failure: they get `scopes: []` now. Every duration was dropped
  too, `--dur-base: 220ms` having no pixel value, with exit 1: a duration crosses as
  milliseconds now, 220.
- **The model announcement shipped a breaking change as a minor** (LC-A17). rollout.md's
  example read "Design system 2.1.0. One breaking change: `--bg-accent` moved", a re-point
  released as a minor, the failure the skill exists to prevent. It is 3.0.0 now, with
  `UPGRADE-3.0.0.md`, and so is the upgrade procedure, whose step 3 committed the codemod
  on its own (`git commit -am`) against §6's one-commit rollback: the upgrade is one
  commit now, after step 6.
- **deprecate.py took a removal outside a major** (LC-A23). deprecation.md puts a removal
  in X+1.0.0, but `--since 2.1.0 --removal 2.2.0` was accepted; only a patch-apart window
  was refused. A removal that is not a later major is refused now, unless `--force`.
- **The reconciliation report's smaller errors** (LC-A23). A duration's delta printed as
  "-30px"; it is in milliseconds, and a colour's row shows its ΔE, not "+0px", under a
  heading that no longer says "more than 2px". A
  colour held in a `$`-variable was to be re-pointed (`$brand: var(--fg-default)`), where
  framework-migrations.md says to delete such variables at their call sites. The report
  says so now for a `$` or `@` variable; a custom property is pointed at a role (a Tier-3
  socket), and a colour in a property with no role, such as `scrollbar-color`, is
  replaced in place. One colour in two holders gets an entry for each, by kind of holder
  and, for plain properties, by property.
- **The lifecycle docs' smaller errors** (LC-A23, LC-B8). deprecation.md said `tsc`
  surfaces `@deprecated`; it does not, and the gate is `@typescript-eslint/no-deprecated`.
  framework-migrations.md said the script reports a `darken()` call's distance to the
  ramp; it cannot compile Sass, so it lists the calls. MIGRATION_PLAN.md offered "20px
  `--pad-inline-sm`", which is 12px; migration SKILL.md said "four" algorithms and listed
  six; and figma-variables-sync called `tokens.css` "`git`-enforced read-only", where the
  CI drift check is what refuses a hand edit.
- **`--interact-at` times the click on the page's clock.** It waited until
  `Date.now()` reached `performance.timeOrigin` plus MS, comparing Node's wall clock with
  the browser's. It now maps the page's `performance.now()` onto Node's monotonic clock
  as NTP does, from the narrowest of three round trips, so a stalled request or reply
  costs at most half that trip (Codex and CodeRabbit on #56), and `clickedAt` is page time.
- **Email dark mode no longer breaks the call to action** (DL-A10). The dark block's
  `a { color: var(--email-dark-link) !important }` beat the button's inline white label:
  #ffa582 on the #c64600 fill, 2.56:1, wherever `prefers-color-scheme` is honoured. Each
  template's dark block now ends with `.button { color: var(--fg-on-accent) !important }`,
  the announcement's call to action has `class="button"`, and its "Back in stock" eyebrow,
  left at the light accent on the dark surface (2.50:1), is re-pointed to the dark link
  colour.
- **`lint_email` measures dark mode** (DL-B6, DL-C3). A new `dark` check applies the
  retained `prefers-color-scheme: dark` rules with build_email's own selector matcher and
  cascade (one source order across `<style>` blocks), as a client that honours them renders
  the email, and measures the text whose colour or background they change, inherited
  colours included. It found both of DL-A10's failures, at the review's figures.
- **The Outlook font rule is in the build** (DL-A11). email-architecture.md §2 said the
  compiler adds an `[if mso]` block that gives the Word engine Arial, without which a stack
  starting with `-apple-system` lands on its default serif; the block never had it. It
  does now, a hand-written PixelsPerInch block gets the font rule beside it, and the lint
  warns when no broad `[if mso]` font rule (on `*`, `body`, `table` or `td`) is in the head and a stack starts with a family Windows
  lacks.
- **The receipt is fluid** (DL-A12). Its container was `width:600px` inline, so with
  `<style>` stripped (Gmail's app with a non-Google account) it was 600px wide on a 375px
  phone. It is `width:100%` with the 600px cap, like the other two templates.
- **Authoring notes stay out of the email** (DL-A20). The build kept any comment holding
  `{{` as an ESP directive, so the receipt's header comment shipped in every build while
  the build reported it dropped. A comment is kept for real ESP syntax only: a Handlebars
  block (`{{#`, `{{/`, `{{^`, `{{else`), a Liquid tag (`{%`), a Mailchimp merge tag
  (`*|IF:X|*`), ERB (`<%`), and conditional comments as before.

### Changed

- **measure_vitals' default throttle is `lighthouse`** (GT-A6). budgets.md derives every
  budget from Lighthouse's Slow 4G profile, and the old default, `slow4g`, applied a
  quarter of its latency. Lab numbers rise with the upgrade: pass `--throttle slow4g` to
  compare with numbers from 3.3.0, then re-baseline on `lighthouse`.
- **One copy of the browser scripts' shared helpers** (GT-C13). a11y_runtime,
  snapshot_matrix and measure_vitals each carried their own browser resolution, freeze
  CSS and JSON reader, and the copies had drifted. They now import
  `scripts/browser_common.mjs`, a byte-identical copy of `shared/browser_common.mjs` in
  each of the three skills, so each skill still runs on its own.
- **The two worked examples are the tools' own output** (LC-C12). design-token-migration's
  worked run (references/worked-run.md) and design-system-versioning's worked release
  (SKILL.md) quoted numbers from fixtures that never shipped. They are now
  `tests/fixtures/worked-run`, eight files, and `tests/fixtures/worked-release.json`, five
  edits to the starter's tokens.css, and both pages quote what the tools print for them
  today: 120 literals in 7 files (the vendor sheet is excluded), 68 rules, 91 replacements,
  119 audit errors before and 37 after; a 3-major, 1-minor, 1-patch release whose re-point
  crosses 4.5:1 (4.92 to 3.56). The worked release said "four edits" and listed five.
- **Release builds compare by content** (N34). `tooling/release/compare.py` compares two
  build folders entry by entry: names, and each entry's bytes (read, hashed and checked
  against its CRC), size, date and mode. A build
  is byte-identical to another only with the same zlib: Windows' Python 3.14 uses
  zlib-ng, the CI's zlib, so 3.3.0's release matched no local build's checksums.
- **One reader for both Figma scripts** (LC-C3). figma_to_tokens and figma_audit each
  carried a copy of the same reader (the shape detector, the four parsers, the value and
  colour helpers and the document model), and the docs said they shared it. It is
  `scripts/figma_common.py` now, beside `dtcg_values.py`, taking the better of the two
  copies where they had drifted; each script lost about 400 lines.

### Tests

- The hydration-click flake: `test_browser_runtime.VitalsMeasures.test_interact_at_clicks_while_the_page_hydrates`
  found no interaction entry on Windows CI twice (#49's first run, #54's merge to `main`),
  and failed with a `TypeError`. Its page started the 3-second task 1.5 s after its script
  parsed, while the click is due 2.5 s after navigation starts, so a late parse put the
  click before the task. The task is now due at 1.5 s on the page's clock, and a missing
  entry fails with the run's numbers. It never failed locally (5 runs before the fix, 4
  after), so there is no fail-before count; the test change is a control.
  `test_browser_scripts.VitalsTiming.test_the_page_clock_survives_a_stalled_request_or_reply`
  runs the clock mapping on fake clocks with stalls; it fails on the PR's first head.
- P18 part 1 (DL-A10, DL-A11, DL-A12, DL-A20): `test_email`, a new module.
  `TemplatesInDarkMode` builds and lints each template and checks every filled link is a
  `.button` the dark block re-points; `LintHasADarkPass` holds the `dark` check to the
  review's 2.56:1 and 2.50:1 and leaves untouched pairs to `contrast`; `OutlookFontRule`,
  `ContainersAreFluid` and `AuthoringCommentsAreDropped` hold the rest. Against `v3.3.0`,
  10 fail. Four are controls: the templates linted clean before (the lint had no dark
  pass), a class rule that wins back the label, a page with no dark block, and a pair the
  dark rules leave alone.
  Codex's review of #57 added four, each failing on its head: text that inherits its colour
  onto a background a dark rule changes, a later `<style>` block winning a tie, a VML
  button's or a component's `[if mso]` font standing in for the scaffold in the lint, and
  a component's override stopping the build from adding it.
- P17 (LC-A17, LC-A23, LC-B8, LC-C6): `test_versioning.DeprecateKeepsRemovalsInAMajor`
  refuses `--removal` 2.2.0, 2.1.1 and 3.1.0 for `--since 2.1.0` and takes 3.0.0 and 4.0.0;
  `test_token_migration.MigrationPipeline` checks the report's millisecond delta and its
  advice for a held colour; `test_figma_sync.DeterministicOutput` runs the drift check on a
  generated `tokens.css` and on a hand edit. Against `v3.3.0`, 3 fail. Two are controls: a
  removal in a later major was always taken, and the drift check already worked; it had no
  test behind the claim. Codex and CodeRabbit on #54 found two more, failing on its head:
  the delete advice reached plain properties (`scrollbar-color`), and durations sat under
  "more than 2px" (`test_the_review_table_names_its_units`). Its next review found two
  more, failing on `79bd76b`: a colour's review row read "+0px", and one colour held by a
  `$` variable and a custom property got the first holder's advice for both
  (`test_one_colour_in_two_kinds_of_holder_gets_both_kinds_of_advice`); and on `090ded4`,
  two plain properties holding one colour were named as the first.
  `test_token_migration.LifecycleDocClaims` holds the doc fixes: a breaking announcement
  names a major and its guide, and the upgrade commits once; the algorithm count matches
  its table; MIGRATION_PLAN's tokens are the sizes it gives them; and deprecation.md names
  the lint rule, not `tsc`, as the gate for `@deprecated`. Against `v3.3.0`, all 4 fail.
- P16 (LC-C3, LC-A22): `test_figma_sync.FigmaCommon` reads a REST export (one with a
  variable whose collection is missing), a plugin export, a two-mode records export and a
  DTCG file through both scripts and holds them to one result, and checks that neither
  script defines a name `figma_common.py` does, so the copies cannot come back.
  `test_figma_sync.ReverseBody` holds the `--reverse` body to the four arrays, an `UPDATE`
  naming each collection's first mode, distinct mode names beside a `light` theme, and no
  scopes on primitives. Against `v3.3.0`, all 6 fail. The reviews of #53 found two more,
  failing on its head (`559cce2`): a flat plugin export's values by mode id
  (`test_a_flat_plugin_export_reads_its_values_by_mode_name`), and a `default` theme
  beside a `light` one, which took the first mode's name and id
  (`test_the_first_mode_takes_a_name_no_theme_has`). Its next review found the dropped
  duration, failing on `v3.3.0` and on `260df86` (`test_a_duration_crosses_as_milliseconds`).
- The test-file exemption: `test_audit_design.TestFilesByThePathBelowTheRoot` audits one JSX
  colour under `neutral/` and under `fixtures/test/`, and a `.test.jsx` and a `__mocks__` file as
  the control. Against `v3.3.0`, 1 fails; the control passes there only because this test's
  own `wds-test-*` folder exempted everything.
- P9 (GT-C13, GT-A14 (a), N34): `test_browser_scripts.SharedHelpers` holds the three
  copies to the master, keeps the moved helpers out of the scripts, and holds both
  freezes to pausing; `test_browser_runtime.test_a_spinner_is_not_a_focus_ring` runs
  the spinner in a real browser. Against `v3.3.0`, all 4 fail.
  `test_release_build` adds two: builds stored instead of deflated compare the same,
  and a changed or missing file is a difference. Codex's review of #38 added a third: a
  payload damaged under an intact directory passed, since only the recorded CRCs were
  compared (the old tool reports such a pair the same). CodeRabbit's added a fourth: an
  entry damaged alike in both builds read as the same error on both sides, so two
  damaged builds compared the same; an unreadable entry is now always a difference.
- P10 part 1 (GT-A5, GT-A14 (b)): `test_browser_scripts` runs the three scripts against
  a stub browser that records each context's options and then fails, and holds every
  `newContext(` call in their source to the bypass where the script injects;
  `test_browser_runtime` audits a page and captures a sheet under `default-src 'self'`,
  and checks disabled controls against a lookalike that is not. Against `v3.3.0`, all 5
  fail. The reviews of #39 added three, each failing on its first head:
  - CI found the Chrome wrap: `test_a_page_with_one_tab_stop_is_not_a_trap` runs a
    one-button page in the default browser and in an installed Chrome or Edge, with a
    page that cancels Tab as the guard (it fails against `v3.3.0` too).
  - Codex found the first-legend exception, now in the disabled-controls test.
  - CodeRabbit found that a bypass in measure_vitals would run a script the CSP blocks:
    `VitalsUnderCsp` measures such a script's layout shift as none.
- P10 part 2 (SB-B3): `test_browser_runtime.test_the_focus_ring_is_measured_at_each_density_the_page_declares`
  runs a toolbar whose ring is clipped at compact and is a box-shadow at spacious, then
  again with `--densities none`; `test_browser_scripts.RuntimeArguments` refuses `--only`
  on a page and a bad `--densities`. Against `v3.3.0`, 2 fail; the `--densities` test is
  a control, since 3.3.0 refused the unknown option. The runtime tests that passed
  `--only CHECK` to a page now leave the other checks out with `--skip`. Codex's review
  of #40 found the dial set on the root alone, which a `<body data-density>` masks: the
  density test runs both, and fails on the PR's first head. CodeRabbit's found that two
  top regions at different densities skipped one value: a third case, failing on the head
  before it. `VitalsUnderCsp`'s control
  page now shifts after its first paint, since a shift before it is not counted (it
  failed on a slow macOS runner).
- P11 (GT-A8, GT-A16, GT-A18): `test_facts.AxeTagAdvice` holds every `--tags` list that
  names `wcag2a` to naming `wcag21a` and `wcag21aa`, and reads the pinned axe-core's tags
  for the rules the docs name; `test_browser_runtime.test_a_best_practice_rule_is_a_warning`
  runs `tabindex` beside `image-alt`; `test_content_and_a11y.StaticBestPractice` and
  `test_numbers.ByteBudgets` recompute the rest. Against `v3.3.0`, all 6 fail. The
  web.dev quote is registered in `evidence.json`. Codex's review of #41 found the `axe_violations`
  budget still counting best-practice warnings, so a budget of 0 failed on one:
  `test_a_best_practice_finding_does_not_breach_a_violation_budget` fails on its head.
- P12 part 1 (GT-A12, GT-A13): `test_content_and_a11y.MatrixStates` generates a sheet
  with a `:focus` ring, a custom state and a combination, an undeclared state, and the
  error state on a span and an input. Against `v3.3.0`, all 4 fail. Codex's review of #42
  added three, each failing on its first head: a wrapper and a button keep `aria-invalid`
  and `disabled` off where they do not belong, `loading+error` (both set `data-state`) is
  refused, and the coverage grid has a column per state. CodeRabbit's added three, failing on
  the head before them: a quoted `<` before `{attrs}`, a conflict judged on the element
  that renders it (`error+valid` on an input, not a span), and `form_control: true`
  keeping `aria-invalid` off a `<div>`.
- P12 part 2 (GT-B7, GT-B8): `test_content_and_a11y.MatrixModel` renders an RTL fixture,
  refuses a bad `dir`, `lang` or key, and reads the LFS line in the summary;
  `test_browser_runtime.MatrixSeesStateChanges` runs a `box-shadow` focus ring and a
  `box-shadow` hover under forced colours (the ring fails, the hover does not, an outline
  ring passes) and keeps the forced-colours baselines apart. Against `v3.3.0`, all 5
  fail. Both browser tests pass in Playwright's Chromium and in an installed Chrome.
- P13 part 1 (GT-A6, GT-A17, GT-C11): `test_browser_runtime.VitalsMeasures` serves pages
  over HTTP and measures TTFB under `slow4g` and the default, a 250 ms click handler
  against TBT, a long task after five quiet seconds and one before, and a click during a
  2-second task with `--interact-at` (its wait is INP's, the task stays in TBT) and
  without it; `test_browser_scripts.RuntimeArguments` refuses `--interact-at` without a
  target or below 0. Against `v3.3.0`, all 5 fail. They pass in Playwright's Chromium and
  in an installed Chrome; a click timed from Node's clock missed the task in Chrome, whose
  cold start delays the request, so `--interact-at` counts from the page's time origin.
  Codex's review of #45 found two, each failing on its head: a request still in flight
  has no Resource Timing entry, so three hanging fetches looked like a quiet network and
  TTI came early (`test_requests_in_flight_keep_the_network_busy`; the requests now come
  from CDP); and the long-task totals dropped the click's task with TBT (they keep it).
  CodeRabbit's made the `--interact` control assert that the click happened, gave the TTI
  test a 9-second settle, and found CDP's unset `receiveHeadersEnd` (-1) added to TTFB:
  `test_browser_scripts.VitalsTiming` runs `networkTtfb()` on its own, and fails with the
  guard deleted.
- P13 part 2 (GT-B5, GT-C11): `test_crux_check` reads a response in the shape the CrUX API
  documents, from a file and from a local server standing in for the API, which records
  the query: the key in the query string and nowhere in the output, a ratio above and
  within, a refusal and no data (exit 2), and a key passed as an argument refused. They
  never touch the network. Against `v3.3.0`, all 5 fail (there was no script). Codex's
  review of #46 found a lab median of 0 left unjudged, so a field CLS of 0.05 against a
  lab CLS of 0 passed: `test_a_lab_median_of_zero_is_exceeded_by_any_field_value` fails
  on its head.
  CodeRabbit's found five, each failing on its head: a non-finite or boolean lab median,
  an invalid p75, a malformed `metrics` container (a traceback), `--ratio inf`, and a
  saved response for another page or device class were compared or crashed; and a plain
  `http://` `CRUX_API_URL` off this machine would carry the key in clear. They exit 2 now.
  Its second round found two more: a page's trailing slash was ignored, so a saved
  `/offers/` passed for `/offers`, and a list for `urlNormalizationDetails` crashed.
- P14 (LC-A8, LC-A9, LC-C5): `test_versioning` builds the review's `fx/ver` system (a
  token file, an entry stylesheet with the layer order, a CSS Modules card and its props),
  extracts each version with `extract_system.py` and diffs it: a density, a reduced-motion
  and a root-element change, the three together, a re-point that moves only at a density,
  densities added and removed, a dark override that crosses 3:1, a local class renamed
  under CSS Modules (with the gate binding), a layer reorder, a system.json from before
  3.4.0, and the vendored token parser. Against `v3.3.0`, 12 fail; 2 are controls (a dark
  override that resolves as before, and the same rename in global CSS). Codex's review of
  #48 found three more, each failing on its head: a re-point equal by default but not
  under reduced motion was a patch, a root that became a fragment went unreported, and a
  local rename that also changed a value was paired as a pure rename. system.json's parts
  now record their declarations (`declares`) so the pairing can compare values.
  CodeRabbit's found three more, each failing on its head: `declares` came from a part's
  first rule only; a component whose file exports its styles object had its keys paired
  as local (`exports_styles` now records it); and `element` was the first JSX root after
  the props interface, so a helper above the component lent it its `<span>`. The root is
  read from the component's own body now.
- P15 part 1 (LC-A11, LC-A12, LC-A19): `test_token_migration.MigrationPipeline` runs the
  review's `fx/mig2` card through extract, cluster and the codemod, with a child selector
  and a nested rule beside it, and a type tie against a commoner 14px;
  `test_rules_spec.TheTierListsAgree` runs the review's `fx/l6` card through the audit and
  extract_system and holds both to the spec's lists. Against `v3.3.0`, 4 fail. Two are
  controls: a negative margin with no padding to cancel keeps its gap token, and the spec's
  new `tiers` examples, which `fail_before.py` swaps out with the rest of the plugin.
  Codex's review of #49 found two more, failing on its head: a cancel matched the padding
  by size alone, so `margin-inline: -8px` read an 8px block padding's token, and a padding
  declared for `.a, .panel` was not `.panel`'s. The pairing keeps to the axis and splits
  selector lists. CodeRabbit's found three more, failing on that fix: the axis did not
  tell left from right, a later `padding-inline` did not replace `padding`, and a grouped
  margin selector found no parent. The pairing works by side, in cascade order, for each
  member of either list.
  Its next review found one more: a padding inside one `@media` decided a margin's cancel
  in another. Each declaration records its at-rule context, and a margin reads its own.
  The review after that found two more, failing on its head (`edf441f`): a print padding
  was read in print though a later base padding wins there, and a layered padding
  replaced an unlayered one that wins the cascade. Rather than model the cascade, the
  pairing now reads only a padding set in one block of the file; set in two, the margin
  keeps its gap token (`test_a_padding_set_in_two_blocks_is_not_cancelled`). The next
  found one more, failing on that fix (`1f141b5`): `!important` was read as a slot of the
  padding, in the extractor and the pairing alike, so `padding: 16px !important` was
  block padding only, and a later plain declaration beat it. It is one value now, and an
  `!important` one wins its block (`test_an_important_padding_is_one_value_and_wins_its_block`).
  Its review on `73e7e62` found two more. `padding-inline-start` was the left padding,
  which it is only left to right: an inline side is read both ways now, and pairs only
  when the two agree (`test_a_logical_side_pairs_only_when_both_directions_agree`, failing
  on that head). And the spec's `tiers` examples never ran through the audit, the gate
  their section names; `test_rules_spec` runs them now (a control: the audit already
  agreed).
- P15 part 2 (LC-A14, LC-C4, LC-C12): `test_versioning.DeprecateRewritesAndCountsAColourRename`
  runs the review's `fx/dep/client` rules through deprecate.py's mapping, the codemod and
  the scan, one rule per line and the same rules on several lines;
  `test_token_migration.TheWorkedRun` reruns worked-run.md against its fixture and
  `test_versioning.TheWorkedRelease` reruns the worked release, each holding every number
  the page quotes to the output. Against `v3.3.0`, all 4 fail.
  Codex's review of #50 found one more, failing on its head: a declaration-scope rewrite
  replaced through `!important` and dropped it, which the font guard had hidden beside a
  `font-weight`. The rewrite ends where the value does now. CodeRabbit's found two more in
  the scan, failing on `28d5b99`: an `!important` declaration, which the codemod rewrites,
  was labelled manual, and a token named inside a quoted `content` string was split at the
  string's `;` (or past an escaped `\"` in it, its next review found) and counted as a
  codemod hit
  (`test_the_scan_reads_important_and_quoted_text_as_the_codemod_does`).

## 3.3.0 — 2026-10-04

Phase 3 of the plan: safe defaults and one set of rules. The audit, stylelint and ESLint
read one spec, `design-rules.json`: a tool writes its data into each gate, and the three
agree on every example in it. CI runs the suite on Windows, Linux and macOS at Python
3.9 and 3.14, and a pushed tag builds the release, which attaches the plugin's zip and
one `.skill` file per skill for the first time. The generators reproduce the starter's
type scale and colour ramps, the contract has the roles its references needed, and the
README's commands paste into bash, PowerShell and cmd. Every fix has a regression test
that fails on 3.2.1, or on the head a review found it on
(`python -B -m unittest discover -s tests`: 513 tests).

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
- **The Supabase reference had no access boundary** (DL-B1, DL-A5, DL-C4), the first
  of the two high-severity gaps. `supabase-integration.md` now says which key each
  process holds (§9): the publishable key in the browser, and FastAPI either as the
  user, forwarding the caller's token so row-level security applies, or as the
  service, where no policy runs and the endpoint must do the policy's job. It says
  that every `VITE_` variable is public, and where validation and authorization are
  enforced. Three pieces of guidance were unsafe or wrong and are corrected:
  - The permission RPC was a `security definer` function in the exposed schema with
    no `search_path`. The template now keeps it in a private schema, pins
    `search_path = ''` and revokes `execute` from `public`.
  - "The JWT's claims" were trusted whole. Authorization data comes from
    `app_metadata` only, and a claim is as old as the token.
  - Realtime `DELETE` events are not policy-filtered, and `REPLICA IDENTITY FULL`
    does not return the old row on a table with RLS, so the fix the reference offered
    did not work in the case it was for.
  It also says that a public Storage bucket is world-readable whatever the policies
  say. Every Supabase fact was re-read at supabase.com on 2026-10-01.
- **The schema tool could not see row-level security** (DL-A6, DL-C1). It skipped
  `ENABLE ROW LEVEL SECURITY` and `CREATE POLICY`, listed "RLS policies" as missing
  from DDL that held them, and assumed RLS was on everywhere. `introspect_schema` now
  reads both statements and column revokes, records them per table, and opens
  `--summary` with a SECURITY block:
  - `BLOCK`: a table with RLS off, or a policy that lets a signed-in user write every
    row because its condition is `true`.
  - `warn`: RLS on with no policy for a signed-in user, or authority columns (`role`,
    `is_admin`, `org_id`) that a user who may update a row can change, with the
    revoke and grant that close it. A column counts as safe only when the user has no
    UPDATE privilege on it, or a policy pins it to the caller (`owner_id = auth.uid()`).
  Policies are replayed as the migrations state them: a dropped policy is gone, and a
  restrictive policy narrows the permissive ones and grants nothing.
  The findings are in the model (`security`), the "Is RLS on?" question defaults from
  the DDL, and `scaffold_ui` repeats the blocking findings and writes each table's
  forbidden-state notes from that table's own RLS. It still writes the screens by
  default; `scaffold_ui --strict` writes nothing and exits 1, for CI. From generated types or a JSON dump the block says "unknown".
- **The reference's column revoke did nothing** (N15, from CodeRabbit on PR #9). It
  told readers to protect `is_admin` with `revoke update (role, is_admin, …) on
  profiles from authenticated`, and secrets with a column-level `revoke select`.
  Postgres ignores a column-level revoke while a table-level grant stands, and
  Supabase grants table-level privileges by default. The reference and the security
  pass now give the form that works: revoke on the table, grant the columns back.
- **The skill's own command failed on two migration files** (N14).
  `introspect_schema supabase/migrations/*.sql` was an argparse error as soon as the
  folder held more than one file. Several DDL files are now read as one schema, in
  the order given, which is also how a later migration's policies reach the table.
  A pattern is expanded by the tool itself, because cmd.exe passes it as written.
- **The schema tool misread what Supabase writes** (DL-A7, DL-C2).
  - `supabase db pull` is `pg_dump --quote-all-identifier`, which quotes types too:
    `"text"` and `"date"` were unknown types, so a title fell back to the id and a
    date became a text input, and `"public"."order_status"` lost its values. An
    identity added by `ALTER TABLE … ADD GENERATED`, and a `serial` default set by
    `ALTER COLUMN`, were missed, so each id was a required number in the form.
  - A function's `$$` body was split at its own `;`, so an `alter table … disable
    row level security` inside a function turned RLS off for the table.
  - In generated types, prettier puts each member of a long union on its own line:
    an enum kept only its first value, and a Row column whose type wrapped was dropped.
  - Migrations: `generated by default as identity` read as an editable id,
    `ALTER TABLE … ADD COLUMN`, `DROP COLUMN`, `ALTER COLUMN` and `RENAME` were ignored, a quoted
    name with a space was not a name, and `CHECK (x between 1 and 99)` gave no bounds.
- **The worked example quoted a fixture nobody had** (DL-B8). It ships now, as
  `tests/fixtures/supabase/`, and the claims in supabase-integration.md §1 are
  measured on it. Two of them were wrong: generated types lose 12 rules across 9
  columns, not 14 across 13, and they lose a key into `auth.users`. The claim that a
  JSON dump gives the same model is gone: that depends on its query. The reference's
  `pg_dump` command keeps the privileges now, because the security pass reads them.

- **Vendor CSS beat every layer** (SB-A8). The canonical `index.css` in
  stack-vanilla-css §4 left `vendor` out of its statement and then imported into it,
  and a layer first named by its import is appended after `overrides`. Three references
  put `vendor` in three different places. The order is now in `design-rules.json`
  (`layers`): `reset, vendor, tokens, base, layout, components, utilities, overrides`,
  plus `theme` in a Tailwind entry. Every statement in the plugin names `vendor`, the
  contract's included. The audit and stylelint refuse a statement out of that order,
  and an `@import … layer(x)` whose `x` the statement does not name.
- **Self-wrapped files were imported with `layer()`** (SB-A23). Starter files open
  their own `@layer` block, so `layer(base)` around `base.css` made `base.base`, which
  stack-vanilla-css itself forbids. handoff-conventions and stack-tailwind did it, and
  style-architecture called it deliberate. handoff §7.1's pre-commit hook audited the
  whole tree on every commit; it takes the staged files now, as the hook does.
- **Two claims about a vendor's `!important` were wrong.** style-architecture §11 said
  a layer makes it lose to your components. stack-vanilla-css §5 said three `!important`s
  in `overrides` beat it. Important declarations reverse the layer order, so the
  vendor's win in both cases. The references now say to strip them at build time, or
  patch a vendored copy.
- **The schema parser misread four kinds of statement** (N16 to N19, from the reviews of #12):
  - A quoted name with a `$` (`"amount$usd"`, which every dump quotes) lost its quotes,
    and the column parser, which reads a bare name as word characters, then dropped the
    column without a word. Such a name keeps its quotes now.
  - `DROP COLUMN` left the column in the primary key, in unique indexes, and in other
    tables' foreign keys. Postgres drops every index and constraint that uses the
    column, the whole primary key with it, and needs `CASCADE` for the foreign keys
    into it, which it then drops. The model does the same, CHECKs included.
  - `RENAME COLUMN` left other tables' foreign keys and the CHECKs on the old name.
    Postgres retargets both, and so does the model; string literals stay as they are.
  - Postgres 18 names a not-null constraint: `add constraint t_name_nn not null name`.
    The parser read it as `ADD COLUMN` and made a column named `constraint`. It now
    makes the column not-null, in `ALTER TABLE` and `CREATE TABLE`, and an
    `ADD CONSTRAINT` it does not know is skipped, never read as a column.
- **The scaffold's policies failed on four kinds of schema** (N20 to N23, from the reviews of #13):
  - A model introspected with `--schema app` got every policy, grant and smoke test on
    `public`. They use the model's schema now.
  - `sql_ident` quoted nine reserved words, so a table named `select` or a column named
    `where` gave invalid SQL. It quotes every word Postgres reserves now, from a copy of
    the parser's list.
  - Postgres cuts a name at 63 bytes, so a table name of 55 bytes or more gave its four
    policies one name, and the second `CREATE POLICY` failed. A name that would be cut
    now shortens the table part, which ends in a hash of the whole name.
  - The smoke test's "no write policy" check counted a policy for `service_role`, which
    the browser never holds. It counts only policies for `public`, `anon` or
    `authenticated` now.
- **The layer statement** (N24 and N25 from the reviews of #14, and N29):
  - The canonical `index.css` stopped after `layout.css`, so a project that copied it
    never imported `utilities.css` or `overrides.css`. It names both now, imported last
    once the project has them, and the four references that quote it follow.
  - An `@import … layer(vendor)` above the `@layer` statement names `vendor` first,
    whatever the statement then says. The spec refuses it now, and so do the audit
    (`layer-statement-position`) and stylelint (`design/layer-order`).
  - stylelint never checked where the statement stands, so a rule above it passed,
    though the audit refused it. `design/layer-order` refuses it now, from a second
    refused example in the spec.
- **On Linux and macOS, `snapshot_matrix` missed a state with no style** (found by the
  first CI run). It called a hover, active or focus-visible cell unstyled only when it
  was pixel-identical to its default cell. The cells sit side by side at different
  subpixel offsets, and there text is antialiased by where it sits, so twin cells never
  matched and the check never fired. It now compares computed styles: a state is
  unstyled when every element of its cell, `::before` and `::after` included, computes
  the same style as in the default cell, leaving out what never changes a pixel (the
  cursor, pointer events, selection, motion timing).

- **The three gates agree on every example in the spec** (N1, N30). The conformance
  tests' list of known disagreements is empty:
  - The audit refuses a factor on a token in spacing and radius,
    `calc(var(--pad-card) * 1.5)` or `/ 2` (L3 `token-factor`), as stylelint did;
    `* -1`, which cancels a token, is still allowed. Positioning is geometry and may
    divide.
  - The audit's type check skipped every length ending in "em", and `rem` ends in "em",
    so `font-size: 1.125rem` passed. It now refuses both, except `font-size: 1em`, which
    sizes an icon to its text and which stylelint now allows too.
  - The audit reads the spec's sizing family, so `max-inline-size: 65ch` and
    `max-width: 600px` are refused (L1 `raw-size`), as stylelint refused them.
  - In a component file the audit refuses an element selector (`.card p`,
    `.card > svg`, `:is(h2, h3)`) and a `*` after a space (`.card *`), as stylelint's
    `selector-max-type` and `selector-max-universal` do (L2 `foreign-selector`). The owl
    is still allowed.
  - A system colour outside `@media (forced-colors: active)` is refused by the audit
    too (L1 `system-color`), in the properties the spec now lists for both gates.
  - `transition-duration: 0s` is no longer a literal duration to the audit, a named
    colour is an error rather than a warning, and a design literal in an inline custom
    property (`style={{ '--gap': '12px' }}`) is refused (L1 `inline-literal`), with the
    units ESLint uses; both gates read them from the spec.
  - stylelint allows a hex in a `var()` fallback, which the spec leaves unchecked:
    `design/color-no-hex` replaces `color-no-hex`. It also allows a margin in an owl rule
    in a component file: `design/component-margins` replaces the component override's
    margin allowlist, and knows the owl.
  - Thirteen reference snippets broke these rules and now follow them: element selectors
    became classes (`.megamenu__link`, `.toc__link`, `.drawer__link`,
    `.work-card__link`, `.table__cell`, `.check-input`, `.field__control`), base and
    layout CSS sits in its layer, and the hero's `18ch` measure is a Tier-3 socket. The
    starter's `sub`/`sup` at `0.75em` and the `cqi` fallback example keep their literal,
    with the audit's pragma beside stylelint's.
  - From #20's review: the factor check now skips a `var()` fallback, as the spec does
    (`var(--pad-card, calc(1rem / 2))`); the owl is the whole `> * + *` in both gates,
    so `.card + *` can no longer space a component's next sibling; stylelint finds the
    owl through an `@media` around the margin, as the audit did; and the header recipe
    keeps the page's reservation for the fixed header, as a `base` rule of its own.
  - From CodeRabbit's review of #20: each `inline-literal` finding names its property
    and value as its snippet, which is its baseline key's text. With the style's line
    there, a key kept only its first 120 characters, so a baselined literal hid a new
    one added further along a long line
    (`test_a_baselined_inline_literal_does_not_hide_a_new_one_beside_it`, which fails on
    `bc911b4`).

- **The holes in the stylelint allowlist are closed, and the gates agree on them**
  (SB-A15, N31). Each hole is now examples in the spec, which the conformance tests run
  through the audit and stylelint:
  - A colour function of literals is refused in every property: a `background` or
    `border` shorthand, a gradient, a filter. `design/no-literal-colour-function`
    replaces `function-disallowed-list`, which named only `rgb`, `rgba`, `hsl`, `hsla`
    and `hwb`. It reads the spec's colour functions, which now include `color-mix()` and
    `light-dark()`, and allows a colour derived from a token, a function with a `var()`
    among its arguments (`oklch(from var(--bg-accent) l c h / 0.5)`), as the audit does.
  - Line weights are a family, `stroke`. `border-width`, the side and logical widths,
    `outline-width` and `outline-offset` take a `--stroke-*` token or `0`, and the
    `border*` and `outline` shorthands take tokens, a style keyword, `currentColor` or
    `transparent`. The audit refuses a literal width too (L1 `raw-stroke`); it read only
    the colour there.
  - A margin outside a component takes the spacing scale: the spacing family lists the
    margin properties. In a component, Law 2 still holds it to alignment, a cancelled
    token, the owl, and now the component's own `::before` and `::after`.
  - Sizing covers every width and height. The maxima and minima, `inline-size`,
    `block-size`, `width` and `height` take a token, `100%`, `auto`, an intrinsic keyword
    or `1em`. A size derived from tokens goes in a socket.
  - The `transition` and `animation` shorthands take the motion tokens: a list of
    properties or keyframe names, tokens, keywords such as `allow-discrete`, `0s` and an
    iteration count. A time, a curve or an easing keyword (`ease-in`, `linear`, in any
    case: names are lowercase kebab-case) is refused there and in the timing-function longhands, by both gates; the audit missed
    the keywords.
  - theme.css's custom properties take a token, a colour word or a keyword, and the
    literals its §0 documents: a breakpoint in rem, never a `var()`, which a media query
    cannot read, and an aspect ratio. A breakpoint may be a CSS-wide keyword too, so
    `--breakpoint-*: initial` still clears Tailwind's own, and a prefix with a rule of
    its own answers to it alone (`--aspect-video: currentColor` is refused). The
    override switched the
    allowlist off, so
    `--spacing-card: 28px` passed. The audit checks them too (L1 `binding-literal`), and
    theme.css's `--animate-spin` and `--animate-pulse` read `--dur-loop`, not `1s` and
    `2s`.
  - Positions (`top`, `left`, `inset*`) are geometry, which the spec gives to the audit
    alone. The audit took `1rem` there for an em, and read only the first length, so
    `inset: -0.4em 12px` passed.
  - N31: `0` among tokens is allowed (`padding: 0 var(--pad-card)`), as the zero rule
    says, and `0px` is refused, as stylelint's `length-zero-no-unit` refused it. A share
    of the container in a spacing property (`calc(100% - var(--gutter-page))`, `5%`) is
    refused by the audit too. The audit no longer exempts a component's margin in a rule
    whose selector names `prose`, or any margin that holds an `auto`:
    `var(--gap-related) auto` sets the component's own block margin.
  - The audit's spacing, stroke, motion and sizing checks read the spec's allowlists, so
    they refuse what stylelint refuses. A value that holds a Sass variable or an
    interpolation is judged with each variable read as a token and each interpolation
    as the expression it emits, so `padding: $space 13px`, `$space 5%` and `#{5%}` are
    refused as their CSS forms are, and the variable is `sass-literal`'s (from the
    reviews of #23).
  - Seven reference blocks, two starter rules and two generated stylesheets broke the new
    rules and now follow them. Three inset focus rings used `* -2`, against the starter's
    `* -1`. The scroll-driven progress bar names its easing token. The table of contents'
    and the progress bar's derived sizes, the imposter's contained height and the
    scaffold's skeleton sizes are sockets. The reading column and the presentation deck's
    slides are `100%` up to the measure. The visually-hidden utility's 1px box carries
    both tools' pragma.

- **The docs promised checks that nobody ran** (SB-A11, SB-A25). Each one now exists,
  or its sentence says what does run:
  - The audit diffs a theme file's `--breakpoint-*` against the token file's `--bp-*`
    when both are in its run, and fails on drift (L1 `breakpoint-drift`), both ways: a
    token no theme copies is drift too, unless a theme drops it with `initial`. Every
    copy is checked, and a token's value is its last declaration. A Tailwind theme
    with no copies still counts, since Tailwind then keeps its own widths, and themes
    split across files mirror the tokens together. A generated theme is skipped, and
    a theme's ignore pragmas apply. A theme pairs only with a token file of its own
    project, the nearest folder above it with a `package.json`, and among those with
    the nearest that declares breakpoints. theme.css and
    stack-tailwind.md said it did; it never had. The v3 `tailwind.config.ts`, which
    the audit does not read, now says its `screens` are kept in step by hand.
  - Nothing compares theme.css's type bindings with the `--type-*` roles, no gate
    tells an ink from a fill by its class name (`text-danger`), the audit does not
    grep `tailwind.config.ts` for literals, and contrast is `check_roles.py`'s, not
    the audit's: the sentences that said otherwise say so. The `/<number>` modifiers
    are the audit's (`tw-opacity-modifier`), not stylelint's, which never sees a class.
  - `:where(.a .b .c .d)` has no specificity, so it no longer draws a
    `compound-specificity` warning (it is still four compound selectors, which N32
    refuses). The v3 config's `spin` and `pulse` read
    `--dur-loop`, as theme.css's do. The checklist has 91 checks, not 92, in three
    docs. The `@apply` "specificity returns" argument holds for v3 only: under this
    suite's layer order the utilities layer still wins. Two ESLint comments named the
    wrong criterion: `anchor-is-valid` does not read link text, and
    `media-has-caption` is WCAG 1.2.2. handoff-conventions.md now asks for
    `camelCaseOnly`, as stack-css-modules.md does, and quotes react.dev: `forwardRef`
    "will be deprecated in a future release".
- **The references' CSS passes the stylelint config too (N3).** The audit already
  held every block meant for copying; stylelint refused 28 of 159, and 56 of 170 at
  3.2.1. Each kind was settled by the spec:
  - Where the spec refuses what a block showed, the block changed. A box-shadow bar
    and a radius formula go through a socket, as the starter's geometry does. An
    `@property`'s `0px` and a `#ffffff` are gone. A view transition's pseudo-elements
    are styled in `base`, not in a component. Rules that broke
    `no-descending-specificity` were reordered, a selector over the cap uses `:where()`,
    side-by-side alternatives are blocks of their own, and the anti-examples say
    `example: wrong`.
  - Escape hatches that named only the audit now name stylelint too, in the one
    comment both read.
  - Where the spec allows what the config refused, the config changed. Sub-layers
    inside a canonical layer, `@layer components { @layer base, skin; }` as
    stack-vanilla-css teaches, are now a spec example: the rule read the nested
    statement as the file's own order and refused `skin`. CSS Modules' `composes` and
    `:global`, which stack-css-modules teaches, are known words.
- **The Tailwind v3 entry is a file (SB-C9).** `assets/configs/index.tailwind-v3.css`
  joins the vanilla and v4 entries, with the vendor layer, and stack-tailwind §11.6
  quotes it instead of writing its own. Preflight goes in `reset`, as in v4. The v3
  `tailwind.config.ts` set a project up with the `@tailwind` directives under a native
  layer statement, the unlayered output its own footer warns about, and without the
  `postcss-import` that `layer()` needs; it now points at the entry.
- **The selector limits are the spec's (N32).** `design-rules.json: selectors` holds
  the specificity cap, 0,3,1, and three compound selectors, with examples both gates
  are held to; `tools/sync_rules.py` writes the limits into each.
  - The audit weighed a selector by counting four chained classes. It now weighs it as
    Selectors 4 and stylelint do: `:where()` scores zero, `:is()`, `:not()` and `:has()`
    their heaviest argument, and a nested rule's `&` its parent's. So `.card:is(.a.b.c)`
    and `.a.b.c p span`, which passed, are over the cap.
  - The audit did not count compounds at all; `compound-selectors` does, as stylelint
    17 counts them, inside a functional pseudo-class too. stylelint refused
    `:where(.a .b .c .d)` and the audit allowed it: `:where()` takes away the weight,
    not the knowledge of four levels of DOM, so the spec refuses it.
    `:where(.a.b.c.d)` is allowed.
  - stylelint also reads the `+` of an An+B (`:nth-last-child(n + 5)`) as a
    combinator. The audit does not, and the spec says so: a quantity query keeps its
    stylelint disable comment.
  - stack-vanilla-css quoted a stylelint config with a 0,3,0 cap and every heading let
    into components. It now points at the shipped config. The landing-page sections'
    FAQ marker weighed 0,4,0, which both gates refuse; its path is in `:where()` now.
- **The type generator reproduces the starter** (SS-A9, SS-C5). Its docstring said a
  command reproduced `tokens.css` "approximately": it printed 9/11/13/16/20/25/31/39/49
  and fluid 49→61 and 61→76.5, against the starter's 11/12/14/16/18/22/28/35/44, 44→72
  and 56→110. SKILL.md's Phase 1 command printed 9.26, 11.11 and 13.33px steps.
  `--preset studio` now prints the starter's `--text-*` exactly. The scale is
  hand-tuned, so the preset is a table, and the docstring says where it departs from
  the math. SKILL.md's Phase 1 runs the preset and says how to depart from it, and
  every type command in the docs runs clean.
- **Fluid type and zoom were half taught** (SS-B5). typography.md §10 called a `rem`
  intercept sufficient for SC 1.4.4. It now adds Barvian's bound, a maximum at most 2.5
  times the minimum, and what zoom does to the starter's hero: in a 1440px window,
  `--text-6xl` grows only 1.33× at 200% and first reaches 2× at 400%. §15 checks both.
  The generator refuses a `--fluid-min-ratio` over 2.5, and any fluid step that
  `--snap-px` rounding leaves over 2.5 times its minimum.
- **The colour generator reproduces the starter** (SS-A9, SS-B7). SKILL.md's Phase 1
  seeded both ramps from `#e8440a`. The accent drifted in hue and lost chroma to sRGB,
  where the starter's holds hue 42 and keeps its P3 tints and shades. The neutral took
  the seed's hue, 36, which reads pink, where the starter's is 75. And the generator
  put the neutral's 500 at L 58%, which regenerates the 4.08:1 `--fg-subtle` failure
  `tokens.css` fixed by hand: it is 53.5% now, 4.60:1 on `--bg-sunken`. Phase 1's two
  commands, and color-system.md's, print the starter's 24 ramp steps exactly.
- **A brand's exact colour was lost** (SS-B6). The ramp replaced the seed's lightness,
  so `#e8440a` became `--accent-500: #f14d1a` and was in no step, without a word.
  `--anchor-seed` makes the seed itself the step nearest it in lightness, written
  precisely enough to name the same hex. Without it, the report gives step 500's
  distance from the seed and points at the flag.
- **An invalid field looked focused** (SB-B4). accessibility.md drew `aria-invalid` in
  `--border-focus`, and content-model-to-ui's scaffold drew it in `--border-accent`. Both
  read `--border-invalid` now. The Figma audit measured an on-status ink on the canvas,
  not on its fill, and the docs and versioning tools now measure each ink on its fill.
- **The starter referred to files it did not ship, and its comments contradicted it**
  (SS-B2, SS-C9, SS-A17, SS-A18).
  - `utilities.css` (one `.visually-hidden`; pattern-invention.md, the stack
    references and the scaffold said `.u-visually-hidden`), `overrides.css` (the empty
    last layer, with its convention) and `theme-init.js` (the no-flash theme script,
    which now survives blocked storage) ship, and index.css imports both stylesheets.
    `[hidden]` stays in reset, the first layer, where its `!important` beats every later
    one.
  - tokens.css named `--gray-800` and `--btn-pad-x`, said components never read Tier 1
    and themes re-point "Tier 2 ONLY", and counted four leadings above five. Law 3
    counted five durations; there are six. motion-system.md never named `--dur-loop`,
    spacing-system.md asked 1.5× between levels the ladder spaces 1.33×, and
    style-architecture.md re-pointed one step of a white-label's ramp.
  - reset.css: `html:has(:target)` smoothed every later scroll once any fragment was
    targeted, so the rule is gone (smooth an in-page link from its click handler), and
    `body` uses `100svh`, not `100dvh`, as layout-composition.md says.
- **The vanilla stack's naming rule 4 named classes the starter does not have.** It
  prefixed the layout primitives (`.l-stack`, `.l-grid`, `.l-center`), and the
  starter's layout.css defines `.stack`, `.grid` and `.center`. The rule now keeps the
  starter's names.
- **The README's commands work in PowerShell and cmd** (XC-A2, N8, XC-B5, XC-C9). The
  install section had a placeholder, and gives the GitHub route now:
  `/plugin marketplace add Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`. `WDS`, the
  plugin's `skills` folder, has a form for bash, PowerShell and cmd, at the path Claude
  Code installs to. Each command is one line whose only expansion is `"$WDS/…"`: no
  assignment, no trailing comment.
- **`python3` and `/tmp/`.** The accessibility and performance skills started their
  local server with `python3`, which on many Windows machines is the Microsoft Store
  placeholder, and so did `measure_vitals.mjs`'s note on `file://` URLs. The state
  matrix wrote its narrowed preview to `/tmp/b.html`. They use `python` and
  `matrix-button.html`.
- **TypeScript is pinned beside typescript-eslint** (N7). The ESLint config composes
  typescript-eslint, whose 8.71.0 accepts TypeScript below 6.1.0, and npm's latest
  TypeScript is 7.0.2, so an unpinned install is a peer conflict. The config's install
  line pins `typescript@~6.0`.

### Added

- **Roles the references needed** (SB-B4, SS-B2). Seven, in the contract (all 14 copies),
  the starter and the deck, both Tailwind configs, the Figma importer, the email map and
  the migration proposal:
  - `--fg-on-success`, `--fg-on-warning` and `--fg-on-danger`, the ink on a filled status
    badge. White measures 3.41:1 on the success fill and 2.25:1 on the warning fill, so
    a filled badge had no legal text colour; the inks are near-black, near-black and
    white (6.10, 9.24 and 4.75:1).
  - `--border-invalid`, an invalid field's boundary: `--danger-500`, and `--danger-400` in
    dark.
  - `--motion-travel-xs/-sm/-md`, travel distance as steps of the spacing scale, which
    motion-system.md told readers to add themselves.

  `check_roles.py` holds each fill to its ink at 4.5:1, and the invalid border to 3:1 on
  every surface (100 pairs, from 88). Translucency needed no role: the ESLint config
  already refuses a `/NN` opacity modifier and points to `--bg-hover`, `--bg-active` and
  `--bg-scrim`.
- **The generators' options for the starter** (SS-C5). `generate_color_ramp.py` gains
  `--gamut p3` (reduce chroma into Display P3, not sRGB; the contrast matrix measures a
  step outside sRGB on the worse of its two sRGB fallbacks), `--neutral-hue` and
  `--anchor-seed`. `generate_type_scale.py --fluid-space` prints the starter's four
  `--space-fluid-*` steps, solved for the type's viewport anchors, which `tokens.css`
  already told readers to regenerate there.
- **The audit in CI** (SB-C10). `--files-from FILE` audits the paths a file or stdin
  (`-`) lists, one per line or NUL-separated, such as
  `git diff --name-only -z origin/main... | python -m scripts.audit_design --files-from -`;
  a listed path that no longer exists, a deleted file, is skipped. `--sarif` writes
  the findings as SARIF, the format GitHub code scanning reads (checked 2026-10-03 at
  docs.github.com: "Code scanning only supports SARIF version `2.1.0`"), with a
  rule per law and id, and paths relative to the working directory under a
  `%SRCROOT%` the run defines. It sets no fingerprint: code scanning reads only its
  own, which `upload-sarif` computes from the source (from the reviews of #24). A
  NUL-separated list keeps each name exactly, even a Linux name that is not UTF-8.
  The line lookup SB-C10 asked for was
  already a bisect.

- **One canonical entry stylesheet per stack** (SB-C9, SS-C9 in part). The starter
  ships `index.css`, and the configs ship `index.tailwind.css` for Tailwind v4. Five
  references quote them through `tools/sync_snippets.py` instead of writing their own.
- **The scaffold proposes each table's row-level security** (DL-B2). It used to
  decide which columns a form writes and emit client validation, with nothing on the
  database side. Now `db/policies/<table>.policies.todo.sql`, join tables included,
  turns RLS on and guesses whose a row is from the keys: the user's own row, an owner
  column, a child of an owned row, a tenant (a commented template) or nobody (read
  only). It revokes the table-level insert and update and grants back the form's
  columns, so the database and the `Draft` type agree. No write policy it proposes
  has a `true` condition, and the schema tool finds no hole in the result.
- **A smoke test per table**, `<table>.policies.test.sql`: plain SQL in a transaction
  that rolls back. It checks that RLS is on, that `anon` sees nothing, that a signed-in
  user sees only their rows, and that the columns outside the form refuse a write.
- **`lib/supabase.ts`** (the rest of DL-B1): the browser's one client, with the
  publishable key. It refuses to start on an `sb_secret_` key or a legacy
  `service_role` JWT.

### Changed

- **The type generator's default is the starter's scale** (SS-C5). With no scale flag
  (`--base`, `--ratio`, `--dual-ratio`, `--steps-up`, `--steps-down`, `--snap-px`,
  `--fluid`, `--fluid-steps`, `--fluid-min-ratio`), `generate_type_scale.py` prints
  `--preset studio`. Any scale flag gives a ratio run, the pure math, as before. The
  default ratio run, 1.2 with three steps down, reached 9.26px, so a plain refusal of
  small steps would have broken every run without flags.
- **Every skill's description fits a claude.ai upload.** The 13 descriptions were 301 to
  368 characters; claude.ai's help center gives 200 for an uploaded skill, and the
  platform 1,024. Each now says what the skill does and what it is not for in 185 to
  200 characters, and `test_skill_budget` holds every one to 200.
- **Python 3.9 or newer**, down from 3.10. The scripts already ran on 3.9, the Python
  macOS still ships; now the tests do too. The harness no longer uses
  `TemporaryDirectory(ignore_cleanup_errors=)`, `write_text(newline=)` or a slice of
  `Path.parents`, all 3.10+, and the README states the new floor.
- **CI** (XC-B3). `.github/workflows/ci.yml` runs the suite and the static checks on
  Windows, Linux and macOS, at Python 3.9 and 3.14, with the pinned Node tools, and
  `claude plugin validate --strict` on the marketplace, the plugin and `plugin.json`.
  Linux adds Playwright's headless shell and Postgres, so the browser and policy tests
  run there too.
- **The release build** (XC-C6). `tooling/release/build.py` replaces `build_zip.py`. It
  makes the plugin's zip, one `.skill` file per skill, packaged as Anthropic's
  skill-creator packages one and carrying the plugin's LICENSE, and `SHA256SUMS`, all
  from git and byte-identical on a rebuild. A pushed `v*` tag makes
  `.github/workflows/release.yml` build them and create the GitHub release, with the
  CHANGELOG's section as its notes; nothing else creates a release.
- **The 17 scripts with a shebang are executable** (N5), as the nine from 3.0.0 were.
- **The spec writes its data into the gates** (N2, SB-C2). `tools/sync_rules.py` writes
  `design-rules.json` into a marked block in each of the three gates, and `--check`
  fails CI when a gate drifts from the spec:
  - the audit: the layer order and statement, the nesting depth, and the colour
    functions it reads as a colour written by hand;
  - the stylelint config: the layer order, the nesting depth, the system colours, and
    the value allowlists, which were hand-written: the four value shapes (`VAR_SEQ`,
    `VAR_ONE`, `VAR_CALC`, `CANCEL`), the keywords, the colour words, the 43 properties
    of eight families (spacing, type, radius, elevation, colour, stacking, motion,
    sizing) and the component margins;
  - the ESLint config: the colour functions, for its raw-colour rule and its
    inline-style rule. The inline-style rule missed `hwb()` and `color()`; the
    raw-colour rule already refused both there, so no verdict changes.

  Why each family takes what it takes moved from the stylelint config's comments into
  the spec, beside the data. Each section of the spec now names the gates that
  enforce it (`gates`). A spec entry the tool cannot write, such as an unknown shape,
  is an error, and nothing is written.
- **Two tools for each PR.** `tools/fail_before.py` runs named tests against an earlier
  revision and this tree, and prints fixed, control, still failing or regression for
  each. `tools/check.py` runs the static checks and the tests a change affects. Its
  report prints on any console: with its output redirected on Windows (cp1252), a
  failing check's `§` reached it as an invalid byte and the report crashed printing it,
  so no report came. The checks now write UTF-8, and a character the console cannot
  encode prints as `?` (`test_tools.CheckReportsOnAnyConsole`, which fails on `9053727`).
- **accessibility.md's testing procedure is a reference of its own** (N4).
  `accessibility-testing.md` has the keyboard, zoom, forced-colors and screen-reader
  passes, the automated tools and what they miss, and regression tests. accessibility.md
  was 60,400 bytes against the 60,500 limit and is 52,963 now; its §10 points to the
  new file, and SKILL.md's reference table lists it.
- **The token contract names its master copy** (XC-A5): `shared/token-contract.md`,
  which each skill's copy matches byte for byte. All 14 copies say so.

### Upgrading

- **A theme file's breakpoints must match the tokens** (SB-A11): when one audit run reads
  a theme file and a token file, each `--breakpoint-*` that differs from its `--bp-*`,
  or has none, is an error (`breakpoint-drift`). So is a `--bp-*` no theme copies, which
  a Tailwind theme with no copies leaves at Tailwind's own width; drop one on purpose
  with `initial`. Audit the folder that holds both.
- **The audit is stricter** (N1, N30): a `rem` or `em` font size, a literal size in
  `max-inline-size`, `max-width`, `min-block-size` or `min-inline-size`, an element
  selector in a component file, a named colour, a system colour outside forced-colors
  mode, and a design literal in an inline custom property are errors now. Each is what
  stylelint or ESLint already refused.
- **Both gates are stricter** (SB-A15, N31). The audit and stylelint now refuse a colour
  function of literals in any property, a literal border or outline width, a literal
  margin outside a component, a literal width or height, a time, curve or easing keyword
  in a `transition` or `animation`, a zero with a unit (`0px`), and a literal in a theme
  file's custom properties. Run both over your project before upgrading: each finding
  names the token to use, and a size derived from tokens moves into a socket. A disable
  comment that names `function-disallowed-list` needs `design/no-literal-colour-function`
  instead. theme.css's `animate-spin` now turns in `--dur-loop` (900ms, was 1s), and
  `animate-pulse` breathes in it too (was 2s).
- **The audit holds the selector limits** (N32): a selector over 0,3,1, or of more than
  three compound selectors, is an error (`compound-specificity`, which warned only on
  four chained classes, and the new `compound-selectors`). Both are what stylelint
  already refused. Wrap the context in `:where()`, which weighs nothing, or give the
  element a class of its own.
- **Two stylelint rules were renamed.** A disable comment for `color-no-hex` names
  `design/color-no-hex` now, and one for a component's margin names
  `design/component-margins` instead of `declaration-property-value-allowed-list`.
- **The type generator refuses a step under 11px** (SS-C5). A ratio run that puts any
  step, or a fluid step's minimum, under 11px exits 2 and names the ways out: fewer
  `--steps-down`, a smaller `--ratio` (1.125 keeps three steps down, at 11.24px), or
  `--allow-small` to emit it with a warning. `--snap-px` is not one: it rounds 9.26px
  to 9. A run with no scale flags now prints the starter's scale instead of the 1.2
  ratio run, and `--preset` cannot be combined with a scale flag.
- **A regenerated neutral's 500 is darker** (SS-A9): L 53.5%, not 58%, as in the
  starter. A neutral generated before 3.3.0 and used for placeholder text measures
  4.08:1 on `--bg-sunken`; regenerate it.
- **`check_roles.py` needs the new roles** (SB-B4, SS-B2). Its built-in pairs read
  `--fg-on-success`, `--fg-on-warning`, `--fg-on-danger` and `--border-invalid`; a
  `tokens.css` without them exits 2 ("not declared"). Declare them (the starter's
  bindings are a start), or pass your own list with `--pairs FILE`.

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
- DL-B1, DL-A5 and DL-C4: `test_docs.SupabaseGuidance.test_the_access_boundary_is_stated`
  holds what the reference must say and must no longer say. Against 3.2.1 it fails
  in 16 subtests. The two dated figures it quotes are in the evidence register.
- DL-A6, DL-C1, N14 and N15: twelve tests in `test_content_and_a11y.SchemaSecurityPass`. Against
  3.2.1 all twelve fail. Controls inside them: a public read policy, a policy for the
  service role and an owner check are not findings.
- DL-A7, DL-C2 and DL-B8: `test_schema_sources`, fifteen tests on real output. The
  worked example in three forms: the migration, a `pg_dump` of it from Postgres 18,
  and the same schema as `gen types` writes it. Also `gen types` for a real 25-table
  project. Against 3.2.1, thirteen fail. The real project's types and the `db pull`
  form pass there, as controls: the parser already read both.
- DL-B2 and DL-B1: `test_policies`, eleven tests. Three run the generated SQL on a
  scratch Postgres when one is on PATH, and skip otherwise. Every proposal applies and
  every smoke test passes. Then four breakages each make their test fail with its
  reason: an open read policy, a re-granted owner column, RLS turned off, and a write
  policy on a read-only table. Against 3.2.1 all eleven fail.
- SB-A8, SB-A23 and SB-C9:
  - `test_rules_spec`: the spec's layer examples through the audit, the stylelint
    config's copy of the order, and every layer statement in the docs, configs and
    starter. Against 3.2.1 all three fail.
  - `test_real_tools.StylelintConfig` runs the examples through the real stylelint,
    and lints the two canonical entries. On 3.2.1 it cannot set up, because the
    entries do not exist there.
- `test_docs` runs `test_harness` on the floor interpreter, and `test_harness` checks
  the temporary folders and `TempDirTest.write` there. On 3.9, 3.2.1's harness errored
  in 181 tests.
- `tools/check_pointers.py --write-register` and `tools/sync_snippets.py` (without
  `--check`) are tested writing a file: UTF-8, LF, byte for byte. With 3.2.1's tools
  both tests error on 3.9, where `write_text` has no `newline`.
- The budget test passes `maxsplit` to `re.split` by keyword, as Python 3.13 asks.
- N16 to N25 and N29, against `8ed2e84`, the `main` before the fix, since none of this
  code is in 3.2.1. Fifteen tests fail there, in 26 failures and 2 errors:
  - `test_schema_sources`: one test per parser fix, four in all.
  - `test_policies`: eight tests. Four run on the scratch Postgres: a schema of its own,
    and reserved words with a 60-byte table name, each apply and pass their smoke tests;
    every word `pg_get_keywords()` reserves is on the list; and a write policy for
    `service_role` passes the smoke test while one for every role fails it.
  - `test_rules_spec`: the entry names a file for every layer (N24), and `test_layers`
    on the new refused example (N25).
  - `test_real_tools.StylelintConfig` on the two new refused examples (N25, N29).
  - The 20 tests in the same classes that pass on both are the controls. Among them is
    the N29 example through the audit, which refused it already.
- `load_script` moves into `wds_support`, for the test that holds the scaffold's copy
  of the reserved words equal to the parser's.
- What the reviews of #16 found, against its first commit (`0a0c249`): five tests fail
  there, and twelve controls pass on both.
  - A rename or a drop no longer reaches into a call (`lower(note)` is not a column
    `lower`) or into a quoted name (`"old.part"` is not `old`).
  - A table constraint listed before its column now applies.
  - The smoke test quotes every name it puts in a string (a table named `it's`).
  - The no-write check counts a role that `anon` or `authenticated` inherits.
  - A second review: a rename or a drop leaves dollar-quoted literals alone; the smoke
    test picks a `do` delimiter no name contains (a table named `cash$$flow`); and the
    no-write check counts inherited privileges (`USAGE`), so a membership granted
    `WITH INHERIT FALSE` is not the browser's. Four tests fail on `81b50f9`.
- N5, the PR tools and the build, from `tools/fail_before.py` against 3.2.1: nine
  fixed and eleven controls.
  - `test_file_modes` reads git's modes (the index, or the commit `WDS_PLUGIN_REV`
    names) and fails on 3.2.1, where 17 scripts with a shebang were 100644.
  - `test_tools`, eight tests, all fixed. `fail_before.py` runs on a fake repository of
    two commits with a fix, a control, a test that still fails, a regression, failing
    subtests, a skip and a failing `setUpClass`. `check.py`'s choice of tests is checked
    on its own, and its list of changed files keeps a path with a space whole.
  - `test_release_build` ports the zip builder's seven tests to `build.py` and adds four:
    each `.skill` file, the sums, a skill the platform refuses, and a long description
    as a warning. The builder lives in `tooling/`, outside the plugin, so all eleven run
    the same builder in both runs: they are controls.
- `test_policies` keeps the scratch cluster's socket in its own folder: Debian's and
  Ubuntu's Postgres put it in `/var/run/postgresql`, which only `postgres` may write.
- N2, part 1: `test_tools.SyncRules`, three tests on a copy of the spec and the two
  gates (a spec change is stale until rewritten, a rewrite of a tree in step changes
  nothing, a gate without its block is an error), and
  `test_rules_spec.test_the_specs_data_is_written_into_the_gates`, which replaces two
  tests that read the stylelint config's layout as text. All four fail on 3.2.1. A fifth,
  from #18's review: the audit's nesting fix said "past depth 2" whatever the spec's
  limit; it now names the generated limit (`test_the_audit_explains_the_limit_the_spec_sets`,
  which fails on `eb4cccc`, with the other three `SyncRules` tests as controls).
- N2, part 2: the conformance tests. One builder turns every `allowed` and `refused`
  example in the spec into a file, and each gate its section names must give the
  spec's verdict: the audit in `test_rules_spec.TheAuditFollowsTheSpec.test_every_example`,
  stylelint and ESLint in `test_real_tools`'s `test_every_example_of_the_spec`. They
  replace five tests that read the stylelint config as text. Where a gate still
  disagrees, `KNOWN_DISAGREEMENTS` names the item that fixes it, and the test fails
  once the gate agrees: three are stylelint's (N1 rows 6 and 7), ten the audit's (N1
  rows 5 and 8, and seven new ones, N30, for P3). Against `9053727`, PR #18's head:
  three new `SyncRules` tests fail (the allowlists, the colour functions, and an
  unknown name that writes nothing), and 25 tests are controls, the conformance tests
  among them, so the generated blocks change no gate's verdict on any example.
  From #19's review: a shape the spec added and a family used was named in the
  stylelint allowlist but never declared, so the config could not load while `--check`
  passed. The block now writes every shape in the spec, and an allowlist that reads a
  name the block has not written first is an error
  (`test_a_new_shape_is_written_before_the_allowlist_that_reads_it`, which fails on
  `a7157c2`).
- The first CI run, on Linux and macOS: `test_browser_runtime.MatrixSeesStateChanges`
  failed there and passes now, which holds the `snapshot_matrix` fix; on Windows it
  passes on both. Two tests assumed Windows: `test_harness` took a relative path across
  drives (the runner's checkout is on `D:`), and `test_release_build` set a mode git
  re-read from the disk on POSIX. On a loaded macOS runner, the mega-menu scenario in
  `test_recipes.NavigationCodeInABrowser` dwelt over a trigger past the recipe's
  switching delay, because it timed the pointer with real waits. Its page now runs on
  Playwright's fake clock, which only the scenario advances. Its diagonal also went two
  thirds of a pixel down per step, so some steps rounded to straight sideways, which
  is not heading into the panel; each step now goes a whole pixel down.
- P3 part 1 (N1, N30): the spec's examples now hold every row of N1 and every case of
  N30, and `KNOWN_DISAGREEMENTS` is empty, so the conformance tests hold all three gates
  to every example; new allowed selectors (`:nth-child(2n + 1)`, `:lang(en)`, `:where()`
  and attributes) guard the audit's selector check against false positives. The
  snippet test files a block written in `@layer base` or `layout` in that layer's file,
  not a component's.
  Against `a7157c2`, #19's head: the audit's and stylelint's conformance legs and the
  renamed-rule fixtures fail (3 tests, 26 subtests), and 29 tests are controls.
- The mega-menu's safe-triangle test failed once more on macOS with 3.14 (#19's CI),
  under the fake clock: the clock does not decide when Chromium delivers a move, so
  a move could land after the hover-intent look had run. Each step of the scenario
  now waits, in real time, until the page has seen its move. Its markup carries the
  reference's new classes.
  It failed again on macOS with 3.9: `page.clock.install()` alone lets the fake clock flow
  in real time, so a slow runner overran the menu's 300 ms cap. A real 60 ms delay per
  step reproduced it locally. The scenario now pauses the clock once the page has
  loaded, and keeps that delay as a guard: it passes with the pause, and fails without.
- P3 part 2 (SB-A15, N31): the spec's examples hold every hole: the colour functions in
  any property, the `stroke` family, margins in a layout file (a family's `layout`
  examples), the wider sizing family, the motion shorthands, the theme bindings (files of
  their own, `*-theme.css`), the audit-only `geometry`, and N31's zeros, shares and
  margins. stylelint also lints theme.css as shipped
  (`test_theme_css_passes_the_override_that_guards_it`), and the spec's binding file class
  is held against the audit and the config's override. Against `cde5e05` (`main`): the
  audit's conformance leg fails 31 subtests and stylelint's 36, the file classes one,
  and the two unit tests that let a zero with a unit pass one each (5 tests); 6 are
  controls, among them the references' snippets, the starter's own stylelint run and
  ESLint's leg. Against `v3.2.1`, 8 fail and 3 are controls.
- P4 (SB-A11, SB-A25, SB-C10): `test_audit_design.ThePromisedChecks` and `TheAuditInCi`.
  Against `fc92cf7`, #23's head: the breakpoint diff, the CLI's list and SARIF, and
  `:where()` fail (6 tests), and so do the doc promises (14 subtests) and the stated
  checklist count (3); the shipped theme's breakpoints, which mirror the starter's
  tokens, are the control. The reviews of #24 added nine, each failing on the head it
  reviewed: the breakpoint diff's other direction and pragmas, and the NUL list,
  against `c3b154e` (2); a repeated declaration, a generated theme, an empty side and
  a theme split across files, against `6c64c24` (4); another project's tokens,
  against `98cf7b8` (1); a nested package's, against `b71ed10` (1); and a listed name
  that is not UTF-8, against `5a7fbae` on Linux (1). Windows and macOS skip that
  one: their file names are always Unicode.
- P5 (N3, SB-C9, N32): `StylelintConfig.test_the_references_css_snippets_pass_the_config`
  lints every CSS block of the references in the files the audit puts it in, and the
  canonical entries' test lints the v3 entry. The spec's `selectors` examples and its
  sub-layer example run through the audit and the real stylelint, and `TheAuditInCi`
  holds `:where()` and a nested rule's weight. Against `a5a54e7` (`main`): the
  references fail 24 subtests, the audit's conformance leg 6, stylelint's 1, the
  allowed fixtures 2 and the canonical entries 1, and the two audit tests fail
  (7 tests); the starter's own runs, the references through the audit and the
  quotes are the controls (5). Against `v3.2.1`, 9 fail and 3 are controls. The
  reviews of #26 added four, each failing on the head it reviewed: a `:hover` rule,
  which adds no nesting depth, was weighed without the rule it sits in, and
  `::slotted()` without its argument (against `5ac2223`); a quoted `)` closed a
  `:where()` early, and a quoted `&` read as nesting (against `781e4ea`). stylelint's
  leg, which already read all four, is the control.
- P6 part 1 (SS-B5, and the type halves of SS-A9, SS-B7 and SS-C5): `test_numbers`
  gains `TypeScale` (11 tests) and `FluidTypeZoom` (2). The preset and the default
  print `tokens.css`'s `--text-*`, SKILL.md's Phase 1 command does too, every type
  command in the docs exits 0 with nothing on stderr, a step or a fluid minimum under
  11px is refused with its ways out unless `--allow-small`, the preset refuses scale
  flags, and a fluid span over 2.5 is refused. Each fluid `--text-*` in `tokens.css` is
  within 2.5 times its minimum, and the figures typography.md §10 quotes recompute from
  it. Against `v3.2.1` and against `ca4f206` (`main`), 10 fail; the 2.5 bound on
  `tokens.css` and a 1.125 run, the refusal's own way out, are the controls (2).
  Codex's review of #28 added one: `--snap-px` rounds a fluid step's two ends apart,
  so a 2.485 shrink emitted 16→40.5px, a 2.53× span
  (`test_a_snapped_fluid_span_over_2_5_times_is_refused`, failing on `38d11cc`).
- P6 part 2 (SS-B6, and the colour halves of SS-A9, SS-B7 and SS-C5): `test_numbers`
  gains `ColourRamps` (10 tests) and two `TypeScale` tests. SKILL.md's and
  color-system.md's colour commands print the starter's 24 ramp steps, every colour
  command in the docs runs, the generated neutral's 500 clears 4.5:1 on `--bg-sunken`,
  `--neutral-hue` sets the hue, `--anchor-seed` keeps `#e8440a` exactly at its nearest
  step, the report gives step 500's distance from the seed, color-system.md quotes
  that report, and `--fluid-space` prints the starter's fluid spacing. Against
  `v3.2.1` and against `38d11cc` (#28's head), 11 fail; every documented colour
  command running is the control (1).
  Codex's review of #29 added one: a P3 step was measured with its channels clipped
  to sRGB, so a hot pink's `--accent-400` read 3.00:1 and UI-safe; with its chroma
  reduced, as a browser may show it, it is 2.58:1. The matrix now takes the worse of
  the two (`test_a_p3_step_is_measured_on_its_worse_srgb_fallback`, failing on
  `9db30d0`).
  CodeRabbit's added another: chroma under 0.0005 was written as none, so the
  anchored step of `oklch(33.9% 0.0003 140)` read `oklch(33.9% 0 0)`, not the `#373837`
  the report named. The anchored step keeps its chroma now, and a seed no `oklch()` of
  six decimals can name is refused
  (`test_an_anchored_near_grey_keeps_its_hex_in_its_css`, failing on `bcca304`).
- P7 part 1 (SB-B4, and SS-B2's roles): `test_check_roles` holds the status inks and the
  invalid border (`test_status_inks_and_the_invalid_border_are_held`),
  `test_contract.InvalidFieldsLookInvalid` reads every `aria-invalid` border rule, and
  `test_figma_sync.StatusInks` measures an ink on its fill. Against `v3.2.1` and against
  `80108ae` (`main`), all 3 fail; `EveryConsumerKnowsEveryRole`, which passes on both
  contracts, is the control (5).
  Codex's review of #31 added two:
  - the filled danger and success variants kept `--fg-on-accent`, near-black in dark
    and 4.38:1 on `--bg-danger`, and the state matrix put `--fg-on-inverse` on the
    warning fill. The scaffold, the stack references and the matrix now use each fill's
    ink (`StatusFillsCarryTheirInk`, 7 subtests failing on `590ab8e`);
  - the Figma export dropped the travel roles as composites, and the versioning report
    did not measure the invalid border on the sunken input.
  CodeRabbit's added two, in the Figma audit: an `on-*` ink whose fill is not in the file
  was not measured at all (it is measured on the system's fill now), and
  `motion-travel-sm = 8` was read as 8ms (`StatusInks`, 2 tests failing on `654034c`).
- P7 part 2 (SS-B2, SS-C9, SS-A17, SS-A18): `test_contract.TheStarterKeepsItsWord`
  recomputes Law 3's counts from tokens.css, reads the comments' names and leading
  count, checks the shipped files and their imports and that no `u-visually-hidden`
  remains, and holds reset.css to no smooth scrolling and `svh`. Against `v3.2.1` and
  against `3cb09cc` (#31's head), all 4 fail. The starter's own audit now reads 7 files.
  CodeRabbit's review of #32 added one: SKILL.md still counted five durations; the Law 3
  test now reads it too (failing on `fc02def`). The contract's "Tier 2 only" now names
  the two Tier-1 moves tokens.css allows.
- P8 part 1 (XC-A5, N9, rule 4): `test_contract.ContractCopies` compares each skill's
  copy with the master and names the ones that differ, and holds the header to naming
  the master. `TheStarterKeepsItsWord.test_the_vanilla_stack_names_the_starters_primitives`
  holds rule 4 to layout.css. `test_docs.Manifests` holds the repository's marketplace
  to the plugin's in every field but `source`, with a planted difference as its positive
  control. Against `v3.2.1`, 2 fail; the other 5 are controls (the copies, the deck's
  tokens and the two manifests agree today).
  Codex's review of #34 added one: under `WDS_PLUGIN_ROOT`, the manifest test compared
  another copy's marketplace with this checkout's, so an older release's legitimate
  drift failed it. It now compares only this repository's own plugin
  (`test_a_copy_elsewhere_is_not_held_to_this_repository`; the old test fails on a
  copy with another description).
  CodeRabbit's added one: the comparison read a missing field and a `null` one alike
  (`test_an_absent_field_differs_from_a_null_one`, which fails on `e97785c`).
- P8 part 2 (XC-A2, N8, XC-B5, XC-C9, N7): `test_docs.PasteableCommands` reads every
  shell line of both READMEs for what bash, PowerShell 5.1 and cmd read differently
  (continuations, comments, `&`, `;`, substitutions, assignments, any variable but
  `"$WDS/…"`, `/tmp/`, `python3`, `~`, single quotes, globs), with broken lines as its
  positive control. It holds the README's three `WDS` forms to plugin.json's version and
  its install to plugin.json's repository, finds no `python3` or `/tmp/` in the skills'
  shell fences or the browser scripts, and holds every typescript-eslint install to a
  TypeScript 6.0 pin, as the repository's toolchain has. Against `v3.2.1`, 5 fail (24
  subtests); the control and the inherited quick start pass on both.
  CodeRabbit's review of #35 added two: the fence reader closed a fence on any ``` line
  and did not read `~~~` fences (`test_fences_pair_as_commonmark_pairs_them`), and an
  install continued over lines was never checked for its pin
  (`test_an_install_split_over_lines_is_still_read`). Both fail on `3121d61`.

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
