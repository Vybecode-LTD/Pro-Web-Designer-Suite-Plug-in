# The Token Contract

Every skill in the Web Design Suite speaks this vocabulary. It is reproduced in each skill so that a single `.skill` file works standalone, and it is identical in all of them. If you change it, change it everywhere — a fork is how the suite stops being a suite.

The canonical implementation is `tokens.css` in the `web-design-studio` skill.

---

## The Nine Laws

1. **Tokens or nothing.** Every value in every rule resolves through a token. Literals live in exactly one file: `tokens.css`.
2. **Parents own the gaps.** A child never sets its own outer margin. Space between siblings comes from the parent's `gap`. Legal exceptions: `margin:auto` for alignment, an owl selector (`> * + *`) written in the parent's own rule, and `calc(var(--token) * -1)` to cancel a known token.
3. **The scale is closed.** 18 spacing steps, 11 type steps, 5 leadings, 6 elevations, 5 durations, 8 z-indexes. Nothing between the steps.
4. **One home per component's styles.** A reviewer must predict a component's appearance from one file. Inline `style` is legal only when *every* key is a CSS custom property.
5. **Layers, not specificity.** `@layer reset, tokens, base, layout, components, utilities, overrides;` declared once, first, before any import. No `!important`, no ID selectors, nesting depth 2 maximum.
6. **Semantic before primitive.** Components read Tier-2 roles (`--pad-card`), never Tier-1 primitives (`--space-6`).
7. **Density is a dial.** Compactness is `--density` (0.875 / 1 / 1.125), not a second set of styles.
8. **Novel patterns pass the gate.** Nothing ships that a first-time user cannot operate with a keyboard.
9. **Nothing ships un-audited.** `python -m scripts.audit_design <path>` exits clean.

---

## The three tiers

Flow is one-way: **PRIMITIVE → SEMANTIC → COMPONENT → rule.**

| Tier | What | Who reads it |
|---|---|---|
| 1 Primitive | Raw values: `--space-6`, `--neutral-800`, `--text-2xl`, `--shadow-md`, `--dur-base` | `tokens.css` only |
| 2 Semantic | A value bound to a role: `--pad-card`, `--fg-muted`, `--type-h2`, `--elevation-card`, `--motion-enter` | Component CSS |
| 3 Component | A role narrowed to one part: `--button-pad-inline`, `--card-inset` | That component's own file; also its public CSS API |

Theme and brand overrides re-point **Tier 2 only**. A theme block containing a component class name means a component had a hardcoded value.

---

## Tier-1 primitives (the closed scales)

**Spacing** — 4px base, closed. There is no `--space-7`, `--space-9`, `--space-11`, `--space-14`.

```
--space-0 --space-px --space-0-5 --space-1 --space-2 --space-3 --space-4
--space-5 --space-6 --space-8 --space-10 --space-12 --space-16 --space-20
--space-24 --space-32 --space-40 --space-48
                 0 1 2 4 8 12 16 20 24 32 40 48 64 80 96 128 160 192 (px)
--space-fluid-sm | -md | -lg | -xl          clamp()ed, 380 -> 1440px anchors
--density                                    0.875 | 1 | 1.125
```

**Type** — `--text-2xs --text-xs --text-sm --text-base --text-lg --text-xl --text-2xl --text-3xl --text-4xl --text-5xl --text-6xl`
**Leading** — `--leading-none --leading-tight --leading-snug --leading-normal --leading-relaxed`
**Tracking** — `--tracking-tighter --tracking-tight --tracking-normal --tracking-wide --tracking-caps`
**Weight** — `--weight-regular --weight-medium --weight-semibold --weight-bold`
**Fonts** — `--font-sans --font-mono`

**Color ramps** (OKLCH, 50 → 950/1000): `--neutral-*` `--accent-*`, plus `--success-100/500/700`, `--warning-*`, `--danger-*`, `--info-*`.

**Radius** — `--radius-none --radius-xs --radius-sm --radius-md --radius-lg --radius-xl --radius-2xl --radius-full`
**Stroke** — `--stroke-hairline --stroke-default --stroke-thick --stroke-focus`
**Shadow** — `--shadow-none --shadow-xs --shadow-sm --shadow-md --shadow-lg --shadow-xl --shadow-focus`
**Motion** — `--dur-instant --dur-fast --dur-base --dur-slow --dur-slower --dur-loop`; `--ease-out --ease-in --ease-in-out --ease-spring --ease-linear`  
  (`--dur-loop` is the one duration reduced-motion does **not** collapse — a spinner that stops spinning reads as a hung page.)
**Breakpoints** — `--bp-sm 30rem · --bp-md 48rem · --bp-lg 64rem · --bp-xl 80rem · --bp-2xl 96rem`
**Other** — `--tap-min 2.75rem` · `--grid-columns 12` · `--measure-prose 68ch` · `--measure-narrow 48ch` · `--width-content 72rem` · `--width-wide 90rem` · `--width-form 28rem`

---

## Tier-2 roles (what components actually read)

**The proximity ladder** — pick by *relationship*, never by pixels:

| Token | @1× | Relationship |
|---|---|---|
| `--gap-fused` | 4px | Two halves of one thing (icon + label) |
| `--gap-tight` | 8px | A thing and its annotation (label + input) |
| `--gap-related` | 12px | Items in one list |
| `--gap-grouped` | 16px | Sibling blocks in one group |
| `--gap-separate` | 24px | Distinct groups in one region |
| `--gap-distinct` | 40px | Unrelated blocks |

**Inset** — `--pad-inline-xs/-sm/-md`, `--pad-block-xs/-sm/-md`, `--pad-card`, `--pad-card-lg`, `--pad-well`
**Page rhythm** — `--space-section`, `--space-subsection`, `--space-block`, `--gutter-page`
**Surfaces** — `--bg-canvas --bg-surface --bg-raised --bg-sunken --bg-inverse`
**Interaction** — `--bg-hover --bg-active --bg-selected --bg-disabled`
**Foreground** — `--fg-default --fg-strong --fg-muted --fg-subtle --fg-disabled --fg-on-accent --fg-on-inverse --fg-accent --fg-link`
**Borders** — `--border-subtle --border-default --border-strong --border-accent --border-focus`
**Intent** — `--bg-accent --bg-accent-hover --bg-success --bg-warning --bg-danger --fg-success --fg-warning --fg-danger`
**Type roles** — `--type-display --type-h1 --type-h2 --type-h3 --type-h4 --type-lead --type-body --type-ui --type-label --type-code`
**Elevation** — `--elevation-flat --elevation-card --elevation-raised --elevation-overlay --elevation-modal --elevation-focus`
**Motion roles** — `--motion-hover --motion-enter --motion-exit --motion-expand --motion-emphasis --motion-loop`
**Z-index ladder** — `--z-base --z-raised --z-sticky --z-dropdown --z-overlay --z-modal --z-toast --z-tooltip`

Note: `--space-section`, `--space-subsection`, `--space-block` and `--space-fluid-*` live in the `--space-*` namespace but **are Tier 2** — the tier is a property of the name's meaning, not its first word.

Primitives with **no** Tier-2 equivalent — `--radius-*`, `--stroke-*`, `--z-*`, `--bp-*`, `--font-*`, `--measure-*`, `--width-*`, `--tap-min` — are read directly by components, and that is correct.

---

## The seven states

Every interactive component implements all of them: **default · hover · focus-visible · active · disabled · loading · error.** Anything that fetches also gets designed **empty** and **loading** states rather than defaulted ones.

State is expressed as a real ARIA attribute where one exists (`aria-expanded`, `aria-current`, `aria-selected`, `aria-invalid`, `:disabled`), otherwise `data-state` / `data-variant` / `data-size` — never `is-*` classes.

---

## Accessibility floor

WCAG 2.2 Level AA, treated as a floor. Contrast is **measured, never assumed**: 4.5:1 body text, 3:1 large text and UI components (SC 1.4.11), and the focus ring pairs `box-shadow: var(--elevation-focus)` with `outline: var(--stroke-focus) solid transparent` so it survives forced-colors mode, which discards `box-shadow`.

---

## Suite cross-references

| Skill | Owns |
|---|---|
| `web-design-studio` | The system itself — tokens, spacing, architecture, navigation, invention, the audit gate |
| `design-token-migration` | Getting an inherited codebase onto the system |
| `figma-variables-sync` | Keeping design files and code speaking one vocabulary |
| `component-state-matrix` | Proving every state × density × theme renders correctly |
| `landing-page-conversion` | The content and persuasion layer the studio skill deliberately omits |
| `design-critique-gate` | Adversarial review before anything reaches a client |
| `design-system-docs` | Documentation generated from the code, so it cannot drift |
| `content-model-to-ui` | A database schema turned into on-system screens |
| `email-template-system` | The same tokens compiled to HTML email, where these laws must bend |
| `perf-budget-gate` | The performance sibling of the design gate |
| `a11y-audit-runner` | The runtime accessibility gate — axe, keyboard, focus, forced-colors |
| `design-system-versioning` | Changing the system without breaking its consumers |
| `client-presentation-builder` | Making the case for the work in the room |
