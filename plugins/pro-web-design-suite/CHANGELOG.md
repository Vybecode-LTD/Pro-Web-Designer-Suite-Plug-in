# Changelog

## 4.0.2 — unreleased

### Changed

- **The listing icon has a name of its own,** and `plugin.json`'s `icon` field names it. Anthropic's
  directory held 4.0.1 for review as "an image the plugin's code could run": a reference whose code
  span said "label + icon" matched the icon by its file name. The image is the same, and the listing
  keeps the icon it took at submission.

### Release builder (development repository)

- `tooling/release/build.py` reads the icon from `plugin.json`'s `icon`, and refuses a release when
  that names a file it doesn't carry. It holds any bundled image or font whose path, or whose file
  name without its extension as a word, appears in text that ships (a text SVG included), except
  `plugin.json` and the image links a Markdown file renders; image syntax quoted as code still counts. That is broader than the directory's own match, whose
  exact rule is unknown, so a distinctive name keeps it quiet. Regression test:
  `test_release_build.TheDirectoryChecks.test_the_shipped_plugin_has_no_findings`, which fails on
  4.0.1, with the controls in `test_an_image_named_outside_an_image_link_is_held` and
  `ReleaseBuild.test_plugin_json_names_the_listing_icon`.

## 4.0.1 — 2026-10-25

An icon for the plugin's listing in Anthropic's directory, before it is submitted there. No
skill, command, hook, script or MCP tool changes.

### Added

- **The listing icon:** a 1024-pixel square PNG beside `plugin.json`, a four-by-four grid of
  tokens stepping through a lightness ramp, with one accent, in VybeCode's colours. The
  directory reads a plugin's icon once, the first time the plugin is saved or submitted in its
  developer portal, and 4.0.0 had none (`claude plugin validate` warns `ICON_MISSING`, Claude
  Code 2.1.309).

### Release builder (development repository)

- `tooling/release/build.py` refuses a release whose icon the directory would not take: not a
  whole PNG (its image data, its end, every chunk's CRC), not square, under 512 or over 2048 pixels a side, or 2,000,000 bytes or more. It
  warns when there is none. It also prints a directory hold when a script names a bundled image
  or font, or a Markdown file quotes its path as code (in a span, or a fence of backticks or
  tildes), which the pre-submission checklist holds for a reviewer (re-read 2026-10-25). Regression test: `test_release_build.TheListingIcon`, which fails on
  4.0.0, with the builder's controls in `ReleaseBuild` and `TheDirectoryChecks`.

## 4.0.0 — 2026-10-24

Phase 6b. 4.0.0 is a major release because Part 5 of the ESLint config moves to another
Tailwind lint plugin (decision D4): a project that copied Part 5 must copy it again. It also
renames the plugin.

### Renamed

- **The plugin is Pro Web Design Suite, `pro-web-design-suite`** (the owner, 2026-10-19). It was
  `web-design-suite`, a name made only of generic words, which Anthropic's directory holds for
  review and which is hard to search for. The id is the prefix of every command
  (`/pro-web-design-suite:gate`, `/pro-web-design-suite:new-system`...), of the MCP tools
  (`mcp__plugin_pro-web-design-suite_gates__*`) and of the subagents
  (`pro-web-design-suite:design-critic`); `displayName` is "Pro Web Design Suite". Both
  marketplace files carry `"renames": {"web-design-suite": "pro-web-design-suite"}`. When Claude Code
  updates the marketplace it moves the enabled plugin to the new name, but **the marketplace keeps
  the name it was added under**, so an install from this repository becomes
  `pro-web-design-suite@web-design-suite`. Claude Code then lists no installed plugin until the next
  session starts, which installs the renamed plugin by itself (2.1.309, R4's live check); 2.1.308's
  `/plugin update web-design-suite@web-design-suite` reported it not found. If `/plugin` still shows
  none, run `/plugin install pro-web-design-suite@web-design-suite` once. (`@pro-web-design-suite` names the
  distribution repository's marketplace, below, and is not found in yours.) A permission rule, hook or
  script that names an old command or tool must be edited. **What keeps the old id:** the files
  in your projects. `contract.json`'s schema `web-design-suite/contract/1`, the DTCG `$extensions` key
  `io.github.vybecode-ltd.web-design-suite`, `/install-gate`'s stamp and `.design-suite.json` read
  and write as before, so no project needs a change.
- **Install from the distribution repository**, `Vybecode-LTD/pro-web-design-suite`:
  `/plugin marketplace add Vybecode-LTD/pro-web-design-suite`, then
  `/plugin install pro-web-design-suite@pro-web-design-suite`. It holds the plugin at its root, as
  released, one commit and one tag per version, and Anthropic's directory reads it. The release
  zip and the distribution repository leave out the plugin's `tests/`, `evals/` and `tools/`
  (221 files where there were 477). They stay in the development repository,
  `Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`, which still works as a marketplace. The plugin
  folder now has a `.gitattributes`, so a clone on Windows checks every file out with LF.
- **Ready for Anthropic's directory.** The README opens with three prompts to try, which surfaces
  load which components (chat loads the skills only), and **what the plugin runs, sends and
  stores**. Everything runs locally and nothing is collected. The plugin connects only to addresses
  you give it: the browser gates load the pages and sitemaps you name, `crux_check.py` calls
  Google's CrUX API with your `CRUX_API_KEY`, and the Figma REST pull is a `curl` you run. `SECURITY.md` says how to report a security problem
  privately, and `plugin.json` has the directory's `documentationUrl`, `supportUrl` and
  `privacyPolicyUrl`.

### Added

- **MJML and React Email from the email tokens** (DL-B4, P41 part 3). The router sent "MJML" to
  email-template-system, which said nothing about it, and nothing reached React Email. The new
  `scripts/export_email_theme.py` writes `email-tokens.json` (or `.design-suite.json`'s
  `emailTokens`, or `--tokens`) in the form each framework reads:
  - **`--format mjml`**: an `<mjml><mj-head>` file to `mj-include` in a template's head, with
    `<mj-attributes>` (the defaults for `mj-all`, `mj-body`, `mj-section`, `mj-text`, `mj-button`,
    `mj-divider`, `mj-spacer` and `mj-table`, and an `mj-class` for each type role, text colour,
    surface, gap and inset), `<mj-breakpoint>`, the link colour inlined, the Word engine's
    `[if mso]` font rule, and an `<mj-style>` with the dark-mode and phone rules.
  - **`--format react-email`**: a TypeScript module (JavaScript for a `.js` or `.mjs` out) with
    `tokens`, `text`, `styles`, `spacers`, `classes`, `headCss`, and `withMso()`, which adds the
    `[if mso]` block React cannot render.

  Every class has a `wds-` name that the dark-mode and phone rules select. The gap and inset
  classes carry none, since MJML replaces a tag's `css-class` with an `mj-class`'s and a section
  would lose its dark rule; the phone gutter has a class of its own, `gutter`, which a section of
  another surface adds (`mj-class="sunken gutter"`), and a browser test measures it. A role the tokens lack is named (`--strict` fails on it), and a value
  that could end its attribute, declaration or comment is refused. Two starters,
  `assets/templates/mjml/product-announcement.mjml` and
  `assets/templates/react-email/product-announcement.tsx`, compile with MJML 5.4 and render with
  React Email 6.11 to HTML that passes `lint_email.py --strict`, and a browser test reads the dark
  and phone rules on both. email-workflow.md §11 covers the include MJML 5 ignores unless it is
  allowed, the classes, `withMso()`, React Email's `Preview` and its second `<title>`, the text
  part, and Maizzle, which is routed away: map its Tailwind theme by hand and lint what it builds.
  The router now also hears React Email, Maizzle and an `mj-` tag. The test toolchain gains
  `mjml` 5.4.1, `react` and `react-dom` 19.3.1 and `react-email` 6.11.3 (`tooling/main`).
- **Right-to-left email, and a label a translation lengthens** (DL-B5, P41 part 2). The skill had
  one line on direction. `assets/templates/product-announcement-rtl.html` is the announcement in
  Arabic: `lang` and `dir` on `<html>`, `dir="rtl"` on every table, the ghost tables included, so
  the Word engine lays the columns out right to left as every other client does, with the source
  in reading order (a browser test measures the columns). Alignment is mirrored, the VML label is
  sized for its text, and an English address is marked `dir="ltr"`. email-architecture.md §11
  says why: Gmail, Outlook.com and Yahoo replace `<body>` with a `<div>` and Outlook for Mac does
  not support it, so the direction lives on the tables, where caniemail tests it (`<body>` is a
  row of the matrix now). It covers what to mirror, mixed-direction text, a translated email's
  own `lang`, `<title>`, preheader, alt text and merge-tag fallbacks, and text that grows
  (W3C's 200–300% for short English strings, registered). `lint_email.py` gains two checks:
  `direction` (a right-to-left language without `dir="rtl"`, an outer table without it, both
  errors; a ghost table without it, a left alignment not mirrored, and `dir="rtl"` on a
  left-to-right language, warnings) and `vml` (a VML button label that looks wider than its
  shape, a warning).
- **`brief_to_log.py`, the message brief into the deck's decision log** (PS-C12, P43 part 3). The
  positioning a landing page was built on reached the review only if someone wrote it up again,
  and the brief's assumptions were never asked in the room. landing-page-conversion's
  `scripts/brief_to_log.py` carries a filled `MESSAGE_BRIEF.md` into client-presentation-builder's
  `DECISION_LOG.md`:
  - **The positioning** becomes a decision. The first answers the specificity test rewrote are
    the options it beat, and who it is not for is its cost.
  - **The claim** becomes a decision, with its supports' proofs as evidence.
  - **Each assumption and each UNKNOWN** becomes an open question.

  What the brief does not record stays a `<placeholder>`, which the deck lists as a gap.
  `--into LOG` adds the blocks under `## Decisions`, numbered after the log's own, and adds
  nothing on a second run. The brief, the log and the SKILL.md name it.
- **Page types beyond software, and the persuasion skills routing to each other** (PS-B4,
  PS-B6; P43 part 2). Every sequence and example was audio, AI or agency.
  - **New page types.** `page-architecture.md` §3 now sequences a B2B demo request for a buying
    committee, a gated lead magnet, a local booking, a donation and a paid-search page (message
    match), with three notes on reading them.
  - **Regulated claims** (§3.1). Health claims are checked against Regulation (EC) No 1924/2006
    Art. 10(1) and its GB text; UK financial promotions against FSMA 2000 s. 21 and FCA COBS
    4.2.1R. Each is flagged before any copy is written.
  - **Localised pages** (§3.2). W3C's expansion figures from IBM are registered: 200–300% for
    strings of up to 10 characters, about 130% over 70.
  - **Calls to action.** `copy-patterns.md` §4 gives each new page type its CTA and friction
    reducer.
  - **Routing.** landing-page-conversion now points to perf-budget-gate (LCP, CLS and INP measured
    in a browser), a11y-audit-runner (§7.1's checks) and design-critique-gate. The critique gate
    points to a11y-audit-runner, component-state-matrix and client-presentation-builder.
  - **SKILL.md budgets.** In landing, the message-hierarchy example in the SKILL.md now points to
    `worked-example.md` §2, which holds it. In the critique gate, the findings paragraph is
    shorter and keeps every rule.
- **`lint_claims.py`, the claims lint** (PS-C6, and PS-B6's claims layer; P43 part 1). No gate read
  what a page says. A countdown that restarts on every visit, a newsletter box ticked in advance,
  a stock count from `Math.random()` or an unsourced "47% faster" passed every one.
  landing-page-conversion's `scripts/lint_claims.py` reads markup (HTML, JSX, Vue, Svelte,
  Astro) and scripts for ten patterns:
  - **errors:** a marketing, consent or add-on box ticked in advance (`checked`, `checked=""`,
    `defaultChecked`, `checked={true}`, `:checked="true"`); a deadline counted from the page load,
    or a constant counted down on every visit; a count made with `Math.random()`.
  - **warnings, which are questions for a person:** "only 3 left" and "12 people are viewing";
    a percentage with no source beside it; a struck-through price; `autocomplete="off"` on a
    field the browser fills; a lazy first image; two filled calls to action in the hero; one
    destination under two labels.

  Warnings fail only under `--strict`. A pragma with a reason switches a rule off for a line or a
  file. `conversion-audit.md` §13 documents it, landing's Phase 6 runs it, and so does the
  critique gate's layer 1, through the new failure-catalog entry L1-4.
- **The UK and EU consumer law to flag for legal review, price tests and consent for tracking**
  (PS-B2, PS-B3, PS-B8, P42 part 2). Each is dated and written as what to flag, never as advice,
  and each date and figure was read at its source on 2026-10-21 and registered:
  - `conversion-audit.md` §11.1, the UK and EU rules a page meets:
    - the DMCC Act, in force since 6 April 2025, with CMA fines up to 10% of turnover or £300,000;
    - reviews: Schedule 20 and UCPD points 23b, 23c and Art. 7(6);
    - the total price, or how a part not yet knowable is worked out, as prominently (s. 230, the
      CMA's drip pricing), and VAT;
    - "was" prices: the EU's 30-day low for goods (not services or digital content), and no fixed
      UK period;
    - personalised prices: Art. 6(1)(ea), with no UK match;
    - the EU withdrawal button from 19 June 2026, where the sale carries a right of withdrawal;
    - the UK subscription rules, still draft, for contracts from 1 January 2027 if Parliament
      approves.
  - SKILL.md's ethics boundary declines drip pricing.
  - `conversion-audit.md` §9.1, price tests: test the packaging before the price, flag four
    things, and size the test on revenue per visitor, whose noise grows with the orders' spread
    (about twice the visitors when order values vary as much as their mean).
  - `conversion-audit.md` §8.1, consent for what the instrumentation list measures:
    - the EU: ePrivacy Art. 5(3), GDPR Arts. 4(11) and 7(3), and Planet49;
    - the UK: PECR's statistics exception since 5 February 2026, with its conditions, and the UK
      GDPR's duties it leaves in place;
    - masking what session recordings see;
    - the EDPB's cookie-banner findings: reject beside accept, nothing pre-ticked, and a legible
      reject.
- **The persuasive devices, held to WCAG 2.2** (PS-B1, P42 part 1). landing-page-conversion
  prescribed countdowns, carousels, sticky bars, modals, consent banners, multi-step signup and
  toasts, and never named the criterion each meets. `conversion-audit.md` §7.1 holds thirteen
  devices to their criteria at their levels (2.2.1 and 2.2.2 for timers and movement, 1.4.2 for an
  autoplaying demo, 2.4.11 for sticky bars and banners, 2.1.2 for modals, 1.4.13 for hover details,
  2.5.8 (with its exceptions) and 1.4.3 for a small pale decline, 3.3.7 for multi-step signup,
  3.3.8 for sign-in and the steps that authenticate, 4.1.3 for toasts), says
  what each asks, and names the check that decides it (`a11y_runtime`'s `obscured`, `taborder` and
  `hover`, axe's `no-autoplay-audio`, `target-size` and `color-contrast`, `a11y_static`'s
  `missing-autocomplete`) or a person, as a11y-audit-runner's coverage table says. It tells WCAG's
  24 by 24 CSS pixels (AA) apart from the suite's 44px `--tap-min`. The critique gate's layer 8
  holds the same devices (failure-catalog L8-6). WCAG's figures are registered at the W3C.
- **The runtime gate runs in Firefox and WebKit** (GT-B9, P35 part 2). `a11y_runtime.mjs --engine
  firefox|webkit` runs axe, the computed names and the real tab order in the build the locked
  Playwright pins (`npx playwright install firefox webkit`), or `--browser PATH`; the checks that
  difference screenshots, emulate forced colours, read closed shadow roots through the DevTools
  protocol or were calibrated in Chromium stay Chromium's, and the run names them
  (`checks-run-in-chromium-only`, a warning). Tab may pass over every link with no `tabindex` (WebKit's
  Windows and macOS builds, as Safari by default; not its Linux build): the run reads it from the
  sequence it drove, expects no such stop, and says so (`engine-skips-links`). `browser_common.mjs` gains
  `launchEngine()`. CI installs Firefox and WebKit on Linux (`test_runtime_engines`).
- **The runtime gate drives the checks the coverage table called drivable** (GT-B6, P35 part 1).
  `a11y_runtime.mjs` has four new checks, each skippable by name and counted by a budget key, and
  `reflow` reads clipped text:
  - `spacing` (1.4.12) injects WCAG's text spacing, `!important` and into every shadow root, and
    reports each box that now clips its text (an error) or lets it spill (a warning);
  - `obscured` (2.4.11) presses Tab from the top and Shift+Tab from the bottom and hit-tests each
    stop against the fixed and sticky elements over it, its own ancestors left out: entirely
    hidden is an error, partly hidden a warning (2.4.12 is AAA);
  - `hover` (1.4.13) takes each control whose `aria-describedby` names a node hidden at rest,
    hovers it (else focuses it), and asserts that the content persists, survives the pointer
    moving onto it, and closes on Esc where it covers other text and reports no input error;
  - `motion` opens the page with and without `prefers-reduced-motion: reduce`, logs every
    animation as it starts, scrolls to the end, and reports motion the preference did not reduce,
    text it left hidden, and a busy loop it stopped: warnings, since this is the suite's policy
    (runtime-checks.md §6, no longer a procedure by hand) and 2.3.3 is AAA;
  - `reflow` reports text a box clips at 200% (1.4.4) or at 320px (1.4.10) that it did not clip at
    the page's own width.

  The budget keys are `text_spacing_failures`, `focus_obscured`, `hover_content_failures`,
  `motion_not_reduced`, `motion_content_hidden` and `motion_busy_stopped`. In automation-coverage.md §3, 1.4.12, 1.4.13
  and 2.4.11 now name the check that runs them. Every check has a page that fails it and one that
  passes, run in the browser (`test_runtime_wcag_checks`).
- **The scaffold writes Svelte** (DL-B3, P37 part 6). `scaffold_ui.py --framework svelte` writes
  the same kit and screens as Svelte 5 components: `<script lang="ts">` with `$props()`,
  callbacks as props as React's are, snippets for children (`{@render children()}`, the state
  block's `action`), and each CSS Module's rules in the component's `<style>` inside
  `@layer components`. Each control and screen holds only the rules for the classes its markup
  uses, since Svelte drops, with a warning, a rule nothing can match; the list's rules for the
  states it does not render yet wait under one `svelte-ignore`, and the loading state reaches its
  skeletons with `:global(*)`. `style:` sets only the skeleton's custom properties. The form's
  summary takes focus once per failed attempt through an `$effect`. The tests compile every
  component for the client and the server with `svelte` 5.57.2 with no warning, render the form on
  the server to read its ids, and run it in jsdom 29.1.1 (both now pinned in `tooling/main`) to
  drive the focus, with #64's count-only effect as the control that fails. content-model-to-ui's
  description now says React, Vue or Svelte.
- **The scaffold writes Vue** (DL-B3, P37 part 5). content-model-to-ui wrote React 19 only.
  `scaffold_ui.py --framework vue` writes the kit and each entity's list, detail, form and six
  states as Vue 3.5 single-file components: `<script setup lang="ts">`, React's props as
  `defineProps`, its callbacks as `defineEmits`, a `v-model` on each control, `<slot />` for
  `children`, and each CSS Module's rules in a `<style scoped>` block inside `@layer components`
  (the seven controls share `ui/Control/Control.css` through `<style scoped src>`). A root's class
  is the component's name, never `.root`, because Vue puts a parent's scope on a child's root
  element too. The form keeps React's three rules: its summary takes focus once per failed
  attempt (a `flush: 'post'` watcher on a `useTemplateRef`) and never for a later blur. The types,
  the fields, `lib/`, `server/` and `db/` are the React scaffold's files; the Tailwind stack works
  as it does for React; `--server-actions` stays React's (exit 2 with Vue). The tests compile every
  component with the real compiler (`vue` 3.5.44, now pinned in `tooling/main`), render the form
  on the server to read the ids its aria attributes name, and drive its focus through the runtime,
  each with a control that fails; the output passes the audit (`--strict`) and `a11y_static`.
- **`a11y_static.py` reads Vue's `v-bind="$attrs"` as a spread** (P37 part 5), as it reads JSX's
  `{...rest}`: the object may supply the label, the `alt` or the name, so a control with one is no
  longer "unlabelled".
- **The scaffold's forms post to Next.js server actions** (DL-B3, P37 part 4). content-model-to-ui
  wrote client-side React forms only. `scaffold_ui.py --server-actions` writes each form as a
  Client Component whose `<form action>` posts its FormData to `server/<table>.actions.ts`, a
  `'use server'` module with `create<Entity>` and `update<Entity>` (the row's key bound, as
  Next.js's forms guide shows); `<Entity>ActionForm.tsx` holds each result in React 19's
  `useActionState`, and the Save button takes its pending state from `useFormStatus`. Each
  action reads the FormData by the column's type (a number, a toggle's `on`, an array's
  `getAll()`, an empty field left out or null), validates it with the generated zod schema,
  returns the schema's first message per field, and writes through `lib/supabase.server.ts`,
  Supabase's own `createServerClient` for Next.js, so it runs as the signed-in user and the
  policies apply; `lib/supabase.ts` reads `NEXT_PUBLIC_` variables. Every control is named,
  the toggles too, since an unnamed control is not posted. Without the flag the scaffold is
  unchanged. `test_scaffold.TheServerActions` runs the generated action in Node against
  stand-ins for Next.js, Supabase and the schema; both stacks parse and pass the audit and
  `a11y_static`.

- **Next.js App Router, Vue, Svelte and Astro** (SB-B6, P37 part 3). The triggers are generic
  ("build me a site"), but the references taught plain CSS, CSS Modules and Tailwind only.
  web-design-studio's `stack-frameworks.md` gives each stack its global entry (the root layout,
  `main.ts`, `+layout.svelte`, a layout's frontmatter), where the layer order is stated so a
  component's styles cannot name `components` first (inlined in Vite's `index.html` and
  SvelteKit's `app.html`), how each compiler's scoping meets the layer order (Vue's
  `[data-v-…]`, Svelte's `.svelte-…` then `:where()`, Astro's three `scopedStyleStrategy`
  values, each compiled from the fixtures), Vue's `v-bind()` and Astro's `define:vars` as Law
  4's exception, SvelteKit's starter `style="display: contents"` moved to a class, the
  `components` globs per stack, and which gate reads which file. Every framework fact is quoted
  from its source with the URL. N49 is decided: a template is the audit's, since the ESLint
  config's rules are written against JSX and a Vue or Svelte template is a syntax tree they
  never visit. `tests/fixtures/stacks` holds a project per stack, on which the audit,
  `a11y_static` and the census run clean and find what is planted in each stack's own place
  (`test_stacks`).

- **stylelint reads SCSS** (D3, P37 part 2). The config linted `.css` files only, so a `.scss`
  file had the audit alone. An override (Part 6) now reads every `.scss` file through
  `postcss-scss` with `stylelint-config-standard-scss` 17, restates the config's own rules over
  it, and reads a Sass variable in a value as a token, as the audit does (`padding: $gap` passes,
  `padding: $gap 5%` does not). The component and token file classes name their `.scss` files
  (`**/components/**/*.scss`, `**/*.module.scss`, `**/components.scss`, `**/tokens.scss`…), in
  the spec and in both gates (the audit and the census took `components.css` only); a theme file's bindings stay CSS, which Tailwind reads. A new rule,
  `design/sass-variable-literal`, refuses what the audit's `sass-literal` refuses: a Sass
  variable that holds a length, a colour, a duration or an easing curve outside a token file,
  a map's included, with a breakpoint and a `@function`'s local left alone. The spec's
  `sass.variables` names both gates; `sass.definitions` (unlayered Sass) stays the audit's,
  since no stylelint rule reads unlayered CSS. A CSS-only project installs nothing new:
  stylelint loads the two packages only for a `.scss` file. The pre-commit hook's stylelint
  list took `\.css$` only, so a staged `.scss` file skipped it (Codex on #167); it takes
  `.scss` too. `test_real_tools.StylelintConfig` (every stylelint example of the spec and every
  starter stylesheet as SCSS draws the rules it draws as CSS; an SCSS component with nesting,
  `@use`, a map, a mixin and `@each` passes both gates, and fails both on each literal),
  `test_precommit_hook.PreCommitHook.test_a_staged_scss_file_reaches_stylelint`,
  `test_recipes.DependencyFacts.test_the_scss_packages_are_the_majors_stylelint_17_takes`.

- **The gates that open a URL reach a client-rendered or signed-in page** (P34 part 1;
  GT-B1, GT-B2). Each ran one `goto(…, 'load')`, so a client-rendered page was audited as
  its empty shell, and a signed-in page as its sign-in: both passed, with almost nothing on
  them. `browser_common.mjs` gives `a11y_runtime.mjs` and `critique_snapshots.mjs` four
  options, run in every context they open (the forced-colours pass and all six captures
  included):
  - `--wait-for SEL`: wait up to 30 s for `SEL` to be visible;
  - `--steps FILE`: a JSON list of `click`, `fill` (a `value`, or `env` naming a
    variable, so a password stays out of the file), `press`, `goto` and `wait-for`;
  - `--storage-state FILE`: a session, Playwright's `storageState`;
  - `--header "Name: V"`: sent to the page's own origin only, never to a third party,
    with `V` read from the environment when it is `env:NAME`.

  `measure_vitals.mjs` takes `--wait-for` and `--storage-state`, and refuses `--steps`
  and `--header`: steps would run in the load it measures, and a header needs request
  routing, which turns off the HTTP cache. Every option is read before a browser starts,
  each mistake named (exit 2). A step that fails, a wait that never ends, or an HTTP
  error status exits 2 too: vitals and the critique used to measure and capture a 401
  page as if it were the page. a11y-audit-runner's `references/scripts.md` gives the
  steps' format. `test_runtime_reach`, `test_json_guards`.
- **The runtime checks read through shadow roots** (P34 part 2; GT-B3). The names,
  tab-order, focus, contrast, keymap and reflow checks used `querySelectorAll` and a
  `TreeWalker`, which stop at a shadow root, so a web-component library's controls were
  checked by axe alone. `browser_common.mjs`' `DEEP_DOM` walks the composed tree in the
  order the browser renders and tabs through it, a slot standing for what is assigned to
  it:
  - every open root, and every closed one: a script's, kept by a wrapped `attachShadow`
    that runs before the page's own scripts, and the parser's
    (`<template shadowrootmode="closed">`), handed over by `keepClosedRoots()` through
    Chromium's DevTools protocol; a closed root is shown to axe for the length of its run;
  - focus inside a root is followed to the element itself, and `blur()` reaches it; a
    host whose root delegates focus is not a stop of its own (Codex on #165);
  - a background is composited up through slots and hosts, so white text slotted onto a
    dark band the shadow tree paints is no longer measured on the white page;
  - a path names an element host by host, `main > x-card >> button.icon`, which a
    keymap's selectors take too (Playwright reads it through open roots).

  The report's `shadowRoots` counts the roots read, and a closed root no check could
  read is a `closed-shadow-roots-unread` warning, never a silent pass.
  `critique_snapshots.mjs` samples text through the same roots, after its captures.
  `test_runtime_shadow`.
- **Several pages and viewports in one run** (P34 part 3; GT-B4). Each run covered one
  URL, and a11y ran only at 1280x900, where a phone's menu button and its target size
  are hidden, while the report template spoke of "all 14 templates".
  - `--urls FILE|URL` in `a11y_runtime.mjs` and `measure_vitals.mjs`: a file of URLs, one
    a line; a JSON list of URLs, or of `{"url", "pageType"}`, each page measured against
    its own type's perf budget; or a `sitemap.xml` (a sitemap index is refused), from a
    file or an http(s) URL. `--max-urls N` (default 50) caps it, and the pages past the
    cap are counted in the report.
  - `--viewports 390x844,1280x900` in `a11y_runtime.mjs`, with `--urls` or one page.
  - Each run is the script on one page at one size, in a process of its own
    (`browser_common.mjs`' `runEach()`), one after another, so no state crosses pages and
    no two loads share the machine. The report holds a row for each run, the errors or
    breaches of each failing one and every run's whole report in `--json`; the exit is
    the worst run's, so a page that does not load is never outweighed. `test_runtime_urls`.
- **`tw_probe.mjs` and `/tw-probe`** (P36 part 2; SB-C3). web-design-studio's new
  script compiles a Tailwind v4 project's entry stylesheet with the project's own
  tailwindcss and checks what it generates. Tailwind writes no CSS for a class it does not
  know, and says nothing, so "`--*: initial` removed `p-4`" was a claim nobody saw fail.
  - **Roles:** every variable an `@theme` block declares in one of Tailwind's utility
    namespaces (tailwindcss.com's table: `--color-*`, `--spacing-*`, `--breakpoint-*`,
    `--container-*` and the rest) must give its class.
  - **Stock:** none of a sample of Tailwind's defaults may generate, unless the theme
    declares that name itself. A failure names what survived: a kept `--spacing` alone
    brings `p-4`, `w-4` and `leading-7` back.
  - **Classes you name** are reported, and `--expect` and `--refuse` hold them.
  - It exits 1 on a failure and 2 when it cannot run. The stylesheets are read in cascade
    order, each after its imports; Tailwind's own files are left out, and a class the
    stylesheet defines itself (`.stack`) is not counted as Tailwind's. On Tailwind 3 it
    exits 2 and points at Part 5's `tailwindConfig` line.
  - `/pro-web-design-suite:tw-probe` runs it from the project's root and explains each
    failure: the sixteenth command. stack-tailwind.md §2.9 teaches it.
  - Tests: `test_tw_probe.TheProbe` runs it on the starter's own Tailwind wiring and on
    the ways a project breaks it; `test_commands.TheChains` runs the command's step.

- **Tailwind v4's variants after `--*: initial`** (P36 part 3; SB-B5), in
  stack-tailwind.md §2.10, each compiled with Tailwind 4.3.3 against the starter's wiring:
  - **Container queries:** `@md:` reads `--container-*`, which §2.5 keeps out, so it
    generates nothing. A container query is a `@custom-variant` with a literal condition,
    named by its role (`cq-wide`, and `cq-card-wide` for a named `@container/card`), which
    also adds no `max-w-*` class. theme.css's note says so.
  - **`motion-reduce:`** is for what the motion tokens cannot stop, a transform at rest or
    an autoplaying animation: the `motion-*` classes already go to 1ms.
  - **`forced-colors:`, `starting:` (`@starting-style`) and `not-*`**, with what each is
    for; `not-[…]` stays refused as an arbitrary selector.
  - **`@reference`** in a CSS module or a Vue, Svelte or Astro `<style>`: without it,
    `@variant dark` compiles with no error against Tailwind's own
    `prefers-color-scheme`, not the project's `[data-theme="dark"]`; `@import` copies the
    whole entry (about 36 KB of the starter's CSS) into each module.
  - **`@source inline()`** for classes no source names (a CMS field), and
    **`@source not inline()`** for classes that must never generate.
  - `test_tw_probe.TheVariantsTheReferenceTeaches` compiles the section's marked block as
    written and checks each claim.

- **The migration counts Tailwind v4's numeric classes** (P36 part 4; LC-B5). In v4,
  `p-4` is `calc(var(--spacing) * 4)`, so while the theme keeps `--spacing` every multiple
  is a class, and the census counted none: a migration sized from it came in short.
  - **The census** reads `--spacing` from each entry that imports `tailwindcss`, through
    its imports in order, as Tailwind builds the theme. The stock value comes from the
    installed `theme.css`, else `0.25rem`. `--*: initial`, `--spacing-*: initial` and
    `--spacing: initial` clear it, and a `default` block never overrides the project's.
  - **The classes:** padding, margin, gap, `space-*`, inset, width, height, `size-*` and
    `leading-*`, each counted at N × `--spacing` with its variants, `!`, its negative
    where Tailwind has one (`-mt-4`, never `-p-4`) and the project's `prefix(tw)`. A
    number counts only as Tailwind 4.3.3 takes it: `p-2.25` yes, `p-2.50` and `p-0.3` no.
    Entries that disagree, a `--spacing` that is no length, or an import it cannot read
    (a package not installed: its theme can set `--spacing`) count none and say why.
  - **The proposal** maps each to its role as it maps `p-[13px]` (`p-4` to `p-well`,
    `-mt-4` to `-mt-grouped`), and reports `leading-6` for its `--type-*` role. **The
    codemod** rewrites only the utility, matched whole: `md:p-4` becomes `md:p-well`, and
    `p-4.5`, `-p-4` and `sp-4` are never read as `p-4`. In a script, both read a numeric
    class only where classes go: a class attribute, a `className={…}` expression and a
    class helper's arguments (`cn()`, `clsx()`, `cva()`…), since a bare `"p-4"` may be
    any data (Codex on #129).
  - framework-migrations.md §5 gives **Move 1 in v4's form**: named `--spacing-*` keys
    beside `--spacing` replace nothing, `--*: initial` does, the census runs before it, and
    `tw_probe --refuse p-4` checks it.
  - Tests: `test_token_migration.TheV4SpacingCensus`; `test_tw_probe.TheMigrationsMoveOne`
    compiles §5's two blocks and runs its command.

### Fixed

- **What R4's live check found in real projects** (`dev plans/web-design-suite-4.0.0-live-check.md`),
  each code fix with a test that fails on 3.6.0 (the description below is text a session reads, with no test):
  - **A web font's `@import url()` stopped the Tailwind v4 census and `/tw-probe`** (react-movies).
    A quoted Google Fonts URL holds a `;` (`wght@0,9..40,100..1000;1,…`): the census's import
    pattern stopped there, read `url(` as a package not installed and withheld every numeric class;
    `tw_probe.mjs` looked for a package named by the URL and exited 2. A URL is the browser's, as
    Tailwind leaves it.
  - **The router heard no skill for "the design-system lint"** (a Vite + Tailwind 4 app), so the
    session searched the disk and copied the lint block from an older install. A hyphenated
    design-system and design-token, the design lint, rules, laws and audit now reach
    web-design-studio.
  - **`a11y_static.py` told a sign-up form's password to take `current-password`** (the Vue
    RealWorld app); the type alone cannot say, so the finding names `new-password` too. And it read
    an XSS sample in a `.ts` fixture's string as an image with no alt: a TypeScript file's markup is
    what markup is made from (lit's `html`/`svg` templates, an Angular `template:`, `innerHTML`),
    and a `.mts` or `.cts` file is audited too.
  - **a11y-audit-runner's description** names the text spacing, hover and motion checks and the
    three engines: a session asked for exactly those wrote its own Playwright script instead.
- **landing-page-conversion didn't load for a countdown banner** (the `no-fake-countdown` eval). The
  router named the skill for "pages that convert", and a session asked for a 15-minute countdown
  that restarts per visitor did the work its own way: once it built an honest timer without saying
  what it had declined, or why. The description now names offers, countdowns and urgency and says
  the skill declines dark patterns, and the router's hint says the same. A countdown, urgency or
  scarcity beside an offer, a sale, a price or a checkout, a dark pattern, and a fake deadline now
  reach the skill without a page's name. With the skill loaded, runs still built the honest timer
  and named the deception only as a condition ("only use it if the offer really ends"): "name it in
  one line and move on" read as permission. The boundary's first rule now counts building the
  honest version as a decline, and gives the reply's opening sentence: "I didn't build [what was
  asked]: [the pattern] deceives because [why]." The eval passed 3 of 3, every judge agreeing.
- **Two false findings in `lint_email.py` on a compiler's markup** (DL-B4, P41 part 3). MJML's
  output had an error and a warning per column. A hidden preheader's colour was measured, and
  MJML's is white on any canvas: the contrast check now skips a preheader, as the dark check did.
  A `font-size:0` wrapper round inline-block columns, MJML's and the fluid-hybrid layout's, was
  read as text at 0px: the type check now measures the text an element sizes itself, not the
  text of a child that sets its own size. And `audit_design.py`, which leaves HTML email to
  `lint_email.py`, now leaves a React Email template too (a file that imports `react-email` or
  `@react-email/*`; a declaration, not a comment or a string): it failed the starter's inline image
  size under L4, in the gate hook as well. The generated theme is marked `@generated`, which the
  audit already leaves alone; email-workflow.md §11 says to keep `emails/` out of ESLint's design
  config, whose files are the project's `ignores`.
- **The email client matrix and the linter's client lists are caniemail's data** (DL-C9, P41
  part 1). A15 corrected the matrix from caniemail's pages by hand in 3.2.0, and the copies drifted
  again: against caniemail's data of 2026-09-16, some 60 cells differed from its latest results
  (Thunderbird's `@media` and custom properties, Gmail's custom properties, Outlook for Mac's `<svg>`
  and web fonts among them), and `lint_email.py` said no client supports `gap`, that Gmail drops
  `object-fit` and that Samsung Email and Thunderbird have no custom properties, where caniemail
  records the opposite. Its errors for `float`, `box-shadow` and eight more traced to no row of the
  matrix. Now email-client-matrix.md §2 is a table written from caniemail's data: 34 features, each
  linked to its page with the date it was tested, and caniemail's notes on each cell under it. The
  linter names the clients each feature fails in from the same data, with the test date. A
  maintainer refreshes both with `tools/sync_caniemail.py --data` (pinned in
  `tests/fixtures/caniemail.json`, MIT licence), so a client that changes is a diff; `--check` runs
  in `check.py`. The table has no column for the new Outlook for Windows, which caniemail does not
  test, and the matrix's own notes say what the cells cannot.
- **`perf_audit` on a bundled site** (P56 part 1, N50, found building webdesignersuite.com with
  `/new-system` and `/install-gate`). `css-import` failed the starter's own `index.css` under
  `--src`, though Vite inlines its `@import`s, so a project fresh from the two commands failed its
  first CI run with seven errors: the rule now reads shipped stylesheets only, and a built file
  that keeps an `@import` still fails. `font-not-preloaded` matched a preload by the source's file
  name, so preloading the bundler's hashed copy (`name.HASH.woff2`, `name-HASH.woff2`) never
  counted; it does now, and a weight's name (`Inter-SemiBold`) is never read as a hash. And
  `missing-preconnect` took the page's own canonical URL for a third-party origin: the canonical's
  host is first-party, and only a `<link>` that fetches something adds an origin (`alternate` and
  `me` load nothing). A budget's `third_party.origins` count can drop by those links.
- **The starter's code blocks and reflow** (P56 part 2, N50, found on the same site). A
  `.page-grid` item holding a long `<pre>` set the whole page's width, 721px at 320px (a WCAG
  1.4.10 failure): `.page-grid > *` takes `min-inline-size: 0`, so the line scrolls in its own box.
  Every code block was set in Courier, because the UA's `code { font-family: monospace }` beat
  inheritance inside `<pre>`: `pre > code` inherits the block's font, `--font-mono`. And on the
  dark canvas a `<pre>` drew no box, `--bg-sunken` being the canvas there: it has a hairline
  `--border-subtle` edge. A project made from the starter before 4.0.0 can copy the three rules.
- **`/install-gate`'s workflow checks the role pairs** (P56 part 3, N50). It vendored
  `check_roles.py` and never ran it, so a role pair that lost its contrast passed CI. The `gates`
  and `windows` jobs run it on the `tokens.css` files the config's `tokens` names, or on
  `src/styles/tokens.css`; with neither, the command says the pairs go unchecked. `check_roles.py`
  takes several files, read in order as one system, as the config reader merges them (Codex on #187). The command runs the check once before it writes the step (CodeRabbit on #187): a configured file that does not exist stops the install, a system `check_roles.py` cannot read as the role vocabulary gets no step and the reason, and pairs that fail now get the step and a warning. Run
  `/install-gate` again to upgrade a project's workflow.
- **`check_roles` reads a scope's blocks as the cascade does** (P57, N51, CodeRabbit on #187). It
  applied every `:root` block before every `[data-theme="dark"]` block, whatever order they were
  written in, so a `:root` that set a role again below the dark block passed on the dark theme's
  value while the page showed `:root`'s. The two selectors weigh the same, so the block written
  later wins, as in a browser; a heavier selector (`[data-theme="dark"] .inverse` over
  `.inverse`) wins whatever the order, and files given together are written in the order listed.
  A system that keeps `:root` first, as the starter does, reads as before; one that put it last
  may now fail pairs it passed. Cascade layers are still read as one: a block in `@layer` counts
  like an unlayered one.
- **The scaffold's controls keep arrays, nulls and the required state** (review of #176, React and
  Vue alike). A multiple select bound `String(value)` and sent one option; it binds the array and
  sends the selected options. An emptied number input sent `NaN`; it sends `null`. `tag-input` and
  `json-editor` went through a text box's `String()`, which made tags comma text and JSON
  `[object Object]`: each is now a marked stub, since the text being typed is not yet a value, and
  a JSON cell shows `JSON.stringify`. A required radio group said so only with its hidden
  asterisk; the group carries `aria-required` and each radio `required`. And a Vue state's copy
  from the answers that began with `:` was written as a directive.
- **`a11y_static` read a framework's document shell as a whole page** (P37 part 3). A Next.js
  root layout (`<body>{children}</body>`), a Vite `index.html` (`<div id="app">`), SvelteKit's
  `app.html` (`%sveltekit.body%`) and an Astro layout (`<slot />`) each got `no-main-landmark`,
  and the first two `no-title`, though the page's `<main>` and title come through the outlet.
  `shell_outlets()` leaves `<main>` to the pages when the body holds a default slot, the
  children's expression (`{children}`, `{@render children()}`, not a page's own `{'hello'}`),
  SvelteKit's placeholder or a module script's mount point (its `type` and `src` in either order), and the title when the
  head holds `%sveltekit.head%` or the file is a Next.js `layout` or exports `metadata` or
  `generateMetadata`. A document with none of these still needs both, an entity in its text
  included. `test_stacks.TheShellsRenderTheirPagesElsewhere`.

- **`a11y_static` read a `<slot>` as no content** (P37 part 3). `<a href="/x"><slot /></a>` in a
  Vue or Astro component had no accessible name, where a component's content is already "cannot
  tell". A `<slot>` now counts as content it cannot see. `test_stacks.TheShellsRenderTheirPagesElsewhere.test_a_slot_names_the_link_it_fills`.

- **The census counted a shadow token as a shadow** (P37 part 3). It blanks `var(--name` before
  its whole-value shadow check, so `box-shadow: var(--shadow-xs)` left `)` as a shadow literal,
  three of them in the starter's own `base.css` and `layout.css`; a fallback became `, 0 1px 2px
  #000)`. A reference alone is no literal now, and a fallback's or a second layer's values are
  read part by part. `test_stacks.TheCensusReadsAShadowToken`.

- **The audit read no bound inline style** (N48, P37 part 1). Its template reader wanted
  whitespace before `style=`, so Vue's `:style="{ color: '#fff' }"` passed, though Law 4
  fails the same declaration as `style=""` or JSX's `style={{…}}`; so did `v-bind:style`,
  Svelte's `style:color` directive, and Angular's `[style.color]`, `[style.width.px]`,
  `[style]`, `[ngStyle]` and `[attr.style]`. `audit_design.py` now reads each start tag's
  attributes (`tag_attributes()`, past quoted and braced values) and each bound style's
  declarations (`bound_styles()`): every object the expression can evaluate to (either arm
  of a ternary, an array's items, a spread's, not a call's argument), a string written out as
  a whole arm of a condition (`on ? '12px' : gap`, `gap ?? '12px'`), each string as
  `style=""`, and one property at a time, with Angular's unit joined to its number. A
  visual property is L4, and a custom property's written-out design literal or Tier-1
  primitive is L1 or L6, as in JSX. Commented-out markup is blanked first, as the census
  blanks it, so neither reads an element that never renders. The migration census (`extract_literals.py`) skipped
  these as expressions; it carries the same reader verbatim and counts each written-out
  value as an inline style, left to hand work. The spec's `inline_styles.bound` holds
  every form; ESLint parses no `.vue`, `.svelte` or Angular template (N49, decided in P37 part 3:
  the templates are the audit's).
  `test_audit_design.TheAuditReadsBoundStyles`,
  `test_token_migration.TheCensusReadsEveryStyleSource.test_bound_styles_are_inline_styles`.

- **The migration matched a colour to a role by ΔE alone** (N40, from R3.6's live
  check). `cluster_values.py` sent the grey `#6b7280` to `--fg-warning`: its little
  chroma kept it off the neutral steps, and the nearest of the rest was a status colour of
  the opposite hue. Slate greys landed on the accent and info ramps, and green and amber
  tints on `--accent-50`. A colour's family now comes first:
  - a neutral (chroma under half of what sRGB holds at its lightness and hue) lands only
    on the neutral ramp;
  - any other colour lands only on a step within 30° of its hue, so a status hue lands on
    its status;
  - ΔE ranks within the family;
  - the ramps are built by the same reading: a muted grey (`#5f8890`, C 0.047) seeds no
    accent and gives the neutrals their hue (Codex on #129).

  `test_token_migration.ColoursKeepTheirFamily` holds 23 greys, tints and status colours
  to their families.
- **The codemod rewrote classes inside longer ones** (C1, the 2026-10-14 audit). An
  arbitrary value's rule had a right boundary only, so `p-[16px]` matched in
  `top-[16px]`, `-p-[16px]` and `sp-[16px]`, and `w-[16px]` in `min-w-[16px]`; when
  `gap-[16px]` had its own rule the two edits overlapped and the whole file was skipped.
  The match now has the census's left boundary too
  (`test_token_migration.TheCodemodRewritesOnlyWhatItMatched`).
- **The codemod and `deprecate` turned a file's line endings** (C2 and H1, the
  2026-10-14 audit). `apply_codemod --apply` read with universal newlines, so a CRLF file
  came back LF on every line, which the dry run never showed; `deprecate add --source`
  wrote the token file in the platform's newline, LF to CRLF on Windows and CRLF to LF
  elsewhere, and its ledger the same way. Each now reads and writes the bytes' own endings,
  and a marker takes the file's (`test_versioning.TheMarkerKeepsTheFilesLineEndings`). The
  dry run's diff is written as its bytes are, where Windows' stdout doubled a CRLF line's
  `\r` (Codex on #130).
- **The accessibility gate never read a rule inside `@layer`, `@media` or `@supports`**
  (H4, the 2026-10-14 audit). `a11y_static` split CSS at depth 0 only, so an at-rule's
  rules were pooled: any `box-shadow` beside an `outline: none` counted as its ring, and
  the focus test read the at-rule's prelude. The starter's `base.css` is all `@layer
  base`, so a reset planted there passed. Each rule is now read on its own at any depth,
  a nested `&` rule against its parent (a comma inside `:is()` is not the list's,
  CodeRabbit on #132), and a condition nested in a rule is read with the rule's own
  declarations (Codex on #132). Reading them found two more: a comment's newlines
  were blanked, so every line after a multi-line comment was misnumbered and its ignore
  comment missed; and a focus rule that moves a skip link on-screen (`translate: 0 0`)
  was called invisible (`test_content_and_a11y.A11yStaticReadsNestedRules`).
- **The state matrix called a state covered that it never rendered** (H5). Only a
  pseudo-class at depth 0 got a mirror rule, so `.btn:is(:hover, :focus-visible)` got
  none, and `.chip { &:hover {…} }` mirrored as `&[data-force-state~="hover"]`, which
  matches nothing; the summary still said every state had a rule. States inside `:is()`
  and `:where()` are mirrored, an arm with no state made never to match
  (`.danger:not(*)`, Codex on #132), a nested rule is read with its parent, and a forced state
  is covered only when a mirror was written; a `:focus-within` ring covers the
  focus-visible cell, which carries it (CodeRabbit on #132)
  (`test_content_and_a11y.MatrixStates`,
  `test_browser_runtime.MatrixSeesStateChanges`).
- **The accessibility gate did not know Vue's or Angular's bindings** (H6). `<img
  :alt="d">` had no alt and a bound `aria-label` no label, so a Vue project with the hook
  was blocked on every bound attribute. `:x`, `v-bind:x`, `[x]` and `[attr.x]` are the
  attribute `x`, a string literal read as its text; `@click`, `v-on:click`, Svelte's
  `on:click` and `(click)` are click handlers, which a `<div>` must not carry alone
  (`test_content_and_a11y.A11yStaticReadsBoundAttributes`).
- **The hook's index mode ran without the project's config** (H7). `DESIGN_GATE_INDEX=1`
  audited a scratch tree of the staged files alone, so the audit read no token files and
  no baseline: a baselined finding refused the commit, and a project ramp's primitive
  passed. The tree now holds `.design-suite.json`, its baselines at their own paths (their
  keys are relative to them) and the default baselines; a token file the config names
  that is not staged is read from the working tree. A staged symlink is replaced in the
  scratch tree, never written through (CodeRabbit on #132)
  (`test_precommit_hook.PreCommitHook`).
- **The audit read a ternary in an inline custom property as a property** (H8). In
  `style={{ '--progress': open ? '1' : '0' }}`, the one inline style the spec allows, the
  quoted `'1' :` was taken for a key and refused. A style object's keys are its depth-0
  entries' now, in `{{ … } as CSSProperties}` a shorthand `{{ zIndex }}`, and a spread's own object literals
  (`...(on ? { zIndex: 3 } : {})`, Codex on #132) too, and a comment before a key in
  markup hides it no longer (CodeRabbit on #132)
  (`test_audit_design.JsxClassesAndCssInJs`).
- **`--reverse` left out a theme's value without a word** (H2, the 2026-10-14 audit). A
  `[data-theme="dark"]` alias to a token the file does not declare was dropped from the
  body with exit 0 and nothing said, so Figma showed the Light alias in Dark. It is
  reported now, the mode named, and the exit is 1
  (`test_figma_sync.ReverseReadsEveryTokenFormat`).
- **A UTF-8 BOM on `tokens.css` emptied the system** (H3). `extract_system`, `build_docs`
  and `diff_system` read it as plain UTF-8, so the first selector was `﻿:root`:
  every token was theme-only, the contract empty, and `diff_system` called the whole
  system removed and added (218 majors on the starter). They read the BOM now
  (`test_project_config.ABomOnTheTokenFile`).
- **The schema reader missed a migration's enum values** (H9). Only `CREATE TYPE` fed the
  enums, so a value `ALTER TYPE … ADD VALUE` added was refused by the scaffold's server
  draft and missing from the form. `ADD VALUE` (with `IF NOT EXISTS`, `BEFORE` and
  `AFTER`) and `RENAME VALUE` are replayed on an enum the files created, and a label's
  `''` is one apostrophe there and in `CREATE TYPE`, and its spaces are kept (Codex on
  #133)
  (`test_schema_sources.MigrationsThatDumpsRewrite`).
- **A table's tail ran into its last column** (H10). The column list ended at the
  statement's last `)`, so `PARTITION BY RANGE (created_at)`, `WITH (…)` or `INHERITS
  (…)` became part of the last column's default, and a trailing table CHECK was lost. The
  list ends at its own closing paren now, a paren inside a string or a `$$…$$` body
  skipped (Codex on #133)
  (`test_schema_sources.MigrationsThatDumpsRewrite`).
- **The migration's estimate left literals out, and counted rules that never fire** (H11,
  H12). `cluster_values.py` put a colour it could not parse (`oklch()`, `lab()`, `lch()`,
  `hwb()`, `color()`, `hsl(0.5turn …)`) and a `letter-spacing` in `px` in neither a rule
  nor a row, so the reconciliation no longer added up to the census. Each is a row to map
  by hand now. And `color: white` got a rule the codemod never applied, since a named
  colour was no colour slot to it, and a hex inside `color-mix()` was counted with a rule
  it could not apply. The codemod takes the census's named colours, and a `color-mix()`
  with a colour written out is one colour function, mapped by hand. A duration in a
  whole `transition` shorthand was counted at both its `--motion-*` pair and its Tier-1
  step; it counts at the one rule that rewrites it, and the codemod no longer refuses a
  mapping whose duration rules are all pairs (CodeRabbit on #135). What the
  reconciliation counts as mechanically replaceable is what `--apply` rewrites
  (`test_token_migration.TheProposalAccountsForTheCensus`).
- **A width never reached its width step** (H13). The proposal snapped a length to the 4px
  scale, which ends at 192px, before trying `--width-form`, `--width-content` and
  `--width-wide`, so `max-width: 1152px` was unmapped and every length past 195px read
  "Decide between 192px and 192px". A width meets the width steps first, and past the scale
  the advice says so. A height never does: a width rule's class is `width`, which the
  codemod gives only `width`, `min-width` and `max-width`, so a height added later keeps
  its value (Codex on #135)
  (`TheProposalAccountsForTheCensus.test_a_width_reaches_its_width_step`).
- **A project's ramp step the proposal could not read was rebuilt without a word** (found
  beside H11). A step in `hwb()`, or a translucent one, was built as if the project had
  not declared it. The report names each such step now
  (`test_project_config.ClusterValuesLandsOnTheProjectsRamps`).
- **Six scripts wrote to a Windows pipe in the ANSI code page** (H15). `check_roles.py`
  sent its verdict's dash as cp1252, and the five workflow commands' scripts had no UTF-8
  reconfigure either. The test that ran every script's `--help` could not see it, since no
  help holds a non-ASCII byte. Every entry script's `__main__` block is read for the
  reconfigure now, with a control that proves the scan fires, and the workflow commands
  are covered (`test_utf8_output`).
- **The Pydantic test skipped on every CI cell** (H15). The suite runs under `uv run
  --no-project`, which has no pydantic, so the scaffold's model never met Pydantic in CI.
  A step of its own runs that test with `pydantic>=2,<3`, and `WDS_REQUIRE_PYDANTIC` fails
  it there rather than skipping (`test_scaffold.TheServerSchemaMirrorsTheConstraints`).
- **An output could replace its own input** (the audit's V7, E9 and G4, and its class 5).
  `--out` equal to the input replaced a Figma export with its audit report, a published
  snapshot with its diff, an email's source with its build or its lint report, the
  findings with their critique, and an audited page with its JSON report, each with exit
  0. `build_presentation --emit-css DIR` wrote `DIR/tokens.css` over the project's own,
  and `cluster_values -o` could land its proposal on it too. One helper decides now,
  `refuse_overwrite()` in `project_config.py` and `refuseOverwrite()` in
  `browser_common.mjs`, and every writer whose output can be one of its inputs calls it
  before it writes anything: exit 2, the input untouched. It compares with the files read,
  not their spelling: a glob's matches, a folder's files, every file of a snapshot, the
  token files and budgets the config names, the screenshots, and a `file://` URL's page
  (Codex on #136). `figma_to_tokens` still writes
  over the project's `--tokens`, which is the Figma-to-code workflow
  (`test_out_guard`).
- **A JSON file of the wrong shape was a traceback, or was read as something else**
  (the audit's S1, S10, V8, G3, G11, G15, E13 and W6, and its class 6). A traceback
  exits 1, the gates' "it fired" code; worse, `check_roles` read a string `scopes` as
  letters, `critique_report` read `"is_taste": "false"` as true and made a major finding
  taste, and `measure_vitals.mjs` and `a11y_runtime.mjs` passed every page against a
  limit written as a string. Every loader checks the shape where it reads the file now,
  and exits 2 naming the file and the key (`defaults.bytes.css`, `rules[0].match`,
  `pair 0: min`):
  - the token readers leave out a token or group whose `$type` is not a string, and
    name it; Node's reader leaves out the same ones. A `$deprecated` that is neither a
    string nor a boolean is named, and the token keeps its group's;
  - the deprecation ledger (`diff_system --deprecations`, `deprecate --ledger`), a
    `system.json` and the docs baseline (`build_docs`), a perf budget (`perf_audit`,
    `measure_vitals.mjs`, the same check in both), an a11y budget, the pairs file,
    the findings, the deck's perf and a11y evidence, the codemod's mapping, the census,
    the content model and its answers, a Figma styles file and the CrUX lab file;
  - `introspect_schema` names a JSON dump's `tables`, `columns`, `foreign_keys` or
    `enums` of the wrong type, with exit 1, its code for an input it cannot use;
  - a baseline of the wrong shape (`audit_design`, `a11y_static`, `perf_audit`) is read
    as an unreadable one, as before: named on stderr, and everything audited.

  `test_json_guards` feeds every loader `[]`, a string, a number and its own wrong keys,
  and fails when a script that reads JSON has no row.
- **A UTF-16 file read as garbage** (the audit's S8 and W7, and its class 4). PowerShell
  5.1's `>` writes UTF-16LE. The token readers decoded CSS as UTF-8 only, so such a
  `tokens.css` read as no tokens and every `var(--x)` was "unknown", in Python and in
  Node; `check_roles` gave a traceback. Every script now reads a project's text through
  `project_config.read_text()`, which finds the encoding as `json.detect_encoding()`
  does (a byte-order mark, else the zero bytes), or through a copy of it in the scripts
  that run on their own (`audit_design`, `a11y_static`, `check_roles`,
  `generate_matrix`). The codemod and `deprecate add --source` write a file back in the
  encoding they read it in, its mark and byte order included (`text_encoding()`); a
  UTF-16 file was skipped as unreadable by the one and a traceback in the other
  (`test_encodings`, which also fails on a script that reads with `encoding="utf-8"`).
- **What a script could not use was dropped without a word** (the audit's S2, V11, V12
  and M9, and its class 7):
  - `read_tokens()` and `read_deprecations()` threw away every problem `dtcg.tokens()`
    reported, so a resolver with sixteen of them read silently. `ProjectTokens` carries
    them as `problems`, and the five gates that read a project's tokens (`audit_design`,
    `diff_system`, `cluster_values`, `figma_audit`, `figma_to_tokens`) print each as a
    warning;
  - `figma_to_tokens --reverse` clamped a colour outside sRGB (`oklch(70% 0.3 150)`)
    with exit 0; it is now a `clamped` problem with the hex Figma gets, exit 1;
  - an input whose only tokens are unsupported said "contains no variables … pass
    `--shape`"; the message now lists what it held and could not give;
  - the codemod dropped a generated file with no skip row; it has one;
  - `diff_system` skipped a pair whose contrast it could not measure (a colour it
    cannot resolve or parse); a pair a changed token reaches is now a note.

  `test_diagnostics`, which also fails on a `_problems` or a `[0]` on `tokens()` or
  `normalise()` anywhere in the scripts.
- **A placeholder in angle brackets broke the command it sat in** (the audit's D4, G13
  and E14, and its class 9). `python -m scripts.audit_design <path> --json > audit.json`
  reads `<path>` as a redirection, in cmd.exe and in bash alike, and 45 commands in the
  skills, the references and the README were written so. A placeholder is now in
  capitals (`PATH`, `RUN_ID`, a colour quoted as `"FOCUS"`); a11y-audit-runner's hook
  recipe copies from `${CLAUDE_PLUGIN_ROOT}` instead of `<web-design-studio>`; and the
  email quick start, which was `mkdir -p`, `cp` and `cat` with a `\` continuation, is a
  copy step for Claude and three commands that paste into bash, PowerShell and cmd
  (`test_docs.PlaceholdersInCapitals`, which reads every shell fence and inline command
  in the skills, the references, the agents and the workflow commands, and the
  repository's live docs).
- **The router heard another domain's words as design work** (the audit's S3). "Deprecate
  the old JWT tokens" was sent to design-system-versioning, "migrate the session tokens
  to Redis" to design-token-migration, "token reference docs for the OAuth API" to
  design-system-docs, "critique my essay" to design-critique-gate, "every state in the
  US" to component-state-matrix and "the lighthouse keeper" to perf-budget-gate. Each
  shared word now routes only beside one of the skill's own (a colour, `tokens.css`, a
  page, a component, a score), as "a patch release?" has since #97
  (`test_hooks.TheRouter`).
- **`rgb()` and `hsl()` lost a fourth comma argument** (the audit's S4).
  `rgb(255, 0, 0, 0.5)` and `hsl(0, 100%, 50%, 0.5)`, the legacy form under the names
  CSS Color 4 made aliases of `rgba()` and `hsla()`, were left out of a DTCG document as
  unsupported; they are written with their alpha (`test_dtcg.TheWriter`).
- **The Python and Node token readers disagreed on three forms, and the gate tools read
  any path** (the audit's S5, S6, S7 and S9):
  - a reference with spaces round it (`" {brand.500} "`) was a reference in Python and
    a literal in Node. Node takes it as Python does;
  - Python read digits that are not ASCII (`"٥"`) as numbers: in a dimension, a colour
    component or alpha, a Tokens Studio number and its math. They are left out, or left
    as written, as Node leaves them;
  - Python read a colour's `components` given as an object by its keys (`{"1": 0, "0":
    0, "0.5": 0}` became `#ff0080`). It is refused, as Node refuses it;
  - the MCP server ran a gate on any path Claude passed, `..`, an absolute path or a
    link out of the project included, and a finding's snippet returned the file's
    lines. A path argument must now be inside the project, compared by real path
    walked a part at a time (a link is followed before a later `..`), and so must
    every link under a folder the gate will walk, the project included when no path is
    given (an error `-32602` names it); the files `.design-suite.json` names are still
    read wherever they are.

  `test_project_config.TheNodeReaderAgrees`, `test_mcp.TheGates`.
- **The accessibility gates misread four things, and the coverage table claimed more than
  they run** (the audit's G1, G2, G5, G6 and G7):
  - `aria-hidden-focusable` read only an element's direct children, and counted those
    that take no focus. It reads the whole subtree now, skips a `hidden` or `inert` one,
    and counts a link with its `href`, a control not disabled, no `type="hidden"`, and
    any element with a non-negative `tabindex`;
  - `empty-control` looked one level deep for a name, and read a component child
    (`<button><Icon/></button>`) as nothing. It looks at any depth, and a component is
    "cannot tell";
  - the runtime's forced-colours survey matched `button|a|summary` anywhere in a tag's
    name, so a filled `main`, `nav`, `span` or `table` counted as a fill-only control;
  - the macOS TBT flake had a cause: the control click came at load + 500 ms, inside
    the fixture's 3-second task on a slow runner. It clicks at 5 s, after the task, and
    the test asserts when it clicked;
  - automation-coverage.md §3 read as this suite's coverage. It now says the table is
    what a tool can decide, and marks the eleven rows whose mechanism neither gate
    runs (1.3.4, one of the seven Full rows, among them). SKILL.md says this suite runs
    six of the seven a tool decides outright.

  `test_content_and_a11y.TheAuditsRuntimeMediums`, `test_browser_runtime.TheForcedColoursSurvey`.
- **The release job, the tooling README and the plugin README were wrong on three
  counts** (the audit's D1, D2 and D3):
  - `release.yml` pinned `actions/checkout` and `astral-sh/setup-uv` by tag while the
    job holds `contents: write` and `GH_TOKEN`, and checkout kept its credential. Both
    are pinned to commit SHAs and checkout sets `persist-credentials: false`, as
    `evals.yml` does;
  - `tooling/README.md` said a build is byte-identical on a rebuild. It is with the
    same zlib; Windows' Python 3.14 deflates with zlib-ng, so a local build's bytes and
    `SHA256SUMS` differ from the release's, and `compare.py` compares by content;
  - the plugin README said three browser scripts need Node; six `.mjs` scripts do.

  `test_release_build.TheAuditsReleaseMediums`.
- **Two kinds of test could pass or fail for the wrong reason** (the audit's T1 and T2):
  - the evidence register kept an entry alive while its doc quoted any of the entry's
    numbers as a substring: "19 categories" on a bare "143", "37–41%" on "41%", "2,000+
    audits" on "13,000". A doc must now quote the figure itself, on its own, or a
    spelling of it that carries the same numbers ("16,384-byte"), and every companion
    value must be quoted on its own in one of the entry's docs. The register is
    regrouped around what each doc quotes: "143" (with its 19 categories), the GDS
    range, Tenon's 37% and Asqatasun's 41% apart, and Deque's 13,000 pages, each re-read
    at its source on 2026-10-16; two spellings no doc used are gone;
  - three tests held a shared runner to an absolute time: the a11y audit's 4,000 rows
    under 20 seconds, and TBT under 50 ms for a page whose only long task TBT should
    leave out, which a slow runner's own loading could break. The ratio bound stays.
    `measure_vitals.mjs`' JSON now lists each run's long tasks (`perRun[].tasks`: the
    start on the page's clock, the duration, `inTbt`, and `leftOut` as `interaction`,
    `before-fcp` or `after-tti`), and the TBT tests find the fixture's own task there
    and read it against TTI (Codex on #154: a total less TBT could not tell it from
    a slow runner's blocking before FCP). Both still fail when the handler or the
    late task is counted.

  `test_evidence.EvidenceRegister`, `test_browser_runtime.VitalsMeasures`.
- **The schema reader, the scaffold, the email build and the deck misread nine things**
  (the audit's E1 to E8 and E10):
  - a naive `timestamp` named `created_at` or `updated_at` (every Prisma `DateTime
    @default(now())`, every Drizzle `timestamp()` without `withTimezone`) became an
    editable datetime-picker. It is a read-only timestamp, and the naive-timestamp
    question is still asked;
  - a table's name went into the scaffold's paths as it was, so `../evil` wrote above
    `features/` and `../../evil` left `--out`. A name with a path separator, `..` or NUL
    is refused (exit 2), and no file is written outside `--out`;
  - a column `2fa` gave a TSX and a Python syntax error, and `it's` an unterminated
    string. Names are written as escaped string literals, `errors['2fa']` where the name
    is no identifier, and a pydantic attribute that would start with a digit takes
    `col_`;
  - a policy that pins a column through a cast (`auth.uid()::text = owner_id::text`), a
    JWT claim (`(auth.jwt() ->> 'sub')::uuid = user_id`) or a quoted camelCase name
    (`auth.uid() = "userId"`) was read as leaving it writable. A string is no call, and
    `= any(...)` does not pin;
  - a Drizzle schema of `pgTable.withRLS(` tables only was sent to the generated-types
    reader;
  - the email minifier removed the space between inline siblings
    (`<strong>Hello</strong> <em>world</em>` read "Helloworld"); it is kept unless a
    block or table tag is beside it;
  - email-client-matrix.md said the templates keep 600 to 750 bytes of `<style>`; they
    keep 751 to 919;
  - the shipped templates did not lint clean as source (their mobile media queries,
    dividers, pull quote and columns held literals). Seven `--email-*` tokens hold
    them, and the builds are byte-identical;
  - the deck put the log template's header placeholders (`<company>`, `<your name>`,
    `<YYYY-MM-DD>`) on the cover with no gap. Each is a gap and stays off the deck.

  `test_scaffold.TheAuditsContentMediums`, `test_email.TheAuditsEmailMediums`,
  `test_presentation.TheHeadersPlaceholders`.
- **Versioning, the docs site and the copy notes left out four things** (the audit's
  V2, V3 and V10, and one found 2026-10-15):
  - with several DTCG files, a later file's record of a token it could not hold lost to
    an earlier file's written value, a false MAJOR. The files are read once, in order,
    and the last wins either way;
  - `deprecate import` read only the written tokens' `$deprecated`, so a deprecated
    token a file could not hold never reached the ledger. `read_deprecations` reads the
    record's marks too (`dtcg.recorded()`, which `diff_system` now reads as well);
  - `extract_system --tokens tokens.json` read the JSON as CSS: no token, exit 0, and a
    config that listed one was skipped. A contract.json or DTCG file is read through
    `read_tokens`, as the gates read it;
  - every SKILL.md's note on copying the scripts named the commands, not the helpers
    they import (`project_config.py`, `dtcg.py`, `figma_common.py`,
    `browser_common.mjs`), so a copied command failed with `ModuleNotFoundError`. Each
    note names them, and a test runs each command copied with only what its note names.

  `test_versioning.TheAuditsVersioningMediums`.
- **Versioning and the docs site misread five things** (the audit's V4, V5, V6 and V9,
  and one found beside them):
  - `deprecate scan` read the suite's own JSON records as consumers: the mapping's
    rules hold `var(--fg-subtle)`, so the token was "NOT SAFE to remove" forever. A
    ledger, a mapping, a scan report and a docs snapshot are skipped;
  - `deprecate add --replacement` was never looked up. It is refused (exit 2, unless
    `--force`) when it is the token itself, is deprecated or removed, or is declared in
    none of the `--source` files;
  - `build_docs` inlined the search index into a `<script>`, so a `</script>` in a
    token's note ended it; every `<` is written as `\u003c`;
  - `diff_system` searched a folder for `system.json` and `tokens.css` only, though the
    docs promise a folder holding a `contract.json` too;
  - `diff_system` read `#2563eb80` as solid and measured its contrast; an 8-digit or
    4-digit hex now carries its alpha, and the pair is a translucent note.

  `test_versioning.TheAuditsVersioningMediums`.
- **The migration's census and proposal misread five things** (the audit's M2 to M6):
  - a Tailwind class with a variant of digits, hyphens or brackets (`2xl:`,
    `group-hover:`, `data-[state=open]:`) or a minus (`-mt-[13px]`) was never counted,
    so never rewritten; and a rule for `data-[state=open]:p-[16px]` would have rewritten
    it to `data-well`;
  - a length in a property outside the spacing and size sets (the size in a `font`
    shorthand, `transform`, `filter`, a grid track) was filed as spacing and counted
    among the distinct spacing values. It is `other-length` now, a row to look at by
    hand, with advice by property;
  - `z-index: -1` was ranked onto the first rung and rewritten to `var(--z-raised)`,
    its sign flipped. A negative z-index is a row of its own;
  - extraction-and-clustering.md §6's role table disagreed with `role_for()` in nine
    cells; it is rewritten from the code, and a test reads every cell back through it;
  - `$gutter: 24px` was told to add a Tier-2 role, where `$brand: #2f6df6` was told to
    delete the variable. A length a preprocessor variable holds gets the same advice.

  M1 (a duration counted at two rules) did not reproduce: #135 fixed it.
  `test_token_migration.TheAuditsMigrationMediums` and `TheRoleTableIsTheCode`.
- **The migration, versioning and Figma tools missed six more things, and their
  references fell behind the code** (the audit's M7, M8 and V13 to V16):
  - the census did not read `@apply p-[13px]` in a stylesheet, or the strings of
    Svelte's and Astro's `class={…}` and Astro's `class:list={[…]}`, which it reads
    in a `.jsx`. It reads them, `@apply p-4` with the project's Tailwind 4 theme, and
    files them as hand work: the codemod rewrites class attributes only (CodeRabbit
    on #157);
  - the codemod's rewrite went through `mkstemp`, so on Linux and macOS a 0644 file
    came back 0600 and a 0755 one lost its execute bit. It keeps the file's mode;
  - `figma_to_tokens` marked a `$type: duration` token not named `dur-*` unresolved
    in `tokens.json`, though its CSS was right;
  - `diff_system` read any design-system-docs schema; it reads the one `build_docs`
    does, and names it when it refuses another (exit 2);
  - `--format all` without `--out-dir` wrote three files into the working folder and
    ignored `--out`. It needs `--out-dir` and refuses `--out` (exit 2);
  - change-classification.md gave a theme override's change or removal as major (the
    code gives patch when it resolves as before) and listed `component-renamed`, which
    nothing emits: the kind is gone, and the table says a renamed component reads as
    removed and added. `figma_audit` dropped a code title nothing emits; the scripts
    references name figma_audit's `-o/--out` and `resolver` shape and extract_system's
    `--no-color-impl`, and `/figma-sync`'s hint names the `resolver` shape.

  M9 and V12 were closed by #140. `test_token_migration`, `test_figma_sync`,
  `test_versioning.TheAuditsVersioningMediums`, `test_docs.TheScriptReferences`.
- **The content, email and runtime gates misreported eight things** (the audit's E11,
  E12, G8 to G10, G12, G14 and G16):
  - `lint_email --source` reported every rule of a `<style>` block on the element's
    line. Each rule has its own line, a comment's newlines and an `@media` block's
    rules counted;
  - `introspect_schema` read Prisma's `Unsupported("geometry")` as a type named
    `unsupported`, with a text input; it reads the type it names, as the SQL does (a
    map picker), and `Unsupported("geography(Point, 4326)")` is no longer cut at its
    first `)`. Neither reader takes a PostGIS SRID for a length any more: only text
    and bit types have one (Codex on #159);
  - `perf_audit` skipped a `report.html` or `stats.html` without a word. It still
    leaves a bundle analyzer's report out, and names each on stderr and in the JSON's
    `ledger.not_counted`, so a real page of that name is seen;
  - `a11y_static` quoted a bound attribute as `type="\x00expr\x00"`; it writes
    `type={…}`, and names a field by its `id` when its `name` is bound. A bare
    `title` no longer reads as a job title (the pattern `^title$&` never matched, and
    a post's title is no `organization-title`), and a number input asks only for a
    number's purposes, so `name="units"` is no address line;
  - its `focus-ring-transition` flagged `transition: outline-color`, which its own
    fix allows;
  - `a11y_runtime` named no criterion for axe's two-digit tags (`wcag1412`,
    avoid-inline-spacing's 1.4.12), and automation-coverage.md's 1.4.12 row now says
    that rule runs;
  - `perf_audit`'s header listed a missing-`srcset` check no rule makes, and it built
    a set of font families it never read.

  E13, G11 and G15 were closed by #138, E14 and G13 by #142.
  `test_email.TheAuditsEmailLows`, `test_schema_sources.TheAuditsContentLows`,
  `test_content_and_a11y.TheAuditsRuntimeLows`.
- **The docs, the pointer check and the suite let nine things slip** (the audit's D5 to
  D9 and T3 to T10):
  - the Core Web Vitals thresholds, the 75th percentile and the evals' "Claude Code
    2.1.269 or later" had no entry in `tests/fixtures/evidence.json`. They are
    registered, each re-read at web.dev and the evals page on 2026-10-16, so every doc
    that quotes them is held to the register; LCP's poor threshold reads 4 s, as
    web.dev gives 4000 ms;
  - `tools/check_pointers.py` walked `skills/` only: it reads the agents and the
    workflow commands too, and their seven pointers are registered;
  - unused imports, f-strings with nothing to format, `raise` in an `except` without
    `from` (13 sites, each `from None`: the message carries the cause) and eight
    locals assigned and never read are gone from the scripts and the tests, none of
    them a check left unwritten. `test_static_checks` keeps the five rules (ruff's
    F401, F541, F841, B904 and SIM115's `open(…).read()`) with the standard library;
  - 81 assertion loops in the tests stopped at their first failure; each case is a
    `subTest` now, and the static checks keep it so;
  - `NoFragileJsonReads` had no positive control and missed a named import's
    `readFileSync`; `PythonFloor` left out the workflow commands' scripts and
    `shared/`; the reduced-motion facts sat behind two `if`s; the manifest's strict
    validation skips on every CI cell, so CI's `validate` job is held to it;
    `wds_support` turns bytecode off for every run; the 2025.10 fixtures use the
    colour object, and the legacy string reads the same; `test_versioning` closes its
    files;
  - CLAUDE.md maps all five tools and both kinds of eval, and a skill byte table in
    the live docs is held to the bytes on disk.

  `test_static_checks`, `test_evidence`, `test_pointers`, `test_docs.TheAuditsDocsLows`,
  `test_powershell_json`, `test_facts`, `test_mcp`, `test_harness.NoBytecode`, `test_dtcg`.
- **The references quoted Baseline browser versions with no entry, and two were wrong**
  (the rest of the audit's D6). Twenty support lines across eight of web-design-studio's
  references are registered in `evidence.json`, each re-read at web-features' own file for
  the feature on 2026-10-16. Re-reading them found:
  - the Popover API is Baseline from Chrome and Edge 116, not 114 (navigation-patterns.md);
  - `@scope` is Baseline since 2026-03-24, with Firefox 146 and Safari 26.4, not "in
    Firefox from 128" (stack-vanilla-css.md);
  - `linear()` (since 2026-06-11) and subgrid (since 2026-03-15) are now widely
    available, so motion-system.md and layout-composition.md say so;
  - accessibility.md gave `@starting-style` and `transition-behavior` one list,
    "Safari 17.5 and 17.4"; each now has its own.

  `test_evidence` reads a browser version wherever a doc quotes one, with each later
  version of the same browser beside it ("Safari 17.5 and 17.4", Codex on #162), and
  fails one that stands in no registered figure or `not_statistics` row; a support figure's source must
  be web-features. Our own observations ("checked in Chromium 153") and the drift examples
  (Chromium 140 and 141) are listed as `not_statistics`.
  `test_evidence.EvidenceRegister.test_every_browser_version_is_registered`.
- **web-design-studio's gates measured and ruled four things wrong** (the audit's W1 to
  W5):
  - `check_roles` read `--fg-default: #00000080` as solid black, 20:1 on the canvas,
    and called `oklch(… / 0.5)` "not a colour": its translucency check ran after a
    parser that drops a hex's alpha and refuses a function's. It runs first now, and
    `generate_color_ramp.py --check` and its seed refuse a translucent colour too
    (`alpha_of()`, `opaque_color()`);
  - both measured a colour outside sRGB with its channels clipped, under which
    `oklch(59% 0.35 273)` is 6.49:1 on white; chroma-mapped, as a browser may show it,
    it is 4.40:1. They take the worse of the two (`worst_contrast`), as the ramp's own
    table did, and `--check` says so;
  - `tw_probe` cleared every key under `--font-*: initial`, where Tailwind keeps the
    weights and sizes (and four other namespaces' keys), so a theme's own `font-bold`
    read as a stock class that survived (`KEPT_UNDER`, from tailwindcss 4.3.3);
  - stylelint refused a layer statement with a layer of the project's own between the
    canonical ones (`…, overrides, print`), which the spec and the audit allow. Both
    gates read a sub-layer in a statement as its parent where it stands, so
    `reset, components.skin, base` is out of order (Codex on #145);
  - ESLint refused `bg-[url(…)]`, `mask-[url(…)]` and `content-['…']`, which the audit
    exempts: neither can be a token. Both exempt a `url()` only when it is the whole
    value, so `bg-[url(…),linear-gradient(13deg,…)]` is refused (Codex on #145).

  The spec has the layer examples and a `tailwind_arbitrary` section, which both gates
  run (`test_rules_spec`, `test_real_tools`); `test_check_roles` and `test_tw_probe` hold
  the rest.
- **web-design-studio's tools missed four more things, and two config comments were
  wrong** (the audit's W8 to W13):
  - `check_roles` skipped a rule holding a nested block (native nesting): the starter
    with one `@media` inside `:root` said "--fg-default is not declared" (exit 2). It
    reads the rule's own declarations, and still not the condition's;
  - the audit flagged `content: "!important"`, words in a string, as the flag, and
    missed the flag written `! important`. It reads the flag as stylelint does;
  - `tw_probe` stopped on `@import "./theme"` (ENOENT, exit 2). It reads `theme.css`,
    as Tailwind and the census do;
  - the pre-commit hook's role stage took `tokens.css` and `x-tokens.css` only, so
    `design.tokens.css` went unchecked. It takes each one-file name design-rules.json's
    `token_files` give a token set, on a file that declares a Tier-2 role; a file of
    primitives alone is passed over, since check_roles needs the roles, and so is a
    modular `tokens/` folder, whose roles read a sibling's primitives (Codex on #156);
  - the ESLint config said the fixtures run ESLint 10.4.0 (they run 10.11.0), and the
    stylelint config's token-file override restated `custom-property-pattern`
    unchanged, under a comment that called it a relaxation.

  W14's `noqa` directives stay: under ruff's default rules they suppress real E402
  and E731 findings, and only a narrower rule set reads them as unused.
  `test_check_roles`, `test_audit_design`, `test_tw_probe`, `test_precommit_hook`,
  `test_recipes.DependencyFacts`.
- **A Tailwind `size-*` was proposed a padding role** (CodeRabbit on #129). `size-[16px]`
  became `size-well`, sizing an icon by `--pad-well`, and v4's counted `size-4` would have
  too. It is a width and a height, so it is a size: reported when no `--width-*` role
  fits (`test_token_migration.TheV4SpacingCensus.test_a_size_is_no_padding`).

- **`tw_probe` read an `@source inline()` class as missing** (found by SB-B5's doc
  test). Its classes are in the first build, so asking for one added no rule, and a role
  it named failed the check. Those lines are set aside when compiling; `@source not
  inline()` stays (`test_tw_probe.TheProbe.test_an_inline_source_does_not_hide_its_classes`).
- **The audit read a file name as a CSS-in-JS template** (found by the audit of
  `tw_probe.mjs`). Its emotion pattern took the `css` of `` `${file}.css` `` for a `css`
  tag, so the rest of the file was audited as unlayered CSS with long selectors. A tag is
  now a name of its own, with no `.`, `$` or word character before it; a real
  `` css` `` template is still audited (`test_audit_design.JsxClassesAndCssInJs`).

### Upgrading

- **Part 5 of `eslint.design.config.mjs` uses eslint-plugin-better-tailwindcss** (P36;
  SB-C4, decision D4), one plugin for both Tailwind majors, in place of
  eslint-plugin-tailwindcss 4.x for v4 and a pinned 3.x for v3. If you copied Part 5:
  1. `npm uninstall eslint-plugin-tailwindcss`, then
     `npm i -D eslint-plugin-better-tailwindcss` (4.9.0 peers ESLint 7 to 10, and
     Tailwind 3.3 or later or 4.1.17 or later).
  2. Copy the new block. On Tailwind v4 it reads your entry CSS (`entryPoint`, which
     replaces `cssConfigPath`); on v3 its `tailwindConfig` line takes `entryPoint`'s
     place (it replaces `config`). The block sets the plugin's `cwd` to the project and
     anchors both paths there, because the plugin resolves `tailwindcss` and reads its
     paths from ESLint's working directory otherwise: from a monorepo root, the root's
     Tailwind, perhaps the other major.
  3. Rename the rules you configured yourself: `no-custom-classname` is
     `no-unknown-classes` (its `whitelist` is `ignore`), `no-contradicting-classname` is
     `no-conflicting-classes`, `enforces-shorthand` is `enforce-shorthand-classes`, each
     under the `better-tailwindcss/` prefix.
  4. **Anchor your own `ownClasses` entries** (`'^card(?:__[a-z0-9-]+)?$'`): the new rule
     tests each entry unanchored, so `card` would also pass `cardd`. On v4 you can drop
     the entries for classes your `@layer components` defines: `detectComponentClasses`
     learns them from the entry. The layout primitives and `u-*` utilities still need
     theirs.

  What changes in what it reports:
  - **New:** a duplicate class (`p-card p-card`) and, on v4, a class v4 keeps only for
    compatibility (`flex-grow` is `grow`).
  - **`classNames()` and `classnames()`** are read, as Part 2 reads them: the block adds
    them to the plugin's default helpers.
  - **Lost on v3:** the conflicting-class check. The plugin's rule compares the CSS v4
    generates and reports nothing on v3.
  - **Dropped:** the old v3 block's `no-arbitrary-value`. Part 1 already refuses an
    arbitrary value on every stack, with no plugin.

  The spike that decided it ran both plugins over the same project and fixtures
  (`dev plans/web-design-suite-d4-spike.md`): they found the same typos, off-scale
  classes and conflicts, in about the same time once warm. The tests run the new block
  through the real plugin on Tailwind 4.3 and 3.4 (`test_real_tools.TailwindPluginV4`
  and `TailwindPluginV3`).

- **`a11y_runtime.mjs` runs four more checks by default** (P35 part 1): `spacing`,
  `obscured`, `hover` and `motion`. Their errors (`spacing`, `obscured`, `hover`) fail a run
  that passed on 3.6.0, and `reflow_failures` now also counts text a box clips at 200% or
  320px. A CI command and a budget that were green may go red with no change of your own.
  Read the new findings first. An error fails the run whatever the budget allows, so to
  roll the checks out one at a time, leave the rest out with `--skip CHECK` and take each
  `--skip` away once its findings are fixed. The `motion` findings are warnings, and fail a
  run only through a budget: `motion_not_reduced`, `motion_content_hidden` or
  `motion_busy_stopped`.

## 3.6.0 — 2026-10-13

### Added

- **DTCG 2025.10, read and write: part 1** (P31; LC-C2, LC-B2 in part). One module,
  `shared/dtcg.py`, reads and writes the Design Tokens format's first stable version,
  copied beside every `project_config.py` and held to the master by a test. It replaces
  figma-variables-sync's `dtcg_values.py`, whose reading it keeps.
  - **A DTCG file is a token file.** `read_tokens()` reads a `*.json` or `*.tokens` file
    with no `"schema"` that holds a token, so `.design-suite.json`'s `tokens`, every
    `--tokens` flag, the audit and the lint configs take one. A token's name is its path
    joined by `-` (`color.bg.surface` is `--color-bg-surface`), and its tier comes from
    its value. `project_config.mjs` reads it the same way, held to the Python reader on
    every value form.
  - **Writing.** `figma_to_tokens.py --format dtcg` writes a 2025.10 document from any
    Figma export or from a `tokens.css`: names split on `-` into groups, a name that is
    also a group's prefix as its `$root`, `var()` as references, every token typed, and
    colours as objects in their own space, with an sRGB `hex` fallback where one can be
    computed (none for `lab()`, `lch()` or a `color()` space other than sRGB). A value DTCG has
    no type for (`clamp()`, `calc()`, `em`, `ch`), a token that refers to one, and each
    theme or density block are named and left out (exit 1).
  - **`diff_system.py`** takes a DTCG file as either snapshot, compared as a contract is:
    default values and tiers.
  - **The migration proposal.** `cluster_values.py` writes `tokens.json` in DTCG beside
    `tokens.css`.
  - `/install-gate` vendors `dtcg.py` with the audit's `project_config.py`.
- **Tokens Studio: part 2** (P31; LC-B2 in part). A Tokens Studio export is read as
  Tokens Studio reads it: the sets a theme uses merged, its source sets and then its enabled
  ones, each in `tokenSetOrder`, each theme
  group a collection whose modes are its themes, and each set no theme enables a
  collection of its own. A Light/Dark export becomes `:root` and `[data-theme="dark"]`,
  where it was `--light-bg-surface` and `--dark-bg-surface`. The legacy `{value, type}`
  keys and Studio's types read as 2025.10's, a bare number on a size is px, and math
  (`{space.base} * 6`) is worked out, where it was written into the CSS; math it cannot
  work out is named and left out. `read_tokens()` and the Node reader read such a file as
  its default theme. A DTCG `number` or `fontWeight` token is written unitless, where an
  opacity became `0.01rem`.
- **Themes through the DTCG resolver: part 3** (P31; LC-C2, LC-B2 in part).
  `figma_to_tokens.py --format dtcg --out-dir DIR` writes every theme with the
  resolver module (2025.10): `tokens.json` holds the default values, one file each
  theme or density block changes (`theme-dark.json`, its overrides only, typed against
  the whole set), and `tokens.resolver.json`, a set and one modifier per kind whose
  default context is `:root`. It works from a Figma export, a Tokens Studio export or a
  `tokens.css`; a rule that is no theme or density (`.inverse`, a media query) is named
  and left out. Where `--out` wrote the default mode alone, a `tokens.css` with
  `[data-theme="dark"]` now goes to DTCG and back to the same blocks.
  - **Reading a resolver.** `figma_to_tokens.py` and `figma_audit.py` read a
    `*.resolver.json` as modes: each modifier a collection of its contexts, a `theme`
    modifier's as `[data-theme]` blocks and a `density` one's as `[data-density]`.
    `read_tokens()`, and so `.design-suite.json`'s `tokens`, the audit and the lint
    configs, read its default. A source is a file beside it, a pointer into one, inline
    tokens, a set or one of a set's sources (`#/sets/base/sources/0`); a context keeps the
    spaces in its value (`[data-theme="high contrast"]`); a URL, an unreadable file, a cycle of sets and a modifier with no
    default are named, and a fan-out of sets is refused.
- **`$deprecated` reaches the release gate: part 4** (P31; LC-C2). A token the old DTCG
  snapshot marks `$deprecated` (itself, or through its group) counts as recorded in
  `diff_system.py`: the file announced it a release ago, so removing it now passes the
  gate, and the report says `deprecation  marked: $deprecated in OLD`. A ledger record
  for the same name wins. `deprecate.py import FILE --since X --removal Y` writes the marks
  into the ledger, so `status`, `scan` and `mapping` see them; the replacement is the
  token the reason names (`"Please use {bg.brand} instead"` is `--bg-brand`). A later
  file that sets the token again without the mark, a `tokens.css` or a `contract.json`
  among them, takes it off.
- **Style Dictionary's and Terrazzo's names: part 5** (P31; LC-B2). Both tools join a
  token's path with `-`, so `color.neutral.500` is `--color-neutral-500` and a component
  reading it skipped a tier unseen: no gate knew the name. `.design-suite.json` takes
  `names`: `prefixes` (each ending in `-`) taken off a name that starts with one, and a
  `rename` table, read first. The audit, stylelint and ESLint read Law 6 through it, in a
  stylesheet, a `(--name)` class and an inline custom property, and a page-rhythm role or
  a null-out under a prefix still passes. The project's own ramp steps are read through
  the map as well: a step renamed to a role passes, and one the tokens file spells with a
  prefix is still a primitive. The spec's `tiers.names` holds the examples,
  and `project_config.py` and `.mjs` check the key alike.
- **Figma on every plan: the Plugin API route** (P32 part 1; LC-B1, LC-C7). The only way
  into Figma was `--reverse`'s REST body, and `POST /v1/files/:key/variables` needs an
  Enterprise plan. `figma_to_tokens.py --reverse --format plugin-script` writes the same
  variables as Plugin API code, which the Figma MCP server's `use_figma` runs (or a
  development plugin), on any plan. It finds collections, modes and variables by name,
  renames a new collection's "Mode 1", keeps primitives out of the pickers (`scopes: []`),
  sets `codeSyntax.WEB` to `var(--token)`, keeps aliases as aliases, updates what differs
  in place and deletes nothing, so a second run changes nothing. A mode the plan does not
  allow is reported with Figma's message and the rest is written. It returns counts and
  the first errors, which is what `use_figma` hands back. SKILL.md routes a connected MCP
  server: `get_variable_defs` reads a selection, audited as records, and `use_figma` runs
  the script. The facts are re-read at Figma's Plugin API, MCP and FAQ pages
  (`references/figma-mapping.md` §14).
- **Each Figma plan's limits** (P32 part 2; LC-B6). A collection's modes are capped by the
  plan: Starter keeps the first only, Professional allows 10 modes per collection and
  Organization 20 modes per collection, and the REST API a maximum of 40 modes, each figure
  re-read at Figma's pages and registered. `figma_audit.py --plan PLAN`, or
  `.design-suite.json`'s new `figma.plan`, reports `MODE_LIMIT` (error) on a collection past
  the cap, as a theme, a density and a brand in one collection soon are, and stops asking
  Starter for a dark mode it cannot hold. `--reverse --format plugin-script --plan` reports
  the same before the run, and a REST body past the endpoint's own cap is not
  written (exit 2): Figma refuses the whole request. Both config
  readers check the key alike. `figma-mapping.md` §14 adds the plans' table, branch keys
  (`local` and the POST take one, `published` does not) and the MCP server's Starter
  allowance.
- **Theming without JavaScript: `light-dark()`** (P33; SS-B3). style-architecture.md §10
  teaches roles that hold both values, `light-dark(LIGHT, DARK)`, picked by the element's
  used `color-scheme`: the OS decides from the first paint with no script, form fields
  follow, and `[data-theme]` stays as the override, one `color-scheme` declaration long.
  Because the colour is resolved where it is used, a `<section data-theme="dark">` is dark
  inside a light page, derived tokens such as `--elevation-card` included, which a
  re-pointing block cannot reach. Support is Baseline 2024 (13 May 2024), widely available
  from November 2026; for older browsers, concrete roles with the `light-dark()` ones inside
  `@supports (color: light-dark(#000, #fff))`. `check_roles.py` holds a `light-dark()` role
  in every scheme the visitor can be in: the one a scope's `color-scheme` names alone
  (`.inverse { color-scheme: dark; }` reads the dark branch), both under `light dark`, light
  under none, reading `color-scheme` through `var()` and that one `@supports`. The starter
  rewritten that way measures, scheme for scheme, as its blocks do, and the example runs in
  a browser in the tests.
- **The top layer and the error state: modern CSS, part 1** (P38; SS-B4 in part).
  accessibility.md gave a modal dialog `z-index: var(--z-modal)`, as if the `--z-*` ladder
  reached the top layer. It does not: a toast at `--z-toast` sits under an open modal, and
  a z-index on a top-layer element orders nothing ("the last element in the top layer is
  rendered on top of everything else"). A new section says so and puts the message about
  what a dialog did inside it, as a `popover="manual"` with `role="status"`: a popover shown from elsewhere
  renders over the dialog too, but the modal has made it inert, so clicks pass through it
  and a screen reader does not reach it. The toast fades in from `@starting-style` and out
  with `transition-behavior: allow-discrete`, each feature's support stated. The field's
  error state adds `:user-invalid`, which waits until the user has touched the field, with
  `:has()` for its hint. A new `test_modern_css` runs each snippet in Chromium on the
  starter's tokens, reading the hit test and Chromium's accessibility tree.
- **Container type, fallback x-height, alpha variants and `height: auto`: modern CSS,
  part 2** (P38; closes SS-B4). Each snippet runs in Chromium in `test_modern_css`, as
  written, on the starter's tokens.
  - **`cqi`** (typography.md §10): type sized to its container, as a fluid token whose
    role a card's headline reads, worked from two anchors as the viewport steps are. The
    `rem` intercept keeps it growing with zoom; a pure-`cqi` size does not grow at all.
    stack-vanilla-css.md no longer keeps the units out of tokens: they are Baseline widely
    available. `inline_styles.literal_units` in the spec takes the six container units,
    so an inline `'4cqi'` is a literal for the audit and ESLint.
  - **`font-size-adjust`** (typography.md §8): one number matches every fallback's
    x-height to the web font's, and narrows the shift without removing it. Checked in
    Chromium: `from-font` reads the fallback itself during a swap and changes nothing, a
    face's `size-adjust` has no effect beside it, and every `font:` shorthand resets it,
    so it is declared after each role's `font:`, on a stack of its own without the
    re-metricked face.
  - **`color-mix()` and relative colour** (color-system.md §9): a role's alpha variants
    derived in the token file, declared on every themed element, since a derived token on
    `:root` alone keeps the light theme's tint inside a dark band.
  - **`interpolate-size`** (motion-system.md §7): a disclosure animating to `auto`, in
    Chromium only and a jump elsewhere, with `visibility` keeping a closed panel's links
    out of the tab order and the accessibility tree, and `inert`, which its toggle sets
    with `aria-expanded`, keeping them out while it closes. §5's table pointed to an accordion
    §7 did not have.
- **The migration census reads every style source, and the rollout recipes** (P39; LC-B5
  in part, LC-B7).
  extract_literals counted 1 of a Sass file's 4 module colour functions, never opened a
  Vue, Svelte, Astro or HTML file, and read no CSS-in-JS object but JSX's `style={{}}`, so
  a migration sized from it came in short.
  - **Sass:** `color.adjust()`, `color.scale()`, `color.change()` and `color.mix()`, and
    their global names, are colour functions, as `darken()` is. CSS's `color()` no longer
    matches inside `adjust-color()`.
  - **Vue, Svelte, Astro and HTML:** each `<style>` block is a stylesheet in its `lang`,
    rewritten by the codemod too; a `lang` the scanner cannot follow (`sass`, Stylus) is
    named among the problems. Scripts and Astro's frontmatter are read as JavaScript,
    `style=""` attributes as inline styles, and `class=""` for Tailwind's arbitrary values.
    A `<style>` in a comment or a script's string is not read.
  - **Style objects:** MUI's `sx`, Emotion's `css`, `styled.div({})`, vanilla-extract and
    Panda, every nested level, with MUI's and Panda's shorthands read as their properties.
    A number in `sx` or Panda may be a theme step, so only strings count there.
  - **cluster_values** sets style objects aside as hand work beside inline styles, each
    with its own reason, so neither is counted as mechanically replaceable.
  - **The rollout** (design-system-versioning's rollout.md): §3's upgrade takes its
    baselines on the version it leaves, before the install, which would otherwise approve
    whatever the new version renders; §6 deprecates a bad release with `npm deprecate`; §2
    has Renovate (`rangeStrategy: "pin"`, `minimumReleaseAge`) and Dependabot
    (`versioning-strategy: increase`, `cooldown`) recipes that open the upgrade and leave
    the visual diff and the merge to a person.
- **Prisma and Drizzle schemas in** (P40; DL-B3 in part). content-model-to-ui read SQL,
  Supabase's generated types and a JSON dump, while its description promised Postgres.
  `introspect_schema.py` now reads a `schema.prisma` and a Drizzle `pgTable` schema too,
  found by themselves (`--format prisma|drizzle` to say so). The shop of `shop.sql`,
  written in each, reads to the same screens: Drizzle's in full, Prisma's less what it
  cannot say (CHECK constraints, the key to `auth.users`), each loss in the model's
  `fidelity`. Neither carries row-level security, so the SECURITY block says unknown.
  Names spelt the JavaScript way (`createdAt`, `authorId`, `priceCents`) now meet the same
  signals as their snake_case spelling, so a timestamp stays out of the form and an
  owner key stays read-only.

### Changed

- **`evals.yml` runs only by hand.** A `v*` tag no longer starts it: the dispatch
  before the tag gates the release, and the tag's own run re-tested the same commit
  for about $9 (the owner, 2026-10-11).

### Fixed

- **A reference to a group's own token** (`{brand.$root}`, `#/brand/$root`), the
  spelling 2025.10 gives it, was left unresolved (P31).
- **A group's `$deprecated`** did not reach its tokens; now each one that does not say
  otherwise carries it, and the description notes it (P31).
- **A value spelt another way was a change** in `diff_system.py`: `oklch(88% …)` for
  `oklch(88.0% …)`, `0px 1px 2px 0px …` for `0 1px 2px …`, `cubic-bezier(0, 0, 1, 1)`
  for `linear`. Two values are now the same when they parse to the same DTCG type and
  value, part by part for a value with no type of its own. Against the stylesheet it
  was written from, a published DTCG file read 27 primitives as edited, and the 53
  tokens it cannot hold (`clamp()`, `ch`, `em`, and what reads them) as added: a major
  release for an unchanged system. The DTCG writer now keeps each token it leaves out,
  with its value, in the file's `$extensions` (`io.github.vybecode-ltd.web-design-suite`,
  `notWritten`), and diff_system reads them back into whichever snapshot is the DTCG
  file: a `clamp()` added since, or changed, is still a change, either way round. A
  quoted keyword (`"serif"`) stays another family than the keyword (the 3.6.0 live
  check; Codex on #119).
- **`--reverse` had no route from a project's tokens into Figma.** It refused a
  `tokens.css`, and given a DTCG file it read the document as a flat map, so its groups,
  or a resolver's own keys (`sets`, `resolutionOrder`), became variables, with exit 0
  and no Dark mode. It now reads a `tokens.css`, a DTCG 2025.10 file and a resolver:
  each theme (`[data-theme]`, or a resolver's `theme` contexts) is a mode of the
  semantic collection, and a density or another condition is named and left out (the
- **A Tokens Studio export never reached figma-variables-sync.** A prompt about one
  that did not say "Figma" heard no skill, and the session wrote its own converter.
  The router now hears "Tokens Studio", and the skill's description names it (the
  3.6.0 live check).
- **A declined dark pattern could go unexplained.** In one of three runs of the
  `no-fake-countdown` eval, the reply built only the honest countdown and never said why
  the resetting one deceives, and its judges failed it. landing-page-conversion's
  ethics boundary now opens by asking for the why in the reply: the pattern, that it
  deceives, and a law only where it applies (3.6.0's evals).

## 3.5.0 — 2026-10-10

### Added

- **The project contract, part 1** (XC-C8, LC-C1, LC-B3). A project can now name its
  token files, component globs, stack, budgets and baselines once, in a
  `.design-suite.json` at its root, instead of flag by flag. A script finds it by walking
  up from the working directory to the repository root, a flag beats it, and an unknown
  key or a wrong shape stops the run with the key named.
  - **One reader.** `shared/project_config.py` reads the config, and a byte-identical
    copy sits beside the scripts that use it, so a skill installed alone has one.
  - **`contract.json`.** `extract_system.py --contract FILE` writes the token system's
    default values by tier: ramps, scales, breakpoints, constants and roles. A token
    declared only in a theme or under a condition has no default and is left out.
  - **The scripts that read them.** `figma_audit.py --tokens` takes a `contract.json` as
    well as a `tokens.css`. With no flag, it and `extract_system.py` read the token files
    the config lists.
  - Part 2 brings the config to the other scripts, the budgets and baselines among them.
- **The project contract, part 2: the project's tokens everywhere** (LC-C1, LC-B3). Every
  script that compared against the starter's token system now reads the project's: a
  `tokens.css` or a `contract.json`, from `--tokens` or the config's token files.
  - **One view of the tokens.** `read_tokens()` gives the scripts a project's token files
    in the contract's sections. A `tokens.css` is read by its defaults, as extract_system
    reads them; web-design-studio's new `references/project-contract.md` says how its
    tiers can differ from a contract's, and what each script takes.
  - **`audit_design.py`.** A token file the project names is a token file wherever it
    sits, so `src/design/system.css` may hold literals. The ramps it declares
    (`--brand-500`) are Tier-1 colours, so a component reading one is a Law 6 leak. The
    config's `components` globs add to the component files, and `baselines.audit` is the
    baseline without `--baseline`.
  - **`figma_audit.py`.** A scale the project declares (spacing, radius, type, stroke, z,
    duration, leading, tracking, weight, breakpoints) replaces the studio's, as its ramps
    already did. The starter's own tokens change nothing.
  - **`figma_to_tokens.py --tokens`.** The project's names join the vocabulary:
    `color/brand/500` comes back as `--brand-500`, recognised and in its tier.
  - **`diff_system.py`.** A `contract.json` is a snapshot, and without a `new` snapshot the
    candidate is the project's token files. Against a contract, the other side is cut down
    to default values and tiers, so a contract diffed against its own `tokens.css` has no
    changes.
  - **`cluster_values.py --tokens`.** A migration lands on the project's ramps: its steps
    of the contract's six ramps replace the derived ones, and a step it lacks is built
    from its own accent. `--accent` still beats it.
- **The project contract, part 3: every key has its readers** (XC-C8). A flag still beats
  each, and each falls back to the script's own default.
  - **Budgets:** `perf_audit.py` and `measure_vitals.mjs` read `budgets.perf`;
    `a11y_runtime.mjs` reads `budgets.a11y`.
  - **Baselines:** `a11y_static.py` reads `baselines.a11y`, `perf_audit.py`
    `baselines.perf`, `build_docs.py --check` `baselines.docs`, and
    `snapshot_matrix.mjs` `baselines.snapshots`.
  - **The email build** (`build_email.py`, `lint_email.py --source`) reads `emailTokens`,
    never the site's `tokens`. **The deck** builds on the config's CSS token files.
    **`scaffold_ui.py`** takes its stack from `stack`.
  - **A Node reader.** `browser_common.mjs` gains `projectConfig()`, which finds and
    checks the file by the Python reader's rules, with the same messages; a test runs
    both on the same files. Python now refuses `"schema": true` and normalises `..` in
    a path, as Node does.
  - **Vendored alone.** `a11y_static.py` copied into a project's `scripts/` without its
    reader runs as it did, like `audit_design.py`.
- **The project contract, part 4: the lint configs read it too** (N37). The audit read a
  project's `.design-suite.json` and stylelint and the ESLint config did not, so a
  component under `src/widgets/` that read `--brand-500` failed one gate and passed two.
  Both configs now read the config from the working directory, as the audit does.
  - **stylelint:** a token file the config names is a token file, so its literals are
    allowed, and the `components` globs join the component files.
  - **ESLint:** a JSX or TSX file the globs match is a component file.
  - **Both:** a step of a ramp the project declares is a Tier-1 colour with a role. Its
    advice comes from the rule spec (`tiers.project_ramps`) through `sync_rules.py`, as
    the audit's now does.
  - **One Node reader.** The config reader moves from `browser_common.mjs`, which
    re-exports it, to `shared/project_config.mjs`. That file also ports `read_tokens()`.
    A copy sits beside each importer, and the two lint configs import it from
    `assets/configs/`, so copy it with them. A test holds both readers to the same
    tokens, refusals and component globs. Both readers now take a config or contract in
    every encoding Python's `json` finds: UTF-8, UTF-16 and UTF-32, with or without a
    byte-order mark.
  - **Globs in stylelint.** stylelint's overrides match with micromatch, whose `**` is
    not the config's, so each glob is translated. Run through stylelint's own matcher, the
    translation matches exactly the files `is_component()` does. micromatch compares a
    path as the tool spelt it, so each glob is written for every spelling of the
    project's folder: resolved, through a link or a subst drive, and on Windows with
    either case of drive letter.
  - **One fix.** A `tokens.css` ramp step must be ASCII digits, as a contract's is:
    `--brand-٥٠٠` was a ramp step to Python and a scale to Node.
- **Hooks, part 1** (XC-C2, LC-C8 and SS-C6 in part, XC-C8's hook part). The plugin
  now ships `hooks/hooks.json`. Each hook runs `hooks/design_hooks.mjs` under `node`, in
  exec form, so Windows spawns it with no shell.
  - **The design gate** (PostToolUse on Edit and Write). After each edit Claude makes to
    a file the audit reads, `audit_design.py` runs on that file, in the config's folder,
    so the project's own components and ramps count. Its findings reach Claude as
    context, capped below Claude Code's 10,000 characters.
  - **The generated-file guard** (PreToolUse on Edit and Write). An edit to a file
    that says it is generated in its first 800 characters is refused, with the reason:
    change its source and regenerate. The markers are the audit's.
  - **The router** (UserPromptSubmit). A prompt that names one skill's work, such as
    WCAG, Figma variables or an HTML email, hears that skill's name, up to two. A crowded
    skill listing drops the descriptions, and then the names are all Claude sees.
  - **Opt-in.** The gate and the guard act only in a project whose `.design-suite.json`
    turns them on, with the new `hooks` key: `{"designGate": true, "generatedFiles":
    true}`. Both readers check the key, with the same messages. The plugin's
    `design_hooks` option (`userConfig`), set to false, turns all three hooks off.
  - **Python, found.** The gate alone needs Python, and looks for it as the pre-commit
    hook does: `WDS_PYTHON`, else `python3`, `python` or `py -3`. Each candidate must
    report major version 3, so the Store placeholder on Windows is passed over. A hook
    that cannot act tells Claude why, or stays silent. It never blocks a tool call
    because of its own failure.
- **Hooks, part 2: the token diff** (LC-C8). After Claude edits one of the project's
  token files, the gate's hook runs `diff_system.py` against the published snapshot, and
  Claude hears the release the edit makes, each breaking change, and each contrast pair
  that crossed a WCAG floor, while it can still undo it. An edit that is only additive,
  or changes nothing, is silent.
  - **Opt-in:** `"hooks": {"tokenDiff": true}`, with the project's `tokens` and the new
    `baselines.system`, the published snapshot. Until that snapshot exists, the hook
    stays silent. Both readers check the new keys. A token file outside the project
    (`../shared/tokens.css`) is found through the session's project, and a config that
    fails its checks is reported for a token file it names, a `contract.json` too.
  - **`diff_system.py`** without `old` compares against `baselines.system`, as it
    already took the config's token files without `new`. It now compares components only
    when both snapshots carry them, as its note always said: a published `system.json`
    against the token files read every component as removed, a major release.
  - The gate's hook now has 180 seconds, for the audit and the diff in one process.
- **Workflow commands, part 1: `/gate` and `/install-gate`** (XC-C3 in part, GT-C12,
  LC-B4, XC-C8). The plugin's first commands are skills only the user invokes
  (`disable-model-invocation: true`), so they stay out of the skill listing. They live in
  `workflow-commands/`, which `plugin.json`'s `skills` key adds to the scan, so the 13
  skills and their `.skill` files are unchanged. Each pre-approves the one script it runs.
  - **`/web-design-suite:gate`** runs `audit_design.py`, `a11y_static.py` and
    `perf_audit.py` on the project, from its root, and gives one verdict per gate. The
    performance gate is skipped, and says so, without a build.
  - **`/web-design-suite:install-gate`** vendors the gate scripts into the project's
    `scripts/`, where every CI recipe and the pre-commit hook expect them, with their
    SHA-256 in `scripts/design-gates.json`. A clean checkout then runs them with no plugin
    and no `PYTHONPATH`. It also writes `.github/workflows/design-gates.yml`:
    - the three gates on Linux, in the Playwright image built for the project's own
      `playwright` (`mcr.microsoft.com/playwright:vX.Y.Z-noble`), with Python installed,
      the build served and waited for, and the browser gates' reports uploaded;
    - the static gates on Windows, where the tests run the job's commands on a fixture;
    - a job run by hand that records the baselines in CI and uploads them to commit,
      dot files included (`include-hidden-files`). The build command sits in a block
      scalar, so YAML reads any command line as itself.

    It reads the baselines' paths from `.design-suite.json`, refuses a `playwright`
    range, and never overwrites a file it did not write, its stamp included. It refuses
    a path the workflow could not run unquoted (a space, `;`, `$()`, a leading `-`), names any package
    the browser gates need that `package.json` lacks (`axe-core`, `serve`, `wait-on`),
    and checks out with `persist-credentials: false`, since `npm ci` runs install
    scripts. A `--dist` named for `/gate` that does not exist is "could not run", not
    skipped.
  - **In CI**, the README says how to run another skill's script: by path, from the
    plugin checked out at a release tag.
- **Workflow commands, part 2: the systems and the lifecycle** (XC-C3, SS-C6 and LC-C9's
  commands; their agents come with the subagents). Six more commands, each pre-approving
  exactly the scripts it runs. Two have a runner, where a step decides the next; the
  others are chains whose body runs the skills' own scripts through
  `${CLAUDE_PLUGIN_ROOT}`. Each writes its reports under `design-reports/` and edits
  nothing it was not asked to.
  - **`/web-design-suite:new-system BRAND`** turns a brand colour into the starter's
    system: the accent ramp with the brand exact at its nearest step, the neutral ramp on
    its hue, the starter's type scale or one from `--ratio`, `--dual-ratio` and `--fluid`,
    and the starter styles in `src/styles/`. Then `check_roles.py` checks every role pair
    in each theme, and a failing pair is named. It never overwrites a file without
    `--force`.
  - **`/web-design-suite:contrast`** checks every role pair in the project's tokens, or
    one foreground on one background. This is SS-C6's `/wds:contrast`; its `/wds:tokens`
    is `/new-system`, and its `/wds:audit` is `/gate`.
  - **`/web-design-suite:migrate`** takes a token migration's census: the literals, the
    clusters and the proposed mapping, with the questions that need a designer. It
    applies nothing.
  - **`/web-design-suite:release-check`** extracts the system, diffs it against the
    published snapshot (`baselines.system`), stops at the gate when a name vanished with
    no deprecation record, and writes the changelog entry and, for a breaking change, the
    migration guide.
  - **`/web-design-suite:figma-sync EXPORT`** audits a Figma export against the token
    system and stops on an error, with the designer's questions; on a clean audit it
    generates the tokens and diffs them against the project's. `figma_audit.py` gains
    `--out FILE`, which writes the questions, creating the folder.
  - **`/web-design-suite:docs-check`** extracts the system and checks the docs' snapshot
    (`baselines.docs`) and every hand-written claim against it.
- **Workflow commands, part 3: delivery, persuasion and the runtime gates** (PS-C11;
  DL-C7's and GT-C9's commands, their agents and hooks to come). Six more:
  - **`/web-design-suite:schema-to-screens SCHEMA`** introspects the schema, puts the
    questions only a person can answer to the user, scaffolds the UI with `--strict` (a
    blocking security finding, such as row-level security off, stops it with nothing
    written), audits the result, and checks it against supabase-integration.md's
    security sections.
  - **`/web-design-suite:email-build TEMPLATE`** lints the source, compiles it with the
    email tokens, lints the result and renders it light, dark and without styles.
  - **`/web-design-suite:deck`** runs the audits, the critique report on the critique's
    findings (stopping on a blocking one), the defence sheet and the deck, from the
    decision log. It has a runner, since the audits' JSON feeds the next steps.
  - **`/web-design-suite:gate-a11y`**, **`gate-perf`** and **`gate-matrix`** run the
    browser halves of the gates by hand: `a11y_runtime.mjs` on a page or a file; the static
    performance audit, then `measure_vitals.mjs` on the served build; the proof sheet,
    then `snapshot_matrix.mjs` against the baselines, which it records only when the
    user has looked at the sheet.
- **Subagents, and `/critique`** (PS-C4, XC-C4, XC-C3, SS-C6 and LC-C9; GT-C9's and
  DL-C7's agents). Six agents in `agents/`, each working in its own context and
  returning only what the conversation needs. None has a tool that edits files.
  - **`design-critic`** critiques with design-critique-gate preloaded and the project's
    CLAUDE.md left out, so the builder's familiarity does not come with it, and returns
    its findings as one JSON block. **`/web-design-suite:critique`** hands it the work,
    and nothing about how it was made, saves the block unedited to
    `design-reports/critique/findings.json`, and reports it; `/deck` takes that file.
  - **`gate-runner`** runs the browser gates and returns only the verdicts, the failing
    findings and the JSON paths. It never updates a baseline.
  - **`a11y-auditor`** and **`design-auditor`** audit with a11y-audit-runner and
    web-design-studio preloaded: by WCAG criterion with the manual checks left, and by
    Law with the drift no script sees.
  - **`supabase-security-reviewer`** reviews a scaffold's row-level security, write
    policies, unprotectable columns and keys, after `/schema-to-screens`.
  - **`codemod-batch-reviewer`** checks one codemod batch against the reconciliation and
    the known traps, with a verdict per file.
- **Hooks, part 3: the a11y gate and the email build** (GT-C9, DL-C7). Two more checks
  in the gate's hook, each behind its own key in `.design-suite.json`'s `hooks`.
  - **`a11yGate`:** after each edit Claude makes to a file `a11y_static.py` reads
    (markup, JSX, CSS, and templates such as `.php` and `.liquid`), it runs on that file
    in the config's folder, with the project's a11y baseline, and Claude hears its
    findings with the audit's. The two share the hook's 9,000 characters, each counting
    what it left out.
  - **`emailBuild`:** after each edit Claude makes to an email template, `lint_email.py`
    checks the source, `build_email.py` builds it into a temporary folder, and
    `lint_email.py` checks the build. Claude hears the errors; the warnings are counted,
    for `/email-build` to show.
  - **`emails`:** a new top-level key, the globs of the email templates, read as
    `components` is. Left out, it is `emails/**/*.html`. `ProjectConfig.is_email()` and
    `isEmail()` answer for a file, and both readers check the new keys.
  - The scripts one edit starts share 160 seconds, inside the hook's 180.
- **The gates as MCP tools** (XC-B1 in part). An MCP server, `gates`, in `.mcp.json`:
  `node mcp/design_gates.mjs`, MCP over stdio, standard library only, with Python found
  as the hooks find it.
  - **Five tools:** `audit_design`, `a11y_static`, `perf_audit`, `check_roles` and
    `diff_system`, named `mcp__plugin_web-design-suite_gates__<tool>`. Each runs the
    skill's script in the project's folder (`CLAUDE_PROJECT_DIR`), so the project's
    `.design-suite.json` counts, and returns its JSON with the exit code and a verdict:
    `pass`, `fail`, or an error when the script could not run.
  - **Safe arguments.** Each tool takes only its schema's arguments, checked; a path
    reaches the script after `--`, so a path never becomes an option.
  - **Sized for the context.** A report past 60,000 characters keeps the head of its
    longest lists, nested ones such as perf_audit's `ledger.assets` too, with
    `truncated` saying how many each left out: Claude Code warns past
    10,000 tokens of tool output and stops at 25,000.
- **An eval suite, and the routing cases** (XC-C1, XC-B2). `evals/` holds cases for
  `claude plugin eval` (Claude Code 2.1.269 or later), each a `prompt.md` with
  `graders/*.md`, the layout `claude plugin eval init` writes.
  - **Routing:** a case for each of the 13 skills, a request phrased as a user would type
    it, which passes when Claude loads that skill (`tool_used` on `Skill`).
  - **Boundaries:** five pairs of sibling skills, each way: a request for one that must
    load it and never the other (`min: 0`, `max: 0`, `arm: both`). The pairs are the
    accessibility audit and the critique, the docs and versioning, the migration and the
    Figma sync, the studio and landing pages, and the state matrix and the accessibility
    audit.
  - **Run them** from the plugin folder with
    `claude plugin eval . --tag routing --ablation none`. Every run is a real model call
    on your account. A routing case cannot pass without the plugin, so the no-plugin arm
    is skipped. The cases grant no shell, so they run on native Windows.
  - **The router, corrected.** The prompt router runs in every eval session too. It
    pointed a critique of a pricing page ("does this look professional") at
    landing-page-conversion alone, and a design system's documentation site at
    web-design-studio alone. It now hears "looks professional" for design-critique-gate,
    and a token reference, or docs or prop tables for a design system, for
    design-system-docs. `test_evals` runs it on every case's prompt. The first full run
    found a third: a review of a signup form for "screen-reader labels" loaded no skill
    in 3 runs, since the router heard "screen reader" only with a space. It hears the
    hyphen now, and the case passes 3 of 3.
  - **The first run:** 22 of 23 cases passed, then 23 of 23 after that fix, for about
    $6 at list price, with Claude Code 2.1.293 and `claude-sonnet-5-5`; in CI on Linux, 23 of
    23 for $4.11.
  - **In CI:** the repository's `evals.yml` runs the routing cases on a release tag or
    when started by hand, never on a pull request, with the CLI and both models pinned
    and a ceiling under the $15 a full run may cost.
- **Outcome cases, scored against a no-plugin baseline** (SS-C7, SB-C6, GT-C10, LC-C10,
  PS-C7, DL-C7). Eleven cases in `evals/<area>/`, each tagged `outcome` and its area:
  - **build:** XC-C1's pricing section, a Tailwind button with a loading state, a card
    whose title link covers the card, and a vendor datepicker's stylesheet;
  - **systems:** colour tokens from the brand colour #e8440a, in two themes;
  - **gates:** a clean axe run is not a WCAG 2.2 AA claim;
  - **lifecycle:** a DTCG export of a project's tokens, and a re-pointed role token is
    not a patch release;
  - **persuasion:** a countdown that restarts for every visitor is refused;
  - **delivery:** a profile form from a Supabase schema, and a receipt email for Outlook
    and dark mode.

  Each case grades what the run wrote, in both arms, so Δ measures the plugin: no raw
  colour or Tier-1 token in a component, the vendor CSS in `layer(vendor)`, a visible
  focus outline, colour objects in the DTCG file, and a judge for the answers. Its
  other graders check, with the plugin only, that its skill fired and that the gate it
  ran passed. A case that needs a project copies one in with a scaffold script.
  - **No shell.** The cases grant `Write`, `Edit` and the plugin's gate tools, and run
    the design audit and the contrast check through the plugin's MCP server, which
    runs outside the sandbox. So they run on native Windows, with no WSL2.
  - **Run them** from the plugin folder with `claude plugin eval . --tag outcome
    --scaffold --allow-real-servers --allow-tools Write Edit` and the two gate tools
    the cases use, as the README shows. Every run is a real model call on your account.
  - **The first run** (one run each way, Claude Code 2.1.293, `claude-sonnet-5-5`): 11
    of 11 passed for $2.21 at list price, with a mean Δ of 0.22. Without the plugin,
    Claude said a re-pointed `--bg-accent` could ship as a patch, built the restarting
    countdown, used `var(--space-4)` in a component and literal `ring-2` and
    `duration-150` classes. With it, the audit caught a Tier-1 leak and Claude fixed it
    before finishing.
  - **In CI:** `evals.yml` runs the routing cases, then the outcome cases in both arms,
    under one ceiling: the outcome set gets what routing left of the $15 a full run may
    cost. A release tag runs both.

### Fixed

- **Email templates are the email lint's** (N39). `/gate` failed a project on the
  plugin's own receipt template: `a11y_static.py` read it as a page, and reported no
  `<main>` landmark and the email reset's `outline: none` on `img`. The a11y hook said
  the same after each edit to a template. A folder's email templates, the files the
  config's `emails` names, are now left to `lint_email.py`, which checks their alt text,
  language and contrast, and `a11y_static.py` lists them as skipped; a template named on
  its own is still read. The hook leaves a template to the email build when that
  runs, and checks it as before when it does not, so no edit goes unchecked.
- **The router and a release question** (P30). "Can we ship this as a patch release?"
  about a change to tokens.css named web-design-studio, not design-system-versioning:
  the versioning route heard only "semver", "breaking change" or "deprecate" in the
  same sentence as tokens, and a file name's dot ends a sentence. It now hears "a
  patch, minor or major release or version" when design tokens, a tokens.css or
  tokens.json, a design system or a CSS custom property are named anywhere in the
  prompt; an API's auth token is not enough.
- **a11y_static's and perf_audit's baselines across platforms** (N38). Both keyed a
  finding by its path with the platform's separator, so a baseline recorded on Linux
  CI suppressed nothing on Windows, and the reverse: the CI template `/install-gate`
  writes records its baselines on Linux and runs the static gates on Windows too. Keys
  now use `/` and drop `./`, as audit_design's do, and a baseline's keys are read the
  same way, so one recorded before keeps matching.
- **A baseline in a folder that does not exist yet** (GT-C12). `audit_design.py`,
  `a11y_static.py` and `perf_audit.py` stopped with a traceback when `--write-baseline`
  named a file in a missing folder, as a config's `ci/audit-baseline.json` is on a fresh
  checkout. Each now creates the folder.
- **`extract_literals.py -o` into a new folder** (P26). It stopped with "cannot write"
  where `cluster_values.py`, `extract_system.py` and `diff_system.py` create the folder.
  `/migrate` writes its census to `design-reports/migration/`.
- **`introspect_schema.py -o` and `--answers-template` into a new folder** (P26). Both
  ended in a traceback; `/schema-to-screens` writes them to `design-reports/screens/`.

## Earlier releases

3.4.0 back to 3.0.1 are in [CHANGELOG-earlier.md](CHANGELOG-earlier.md), so that
neither file passes the 256 KiB a file may hold before Anthropic's directory sends it to a reviewer.
