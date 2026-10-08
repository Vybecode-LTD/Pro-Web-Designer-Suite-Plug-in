/**
 * =========================================================================
 * eslint.design.config.mjs — the Nine Laws, enforced in JSX/TSX
 * =========================================================================
 *
 * A flat-config FRAGMENT. It carries no parser, no TypeScript rules, no
 * React rules, no `ignores`. Compose it into the project config:
 *
 *   // eslint.config.mjs
 *   import js from '@eslint/js';
 *   import tseslint from 'typescript-eslint';
 *   import design from './assets/configs/eslint.design.config.mjs';
 *
 *   export default [
 *     js.configs.recommended,
 *     ...tseslint.configs.recommended,
 *     ...design,                       // design laws last: it escalates
 *   ];
 *
 * PEER DEPENDENCIES
 *   npm i -D eslint@^10 eslint-plugin-jsx-a11y
 *
 *   ESLint 9 reached end of life on 2026-08-06. eslint-plugin-jsx-a11y
 *   6.10.2 declares a peer range that stops at ESLint 9, although its rules
 *   run under ESLint 10. The suite's fixtures run this config on 10.4.0.
 *   Until a release widens the range, tell npm in package.json:
 *
 *     "overrides": { "eslint-plugin-jsx-a11y": { "eslint": "$eslint" } }
 *
 *   The composition above also needs typescript-eslint, and a TypeScript it
 *   accepts. typescript-eslint 8.71.0 takes TypeScript below 6.1.0, and
 *   npm's latest TypeScript is 7.0.2 (both read on npm, 2026-10-04), so an
 *   unpinned install is a peer conflict. Pin TypeScript beside it:
 *
 *     npm i -D typescript-eslint typescript@~6.0
 *
 *   Copy project_config.mjs with this file: the config imports it from its
 *   own folder (both are in the plugin's assets/configs/).
 *
 * THE PROJECT'S OWN CONFIG (N37)
 * ------------------------------
 * A project's .design-suite.json reaches this file as it reaches
 * scripts/audit_design.py and the stylelint config, read from the working
 * directory: its `components` globs join the component files (a JSX or TSX
 * file they match is one), and the ramp steps its tokens declare
 * (`--brand-500`) are Tier-1 colours with a role, in an inline custom
 * property and in a `(--name)` class. Without a config nothing changes; a
 * config with a mistake stops the run with the key named, as the audit does.
 *
 * WHY LINT RULES AND NOT A STYLE GUIDE
 * ------------------------------------
 * Every law in this file is one a competent engineer already agrees with
 * and will still break at 6pm on a Thursday with a client on the phone.
 * The theme config (assets/configs/theme.css) removes the off-scale
 * classes so they cannot be typed. This file closes the two doors Tailwind
 * leaves open regardless of theme configuration — arbitrary values and the
 * `style` prop — because no amount of `@theme` configuration can shut
 * them. Law 9: nothing ships un-audited.
 *
 * SEVERITY POLICY
 * ---------------
 * Everything here is `error`. A design-system warning is a design-system
 * suggestion, and a suggestion loses to a deadline. If a rule is genuinely
 * wrong for one line, disable it on that line with a `--` justification;
 * that comment is the audit trail and it survives in `git blame`. A rule
 * you keep disabling is a missing token — add the token.
 * ========================================================================= */

import jsxA11y from 'eslint-plugin-jsx-a11y';
import { lintProject } from './project_config.mjs';

/* =========================================================================
 * PART 1 — PATTERNS
 * =========================================================================
 * Declared once, as real RegExp objects, and interpolated into esquery
 * selectors via `.source`. Writing them inline as selector strings means
 * double-escaping every backslash, which is how these rules silently stop
 * matching anything and nobody notices for a quarter.
 *
 * The plugin's tests apply these patterns to fixture class lists
 * (tests/test_audit_design.py); if you change one, change the fixture.
 * ========================================================================= */

/* LAW 1 + LAW 3 — Tailwind arbitrary VALUES: `mt-[13px]`, `text-[#e8440a]`,
 * `w-[calc(100%-2rem)]`, `min-[600px]:flex`.
 *
 * This is the drift the skill exists to prevent, and it is the one thing
 * `@theme` cannot switch off: arbitrary values are a language feature of
 * the class parser, not a theme entry. Deleting the stock scale makes `p-4`
 * generate nothing (silently — it is not a build error); it does nothing
 * about `p-[17px]`. Only a linter closes it.
 *
 * Arbitrary VARIANTS are explicitly allowed — `data-[state=open]:`,
 * `aria-[expanded=true]:`, `group-[.is-open]:`, `peer-[:checked]:`,
 * `has-[img]:`, `supports-[display:grid]:`, `not-[...]`, `nth-[2n]:`. Those
 * select a STATE; they carry no value and cannot drift off-scale. Banning
 * them would make every Radix/Headless-UI integration unreachable, and a
 * rule that blocks correct code gets switched off wholesale. */
const ARBITRARY_VALUE =
  /(?<![-\w])(?!(?:data|aria|group|peer|has|not|in|supports|nth|nth-last)\b)[a-zA-Z][\w-]*-\[/;

/* LAW 1 — Tailwind arbitrary PROPERTIES: `[mask-type:luminance]`,
 * `[--my-var:4px]`. A whole declaration smuggled into a class attribute.
 * Undiscoverable, un-themeable, invisible to every audit that reads CSS.
 * If a component needs a property Tailwind has no utility for, that is an
 * `@utility` in theme.css or a rule in the component's own stylesheet. */
const ARBITRARY_PROPERTY = /(?<![-\w])\[[a-zA-Z-]+:/;

/* LAW 5 — `!important`, in both spellings: v3's `!bg-accent` prefix and
 * v4's `bg-accent!` suffix. Specificity is solved by the layer order, not
 * by force. An `!` means two rules are fighting, and the fix is to move one
 * of them into the right layer — `overrides` exists precisely so that a
 * genuine one-off never needs this. */
const IMPORTANT_MODIFIER = /(?<![-\w])![a-zA-Z]|[\w\])]!(?=\s|$)/;

/* LAW 6 — stock Tailwind palette classes: `bg-neutral-800`, `text-slate-500`.
 * With `--*: initial` in theme.css these do not resolve and produce nothing,
 * which is worse than an error: the element renders with no background and
 * looks like a CSS loading bug. Catch them at the source.
 *
 * This also catches the real failure: `bg-neutral-800` is a PRIMITIVE. Even
 * if it rendered, it would be a component reading Tier 1 — the exact tier
 * skip that makes "a bit more contrast in cards" a grep across 200 files.
 * The role is `bg-surface`, and it is already correct in dark mode. */
const STOCK_PALETTE =
  /(?<![-\w])(?:bg|text|border|ring|fill|stroke|divide|outline|shadow|accent|caret|decoration|from|via|to|placeholder)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}\b/;

/* LAW 3 + LAW 6 — numeric spacing steps: `p-4`, `mt-12`, `gap-7`.
 * `-0` and `-px` are permitted; they are real steps in tokens.css.
 * Fractions (`w-1/2`) are untouched — those are layout ratios, not spacing.
 *
 * With theme.css loaded these classes generate nothing, so this rule mainly
 * fires on code pasted in from a tutorial, a v0/AI-generated component, or
 * a developer's muscle memory. All three are exactly how a system dies. */
const NUMERIC_SPACING =
  /(?<![-\w])(?:p[xytrbles]?|m[xytrbles]?|gap-[xy]|gap|space-[xy])-(?:[1-9]\d*(?:\.\d+)?|0\.\d+)(?![\w-])/;

/* LAW 1 — literal values that no theme can remove: `duration-300`,
 * `delay-150`, `z-50`, `z-9999`, `border-2`, `ring-2`, `outline-offset-2`,
 * `underline-offset-2`. Tailwind generates a bare number for these utilities
 * whatever the theme says, so `--*: initial` leaves them all working. A literal
 * duration also opts out of the reduced-motion tokens. Use the roles:
 * motion-hover, z-modal, border-stroke, the focus-ring utility. */
const LITERAL_UTILITY =
  /(?<![-\w])(?:duration|delay|-?z|border(?:-[xytrblse])?|ring|ring-offset|outline|outline-offset|underline-offset)-\d+(?:\.\d+)?(?![\w./-])/;

/* LAW 1 — `/NN` opacity modifiers: `bg-accent/37`, `text-fg/80`. The number is
 * a literal alpha compiled into color-mix(). Translucency has roles
 * (--bg-hover, --bg-active, scrims); a modifier is a colour nobody chose. */
const OPACITY_MODIFIER =
  /(?<![-\w])(?:bg|text|border|ring|fill|stroke|outline|shadow|decoration|from|via|to|placeholder|accent|caret|divide)-[a-z][\w-]*\/\d+(?![\w])/;

/* LAW 2 — any outer margin utility except `auto`. `mx-auto` and `m-auto`
 * survive because centring is a container positioning ITSELF, not a child
 * pushing its siblings around.
 *
 * Scoped to component directories in Part 4, because a page-level layout
 * file is allowed to place things. */
const OUTER_MARGIN = /(?<![-\w])-?m(?:x|y|t|r|b|l|s|e|bs|be|is|ie)?-(?!auto(?![\w-]))[\w[]/;

/* LAW 2 — `space-x-*`, `space-y-*`, `divide-*`.
 * These compile to `margin-left` / `border-left-width` on
 * `> * + *`: every child except the first setting its own outer edge. Four
 * concrete failures, not one aesthetic objection:
 *   1. it breaks the instant the row wraps — the wrapped item keeps the
 *      inline margin and gains no block spacing;
 *   2. it inverts under `flex-row-reverse` and puts the gap on the wrong
 *      side;
 *   3. `order-*` reorders the DOM visually but `:first-child` does not
 *      move, so the un-spaced item ends up in the middle;
 *   4. it adds a selector and a specificity bump per child, for a job one
 *      `gap` declaration on the parent does with neither.
 * `gap` is the parent owning the gap. Use it. */
const SPACE_BETWEEN = /(?<![-\w])(?:space-[xy]-|divide-[xy]?(?:-|\b))/;

/* LAW 1 — a color literal anywhere in a JS/TS string: hex, `rgb()`,
 * `hsl()`, `oklch()`, `lab()`, `color()`. Chart configs, canvas fills,
 * `<meta name="theme-color">`, SVG `fill` props and email templates are
 * where these actually appear, and every one of them is a surface that
 * silently ignores dark mode.
 *
 * Read the token instead:
 *   getComputedStyle(el).getPropertyValue('--bg-accent')
 * or pass the token through a custom property and let CSS resolve it.
 *
 * KNOWN FALSE POSITIVE: a fragment identifier whose characters are all hex
 * — `href="#abc"`, `href="#defaced"`. Disable on the line with a
 * justification; it will be rare enough to be worth the noise everywhere
 * else.
 *
 * The colour functions come from assets/rules/design-rules.json
 * (values.colour_functions), as the audit's do, and so do the literal units
 * (inline_styles) and Law 6's tier lists (tiers), which TIER1_SHORTHAND
 * below is built from. */
// BEGIN design-rules: written by tools/sync_rules.py from assets/rules/design-rules.json; edit the spec, then rerun it
const COLOUR_FUNCTIONS = [
  'rgb', 'rgba', 'hsl', 'hsla', 'hwb', 'lab', 'lch', 'oklab', 'oklch', 'color', 'color-mix',
  'light-dark',
];
const LITERAL_UNITS = [
  'px', 'rem', 'em', 'ch', 'ex', 'vw', 'vh', 'vmin', 'vmax', '%', 'deg', 's', 'ms',
];
const TIER1_WITH_ROLE = {
  'space-': 'a proximity/inset role (--gap-related, --pad-card, --space-section)',
  'neutral-': 'a color role (--bg-surface, --fg-muted, --border-default)',
  'accent-': 'a color role (--bg-accent, --fg-accent, --border-accent)',
  'success-': 'a color role (--bg-success, --fg-success)',
  'warning-': 'a color role (--bg-warning, --fg-warning)',
  'danger-': 'a color role (--bg-danger, --fg-danger)',
  'info-': 'a color role',
  'text-': 'a type role (--type-body, --type-h2, --type-ui)',
  'leading-': 'a type role (--type-*), which carries leading in its shorthand',
  'shadow-': 'an elevation role (--elevation-card, --elevation-modal)',
};
const TIER2_EXCEPTIONS = [
  '--space-section', '--space-subsection', '--space-block', '--space-fluid-sm', '--space-fluid-md',
  '--space-fluid-lg', '--space-fluid-xl',
];
const TIER1_NULLS = ['--space-0', '--radius-none', '--shadow-none'];
const PROJECT_RAMP_ADVICE = 'a color role (--bg-*, --fg-*, --border-*)';
// END design-rules

/* The project's config, from the working directory (N37, in the header). */
const PROJECT = lintProject();
const PROJECT_RAMP_STEPS = new Set(PROJECT.rampSteps);
const RAW_COLOR = new RegExp(
  /(?:^|[\s(:,'"`[])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![0-9a-zA-Z])/.source +
    String.raw`|\b(?:${COLOUR_FUNCTIONS.join('|')})\s*\(`,
);

/* LAW 6 — v4's `(--name)` shorthand naming a Tier-1 primitive that has a
 * role: `p-(--space-6)`, `bg-(--neutral-800)`, and with a type hint,
 * `text-(length:--text-lg)`. The same tier skip as a stock palette class,
 * spelled so the palette rule cannot see it. The prefixes, the page-rhythm
 * roles under --space- and the null-outs are the spec's (design-rules.json:
 * tiers), so `p-(--space-section)` and `shadow-(--shadow-none)` pass, as they
 * do in the audit and stylelint. */
const TIER1_SHORTHAND = new RegExp(
  String.raw`\((?:[a-z-]+:)?--(?!(?:${[...TIER2_EXCEPTIONS, ...TIER1_NULLS].map((n) => n.slice(2)).join('|')})\))` +
    String.raw`(?:${Object.keys(TIER1_WITH_ROLE).join('|')})[\w-]*\)`,
);

/* The advice for a primitive that has a role, or null for anything else:
 * what `style-prop-custom-properties-only` gives an inline value (Part 3). */
const VAR_NAME = /var\(\s*(--[\w-]+)/g;
const tier1Advice = (ref) => {
  if (TIER2_EXCEPTIONS.includes(ref) || TIER1_NULLS.includes(ref)) return null;
  if (PROJECT_RAMP_STEPS.has(ref)) return PROJECT_RAMP_ADVICE;
  const prefix = Object.keys(TIER1_WITH_ROLE).find((p) => ref.slice(2).startsWith(p));
  return prefix ? TIER1_WITH_ROLE[prefix] : null;
};

/* LAW 6 again — the `(--name)` shorthand naming a step of one of the
 * project's own ramps, `bg-(--brand-500)`, or null without one. A shorthand
 * holds only `--[\w-]+`, as the audit reads it, so no other name can be in one;
 * a step TIER1_SHORTHAND already refuses (`--accent-500`) is left to it, and
 * a page-rhythm role or a null-out is not a leak. */
const SHORTHAND_STEPS = PROJECT.rampSteps.filter(
  (name) => /^--[\w-]+$/.test(name) && tier1Advice(name) && !TIER1_SHORTHAND.test(`(${name})`),
);
const PROJECT_SHORTHAND = SHORTHAND_STEPS.length
  ? new RegExp(String.raw`\((?:[a-z-]+:)?(?:${SHORTHAND_STEPS.join('|')})\)`)
  : null;

/* =========================================================================
 * PART 2 — SELECTOR SCOPES
 * =========================================================================
 * A class name reaches the DOM by four routes, and a rule that only knows
 * the first is a rule that only catches beginners:
 *
 *   1. `className="…"`                      a Literal in a JSXAttribute
 *   2. `className={cn('…', x && '…')}`      Literals inside a helper call
 *   3. `const variants = { primary: '…' }`  a lookup table, often in a
 *                                           separate file from the JSX
 *   4. `className={`px-${n}`}`              a template literal (Part 3)
 *
 * cva/tv configs are route 2 by construction, since their variant maps are
 * descendants of the `cva(...)` CallExpression.
 * ========================================================================= */

const CLASS_ATTR = "JSXAttribute[name.name=/^(className|class)$/]";

const CLASS_HELPER =
  "CallExpression[callee.name=/^(cn|clsx|classNames|classnames|cva|tv|twMerge|twJoin|cx)$/]";

/* Route 3. Matches `buttonVariants`, `cardStyles`, `rowClasses` — the
 * naming conventions a variant table actually uses. Deliberately a
 * heuristic: it costs nothing when it misses and catches the common case
 * where a variant map has drifted into a `constants.ts` nobody reviews. */
const CLASS_TABLE =
  "VariableDeclarator[id.name=/([Vv]ariants?|[Ss]tyles?|[Cc]lasses|[Cc]lassNames?)$/]";

const CLASS_SCOPES = [CLASS_ATTR, CLASS_HELPER, CLASS_TABLE];

/** Build one `no-restricted-syntax` entry per scope × node kind.
 *
 *  Both `Literal` and `TemplateElement` are needed: a class list inside
 *  backticks is a TemplateLiteral whose text lives in `TemplateElement`
 *  nodes, and a rule that only checks `Literal` misses every conditional
 *  class list written with template syntax. */
const forbidInClasses = (pattern, message) =>
  CLASS_SCOPES.flatMap((scope) => [
    { selector: `${scope} Literal[value=/${pattern.source}/]`, message },
    {
      selector: `${scope} TemplateElement[value.raw=/${pattern.source}/]`,
      message,
    },
  ]);

/* =========================================================================
 * PART 3 — LOCAL PLUGIN
 * =========================================================================
 * Two laws cannot be expressed as an esquery selector because they need to
 * inspect the SHAPE of a node, not its text. They are implemented here as
 * real rules. No placeholder, no stub — these run.
 * ========================================================================= */

/** LAW 4 — One home per component's styles.
 *
 *  The `style` prop is a second home for a component's styles, at a
 *  specificity no stylesheet can reach and in a place no audit, no theme
 *  and no media query can see. `style={{ padding: 16 }}` is unreachable by
 *  dark mode, by `[data-density]`, by print styles and by the token
 *  pipeline simultaneously.
 *
 *  THE ONE LEGITIMATE USE is passing a value only the runtime knows into
 *  CSS as a custom property, so that the STYLING still lives in the
 *  stylesheet and only the NUMBER crosses the boundary:
 *
 *      <div className="progress" style={{ '--progress': pct }} />
 *      .progress::after { inline-size: calc(var(--progress) * 1%); }
 *
 *  That is the rule: every key must start with `--`. Anything else — an
 *  identifier key, a spread whose contents cannot be seen, a computed key
 *  whose name cannot be known — is reported.
 *
 *  It also reports a custom-property whose VALUE is a design literal
 *  (`style={{ '--gap': '12px' }}`), because that is Law 1 sneaking in
 *  through Law 4's one exception. A number, an identifier, a member
 *  expression or a call is fine — those are the runtime values this
 *  exception exists for. So is a role: `{ '--gap': 'var(--gap-related)' }`.
 *  A Tier-1 primitive that has a role is not (`'var(--space-4)'`): that is
 *  Law 6 skipping a tier through the same exception. */
const stylePropCustomPropertiesOnly = {
  meta: {
    type: 'problem',
    docs: {
      description:
        'Disallow the JSX `style` attribute unless every key is a CSS custom property (Law 4)',
    },
    schema: [],
    messages: {
      stringAttr:
        'Law 4 (one home per component\'s styles): `style="…"` is not valid JSX and is never the right home for styles. Move this to the component stylesheet.',
      notAnObject:
        'Law 4 (one home per component\'s styles): the `style` prop must be an inline object literal so its keys can be checked. A style object built elsewhere hides arbitrary CSS from every audit. Move the styling to the component stylesheet and pass only runtime numbers as `--custom-properties`.',
      spread:
        'Law 4 (one home per component\'s styles): a spread in `style` hides its keys from the audit. Enumerate the custom properties you actually need.',
      computedKey:
        'Law 4 (one home per component\'s styles): a computed key in `style` cannot be verified to be a custom property. Use a literal `"--name"` key.',
      plainProperty:
        'Law 4 (one home per component\'s styles): `{{ name }}` is a CSS property set inline, where no theme, density mode, media query or audit can reach it. The only permitted `style` keys are CSS custom properties (`--name`), used to pass a runtime value into the stylesheet.',
      literalValue:
        'Law 1 (tokens or nothing): `{{ name }}: {{ value }}` hardcodes a design value inside the one place inline styles are allowed. Pass a runtime NUMBER and do the arithmetic in CSS with calc(), or point the property at a token: `var(--gap-related)`.',
      tier1Value:
        'Law 6 (semantic before primitive): `{{ name }}: {{ value }}` reads the Tier-1 primitive `{{ ref }}`. Right value, wrong tier: use {{ advice }}.',
    },
  },
  create(context) {
    /* A design literal: a number with a unit, a raw hex, or a colour
     * function, from the spec (LITERAL_UNITS, COLOUR_FUNCTIONS), as the audit
     * reads one. Bare numbers, identifiers, member expressions and calls are
     * runtime values and are exactly what this exception exists to carry. */
    const DESIGN_LITERAL = new RegExp(
      String.raw`^-?\d*\.?\d+(?:${LITERAL_UNITS.join('|')})$|^#[0-9a-fA-F]{3,8}$` +
        String.raw`|^(?:${COLOUR_FUNCTIONS.join('|')})\(`,
    );

    const keyNameOf = (prop) => {
      if (prop.computed) return null;
      const { key } = prop;
      if (key.type === 'Identifier') return key.name;
      if (key.type === 'Literal' && typeof key.value === 'string') return key.value;
      return null;
    };

    return {
      JSXAttribute(node) {
        if (node.name.type !== 'JSXIdentifier' || node.name.name !== 'style') return;

        const value = node.value;
        if (!value) return; // bare `style` — not our business

        if (value.type === 'Literal') {
          context.report({ node, messageId: 'stringAttr' });
          return;
        }
        if (value.type !== 'JSXExpressionContainer') return;

        for (const expr of objectsOf(value.expression)) {
          if (expr.type !== 'ObjectExpression') {
            context.report({ node: expr, messageId: 'notAnObject' });
            continue;
          }
          checkObject(expr);
        }
      },
    };

    /* The value may be wrapped — `{…} as React.CSSProperties`, `satisfies`,
     * `!`, parentheses — or chosen at runtime: `span ? { … } : undefined`,
     * `on && { … }`, `a ?? { … }`. Check every object it can evaluate to;
     * `undefined`, `null` and `false` set no style at all. */
    function objectsOf(expr) {
      if (!expr) return [];
      switch (expr.type) {
        case 'TSAsExpression':
        case 'TSSatisfiesExpression':
        case 'TSNonNullExpression':
        case 'TSTypeAssertion':
        case 'ParenthesizedExpression':
          return objectsOf(expr.expression);
        case 'ConditionalExpression':
          return [...objectsOf(expr.consequent), ...objectsOf(expr.alternate)];
        case 'LogicalExpression':
          // `a && b` renders b or a falsy a; `a || b` and `a ?? b` either side.
          return expr.operator === '&&'
            ? objectsOf(expr.right)
            : [...objectsOf(expr.left), ...objectsOf(expr.right)];
        case 'Identifier':
          return expr.name === 'undefined' ? [] : [expr];
        case 'Literal':
          return expr.value === null || expr.value === false ? [] : [expr];
        default:
          return [expr];
      }
    }

    function checkObject(expr) {
        for (const prop of expr.properties) {
          if (prop.type === 'SpreadElement' || prop.type === 'ExperimentalSpreadProperty') {
            context.report({ node: prop, messageId: 'spread' });
            continue;
          }
          const name = keyNameOf(prop);
          if (name === null) {
            context.report({ node: prop, messageId: 'computedKey' });
            continue;
          }
          if (!name.startsWith('--')) {
            context.report({ node: prop, messageId: 'plainProperty', data: { name } });
            continue;
          }
          const v = prop.value;
          if (
            v &&
            v.type === 'Literal' &&
            typeof v.value === 'string' &&
            DESIGN_LITERAL.test(v.value.trim())
          ) {
            context.report({
              node: v,
              messageId: 'literalValue',
              data: { name, value: v.value },
            });
          }
          if (v && v.type === 'Literal' && typeof v.value === 'string') {
            for (const [, ref] of v.value.matchAll(VAR_NAME)) {
              const advice = tier1Advice(ref);
              if (advice) {
                context.report({
                  node: v,
                  messageId: 'tier1Value',
                  data: { name, value: v.value, ref, advice },
                });
              }
            }
          }
        }
    }
  },
};

/** LAW 1 — Dynamic class construction.
 *
 *  Tailwind does not execute your code; it reads your files with a regex.
 *  `` `text-${tone}-500` `` is not a class name in any file, so no CSS is
 *  generated and the element renders unstyled. The failure is invisible in
 *  dev (the class was probably generated by some other file that happened
 *  to contain it) and appears in production after tree-shaking, which is
 *  the worst possible time to find it.
 *
 *  The tell is a template chunk that ends mid-class — with `-`, `:` or an
 *  alphanumeric — immediately before an interpolation. A chunk that ends in
 *  whitespace is fine: that is a whole class name being switched in, which
 *  is what the variant table in Part 2 route 3 exists for.
 *
 *  The fix is always the same: map to complete class names.
 *      const TONE = { danger: 'bg-danger', success: 'bg-success' } */
const noDynamicClassConstruction = {
  meta: {
    type: 'problem',
    docs: {
      description:
        'Disallow building Tailwind class names by interpolation, which the source scanner cannot see (Law 1)',
    },
    schema: [],
    messages: {
      partial:
        'Law 1 (tokens or nothing): this interpolation completes a class name ("{{ prefix }}${…}"). Tailwind scans source text and will never generate this class, so the element ships unstyled. Map to whole class names instead: `const TONE = {{ example }}`.',
    },
  },
  create(context) {
    const inClassContext = (node) => {
      for (let n = node.parent; n; n = n.parent) {
        if (
          n.type === 'JSXAttribute' &&
          n.name?.type === 'JSXIdentifier' &&
          /^(className|class)$/.test(n.name.name)
        ) {
          return true;
        }
        if (
          n.type === 'CallExpression' &&
          n.callee?.type === 'Identifier' &&
          /^(cn|clsx|classNames|classnames|cva|tv|twMerge|twJoin|cx)$/.test(n.callee.name)
        ) {
          return true;
        }
      }
      return false;
    };

    return {
      TemplateLiteral(node) {
        if (node.expressions.length === 0) return;
        if (!inClassContext(node)) return;

        node.expressions.forEach((_, i) => {
          const raw = node.quasis[i]?.value?.raw ?? '';
          if (raw.length === 0) return; // interpolation at the very start
          if (/[\s]$/.test(raw)) return; // whole class being switched in — fine
          const prefix = raw.slice(Math.max(0, raw.length - 24));
          context.report({
            node: node.quasis[i],
            messageId: 'partial',
            data: { prefix, example: "{ danger: 'bg-danger' }" },
          });
        });
      },
    };
  },
};

const designLaws = {
  meta: { name: 'design-laws', version: '1.0.0' },
  rules: {
    'style-prop-custom-properties-only': stylePropCustomPropertiesOnly,
    'no-dynamic-class-construction': noDynamicClassConstruction,
  },
};

/* =========================================================================
 * PART 4 — THE CONFIG
 * ========================================================================= */

/** Accessibility. Law 8 (a novel pattern passes a usability gate) has a
 *  floor, and this is it: a pattern that cannot be operated by keyboard or
 *  announced by a screen reader has not passed any gate.
 *
 *  `jsx-a11y` ships most of its recommended set as `warn`. Warnings are
 *  suggestions. The escalations below are the rules that map to an actual
 *  WCAG failure a client can be sued over, or to a control a keyboard user
 *  simply cannot reach — those are errors. */
const a11yConfig = {
  name: 'design-laws/a11y',
  ...jsxA11y.flatConfigs.recommended,
  rules: {
    ...jsxA11y.flatConfigs.recommended.rules,

    /* WCAG 1.1.1 — non-text content. An unlabelled image or icon button is
     * a dead end for a screen reader, and an icon-only button is the single
     * most common unlabelled control in agency work. */
    'jsx-a11y/alt-text': 'error',
    'jsx-a11y/anchor-has-content': 'error',
    'jsx-a11y/heading-has-content': 'error',

    /* WCAG 2.1.1 — keyboard. A `<div onClick>` is invisible to Tab, to
     * Enter, to Space and to voice control. Use a `<button>`. */
    'jsx-a11y/click-events-have-key-events': 'error',
    'jsx-a11y/no-static-element-interactions': 'error',
    'jsx-a11y/no-noninteractive-element-interactions': 'error',
    'jsx-a11y/interactive-supports-focus': 'error',

    /* WCAG 4.1.2 — name, role, value. A wrong `role` or an invalid ARIA
     * attribute is worse than none: it lies to assistive tech confidently. */
    'jsx-a11y/aria-props': 'error',
    'jsx-a11y/aria-proptypes': 'error',
    'jsx-a11y/aria-role': 'error',
    'jsx-a11y/aria-unsupported-elements': 'error',
    'jsx-a11y/role-has-required-aria-props': 'error',
    'jsx-a11y/role-supports-aria-props': 'error',
    'jsx-a11y/no-redundant-roles': 'error',

    /* WCAG 1.3.1 / 3.3.2 — a form control with no programmatic label.
     * Placeholder text is not a label; it disappears on focus. */
    'jsx-a11y/label-has-associated-control': [
      'error',
      { assert: 'either', depth: 3 },
    ],

    /* An <a> must go somewhere: `anchor-is-valid` refuses one with no
     * href, `#` or `javascript:`, which is a button pretending. It does not
     * read link text: "Click here" (WCAG 2.4.4) is review's, since
     * `anchor-ambiguous-text` is off. */
    'jsx-a11y/anchor-is-valid': 'error',

    /* Focus must never be removed without a replacement. Our replacement is
     * the `focus-ring` utility; `outline: none` on its own is a WCAG 2.4.7
     * failure and the fastest way to make a site unusable by keyboard. */
    'jsx-a11y/no-autofocus': 'error',
    'jsx-a11y/tabindex-no-positive': 'error',

    /* WCAG 2.2.2 — motion: `<marquee>` and `<blink>`, including the ones a
     * designer asked for. */
    'jsx-a11y/no-distracting-elements': 'error',
    /* WCAG 1.2.2 — captions: <audio> and <video> carry a captions track. */
    'jsx-a11y/media-has-caption': 'error',
  },
};

/** The product-wide `no-restricted-syntax` entries.
 *
 *  Hoisted into a constant because flat config REPLACES a rule's options
 *  rather than merging them. A later config block that sets
 *  `no-restricted-syntax` for component files would otherwise silently drop
 *  every entry below for exactly the files that need them most. This is the
 *  single most common way a flat config quietly stops enforcing something;
 *  compose the arrays, never re-declare the rule. */
const CORE_RESTRICTED_SYNTAX = [
      ...forbidInClasses(
        ARBITRARY_VALUE,
        'Law 1 (tokens or nothing) + Law 3 (the scale is closed): Tailwind arbitrary values are banned. ' +
          'A value typed into a class attribute traces to nothing, survives no rebrand, and is invisible to the token audit. ' +
          'Use a role class (p-card, gap-related, text-h2, rounded-panel). ' +
          'If no role fits, the answer is a new Tier-2 token in tokens.css and a line in theme.css — not a bracket. ' +
          'Arbitrary VARIANTS (data-[…], aria-[…], group-[…], has-[…], supports-[…]) are allowed; they carry state, not values.'
      ),

      ...forbidInClasses(
        ARBITRARY_PROPERTY,
        'Law 1 (tokens or nothing): an arbitrary property ([prop:value]) is a CSS declaration smuggled into a class attribute — ' +
          'undiscoverable, un-themeable, and invisible to every audit that reads CSS. ' +
          'Add an @utility in theme.css, or put the declaration in the component stylesheet.'
      ),

      ...forbidInClasses(
        IMPORTANT_MODIFIER,
        'Law 5 (layers, not specificity): `!important` is banned in both spellings (!class and class!). ' +
          'An `!` means two rules are fighting. Move the loser into the right layer — the order is ' +
          'reset, tokens, base, layout, components, utilities, overrides, and `overrides` exists so a genuine one-off never needs force.'
      ),

      ...forbidInClasses(
        STOCK_PALETTE,
        'Law 6 (semantic before primitive): stock Tailwind palette classes are banned. ' +
          'They are Tier-1 primitives — a component reading one has skipped the role layer, and it will not follow dark mode. ' +
          'With theme.css loaded these generate NO CSS at all, so the element ships with no background. ' +
          'Use the role: bg-surface, bg-sunken, text-muted, text-strong, border-line, bg-danger, text-danger-fg.'
      ),

      ...forbidInClasses(
        NUMERIC_SPACING,
        'Law 3 (the scale is closed) + Law 6 (semantic before primitive): numeric spacing steps are banned. ' +
          'p-4 says how many pixels; p-card says what the thing is, and follows [data-density] for free. ' +
          'Use the proximity ladder (gap-fused, gap-tight, gap-related, gap-grouped, gap-separate, gap-distinct) ' +
          'and the inset roles (p-card, p-card-lg, p-well, px-inline-md, py-block-sm). p-0 and p-px are on the scale.'
      ),

      ...forbidInClasses(
        LITERAL_UTILITY,
        'Law 1 (tokens or nothing): a bare number in duration-*, delay-*, z-*, border-*, ring-* or *-offset-* is a literal. ' +
          'Tailwind generates these whatever the theme says, so the closed scale does not remove them. ' +
          'Use the role: motion-hover / motion-enter, z-dropdown / z-modal, border-stroke / border-thick, focus-ring.'
      ),

      ...forbidInClasses(
        OPACITY_MODIFIER,
        'Law 1 (tokens or nothing): a /NN opacity modifier is a literal alpha. ' +
          'Translucency has roles — bg-hover, bg-active, the scrim role — so dark mode and contrast checks can reach it.'
      ),

      ...forbidInClasses(
        TIER1_SHORTHAND,
        'Law 6 (semantic before primitive): (--space-6), (--neutral-800) and friends read a Tier-1 primitive. ' +
          'Use the role class (p-card, bg-surface), or the role variable: p-(--pad-card).'
      ),

      ...(PROJECT_SHORTHAND
        ? forbidInClasses(
            PROJECT_SHORTHAND,
            "Law 6 (semantic before primitive): this reads a step of one of the project's own ramps " +
              `(.design-suite.json). Right value, wrong tier: use ${PROJECT_RAMP_ADVICE}.`
          )
        : []),

      ...forbidInClasses(
        SPACE_BETWEEN,
        'Law 2 (parents own the gaps): space-x-*, space-y-* and divide-* set a margin or border on every child but the first. ' +
          'That breaks when the row wraps, inverts under flex-row-reverse, and misplaces itself under order-*. ' +
          'Put `gap-*` on the parent: one declaration, no :not(:first-child), correct in every direction.'
      ),

      /* ---- Law 1 — color literals anywhere in JS/TS ------------------- */
      {
        selector: `Literal[value=/${RAW_COLOR.source}/]`,
        message:
          'Law 1 (tokens or nothing): a color literal in JavaScript. ' +
          'Chart configs, canvas fills and SVG props are still product surfaces, and a literal there ignores dark mode silently. ' +
          'Read the token — getComputedStyle(el).getPropertyValue("--bg-accent") — or pass it through a CSS custom property and let CSS resolve it. ' +
          'Every color in this product lives in tokens.css.',
      },
      {
        selector: `TemplateElement[value.raw=/${RAW_COLOR.source}/]`,
        message:
          'Law 1 (tokens or nothing): a color literal in a template string. See tokens.css — every color has a role name.',
      },

      /* ---- Law 5 — no IDs as styling hooks --------------------------- */
      {
        selector: "JSXAttribute[name.name='id'] Literal[value=/^(js-|style-|the-)/]",
        message:
          'Law 5 (layers, not specificity): an id used as a styling or scripting hook. ' +
          'An id selector outranks every class and every layer, so it can only be beaten by another id or by !important. ' +
          'Use a data attribute (data-testid, data-state) or a class.',
      },
];

/** Rules that apply to every JSX/TSX file in the product. */
const coreConfig = {
  name: 'design-laws/core',
  files: ['**/*.{js,jsx,ts,tsx}'],
  plugins: { 'design-laws': designLaws },
  rules: {
    /* ---- Law 4 — one home per component's styles ---------------------- */
    'design-laws/style-prop-custom-properties-only': 'error',

    /* ---- Law 1 — the scanner cannot see interpolated class names ------ */
    'design-laws/no-dynamic-class-construction': 'error',

    /* ---- Laws 1, 3, 5, 6 — text patterns in class lists --------------- */
    'no-restricted-syntax': ['error', ...CORE_RESTRICTED_SYNTAX],

    /* ---- Law 1 — the CSS-in-JS escape hatch --------------------------
     * styled-components, emotion, @stitches and friends are a second home
     * for styles with their own scale, their own theme object and their own
     * runtime. Two systems, one product. If a project is already on one,
     * delete this entry and point its theme object at tokens.css instead —
     * but do not add one to a project that is not. */
    'no-restricted-imports': [
      'error',
      {
        paths: [
          {
            name: 'styled-components',
            message:
              'Law 1 + Law 4: CSS-in-JS is a second styling home with a second scale. Styles live in the component stylesheet; values live in tokens.css.',
          },
          {
            name: '@emotion/styled',
            message:
              'Law 1 + Law 4: CSS-in-JS is a second styling home with a second scale. Styles live in the component stylesheet; values live in tokens.css.',
          },
          {
            name: '@emotion/react',
            message:
              'Law 1 + Law 4: CSS-in-JS is a second styling home with a second scale. Styles live in the component stylesheet; values live in tokens.css.',
          },
        ],
        patterns: [
          {
            group: ['tailwindcss/colors', 'tailwindcss/defaultTheme'],
            message:
              'Law 6 (semantic before primitive): importing Tailwind\'s stock theme reintroduces the scale theme.css deliberately deleted. The palette is tokens.css.',
          },
        ],
      },
    ],
  },
};

/** Law 2 is stricter inside component directories than in page layout.
 *
 *  A COMPONENT must not know what is next to it. It renders at its natural
 *  size and the parent decides the spacing; that is the whole reason a card
 *  can be dropped into a grid, a sidebar or a modal without edits. A
 *  component that sets `mt-related` on itself has hardcoded one context and
 *  will be wrong in the other two.
 *
 *  A LAYOUT file is the parent, so it is allowed to place things — though
 *  even there `gap` is almost always the better tool, and a margin is worth
 *  a second look.
 *
 *  ESCAPE HATCH, documented so it is visible rather than silent:
 *
 *      {/* eslint-disable-next-line no-restricted-syntax --
 *          Law 2 escape: optical alignment. The icon's bounding box sits
 *          1px below its visual centre at this size; no gap can express
 *          that. Reviewed by <name>, <date>. *\/}
 *
 *  If the justification is not a sentence about optics or a documented
 *  browser bug, it is not an escape hatch, it is a shortcut. */
const componentConfig = {
  name: 'design-laws/components',
  files: [
    '**/components/**/*.{jsx,tsx}',
    '**/ui/**/*.{jsx,tsx}',
    'packages/ui/**/*.{jsx,tsx}',
    (file) => /\.[jt]sx$/.test(file) && PROJECT.isComponent(file),  // the project's `components` (N37)
  ],
  rules: {
    /* Note the spread of CORE_RESTRICTED_SYNTAX. Without it, this block
     * would replace the rule's options wholesale and component files — the
     * files this whole system exists to protect — would stop being checked
     * for arbitrary values, !important and off-scale spacing entirely. */
    'no-restricted-syntax': [
      'error',
      ...CORE_RESTRICTED_SYNTAX,
      ...forbidInClasses(
        OUTER_MARGIN,
        'Law 2 (parents own the gaps): a component must not set its own outer margin. ' +
          'It has hardcoded one context and will be wrong in every other one — a card with mt-related is wrong in a grid, a sidebar and a modal. ' +
          'Render at natural size and let the parent space you with `gap-*`. ' +
          '`mx-auto` and `m-auto` are allowed: that is a container centring itself, not a child pushing a sibling.'
      ),
    ],
  },
};

/* =========================================================================
 * PART 5 — TAILWIND PLUGIN SETTINGS
 * =========================================================================
 * `eslint-plugin-tailwindcss` has two lines, and they learn the class
 * universe from different places (registry and README, 2026-09):
 *
 *   - 4.x (4.4.0) is made for Tailwind v4. It reads the CSS entry named by
 *     `settings.tailwindcss.cssConfigPath`, the file that imports
 *     tailwindcss and theme.css. `no-custom-classname` is the valuable rule
 *     there: v4 generates nothing for a class that does not exist and says
 *     nothing, so a misspelt role class ships as a silent no-op.
 *
 *   - 3.x reads a v3 `tailwind.config.js`, including the classes its
 *     plugins add with `addUtilities`. A v3 project must pin it
 *     (`npm i -D eslint-plugin-tailwindcss@3`): an unpinned install now
 *     brings 4.x, which requires tailwindcss ^4. After `corePlugins: {
 *     space: false }` and a replaced scale, `no-custom-classname` catches a
 *     large and useful set of classes that simply do not exist. 3.18 cannot
 *     find tailwindcss from a relative config path ("Could not resolve
 *     tailwindcss"), and ESLint 10 loads this file from whichever folder it
 *     is linting, so the block anchors the path at the project: the nearest
 *     folder above this file that holds a package.json.
 *
 * Neither plugin knows the classes your own CSS defines. `ownClasses` lists
 * the starter's layout primitives (`stack`, `cluster--tight`,
 * `with-sidebar__rail`) and its `u-*` utilities; add each of your
 * components' blocks the same way before you make the rule an error, or
 * every one of them is reported. Keep each entry self-contained: 4.x reads
 * an entry as `^entry$`, so a bare `a|b` would pass any class starting with
 * `a`.
 *
 * The suite's tests run both blocks below, uncommented, through the real
 * plugin (4.4 with Tailwind 4.3, 3.18 with Tailwind 3.4), from a folder
 * above the project, over the starter's own classes and a set of typos.
 *
 * Either way, the custom rules in Part 3 and the selector rules in Part 4
 * already cover arbitrary values, `!important`, off-scale spacing and stock
 * palette classes. The plugin adds `no-custom-classname`,
 * `no-contradicting-classname` (`p-card p-card-lg` on one element) and
 * `enforces-shorthand` (`pt-card pb-card` → `py-card`).
 *
 * `prettier-plugin-tailwindcss` is a separate, unconditional requirement
 * and works on both versions. Class ORDER is not enforced by this file and
 * must not be: a lint rule that reorders class names produces a diff on
 * every file and an argument in every review. Prettier sorts on save, the
 * order stops being a decision, and Law 5's "layout → box → typography →
 * visual → interactive → state" reading order is simply what the formatter
 * produces.
 * ========================================================================= */

// import tailwind from 'eslint-plugin-tailwindcss';
//
// // The classes your own CSS defines, which neither plugin can know (see
// // the note above). Add your components' blocks, one entry each.
// const ownClasses = [
//   '(?:band|bleed-(?:full|prose|wide)|center|cluster|cover|flow|frame|grid|imposter(?:-anchor)?'
//     + '|media-object|page-grid|page-shell|prose|reel|region(?:-compact)?|row|sections|skip-link'
//     + '|split|stack|subsections|switcher|with-sidebar)(?:__[a-z0-9-]+)?(?:--[a-z0-9-]+)?',
//   'u-[a-z0-9-]+',
// ];
//
// Tailwind v4, eslint-plugin-tailwindcss@4:
// const tailwindConfig = {
//   name: 'design-laws/tailwind',
//   files: ['**/*.{jsx,tsx}'],
//   plugins: { tailwindcss: tailwind },
//   settings: {
//     tailwindcss: {
//       // The entry that imports tailwindcss and theme.css (stack-tailwind.md §2).
//       cssConfigPath: './src/styles/index.css',
//       // Our own composers, so the plugin lints their string arguments too.
//       functions: ['cn', 'clsx', 'classNames', 'cva', 'tv', 'twMerge', 'cx'],
//     },
//   },
//   rules: {
//     // Law 3: a class the theme does not generate is off the scale, and v4
//     // drops it without a word.
//     'tailwindcss/no-custom-classname': ['error', { whitelist: ownClasses }],
//     // Law 3: `p-card p-card-lg` — two values for one property; the one
//     // that wins is whichever Tailwind emits last, not the one written
//     // last. (`p-card px-inline-md` is not a conflict: the longhand
//     // always follows the shorthand.)
//     'tailwindcss/no-contradicting-classname': 'error',
//     // Readability: `pt-card pb-card` is `py-card`.
//     'tailwindcss/enforces-shorthand': 'warn',
//   },
// };
//
// Tailwind v3, eslint-plugin-tailwindcss@3:
// import fs from 'node:fs';
// import path from 'node:path';
// // The project: the nearest folder above this file with a package.json.
// let project = import.meta.dirname;
// while (!fs.existsSync(path.join(project, 'package.json')) && path.dirname(project) !== project) {
//   project = path.dirname(project);
// }
// const tailwindV3Config = {
//   name: 'design-laws/tailwind-v3',
//   files: ['**/*.{jsx,tsx}'],
//   plugins: { tailwindcss: tailwind },
//   settings: {
//     tailwindcss: {
//       // Absolute, so it holds from any folder ESLint runs in (see the note above).
//       config: path.join(project, 'tailwind.config.ts'),
//       // Our own composers, so the plugin lints their string arguments too.
//       callees: ['cn', 'clsx', 'classNames', 'cva', 'tv', 'twMerge', 'cx'],
//     },
//   },
//   rules: {
//     // Law 3: a class that does not exist in the theme is, by definition,
//     // off the scale. 3.x also learns the classes the config's plugins add
//     // with `addUtilities` (focus-ring, tap-target, motion-*).
//     'tailwindcss/no-custom-classname': ['error', { cssFiles: [], whitelist: ownClasses }],
//     // Law 3: `p-card p-card-lg` — two values for one property; the one
//     // that wins is whichever Tailwind emits last, not the one written
//     // last. (`p-card px-inline-md` is not a conflict: the longhand
//     // always follows the shorthand.)
//     'tailwindcss/no-contradicting-classname': 'error',
//     // Readability: `pt-card pb-card` is `py-card`.
//     'tailwindcss/enforces-shorthand': 'warn',
//     // Law 3: no arbitrary values. Part 3 bans them too; belt and braces.
//     'tailwindcss/no-arbitrary-value': 'error',
//   },
// };

/* =========================================================================
 * EXPORTS
 * =========================================================================
 * Default export is the composed fragment, in cascade order: a11y first,
 * then the product-wide laws, then the stricter component scope. Named
 * exports are for projects that need to place them differently — for
 * instance, running `componentConfig` over a design-system package but not
 * over a marketing site in the same monorepo.
 * ========================================================================= */

export { designLaws, a11yConfig, coreConfig, componentConfig };

export default [a11yConfig, coreConfig, componentConfig];
