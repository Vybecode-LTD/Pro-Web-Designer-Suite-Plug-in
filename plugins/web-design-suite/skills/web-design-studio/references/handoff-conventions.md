# Handoff Conventions

The rules that let five people, a designer, and a Claude Code session touch the same
codebase in the same week without it drifting. Everything here exists to make one
sentence true: **a reviewer should not be able to tell which developer wrote a file.**

This document is the operational half of the studio's design system. The other
references say what good looks like; this one says where it lives, what it's called,
who may change it, and what has to be true before it ships. Read it before the first
commit on a project, not after the first disagreement.

The Nine Laws are assumed throughout and restated where a convention exists to enforce
one. Law numbers appear inline like **(Law 2)** so a reviewer can cite rather than
argue.

---

## Contents

1. [The repository shape](#1-the-repository-shape) — [tree](#11-the-canonical-tree) · [styles/](#12-styles--the-cascade-in-file-order) · [components/](#13-components--one-folder-one-component) · [token pipeline](#14-the-token-pipeline-source-of-truth)
2. [Naming conventions](#2-naming-conventions) — [files](#21-files-and-folders) · [CSS classes](#22-css-classes-pick-one-per-project) · [custom properties](#23-custom-property-grammar) · [props](#24-component-prop-naming) · [state](#25-state-data-attributes-not-classes) · [test ids](#26-test-ids)
3. [The component contract](#3-the-component-contract)
4. [Design-to-code mapping](#4-design-to-code-mapping)
5. [Working alongside other developers](#5-working-alongside-other-developers)
6. [The PR review checklist](#6-the-pr-review-checklist)
7. [Claude Code handoff](#7-claude-code-handoff)
8. [Definition of done](#8-definition-of-done)

---

## 1. The repository shape

Directory structure is not bikeshedding. It is the cheapest form of documentation:
a developer who can guess where a file lives never opens the wrong one, and an agent
that can guess never creates a duplicate. Every project in the studio uses this shape.
Deviations are allowed, documented in `DESIGN_DECISIONS.md`, and never silent.

### 1.1 The canonical tree

```
project/
├── CLAUDE.md                  # Laws + stack + audit command. First file an agent reads.
├── IMPLEMENTATION.md          # Ordered runbook. Current state + next task.
├── DESIGN_DECISIONS.md        # Why non-obvious choices were made. Append-only.
├── package.json               # `design:audit` and `design:tokens` scripts live here.
│
├── design/
│   ├── tokens.json            # SOURCE OF TRUTH for every design value. Hand-edited.
│   └── build-tokens.mjs       # tokens.json -> tokens.css + tokens.ts. Deterministic.
│
├── src/
│   ├── styles/
│   │   ├── index.css          # ONLY file that @imports. Declares the layer order.
│   │   ├── tokens.css         # GENERATED. Never hand-edited. Tier 1 + Tier 2.
│   │   ├── reset.css          # Normalize + opinionated defaults. No project styling.
│   │   ├── base.css           # Element defaults: body, headings, a, ul, form controls.
│   │   ├── layout.css         # Layout primitives: .stack .cluster .grid .container.
│   │   └── utilities.css      # Escape-hatch single-purpose classes. Tightly bounded.
│   │
│   ├── components/
│   │   └── Button/
│   │       ├── Button.tsx          # The component. One styling home (Law 4).
│   │       ├── Button.module.css   # Its styles. Tier 3 tokens declared at the top.
│   │       ├── Button.types.ts     # Public props. Exported for consumers.
│   │       ├── Button.stories.tsx  # Every variant x size x state. The visual contract.
│   │       ├── Button.test.tsx     # Behaviour + a11y. Not screenshots.
│   │       └── index.ts            # `export { Button } from './Button'` and types.
│   │
│   ├── app/                   # Routes. Composition only.
│   │   ├── routes/
│   │   └── layouts/
│   │
│   ├── lib/                   # Framework-agnostic logic. No JSX, no CSS imports.
│   │   ├── tokens.ts          # GENERATED. Typed token names for JS consumers.
│   │   ├── api/
│   │   └── utils/
│   │
│   └── hooks/                 # Reusable stateful logic. useDisclosure, useMediaQuery.
│
├── public/                    # Served verbatim at the origin root. Fonts, favicons, og.
└── scripts/
    └── audit_design.py        # Law 9's enforcement. Wired to npm + pre-commit.
```

### 1.2 `styles/` — the cascade in file order

`index.css` is the only file permitted to `@import`, and its first statement is the
layer declaration **(Law 5)**. Declaring the order up front means every later file can
be written in whatever order is convenient — the cascade is already decided.

```css
/* src/styles/index.css — the whole cascade, in one place. */
@layer reset, tokens, base, layout, components, utilities, overrides;

@import url("./reset.css")     layer(reset);
@import url("./tokens.css")    layer(tokens);
@import url("./base.css")      layer(base);
@import url("./layout.css")    layer(layout);
@import url("./utilities.css") layer(utilities);
/* components/*.module.css declare `@layer components` internally. */
```

| File | Belongs here | Never here |
|---|---|---|
| `tokens.css` | Tier 1 primitives, Tier 2 roles, theme re-points, density modes, reduced-motion overrides | Any selector that names a component. Any rule that sets a property other than a custom property. Hand edits of any kind — it is generated |
| `reset.css` | `box-sizing`, margin zeroing, `img { display:block; max-inline-size:100% }`, form-control font inheritance | Colors, spacing, anything with brand in it. A reset that styles is a theme in disguise |
| `base.css` | Element-level defaults bound to Tier 2: `body { font: var(--type-body); color: var(--fg-default) }`, heading `font`, `a` color, focus-visible ring | Classes. If it needs a class it is not a base style |
| `layout.css` | The five or six layout primitives, each owning `gap`/`padding` **(Law 2)** | Anything visual — color, shadow, radius. A layout primitive is invisible |
| `utilities.css` | A closed set of single-purpose classes: `.visually-hidden`, `.text-balance`, `.flow`, density/theme attribute helpers | Open-ended utility generation in a non-Tailwind project. A utility per spacing step is a second, worse token system |
| `overrides` layer | Empty on a healthy project. Third-party widget corrections only, each with a comment naming the widget and a removal condition | Your own components. Reaching for `overrides` to beat your own CSS means the component is wrong |

**Why no `components.css`.** Global component stylesheets are where dead CSS goes to
hide. A component's styles live beside it and are deleted with it — the only reliable
way to keep a stylesheet from outliving its markup.

### 1.3 `components/` — one folder, one component

The folder is the unit. Six files is not ceremony; each one answers a question a
reviewer or an agent will otherwise ask in Slack.

| File | Answers | Rule |
|---|---|---|
| `Button.tsx` | What does it render? | One styling home **(Law 4)**. Either the module, or Tailwind classes, never both |
| `Button.module.css` | What does it look like? | Tier 3 tokens declared in the first block, sourced from Tier 2 **(Law 6)**. Max nesting depth 2 **(Law 5)** |
| `Button.types.ts` | What is its public surface? | Exported. Consumers import types from here, never from the `.tsx` |
| `Button.stories.tsx` | What does every state look like? | Must include a story per variant, per size, and one "all states" story. This is what a designer reviews |
| `Button.test.tsx` | Does it behave? | Keyboard map, ARIA, controlled/uncontrolled. Not pixel snapshots — those fail on token changes that were intentional |
| `index.ts` | How do I import it? | `export { Button } from './Button'; export type { ButtonProps } from './Button.types';` Nothing else. No logic in a barrel |

A component folder must never contain: a route, a data fetch, a hard-coded copy string
that isn't a default, a second component that "only this one uses" (promote it to its
own folder — the second consumer always arrives), or a `utils.ts` that other components
import (that belongs in `lib/`).

**Nesting.** `components/Card/CardHeader.tsx` is permitted only when `CardHeader` is
meaningless outside `Card` and is exported as `Card.Header`. If it can be used alone,
it gets its own top-level folder.

### 1.4 The token pipeline (source of truth)

There is exactly one source of truth for design values: **`design/tokens.json`**.
CSS and TS are both generated from it. The reason is arithmetic: the moment a value can
be edited in two places, two people edit it in one place each, and the bug that follows
costs more than the pipeline.

```
design/tokens.json  ──build-tokens.mjs──┬──▶ src/styles/tokens.css   (CSS custom props)
   (hand-edited,                        └──▶ src/lib/tokens.ts       (typed names + values)
    reviewed, versioned)
```

Rules, all enforced by the auditor:

1. **Generated files carry a banner and are never hand-edited.** The build writes it;
   the auditor fails the run if a generated file's content doesn't match a fresh build.

   ```css
   /* AUTO-GENERATED by design/build-tokens.mjs from design/tokens.json.
      Do not edit. Your changes will be overwritten by `npm run design:tokens`. */
   ```

2. **Generated files are committed**, not gitignored. A fresh clone must build and run
   without a token step, and a reviewer must be able to see the diff a token change
   produces — that diff is the design review.
3. **`tokens.json` mirrors the tier model.** Top-level keys `primitive` and `semantic`.
   The build refuses to emit a `semantic` value that is a literal rather than a
   reference **(Law 1)**, and refuses a `primitive` reference to another primitive.
4. **Tailwind, when used, is generated too.** `tailwind.config` imports `tokens.ts` and
   maps the **semantic** tier onto its theme. A project that hand-writes a Tailwind
   palette has two token systems and one of them is lying.
5. **`lib/tokens.ts` exists for runtime consumers only** — chart libraries, canvas,
   `matchMedia` breakpoints. It is never imported by a component to set a style that CSS
   could set.

---

## 2. Naming conventions

Names are an interface. Every inconsistency is a lookup a future reader has to perform.

### 2.1 Files and folders

| Thing | Convention | Example | Rationale |
|---|---|---|---|
| Component folder | `PascalCase` | `components/DataTable/` | Matches the exported symbol, so `import { DataTable } from '@/components/DataTable'` reads as one name |
| Component file | `PascalCase.tsx` | `DataTable.tsx` | The folder name and the component name **must agree exactly**. A `Table/` folder exporting `DataGrid` is a rename that was never finished |
| Styles | `PascalCase.module.css` | `DataTable.module.css` | Colocated, identically named, deleted together |
| Hooks | `camelCase.ts`, `use` prefix | `useDisclosure.ts` | Lint rules key off the prefix |
| `lib/`, `app/`, `public/` files | `kebab-case` | `format-currency.ts`, `order-detail.tsx` | Non-component modules export multiple symbols; no single name to agree with. Kebab also survives case-insensitive filesystems, which is where most "works on my machine" CI failures come from |
| Route segments | `kebab-case` | `app/routes/order-detail/` | They are URLs. URLs are lowercase |
| CSS files in `styles/` | `kebab-case` | `layout.css` | Same reason |
| Test / story | `<Name>.test.tsx`, `<Name>.stories.tsx` | | Sorts adjacent to the component |

### 2.2 CSS classes (pick one per project)

**A project picks ONE of these and records the choice in `CLAUDE.md`.** Mixing is the
single fastest way to make a codebase feel like three codebases. All three obey the
same laws underneath; they differ only in how a class name is produced.

| Approach | Use when | Convention | Gotcha |
|---|---|---|---|
| **CSS Modules, camelCase** — *the default for this studio* | React 19 + Vite, any client, any team size | `.root`, `.label`, `.isLoading` → `styles.root`. Every component's outermost class is `.root` | camelCase because `styles.is-loading` is a syntax error. Enable `localsConvention: 'camelCase'` in Vite and never dash a class |
| **Tailwind, utility-first** | Client's team already lives in Tailwind, or the project is heavily marketing-page shaped | Utilities inline; extract to a component the moment a class list repeats twice, never to `@apply` | Tailwind's default scale is NOT our scale. Map the theme to semantic tokens (§1.4) or Law 3 dies quietly. `@apply` recreates a stylesheet with worse tooling — banned |
| **BEM, plain CSS** | No build-step control, a CMS theme, or a handoff to a non-JS team | `.card`, `.card__title`, `.card--featured`. One block per file | Depth stops at one element. `.card__header__title` means the header is a block |

Cross-cutting rules regardless of choice:
- The outermost element of a component carries exactly one component-owned class.
- No class encodes a value (`.mt-24`, `.text-red`). It encodes a role.
- No class is targeted by a test. Tests use roles or `data-testid` (§2.6).

### 2.3 Custom property grammar

Every custom property follows `--<category>-<role>-<variant>`, matching `tokens.css`.
Read left to right it narrows: what kind of value, what job, which flavour.

```
--bg-accent-hover
  │  │      └── variant   optional; a state or modifier
  │  └───────── role      the job: what this value is FOR
  └──────────── category  bg | fg | border | gap | pad | space | text | radius | shadow
                          | elevation | dur | ease | motion | z | measure | width | bp
```

| Tier | Shape | Example | Who may read it |
|---|---|---|---|
| 1 primitive | `--<scale>-<step>` | `--space-6`, `--neutral-800`, `--accent-500` | `tokens.css` only. **Never a component (Law 6)** |
| 2 semantic | `--<category>-<role>[-<variant>]` | `--pad-card`, `--fg-muted`, `--gap-related` | Any stylesheet. This is the team's vocabulary |
| 3 component | `--<component>-<property>[-<axis>]` | `--btn-pad-x`, `--card-gap`, `--table-row-h` | Its own component file. Declared at the top, sourced from Tier 2 |

Naming failures that mean something is wrong:
- A role named after its value (`--gap-24`, `--fg-gray`) — it is a primitive alias, delete it.
- A role that needs "and" to explain (`--pad-card-and-modal`) — it is two roles.
- A Tier 3 token on `:root` — it is not component-scoped, so it is a Tier 2 role in disguise.

### 2.4 Component prop naming

The standard triad is **`variant` · `size` · `tone`**. Every component that has visual
options uses these three names and no synonyms. `kind`, `type`, `appearance`, `color`,
`scale`, `intent`, `level` are all banned — not because they're bad words but because
five of them in one codebase means five lookups.

| Prop | Controls | Typical values |
|---|---|---|
| `variant` | Structural/visual treatment | `'solid' \| 'outline' \| 'ghost' \| 'link'` |
| `size` | Dimensional scale | `'sm' \| 'md' \| 'lg'` — `md` is always the default |
| `tone` | Semantic meaning / intent color | `'neutral' \| 'accent' \| 'success' \| 'warning' \| 'danger'` |

Rules:
- **Boolean props are named for the true state**, positively: `disabled`, `loading`,
  `selected`, `required`. Never `isDisabled`, never `notEditable`. Negative booleans
  force double-negative reasoning at every call site (`notEditable={false}`).
- **`isX` is banned for visual variants.** `isPrimary` is `variant="solid" tone="accent"`.
  A boolean per visual option produces `isPrimary isLarge isDanger` and an
  unrepresentable state the day two are true.
- **Event props are `on<Thing><Verb>`**: `onValueChange`, `onOpenChange`, `onSelect`.
  Not `onChangeValue`, not `handleChange` (that's the local handler's name).
- **Controlled/uncontrolled pairs are `value` / `defaultValue` + `onValueChange`.**
  Mirroring the DOM means no one has to learn your API.
- `className` and `ref` are always accepted (§3). `style` never appears in a props type
  as a styling hook; it exists only to pass runtime numbers **(Law 4)**.

### 2.5 State: data attributes, not classes

State goes on the element as `data-*`, not as a class.

```tsx
<div className={styles.root} data-state={open ? 'open' : 'closed'} data-tone={tone}>
```
```css
.root[data-state="open"] { grid-template-rows: 1fr; }
.root[data-tone="danger"] { --card-accent: var(--bg-danger); }
```

Four reasons this is not a style preference:

1. **State is exclusive by construction.** `data-state` holds one value. Classes let
   `.is-open .is-closed` coexist, and eventually they do.
2. **Specificity stays flat (Law 5).** `[data-state="open"]` and `.root` are both
   (0,1,0)-ish and compose inside one layer without escalation.
3. **Tests read the same thing the CSS reads.** `expect(el).toHaveAttribute('data-state','open')`
   asserts the contract. Asserting a hashed CSS-Module class asserts the bundler.
4. **It survives the styling choice.** Swap CSS Modules for Tailwind
   (`data-[state=open]:grid-rows-1`) and the component's state API is unchanged.

Use ARIA attributes as the selector when one already expresses the state —
`[aria-expanded="true"]`, `[aria-selected="true"]`, `[disabled]`. Styling off ARIA makes
a missing ARIA attribute visible immediately, which is a feature.

### 2.6 Test ids

Order of preference for selecting an element in a test: **role + accessible name** →
`data-testid` → never a class, never a DOM path. A test that can only find an element by
class is a test that will pass while the element is invisible to a screen reader.

`data-testid="<component>-<part>"`, kebab-case: `data-testid="data-table-row"`.
Stripped in production builds via the JSX transform. Never reused as a styling hook.

---

## 3. The component contract

A component is **done** when all twelve are true. This list is the review; "it works"
is not on it.

1. **One styling home (Law 4).** Module *or* utilities, not both. The only permitted
   inline `style` is a runtime number entering CSS as a custom property:
   `style={{ '--progress': pct } as CSSProperties}`. An inline `style` that sets a
   named CSS property is a bug.
2. **Token-only values (Laws 1, 6).** Every declaration traces to a Tier 2 role, via a
   Tier 3 token where the component needs its own vocabulary. Zero literals — including
   `0`, which is `--space-0`, and `1px`, which is `--stroke-hairline`.
3. **`className` merges, never replaces.** `className={cx(styles.root, className)}`,
   consumer last so it can win inside the same layer. A component that drops the passed
   `className` will be forked by the first person who needs to position it.
4. **`ref` is a prop (React 19).** No `forwardRef` — it is deprecated for new code on 19.

   ```tsx
   export function Button({ ref, variant = 'solid', size = 'md', tone = 'neutral',
                            className, ...rest }: ButtonProps) {
     return <button ref={ref} className={cx(styles.root, className)}
                    data-variant={variant} data-size={size} data-tone={tone} {...rest} />;
   }
   ```
5. **Rest props spread onto the correct element** — the one that owns the semantics and
   the ref. For a composite, document which element receives them; `aria-label` landing
   on a wrapper `<div>` instead of the `<button>` is silent breakage.
6. **All seven states implemented**: default, hover, focus-visible, active, disabled,
   loading, error. Plus `empty` for anything that renders a collection. A state you
   didn't design is a state the browser designed for you.
7. **Controlled and uncontrolled both work**, and a story demonstrates each. Pick one
   internally (`useControllableState`-style) rather than branching at every usage.
8. **RTL-safe by construction.** Logical properties only: `margin-inline`,
   `padding-block`, `inset-inline-start`, `border-start-start-radius`, `text-align: start`.
   Physical `left/right/top/bottom` appear only for genuinely physical things (a drop
   shadow's offset, a fixed scrim).
9. **Dark mode by construction.** Zero `[data-theme="dark"]` selectors in the component
   **(Law 1 + §1.4)**. If the component needs a dark-specific value, the fix is a new
   Tier 2 role that both themes re-point — not a selector.
10. **Density-aware (Law 7).** Spacing comes from `--gap-*`/`--pad-*`, which already
    multiply by `--density`. Setting `--density` on an ancestor must visibly recompose
    the component with no rule changes. Verify it; don't assume it.
11. **Keyboard map documented** in the component's doc comment and asserted in tests:
    every key, what it does, and what receives focus on open and on close.
12. **Audit clean (Law 9).** `python -m scripts.audit_design` reports zero findings for
    the component's files.

Additionally, a component **never sets its own outer margin (Law 2)** — no
`margin-block-end`, no `margin-top` on the root, ever. Its parent supplies `gap`. This
is what makes a component reusable in a context its author never saw.

---

## 4. Design-to-code mapping

The handoff fails in one specific way: the designer's file contains values the system
doesn't have, the developer rounds them silently, and six months later nobody can say
what the spacing scale is. The fix is procedural, not technical.

### 4.1 Figma → token, one-to-one

| Figma | Maps to | Rule |
|---|---|---|
| Variable collection `primitive/` | Tier 1 in `tokens.json` | Names match exactly: Figma `space/6` → `--space-6` |
| Variable collection `semantic/` | Tier 2 | Figma `bg/surface` → `--bg-surface`. **The designer names roles, not values** |
| Variable mode (Light / Dark) | `[data-theme]` re-point | Modes may only re-point semantic variables — the same rule as the CSS |
| Text style | `--type-*` composite | One Figma text style per `--type-*` token. Not one per usage |
| Effect style | `--elevation-*` | Named for the role (`elevation/card`), not the blur radius |
| Component variant property | `variant` / `size` / `tone` prop | Property names in Figma use the same triad. A Figma property called "Style" becomes a rename argument later |
| Auto-layout frame | A layout primitive, not a wrapper `<div>` | Vertical auto-layout → `.stack`; horizontal with wrap → `.cluster`; gap → a `--gap-*` role |
| Auto-layout padding | `--pad-*` role | Uniform padding → `--pad-card`/`--pad-well`. Asymmetric padding → two roles, or an optical-alignment note |
| Constraints / Grow | `flex`/`grid` on the primitive | Never a fixed width. A fixed width in code is a breakpoint bug waiting |
| Absolute-positioned element | A conversation | Absolute position in Figma is usually a decoration; occasionally it's a layout the system can't express |

### 4.2 Audit the Figma file before writing code

Twenty minutes here saves a week of drift. In order:

1. **Detached instances.** Select all → count components vs frames. A detached instance
   is a fork that will arrive in code as a one-off component.
2. **Off-scale spacing.** Read every auto-layout gap and padding. Anything not in
   `--space-*` (4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128…) goes on the list.
   28px and 18px are the two that show up most.
3. **Off-scale type.** Any text not bound to a text style, any size not in the type
   scale, any line-height typed by hand.
4. **Raw fills.** Any fill that is a hex rather than a variable.
5. **Effect one-offs.** Shadows typed inline instead of an effect style.
6. **Contrast.** Check body-on-surface and muted-on-surface in both modes with a plugin.
   Do not trust that the palette was checked.

Produce one list. Send it once, before estimating — not in dribs during build.

### 4.3 When the design and the system disagree

**The rule: if a designer's value has no token, the conversation happens BEFORE code.**
Not after, not "I'll match it for now". Matching it for now is how `--space-7` gets
born at 2am with nobody's sign-off.

Three outcomes, in order of preference:

1. **The design snaps to an existing step.** 28px → 24px or 32px. Usually invisible, and
   this is the outcome ~80% of the time.
2. **A new Tier 2 role is needed.** The value exists on the scale, but no role names this
   relationship. Routine — add it (§5.2).
3. **A new Tier 1 step is genuinely required.** A real design decision. Requires sign-off
   (§5.2) and a `DESIGN_DECISIONS.md` entry.

Send this. Short, specific, no adjectives:

```
Subject: [ProjectName] — 4 off-scale values in Pricing v3

Found while mapping Pricing v3 to tokens. Each needs a decision before I build.

1. Card padding 28px (frame "Plan card")      -> nearest tokens 24 / 32. Proposing 24.
2. Gap 18px between plan title and price      -> nearest 16 / 20. Proposing 16 (--gap-tight).
3. Heading 30px (frame "Plan name")           -> scale has 28 (--text-2xl) / 35. Proposing 28.
4. Fill #F7F5F2 on the comparison strip       -> no variable. Closest is bg/canvas.
   If this is meant to be a distinct surface, it needs a new semantic role — say the
   word and I'll add `bg/subtle` to the collection and the token file.

Defaults if I don't hear back by <date>: the "Proposing" option above, recorded in
DESIGN_DECISIONS.md. Nothing is blocked.
```

The last paragraph matters as much as the list: it converts a blocking question into a
timed default, so the handoff never stalls on a reply.

---

## 5. Working alongside other developers

### 5.1 Branches and commits

- `main` always deploys. `feat/<area>-<short-desc>`, `fix/<area>-<short-desc>`,
  `chore/…`, `design/<token-or-system-change>`. The `design/` prefix exists so system
  changes are visible in the branch list — they need different reviewers.
- Conventional commits, with two scopes that carry weight:
  `feat(tokens): add bg-subtle surface role` and `refactor(system): …`. Any commit
  scoped `tokens` or `system` requires a design reviewer.
- **A token change and a feature never ride in the same commit.** They have different
  blast radii and different reviewers. Split them; the token commit lands first.
- Rebase before merge. Squash feature branches, preserve token commits — you will want
  to bisect a spacing regression someday.

### 5.2 The design-system change protocol

The one rule everyone must know:

> **Adding a Tier 1 value is a design decision requiring sign-off.
> Adding a Tier 2 role is routine.**

| Change | Who | Review | Also required |
|---|---|---|---|
| Add a Tier 2 semantic role | Any developer | Normal PR review | A one-line comment naming its job |
| Re-point a Tier 2 role | Any developer | Normal PR + visual check of every consumer | Grep the consumers first; a re-point is a global change |
| Add a Tier 1 primitive step | Proposal only | **Design lead sign-off**, `design/` branch | `DESIGN_DECISIONS.md` entry: what needed it, what was tried, why the existing steps failed |
| Change a Tier 1 value | Proposal only | **Design lead sign-off** + full visual regression | Same, plus a migration note |
| Add a component to the system | Any developer | Design + one engineer | Stories, contract checklist, docs entry |
| Deprecate anything | Any developer | Normal PR | §5.4 |

Why the asymmetry: Tier 2 roles are vocabulary, and a team should be able to name new
relationships freely — they cost nothing and they make intent legible. Tier 1 steps are
the grid the whole product sits on **(Law 3)**; one extra step makes every future
"which one?" decision harder, forever.

### 5.3 Introducing a component without forking one

Forking is the default failure. `Button.tsx` → `ButtonV2.tsx` → three buttons, two of
which are wrong. The decision sequence, in order — stop at the first yes:

1. **Does an existing component do this with a new `variant`/`size`/`tone` value?**
   Add the value. Cheapest, and it keeps one keyboard map and one a11y story.
2. **Does it need a different internal arrangement but the same semantics?** Add a
   composition slot (`leading`/`trailing`/`children`) rather than a boolean per layout.
3. **Is it the same behaviour with different markup?** Extract the behaviour into a hook
   (`useDisclosure`) and build the second component on it. Two components, one brain.
4. **Is it genuinely a different thing?** New folder, new name, full contract (§3).
   Different *thing* means different job — not "same job, client wanted it rounder".

Never acceptable: copying a component file and editing it; wrapping a component to
override its CSS from outside; adding a `legacy` prop that switches whole appearances.

### 5.4 Deprecation with a codemod-able path

Deprecate in one PR, remove in another, at least one release apart.

```tsx
/** @deprecated Use `tone="danger"` instead of `destructive`. Removed in v3.
 *  Codemod: npx jscodeshift -t codemods/button-destructive-to-tone.ts src/ */
destructive?: boolean;
```

The deprecation PR must ship: the JSDoc `@deprecated` with the replacement *and* the
removal version; a dev-only `console.warn` fired once per component; an entry in
`DESIGN_DECISIONS.md`; and either a codemod in `codemods/` or a note stating the exact
grep that finds every call site. "Search for it" is not a migration path — the person
doing the migration will be an agent that needs an executable instruction.

For a token: keep the old name as an alias (`--btn-bg: var(--bg-accent);`) for one
release, with a comment naming the removal PR. Never delete a token in the same PR that
renames it — every in-flight branch breaks at once.

### 5.5 The "no local override" rule and its escape hatch

**No file outside a component's folder may style that component.** No
`.dashboard .Button { padding: … }`, no `:global`, no utility class bolted on to change
its internals. Local overrides are how a design system becomes a suggestion: the
component looks right in Storybook and wrong in four pages, and no one can fix it
centrally because four pages depend on the drift.

The escape hatch that replaces it — **a component exposes its own custom properties as
its adjustment API**:

```css
/* Button.module.css */
.root {
  --btn-pad-x: var(--pad-inline-md);   /* Tier 3 <- Tier 2. Public: consumers may set it. */
  --btn-pad-y: var(--pad-block-sm);
  padding-inline: var(--btn-pad-x);
  padding-block:  var(--btn-pad-y);
}
```
```css
/* Toolbar.module.css — legal, local, and bounded. */
.toolbar .root { --btn-pad-x: var(--pad-inline-sm); }
```

This is permitted because it is still Tier 2 in, still tokens only, still inside the
component's declared API — and because the day the button's padding model changes, the
component changes and every consumer follows. Which Tier 3 tokens are public is
documented in the component's doc comment. Anything undocumented is private, and
setting it is a review failure.

---

## 6. The PR review checklist

Run in order. Every item is a yes/no answerable in seconds. A "no" blocks; a "no" with
a `DESIGN_DECISIONS.md` entry attached is a conversation.

**Tokens**
- [ ] `python -m scripts.audit_design` is clean in CI on this branch?
- [ ] Zero literal values in the diff outside `tokens.json` / generated files?
- [ ] No Tier 1 token (`--space-*`, `--neutral-*`, `--accent-*`) read by a component?
- [ ] New Tier 1 steps: none, or sign-off linked in the PR description?
- [ ] Generated files regenerated, not hand-edited (diff matches a fresh build)?

**Spacing**
- [ ] No child sets an outer margin — parents own every gap?
- [ ] Gaps at the same hierarchy level use the same role?
- [ ] The gap role chosen matches the *meaning* (`--gap-tight` for label+input, not "looks right")?
- [ ] Setting `--density="compact"` on an ancestor recomposes it correctly?

**Style architecture**
- [ ] One styling home per component — no mixed inline/module/utility?
- [ ] Every rule inside a named layer; no unlayered CSS?
- [ ] Zero `!important`, zero ID selectors, nesting depth ≤ 2?
- [ ] No selector reaching into another component's internals?
- [ ] Deleted markup took its CSS with it?

**Semantics & accessibility**
- [ ] Correct element for the job — `<button>` for actions, `<a>` for navigation?
- [ ] Every interactive element reachable and operable by keyboard, in visual order?
- [ ] Focus visible everywhere, and focus moved deliberately on open/close?
- [ ] Every input has a programmatic label; every icon-only control has an accessible name?
- [ ] State expressed in ARIA, not only in color?

**Responsive**
- [ ] Checked at 320 / 390 / 768 / 1024 / 1440 / 1920?
- [ ] No horizontal scroll at any width, including at 200% zoom?
- [ ] Breakpoints chosen where the content breaks, not at device names?
- [ ] Touch targets ≥ `--tap-min` (44px)?

**States**
- [ ] All seven interactive states present?
- [ ] Empty, loading, and error states designed — not a spinner and a blank div?
- [ ] Long-string and zero-item cases don't break the layout?

**Performance**
- [ ] Images sized (`width`/`height` or `aspect-ratio`) so nothing shifts?
- [ ] Fonts preloaded with `font-display: swap` and a matched-metric fallback?
- [ ] Animations on `transform`/`opacity` only?
- [ ] No new dependency that duplicates something already in `lib/`?

**Docs**
- [ ] Stories cover every variant and the all-states case?
- [ ] New tokens documented with their role in `tokens.json`?
- [ ] Non-obvious decisions appended to `DESIGN_DECISIONS.md`?
- [ ] `IMPLEMENTATION.md`'s "Last Completed Task" updated?

---

## 7. Claude Code handoff

Work in this studio is routinely finished by a Claude Code session with no memory of the
conversation that produced the design. A handoff bundle is not documentation; it is the
agent's entire world model. Anything not in it did not happen.

### 7.1 What the bundle must contain

| Artifact | Contains | Why it's non-optional |
|---|---|---|
| `CLAUDE.md` | The Nine Laws, the project's stack, the styling choice, the token paths, the audit command | Loaded automatically. An agent without it will write reasonable, off-system code |
| `IMPLEMENTATION.md` | An ordered runbook, tasks numbered, with a **Last Completed Task** section at the top | The agent must be able to answer "where do I start?" from one file |
| `design/tokens.json` + generated CSS/TS | The value vocabulary | Without it the agent invents values, and they'll be plausible |
| `scripts/audit_design.py` wired to `npm run design:audit` **and** a pre-commit hook | Law 9's teeth | An agent will run a documented npm script. It will not intuit a Python module path |
| `DESIGN_DECISIONS.md` | Why non-obvious choices were made | Prevents the agent "fixing" a deliberate choice. This is the highest-value file in the bundle and the most often missing |
| Component stories | The visual contract | The agent's only way to know what "right" looks like |

Wire the audit so it cannot be skipped:

```json
{ "scripts": {
    "design:tokens": "node design/build-tokens.mjs",
    "design:audit":  "python -m scripts.audit_design",
    "predeploy":     "npm run design:audit"
} }
```
```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: design-audit
      name: design system audit
      entry: python -m scripts.audit_design
      language: system
      pass_filenames: false
```

### 7.2 The `CLAUDE.md` template

Copy verbatim, fill the bracketed lines, delete nothing.

````markdown
# CLAUDE.md — <Project Name>

## Stack
- React 19 + Vite + TypeScript. **React 19: `ref` is a prop. Never use `forwardRef`.**
- Styling: <CSS Modules (camelCase) | Tailwind | plain CSS custom properties> — **this
  project uses exactly one. Do not introduce a second.**
- Backend: <FastAPI | Supabase>. Deploys on Railway. Env via `.env` / Railway vars.
- Package manager: <npm | pnpm>.

## The Nine Laws — non-negotiable

1. **Tokens or nothing.** Every value in every rule traces to a Tier-2 token. Literals
   exist only in `design/tokens.json`. No hex, no px, no ms in a component.
2. **Parents own the gaps.** A child never sets outer margin. The parent sets `gap`.
3. **The scale is closed.** No values between defined steps. If a gap "needs" 28px, the
   layout is wrong, not the scale.
4. **One home per component's styles.** No mixing inline/stylesheet/utilities. Inline
   `style` only to pass a runtime number in as a custom property.
5. **Layers, not specificity.** `@layer reset, tokens, base, layout, components,
   utilities, overrides`. No `!important`. No IDs. Max nesting depth 2.
6. **Semantic before primitive.** Components read `--pad-card`, never `--space-6`.
7. **Density is a dial.** Spacing scales via `--density`; never rewrite padding rules.
8. **Novel patterns pass a usability gate** before they ship. Proven pattern first.
9. **Nothing ships un-audited.** `npm run design:audit` must be clean.

## Token system
- Source of truth: `design/tokens.json` (hand-edited).
- Generated: `src/styles/tokens.css`, `src/lib/tokens.ts` — **NEVER hand-edit.**
  Regenerate with `npm run design:tokens`.
- Tiers: Tier 1 primitive (`--space-6`, `--neutral-800`) → Tier 2 semantic
  (`--pad-card`, `--fg-muted`) → Tier 3 component (`--btn-pad-x`, declared in the
  component file). **Components read Tier 2 only.**
- Dark mode: `[data-theme="dark"]` re-points Tier 2 in `tokens.css`. **There must be
  zero `dark` selectors in any component file.**
- Density: `[data-density="compact|comfortable|spacious"]` sets `--density`.
- Brand accent hue: <42>. Neutral hue: <75>.

## Commands
```bash
npm run dev            # Vite dev server
npm run design:tokens  # regenerate tokens.css + tokens.ts from tokens.json
npm run design:audit   # Law 9 gate — MUST be clean before you say you're done
npm run test
npm run build
```

## Where things go
- `src/styles/` — global cascade only. `index.css` declares the layer order.
- `src/components/<Name>/` — `<Name>.tsx`, `<Name>.module.css`, `<Name>.types.ts`,
  `<Name>.stories.tsx`, `<Name>.test.tsx`, `index.ts`. Folder name == component name.
- `src/app/routes/` — composition only. No component definitions, no styling decisions.
- `src/lib/` — framework-agnostic logic. No JSX, no CSS imports.
- `public/` — served verbatim. Fonts, favicons, og images.

## Conventions
- Props: `variant` / `size` / `tone`. Booleans named for the true state (`disabled`,
  not `isDisabled`). No `isPrimary`-style visual booleans.
- State on elements: `data-state="open"`, styled as `[data-state="open"]`. Not classes.
- Tests select by role + accessible name, else `data-testid="<component>-<part>"`.
- Logical properties only (`margin-inline`, `inset-inline-start`). The product ships RTL.
- Every component: merges `className`, accepts `ref`, spreads rest props onto the
  semantic element, implements default/hover/focus-visible/active/disabled/loading/error.

## Before you say a task is done
1. `npm run design:audit` — clean.
2. `npm run test` — green.
3. Checked at 320 / 390 / 768 / 1024 / 1440 px and at 200% zoom.
4. Keyboard-only pass: everything reachable, focus always visible.
5. Toggled `[data-theme="dark"]` — no component CSS changed to make it work.
6. Updated **Last Completed Task** in `IMPLEMENTATION.md`.
7. Appended any non-obvious choice to `DESIGN_DECISIONS.md`.

## Do not
- Do not add a Tier 1 token (a new `--space-*` / ramp step) without asking. That is a
  design decision requiring sign-off. Adding a Tier 2 role is fine — do it freely.
- Do not hand-edit generated files.
- Do not add a CSS framework, UI kit, or icon library not already in `package.json`.
- Do not fork a component to make a variant. Add a `variant`/`tone` value.
- Do not style a component from outside its folder. Set its documented Tier 3 custom
  properties instead.
- Do not use `!important` to resolve a conflict. Fix the layer.
````

### 7.3 `IMPLEMENTATION.md` shape

```markdown
# Implementation Runbook

## Last Completed Task
**Task 7 — Pricing page card grid.** Committed `a1b2c3d` on 2026-09-16.
Notes: card padding snapped 28px → `--pad-card` (24px) per designer approval in
DESIGN_DECISIONS #12. `--gap-grouped` between cards.
**Next: Task 8.**

## Task list
- [x] 1. Token pipeline + layer order
- [x] 2. Layout primitives (stack, cluster, grid, container)
- [x] 3. Button, Input, Field
- [ ] 8. Pricing comparison table — needs a `bg-subtle` surface role (see #14)
- [ ] 9. Checkout flow

## Blocked / needs a decision
- #14 `bg/subtle` surface role — asked designer 2026-09-16, no reply. Default if
  silent by 09-20: use `--bg-sunken`.
```

**Last Completed Task** is the single highest-leverage section: it is how a new session
resumes in one read instead of five greps and a guess.

---

## 8. Definition of done

### A component is done when

1. All twelve contract items (§3) are true.
2. Stories exist for every `variant` × `size` × `tone` it claims, plus an all-states story.
3. Tests cover the keyboard map, the controlled and uncontrolled paths, and the
   accessible name of every interactive part.
4. It renders correctly under `[data-theme="dark"]` and `[data-density="compact"]` with
   no component CSS written for either.
5. It contains zero outer margins **(Law 2)** and zero Tier 1 token reads **(Law 6)**.
6. Its public Tier 3 custom properties are documented in its doc comment.
7. `npm run design:audit` and `npm run test` are clean.

### A page is done when

1. Every component on it is done by the above.
2. It composes — the page file contains layout and data, not styling decisions. A page
   that needed new CSS to look right has found a missing layout primitive; build the
   primitive.
3. Verified at 320 / 390 / 768 / 1024 / 1440 / 1920 and at 200% zoom, with no horizontal
   scroll at any of them.
4. Section rhythm uses `--space-section` / `--space-subsection` / `--space-block`
   consistently; two sections at the same level have identical separation.
5. Keyboard-only pass completes the page's primary task. Focus order matches visual
   order. A skip link reaches `<main>`.
6. Landmarks present and unique: one `<main>`, labelled `<nav>`s, `<h1>` present once,
   heading levels unskipped.
7. Real content, including the longest plausible string and the empty case.
8. Loading, empty, and error states designed — reached by disabling the network, not
   only by imagining them.
9. Lighthouse/CWV: LCP element identified and preloaded, CLS sources eliminated, no
   layout-triggering animation.
10. `references/review-checklist.md` run top to bottom, clean.
11. `IMPLEMENTATION.md` and `DESIGN_DECISIONS.md` updated in the same PR.
