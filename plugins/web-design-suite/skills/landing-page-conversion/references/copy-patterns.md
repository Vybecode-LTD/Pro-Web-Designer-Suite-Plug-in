# Copy Patterns

The writing. Formulas, the worked version of each, and what each one fails at — because every headline formula has a characteristic failure and knowing it is what stops you shipping the bad instance.

All examples are drawn from the three markets this skill exists to serve: audio software, AI tools, and agency work.

## Contents

1. [The specificity rule](#1-the-specificity-rule)
2. [Headlines](#2-headlines)
3. [Subheads](#3-subheads)
4. [CTA microcopy](#4-cta-microcopy)
5. [Value props: feature → benefit → proof](#5-value-props-feature--benefit--proof)
6. [Social proof that is actually persuasive](#6-social-proof-that-is-actually-persuasive)
7. [Pricing copy](#7-pricing-copy)
8. [FAQ as objection handling](#8-faq-as-objection-handling)
9. [Empty, error and success microcopy](#9-empty-error-and-success-microcopy)
10. [Voice](#10-voice)
11. [Anti-patterns](#11-anti-patterns)

---

## 1. The specificity rule

> **Concrete beats clever. If the line could belong to a competitor, it is not a line, it is a mood.**

This is the single test that improves the most copy the fastest, and it is mechanical enough to apply without taste.

**The swap test.** Take your headline. Put a direct competitor's name on it. Is it still true? If yes, you have written a category description, and the reader learns nothing from it except that you exist.

| Wrote | Swap test | Verdict |
|---|---|---|
| "Professional audio tools for modern producers" | Every plugin company could ship this | Mood |
| "Match your mix to a reference track in one pass" | Only true of products that do that | Claim |
| "AI-powered insights for your business" | Every AI company on earth | Mood |
| "Turns 200 support tickets into the five bugs causing them" | Specific mechanism, specific output | Claim |
| "We build beautiful, high-performing websites" | Every agency alive | Mood |
| "Design systems for teams shipping on three platforms at once" | Names an audience with a real problem | Claim |

**The second test: could it be argued with?** A claim a competitor could publicly dispute is a claim that carries information. "The most intuitive DAW" cannot be disputed because it means nothing. "Renders a 12-minute master in under 30 seconds on an M-series Mac" can be disputed, checked, and therefore believed.

**Where specificity comes from.** Four sources, in order of strength:

1. **A number you can source** — latency, file size, time saved, throughput, a price.
2. **A named constraint** — "works offline", "no card required", "runs on Apple silicon natively".
3. **A named situation** — "when the client sends stems at 3am", "the fourth revision round".
4. **A named replacement** — "instead of an hour A/B-ing against a reference in your DAW".

If a line has none of these, it has no content. Add one before you touch its rhythm.

**One honest caveat.** Specificity narrows. A headline that names mixing engineers will lose mastering engineers who would also have bought. That trade is usually worth taking — a page that speaks precisely to the core audience outperforms one that speaks vaguely to everyone — but it is a trade, not a free win, and on a page that must serve two genuinely different audiences the right answer is two pages, not one vague one.

---

## 2. Headlines

Eight formulas. Each is a *starting shape*, not a template to fill blindly; the shape's job is to force a decision about what the claim is.

### 2.1 Outcome

**Shape** [Achieve specific outcome] [with a constraint that makes it credible].
**Example** "Match any reference track's tonal balance in one pass."
**Why it works** It is the message hierarchy's claim, said once. The constraint ("in one pass") is what turns a promise into a spec.
**Fails when** The outcome is generic ("Make better music"). Then it is a wish, and the reader supplies their own, less flattering, interpretation.

### 2.2 Replacement

**Shape** [New thing] instead of [the tedious thing they do now].
**Example** "Reference matching without an hour of A/B-ing in your DAW."
**Why it works** Names the thing being displaced, which is the clause most positioning statements skip. It also flatters the reader by describing their current workflow accurately.
**Fails when** The replaced thing is not actually what they do. Get this wrong and the reader concludes you do not know the work — the most expensive impression to create on a technical page.

### 2.3 Audience-first

**Shape** For [specific person in a specific situation]: [what it does].
**Example** "For engineers delivering client stems on a deadline: one-pass reference matching."
**Why it works** Self-selection in three words. Readers who are not that person leave immediately, which is a feature.
**Fails when** The audience is a demographic rather than a situation. "For creators" selects nobody.

### 2.4 Mechanism

**Shape** [Does the thing] by [the specific way it works].
**Example** "Hits your reference curve with a 32-band linear-phase EQ, not a preset."
**Why it works** Technical audiences buy mechanisms. Stating yours signals that you have one, which most competitors' pages do not.
**Fails when** The mechanism is a buzzword ("powered by AI"). A mechanism nobody can evaluate is a claim with extra syllables.

### 2.5 Contrarian

**Shape** [Received wisdom] is [wrong / unnecessary]. [What to do instead].
**Example** "Your reference track doesn't need a mastering engineer to be useful."
**Why it works** Creates a small open loop, and open loops get scrolled.
**Fails when** The contrarian claim is not defended immediately below. A hot take with no follow-through is the copywriting equivalent of a jump scare.

### 2.6 Quantified result

**Shape** [Number] [unit of the thing they care about], [condition].
**Example** "Twelve-minute master rendered in 28 seconds on an M2 Air."
**Why it works** A number is the strongest form of specificity and the hardest to fake credibly.
**Fails when** The number is unverifiable or averaged into meaninglessness ("save up to 10 hours a week"). "Up to" is the tell; readers read it as "not".

### 2.7 Question

**Shape** [The reader's actual internal question]?
**Example** "Why does your mix fall apart on laptop speakers?"
**Why it works** Rare and effective when the question is one the reader has genuinely asked. It borrows their own attention.
**Fails when** The answer is obviously yes or obviously no ("Want more customers?"). Then it is a rhetorical throat-clear that wastes the most valuable line on the page. Use this formula least.

### 2.8 Category creation

**Shape** The [new category name] for [audience].
**Example** "The reference-matching layer for your mastering chain."
**Why it works** When the product genuinely does not fit an existing shelf, naming the shelf is the fastest way to be understood.
**Fails when** The category already exists and you invented a synonym for it. Then the reader has to translate, and translation is friction. Only create a category when the honest answer to "what is it like?" is "nothing, really" — which is rarer than founders believe.

### Selecting between them

| If the reader… | Use |
|---|---|
| Does not know the category exists | 2.8 Category creation, or 2.2 Replacement |
| Knows the category, is comparing options | 2.4 Mechanism, or 2.6 Quantified result |
| Has the problem but not the vocabulary | 2.7 Question, or 2.5 Contrarian |
| Is one of several audiences on a shared page | 2.3 Audience-first |
| Is ready to buy and needs one reason | 2.1 Outcome |

### Length and setting

Two lines at `--type-display` is the practical ceiling; three wraps into a paragraph and stops being a headline. Set the H1 to `--measure-narrow`, never `--measure-prose` — a display-size line at 68ch forces the eye to travel too far to find the line return, and the headline stops reading as one unit. `--type-display` sets the size, weight and `--leading-tight`; its tracking, `--tracking-tighter`, comes from base.css, on the `h1` and on `.text-display`. Set the headline through one of those and add no tracking of your own.

---

## 3. Subheads

The sub-headline exists to do the work the headline could not carry without becoming a paragraph. It has exactly three legitimate jobs, and it should do **one**:

| Job | When | Example |
|---|---|---|
| **Mechanism** | The headline is an outcome and the reader will ask "how?" | "It analyses both files, shows you the difference band by band, and corrects it with a linear-phase EQ you can see and override." |
| **Scope** | The headline is a claim and the reader will ask "on what?" | "Any source material, any genre, at any sample rate up to 192kHz. VST3, AU and AAX." |
| **The unlike** | The headline is a category and the reader will ask "versus what?" | "Not a preset chain and not a mastering service — a tool that shows its working and hands you the controls." |

Rules: one to two sentences, set at `--type-lead` inside `--measure-narrow`, `--gap-tight` from the headline because they are one group. Never restate the headline in different words — the reader notices, and it teaches them that reading the rest is optional. Never introduce a second claim; the page makes one.

---

## 4. CTA microcopy

### The pattern: verb + outcome

A button label names **what the reader gets**, not what they do to a form.

| Weak | Why | Better |
|---|---|---|
| "Get started" | Started at what? Names the effort and not the reward. The most-used and least-informative label on the web | "Start your 14-day trial" |
| "Submit" | Names the form's need, not the reader's | "Send the brief" |
| "Learn more" | Promises reading, which is a cost | "See how the matching works" |
| "Sign up" | Names the obligation | "Create your free account" |
| "Download" | Fine when the file is the point — be explicit about what arrives | "Download the demo (42 MB, macOS)" |
| "Contact us" | Names a conversation the reader has to start | "Book a 20-minute call" |

"Get started" is not forbidden — it is *unfinished*. It underperforms a specific promise for a mechanical reason: the reader is deciding whether the click is worth the unknown that follows, and a specific label collapses the unknown. Every ambiguity you leave in a button is an ambiguity the reader resolves pessimistically.

### First person vs second person

"Start **my** trial" versus "Start **your** trial". You will see the first-person version recommended as a reliable lift, traceable to a single well-publicised split test on one site more than a decade ago. **Treat it as a heuristic with weak external validity, not a rule.** The defensible version of the underlying idea: first person reads as the user's own voice completing a sentence, second person reads as the site addressing the user. First person can sound infantilising on a technical product ("Get my free ebook!") and natural on a consumer one. Pick by register (§10), stay consistent across the page, and do not present it as an evidence-backed decision.

### The friction reducer

The line beneath the button removes the unspoken cost of clicking. It is the highest-leverage twelve words on most pages and it is usually missing.

```
[ Start your 14-day trial ]
No card required · Full feature set · Cancel in one click
```

Write it against the *actual* next screen. If the next screen asks for a card, do not write "no card required" — write "Card required, we email you 3 days before it bills." A friction reducer that lies is a trust bomb with a three-second fuse.

Set it at `--type-ui` with `--fg-muted`, `--gap-tight` below the button so it binds to the button rather than floating as its own statement.

### Secondary CTAs

One primary action. A secondary CTA is a text link or a `--border-default` outline button, never a second filled button, and it should be a lower-commitment version of the same journey ("Buy now" / "Try the demo first"), not a different journey. Two filled buttons of equal weight is a choice the reader did not come to make, and the common response to an unwanted choice is neither option.

---

## 5. Value props: feature → benefit → proof

Features are what it has. Benefits are what changes for the reader. Proof is why they should believe the second thing.

**The ladder.** Take every feature and walk it up until it stops being about the software.

```
FEATURE    32-band linear-phase EQ with automatic curve matching
  ↓  so what?
BENEFIT    Your mix sits in the same tonal space as the record you're chasing
  ↓  so what?
OUTCOME    You stop burning an hour A/B-ing and get the revision back the same day
  ↓  why should I believe you?
PROOF      Interactive demo — drop in any two files and see the curve, no install
```

Write the prop at the **outcome** rung, carry the mechanism in the body line, and attach the proof. Writing at the feature rung produces a spec sheet in the value-prop slot; writing at the benefit rung without the mechanism produces a promise the reader cannot evaluate.

**The finished shape:**

> **Same-day revisions, not next-day**
> Automatic curve matching against any reference, with a 32-band linear-phase EQ you can see and override.
> *Try it on your own files →*

Three lines: outcome, mechanism, proof. Title at `--type-h4`, body at `--type-body` and `--measure-narrow`, proof link at `--type-ui` with `--fg-link`, separated by `--gap-tight` inside the card.

**Two failure modes to watch.** *Benefit inflation* — climbing the ladder past the point where the claim is still true ("ship better records", "grow your career"). Stop at the last rung you can defend. And *undifferentiated benefit* — "saves you time" is technically the outcome of every product ever sold; the mechanism is what makes it yours.

**Three, not five.** The message hierarchy has three supports. Five props means two of them are features that got promoted, or one support got split in half.

---

## 6. Social proof that is actually persuasive

The difference between proof that works and proof that reads as filler is entirely in three properties.

**Specific.** Names a result, a number, or a situation. "Great product!" contains no information; "It caught a phase issue I'd missed on three previous passes" contains a testable claim.

**Attributed.** Name, role, and company or project — ideally with a photo and a link to something real. An unattributed quote is indistinguishable from an invented one, which means a reader treats it as invented, which means it costs you rather than helping.

**About the objection.** The best testimonial does not praise you; it dissolves the specific fear that was blocking the reader. Line them up against your objection list, not against your feature list.

| Objection | A quote that dissolves it |
|---|---|
| "This won't work on my kind of material" | "I run mostly acoustic jazz and it handled a double bass without smearing the low mids." |
| "Setup will eat my afternoon" | "Installed, authorised and on a session inside ten minutes." |
| "It'll be a black box I can't override" | "Every move it makes is on the curve and I can drag any band. I use about half its suggestions." |
| "You're a two-person company, will you still exist next year?" | "Been using it since the 1.0 beta. Three updates since, all free." |

**Lead with the objection clause.** Cut the throat-clearing preamble and start the quote at the part that does work. Most raw testimonial text has two useless sentences in front of one excellent one.

**What to do with no testimonials.** Never invent one. In descending order of strength, the honest substitutes are: a working demo the reader can run on their own material; a public changelog or build log; named beta testers with permission to quote; a founder's note explaining what exists and what does not; an unconditional refund window stated in plain terms. All five are checkable, which is the property that makes proof proof.

**Numbers you can state.** "14,000 installs" if you can count them. "Used on 40 released records" if you can list them. Do not round up into significance — "thousands of producers" reads as fewer than a precise number, because precision is itself a signal.

**Logos** need permission and recognisability. A logo the reader does not recognise is a shape. Add a kicker naming the relationship: "Shipping on records by", "Built with", "Used daily at".

---

## 7. Pricing copy

### Anchoring, honestly

Anchoring is real and it is also where most pricing-page dishonesty lives. The honest uses:

- **Order the plans high to low, or put the recommended plan visually first.** The first number sets the reader's frame for the rest. This is a presentation decision, not a manipulation.
- **Anchor against the replaced cost, not an invented "value".** "One mastering revision round" or "two hours of engineer time" is a real comparison the reader can check. "$4,000 of value for $49" is not a comparison; it is a number you made up.
- **Show the annual saving as a real number**, next to a real monthly price. "$490/yr (save $98)" beats "$40.83/mo billed annually", which is a monthly price the reader will never see on a statement.

The dishonest uses, which this skill declines: a struck-through price that was never charged, a "regular price" that is permanently discounted, and a decoy plan that exists only to make another look reasonable and that no customer has ever bought.

### Plan naming

Names do one job: help the reader self-identify in one glance.

| Approach | Example | When |
|---|---|---|
| **By user** | Solo · Studio · Label | Best default. The reader recognises themselves and stops comparing feature lists |
| **By scale** | Up to 5 seats · Up to 25 · Unlimited | When the axis genuinely is volume. Put the number *in the name* |
| **By tier** | Free · Pro · Enterprise | Conventional and content-free. Acceptable only with a one-line "who it is for" under each |
| **By metal** | Bronze · Silver · Gold | Communicates nothing except that someone reached for a metaphor |

Always add the who-line under the name — one sentence, in the reader's terms: "For one engineer working on their own sessions." It is the most-skipped element on pricing pages and it does more than the feature list beneath it.

### "Contact us"

An enterprise tier with no number is defensible when the price genuinely depends on scope. An entire self-serve product hidden behind "contact us" is not: it answers the price objection as *expensive, and you will have to talk to a salesperson*, and a meaningful share of readers will disqualify themselves rather than find out.

If you must:

- **Publish a floor.** "Custom plans start at $2,400/yr." A floor filters unqualified enquiries, which is the actual reason teams hide prices.
- **Say what drives the price.** "Priced by number of seats and support tier."
- **Say what happens next, with a time.** "A 20-minute call. We send a quote within two business days."

For agency work, publish an engagement range and a typical project shape ("Most design-system engagements run 6–10 weeks, from $18k"). The enquiries you lose are the ones you were going to lose in the second email.

---

## 8. FAQ as objection handling

A landing-page FAQ is not support content. It is the last objection sweep before the final ask, and it should be written from the sales conversation, not the help desk.

**Sourcing the questions.** Ask whoever talks to customers what they get asked in the last five minutes before a yes. Read support tickets from the first week after purchase — those are the things the page failed to say. Read the competitor's subreddit. Every one of those is a real objection in the reader's own words.

**Writing an answer.**

1. Answer in the first sentence. Not context, not a preamble — the answer.
2. Then explain, in two sentences at most.
3. Then link to the depth if there is any.

> **Does it work on Apple silicon?**
> Yes, natively — there is no Rosetta build because there does not need to be. Universal 2 binary, tested on M1 through M4. [Full system requirements →]

**Include the uncomfortable ones.** "What happens to my presets if I stop paying?" "Can I use this on client work?" "What if it doesn't work on my material?" A page that only handles easy questions tells the reader the hard ones have bad answers. Answering a hard question honestly — including "no, and here's what we'd suggest instead" — buys more credibility than any testimonial.

**Order by how blocking the question is**, not by category. The question that stops the most readers goes first.

**Structure.** Real `<details>`/`<summary>` so it works without JavaScript and is findable by in-page search. `.stack--related` of disclosures, summary row at `min-block-size: var(--tap-min)`, dividers at `--border-subtle`, answer body inset `--pad-well`. Consider leaving the first one open.

---

## 9. Empty, error and success microcopy

The three screens that get written last and read most carefully, because the reader is already invested.

**Empty states.** An empty state is a first-run teaching opportunity, not an apology. Name what goes here, why it is worth doing, and give the one action. "No projects yet" is a status; "Drop a session here to analyse it — or try it on our demo stems" is an onboarding step. Set the guidance at `--type-body` with `--fg-muted` inside `--measure-narrow`.

**Errors.** Three components, in order: what happened, why, what to do next. Never blame the user, never expose a stack trace, never say "invalid input" without saying what would be valid.

| Bad | Good |
|---|---|
| "Invalid email" | "That address is missing an @ — check for a typo?" |
| "Error 422" | "We couldn't read that file. It needs to be WAV or AIFF, 16 or 24-bit." |
| "Payment failed" | "Your bank declined the charge. Nothing was taken. Try another card, or your bank may need to approve it." |
| "Something went wrong" | "We couldn't save that. Your text is still here — try again, and if it keeps failing, mail support@ and quote R-4471." |

Errors carry `--fg-danger` on `--bg-surface` (never white on `--bg-danger` for body-length text — a block of reversed error text is hard to read and harder to act on), are bound to the field with `aria-describedby`, and set `aria-invalid="true"`. Colour is never the only signal: an icon or the word "Error" must carry it too (WCAG 2.2 SC 1.4.1).

**Success.** Confirm precisely what happened, and give the next step. "Thanks!" is a dead end. "Your download is starting — we also emailed the licence key to alex@studio.com. Check spam if it isn't there in five minutes." is a confirmation, a record, and a pre-emptive support ticket avoided. Post-purchase and post-signup success screens are the cheapest place on the whole funnel to reduce support load.

---

## 10. Voice

### Match the product's register

Register is set by what the reader is doing when they read you, not by what you would like to sound like.

| Audience | Register | Tells |
|---|---|---|
| Working engineers, producers | Peer-to-peer, technically dense, no hype | Specs in the body copy, formats and versions named, no exclamation marks |
| Developers | Terse, factual, code-first | A code sample above the fold, honest limitations, a link to the source |
| Agency clients (marketing leads) | Confident, outcome-led, business-literate | Named results, timelines, a clear engagement model |
| Consumers | Warm, plain, benefit-led | Short sentences, no jargon, the price where they can see it |
| Enterprise buyers | Measured, risk-aware | Security, compliance, SLA, references, migration path |

The common error is writing every page in the fourth register because that is what "marketing copy" sounds like in the templates.

### Writing for people who distrust marketing language

This is the register that matters most for audio software, developer tools, and any technical buyer — and it is the hardest to fake, because the audience is *specifically trained* to detect it. They have read a thousand product pages and their default assumption is that the page is hiding something.

**What earns trust:**

- **Numbers with units.** "12 ms round-trip at 128 samples" not "ultra-low latency."
- **Named limitations.** "Doesn't do multiband compression — use it in front of one." Stating what you are not is the single strongest trust signal available, because it is costly and nobody fakes it in the costly direction.
- **Versions, formats, requirements.** VST3/AU/AAX, macOS 12+, Windows 10+, sample rates, licence terms, offline authorisation. Missing these reads as evasion.
- **Showing the working.** A screenshot of the actual UI. A curve. A waveform. A code sample. Let them evaluate rather than believe.
- **Letting them try it before they trust you.** A demo build, a browser sandbox, an unconditional refund. The offer itself is the argument.
- **Plain sentences.** Short, declarative, subject-verb-object.

**What burns it instantly:**

- "Revolutionary", "game-changing", "seamlessly", "effortlessly", "unlock", "supercharge", "next-generation", "state-of-the-art."
- "AI-powered" with no statement of what the model does. To this audience it currently reads as *we would rather not say how it works*.
- Adjectives where a number belongs. "Blazing fast" is a confession that you did not measure.
- Stock photos of people who do not do this job.
- Exclamation marks in a spec context.
- Testimonials that sound written by you. They can tell; the giveaway is that the quote uses your product's marketing vocabulary rather than the customer's working vocabulary.

**The rewrite that fixes most of it:** delete every adjective, then add back only the ones you can prove. A page that survives that operation reads as confident. A page that collapses into nothing had no content, and the adjectives were load-bearing — which is the finding, not a styling problem.

---

## 11. Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| Headline that names the category instead of making a claim | Carries no information. A claim can be disagreed with, which is what makes it worth believing |
| Subhead that restates the headline | Teaches the reader that reading the rest is optional |
| "Get started" with nothing after it | Leaves the reader to guess what follows the click, and they guess pessimistically |
| Two filled buttons of equal weight | An unwanted choice; the common answer to an unwanted choice is neither |
| Value props written as features | Answers "what does it have" when the reader is asking "what changes for me" |
| Five value props | The message hierarchy has three supports. Two of those five are promoted features |
| "Up to X%" | Readers parse "up to" as "not". If the number is real, state the condition under which it is real |
| Unattributed testimonials | Indistinguishable from fabricated, so treated as fabricated |
| Testimonials praising you rather than answering an objection | Pleasant, inert. Proof is only proof against a specific doubt |
| "Trusted by thousands" | Rounds a precise number into a vague one, losing the signal that precision carries |
| Struck-through price that was never charged | Fabricated anchor. Also a prohibited practice in several jurisdictions |
| Metal-tier plan names with no who-line | Communicates nothing except that a metaphor was reached for |
| "Contact us" as the only price on a self-serve product | Answers the price objection as "expensive". Publish a floor |
| Support FAQ on a landing page | Occupies the objection slot with content that handles no objection |
| Error text that says what is wrong but not what would be right | Leaves the reader stuck at the exact moment they were trying to give you money |
| Exclamation marks on a technical page | Register mismatch; reads as someone performing enthusiasm at a reader doing work |
| Adjectives standing in for numbers | "Blazing fast" is a confession that nobody measured |
| "AI-powered" with no mechanism | To a technical audience, currently parses as an evasion |

---

Related: `references/page-architecture.md` (where each block sits and why), `references/conversion-audit.md` (testing whether the copy lands), `assets/MESSAGE_BRIEF.md` (the positioning and hierarchy this copy is written from), and `web-design-studio`'s `references/typography.md` for measure, leading and the `--type-*` roles named throughout.

---

## 12. Three things worth saying plainly

**On why pages fail.** Almost every under-performing landing page fails in the first screen, and fails for the same reason: it describes a *category* instead of making a *claim*. "The modern platform for audio production teams" is a category description. "Match any reference track's tonal balance in one pass" is a claim. The first is safe and says nothing; the second can be argued with, which is exactly what makes it worth reading. If your headline cannot be disagreed with, it cannot be believed either.

**On technical audiences.** Producers, engineers and developers have an active allergy to marketing register, and they are the audience for most of this work. The rule is not "write less" — it is **write with the density of a spec sheet and the structure of an argument**. Give the latency figure, the plugin formats, the sample rates, the licence terms, the CPU cost. Every concrete detail buys you the right to make one claim. Every adjective spends that credit without buying anything.

**On what conversion work actually is.** It is not a bag of tricks applied to a finished page. It is the discipline of being specific in public: saying who the product is for, what it replaces, and what it costs, in an order a stranger can follow, with evidence you can defend. That is also, not coincidentally, the same discipline that makes the product clearer to build.
