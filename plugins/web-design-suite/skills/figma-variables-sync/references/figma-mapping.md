# Figma → Token Mapping

The complete correspondence between what a designer builds in Figma and what the
system holds in `tokens.css`. Read it before writing a sync script, before
reviewing a Figma file, and before agreeing to any naming scheme in a shared
library — naming is the part that is expensive to change later.

Two sentences carry most of the weight:

> **A Figma collection is a tier. A Figma mode is a theme.**

Everything below is consequences of those two.

## Contents

1. [The shape of the mapping](#1-the-shape-of-the-mapping)
2. [Collections → tiers](#2-collections--tiers)
3. [Modes → themes](#3-modes--themes)
4. [Variable types — what each one can and cannot hold](#4-variable-types--what-each-one-can-and-cannot-hold)
5. [Aliasing → `var()`](#5-aliasing--var)
6. [Scoping → where a token is allowed to be used](#6-scoping--where-a-token-is-allowed-to-be-used)
7. [Text styles → the type roles](#7-text-styles--the-type-roles)
8. [Effect styles → the elevation roles](#8-effect-styles--the-elevation-roles)
9. [Auto-layout → the layout primitives and the proximity ladder](#9-auto-layout--the-layout-primitives-and-the-proximity-ladder)
10. [Component properties and variants → `variant` / `size` / `tone`](#10-component-properties-and-variants--variant--size--tone)
11. [Constraints and resizing → responsive strategy](#11-constraints-and-resizing--responsive-strategy)
12. [Naming that survives the round trip](#12-naming-that-survives-the-round-trip)
13. [What each side can express that the other cannot](#13-what-each-side-can-express-that-the-other-cannot)
14. [The REST API, precisely](#14-the-rest-api-precisely)

---

## 1. The shape of the mapping

| Figma construct | System construct | Fidelity |
|---|---|---|
| Variable collection | A tier (`primitive` / `semantic` / `component`) | Exact |
| Mode inside a collection | A theme selector (`:root`, `[data-theme="dark"]`) | Exact |
| Variable (COLOR / FLOAT) | A Tier-1 or Tier-2 token | Exact |
| Variable (STRING / BOOLEAN) | A token, or nothing | Partial — see §4 |
| Variable alias | `var(--other-token)` | Exact |
| Variable scope | Nothing in CSS; a lint rule | Advisory |
| Text style | A `--type-*` composite | Lossy — CSS composes, Figma flattens |
| Effect style | A `--elevation-*` role | Lossy — see §8 |
| Auto-layout gap | The parent's `gap`, from a `--gap-*` role | Exact, and important |
| Auto-layout padding | A `--pad-*` role | Exact |
| Hug / Fill / Fixed | `fit-content` / `1fr` / a fixed size | Exact |
| Component variant property | A `variant` / `size` / `tone` prop | Exact if named right |
| Constraint | A layout rule, usually a grid | Advisory |
| Absolute position | A conversation (§9) | None |

Fidelity is the column that matters. "Exact" means a sync tool can move it both
ways without a human. "Lossy" means a human has to decide what survives, and any
tool that claims otherwise is silently choosing for you.

---

## 2. Collections → tiers

One collection called `Tokens` holding four hundred variables has no tiering,
which means **PRIMITIVE → SEMANTIC → COMPONENT** is not expressible and a
designer can bind a card's background straight to `neutral/0`. When a rebrand
lands, what goes wrong in an untiered codebase goes wrong in the file.

Three collections, in this order:

| Collection | Holds | Modes | May alias |
|---|---|---|---|
| `Primitives` | Raw ramps and scales: `space/6`, `neutral/500`, `text/2xl` | **One.** Named `Value` | Nothing |
| `Semantic` | Roles: `bg/surface`, `fg/muted`, `pad/card`, `gap/related` | Light, Dark, and any brand | Primitives only |
| `Component` | Part-level: `button/pad-inline`, `card/inset` | Usually one | Semantic only |

**Primitives have exactly one mode.** The single most load-bearing rule in the
mapping. A primitive that changes between Light and Dark is not a primitive; it
is a semantic role wearing a primitive's name, and the day someone needs the
light-mode value *inside* dark mode — a light card on a dark page, a printed
export — there is no name left to say it with. Tier 1 is constant across every
theme; that is what makes it primitive.

`figma_audit.py` reports a collection holding three or more semantic colour roles
with only one mode (`MISSING_DARK_MODE`). It cannot see the inverse from names
alone, so check by hand that the Primitives collection has a single column.

**Extended collections** (Figma, November 2025) let a collection inherit from a
parent and override selected variables — a sub-brand re-pointing nine roles and
inheriting the rest, which is exactly the shape of a brand theme block. Gated to
Enterprise; elsewhere, use an extra mode.

---

## 3. Modes → themes

A mode is a column. Every variable has a value in every column and Figma will not
let you leave one blank — it inherits the default mode's. That is precisely the
semantics of a CSS theme block that re-points some tokens and lets the rest fall
through from `:root`.

| Mode name | Selector emitted | Note |
|---|---|---|
| The collection's default mode | `:root` | Whatever it is called — `Value`, `Light`, `Default` |
| `Dark`, `Night` | `[data-theme="dark"]` | |
| `Light` (when not the default) | `[data-theme="light"]` | For a dark-first product |
| `Compact` / `Comfortable` / `Spacious` | `[data-density="…"]` | See the warning below |
| Anything else | `[data-theme="<slug>"]` | Brands, white-labels, per-customer skins |

**Density is not a mode.** Law 7 makes compactness `--density` (0.875 / 1 /
1.125) — one multiplier, not a second set of values. A Figma file *can* hold
density as a third mode and `figma_to_tokens.py` will emit
`[data-density="compact"]`, but that column must be the same numbers times the
same multiplier. Hand-tuned, it drifts, and then the two sides disagree about
what "compact" means. Prefer one mode plus the dial.

**The generated theme block holds only the re-points.** `figma_to_tokens.py`
omits any token whose value in a mode equals `:root`. A theme block that repeats
an inherited value looks like it owns it, and the next person edits the wrong
one. `--full-themes` restates everything if you need it.

**A theme block containing a component selector means a component hardcoded a
value.** Same test in Figma: if the Dark column changes something in the
Component collection, a component bound to a primitive instead of a role.

---

## 4. Variable types — what each one can and cannot hold

Figma has exactly four: `COLOR`, `FLOAT`, `STRING`, `BOOLEAN`. There is no
dimension type, no duration type, no shadow type, no composite type.

| Type | Holds | Maps cleanly to | Does not map |
|---|---|---|---|
| `COLOR` | 8-bit sRGB + float alpha | `--neutral-*`, `--accent-*`, `--bg-*`, `--fg-*`, `--border-*` | Wide-gamut OKLCH outside sRGB; gradients; `color-mix()` |
| `FLOAT` | One number, unitless | `--space-*`, `--radius-*`, `--text-*`, `--leading-*`, `--tracking-*`, `--weight-*`, `--stroke-*`, `--z-*`, `--dur-*` (as ms) | `clamp()`; anything with two numbers |
| `STRING` | Text | `--font-sans`, `--font-mono`, a `content` string | Anything a browser has to parse as a value |
| `BOOLEAN` | true / false | A feature flag driving a `data-*` attribute | Nothing in the token layer |

Four practical consequences:

**FLOAT has no unit.** A `FLOAT` of `24` is 24 *somethings*. Figma renders it in
px; the system stores `1.5rem`. `figma_to_tokens.py` converts px → rem at 16px
and leaves `--space-px`, the strokes and the durations in their own units — a 1px
hairline in rem is a rounding bug on a zoomed page.

**Durations must be agreed as milliseconds**, and nothing in the file says so.
Write it in the variable's description, which Figma carries through the REST API
and this skill carries through to the generated comment.

**`clamp()` cannot cross.** `--space-fluid-*`, `--text-5xl` and `--text-6xl` are
`clamp()`s and a Figma variable cannot hold one. Either hold both endpoints as
two variables and compose the clamp in the build (adds a name nobody reads), or —
better — keep the fluid steps in code and hold the endpoints in Figma as
annotation. This is why the audit's type table includes both ends of each fluid
step: a designer's fixed 72px hero is `--text-5xl` at its ceiling, not an
off-scale value.

**`VariableComposedColor`** (Figma, September 2026) authors colour and opacity
independently, with `COLOR_OPACITY` as a new FLOAT scope. Both scripts read it —
a composed colour resolves to its base plus the opacity channel — but there is no
CSS equivalent, since `oklch(… / <alpha>)` takes a literal. A composed colour
whose opacity is itself an alias flattens on the way out and the link is lost.

---

## 5. Aliasing → `var()`

A Figma alias is `{"type": "VARIABLE_ALIAS", "id": "VariableID:41:22"}` — the
same relationship as `--bg-surface: var(--neutral-0)`. A reference, not a copy,
and flattening it is the most common way a sync tool destroys a design system: a
flattened export is four hundred hex values with no tiering, and the rebrand that
follows is a find-and-replace. `figma_to_tokens.py` never flattens.

Three failure modes, all handled without crashing:

| Case | What the scripts do |
|---|---|
| **Missing reference** — the target is in a library that was not exported | Audit: `BROKEN_ALIAS`, error. Generator: comments the whole declaration out, so `var(--x)` fails visibly rather than inheriting |
| **Alias cycle** — A → B → A | Audit: `ALIAS_CYCLE`, error, naming the node the loop closes at. Generator: emits the reference and warns; CSS treats it as invalid at computed-value time, which is loud and therefore correct |
| **Cross-collection alias** — Semantic → Primitive | Normal and correct. Semantic → Semantic is a smell: one role should not be defined as another role, because the day they diverge there is no name for the difference |

**Alias direction is the tier check.** An alias that points *up* the tiers —
a primitive aliasing a semantic role — inverts the flow and is always a bug.
Grep the export for it before believing any other number in the file.

---

## 6. Scoping → where a token is allowed to be used

Figma variable scopes restrict where a variable appears in the picker: a FLOAT
scoped `CORNER_RADIUS` will not be offered as a gap. There is no CSS equivalent
— a custom property can be used anywhere — but scopes are the best signal a file
gives about *what a variable is for*, and both scripts use them.

Scopes as the API defines them, and what the scripts do with each:

| Type | Scopes | Checked against |
|---|---|---|
| FLOAT | `GAP`, `PARAGRAPH_SPACING`, `PARAGRAPH_INDENT` | the 18-step spacing scale |
| | `CORNER_RADIUS` | the 8-step radius scale |
| | `FONT_SIZE`, `LINE_HEIGHT`, `LETTER_SPACING`, `FONT_WEIGHT` | the type, leading, tracking and weight scales |
| | `STROKE_FLOAT` | `--stroke-*` |
| | `WIDTH_HEIGHT` | `--tap-min`, when the name sounds interactive |
| | `ALL_SCOPES`, `TEXT_CONTENT`, `OPACITY`, `EFFECT_FLOAT`, `COLOR_OPACITY` | nothing — no closed scale applies |
| STRING | `ALL_SCOPES`, `TEXT_CONTENT`, `FONT_FAMILY`, `FONT_STYLE`, `FONT_VARIATIONS` | nothing |
| COLOR | `TEXT_FILL` | contrast is measured against the surfaces it lands on |
| | `ALL_SCOPES`, `ALL_FILLS`, `FRAME_FILL`, `SHAPE_FILL`, `STROKE_COLOR`, `EFFECT_COLOR` | the ramps |

**Scope beats name.** A designer who scoped a variable told you what it is for;
a name is a guess. Both scripts read scope first and fall back to the name, and
the name patterns are anchored at the start of the slug — `fg-muted` is a text
role, `brand-ink-blue` is not, and an unanchored match on "ink" is the classic
way a token linter earns its reputation for false positives.

**Reverse direction.** `--reverse` assigns scopes from the token name, which is
the whole argument for the naming grammar: `--pad-card` gets `GAP` and
`WIDTH_HEIGHT`, `--fg-muted` gets `TEXT_FILL`, `--border-default` gets
`STROKE_COLOR`. A well-named token knows where it is allowed to be used.

---

## 7. Text styles → the type roles

Figma text styles and CSS type roles are nearly the same idea and differ in one
way that costs work every time.

| `--type-*` role | Figma text style | Composed from |
|---|---|---|
| `--type-display` | `type/display` | `--weight-bold`, `--text-6xl`, `--leading-tight`, `--font-sans` |
| `--type-h1` … `--type-h4` | `type/h1` … `type/h4` | weight + size + leading + family |
| `--type-lead` | `type/lead` | |
| `--type-body` | `type/body` | |
| `--type-ui` | `type/ui` | Buttons, menu items, controls |
| `--type-label` | `type/label` | Field labels, badges |
| `--type-code` | `type/code` | `--font-mono` |

**Ten roles. Not eleven, and not one per usage.** `Card title` and `Modal title`
are `--type-h4` at two call sites; making them two styles means the day headings
get tighter you change two things and miss a third. The audit reports any text
style whose name does not resolve to a role (`UNMAPPED_TEXT_STYLE`).

**The difference that costs work: composition.** In CSS, `--type-h2` is a `font`
shorthand built from four primitives, so changing `--text-3xl` moves every h2 in
the product. In Figma a text style holds four *flat numbers*; changing `text/3xl`
does not move a style built from it. Figma variables *can* be bound into a text
style's size, weight, line-height and letter-spacing individually, and **when
they are, the link is live and the round trip works.** When they are not, the
style is a snapshot and the file drifts from the tokens beside it without
anything appearing to break.

> **Check this first in any file.** Select a text style and look at whether its
> font size shows a variable chip or a bare number. Bare numbers mean the type
> scale in the file is decorative.

The REST boundary is lossy here too. `GET /v1/files/:file_key/styles` returns
*metadata* — `key`, `file_key`, `node_id`, `style_type`, `name`, `description` —
not the type properties. For the actual `fontSize` and `lineHeightPx` you read
the nodes the style is applied to (`GET /v1/files/:file_key/nodes`) and match on
`styles.text`. Both scripts accept either shape: metadata alone (the name is
checked against the roles) or metadata plus a `style` object carrying `TypeStyle`
fields — `fontFamily`, `fontWeight`, `fontSize`, `lineHeightPx`,
`lineHeightPercent`, `letterSpacing`, `textCase`, `textDecoration` — in which
case the numbers are checked against the scales too.

There is no `POST` for styles. Code → Figma for type means a human building ten
text styles once and binding each field to the variables this skill generated:
twenty minutes, once, and the cheapest twenty minutes in the workflow.

---

## 8. Effect styles → the elevation roles

| `--elevation-*` | Figma effect style | Composed from |
|---|---|---|
| `--elevation-flat` | `elevation/flat` | `--shadow-none` |
| `--elevation-card` | `elevation/card` | `--shadow-sm` |
| `--elevation-raised` | `elevation/raised` | `--shadow-md` |
| `--elevation-overlay` | `elevation/overlay` | `--shadow-lg` |
| `--elevation-modal` | `elevation/modal` | `--shadow-xl` |

Three rules; the audit checks the first.

**Name for the role, never the value.** `Shadow 12 Soft` cannot be re-tuned
without renaming it everywhere, so it never gets re-tuned. `elevation/card` can.
Unmapped names are reported as `UNMAPPED_EFFECT_STYLE`.

**Every level is a pair of shadows** — a tight contact shadow plus a wider
ambient one; single-shadow elevation always reads as a sticker. Figma expresses
this as two `DROP_SHADOW` effects in one style, one-to-one. A file with one
shadow per level has half an elevation system.

**Dark mode is not a mirror, and effect styles have no modes.** `tokens.css`
re-points the shadows in dark to much higher alphas, because depth on dark
surfaces comes mostly from a lighter surface plus a top hairline. A Figma effect
style is one fixed set of effects, so a file that needs both ships
`elevation/card` and `elevation/card-dark` while the code ships one name
re-pointed per theme. This asymmetry is permanent — document it rather than
trying to sync it.

---

## 9. Auto-layout → the layout primitives and the proximity ladder

**This is the section that decides whether a Figma file is worth anything.**

Figma auto-layout `gap` is set on the **parent frame** and applies between its
children. That is Law 2 — parents own the gaps — implemented in the design tool.
A designer who builds in auto-layout has already obeyed the law that developers
break most often, and the file translates almost mechanically:

| Auto-layout property | Maps to | Token |
|---|---|---|
| Direction: vertical | `.stack` | — |
| Direction: horizontal | `.cluster` | — |
| Wrap: on | `.cluster` with `flex-wrap: wrap` | — |
| Gap (item spacing) | the parent's `gap` | a `--gap-*` role |
| Padding, uniform | `padding` | `--pad-card` / `--pad-well` |
| Padding, asymmetric | `padding-inline` + `padding-block` | `--pad-inline-*` + `--pad-block-*` |
| Alignment (9-point control) | `align-items` + `justify-content` | — |
| Hug contents | `width: fit-content` / `auto` track | — |
| Fill container | `flex: 1` / `1fr` track | — |
| Fixed | a width — **and a question** | see below |
| "Absolute position" toggle | a conversation | see below |

**The gap is chosen by relationship, not by pixels.** The proximity ladder maps
onto auto-layout gaps directly:

| Figma gap @1× | Token | The relationship it asserts |
|---|---|---|
| 4 | `--gap-fused` | Two halves of one thing — icon + label |
| 8 | `--gap-tight` | A thing and its annotation — label + input |
| 12 | `--gap-related` | Items in one list |
| 16 | `--gap-grouped` | Sibling blocks in one group |
| 24 | `--gap-separate` | Distinct groups in one region |
| 40 | `--gap-distinct` | Unrelated blocks |

When you read a gap out of a file, do not write down `24`. Write down
`--gap-separate`, and if the relationship it implies is wrong — two items in one
list sitting 24px apart — that is a design finding, not a spacing finding, and it
is worth more than the twelve off-scale values underneath it.

**A badly built file is full of absolute positioning** — frames with children at
fixed x/y instead of auto-layout. This is the expensive signal and it outweighs
every number in the audit. Nothing has a parent-owned gap, so **every gap in the
file is a measurement rather than a decision**: the numbers are what the
designer's hand did, not what the designer meant. Nothing reflows, so the file
says nothing about responsive behaviour and every breakpoint is an invention
during the build. And components will have been detached to nudge things, so the
variant structure is unreliable too.

Say it early and in terms of cost: *"this file is positioned rather than laid
out, so I'll be inventing the responsive behaviour — either we spend half a day
converting it to auto-layout, or we accept that I'll be guessing and we review on
staging instead of in Figma."* Both answers are fine. Discovering it in week two
is not.

**Fixed widths are a question, not a value.** A fixed 320px card might be a real
constraint (a sidebar) or a leftover from designing at one viewport. Ask. A fixed
width that reaches code is a breakpoint bug waiting.

---

## 10. Component properties and variants → `variant` / `size` / `tone`

Figma component properties come in four kinds — Variant, Boolean, Instance swap,
and Text — and they map to props with almost no loss, provided the names match.

| Figma | Prop | Rule |
|---|---|---|
| Variant property `Variant` (Primary / Secondary / Ghost / Danger) | `variant` | The triad's first member. Values are lower-case in code |
| Variant property `Size` (sm / md / lg) | `size` | Same three names in both places |
| Variant property `Tone` (neutral / accent / success / warning / danger) | `tone` | Maps to the intent roles |
| Variant property `State` (default / hover / focus / active / disabled) | **not a prop** | State is an ARIA attribute or `data-state`, never a prop (contract, §the seven states) |
| Boolean property `Has icon` | `icon?: ReactNode` | A boolean in Figma is usually an optional slot in code |
| Instance swap `Icon` | `icon` prop | |
| Text property `Label` | `children` | |

**Three property names, forever: `variant`, `size`, `tone`.** A Figma property
called `Style` or `Type` or `Kind` becomes a rename argument the first time
someone writes a component, and renaming a variant property in Figma detaches
nothing but does break every instance override. Agree the triad before the
library is built.

**State is not a variant.** A `State` variant property is right for Figma —
there is no other way to draw a hover state — and wrong for code, where hover is
`:hover` and disabled is `:disabled`. Those variants are the *specification* for
the seven states, not a prop. Expect the count to differ: Figma usually draws
four, the contract requires seven, and **the three that are missing —
focus-visible, loading, error — are the three that decide whether the thing
works.** Ask for them in the audit.

Proving variant × size × theme × density all render is `component-state-matrix`'s
job, not this skill's.

---

## 11. Constraints and resizing → responsive strategy

Constraints (Left / Right / Center / Scale / Left-and-right) describe what
happens when a frame is resized. A weak signal — most files have the defaults —
but where they are set deliberately they carry real intent.

| Constraint | Usually means | In code |
|---|---|---|
| Left + Top | Fixed position in a fixed frame | Usually a sign the frame should be auto-layout |
| Left and Right | Fills the width | `1fr`, or `width: 100%` |
| Center | Centred at every width | `margin-inline: auto` with a `--width-*` cap |
| Scale | Proportional | Rare and usually wrong outside illustration |

More useful than constraints: **the number of frames the designer drew.** One
1440 artboard is no responsive story. 1440 / 768 / 390 is three data points, and
the breakpoints between them are yours to pick from `--bp-*`. 1440 and 375 gives
you endpoints — enough for fluid type and spacing, not enough for where a nav
collapses.

The question that buys the most information for the least designer time:

> *"At 768, does this three-column grid become two or one, and does the sidebar
> collapse or move below?"*

Ask it about the two or three layouts that actually change. Do not ask for a
tablet artboard of every screen; you will not get it and you do not need it.

---

## 12. Naming that survives the round trip

Figma groups variables with `/`. The system names them
`--category-role-variant`. These are the same grammar with a different separator,
and the round trip is lossless when the file follows three rules.

**Rule 1 — one `/` after the category word.** `space/6` → `--space-6`,
`neutral/500` → `--neutral-500`, `bg/surface` → `--bg-surface`, `fg/on-accent` →
`--fg-on-accent`, `pad/card-lg` → `--pad-card-lg`, `elevation/card` →
`--elevation-card`. Deeper nesting reads nicely and converts lossily, because
`color/brand/accent/500` and `color/brand-accent/500` slugify to the same thing.

**Rule 2 — tier and category words at the front, or not at all.**
`figma_to_tokens.py` strips a leading tier word (`primitive`, `semantic`, `core`,
`global`, `component`, `theme`, `alias`, `token`…) and then, one segment at a
time, a leading category word (`color`, `size`, `spacing`, `dimension`,
`typography`, `effect`…) — **but only while what remains is a name the contract
recognises.** `Primitive/Color/Neutral/500` → `--neutral-500`. It also tolerates
a `gray-`/`grey-` prefix for `neutral-`, because that one is in every file ever
built.

**Rule 3 — the name is the role, not the value.** `gray/light-2`, `Shadow 12`,
`Blue 500 New`, `spacing/medium`, `text/heading-big` all fail the only test that
matters: can this be re-tuned without renaming it? `--fg-muted` survives a
palette change; `gray/light-2` does not.

**Anything the converter cannot place is emitted with its own slug and reported
on stderr as `unmapped-name`.** It never guesses. A generator that renames
`brand/coral` to `--accent-450` to make it fit has quietly created a second
vocabulary — the exact failure the suite exists to prevent.

---

## 13. What each side can express that the other cannot

This table is where every sync tool quietly loses information. Read it before
believing any tool's claim of a "lossless" sync, including this one's.

### Figma can express, CSS cannot

| Figma | Why it does not cross | What to do |
|---|---|---|
| **Variable scopes** | CSS custom properties have no usage restriction | Keep them in Figma; enforce the same intent in code with `audit_design.py` |
| **`hiddenFromPublishing`** | No CSS equivalent | Treat as "internal"; keep it out of the generated files |
| **Instance swap properties** | A component reference, not a value | A React prop; not a token |
| **Prototype interactions and reactions** | Not a style at all | A spec for behaviour — read it, do not sync it |
| **Layout grids** | Figma's grid is a visual guide; CSS grid is layout | Translate by hand into `--grid-columns` and a container |
| **Constraints** | Descriptive, not prescriptive | Notes for the responsive plan (§11) |
| **Blend modes, masks, boolean ops** | Partially expressible, rarely worth it | Export as an asset |
| **Extended-collection overrides** | Close to a theme block, but with its own inheritance rules | Map to a `[data-theme="brand-x"]` block manually |

### CSS can express, Figma cannot

| CSS | Why it does not cross | What to do |
|---|---|---|
| **`clamp()` / fluid values** | A FLOAT is one number | Hold both endpoints in Figma; compose the clamp in code |
| **`calc()`** — including `calc(var(--space-6) * var(--density))` | No arithmetic in a variable value | Density stays a code-only dial (Law 7) |
| **Composite shorthands** — `--type-*`, `--motion-*`, `--shadow-*`, `--elevation-*` | A variable is one scalar | Ship as Figma *styles*, named for the same role |
| **Relative colour and `color-mix()`** | Figma stores resolved colours | Resolve in code; Figma holds the result |
| **Wide-gamut OKLCH outside sRGB** | Figma is 8-bit sRGB | Accept the clamp. `--accent-600` is out of sRGB and round-trips slightly duller. Both scripts snap a colour whose 8-bit rendering matches a ramp step back to that step's canonical OKLCH, so the loss happens once at the boundary and the generated numbers are identical run to run (whitespace and trailing zeros will differ from a hand-aligned `tokens.css`; the values do not) |
| **`:focus-visible`, `:has()`, `@media`, `prefers-reduced-motion`** | Figma has no cascade | The seven states and reduced motion are a code contract; Figma can only draw them |
| **Cascade, inheritance, layers** | Figma resolves at bind time | Why a Figma file cannot be the whole source of truth |
| **`currentColor`** | No indirection to a context | Bind explicitly in Figma |

**The honest summary:** Tier 1 and Tier 2 *scalars* — every colour, every
spacing step, every size, every radius, every duration — round-trip exactly. The
composites do not cross at all. That split is not a limitation of this tool; it
is the shape of the two systems, and the right response is to name the
composites in both places and sync only the scalars they are built from.

---

## 14. The REST API, precisely

Checked against Figma's developer documentation in September 2026. Do not quote
anything here that you have not re-checked if a year has passed; the Variables
API has moved more than once.

### Endpoints

| Method + path | Scope | Plan |
|---|---|---|
| `GET /v1/files/:file_key/variables/local` | `file_variables:read` | Enterprise org full members only |
| `GET /v1/files/:file_key/variables/published` | `file_variables:read` | Enterprise org full members only |
| `POST /v1/files/:file_key/variables` | `file_variables:write` | Enterprise org full members only, plus edit access to the file |

The GETs are Tier 2 for rate limiting; the POST is Tier 3.

> **The plan gate is the single most important fact in this document.** The
> Variables REST API has been Enterprise-only since it launched in June 2023. If
> the company is on Professional or Organization, **no amount of scripting gets
> variables out over the API** — the exported-JSON path is not a fallback, it is
> the only path. Confirm the plan before promising anyone a pipeline.

### `GET …/variables/local` response

```
{ "status", "error", "meta": {
    "variables": { "<variableId>": {
        "id", "name", "key", "variableCollectionId",
        "resolvedType": "BOOLEAN" | "FLOAT" | "STRING" | "COLOR",
        "valuesByMode": { "<modeId>": Boolean | Number | String | Color
                                       | VariableAlias | VariableComposedColor },
        "remote", "description", "hiddenFromPublishing",
        "scopes": VariableScope[], "codeSyntax": { "WEB"?, "ANDROID"?, "iOS"? } } },
    "variableCollections": { "<variableCollectionId>": {
        "id", "name", "key", "modes": [{ "modeId", "name", "parentModeId" }],
        "defaultModeId", "remote", "hiddenFromPublishing", "variableIds",
        "isExtension", "parentVariableCollectionId", "rootVariableCollectionId",
        "inheritedVariableIds", "localVariableIds", "variableOverrides",
        "deletedButReferenced" } } } }
```

`Color` is `{ "r", "g", "b", "a" }`, each channel between 0 and 1.
`VariableAlias` is `{ "type": "VARIABLE_ALIAS", "id": <variable id> }`.

`local` returns everything including unpublished drafts; `published` returns only
what the library has published, keyed by `key` rather than `id`. `local` is
almost always what you want for a handoff — the thing you are arguing about is
rarely published yet.

### `POST …/variables` request body

Four optional arrays, applied atomically, each entry carrying
`"action": "CREATE" | "UPDATE" | "DELETE"` (`id` required for UPDATE and DELETE,
optional for CREATE):

| Array | Entry fields |
|---|---|
| `variableCollections` | `action`, `id`, `name`, `parentVariableCollectionId`, `initialModeId`, `initialModeIdToParentModeIdMapping`, `hiddenFromPublishing` |
| `variableModes` | `action`, `id`, `name`, `variableCollectionId` |
| `variables` | `action`, `id`, `name`, `variableCollectionId`, `resolvedType`, `description`, `hiddenFromPublishing`, `scopes`, `codeSyntax` |
| `variableModeValues` | `variableId`, `modeId`, `value` |

**Temporary ids.** At create time you may put your own id in a collection's,
mode's or variable's `id`, and in a collection's `initialModeId`, then reference
it elsewhere in the same body. They are scoped to one request and must be unique
within it. `--reverse` uses `tmp_collection_*`, `tmp_mode_*`, `tmp_var_*`.

**One subtlety.** A collection's initial mode is created *with the collection*;
`initialModeId` only names it so you can refer to it. A `VariableModeChange` with
`"action": "CREATE"` for that same id asks Figma to make it twice. `--reverse`
names the initial mode on the collection and only `CREATE`s the extra modes.

### What to do when you are not on Enterprise

| Need | Enterprise | Everyone else |
|---|---|---|
| Read variables | `GET …/variables/local` | A plugin export (SKILL.md, step 1) |
| Write variables | `POST …/variables` | `--reverse` builds the payload; a plugin or a human imports it |
| Read styles | `GET …/styles` + `GET …/nodes` | The same plugin export, or a screenshot and a conversation |
| Automate on merge | CI hits the API | CI checks the committed export; a human re-exports when the file changes |

Figma announced native import and export of variables conforming to the W3C
Design Tokens Community Group 1.0 specification, rolling out in stages from late
2025. **Verify its availability and its exact file shape in the app before
building on it** — the rollout has been staged and reported dates have moved;
this document does not claim to know its current state. Both scripts already read
DTCG-shaped JSON (`$value` / `$type`, `{group.token}` references), so if it is
live in your account it works today.
