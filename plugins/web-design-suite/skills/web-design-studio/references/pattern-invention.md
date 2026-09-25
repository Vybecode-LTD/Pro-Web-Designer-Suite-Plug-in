# Pattern Invention

**How to invent interaction patterns that are memorable *and* shippable.**

This is the studio's method for the half of the work that isn't covered by a component
library. The other half — tokens, layout, typography, audit — is covered elsewhere in this
skill. This document exists because "use the standard pattern" is correct maybe 85% of the
time, and the remaining 15% is where the work becomes worth the invoice.

Everything here is procedure. Run it in order. The Gate (§4) is not advisory.

---

## Contents

1. [The premise: why invent, and where you must not](#1-the-premise)
   - 1.1 [The case for invention](#11-the-case-for-invention)
   - 1.2 [The counterweight: Jakob's Law and transfer of learning](#12-the-counterweight)
   - 1.3 [The no-innovation list](#13-the-no-innovation-list)
   - 1.4 [The boundary, stated crisply](#14-the-boundary-stated-crisply)
2. [The invention procedure](#2-the-invention-procedure)
   - Step 1 — [State the job](#step-1--state-the-job)
   - Step 2 — [Decompose the stock pattern into atoms](#step-2--decompose-the-stock-pattern-into-atoms)
   - Step 3 — [Apply transforms](#step-3--apply-transforms)
   - Step 4 — [Cross-pollinate from another medium](#step-4--cross-pollinate-from-another-medium)
   - Step 5 — [Sketch three variants at three risk levels](#step-5--sketch-three-variants-at-three-risk-levels)
   - Step 6 — [Run the Gate](#step-6--run-the-gate)
   - Step 7 — [Prototype the smallest testable slice](#step-7--prototype-the-smallest-testable-slice)
3. [The safe-novelty ladder](#3-the-safe-novelty-ladder)
4. [THE GATE](#4-the-gate)
   - 4.1 [Hard-fail items](#41-hard-fail-items-any-single-fail--redesign)
   - 4.2 [Soft-fail items](#42-soft-fail-items-scored)
   - 4.3 [Verdict rule](#43-verdict-rule)
5. [Worked examples](#5-worked-examples)
   - 5.1 [Preset browser for an audio plugin's web console](#51-worked-example-a--preset-browser)
   - 5.2 [Agency case-study index](#52-worked-example-b--case-study-index)
   - 5.3 [A/B audition comparator on a product marketing page](#53-worked-example-c--ab-audition-comparator)
6. [Documenting an invented pattern](#6-documenting-an-invented-pattern)

---

## 1. The premise

### 1.1 The case for invention

**Differentiation is a deliverable.** A site that is a component-library install with a new
accent hue has bought the client nothing they could not have bought for a tenth of the price.
The distinctive interaction is often the only part of the work the client's own customers can
describe afterwards. "The thing where you drag the two mixes against each other" is a
marketing asset. "It had cards" is not.

**Stock patterns encode a domain they were designed for, and yours may not be it.** The
dropdown was designed for short, flat, known option sets. Apply it to 400 synth presets whose
salient property is *how they sound* and you get a pattern that is technically correct and
functionally useless: serial, blind, text-mediated access to a set whose real structure is
continuous and auditory. The stock pattern is not neutral; choosing it uncritically is still
a design decision, just an unexamined one.

**Every standard pattern was invented, and most were violently novel at the time.** Drag and
drop, pull-to-refresh, infinite scroll, the command palette, slide-to-unlock, the undo toast
— each arrived as a strange thing someone had to learn. Treating the current pattern set as
permanent is a claim that interaction design finished, which it plainly did not.

### 1.2 The counterweight

**Jakob's Law**: users spend most of their time on *other* sites, so they expect yours to work
like the others. Not a preference — the actual state of their expectations on arrival. Every
deviation spends attention the user came to spend on your content.

**Transfer of learning** is the mechanism underneath it. A user's competence at your interface
is almost entirely borrowed. Positive transfer is free: if your checkbox is a checkbox, they
already know it. Negative transfer is worse than no transfer — a control that *looks* like
something known but behaves differently does not merely fail to help, it misleads and then
erodes trust in everything around it. A "slider" that snaps to unlabeled positions is negative
transfer. A thing that looks like nothing they've seen is at least honest about needing to be
learned.

**The economics are asymmetric.** A successful invention buys delight and memorability — real
but diffuse. A failed one buys a user who cannot check out, cannot find the pricing, or
believes the product is broken. The process must be asymmetric too: invention is opt-in,
gated, and defaults to the conservative variant when evidence is thin.

**Novelty has a per-page budget.** One invented pattern reads as craft. Four reads as a site
that cannot be used. Spend the budget on the one interaction that expresses what the product
actually is, and ship stock everywhere else. A memorable site is one strange thing surrounded
by competence.

### 1.3 The no-innovation list

In these categories, invention is forbidden. Not discouraged — forbidden. Use the most boring
correct implementation available and spend the creativity on how it looks.

| Category | Why it is closed |
| --- | --- |
| **Authentication** | Password managers, autofill, and passkeys are an ecosystem contract. Non-standard fields, custom "type your password in six boxes", or split email/password steps break autofill and push users to weaker passwords. Cost of failure: locked out. |
| **Checkout & payment** | Every non-standard step is measurable abandonment. Card fields must be standard `autocomplete` targets. Cost of failure: money, and in some jurisdictions, liability. |
| **Destructive confirmations** | The "are you sure" dialog is boring because it must be. No clever gesture confirmations, no swipe-to-delete without undo, no inverted button order. Cost of failure: irreversible data loss. |
| **Form field semantics** | A `<select>` is a `<select>`; a checkbox is multi-select; a radio is single-select; a required field is marked, not inferred. Re-inventing field semantics breaks autofill, password managers, screen readers, and every user's twenty years of habit at once. |
| **Scrolling** | Never hijack, never retime, never invert, never bind scroll to a non-scroll action. Scroll is the single most overlearned motor behaviour on the web and the one most tied to vestibular symptoms. |
| **Browser back** | Back must go back. History entries must correspond to things the user perceives as places. Trapping back, or consuming it to close a decorative overlay, is user-hostile. |
| **Text selection** | Do not disable it, do not intercept it, do not repurpose drag-on-text for anything else. Users select text to read, copy, search, and translate. |
| **Link behaviour** | Links navigate. They are `<a href>`, they show their destination on hover, they open in the same tab unless there's a real reason, they work with middle-click and Cmd-click. A `<div onclick>` "link" is not a link. |

Add to this list any interaction where **the cost of the user being wrong exceeds mild
confusion**: anything touching money, identity, deletion, legal consent, or safety.

### 1.4 The boundary, stated crisply

> **Innovate on expression, arrangement, and feedback.
> Do not innovate on primitives, affordances, and expectations.**

- **Expression** — how a thing looks, moves, sounds, and feels. Free territory.
- **Arrangement** — what is next to what, what order, what grouping, what spatial logic.
  Mostly free; costs a wayfinding check.
- **Feedback** — what the interface says back after an action, and how richly. Mostly free;
  costs an accessibility check.
- **Affordance** — the signal that says "this is operable, and this is how." Innovate only
  with strong evidence and a visible cue at rest.
- **Primitive** — the atomic control and its contract: button, link, field, checkbox, scroll,
  selection, back. Closed.
- **Expectation** — what the user believes will happen next. Never violate; you may *exceed* it.

A useful test: if your idea changes what the user must *know*, it is expensive. If it changes
what the user *sees and feels* while doing something they already know how to do, it is cheap.
Push inventions toward the cheap side and they ship.

---

## 2. The invention procedure

Seven steps. Do not skip Step 2 — the decomposition is the actual engine here; the rest is
scaffolding around it.

### Step 1 — State the job

Write three sentences before drawing anything.

1. **Job-to-be-done.** `When I <situation>, I want to <motivation>, so I can <outcome>.`
   Write it from the user's side, in their words. No UI nouns allowed in this sentence — if
   you write "so I can open the modal", you have described a mechanism, not a job.
2. **Mental model.** What does the user already believe about this content? What do they
   think the underlying structure *is*? (A record collection? A timeline? A mixing desk? A
   filing cabinet?) The invented pattern should match the model they already hold, not a new
   one you would like them to learn.
3. **The constraint the stock pattern fails.** Name it specifically and measurably: "the
   stock pattern requires N clicks to compare two items that must be compared", "the stock
   pattern renders the one property that matters (sound / motion / colour-in-context)
   invisible", "the stock pattern has no place to put the 40-word rationale each option
   needs".

If you cannot complete sentence 3 with something concrete, **stop and use the stock pattern.**
This is the most common correct outcome of this procedure and it is not a failure.

### Step 2 — Decompose the stock pattern into atoms

Every interaction pattern is a fixed set of atoms. Write them out for the stock pattern, then
you can transform them one at a time instead of trying to invent a whole pattern at once.

| Atom | The question it answers |
| --- | --- |
| **Trigger** | What starts it? (click, focus, hover, scroll position, drag, key, time, data change) |
| **Target** | What does it act on, and what is the unit of manipulation? (one item, a range, a whole set, a property) |
| **Feedback** | What does the system say back, in what channel, and how fast? |
| **State** | What states exist, and where does the user read the current one from? |
| **Affordance** | What at rest tells the user this is operable and how? |
| **Dismissal** | How does it end or close? What is the escape? |
| **Undo** | Can it be reversed, and how does the user learn that? |

**Worked decomposition 1 — the select dropdown.**

| Atom | Stock behaviour |
| --- | --- |
| Trigger | Click/Enter on a collapsed control |
| Target | Exactly one item from a flat list; unit = one whole option |
| Feedback | List appears; highlight follows pointer/arrow keys; chosen label replaces the trigger's text |
| State | Collapsed/expanded; selected value shown in the trigger |
| Affordance | Bordered field + caret glyph, borrowed from OS form controls |
| Dismissal | Select an item, click outside, or `Esc` |
| Undo | Re-open, pick again. No explicit undo. |

Immediately visible: feedback is *text only*, the unit is *one whole option*, and **there is no
compare** — you cannot hold two options side by side. For a set whose differences are
non-textual (sounds, colours, layouts, motion), the pattern deletes the information that
matters. That is the opening.

**Worked decomposition 2 — the modal dialog.**

| Atom | Stock behaviour |
| --- | --- |
| Trigger | Click on a button |
| Target | A task performed *away* from its context |
| Feedback | Scrim + centred panel + focus trap |
| State | Open/closed, binary; background frozen |
| Affordance | The trigger button's label |
| Dismissal | Confirm, cancel, `Esc`, scrim click |
| Undo | Whatever the task provides; usually nothing |

Visible: state is *binary*, so there is no "half-considering it"; the target is removed from
its context, so any task requiring reference to the page behind it is fighting the pattern.
Openings: make state continuous (a preview that deepens), or keep the context visible.

**Worked decomposition 3 — the filter sidebar.**

| Atom | Stock behaviour |
| --- | --- |
| Trigger | Click a checkbox |
| Target | The result set; unit = one boolean facet |
| Feedback | Result list re-renders, usually with no transition; a count changes |
| State | A set of checked boxes, read from the sidebar, far from the results |
| Affordance | Native checkboxes |
| Dismissal | "Clear all" |
| Undo | Uncheck — but the previous result set's *scroll position and sense of place* is gone |

Visible: feedback is a discontinuous jump, so the user never sees *what the filter did* — only
where it landed. The opening is in **feedback** and **transition**, which are the cheap,
free-to-innovate layers. This is the ideal shape of an invention target.

### Step 3 — Apply transforms

Take the atom list and run operations against it. These are the sixteen that pay off most
often. Apply one at a time; two at once produces something nobody can learn.

| # | Transform | Operation | Concrete example |
| --- | --- | --- | --- |
| 1 | **Change the dimension** | Re-map the layout axis: list → radial, list → 2D plane, time → space | Version history as a horizontal spine rather than a dated list; colour picker as a 2D plane rather than three sliders |
| 2 | **Change the input channel** | Swap the trigger: click → scrub, hover → proximity, discrete → continuous | Volume set by dragging across a waveform rather than typing dB; a card that responds to cursor *distance*, not just `:hover` |
| 3 | **Invert the direction** | Bring content to the cursor instead of moving the cursor to content | A radial menu that appears *under* the pointer; a toolbar that docks to the selection instead of the window edge |
| 4 | **Collapse two steps into one gesture** | Merge select + act | Drag a file directly onto a target rather than select → menu → "move to"; type-to-filter-and-run in a command palette |
| 5 | **Defer commitment** | Preview before commit; make the destructive step the last one | Hovering a theme swatch themes the live page; "apply" only persists it |
| 6 | **Make state spatial** | Read state from position, not from a label | An unsaved-changes indicator as a physical offset between two stacked cards; filter state shown as chips *in* the result header |
| 7 | **Make history navigable** | Expose the past as a place you can go | A scrubbable timeline of edits; "compare with 3 versions ago" side by side |
| 8 | **Borrow from an adjacent medium** | Import a whole interaction idiom (see §Step 4) | Solo/mute buttons from a DAW applied to dashboard series; a camera's exposure histogram applied to content density |
| 9 | **Change the unit of manipulation** | Operate on a range, a property, or a set instead of one item | Select a *date range* by dragging across the chart, not two date pickers; edit one property across 12 selected items at once |
| 10 | **Add a second simultaneous channel** | Carry redundant information in a second modality | Position *and* colour; motion *and* a live numeric readout; a chart that sonifies while it animates |
| 11 | **Remove a step entirely** | Delete a step and let a default absorb it | Auto-save removes "save"; inline edit removes "edit mode"; typeahead removes "search" as a distinct page |
| 12 | **Make the container adapt** | Reshape the frame instead of reflowing the content | A panel that grows to the content's natural measure rather than truncating; a nav that changes *shape* at a breakpoint rather than collapsing to a hamburger |
| 13 | **Make the transition carry the information** | The animation *is* the explanation of what changed | Filtered-out cards visibly travel out rather than vanishing, so the user learns what the filter did |
| 14 | **Change the persistence** | Make an ephemeral thing durable, or vice versa | A tooltip that can be pinned; a modal that becomes a dockable panel; a notification that leaves a trace in a log |
| 15 | **Expose the mechanism** | Show the system's reasoning instead of only its output | A search result that shows which term matched where; a recommendation that names its reason |
| 16 | **Change the granularity of feedback** | Coarse → fine, or after-the-fact → live | A progress bar that names the current file; validation that reports as you type the *last* character of a field rather than on blur |

Run through all sixteen against one atom (usually *feedback* or *target*) and you will
generate twenty ideas in fifteen minutes. Most are bad. That is the intent — the gate is
downstream, so generate cheaply.

### Step 4 — Cross-pollinate from another medium

Interaction idioms that are mature in another medium arrive on the web pre-tested by decades
of professional use. They also carry a learnability advantage with the *right* audience: an
audio product's users already know a DAW.

| Source domain | The specific idiom it offers | Maps onto |
| --- | --- | --- |
| **Audio production (DAW)** | Solo / mute per track; A/B compare with instant recall; automation lanes under a timeline; scrub-to-audition; a gain-staged signal chain | Dashboard series isolation; before/after comparators; per-item history under a list; preview-on-focus in any browser of media; multi-step data pipeline UIs |
| **Cartography** | Semantic zoom (labels change kind, not just size); pan-and-orient; layer toggles; the minimap | Zoomable org charts, dependency graphs, long documents; a persistent overview beside a detail view; "layers" for annotation and diff |
| **Film editing (NLE)** | The scrub head; in/out points on a strip; ripple vs. roll edits; the J-cut (audio leads picture) | Scrubbable case-study reels; range selection over any timeline; transitions where one channel of change leads the other by ~80ms and reads as "intentional" |
| **CAD / vector tools** | Snapping and guides; constraint-based layout; direct manipulation of handles; ortho-lock via modifier | Drag-and-drop builders; resizable dashboards; any editor where alignment matters; modifier keys as a discoverability-free power layer |
| **Gaming** | Diegetic UI (status expressed in the world, not a HUD); radial menus; progressive ability unlock; the tutorial-by-doing | Status as part of the content rather than a badge bar; touch-friendly contextual menus; feature reveal on capability rather than on day count |
| **Physical instruments** | Detented vs. continuous controls; the physical stop at range limits; bimanual operation; the single dominant control | Sliders that snap at meaningful values; visible resistance at a limit rather than silent clamping; modifier-plus-drag; a hero control that dominates the panel |
| **Aviation instruments** | The attitude indicator (one glyph, many variables); alert *levels*, not one alert style; the scan pattern; "dark cockpit" (no light = all good) | Dense multivariate status tiles; a genuine 3-level alert hierarchy; a status board where quiet means healthy |
| **Print / editorial** | The pull quote; marginalia; the multi-column measure; drop caps and entry points; the spread as a designed unit | Long-form scroll design; annotation rails; landing pages composed as spreads rather than stacked bands |
| **Board games** | Visible shared state; the turn structure; the rulebook that fits on a card; tokens whose position *is* their meaning | Collaborative tools' presence indicators; multi-step wizards with a visible board; kanban where position carries status |
| **Terminal / CLI** | Composition (pipe one result into the next); the command palette; history recall; terse aliases for experts | Power-user layers on a GUI; chained filters; `Cmd+K`; a fast path that coexists with, never replaces, the discoverable path |

Rule for borrowing: **import the idiom, not the skin.** Take the DAW's A/B-compare *concept*;
do not take its brushed-metal knobs. Skeuomorphism imports the aesthetic and drops the
learnability, which is the worst trade available.

### Step 5 — Sketch three variants at three risk levels

Always three. One variant is an opinion; three is a decision with a fallback.

| Level | Definition | What it costs the user |
| --- | --- | --- |
| **Conservative** | A stock pattern, restyled and well-executed. Novelty lives entirely in expression. | Nothing. Zero learning. Costs *you* the differentiation. |
| **Distinctive** | Stock atoms, recombined. The user recognises every part; the arrangement or feedback is new. | Two to five seconds of orientation on first encounter, no re-learning after. |
| **Radical** | A new affordance or a new input channel. The user must learn something. | Real learning cost, a discoverability liability, and a permanent accessibility burden. |

For each, write one sentence of cost in the user's terms — not "more complex to build" but
"a first-time visitor on a phone will not realise the panel is draggable." Costs written in
engineering terms are how radical variants get waved through.

**Default to the distinctive variant.** The conservative is your fallback when the gate fails;
the radical needs an affirmative reason to exist, not merely the absence of an objection.

### Step 6 — Run the Gate

See §4. Non-negotiable, and run *before* the build, on the sketch.

### Step 7 — Prototype the smallest testable slice

Before building the real thing, define:

- **The slice**: the smallest artefact that tests the *risky* claim. For "users will realise
  they can drag this", that is a static screenshot plus one question — not a working build.
  Do not build interaction to test discoverability; build interaction to test *feel*.
- **The success signal, written in advance**: "4 of 5 first-time users operate it within 10
  seconds with no prompt", or "median time-to-first-compare under 8 seconds". Writing the
  signal after seeing results is how everything passes.
- **The kill condition**: what result sends you to the conservative variant. Name it now,
  while you are not yet in love with the idea.
- **The instrument**: five-second test for discoverability; unmoderated first-click for
  learnability; a moderated pass for anything with a keyboard or screen-reader story; and a
  live check with the actual `prefers-reduced-motion` setting on.

If you cannot state the success signal, the idea is not yet specific enough to build.

---

## 3. The safe-novelty ladder

Every idea sits on exactly one layer. Locate it before arguing about it — most disagreements
about novelty are actually disagreements about which layer something is on.

| Layer | You are changing | Freedom | Evidence required before ship |
| --- | --- | --- | --- |
| **1. Decoration** | Colour, texture, type, imagery, ornament, sound design, the *aesthetic* of motion | **Free.** Innovate constantly; this is where the brand lives. | Contrast audit, reduced-motion pass, performance budget. No user testing. |
| **2. Arrangement** | Where things sit, grouping, order, density, the spatial logic of a page | **High.** Most memorable web design is arrangement novelty. | Wayfinding check: can a user state where they are and what else exists? Responsive + RTL pass. |
| **3. Feedback** | What the system says back, in which channel, how fast, how richly | **Medium.** The highest-value layer per unit of risk — new feedback rarely breaks anything and reliably reads as craft. | Accessibility announcement plan, reduced-motion equivalent, a non-visual channel for anything colour- or motion-only. |
| **4. Control affordance** | How the user knows a thing is operable and how to operate it | **Low.** Needs an affirmative case and a visible cue at rest. | Five-second discoverability test with real first-time users, keyboard equivalence proven, ARIA mapping named. Full Gate, no soft-fails permitted on discoverability. |
| **5. Interaction primitive** | The contract of button/link/field/scroll/selection/back/focus | **None.** Closed. | N/A — do not. |

Two rules that follow:

- **Push the idea down the ladder.** Nearly every layer-4 idea has a layer-2 or layer-3
  sibling that delivers 80% of the distinctiveness at 10% of the risk. "A radial menu"
  (layer 4) becomes "a menu that opens toward the cursor with a staggered reveal" (layers
  2+3) and now nobody has to learn anything. Do this reduction *before* you defend the idea.
- **A stack of layer-1 and layer-2 novelty reads as more designed than one layer-4 stunt.**
  Distinctiveness accumulates from consistency of expression, not from a single trick.

---

## 4. THE GATE

Every invented pattern clears this before a line of production code. Score it on the sketch,
re-score it on the prototype, and record the final score in the pattern's documentation (§6).

### 4.1 Hard-fail items (any single fail → redesign)

Answer each with evidence, not intention. "We'll handle that in QA" is a fail.

| # | Item | Pass condition | Fail examples |
| --- | --- | --- | --- |
| H1 | **Discoverability** | A first-time user finds the interaction with no instruction. There is a **visible cue at rest** — before hover, before focus, before scroll. Name the cue explicitly. | The affordance only appears on hover. The cue is a coach-mark or a tooltip on first visit (that is an admission of failure, not a cue). |
| H2 | **Learnability (5-second rule)** | Shown a static screenshot for five seconds, a user can state what will happen if they act. Prediction, not exploration. | "I'd have to click it and see." Two plausible contradictory predictions. |
| H3 | **Keyboard equivalence** | The complete task is achievable with keyboard alone, in a sane tab order, with a visible focus ring (`--shadow-focus`), and no keyboard trap. Every pointer gesture has a key equivalent. **No exceptions, ever.** | Drag-only reordering. Hover-only reveal. A custom widget that takes focus but has no arrow-key model. |
| H4 | **Touch** | Works with a finger. No behaviour depends on hover. Every target ≥ `--tap-min` (44px). **No scroll hijacking** — the page's vertical scroll is never retimed, intercepted or converted into another action. Horizontal drag near a viewport edge does not fight the OS back-gesture. | Cursor-proximity effects that are the only signal. A horizontal carousel that swallows the edge-swipe back gesture. `wheel` handlers with `preventDefault` driving a narrative. |
| H5 | **Screen reader** | You can name the announcement, in words, for every state. You can name the **existing ARIA pattern it is closest to** (`tablist`, `listbox`, `slider`, `tree`, `disclosure`, `grid`, `dialog`…) and implement with real semantics — native elements first, `role` only where nothing native fits. **If it maps to no existing ARIA pattern, it probably cannot be understood, and that is a fail.** | A pile of `role="presentation"` plus `aria-label` on divs. A pattern whose announcement you cannot write down. Live regions used to narrate motion. |
| H6 | **Reduced motion / vestibular safety** | With `prefers-reduced-motion: reduce`, the pattern is fully functional and all *information* is still conveyed. No parallax, no large-area movement, no motion the user did not initiate. **If the pattern *is* the motion, it fails.** | A comparison that only exists as a crossfade. A state change readable only from a transition. Any effect that survives reduced-motion because "it's subtle". |
| H7 | **Reversibility** | The user can escape or undo. `Esc` closes anything modal or expanded. Destructive outcomes are undoable, not merely confirmed. Accidental activation costs nothing. | No `Esc`. A drag that commits a deletion with no undo. A state change that loses scroll position with no way back. |
| H8 | **Cost of being wrong** | Worst case for a user who misunderstands the pattern is **mild confusion, recoverable in one action**. Anything above that — lost work, wrong purchase, missed information, wrong destination — is a fail. | A gesture that can submit a form. A control whose misread sends the user to the wrong plan. Content only reachable via the novel path. |

### 4.2 Soft-fail items (scored)

Score each **2 = clean pass**, **1 = partial**, **0 = fail**.

| # | Item | What a 2 looks like |
| --- | --- | --- |
| S1 | **No-JS / slow-JS** | Content is present and readable server-rendered; the pattern is a progressive enhancement layered on top. Nothing is `hidden` until JS decides otherwise. |
| S2 | **Small viewport** | Has a designed phone form, not a squeezed one. Often the conservative variant *is* the phone form; that is a legitimate answer. |
| S3 | **200% zoom / 320px reflow** | No horizontal scroll, no clipping, no overlap at 200% zoom (WCAG 1.4.10). Absolute positioning survives. |
| S4 | **RTL** | Direction-aware: logical properties (`inline-start`/`inline-end`), mirrored motion, mirrored arrow-key semantics where appropriate. |
| S5 | **Long / translated labels** | Survives German. No fixed-width control holding variable text; no layout that depends on a two-word label. |
| S6 | **Slow network** | Degrades with a designed loading and empty state; no layout shift on arrival; nothing that only makes sense once all assets have loaded. |
| S7 | **Consistency tax** | Does *not* create a second, inconsistent way to do something the product already does elsewhere. If it does, either it replaces the old way everywhere, or it does not ship. |
| S8 | **Performance** | Animates `transform`/`opacity` only; no layout thrash; no `wheel`/`pointermove` handler doing work outside `requestAnimationFrame`; measured on a mid-tier Android, not the studio's laptop. |
| S9 | **Density & theming** | Honours `--density` and the dark theme without a bespoke selector. Built from Tier-2 tokens, so it inherits both for free. |
| S10 | **Maintainability** | One home for its styles, expressible as a documented component, no magic numbers, no specificity war. A junior can modify it in a year. |

### 4.3 Verdict rule

1. **Any hard-fail (H1–H8) → redesign or drop.** No overrides, no "we'll note it as a known
   issue". A hard-fail is a defect, not a trade-off.
2. **Soft-fail score ≥ 17/20 → ship as designed.**
3. **13–16 → ship only with the named repairs scheduled in the same build.** List them; they
   are not backlog.
4. **≤ 12 → demote to the conservative variant.** Two or more zeroes is an automatic demotion
   regardless of total; a single catastrophic dimension is not offset by elegance elsewhere.
5. **Re-run the Gate after the build.** The sketch score is a prediction; the built score is
   the record. Nothing ships un-audited.

---

## 5. Worked examples

### 5.1 Worked example A — preset browser

*Context: web console for a mastering plugin. 400 factory presets, users are producers.*

**Step 1 — job.**
*JTBD:* "When I'm half an hour into a mix and losing objectivity, I want to hear three or four
starting points quickly, so I can pick one and get back to work."
*Mental model:* a record crate. Flip, sample, keep two fingers in the box.
*Constraint the stock pattern fails:* a `<select>` of 400 names makes the salient property —
**what it sounds like** — invisible, and permits zero comparison. Auditioning four presets
costs eight interactions and the user has forgotten the first one by the fourth.

**Step 2 — decomposition.** (Stock: the dropdown, per §Step 2.) Feedback is text-only; unit is
one whole option; there is no compare; state lives in a collapsed field far from the content.

**Step 3 — transforms tried.** #2 change input channel (hover → audition), #5 defer commitment
(audition ≠ load), #6 make state spatial (a "crate" of held candidates), #9 change unit
(compare a *pair*, not one), #1 change dimension (a 2D brightness × density plane), #8 borrow
from DAW (A/B recall, solo).

**Step 5 — variants.**

- **Conservative.** Filtered list, click to load, a "revert" button.
  *Cost:* none. Also indistinguishable from every other plugin.
- **Distinctive.** A keyboard-navigable list where **focus auditions** (arrow keys walk and
  play, with a visible "auditioning" state), `Space` holds a preset into a **compare tray** of
  up to three, `Enter` commits. Loading is explicit and separate from auditioning.
  *Cost:* ~4 seconds to learn that arrow keys play; the tray needs a label.
- **Radical.** A 2D character map — brightness on X, density on Y — presets as unlabeled dots,
  cursor proximity continuously crossfades the audition between nearby dots.
  *Cost:* a first-time user cannot tell it is operable, cannot find a preset by name, has no
  keyboard model, and on touch there is no proximity at all.

**Step 6 — Gate.**

| Variant | H1 | H2 | H3 | H4 | H5 | H6 | H7 | H8 | Soft |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Radical | **FAIL** — no cue at rest, dots read as decoration | **FAIL** — users predict "a chart" | **FAIL** — continuous 2D proximity has no key model | **FAIL** — proximity does not exist on touch | **FAIL** — maps to no ARIA pattern; a dot cloud is not a listbox | pass | pass | **FAIL** — name search impossible, so presets become unreachable | — |
| Distinctive | pass — list is visibly a list; a persistent "↑↓ to audition" hint sits in the header | pass | pass — full arrow/Space/Enter model | pass — on touch, tap = audition, a "Hold" button replaces `Space`; targets ≥ `--tap-min` | pass — it is a `listbox`, honestly implemented, with a polite live region naming the auditioning preset | pass — audition is audio, not motion; the only animation is a 140ms highlight | pass — `Esc` stops audition and returns to the loaded preset | pass — worst case is hearing a preset you didn't want | 19/20 (S1 = 1: audition needs JS; the list itself is server-rendered) |

**Verdict: the radical is dead** — five hard-fails, and the fatal one is H8: it made the
product's content unreachable in service of an aesthetic. **The distinctive ships at 19/20.**
Note what survived from the radical: continuous audition became *focus-driven* audition, which
is the same insight with a keyboard model attached. Radical variants are usually not wasted —
they are where the insight comes from, and the distinctive variant is where it gets a chassis.

```html
<div class="preset-browser">
  <p class="preset-browser__hint" id="preset-hint">
    ↑ ↓ to audition · Space to hold for compare · Enter to load
  </p>

  <ul class="preset-list" role="listbox" aria-label="Factory presets"
      aria-describedby="preset-hint" aria-activedescendant="preset-glass-plate" tabindex="0">
    <li class="preset" role="option" id="preset-glass-plate" aria-selected="true"
        data-auditioning="true">
      <span class="preset__name">Glass Plate</span>
      <span class="preset__meta">bright · wide · 2.4 s</span>
    </li>
    <!-- … -->
  </ul>

  <p class="u-visually-hidden" aria-live="polite" id="preset-status">Auditioning Glass Plate</p>
</div>
```

```css
@layer components {
  .preset-browser {
    display: grid;
    gap: var(--gap-related);          /* parent owns the gap */
    padding: var(--pad-card);
    background: var(--bg-surface);
    border-radius: var(--radius-xl);
    box-shadow: var(--elevation-card);
  }

  .preset-browser__hint { font: var(--type-label); color: var(--fg-muted); }

  .preset-list {
    display: grid;
    gap: 0;                           /* rows are separated by rules, not gaps */
    margin: 0;
    padding: 0;                       /* 0 is the one literal allowed: it is
                                         the absence of a value, not a scale step */
    list-style: none;
  }
  .preset-list:focus-visible { outline: none; box-shadow: var(--shadow-focus); }

  .preset {
    display: flex;
    justify-content: space-between;
    gap: var(--gap-tight);
    min-block-size: var(--tap-min);   /* finger-sized on touch, harmless on desktop */
    align-items: center;
    padding-inline: var(--pad-inline-md);
    padding-block: var(--pad-block-md);
    border-block-end: var(--stroke-hairline) solid var(--border-subtle);
    border-radius: var(--radius-md);
    font: var(--type-ui);
    color: var(--fg-default);
    transition: background-color var(--motion-hover);
  }
  .preset__meta { font: var(--type-label); color: var(--fg-muted); }

  /* Auditioning state is carried by colour AND a left bar AND the live region —
     three channels, so none of them is load-bearing alone. */
  .preset[data-auditioning="true"] {
    background: var(--bg-selected);
    box-shadow: inset var(--stroke-thick) 0 0 0 var(--border-accent);
  }

  .preset[data-held="true"] .preset__name::after {
    content: "held";
    margin-inline-start: var(--gap-fused);
    font: var(--type-label);
    color: var(--fg-accent);
  }

  /* No reduced-motion block is needed, and that is the point: --motion-hover already
     collapses to 1ms at the token layer, and nothing here is carried by motion. If an
     invented pattern needs a bespoke reduced-motion rule, it is leaning on motion. */
}
```

The keyboard model is the pattern — audition on move, hold on `Space`, commit on `Enter`,
escape to the loaded preset. Written out, because H3 is not satisfied by intent:

```js
list.addEventListener('keydown', (e) => {
  const step = { ArrowDown: 1, ArrowUp: -1, Home: -Infinity, End: Infinity }[e.key];

  if (step !== undefined) {
    e.preventDefault();                         // own the arrows; do not scroll the page
    setActive(clamp(activeIndex + step));
    audition(options[activeIndex]);             // moving IS auditioning
    status.textContent = `Auditioning ${options[activeIndex].dataset.name}`;
  } else if (e.key === ' ') {
    e.preventDefault();                         // Space holds, it does not select
    toggleHold(options[activeIndex]);
  } else if (e.key === 'Enter') {
    commit(options[activeIndex]);               // the only step that changes the patch
  } else if (e.key === 'Escape') {
    stopAudition();
    setActive(loadedIndex);                     // H7: escape returns you to where you were
  }
});

// Leaving the widget must never strand audio playing. Blur is a release, always.
list.addEventListener('blur', stopAudition);
```

### 5.2 Worked example B — case-study index

*Context: the studio's own site. 14 case studies. The client-facing goal is "this studio thinks
about problems, not just pixels."*

**Step 1 — job.** "When I'm shortlisting agencies, I want to see whether they've solved a
problem like mine, so I can decide whether to email them." *Mental model:* a portfolio — a
stack of things, browsable in any order. *Constraint the stock pattern fails:* a uniform card
grid sorts by recency and presents every project as equivalent, which hides the one thing the
visitor is scanning for — **the kind of problem solved**.

**Step 2 — decomposition (filter sidebar + grid).** Feedback is a discontinuous re-render;
state lives in a sidebar far from the results; arrangement carries no meaning at all.

**Step 3 — transforms.** #1 change the dimension (arrange by problem type, not date), #13 make
the transition carry the information (show cards *leaving* when filtered), #6 make state
spatial (the filter state is the column you are in), #7 make history navigable.

**Step 5 — variants.**

- **Conservative.** Card grid + filter chips. *Cost:* none; also forgettable.
- **Distinctive.** Cards laid out in **columns by problem type** ("rebuild trust", "make the
  complex legible", "launch under deadline"), each column a sticky heading with its own scroll;
  filtering *re-flows* cards between columns with a FLIP transition so you see what moved.
  *Cost:* ~5 seconds to grasp that columns are themes, not stages of a process.
- **Radical.** A full-viewport horizontal filmstrip: vertical wheel scrolls it sideways, cards
  scale toward the centre, no visible pagination.
  *Cost:* scroll does not do what scroll does.

**Step 6 — Gate.** The radical dies at **H4**: it retimes and re-axes the page's vertical
scroll, which is on the no-innovation list, and its horizontal drag collides with the iOS
back-gesture at the screen edge. It also takes **H6** (the scale-toward-centre effect *is* the
hierarchy, so reduced-motion leaves a flat undifferentiated strip) and **H2** (a trackpad user
predicts vertical movement and gets sideways). Three hard-fails.

The distinctive variant scores 18/20: **S2 = 1** — on a phone the columns stack and the
re-flow transition is dropped, so the pattern's whole point is desktop-only; **S1 = 1** — the
static column layout renders server-side, the FLIP transition needs JS. Both acceptable, both
named. Ships.

```css
@layer components {
  .work-index {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
    gap: var(--gap-separate);           /* parent owns the gap */
    padding-inline: var(--gutter-page);
  }

  .work-theme__heading {
    position: sticky;
    inset-block-start: 0;
    z-index: var(--z-raised);
    padding-block: var(--pad-block-md);
    background: var(--bg-canvas);
    font: var(--type-h4);
    color: var(--fg-strong);
    letter-spacing: var(--tracking-tight);
  }

  .work-theme__list { display: grid; gap: var(--gap-grouped); }

  .work-card {
    padding: var(--pad-card);
    background: var(--bg-surface);
    border: var(--stroke-default) solid var(--border-subtle);
    border-radius: var(--radius-lg);
    box-shadow: var(--elevation-card);
    transition: box-shadow var(--motion-hover), translate var(--motion-enter);
  }
  .work-card:hover,
  .work-card:focus-within { box-shadow: var(--elevation-raised); }
  .work-card a:focus-visible { outline: none; box-shadow: var(--shadow-focus); }

  /* The FLIP re-flow is the invented part. It is an enhancement: the class is
     added by script only when motion is allowed, so reduced-motion users get the
     same rearrangement instantly, with no information lost. */
  .work-card[data-flip="true"] { transition: translate var(--motion-expand); }

  @media (prefers-reduced-motion: reduce) {
    .work-card[data-flip="true"] { transition: none; }
  }
}
```

### 5.3 Worked example C — A/B audition comparator

*Context: marketing page for the mastering plugin. The page must make a processed/unprocessed
difference audible in under ten seconds, to a sceptical engineer.*

**Step 1 — job.** "When I'm deciding whether a plugin is worth 30 minutes of my evening, I want
to hear the difference on material I recognise, so I can judge it honestly." *Mental model:* the
bypass button — the single most-used control in audio, pressed thousands of times. *Constraint:*
two separate play buttons force sequential listening with a gap, and auditory memory across a
gap is famously unreliable. The comparison has to be **instant and at the same playback
position**, or it proves nothing.

**Step 3 — transforms.** #8 borrow from the DAW (A/B recall at the same transport position),
#5 defer commitment (the compare does not change anything), #10 second channel (a waveform
that visibly changes alongside the audio), #2 change input channel (hold-to-hear-original).

**Step 5 — variants.**

- **Conservative.** Two audio players, labelled Before and After. *Cost:* none; also proves
  nothing, because the comparison is lost across the gap.
- **Distinctive.** One transport; a segmented Before/After control that swaps source
  instantly, keeping position. *Cost:* nothing, really.
- **Radical.** Hold-to-compare: holding the primary key or the button switches to the original
  and releases back — the DAW bypass idiom exactly. Position preserved, gapless.

Here the radical is the *better* idea, and the Gate's job is to tell us whether it can be made
safe rather than to reflexively kill it.

**Step 6 — Gate on the radical, first pass.** **H1 fails** — a "hold" affordance has no cue at
rest and nobody will discover it. **H3 fails** — hold-to-compare on a key has no defined
keyboard contract and traps a user who tabs away mid-hold.

**Repairs** (this is the normal use of the Gate — repair, then re-score):

1. Ship the *distinctive* segmented control as the primary, always-visible affordance. It is
   the discoverable path and it fully performs the job on its own.
2. Layer hold-to-compare as a **power path** on the same button: press-and-hold on pointer,
   `Space` held on keyboard, with the label changing to "Hold for original" while focused.
   Borrowed from the CLI lesson in §Step 4 — the fast path *coexists with*, never replaces,
   the discoverable one.
3. `pointerup`, `keyup`, `blur`, and `visibilitychange` all release the hold, so no state can
   be stranded.

**Re-score:** H1 pass (the segmented control is the cue; hold is a bonus nobody must find),
H2 pass, H3 pass (`Space` toggles; hold is additive), H4 pass (tap toggles; hold works via
`pointerdown`/`pointerup`; targets ≥ `--tap-min`), H5 pass (it is a two-option `radiogroup`,
plainly), H6 pass (the comparison is *audio*; the waveform is decorative reinforcement and
its animation drops cleanly), H7 pass (`Esc` stops playback; release always returns to After),
H8 pass (worst case: you hear the wrong version for a second). Soft: **18/20** — S1 = 1
(requires JS and audio), S6 = 1 (a 2 MB audio file on 3G needs its designed loading state,
which is scheduled in this build).

**Verdict: the radical ships, because the repair turned a new affordance into an optional
layer over a stock one.** That is the general move — when a radical idea is genuinely better,
do not defend it, *demote it to a second layer* over a conservative primary. You keep the
idea and lose the liability.

```html
<div class="ab-compare">
  <div class="ab-compare__switch" role="radiogroup" aria-label="Audio version">
    <button type="button" role="radio" aria-checked="false" class="ab-compare__btn">Before</button>
    <button type="button" role="radio" aria-checked="true"  class="ab-compare__btn"
            data-hold="true">After<span class="ab-compare__hold-hint"> · hold for original</span></button>
  </div>
  <p class="u-visually-hidden" aria-live="polite">Playing: after processing</p>
</div>
```

```css
@layer components {
  .ab-compare__switch {
    display: inline-flex;
    gap: 0;
    padding: var(--pad-block-xs);
    background: var(--bg-sunken);
    border-radius: var(--radius-full);
  }

  .ab-compare__btn {
    min-block-size: var(--tap-min);
    padding-inline: var(--pad-inline-md);
    border: none;
    border-radius: var(--radius-full);
    background: transparent;
    font: var(--type-ui);
    color: var(--fg-muted);
    cursor: pointer;
    transition: background-color var(--motion-hover), color var(--motion-hover);
  }
  .ab-compare__btn[aria-checked="true"] {
    background: var(--bg-surface);
    color: var(--fg-strong);
    box-shadow: var(--elevation-card);
  }
  .ab-compare__btn:focus-visible { outline: none; box-shadow: var(--shadow-focus); }

  /* The hold hint only appears once the control is focused or hovered — it is a
     refinement of an affordance that is already visible, not the affordance itself.
     That distinction is what got this through H1. */
  .ab-compare__hold-hint { display: none; color: var(--fg-subtle); }
  .ab-compare__btn:is(:hover, :focus-visible) .ab-compare__hold-hint { display: inline; }

  @media (prefers-reduced-motion: reduce) {
    .ab-compare__btn { transition: none; }
  }
}
```

The hold layer is four lines of intent and four lines of release. The release handlers are
the ones that got this through H7 — every way of leaving the interaction ends the hold:

```js
const hold   = () => { if (!held) { held = true;  swapTo('before'); } };
const release = () => { if (held)  { held = false; swapTo('after');  } };

btn.addEventListener('pointerdown', hold);
btn.addEventListener('keydown', (e) => { if (e.key === ' ') { e.preventDefault(); hold(); } });

// Four ways out, all of them release. A stranded hold would mean the visitor hears
// the unprocessed audio and concludes the plugin does nothing.
btn.addEventListener('pointerup', release);
btn.addEventListener('pointercancel', release);   // finger dragged off the button
btn.addEventListener('keyup', (e) => { if (e.key === ' ') release(); });
btn.addEventListener('blur', release);
document.addEventListener('visibilitychange', release);
```

---

## 6. Documenting an invented pattern

An invented pattern that lives only in one page is a liability: the next person re-invents it
slightly differently and the product now has two of them. Write it into the design system the
day it ships, using this template.

````markdown
# Pattern: <Name>

A short, memorable, *descriptive* name. "Compare Tray", not "PresetFlow".

**Status:** shipped · experimental · deprecated
**Owner:** <name>  ·  **Shipped:** <date>  ·  **Gate score:** H 8/8, S 19/20

## Job
The JTBD sentence from Step 1, verbatim. Plus one line on the constraint the stock
pattern failed — this is what stops someone "simplifying" it back to a dropdown.

## When to use / when not to
Two bullet lists. The "not" list is the more important one. Name the stock pattern
that should be used instead in each excluded case.

## Anatomy
Numbered parts with the class names, and a diagram or annotated screenshot.
  1. `.preset-list` — the listbox container; owns the gaps between rows.
  2. `.preset` — one option row; never sets its own outer margin.
  3. `.preset__meta` — secondary descriptors.

## States
Every state, its visual treatment, and the *non-visual* channel that carries it too.
| State | Visual | Second channel |
| rest | `--fg-default` on `--bg-surface` | — |
| focused/auditioning | `--bg-selected` + inset accent bar | live region announcement |
| held | "held" suffix in `--fg-accent` | `aria-selected` |
| disabled | `--fg-disabled` | `aria-disabled="true"` |

## Tokens consumed
List every Tier-2 token the component reads, and the Tier-3 tokens it declares.
Anyone should be able to re-theme this from this list alone.
Tier 2: --bg-surface, --bg-selected, --fg-default, --fg-muted, --fg-accent,
        --border-subtle, --border-accent, --gap-related, --gap-tight,
        --pad-card, --pad-inline-md, --radius-xl, --radius-md,
        --elevation-card, --motion-hover, --shadow-focus, --tap-min, --type-ui
Tier 3: --preset-row-min-h (= var(--tap-min))

## Keyboard map
| Key | Action |
| Tab | move focus to/from the widget (the widget is one tab stop) |
| ↑ / ↓ | move the active option; auditions it |
| Home / End | first / last option |
| Space | hold the active option into the compare tray |
| Enter | load the active option |
| Esc | stop audition, restore the loaded preset |

## ARIA mapping
Name the standard pattern it implements and any deviation, with the reason.
> Implements the APG **Listbox** pattern with `aria-activedescendant`. Deviation:
> `Space` is bound to "hold" rather than "select", because selection here is
> `Enter` (commit). Announced via a polite live region on audition change.

## Do / Don't
- **Do** keep the audition hint visible at rest; it is what passed H1.
- **Do** let the parent own the gaps; the row sets no outer margin.
- **Don't** make audition the commit action — the separation is the whole pattern.
- **Don't** use this below 3 options; use a `radiogroup`.
- **Don't** nest two of these on one page. Novelty budget.

## Gate record
The full scored table, dated, plus the named repairs and whether they landed.
Re-run and re-date this whenever the pattern is materially changed.
````

Two habits make this stick:

- **The Gate record is part of the pattern, not a historical note.** When someone proposes a
  change, they re-score the affected rows. A pattern whose Gate record is older than its last
  material change is un-audited, and un-audited things do not ship.
- **Name the pattern early.** An invented interaction with no name is renegotiated in every
  meeting. Once it is "the Compare Tray", it is a component with an owner, a test, and a
  documented contract — which is the difference between a studio's signature and a one-off.
