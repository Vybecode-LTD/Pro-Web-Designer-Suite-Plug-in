# Spacing System

The most important file in this skill. Spacing is where interfaces silently fall apart, and it is the single thing that most reliably separates work that looks professional from work that looks close.

Read this before you write a single layout rule.

## Contents

1. [Why spacing goes wrong](#1-why-spacing-goes-wrong)
2. [The closed scale](#2-the-closed-scale)
3. [Law 2 — parents own the gaps](#3-law-2--parents-own-the-gaps)
4. [The proximity ladder — picking a gap by meaning](#4-the-proximity-ladder--picking-a-gap-by-meaning)
5. [The three kinds of space](#5-the-three-kinds-of-space)
6. [The spacing decision procedure](#6-the-spacing-decision-procedure)
7. [Optical spacing — where the math lies](#7-optical-spacing--where-the-math-lies)
8. [Nested radius and the corner rule](#8-nested-radius-and-the-corner-rule)
9. [Vertical rhythm and heading asymmetry](#9-vertical-rhythm-and-heading-asymmetry)
10. [Page rhythm — section, subsection, block](#10-page-rhythm--section-subsection-block)
11. [Density as a dial](#11-density-as-a-dial)
12. [Responsive spacing](#12-responsive-spacing)
13. [Debugging a layout that "feels off"](#13-debugging-a-layout-that-feels-off)
14. [Anti-patterns](#14-anti-patterns)

---

## 1. Why spacing goes wrong

Spacing chaos is not a taste problem and it is not a discipline problem. It is a **systems** problem with four specific causes. Every messy stylesheet you have ever opened has at least three of them.

### Cause 1 — two owners for one gap

A card sets `margin-bottom: 16px`. Its parent grid sets `gap: 24px`. The real gap is 24px in a grid, 40px in a block container, and somewhere between in a flex column depending on margin collapsing. Nobody can predict it by reading either file. When a designer says "these cards are too far apart," a developer opens the parent, changes the gap, and fixes half the instances.

This is the big one. It accounts for most of the "why is this 8px lower than that" bugs you have ever chased.

### Cause 2 — an unbounded value space

If `margin-top` may be any number, then the number chosen is whatever looked right in the browser at 3pm on a 27-inch display. Two developers solving the same problem on the same day will land on 14px and 16px. Neither is wrong. Together they are wrong, because the interface now has two values doing one job and no way to tell which is canonical.

### Cause 3 — values chosen by eye, one at a time

Eyeballing is fine for one gap and catastrophic across four hundred. The eye is excellent at *comparison* and poor at *absolute recall*. You can tell instantly that two adjacent gaps differ; you cannot remember what you used on a different page last Tuesday.

### Cause 4 — space that encodes nothing

`margin-top: 24px` says nothing about *why*. There is no rule to check it against, so there is no such thing as it being wrong, so it never gets fixed. The gap between a label and its input and the gap between two unrelated sections both being "24px" is invisible in code and glaring on screen.

### The four fixes, one to one

| Cause | Fix | Law |
|---|---|---|
| Two owners for one gap | Exactly one element owns any given gap: the parent | Law 2 |
| Unbounded value space | A closed scale — the in-between values do not exist | Law 3 |
| Chosen by eye, one at a time | Chosen by **relationship**, from a semantic ladder | Law 6 |
| Encodes nothing | Role tokens name the relationship, so the value is checkable | Laws 1, 9 |

Every section below is one of these four fixes in detail. If you internalize nothing else, internalize that spacing is *decided by rule, not by eye*, and that the rule is about **meaning**, not pixels.

---

## 2. The closed scale

The scale in `tokens.css` has 18 steps. There is no step between them. That is not a limitation; it is the entire mechanism.

```
0  1px  2  4  8  12  16  20  24  32  40  48  64  80  96  128  160  192
```

**Why 4px as the base.** 4 divides evenly into every common icon size, line-height, and control height, and it is fine enough that you never need a half-step for real layout. 8px grids are popular and too coarse — the moment you need 12px padding on a chip, an 8px grid forces you to 8 (cramped) or 16 (bloated), and the developer writes `padding: 12px` anyway and the system is dead.

**Why the steps get coarser as they grow.** At small sizes the eye reads *difference*: 4px vs 8px is obviously double. At large sizes the eye reads *ratio*: 80px vs 84px is indistinguishable, so having both is pure noise. The scale is linear through 24 and roughly geometric above it because that is how perception works, not because it looks tidy in a table.

**Why there is no `--space-7`.** Because the day you add one is the day the scale stops being a constraint and becomes a menu. Constraints are what make a system; a menu is just a list of values with extra steps.

### When a gap "needs" a value that isn't on the scale

It doesn't. One of these is true instead:

1. **You are correcting for something optical.** Fix the optical cause (see §7), not the gap. A button that looks 2px too low usually has a line-height or icon-baseline problem, not a padding problem.
2. **You are compensating for a wrong neighbouring value.** A 28px gap that "looks right" next to a 20px gap that should have been 24px. Fix the 20.
3. **The element is the wrong size.** If a 14px gap is needed to make two things line up, something above them is off-grid.
4. **It is genuinely not a spacing value** — a 22px avatar, a 3px progress bar. Those are sizes, not spaces, and they live in their own tokens.

### The legitimate exceptions

Only these, and each is a *size* or a *sub-pixel optical correction*, not a layout gap:

- `1px` hairlines and borders (`--space-px`, `--stroke-*`)
- `2px` optical gaps between an icon and its label (`--space-0-5`)
- Negative values used to cancel a known token, always written as `calc(var(--token) * -1)` so the relationship survives a token change
- `em`-relative values inside typography (superscript offsets, icon sizing that must track font-size)

Anything else off-scale is a bug and `scripts/audit_design.py` will say so.

---

## 3. Law 2 — parents own the gaps

> **A child never sets its own outer margin. The space between siblings is set by their parent.**

This is the highest-leverage rule in this document. Everything about spacing gets easier once it holds.

### Why it works

A component cannot know its context. A `<Card>` might sit in a grid, a sidebar, a modal, or alone on a page. If the card carries `margin-bottom`, it is asserting a fact about a relationship it cannot see. The parent *can* see it — the parent is literally the element that knows what is next to what.

There is also a mechanical payoff: `gap` does not collapse, does not appear before the first child or after the last, does not need `:last-child` resets, and does not fight `flex-direction` changes. Margin does all four.

### What it looks like

```css
@layer components {
  /* The card owns its INSIDE. It owns no space outside itself. */
  .card {
    --card-inset: var(--pad-card);        /* Tier 3, sourced from Tier 2 */
    padding: var(--card-inset);
    border-radius: var(--radius-lg);
    background: var(--bg-surface);
    box-shadow: var(--elevation-card);
  }
}

@layer layout {
  /* The parent owns the space BETWEEN cards. One declaration, one owner. */
  .card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
    gap: var(--gap-grouped);
  }
}
```

Drop `.card` into a different parent and it spaces correctly with zero changes. That is the test.

### The owl selector, and why it does not break the law

`gap` is unavailable in exactly one situation worth caring about: a container of flowing prose, where `display: flex` would turn bare text nodes into anonymous flex items and shred the content. There, use the owl:

```css
@layer layout {
  .prose > * + * {
    margin-block-start: var(--space-block);
  }
}
```

This still obeys Law 2. **Ownership is about which rule decides, not which box carries the pixels.** The rule lives in the parent's selector, in the parent's file, and changing it changes every gap in that container at once. A child setting `margin-block-start` on itself is a different thing entirely — it is a fact asserted from inside, invisible from the parent.

The distinguishing test: *can you change every gap in this container by editing one declaration?* If yes, the parent owns it.

### The three legitimate uses of margin

1. **`margin: auto` for alignment** — `margin-inline: auto` to center, `margin-inline-start: auto` to push an item to the end of a flex row. This is positioning, not spacing.
2. **The owl selector, written in the parent's rule**, as above.
3. **The flow containers, `.flow` and `.prose`** — explicitly owned containers for CMS or markdown content where you do not control the child elements. They share one rhythm, written once in layout.css (§9). Do not add a third; a third context that needs spacing is a layout, and gets a `gap`.

Everything else is a violation and the auditor flags it.

### Migrating an existing codebase

When you inherit a stylesheet full of child margins, do not fix them one at a time. Do this:

1. Add `gap` to the parent with the correct token.
2. Delete *all* outer margins from the children in that container in the same commit. Partial migration is worse than either state, because now the gap is `gap + margin` and nobody can tell which to edit.
3. Run the auditor scoped to that directory.
4. Repeat per container, one commit each.

---

## 4. The proximity ladder — picking a gap by meaning

This is the fix for "chosen by eye." You do not decide how many pixels two things should be apart. You decide **how strongly they belong together**, and the ladder gives you the pixels.

| Token | Value @ density 1 | Relationship | Examples |
|---|---|---|---|
| `--gap-fused` | 4px | Two halves of one thing | Icon + its label, currency symbol + amount, avatar + name in a single chip |
| `--gap-tight` | 8px | One thing and its annotation | Label + input, heading + its kicker, value + its unit, button + button in a paired group |
| `--gap-related` | 12px | Items in one list | Nav links, tags, table cells, list items, form rows in the same fieldset |
| `--gap-grouped` | 16px | Sibling blocks in one group | Cards in a grid, form fields, list of settings rows |
| `--gap-separate` | 24px | Distinct groups in one region | Fieldsets, card cluster vs its footer, sidebar sections |
| `--gap-distinct` | 40px | Unrelated blocks | A section's heading block vs its content grid, toolbar vs canvas |

This is Gestalt proximity, encoded. Human perception groups by distance before it groups by anything else — before colour, before alignment, before borders. If a label is 16px from its input and 12px from the input above it, the user's eye binds it to the wrong field, and no amount of styling fixes that.

### The one rule that catches most errors

> **Space between groups must be visibly larger than space within groups — at least one rung up the ladder, ideally 2×.**

Adjacent rungs on the ladder are 1.33–1.66× apart (related to grouped, 12 to 16px, is the tightest), which is the minimum that reads as intentional. If you need a boundary to be unmistakable, skip a rung.

Look at the ladder as a picture of the failure it prevents:

```
WRONG — everything 16px. The eye cannot find the groups.
  Label
  Input
  Label
  Input

RIGHT — 8px within, 24px between. The groups are obvious before you read a word.
  Label
  Input

  Label
  Input
```

### Choosing between two adjacent rungs

When you genuinely cannot decide between `--gap-related` and `--gap-grouped`, the tiebreaker is: **what happens if a user scans without reading?** Pick the rung that makes the grouping correct for someone who never reads the labels. Denser interfaces with a strong scanning pattern (tables, settings lists) take the tighter rung; marketing and editorial take the looser one.

Never split the difference. Splitting the difference is how a seventh step gets added to the scale.

---

## 5. The three kinds of space

Confusing these is the second most common structural spacing error. Every space in an interface is exactly one of three kinds, and they are owned by different elements and use different tokens.

| Kind | What it is | Owned by | CSS | Tokens |
|---|---|---|---|---|
| **Inset** | Space inside a container, between its edge and its content | The container | `padding` | `--pad-card`, `--pad-inline-md`, `--pad-block-sm`, `--pad-well` |
| **Stack** | Vertical space between siblings | The parent | `gap` / `row-gap` | The proximity ladder, `--space-block` |
| **Inline** | Horizontal space between siblings | The parent | `gap` / `column-gap` | The proximity ladder |

### Inset rules

- Inset is uniform unless there is a reason it is not. `padding: var(--pad-card)` beats four separate values.
- When it is not uniform, the reason is almost always **optical**: a container holding text with descenders, a control with a trailing chevron, a card with a full-bleed image at the top. Those get `padding-block` and `padding-inline` set separately, with a comment naming the reason.
- **Inset scales with the container's weight, not its size.** A modal is not a big card; it is a heavier surface, so it takes `--pad-card-lg`. A 600px-wide card and a 300px-wide card in the same grid take the same inset — varying it makes the grid look broken.
- Inset and the scale interact with radius. See §8.

### Stack rules

- A stack's gap is one value for the whole stack. If two children need different spacing from their neighbours, you have two stacks, not one stack with exceptions.

```css
/* WRONG — exception inside a stack. example: wrong */
.settings { display: grid; gap: var(--gap-grouped); }
.settings > .danger-zone { margin-block-start: var(--space-12); }
```

```css
/* RIGHT — two stacks, the outer one expressing the real relationship */
.settings-page { display: grid; gap: var(--gap-distinct); }
.settings      { display: grid; gap: var(--gap-grouped); }
```

The second version is longer and it is the one that survives contact with a second developer, because the relationship is in the structure where it can be seen.

### Inline rules

- Horizontal gaps in a row of mixed-size items read **tighter** than the same vertical gap. Text sitting side by side has its own side bearings; stacked text does not. If a row and a column must read as equally spaced, the row usually needs one rung *up*.
- Wrapping rows need `gap` on both axes, and the row gap should be equal to or slightly tighter than the column gap, never looser — a wrapped item reads as a continuation, not a new group.

---

## 6. The spacing decision procedure

Run this every time you are about to type a spacing value. It takes five seconds and it removes eyeballing from the process entirely.

```
1. What KIND of space is this?
   inside a container ........................ INSET  -> --pad-*
   between siblings .......................... STACK or INLINE -> ladder
   between page regions ...................... PAGE RHYTHM -> §10

2. If inset: what is this container's weight?
   chip / tag ................................ --pad-inline-xs + --pad-block-xs
   control (button, input) ................... --pad-inline-md + --pad-block-md
   card / panel .............................. --pad-card
   modal / hero surface ...................... --pad-card-lg
   well / callout / code block ............... --pad-well

3. If between siblings: what is the RELATIONSHIP?
   two halves of one thing ................... --gap-fused
   a thing and its annotation ................ --gap-tight
   items in one list ......................... --gap-related
   sibling blocks in one group ............... --gap-grouped
   distinct groups in one region ............. --gap-separate
   unrelated blocks .......................... --gap-distinct

4. Who OWNS it?
   Always the parent. If you are typing `margin` on a child, stop and
   go up one level. (Exceptions: §3.)

5. Does the value you landed on differ from the gap one level up?
   It must, by at least one rung. If it does not, one of the two is wrong.

6. Run the auditor before you call it done.
```

**Worked example — a form field.**

Label, input, help text, and a stack of fields inside a fieldset, inside a form.

- Label → input: a thing and its annotation, but *inverted* — the label annotates the input. `--gap-tight` (8px).
- Input → help text: also annotation. `--gap-tight` (8px). Same rung is correct here: they bind to the same input.
- Field → field: sibling blocks in one group. `--gap-grouped` (16px). Check: 16 ÷ 8 = 2×. The field boundary is unmistakable. Good.
- Fieldset → fieldset: distinct groups. `--gap-separate` (24px). Check: 24 ÷ 16 = 1.5×. Adequate, and if the fieldsets have legends, the legend does additional grouping work. If they do not, skip a rung to `--gap-distinct`.
- Form → submit row: unrelated block. `--gap-distinct` (40px), because the submit button must not read as another field.

```css
@layer components {
  .field      { display: grid; gap: var(--gap-tight); }
  .field-list { display: grid; gap: var(--gap-grouped); }
  .fieldset-list { display: grid; gap: var(--gap-separate); }
  .form       { display: grid; gap: var(--gap-distinct); }
}
```

Four declarations. Every gap in the form is now predictable, adjustable in one place, and correct by construction. Notice that no element in this form sets a margin.

---

## 7. Optical spacing — where the math lies

Mathematically equal spacing is not perceptually equal spacing. Knowing exactly where the math lies is the difference between "clean" and "designed."

The rule underneath all of these: **the eye measures the visual mass of a shape, not its bounding box.** Any time a bounding box contains a lot of empty area, the math will be wrong.

### 1. Text has invisible padding

A line of text occupies its line-height box, but the glyphs sit in a smaller area inside it — roughly the cap-height to baseline band. At `--leading-normal` (1.6) on 16px text, there is about 5px of empty space above and below the visible letters.

Consequence: a card with `padding: 24px` whose only content is text looks like it has ~29px of vertical padding and 24px of horizontal padding. It reads top-heavy and wide.

Fix: for text-only containers, reduce block padding by roughly half the leading overhang, or use `text-box-trim` / `text-box-edge` where support allows.

```css
@layer components {
  .quote {
    /* Leading adds ~0.3em of empty band top and bottom. Trim it so the
       optical inset matches the horizontal one. */
    /* stylelint-disable-next-line declaration-property-value-allowed-list -- design-audit-ignore-next-line: L1 -- optical: the leading band, until text-box-trim below takes over */
    padding-block: calc(var(--pad-card) - 0.3em);
    padding-inline: var(--pad-card);
  }

  @supports (text-box-edge: cap alphabetic) {
    .quote {
      text-box-edge: cap alphabetic;
      text-box-trim: trim-both;
      padding-block: var(--pad-card);   /* now the math is honest again */
    }
  }
}
```

### 2. Round shapes need more space than square ones

A circle inscribed in a 40px box touches its edges at exactly one point per side; a square fills them. Set a circular avatar and a square thumbnail the same distance from a text block and the avatar looks further away.

Fix: circles and pills take roughly 10–15% less surrounding gap than rectangles of the same bounding size. In practice: drop one rung, or add the correction as a Tier-3 property with a comment.

### 3. Icons sit in oversized boxes

A 24px icon usually contains a 20px glyph with 2px of built-in padding. Gap it at `--gap-fused` (4px) from its label and the real optical gap is 6px, which is right. Gap it at `--gap-tight` (8px) and it reads as 10px and drifts apart.

**Rule: icon-to-label is always `--gap-fused`.** They are one thing.

### 4. Optical centering of a shape with direction

A play triangle centered mathematically in a circle looks left-heavy, because its visual mass sits toward the flat edge. Same for a chevron in a button, a caret in a select, or any glyph with strong directional weight.

Fix: nudge by 1–2px toward the point. This is one of the few legitimate uses of a raw pixel value — write it as `--nudge` with a comment stating it is an optical correction:

```css
.play-button__glyph {
  /* Optical: the triangle's mass sits left of its bounding-box center. */
  --optical-nudge: 1px;
  translate: var(--optical-nudge) 0;
}
```

### 5. Buttons with a trailing icon are not symmetric

Text has side bearings; an icon does not. Equal padding on both sides makes the icon side look tighter.

Fix: reduce the icon-side padding by one rung, or better, let the gap do the work and use `padding-inline: var(--pad-inline-md) var(--pad-inline-sm)` on icon-trailing buttons. Comment it.

### 6. Large type needs less leading and more space around it

Covered fully in `references/typography.md`, but the spacing consequence: a 44px heading with `--leading-tight` still carries a large empty band. The space *above* a heading must be measured from the cap-height, not the line box, which in practice means large headings need a rung more space above them than the ladder suggests.

### The optical-correction discipline

Every optical correction is a raw value, which means every one is a potential drift vector. So:

- It lives in a Tier-3 custom property with a name containing `optical` or `nudge`.
- It carries a comment stating the perceptual reason.
- It is never larger than 2px. A correction bigger than 2px is not optical; it is a layout bug you are papering over.
- The auditor allowlists properties matching `--*-nudge` and `--optical-*` and flags raw nudges that are not declared that way.

---

## 8. Nested radius and the corner rule

When a rounded element sits inside another rounded element, their radii must be related or the corners look peeled.

> **inner radius = outer radius − the padding between them**

A card with `--radius-xl` (16px) and `--pad-card` (24px) holding an image: the image's radius should be 16 − 24 = negative, i.e. `0`... which is wrong-looking too. The real rule has a floor:

```css
.card {
  --card-radius: var(--radius-xl);
  --card-inset: var(--pad-card);
  border-radius: var(--card-radius);
  padding: var(--card-inset);
}

.card__media {
  /* Concentric corners. max() keeps it sane when the inset exceeds the
     radius — at that point the child is far enough from the corner that
     a small independent radius reads fine. Geometry over tokens goes in
     a socket, as the starter's layout primitives do. */
  --card-media-radius: max(var(--radius-sm), calc(var(--card-radius) - var(--card-inset)));
  border-radius: var(--card-media-radius);
}
```

The visible failure mode when you get this wrong: the gap between the two curves varies around the corner instead of staying constant, and the whole card reads as slightly amateur without anyone being able to say why.

**Full-bleed children are the common case.** An image that touches the card's edge (inset 0) takes the card's *exact* radius on the touching corners and `0` on the others:

```css
.card__media--bleed {
  border-start-start-radius: var(--card-radius);
  border-start-end-radius: var(--card-radius);
  border-end-start-radius: 0;
  border-end-end-radius: 0;
  margin: calc(var(--card-inset) * -1);      /* cancel the inset, from the parent's own rule */
  margin-block-end: 0;
}
```

Note the negative margin is written as `calc(token * -1)`, so changing `--pad-card` keeps it correct. Raw `-24px` here is exactly the kind of literal that rots.

---

## 9. Vertical rhythm and heading asymmetry

> **A heading belongs to the content that follows it, so the space above a heading is always larger than the space below it.**

This is the single most-violated typographic spacing rule on the web, and fixing it makes long-form pages instantly read better. Default browser styles get it wrong (equal margins), and most resets do not fix it.

Ratio: at least **2:1**, above to below, at every width. Larger headings take the larger ratio, because a bigger heading is a stronger boundary.

<!-- snippet: layout.css#flow -->
```css
:is(.flow, .prose) {
  --flow-gap: var(--space-block);
}
:is(.flow, .prose) > * + * { margin-block-start: var(--flow-gap); }

/* A heading belongs to the thing it introduces: far from what came before,
   scaled to its rank, and close to what follows. Proximity does the work a
   horizontal rule would otherwise do. Above to below is at least 2:1 at
   every width: h2 40→88 : 12, h3 40 : 12, h4 24 : 12. */
:is(.flow, .prose) > * + h2 { margin-block-start: var(--space-subsection); }
:is(.flow, .prose) > * + h3 { margin-block-start: var(--gap-distinct); }
:is(.flow, .prose) > * + :is(h4, h5, h6) { margin-block-start: var(--gap-separate); }

/* Written after the heading rules, at equal specificity, so a heading that
   follows a heading takes this tight gap too: two stacked headings are a
   title and its subtitle, not two sections. */
:is(.flow, .prose) > :is(h1, h2, h3, h4, h5, h6) + * {
  margin-block-start: var(--gap-related);
}

/* An <hr> means "the subject changes": subsection weight on both sides. */
:is(.flow, .prose) > * + hr,
:is(.flow, .prose) > hr + * { margin-block-start: var(--space-subsection); }
```

Read the result: after an `h3`, the next element sits 12px away (`--gap-related`) — bound tightly to the heading. Before an `h3`, there are 40px (`--gap-distinct`). The heading visually leads its section instead of floating between two.

**In component contexts (not prose), the same asymmetry is expressed structurally**, which is cleaner:

```css
.section {
  display: grid;
  gap: var(--gap-distinct);        /* between the header block and the body */
}
.section__header {
  display: grid;
  gap: var(--gap-tight);           /* heading to its subtitle: tight */
}
```

The heading and its subtitle are one group, tightly spaced. That group is far from the body. Same perceptual result, no margins, Law 2 intact.

---

## 10. Page rhythm — section, subsection, block

Page-level space is fluid, because a fixed 96px section gap is a scroll tax on a 390px phone and looks unfinished on a 27-inch display.

| Token | Range | Use |
|---|---|---|
| `--space-section` | 64 → 144px | Between top-level page sections |
| `--space-subsection` | 40 → 88px | Between major parts within one section |
| `--space-block` | 24 → 48px | Between prose blocks, between a heading group and its content |
| `--gutter-page` | 16 → 24px | Left and right page margins |

### The section-boundary rule

Who owns the space between two sections? Law 2 says the parent — but a section with a painted background cannot be separated by a `gap`, because a gap cannot be painted.

So there are exactly two page modes, and a page picks one:

**Mode A — unbanded.** No section paints a background. The page container owns all boundaries:

```css
.sections { display: grid; gap: var(--space-section); }
```

**Mode B — banded.** Sections paint backgrounds. Each section owns its own vertical padding, and the boundary between two sections is the sum of two paddings:

```css
.sections--banded > .section { padding-block: var(--space-subsection); }
```

Two sections therefore meet with `2 × --space-subsection` (80 → 176px), slightly more than `--space-section`. That is correct, not a rounding error: a colour change is a stronger boundary, and it needs more air on each side to avoid looking cramped against the band edge.

**Never mix the modes on one page.** A banded section next to an unbanded one produces a boundary of `--space-section + --space-subsection`, which is visibly wrong and impossible to reason about. If a design needs one accent band in an otherwise unbanded page, give that band `padding-block: var(--space-subsection)` and set its *neighbours'* gap contribution to zero in the parent — do not let the two systems add.

### Gutters and the content column

<!-- snippet: layout.css#center -->
```css
.center {
  --center-max: var(--width-content);
  --center-gutter: var(--gutter-page);
  /* Derived: the column plus a gutter on each side. */
  --center-box: calc(var(--center-max) + var(--center-gutter) * 2);
  box-sizing: border-box;
  max-inline-size: var(--center-box);
  margin-inline: auto;
  padding-inline: var(--center-gutter);
}

.center--prose  { --center-max: var(--measure-prose); }
.center--narrow { --center-max: var(--measure-narrow); }
.center--form   { --center-max: var(--width-form); }
.center--wide   { --center-max: var(--width-wide); }
.center--flush  { --center-gutter: var(--space-0); }
```

The gutters are added back to the cap, so `--width-content` means the content column and not the column minus two gutters. The gutter is a socket, so `.center--flush` drops it by re-pointing one variable. (`inline-size: min(100% - 2 × gutter, max)` draws the same column; padding is what lets a modifier remove the gutter.) `margin-inline: auto` is the alignment exception from §3, not a spacing margin.

---

## 11. Density as a dial

Compactness is a property of a *context*, not of a component. An admin table and a marketing page can use the same card component at different densities, and that must not require a second set of styles.

Because every Tier-2 spacing role is `calc(primitive * var(--density))`, one attribute recomposes an entire subtree:

```html
<main data-density="comfortable">
  <section class="dashboard" data-density="compact"> … </section>
</main>
```

```css
[data-density="compact"]     { --density: 0.875; }  /* 16px -> 14px */
[data-density="comfortable"] { --density: 1; }
[data-density="spacious"]    { --density: 1.125; }  /* 16px -> 18px */
```

### What density must not do

- **It must not change page rhythm.** `--space-section` and friends are fluid on viewport, not on density — a compact dashboard still needs the same air between its regions or it becomes a wall.
- **It must not push a tap target below `--tap-min`.** Control heights are floored: `min-block-size: var(--tap-min)`. Check this at `compact` on a touch device.
- **It must not go below 0.875 or above 1.125.** Outside that band the multiplied values start landing far from the scale and the interface stops looking like the same product. If you need a denser view than 0.875 gives, you need a different component (a table row, not a card), not a smaller dial.

### Verifying density

Every component's review includes: render it at all three densities and confirm nothing overlaps, nothing clips, no target drops below 44px, and the proximity relationships still read correctly. Density is the cheapest way to discover that a component had a hardcoded value in it.

---

## 12. Responsive spacing

Three rules, in priority order.

**1. Prefer fluid over breakpoints.** A `clamp()` value adapts continuously and needs no maintenance. Every breakpoint you add is a discontinuity someone will eventually have to debug. Use the `--space-fluid-*` tokens for anything page-scale.

**2. Prefer intrinsic over extrinsic.** `grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr))` adapts to available space with no query at all. A container query adapts to the *component's* space, which is almost always what you actually meant when you wrote a media query. See `references/layout-composition.md`.

**3. Change spacing at a breakpoint only when the relationship itself changes.** If a sidebar becomes a stacked block, the gap between it and the content genuinely means something different, and it should change. If the layout is the same and only the screen is bigger, use a fluid token.

### The mobile spacing correction

Component insets should shrink on small screens; **page rhythm should shrink more**. The reason: on a phone, horizontal space is scarce and vertical space is cheap to scroll but expensive in attention. A 96px section gap costs a third of the viewport.

The fluid tokens already do this. What they do not do is fix component insets, so for card-heavy layouts:

```css
.card {
  --card-inset: var(--pad-card);
}

@container (max-width: 30rem) {
  .card { --card-inset: var(--pad-well); }   /* one rung down, via the Tier-3 socket */
}
```

Note this changes a Tier-3 property, not the rule. The component's declarations are untouched.

---

## 13. Debugging a layout that "feels off"

A procedure, in order. Stop at the first thing you find; it is usually the only thing.

**1. Are two gaps at the same hierarchy level different?**

```bash
# List every spacing declaration in a component tree and look for outliers
rg --no-heading -o '(gap|padding|margin)[^;:]*:\s*[^;]+;' src/components | sort | uniq -c | sort -rn
```

Anything appearing once is suspicious. Anything using a raw value is a bug.

**2. Is anything off-scale?** Run `python -m scripts.audit_design src/`. This catches raw values, Tier-1 leakage into components, and child margins in one pass.

**3. Is a gap owned twice?** In DevTools, select the child and check whether it has a margin while its parent has a gap. This is the single most common cause of "this one card is lower than the others."

**4. Does the proximity match the meaning?** Walk the component and say out loud what each gap means. "This is 16px because the label annotates the input" — if you cannot finish the sentence, the value was eyeballed.

**5. Is it optical?** If everything measures correctly and it still looks wrong, it is §7. Most often: text leading overhang in a padded box, or an icon gapped as if it were text.

**6. Is it alignment, not spacing?** Two elements 24px apart that do not share a left edge read as badly spaced even when they are not. Check that edges land on a shared vertical line before touching any gap.

**7. Is the measure wrong?** A text block wider than ~75ch reads as badly spaced because the eye loses the line return. The fix is `--measure-prose`, not a gap.

---

## 14. Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| `margin-bottom` on a component's root | Law 2. The component asserts a relationship it cannot see. Breaks the moment it moves. |
| `:last-child { margin-bottom: 0 }` | A symptom of the above. You are patching a design flaw with a selector. Use `gap`. |
| `margin-top: 13px` | Off-scale. Whatever it is fixing, it is not fixing it at the cause. |
| `space-y-4` (Tailwind) | Implemented as child margins with a `:not(:last-child)` — same ownership problem, hidden behind a nice name. Use `gap-*`. |
| `padding: 24px` in a component | Literal. Use `var(--pad-card)`. When density changes, the literal does not. |
| `var(--space-6)` in a component | Tier-1 leakage (Law 6). Correct value, wrong tier. It works until the day "more air in cards" means grepping for `--space-6` across 200 files. |
| Negative margins as a layout tool | Fragile, invisible in DevTools' box model, and breaks at every breakpoint. The only legal negative margin cancels a known token via `calc(token * -1)`. |
| Fixed heights to force spacing | The content will exceed it. It always exceeds it. Use padding and let the box grow. |
| One-off media query inside a component | Component breakpoints belong to the container, not the viewport. Use `@container`. |
| Spacing "fixed" with `transform: translateY()` | Moves the paint, not the layout. Everything around it is still wrong, and now it overlaps. |
| Different gaps for the same relationship on two pages | The relationship has one meaning, so it has one token. If they genuinely differ, one of the two pages has the relationship wrong. |
| Adding a scale step to resolve a disagreement | The disagreement is about which relationship it is. Resolve that instead. |

---

## The three sentences to remember

1. **Parents own the gaps** — a child that sets its own outer margin is asserting a fact it cannot know.
2. **Pick by relationship, not by pixels** — the ladder converts meaning into a value, which is why the value is checkable.
3. **The scale is closed** — the in-between values do not exist, and everything downstream depends on that staying true.

Related: `references/style-architecture.md` (where the rules live), `references/layout-composition.md` (the primitives that implement them), `references/typography.md` (leading, measure, and the type side of rhythm), `scripts/audit_design.py` (the enforcement).
