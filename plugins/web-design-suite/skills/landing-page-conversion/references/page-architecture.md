# Page Architecture

The section-by-section model. Which blocks exist, what each one is *for*, where it sits, what it costs when it is there for no reason, and how it is spaced in real tokens.

Read this after the message hierarchy exists (SKILL.md Phase 2) and before any markup. A section order chosen before the argument is known is a template, and a template is somebody else's argument wearing your logo.

## Contents

1. [The objection ladder](#1-the-objection-ladder) — the ordering principle everything else follows
2. [The section catalog](#2-the-section-catalog) — 13 canonical sections
3. [Sequences by page type](#3-sequences-by-page-type)
4. [Page length](#4-page-length)
5. [One CTA or many](#5-one-cta-or-many)
6. [Rhythm, banding and the scroll contract](#6-rhythm-banding-and-the-scroll-contract)
7. [Anti-patterns](#7-anti-patterns)

---

## 1. The objection ladder

A reader works through six questions, in roughly this order, and stops at the first one that goes unanswered long enough to become annoying:

```
1. What is it?              ──▶  if unanswered: they leave in seconds
2. Is it for me?            ──▶  if unanswered: they assume it is for someone bigger
3. Does it work?            ──▶  if unanswered: interest, no belief
4. Can I trust you?         ──▶  if unanswered: belief, no card
5. What does it cost?       ──▶  if unanswered: they assume the worst and self-disqualify
6. What if I'm wrong?       ──▶  if unanswered: the CTA is a cliff, nobody steps off it
```

**The ordering is not a style choice; it is a dependency graph.** Question 3 has nothing to attach to until 1 is answered — proof of a thing you cannot name is noise. Question 5 reads as presumptuous before 3 and 4: a price is a request for a decision, and a decision requires belief first. This is why "pricing above the fold" advice is wrong for most products and right for a few (see §3, single-product ecommerce, where the reader arrived already knowing what the category is).

**The gap rule.** Readers do not fail at sections; they fail at *gaps*. A page with a superb testimonial wall placed before the reader knows what the product does loses people at the gap between question 1 and question 3, and the testimonials were never read. When a page underperforms, find the gap before you rewrite a section.

**Answering early is free; answering late is not.** Nothing stops question 5 being partially answered in the hero ("From $49, one-time") — an early answer removes a whole class of reader anxiety at zero cost. The failure mode is only ever *late*, or *never*.

**Ordering is per-reader, not per-page, and you cannot have it both ways.** A page serving both "never heard of this" and "sent here by a colleague, ready to buy" has to serve the first order and let the second skip — which is what a sticky header CTA and an anchored pricing link are *for*. That is the honest resolution: sequence for the uninformed reader, and give the informed one a fast path out of the sequence.

---

## 2. The section catalog

Each entry uses the same seven fields so two options can be diffed in ten seconds.

**Job · Include when · Dead weight when · Position · Anatomy · Spacing · Fails when**

### 2.0 The spacing spec at a glance

Every section in this catalog is built from the same five relationships. Learn these five and the per-section specs below read as confirmations rather than new rules.

| Relationship | Token | Why that rung |
|---|---|---|
| Section → section | `--space-subsection` × 2 via `.band` padding | A painted boundary needs more air on each side than an invisible one |
| Section heading group → section body | `--gap-distinct` | The heading leads the section; at anything tighter it reads as a caption on the first card |
| Eyebrow → heading → deck | `--gap-tight` | One group. The whole point of the eyebrow is that it binds to the heading |
| Card → card in a row | `--gap-grouped` | Siblings in one group. Check: 16 ÷ 8 = 2× the internal gap, so the card boundary is unmistakable |
| Button → the line beneath it | `--gap-tight` | The line annotates the button. At `--gap-related` it reads as its own statement and stops doing its job |

The one measurement that catches most errors on a marketing page: **the gap between two cards must be visibly larger than the gap between a card's title and its body.** When they are equal — and on hand-built marketing pages they very often are — the eye cannot find the card boundaries and the row reads as one undifferentiated block of text.

### 2.0.1 Does this section stay?

Run this before adding any section, and on every section of a page you are auditing.

```
1. Which of the six objections does it answer?
     none ................................. cut it
2. Is that objection already answered above?
     yes .................................. cut it, or merge the new specifics upward
3. Does it answer that objection with evidence, or with adjectives?
     adjectives ........................... rewrite it or cut it; it is not a section, it is a mood
4. Would a reader who skipped it be unable to convert?
     no ................................... demote it: a link, an FAQ row, or the footer
5. Does it sit before the objection it answers gets raised?
     yes .................................. move it down; early answers are free, but only
                                            when they are short. A full section answering a
                                            question nobody has yet is a section nobody reads
```

---

### 2.1 Hero

**Job** Answer "what is it" and "is it for me" in one screen, and make the primary ask.
**Include when** Always. There is no page without one.
**Dead weight when** Never dead weight, but frequently *empty*: a hero with a category description and a stock illustration occupies the most valuable screen on the site and answers nothing.
**Position** First. Non-negotiable.
**Anatomy** Eyebrow (audience or category) → H1 (the claim) → sub (mechanism / scope / the "unlike") → primary CTA → friction-reducer line → optional secondary CTA → supporting media (product, not metaphor).
**Spacing** `.cover--partial` inside a `.band`, `.split.split--2-1` for copy-beside-media. Eyebrow→H1→sub as a `.stack--tight` (`--gap-tight`): they are one group. Copy block → CTA cluster: `--gap-separate`. CTA → friction line: `--gap-tight` — the line annotates the button and must not read as a separate statement. Copy pane capped at `--measure-narrow`; a hero sub at `--measure-prose` is too wide to scan at `--type-lead`.
**Fails when** (a) the H1 names a category rather than making a claim; (b) the media is an abstract illustration instead of the product; (c) `--cover-min: 100svh` hides the fact that the page continues — use `.cover--partial`, which is deliberately shorter than a screen precisely so the next section peeks; (d) the hero image is the LCP element and is unoptimised, which turns your best screen into your slowest one.

---

### 2.2 Logo bar / social-proof strip

**Job** Buy the reader's patience for the next four screens. It is a trust *deposit*, not an argument.
**Include when** You have recognisable names, or numbers you can source ("14,000 installs", "used on 40 released records"). Recognisability is relative to the audience: a studio the reader follows beats a Fortune 500 they do not care about.
**Dead weight when** The logos are unrecognisable to this audience, or are "as featured in" directory listings anybody can buy. An unrecognisable logo wall reads as padding and costs a screen.
**Position** Immediately after the hero, or tucked into the hero's lower edge. Late in the page it does nothing — the trust question has already been asked and answered by absence.
**Anatomy** One line of kicker text ("Shipping on records by") + 4–7 marks, monochrome, optically equalised.
**Spacing** `.band--tight` (`--space-block` block padding, not `--space-subsection`) — it is a strip, not a section. `.grid.grid--min-xs` with `--gap-grouped`, or a `.cluster--grouped` centred. Kicker → marks: `--gap-related`. Marks use `.frame--contain`; never crop a mark.
**Fails when** It is styled as loudly as a real section and so reads as a claim rather than a deposit. Also when there are exactly two logos, which reads as *only two*.

---

### 2.3 Problem statement

**Job** Answer "is it for me" by describing the reader's current situation better than they would describe it themselves.
**Include when** The pain is real, specific and currently tolerated — the reader has a workaround they are not thinking about as a problem. This is the section that converts "I didn't know I needed this."
**Dead weight when** The reader arrived *because* they have the problem (search-driven, category-aware, ecommerce). Then it is a screen of telling someone what they already know, and it delays question 3.
**Position** Right after the hero, before value props. It sets up the props as answers.
**Anatomy** A heading naming the situation → 2–4 short concrete instances (not adjectives — instances) → one transitional line to the solution. Optional: a stark before/after pair.
**Spacing** `.center--prose` inside a `.band`. Heading → body: `--gap-related`. Instances as a `.stack--related`. Keep to `--measure-prose`; this is the one section that is genuinely prose.
**Fails when** It is written as agitation ("Are you TIRED of…"). The register is wrong for any technical audience and it signals that what follows will be a pitch rather than a spec. Describe the situation flatly and let it be recognisable; recognition does the work agitation is trying to fake.

---

### 2.4 Value props

**Job** Answer "does it work" at a summary level — the three supports from the message hierarchy, as outcomes.
**Include when** Always, in some form.
**Dead weight when** Written as a feature list. Then it is a spec sheet in the wrong place, and it answers a question ("what does it have") nobody asked yet.
**Position** After the problem statement, before the deep-dives. It is the argument's table of contents.
**Anatomy** Three cards: icon (optional) → outcome-shaped title → one sentence of mechanism → optionally one proof fragment. Three, because the hierarchy has three supports.
**Spacing** `.switcher.switcher--max-3` with `--gap-grouped`. Inside a card: icon → title `--gap-tight`; title → body `--gap-tight`; card inset `--pad-card`. Section header block → card row: `--gap-distinct`, so the heading leads the row instead of floating between it and the previous band. Use `.grid--rows-aligned` (subgrid) if the titles wrap to different heights — otherwise one two-line title shoves its body copy out of alignment with its neighbours.
**Fails when** Four or five props, because then none are primary; or three props that are three restatements of one thing.

---

### 2.5 How it works

**Job** Convert belief-in-principle into belief-in-practice by showing the shape of the work. Answers the unspoken "what will I actually be doing?"
**Include when** The product involves a process the reader cannot guess: a workflow, an integration, a setup, a hand-off. Strong for agencies, API tools, services, anything installed.
**Dead weight when** The product is self-evident on sight (a single-purpose plugin, a t-shirt). Three steps that say "1. Buy it 2. Install it 3. Use it" insult the reader.
**Position** After value props. It is the first *concrete* section and it earns the deep-dives that follow.
**Anatomy** Three or four numbered steps, each: step number → verb-led title → one line → optionally a small screenshot. Four is the ceiling; a five-step process reads as effortful, which is the opposite of the intended effect.
**Spacing** `.switcher.switcher--max-3` for horizontal steps, or `.stack--distinct` of `.split.split--1-2` rows for a vertical walkthrough. Number → title `--gap-fused` (they are one thing); title → body `--gap-tight`; step → step `--gap-grouped`. Step numerals take `--type-h3` and `--fg-accent`, never a decorative circle that costs a tap target's worth of space and says nothing.
**Fails when** The steps describe your internal process rather than the reader's experience. "We analyse your requirements" is your step; "You send one stem" is theirs.

---

### 2.6 Feature deep-dives

**Job** Answer "does it work" in detail, one support at a time, for the reader who is now leaning in.
**Include when** The product has 2–4 capabilities that each need a paragraph and a picture, and a scanner has already been served by the value props above.
**Dead weight when** Every feature gets a row. Six alternating image/text rows is the single most recognisable "we ran out of argument and kept scrolling" pattern on the web.
**Position** After how-it-works. This is where a long page earns its length — a reader here is qualified and reading, not scanning.
**Anatomy** Per row: eyebrow → H3 → 1–2 sentences → optional bullet list of specifics → optional inline link to docs → media showing the actual interface. Alternate the media side to keep the eye moving, but keep the *text* alignment constant; alternating text alignment is disorientation, not rhythm.
**Spacing** `.split.split--1-2` / `.split--2-1` alternating, `--gap-separate` between panes, `.subsections` (`--space-subsection`) between rows. Within a text pane: `.stack--tight` for the heading group, `--gap-related` to the body. Media in a `.frame--3-2` with `.frame--rounded`.
**Fails when** The media is a floating browser-chrome mockup at an angle. Show the interface at 1:1 doing the thing the paragraph describes; a reader evaluating a tool is reading your screenshot for evidence, not decoration.

---

### 2.7 Demo / media

**Job** Replace an argument with an observation. The strongest section available when the product can be shown.
**Include when** There is something to *hear*, *see* or *try*: an audio A/B, a 20-second screen capture, an interactive sandbox. For audio software this is usually the highest-value block on the page and it is routinely buried.
**Dead weight when** It is a 4-minute talking-head video. Nobody watches it, it is a large network request, and it usually blocks the LCP.
**Position** As early as it can be understood — often *inside* the hero, otherwise immediately after the value props. A demo below the third screenful is a demo most readers never reach.
**Anatomy** A framed player or sandbox → a one-line caption stating what to listen/look for → a fallback still. Never autoplay with sound. Provide captions and a transcript for video: an accessibility requirement (WCAG 2.2 A/AA), and also how the content becomes indexable and skimmable.
**Spacing** A `.frame` at its default `--frame-ratio: 16 / 9` — the aspect ratio is what stops the page reflowing when the media loads, which is the CLS fix. Caption → frame: `--gap-tight`. Section is `.band--flush` when the media bleeds edge to edge.
**Fails when** It loads eagerly. Poster image + click-to-load keeps the embed's JavaScript off the critical path; a third-party video embed loaded eagerly is one of the most common causes of a slow landing page.

---

### 2.8 Testimonials and case studies

**Job** Answer "can I trust you" with someone who is not you.
**Include when** You have real quotes. Real means: attributed to a named person with a role and a company or project, ideally with a photo and a link.
**Dead weight when** The quotes are generic praise ("Great product, highly recommend!"). Generic praise is worse than no praise — it is the exact texture of a fabricated testimonial, so it costs trust rather than buying it.
**Position** After the deep-dives and before pricing. Trust must exist before a price is a reasonable request.
**Anatomy** Per card: the quote (leading with the *objection it dissolves*, not with the compliment) → name → role → company/project → optional photo, logo, or link to the full case study. Case studies add: situation → what they did → a measurable result.
**Spacing** `.grid.grid--min-sm` with `--gap-grouped`; card inset `--pad-card`, `--elevation-card`, `--radius-lg`. Quote → attribution `--gap-separate` (the attribution is a distinct group, and the gap is what makes the quote read as ended). Avatar → name `--gap-fused`. Quote at `--type-lead`, attribution at `--type-ui` with `--fg-muted`.
**Fails when** Three of them sit in a carousel that auto-advances. A carousel shows one third of your proof and moves it before it is read; a grid shows all three. If you have twelve, use a `.reel` — it is honest about its overflow — or a wall, not a rotator.

---

### 2.9 Comparison table

**Job** Answer "why you and not the thing I'm currently using" for a reader who has explicitly framed it as a choice.
**Include when** The category is crowded and the reader is definitely comparing, or you are replacing a specific well-known workflow. Also strong as *us-vs-the-manual-way* rather than us-vs-a-named-rival.
**Dead weight when** The category is unfamiliar. A comparison table then teaches the reader that alternatives exist, hands them the search terms, and does your competitor's acquisition for free.
**Position** Late — after proof, adjacent to pricing.
**Anatomy** 5–8 rows maximum, chosen as the dimensions the *reader* cares about, not the ones you win on. Include at least one row where you lose or are equal; a table you win 12–0 is read as marketing and discounted entirely. Honest tables are more persuasive precisely because dishonest ones are so common.
**Spacing** A real `<table>` with `--border-subtle` rules, cell padding `--pad-block-sm --pad-inline-md`, header row `--type-label` with `--tracking-caps` and `--fg-muted`. On narrow viewports, do not shrink the type — put the table in a `.reel` or transpose it to stacked cards.
**Fails when** Competitor claims are stale or wrong. Date the table, state what version you compared, and be prepared for the competitor's user to arrive and check.

---

### 2.10 Pricing

**Job** Answer "what does it cost", and identify which plan *this* reader should take.
**Include when** Nearly always, even if the answer is a range. An absent price is not a deferred objection; it is an answered one, answered as "expensive and I will have to talk to someone."
**Dead weight when** Genuinely never on a page whose action is a purchase or a trial. On a pure waitlist page, a price signal ("will be around $79") is still worth a line.
**Position** After proof, before FAQ. The FAQ that follows exists largely to answer the objections the price just created.
**Anatomy** 2–4 plans, one visibly recommended, each: plan name → price with period → who it is for (one line — this is the most-skipped and most-useful element) → 4–6 differentiating features, not the full list → CTA. Plus: billing period toggle if there is one, a plain statement of what happens at the end of a trial, and the refund or cancellation terms in text, not in a tooltip.
**Spacing** `.switcher.switcher--max-3` with `--gap-grouped`; card `--pad-card-lg`, `--radius-xl`, `--elevation-card`, recommended card `--border-accent` and `--elevation-raised`. Inside: name → price `--gap-tight`; price → audience line `--gap-tight`; audience → feature list `--gap-separate`; features `--gap-related`; features → CTA `--gap-distinct`, so the button never reads as another feature row.
**Fails when** All plans look equally good, so the reader has to do comparison work and does not. Recommend one. Also when the difference between plans is a list of 20 checkmarks: the reader cannot find the axis. Name the axis ("by number of seats", "by number of tracks").

---

### 2.11 Objection handling / FAQ

**Job** Answer "what if I'm wrong" — the last-mile objections that stop a ready reader.
**Include when** Always, on any page with a real commitment behind the CTA.
**Dead weight when** It is a support FAQ. "How do I reset my password" belongs in a help centre; on a landing page it takes the slot that belonged to "does this work on Apple silicon."
**Position** After pricing, before the final CTA. It is the last objection sweep.
**Anatomy** 5–8 questions written in the reader's voice, ordered most-blocking first. Each answer opens with the answer, then explains. Include the uncomfortable ones — the ones a sales rep gets asked and a marketing page avoids — because a page that only handles easy objections signals that the hard ones have bad answers.
**Spacing** `.stack--related` of `<details>` inside `.center--prose`. Summary row: `--pad-block-md --pad-inline-md`, `min-block-size: var(--tap-min)`, divider `--border-subtle`. Answer body inset `--pad-well`, `--gap-related` from the summary. Answers at `--measure-prose`.
**Fails when** Everything is collapsed and nothing is open. Consider leaving the top item expanded, or rendering short answers open — a wall of identical closed rows is a wall of work, and search engines and screen readers both do better with the text present.

---

### 2.12 Final CTA

**Job** Ask, once more, of the reader who has read everything and is convinced.
**Include when** Always.
**Dead weight when** Never, but frequently *wasted*: a band containing the word "Ready to get started?" and a button restates nothing and converts nobody.
**Position** Last content section, before the footer.
**Anatomy** Restate the claim in one line (not "get started" — the *claim*) → the CTA with the same verb and label as the hero's → the friction-reducer → optionally the guarantee. A reader here has forgotten the exact wording of the hero; this is where you land it.
**Spacing** `.band--loose` with a distinct surface (`--bg-inverse` or `--bg-sunken`). `.center--intrinsic` so the text stays left-aligned and readable while the block sits on the page's centre line. Claim → CTA `--gap-separate`; CTA → friction line `--gap-tight`.
**Fails when** Its button label differs from the hero's. Two labels for one action makes a reader wonder whether they are two actions.

---

### 2.13 Footer

**Job** Catch the reader who did not convert, and carry the credibility furniture.
**Include when** Always.
**Dead weight when** It has become a sitemap of pages nobody visits. Every footer link is an exit; each one should be a *deliberate* exit.
**Position** Last.
**Anatomy** Product links, company links, legal (terms, privacy, refund policy, cancellation), contact, the low-priority-but-necessary trust signals (company registration, support email, security page). For anything with a subscription, the cancellation path is linked here in plain words — this is both the decent thing and, under ROSCA-style rules, the defensible one.
**Spacing** `.band` on `--bg-sunken`. `.with-sidebar` or a `.grid--min-xs` of link columns, `--gap-separate` between columns, `--gap-related` within one. Column heading `--type-label`, `--tracking-caps`, `--fg-muted`; links `--type-ui`. Legal row `--type-label`, `--fg-subtle`, separated by `--gap-distinct`.
**Fails when** It is bigger than the final CTA. The footer is the place a reader lands after deciding not to decide; it should not compete for their attention on the way down.

---

## 3. Sequences by page type

Each row is a complete section order. `→` is scroll order. Sections in *(parentheses)* are optional and should be justified.

| Page type | Section order |
|---|---|
| **Product launch** (new thing, unknown category) | Hero → Demo → Problem → Value props → How it works → Feature deep-dives → Testimonials → Pricing → FAQ → Final CTA → Footer |
| **SaaS free-trial signup** | Hero (CTA = start trial) → Logo strip → Value props → Demo → How it works → Feature deep-dives → Testimonials → Pricing → FAQ (trial terms first) → Final CTA → Footer |
| **Waitlist / pre-launch** | Hero (CTA = join) → Demo → Problem → What it will do (3 props) → Who is building it → *(Roadmap / public changelog)* → *(Price signal)* → FAQ (when, how much, what happens to my email) → Final CTA → Footer |
| **App / plugin download** | Hero (CTA = download, with platform detected) → Demo (audio or video) → Value props → System requirements & formats → Feature deep-dives → Testimonials → Pricing → FAQ (licence, activation, offline, upgrades) → Final CTA → Footer |
| **Agency / services** | Hero (CTA = book a call) → Client logo strip → Problem → What we do (3 services) → How we work (process) → Case studies *(the deep-dives are the case studies)* → Team → Pricing or engagement model → FAQ (timeline, cost, ownership, what we need from you) → Final CTA → Footer |
| **Single-product ecommerce** | Hero (product, price, buy — all three visible) → Gallery → Key specs → Value props → Reviews → Details & materials → Shipping & returns → FAQ → Final CTA → Footer |
| **Event / webinar registration** | Hero (what, when, who, register) → Who it is for → Agenda → Speakers → *(Past attendee proof)* → Logistics (time zones, recording, cost) → FAQ → Final CTA → Footer |

Three things to read out of that table.

**Ecommerce is the exception that proves the ladder.** Price sits in the hero because the reader arrived already knowing what a pair of headphones is — questions 1 and 2 were answered by the ad they clicked. When the category is known, the ladder compresses at the top.

**Waitlists invert proof and specifics.** With no users and no shipped product, questions 3 and 4 cannot be answered with testimonials, so they are answered with *transparency*: who is building it, in the open, on what timeline. That is the honest substitute and it works, because it is checkable.

**Agency pages replace features with cases.** An agency's deep-dive section *is* its case studies; running both is how a services page reaches 4,000 words of nothing. The proof and the explanation are the same artifact.

---

## 4. Page length

**Long pages are not worse. Unanswered objections are worse.**

The real relationship: length should equal the number of objections × the space each needs. A $29 plugin for an audience that already knows the category needs four sections. A $12,000 annual contract sold to a committee needs twelve, because there are more objections and several of them belong to people who are not the reader.

What the evidence actually supports is thinner than either camp claims. NN/g's eye-tracking (2018, 120 participants, 130,000+ fixations) found ~57% of viewing time above the fold and ~74% within the first two screenfuls, against ~80% above the fold in their 2010 study. Read that correctly: **attention decays sharply with depth, but the cliff is further down than it used to be, and it has always been a decay curve rather than a wall.** Nothing in it says a long page converts worse. What it says is that everything you place deep must earn its depth, because fewer eyes reach it.

Practical consequences:

- **Front-load by objection priority, not by section prettiness.** The thing most readers need to know goes highest, regardless of how good the section below it looks.
- **Every screenful must contain a reason to reach the next one.** An unanswered question, a partial list, a visible section boundary. A screen that resolves completely is a screen people leave on.
- **Deep sections serve qualified readers.** A reader at screen eight is more valuable than one at screen two, so depth is where detail, specs and long-form case studies belong — not where you hide things you would rather not say.
- **Cut sections that answer nothing before you shorten sections that answer something.** Trimming a good section to "reduce length" while keeping a decorative one is the commonest way a page gets shorter and worse.

**The test.** Write your objection list. Map each section to an objection. Any section with no objection is cut. Any objection with no section is added. The resulting length is the correct length, and it is not a number you chose.

---

## 5. One CTA or many

Two different questions get confused here.

**How many distinct actions?** Ideally one. A page asking a reader to buy *and* book a demo *and* join a newsletter has made the reader pick a path, and picking a path is a decision they did not come to make. Every additional action divides attention and dilutes the measurement. If a second action is genuinely needed, make it visibly secondary — a text link, not a second filled button — and make it a *lower-commitment version of the same journey* ("Buy now" / "Try the demo first"), never a different journey.

**How many times do you ask?** As many times as there are natural decision points. This is not a contradiction: one action, repeated. A reader becomes ready at different moments, and the cost of scrolling back to find a button is a real cost that some readers will not pay.

The placement rule:

| Position | Include when |
|---|---|
| Hero | Always |
| After the demo | The demo is the strongest proof you have — some readers are convinced right there |
| After value props | The page is longer than ~4 screens |
| In each pricing card | Always, when pricing exists |
| Final CTA band | Always |
| Sticky header | The page is longer than ~6 screens, or informed readers are a meaningful share of traffic |

**The consistency rule.** Same verb, same label, same destination, every time. "Start free trial" in the hero and "Get started" in the footer look like two offers to a reader who is scanning, and the ambiguity costs more than the extra placement gains.

**Sticky mobile CTA bars.** Legitimate, and a real tax: a fixed bar on a 780px-tall phone viewport permanently removes ~8–10% of the content area, on top of browser chrome. Worth it on a high-commitment page; not worth it on a page with three sections. If you use one, it must not cover the last section's own CTA, and it must respect safe-area insets.

---

## 6. Rhythm, banding and the scroll contract

Section boundaries are a reading aid, not decoration. The reader uses them to decide whether the next block is a new argument or a continuation, and they make that decision peripherally, before reading a word.

**Pick one mode** (`web-design-studio`, `layout.css` §0.2). Most landing pages want **banded**: every section is a `.band` paying `--space-subsection` on both block edges, so a seam measures two of those — slightly more than `--space-section`, which is correct, because a colour change deserves more air on each side than an invisible boundary. Give transparent sections `.band` too; a uniform rule beats two rules.

**Alternate surfaces, do not alternate loudly.** `--bg-canvas` → `--bg-surface` → `--bg-canvas` → `--bg-sunken` gives four distinguishable bands with no colour invention at all. Reserve `--bg-inverse` for exactly one band — usually the final CTA — because its scarcity is what makes it read as the page's emphatic close.

**The heading block is a group.** Section eyebrow → H2 → deck is a `.stack--tight`; that group sits `--gap-distinct` from the section's body. This is the heading-asymmetry rule expressed structurally instead of with margins, and it is what makes a heading lead its section rather than float between two.

**Anchors and sticky headers.** If a header is sticky, in-page anchors land behind it. Fix it with `scroll-padding-block-start` on `:root` and `scroll-margin-block-start` on targets — `.page-shell` already derives that from `--header-block-size`. A JS scroll-offset hack breaks the moment the header's height changes.

**One more scroll fact worth building around:** every section that paints a background must also reserve space for its media. A `.frame` with an `aspect-ratio` reserves the box before the image arrives; without it the section grows on load and everything below jumps, which is CLS, and CLS on a landing page usually manifests as a reader tapping a button that has just moved.

---

## 7. Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| Sections chosen from a template before the message exists | The template's order is someone else's objection ladder. It will be wrong in a way nobody can name |
| A 100svh hero | Hides that the page continues. `.cover--partial` is shorter than a screen on purpose |
| Auto-advancing testimonial carousel | Shows one third of your proof and removes it before it is read. Use a grid, a wall, or an honest `.reel` |
| Six alternating image/text feature rows | Ran out of argument, kept scrolling. Two to four, each carrying a different support |
| Comparison table you win 12–0 | Read as marketing and discounted whole. Include a row where you lose |
| "Contact us for pricing" on a self-serve product | Answers the price objection as "expensive". If you must, publish a floor: "Plans start at $X" |
| Support FAQ on a landing page | Occupies the objection-handling slot with content that handles no objection |
| Trust badges with no referent (generic "Secure" shields) | Reads as the visual grammar of a scam site, because that is where it is most used. Link to the real security page instead |
| Newsletter modal on first scroll | Interrupts question 1 to ask question 6. If you must, trigger on exit intent or on depth, never on arrival |
| Footer larger than the final CTA | The exit is more prominent than the ask |
| Pricing before proof | A price is a request for a decision, and a decision requires belief first |
| Two different labels for the one action | Reads as two offers. Same verb, same label, everywhere |
| A section added because the page "looked short" | Length is an output of the objection list, never an input |

---

Related: `references/copy-patterns.md` (what goes inside each of these blocks), `references/conversion-audit.md` (checking an existing page's architecture against this model), `assets/page-sections.css` (the shells), and `web-design-studio`'s `references/spacing-system.md` §10 for page rhythm and `references/layout-composition.md` for the primitives named throughout.
