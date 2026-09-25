# Extraction

How to read a design system out of its own source. This is the technical core of the skill: everything `build_docs.py` renders, `extract_system.py` first has to recover from CSS and TypeScript that were written for a browser, not for a parser.

The governing constraint: **a parser that refuses a file is a parser nobody runs twice.** Every rule below degrades rather than fails. An unknown at-rule is skipped, an unparseable value is reported as unresolved with a reason, a component with no props file gets a page without a props table. Nothing aborts.

## Contents

1. [The scanner](#1-the-scanner)
2. [Tier classification](#2-tier-classification)
3. [Cascade contexts and theme re-points](#3-cascade-contexts-and-theme-re-points)
4. [Comments are the only prose the source already has](#4-comments-are-the-only-prose-the-source-already-has)
5. [Static resolution, and its honest limits](#5-static-resolution-and-its-honest-limits)
6. [Parsing a component stylesheet](#6-parsing-a-component-stylesheet)
7. [Forced states](#7-forced-states)
8. [Parsing the TS/TSX](#8-parsing-the-tstsx)
9. [Detecting what is missing](#9-detecting-what-is-missing)
10. [Determinism](#10-determinism)

---

## 1. The scanner

A regex over a stylesheet gets you about 80% of the way and then silently lies. `@layer`, nested rules, `:not(...)` with a comma in it, a `;` inside a `url()`, a comment between a value and its semicolon — each of those breaks a different regex. The extractor uses a small character-level scanner instead, about 120 lines, which tracks four things:

- **a selector stack** — the nested rule chain, outermost first, so a declaration knows its full context;
- **an at-rule stack** — `@layer components`, `@media (prefers-color-scheme: dark)`, `@supports`, preserved in order;
- **balanced parens and strings** — a `(` is consumed to its matching `)` in one step, so commas and semicolons inside `clamp()`, `var()` fallbacks and `url()` are never mistaken for separators;
- **line numbers** — every declaration carries one, because "where is this declared" is a question every reader has and a link is the answer.

It emits a flat list of declarations, each with `prop`, `value`, `line`, `selectors`, `at_rules` and `note`, plus the rules that contain them. Everything downstream is a query over that list. Nothing downstream re-parses CSS, which is the reason `build_docs.py` imports the scanner rather than owning a second one: two CSS parsers in one tool is two opinions about what a socket is.

**What it deliberately does not do:** resolve the cascade. It does not decide which of two competing rules wins. Specificity is a rendering question, and a documentation tool that guesses at it will be wrong in exactly the interesting cases. Where two declarations of the same token exist, both are recorded, with their contexts, and the page shows both.

---

## 2. Tier classification

The tier of a token is the single most load-bearing fact about it: it decides who may read it, and a docs page that gets it wrong teaches a Law 6 violation.

There are two signals, and the extractor uses both.

### Signal 1 — the name

The contract's vocabulary is a closed list of prefixes:

| Tier 1 prefixes | Tier 2 prefixes |
|---|---|
| `--space-` `--neutral-` `--accent-` `--success-` `--warning-` `--danger-` `--info-` `--text-` `--leading-` `--tracking-` `--weight-` `--font-` `--radius-` `--stroke-` `--shadow-` `--dur-` `--ease-` `--bp-` `--z-` `--measure-` `--width-` `--tap-` `--density` `--grid-columns` | `--gap-` `--pad-` `--gutter-` `--bg-` `--fg-` `--border-` `--type-` `--elevation-` `--motion-` |

Note what is *not* in the Tier-2 column: `--radius-*`, `--stroke-*`, `--z-*`, `--bp-*`, `--font-*`, `--measure-*`, `--width-*`, `--tap-min`. Those are primitives with no role layer, and a component reading them directly is correct. A classifier that flags them produces a gap list nobody trusts, which is the same as no gap list.

### Signal 2 — what the value references

A declaration whose value is a literal is a primitive. A declaration whose value is `var(--something-else)` is re-pointing, which is what a role does. This is the fallback for project-local names the contract never saw:

```css
--brand-surface-alt: var(--neutral-100);   /* references a token  -> Tier 2 */
--brand-blur:        8px;                  /* a literal           -> Tier 1 */
```

### The trap

> `--space-section`, `--space-subsection`, `--space-block` and `--space-fluid-sm|md|lg|xl` live in the `--space-*` namespace and **are Tier 2**.

The tier is a property of the name's *meaning*, not its first word. Page rhythm reads better in the spacing namespace, so that is where it lives, and every prefix-only classifier gets all seven of them wrong — marking Tier-2 roles as primitives, which then makes every correct component that reads `var(--space-section)` look like a Law 6 violation. The exception list is checked **before** the prefix table, and it is checked in `audit_design.py` too. If you fork one, fork both.

The classifier records *why* it decided, and the docs page prints it. "name — `--pad-*` → inset role" and "contract exception list" are different levels of confidence, and a reader auditing the tier column deserves to see which one they are looking at.

### A structural check worth running

The contract says themes re-point Tier 2 **only**. So any token that (a) classifies as Tier 1 by name and (b) is re-pointed inside a theme block is a contradiction worth reporting — either it is a documented exception, or it is a role that was never made.

Run against the canonical `tokens.css`, this reports eleven: `--shadow-xs` through `--shadow-xl` re-pointed by the dark theme, and `--dur-*` plus `--ease-spring` re-pointed under `prefers-reduced-motion`. Both are deliberate and both are correct — shadows read as mud on dark surfaces and have no elevation-role indirection at the primitive level; reduced motion collapses durations at the source. They are reported at `info` severity precisely because they are the kind of thing a reader should see once and then stop worrying about. A checker that suppressed them would also suppress the accidental version.

---

## 3. Cascade contexts and theme re-points

Every declaration of a custom property is filed by the context it appears in, derived from the selector and the enclosing at-rules:

| Context | Detected from | Example |
|---|---|---|
| `root` | `:root`, `html`, `:where(:root)` | the default values |
| `theme` | `[data-theme="x"]`, or `@media (prefers-color-scheme: dark)` | the dark re-points |
| `density` | `[data-density="x"]` | `--density: 0.875` |
| `condition` | `prefers-reduced-motion`, `forced-colors`, `prefers-contrast` | the motion collapse |
| `scoped` | anything else | a component or a region override |

From those, one resolution environment is built per theme: the root values, with each theme's overrides applied over the top. Density gets its own environments rather than multiplying the theme matrix, because density is a *multiplier* (Law 7), not a second set of values — so a token is resolved at density 1 and reported separately at compact and spacious only when the two differ.

Against the canonical token file this recovers 31 dark re-points, 3 density modes and 6 reduced-motion overrides, with no configuration.

**A token declared only inside a theme** is recorded and flagged. It resolves to nothing in the default theme, which is a real bug that is invisible in review because the theme you are looking at is the one where it works.

---

## 4. Comments are the only prose the source already has

```css
--neutral-500: oklch(53.5% 0.009 75);
/* 500 sits at L 53.5%, not the 58% a naive even ramp would give. That extra
   darkness is what lets --fg-subtle clear 4.5:1 on --bg-sunken. Verified 4.60:1. */
```

That paragraph is the highest-value sentence in the entire token file and it already exists. Extracting it costs nothing and skipping it throws away the one piece of rationale a parser *can* reach.

Two attachment rules, both of which have a trap in them:

**A comment with code before it on the same line annotates that line.** `--space-4: 1rem;  /* 16px the anchor step */`. The trap: the declaration was already flushed by the `;` before the scanner reached the comment, so attaching notes has to happen in a **second pass** over the collected declarations, keyed by line. Doing it inline silently drops every trailing comment in the file — which is most of the useful ones.

**A comment with nothing before it annotates whatever follows it**, if it ends on the line immediately above. Banner comments (`/* ---- 3. TYPOGRAPHY ---- */`) are followed by a blank line in every file written to the house style, so the rule separates them from real notes without a heuristic. Rules of dashes and equals signs are stripped from the text anyway.

---

## 5. Static resolution, and its honest limits

The goal is the number a designer asked for. The rule is that **an admitted "cannot compute" is worth more than a confident wrong value**, because the first costs a reader thirty seconds and the second costs them a bug.

### Substitution

`var(--x)` is replaced with `--x`'s value in the current environment, recursively, with the fallback used when the token is undeclared, a cycle detected by keeping the chain, and a depth cap. An undeclared token with no fallback is not an error — it is a finding, reported as `--x is referenced but never declared`.

### Evaluation

Expressions are evaluated as a **linear combination of units** rather than a single number: `{px: 24}`, `{rem: 0.811, vw: 0.755}`, `{"": 1}` for a bare number. Addition and subtraction merge the maps; multiplication and division require one side to be dimensionless, which is exactly the CSS rule. `rem` folds to px at `--root-font-size` (16 by default, and settable, because a system that ships a 62.5% root and does not say so is a system whose docs are all wrong by a factor of 1.6).

| Construct | Result |
|---|---|
| `calc(var(--space-6) * var(--density))` | `24px` — exact |
| `min()` / `max()` with static args | the computed value |
| `clamp(4rem, 2.113rem + 7.547vw, 9rem)` | `64px … 144px` — a **range**, labelled fluid |
| `calc()` embedded in a larger literal | folded in place, so `--shadow-focus` prints `0 0 0 4px …` rather than `0 0 0 calc(2px * 2) …` |
| `oklch()` / hex | the value, the hex, and the contrast |
| anything in `em`, `ch`, `ex`, `%`, `cq*` | unresolved, with what it is relative to |

### What cannot be resolved, and why the reason matters

Against the canonical token file, exactly seven tokens do not resolve: `--measure-prose` and `--measure-narrow` (`ch` — relative to the rendered font's `0` advance) and the five `--tracking-*` (`em` — relative to the element's own font size). Ten more resolve to ranges rather than points: the four `--space-fluid-*`, the four page-rhythm roles built on them, and `--text-5xl` / `--text-6xl`.

Every one of those is reported with the unit and the thing the unit is relative to. That phrasing is deliberate: "unresolved" teaches nothing, "depends on `ch` — relative to the rendered font's `0` advance" teaches the reader why no tool will ever give them a number, so they stop looking for one.

### Colour and contrast

Colours resolve to an OKLCH triple, a hex, and an alpha. Contrast is computed for every `--fg-*` role against every surface role, in every theme, using the **same OKLab and WCAG functions as `generate_color_ramp.py`** — imported from it when the suite is installed whole, and a verified byte-identical vendored copy otherwise, with `--check-color-impl` to prove the two agree. This is not fastidiousness: the day a docs page reports 4.48:1 and the ramp generator reports 4.52:1 for the same pair, both numbers become worthless and the team goes back to eyeballing.

Two deliberate refusals:

- **`--fg-on-*` is never measured against a surface.** It names its own background; white on `--bg-canvas` produces a meaningless 1.05:1 that clutters the table and trains people to ignore the column.
- **A translucent role gets no ratio at all.** `--bg-hover` is `oklch(0% 0 0 / 0.04)`; its contrast depends on what is behind it, which the source cannot say. The limitation is printed instead of a number.

---

## 6. Parsing a component stylesheet

The five-part component shape from `style-architecture.md` §6 is what makes this tractable. A component that follows it is self-describing.

### Finding the component

A component root is a rule whose selector is exactly one class, and which declares custom properties namespaced to that class:

```css
.button { --button-pad-inline: …; --button-bg: …; }
```

`.button` + `--button-*` is a self-identifying pair. No manifest, no naming convention beyond the one the contract already requires, and no false positives — a utility class does not declare a socket block. Run against the studio's own `layout.css`, this finds seventeen layout primitives (`.stack`, `.cluster`, `.with-sidebar`, …) without being told they exist.

### Reading the five parts

| Part | Recovered from |
|---|---|
| 1. Sockets | custom properties on the root rule: name, default, inferred type, source comment |
| 2. Structure | the non-custom declarations on the root rule, which tell you which socket each property consumes |
| 3. Variants and sizes | `[data-variant="x"]` and `[data-size="x"]` selectors, and which sockets each re-points |
| 4. States | pseudo-classes and ARIA attributes (see below) |
| 5. Parts | `.component__part` classes and the properties each sets |

The socket's **accepted type** is inferred from the default's resolved kind: a default of `var(--pad-inline-md)` resolves to a length, so the socket accepts `<length>`; `var(--motion-hover)` resolves to a duration and an easing curve, so it accepts `<time> <easing-function>`. That is the column a consumer needs before setting a socket from outside, and nobody has ever maintained it by hand.

The socket's **consumers** come from scanning every declaration in the component for `var(--button-x)`. A socket with no consumers is published API that does nothing.

### State detection, and the guard trap

| State | Signature |
|---|---|
| `hover` | `:hover` |
| `focus-visible` | `:focus-visible` |
| `active` | `:active` |
| `disabled` | `:disabled`, `[aria-disabled`, `[data-state="disabled"` |
| `loading` | `[data-state="loading"`, `[aria-busy` |
| `error` | `[aria-invalid`, `[data-state="error"`, `[data-invalid` |

**Strip `:not(...)` before matching.** `.button:hover:not(:disabled)` is a hover rule. The `:disabled` inside the guard is a *condition on when hover applies*, not a disabled-state rule — and reading it as one makes every correctly-written component appear to implement a state it does not. This is the single highest-yield line in the state parser, and it is four characters of regex.

`:focus-within` is recorded but is **not** counted as focus coverage. A component that styles the container but not the control produces the failure where the card lights up and the thing with focus does not, so it is reported as a `weak-state` rather than quietly counted as a pass.

---

## 7. Forced states

You cannot hover twelve examples at once, so every pseudo-class state rule is mirrored onto an attribute:

```css
/* yours */      .button:hover:not(:disabled)                      { --button-overlay: var(--bg-hover); }
/* generated */  .button[data-force-state~="hover"]:not(:disabled) { --button-overlay: var(--bg-hover); }
```

Three properties make this safe:

- **Identical specificity.** `:hover` and `[data-force-state~="hover"]` are both 0,1,0, so the mirror wins on document order, not on a fight — no `!important`, no escalation, nothing to unwind later.
- **Same layer, same at-rule context.** The mirror is emitted inside the rule's own `@layer` and inside any `@media` it was written in. A hover rule behind `@media (hover: hover)` stays behind it, and will therefore not render on a coarse pointer — which is correct, and is worth knowing when a hover example looks empty.
- **Guards are left alone.** `:not(:disabled)` is copied verbatim; only the state pseudo-class is rewritten.

This is the same mechanism `component-state-matrix` uses, for the same reason. The difference is scope: the matrix renders the whole cross-product as a test, the docs render one instance per state as an illustration.

---

## 8. Parsing the TS/TSX

Three things are wanted, in descending order of value: the JSDoc, the defaults, the types.

**Props** come from `export interface XProps` or `type XProps = {`, matched to the closing brace by counting depth (strings skipped), then read member by member: `name`, optional flag, type, and the JSDoc block immediately above it.

**Defaults** come from the destructuring in the signature — `function Button({ variant = "default", size = "default" })` — not from a `defaultProps` object, which is deprecated in React and increasingly absent. This is the column that hand-written docs get wrong most often, because a default changes in a one-line diff that nobody thinks of as a documentation change.

**The component's own JSDoc** is the block immediately above the function. One trap, and it is nastier than it looks:

```python
re.search(r"/\*\*(.*?)\*/\s*(?:export\s+)?function\s+Button\b", text, re.S)   # WRONG
```

A lazy `.*?` still lets the match *start* at an earlier comment and swallow everything between — so the one-line component summary comes back as the entire props interface, comment markers and all. The fix is to forbid crossing a comment terminator:

```python
re.search(r"/\*\*((?:(?!\*/).)*)\*/\s*(?:export\s+)?function\s+Button\b", text, re.S)
```

**The rendered element** is read from the first tag in the `return`, which is what makes the keyboard section possible: a `<button>` carries Enter/Space activation and focusability as a fact of the platform, and that much can be stated without a human. It is also what settles whether a component is interactive, which decides whether the seven-state rule applies to it. A card is a surface; a button is a control; the distinction comes from the element and from whether any interaction rule exists at all.

---

## 9. Detecting what is missing

Absence is the whole game. A linter reads what is written; the interesting failures in a design system are things nobody wrote.

| Finding | How it is found | Why it is not visible otherwise |
|---|---|---|
| `missing-state` | the seven, minus what the selectors implement, for interactive components only | An unwritten state produces no rule, so there is no line for a linter to object to. It renders as `default` and looks fine. |
| `unconsumed-socket` | a socket no declaration reads and no selector re-points | Valid CSS. Silently does nothing, forever, while looking like API. |
| `orphan-token` | declared, and in nobody's `referenced_by` | A token nothing reads has no effect and no error. |
| `tier1-leak` | a component value reading a primitive that has a role | Same rule as `audit_design.py` L6, and the two agree by construction — same prefix list, same exception list. |
| `no-theme-coverage` | every socket resolves identically in light and dark | The component looks right in the theme you are in. |
| `undocumented-component` | in the source, absent from `--prose` | Nothing anywhere says a page is missing. |
| `orphan-doc` | in `--prose`, absent from the source | The worst of the set: a page telling people to use something that is gone. |

Two calibrations that keep the list credible:

**Zero is not always a bug.** An unreferenced Tier-1 ramp step is a spare, and gets `info`. An unreferenced Tier-2 role is a decision nobody took, and gets `warning`. Severity that does not discriminate is severity nobody reads.

**Null-outs are not leaks.** `--space-0`, `--radius-none` and `--shadow-none` are exempt from `tier1-leak`: zero is zero, and `--sections-gap: var(--space-0)` asserts no value at all. Without that exemption the studio's own `layout.css` produces five false findings, and five false findings is how a team learns to ignore a report.

---

## 10. Determinism

`system.json` is the drift baseline, so it must be byte-stable across runs on unchanged input. Three rules:

1. **No timestamps.** A generated-at field makes every CI run report drift, and the gate is switched off within a week.
2. **Sorted everything.** Tokens by name, components by name, sockets by name, gaps by severity then kind then subject.
3. **Relative paths.** Everything is relative to `--root`, so the file does not encode one machine's checkout directory.

The environment-dependent facts — which colour implementation was bound, the rem basis — go in a `meta` key that the drift diff ignores. They are worth printing and are not worth failing a build over.

---

## The three sentences to remember

1. **The five-part component shape makes the component self-describing** — `.button` declaring `--button-*` identifies itself, and the socket block is the API table.
2. **Say what you cannot resolve, and why** — `64px … 144px` and "depends on `ch`" are better documentation than any single number a static tool could invent.
3. **Absence is the finding** — a state nobody wrote, a socket nobody reads and a role nobody references are all perfectly valid CSS, and all three are only visible to a tool that looks for what is not there.

Related: `references/documentation-model.md` (what to do with all of this), `references/drift-detection.md` (keeping it true), `references/token-contract.md` (the vocabulary being parsed).
