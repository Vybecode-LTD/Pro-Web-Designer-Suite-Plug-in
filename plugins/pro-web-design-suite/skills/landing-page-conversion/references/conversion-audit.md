# Conversion Audit

The review procedure for a page that already exists. Two passes — message and technical — run in that order, because a fast page that says nothing is a fast page that says nothing.

Work it top to bottom. Stop and write the finding down when you find one; do not fix as you go, because the ranking at the end depends on seeing all of them.

## Contents

1. [Before you start](#1-before-you-start)
2. [The five-second test](#2-the-five-second-test)
3. [The squint test](#3-the-squint-test)
4. [Scroll-depth reasoning](#4-scroll-depth-reasoning)
5. [The friction inventory](#5-the-friction-inventory)
6. [Form design for conversion](#6-form-design-for-conversion)
7. [The technical layer](#7-the-technical-layer)
8. [Instrumentation you need before claiming anything](#8-instrumentation-you-need-before-claiming-anything)
9. [A/B testing, honestly](#9-ab-testing-honestly)
10. [The report](#10-the-report)

---

## 1. Before you start

Get four things, or state that you could not:

| Need | Why |
|---|---|
| The traffic source | A page is not good or bad in the abstract; it is a continuation of whatever sentence the ad, search result or referral started. Mismatch there presents as every other symptom |
| The one action the page exists to produce | Without it you are reviewing aesthetics |
| What happens immediately after the click | The heaviest friction on most pages is one screen *past* the page |
| Current numbers, if any exist | Conversion rate, bounce, scroll depth, form abandonment. If none exist, that is finding #1 (see §8) |

Then view the page the way its traffic does: **on a phone, on a throttled connection, cold cache, in a private window.** Most audits are conducted on a fast laptop with the site warm, which is the one condition under which no real visitor ever sees it.

---

## 2. The five-second test

Show the first screen for five seconds. Take it away. Ask:

1. What does this company sell?
2. Who is it for?
3. What would happen if you clicked the main button?
4. What do you remember?

Run it with **five people who do not know the product**, and read it for a gross failure, not a measurement. NN/g's five-user rule, that five people find about 85% of the problems when each finds about 31%, is for iterative qualitative testing ([NN/g](https://www.nngroup.com/articles/why-you-only-need-to-test-with-5-users/)). Five answers to "what does this company sell?" catch a hero that fails outright (none or one of the five can say) and nothing finer. Comparing two headlines makes the answers a measure, and for a quantitative study NN/g recommends 20 users ([NN/g](https://www.nngroup.com/articles/quantitative-studies-how-many-users/)): about that many per variant. Five people who match the audience is far better than five colleagues; colleagues cannot un-know what the product is.

**Reading the results.**

| Result | Diagnosis | Fix |
|---|---|---|
| Cannot answer Q1 | The headline names a category or a feeling, not a claim | Rewrite the H1 against the specificity rule |
| Answers Q1 but not Q2 | No audience signal | Add the eyebrow, or make the headline audience-first |
| Answers Q1 and Q2 but Q3 is wrong | CTA label is ambiguous, or its visual weight is wrong | Verb + outcome label; check it is the only primary button on the screen |
| Remembers the visual, not the claim | Media is louder than the message — usually an abstract hero illustration | Replace the metaphor with the product |
| Everyone says something slightly different | The headline is genuinely ambiguous. This is worse than being wrong, because the ambiguity is invisible to you | Rewrite and re-test |

This test finds more real problems than any other single thing in this file, and it takes an afternoon.

---

## 3. The squint test

Blur the page — squint, or apply a heavy blur in the browser's dev tools — so the type is unreadable and only shape, weight and contrast survive.

- **Is there exactly one obvious focal point per screen?** Two competing focal points means the reader arbitrates, and arbitration is a cost.
- **Is the primary CTA the highest-contrast element on the first screen?** If a cookie banner, a nav CTA and the hero CTA are all equally loud, none is primary.
- **Do the sections separate?** If bands blur into one column of grey, the boundaries are not doing their job — see the banding rules in `page-architecture.md` §6.
- **Do card rows read as rows?** If the inter-card gap and the intra-card gaps blur to the same weight, the grid reads as one block. This is the `--gap-grouped`-versus-`--gap-tight` failure, and it is extremely common on hand-built marketing pages.
- **Does anything read as a button that is not one?** Filled, rounded rectangles that are not clickable are a real, measurable annoyance.

The squint test is checking hierarchy, which is a design property. Findings here route back to `web-design-studio` — `references/spacing-system.md` for gaps, `references/color-system.md` for contrast — rather than to a copy rewrite.

---

## 4. Scroll-depth reasoning

You are answering one question: **does the order of the page match the order the reader's questions arrive in?**

Walk the page top to bottom and, at each section boundary, write down: *which of the six objections has just been answered, and which one is now open?* (The ladder is in `page-architecture.md` §1.)

Three failure shapes show up:

- **The gap.** An objection goes unanswered for three or more sections. Readers who care about it leave in that interval, and the sections in the interval look like the problem when they are not.
- **The inversion.** Pricing before proof, proof before the reader knows what the product is, features before the problem. Each inversion presents to the reader as "this page is confusing", which they will not be able to articulate in a survey.
- **The dead screen.** A full screenful that answers nothing — usually a decorative band or a restatement. Every dead screen pushes live content further down the attention curve.

**What the eye-tracking evidence actually supports.** NN/g (2018, 120 participants, 130,000+ fixations) recorded roughly **57%** of viewing time above the fold and **74%** within the first two screenfuls, against about 80% above the fold in their 2010 study. The useful reading is not "put everything above the fold" — that has never been what it meant. It is: **attention decays steeply with depth, and the decay curve is what you are budgeting against.** Placing something deep is a decision to have fewer people see it. Sometimes that is exactly right; it must be a decision.

**If you have scroll-depth analytics**, look for the screen where the drop is steepest and read the section immediately *above* it. The drop-off is usually caused by the section people just finished, not the one they did not reach.

---

## 5. The friction inventory

List **every field, click, decision, wait and unknown** between the reader's intent and a completed conversion. Number them. The list itself is usually the finding.

A worked one, for a plugin trial:

```
 1  Click "Try free"                              click
 2  Modal: choose macOS / Windows                 decision   ← detectable, should not be asked
 3  Email field                                   field
 4  Password field                                field      ← needed at all? magic link?
 5  Confirm password                              field      ← delete; use a show-password toggle
 6  "Company" field (optional but present)        field      ← delete; optional fields still cost
 7  Newsletter checkbox, pre-ticked               decision   ← untick it. Pre-ticked is sneaking
 8  Submit                                        click
 9  "Check your email"                            wait       ← unknown duration, no fallback
10  Open mail client, find email                  context switch  ← the single biggest drop here
11  Click verify link                             click
12  Land on account page, find download           decision   ← should be an automatic download
13  Download 420 MB                               wait       ← state the size before step 1
14  Install, authorise with licence file          decision   ← the second biggest drop
```

Fourteen steps, of which perhaps six are unavoidable. For each one ask, in order:

1. **Can it be deleted?** (Steps 5, 6 here.)
2. **Can it be deferred until after the conversion?** (Company name, at first use.)
3. **Can it be defaulted or detected?** (Step 2 — platform is in the user-agent.)
4. **Can it be made faster?** (Step 13 — is 420 MB really necessary for a trial?)
5. **If none of the above, can the cost at least be made visible up front?** An expected wait is a fraction of the cost of a surprise one.

**Context switches are the expensive ones.** Step 10 leaves your site entirely. Every step that requires the reader to go somewhere else and come back is where the largest single drops live. Email verification before first use is the classic: consider verifying *after* the user has experienced value, not before.

**The inventory also produces the copy.** Every unavoidable step is something the friction-reducer line under the button should have warned about. "No card. 420 MB download. Licence arrives by email."

---

## 6. Form design for conversion

The highest-density source of real evidence in this whole field, because forms have been studied to death. Use it.

**Field count.** Baymard's checkout research finds the average US checkout shows **14.88 form fields** by default (23.48 form elements), where an ideal flow needs **7–8**. The generalisable principle is not the numbers, it is the mechanism: **every field is a decision, a keystroke and an opportunity to abandon, and the ones you cannot justify are pure loss.** Baymard's own abandonment research (a documented ~**70%** average across 50 studies) puts *required account creation* and *an overly long or complex checkout* among the top stated reasons. On a landing page, the equivalent is a signup form asking for company size before the product has been seen.

**The procedure.** For each field: *what breaks if I delete this?* If the answer is "our CRM has a blank column", delete it. Marketing's reporting convenience is not worth a percentage point of signups; the data can be collected later, in-product, from someone who has already converted.

**Optional vs required.** Optional fields are not free — the reader still reads them, still decides, still slows down. Delete optional fields rather than marking them optional. If one must stay, mark **optional** explicitly rather than marking everything else required; asterisks require a legend, and legends are read by nobody.

**Input types and autofill.** This is free conversion and it is skipped constantly.

```html
<input type="email"  name="email"      autocomplete="email"
       inputmode="email" autocapitalize="off" spellcheck="false">
<input type="tel"    name="phone"      autocomplete="tel">
<input type="text"   name="cc-number"  autocomplete="cc-number" inputmode="numeric">
<input type="text"   name="postal"     autocomplete="postal-code">
<input type="password" name="new-pw"   autocomplete="new-password">
```

The right `type` and `inputmode` change the mobile keyboard, which changes the number of taps. `autocomplete` with the correct token lets the browser and password manager fill the form in one gesture. Breaking autofill — with a custom component that is not a real `<input>`, or with `autocomplete="off"` on a personal-details field — is one of the most expensive self-inflicted wounds available, and it is invisible on desktop where you tested it.

**Labels.** Always a real `<label for>`, always visible, above the field. Placeholder-as-label fails the moment the user types (the label vanishes exactly when it is needed for review), fails contrast, fails autofill review, and fails screen readers. Label → input is `--gap-tight`; field → field is `--gap-grouped`; the 2× ratio is what binds each label to the right input.

**Validation timing.** Validate on **blur**, not on every keystroke: validating as the user types shows an error for an email address they have not finished writing, and premature errors train the reader to ignore all errors. On submit, move focus to the first error and summarise the errors at the top of the form. Keep everything the user typed. Bind the message with `aria-describedby`, set `aria-invalid="true"`, and never signal with colour alone.

**Error recovery.** The rules in `copy-patterns.md` §9 apply, plus: never clear a field on error (especially passwords and card numbers), never lose the rest of the form, and if the failure is on your side say so explicitly — a reader who believes they made the mistake tries once more; a reader who believes you broke leaves without resentment and often comes back.

**Multi-step vs single.** A long form split into steps with a visible stepper usually feels shorter and completes better, because each screen is a small commitment and progress is legible. But every step boundary is a place to leave. Split when the sections are genuinely different kinds of information (contact / project / budget); never split a five-field form to look modern.

**Tap targets.** Every input, button and checkbox at `min-block-size: var(--tap-min)` (44px). Check it at `data-density="compact"`, which is where floors get breached. The 44px is the suite's policy; WCAG 2.2 AA asks less (§7.1, 2.5.8), so a page that meets AA can still miss the floor.

---

## 7. The technical layer

Performance is a conversion issue for a mechanical reason: a reader who is waiting is a reader deciding whether to keep waiting. Be careful with the headline numbers, though. The widely-cited Deloitte/Google *Milliseconds Make Millions* study (37 sites, 30M+ sessions, late 2019) associated a 0.1s mobile speed improvement with an 8.4% retail conversion lift — but it was **observational**, not a controlled experiment, and fast sites correlate with well-resourced sites. Fix speed on the mechanism, not on a promised multiplier.

**The thresholds** (Google's Core Web Vitals, measured at the 75th percentile of real users):

| Metric | Good | What it is |
|---|---|---|
| LCP | ≤ 2.5s | When the largest above-the-fold element finishes rendering |
| CLS | ≤ 0.1 | How much content moved unexpectedly |
| INP | ≤ 200ms | Responsiveness to the user's interactions |

**LCP — what usually causes a slow one**, roughly in order of how often it is the answer on a marketing page:

1. **The hero image is enormous and unoptimised.** It is usually the LCP element by definition. Serve AVIF or WebP, size it to the layout, `srcset` for density, and set `fetchpriority="high"` on it. Do **not** lazy-load the LCP image — `loading="lazy"` on the hero is one of the most common accidental regressions.
2. **A render-blocking font.** `font-display: swap` (or `optional`), preload the one weight used above the fold, and self-host rather than round-tripping to a third-party origin.
3. **Render-blocking CSS and JS in `<head>`.** Inline the critical CSS, `defer` everything else. A landing page rarely needs a framework at all.
4. **Third-party tags.** Analytics, chat widget, heatmap tool, consent banner, video embed, five pixels. Each is a connection, a script and a risk. Load them after interaction or after load; a chat widget that blocks the hero is costing more than it earns.
5. **Slow TTFB.** Server or origin latency; put a CDN in front of it. Static marketing pages should be served from an edge cache.

**CLS — the two causes worth checking first:**

1. **Images and embeds with no reserved space.** Every image gets `width` and `height` attributes or a `.frame` with an `aspect-ratio`. The frame primitive exists for exactly this.
2. **Font swap reflow.** A fallback with very different metrics reflows the headline when the web font arrives. Match `size-adjust`, `ascent-override` and `descent-override` on the fallback `@font-face`, or accept the fallback for body text.

Also: never inject a banner, cookie notice or promo bar *above* existing content after load. Reserve its space, or overlay it.

**Mobile specifics.** Tap targets ≥ 44px with real spacing between them. No horizontal scroll — check by setting the viewport to 320px, and remember that a full-bleed element built with negative margins will produce horizontal scroll when a scrollbar appears, which is why `.page-grid`'s named-line breakout exists. Respect `prefers-reduced-motion`; the tokens already collapse durations to 1ms. Check the page with the OS at 200% text size.

**Accessibility is part of this pass, not a separate one.** Contrast measured rather than assumed, a visible focus ring on every interactive element, a working skip link, headings in order, real landmarks, and every form control labelled. Route to `web-design-studio`'s `references/accessibility.md`. A page that a keyboard user cannot complete has a conversion rate of zero for that user, which is the most literal conversion problem there is.

### 7.1 The persuasive devices, against WCAG 2.2

Every device this skill writes for meets a WCAG 2.2 criterion ([W3C](https://www.w3.org/TR/WCAG22/), the Recommendation of 12 December 2024), and its usual form fails it. Hold each one to its criterion when you build it and again in this pass. Whether a tool can decide a criterion, and whether this suite's gates do, is in `a11y-audit-runner`'s `references/automation-coverage.md` §3. The last column names the check that runs, or a person where none does.

| Device | Criterion (level) | What it asks of the device | Checked by |
|---|---|---|---|
| A countdown or an "offer ends in" timer that ticks | 2.2.2 Pause, Stop, Hide (A) | Information that updates on its own beside other content can be paused, stopped or hidden, or its updates slowed, unless the updating is essential. Never put the ticking text in a live region: a screen reader would read out every second | A person |
| A held basket, a reserved seat, a session that expires | 2.2.1 Timing Adjustable (A) | The visitor can turn the limit off or set it to at least ten times its length, or is warned and given at least 20 seconds to extend it with a simple action, at least ten times. A real-time event such as an auction, a limit that is essential, and one longer than 20 hours are exempt | A person: no tool knows a limit exists |
| A carousel, a rotating testimonial, a ticker, an animated badge | 2.2.2 Pause, Stop, Hide (A) | Movement that starts on its own, lasts more than five seconds and sits beside other content has a pause, stop or hide control, unless the movement is essential | A person |
| An audio demo that plays on load | 1.4.2 Audio Control (A) | Sound that plays on its own for more than 3 seconds can be paused or stopped, or its volume set apart from the system's. Better: the demo starts when the visitor presses play | axe's `no-autoplay-audio`, in `a11y_runtime` |
| A sticky header or CTA bar; a cookie or promo banner on an edge | 2.4.11 Focus Not Obscured (Minimum) (AA) | A control that takes keyboard focus is never entirely hidden by content the page lays over it | `a11y_runtime`'s `obscured`, down the page and back up |
| An exit-intent, newsletter or discount modal | 2.1.2 No Keyboard Trap (A); 2.4.3 Focus Order (A) | Focus moves into the dialog when it opens, can leave it by keyboard (Esc, or a visible close), and lands back where it was | `a11y_runtime`'s `taborder` for focus caught outside a modal dialog; Esc, the close control and whether the order makes sense, a person: `taborder` presses only Tab, and lets a modal hold focus |
| A price detail or the terms shown on hover | 1.4.13 Content on Hover or Focus (AA) | Esc dismisses it without moving the pointer, the pointer can move onto it, and it stays until dismissed or until its trigger goes | `a11y_runtime`'s `hover`, for a node `aria-describedby` ties to its control |
| A small "No thanks", a close ×, an unsubscribe link | 2.5.8 Target Size (Minimum) (AA) | At least 24 by 24 CSS pixels, or spaced so that a 24px circle centred on each small target crosses no other target and no other such circle. A link inside a sentence, a control with an equivalent elsewhere on the page, a browser's own control and an essential presentation are exempt. The suite's `--tap-min` (44px) is its own policy, stricter than AA | axe's `target-size`, in `a11y_runtime` |
| A pale decline link | 1.4.3 Contrast (Minimum) (AA) | Text at 4.5:1, or 3:1 when large. A decline made hard to read is confirmshaming and a contrast failure at once | axe's `color-contrast`, in `a11y_runtime`; `check_roles.py` for the roles |
| A multi-step signup or checkout | 3.3.7 Redundant Entry (A) | What the visitor gave earlier in the same process is filled in or offered to pick, unless entering it again is essential, is for security, or the earlier value no longer holds | A person |
| A sign-in, or a code or CAPTCHA that proves who the visitor is; the fields a signup asks for | 3.3.8 Accessible Authentication (Minimum) (AA); 1.3.5 Identify Input Purpose (AA) | 3.3.8 holds the steps that authenticate, not account creation: none needs a password remembered, a code transcribed or a puzzle solved unless it offers another way or help (paste and password managers work; a CAPTCHA has a path without a puzzle). Personal fields, at signup and anywhere else, carry `autocomplete` (1.3.5) | `a11y_static`'s `missing-autocomplete` (1.3.5); the rest, a person |
| A toast, "added to basket", a stock count that updates, a success message | 4.1.3 Status Messages (AA) | A message that reports a result without taking focus sits in a live region (`role="status"`, or `role="alert"` for an error) that exists before its text changes | A person |
| A consent banner | 2.1.1 Keyboard (A); 2.4.11 Focus Not Obscured (Minimum) (AA); 1.4.3 Contrast (Minimum) (AA) | It is reachable by keyboard, never hides the focused control, and its reject choice reads as clearly as its accept (the law on the banner itself: §8.1) | `a11y_runtime`'s `taborder` and `obscured`; axe's `color-contrast` |

The critique gate holds the same devices in its layer 8 (`design-critique-gate`'s `references/failure-catalog.md` L8-6), so a page reviewed there and audited here gets one answer.

---

## 8. Instrumentation you need before claiming anything

If you cannot measure it, you cannot say you improved it — and you especially cannot say by how much. The minimum, in priority order:

1. **The conversion event itself**, fired server-side or on a confirmed state change, not on a button click. A click is an intent; a conversion is an outcome, and the gap between them is where the money leaks.
2. **Traffic segmented by source.** An "improvement" that coincided with a change in traffic mix is not an improvement.
3. **Scroll depth**, at 25/50/75/100%. Cheap, and it turns the architecture review from argument into evidence.
4. **Form field analytics** — which field was focused last before abandonment. This single measurement usually identifies the problem field outright. Record the field, never what was typed in it (§8.1).
5. **Core Web Vitals from real users** (field data, via `web-vitals` or the Chrome UX Report), not just lab numbers from Lighthouse. Lab data is a debugging tool; field data is the truth.
6. **Error events.** Failed submissions, validation failure rates per field, JS exceptions. A 4% JS error rate on one browser is invisible in every other metric.

Then: **wait for a baseline before changing anything.** Two to four weeks of the current page, so weekday/weekend and campaign cycles are inside the baseline. Changing the page and the measurement at the same time produces a number nobody can interpret, and that number will be quoted for two years.

### 8.1 Consent for what you measure

*As of 2026-10-21, and a list to flag for the client's lawyer, as §11.1 is.* Most of the list above stores something on the visitor's device or reads from it, and that needs the visitor's consent before it runs, with the exceptions below.

| Where | The rule | What it means for the list above |
|---|---|---|
| EU | Storing or reading anything on a visitor's device needs their consent, given with clear and comprehensive information, unless it is strictly necessary for a service they asked for ([ePrivacy Directive Art. 5(3)](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02002L0058-20091219)). Consent is a statement or a clear affirmative action (GDPR Art. 4(11)); a pre-ticked box is not one ([Planet49, C-673/17](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:62017CJ0673)); and withdrawing it must be as easy as giving it (GDPR Art. 7(3)) | Analytics, scroll depth, heatmaps, session recordings and form analytics wait for consent. A count of completed orders taken on the server reads nothing from the device |
| UK | Since 5 February 2026, PECR (as the Data (Use and Access) Act 2025 amended it) allows storing or reading without consent when the sole purpose is to collect statistics about how a site is used, with a view to improving it, when the visitor is told clearly, can object simply and for free, and has not objected, and the data goes to no one but those helping to improve the site ([Schedule A1, paragraph 5](https://www.legislation.gov.uk/uksi/2003/2426/schedule/A1)). Everything else still needs consent | First-party analytics used only to improve the site can run with notice and an opt-out. A tool that uses the data for its own purposes, and an advertising pixel, still need consent |

**Session recordings and form analytics see what people type.** Mask every input by default, and record only what the question needs: the GDPR's data minimisation holds personal data to what is "adequate, relevant and limited to what is necessary" (Art. 5(1)(c)). Never record a password, payment or health field, masked or not.

**The banner is a dark-pattern hotspot of its own.** In a report adopted on 17 January 2023, the EDPB's cookie banner taskforce recorded that most authorities treat a banner with no reject option on the layer that holds the accept button as an infringement, that pre-ticked boxes do not make consent, and that a reject button whose text is unreadable against its background can be manifestly misleading ([EDPB](https://www.edpb.europa.eu/system/files/2023-01/edpb_20230118_report_cookie_banner_taskforce_en.pdf)). So: reject beside accept, with the same weight; nothing ticked in advance; and the reject button held to 1.4.3 like any other text (§7.1).

---

## 9. A/B testing, honestly

This is where most conversion advice quietly stops being true for the companies it is given to.

**The arithmetic.** For a two-sided test at 95% confidence and 80% power, sample size per variant is approximately

```
n ≈ 16 · p(1 − p) / δ²        p = baseline rate, δ = absolute difference you want to detect
```

Work an example. Baseline conversion 3%, and you want to detect a 20% *relative* improvement, so δ = 0.006:

```
n ≈ 16 × 0.03 × 0.97 / 0.006²  ≈  12,900 per variant  ≈  25,800 sessions total
```

At 2,000 sessions a month, that test takes **thirteen months**. By then the traffic mix, the product and the market have all changed, and you have run one test.

**Why most small-site tests are underpowered**, and what goes wrong when you run them anyway:

- **Stopping when it looks significant** inflates the false-positive rate badly. Peeking at a running test and stopping on the first green result is the single commonest way to generate confident nonsense.
- **An underpowered test that "wins" overstates the effect size.** Conditional on reaching significance with a small sample, the observed lift must be large — so the winners you do find are systematically exaggerated. This is why so many reported "27% lifts" do not replicate.
- **Most true effects are small.** Detecting a 3% relative improvement needs roughly 45× the sample of detecting a 20% one. Small sites can only ever detect large effects, which means A/B testing on a small site is a tool for finding *big* changes, not for tuning.
- **Multiple tests multiply false positives.** Five simultaneous tests at α = 0.05 give roughly a 23% chance of at least one spurious winner.

**What to do instead, when you do not have the traffic:**

| Method | What it is good for | Cost |
|---|---|---|
| **Usability testing with five people** | Finding the problems that stop people completing. Qualitative and iterative: five a round surface most issues (NN/g). Not for choosing between two versions, which needs about 20 users per variant | An afternoon a round |
| **Five-second tests** | Whether the message lands at all | An hour |
| **Sequential qualitative review** | Ship the better-argued version, watch the qualitative signals — support tickets, replies, the questions people ask in the demo call | Free |
| **Session recordings and form analytics** | Where people stall, which field kills the form. With consent where the law asks for it, and every input masked (§8.1) | Cheap |
| **Fixing the things that are definitely broken** | Broken autofill, a 4s LCP, an unanswered objection, a missing price. None of these need a test | The work itself |
| **Shipping the better-argued version** | When you cannot measure, argue. Write down why you believe the change helps, ship it, and keep the note | Free |

**The honest framing:** on a low-traffic site, A/B testing is not a measurement instrument, it is a coin-flip with a progress bar. Say that plainly rather than running a test that cannot answer the question. Big, argued changes shipped in sequence, with the reasoning written down, beat a year of underpowered tests — and the written-down reasoning is what makes the next change better, which is the compounding part.

**When testing *is* worth it:** you have the traffic (tens of thousands of sessions per variant within a few weeks), the change is large and directional, you fixed the sample size and duration *before* starting, you run one test at a time, and you can live with the answer being "no difference" — which is the most common true answer and the one nobody plans for.

### 9.1 Price tests

A price test tests the business, not the page, and it carries duties a headline test does not. Test the packaging before the price: what each plan includes, monthly against annual, the order the plans are shown in, which one is marked as recommended. Every visitor still sees one price list, so none of what follows applies.

If you test the price itself, flag four things for the client's lawyer before it starts (§11.1):

1. **Personalisation.** In the EU a price set for a visitor by automated decision-making must say so (Consumer Rights Directive Art. 6(1)(ea)). Whether a random split counts is a question for the lawyer, not for this skill.
2. **The lowest price shown is on the record.** An EU "was" price must be the lowest the trader applied in the 30 days before a reduction (Price Indication Directive Art. 6a), and a test arm's lower price may count. Log every arm's price with its dates.
3. **The checkout charges what the page showed,** in every arm, with every mandatory fee in the first price shown (s. 230 of the UK's DMCC Act).
4. **Customers compare.** Someone who paid more will meet someone who paid less. Decide before the test what you will do then: refund the difference, or do not run it.

**Revenue per visitor is noisier than conversion.** A price change moves the conversion rate and the order value in opposite directions, so the measure that decides a price test is revenue per visitor, and it needs more traffic. The formula above is the binary case of n ≈ 16 · σ² / δ², where σ² is the measure's variance. A conversion rate's is p(1 − p). Revenue per visitor's, when the orders have mean μ and a standard deviation c times μ, is p · μ² · (1 + c² − p). To detect the same relative change, that is (1 + c² − p) / (1 − p) times the visitors: about twice when order values vary as much as their mean (c = 1), and five times at c = 2. The example above, a 3% baseline and a 20% relative change, needs about 12,900 visitors per variant on conversion and about 26,300 on revenue per visitor at c = 1.

---

## 10. The report

Deliver findings in this shape. Ranked by expected effect over effort, and honest that "expected" is judgement until there is data.

```
FINDING     One sentence. What is wrong.
EVIDENCE    What you observed — test result, measurement, the specific line on the page.
MECHANISM   Why it costs conversions. If you cannot state the mechanism, downgrade it to a hunch.
FIX         The specific change, at the system level, not a local patch.
CONFIDENCE  High (measured / evidence-backed) · Medium (mechanism is sound, unmeasured)
            · Low (heuristic, worth trying, do not promise a number)
EFFORT      Hours, days, or weeks.
```

Separate the certainties from the guesses explicitly, and never launder a guess by putting a number on it. "The hero does not say what the product is; five of five testers could not describe it" is worth more to the client than any predicted percentage, because it is true and it is actionable.

Close the report with the design gate:

```bash
python -m scripts.audit_design PATH        # from web-design-studio
```

---

Related: `references/page-architecture.md` (the ladder the scroll review is measured against), `references/copy-patterns.md` (the rewrites this audit prescribes), and `web-design-studio`'s `references/accessibility.md` and `references/review-checklist.md` for the design-side gate.

---

## 11. Dark patterns, as the law names them

These have names because regulators gave them names. *As of 2026-10-07:* in the **EU**, dark patterns fall under the Unfair Commercial Practices Directive — misleading actions and omissions (Arts. 6–7), aggressive practices (Arts. 8–9), and the Annex I blacklist, which includes falsely stating a product is available for a very limited time. The **Digital Services Act Art. 25** binds only providers of online platforms, and its paragraph 2 says the prohibition "shall not apply to practices covered by Directive 2005/29/EC or Regulation (EU) 2016/679" ([Art. 25](https://eur-lex.europa.eu/eli/reg/2022/2065/oj/eng)): for an ordinary company's site it adds nothing to the UCPD. A **Digital Fairness Act** is announced, not proposed: the European Parliament's legislative train lists it as "Announced", with an indicative Q4 2026 ([EP](https://www.europarl.europa.eu/legislative-train/theme-protecting-our-democracy-upholding-our-values/file-digital-fairness-act)). In the **US**, the FTC has brought dark-pattern and negative-option cases under the FTC Act and ROSCA, which requires clear disclosure of material terms, express informed consent, and a simple cancellation mechanism. (Be precise about this one: the FTC's 2024 "click-to-cancel" Negative Option Rule was **vacated** by the Eighth Circuit in July 2025, and the FTC restarted rulemaking in early 2026 — so the specific rule is not in force, but ROSCA and Section 5 enforcement are, and several US states have their own automatic-renewal statutes. "The rule got struck down" is not a defence.)

### 11.1 The UK and EU rules to flag for legal review

*As of 2026-10-21.* This is a list of what to flag to the client's lawyer, not legal advice: a page that does one of these gets a line in the report and a referral, never a verdict (client-presentation-builder's `objection-handling.md` §5). In the UK the rules are the Digital Markets, Competition and Consumers Act 2024 ([DMCC Act](https://www.legislation.gov.uk/ukpga/2024/13/part/4/chapter/1)), whose unfair-practices chapter has been in force since 6 April 2025. Under it the CMA fines directly, up to 10% of a trader's turnover or £300,000, whichever is higher ([s. 182](https://www.legislation.gov.uk/ukpga/2024/13/section/182)). In the EU they are the consumer directives the 2019 Omnibus Directive amended.

| What the page does | UK | EU | What to flag |
|---|---|---|---|
| Shows reviews or testimonials | Schedule 20, paragraph 13 bans submitting a fake review or one that hides its incentive, or commissioning someone to write one, publishing reviews in a misleading way, and publishing them without reasonable and proportionate steps to keep fakes out and take them down | UCPD Annex I point 23b bans saying reviews come from people who used or bought the product without checking, and 23c false or misrepresented reviews; Art. 7(6) makes how the trader checks them material information | Where each review came from, how they are checked, and whether any was paid for or gifted, said beside them |
| Shows a price before fees, delivery or tax | The invitation to purchase carries the total price, with every fee, tax or charge the buyer must pay (s. 230). Adding them later is what the CMA calls drip pricing ([CMA209](https://www.gov.uk/government/publications/price-transparency-cma209/providing-clear-and-accurate-information-about-prices-summary)). The Price Marking Order 2004's selling price includes VAT | The selling price is the final price, including VAT and all other taxes (Price Indication Directive Art. 2) | Every mandatory charge in the first price shown, and VAT in every price shown to consumers |
| Announces a sale against a "was" price | The Act sets no fixed period; a reference price that misleads is a misleading action (s. 226) | The prior price is the lowest the trader applied in the 30 days before the reduction (Price Indication Directive Art. 6a) | The price history behind every "was", and in the EU its 30-day low |
| Shows a price set for this visitor by an algorithm | The Consumer Contracts Regulations 2013 (Schedule 2) carry no matching duty; a price that misleads is still a misleading action (s. 226) | The trader says the price was personalised on the basis of automated decision-making (Consumer Rights Directive Art. 6(1)(ea)); recital 45 of Directive 2019/2161 leaves out dynamic pricing that does not personalise | Whether any price is personalised, a price test's arms included (§9.1) |
| Sells online to EU consumers | — | From 19 June 2026, a withdrawal function labelled "withdraw from contract here", or as plainly, prominently displayed and available for the whole withdrawal period (Consumer Rights Directive Art. 11a, from [Directive 2023/2673](https://eur-lex.europa.eu/eli/dir/2023/2673/oj/eng)) | Where the withdrawal button is, and that it stays reachable |
| Sells a subscription | The Act's subscription rules are not in force. Draft regulations laid in October 2026 would apply them to contracts entered on or after 1 January 2027, if Parliament approves them ([DBT's draft guidance](https://www.gov.uk/government/publications/subscription-contracts)) | The UCPD and the Consumer Rights Directive's information duties apply as for any sale | Renewal terms beside the button, reminders before it bills, a way out as easy as the way in; recheck the UK date before relying on it |

The drip-pricing row in SKILL.md's ethics boundary is there for the reason the law is: extra costs are the commonest reason US shoppers give for leaving a checkout, named by 40% of them once those "just browsing" are set aside ([Baymard](https://baymard.com/lists/cart-abandonment-rate)).

---

## 12. The ranking that holds up most often

1. The page does not say what it is within one screen. *(Rewrite the hero. Costs an afternoon, changes everything downstream.)*
2. An objection is unanswered and the reader hits the CTA without an answer. *(Add the section. Usually FAQ or pricing.)*
3. The form asks for more than the next step requires. *(Delete fields. The cheapest change on this list.)*
4. The proof is generic. *(Get one real, attributed, specific testimonial. Costs an email.)*
5. LCP is slow because the hero image is unoptimised. *(Half a day, mechanically certain.)*
6. Everything else.

Button colour is not on the list. It is not that colour never matters — contrast and visual hierarchy matter a great deal, and `web-design-studio`'s `references/color-system.md` owns that — but "change the button to orange" as a *conversion* intervention is the most-repeated piece of folklore in this field and the least supported.
