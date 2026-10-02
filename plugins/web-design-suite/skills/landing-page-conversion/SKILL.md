---
name: landing-page-conversion
description: Write and structure landing, pricing and product pages, from positioning to section order and copy, audited for conversion. Honest persuasion only. Not for visual critique (design-critique-gate).
---

# Landing Page Conversion

> **Running the scripts** — by path, from the user's project root, so `src/`
> means the project's `src/` and every output lands in the project, never
> inside this plugin:
>
> ```bash
> python "${CLAUDE_PLUGIN_ROOT}/skills/web-design-studio/scripts/audit_design.py" src/ --strict
> ```
>
> The commands below are written `python -m scripts.<name>`. That form is for a project that
> has copied the scripts into its own `scripts/` folder, as CI and git hooks
> do; when you run one here, use the path form.
> From sibling skills: `${CLAUDE_PLUGIN_ROOT}/skills/web-design-studio/scripts/audit_design.py`.

The sibling skill `web-design-studio` owns **form**: tokens, spacing, architecture, navigation, the audit gate. It says nothing about what a page should *say* or in what order. That omission is deliberate, and this skill is the missing half.

A page that converts is not a well-designed page with persuasive words dropped into it. It is an argument, sequenced, and then given a body. Get the argument wrong and no amount of spacing discipline rescues it — you have built a beautiful vehicle for a claim nobody wanted.

---

## The one principle

> **Message before layout. You cannot choose a section order until you know what the page is arguing, and you cannot write a hero until you can say who it is for and what it replaces.**

This inverts how most landing pages get built. The usual order is: pick a template, fill the boxes, write copy to fit the boxes. That produces a page whose structure was decided by a template author who had never heard of the product, and whose copy was constrained to fit a 60-character slot.

The order here is the reverse: **positioning → message hierarchy → architecture → copy → layout → audit.** Layout is phase 5 of 6. By the time you open a stylesheet, every decision it has to express is already made, which is also why the markup goes on-system from the first commit rather than being retro-fitted.

The diagnostic that proves this matters: when a page "isn't converting," the cause is almost never the button colour. It is that a visitor got four screens in and still could not tell what the thing *is*, or who it is for, or what it replaces in their week. Those are message failures. They are invisible to a design review and obvious in a five-second test.

---

## The ethics boundary

**This skill writes honest persuasion. It declines deception, and offers the honest version instead.**

Honest persuasion is: making a true claim clearly, in the order a reader can absorb it, with real evidence attached, and asking plainly for the next step. That is the entire job. Everything below is outside it.

| Declined | What it actually is | The honest alternative |
|---|---|---|
| Invented testimonials, made-up customer names, stock-photo "customers" | Fabricated evidence | Ask the user for three real customers. If there are none, say "we're new" and use a founder's note, a public build log, or a money-back guarantee |
| Statistics with no source ("increases productivity 47%") | Fabricated evidence | Measure it, or state the mechanism without a number |
| Countdown timers that reset on reload; "3 people are viewing this"; permanent "ends tonight" | Fake scarcity / false urgency | A real deadline with a real date, or no urgency device at all. A launch price that genuinely ends is worth more than a timer nobody believes |
| Confirmshaming ("No thanks, I don't want more revenue") | Coercive framing | A neutral decline: "Not now" |
| Ads or affiliate blocks styled as editorial content | Disguised advertising | Label it. A visible "Sponsored" costs less than the trust it protects |
| Cancellation buried, phone-only, or behind a retention maze | Obstruction / roach motel | Cancel in the account page, in the same number of clicks it took to subscribe |
| Pre-ticked upsells, sneaking items into a cart, hidden auto-renew | Sneaking | Opt-in, unticked, with the renewal terms next to the button |
| "Free" that is a trial with stored card and no reminder | Bait / hidden cost | Say "14-day trial, card required, we email you 3 days before it bills" |

These have names because regulators gave them names; the EU and US law behind each is in `references/conversion-audit.md` §11.

**The practical argument, which matters more for a small company than the legal one.** A dark pattern converts someone who did not want the thing. You now own a refund, a chargeback, a support ticket, a public review, and one person who tells their peers. For a plugin company selling to a few thousand producers, or an agency whose pipeline is referrals, the audience is small enough that reputations are single-threaded. A burned prospect costs more than a converted one is worth, and the arithmetic does not improve at scale — it just takes longer to show up.

If a user asks for one of these directly, do not lecture. Name what it is in one line, produce the honest alternative that serves the same goal, and move on.

---

## Evidence discipline

Conversion writing is full of confidently-stated folklore, most of it a real finding from one company's site generalised into a law. Mark what you are standing on:

**Real, and citable by name.** The Baymard Institute's checkout and form research. Nielsen Norman Group's eye-tracking on scroll and attention. NN/g's argument that five participants surface most usability problems in a qualitative study. Google's Core Web Vitals thresholds (LCP ≤ 2.5s, CLS ≤ 0.1, INP ≤ 200ms at the 75th percentile). WCAG 2.2 AA. The figures worth quoting from each, with what they measure, are in `references/conversion-audit.md`.

**Correlational, so do not state it as causation.** Deloitte and Google's *Milliseconds Make Millions* study associated faster mobile pages with higher retail conversion, but it was observational monitoring, not a controlled experiment (`references/conversion-audit.md` has its numbers). Faster sites also tend to be better-resourced sites. Speed is worth fixing on mechanism alone; do not promise the number.

**Practitioner heuristic — useful, not evidence.** "Above the fold" as a hard rule. Specific button colours. Urgency devices. Optimal word counts. "Long pages convert better" and "short pages convert better" in equal measure. Say "this is a heuristic" out loud when you use one, and prefer the mechanism ("a reader who cannot tell what this is will not scroll") over a borrowed statistic.

**The rule.** Before stating a specific number, verify it. If you cannot find the source, cut the number and state the mechanism instead. A hedged fake statistic is still a fake statistic — hedging launders it rather than fixing it.

---

## Routing: what was actually asked

Most requests arrive as a symptom, not a phase number. Route from the symptom.

| What they say | What it usually is | Start at |
|---|---|---|
| "Build me a landing page for X" | Nothing exists; positioning may be unsettled | Phase 1 |
| "Write my hero section" | A hero cannot be written in isolation — it is the compressed form of the whole argument | Phase 1, then 4 |
| "Why isn't this page converting?" | A message failure that looks like a design failure | Phase 6 conversion pass, then back to 1 if positioning fails |
| "Our bounce rate is terrible" | Either the page does not match the ad/search intent that brought them, or the first screen does not say what it is | Phase 6 five-second test |
| "Make this copy punchier" | Usually "make it more specific", which is the opposite of punchier | Phase 4, specificity rule |
| "Rewrite the pricing page" | Plan naming, anchoring, and the "contact us" decision | Phase 4, pricing section |
| "People sign up and never activate" | Not a landing-page problem. Say so — the page sold something the product does not yet deliver on first run | Report the mismatch, do not paper over it |
| "Add a countdown timer / some urgency" | See the ethics boundary. Offer the real-deadline version | Ethics boundary |
| "Audit this URL" | Existing page | Phase 6, both passes |

Two things worth refusing early, politely. A request to write a hero when nobody can say who the product is for produces a confident sentence about nothing; ask the positioning question first. And a request to optimise a page whose product promise is unclear is a request to make an unclear promise louder.

---

## What this skill produces

Unless told otherwise, finish with: the filled-in `MESSAGE_BRIEF.md`, the ordered section architecture with a one-line justification per section, the full page copy block by block, the markup in layout primitives, `page-sections.css` adapted to the project, and the audit results with fixes ranked by expected effect over effort. State every assumption you had to make about the audience at the top, because those are the assumptions a real test would attack first.

---

## Workflow

Work the phases in order. Each phase's output is the next phase's input; skipping ahead is how you end up rewriting a hero six times because the positioning was never settled.

### Phase 0 — Four inputs, before anything

Ask, or decide and state the assumption. Each one changes the page, not just the wording.

| Input | Why it gates everything after it |
|---|---|
| **Who is arriving, and from where?** Ad, search, newsletter, a post, a podcast mention, a direct link from a DAW's plugin manager | The page must continue the sentence the source started. A page that does not visibly match the ad that produced the click reads as the wrong page, and no amount of copy quality survives that |
| **What is the one action?** Buy, trial, demo, waitlist, download, book a call, install | Decides the whole architecture. A waitlist page and a trial page answer *different* objections in a different order |
| **What happens immediately after the click?** Card form, 400MB download, a 12-field enterprise form, a calendar picker | This is the friction the page has to pre-pay for. Copy that ignores a heavy next step converts clicks and loses people one screen later, which looks like a good page and is not |
| **What proof exists today?** Real customers, real numbers, a public demo, nothing yet | Decides whether the proof sections are real or must be replaced with mechanism, transparency and guarantee. Never with invention |

The fourth question is the one that most often changes the plan. A pre-launch audio plugin with no users cannot run a testimonial wall, and the honest substitutes — an audio demo you can A/B in the browser, a signed beta-tester quote, a public changelog, a 30-day refund with no conditions — outperform a fabricated one, because a reader in this market has seen the fabricated version a hundred times.

### Phase 1 — Positioning first

You cannot write a hero until you can complete this sentence. If the user is present, ask. If not, draft it, state it at the top of your output as an assumption, and proceed.

> For **[a specific person in a specific situation]**, **[product]** is the **[category]** that **[the one thing it does better]**, unlike **[the thing they use today]**.

The last clause is the one people skip and the one that does the most work. Every product replaces something — a competitor, a spreadsheet, a freelancer, a manual process, or doing nothing. Naming it tells the reader which mental shelf to put you on, and a reader who cannot shelve you leaves.

**The specificity test.** Read the statement back and ask, for each blank: *could a direct competitor put their name in this sentence and have it still be true?* If yes, the blank is not doing work.

| Blank | Fails the test | Passes |
|---|---|---|
| Who | "creators", "teams", "businesses" | "mixing engineers who deliver 3–10 client stems a week" |
| Category | "a platform", "a solution" | "a mastering-chain plugin", "a stem-separation service" |
| One thing better | "faster, easier, better" | "matches a reference track's tonal balance in one pass" |
| Replaces | "manual processes" | "an hour of A/B-ing against a reference in the DAW" |

Two more rules. **One "one thing."** A statement with three differentiators has none — the reader remembers whichever they read last. And **the replacement must be something the reader actually does today**, not a competitor they have never heard of; "unlike [obscure competitor]" teaches the reader that a category exists and then sends them to Google.

Write it into `assets/MESSAGE_BRIEF.md` §1 before continuing. If you cannot fill it in, that is the finding — stop and say so. A page cannot fix unresolved positioning, and building one anyway just ships the confusion at scale.

### Phase 2 — Message hierarchy

A landing page makes **one claim**. Everything else exists to make that claim survivable.

```
THE CLAIM            one sentence, the thing you want remembered
  SUPPORT 1            why the claim is true
    PROOF                the evidence a sceptic would accept
  SUPPORT 2
    PROOF
  SUPPORT 3
    PROOF
```

Three supports, because two reads as thin and four reads as a list nobody finishes. Each support gets exactly one proof, and the proof has to be something a sceptic would accept: a number you can source, a named customer, a demo they can run, a spec, a guarantee with terms. "Trusted by thousands" is not a proof; it is the claim repeated in a lower voice.

A filled-in one, for an audio plugin:

```
CLAIM     Match your mix to a reference track's tonal balance in one pass.
  S1        It listens to both and shows you the difference, band by band.
    P        Interactive demo: drop in any two files, see the curve, in the browser.
  S2        The correction is a transparent linear-phase EQ, not a preset.
    P        Spec: 32-band linear-phase, < 0.1 dB ripple, latency reported to the host.
  S3        It runs on the session you already have open.
    P        VST3 / AU / AAX, macOS 12+ and Windows 10+, Apple silicon native.
```

Note what every proof has in common: a sceptic can check it without trusting you. That is the test.

Write this before any layout exists. It is the page's outline, and the section order in Phase 3 is derived from it rather than invented. If a section you want does not carry a support or a proof, it is decoration — cut it or demote it to the footer.

Template and worked example: `assets/MESSAGE_BRIEF.md`.

### Phase 3 — Page architecture

Sequence the sections to answer objections in the order a real reader raises them:

**what is it → is it for me → does it work → can I trust you → what does it cost → what happens if I'm wrong**

A page that answers these out of order loses people at the gap. Pricing before proof reads as presumptuous; proof before the reader knows what the thing is has nothing to attach to. The failure is not that the information is missing — it is usually all there — but that it arrives after the question has already been abandoned.

| The reader's question | The section that answers it | What happens if it is missing |
|---|---|---|
| What is it? | Hero headline + sub | They leave in under ten seconds. This is the single most common failure |
| Is it for me? | Hero eyebrow, problem statement, audience-named value props | They understand the product and assume it is for someone else |
| Does it work? | Demo, how-it-works, feature deep-dive, before/after | They believe you can do it, not that it will work on *their* material |
| Can I trust you? | Logos, testimonials, case studies, named team, security page | They want it, and will not enter a card |
| What does it cost? | Pricing — visible, with the plan they need identified | They assume the worst price and self-disqualify |
| What if I'm wrong? | Guarantee, trial terms, cancellation path, FAQ, migration story | The CTA is a cliff edge, so nobody steps off it |

Pick the section order from the page-type table in `references/page-architecture.md` §3, then justify every section against the objection it answers. A section that answers no objection is dead weight, and dead weight is not neutral: it pushes the sections that *do* work below the reader's attention budget.

A page is not "too long." It is **unfinished** (an objection goes unanswered) or **padded** (sections that answer nothing). Length is the consequence of the objection list, not a design target.

### Phase 4 — Write the blocks

Hero, value props, proof, objection handling, pricing, FAQ, final CTA. Formulas, worked examples and the failure mode of each are in `references/copy-patterns.md`.

The rule that governs all of them: **concrete beats clever.** A reader scanning a page is doing information foraging, not appreciating wordplay. If a line could be a headline for a different product in the same category, it is not a headline, it is a mood.

Each block has one job, and only one:

| Block | Its single job | Written from |
|---|---|---|
| Eyebrow | Name the audience or the category so the reader can self-select in one glance | Positioning: who |
| Headline | State the claim in the reader's words | Message hierarchy: the claim |
| Sub-headline | Do the work the headline could not — mechanism, scope, or the "unlike" | Positioning: category + replaces |
| Primary CTA | Name the *outcome* of clicking, not the click | The next real step |
| Friction reducer | Remove the unspoken cost of the click ("No card. 20MB download.") | The objection nearest the button |
| Value prop | One outcome, one mechanism, one proof | Supports 1–3 |
| Proof block | Attribute a specific result to a named person about a named objection | The proofs |
| FAQ entry | Answer an objection a sceptic would actually raise, in their words | The objections nobody said out loud |
| Final CTA | Restate the claim and ask once more, for readers who scrolled the whole way | The claim |

Write in this order: claim → sub → CTA → props → proof → FAQ → eyebrow. The eyebrow last, because it is the only line whose job depends on what everything else already said.

### Phase 5 — Wire it to the design system

Now, and not before, express the structure in `web-design-studio`'s layout primitives: the table, markup and rules are in `references/page-architecture.md` §8.

### Phase 6 — Audit

Two passes, both in `references/conversion-audit.md`:

- **Conversion** — five-second test, squint test, scroll-depth reasoning, friction inventory from intent to completion.
- **Technical** — LCP, CLS, render-blocking, form friction, tap targets, and the analytics you need in place *before* you are entitled to claim anything improved.

Then run the design gate:

```bash
python -m scripts.audit_design <path>      # from web-design-studio
```

Law 9 applies here exactly as it does in the studio skill: nothing ships un-audited.

Report findings ranked by **expected effect over effort**, and be honest that "expected" is a judgement, not a measurement, until the page has traffic and instrumentation. The ranking that holds up most often: `references/conversion-audit.md` §12.

---

## Reference routing

Read the file when you hit the decision it covers. Do not read them all up front.

| Read this | When |
|---|---|
| `references/page-architecture.md` | Choosing or ordering sections; deciding page length; one CTA vs many |
| `references/copy-patterns.md` | Writing any line of page copy — headlines, CTAs, props, proof, pricing, FAQ |
| `references/conversion-audit.md` | Reviewing an existing page; form design; LCP/CLS; A/B testing questions |
| `references/worked-example.md` | You want the whole chain on one product before starting your own |
| `references/token-contract.md` | Any CSS decision — the nine laws, three tiers, every token name |
| `assets/MESSAGE_BRIEF.md` | Phases 1–2. Fill it in; it is the deliverable, not a warm-up |
| `assets/page-sections.css` | Phase 5. Drop-in section shells on the layout primitives |

Cross-skill: `web-design-studio` owns `references/spacing-system.md` (any spacing value), `references/layout-composition.md` (the primitives), `references/accessibility.md` (always), and the audit script.
