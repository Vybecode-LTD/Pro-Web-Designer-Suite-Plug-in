# Accessibility Testing — the procedure before anything ships

How to check what `accessibility.md` specifies, by hand and by machine. Run the passes in this order: steps 1–3 find most of what matters and need no tooling. The criteria, the focus contract and the key maps are in `accessibility.md`; how a runner automates these passes on every commit is in `a11y-audit-runner`.

## Contents

1. [Keyboard-only pass](#1-keyboard-only-pass)
2. [Zoom and reflow](#2-zoom-and-reflow)
3. [Forced colors / Windows High Contrast](#3-forced-colors--windows-high-contrast)
4. [Screen reader smoke test](#4-screen-reader-smoke-test)
5. [Automated tools — and what they cannot do](#5-automated-tools--and-what-they-cannot-do)
6. [Regression](#6-regression)

---

## 1. Keyboard-only pass

Unplug the mouse. Then, on every page and every flow:

- Tab from the top. **The first stop is the skip link**; activate it and confirm focus lands in `<main>`.
- Tab through every control. The ring is **always visible** and **never obscured** (2.4.11) by sticky chrome. Tab order matches visual order.
- Operate every widget with the key map in `accessibility.md` §4.
- Open and close every dialog, menu and drawer. `Esc` works. **Focus returns to the trigger.**
- Tab backwards through the whole page with `Shift+Tab`. Backwards order is where broken focus management hides.
- Tab into and back out of every third-party embed.
- Submit every form with errors and confirm focus goes somewhere useful.

## 2. Zoom and reflow

- **200% browser zoom** (1.4.4): no clipped text, no overlapping content, nothing requiring horizontal scroll to read a line.
- **400% zoom on a 1280×1024 window** (1.4.10) — equivalent to a 320px-wide viewport. No two-dimensional scrolling. Content reflows to one column; nothing is hidden and no function is lost. Sticky headers are the usual casualty: at 400% a 64px header can eat half the viewport, so collapse it.
- **Text spacing** (1.4.12): inject `line-height: 1.5 !important; letter-spacing: 0.12em !important; word-spacing: 0.16em !important;` on `*` and `margin-block-end: 2em !important` on `p`. Nothing clips or overlaps. Fixed-height buttons and cards fail here.

## 3. Forced colors / Windows High Contrast

This is where token-based color systems break, and they break in predictable ways. Emulate in DevTools (Rendering → Emulate CSS media feature `forced-colors: active`) and verify on real Windows HCM before launch.

What breaks, and why:

| Symptom | Cause | Fix |
|---|---|---|
| **The focus ring disappears** | `box-shadow` is discarded in forced-colors mode, so a ring drawn only with `box-shadow` vanishes | Draw the ring as an `outline` (`accessibility.md` §3). Its color is forced to a system color and it stays |
| **All elevation vanishes** | Same — shadows are gone, so a "raised" card is flush with the page | `@media (forced-colors: active) { .card { border: var(--stroke-default) solid CanvasText; } }` |
| **Filled and ghost buttons look identical** | Both backgrounds are forced to `ButtonFace`. Anything distinguished only by background color collapses | Add a border, or `forced-color-adjust: none` on the one element that must keep its fill (and then guarantee its contrast yourself) |
| **Selected / active / error states disappear** | `--bg-selected`, `--bg-hover`, `--bg-active` and status fills are all forced to the same color | Pair every color-carried state with a border, an underline, an icon or `Highlight`/`HighlightText` |
| **The modal scrim is gone** | Translucent overlays are forced opaque or dropped; the dialog floats with no separation | Give the dialog a `CanvasText` border in the media query |
| **Icons turn invisible or the wrong color** | CSS `fill`/`stroke` are forced; SVG **presentation attributes** (`fill="#666"` in the markup) are **not** | Always `fill="currentColor"` on inline SVG, so the icon follows the forced text color |
| **A transparent border suddenly appears** | `border-color: transparent` is forced to a visible system color | Intentional in the focus-ring trick; a bug everywhere else. Use `border-style: none`, not a transparent border, for spacing hacks |

Use system color keywords **in pairs** — `Canvas`/`CanvasText`, `ButtonFace`/`ButtonText`, `Field`/`FieldText`, `Highlight`/`HighlightText`, `LinkText`, `GrayText` for disabled. Never guess which is light. Use `forced-color-adjust: none` sparingly and only where color *is* the content (a color swatch, a chart key, a brand gradient) — it opts you out of the user's entire accommodation.

## 4. Screen reader smoke test

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

## 5. Automated tools — and what they cannot do

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

## 6. Regression

Put `axe-core` in the component test suite (`jest-axe`, `cypress-axe`, `@axe-core/playwright`) and assert zero violations per component. Add a keyboard-navigation test for every custom widget. Accessibility regressions are cheap to prevent and expensive to find later.
