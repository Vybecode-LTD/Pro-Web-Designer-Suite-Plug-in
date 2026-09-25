# Message Brief — <PRODUCT NAME>

The output of Phases 1 and 2. Fill this in **before** any section order, any copy, and any CSS. It is a deliverable, not a warm-up: the page's architecture is derived from §3, and every line of copy is written from §2 and §3.

Delete the guidance in *italics* as you fill each section in. If you cannot fill a field, write **UNKNOWN** rather than something plausible — an honest gap is a research task; an invented answer is a page built on a guess nobody remembers making.

---

## 0. Context

| | |
|---|---|
| **Date / owner** | |
| **One action this page exists to produce** | *buy · start trial · book call · join waitlist · download · register* |
| **Traffic source(s)** | *the page must continue the sentence the source started* |
| **What happens immediately after the click** | *card form · 400MB download · calendar picker · 12-field enterprise form* |
| **Proof that exists today** | *named customers · numbers you can source · a runnable demo · nothing yet* |
| **Known constraints** | *legal, brand, platform, launch date* |

---

## 1. Positioning statement

> For **__________________________** *(a specific person in a specific situation)*
> **__________________________** *(product)* is the **__________________________** *(category)*
> that **__________________________** *(the one thing it does better)*,
> unlike **__________________________** *(what they use today)*.

### The specificity test

For each blank: *could a direct competitor put their name in this sentence and have it still be true?* If yes, the blank is not doing work.

| Blank | Your answer | Could a competitor claim it? | Rewritten |
|---|---|---|---|
| Who | | ☐ yes ☐ no | |
| Category | | ☐ yes ☐ no | |
| One thing better | | ☐ yes ☐ no | |
| Replaces | | ☐ yes ☐ no | |

Two rules the test does not catch:

- **One "one thing."** Three differentiators means none; the reader keeps whichever they read last.
- **The replacement must be something they actually do today** — a competitor, a spreadsheet, a freelancer, a manual process, or nothing. Naming an obscure competitor teaches the reader that a category exists and then sends them to Google.

### Who this is explicitly *not* for

*Write it down. It is the fastest way to make the "who" specific, and it is often the most useful line in this document.*

---

## 2. The audience, concretely

| | |
|---|---|
| **What they do all day** | |
| **The situation in which they'd look for this** | *the trigger, not the persona* |
| **What they use today, by name** | |
| **What it costs them** | *time, money, quality, risk — in units* |
| **Their vocabulary for the problem** | *the exact words they'd type into a search box* |
| **Their register** | *peer-to-peer technical · developer · business · consumer · enterprise* |
| **What makes them distrust a product page** | *this is the anti-pattern list for this specific page* |

---

## 3. Message hierarchy

One claim. Three supports. One proof per support. Nothing else goes on the page without a reason.

### The claim

> ______________________________________________________________

*One sentence. The thing you want remembered if they read nothing else. It must be arguable — a claim a competitor could publicly dispute is a claim that carries information.*

### Support 1

| | |
|---|---|
| **Why the claim is true** | |
| **Proof** | |
| **Can a sceptic check it without trusting us?** | ☐ yes ☐ no — *if no, it is not a proof* |

### Support 2

| | |
|---|---|
| **Why the claim is true** | |
| **Proof** | |
| **Can a sceptic check it without trusting us?** | ☐ yes ☐ no |

### Support 3

| | |
|---|---|
| **Why the claim is true** | |
| **Proof** | |
| **Can a sceptic check it without trusting us?** | ☐ yes ☐ no |

---

## 4. The objection list

The page's section order is derived from this table. Every objection gets a section; every section answers an objection.

| # | The reader's question | The specific objection, in their words | Section that answers it | Answered by |
|---|---|---|---|---|
| 1 | What is it? | | Hero | *headline + sub* |
| 2 | Is it for me? | | | |
| 3 | Does it work? | | | |
| 4 | Can I trust you? | | | |
| 5 | What does it cost? | | | |
| 6 | What if I'm wrong? | | | |
| + | *the uncomfortable one nobody wants on the page* | | FAQ | |

**Check:** any section not in the right-hand column is dead weight — cut it. Any objection with no section is a hole — add one.

---

## 5. Proof inventory

| Type | Have it? | Specific, attributed, about an objection? | Where it goes |
|---|---|---|---|
| Named customers / logos | | | |
| Attributed testimonials | | | |
| Case study with a measurable result | | | |
| Numbers we can source | | | |
| A demo they can run themselves | | | |
| Specs, formats, requirements | | | |
| Guarantee / refund / cancellation terms | | | |
| Public changelog or build log | | | |

**If the top rows are empty**, the honest substitutes, in descending order of strength: a runnable demo · a public build log · named beta testers with permission · a founder's note about what exists and what does not · an unconditional refund window. Never a fabricated testimonial, a stock-photo customer, or an unsourced statistic. See SKILL.md, *The ethics boundary*.

---

## 6. Assumptions

*Everything above that is a belief rather than a fact. These are what a real test would attack first, so they belong at the top of the delivered work, not buried.*

1.
2.
3.

---
---

# Worked example — "Referent" (a professional audio plugin)

*A filled-in brief, for shape. The full chain — architecture, copy and markup — continues in `references/worked-example.md`.*

## 0. Context

| | |
|---|---|
| **One action** | Download the 14-day demo build |
| **Traffic source** | Gearspace threads, a YouTube mixing channel, and the maker's newsletter |
| **After the click** | 180 MB installer, licence key by email, offline authorisation supported |
| **Proof today** | 11 named beta testers, a browser demo that runs on the visitor's own files, published null-test measurements |
| **Constraints** | Two-person company. No enterprise sales motion. macOS + Windows only |

## 1. Positioning statement

> For **mixing engineers who deliver three to ten client revisions a week**, **Referent** is the **reference-matching plugin** that **shows you the tonal difference between your mix and any reference track, band by band, and corrects it in one pass**, unlike **spending an hour A/B-ing against a reference inside your DAW**.

**Not for:** mastering engineers who want a finished chain, or beginners looking for a one-click "make it loud" preset. Both are said plainly on the page; saying so costs a few sales and prevents a lot of refunds.

## 3. Message hierarchy

**Claim:** *Match your mix to a reference track's tonal balance in one pass.*

| | Support | Proof | Checkable? |
|---|---|---|---|
| 1 | It shows you the difference before it changes anything — 32 bands, both curves on one graph | Browser demo: drop in any two files, see the curve, no install | Yes — they use their own material |
| 2 | The correction is a transparent linear-phase EQ you can override, not a preset or a black box | Published null test and phase-response plots; every band is draggable in the UI | Yes — they can run the null test themselves |
| 3 | It runs inside the session you already have open | VST3 / AU / AAX · macOS 12+ · Windows 10+ · Apple silicon native · up to 192 kHz | Yes — it is a spec |

## 4. Objection list

| # | Question | In their words | Section |
|---|---|---|---|
| 1 | What is it? | "Is this another one-click mastering thing?" | Hero |
| 2 | Is it for me? | "Will it cope with acoustic material, or is it made for EDM?" | Problem + value props |
| 3 | Does it work? | "Does it actually sound transparent, or does it smear the low mids?" | Demo + deep-dives |
| 4 | Can I trust you? | "Two-person company — will this still be supported in a year?" | Testimonials + changelog |
| 5 | What does it cost? | "Is this a subscription?" | Pricing |
| 6 | What if I'm wrong? | "What happens to sessions using it if I stop paying?" | FAQ |
| + | The uncomfortable one | "What can't it do?" | FAQ, answered directly: no multiband compression, no loudness maximiser |

## 6. Assumptions

1. The audience's primary pain is *revision turnaround time*, not audio quality. If it is actually quality, the claim's emphasis is wrong and the hero needs rewriting.
2. "One-time purchase" is a stronger differentiator than any feature, because the category is drifting to subscription. Untested.
3. Readers arrive knowing what reference matching *is*. If they do not, the page needs a problem statement twice as long.
