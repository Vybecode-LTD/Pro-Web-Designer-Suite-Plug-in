/**
 * =========================================================================
 * stylelint.config.mjs — the Nine Laws, enforced in CSS
 * =========================================================================
 *
 * The ESLint config guards the JSX side; this guards the stylesheet side.
 * Between them there is no route from a design value to the browser that
 * does not pass through tokens.css.
 *
 * PEER DEPENDENCIES
 *   npm i -D stylelint@^17 stylelint-config-standard@^40
 *
 *   stylelint-config-standard 40 requires stylelint ^17, so pairing it with
 *   stylelint 16 stops npm with ERESOLVE. Stylelint 17 needs Node 20.19+.
 *   It also reads nesting differently. The selector-max-* rules below check
 *   each nested selector as written instead of desugaring it, and `&` takes
 *   the largest specificity in its parent's list. So the limits apply per
 *   written selector, and `max-nesting-depth` caps the nesting itself.
 *   (stylelint.io/migration-guide/to-17. The suite's tests run this file
 *   through stylelint 17.15 with stylelint-config-standard 40.0, over the
 *   starter's own stylesheets.)
 *
 *   package.json
 *     "lint:css": "stylelint \"src/**\/*.css\" \"packages/**\/*.css\""
 *
 * WHY AN ALLOWLIST AND NOT A DENYLIST
 * -----------------------------------
 * A denylist enumerates the mistakes you have already seen. An allowlist
 * enumerates what is correct, which is a much shorter list and, crucially,
 * one that does not need updating every time someone invents a new way to
 * be wrong. `padding: 13px` and `padding: 0.8125rem` and
 * `padding: clamp(12px, 2vw, 14px)` are three spellings of one mistake; an
 * allowlist of `var(--…)` catches all three and the fourth nobody has
 * thought of yet.
 *
 * Every rule below is `error`. See the severity note in
 * eslint.design.config.mjs: a design-system warning is a suggestion.
 * ========================================================================= */

import stylelint from 'stylelint';

/* =========================================================================
 * PART 1 — THE CANONICAL LAYER ORDER (LAW 5)
 * ========================================================================= */

/* The layers, weakest first:
 *   reset       Preflight / normalize. Beaten by literally everything.
 *   vendor      CSS you do not control, imported with layer(vendor). Named
 *               even before there is any: a layer first named by its import
 *               lands after overrides and beats everything (SB-A8).
 *   tokens      tokens.css. Declarations only, no selectors that paint.
 *   theme       Tailwind's generated @theme output (v4 only).
 *   base        element defaults: html, body, headings, links.
 *   layout      page-level primitives: stack, grid, sidebar, gutter.
 *   components  one file per component. The bulk of hand-written CSS.
 *   utilities   Tailwind's utilities. Must beat components, or a `p-card-lg`
 *               on a `.card` would lose to the card's own padding and the
 *               utility would appear not to work.
 *   overrides   the documented one-off. Last, so it needs no !important.
 * The order, the nesting depth and the system colours below come from
 * assets/rules/design-rules.json. */
// BEGIN design-rules: written by tools/sync_rules.py from assets/rules/design-rules.json; edit the spec, then rerun it
const LAYER_ORDER = [
  'reset', 'vendor', 'tokens', 'theme', 'base', 'layout', 'components', 'utilities', 'overrides',
];
const MAX_NESTING = 2;
const SYSTEM_COLOR_NAMES = [
  'accentcolor', 'accentcolortext', 'activetext', 'buttonborder', 'buttonface', 'buttontext',
  'canvas', 'canvastext', 'field', 'fieldtext', 'graytext', 'highlight', 'highlighttext',
  'linktext', 'mark', 'marktext', 'selecteditem', 'selecteditemtext', 'visitedtext',
];
// END design-rules

/* =========================================================================
 * PART 2 — LOCAL PLUGIN: LAYER ORDER (LAW 5)
 * =========================================================================
 * Stylelint has no core rule for this. It matters enough to write one.
 *
 * Getting the layer STATEMENT wrong is the quietest possible failure: a
 * layer that is used before it is named is appended to the end of the order
 * in first-use order, so a stylesheet that "works on my machine" reorders
 * itself the moment an import order changes or a bundler splits a chunk.
 * The symptom is a component that is correct in dev and wrong in
 * production, which is the most expensive class of bug an agency ships.
 *
 * Two checks:
 *   1. The file declares layers in the canonical order — extra layers may
 *      be omitted from the middle, but the ones present must not be out of
 *      sequence, and there must be exactly one statement.
 *   2. Every `@layer name { … }` block uses a name from the list. A typo
 *      (`@layer component {`) creates a brand new last-place layer and
 *      wins every cascade fight silently.
 * ========================================================================= */

const { createPlugin, utils } = stylelint;
const layerRuleName = 'design/layer-order';

const layerMessages = utils.ruleMessages(layerRuleName, {
  outOfOrder: (found, expected) =>
    `Law 5 (layers, not specificity): @layer statement declares "${found}" but the canonical order is "${expected}". ` +
    `Layers are ranked by the order they are FIRST NAMED, so a wrong statement silently reranks the whole stylesheet.`,
  duplicateStatement: () =>
    `Law 5 (layers, not specificity): more than one @layer statement in this file. ` +
    `Only the first establishes the order; the rest are no-ops that read as if they do something. Declare the order once, in the entry stylesheet.`,
  unknownLayer: (name) =>
    `Law 5 (layers, not specificity): "@layer ${name}" is not one of [${LAYER_ORDER.join(', ')}]. ` +
    `An undeclared layer is appended AFTER every declared one, so this rule now beats utilities and overrides. ` +
    `If the layer is real, add it to the canonical order; if it is a typo, it is the most expensive kind.`,
  undeclaredImport: (name) =>
    `Law 5 (layers, not specificity): \`layer(${name})\` imports into a layer the @layer statement does not name. ` +
    `A layer first named by its import is appended after overrides, so these rules beat every rule you write. Name it in the statement.`,
  importBeforeStatement: (name) =>
    `Law 5 (layers, not specificity): \`layer(${name})\` comes before the @layer statement, so it names "${name}" first ` +
    `and the statement no longer decides where it goes. Move the statement above every @import.`,
  ruleBeforeStatement: () =>
    `Law 5 (layers, not specificity): a rule comes before the @layer statement. A layer's position is fixed the first time ` +
    `its name is used, so the statement must be the first thing in the entry stylesheet, before every @import and every rule.`,
  nestedLayer: (name) =>
    `Law 5 (layers, not specificity): "@layer ${name}" nested inside another layer creates a sub-layer whose rank is not obvious from the order statement. Flatten it.`,
});

const layerOrderRule = (primary) => (root, result) => {
  if (!utils.validateOptions(result, layerRuleName, { actual: primary, possible: [true] })) {
    return;
  }

  let seenStatement = false;
  let statement = null;
  const declaredNames = new Set();

  root.walkAtRules(/^layer$/i, (atRule) => {
    /* A STATEMENT has no block: `@layer a, b, c;` */
    const isStatement = atRule.nodes === undefined;

    if (isStatement) {
      if (seenStatement) {
        utils.report({
          message: layerMessages.duplicateStatement(),
          node: atRule,
          result,
          ruleName: layerRuleName,
        });
        return;
      }
      seenStatement = true;
      statement = atRule;

      const declared = atRule.params
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
      declared.forEach((name) => declaredNames.add(name));

      /* Subsequence check: omitting a layer is fine, reordering is not. */
      let cursor = -1;
      let ordered = true;
      for (const name of declared) {
        const idx = LAYER_ORDER.indexOf(name);
        if (idx === -1) {
          utils.report({
            message: layerMessages.unknownLayer(name),
            node: atRule,
            result,
            ruleName: layerRuleName,
          });
          ordered = false;
          break;
        }
        if (idx <= cursor) {
          ordered = false;
          break;
        }
        cursor = idx;
      }
      if (!ordered) {
        utils.report({
          message: layerMessages.outOfOrder(declared.join(', '), LAYER_ORDER.join(', ')),
          node: atRule,
          result,
          ruleName: layerRuleName,
        });
      }
      return;
    }

    /* A BLOCK: `@layer components { … }` */
    const name = atRule.params.trim();
    if (name && !LAYER_ORDER.includes(name)) {
      utils.report({
        message: layerMessages.unknownLayer(name),
        node: atRule,
        result,
        ruleName: layerRuleName,
      });
    }
    if (atRule.parent && atRule.parent.type === 'atrule' && /^layer$/i.test(atRule.parent.name)) {
      utils.report({
        message: layerMessages.nestedLayer(name),
        node: atRule,
        result,
        ruleName: layerRuleName,
      });
    }
  });

  /* An import into a layer the statement leaves out (SB-A8). */
  if (!seenStatement) return;
  const before = (node) =>
    node.source.start.line < statement.source.start.line ||
    (node.source.start.line === statement.source.start.line &&
      node.source.start.column < statement.source.start.column);
  let importAbove = null;
  root.walkAtRules(/^import$/i, (atRule) => {
    const m = /\blayer\(\s*([\w.-]+)\s*\)/i.exec(atRule.params);
    if (!m) return;
    if (!declaredNames.has(m[1])) {
      utils.report({
        message: layerMessages.undeclaredImport(m[1]),
        node: atRule,
        result,
        ruleName: layerRuleName,
      });
    }
    if (!importAbove && before(atRule)) importAbove = m[1];
  });

  /* The statement comes first: a rule above it (N29), or an import into a
     layer (N25), names its layers before the statement can. One report per
     file, as the audit's layer-statement-position. */
  let ruleAbove = false;
  root.walkRules((rule) => {
    if (before(rule)) ruleAbove = true;
  });
  if (ruleAbove || importAbove) {
    utils.report({
      message: ruleAbove
        ? layerMessages.ruleBeforeStatement()
        : layerMessages.importBeforeStatement(importAbove),
      node: statement,
      result,
      ruleName: layerRuleName,
    });
  }
};

layerOrderRule.ruleName = layerRuleName;
layerOrderRule.messages = layerMessages;
layerOrderRule.meta = { url: 'references/style-architecture.md#layers' };

const designPlugin = createPlugin(layerRuleName, layerOrderRule);

/* -------------------------------------------------------------------------
 * LOCAL RULE: SYSTEM COLOURS ONLY IN FORCED-COLORS MODE (LAW 1)
 *
 * `Canvas`, `ButtonText`, `Highlight` and the rest are the only correct
 * colours inside `@media (forced-colors: active)`: the page's palette is gone
 * and the user's is in charge, so a focus ring or a border names the system
 * colour it stands for. Anywhere else a system colour is a literal no token
 * controls, no theme re-points and no contrast check measures — `Highlight`
 * renders each user's own OS accent. The value allowlist cannot see the media
 * query, so it accepts them (COLOUR_WORDS, Part 3) and this rule refuses them
 * outside it, shorthands included (`border: 1px solid ButtonText`).
 * ------------------------------------------------------------------------- */

/* SYSTEM_COLOR_NAMES is in PART 1's design-rules block. */
const systemColorRuleName = 'design/system-colors-in-forced-colors';
const systemColorMessages = utils.ruleMessages(systemColorRuleName, {
  outside: (word) =>
    `Law 1 (tokens or nothing): "${word}" is a CSS system colour, which is right only inside ` +
    `@media (forced-colors: active). Anywhere else it is a colour no token controls, no theme re-points ` +
    `and no contrast check measures. Use a role token.`,
});
/* Properties whose values can hold a colour. Others are left alone: `canvas`
 * or `mark` may be a grid-area or an animation name. */
const COLOUR_PROPERTY = /^(?:color|fill|stroke|stop-color|flood-color|lighting-color|accent-color|caret-color|background(?:-color)?|border(?:-[a-z]+)*|outline(?:-color)?|text-decoration(?:-color)?|text-emphasis(?:-color)?|column-rule(?:-color)?|box-shadow|text-shadow)$/i;
const SYSTEM_COLOR_WORD = new RegExp(`^(?:${SYSTEM_COLOR_NAMES.join('|')})$`, 'i');

const inForcedColors = (node) => {
  for (let parent = node.parent; parent; parent = parent.parent) {
    if (parent.type === 'atrule' && /^media$/i.test(parent.name)
        && /forced-colors\s*:\s*active/i.test(parent.params)) {
      return true;
    }
  }
  return false;
};

const systemColorRule = (primary) => (root, result) => {
  if (!utils.validateOptions(result, systemColorRuleName, { actual: primary, possible: [true] })) {
    return;
  }
  root.walkDecls(COLOUR_PROPERTY, (decl) => {
    const word = decl.value.split(/[\s,/()]+/).find((w) => SYSTEM_COLOR_WORD.test(w));
    if (word && !inForcedColors(decl)) {
      utils.report({
        message: systemColorMessages.outside(word),
        node: decl,
        word,
        result,
        ruleName: systemColorRuleName,
      });
    }
  });
};

systemColorRule.ruleName = systemColorRuleName;
systemColorRule.messages = systemColorMessages;
systemColorRule.meta = { url: 'references/accessibility.md' };

const systemColorPlugin = createPlugin(systemColorRuleName, systemColorRule);

/* =========================================================================
 * PART 3 — THE VALUE ALLOWLISTS (LAW 1, LAW 3, LAW 6)
 * =========================================================================
 * `declaration-property-value-allowed-list` compares the WHOLE declaration
 * value against each entry. A plain string must match exactly; a string
 * wrapped in slashes is compiled with `new RegExp` and is UNANCHORED unless
 * you anchor it yourself — which is the single most common way these rules
 * are written too loosely to catch anything. Every regex below is anchored
 * with `^` and `$`.
 *
 * READ THE REGEXES
 * ----------------
 *   VAR_SEQ   ^(?:var\(--[a-z0-9-]+\)\s*)+$
 *             One or more `var(--token)` references, whitespace-separated,
 *             and NOTHING else. `^`…`$` means no stray literal can ride
 *             along, so `padding: var(--pad-card) 2px` is caught while
 *             `padding: var(--pad-block-md) var(--pad-inline-md)` passes.
 *             `[a-z0-9-]` also enforces the kebab-case token naming
 *             convention: `var(--padCard)` is rejected as a typo, because
 *             a `var()` pointing at a token that does not exist resolves to
 *             nothing and the declaration is dropped in silence.
 *
 *   VAR_ONE   ^var\(--[a-z0-9-]+(\s*,\s*.+)?\)$
 *             Exactly one token, with or without a fallback. Used for
 *             properties where a sequence is meaningless (`font-size`,
 *             `z-index`, `line-height`). A fallback is not checked: the
 *             token is the value (design-rules.json, var_fallback), as in
 *             audit_design.
 *
 *   CANCEL    ^calc\(\s*(var(--t)\s*\*\s*-1|-1\s*\*\s*var(--t))\s*\)$
 *             Law 2's third exception: a margin that cancels a known
 *             token, `calc(var(--card-inset) * -1)`. Only `-1`: any other
 *             factor invents a step (Law 3).
 *
 *   VAR_CALC  ^calc\(\s*var\(--[a-z0-9-]+\)\s*[-+]\s*var\(--[a-z0-9-]+\)\s*\)$
 *             A token MINUS or PLUS a token, nothing else — no bare
 *             numbers, no multiplication. This exists for exactly one job:
 *             the nested-radius rule from tokens.css §7, where inner radius
 *             = outer radius − inner padding. Multiplication is excluded on
 *             purpose: `calc(var(--space-4) * 1.5)` is inventing a step
 *             between steps, which is Law 3's whole prohibition wearing a
 *             `calc()` as a disguise. (Density scaling also multiplies —
 *             that is why it lives in tokens.css, in one place, where it is
 *             a system decision rather than a component's improvisation.)
 * ========================================================================= */

const VAR_SEQ = String.raw`/^(?:var\(--[a-z0-9-]+\)\s*)+$/`;
const VAR_ONE = String.raw`/^var\(--[a-z0-9-]+(\s*,\s*.+)?\)$/`;
const CANCEL = String.raw`/^calc\(\s*(?:var\(--[a-z0-9-]+\)\s*\*\s*-1|-1\s*\*\s*var\(--[a-z0-9-]+\))\s*\)$/`;
const VAR_CALC = String.raw`/^calc\(\s*var\(--[a-z0-9-]+\)\s*[-+]\s*var\(--[a-z0-9-]+\)\s*\)$/`;

/* CSS-wide keywords. Not design values; they are the language, and they are
 * how a component says "do not participate" rather than "be this colour". */
const KEYWORDS = ['inherit', 'initial', 'unset', 'revert', 'revert-layer'];

/* COLOUR_WORDS  The colour keywords that are not a colour from the palette,
 * in any case (CSS keywords are case-insensitive, and a plain string in this
 * rule matches one spelling only). `currentColor` and `transparent` follow
 * the text or paint nothing. The CSS system colours (`Canvas`, `ButtonText`,
 * `Highlight`…) are the only correct values in
 * `@media (forced-colors: active)`, where the user's palette replaces the
 * page's; this allowlist cannot see the media query, so the
 * design/system-colors-in-forced-colors rule (Part 2) refuses them anywhere
 * else. */
const COLOUR_WORDS = String.raw`/^(?:currentcolor|transparent|${SYSTEM_COLOR_NAMES.join('|')})$/i`;

const VALUE_ALLOWLIST = {
  /* ---- Spacing. Law 1 + Law 3 + Law 6 --------------------------------
   * `0` is on the scale (`--space-0`) and is spelled `0` far more often
   * than `var(--space-0)`; fighting that is pedantry, not rigour. Nothing
   * else unitless or unitful gets through. */
  padding: [VAR_SEQ, VAR_CALC, '0', ...KEYWORDS],
  'padding-top': [VAR_ONE, VAR_CALC, '0', ...KEYWORDS],
  'padding-right': [VAR_ONE, VAR_CALC, '0', ...KEYWORDS],
  'padding-bottom': [VAR_ONE, VAR_CALC, '0', ...KEYWORDS],
  'padding-left': [VAR_ONE, VAR_CALC, '0', ...KEYWORDS],
  'padding-inline': [VAR_SEQ, VAR_CALC, '0', ...KEYWORDS],
  'padding-block': [VAR_SEQ, VAR_CALC, '0', ...KEYWORDS],
  'padding-inline-start': [VAR_ONE, VAR_CALC, '0', ...KEYWORDS],
  'padding-inline-end': [VAR_ONE, VAR_CALC, '0', ...KEYWORDS],
  'padding-block-start': [VAR_ONE, VAR_CALC, '0', ...KEYWORDS],
  'padding-block-end': [VAR_ONE, VAR_CALC, '0', ...KEYWORDS],

  /* Law 2 lives here too: `gap` is the ONLY sanctioned way to space
   * siblings, so it had better be on-scale. */
  gap: [VAR_SEQ, '0', ...KEYWORDS],
  'row-gap': [VAR_ONE, '0', ...KEYWORDS],
  'column-gap': [VAR_ONE, '0', ...KEYWORDS],

  /* ---- Typography. Law 1 + Law 3 -------------------------------------
   * No `em`, no `%`, no `1.4`. Type size and leading are the two values
   * every project drifts on first, because "just a bit bigger" always
   * feels harmless and is never reversible.
   *
   * `1` is NOT allowed for line-height even though `--leading-none: 1`.
   * Writing the literal is how the next person learns the scale is
   * optional. */
  'font-size': [VAR_ONE, ...KEYWORDS],
  'line-height': [VAR_ONE, ...KEYWORDS],
  'letter-spacing': [VAR_ONE, 'normal', ...KEYWORDS],
  'font-weight': [VAR_ONE, ...KEYWORDS],
  'font-family': [VAR_ONE, ...KEYWORDS],
  /* The `font` shorthand is how Tier 2's `--type-*` roles are consumed:
   * `font: var(--type-h2)` sets weight, size, leading and family in one
   * declaration that cannot half-apply. */
  font: [VAR_ONE, ...KEYWORDS],

  /* ---- Radius. Law 1 -------------------------------------------------
   * `50%` is the one genuine exception: a perfect circle is a geometric
   * relationship, not a design value, and `--radius-full` (9999px) gives
   * you a pill, not a circle, on a non-square box. */
  'border-radius': [VAR_SEQ, VAR_CALC, '0', '50%', ...KEYWORDS],
  'border-start-start-radius': [VAR_ONE, VAR_CALC, '0', ...KEYWORDS],
  'border-start-end-radius': [VAR_ONE, VAR_CALC, '0', ...KEYWORDS],
  'border-end-start-radius': [VAR_ONE, VAR_CALC, '0', ...KEYWORDS],
  'border-end-end-radius': [VAR_ONE, VAR_CALC, '0', ...KEYWORDS],

  /* ---- Elevation. Law 1 + Law 6 --------------------------------------
   * Reach for `--elevation-card`, not `--shadow-sm`. A hand-written
   * shadow is always a single layer and always reads as a sticker; the
   * tokens are physically consistent PAIRS (contact + ambient). */
  'box-shadow': [VAR_ONE, 'none', ...KEYWORDS],

  /* ---- Color. Law 1 + Law 6 ------------------------------------------
   * `currentColor` and `transparent` are keywords, not colours, and the
   * system colours belong to forced-colors mode (COLOUR_WORDS). Note what
   * is NOT here: no `oklch()`, no hex, no `rgb()` — not even a "temporary"
   * one, because a hex in a component is the one thing dark mode cannot
   * follow, and it will be found six months later by a client. */
  color: [VAR_ONE, COLOUR_WORDS, ...KEYWORDS],
  'background-color': [VAR_ONE, COLOUR_WORDS, ...KEYWORDS],
  'border-color': [VAR_SEQ, COLOUR_WORDS, ...KEYWORDS],
  'outline-color': [VAR_ONE, COLOUR_WORDS, ...KEYWORDS],
  'text-decoration-color': [VAR_ONE, COLOUR_WORDS, ...KEYWORDS],
  fill: [VAR_ONE, COLOUR_WORDS, 'none', ...KEYWORDS],
  stroke: [VAR_ONE, COLOUR_WORDS, 'none', ...KEYWORDS],
  'accent-color': [VAR_ONE, 'auto', ...KEYWORDS],

  /* ---- Stacking. Law 3 -----------------------------------------------
   * The z-index ladder in tokens.css is CLOSED and ordered by what
   * occupies each rung. A literal `z-index: 9999` is not a value, it is a
   * surrender, and the next person writes 10000. */
  'z-index': [VAR_ONE, '0', 'auto', ...KEYWORDS],

  /* ---- Motion. Law 1 -------------------------------------------------
   * Duration and easing are role-paired in tokens.css ("they travel
   * together or you get drift"). `0s` is allowed for the genuine case of
   * disabling one transition among several in a shorthand list.
   *
   * Note that `prefers-reduced-motion` collapses every duration token to
   * 1ms in tokens.css. A literal `200ms` here opts the component OUT of
   * that, which is a vestibular-safety failure, not a style nit. */
  'transition-duration': [VAR_SEQ, '0s', ...KEYWORDS],
  'animation-duration': [VAR_SEQ, '0s', ...KEYWORDS],
  'transition-timing-function': [VAR_SEQ, ...KEYWORDS],
  'animation-timing-function': [VAR_SEQ, ...KEYWORDS],

  /* ---- Sizing that is really spacing. Law 1 ---------------------------
   * Line length is a spacing decision. `max-inline-size: 65ch` in a
   * component is the same mistake as `padding: 13px`, and it is the one
   * people defend hardest. */
  'max-inline-size': [VAR_ONE, 'none', '100%', 'max-content', 'min-content', 'fit-content', ...KEYWORDS],
  'max-width': [VAR_ONE, 'none', '100%', 'max-content', 'min-content', 'fit-content', ...KEYWORDS],
  /* The small- and dynamic-viewport units: `100svb` does not jump when
   * mobile browser chrome hides, which is why the page shell uses it. */
  'min-block-size': [VAR_ONE, '0', '100%', '100dvh', '100dvb', '100svh', '100svb', 'auto', ...KEYWORDS],
  'min-inline-size': [VAR_ONE, '0', '100%', 'auto', ...KEYWORDS],
};

/* Law 2, as a value allowlist rather than a property ban.
 *
 * A blanket `property-disallowed-list: [/^margin/]` would also forbid
 * `margin: 0` (a legitimate reset) and `margin-inline: auto` (a container
 * centring ITSELF, which is not a child pushing a sibling). Both are
 * correct, and a rule that flags correct code is a rule that gets switched
 * off wholesale. So: the margin properties exist, and their value set is
 * `0` and `auto`.
 *
 * This is scoped to component files in Part 5. Layout primitives are the
 * parent, and the parent is allowed to place things — though even there,
 * `gap` is almost always the better instrument. */
const MARGIN_ALLOWLIST = Object.fromEntries(
  [
    'margin',
    'margin-top',
    'margin-right',
    'margin-bottom',
    'margin-left',
    'margin-inline',
    'margin-block',
    'margin-inline-start',
    'margin-inline-end',
    'margin-block-start',
    'margin-block-end',
  ].map((prop) => [prop, ['0', 'auto', '0 auto', 'auto 0', CANCEL, ...KEYWORDS]])
);

/* =========================================================================
 * PART 4 — THE CONFIG
 * ========================================================================= */

export default {
  extends: ['stylelint-config-standard'],
  plugins: [designPlugin, systemColorPlugin],

  rules: {
    /* ---- LAW 5: layers, not specificity ------------------------------ */

    [layerRuleName]: true,

    /* ---- LAW 1: a system colour belongs to forced-colors mode -------- */

    [systemColorRuleName]: true,

    /* `!important` is the admission that the layer order is wrong. There is
     * no legitimate use in a codebase that has `overrides` as its last
     * layer — that layer exists precisely so the one-off can win by
     * position instead of by force. */
    'declaration-no-important': true,

    /* An id selector outranks every class, in every layer, forever. It can
     * only be beaten by another id or by `!important`, which is how one id
     * becomes three. Use a class or a data attribute. */
    'selector-max-id': 0,

    /* Two levels. Deeper nesting encodes the DOM shape into the
     * stylesheet, so a markup change that should be free becomes a CSS
     * change — and the specificity climbs with every level, which is the
     * same fight `!important` loses. Media queries, `@supports`, `@layer`
     * and `@container` do not count: they add no specificity. */
    'max-nesting-depth': [
      MAX_NESTING,
      {
        ignore: ['pseudo-classes'],
        ignoreAtRules: ['media', 'supports', 'layer', 'container', 'scope'],
      },
    ],

    /* Specificity should not climb as the file goes down; when it does, a
     * later rule can be beaten by an earlier one and the file stops reading
     * top-to-bottom. */
    'no-descending-specificity': true,

    /* A cap, not a preference. `.card .header .title span` is four levels
     * of DOM knowledge in one selector. */
    'selector-max-compound-selectors': 3,
    'selector-max-specificity': '0,3,1',

    /* ---- LAWS 1, 3, 6: tokens or nothing ----------------------------- */

    'declaration-property-value-allowed-list': VALUE_ALLOWLIST,

    /* Belt and braces on colour. The allowlist above covers the properties
     * that matter; these catch a hex anywhere else at all — a gradient
     * stop, a `filter: drop-shadow()`, an SVG attribute, a mask. */
    'color-no-hex': true,
    'color-named': 'never',
    'function-disallowed-list': ['rgb', 'rgba', 'hsl', 'hsla', 'hwb'],

    /* Tokens are kebab-case. A `var()` pointing at a name that does not
     * exist resolves to nothing and the declaration is dropped in silence —
     * the most expensive kind of typo, because the page still renders. */
    'custom-property-pattern': '^[a-z0-9]+(-[a-z0-9]+)*$',

    /* ---- LAW 4: one home per component's styles ---------------------- */

    /* `@apply` is banned everywhere except the allowlisted bridge file in
     * Part 5. See the long note there — this is not a style preference. */
    'at-rule-disallowed-list': ['apply'],

    /* Tailwind v4 at-rules Stylelint does not know. Listing them here is
     * also a closed list: a typo'd `@utilty` is still an error. */
    'at-rule-no-unknown': [
      true,
      {
        ignoreAtRules: [
          'theme',
          'source',
          'utility',
          'variant',
          'custom-variant',
          'plugin',
          'reference',
          'config',
          'tailwind',
          'screen',
          'apply',
        ],
      },
    ],

    /* ---- HOUSEKEEPING THAT IS ACTUALLY LAW ENFORCEMENT ---------------- */

    /* Duplicates mean two people styled the same thing and neither knew.
     * That is Law 4's failure mode showing up inside a single file. */
    'declaration-block-no-duplicate-properties': [
      true,
      { ignore: ['consecutive-duplicates-with-different-values'] },
    ],
    'no-duplicate-selectors': true,

    /* Vendor prefixes come from the build, not from hand. A hand-written
     * prefix is a value the audit cannot see. */
    'property-no-vendor-prefix': true,
    'value-no-vendor-prefix': true,

    /* stylelint-config-standard opinions that fight Tailwind's generated
     * output and custom-property-heavy authoring. Off, with reasons. */

    /* Formatting is Prettier's job. A formatting rule in the design gate
     * only teaches people that the gate cries wolf. */
    'custom-property-empty-line-before': null,
    'declaration-empty-line-before': null,
    'comment-empty-line-before': null,
    'at-rule-empty-line-before': null,
    'rule-empty-line-before': null,
    'comment-whitespace-inside': null,
    /* `.row--start { --row-align: flex-start; }` on one line is a table of
     * modifiers, and it is how layout.css lists them. Line breaks are
     * formatting. */
    'declaration-block-single-line-max-declarations': null,

    /* The references spell imports both ways: `@import url("./tokens.css")
     * layer(tokens)` in the vanilla and CSS-modules entries, and
     * `@import "tailwindcss/theme.css" layer(theme)` in the Tailwind entry
     * (stack-tailwind.md §2). The standard config's `url` notation refused
     * the second; `string` would refuse the first. The spelling is not a
     * design law. */
    'import-notation': null,

    /* Font stack names are proper nouns: "Geist Sans", "SFMono-Regular",
     * "Segoe UI". Lowercasing them is wrong, and it is the only place this
     * rule fires in a token-driven codebase. */
    'value-keyword-case': null,

    /* OKLCH hue is an angle written as a bare number — `oklch(64.5% 0.188
     * 42)`. That is the spelling the generator emits and the one the CSS
     * Color 4 examples use; `42deg` is legal but nobody writes it, and a
     * rule that rewrites every ramp step is a rule that gets turned off. */
    'hue-degree-notation': null,

    /* `oklch(0% 0 0 / 0.05)` is clearer than `/ 5%` for a shadow alpha,
     * and the shadow tokens are the only alphas in the system. */
    'alpha-value-notation': null,
    /* Our class names are role names, not BEM; the standard pattern would
     * reject `.card__title` and `.focus-ring` alike. */
    'selector-class-pattern': null,
    /* `@media (width >= 48rem)` range syntax is the modern spelling and the
     * standard config's media-feature rules do not all understand it. */
    'media-feature-range-notation': null,
  },

  /* =======================================================================
   * PART 5 — OVERRIDES
   * =======================================================================
   * Each block below is a documented exemption. There are four, and the
   * list should not grow: every addition is a place the laws stop applying,
   * and the whole value of the system is that the answer to "where can I
   * put a literal?" is a short list somebody can hold in their head.
   * ===================================================================== */

  overrides: [
    /* ---------------------------------------------------------------------
     * 1. tokens.css — the ONE file where literals live (Law 1).
     *
     * This is the definition of Law 1, not an exception to it: "literals
     * live only in tokens.css". Every rule that bans a raw value is
     * switched off here and nowhere else, which is what makes the file
     * meaningful — there is exactly one place to look, and one file to
     * review when a brand changes.
     * ------------------------------------------------------------------ */
    {
      files: ['**/tokens.css', '**/*-tokens.css', '**/*.tokens.css', '**/tokens/*.css'],
      rules: {
        'declaration-property-value-allowed-list': null,
        'color-no-hex': null,
        'color-named': null,
        'function-disallowed-list': null,
        /* Tier-1 steps are `--space-0-5`, `--text-2xs`, `--radius-2xl`:
         * digits inside segments, which the strict pattern rejects. */
        'custom-property-pattern': '^[a-z0-9]+(-[a-z0-9]+)*$',
        /* `no-duplicate-selectors` stays ON: a second `[data-theme="dark"]`
         * block that quietly redefines a token is the bug it catches. The
         * starter opens one `:root` block per tier (primitives, roles, …)
         * and marks each repeat with a disable comment that says so. */
      },
    },

    /* ---------------------------------------------------------------------
     * 2. theme.css / tailwind bindings — the binding layer.
     *
     * Allowed the four literal exceptions documented in theme.css §0
     * (breakpoints, CSS-wide keywords, keyframe geometry, aspect ratios)
     * and nothing else. `color-no-hex` stays ON: a breakpoint has to be a
     * literal because media queries cannot read custom properties; a colour
     * never has to be.
     * ------------------------------------------------------------------ */
    {
      files: ['**/theme.css', '**/*-theme.css'],
      rules: {
        'declaration-property-value-allowed-list': null,
        'custom-property-pattern': null, // `--text-h1--line-height` is Tailwind's syntax
        'at-rule-disallowed-list': null,
      },
    },

    /* ---------------------------------------------------------------------
     * 3. COMPONENT FILES — Law 2, at its strictest.
     *
     * A component must not know what is next to it. It renders at its
     * natural size; the parent decides the spacing. That is the entire
     * reason a card can be dropped into a grid, a sidebar or a modal
     * without edits, and a component that sets `margin-block-start` on
     * itself has hardcoded one of those three and will be wrong in the
     * other two.
     *
     * What does NOT need an escape hatch: cancelling a known token is Law
     * 2's third exception and legal in both gates, e.g.
     * `margin-block-start: calc(var(--stroke-hairline) * -1);`.
     *
     * THE ESCAPE HATCH is for a value neither gate accepts, and it is
     * deliberately awkward to use. One comment carries both directives,
     * because each tool reads "next line" as the line after the comment:
     *
     *   .tooltip__arrow {
     *     /* stylelint-disable-next-line declaration-property-value-allowed-list --
     *        design-audit-ignore-next-line: L1, L2 --
     *        Law 2 escape: optical alignment. The arrow's bounding box sits
     *        1px below its visual centre because of the border join; no
     *        parent gap can express a sub-pixel optical correction.
     *        Reviewed by <name>, <date>. *\/
     *     margin-block-start: -1px;
     *   }
     *
     * The justification must name WHY no gap can do the job — optical
     * alignment, a documented browser bug, a third-party widget whose DOM
     * you do not control. "It looked better" is not a justification; it is
     * a layout that has not been thought through, and the fix is upstream
     * in the parent.
     * ------------------------------------------------------------------ */
    {
      files: [
        '**/components/**/*.css',
        '**/ui/**/*.css',
        '**/*.module.css',
        '**/components.css',
      ],
      rules: {
        'declaration-property-value-allowed-list': {
          ...VALUE_ALLOWLIST,
          ...MARGIN_ALLOWLIST,
        },
        /* A component styling anything but itself and its own parts is
         * reaching outside its box. `> *`, `+ *` and descendant element
         * selectors are how one component quietly starts owning another's
         * spacing — which is Law 2 broken from the other direction. */
        /* Universal selectors after `>` and `+` are the owl, written in the
         * parent's own rule, which Law 2 allows. After a space (`.card *`)
         * they still count. */
        'selector-max-universal': [0, { ignoreAfterCombinators: ['>', '+'] }],
        'selector-max-type': 0,
      },
    },

    /* ---------------------------------------------------------------------
     * 4. THE @apply BRIDGE — one file, and only during a migration.
     *
     * WHY `@apply` IS BANNED EVERYWHERE ELSE
     *
     * `@apply` copies a utility's declarations into a rule. The moment it
     * does, three things Tailwind exists to prevent come back:
     *
     *   - SPECIFICITY RETURNS. A utility is a single class in the
     *     `utilities` layer and beats component CSS by layer order.
     *     `@apply`-ed into `.card .title`, the same declarations now carry
     *     that selector's specificity and live in the `components` layer —
     *     so `p-card-lg` on the element no longer overrides it, and you get
     *     the classic "the utility isn't working" ticket.
     *   - ORDER RETURNS. Tailwind sorts utilities into a known cascade.
     *     `@apply` output is emitted where you wrote it, so which of two
     *     conflicting declarations wins now depends on file import order.
     *   - THE COST RETURNS. Utilities are shared by every element that uses
     *     them; `@apply` duplicates their bytes into every rule, which is
     *     the atomic-CSS bargain thrown away while keeping the class-soup
     *     syntax.
     *
     * And it buys nothing: `.btn { @apply px-inline-md py-block-sm; }` and
     * `.btn { padding: var(--pad-block-sm) var(--pad-inline-md); }` produce
     * the same CSS, but the second reads as CSS, is greppable by property,
     * and is checked by the allowlist above. `@apply` is a layer of
     * indirection over the token layer that already exists.
     *
     * THE NARROW LEGITIMATE CASE, and it is the only one: a bridge file
     * during a migration, where third-party or legacy markup you do not
     * control carries class names you must style, and you want those
     * styles to stay in step with the utilities during the changeover. Put
     * it in ONE file, name the file for what it is, and delete it when the
     * migration lands.
     * ------------------------------------------------------------------ */
    {
      files: ['**/styles/legacy-bridge.css', '**/styles/vendor-overrides.css'],
      rules: {
        'at-rule-disallowed-list': null,
        /* Stylelint validates at-rule preludes against the CSS spec and
         * `@apply`'s prelude is not in it, so this fires on every line of a
         * file where `@apply` is deliberately allowed. */
        'at-rule-prelude-no-invalid': null,
        'no-descending-specificity': null,
        'selector-max-type': null,
      },
    },
  ],
};
