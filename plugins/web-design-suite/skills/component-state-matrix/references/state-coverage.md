# State Coverage

The complete state model, and what each missing state looks like in the wild.

`audit_design.py` proves the *code* is clean. It cannot prove a state exists, because a state that was never written produces no violation — there is nothing there to be wrong. That absence is invisible to a linter and obvious on a proof sheet. This file is what you read the sheet against.

---

## 1. The seven interactive states

Every interactive component implements all seven. Not "supports" — *implements*, visibly, with a token behind it.

| State | Expressed as | Driven by | Must not |
|---|---|---|---|
| default | the root rule | the component's Tier-3 sockets | be the only state anyone designed |
| hover | `:hover:not(:disabled)` | `--bg-hover` | be the only affordance; carry information |
| focus-visible | `:focus-visible` | `--shadow-focus` + `--stroke-focus` | be removed, be thinner than 2px, be clipped |
| active | `:active:not(:disabled)` | `--bg-active` | move layout; be slower than `--dur-instant` |
| disabled | `:disabled` / `[aria-disabled="true"]` | `--bg-disabled`, `--fg-disabled` | be unfocusable if it needs explaining |
| loading | `[data-state="loading"]` + `aria-busy` | `--fg-muted`, `--motion-*` | change the component's size |
| error | `[aria-invalid="true"]` | `--fg-danger`, `--bg-danger` | be carried by colour alone |

State is a **real ARIA attribute where one exists**, `data-state` otherwise, and **never** an `is-*` class. Three reasons, from `style-architecture.md` §8: `data-state` holds one value so two states cannot both be true; `[data-state="x"]` and `.card` are both 0,1,0 so specificity stays flat; and styling the accessibility attribute directly means the announced state and the painted state cannot diverge.

---

### 1.1 default

**Means:** the component at rest, with nothing happening to it.

**Expressed:** the root rule. Nothing to add.

**Token:** the component's own Tier-3 sockets, each defaulting to a Tier-2 role.

**Must not:** be the only state that got design attention. A component whose default is beautiful and whose other six are browser defaults is a component that looks finished in a screenshot and feels broken in a hand.

**Failure signature:** none — it is always present. It is on the sheet as the reference every other row is compared against. If a row looks identical to the default row, that row is the bug.

---

### 1.2 hover

**Means:** a pointing device is over the target. Nothing has been committed.

**Expressed:** `.thing:hover:not(:disabled)`. Guard with `:not(:disabled)` rather than ordering the disabled rule after it — ordering-based resolution breaks the moment somebody inserts a rule in between, and a guard is explicit where order is implicit.

**Token:** `--bg-hover` (a translucent overlay, so it composes over any surface and you never need a per-variant hover colour).

**Must not:**
- Be the only affordance. Touch has no hover and keyboards have no hover. Anything discoverable *only* on hover is undiscoverable to most of your users.
- Carry information. A tooltip that appears on hover and nowhere else is a hidden feature.
- Change the box. A hover that adds a border where there was none shifts everything beside it.

**Failure signature when missing:** the hover row is pixel-identical to the default row. On the sheet that is unmissable; in a browser it reads as "the page is dead".

**The signature that is worse than missing:** the hover row is *identical across variants*. That means `:hover { --btn-bg: var(--bg-hover) }` overwrote the primary variant's `--btn-bg: var(--bg-accent)` instead of composing over it, and your primary button turns pale grey the instant a pointer touches it. The fix is to make hover a layered overlay (`background-image: linear-gradient(var(--bg-hover), var(--bg-hover))`) or to give each variant its own hover socket. **You will not see this by looking at one button.** You see it the moment hover and variant are on the same sheet — which is exactly why the state pass renders states × variants and not states alone.

---

### 1.3 focus-visible

**Means:** the element has keyboard focus and the browser has decided the user needs to see where they are.

**Expressed:** `:focus-visible`, never `:focus`. `:focus` fires on mouse clicks too and produces rings nobody asked for, which is how teams end up with `outline: none` and an inaccessible product.

**Token:** an outline for the ring, and a box-shadow only for the gap (the starter's reset.css does this for every element):

```css
.thing:focus-visible {
  outline: var(--stroke-focus) solid var(--border-focus);
  outline-offset: var(--stroke-focus);
  /* stylelint-disable-next-line declaration-property-value-allowed-list -- the gap ring: a spread of two tokens, as reset.css draws it */
  box-shadow: 0 0 0 var(--stroke-focus) var(--bg-canvas);   /* the gap, not the ring */
}
```

The ring is the `outline`, and that is not a style choice. Windows High Contrast / forced-colors mode discards `box-shadow` entirely and repaints `outline` in the system highlight colour. A component's own `box-shadow`, in a later layer, replaces a shadow ring but cannot touch an outline. Draw the ring as a shadow and it vanishes for exactly the users who most need it.

**Must not:**
- Be removed. Ever. `outline: none` without a replacement is the single most common accessibility defect in production CSS.
- Be lower than 3:1 against *both* the component and the surface behind it (SC 1.4.11, adjacent colours), or thinner than 2px (the 2px perimeter is 2.4.13, Level AAA, which this suite holds as a floor).
- Be clipped. `overflow: hidden` on a parent eats a ring drawn outside the border box. Leave room around the element, or use a negative `outline-offset` inside a scroller. The gap is painted in `--bg-canvas` so the ring stays readable on any fill.

**Failure signature when missing:** the focus-visible row looks like the default row. Tab through the real component and you cannot tell where you are. On a dark theme with a clipped ring you get the nastier variant — the ring is present in light, absent in dark, because the inner ring colour was resolved against the wrong canvas.

**Watch for:** a focus ring that is present but the *same colour as the component*. Contrast the ring against the component, not against the page.

---

### 1.4 active

**Means:** the press has landed and has not yet been released.

**Expressed:** `.thing:active:not(:disabled)`.

**Token:** `--bg-active` — a heavier overlay than `--bg-hover`, and `--dur-instant` if anything animates.

**Must not:**
- Move layout. `transform: translateY(1px)` is fine because transforms do not reflow; `margin-block-start: 1px` is not.
- Be slow. Anything over ~80ms and the press feels like it did not register, so people press again.
- Be skipped on touch. Touch has no hover, so `:active` is the *only* pre-commit feedback a finger ever gets. On touch, active is not a nicety; it is the entire affordance.

**Failure signature when missing:** the active row matches the hover row. Users on a pointer barely notice. Users on touch tap, see nothing, and tap again — which is where duplicate submissions come from.

---

### 1.5 disabled

**Means:** the control exists, is relevant, and is not operable right now.

**Expressed:** `:disabled` for real form controls, `[aria-disabled="true"]` for everything else (and for controls you want to keep focusable so a screen reader can find them and a tooltip can explain *why*).

| Which | When | Consequence |
|---|---|---|
| `disabled` | the control is genuinely inert and needs no explanation | removed from tab order, no events |
| `aria-disabled="true"` | the user needs to know why, or will re-enable it themselves | stays focusable; you must block the action in JS |

**Token:** `--bg-disabled`, `--fg-disabled`, plus `cursor: not-allowed`.

**Must not:**
- Be invisible. Disabled must read as disabled *without* colour: pair the reduced contrast with a visibly flatter surface or removed elevation.
- Be illegible. Disabled text is exempt from WCAG contrast minimums (SC 1.4.3 exempts inactive controls) — that is a legal exemption, not a design licence. If nobody can read which button is disabled, the exemption has not helped anyone.
- Be the product's error-handling strategy. A permanently disabled submit button with no explanation is a dead end; an enabled button that explains what is missing is a conversation.

**Failure signature when missing:** the disabled row is fully saturated and looks pressable. Worse: the *primary* disabled cell still reads as the brand accent, so the most prominent thing on screen is the one thing that does nothing.

---

### 1.6 loading

**Means:** the component has started work that has not finished.

**Expressed:** `[data-state="loading"]` on the element, `aria-busy="true"` for assistive tech. Both, not either: `data-state` is what the CSS reads, `aria-busy` is what the screen reader reads.

**Token:** `--fg-muted` for the dimmed content, `--motion-*` for any spinner, `--dur-*` never hardcoded so `prefers-reduced-motion` collapses it.

**Must not:**
- **Change size.** This is the rule people break. Replacing "Save changes" with a spinner shrinks the button, moves everything beside it, and moves the thing the user is about to click. Reserve the width: keep the label in place at reduced opacity and overlay the spinner, or set `min-inline-size` from the resting label.
- Spin forever with no timeout. A loading state with no failure path becomes a permanent loading state.
- Be the only feedback for something instant. Under ~200ms a spinner reads as a flicker and makes the app feel slower than no spinner at all.

**Failure signature when missing:** the loading row is identical to default, and in the real product a double-click submits twice. On the sheet, put the loading cell next to the default cell at the same density and *measure* — if the box moved, the layout will jump in production.

---

### 1.7 error

**Means:** the value is invalid, or the action failed.

**Expressed:** `[aria-invalid="true"]` for form controls (this is the one the screen reader announces), `data-state="error"` for everything else. Pair either with `aria-describedby` pointing at the message.

**Token:** `--fg-danger`, `--bg-danger`, `--border-default` re-pointed to the danger role.

**Must not:**
- Be carried by colour alone (SC 1.4.1). A red border and nothing else is invisible to roughly 1 in 12 men. Add an icon, a message, or a weight change.
- Appear before the user has finished. Validating on every keystroke of an email field tells someone their address is invalid four times while they type it.
- Disappear on blur without being fixed.

**Failure signature when missing:** the error row is identical to default — so a failed submit looks exactly like a successful one. The second signature: the error row differs *only* in border colour, which is the colour-alone failure, and it is easiest to catch by looking at the error row with your eyes half-closed.

---

### 1.8 Precedence — which state wins when two are true

States overlap constantly: a disabled button is also hovered, an invalid input is also focused. Decide the precedence once, encode it in guards, and the sheet will show you whether you got it right — the state pass renders each state in isolation, so any cell that looks like a *different* row's cell is a precedence bug.

| Both true | Winner | Why |
|---|---|---|
| disabled + hover | disabled | the control does nothing; a hover affordance is a lie |
| disabled + focus | disabled *appearance*, focus *ring* | `aria-disabled` controls stay focusable so their tooltip can be read; the ring must still show |
| loading + hover | loading | the press already landed |
| loading + disabled | disabled | if it is inert, that is the more important fact |
| error + focus-visible | both, composed | the ring sits outside the border box, the error colours the border — they do not collide by construction |
| error + disabled | disabled | an inert control's validity is not actionable |
| selected + hover | both, composed | selection is persistent, hover is transient; they must be distinguishable *and* combinable |

**Encode precedence as guards, not as order.**

```css
/* good — explicit, survives someone inserting a rule between them */
.button:hover:not(:disabled)  { --button-bg: var(--bg-hover); }
.button:active:not(:disabled) { --button-bg: var(--bg-active); }
```

```css
/* example: wrong — works today, breaks the first time the file is edited */
.button:hover   { --button-bg: var(--bg-hover); }
.button:disabled { --button-bg: var(--bg-disabled); }  /* wins only because it is later */
```

Order-based resolution is invisible: nothing in the source says "this must stay below that". A guard says it out loud and cannot be broken by a refactor.

**The composition problem.** `:hover { --button-bg: var(--bg-hover) }` *replaces* the variant's fill instead of darkening it. On the sheet, every variant's hover cell looks identical — pale grey — including the primary. Two fixes:

```css
/* A. overlay — hover composes over whatever the variant set */
.button {
  --button-overlay: transparent;
  background-image: linear-gradient(var(--button-overlay), var(--button-overlay));
}
.button:hover:not(:disabled) { --button-overlay: var(--bg-hover); }
```

```css
/* B. per-variant hover socket — more explicit, more lines */
.button { --button-bg-hover: var(--bg-hover); }
.button[data-variant="primary"] { --button-bg-hover: var(--bg-accent-hover); }
.button:hover:not(:disabled) { --button-bg: var(--button-bg-hover); }
```

Prefer B when the variants have genuinely different hover intents (a primary darkens, a ghost gains a surface). Prefer A when every variant wants the same relative darkening.

---

## 2. Content states are not interaction states

The seven above are things a *user* does to a component. The list below is things the *world* does to it, and it is where real products break — because the seven are in every design system checklist and these are in none of them.

| Content state | What it is | What breaks | Fixture to write |
|---|---|---|---|
| **empty** | the data arrived and there is none | a card with no title collapses; a table renders a header and a void | `""`, `null`, `[]` |
| **loading** (content) | data has not arrived yet | layout shifts when it does | skeleton at the resting size |
| **partial** | some fields present, some not | optional avatar missing pushes the name left | half the fields populated |
| **error** (content) | the fetch failed | the empty state is shown instead, so the user retries nothing | an error payload |
| **too-much-content** | three lines where you designed one | the card grows and breaks a grid row; text clips mid-word | 4× the design copy |
| **too-little-content** | one word where you designed three | the card shrinks below its neighbours and the row looks broken | a single short word |
| **long-string** | one unbroken token | overflows the box entirely — no space to wrap at | a 45-character word, a filename, an API key |
| **RTL** | `dir="rtl"` | physical properties (`margin-left`, `left`) do not mirror | the same fixture with `dir="rtl"` |
| **translated-label** | German is ~35% longer than English | buttons wrap to two lines; nav bars overflow | the real string, or `+35%` padding text |

Three rules that follow from this table:

1. **Every fetch gets a designed empty state and a designed loading state.** Defaulting them is not a decision, it is an omission that ships.
2. **Use logical properties everywhere** — `padding-inline`, `margin-block`, `inset-inline-start`. RTL then costs nothing. Retrofitting it costs a sprint.
3. **The long-string fixture is not an edge case.** Filenames, email addresses, IDs and URLs are unbroken tokens and they are in every product. `overflow-wrap: anywhere` or `text-overflow: ellipsis` with a `title` — pick one per component and be consistent.

The generator takes these as **content fixtures**, not as states, and renders them on their own pass against density. That is deliberate: a long string interacts with the box, and the box is what density changes. A long string does not interact with hover.

---

## 3. Combinatorics, and the pruning rule

The full matrix is:

```
states × variants × sizes × densities × themes × content fixtures
```

For a modest button — 7 states, 3 variants, 2 sizes, 3 densities, 2 themes, 5 fixtures — that is **1,260 cells**. Add a card and you are past 1,600. Nobody reads 1,600 cells, which means a full-cross sheet is a sheet that gets generated once and never looked at again.

**The pruning rule: render the cross-product only of the axes that can interfere. Render the others independently.**

Two axes interfere when they write to the same tokens, or when one changes the box the other lives in.

| Pair | Interfere? | Why |
|---|---|---|
| state × variant | **yes** | both re-point the same colour sockets; hover can silently overwrite a variant's fill |
| state × theme | **yes** | a translucent hover overlay tuned on white is invisible on near-black |
| state × size | no | size touches padding, state touches colour |
| state × density | no | same reason |
| state × content | no | hover does not care how long the label is |
| variant × size | **yes** | both re-point padding and radius sockets |
| density × size | **yes** | both scale the same padding sockets; `sm` at `compact` is the smallest box you ship |
| density × content | **yes** | a long string in a compact cell is a different problem from a long string in a spacious one |
| density × theme | no | density is spacing, theme is colour |
| theme × content | no | text length does not change with theme |

That gives three passes, which is what `generate_matrix.py --profile pruned` emits:

| Pass | Cross product | Fixed at defaults | What it catches |
|---|---|---|---|
| **state** | states × variants × themes | size, density, fixture | missing states, hover clobbering a variant, dark-mode overlays, invisible focus rings |
| **density** | densities × sizes × variants × themes | state, fixture | hardcoded padding, radius that does not scale, `sm` × `compact` below the tap target |
| **content** | fixtures × densities × themes | state, variant, size | overflow, collapse, clipping, translated labels |

The same button drops from 1,260 cells to **108**, and every one of them is a cell a human will actually look at.

**Theme is in every pass** even though it is independent of density and content. It is the cheapest axis (it is the inner axis of each cell, so it adds no rows) and the highest-yield one — a hardcoded colour is invisible in light and screaming in dark. Pay for it everywhere.

**When to reach for `--profile full`:** when the pruned sheet found something and you want to know its exact boundary, or when you have just changed the token layer itself. Not on every CI run.

---

## 4. Per-archetype checklist

The state each archetype is most often missing, from reviewing real component libraries. Check these first.

| Archetype | Usually missing | Why it goes missing |
|---|---|---|
| **Button** | `loading`, and `active` on touch | loading is JS-side so nobody styles it; `:active` feels redundant next to `:hover` on a desktop |
| **Input** | `disabled` + `readonly` as *different* states; `error` with a message, not just a border | readonly is treated as a flavour of disabled, then users cannot copy from it |
| **Select** | the open state of the menu, and the `disabled` option | the closed control gets designed, the popup gets whatever the browser gives |
| **Checkbox / radio** | `indeterminate`, and `focus-visible` on the *custom* control | the native input is hidden to style a box, and focus goes with it |
| **Card** | `focus-visible` when the whole card is a link | the card was designed as a surface, then made clickable later |
| **Table row** | `selected` vs `hover` vs `focus-visible` as three distinguishable things | they collapse into one grey and selection becomes unreadable |
| **Nav item** | `aria-current="page"` distinct from `hover` | "current" is styled as hover, so hovering a sibling makes two items look current |
| **Modal** | the scrim's `loading`, and focus return on close | the dialog is designed, the transition into and out of it is not |
| **Toast** | `error` vs `warning` at the same `elevation`; the exit state | toasts are designed as a happy-path success message |
| **Tabs** | `disabled` tab, and the focus ring *inside* the clipped tab strip | `overflow: hidden` on the strip eats the ring |
| **Avatar** | `loading` and the image-failed fallback | the fallback initial is drawn but never tested against a broken URL |
| **Badge** | `too-much-content` (a three-digit count), and `error`/`warning` variants at small size | badges are designed with "3" in them |

### The two universals

Whatever the archetype:

1. **Focus-visible is the one most often missing and the one that matters most.** Check it first, in both themes, at the smallest size, inside any parent with `overflow: hidden`.
2. **A state that looks identical to `default` on the sheet is a state that does not exist.** That is the entire reading procedure compressed into one sentence.

---

## 5. Reading a coverage gap

`generate_matrix.py` marks a cell `no rule` when nothing in the component's **own** stylesheet matches the state. That is a prompt, not a verdict, and it is deliberately conservative:

| Situation | The flag means |
|---|---|
| the focus ring comes from a global `:where(:focus-visible)` rule in `base.css` | false positive — look at the cell, it will be fine |
| the state is genuinely unimplemented | true positive — the cell will look like `default` |
| the state is implemented in JS by swapping a class | true positive, and against `web-design-studio/references/style-architecture.md` §8: state belongs in `data-state`, not a class |

So: the flag tells you where to look. The cell tells you what is true. Never resolve a flag without looking at its cell.

---

## 6. Adding a state to a component

A state is three things, and it is not implemented until all three exist. Missing any one produces a distinct, recognisable symptom.

| Piece | Where | Missing it looks like |
|---|---|---|
| **the rule** | the component's stylesheet, part 4 of the five-part shape | the cell renders as `default` |
| **the attribute** | the component's markup / its JS | works on the sheet, dead in the product |
| **the manifest entry** | `matrix.json` `states` | the state is never rendered, so nobody ever notices it is broken |

The order to do them in is **manifest first**. Declare the state before you write it, generate the sheet, see the `no rule` flag and the default-looking cell, then write the rule and watch the cell change. That is a three-minute red-green loop with no test framework in it.

### The checklist for a new state

1. Add it to `states` in `matrix.json`.
2. Generate; confirm the cell renders and is flagged `no rule`.
3. Pick the expression: a real ARIA attribute if one exists (`aria-expanded`, `aria-current`, `aria-selected`, `aria-invalid`, `:disabled`), else `data-state`. Never an `is-*` class.
4. Write the rule as a **socket re-point**, not new structure. If the state needs a property the component does not already declare, add the socket to the root rule first.
5. Guard it against the states that outrank it (§1.8).
6. Regenerate; confirm the cell now differs from `default` in both themes and at all three densities.
7. Wire the attribute in the component's code, and assert on it in the behavioural test — the same attribute the CSS reads, which is the whole reason state lives in attributes.
8. Accept the new baselines in the same commit as the CSS.

### When a state genuinely does not apply

Some do not. A static `<div>` card has no `active`. A display-only badge has no `disabled`.

Do not silently drop it — **omit it from `states` in the manifest and say why in the component's `note`.** The coverage table then shows `—` rather than a gap, and the next person reads the reason instead of re-litigating the decision. An undocumented omission is indistinguishable from an oversight, and in six months nobody will remember which it was.
