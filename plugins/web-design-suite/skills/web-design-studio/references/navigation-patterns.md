# Navigation Patterns — the proven set

The half of the navigation reference covering patterns with a track record. Its sibling covers inventing new ones and the usability gate they must pass (Law 8). Reach for this **before** you draw a header: navigation is the first structural decision a site makes and the most expensive to reverse, because it is entangled with the URL scheme, the IA, and every internal link on the site.

Laws that bite hardest here: **1** tokens or nothing · **2** parents own the gaps (a nav item never sets its own outer margin; the bar sets `gap`) · **5** layers, not specificity (nav lives in `@layer components`, never wins by `!important`) · **7** density is a dial (a nav built right compacts via `--density`, not by rewriting padding) · **9** nothing ships un-audited.

Catalog entries use nine fixed fields so you can diff two options in ten seconds: **Is · Wins · Fails · Scent · Keyboard · Touch · A11y · Build · Spacing.**

## Contents

1. [Selection matrix](#1-selection-matrix) — [by archetype](#11-by-site-archetype) · [by scale](#12-by-number-of-top-level-destinations)
2. [Catalog](#2-catalog) — [2.1 Top bar](#21-horizontal-top-bar) · [2.2 Sticky / fixed / scroll-aware](#22-sticky-vs-fixed-vs-scroll-aware) · [2.3 Mega menu](#23-mega-menu) · [2.4 Dropdowns](#24-dropdowns-details-popover-js) · [2.5 Sidebar](#25-sidebar-nav) · [2.6 Bottom tab bar](#26-bottom-tab-bar-mobile) · [2.7 Hamburger / drawer](#27-hamburger--off-canvas-drawer) · [2.8 Command palette](#28-command-palette-k) · [2.9 Breadcrumbs](#29-breadcrumbs) · [2.10 Faceted filtering](#210-faceted-filtering--filter-rail) · [2.11 Tabs vs segmented vs sub-nav](#211-tabs-vs-segmented-control-vs-sub-nav) · [2.12 Anchor nav + scroll-spy](#212-in-page-anchor-nav--scroll-spy) · [2.13 Pagination vs infinite scroll](#213-pagination-vs-infinite-scroll-vs-load-more) · [2.14 Stepper](#214-stepper--wizard) · [2.15 Footer](#215-footer-as-navigation) · [2.16 Search](#216-search-as-navigation) · [2.17 Disclosure containers](#217-progressive-disclosure-containers)
3. [Cross-cutting rules](#3-cross-cutting-rules)
4. [Spacing spec](#4-spacing-spec)
5. [Failure gallery](#5-failure-gallery)
6. Code for the four most-often-broken patterns: `navigation-code.md`

---

## 1. Selection matrix

### 1.1 By site archetype

| Archetype | Primary nav | Secondary | Known failure mode |
|---|---|---|---|
| Marketing / brochure | Top bar, 4–6 items, one accent CTA at the right end | Fat footer; anchor nav on long pages | Clever labels ("Solutions", "Platform") carry no scent; traffic pools on the homepage |
| SaaS app | Persistent left sidebar, collapsible to icon rail | Top bar for org/account/search + ⌘K | Sidebar grows to 20 undifferentiated rows; the active state is a slightly bolder font nobody sees |
| E-commerce | Top bar + mega menu over the category tree | Faceted filter rail, breadcrumbs, persistent search | Hover mega menu with no intent guard flickers on diagonal paths; filters not in the URL, so shared links show the wrong products |
| Editorial | Top bar of sections + prominent search | Fat footer, next/related, section landings | Infinite scroll eats the footer and destroys back-button return; the current section stops being visible once you scroll |
| Documentation | Three-pane: sidebar tree · content · TOC with scroll-spy | Breadcrumbs, prev/next, version switcher, ⌘K | Tree ships fully expanded (200 rows) or fully collapsed (no scent); scroll-spy flickers because it was built on `scroll` + `offsetTop` |
| Portfolio | Minimal bar (2–4 items) or a single index page | Project prev/next; back-to-index that restores scroll | Nav as art piece: unlabelled icons, hover-only reveal, no focus states. Fails the Law 8 gate outright |
| Community | Top bar + persistent search | Category rail, activity rail, tabs for sort | Sort tabs aren't URLs, so "hot" can't be linked or indexed; unread state is the only wayfinding and it resets |
| Dashboard | Icon rail or collapsible sidebar; content-level tabs | Breadcrumb for drill-down; global scope control | No way back up because cards were built as `<div onclick>`; scope is component state instead of URL state |
| Multi-brand enterprise | Property switcher + per-brand top bar | Global utility strip above; unified footer | Two competing navs stack to 140px of chrome; the switcher looks like nav so people use it as nav |

### 1.2 By number of top-level destinations

| Count | What works | Why |
|---|---|---|
| **1–4** | Inline links in the bar. Keep them inline on mobile — no hamburger | Four items fit under 360px at `--text-sm`. Hiding four costs a tap and all the scent for zero gain |
| **5–7** | One-row horizontal bar, no dropdowns needed. Mobile: bottom tab bar (if ≤5, app-like) or drawer | Still scannable as one chunk; serial-position effects are strong and usable |
| **8–12** | Bar of 5–7 **groups**, each opening a dropdown or mega menu. Never 12 flat items | Past ~7 undifferentiated items the eye stops chunking and starts linear reading. Grouping restores the chunk |
| **12+** | Mega menu with columns and column headings, or a persistent sidebar tree | Columns add a second axis; a column heading is a scent label that costs one glance and saves a menu level |
| **Hundreds** | Search-first with browse secondary: prominent search, facets, breadcrumbs | No menu can enumerate the space. The menu's job changes from listing destinations to teaching the catalog's vocabulary |

**Corollary:** the count that matters is *top-level* items, not pages. A 40 000-page docs site can have 6. If you can't get the top level to ≤7, the problem is the IA, not the nav component.

---

## 2. Catalog

### 2.1 Horizontal top bar
**Is** One row: brand · primary links · utility actions. Variants: *left-logo-right-actions* (default), *split* (links flanking a centred logo), *centred logo* (logo on its own row, links below).
**Wins** ≤7 destinations; content-led sites; anywhere first impression matters and horizontal space is plentiful.
**Fails** App shells with three-level hierarchies (a bar can't show three levels); anything needing >7 slots.
**Scent** The strongest of any bar pattern — every destination visible, no interaction required. That is its whole advantage; do not throw it away by hiding items.
**Keyboard** Links in a list; tab order = DOM order. **Never add `role="menubar"`** — it opts you into the full APG contract (arrow keys, Home/End, typeahead, roving tabindex) you won't implement, and suppresses link semantics.
**Touch** Below `--bp-md`: keep ≤4 items inline, else drawer or bottom bar. Bar ≤56px on phones.
**A11y** `<header><nav aria-label="Main"><ul><li><a>`; `aria-current="page"` on the active link. Every `<nav>` on the page needs a *distinct* label ("Main", "Breadcrumb", "Footer", "On this page").
**Build** The `<ul>` is not decoration — it gives screen-reader users an item count before they commit to listening. The logo's accessible name is the company name, not "logo".
**Spacing** Bar is flex with `gap: var(--gap-separate)` between the three zones; link list `gap: var(--gap-related)`; item `padding: var(--pad-block-md) var(--pad-inline-md)` with `min-height: var(--tap-min)`; inset `var(--gutter-page)`.

### 2.2 Sticky vs. fixed vs. scroll-aware
**Is** Four behaviours, routinely confused. *Static*: scrolls away. *Sticky*: stays in flow, sticks at a threshold — silently does nothing if any ancestor has `overflow: hidden/auto`. *Fixed*: out of flow, so you reserve its height yourself. *Scroll-aware*: fixed, hides on scroll down, reveals on scroll up.
**Wins** Pages over ~3 viewports; nav used mid-task (apps, docs); a persistent CTA or search that is the point of the bar.
**Fails** Short pages (pure occlusion — nothing to return to). Mobile: a 64px fixed bar on a 780px viewport is a permanent ~10% tax on the content area, before browser chrome. Reading-focused pages, where peripheral motion costs attention.
**The direction rule** Never toggle on raw delta — trackpad momentum and iOS rubber-banding flip the sign every frame and you get a strobing header. (1) Track `lastY`, ignore zero deltas. (2) On a direction change, record where that direction began and *do not act*. (3) Act only once travel in the new direction exceeds a **hysteresis threshold of 8–16px** — 12px survives trackpads and cheap Android panels. (4) Always reveal when `scrollY <= headerHeight`; nobody should scroll up to get the header back at the top of the page. (5) Never hide while a menu inside is open or focus is inside the header — a keyboard user tabbing a long page scrolls the document, and hiding what they're tabbing through is a trap.
**Scent** Neutral. Scroll-aware trades continuous visibility for content area and keeps recovery to one flick.
**Keyboard** Header is early in the DOM, so early in tab order — good. Must be skip-link-bypassable, and must reveal on `focusin`.
**Touch** Prefer scroll-aware to sticky on phones. With `fixed`, reserve height on `<main>` or the first screenful is hidden.
**A11y** Fixed headers break in-page anchors — targets land behind them. Fix with `scroll-padding-top` on `:root` and `scroll-margin-top` on targets, not a JS offset hack. Under `prefers-reduced-motion` the tokens collapse durations to 1ms so the header snaps; that is correct, not a bug.
**Build** Animate `transform: translateY(-100%)` only — animating `top`/`height`/`margin` reflows the document every frame. rAF-throttle the handler. Code: `navigation-code.md` §1.
**Spacing** Desktop target 64px, built from `--pad-block-md` + item box, never hardcoded. Mobile ≤56px. `z-index: var(--z-sticky)`.

### 2.3 Mega menu
**Is** A wide panel from a top-bar trigger, laid out in labelled columns; optionally a featured cell in the last column.
**Wins** 12+ destinations with a real two-level structure — category trees, large portfolios, universities. Flattening two levels into one glance is the biggest wayfinding win available in a bar.
**Fails** Under ~8 children (use a dropdown; a mega panel for 5 links looks like a bug). And whenever it opens on hover with no intent guard.
**Scent** Best in class *if* column headings are real nouns from the user's vocabulary. Forty links with no headings is worse than a dropdown of eight.
**The diagonal-path problem** User is on trigger B with the panel open below, and moves diagonally toward a link in its lower-left. That path crosses trigger A; naive `mouseenter` switching swaps the panel mid-motion and the target vanishes from under the cursor. This is the defining mega-menu defect. Two fixes: **safe triangle** (correct) — build a triangle from the pointer's last position to the two *leading* corners of the open panel (top-left/top-right for a panel below a bar; the two left corners for a sidebar flyout) and suppress switching while the pointer is inside it, capped at ~300ms so a stalled pointer resolves; **intent delay** (adequate) — open after ~100ms, close after ~150–300ms; cheaper, but adds latency to every legitimate open and still mis-switches on a fast diagonal. Never use a transparent `::before` bridge over siblings — it makes the neighbouring triggers unclickable.
**Keyboard — what most get wrong** The trigger is a `<button aria-expanded aria-controls>`, not a link; if the category has a landing page, put that link *first inside the panel* ("All Shoes →") — a control that both navigates and expands satisfies neither user. **Do not use `role="menu"`/`menuitem`.** Those are for application command menus: they strip link semantics, remove items from the AT links rotor, force virtual-cursor users into forms mode, and oblige you to implement roving tabindex. A mega menu is a disclosure containing lists of links; `<button aria-expanded>` + `<ul><li><a>` is correct and complete. `Escape` closes and returns focus to the trigger. Tabbing past the last link closes and continues — **no focus trap**; this is non-modal.
**Touch** There is no hover. Below `--bp-lg`, convert to an accordion inside the drawer. A hover-only mega menu on touch fires hover *and* click on first tap, navigating before the panel is read.
**A11y** `aria-expanded` synced on every state change; panel labelled by its trigger via `aria-labelledby`; column headings are real elements bound to the `<ul>` with `aria-labelledby`. Close on `focusout` when focus leaves the trigger+panel subtree. One panel open at a time.
**Build** Render the panel adjacent to its trigger so tab order is natural. Code: `navigation-code.md` §2.
**Spacing** Panel `padding: var(--pad-card)`; columns `gap: var(--gap-separate)`; links in a column `gap: var(--gap-related)`; heading→first link `var(--gap-tight)`; `background: var(--bg-raised)`, `box-shadow: var(--elevation-overlay)`, `border-radius: var(--radius-xl)`, `z-index: var(--z-dropdown)`, entrance `var(--motion-enter)`.

### 2.4 Dropdowns: `<details>`, Popover, JS
**Is** A small panel (≤10 links) under a trigger. Three honest implementations:

| | `<details>/<summary>` | Popover API | Hand-rolled JS |
|---|---|---|---|
| Works with no JS | Yes | Yes (`popovertarget` is declarative) | No |
| Light dismiss | You write it | Built in (`popover="auto"`) | You write it |
| `Escape` to close | You write it | Built in | You write it |
| Top layer (escapes `overflow: hidden`) | No | Yes | No |
| `aria-expanded` | Not reliably mapped across AT | **Set by the browser** on a `popovertarget` invoker; don't script it | You set it |
| Positioning | Normal flow | Top layer — needs CSS anchor positioning or JS | You place it |
| Animating open/close | Needs a wrapper; `height` isn't animatable on `<details>` | Needs `@starting-style` + `transition-behavior: allow-discrete` | Free |

**Honest recommendation** Popover API for new work — top layer, light dismiss and `Escape` for zero JS, Baseline across Chrome/Edge 114+, Safari 17+, Firefox 125+. The browser gives a `popovertarget` invoker an implicit `aria-expanded` and `aria-details` (MDN, "Using the Popover API"). In Chromium 153 the invoker reads collapsed, expanded, then collapsed again after light dismiss, with no script. So leave `aria-expanded` off the invoker. A hand-written value is one more thing to keep in step, and light dismiss never updates it. CSS anchor positioning is the right placement answer but is younger than the popover API — ship a `position: absolute` fallback inside `@supports not (anchor-name: --a)`. Use `<details>` when it must work before hydration and you'll write outside-click and `Escape` yourself. Hand-roll only for behaviour neither gives you.
**Wins** Utility menus — account, language, sort — 3–10 items, secondary importance. **Fails** As primary nav past ~10 items, or nested two levels deep (a submenu inside a dropdown is a hit-area nightmare on every device).
**Scent** Weak; contents invisible until opened. Compensate with a specific trigger label ("Account", not "⋯").
**Keyboard** `Enter`/`Space` opens, `Escape` closes *and restores focus to the trigger*, `Tab` moves through and closes on exit.
**Touch** Open on click, never hover. Trigger and every item ≥ `--tap-min`.
**Spacing** Panel `padding: var(--pad-block-sm) var(--pad-inline-xs)`; items `var(--pad-block-md) var(--pad-inline-md)`, `min-height: var(--tap-min)`; groups `gap: var(--gap-tight)` with a `--border-subtle` rule between.

### 2.5 Sidebar nav
**Is** A vertical rail beside the content, in four shapes: *persistent*, *collapsible* (to nothing), *icon rail* (to icons + tooltips), *three-pane* (rail → section tree → content: the docs/mail shape).
**Wins** Apps and docs — repeated navigation within a session, hierarchy deeper than two levels. Vertical space is cheap: a sidebar holds 20 items where a bar holds 7.
**Fails** Content-led marketing (steals the content column for nav nobody uses twice); any viewport below `--bp-lg` without a drawer fallback.
**Scent** Excellent when grouped with section labels and the current item is unambiguous. Near-zero in icon-rail mode — icons alone are guessable for about six universal concepts (home, search, settings, user, add, back). Everything else needs a label, and a tooltip is not a label.
**Keyboard** A list of links; tab order = DOM order. Collapsible groups are `<button aria-expanded>` + `<ul>`. Do not build `role="tree"` unless users genuinely move nodes — trees carry a heavy contract (arrows, expand/collapse, typeahead, level announcement) and a docs sidebar is a nested list of links.
**Touch** Becomes the drawer below `--bp-lg`; preserve group expansion state across the transition.
**A11y** `<nav aria-label="Sections">`; `aria-current="page"` on the exact page, `aria-current="true"` on an ancestor if you highlight the trail. Icon rail: a visually-hidden `<span>` is more reliable than `aria-label` on an anchor wrapping an `<svg>`.
**Build** `position: sticky; top: var(--nav-offset)` inside a grid, never `fixed` — sticky keeps the footer reachable. Add `overflow-y: auto; overscroll-behavior: contain` so scrolling past its end doesn't chain to the page.
**Spacing** Rail `padding-inline: var(--pad-inline-sm)`; rows `var(--pad-block-sm) var(--pad-inline-md)`, `min-height: var(--tap-min)`, `gap: var(--space-0)` (separation comes from the selected pill, not air); groups `gap: var(--gap-separate)`; group label `--type-label`, `--fg-muted`, `--tracking-caps`. Left-edge rule in [§4](#4-spacing-spec).

### 2.6 Bottom tab bar (mobile)
**Is** 3–5 persistent destinations fixed to the bottom of the viewport.
**When it beats a hamburger** App-like sites (repeat visits, task switching), ≤5 destinations, and those destinations are *peers* rather than a hierarchy. The advantage is mechanical: the bottom third of a phone is the thumb-reachable zone, and the destinations stay **visible** — exactly what a hamburger destroys. If you can get to five, prefer this over a drawer every time.
**Fails** >5 items (labels truncate, targets drop below `--tap-min`); hierarchical IA where sections aren't peers; content sites where a permanent bar is pure tax. Also collides with iOS Safari's bottom chrome and the Android gesture bar.
**Scent** Good and constant. Labels mandatory — icon-only bottom bars fail outside the universal six.
**Keyboard** Still a `<nav>` of links; don't put primary nav last in the DOM. If it switches peer views of *one* page, it may be tabs — see §2.11.
**Touch** ≥ `--tap-min` per target, 48–56px including label. Respect `env(safe-area-inset-bottom)` or the last row sits under the home indicator.
**A11y** `<nav aria-label="Primary">`, `aria-current="page"`. Never convey the active tab by color alone — add weight, a filled icon variant, or an indicator bar.
**Spacing** `padding-block: var(--pad-block-sm)`; `padding-bottom: calc(var(--pad-block-sm) + env(safe-area-inset-bottom))`; equal-fraction grid with `gap: var(--space-0)` so targets are identical; icon→label `var(--gap-fused)`; `z-index: var(--z-sticky)`.

### 2.7 Hamburger / off-canvas drawer
**Is** An icon button opening an edge panel containing the nav.
**The discoverability cost is real** Repeated usability work (NN/g among others) finds hidden navigation measurably reduces discovery and use of the destinations inside, compared with the same destinations shown inline. The effect is largest on desktop, where no space constraint justifies the hiding. Treat "hamburger on desktop" as a defect; treat "hamburger on mobile" as a cost you pay only after running out of room.
**Mitigations that work** (1) Keep the 2–3 highest-value destinations **visible** and put the rest behind "More" — partial visibility retains most of the scent. (2) Put the word **Menu** beside the glyph; a labelled icon outperforms the bare one. (3) Prefer a bottom tab bar when the IA allows ≤5 peers. (4) Keep the primary conversion action outside the drawer, always visible.
**Wins** Phone viewports with >5 destinations, or a deep tree needing an accordion. **Scent** Zero until opened. That is the whole problem.
**Keyboard/focus (modal)** On open, move focus into the drawer — to a `tabindex="-1"` heading (better than the close button: the screen reader announces what opened). Trap `Tab`. `Escape` closes. On close, return focus to the trigger with `focus({ preventScroll: true })`. Background goes `inert`.
**Touch** Rows ≥ `--tap-min`. Lock body scroll and set `overscroll-behavior: contain` on the panel.
**Build** Use `<dialog>` + `showModal()`: top layer, backdrop, `Escape`, focus containment and background inertness from the platform, correctly, free. Baseline since 2022. Hand-roll with the `inert` attribute (Baseline since 2023) only when the drawer must be **non-modal** — i.e. the page behind stays usable. Code: `navigation-code.md` §3.
**Spacing** Panel `padding: var(--pad-card)`, `inline-size: min(88vw, 22rem)`; rows `var(--pad-block-md) var(--pad-inline-md)`, `min-height: var(--tap-min)`; groups `gap: var(--gap-separate)`; scrim at `--z-overlay`; transition `var(--motion-expand)`.

### 2.8 Command palette (⌘K)
**Is** A modal input over a fuzzy-matched index of destinations and actions.
**Primary vs supplementary** Supplementary, almost always. Defensible as primary only when users are repeat/expert, the destination space is large and flat, **and** a full visible navigation still exists. It is JS-only and undiscoverable by definition, so it can never be the sole route to anything.
**Wins** Dense apps and docs with expert users. **Fails** First-visit sites, and anywhere it's the only path.
**Scent** None before opening, excellent after — it surfaces destination *names*. Make it discoverable with a visible affordance showing the shortcut ("Search ⌘K"); that is the difference between 3% adoption and 40%.
**Keyboard** `⌘K`/`Ctrl+K` opens (guard against firing while focus is in a text input). `↑`/`↓` move the active option, `Enter` activates, `Escape` closes and restores focus. Do **not** move DOM focus between options — use `aria-activedescendant`.
**Touch** Largely irrelevant; never make it the mobile nav.
**A11y** Combobox pattern: `role="combobox"` + `aria-expanded` + `aria-controls` → `role="listbox"` of `role="option"`, with `aria-activedescendant`. Announce result counts in a polite live region *after a debounce*, or every keystroke floods the screen reader.
**Build** Index destinations and actions separately and label the groups; ranking that mixes them is unreadable.
**Spacing** Dialog `padding: var(--pad-card)`, `max-inline-size: 36rem`, offset from top ~12vh; options `var(--pad-block-md) var(--pad-inline-md)`, `min-height: var(--tap-min)`; groups `gap: var(--gap-related)`; `--elevation-modal`, `--z-modal`.

### 2.9 Breadcrumbs
**Is** A horizontal trail showing position in the hierarchy. Two kinds, and the difference matters:
- **Location breadcrumb** (use this): the item's fixed position in the IA — `Home › Women › Shoes › Running`. Identical for every user, derivable from the URL or content model, cacheable, good for SEO, and it teaches the taxonomy.
- **Path / attribution breadcrumb** (avoid): the trail the user actually walked. It duplicates the back button, differs per session, produces absurd trails after a few sideways moves, and is unreliable to reconstruct. The one legitimate variant is a single explicit "← Back to search results" that preserves query *and* scroll position.

**Wins** Hierarchies ≥3 deep, and any site with heavy deep-link entry — a user landing from Google has no context and a breadcrumb supplies all of it in one line. **Fails** Flat sites (a two-item crumb is noise) and linear flows (use a stepper).
**Scent** High per pixel: it names both where you are and every level you can climb to.
**Keyboard** Plain links; nothing special. **Touch** On phones truncate the *middle* (`Home › … › Running`), keep first and last, and make the ellipsis a real expanding button. Never truncate the current page.
**A11y** `<nav aria-label="Breadcrumb"><ol>`; the last item is the current page, `aria-current="page"`, and **not** a link. Separators are decorative — `::before` content or an `aria-hidden` span. Never let "/" into the accessible name.
**Spacing** `gap: var(--gap-tight)` between crumb and separator; `--type-ui`; `--fg-muted` with the current page at `--fg-default`; `var(--gap-grouped)` above the content.

### 2.10 Faceted filtering / filter rail
**Is** Grouped multi-select constraints over a result set — category, price, size, brand, rating. On large catalogs this *is* the navigation, not a decoration on top of it.
**Wins** Result sets over ~50 items with meaningful attributes. **Fails** Small or homogeneous sets; facets with one available value; facets the merchandiser cares about and the shopper doesn't.
**Non-negotiables** (1) **Counts on every value**, computed from the current result set — `Nike (42)` tells the user what a click costs before they spend it. (2) **Zero-result values disabled or hidden**, never clickable; a click that yields "0 results" is a design failure, not user error. (3) **Applied filters as removable chips** above the results, plus one "Clear all". (4) **Every filter in the URL query string** — shareable, bookmarkable, back-button-correct, restorable. Filters held only in component state are the most common serious bug in commerce nav. (5) **Announce the new result count** in a polite live region after the debounce.
**Scent** Excellent — counts are the scent.
**Keyboard** Groups are `<fieldset><legend>`; values are real checkboxes/radios. Custom toggles that lose group semantics lose the group announcement too.
**Touch** Full-screen sheet with **batched Apply** and a live "Show 128 results" count on the button. Desktop applies instantly (cheap to undo); instant apply behind a mobile sheet re-renders a list the user can't see.
**Spacing** Rail `padding-inline-end: var(--gap-separate)`; groups `gap: var(--gap-separate)`; values `gap: var(--gap-tight)`, each row `min-height: var(--tap-min)`; chips `var(--pad-block-xs) var(--pad-inline-xs)`, `--radius-full`, row `gap: var(--gap-tight)`.

### 2.11 Tabs vs. segmented control vs. sub-nav
**Is** Three things that look like a row of choices and are not interchangeable. Apply the rule in order:
1. **Is each item a distinct URL you'd want indexed, linked or bookmarked as a page?** → **Sub-nav.** Real `<a href>` in a `<nav aria-label="Section">`, server navigation, `aria-current="page"`. Not tabs.
2. **Do the items show mutually exclusive views of one object, content already loaded or cheap, page identity unchanged?** → **Tabs.** `role="tablist"/"tab"/"tabpanel"`, roving tabindex, arrow-key navigation, `aria-selected`. Still deep-linkable via hash or query — "tabs" is not an excuse for un-linkable state.
3. **Do the items change a *parameter* of one unchanging view (sort, units, date range, list-vs-grid)?** → **Segmented control.** A `radiogroup`, visually one pill-divided control, 2–5 short labels. Not tabs — there is no panel to associate.

**Common error** Building product sections ("Overview / Specs / Reviews") as a `tablist` when each is a crawlable URL with inbound links: you take on the heavy keyboard contract, lose indexability, and hide two-thirds of the content from find-in-page.
**Scent** Sub-nav highest (real destinations), tabs medium, segmented lowest (it's a setting, not a place).
**Touch** Scrollable strips need a visible overflow affordance (a fade edge) and `scroll-snap-type: inline mandatory`. Never a horizontally scrolling strip with no cue.
**Spacing** Tab `var(--pad-block-md) var(--pad-inline-md)`, `min-height: var(--tap-min)`; strip `gap: var(--gap-related)`; rule `--border-subtle` with the active indicator `--border-accent`, `transition: var(--motion-enter)`. Segmented: outer `padding: var(--pad-block-xs)`, `background: var(--bg-sunken)`, `--radius-full`, segments `gap: var(--space-0)`.

### 2.12 In-page anchor nav + scroll-spy
**Is** A TOC beside long content that highlights the section in view and scrolls to sections on click.
**Wins** Documents over ~3 viewports with real headings — docs, long-form, legal text, changelogs. It turns an unbounded scroll into a bounded map. **Fails** Short pages, and pages whose headings aren't parallel (a TOC of vague headings advertises a badly structured document).
**The rootMargin trick** Naive scroll-spy (`scroll` listener + `offsetTop`) is slow and flickers. Use `IntersectionObserver` with a **collapsed root** — a thin band near the top of the viewport, just below the sticky header: `rootMargin: "-${navOffset}px 0px -75% 0px"`. A section is current exactly while its box intersects that band; switching becomes crisp and cheap. Three details make it feel right: (1) **never clear to nothing** — keep the last active id between sections and during fast scroll; (2) **handle the bottom** — a final section shorter than the band never reaches it, so force the last entry active when scrolled to the document bottom; (3) **pick the topmost** when several intersect, by document order.
**Scent** High — it shows the whole document's shape at a glance.
**Keyboard** Plain links. Add `scroll-padding-top` on `:root` and `scroll-margin-top` on headings so a clicked anchor doesn't land under the header.
**Touch** Usually collapses to a `<details>` "On this page" above the content; keep it, it's the only map on a phone.
**A11y** `<nav aria-label="On this page">`; `aria-current="true"` on the active link (pick `"true"` or `"location"` and be consistent). Headings stay real `<h2>/<h3>` — the TOC mirrors the outline, it doesn't replace it. Do not announce scroll-spy changes in a live region; it's ambient state, not an event.
**Build** Code: `navigation-code.md` §4.
**Spacing** Items `gap: var(--gap-tight)`; nested level indented `var(--pad-inline-md)`; active marker a `--stroke-thick` left rule in `--border-accent` against `--border-subtle`; `--type-ui`, `--fg-muted` → `--fg-default` when active.

### 2.13 Pagination vs. infinite scroll vs. load-more

| | Pagination | Infinite scroll | Load more |
|---|---|---|---|
| Footer reachable | Yes | **No** | Yes |
| Back-button return | Free (URL) | Hard | Moderate |
| Sense of progress | Explicit | None | Explicit |
| Keyboard / AT | Good | Poor | Good |
| Best for | Search, commerce, archives | Feeds with no end state | Galleries, moderate lists |

**The footer-access problem** Infinite scroll makes the footer unreachable — nearing it pushes it away. Since the fat footer holds support, legal, account and secondary nav, infinite scroll quietly deletes a whole navigation surface. If you must use it, relocate that content to a sidebar or header, or stop auto-loading after N pages and switch to a button.
**The back-button / state-restoration problem** User scrolls 8 pages, opens item 87, hits back, lands at the top of page 1. The most-complained-about defect in commerce listings. The fix has three parts, all required: (1) reflect position in the URL as each page boundary passes, with `history.replaceState` — not `pushState`, or you create 40 history entries; (2) set `history.scrollRestoration = 'manual'` and restore scroll yourself *after* the list re-renders, not on `DOMContentLoaded`; (3) persist the loaded pages (sessionStorage or a cache) so returning re-renders pages 1–8 instead of refetching from 1. Can't commit to all three? Use pagination.
**The load-more focus rule** After appending, move focus to the first new item (`tabindex="-1"`), or keep focus on the button and announce "20 more results, 80 of 240" politely. Doing neither strands keyboard users at the bottom of a list that silently grew.
**A11y** Pagination is `<nav aria-label="Pagination"><ol>` with `aria-current="page"` on the current number and real `?page=` links — not buttons.
**Spacing** Row `gap: var(--gap-tight)`; each control `min-inline-size: var(--tap-min); min-height: var(--tap-min)`; `var(--gap-distinct)` above.

### 2.14 Stepper / wizard
**Is** A linear multi-step flow with a visible progress indicator — checkout, onboarding, long forms.
**Wins** Genuinely sequential tasks where later steps depend on earlier ones, or where one page would intimidate. The indicator's real job is to **bound the commitment**: "3 steps" converts better than an unknown number. **Fails** Independent steps (use one page with sections) and flows under 3 steps.
**Scent** Moderate — it shows how far, rarely what's inside. Name the steps; "Step 2 of 4" alone tells nobody what's coming.
**Keyboard** Backward navigation always available; forward to visited steps allowed. Never lose entered data on back. Validate on step submit, not per keystroke.
**Touch** Indicator dot ≥24px with the hit area padded to `--tap-min`; on phones collapse to "Step 2 of 4 · Shipping" plus a progress bar.
**A11y** `<nav aria-label="Progress"><ol>`; current step `aria-current="step"`; completed steps are links, future steps plain text or disabled — state conveyed by more than color. On step change move focus to the new step's heading (`tabindex="-1"`); a visual-only change is invisible to AT.
**Build** Put the step in the URL so refresh doesn't restart the flow.
**Spacing** Row `gap: var(--gap-related)`; connector `--border-subtle`, completed `--border-accent`; `var(--gap-separate)` below the indicator.

### 2.15 Footer as navigation
**Is** The "fat footer": a multi-column link directory at the bottom of every page.
**Wins** Always, on content sites. A user who reaches the bottom has either finished or failed; both states want a next destination. It is also the correct home for the long tail of links that must exist and must not clutter the header.
**What belongs** A condensed sitemap of top sections (**the same labels as the header** — different words for one destination read as two places); support and contact; legal (privacy, terms, accessibility statement, cookie settings); account/auth; company (about, careers, press); locale switcher; social; copyright. **Not**: the primary CTA's only home, or navigation that appears nowhere else.
**How many** 4–6 columns, ≤8 links each, with real column headings. Past that it's a wall, not a directory.
**Scent** Good — heading + link text, no interaction needed. **Keyboard** Plain links; it's the last landmark, so skip-links matter more, not less.
**Touch** Columns become accordions, but headings stay visible so the structure is still legible collapsed.
**A11y** `<footer><nav aria-label="Footer">`, each column a `<ul>` bound to its heading with `aria-labelledby`.
**Spacing** Columns `gap: var(--gap-distinct)` across, `var(--gap-separate)` stacked; links `gap: var(--gap-related)`; `var(--space-section)` above the footer, `var(--space-block)` below; top rule `--border-subtle`.

### 2.16 Search as navigation
**Is** A query input as a primary means of traversal rather than a utility.
**When it should be primary** Catalogs over roughly 1 000 items; known-item goals (part number, error message, API name); content that doesn't decompose into a clean taxonomy. On docs and large commerce, search is the most-used nav control on the site — give it a persistent field, not an icon that expands. **When secondary** Small sites and exploration-led sites; a search box on a 12-page site signals that the navigation failed.
**Scent** None until typed, then the best available — it reflects the corpus's actual vocabulary back.
**Keyboard** Autocomplete is a combobox (see §2.8). `/` or `⌘K` to focus is a welcome convention; don't steal `/` while focus is in a text field.
**Touch** Input ≥ `--tap-min`; don't auto-zoom (input font-size ≥ `--text-base` on iOS).
**A11y** `role="search"` landmark (or `<search>`). Real `<label>`, visually hidden if you must — a placeholder is not a label. Announce result counts politely.
**Zero-result design** A zero-result page is a navigation problem and never a dead end. It must contain: (1) the query echoed in a focused, selected, editable input; (2) a spelling suggestion — *suggest*, never silently substitute; (3) **relaxed results**: drop the least-specific term and label it ("No results for *X Y Z*. Showing results for *X Y*."); (4) popular categories or top destinations as a browse escape hatch; (5) a human escape hatch — contact/support.
**Build** Show recent and popular queries on focus; add a scope selector when the corpus is heterogeneous.
**Spacing** Input `var(--pad-block-md) var(--pad-inline-md)`, icon→text `var(--gap-fused)`; suggestion rows `min-height: var(--tap-min)`; panel `--bg-raised` / `--elevation-overlay` / `--z-dropdown`.

### 2.17 Progressive disclosure containers
**Is** Four containers, one decision rule each. The rule is about **what the content costs the user**, not how it looks.

| Container | Use when | Don't when |
|---|---|---|
| **Disclosure** (`<details>`, "Show advanced") | One optional detail attached to one thing; most users never need it | The content is essential to the decision on the page |
| **Accordion** (a set of disclosures) | Several peer sections, comparable in kind, of which a user wants one or two — FAQs, spec groups, filter groups | It's short enough to just show; or users need to *compare* sections (they can't, if only one opens) |
| **Drawer** (edge panel) | A secondary task that benefits from the page staying visible and its context intact — filters, item preview, settings | The task is the primary content of a page (give it a URL) |
| **Modal** | The flow genuinely cannot continue until answered, or a destructive action needs confirmation | Anything else |

**The modal test** Ask "what happens if the user ignores this?" If the answer is "nothing", it is not a modal. Modals stop the world; that cost is justified only when stopping the world is the point. A modal that exists because there was nowhere to put something is an IA failure wearing a scrim.
**Accordion specifics** Header is `<h3><button aria-expanded aria-controls>…</button></h3>` — the heading gives AT users the outline, the button gives them the control. Allow multiple open unless the content is genuinely exclusive. Never trap the only copy of critical content (pricing, shipping) inside a collapsed panel: collapsed content is found less often and find-in-page may not reach it.
**Keyboard** `Enter`/`Space` toggles; focus stays on the header (do **not** move it into the panel — the user opened it to read, not to type). **Touch** Header `min-height: var(--tap-min)`; the whole header row is the target, not just the chevron.
**Spacing** Header `var(--pad-block-md) var(--pad-inline-md)`; panel `padding: var(--pad-well)`; rows separated by a `--border-subtle` rule, not a gap; expansion `var(--motion-expand)` on `grid-template-rows: 0fr → 1fr` (the only reliable height-auto animation).

---

## 3. Cross-cutting rules

**Information scent: labels beat clever names.** A nav label is a promise about what's behind it. "Solutions", "Discover", "Explore", "Platform" promise nothing — users can't predict the destination, so they click everything or leave. Use the words users already say. Test: show the bar to someone outside the project and ask what each item leads to; anything they get wrong is a broken label, no matter how much the brand likes it. Label length is not the enemy — "Pricing & Plans" outperforms "Value".

**The "you are here" problem.** Users who can't locate themselves can't navigate. Solve it *redundantly* — at least three of these on every page:
- `aria-current="page"` on the active link (`"step"`, `"location"`, `"true"` for other cases). This is the machine-readable answer and it is not optional.
- A **visual state that is not color alone** — weight change, filled indicator, background pill. Color-only active states fail for ~8% of men, for high-contrast and forced-colors modes, and in print.
- A **breadcrumb** on anything ≥3 levels deep.
- The `<title>` — the first thing a screen reader announces after navigation, and the tab label. `Running Shoes — Women's — Acme` beats `Acme`.
- The **h1**, matching the nav label that got the user here. Divergence reads as a wrong turn.

**Focus management when nav opens and closes.** The full contract:
- **Open, modal** (drawer, palette): move focus into the container — to its heading with `tabindex="-1"` (preferred; the name gets announced) or the close button. Trap `Tab`. Make everything else `inert`, or use `<dialog>.showModal()`, which does it for you. `Escape` closes.
- **Open, non-modal** (dropdown, mega menu, popover): **no trap**. Focus may move to the panel's first item (click-opened) or stay on the trigger (hover-opened). `Tab` out closes and continues naturally. `Escape` closes and returns focus to the trigger.
- **Close, always:** return focus to the opener with `focus({ preventScroll: true })`. If it no longer exists, focus its nearest surviving ancestor container — **never `<body>`**, which sends screen-reader users back to the top of the page. This is the single most common focus bug in navigation.
- **Never** move focus on hover, and never on scroll.

**Skip links, done properly.** First focusable element in the DOM, before the header. `<a href="#main">Skip to content</a>` targeting `<main id="main" tabindex="-1">` — without `tabindex="-1"` on the target, several browsers move the *scroll* but not the *focus*, and the next `Tab` restarts from the top. Hide it with `transform`/`clip-path`, never `display: none` or `visibility: hidden`, which remove it from the tab order entirely. On `:focus-visible` it must be visible *above* the header: `z-index: calc(var(--z-sticky) + 1)`. Add `scroll-padding-top` so the target clears a fixed header. Add a second link to skip any long repeated list (search results, a sidebar).

**Mobile-first ordering.** Design the phone nav first: it forces the prioritisation you then carry upward. A desktop-first nav invariably has nine items and no ranking. The rule: DOM order *is* the mobile order *is* the accessibility order. Visual reordering on desktop uses `order`/grid placement, but never across a visual group boundary — tab order jumps and keyboard users lose the plot.

**Item ordering and serial-position effects.** Recall and click-through peak at the **first** and **last** positions and trough in the middle. So: highest-value destination first (after the logo); conversion action last, at the right end, visually differentiated; items you must carry but nobody prioritises go in the middle. Don't order by org chart. Don't alphabetise a 6-item bar — alphabetical carries no scent below about 20 items, where it starts working as a lookup aid instead.

**When a menu needs grouping.** Eight. Up to ~7 the eye chunks a row or column as one unit; past that it degrades into linear reading. At 8+, introduce groups with real headings (mega-menu column heading, sidebar section label). Groups obey the same limit: more than 7 groups means you need a level, not more labels.

**The URL is navigation state.** Decide per piece:
- **URL path:** pages, sections, items, wizard steps, paginated position.
- **URL query:** filters, sort, search query, view mode, and any tab whose panel someone would link to. This is what makes a result set shareable and the back button correct.
- **Not in the URL:** transient UI — which mega menu is hovering open; scroll position (that's history state); whether the sidebar is collapsed (that's a preference — `localStorage`).
- A modal that is a **destination** gets a URL (photo viewer, detail overlay); a modal that is a **confirmation** does not.
- **Back closes the topmost layer** that was pushed to history, and only that one. If you `pushState` on drawer open, you must pop it when closing by button or `Escape`, or the user accumulates phantom history entries.

**Progressive enhancement — no JS, and before hydration.** The primary nav is real `<a href>` elements in the HTML, always: a client-rendered nav is invisible to crawlers, broken during hydration, and gone when a script fails. Dropdowns degrade — `<details>` works with zero JS, `popovertarget` works declaratively, a hand-rolled JS menu degrades to nothing, so render its submenu links **visible by default** and let JS collapse them on boot. The scroll-aware header defaults to *visible*; hiding is the enhancement. The drawer's fallback is `:target` (hamburger as `<a href="#nav">`) or the nav rendered inline. The command palette is JS-only and therefore never the only path. And avoid nav that changes height when JS boots — that is a CLS hit at the very top of the page.

---

## 4. Spacing spec

**The tap-target rule.** Every interactive nav element gets `min-height: var(--tap-min)`, and icon-only controls also `min-inline-size: var(--tap-min)`. 44px is a floor, not a target. If the visual design wants a 32px pill, the *pill* is 32px and the *hit area* is extended — never the reverse:

```css
.nav__link { position: relative; min-height: var(--tap-min); }
.nav__link::after {                       /* extend the hit box past the visual box */
  content: ""; position: absolute; inset-inline: 0;
  inset-block: calc((var(--tap-min) - 100%) / -2);
}
```

**Item padding drives bar height — never the reverse.** Don't set `height: 64px`. Set the item box and let the bar grow:

```css
.nav {
  --nav-pad-block: var(--pad-block-md);          /* Tier 3, sourced from Tier 2 */
  padding-block: var(--nav-pad-block);
  padding-inline: var(--gutter-page);
}
.nav__link { padding: var(--pad-block-md) var(--pad-inline-md); min-height: var(--tap-min); }
```

Bar height is then `--tap-min + 2 × --pad-block-md` ≈ 68px at default density, and it compacts automatically when an admin shell sets `data-density="compact"` (Law 7). For ≤56px on phones, drop the *bar's* own `padding-block` to `--pad-block-sm` at small viewports; the item keeps `--tap-min`.

**Gaps between items vs. groups — two values, never one.**

```css
.nav          { display: flex; align-items: center; gap: var(--gap-separate); }  /* zones */
.nav__list    { display: flex; align-items: center; gap: var(--gap-related);  }  /* items */
.nav__actions { display: flex; align-items: center; gap: var(--gap-tight);    }  /* actions */
```

If items and groups share a gap the grouping disappears and you're back to a flat row of twelve. The ratio that reads as "two groups" is about 2:1 — `--gap-separate` against `--gap-related`. Children set **no margins** (Law 2).

**The optical alignment problem beside a logo.** A text link has invisible side bearing: its padding box starts before its glyphs do. A logo mark has none — its bounding box is its ink. So a mathematically equal gap between logo and first link *looks* too large. Correct by subtracting the link's inline padding from the zone gap, as a Tier-3 token in the component's own file:

```css
.nav {
  --nav-gap-after-logo: calc(var(--gap-separate) - var(--pad-inline-md));
  column-gap: var(--nav-gap-after-logo);
}
.nav__actions { padding-inline-end: calc(var(--gutter-page) - var(--pad-inline-md)); }
```

Same problem at the right edge: the last item's trailing padding makes the bar look over-guttered, so pull the actions zone in by the same amount. Verify by dropping a vertical rule from the content column's edge through the bar — it should touch **glyphs and logo ink**, not padding boxes.

**Where a sidebar item's left edge aligns.** Three edges are in play: the panel's text gutter, the selected pill's edge, and the content column. The rule: (1) the item's **text** aligns with the section label above it and with the panel's text gutter; (2) the **selected pill** bleeds outward from that text by `--pad-inline-md`, so the panel's own `padding-inline` must be at least `--pad-inline-sm`, or the pill touches the panel edge and reads as a rendering error; (3) the panel's outer edge sits one `--gutter-page` from the viewport, and the gap to the content column is `--gap-distinct` — they are unrelated blocks and should read that way; (4) nested items indent by exactly `var(--pad-inline-md)` per level, applied as the *parent list's* `padding-inline-start`. Two levels is the legible maximum; at three, switch to three-pane.

```css
.sidebar          { padding-inline: var(--pad-inline-sm); }
.sidebar__nav     { display: grid; gap: var(--gap-separate); }   /* between groups */
.sidebar__group   { display: grid; gap: 0; }                     /* rows are contiguous */
.sidebar__link    { padding: var(--pad-block-sm) var(--pad-inline-md);
                    min-height: var(--tap-min); border-radius: var(--radius-md); }
.sidebar__link[aria-current="page"] { background: var(--bg-selected); color: var(--fg-accent); }
.sidebar__sublist { padding-inline-start: var(--pad-inline-md); }
```

**Publish the header height once**, so anchors, sticky sidebars and scroll-spy all read the same number. Register it as a `<length>`, so that script reads it back in pixels. Unregistered, it reads back as its `calc()` text:

```css
@property --nav-offset { syntax: '<length>'; inherits: true; initial-value: 0px; }
:root {
  --nav-offset: calc(var(--tap-min) + var(--pad-block-md) * 2);
  scroll-padding-top: calc(var(--nav-offset) + var(--gap-grouped));
}
@layer base {
  :is(h2, h3, h4)[id] { scroll-margin-top: calc(var(--nav-offset) + var(--gap-grouped)); }
}
```

---

## 5. Failure gallery

Each of these is a defect, not a preference.

- **Hover-only menus on touch.** Touch has no hover. The first tap synthesises hover *and* click, so the user navigates before reading the panel — or gets a panel they can't dismiss.
- **Nav that reflows on scroll.** Shrinking the header or swapping the logo on scroll reflows the document every frame and moves targets under the user's finger. Animate `transform` and `opacity`, or nothing.
- **Hamburger on desktop.** No space constraint justifies hiding navigation at 1440px. It measurably reduces use of what's inside, and it's usually visual minimalism dressed up as responsive design.
- **More than 7 undifferentiated top-level items.** Past the chunking limit the row becomes linear reading; scan time rises and users pick the first plausible item instead of the right one.
- **`<div onclick>` instead of `<a href>`.** Not focusable, not announced as a link, no middle-click, no open-in-new-tab, no right-click, no status-bar URL, invisible to crawlers, dead with JS off. There is no upside. If it navigates, it is an anchor.
- **Focus lost on menu close.** Focus falls to `<body>` and the next `Tab` restarts at the top of the page. Open-then-close teleports a keyboard user to the beginning of the document.
- **Sticky headers taller than 64px on mobile.** On a 780px viewport that's 8%+ permanently gone before browser chrome. Use scroll-aware and keep the bar ≤56px.
- **Animated nav that blocks interaction until it finishes.** A 400ms drawer that ignores clicks and keys until `transitionend` drops every fast user's first action. The target is interactive on frame one; the animation is decoration over an already-live UI.
- **Icon-only nav without labels.** Outside about six universal glyphs, icons are guesses. A tooltip is not a label: it doesn't exist on touch and it arrives after the hesitation.
- **Two labels for one destination.** "Pricing" in the header and "Plans & Pricing" in the footer read as two different pages and quietly erode trust in the whole IA.
- **Active state conveyed by color alone.** Fails color-vision deficiency, high-contrast and forced-colors modes. Add weight, a rule, or a filled state.
- **Nav rendered client-side only.** Invisible to crawlers, absent during hydration, gone on script error.
- **`role="menu"` on a list of links.** Strips link semantics, hides items from the AT links rotor, and commits you to a keyboard contract you did not implement.
- **Filters or tabs with no URL.** Unshareable, unbookmarkable, and the back button does the wrong thing. State the user can see is state the URL should carry.

---

---

**Ship checklist (Law 9).** Tab the whole nav with no mouse. Run it with a screen reader and confirm links announce as links. Test every hover behaviour on a real touch device. Confirm the active page is identified by `aria-current` **and** a non-color visual state. Confirm every filter, tab and page is in the URL. Disable JS and confirm every destination is still reachable. Scroll with a trackpad and confirm zero jitter. Then view the whole bar at `data-density="compact"` and `data-theme="dark"` — without editing a single component rule.
