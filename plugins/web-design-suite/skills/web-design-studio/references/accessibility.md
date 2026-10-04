# Accessibility

WCAG 2.2 Level AA is this suite's floor. The legal baselines are older, and it is worth knowing which (checked 2026-09-25). In the EU, the European Accessibility Act's harmonised standard is EN 301 549 v3.2.1, which is WCAG 2.1 AA. v4.1.1, which moves to WCAG 2.2, was published on 2026-09-02 and takes over once the Official Journal cites it. US ADA Title II requires WCAG 2.1 AA, from 2027-04-26 for public entities of 50,000 people or more and from 2028-04-26 for smaller ones. Section 508 is WCAG 2.0 AA. Meeting 2.2 AA covers all three, and it is what procurement questionnaires increasingly ask about. **Treat it as a floor, not a goal.** A page can pass every AA success criterion and still be miserable to use with a screen reader — AA does not require that focus order be *sensible*, only that it be programmatically determined; it does not require that an error message be *useful*, only that it exist.

This file is the executable version of Law 9: nothing ships un-audited. It uses the tokens in `assets/starter/styles/tokens.css` as ground truth and defers to `references/color-system.md` for all contrast arithmetic.

**One nomenclature note up front, because it trips people:** in the published WCAG 2.2 Recommendation, **2.4.11 Focus Not Obscured (Minimum)** is the Level AA criterion; **2.4.13 Focus Appearance** — the one with the geometry requirement — is **Level AAA**. This skill holds 2.4.13 as a floor anyway, because the AA criteria alone permit a focus indicator you cannot see, and because the reset's focus ring (§3) satisfies it for free.

## Contents

1. [The floor, stated concretely](#1-the-floor-stated-concretely)
2. [Semantics first](#2-semantics-first)
3. [Focus](#3-focus)
4. [Keyboard](#4-keyboard)
5. [Contrast](#5-contrast)
6. [Forms](#6-forms)
7. [Motion, media, and time](#7-motion-media-and-time)
8. [Touch and pointer](#8-touch-and-pointer)
9. [Content](#9-content)
10. [Testing procedure](#10-testing-procedure)
11. [Anti-patterns](#11-anti-patterns)

---

## 1. The floor, stated concretely

Every criterion below is one a marketing or product website actually touches. Criteria covering pre-recorded audio description, sign language, live captions and similar media-heavy requirements are omitted; add them when the project has that media.

| SC | Level | Plain English | Where it shows up here | How to verify |
|---|---|---|---|---|
| **1.1.1** Non-text Content | A | Every image, icon and control has a text alternative appropriate to its purpose | Alt-text decision tree §9 | Turn off images; read the page. Every `<img>` has an `alt` attribute (possibly empty) |
| **1.3.1** Info & Relationships | A | Visual structure is also in the markup: headings, lists, tables, labels, groups | Landmark + heading skeleton §2 | Heading outline in the a11y tree; every `<table>` has `<th scope>`; every group has `<fieldset><legend>` |
| **1.3.2** Meaningful Sequence | A | DOM order matches the reading order | Never reorder with `order:`/`grid-row` in a way that breaks reading §2 | Disable CSS; the page still reads in order |
| **1.3.3** Sensory Characteristics | A | Instructions don't rely on shape, size, position or sound alone | "Click the button below" → name the button | Grep copy for "above", "below", "on the right", "the round one" |
| **1.3.4** Orientation | AA | Works in both portrait and landscape | Never lock orientation | Rotate a phone |
| **1.3.5** Identify Input Purpose | AA | Fields collecting the user's own data carry `autocomplete` tokens | Forms §6 | Every personal-data input has a valid `autocomplete` value |
| **1.4.1** Use of Color | A | Color is never the only carrier of information | Status uses icon + text + `--fg-danger`, never color alone | Grayscale screenshot; all meaning survives |
| **1.4.3** Contrast (Minimum) | AA | 4.5:1 text, 3:1 for ≥24px regular / ≥19px bold | `--fg-default`, `--fg-muted`, `--fg-subtle` §5 | `python -m scripts.generate_color_ramp --check A B` |
| **1.4.4** Resize Text | AA | 200% text zoom with no loss of content or function | `rem`-based type scale, no fixed-height text containers | Browser zoom to 200% |
| **1.4.5** Images of Text | AA | Use real text, not pictures of text | Headings are text; `--text-*` handles the scale | Try to select the text |
| **1.4.10** Reflow | AA | 320 CSS px wide with no two-dimensional scrolling | Fluid `--space-fluid-*`, `--gutter-page`, `--measure-*` | 1280px window at 400% zoom |
| **1.4.11** Non-text Contrast | AA | 3:1 for control boundaries, states, and meaningful graphics | `--border-default`, `--border-focus`, icon-only buttons §5 | Contrast check against *adjacent* color |
| **1.4.12** Text Spacing | AA | No loss when line-height→1.5×, para spacing→2×, letter→0.12em, word→0.16em | Unitless `--leading-*`; never fixed heights on text boxes | Inject the bookmarklet CSS; nothing clips |
| **1.4.13** Content on Hover or Focus | AA | Hover/focus content is dismissible, hoverable, persistent | Tooltips, popovers §5 | Esc dismisses; pointer can travel into it; it does not vanish on its own |
| **2.1.1** Keyboard | A | All functionality is operable by keyboard | Key maps §4 | Unplug the mouse |
| **2.1.2** No Keyboard Trap | A | Focus can always move away by keyboard | Dialog trap uses `inert` + Esc §3 | Tab through the whole page in both directions |
| **2.1.4** Character Key Shortcuts | A | Single-character shortcuts can be turned off, remapped, or are focus-scoped | `/` to search must not fire while typing | Type in every field; no shortcut fires |
| **2.2.1** Timing Adjustable | A | Time limits can be turned off, adjusted, or extended | Session timeouts §7 | Wait one out |
| **2.2.2** Pause, Stop, Hide | A | Auto-moving/blinking/scrolling content over 5s has a control | Carousels, marquees, background video §7 | Look for the pause button |
| **2.3.1** Three Flashes | A | Nothing flashes more than 3×/second | §7 | Frame-count any flashing content |
| **2.4.1** Bypass Blocks | A | A way to skip repeated navigation | Skip link §3 | Tab once from page load |
| **2.4.2** Page Titled | A | Unique, descriptive `<title>` | "Page — Section — Site" | Read the tab |
| **2.4.3** Focus Order | A | Focus order preserves meaning and operability | DOM order = visual order §3 | Tab through; watch the ring |
| **2.4.4** Link Purpose (In Context) | A | Link text makes sense from its context | §9 | Read the links list alone |
| **2.4.5** Multiple Ways | AA | More than one route to each page | Nav + search + sitemap + footer | Site audit |
| **2.4.6** Headings and Labels | AA | Headings and labels describe their content | §2, §6 | Read the heading outline as a table of contents |
| **2.4.7** Focus Visible | AA | Keyboard focus has a visible indicator | The outline ring, §3 | Tab; the ring is always visible |
| **2.4.11** Focus Not Obscured (Min) | **AA — new in 2.2** | The focused component is not *entirely* hidden by author content | Sticky headers/footers are the usual culprit §3 | Tab through with a sticky header; nothing disappears under it |
| **2.5.1** Pointer Gestures | A | Multipoint/path gestures have a single-pointer alternative | Pinch-zoom maps, swipe carousels §8 | Operate with one finger, no path |
| **2.5.2** Pointer Cancellation | A | Act on up-event, not down-event | §8 | Press, drag off, release — nothing happens |
| **2.5.3** Label in Name | A | The accessible name contains the visible label text | `aria-label` must not contradict visible text §6 | Voice control: say the visible label |
| **2.5.4** Motion Actuation | A | Device-motion features have a UI alternative and can be disabled | Shake-to-undo | Rare on web; check if present |
| **2.5.7** Dragging Movements | **AA — new in 2.2** | Drag operations have a single-pointer non-drag alternative | Sliders, sortable lists, kanban §8 | Complete the task with clicks only |
| **2.5.8** Target Size (Minimum) | **AA — new in 2.2** | 24×24 CSS px, or adequately spaced | `--tap-min` (44px) exceeds it §8 | Measure the smallest control |
| **3.1.1** Language of Page | A | `<html lang>` is set and correct | §9 | View source |
| **3.1.2** Language of Parts | AA | Inline language changes are marked | `<span lang="fr">` §9 | Listen to a screen reader hit them |
| **3.2.1** On Focus | A | Focus alone never changes context | No auto-submit on focus | Tab through forms |
| **3.2.2** On Input | A | Changing a value alone never changes context | No auto-submit on `select` change | Change every select |
| **3.2.3** Consistent Navigation | AA | Repeated nav is in the same order across pages | One nav component, one home §2 | Compare three pages |
| **3.2.4** Consistent Identification | AA | The same function is named the same way everywhere | "Search" is not "Find" on page 2 | Component audit |
| **3.2.6** Consistent Help | **A — new in 2.2** | If help (contact, chat, self-help) is on multiple pages, it is in the same relative order | Footer contact block, chat launcher §9 | Compare pages; the help entry point does not move |
| **3.3.1** Error Identification | A | Errors are identified in text | §6 | Submit an empty form |
| **3.3.2** Labels or Instructions | A | Inputs have labels and needed instructions | §6 | Every input has a programmatic label |
| **3.3.3** Error Suggestion | AA | When a fix is known, suggest it | "Use the format YYYY-MM-DD" §6 | Enter a malformed value |
| **3.3.4** Error Prevention | AA | Legal/financial/data submissions are reversible, checked, or confirmable | Checkout, account deletion | Try to make an irreversible mistake |
| **3.3.7** Redundant Entry | **A — new in 2.2** | Info already entered in the same process is auto-filled or selectable | "Billing same as shipping" §6 | Walk a multi-step flow |
| **3.3.8** Accessible Authentication (Min) | **AA — new in 2.2** | No cognitive function test (memorise, transcribe, puzzle) without an alternative | Allow paste; support password managers §6 | Paste into every password and OTP field |
| **4.1.2** Name, Role, Value | A | Every control exposes name, role, state, and fires change notifications | §2, §4 | Inspect the accessibility tree |
| **4.1.3** Status Messages | AA | Status changes are announced without moving focus | `role="status"` / `aria-live` §6 | Trigger a toast with a screen reader on |

Two notes on 2.2 specifically. **4.1.1 Parsing was removed** — duplicate IDs and unclosed tags are no longer an SC failure in themselves (they still break `aria-labelledby`, so they still break your page). And the criteria marked new above are the ones audits are currently finding everywhere, because sites built to 2.1 have never been checked against them.

---

## 2. Semantics first

**The first accessibility tool is the right element.** A `<button>` arrives with a role, a name from its content, keyboard activation on Enter and Space, a focus ring, a disabled state, form participation, forced-colors styling and the right announcement in every screen reader. A `<div onclick>` with `role="button"`, `tabindex="0"`, `aria-pressed`, and a keydown handler is an imitation that will be wrong in at least one of those respects, forever.

Before writing any ARIA, ask: is there an element for this? `<button> <a href> <details>/<summary> <dialog> <input type> <select> <label> <fieldset>/<legend> <table> <nav> <main> <output> <progress> <meter>` cover most of what a website needs.

### The landmark skeleton

```html
<body>
  <a class="skip-link" href="#main">Skip to content</a>

  <header>                                   <!-- role=banner (page-level only) -->
    <nav aria-label="Primary"> … </nav>
  </header>

  <main id="main" tabindex="-1">             <!-- exactly one per page -->
    <h1>…</h1>
    <section aria-labelledby="pricing-h">
      <h2 id="pricing-h">Pricing</h2>
    </section>
  </main>

  <aside aria-label="Related articles"> … </aside>   <!-- role=complementary -->

  <footer>                                   <!-- role=contentinfo (page-level) -->
    <nav aria-label="Footer"> … </nav>
  </footer>
</body>
```

Rules that matter:

- **`<header>` and `<footer>` are only landmarks when they are not inside `<article>`, `<aside>`, `<main>`, `<nav>` or `<section>`.** A card's `<footer>` is not a `contentinfo`. This is why a page can appear to have six footers in the landmarks list and actually have one.
- **Every repeated landmark of the same type needs a distinguishing `aria-label`.** Two `<nav>`s both announced as "navigation" is a navigation failure. Do not put the word "navigation" in the label; the role already says it.
- **`<section>` is only a landmark (`region`) when it has an accessible name.** An unnamed `<section>` is a generic div with extra characters. Name it with `aria-labelledby` pointing at its own heading.
- **One `<main>`.** Screen reader users jump to it constantly.

### The heading outline is the document's real navigation

Screen reader users navigate by heading more than by any other method. The outline must be readable on its own as a table of contents.

- **One `<h1>`**, matching the page's subject and roughly the `<title>`.
- **Never skip a level going down.** h2 → h4 tells a user a level was lost. Going back up (h4 → h2) is fine and normal.
- **Choose the level by structure, not by size.** Size comes from `--type-h2` etc., which is a class, not the tag. A visually small section heading that is structurally an h2 is `<h2 class="type-h4">`.
- **Never use a heading for emphasis**, and never wrap a heading around a whole card.

Verify with the accessibility tree, or one line in the console:

```js
console.table([...document.querySelectorAll('h1,h2,h3,h4,h5,h6')]
  .map(h => ({ level: +h.tagName[1], text: h.textContent.trim().slice(0, 70) })));
```

### DOM order is the reading order

`order`, `row-gap` tricks, `grid-row`, `position: absolute` and `direction` can all put an element somewhere its DOM position does not predict. Screen readers, keyboard focus and `Tab` follow the DOM (1.3.2, 2.4.3). **Reorder the DOM, not the layout** — or accept the reorder only where it is visually and semantically insignificant. The single most common failure: a mobile layout that moves a CTA above the content visually while it remains last in the DOM.

### When ARIA helps, and the five rules

ARIA adds semantics HTML lacks: `aria-expanded`, `aria-current`, `aria-live`, `aria-describedby`, `role="tablist"`, `aria-controls`, `aria-selected`. It is genuinely necessary for composite widgets — tabs, comboboxes, trees, menus — because HTML has no element for them.

1. **Use a native element if one exists** with the semantics and behaviour you need.
2. **Do not change native semantics** unless you really must. `<h2 role="tab">` is almost always the wrong call; wrap instead.
3. **All interactive ARIA controls must be keyboard operable.** ARIA adds no behaviour whatsoever — `role="button"` does not make Enter work.
4. **Never put `role="presentation"` or `aria-hidden="true"` on a focusable element.** It becomes a control that focus can reach but assistive tech cannot see or name.
5. **Every interactive element has an accessible name.**

And the sixth, which is really the first: **no ARIA is better than bad ARIA.** Incorrect ARIA actively overrides what the browser got right. `role="button"` on a link removes the link's navigation announcement. `aria-label` on a `<div>` with no role is silently ignored. An `aria-expanded` that never updates tells the user the menu is closed while it is open — worse than saying nothing.

### `role="presentation"` vs `aria-hidden` vs `inert`

Three different tools, routinely confused:

| Tool | Removes the **element's** semantics | Removes the **subtree** | Removes focusability | Blocks pointer events | Use for |
|---|---|---|---|---|---|
| `role="presentation"` / `role="none"` | Yes | No — children are still announced | No | No | A layout `<table>`, a `<ul>` used purely for layout, an `<img>` that is decorative (`alt=""` is better) |
| `aria-hidden="true"` | Yes | **Yes** | **No — and that is the trap** | No | A decorative icon *inside* a labelled button; visually duplicated text |
| `inert` | — | Yes (also hides from AT) | **Yes** | **Yes** | Everything behind an open modal; an off-screen drawer; a disabled panel |

The fatal combination is `aria-hidden="true"` on a container that holds focusable elements: keyboard users tab into a region screen readers insist is not there. **If you are hiding a region, use `inert`.** Reserve `aria-hidden` for non-focusable decoration.

```html
<!-- Correct: the icon is decoration, the button is named by its text -->
<button class="btn"><svg aria-hidden="true" focusable="false">…</svg> Save</button>

<!-- Correct: an open dialog makes the rest of the page inert -->
<div id="page-root" inert> … </div>
<dialog open> … </dialog>
```

`inert` is supported in all current engines and replaces every hand-rolled focus trap for the *background* half of the problem. `focusable="false"` on inline SVG is still needed for legacy IE-era behaviour in some toolchains and costs nothing.

---

## 3. Focus

Focus is the keyboard user's cursor. If they cannot see it, the page is unusable — not degraded, unusable.

### The visible indicator

```css
/* One rule, in reset.css, applied to everything focusable. */
:focus-visible {
  outline: var(--stroke-focus) solid var(--border-focus);  /* the ring */
  outline-offset: var(--stroke-focus);
  /* stylelint-disable-next-line declaration-property-value-allowed-list -- ring 1, the gap: a spread of two tokens, drawn here once */
  box-shadow: 0 0 0 var(--stroke-focus) var(--bg-canvas);  /* the gap */
}
```

Why that shape:

- **Two rings: a 2px gap in the canvas color, then a 2px ring in `--border-focus`.** The canvas gap is what makes it legible on a dark button, a photo, or an accent fill: the indicator never sits directly against the component's own color.
- **The ring is an `outline`, not a `box-shadow`.** A component that draws its own `box-shadow` — a button's elevation, a card's shadow — sits in a later layer and replaces any ring drawn with `box-shadow`, so the keyboard user sees nothing (2.4.7). No component sets `outline`, so this ring survives all of them; a component with its own shadow loses only the gap.
- **It satisfies 2.4.13's geometry**: the accent ring is a 2px-thick perimeter around the whole component, which is the minimum area the criterion asks for.
- **It satisfies the 3:1 contrast requirement.** `--border-focus` is `--accent-600`; measured against `--bg-canvas` it is **4.67:1** in light mode and **4.23:1** in dark (where `--border-focus` is deliberately *not* re-pointed, and does not need to be). Against `--bg-surface` in light mode it is 4.92:1. Verify any change with `python -m scripts.generate_color_ramp --check '<focus>' '<adjacent>'`.
- **Forced colors keep it.** In forced-colors mode `box-shadow` is discarded, so a shadow-only ring vanishes completely; an outline is repainted in a system color and stays. That is the difference between a working and a non-existent focus ring for Windows High Contrast users (§10).

**Never `outline: none` without a replacement in the same rule.** If you find one, the fix is not to add the outline back at a different specificity; the fix is to delete the reset.

### `:focus-visible` vs `:focus`

`:focus` matches whenever an element has focus, including after a mouse click. `:focus-visible` matches when the browser's heuristic says the indicator should be shown — keyboard navigation, or any focus on a text input.

**Use `:focus-visible` for the ring.** Use `:focus` only when the state must be visible regardless of input modality, which in practice means text inputs (where `:focus-visible` already matches) and elements whose focus is load-bearing for a visible affordance.

Two consequences worth knowing:

- Programmatic `.focus()` after a *mouse*-initiated action generally does **not** match `:focus-visible`. That is correct behaviour — the mouse user does not need a ring — and it means route-change focus targets stay quiet for mouse users and visible for keyboard users automatically.
- `:focus-within` is the right hook for styling a *container* when something inside it is focused (a form group, a card with a link). Prefer it over JS.

### Focus order

Focus order must match visual order (2.4.3). This is not a suggestion you can style around — it is a DOM-order requirement (§2). The three recurring failures:

1. A CSS `order` or `grid-area` reorder on mobile.
2. A modal or drawer rendered at the top of the DOM but visually last, or vice versa. Render overlays in a portal at the end of `<body>`, which matches how they read.
3. `position: absolute` moving a control somewhere its DOM position does not suggest.

### Focus management: where focus goes when the focused thing disappears

**The rule: focus never falls to `<body>`.** When `<body>` receives focus, a screen reader user is returned to the top of the document with no announcement, and a keyboard user's next Tab starts from the beginning of the page.

| Event | Where focus goes |
|---|---|
| **Dialog opens** | The dialog itself, or its first meaningful control. Prefer the dialog container (`tabindex="-1"`) so the whole title and description are announced. Never the close button — the user hears "Close" as the first thing. |
| **Dialog closes** | **Back to the element that opened it.** Store the reference on open. If that element no longer exists (the row was deleted), fall back to the nearest surviving container. |
| **Client-side route change** | Focus the `<h1>` or `<main>` of the new view (`tabindex="-1"`), and update `<title>`. Without this, the user is silently left focused on a link that no longer exists. |
| **An item is deleted from a list** | The next item; if it was last, the previous; if the list is now empty, the list container or its empty-state heading. |
| **A step in a wizard advances** | The new step's heading. |
| **Content is expanded (disclosure)** | Nowhere — focus stays on the trigger, whose `aria-expanded` changes. Do not move focus into a disclosure. |
| **An async error appears** | Nowhere automatically for a status message (use a live region); *do* move focus to the error summary on a failed form submit (§6). |
| **A toast appears** | Nowhere. Announce it with `role="status"`. Moving focus to a toast steals the user's place. |

```js
// Route change — the minimum viable version.
function onRouteChange(view) {
  document.title = `${view.title} — Studio`;
  const target = view.root.querySelector('h1') ?? view.root;
  target.setAttribute('tabindex', '-1');
  target.focus();                       // won't show a ring for mouse users
  target.addEventListener('blur', () => target.removeAttribute('tabindex'),
                          { once: true });
}
```

### Focus trapping

A modal dialog must trap focus; nothing else should. Use the platform:

- **`<dialog>` with `showModal()`** traps focus, renders in the top layer, makes the rest of the document inert, and handles Esc. Use it unless you have a specific reason not to.
- **If hand-rolling**, the correct construction is `inert` on everything outside plus an Esc handler — not a `keydown` Tab-cycling loop. A Tab loop misses the browser chrome, the URL bar and the find bar, which users legitimately need to reach; `inert` does not.
- **Never trap focus in a non-modal thing.** A dropdown, a carousel and a video player must all let Tab out (2.1.2). A menu closes on Tab; it does not swallow it.

```css
/* The scrim is a Tier-2 role in the starter's tokens.css, so no call site
   holds the literal (Law 1). */
:root { --bg-scrim: oklch(0% 0 0 / 0.5); }

.dialog { z-index: var(--z-modal); box-shadow: var(--elevation-modal); }
.dialog::backdrop { background: var(--bg-scrim); }
```

### Skip links

2.4.1. One link, first in the DOM, visible on focus, pointing at `<main>`.

<!-- snippet: layout.css#skip-link -->
```css
/* Skip link. Present in the DOM, off-screen until focused. Never
   `display: none` — that removes it from the tab order, which is the one
   thing it exists for. */
.skip-link {
  position: absolute;
  inset-block-start: var(--space-0);
  inset-inline-start: var(--space-0);
  z-index: var(--z-toast);
  padding: var(--pad-block-md) var(--pad-inline-md);
  font: var(--type-ui);
  color: var(--fg-default);
  background: var(--bg-surface);
  border-radius: var(--radius-md);
  box-shadow: var(--elevation-overlay);
  translate: 0 -150%;
  transition: translate var(--motion-enter);
}
.skip-link:focus-visible { translate: 0 0; }
```

Move it off-screen with `transform`, not `display: none` (which makes it unfocusable) and not `visibility: hidden`. Target `<main id="main" tabindex="-1">` — without `tabindex="-1"` the anchor scrolls but focus stays behind in most browsers.

### 2.4.11 Focus Not Obscured

A sticky header or a cookie bar that covers a focused control fails at AA. Two fixes, both cheap:

```css
:root { scroll-padding-block-start: var(--nav-offset); } /* the header's height, published once: navigation-patterns.md §4 */
```

`scroll-padding` makes the browser's own scroll-into-view leave room. Then **tab through the entire page with the header sticky and a cookie banner open** and watch for a ring that disappears. Sticky *footers* and chat launchers are the most-missed case.

---

## 4. Keyboard

### Expected key map by pattern

Every row is the ARIA Authoring Practices behaviour a user has learned elsewhere. Deviating is a usability failure even when it is technically conformant.

| Pattern | Keys |
|---|---|
| **Button** | `Enter` and `Space` activate. `Space` fires on key*up*; `Enter` on key*down* |
| **Link** | `Enter` only. `Space` scrolls the page and must keep doing so |
| **Checkbox** | `Space` toggles. `Enter` does nothing (it submits the form) |
| **Radio group** | `Tab` enters the group at the checked radio (or the first, if none). `↑`/`←` previous, `↓`/`→` next — **and selects it**. `Space` selects. `Tab` leaves the whole group |
| **Select / combobox** | `↓` or `Alt+↓` opens. `↑`/`↓` move. `Enter` commits. `Esc` closes without committing (and, if already closed, clears). `Home`/`End`. Printable characters do typeahead |
| **Tabs** | `Tab` reaches the tablist once, then the panel. `←`/`→` (or `↑`/`↓` if vertical) move between tabs with roving `tabindex`. `Home`/`End` first/last. Automatic activation selects on arrow; manual activation requires `Enter`/`Space` — use manual when the panel is expensive to load |
| **Menu / menu button** | `Enter`, `Space`, or `↓` opens and focuses the first item; `↑` opens and focuses the last. `↑`/`↓` move, wrapping. `Esc` closes **and returns focus to the trigger**. `Tab` closes the menu and moves on. `→`/`←` open/close submenus. Typeahead. Items are not in the tab order |
| **Dialog (modal)** | `Tab`/`Shift+Tab` cycle within. `Esc` closes. Focus in on open, back to the trigger on close |
| **Disclosure** | `Enter`/`Space` toggles. Focus stays on the trigger. `aria-expanded` reflects the state |
| **Slider** | `←`/`↓` decrement, `→`/`↑` increment, `Home` min, `End` max, `PageUp`/`PageDown` large step. Announce via `aria-valuenow`/`aria-valuetext` |
| **Tree** | `↑`/`↓` move through visible nodes. `→` expands, or moves to the first child. `←` collapses, or moves to the parent. `Home`/`End`. `Enter` activates. `*` expands all siblings. Typeahead |
| **Grid / data grid** | Arrows move by cell. `Home`/`End` row start/end. `Ctrl+Home`/`Ctrl+End` first/last cell. `PageUp`/`PageDown` by viewport. `Enter` or `F2` enters edit mode; `Esc` exits it. The grid is one tab stop |

Two cross-cutting behaviours: **`Esc` always cancels the innermost dismissible thing** and never more than one layer at a time; and **any composite widget is a single tab stop** with a roving `tabindex` inside it — a 40-item menu that is 40 tab stops is a failure even though every item is reachable.

### No keyboard trap (2.1.2)

Focus must be able to leave every component by standard keys. If a component requires a non-standard key to escape (an embedded editor that eats Tab, for example), it must say so when focus enters — and offer `Esc` as the escape. Third-party embeds (maps, video players, payment iframes, chat widgets) are where traps actually live. **Tab through every embed on the page, in both directions, on every project.**

### `tabindex` discipline

- **`tabindex="0"`** — insert into the natural tab order at the element's DOM position. Only for a custom control that genuinely has no native equivalent.
- **`tabindex="-1"`** — programmatically focusable, not in the tab order. Used for focus targets (`<main>`, dialog containers, headings) and for the non-active items of a roving-tabindex widget.
- **`tabindex="1"` or any positive value — never.** Positive values create a *second* tab order that runs before every `tabindex="0"` element on the page, including browser-native controls. One positive value anywhere means every other interactive element must also be numbered, forever, in every future change. It is unmaintainable by construction.

```bash
grep -rnE 'tabindex=["'"'"']?[1-9]' src/    # must return nothing
```

---

## 5. Contrast

The arithmetic, the thresholds table, gamut handling and the APCA discussion all live in `references/color-system.md` §7. This section covers only where teams actually fail.

- **1.4.3 Contrast (Minimum), AA** — 4.5:1 for text under 24px regular / 19px bold; 3:1 at or above those sizes.
- **1.4.11 Non-text Contrast, AA** — 3:1, against *adjacent* colors, for (a) boundaries required to identify a control, (b) states that carry meaning, (c) graphics required to understand the content.
- **1.4.13 Content on Hover or Focus, AA** — anything that appears on hover or focus must be **dismissible** (Esc, without moving the pointer), **hoverable** (the pointer can move into it without it vanishing), and **persistent** (it stays until dismissed, focus moves, or it stops being valid). A CSS-only tooltip on `:hover` with a gap between trigger and tooltip fails "hoverable" every time.

### The five places teams fail

1. **Placeholder text.** It is text, and 1.4.3 applies at 4.5:1 — there is no exemption. The starter's `--fg-subtle` (`--neutral-500`) clears it only because its ramp step was darkened for the purpose: 4.91:1 (--neutral-500 on --neutral-50) on the canvas and 4.60:1 (--neutral-500 on --neutral-100) on the sunken well, its worst light surface. `check_roles.py` holds it there (`color-system.md` §6). Also: **placeholder is not a label** (§6), so the correct fix is often to delete it.
2. **Disabled state.** Genuinely exempt from 1.4.3 — but only if the control is genuinely inactive. A control that looks disabled and still works, or a "disabled" submit button that is the only feedback about an invalid form, is not exempt and is a usability failure regardless. `--fg-disabled` (`--neutral-400`, 2.53:1) is only legitimate on `disabled`/`aria-disabled` controls.
3. **Focus rings.** Covered by 1.4.11 at AA and by 2.4.13's 3:1 focused-vs-unfocused requirement. The focus ring (`--border-focus`) clears it at 4.23–4.92:1 (§3). The failure mode is a custom ring that only exists in one theme.
4. **Icon-only buttons.** The icon *is* the affordance, so 1.4.11's 3:1 applies to the glyph against its background. A `--fg-muted` (`--neutral-600`, 6.35:1) icon is fine; a `--border-default` (`--neutral-300`, 1.51:1) one is not. Icon-only controls also need an accessible name (§9).
5. **Control boundaries.** An input whose only boundary is `--border-default` on `--bg-surface` measures **1.51:1** — below the 3:1 that 1.4.11 requires for "boundaries necessary to identify the control". This is fine when the input has a distinct fill (`--bg-sunken` against `--bg-surface` and the border is decorative), and a failure when the input is the same color as the page. **Decide which of the two you are shipping and check it.** Same problem, same answer, for dark mode's `--border-default` (`--neutral-800` on `--neutral-1000` = 1.42:1).

Check any pair:

```bash
python -m scripts.generate_color_ramp --check 'oklch(56.5% 0.176 42)' 'oklch(98.2% 0.003 75)'
# → 4.67:1  (--border-focus on --bg-canvas)
```

---

## 6. Forms

Forms are where accessibility failures cost money directly.

### Label association — four mechanisms, in order of preference

| Mechanism | Use when |
|---|---|
| `<label for="id">` + `<input id="id">` | **Default.** Explicit, survives DOM moves, clickable label, works everywhere |
| `<label>` wrapping the input | Acceptable; awkward to style and can double-fire click handlers on nested controls |
| `aria-labelledby="id1 id2"` | The visible label exists but cannot be a `<label>` — e.g. a cell header naming a control in a table, or composing a name from two elements |
| `aria-label="…"` | **Last resort**: no visible text exists at all (icon-only button, a search field with only a magnifier). Overrides all visible text, invisible to sighted users, and untestable by eye |

Never `title` — it is a tooltip, not a label, and it does not appear on touch or for keyboard users.

**2.5.3 Label in Name:** when a visible label exists, the accessible name must *contain* its text, in the same order. `<button aria-label="Submit application">Send</button>` breaks voice control: the user says "click Send" and nothing happens. If you add `aria-label`, either there is no visible text or the label starts with the visible text.

### The complete field

```html
<div class="field">
  <label for="email">Email address</label>

  <input
    id="email"
    name="email"
    type="email"
    autocomplete="email"
    required
    aria-describedby="email-help email-error"
    aria-invalid="true">

  <p id="email-help" class="field-help">We only use this for receipts.</p>
  <p id="email-error" class="field-error">
    <svg aria-hidden="true" focusable="false">…</svg>
    Enter an email address in the format name@example.com.
  </p>
</div>
```

- **`aria-describedby` takes a space-separated list** and can safely reference an element that does not exist yet or is currently empty — so wire help *and* error at render time and only fill the error element when there is one. Swapping `aria-describedby` on and off is a common source of missed announcements.
- **`aria-invalid="true"` goes on the input**, and comes off when the error clears. Do not set `aria-invalid="false"` before the user has entered anything — several screen readers announce "valid", which is noise.
- **The error message must state the problem *and*, where the fix is knowable, the fix** (3.3.3). "Invalid" fails. "Enter an email address in the format name@example.com" passes.
- **An invalid field takes `--border-invalid`, never `--border-focus`.** A field drawn in the focus colour looks focused, not wrong. `--border-invalid` is `--danger-500`, 4.23:1 (--danger-500 on --neutral-100) on the sunken input, over the 3:1 of SC 1.4.11. The border is not the only cue: the message's icon carries the state without colour.
- **Error text needs an icon or prefix, not just `--fg-danger`** (1.4.1), and `--fg-danger` (`--danger-700`) must clear 4.5:1 on its surface — it does, at 8.14:1 on `--bg-surface`.
- **Required fields:** use the `required` attribute (which sets `aria-required` implicitly) and mark it in the visible label with a word or a legend-explained asterisk. An asterisk with no legend is not an instruction.

```css
.field { display: grid; gap: var(--gap-tight); }
.field-help  { font: var(--type-label); color: var(--fg-muted); }
.field-error { font: var(--type-label); color: var(--fg-danger); }
.input[aria-invalid="true"] { border-color: var(--border-invalid); }
```
(Parents own the gaps — Law 2. The label does not set its own margin.)

### Groups

Radios and checkbox sets need a group name, or the user hears "Standard, radio button, 1 of 3" with no idea what is being chosen.

```html
<fieldset>
  <legend>Shipping speed</legend>
  <label><input type="radio" name="speed" value="std"> Standard (3–5 days)</label>
  <label><input type="radio" name="speed" value="exp"> Express (next day)</label>
</fieldset>
```

`<fieldset>`/`<legend>` is the native mechanism and the one to use. `role="radiogroup"` + `aria-labelledby` is the fallback when the markup cannot be a fieldset.

### `autocomplete` (1.3.5)

Required at AA for any field collecting information *about the user*. It also raises conversion and is what makes password managers work (which is half of 3.3.8).

Common tokens: `name given-name family-name email username new-password current-password one-time-code organization street-address address-line1 address-line2 address-level2` (city) `address-level1` (state) `postal-code country-name tel bday cc-name cc-number cc-exp cc-csc url`. Prefix with `shipping`/`billing` for address sections. An invalid token is worse than none — the browser ignores it and the SC is not met.

### Inline validation timing

The rule: **validate on blur, re-validate on input only once the field is already invalid.**

- **Never validate on every keystroke for a field the user has not finished.** Typing `j` into an email field and being told "enter a valid email" is the interface arguing with someone mid-sentence.
- **On blur**, validate and show the error.
- **Once a field is showing an error, re-validate on `input`** so the error disappears the moment it is fixed. Clearing feedback should be instant; raising it should not be.
- **On submit with errors:** move focus to an error *summary* at the top (`tabindex="-1"`, listing each error as a link to its field), or to the first invalid field. Do not just paint them red.
- **Announce count changes with `role="alert"` on the summary** — it is assertive, which is correct here and almost nowhere else.

### 3.3.7 Redundant Entry and 3.3.8 Accessible Authentication

- **Redundant Entry (A):** in a multi-step process, anything already given is auto-populated or offered for selection — "Billing address same as shipping", a review step that shows the earlier answers rather than asking again. Exceptions: re-entry is essential (confirming a password), the information is no longer valid, or it is a security requirement.
- **Accessible Authentication (AA):** no step may require a cognitive function test — remembering a password, transcribing a code, solving a puzzle — without an alternative. In practice:
  - **Allow paste.** `onpaste="return false"` on a password or OTP field is a direct failure. So is splitting an OTP into six separate single-character inputs unless paste distributes across them.
  - **Support password managers**: real `<input type="password">`, correct `autocomplete` (`current-password` / `new-password`), a stable `name`, and no JS that clears the field on focus.
  - **`autocomplete="one-time-code"`** on OTP fields lets the platform fill them from SMS.
  - **Image-recognition CAPTCHAs are cognitive function tests.** Object recognition and personal content are explicitly permitted alternatives; a puzzle is not. Prefer invisible/risk-based challenges, or offer email-link authentication as the alternative path.

---

## 7. Motion, media, and time

Full treatment in `references/motion-system.md` §8. The conformance surface:

- **2.2.2 Pause, Stop, Hide (A)** — any content that moves, blinks, scrolls or auto-updates **for more than 5 seconds**, in parallel with other content, needs a mechanism to pause, stop or hide it. This catches auto-advancing carousels, background video, marquees, animated hero backgrounds and live-updating tickers. A carousel that advances itself with no pause button is the single most common A-level failure on marketing sites. The cheapest compliant answer is: **do not auto-advance.**
- **2.3.1 Three Flashes (A)** — nothing flashes more than three times per second unless it is below the general flash and red flash thresholds. Applies to video content and to "look at me" animations. This one can cause seizures; it is not a checkbox.
- **2.2.1 Timing Adjustable (A)** — a session timeout, a checkout hold, or a "this code expires in 60s" must be turnable off, adjustable to 10× the default, or extendable with at least 20 seconds' warning and a simple action (pressing a key) to extend, up to ten times. Exceptions: real-time events, essential time limits, and limits over 20 hours.
- **Autoplay** — `autoplay` is permitted only when the media is muted, under 5 seconds or has a control, and does not interfere with the rest of the page (1.4.2 covers audio specifically: any audio playing for more than 3 seconds needs a pause/stop or an independent volume control). Gate autoplay on `prefers-reduced-motion` as well; it is not required by WCAG but it is right.
- **Captions and transcripts** — captions for pre-recorded video with audio (1.2.2, A) and audio description or a media alternative (1.2.3, A; 1.2.5 AA raises this to audio description). A **transcript** is not a substitute for captions, but it is the highest-value artefact you can produce: it serves deaf users, people in noisy environments, search engines and anyone who would rather read. Auto-generated captions must be corrected; uncorrected machine captions routinely fail on names, numbers and technical terms — which are the words that carry the meaning.

---

## 8. Touch and pointer

### 2.5.8 Target Size (Minimum), AA — 24×24, and why this skill uses 44

The criterion requires 24×24 CSS px, with five exceptions: **spacing** (a 24px-diameter circle centred on the target does not intersect another target's circle), **equivalent** (another control on the same page does the same job and meets the size), **inline** (targets inside a sentence, or sized by the line-height of their text), **user-agent control** (unstyled native controls), and **essential**.

`--tap-min` is **44px** (2.75rem) — the AAA figure from 2.5.5, and the platform guidance from both Apple (44pt) and Google (48dp). This skill uses it as the default because 24px is a legal minimum derived from what is defensible, not from what is usable: it is roughly half the width of an adult fingertip's contact patch, and error rates on 24px targets are measurably worse, particularly one-handed and while moving.

```css
/* A control whose visual is smaller than its target. Layout does not change. */
.icon-btn {
  min-inline-size: var(--tap-min);
  min-block-size: var(--tap-min);
  display: grid;
  place-items: center;
}

/* When the visual truly must stay small (a tag's × ), grow the hit area only. */
.tag-remove { position: relative; }
.tag-remove::after {
  content: "";
  position: absolute;
  inset: 50%;
  inline-size: var(--tap-min);
  block-size: var(--tap-min);
  translate: -50% -50%;
}
```

The pseudo-element trick is the correct answer for dense UI: the target grows, the layout does not. Check that adjacent targets' expanded areas do not overlap — if they do, the spacing exception has been used up and you have a mis-tap generator.

**The other half of target size is spacing between targets.** Two 44px buttons flush against each other are still a mis-tap risk; `--gap-tight` between them is the minimum, `--gap-related` for anything destructive next to anything routine.

### 2.5.7 Dragging Movements, AA

Anything operated by dragging needs a **single-pointer alternative that is not a drag**. Not "also works with a keyboard" — a non-drag *pointer* path.

| Drag interaction | Required alternative |
|---|---|
| Reorderable list / kanban | "Move up" / "Move down" buttons, or a "Move to…" menu |
| Slider | Click on the track to set the value, or ± buttons, or a number input |
| Drag-to-upload | A visible file-picker button (the drop zone must be *additive*) |
| Map pan | Directional buttons, or click-to-centre |
| Drag-to-dismiss (sheet, toast) | A close button |
| Split pane / resizer | Preset size buttons, or a double-click to reset |

Exceptions are narrow: dragging is essential (a drawing canvas), or the drag is entirely the user agent's (native text selection).

### 2.5.2 Pointer Cancellation — act on up, not down

The down-event must not execute the function. This exists so a user who presses the wrong control can slide off it and release harmlessly — which is how everyone with a tremor, a stylus, or a phone in one hand actually operates a screen.

- **Use `click`, not `pointerdown`/`mousedown`, to perform actions.** `click` already fires only when press and release land on the same element, and it is emitted by keyboard activation too — one handler, both modalities.
- Visual press feedback *may* start on `pointerdown` (that is `:active`, and it is the right place for it). The *action* may not.
- If you must act on down (a piano key, a game control — the "essential" exception), provide an undo.
- **Never `preventDefault()` on `pointerdown` for an interactive element** — it suppresses the `click` that keyboard users and assistive tech rely on.

### Hover-dependent content

`:hover` does not exist on touch, and on touch a first tap often produces a sticky hover that never clears.

- Anything reachable only by hover must also be reachable by focus, and on touch by tap. A nav dropdown that opens on hover must open on click/Enter as well.
- Gate hover-only affordances with `@media (hover: hover) and (pointer: fine)`.
- Content shown on hover must satisfy 1.4.13 (§5): dismissible with Esc, hoverable, persistent.
- **Never put content only in a `title` attribute.** It never appears on touch, never on keyboard focus in most browsers, and is announced inconsistently.

---

## 9. Content

### Alt text decision tree

Ask, in this order:

1. **Is the image inside a link or button, and the only content?** → **Functional.** The alt describes the *destination or action*, not the picture. A logo linking home: `alt="Studio — home"`. A magnifier in a search button: `alt="Search"` (or `aria-label` on the button and `aria-hidden` on the SVG). Never `alt="magnifier icon"`.
2. **Does the image contain text that matters?** → **Text in image.** The alt reproduces the text exactly. Then ask why it is an image at all (1.4.5) — logos and wordmarks are the only routine exemption.
3. **Does the image convey information not present in the surrounding text?** → **Informative.** Describe the information, not the composition. Context decides length: on a product page, `alt="Charcoal wool overcoat, front view, mid-calf length"`; in an article about layering, the relevant detail may be different entirely. Aim under ~150 characters; if you need more, it is complex.
4. **Is it a chart, diagram, map or infographic?** → **Complex.** Short `alt` naming what it is and its headline finding, plus a full text alternative adjacent — a caption, a `<details>` table, or prose. The data table is almost always the better artefact. `aria-details` can link to it.
5. **Otherwise** → **Decorative.** `alt=""` (empty, but the attribute **must be present** — a missing `alt` causes screen readers to read the filename). Background flourishes, dividers, stock photos that repeat the adjacent text, and every icon that sits beside its own visible label.

Never begin with "image of" or "photo of" — the role is already announced. Do name the medium when it is the point: "Illustration of…", "Screenshot of…", "Chart showing…".

### Link text that works out of context

Screen reader users pull up a list of every link on the page. Three "Read more" entries in that list are three identical, useless rows. 2.4.4 permits context from the same sentence or list item, but the honest bar is: **does the link text alone say where it goes?**

- Write the destination into the link: "Read the 2026 accessibility report", not "Read more".
- If the design demands "Read more", extend the accessible name: `<a href="…">Read more<span class="visually-hidden"> about the 2026 accessibility report</span></a>`. This keeps 2.5.3 satisfied because the visible text still starts the name.
- **Links that open in a new tab must say so** in the accessible name, and should carry `rel="noopener"`.
- **A link and a button are different things.** A link navigates (Enter, right-click, middle-click, copy address, shows in the status bar). A button performs an action. `<a href="#" onclick>` and `<button>` used for navigation are both wrong, and both break user expectations that have nothing to do with assistive tech.

### Language, reading order, abbreviations

- **`<html lang="en">`** (3.1.1) — sets screen-reader pronunciation, hyphenation, quote marks and font fallback. A page announced in the wrong language accent is effectively unreadable. Use the right subtag: `en-GB`, `pt-BR`.
- **`<span lang="fr">raison d'être</span>`** (3.1.2, AA) for inline language shifts. Not needed for words fully naturalised into the page language.
- **Reading order** — see §2. Also: visually-hidden text must be *clipped*, never `display: none` or `visibility: hidden` (which remove it from AT too) and never `font-size: 0` or `text-indent: -9999px` (which break selection, search and RTL):
  ```css
  .visually-hidden {
    position: absolute;
    inline-size: var(--space-px); block-size: var(--space-px);
    padding: var(--space-0); margin: calc(var(--space-px) * -1);
    overflow: hidden; clip-path: inset(50%); white-space: nowrap; border: 0;
  }
  ```
- **Abbreviations** — `<abbr title="…">` on first use. The `title` is not reliably announced, so **expand it in the text on first use** and use `<abbr>` as a supplement, not a substitute.
- **3.2.6 Consistent Help** — if a contact link, chat launcher, help page link or support phone number appears on more than one page, it must be in the **same relative order** relative to the rest of the page content. In practice: put it in the footer (or the header) and leave it there. Moving the chat launcher from bottom-right on marketing pages to the nav on docs pages is the failure.

---

## 10. Testing procedure

Run in this order. Steps 1–3 find most of what matters and need no tooling.

### 1. Keyboard-only pass

Unplug the mouse. Then, on every page and every flow:

- Tab from the top. **The first stop is the skip link**; activate it and confirm focus lands in `<main>`.
- Tab through every control. The ring is **always visible** and **never obscured** (2.4.11) by sticky chrome. Tab order matches visual order.
- Operate every widget with the key map in §4.
- Open and close every dialog, menu and drawer. `Esc` works. **Focus returns to the trigger.**
- Tab backwards through the whole page with `Shift+Tab`. Backwards order is where broken focus management hides.
- Tab into and back out of every third-party embed.
- Submit every form with errors and confirm focus goes somewhere useful.

### 2. Zoom and reflow

- **200% browser zoom** (1.4.4): no clipped text, no overlapping content, nothing requiring horizontal scroll to read a line.
- **400% zoom on a 1280×1024 window** (1.4.10) — equivalent to a 320px-wide viewport. No two-dimensional scrolling. Content reflows to one column; nothing is hidden and no function is lost. Sticky headers are the usual casualty: at 400% a 64px header can eat half the viewport, so collapse it.
- **Text spacing** (1.4.12): inject `line-height: 1.5 !important; letter-spacing: 0.12em !important; word-spacing: 0.16em !important;` on `*` and `margin-block-end: 2em !important` on `p`. Nothing clips or overlaps. Fixed-height buttons and cards fail here.

### 3. Forced colors / Windows High Contrast

This is where token-based color systems break, and they break in predictable ways. Emulate in DevTools (Rendering → Emulate CSS media feature `forced-colors: active`) and verify on real Windows HCM before launch.

What breaks, and why:

| Symptom | Cause | Fix |
|---|---|---|
| **The focus ring disappears** | `box-shadow` is discarded in forced-colors mode, so a ring drawn only with `box-shadow` vanishes | Draw the ring as an `outline` (§3). Its color is forced to a system color and it stays |
| **All elevation vanishes** | Same — shadows are gone, so a "raised" card is flush with the page | `@media (forced-colors: active) { .card { border: var(--stroke-default) solid CanvasText; } }` |
| **Filled and ghost buttons look identical** | Both backgrounds are forced to `ButtonFace`. Anything distinguished only by background color collapses | Add a border, or `forced-color-adjust: none` on the one element that must keep its fill (and then guarantee its contrast yourself) |
| **Selected / active / error states disappear** | `--bg-selected`, `--bg-hover`, `--bg-active` and status fills are all forced to the same color | Pair every color-carried state with a border, an underline, an icon or `Highlight`/`HighlightText` |
| **The modal scrim is gone** | Translucent overlays are forced opaque or dropped; the dialog floats with no separation | Give the dialog a `CanvasText` border in the media query |
| **Icons turn invisible or the wrong color** | CSS `fill`/`stroke` are forced; SVG **presentation attributes** (`fill="#666"` in the markup) are **not** | Always `fill="currentColor"` on inline SVG, so the icon follows the forced text color |
| **A transparent border suddenly appears** | `border-color: transparent` is forced to a visible system color | Intentional in the focus-ring trick; a bug everywhere else. Use `border-style: none`, not a transparent border, for spacing hacks |

Use system color keywords **in pairs** — `Canvas`/`CanvasText`, `ButtonFace`/`ButtonText`, `Field`/`FieldText`, `Highlight`/`HighlightText`, `LinkText`, `GrayText` for disabled. Never guess which is light. Use `forced-color-adjust: none` sparingly and only where color *is* the content (a color swatch, a chart key, a brand gradient) — it opts you out of the user's entire accommodation.

### 4. Screen reader smoke test

You do not need to be fluent. You need to run one pass and listen for specific failures. Use **VoiceOver + Safari** on macOS (`Cmd+F5`), **NVDA + Firefox** on Windows (free), or **TalkBack + Chrome** on Android. Test with *one* real screen reader rather than none; the pairings above are what users actually run.

Listen for:

- **Unlabelled controls** — "button", "link", "edit text" with no name. Every one is a 4.1.2 failure.
- **"Clickable"** on a div (NVDA) — you have a fake control.
- **Filenames read aloud** — a missing `alt`.
- **The heading list** (VoiceOver `Ctrl+Opt+U` → Headings; NVDA `Insert+F7`) — read it as a table of contents. Does it describe the page?
- **The landmark list** — one `main`, uniquely named `nav`s, no stray `contentinfo`.
- **The links list** — any "click here", "read more", or bare URL.
- **State announcements** — "expanded"/"collapsed", "selected", "checked", "invalid entry". Toggle each control and confirm the announcement changes.
- **Live regions** — trigger a toast, a form error, a search-results update. Is it announced at all? Is it announced *twice*? (Two live regions on the same content, or `role="alert"` on a region that also has `aria-live`.)
- **Silence after an action** — the deadliest failure. Submit a form, delete a row, open a dialog. Silence means the user does not know it worked.

### 5. Automated tools — and what they cannot do

```bash
npx @axe-core/cli https://example.com --exit          # axe, CI-friendly
npx lighthouse https://example.com --only-categories=accessibility
npx pa11y-ci --sitemap https://example.com/sitemap.xml
```

Also run axe DevTools or WAVE in the browser on each template, and enable `eslint-plugin-jsx-a11y` (or the framework equivalent) so the cheapest class of error never reaches a branch.

**Automation finds well under half of the barriers.** In the one controlled study, the best single tool found 37–41% of 143 planted barriers (GDS, 2017), which is consistent with what every audit finds when it re-tests an "axe-clean" site. (Deque's 57%, 2021, is a different quantity: issues counted by volume, not barriers or criteria.) By criterion, a tool fully decides 7 of the 55 A and AA criteria and part of 31 more (`a11y-audit-runner/references/automation-coverage.md` §3). A clean axe report means the machine-checkable subset passes. It does not mean the page is accessible.

**What automation reliably catches:** missing `alt`, missing form labels, text contrast against a solid background, empty buttons and links, missing `lang`, duplicate IDs, invalid ARIA attribute names and values, ARIA references that point at nothing, missing document title, positive `tabindex`.

**What it cannot catch, and which is where real failures live:**

- Whether the alt text is *correct* — `alt="image"` passes every scanner.
- Whether the heading outline is *meaningful*.
- Whether focus order makes sense, or where focus goes when something disappears.
- Whether a custom widget's keyboard behaviour matches what users expect.
- Whether an error message is useful.
- Whether an `aria-live` region actually announces at the right moment.
- Whether link text works out of context.
- Contrast against gradients, images, video, or any semi-transparent overlay.
- Whether a "disabled" control is genuinely inactive.
- Everything in forced-colors mode.
- Whether the thing is comprehensible.

**The audit order that works: keyboard, then zoom/reflow, then forced colors, then a screen reader pass, then run the scanner to catch what you missed.** Running the scanner first produces a false sense of completion, which is the most expensive outcome available.

### 6. Regression

Put `axe-core` in the component test suite (`jest-axe`, `cypress-axe`, `@axe-core/playwright`) and assert zero violations per component. Add a keyboard-navigation test for every custom widget. Accessibility regressions are cheap to prevent and expensive to find later.

---

## 11. Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| `outline: none` with no replacement | Removes the only indicator keyboard users have. 2.4.7. The most common accessibility bug on the web |
| `<div onclick>` as a button | No role, no name, no keyboard, no focus, no disabled state, no forced-colors styling. 2.1.1 + 4.1.2 |
| Placeholder as the label | Vanishes on input, so the user cannot check what they typed; fails 4.5:1 at the starter's `--fg-subtle`; not announced as a label by all AT; breaks autofill. 3.3.2 |
| `aria-hidden="true"` on a container with focusable children | Keyboard users tab into content screen readers say is absent. A trap with no exit announcement |
| Positive `tabindex` | Creates a second tab order that precedes everything else and must then be maintained across every future change. 2.4.3 |
| Hand-rolled Tab-cycling focus trap | Traps the user out of browser chrome, the URL bar and find-in-page. Use `inert` + `<dialog>` |
| `title` as the accessible name | Not shown on touch, not shown on keyboard focus in most browsers, announced inconsistently. 1.1.1 / 4.1.2 |
| Colour as the only status carrier | Invisible to ~8% of men, all users in forced-colors mode, and anyone on a bad screen. 1.4.1 |
| Auto-advancing carousel with no pause | 2.2.2 at Level A, plus a vestibular trigger, plus measurably ignored by users |
| Auto-focusing the first field on page load | Steals the screen reader from the page heading and jumps the viewport on mobile. Only defensible on a single-purpose page (a search page, a login page) |
| `onpaste="return false"` on a password or OTP | Direct 3.3.8 failure, and blocks password managers |
| A skip link that is `display: none` until focus | `display: none` is unfocusable, so the link can never be reached. 2.4.1 |
| Icon-only buttons with no accessible name | 4.1.2, and 1.4.11 if the glyph is under 3:1 |
| `role="button"` on an `<a href>` | Removes the link announcement, breaks middle-click, right-click and "copy link address", and Space now does two contradictory things |
| Live region added to the DOM at the same moment as its content | The region must exist *before* the content changes, or nothing is announced. Render empty regions up front |
| "Accessible" mode as a separate page or widget overlay | Separate but unequal, always out of date, and overlays measurably make things worse. Fix the page |
| Shipping on an axe-clean report alone | Finds well under half of the barriers, and fully decides 7 of the 55 A and AA criteria. §10 |
