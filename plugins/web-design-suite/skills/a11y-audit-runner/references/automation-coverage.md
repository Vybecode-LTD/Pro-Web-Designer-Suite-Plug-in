# Automation Coverage

What a machine can check, what it cannot, and why. This is the file to read before anyone writes the word "accessible" in a document a client will keep.

The criteria themselves are specified in `web-design-studio/references/accessibility.md` §1 — plain English, where each shows up in this system, and how to verify it by hand. **This file does not restate them.** It answers a different question: for each one, *can a script decide?*

## Contents

1. [The one-sentence version](#1-the-one-sentence-version)
2. [Why "not automatable" almost always means "about meaning"](#2-why-not-automatable-almost-always-means-about-meaning)
3. [The coverage table](#3-the-coverage-table)
4. [False negatives: why a clean axe run is misleading](#4-false-negatives-why-a-clean-axe-run-is-misleading)
5. [False positives: why teams disable rules](#5-false-positives-why-teams-disable-rules)
6. [What to automate first](#55-what-to-automate-first-if-you-cannot-do-all-of-it)
7. [The coverage figure, with its sources](#6-the-coverage-figure-with-its-sources)
8. [How to say it in a report](#7-how-to-say-it-in-a-report)

---

## 1. The one-sentence version

**A tool can check whether a thing is present and well-formed. It cannot check whether the thing is right.**

Every row of the table in §3 is that sentence applied once. `alt` present: checkable. `alt` correct: not. Heading levels sequential: checkable. Heading outline meaningful: not. Contrast of two declared colours: checkable. Contrast of text over a photograph: not. Focus order programmatically determinable: checkable. Focus order sensible: not.

This is not a temporary limitation waiting on better tooling. Two of the categories are **genuinely undecidable by a machine**, in the ordinary sense that the answer depends on what the content means to a reader. A model can produce a plausible guess at whether alt text is good. A plausible guess is not a conformance result, and treating one as a conformance result is how a VPAT becomes a liability.

---

## 2. Why "not automatable" almost always means "about meaning"

Group the AA criteria by what they actually ask, and the pattern is immediate:

| The criterion asks about | Machine-checkable? | Examples |
|---|---|---|
| **Presence of an attribute or element** | Fully | `alt` exists, `<title>` exists, `lang` is set, every `<img>` has an `alt`, every control has a programmatic label |
| **Well-formedness against a spec** | Fully | valid ARIA names and values, valid `autocomplete` tokens, `aria-*` references that resolve, valid roles |
| **Arithmetic over declared values** | Fully, within its assumptions | contrast between two solid colours, target size in CSS pixels, heading level sequence |
| **Rendered behaviour** | Partly — needs a browser | is the focus ring visible, where does Tab actually go, does the layout reflow at 320px, what does forced-colors remove |
| **Whether the text is the right text** | **No** | is the alt correct, is the link text meaningful in context, is the error message helpful, is the heading a description |
| **Whether an order or sequence makes sense** | **No** | does the focus order preserve meaning, does the heading outline read as a table of contents, is the reading order the intended one |
| **Whether a behaviour matches expectation** | Partly — with a declared expectation | does Esc close the dialog *(automatable, given a key map)*; is this the dialog a user expected *(not)* |
| **Whether a person can understand it** | **No** | 3.3.3 Error Suggestion, 2.4.6 Headings and Labels, 1.3.3 Sensory Characteristics |

The rows in bold are not a small tail. They include 1.1.1 (the single most common failure by volume), 2.4.4, 2.4.6, 3.3.1, 3.3.3 and most of 2.4.3 — and they are where the failures that actually stop somebody completing a task live.

A useful way to hold it: **the machine checks the grammar; a person checks the sentence.** A page can be grammatically perfect and say nothing.

---

## 3. The coverage table

Each row cross-references `accessibility.md` §1 rather than restating it. **Full** means a tool decides correctly with no human input. **Partial** means a tool decides a proper subset, and the remainder needs a person or a declared expectation. **None** means the answer depends on meaning.

| SC | Auto | What a tool can decide | What it cannot, and why |
|---|---|---|---|
| **1.1.1** Non-text Content | **Partial** | `alt` is absent; `alt` is a filename, a placeholder or opens "image of"; a button or link has no name at all | **Whether the alt is correct.** `alt="image"` passes every scanner ever shipped. Whether a decorative image should have been described, or a described one should have been `alt=""`, is a content judgement. Volume-wise this is the biggest single gap in the whole table |
| **1.3.1** Info & Relationships | **Partial** | heading level skips, missing/duplicate landmarks, `<table>` without `<th scope>`, radio sets outside a `<fieldset>` | **Whether the structure describes the content.** Every heading can be at the right level and the outline still be meaningless. A `<div>` grid that looks like a table but is not is invisible here |
| **1.3.2** Meaningful Sequence | **Partial** | DOM order vs visual order disagreements from CSS `order`, `grid-area`, `position: absolute` | **Which order is the meaningful one.** The tool can say the two disagree; only a reader knows which is right |
| **1.3.3** Sensory Characteristics | **None** | — | "Click the button on the right" is ordinary English. Detecting it requires understanding that the sentence identifies a control by position |
| **1.3.4** Orientation | Full | a CSS or meta orientation lock | — |
| **1.3.5** Identify Input Purpose | **Full** | a personal-data field with no `autocomplete`, or with an invalid token | Whether the token chosen is the *right* one for the field is nearly always inferable from the name and label, so this is one of the few content-ish criteria a tool genuinely closes |
| **1.4.1** Use of Color | **None** | (a tool can flag links with no underline in body text — a heuristic, not the criterion) | Requires knowing what information the colour carries. A red border on an invalid field is a failure; a red brand accent is not, and they are the same CSS |
| **1.4.3** Contrast (Minimum) | **Partial** | any pair of solid, opaque colours — this is the highest-volume automated find on the web | **Text over an image, gradient, video or translucent overlay.** axe returns *incomplete* for these, which most CI jobs silently discard. The runtime layer composites overlays (`runtime-checks.md` §7) and still refuses to judge photographs |
| **1.4.4** Resize Text | **Partial** | zoom disabled via `user-scalable=no`/`maximum-scale`; clipping and overflow measured at 200% | Whether clipped content mattered |
| **1.4.5** Images of Text | **None** | — | Requires reading the image |
| **1.4.10** Reflow | **Partial** | two-dimensional scrolling at a 320px-equivalent viewport, with the widest offender named | Whether content or functionality was *lost* rather than merely rearranged |
| **1.4.11** Non-text Contrast | **Partial** | focus-ring contrast measured in pixels; icon and border contrast against a solid adjacent colour | **Which boundaries are "required to identify the control"** — that is a design judgement about affordance, not a property of the CSS |
| **1.4.12** Text Spacing | **Partial** | inject the bookmarklet CSS and diff for clipping | Whether the clipping matters, and whether meaning survived |
| **1.4.13** Content on Hover/Focus | **Partial** | Esc dismissal is drivable; persistence can be timed | **Hoverable** — whether the pointer can travel into it without it vanishing — is a geometry-and-timing question that is drivable in principle and reliably wrong in practice |
| **2.1.1** Keyboard | **Partial** | a focusable element the tab sequence never reaches; a click handler on a non-interactive element with no role, tabindex or key handler; a declared key map that does not hold | **Whether every FUNCTION is operable.** A tool does not know what the functions are. Drag-to-reorder with no keyboard path is invisible to it |
| **2.1.2** No Keyboard Trap | **Full** | drive Tab and Shift+Tab and detect a cycle shorter than the page's tab stops | Third-party iframes are opaque; the tool can see focus enter and not come back, which is usually enough |
| **2.1.4** Character Key Shortcuts | **Partial** | single-key listeners on `document` | Whether they are focus-scoped or remappable |
| **2.2.1** Timing Adjustable | **None** | — | Requires knowing a time limit exists and what it governs |
| **2.2.2** Pause, Stop, Hide | **Partial** | CSS animations over 5s with no pause control; `autoplay` media | Whether a control elsewhere pauses it |
| **2.3.1** Three Flashes | **Partial** | frame-differencing a recording, in principle | Nobody does this in CI. Treat as manual |
| **2.4.1** Bypass Blocks | **Partial** | a skip link exists, is first, is focusable and is not `display: none` | Whether it lands somewhere useful |
| **2.4.2** Page Titled | **Partial** | `<title>` exists and is non-empty | **Whether it is descriptive and unique.** `<title>Home</title>` on nine pages passes |
| **2.4.3** Focus Order | **Partial** | positive `tabindex`; backwards DOM jumps; skipped stops | **Whether the order preserves MEANING.** This is the criterion's actual text and it is not computable. See §4 |
| **2.4.4** Link Purpose | **Partial** | empty links, bare-URL links, exact matches against a vague-text list | **Whether "Read the report" is clear enough here.** Context decides, and context is prose |
| **2.4.5** Multiple Ways | **None** | — | A site-level architecture question |
| **2.4.6** Headings and Labels | **None** | — | "Describes topic or purpose" is the whole criterion, and it is a judgement about language |
| **2.4.7** Focus Visible | **Full** *(rendered)* | screenshot focused vs unfocused, measure the delta and its contrast. `outline: none` in source is a hint; pixels are the answer | Nothing meaningful. This is the criterion automation closes best once you stop reading CSS and start measuring |
| **2.4.11** Focus Not Obscured | **Partial** | compare the focused element's rect against sticky/fixed elements' rects | Partial obscuring is permitted at AA; deciding "entirely hidden" at the edges is fiddly |
| **2.5.1** Pointer Gestures | **None** | — | Requires knowing a gesture exists |
| **2.5.2** Pointer Cancellation | **Partial** | actions bound to `pointerdown`/`mousedown` rather than `click` | Whether the down-event *executes* the function or only previews it |
| **2.5.3** Label in Name | **Full** | the visible text is not contained in the computed accessible name | Ordering subtleties in a few languages |
| **2.5.7** Dragging Movements | **None** | — | Requires knowing a drag exists and whether the alternative is equivalent |
| **2.5.8** Target Size | **Partial** | measure every target's rect | The **spacing**, **inline**, **equivalent** and **essential** exceptions all need judgement; axe gets the geometry right and the exceptions approximately |
| **3.1.1** Language of Page | **Full** | `lang` present and a valid BCP 47 tag | Whether it matches the actual language — detectable heuristically, not a conformance result |
| **3.1.2** Language of Parts | **None** | — | Requires detecting a language change in running text |
| **3.2.1 / 3.2.2** On Focus / On Input | **Partial** | drive focus and change events and watch for navigation or DOM replacement | What counts as a "change of context" is partly a judgement |
| **3.2.3 / 3.2.4 / 3.2.6** Consistency | **Partial** | compare nav order and component names across a crawl | Whether two differently-named things do the same job |
| **3.3.1** Error Identification | **Partial** | submit invalid and check for `aria-invalid`, a described-by error, a live region | **Whether the error was identified in TEXT the user can act on** |
| **3.3.2** Labels or Instructions | **Full** | no label by any of the four mechanisms | Whether the label says the right thing (that is 2.4.6, above) |
| **3.3.3** Error Suggestion | **None** | — | "When the fix is known, suggest it" is a judgement about both the fix and the suggestion |
| **3.3.4** Error Prevention | **None** | — | Requires knowing which submissions are legal, financial or irreversible |
| **3.3.7** Redundant Entry | **None** | — | Requires knowing what was already entered and whether re-entry is essential |
| **3.3.8** Accessible Authentication | **Partial** | `onpaste` blocked on a password or OTP field; split single-character OTP inputs; missing `autocomplete` on credentials | Whether a CAPTCHA's alternative path is genuinely equivalent |
| **4.1.2** Name, Role, Value | **Partial** | empty computed accessible names, invalid roles, invalid ARIA values, ARIA references that resolve to nothing, states that never change when driven | **Whether the name is a good name**, and whether the role is the *right* role for what the thing does |
| **4.1.3** Status Messages | **Partial** | a live region exists before its content changes; an action produced no announcement at all | **Whether the announcement was timely, once, and useful** |

Count the rows. Roughly a third are **Full**, a bit under half are **Partial**, and the rest are **None** — which is the coverage figure in §6 arrived at from the other direction, and it lands in the same place.

---

## 4. False negatives: why a clean axe run is misleading

These are the ones that matter, because each is a page that passes CI and fails a user. Every one of them is real and common.

### 4.1 A `role="button"` div that a keyboard cannot reach

```html
<div role="button" aria-label="Delete" onclick="del()">✕</div>
```

axe passes it: the role is valid, the name is present, the element is not `aria-hidden`. **There is no `tabindex`, so the keyboard never reaches it.** The element is perfectly described and completely inoperable.

The inverse also passes: add `tabindex="0"` and it is now a tab stop with a name and a role — and **Enter and Space still do nothing**, because ARIA adds no behaviour. Every scanner reports a clean page.

*How this skill catches it:* `a11y_static.py` flags a click handler on a non-interactive element and grades it by what is missing; the runtime tab-order pass shows an element in the sequence that no key activates. Neither is a substitute for using a `<button>`.

### 4.2 An `aria-label` that is present, wrong and unflagged

```html
<button aria-label="Submit application">Send</button>
<a href="/careers" aria-label="Home">Careers</a>
```

Both have names. Both are wrong, and the second is actively dangerous: a screen reader user hears "Home" and lands on the careers page. **`aria-label` silently overrides the visible text**, which is exactly why it is a last resort.

The first is a 2.5.3 failure that *is* automatable — the visible text is not contained in the name — and this skill's `names` check finds it. The second is not: "Home" is a perfectly plausible name, and only a reader knows it is a lie. **`aria-label` is where a scanner's blindness is most concentrated**, because it turns a missing-name failure (detectable) into a wrong-name failure (not).

### 4.3 A focus order that is valid and nonsensical

2.4.3 says focus order must "preserve meaning and operability". A tool can detect that focus moved backwards in the DOM. It cannot detect this:

> A checkout page. Tab: email → *promo code* → *newsletter checkbox* → card number → expiry → CVC → *"edit shipping address"* → Pay.

Nothing is skipped. Nothing is trapped. No positive `tabindex`. DOM order and visual order agree. It is machine-perfect and it interrupts a payment twice and puts an address edit after the card details. **No tool has an opinion about this, and every user does.**

*What to do:* print the tab order (`a11y_runtime.mjs` does) and read it as a sentence. It takes thirty seconds per template and it is the highest-yield thirty seconds in the whole protocol.

### 4.4 Contrast that passes on a colour nobody can see

```css
.hero-text  { color: #767676; background: #ffffff; }   /* 4.54:1 — passes */
.hero-scrim { position: absolute; inset: 0; background: rgb(255 255 255 / 0.7); }
```

Every static contrast checker reports 4.54:1 and moves on. **Composited, the text renders at about 1.4:1.** axe, which reads rendered colours, usually returns *incomplete* here rather than a violation — and an incomplete that nobody reads is a pass.

Same shape, other forms: text over a gradient that is fine at one end; text over a video whose first frame is dark and whose tenth is white; a `mix-blend-mode` that inverts on scroll; a disabled overlay dropped over a live form.

*How this skill catches it:* the runtime contrast pass composites every translucent overlay painted above the text, including `pointer-events: none` scrims, and reports both numbers so the gap is explicit. Verified on the fixture: declared **5.33:1**, rendered **1.46:1**.

### 4.5 The others, briefly

| False negative | Why it passes |
|---|---|
| A `<table>` of `<div>`s | No table semantics to check, so no table rules fire. Row and column relationships simply do not exist, and nothing reports their absence |
| A live region added to the DOM at the same moment as its content | The region exists at scan time. It announced nothing at the moment it mattered |
| `aria-expanded` that never updates | Valid attribute, valid value. It just lies. Only driving the control finds it |
| A "disabled" control that still works | `aria-disabled="true"` is exempt from contrast. Whether the control is genuinely inactive is a behaviour, not an attribute |
| A skip link that goes to a `<div>` with no `tabindex="-1"` | Link present, target present, href resolves. Focus stays behind in most browsers |
| Everything in forced-colors mode | Scanners run in normal mode. The whole failure class is out of frame unless you emulate it deliberately |
| A modal that does not return focus to its trigger | Focus went *somewhere*. It went to `<body>`, silently, and the next Tab starts at the top of the page |
| An animation over the vestibular threshold | Motion is not a static property |

---

## 5. False positives: why teams disable rules

A false positive costs more than a missed finding, because it does not cost one finding — it costs the rule, and often the tool. The rules below are the ones teams actually turn off, with the honest reason and the right response.

| Flagged | Why it fires | The right response |
|---|---|---|
| **`color-contrast` on text over an image** | axe cannot sample the image, so it returns **incomplete** — and many wrappers surface incompletes as failures | Do not disable. Route incompletes to a human queue. This skill reports them separately, as warnings, with the reason |
| **`color-contrast` on text mid-animation** | The screenshot caught a fade at 40% opacity | Freeze animations before scanning. `a11y_runtime.mjs` injects a 1ms animation/transition override for exactly this |
| **`region` / "all content in landmarks"** | It is a **best-practice** rule, not a WCAG criterion, and it fires on every fragment and every Storybook story | Scope your tag set. `--tags wcag2a,wcag2aa,wcag22aa` for the gate; add `best-practice` for a full-page review |
| **`landmark-one-main` on a component fixture** | A component is not a page | Same answer: page rules belong to page runs. In `--matrix` mode this skill attributes violations to cells and demotes anything in the sheet's own chrome |
| **`nested-interactive`** on a genuine composite | A `role="tab"` inside a `role="tablist"` inside a toolbar can look nested | Check it once. If it is a real APG pattern, a per-element suppression with the pattern named beats disabling the rule |
| **`duplicate-id`** in a framework that generates ids | React 18's `useId` and most SSR frameworks produce unique ids; hand-rolled counters do not | Fix the generator. This is a genuine defect with a low-severity face — it breaks every `aria-labelledby` pointing at it |
| **`target-size` on inline links** | The **inline** exception exists precisely for links in a sentence | axe implements the exceptions approximately. Verify by hand, then suppress with the exception named |
| **`aria-allowed-attr` on a valid pattern** | Usually the pattern is not valid and the author is attached to it | Read the APG entry before suppressing. This rule is right more often than the person disabling it |
| **`heading-order` on a fragment** | The fragment starts at h2 because its page supplies the h1 | Run structural rules on assembled pages, not on fragments. `a11y_static.py` only raises `no-h1` on files that look like documents |
| **An unlabelled control rendered by a third party** | Payment iframes, chat widgets, map embeds | You cannot fix it and you are still responsible for it. Record it in the exceptions table with the vendor, the ticket and the date — that is what a VPAT's "Partially Supports" is for |

**The rule that follows from this table:** suppress with a reason, in the code, at the narrowest scope, or not at all. This skill's pragmas are comment-based for that reason — `a11y-audit-ignore-next-line: K -- third-party embed, ticket A11Y-91` shows up in a diff and gets argued about. A line in a config file does not.

### 5.1 The incompletes problem, which is neither a false positive nor a pass

axe returns three result types: `violations`, `passes`, and **`incomplete`** — cases where the rule ran and could not decide. Almost every CI integration written by hand asserts `violations.length === 0` and never looks at `incomplete`.

That is a real hole, and it is concentrated in exactly the places the false negatives in §4 live:

| Common incomplete | Why axe cannot decide | What a human has to do |
|---|---|---|
| `color-contrast` over an image, gradient or translucent layer | the background is not a colour | look at the worst region, or put the text on a measured scrim |
| `color-contrast` on text that is partly transparent | the composite depends on what is behind it | compute it, or stop fading text |
| `aria-valid-attr-value` on an IDREF resolved at runtime | the target may appear later | confirm the reference resolves once the view has settled |
| `frame-tested` | a cross-origin iframe cannot be scanned | test the embed separately, or get the vendor's ACR |
| `link-in-text-block` | whether the link is distinguishable without colour depends on the surrounding style | check it in greyscale |

**An incomplete is the tool asking a question, and an unanswered question is not a pass.** This skill reports incompletes as warnings, with their selectors, and says so in the finding text. Under `--strict` they fail. Resolve each one and record the decision; the record is what makes the next audit cheap.

---

## 5.5 What to automate first, if you cannot do all of it

The WebAIM Million data in §6 is a prioritisation list handed over for free: six machine-detectable failures account for the overwhelming majority of detected errors across a million home pages. If you are standing up a gate on a codebase with no accessibility work behind it, this is the order.

| Order | Failure | On % of home pages | Cost to gate | Why here |
|---|---|---|---|---|
| 1 | **Low-contrast text** | 83.9% | trivial — one axe rule, or one token review | Highest volume by a distance, and fixing it is usually *one* token repointed, not a hundred edits. `--fg-subtle` at `--neutral-500` failing 4.5:1 is the canonical instance |
| 2 | **Missing `alt`** | 53.1% | trivial to detect | Detecting it is free; writing good alt is the expensive part, and that is the point — the tool clears the queue so a writer can work through what remains |
| 3 | **Missing form labels** | 51.0% | trivial | Directly costs conversions as well as conformance. The four mechanisms are in `accessibility.md` §6 |
| 4 | **Empty links** | 46.3% | trivial | Nearly always an icon-only control whose `<svg>` is the entire content |
| 5 | **Empty buttons** | 30.6% | trivial | Same cause, same fix: name on the control, `aria-hidden` on the glyph |
| 6 | **Missing document `lang`** | 13.5% | one line, once | Cheapest fix on this page. A whole site's pronunciation for a single attribute |

All six are **Full** rows in §3 and all six are in `a11y_static.py` — no browser, one second, every commit. **Close these before you spend a day arguing about ARIA patterns**, because this is where the users are.

Then, in order of what the next increment buys:

7. **Positive `tabindex` and `outline: none`** — cheap to detect, catastrophic in effect, and both are usually a single deletion.
8. **The runtime focus-ring measurement** — the one check that turns 2.4.7 from "we have a CSS rule" into evidence.
9. **Forced-colors** — an entire user population that no normal-mode scan represents at all.
10. **The key map** — the most expensive to write and the thing that stops composite widgets regressing forever.

---

## 6. The coverage figure, with its sources

Three measurements, three methodologies, one conclusion.

| Source | Figure | What was measured |
|---|---|---|
| **[GDS, 2017](https://accessibility.blog.gov.uk/2017/02/24/what-we-found-when-we-tested-tools-on-the-worlds-least-accessible-webpage/)** | **37–41%** best single tool; **71%** all ten combined; **29%** found by none | A page with **143 deliberately planted failures in 19 categories**, run through ten automated tools. Tenon found 37% counting errors and warnings; Asqatasun 41% counting its manual-inspection prompts |
| **[Deque, 2021](https://www.deque.com/blog/automated-testing-study-identifies-57-percent-of-digital-accessibility-issues/)** | **57%** | Issues **by volume** — not by criterion — across 2,000+ audits, ~13,000 first-assessment pages and ~300,000 issues, using the axe suite **including Intelligent Guided Testing**, in which a human answers questions |
| **[WebAIM Million, 2026](https://webaim.org/projects/million/)** | **95.9%** of home pages | One million home pages scanned. 56.1 detectable errors per page on average, and six categories dominate: low-contrast text 83.9%, missing alt 53.1%, missing form labels 51.0%, empty links 46.3%, empty buttons 30.6%, missing document language 13.5% |

**Read together they are not in conflict.** The GDS study counts *criteria a tool can evaluate*, with a known denominator, which is the honest way to answer "what fraction of WCAG does this cover" — and the answer is roughly a third. The Deque study counts *issues found*, which is higher because the machine-detectable failures are also the most numerous ones, and because guided testing puts a human in the loop. WebAIM explains why both are true at once: the same six machine-detectable failures appear on nearly every site on the web, over and over.

**The figure this skill uses is "roughly a third", sourced to GDS 2017**, because it is the only one with a known denominator and no vendor interest, and because it is the conservative number. If you quote 57%, quote what it measures.

Two corollaries worth stating:

- **The automated third is enormously worth having.** 83.9% of home pages fail on low-contrast text — a fully automatable check. Closing the machine-checkable set is not a small win; it is most of the *volume* of harm on the web, and it costs a second of CI.
- **It is still a third of the criteria.** Volume and coverage are different quantities, and a report that reaches for whichever is more flattering is a report that will not survive its first real audit.

---

## 7. How to say it in a report

**The rule: the automated gate is a floor, and its passing is never reported as "accessible".**

This is not pedantry. In the EU the European Accessibility Act and EN 301 549 make an accessibility statement a document a person can rely on and act against; in the US, VPAT/ACR language feeds federal procurement. A claim of conformance based on a scanner is a claim you cannot support, and the people it misleads first are your own team — a green badge is the most effective way ever devised to stop a manual pass happening.

### Do not write

> ❌ "The site is WCAG 2.2 AA compliant."
> ❌ "Accessibility verified by automated testing."
> ❌ "0 accessibility errors."
> ❌ "Fully accessible."
> ❌ "Certified accessible" — there is no certification.

### Write

> ✅ **"Automated checks pass."** Scoped, true, and does not imply a conclusion it cannot support.
>
> ✅ For a status summary:
> *"Automated accessibility checks (axe-core 4.13, WCAG 2.2 A/AA rule set) return zero violations across all 14 page templates and 312 component states. Automated testing covers an estimated one third of WCAG success criteria; the remainder was evaluated manually on 2026-09-10 using the protocol in Appendix B. Two criteria are Partially Supported — see the exceptions table."*
>
> ✅ For a VPAT/ACR remark:
> *"Supports. Verified by automated rule (axe-core `color-contrast`) across all templates and by manual sampling of 12 representative components on 2026-09-10."*
>
> ✅ For something you have not tested:
> *"Not Evaluated."* This is a legitimate, honest entry. Guessing is not.
>
> ✅ When a third party is the problem:
> *"Partially Supports. The embedded payment iframe (Vendor, component v4.2) does not expose accessible names for its card fields. Reported to the vendor 2026-08-14, ref ABC-1182. Users can complete the same purchase via the phone path documented at /help/order-by-phone."*

### The three sentences to have ready

Somebody will ask these. Have the answer, not a flinch.

1. **"Did it pass?"** → *"The automated checks pass. Those cover about a third of the criteria; here is what the manual pass found."*
2. **"So it's accessible?"** → *"It meets the criteria we've evaluated, which is all of AA. 'Accessible' is about whether people can actually use it, and the strongest evidence for that is testing with disabled users — see `manual-protocol.md` §8."*
3. **"Why did the audit find things CI didn't?"** → *"By design. CI catches the machine-checkable third on every commit so the auditor's time goes to the rest. If the audit had found things CI *could* have caught, that would be the failure."*

That last one is the whole skill in one exchange. An external audit that finds only judgement-level issues means the gate is working.
