# Navigation Code — the four most-often-broken patterns

Working code for the navigation patterns that break most often when built by hand. Choose the pattern first in `navigation-patterns.md` (§1 and §2); this file is how to build it.

## Contents

1. [Scroll-aware header](#1-scroll-aware-header)
2. [Mega menu with safe triangle + keyboard](#2-mega-menu-with-safe-triangle--keyboard)
3. [Off-canvas drawer with focus management and `inert`](#3-off-canvas-drawer-with-focus-management-and-inert)
4. [Scroll-spy with IntersectionObserver](#4-scroll-spy-with-intersectionobserver)

---

All CSS reads Tier-2 tokens only; component-specific values are Tier-3 variables declared in the component's own block (Laws 1 and 4), inside `@layer components` (Law 5).

## 1. Scroll-aware header

```html
<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header" data-scroll-aware>
  <nav class="nav" aria-label="Main">
    <a class="nav__brand" href="/">Acme</a>
    <ul class="nav__list">
      <li><a href="/product" aria-current="page">Product</a></li>
      <li><a href="/pricing">Pricing</a></li>
    </ul>
    <div class="nav__actions"><a class="btn" href="/signup">Start free</a></div>
  </nav>
</header>
<main id="main" tabindex="-1">…</main>
```

```css
@layer components {
  .site-header {
    position: fixed; inset-block-start: 0; inset-inline: 0;
    z-index: var(--z-sticky);
    background: var(--bg-surface);
    border-block-end: var(--stroke-hairline) solid var(--border-subtle);
    transition: transform var(--motion-enter);      /* only transform is animated */
    will-change: transform;
  }
  .site-header[data-hidden="true"] {
    transform: translateY(-100%);
    transition: transform var(--motion-exit);
  }
  /* The page reserves the header's height: the base rule below. A component
     styles itself, never <body>. */

  /* The skip link is the starter's .skip-link (layout.css), not a second copy
     here: one class, one home. Its --z-toast sits above --z-sticky, so it
     clears this header. */
}
```

The fixed header leaves the flow, so the page reserves its height. That rule is the page's, in `base`:

```css
@layer base {
  body { padding-block-start: var(--nav-offset); }   /* navigation-patterns.md §4 publishes --nav-offset */
}
```

```js
// Hysteresis is what separates this from the jittery version.
const header = document.querySelector('[data-scroll-aware]');
const HYSTERESIS = 12;            // px of committed travel before we believe a flip
let lastY = scrollY, anchorY = scrollY, direction = 'up', hidden = false, ticking = false;

const setHidden = (next) => {
  if (next === hidden) return;    // never touch the DOM for a no-op
  hidden = next;
  header.dataset.hidden = String(next);
};

function update() {
  ticking = false;
  const y = Math.max(0, scrollY);
  const delta = y - lastY;
  lastY = y;
  if (delta === 0) return;

  const next = delta > 0 ? 'down' : 'up';
  if (next !== direction) { direction = next; anchorY = y; return; }  // await commitment
  if (Math.abs(y - anchorY) < HYSTERESIS) return;                     // inside the deadband

  const inRevealZone = y <= header.offsetHeight;   // always visible at the top of the page
  const menuOpen     = header.querySelector('[aria-expanded="true"]') !== null;
  const focusInside  = header.contains(document.activeElement);
  setHidden(!(inRevealZone || direction === 'up' || menuOpen || focusInside));
}

addEventListener('scroll', () => {
  if (!ticking) { ticking = true; requestAnimationFrame(update); }
}, { passive: true });

header.addEventListener('focusin', () => setHidden(false));  // never hide what's being tabbed
```

## 2. Mega menu with safe triangle + keyboard

```html
<nav class="nav" aria-label="Main">
  <ul class="nav__list" data-megamenu>
    <li class="nav__item">
      <button type="button" class="nav__trigger" id="trigger-shoes"
              aria-expanded="false" aria-controls="panel-shoes">Shoes</button>
      <div class="megamenu" id="panel-shoes" aria-labelledby="trigger-shoes" hidden>
        <div class="megamenu__col">
          <p class="megamenu__heading" id="mm-run">Running</p>
          <ul class="megamenu__list" aria-labelledby="mm-run">
            <li><a class="megamenu__link" href="/shoes/running">All running shoes</a></li>
            <li><a class="megamenu__link" href="/shoes/trail">Trail</a></li>
          </ul>
        </div>
      </div>
    </li>
  </ul>
</nav>
```

Note what is absent: no `role="menu"`, no `role="menuitem"`, no `aria-haspopup="menu"`. The trigger is a disclosure button and the panel is a set of labelled link lists — the one contract screen readers actually handle well.

```css
@layer components {
  .megamenu {
    position: absolute; inset-inline: var(--gutter-page); inset-block-start: 100%;
    z-index: var(--z-dropdown);
    display: grid; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
    gap: var(--gap-separate);
    padding: var(--pad-card);
    background: var(--bg-raised);
    border: var(--stroke-hairline) solid var(--border-subtle);
    border-radius: var(--radius-xl);
    box-shadow: var(--elevation-overlay);
  }
  .megamenu[hidden]     { display: none; }
  .megamenu__col        { display: grid; gap: var(--gap-tight); }
  .megamenu__list       { display: grid; gap: var(--gap-related); }
  .megamenu__heading    { font: var(--type-label); color: var(--fg-muted);
                          letter-spacing: var(--tracking-caps); text-transform: uppercase; }
  .megamenu__link       { display: flex; align-items: center; min-height: var(--tap-min);
                          padding-inline: var(--pad-inline-xs); border-radius: var(--radius-sm); }
  .megamenu__link:hover { background: var(--bg-hover); }
}
```

```js
const bar = document.querySelector('[data-megamenu]');
const items = [...bar.querySelectorAll('.nav__item')].map(li => ({
  li, trigger: li.querySelector('.nav__trigger'), panel: li.querySelector('.megamenu'),
}));
let open = null, openedByHover = false, lastPoint = null, pending = null;
const SAFE_MAX_MS = 300;   // cap, so a pointer drifting slowly inside the triangle still resolves
const LOOK_MS = 60;        // how often a deferred switch looks again

function show(item, byHover = false) {
  if (open === item) return;
  if (open) hide(open);
  open = item;
  openedByHover = byHover;
  item.panel.hidden = false;
  item.trigger.setAttribute('aria-expanded', 'true');
}
function hide(item) {
  item.panel.hidden = true;
  item.trigger.setAttribute('aria-expanded', 'false');
  if (open === item) open = null;
}

/* Safe triangle: apex = where the pointer was, base = the open panel's LEADING edge.
   Panel below a bar -> its top edge. Sidebar flyout -> swap to the two left corners. */
const side = (p, a, b) => (p.x - b.x) * (a.y - b.y) - (a.x - b.x) * (p.y - b.y);
function inTriangle(p, a, b, c) {
  const d1 = side(p, a, b), d2 = side(p, b, c), d3 = side(p, c, a);
  return !((d1 < 0 || d2 < 0 || d3 < 0) && (d1 > 0 || d2 > 0 || d3 > 0));
}
function headingIntoPanel(from, to) {
  if (!open || !from || !to || (from.x === to.x && from.y === to.y)) return false;  // a still pointer is not heading anywhere
  const r = open.panel.getBoundingClientRect();
  return from.y < r.top &&
    inTriangle(to, from, { x: r.left, y: r.top }, { x: r.right, y: r.top });
}

/* Hovering onto another trigger switches to it, unless the pointer is on its way
   into the open panel. Each look re-tests the triangle against the pointer's newest
   position, up to the cap, and a pointer that has moved on is never switched to. */
function hoverTo(item, from, since) {
  clearTimeout(pending);
  const to = lastPoint;
  if (open && open !== item && headingIntoPanel(from, to) &&
      performance.now() - since < SAFE_MAX_MS) {
    pending = setTimeout(() => hoverTo(item, to, since), LOOK_MS);
    return;
  }
  if (item.li.matches(':hover')) show(item, true);
}

bar.addEventListener('pointermove', (e) => {
  if (e.pointerType === 'mouse') lastPoint = { x: e.clientX, y: e.clientY };
}, { passive: true });

items.forEach(item => {
  item.li.addEventListener('pointerenter', (e) => {
    if (e.pointerType !== 'mouse') return;               // touch and pen never hover
    const from = lastPoint;
    lastPoint = { x: e.clientX, y: e.clientY };
    hoverTo(item, from, performance.now());
  });
  // Click/keyboard open: identical behaviour on touch, where hover never fires.
  // Clicking a trigger whose panel hover opened keeps the panel open: people
  // click what they are pointing at.
  item.trigger.addEventListener('click', () => {
    if (open !== item) show(item);
    else if (openedByHover) openedByHover = false;
    else hide(item);
  });
});

bar.addEventListener('pointerleave', (e) => {
  if (e.pointerType !== 'mouse') return;
  clearTimeout(pending);
  if (open && openedByHover && !open.li.contains(document.activeElement)) hide(open);
});
document.addEventListener('click', (e) => {              // a clicked-open panel closes on
  if (open && !open.li.contains(e.target)) hide(open);  // a click anywhere else
});

// Non-modal contract: Escape returns focus, Tab out closes. No trap, ever.
bar.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && open) { const t = open.trigger; hide(open); t.focus(); }
});
bar.addEventListener('focusout', (e) => {
  if (open && !open.li.contains(e.relatedTarget)) hide(open);
});
```

## 3. Off-canvas drawer with focus management and `inert`

`<dialog>.showModal()` gives you the top layer, backdrop, `Escape`, focus containment and background inertness from the platform — correctly, with no trap code to get wrong. Baseline since 2022. Hand-roll with the `inert` attribute (Baseline 2023) only when the drawer must be **non-modal**.

```html
<button type="button" id="nav-toggle" aria-expanded="false" aria-controls="nav-drawer">
  <svg aria-hidden="true" …></svg> Menu
</button>

<dialog id="nav-drawer" class="drawer" aria-labelledby="drawer-title">
  <h2 id="drawer-title" tabindex="-1">Navigation</h2>
  <button type="button" data-close>Close</button>
  <nav aria-label="Main"><ul class="drawer__list"><li><a class="drawer__link" href="/">Home</a></li>…</ul></nav>
</dialog>
```

```css
@layer components {
  .drawer {
    --drawer-width: min(88vw, var(--width-form));  /* Tier 3: never wider than the forms it holds */
    inline-size: var(--drawer-width); max-inline-size: none;
    block-size: 100dvh; max-block-size: none;
    margin: 0 0 0 auto;                          /* right-edge drawer */
    padding: var(--pad-card);
    border: 0; border-radius: 0;
    background: var(--bg-surface); color: var(--fg-default);
    box-shadow: var(--elevation-modal);
    overflow-y: auto; overscroll-behavior: contain;
    translate: 100% 0;
    transition: translate var(--motion-expand),
                display var(--motion-expand) allow-discrete,
                overlay var(--motion-expand) allow-discrete;
  }
  .drawer[open] { translate: 0 0; }
  @starting-style { .drawer[open] { translate: 100% 0; } }

  .drawer::backdrop        { background: var(--bg-scrim); opacity: 0;
                             transition: opacity var(--motion-enter) allow-discrete; }
  .drawer[open]::backdrop  { opacity: 1; }
  @starting-style { .drawer[open]::backdrop { opacity: 0; } }

  .drawer__list   { display: grid; gap: var(--gap-related); }
  .drawer__link { display: flex; align-items: center; min-height: var(--tap-min);
                  padding: var(--pad-block-md) var(--pad-inline-md);
                  border-radius: var(--radius-md); }
}
```

```js
const toggle = document.getElementById('nav-toggle');
const drawer = document.getElementById('nav-drawer');
const title  = document.getElementById('drawer-title');
let opener = null;

function openDrawer() {
  opener = document.activeElement;
  drawer.showModal();                     // top layer + backdrop + Escape + background inert
  toggle.setAttribute('aria-expanded', 'true');
  document.documentElement.style.overflow = 'hidden';            // body scroll lock
  title.focus({ preventScroll: true });   // heading, not first link: SR announces what opened
}

drawer.addEventListener('close', () => {
  toggle.setAttribute('aria-expanded', 'false');
  document.documentElement.style.overflow = '';
  // Return focus to the opener; fall back to a surviving ancestor — never to <body>.
  ((opener?.isConnected && opener) || toggle).focus({ preventScroll: true });
  opener = null;
});

toggle.addEventListener('click', openDrawer);
drawer.addEventListener('click', (e) => {
  // Light dismiss: <dialog> won't do it. A click on the backdrop targets the
  // dialog, but so does a click in the drawer's own padding, so test where the
  // click landed, not what it landed on.
  const r = drawer.getBoundingClientRect();
  const outside = e.clientX < r.left || e.clientX > r.right ||
                  e.clientY < r.top || e.clientY > r.bottom;
  if (e.target === drawer && outside) drawer.close();
  if (e.target.closest('[data-close], a')) drawer.close();  // SPA nav must close it too,
});                                                   // or focus is stranded in a hidden panel
```

For a genuinely non-modal drawer, skip `<dialog>`, toggle the panel's `hidden`, and leave the background reachable. If you find yourself adding `inert` to the background, the drawer is modal — use `<dialog>`.

## 4. Scroll-spy with IntersectionObserver

```js
// The band: a thin strip just below the sticky header. A heading is "current"
// exactly while its box intersects that strip.
const toc   = document.querySelector('[data-toc]');
const links = new Map([...toc.querySelectorAll('a[href^="#"]')]
                .map(a => [decodeURIComponent(a.hash.slice(1)), a]));
const headings = [...links.keys()].map(id => document.getElementById(id)).filter(Boolean);
// --nav-offset is registered as a <length> (navigation-patterns.md §4), so it
// reads back in pixels.
// Unregistered, it reads back as calc() text, parseFloat() gives NaN, and a
// `|| 64` fallback hides that the band sits in the wrong place.
const navOffset = parseFloat(
  getComputedStyle(document.documentElement).getPropertyValue('--nav-offset'));

const visible = new Set();
let active = null;

function setActive(id) {
  if (!id || id === active) return;
  links.get(active)?.removeAttribute('aria-current');
  links.get(id)?.setAttribute('aria-current', 'true');
  active = id;
}

const observer = new IntersectionObserver((entries) => {
  for (const e of entries) {
    e.isIntersecting ? visible.add(e.target.id) : visible.delete(e.target.id);
  }
  // Rule 3: several can intersect during fast scroll — take the topmost in document order.
  // Rule 1: if nothing intersects, keep the last active id. Never clear to nothing.
  if (visible.size) setActive(headings.find(h => visible.has(h.id))?.id);
}, {
  // Top inset clears the header; bottom inset collapses the root to a ~25vh band.
  rootMargin: `-${navOffset}px 0px -75% 0px`,
  threshold: 0,
});
headings.forEach(h => observer.observe(h));

// Rule 2: the last section is often too short to reach the band. Force it at the bottom.
addEventListener('scroll', () => {
  if (innerHeight + scrollY >= document.documentElement.scrollHeight - 2) {
    setActive(headings.at(-1).id);
  }
}, { passive: true });
```

```css
@layer components {
  .toc {
    position: sticky; inset-block-start: calc(var(--nav-offset) + var(--gap-grouped));
    display: grid; gap: var(--gap-tight);
    max-block-size: calc(100dvh - var(--nav-offset) - var(--gap-distinct));
    overflow-y: auto; overscroll-behavior: contain;
  }
  /* Each link is a .toc__link and each list a .toc__list: the component styles
     its own parts by class, never the elements inside it (Law 2). */
  .toc__link {
    font: var(--type-ui); color: var(--fg-muted);
    padding-block: var(--pad-block-xs); padding-inline-start: var(--pad-inline-sm);
    border-inline-start: var(--stroke-thick) solid var(--border-subtle);
    transition: color var(--motion-hover), border-color var(--motion-hover);
  }
  .toc__link[aria-current] { color: var(--fg-default); border-inline-start-color: var(--border-accent); }
  .toc__list .toc__list    { padding-inline-start: var(--pad-inline-md); }
}
```
