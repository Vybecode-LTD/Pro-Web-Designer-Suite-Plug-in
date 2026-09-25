/* =========================================================================
 * tailwind.config.ts — the Tailwind v3 binding layer
 * =========================================================================
 *
 * APPENDIX FILE. Tailwind v4 is the primary target; use assets/configs/
 * theme.css unless the client is pinned to v3. Reach for this only when a
 * v4 migration is out of scope for the engagement.
 *
 * Same contract as theme.css: this file contains NO design decisions. Every
 * value is `var(--token)` pointing into assets/starter/styles/tokens.css,
 * except the four literal exceptions documented in theme.css §0.
 *
 * THE ONE STRUCTURAL DIFFERENCE FROM v4
 * -------------------------------------
 * These keys sit under `theme`, NOT under `theme.extend`. That is load-
 * bearing and it is the entire point of the file. `extend` merges with
 * Tailwind's stock scale and leaves `p-4`, `bg-neutral-800` and `text-sm`
 * alive next to ours — two scales, one codebase, and a slow drift nobody
 * can grep for. A top-level key REPLACES the default, so after this config
 * an off-scale class generates no CSS (silently — the linter flags it, the
 * build does not). That is Law 3 (the scale is closed) expressed as a
 * config shape.
 *
 * Keys we do not list keep their defaults, deliberately: `opacity`,
 * `flex`, `gridTemplateColumns` and friends hold no design values.
 *
 * REQUIRED PEER SETUP
 * -------------------
 *   npm i -D tailwindcss@^3 postcss autoprefixer prettier-plugin-tailwindcss
 *
 *   postcss.config.js:  { plugins: { tailwindcss: {}, autoprefixer: {} } }
 *   src/styles/index.css:
 *     @layer reset, tokens, base, layout, components, utilities, overrides;
 *     @import "./tokens.css";
 *     @tailwind base;        // v3 emits into its own `base`/`components`/
 *     @tailwind components;  // `utilities` layers; see the note at the
 *     @tailwind utilities;   // bottom of this file about reconciling them.
 * ========================================================================= */

import type { Config } from 'tailwindcss';
import plugin from 'tailwindcss/plugin';

/* -------------------------------------------------------------------------
 * `t('--foo')` is a one-character-cheaper `var(--foo)` and, more usefully,
 * a single choke point: the audit script greps this file for any string
 * that is not a `t()` call, so a stray literal cannot hide in 400 lines of
 * config. Law 1.
 * ---------------------------------------------------------------------- */
const t = (token: `--${string}`): string => `var(${token})`;

export default {
  /* -----------------------------------------------------------------------
   * CONTENT — the v3 equivalent of v4's `@source`.
   *
   * Include every workspace package whose source contains class names. A
   * design system shipped from `packages/ui` that is missing here generates
   * no CSS, renders unstyled in the consuming app, and reads as a build
   * bug rather than a config omission. Never glob into `dist`: stale
   * classes from a build artifact keep dead CSS alive forever.
   * -------------------------------------------------------------------- */
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
    './packages/ui/src/**/*.{ts,tsx}',
  ],

  /* -----------------------------------------------------------------------
   * DARK MODE — attribute, not class, to match tokens.css.
   *
   * The `['selector', ...]` two-element form is v3.4.1+. On older v3 use
   * `darkMode: ['class', '[data-theme="dark"]']`, which is the same
   * mechanism under a legacy name.
   *
   * In a correctly token-driven component you should almost never write
   * `dark:`. Every Tier-2 color role is re-pointed by `[data-theme="dark"]`
   * in tokens.css, so `bg-surface` is already correct in both themes. More
   * than one or two `dark:` classes in a component means a missing role.
   * -------------------------------------------------------------------- */
  darkMode: ['selector', '[data-theme="dark"]'],

  theme: {
    /* ---------------------------------------------------------------------
     * SCREENS — literal exception #1. Media query conditions cannot read
     * custom properties, so these must mirror `--bp-*` by hand.
     * `scripts/audit_design.py` diffs the two and fails on drift.
     * ------------------------------------------------------------------ */
    screens: {
      sm: '30rem',   /*  480px — mirrors --bp-sm  */
      md: '48rem',   /*  768px — mirrors --bp-md  */
      lg: '64rem',   /* 1024px — mirrors --bp-lg  */
      xl: '80rem',   /* 1280px — mirrors --bp-xl  */
      '2xl': '96rem' /* 1536px — mirrors --bp-2xl */,
    },

    /* ---------------------------------------------------------------------
     * SPACING — drives p-*, m-*, gap-*, space-*, inset-*, w-*, h-*.
     *
     * Replacing this key deletes `p-4`, `gap-7`, `mt-12` and every other
     * numeric step in one stroke. What remains is the proximity ladder and
     * the inset roles, so a class name states a RELATIONSHIP rather than a
     * measurement. Law 6.
     *
     * Every value here resolves through `calc(step * var(--density))`
     * upstream, so `[data-density="compact"]` on any subtree recomposes it
     * with zero component changes. Law 7. Unlike v4 there is no `@theme
     * inline` distinction to get wrong here — v3 inlines `var()` into the
     * utility by construction, which is the one thing v3 makes easier.
     * ------------------------------------------------------------------ */
    spacing: {
      0: t('--space-0'),
      px: t('--space-px'),

      /* Proximity ladder — pick by meaning, not by measured result. */
      fused: t('--gap-fused'),         /* icon + its label      */
      tight: t('--gap-tight'),         /* label + its input     */
      related: t('--gap-related'),     /* items in one group    */
      grouped: t('--gap-grouped'),     /* sibling cards, rows   */
      separate: t('--gap-separate'),   /* distinct groups       */
      distinct: t('--gap-distinct'),   /* unrelated blocks      */

      /* Insets. */
      'inline-xs': t('--pad-inline-xs'),
      'inline-sm': t('--pad-inline-sm'),
      'inline-md': t('--pad-inline-md'),
      'block-xs': t('--pad-block-xs'),
      'block-sm': t('--pad-block-sm'),
      'block-md': t('--pad-block-md'),
      card: t('--pad-card'),
      'card-lg': t('--pad-card-lg'),
      well: t('--pad-well'),

      /* Page rhythm — fluid clamps, correct at 390px and at 1440px. */
      section: t('--space-section'),
      subsection: t('--space-subsection'),
      block: t('--space-block'),
      gutter: t('--gutter-page'),

      /* Minimum finger target. */
      tap: t('--tap-min'),
    },

    /* ---------------------------------------------------------------------
     * COLORS
     *
     * Naming convention, identical to theme.css §4 so components port
     * between v3 and v4 unchanged: BARE NAME = the fill, `-fg` SUFFIX =
     * the ink. `bg-danger` is the 500-weight solid; `text-danger-fg` is the
     * 700-weight that clears 4.5:1 on a light surface.
     *
     * ---- THE v3 OPACITY-MODIFIER LIMITATION, READ THIS ----
     *
     * `bg-surface/50` DOES NOT WORK with `var()` colors. v3 implements the
     * `/opacity` modifier by substituting an `<alpha-value>` placeholder
     * into the color, which requires the token to be stored as bare
     * channels (`210 40% 96%`) rather than a complete color function. Our
     * tokens are complete `oklch()` values, on purpose — channel-splitting
     * a color token makes it unreadable, un-inspectable in devtools, and
     * impossible to hand to a designer.
     *
     * So the modifier silently produces an invalid value and the
     * declaration is dropped. The fix is not to split the tokens; it is to
     * stop reaching for opacity. A translucent surface is a design
     * decision that deserves a role: `--bg-hover` and `--bg-active` in
     * tokens.css are already translucent overlays that compose over ANY
     * surface, which is why no component needs a per-variant hover color.
     * If you genuinely need a new translucency, add a Tier-2 role.
     *
     * The Stylelint config bans `/<number>` modifiers on these classes for
     * exactly this reason. v4 has no such limitation — `color-mix()` makes
     * the modifier work against complete colors — which is one more reason
     * to push clients off v3.
     * ------------------------------------------------------------------ */
    colors: {
      /* Literal exception #2 — CSS-wide keywords. */
      transparent: 'transparent',
      current: 'currentColor',
      inherit: 'inherit',

      /* Surfaces, back to front. */
      canvas: t('--bg-canvas'),
      surface: t('--bg-surface'),
      raised: t('--bg-raised'),
      sunken: t('--bg-sunken'),
      inverse: t('--bg-inverse'),
      scrim: t('--bg-scrim'),

      /* Interaction overlays — translucent, compose over any surface. */
      hover: t('--bg-hover'),
      active: t('--bg-active'),
      selected: t('--bg-selected'),
      disabled: t('--bg-disabled'),

      /* Foreground. */
      default: t('--fg-default'),
      strong: t('--fg-strong'),
      muted: t('--fg-muted'),
      subtle: t('--fg-subtle'),
      link: t('--fg-link'),
      'on-accent': t('--fg-on-accent'),
      'on-inverse': t('--fg-on-inverse'),
      'disabled-fg': t('--fg-disabled'),

      /* Intent fills. */
      accent: t('--bg-accent'),
      'accent-hover': t('--bg-accent-hover'),
      success: t('--bg-success'),
      warning: t('--bg-warning'),
      danger: t('--bg-danger'),

      /* Intent inks. */
      'accent-fg': t('--fg-accent'),
      'success-fg': t('--fg-success'),
      'warning-fg': t('--fg-warning'),
      'danger-fg': t('--fg-danger'),

      /* Lines. */
      'line-subtle': t('--border-subtle'),
      line: t('--border-default'),
      'line-strong': t('--border-strong'),
      'line-accent': t('--border-accent'),
      focus: t('--border-focus'),

      /* Tier 1 ramps are NOT exposed. There is no `bg-neutral-800`. If a
       * design needs a step no role names, add a Tier-2 role in tokens.css
       * and a line here — do not let a component reach past the role
       * layer. Law 6, enforced by the class not existing. */
    },

    /* ---------------------------------------------------------------------
     * TYPOGRAPHY
     *
     * The tuple form ships size + leading + tracking + weight from ONE
     * class, which is the v3 equivalent of v4's `--text-*--line-height`
     * companions and the same shape as Tier 2's `--type-*` shorthands.
     *
     * You cannot get `text-h2`'s size without its leading. That is the
     * point: a 35px heading left at body leading is the single most common
     * typographic bug in shipped marketing sites.
     *
     * Tier 1 steps are not exposed. `text-3xl` does not exist; ask for the
     * role.
     * ------------------------------------------------------------------ */
    fontSize: {
      display: [
        t('--text-6xl'),
        {
          lineHeight: t('--leading-tight'),
          letterSpacing: t('--tracking-tighter'),
          fontWeight: t('--weight-bold'),
        },
      ],
      /* A section-opening display size below the page hero. Fluid, because
       * a fixed 44px+ heading is either cramped on a laptop or unreadable
       * on a phone. */
      'display-sm': [
        t('--text-5xl'),
        {
          lineHeight: t('--leading-tight'),
          letterSpacing: t('--tracking-tighter'),
          fontWeight: t('--weight-bold'),
        },
      ],
      h1: [
        t('--text-4xl'),
        {
          lineHeight: t('--leading-tight'),
          letterSpacing: t('--tracking-tighter'),
          fontWeight: t('--weight-bold'),
        },
      ],
      h2: [
        t('--text-3xl'),
        {
          lineHeight: t('--leading-tight'),
          letterSpacing: t('--tracking-tight'),
          fontWeight: t('--weight-semibold'),
        },
      ],
      h3: [
        t('--text-2xl'),
        {
          lineHeight: t('--leading-snug'),
          letterSpacing: t('--tracking-tight'),
          fontWeight: t('--weight-semibold'),
        },
      ],
      h4: [
        t('--text-xl'),
        {
          lineHeight: t('--leading-snug'),
          letterSpacing: t('--tracking-tight'),
          fontWeight: t('--weight-semibold'),
        },
      ],
      lead: [
        t('--text-lg'),
        {
          lineHeight: t('--leading-normal'),
          letterSpacing: t('--tracking-normal'),
          fontWeight: t('--weight-regular'),
        },
      ],
      body: [
        t('--text-base'),
        {
          lineHeight: t('--leading-normal'),
          letterSpacing: t('--tracking-normal'),
          fontWeight: t('--weight-regular'),
        },
      ],
      /* Same size as `body`, looser leading. A separate role because the
       * decision is "this is read for minutes", not "this is bigger". */
      prose: [
        t('--text-base'),
        {
          lineHeight: t('--leading-relaxed'),
          letterSpacing: t('--tracking-normal'),
          fontWeight: t('--weight-regular'),
        },
      ],
      ui: [
        t('--text-sm'),
        {
          lineHeight: t('--leading-snug'),
          letterSpacing: t('--tracking-wide'),
          fontWeight: t('--weight-medium'),
        },
      ],
      label: [
        t('--text-xs'),
        {
          lineHeight: t('--leading-snug'),
          letterSpacing: t('--tracking-wide'),
          fontWeight: t('--weight-medium'),
        },
      ],
      caps: [
        t('--text-xs'),
        {
          lineHeight: t('--leading-snug'),
          letterSpacing: t('--tracking-caps'),
          fontWeight: t('--weight-semibold'),
        },
      ],
      meta: [
        t('--text-2xs'),
        {
          lineHeight: t('--leading-snug'),
          letterSpacing: t('--tracking-wide'),
          fontWeight: t('--weight-regular'),
        },
      ],
      code: [
        t('--text-sm'),
        {
          lineHeight: t('--leading-normal'),
          letterSpacing: t('--tracking-normal'),
          fontWeight: t('--weight-regular'),
        },
      ],
    },

    /* Named `body`/`code`, not `sans`/`mono`: a client who moves to a serif
     * should not have to rename every class in the codebase. */
    fontFamily: {
      body: t('--font-sans'),
      code: t('--font-mono'),
    },

    fontWeight: {
      regular: t('--weight-regular'),
      medium: t('--weight-medium'),
      semibold: t('--weight-semibold'),
      bold: t('--weight-bold'),
    },

    /* Standalone leading and tracking, for what `text-*` cannot cover:
     * multi-line numerals, a heading that wraps into a caption. */
    lineHeight: {
      flat: t('--leading-none'),
      display: t('--leading-tight'),
      heading: t('--leading-snug'),
      body: t('--leading-normal'),
      long: t('--leading-relaxed'),
    },

    letterSpacing: {
      display: t('--tracking-tighter'),
      heading: t('--tracking-tight'),
      body: t('--tracking-normal'),
      ui: t('--tracking-wide'),
      allcaps: t('--tracking-caps'),
    },

    /* ---------------------------------------------------------------------
     * RADIUS — roles over steps.
     *
     * NESTING RULE: inner radius = outer radius − inner padding.
     * `rounded-panel` (16px) with `p-card` (24px) holds a child at
     * `rounded-flat`. Concentric corners that ignore this look peeled.
     * ------------------------------------------------------------------ */
    borderRadius: {
      flat: t('--radius-none'),
      hairline: t('--radius-xs'),
      inner: t('--radius-sm'),
      control: t('--radius-md'),
      card: t('--radius-lg'),
      panel: t('--radius-xl'),
      hero: t('--radius-2xl'),
      pill: t('--radius-full'),
    },

    borderWidth: {
      0: '0',
      hairline: t('--stroke-hairline'),
      DEFAULT: t('--stroke-default'),
      thick: t('--stroke-thick'),
    },

    /* ---------------------------------------------------------------------
     * ELEVATION — reach for the role, never the step. `--shadow-md` is a
     * pair of offsets; `--elevation-raised` is a statement about where the
     * thing sits in the stack, and dark mode re-points the steps
     * underneath without touching a component.
     * ------------------------------------------------------------------ */
    boxShadow: {
      flat: t('--elevation-flat'),
      card: t('--elevation-card'),
      raised: t('--elevation-raised'),
      overlay: t('--elevation-overlay'),
      modal: t('--elevation-modal'),
      focus: t('--shadow-focus'),
    },

    /* ---------------------------------------------------------------------
     * MOTION. v3 does have `transitionDuration` and
     * `transitionTimingFunction` namespaces (v4 dropped duration), but
     * prefer the `motion-*` utilities registered in the plugin below:
     * tokens.css is explicit that duration and easing "travel together or
     * you get drift", and two separate classes are two chances to drift.
     * ------------------------------------------------------------------ */
    transitionDuration: {
      instant: t('--dur-instant'),
      fast: t('--dur-fast'),
      base: t('--dur-base'),
      slow: t('--dur-slow'),
      slower: t('--dur-slower'),
    },

    transitionTimingFunction: {
      enter: t('--ease-out'),
      exit: t('--ease-in'),
      move: t('--ease-in-out'),
      bounce: t('--ease-spring'),
      steady: t('--ease-linear'),
    },

    /* ---------------------------------------------------------------------
     * Z-INDEX — a closed ladder, named for the thing that occupies it.
     * There is no `z-50`. If two things need to stack within one rung they
     * are siblings and source order decides, which is the honest answer.
     * ------------------------------------------------------------------ */
    zIndex: {
      base: t('--z-base'),
      raised: t('--z-raised'),
      sticky: t('--z-sticky'),
      dropdown: t('--z-dropdown'),
      overlay: t('--z-overlay'),
      modal: t('--z-modal'),
      toast: t('--z-toast'),
      tooltip: t('--z-tooltip'),
    },

    /* ---------------------------------------------------------------------
     * MEASURE AND CONTAINER WIDTHS. Line length is a spacing decision:
     * 60-75 characters is the readable band, and `max-w-prose` is how you
     * hit it without counting.
     * ------------------------------------------------------------------ */
    maxWidth: {
      none: 'none',
      full: '100%',
      prose: t('--measure-prose'),
      narrow: t('--measure-narrow'),
      content: t('--width-content'),
      wide: t('--width-wide'),
      form: t('--width-form'),
    },

    /* `extend` is legitimate ONLY for keys that hold no design value — the
     * grid column count is a structural fact, not a decision a component
     * gets to make. Anything with a unit belongs in a replaced key above. */
    extend: {
      keyframes: {
        /* Literal exception #3 — keyframe geometry. A full turn is 360deg
         * in every brand. */
        spin: { to: { transform: 'rotate(360deg)' } },
        pulse: { '50%': { opacity: '0.5' } },
        enter: {
          from: { opacity: '0', transform: `translateY(${t('--space-2')})` },
          to: { opacity: '1', transform: 'none' },
        },
      },
      animation: {
        spin: `spin 1s ${t('--ease-linear')} infinite`,
        pulse: `pulse 2s ${t('--ease-in-out')} infinite`,
        enter: `enter ${t('--dur-base')} ${t('--ease-out')} both`,
      },
    },
  },

  /* -----------------------------------------------------------------------
   * CORE PLUGINS OFF
   *
   * Two of these are Law enforcement, not preference:
   *
   *   space   — `space-x-*` / `space-y-*` set `margin-left`/`margin-top` on
   *             every child except the first. That is a child setting its
   *             own outer margin, which is precisely what Law 2 forbids,
   *             and it breaks the moment the list wraps, reverses under
   *             `flex-row-reverse`, or gets reordered by `order-*`. `gap`
   *             is the parent owning the gap: one declaration, no
   *             `:not(:first-child)` selector, correct in every direction.
   *             Turning the plugin off means the class cannot be typed.
   *
   *   divideWidth / divideColor — same mechanism (`border-left-width` on
   *             children), same failure. Use a parent with `gap` and a
   *             `border-line-subtle` on the separator element, or
   *             `hairline` pseudo-borders in the component's own file.
   *
   * `container` is off because it hardcodes its own max-widths and
   * paddings, neither of which come from tokens. Use `max-w-content
   * page-gutter`.
   * -------------------------------------------------------------------- */
  corePlugins: {
    space: false,
    divideWidth: false,
    divideColor: false,
    divideStyle: false,
    container: false,
  },

  plugins: [
    /* ---------------------------------------------------------------------
     * SEMANTIC UTILITIES — the v3 equivalent of v4's `@utility`.
     *
     * `addUtilities` registers into the `utilities` layer, so these sit
     * alongside Tailwind's own and are ordered by the same rules. Do not
     * use `addComponents` for these: components-layer classes lose to any
     * utility, which is how you end up with a `focus-ring` that a stray
     * `shadow-card` silently beats.
     * ------------------------------------------------------------------ */
    plugin(({ addUtilities }) => {
      addUtilities({
        /* Motion pairs — duration and easing bound together so a 320ms
         * drawer cannot ship with a hover easing. */
        '.motion-hover': {
          transitionDuration: t('--dur-fast'),
          transitionTimingFunction: t('--ease-out'),
        },
        '.motion-enter': {
          transitionDuration: t('--dur-base'),
          transitionTimingFunction: t('--ease-out'),
        },
        '.motion-exit': {
          transitionDuration: t('--dur-fast'),
          transitionTimingFunction: t('--ease-in'),
        },
        '.motion-expand': {
          transitionDuration: t('--dur-slow'),
          transitionTimingFunction: t('--ease-in-out'),
        },
        '.motion-emphasis': {
          transitionDuration: t('--dur-slow'),
          transitionTimingFunction: t('--ease-spring'),
        },
        '.motion-instant': {
          transitionDuration: t('--dur-instant'),
          transitionTimingFunction: t('--ease-out'),
        },
        '.motion-page': {
          transitionDuration: t('--dur-slower'),
          transitionTimingFunction: t('--ease-in-out'),
        },

        /* One focus ring, everywhere — the same ring as reset.css. The
         * visible ring is an OUTLINE: forced-colors mode repaints it, and a
         * `shadow-*` class on the same element cannot remove it. The
         * box-shadow is only the canvas-coloured gap. Always pair with
         * `focus-visible:`; a mouse click should not paint a ring. */
        '.focus-ring': {
          outline: `${t('--stroke-focus')} solid ${t('--border-focus')}`,
          outlineOffset: t('--stroke-focus'),
          boxShadow: `0 0 0 ${t('--stroke-focus')} ${t('--bg-canvas')}`,
        },

        /* 44px. Non-negotiable on anything a finger touches. A visually
         * 24px icon button still needs this — pad it or give it a
         * transparent hit area. */
        '.tap-target': {
          minInlineSize: t('--tap-min'),
          minBlockSize: t('--tap-min'),
        },

        /* The one place a horizontal margin is correct: a container
         * centring itself. Law 2 governs SIBLING spacing. */
        '.page-gutter': {
          paddingInline: t('--gutter-page'),
          marginInline: 'auto',
        },

        '.grid-layout': {
          display: 'grid',
          gridTemplateColumns: `repeat(${t('--grid-columns')}, minmax(0, 1fr))`,
          gap: t('--gap-grouped'),
        },
      });
    }),
  ],
} satisfies Config;

/* =========================================================================
 * LAYERS IN v3 — read this before mixing v3 with native cascade layers
 * =========================================================================
 * v3 does NOT emit native cascade layers. Its `@layer base|components|
 * utilities` are Tailwind directives: at build time they move rules to
 * where the matching `@tailwind` directive sits, and the output is plain,
 * UNLAYERED CSS. Unlayered CSS beats every native layer whatever the
 * specificity, so with `@layer reset, tokens, base, …` in the same sheet,
 * v3's preflight (`button { background-color: transparent }`) and every
 * utility override your layered CSS — the opposite of Law 5.
 *
 * Put Tailwind's output INTO the layers instead. Build it as two sheets
 * and import them with native layer() (postcss-import 15+, listed before
 * tailwindcss in the PostCSS plugins, keeps the layer when it inlines):
 *
 *   tailwind-base.css        @tailwind base;
 *   tailwind-utilities.css   @tailwind components; @tailwind utilities;
 *
 *   index.css
 *   @layer reset, tokens, base, layout, components, utilities, overrides;
 *   @import url("./tailwind-base.css") layer(base);
 *   @import url("./tailwind-utilities.css") layer(utilities);
 *
 * Check the built CSS once: preflight's `button { … }` must sit inside
 * `@layer base`. If your toolchain cannot do that, keep ALL hand-written
 * CSS unlayered too and order it by import — Law 5 then holds only by
 * convention. v4 removes the problem: it emits native layers itself.
 *
 * Do not use v3's `@layer components { ... }` directive (the Tailwind one)
 * for hand-written CSS. It is not the native at-rule: it moves the rules
 * into Tailwind's unlayered output, purges any class the content globs do
 * not see, and hides where a rule really lands.
 * ========================================================================= */
