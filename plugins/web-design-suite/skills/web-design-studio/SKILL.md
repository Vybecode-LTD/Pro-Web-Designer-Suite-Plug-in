---
name: web-design-studio
description: Design systems and front-end architecture, enforced by an audit that fails the build. Covers tokens.css, a closed spacing and type scale, OKLCH colour with measured contrast, cascade layers, layout primitives and density. Use for new builds, redesigns and CSS architecture. Not for page copy (landing-page-conversion) or reviewing finished work (design-critique-gate).
---

# Web Design Studio

> **Running the scripts** — by path, from the user's project root, so `src/`
> means the project's `src/` and every output lands in the project, never
> inside this plugin:
>
> ```bash
> python "${CLAUDE_SKILL_DIR}/scripts/generate_color_ramp.py" "#e8440a" --name accent --format css
> ```
>
> The commands below are written `python -m scripts.<name>`. That form is for a project that
> has copied the scripts into its own `scripts/` folder, as CI and git hooks
> do; when you run one here, use the path form.
> This skill's scripts are in `${CLAUDE_SKILL_DIR}/scripts/` (audit_design.py, check_roles.py, generate_color_ramp.py, generate_type_scale.py).

A complete method for designing and building websites that look considered and stay coherent when more than one person touches them.

Two halves, held in tension on purpose:

- **Rigor.** A closed token system, one styling home per component, and a script that fails the build when either slips. This is what makes work survive handoff.
- **Invention.** A disciplined procedure for producing navigation and control patterns that do not exist yet, with a gate that stops the unusable ones from shipping. This is what makes work worth handing off.

Neither half works alone. Rigor without invention produces competent, forgettable sites. Invention without rigor produces a beautiful first draft and a codebase nobody can extend.

---

## The Nine Laws

These are the whole skill compressed. Everything in `references/` is one of them in detail.

**1. Tokens or nothing.** Every value in every rule resolves through a token. Literal values live in exactly one file: `tokens.css`. A literal anywhere else is a decision nobody can find, change or theme.

**2. Parents own the gaps.** A child never sets its own outer margin. The space between siblings is set by the parent, with `gap`. A component cannot know what it sits next to, so a margin declared inside it is a fact asserted from a position of ignorance — and it is the single largest source of "why is this one 8px lower."

**3. The scale is closed.** 18 spacing steps, 11 type steps, 5 leadings, 6 elevations, 5 durations, 8 z-indexes. There is nothing between the steps. The constraint is the mechanism; the moment you add a step to settle a disagreement, the scale becomes a menu and stops doing its job.

**4. One home per component's styles.** A reviewer who has never seen a component must be able to predict its appearance from one file. Inline `style` is permitted only when every key is a CSS custom property — that passes a runtime *number* into the cascade without moving a visual *decision* out of the stylesheet.

**5. Layers, not specificity.** `@layer reset, vendor, tokens, base, layout, components, utilities, overrides;` — declared once, first, before any import. Override order is decided by the layer statement, never by winning a selector fight. No `!important`, no ID selectors, nesting depth 2 maximum.

**6. Semantic before primitive.** Components read role tokens (`--pad-card`, `--fg-muted`), never primitives (`--space-6`, `--neutral-600`). Right value, wrong tier is still wrong: the day "more air in cards" lands, you want to change one role, not grep a repo.

**7. Density is a dial.** Compact and spacious are `--density`, not a second set of styles. If a component has a hardcoded value anywhere, switching density is what reveals it.

**8. Novel patterns pass the gate.** Invention is expected. Shipping something a first-time user cannot operate with a keyboard is not. Every invented pattern clears the hard-fail checklist in `references/pattern-invention.md` before it enters a build.

**9. Nothing ships un-audited.** `python -m scripts.audit_design <path>` must exit clean. Not "looks fine to me" — clean.

---

## Workflow

Work the phases in order. The ordering is not bureaucracy: every phase's decisions are inputs to the next, and skipping ahead is how projects end up with a beautiful hero section bolted to an incoherent system.

### Phase 0 — Brief

Before any file exists, get four things settled. If the user is present, ask; if not, decide, state the assumption at the top of your output, and proceed.

| Question | Why it gates everything after it |
|---|---|
| **Stack?** Tailwind, vanilla CSS, CSS Modules/SCSS | Decides which enforcement config ships and how components are authored |
| **Archetype?** marketing, SaaS app, commerce, editorial, docs, portfolio | Decides the navigation pattern before you draw anything |
| **Brand adjectives?** 3–5 words | Feeds directly into hue, chroma and neutral temperature |
| **New build or existing site?** | An existing site starts with an audit, not a design |

For an existing site, run `python -m scripts.audit_design` first and read the result before proposing anything. The findings usually *are* the brief.

### Phase 1 — Tokens

Copy `assets/starter/styles/tokens.css` and adapt it. This is the only phase where you write literal values.

1. **Color.** Derive the accent hue from the brand adjectives using the table in `references/color-system.md` §4, then generate the ramps:
   ```bash
   python -m scripts.generate_color_ramp "#e8440a" --name accent --format css
   python -m scripts.generate_color_ramp "#e8440a" --neutral --name neutral --format css
   ```
   The script prints the WCAG matrix. **Verify contrast, never assume it** — the starter tokens themselves shipped with two failing pairings until the generator caught them.
2. **Type.** Pick a ratio for the archetype (dense UI 1.125–1.2, editorial 1.25–1.333) and generate:
   ```bash
   python -m scripts.generate_type_scale --base 16 --ratio 1.2 --dual-ratio 1.25 --fluid 380 1440 --format css
   ```
3. **Spacing.** Leave the scale alone. Adapt only the Tier-2 *roles* if the project's rhythm genuinely differs.

Deliver the token file and get sign-off on it before building anything. A token change after twenty components exist is cheap; a token *disagreement* discovered then is not.

### Phase 2 — Structure before surface

Decide navigation and layout before any visual design. Read `references/navigation-patterns.md` §1 — the selection matrix keyed on archetype and on number of top-level destinations — and pick the pattern. Then pick the page skeleton from `references/layout-composition.md`.

This is also where invention happens, because navigation is where a site's personality actually lives. Run the procedure in `references/pattern-invention.md` and produce three variants at three risk levels. Run the gate. Present the conservative and distinctive options with what each costs the user; do not present a radical variant that failed the gate.

### Phase 3 — Layout primitives

Copy `assets/starter/styles/layout.css`. Build every page as a composition of Stack, Cluster, Grid, Sidebar, Switcher, Center, Cover, Frame, Reel. Write no bespoke layout CSS. This is what keeps spacing decisions in ten places instead of four hundred.

### Phase 4 — Components

For each component, follow the five-part shape in `references/style-architecture.md` §6: socket block, structure, variants, states, parts. Every interactive component implements all seven states — default, hover, focus-visible, active, disabled, loading, error — plus designed empty and loading states for anything that fetches.

Pick each gap with the procedure in `references/spacing-system.md` §6. Say out loud what each gap means. If you cannot finish the sentence "this is `--gap-tight` because…", you eyeballed it.

### Phase 5 — Audit and gate

```bash
python -m scripts.audit_design src/ --strict
```

Then run `references/review-checklist.md` top to bottom: 92 checks across tokens, spacing, architecture, type, color, responsive, states, accessibility, motion, performance, content and handoff. A failed check is fixed **at the system level** — a token, a primitive, a role — never patched locally. A local patch is precisely how the drift starts.

### Phase 6 — Handoff

Per `references/handoff-conventions.md`: repo shape, a `CLAUDE.md` restating the laws and the audit command, an ordered `IMPLEMENTATION.md`, `DESIGN_DECISIONS.md` for the non-obvious choices, and the audit wired into an npm script and a pre-commit hook. The template is in `references/handoff-conventions.md` §7, copy-paste ready.

---

## The suite

`web-design-studio` is the system. Twelve sibling skills extend it, and each one shares this skill's token vocabulary and the nine laws verbatim (`references/token-contract.md` is identical in all thirteen). Reach for them by name.

| Skill | Reach for it when |
|---|---|
| **design-token-migration** | You inherited a codebase. Extracts every literal, clusters them into what they were *trying* to be, proposes a token file derived from the code's own values, generates the codemod, and proves it worked with a before/after audit diff. Includes a baseline-and-freeze strategy so the gate goes on today rather than after a rewrite nobody approves. |
| **figma-variables-sync** | A designer handed you a file. Audits it for off-scale values *before* you build, maps Figma variables/modes/auto-layout onto the three tiers, generates tokens in both directions, and gives you the message to send back when the design and the system disagree. |
| **component-state-matrix** | A component is "done". Renders every component across 7 states × 3 densities × 2 themes as one proof sheet, which is the only reliable way to find a hardcoded value, a missing state, or a dark mode that was never re-pointed. Screenshot-diffs in CI. |
| **landing-page-conversion** | The page has to persuade. This skill owns everything this one deliberately omits: positioning, message hierarchy, section sequencing against the objection ladder, headline and CTA copy, and the conversion audit. |
| **design-critique-gate** | You are about to show it to a client. The adversarial pass — ten layers in the order a real reviewer's eye moves, a catalogue of the failures that make work read as *almost* professional, and a severity rubric that surfaces the three things actually worth fixing. |
| **design-system-docs** | Somebody else has to use this. Generates the documentation *from* the token files and component socket blocks, so it cannot drift, and fails CI when a hand-written claim stops matching the code. |
| **content-model-to-ui** | The schema exists and now it needs screens. Maps Postgres/Supabase columns to controls by semantics rather than type, asks the handful of questions a schema cannot answer, and scaffolds on-system list/detail/form views. |
| **email-template-system** | It has to land in an inbox. The one place these laws must bend — tables, inlined styles, no cascade — owned deliberately, with the token file still the source of truth and a compiler doing the inlining. |
| **perf-budget-gate** | Fast is a feature you have to defend. The sibling of `audit_design.py`: static budget checks on every commit, real LCP/CLS/INP measurement in CI, and a baseline so an existing slow site can be frozen rather than ignored. |
| **a11y-audit-runner** | The runtime accessibility gate. axe-core, computed accessible names, real tab-order extraction, focus visibility measured in pixels rather than assumed, forced-colors. Honest that automation decides only part of WCAG, and builds the human pass into the workflow. |
| **design-system-versioning** | The system has consumers now. Classifies every change against a token-specific breaking-change taxonomy, computes the blast radius of a Tier-1 edit, flags contrast crossings, and generates the changelog, migration guide and codemod. |
| **client-presentation-builder** | You have to present it. Turns the decision log and the gate results into a deck that argues decisions rather than defending taste — and refuses to dress a coin-flip up as rationale. |

The usual chain on a client project: `design-token-migration` (if inherited) → `figma-variables-sync` (if designed elsewhere) → **this skill** → `content-model-to-ui` (if it is data-driven) → `landing-page-conversion` (if it sells) → `component-state-matrix` → `perf-budget-gate` → `a11y-audit-runner` → `design-critique-gate` → `design-system-docs` → `client-presentation-builder` → ship. `design-system-versioning` governs every change after that.

---

## Reference routing

Read the file when you hit the decision it covers. Do not read them all up front.

| Read this | When |
|---|---|
| `references/spacing-system.md` | **Any time you are about to type a spacing value.** The most important file here. |
| `references/style-architecture.md` | Setting up a stylesheet, deciding where a declaration goes, or untangling an override |
| `references/color-system.md` | Choosing or verifying a palette, dark mode, contrast, gradients |
| `references/typography.md` | Type scale, leading, measure, tracking, font loading, fluid type |
| `references/layout-composition.md` | Page skeletons, grids, container queries, responsive strategy, alignment |
| `references/navigation-patterns.md` | Choosing or building any nav — 17 patterns with keyboard, touch and a11y contracts |
| `references/navigation-code.md` | Building a scroll-aware header, a mega menu, a drawer or a scroll-spy: working code |
| `references/pattern-invention.md` | Inventing anything, or deciding whether an idea is safe to ship |
| `references/motion-system.md` | Any animation, transition, or scroll behavior |
| `references/accessibility.md` | Always, and specifically before declaring anything done |
| `references/handoff-conventions.md` | Repo structure, naming, Figma mapping, multi-dev rules, Claude Code handoff |
| `references/review-checklist.md` | The final gate, every time |
| `references/token-contract.md` | The shared vocabulary — identical across all thirteen suite skills |
| `references/stack-tailwind.md` | The project uses Tailwind |
| `references/stack-vanilla-css.md` | The project uses plain CSS + custom properties |
| `references/stack-css-modules.md` | The project uses CSS Modules or SCSS Modules |

---

## Scripts

All stdlib-only Python 3, no dependencies.

```bash
# The gate. Law 9.
python -m scripts.audit_design src/                    # audit
python -m scripts.audit_design src/ --strict           # warnings fail too
python -m scripts.audit_design src/ --json             # machine-readable
python -m scripts.audit_design src/ --write-baseline .design-baseline.json
                                                       # adopt on a legacy repo:
                                                       # only NEW findings fail
python -m scripts.check_roles src/styles/tokens.css   # role pairs per theme: text 4.5:1,
                                                       # borders and the focus ring 3:1

# Generators. Run these in Phase 1.
python -m scripts.generate_color_ramp "#e8440a" --name accent --format css
python -m scripts.generate_color_ramp "#e8440a" --neutral --name neutral
python -m scripts.generate_color_ramp --check "#ffffff" "oklch(56.5% 0.176 42)"
python -m scripts.generate_type_scale --base 16 --ratio 1.2 --fluid 380 1440 --preview
```

`check_roles.py` is the palette's gate: it resolves every Tier-2 role in light, dark and `.inverse`, checks the pairs components put together, and prints the role table `references/color-system.md` §6 quotes (`--table`). Run it on every change to `tokens.css`.

`audit_design.py` enforces Laws 1–6 across CSS, SCSS, JS and JSX: class strings in `className` and in `cn()`, `clsx()`, `cva()` and the other class helpers, Tailwind v4 syntax, and styled-components or emotion template bodies, audited as CSS. A style object passed by name (`style={box}`) is out of its reach; ESLint's `style` rule covers the inline form. It understands cascade layers, distinguishes component files from token files, knows that `em` is a ratio and `vw` is relational, and allows the documented exceptions (`margin: auto`, the owl selector written in a parent's rule, `calc(var(--t) * -1)`). Escape hatches are comment pragmas, so every one is visible in review:

```css
/* design-audit-ignore-next-line: L2 -- CMS flow container, see ADR-014 */
```

---

## Starter assets

`assets/starter/styles/` is a working, drop-in stylesheet set. It passes its own audit.

| File | What it is |
|---|---|
| `tokens.css` | The three-tier token system. Contrast-verified. The one file with literals. |
| `reset.css` | Modern reset. The margin-zeroing is what *enables* Law 2. |
| `base.css` | Element defaults, prose rhythm with heading asymmetry, all in `:where()` |
| `layout.css` | Every layout primitive, each with Tier-3 sockets |

`assets/configs/` holds the enforcement: `theme.css` (Tailwind v4 `@theme`), `tailwind.config.ts` (v3), `eslint.design.config.mjs`, `stylelint.config.mjs`, `pre-commit-design-gate.sh`.

---

## Two things worth saying plainly

**On spacing.** Most spacing chaos is not a taste failure or a discipline failure. It is four specific systems failures — two owners for one gap, an unbounded value space, values chosen by eye one at a time, and space that encodes no meaning. Laws 1, 2, 3 and 6 are those four failures inverted. Fixing spacing is not about being more careful; it is about making the careless answer impossible to write.

**On invention.** Innovate on *expression, arrangement and feedback*. Never on *primitives, affordances and expectations*. Scrolling, browser back, text selection, link behavior, form semantics, authentication and checkout are closed — not because they are perfect, but because a user's transferred expectation is worth more than any improvement you could make. Everything above that line is open, and that is a much larger territory than it sounds.

---

## Deliverable shape

Inside a repository — Claude Code working in the user's project — write the files into the repo itself, where they are committed and reviewed like any change. Only when there is no repository to write into (a chat session, a handoff to another team), or the user asks for one, package the result as a ZIP that drops straight into a repository. Either way the deliverable is the same set: the full folder structure, the token and style files, the components built so far, `CLAUDE.md`, `IMPLEMENTATION.md`, `DESIGN_DECISIONS.md`, the audit script, and the lint configs wired into `package.json` and a pre-commit hook. The test is that Claude Code can be pointed at the result and continue without asking a single structural question.
