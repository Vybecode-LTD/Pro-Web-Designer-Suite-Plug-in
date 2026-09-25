# Screen Patterns

The screen set a content model implies, and how each one is built from the suite's layout primitives.

`field-mapping.md` decides what each column becomes. This file decides what the columns get assembled into: which screens exist, how each is composed, what it does at 320px, and — §10 — the states that separate a product from a demo.

Primitives are from `web-design-studio/references/layout-composition.md` and are used by name: `.stack`, `.cluster`, `.row`, `.split`, `.with-sidebar`, `.switcher`, `.grid`, `.center`, `.cover`, `.frame`, `.reel`. Spacing is the proximity ladder, picked by relationship and never by pixels.

## Contents

1. [The screen set](#1-the-screen-set)
2. [Index: table vs card grid vs feed](#2-index-table-vs-card-grid-vs-feed)
3. [Index anatomy](#3-index-anatomy)
4. [The wide table on a phone](#4-the-wide-table-on-a-phone)
5. [Detail](#5-detail)
6. [Create and edit](#6-create-and-edit)
7. [Inline edit](#7-inline-edit)
8. [Delete confirmation](#8-delete-confirmation)
9. [Bulk actions](#9-bulk-actions)
10. [Filter and search](#10-filter-and-search)
11. [Dashboard](#11-dashboard)
12. [The states generators skip](#12-the-states-generators-skip)
13. [Form UX](#13-form-ux)

---

## 1. The screen set

One entity implies six screens and two overlays. Not every entity needs all of them — an owned child (`ON DELETE CASCADE`, no title of its own) lives inside its parent's form and needs almost none.

| Screen | Exists when | Primary composition |
|---|---|---|
| **Index** | The entity has more than a handful of rows | `.center` → `.stack--separate` → table or `.grid` |
| **Detail** | The entity has fields the index cannot show | `.center` → `.with-sidebar` |
| **Create** | Users make these | `.center--form` → `.stack--separate` of fieldsets |
| **Edit** | Users change these | Same component as create, different initial values |
| **Delete** | Users remove these | `.imposter` dialog |
| **Filter / search** | Index rows exceed one screen | `.cluster` above the index, or a `.with-sidebar__rail` |
| **Bulk actions** | Users do the same thing to many rows | A selection bar, `.row--between` |
| **Dashboard** | Somebody asked "how is it going" | `.grid` of `.switcher`-ed tiles |

**Create and edit are one component.** They differ in initial values, in whether the primary button says "Create" or "Save", and in whether leaving is destructive. They do not differ in layout, field order or validation, and building them twice guarantees they diverge — the third field gets added to one of them.

---

## 2. Index: table vs card grid vs feed

The decision rule, in order. First match wins.

| Choose | When | Because |
|---|---|---|
| **Card grid** | There is an image column **and** ≤ 5 scannable fields | People recognise these records by looking. A thumbnail in a table cell is a thumbnail nobody can see |
| **Table** | ≥ 5 scannable columns, **or** ≥ 2 numeric columns | Values must line up vertically to be comparable, and vertical alignment is the one thing only a table does |
| **Feed** | A `body` / `content` / `message` column **and** ≤ 3 other fields | The record *is* its text, so show some of it rather than a row that says nothing |
| **Table** | otherwise | The default. A table is never the *wrong* answer, only sometimes the dull one |

Two refinements the rule cannot make:

**`description` is not `body`.** A description accompanies a thing; a body *is* the thing. A feed of descriptions is a table with its columns knocked out. This is why the feed test looks for `body`, `content`, `message`, `post`, `transcript` — the nouns that mean "the record is text" — and not for any long-form column.

**Touch in the field overrides everything.** If people use this on a phone while doing something else, a wide table is the wrong shape whatever the field count, and the answer is a card list with two or three fields per card. No schema signal reveals this, so it is question `<table>.index_layout`.

---

## 3. Index anatomy

```
.center
└── .stack--separate                       page regions
    ├── header  .cluster--between          title ······ primary action
    ├── filters .cluster                   search, facets, active-filter chips
    ├── [selection bar]  .row--between     appears only with a selection
    ├── the list                           table | .grid | .stack--related
    └── pagination  .cluster--between      range, controls
```

| Boundary | Token | Why that rung |
|---|---|---|
| Between page regions | `--gap-separate` | Distinct groups in one region |
| Header title ↔ action | `--gap-grouped`, via `.cluster--between` | They are peers on one line |
| Between filter controls | `--gap-related` | Items in one group |
| A label and its input | `--gap-tight` | A thing and its annotation |
| An icon and its label | `--gap-fused` | Two halves of one thing |
| Table cell inset | `--pad-block-sm` / `--pad-inline-md` | Block tighter than inline: rows read across, and equal padding makes a row look loose and a column look cramped |
| Card grid gap | `--gap-grouped` | Sibling cards |
| Card inset | `--pad-card` | |

**Table specifics that are not optional.**

- `font-variant-numeric: tabular-nums` and `text-align: end` on every numeric column. Proportional digits make a column of prices unalignable, so a user cannot spot the order of magnitude by eye — which is the only reason the column is there.
- The title cell is the link, not the row. A whole-row link is one enormous tab stop whose accessible name is the entire row read aloud.
- `position: sticky` on `thead` with `z-index: var(--z-raised)`. A header that scrolls away turns column 6 into an unlabelled number.
- `aria-sort` on the sorted `th`, and it must be on the `th`, not the button inside it.

**Card grid specifics.**

- `.grid` with `--grid-min` from the derived track floors (`--min-sm` = `--width-content / 4`). Never a fixed column count — seven items then need a special case.
- `.frame` around every image so the grid does not reflow as images load, and so cards agree when the source assets do not.
- `.stack--fill` + `.stack__push-end` to pin card footers to the same line when titles wrap differently. Or subgrid, if you have it.

**Pagination.** Say the range — "Showing 21–40 of 312" — not just the page number. A page number alone cannot answer "am I nearly done", which is the question people actually have. If the count is expensive, "Showing 21–40" with a next control is honest; a fabricated total is not.

---

## 4. The wide table on a phone

The genuinely hard problem, and the one where generated UIs give up. There are three real options and each is right somewhere.

| Option | How | Right when | Cost |
|---|---|---|---|
| **1. Scroll it honestly** | `overflow-x: auto` on a focusable, labelled wrapper; `position: sticky` on the identifying column | Users compare rows, and the column set matters. Dense operational data | Two-axis scrolling is awkward on touch; discovery of the horizontal axis is imperfect |
| **2. Collapse to cards** | Below a threshold, each row becomes a card of label/value pairs | Users act on one record at a time. Most consumer and admin CRUD | Comparison across rows is gone. Vertical length multiplies |
| **3. Priority columns** | Show 2–3 columns; the rest behind a per-row expand | There is a clear priority order and users mostly need the top of it | Someone has to rank the columns, and the ranking is per-screen product knowledge |

**The scaffold ships option 1**, because it is the only one that needs no further decisions, degrades rather than hides, and keeps every value reachable. The wrapper is not just `overflow-x`:

```html
<div class="scroller" tabindex="0" role="region" aria-label="Products, scrollable table">
```

`tabindex="0"` and an accessible name are mandatory, not polish. A scroll container that cannot take focus is unreachable by keyboard, and its off-screen content cannot be read at all (WCAG 2.1.1). `base.css` already supplies the focus indicator that becomes required once the markup carries the attribute.

**The sticky identifying column is what makes option 1 work.** Without it, a row scrolled to its fifth column belongs to nobody, and the user has to scroll back to find out whose price they are looking at.

**Choosing option 2 or 3 is a real design change, not a media query.** Do it as a deliberate second rendering of the same data, decided by a container query on the list's own wrapper (`@container`) rather than a viewport breakpoint — a table in a 288px rail has the same problem as a table on a phone, and a media query gets that case wrong.

---

## 5. Detail

```
.center
└── .with-sidebar
    ├── .with-sidebar__main  .stack--separate
    │   ├── h1 (the title column)
    │   ├── dl of field pairs   .grid, auto-fit minmax(--measure-narrow, 1fr)
    │   ├── related: owned children (inline sub-table)
    │   └── related: independent children (a few rows + a link)
    └── .with-sidebar__rail  .stack--related
        ├── primary action
        ├── destructive action
        └── metadata: created, updated, owner
```

`.with-sidebar` rather than `.split` because the rail should give up on a *content* threshold, not a viewport one. The detail page then works unchanged inside a drawer and inside a 288px column, which `@media` cannot deliver.

**A definition pair is one thing**, so `dt` and `dd` sit at `--gap-fused`. Anything looser and the term stops reading as belonging to the value; the eye starts pairing each value with the term *below* it, which is the same failure as a heading spaced closer to the paragraph above it than the one below.

**The h1 is the title column, and a uuid is not a title.** When nothing in the table looks like one, the scaffold puts the primary key in the heading and marks it `TODO(title)` — visibly, because a generator that quietly puts a key in an `h1` produces screens that look finished and are unusable.

**Actions belong in the rail, not the header.** A destructive action beside a page title is one mis-click from a deleted record, and the rail puts distance between "I am reading this" and "I am changing this" without needing a confirmation for every action.

---

## 6. Create and edit

```
.center--form                               a 28rem column, not the page width
└── form .stack--separate
    ├── error summary (only when invalid)
    ├── fieldset  .stack--grouped           one per group
    │   └── Field × n                       label / control / help / error
    └── actions .cluster--tight             Save · Cancel
```

**`--width-form` (28rem), not the content width.** A 1152px-wide form has inputs a user's eye cannot track from label to field, and the label ends up miles from what it labels. The exception is a form with genuinely parallel sections, which is `.switcher` of two form columns — and which is usually a sign the form should be two steps.

**Field order is not column order.** Columns are ordered by when someone added them. Fields are ordered by how a person fills the thing in: identity first (what is it called), then its content, then its classification, then its relationships, then scheduling, then the machinery. The scaffold groups by control shape as a stand-in for this and says so — the grouping question exists because the stand-in is only ever approximately right.

**Every fieldset has a real `legend`.** A fieldset with no legend is a box; with one, it is a section a screen reader can announce and a user can skip.

---

## 7. Inline edit

Editing a value in place, without leaving the list.

Worth it for: a status change, a toggle, a quantity, a single short text field. Not worth it for: anything with more than one field, anything with cross-field validation, anything with a slow save.

The rules that make it not feel broken:

- **The affordance must exist before hover.** A value that only reveals it is editable when a pointer touches it is invisible on touch and to keyboard users. A persistent, low-contrast edit affordance beats a hover reveal.
- **The edit surface must not resize the row.** If the input is taller than the text it replaces, every row below jumps, and the thing the user was about to click moves. Size the input to the cell's existing line box.
- **Escape reverts, Enter commits, blur commits.** Blur-to-cancel loses work, and users will click away by accident.
- **Optimistic, with a rollback that is visible.** See §12.
- **One editor at a time.** Two open editors in one list is two unsaved states and no way to reason about "save".

---

## 8. Delete confirmation

An `.imposter` dialog inside `.imposter-anchor`, with `--imposter-margin` and `overflow: auto` so the confirm button is reachable on a 667px-tall phone.

**"Are you sure?" is not a confirmation.** It asks the user to re-affirm an intent they already expressed, and gives them no new information on which to change their mind. A confirmation that earns its interruption does three things:

1. **Names the record.** "Delete *Ceramic Mug*?" — not "Delete this item?"
2. **States what else goes.** `ON DELETE CASCADE` is exactly this list, and it is the only thing the user cannot work out for themselves: "This also deletes 14 order lines."
3. **Labels the button with the verb.** "Delete" and "Cancel", never "OK" and "Cancel". A user scanning for the safe exit reads the buttons, not the prose.

**Skip the dialog when undo is possible.** A soft delete with a 10-second undo toast is strictly better than a confirmation: it costs nothing on the happy path and recovers the mistake the dialog was trying to prevent. Reserve the dialog for genuinely irreversible deletes — and for those, consider type-to-confirm rather than a button.

Focus goes to the dialog on open, is trapped inside it, and returns to the trigger on close. A dialog that returns focus to `<body>` puts a keyboard user back at the top of the page.

---

## 9. Bulk actions

```
.row--between   appears when selection > 0, replaces the filter bar's position
├── "3 selected"  +  Select all 312
└── .cluster--tight   actions, destructive last and visually separated
```

- **The selection bar must not shift the page.** Reserve its height, or overlay it. A bar that pushes the table down moves the checkbox the user is about to click.
- **"Select all on this page" and "select all matching the filter" are different, and users will assume the second.** Say which one happened, and offer the other explicitly.
- **A bulk destructive action needs a confirmation naming the count.** "Delete 312 products" is a different sentence from "Delete 3 products" and deserves a different amount of friction.
- **Report partial failure per record.** A bulk action over 312 rows where 4 fail must say *which* 4. "Some items could not be updated" is a dead end.
- **The header checkbox is tri-state.** `indeterminate` is a DOM property, not an attribute — it cannot be set in markup and is the single most commonly missed detail here.

---

## 10. Filter and search

| Filters | Placement |
|---|---|
| 1–3 | `.cluster` above the list |
| 4+ | `.with-sidebar__rail`, or a drawer on narrow screens |
| Faceted with counts | Rail, always — counts need vertical room |

- **Active filters are visible as removable chips.** The commonest support ticket about a list is "my record is missing", and the commonest cause is a filter the user forgot was on.
- **Search is debounced, not submitted.** ~250ms. Below that you fire per keystroke; above it feels broken.
- **The result count updates with the filter**, and it is what tells the user the filter did something.
- **Filter state lives in the URL.** A filtered list a user cannot send to a colleague is a filtered list they will screenshot instead.
- **Filtered-empty is a different screen from empty.** §12.

`ilike` vs `tsvector` changes what the search box can promise — see `supabase-integration.md` §7.

---

## 11. Dashboard

The screen most likely to be decoration. One rule keeps it honest:

> **Every tile answers a question somebody actually asks, and says what to do when the answer is bad.**

```
.center--wide
└── .stack--separate
    ├── .switcher--max-4     headline metrics, equal peers
    ├── .grid--min-md        charts and tables
    └── .stack--related      recent activity
```

`.switcher` for the metric row rather than `.grid`, because metrics are peers: three become three rows at narrow widths, never two-plus-one. An orphaned third metric on its own row reads as an afterthought.

- **A number with no comparison is not information.** "1,284 orders" says nothing; "1,284 orders, +12% on last week" says something.
- **Every tile loads independently**, with its own skeleton. One slow query must not hold the page.
- **Empty tiles say why.** "No orders yet" beats a zero, because a zero looks like a bug.
- **Chart colour comes from the token layer**, read via `getComputedStyle().getPropertyValue('--bg-accent')` or set through a custom property. A hex in chart config is a colour dark mode cannot re-point.

---

## 12. The states generators skip

This section is why a generated UI feels generated. All eight of these are reachable in production, all eight are invisible in development with seeded data, and each one is a different screen — not one screen with different words.

| State | Reached when | Must do | Must not do |
|---|---|---|---|
| **First-run empty** | No records have ever existed | Say what this screen will hold, why it is worth filling in, and offer **one** action | Say "No data". Offer two competing actions |
| **Filtered empty** | A filter or search matched nothing | Name the active filters and offer to clear them | Offer "Create record" — the records exist, this query missed them |
| **Loading** | The first fetch is in flight | A skeleton with the real content's dimensions | A centred spinner. It says nothing about what is coming and lets the page jump when it arrives |
| **Partial / streaming** | Some rows have arrived | Render what you have; show the rest loading in place | Hold everything until all of it is ready |
| **Error** | The request failed | Say what failed in the user's terms and offer a retry | Show the transport error. End without a route forward |
| **Permission denied** | RLS or a policy filtered everything | Say the user lacks access and who to ask | Leak whether any records exist. Render it as "empty" |
| **Stale** | A realtime event or a failed revalidation | Label the data above it and offer a refresh | Silently replace what the user is reading. Blank the list |
| **Optimistic + rollback** | A write is in flight | Show the intended result immediately, marked pending | Roll back silently. The user will not notice their change vanished |

**First-run vs filtered empty is the one that matters most**, because the two ask the user to do opposite things. "Nothing here yet, make the first one" and "your filter matched nothing, clear it" are not variations on a message; they are different screens with different primary actions, and shipping one for both makes the product feel like it is not listening.

**The skeleton must match the real content's dimensions.** If the skeleton and the loaded row are different heights, the page jumps when data lands and whatever the user was about to click moves. That jump is the entire reason to prefer a skeleton over a spinner, so a skeleton that does not match is strictly worse than a spinner — it costs more and delivers nothing. Match the row height, the column count and the line count.

**Permission-denied is a real state under RLS, not a hypothetical.** A row the user cannot see and a row that does not exist produce the *same* response, so if the UI does not distinguish them deliberately it will tell someone their data is gone. `supabase-integration.md` §2 has the mechanics; the UI consequence is that the list's state is a union with a `forbidden` arm, not a `rows.length === 0` check.

**Optimistic rollback must be visible and must not lose the input.** The failure sequence is: show the change, mark it pending, the write fails, restore the previous value, and tell the user *with their input still recoverable*. A rollback that silently reverts is worse than no optimism, because the user believes the change was saved.

**"We will add RLS later" is always true.** Generate the forbidden state even when RLS is off today — retrofitting it means touching every list in the app.

---

## 13. Form UX

Eleven decisions, each of which a generator gets wrong by default.

**Field order** follows the filling-in order, not the column order (§6).

**Grouping** into fieldsets with real legends. Past about seven fields a flat form becomes a questionnaire and completion drops.

**Required marking, both ways.** The asterisk is decorative and `aria-hidden`; the `required` attribute is what actually announces it. One without the other means sighted and screen-reader users see different forms. And mark whichever set is *smaller* — on a form where 14 of 15 fields are required, marking the optional one is the useful information.

**Validation timing.** Never on the first keystroke. Validate on blur, then re-validate on change *once the field has been blurred* — so a field the user is fixing updates live, and a field they have not reached yet stays quiet. Telling someone their email is invalid while they are still typing the `@` is the most common form-UX failure there is.

**The error summary comes first in the DOM and takes focus on failed submit.** On a long form the invalid field is usually off-screen, and a user who presses Save and sees nothing happen concludes the button is broken. Each summary entry links to its field.

**Errors sit below their field**, in `--fg-danger`, referenced by `aria-describedby`, with `aria-invalid` on the control. Help text is referenced first so the guidance is heard before the complaint.

**Error copy says what to do.** "Enter an email address, like name@example.com" beats "Invalid email". The user already knows it is invalid; that is why the message is there.

**Save and discard.** The primary action is the first tab stop among the actions and carries the accent. "Cancel" becomes "Discard changes" once the form is dirty, because the consequence changed and the label should too.

**Unsaved-changes guarding.** Block the route change while dirty, and say what will be lost. The browser's own `beforeunload` covers tab close and nothing else — an in-app navigation needs the router's own guard, and forgetting it is why people lose work in SPAs specifically.

**Disabled submit is usually wrong.** A disabled Save button gives the user nothing to click and no explanation for why. Leave it enabled, validate on submit, and move focus to the summary. The exception is a submit already in flight, which must be blocked to prevent a double write — and that is `loading`, not `disabled`.

**Autosave, for long forms only.** Save on a debounce, show an explicit "Saved at 14:32" rather than a flash, keep the manual save as well, and handle the offline case by queueing. Autosave without a visible state is indistinguishable from data loss.

---

Related: `field-mapping.md` (what each column becomes), `supabase-integration.md` (RLS, realtime, pagination), `web-design-studio/references/layout-composition.md` (the primitives), `component-state-matrix` (proving all seven states actually render).
