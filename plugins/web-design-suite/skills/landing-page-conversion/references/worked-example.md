# Worked Example — Referent

One product, the whole chain: positioning → message hierarchy → architecture → copy → markup. Read it when you want to see what "done" looks like before starting your own.

The product is a professional audio plugin, because that is the hardest register to write for — a technical audience with an active allergy to marketing language — and anything that works there transfers down to easier markets.

**Referent** is fictional. The specs, the beta testers and the null-test claims below are invented *for this document* and labelled as such here so nobody copies them into a real page. That is the point of the ethics boundary: in real work, every one of these lines must come from something true.

---

## 1. Positioning (Phase 1)

> For **mixing engineers who deliver three to ten client revisions a week**, **Referent** is the **reference-matching plugin** that **shows you the tonal difference between your mix and any reference track, band by band, and corrects it in one pass**, unlike **spending an hour A/B-ing against a reference inside your DAW**.

**Specificity test:**

| Blank | Could a competitor claim it? | Why not |
|---|---|---|
| Mixing engineers delivering 3–10 client revisions a week | No | Names a *situation* (deadline pressure, volume), not a demographic |
| Reference-matching plugin | No | An actual shelf. Not "an audio platform" |
| Shows the difference band by band, corrects in one pass | No | Two competitors correct without showing; one shows without correcting |
| An hour A/B-ing in the DAW | No | Names what they do *today*, not a rival brand |

**Not for:** mastering engineers who want a finished chain, or beginners wanting a one-click "make it loud" preset. Both are said on the page. It costs a few sales and prevents a lot of refunds, and — more importantly for a two-person company — it prevents a lot of one-star reviews from people the product was never for.

---

## 2. Message hierarchy (Phase 2)

**Claim:** *Match your mix to a reference track's tonal balance in one pass.*

| | Support | Proof | Checkable without trusting us? |
|---|---|---|---|
| 1 | It shows you the difference before it changes anything — 32 bands, both curves on one graph | Browser demo: drop in any two of your own files, see the curve, no install | Yes, on their own material |
| 2 | The correction is a transparent linear-phase EQ you can override, not a preset or a black box | Published null test and phase-response plots; every band is draggable | Yes, they can run the null test |
| 3 | It runs inside the session already open | VST3 / AU / AAX · macOS 12+ · Windows 10+ · Apple silicon native · up to 192 kHz | Yes, it is a spec |

Every proof is something a sceptic can verify without believing a word on the page. That is the test, and it is the only test.

---

## 3. Architecture (Phase 3)

Page type: **app / plugin download.** One action: download the 14-day demo build.

| # | Section | Objection it answers | Why here |
|---|---|---|---|
| 1 | Hero | What is it? Is it for me? | The claim, the audience, and the download in one screen |
| 2 | Demo | Does it work? | The strongest proof this product has. It goes second, not eighth — a demo below the third screenful is a demo most readers never reach |
| 3 | Proof strip | Can I trust you? (deposit) | Buys patience for the next four screens. A strip, not a section — `.band--tight` |
| 4 | Value props | Is it for me? Does it work? | The three supports, as outcomes |
| 5 | How it works | Does it work, in practice? | Three steps. Converts belief-in-principle to belief-in-practice |
| 6 | Feature deep-dives | Does it work, in detail? | Two rows, one per support that needs a picture. Not six |
| 7 | Specs | Is it for me? (technical) | Formats, versions, requirements. A technical audience reads this before the testimonials |
| 8 | Testimonials | Can I trust you? | After the deep-dives, before the price |
| 9 | Pricing | What does it cost? | One-time purchase is the differentiator; it gets a section, not a footnote |
| 10 | FAQ | What if I'm wrong? | Licence, upgrades, what it cannot do |
| 11 | Final CTA | — | Restates the claim and asks once more |
| 12 | Footer | — | Legal, support, the things a two-person company must show |

**No problem statement.** The audience arrives already knowing that matching a reference is slow — they came from a thread about exactly that. A section explaining their own workflow to them would delay the demo by one screen, and the demo is the page's best asset.

**No comparison table.** The category is crowded but the reader's alternative is *their own DAW workflow*, not a named rival. A table would teach some readers that rivals exist and hand them the search terms.

---

## 4. The copy (Phase 4)

### Hero

> **FOR MIXING ENGINEERS ON A DEADLINE** *(eyebrow — audience, self-selection in five words)*
>
> # Match your mix to a reference track in one pass.
>
> Referent puts your mix and your reference on the same graph, 32 bands wide, then corrects the difference with a linear-phase EQ you can see and override. No presets. No guessing what changed.
>
> **[ Download the 14-day demo ]**  ·  *Hear it on your own files →*
>
> 180 MB · macOS 12+ / Windows 10+ · No card, no account

*Headline formula 2.1 (outcome) with the credibility constraint carried by "in one pass". The sub does the **mechanism** job. The friction reducer states the three things a reader would otherwise have to find out by clicking — and states them accurately, which is the whole value of the line.*

### Demo

> ## Run it on your own material
> Drop in a mix and a reference. You will see the curve before you download anything.
> *(Interactive browser demo. Nothing is uploaded — it runs locally.)*

*One line of caption telling the reader what to look for. "Nothing is uploaded" answers an objection nobody will say out loud and several will act on.*

### Proof strip

> **Used on records by**  ·  six studio marks, monochrome

### Value props

> ### You see the difference before anything changes
> Both curves on one graph, 32 bands. Referent shows you what it is about to do, and you decide whether it is right.
> *Try it in the browser →*
>
> ### Transparent correction, not a preset chain
> Linear-phase EQ, under 0.1 dB of ripple, latency reported to your host. Every band is draggable. Most engineers accept about half of its suggestions, and that is the intended use.
> *Read the null test →*
>
> ### It runs in the session you already have open
> VST3, AU and AAX. Native on Apple silicon. Up to 192 kHz. No cloud round-trip, no account, works offline.
> *Full requirements →*

*Each is outcome → mechanism → proof. Note the second one states a limitation ("most engineers accept about half") — which reads as confidence, because nobody fakes a claim in that direction.*

### How it works

> **1. Load a reference** — any file, any length. Referent uses the loudest 30 seconds by default; you can pick a range.
> **2. Play your mix** — it builds both curves in real time. Twenty seconds is usually enough.
> **3. Apply, then argue with it** — accept the whole curve, or drag the bands you disagree with.

*Steps written as the reader's actions, not ours. Step 3's verb is deliberate: "argue with it" tells a suspicious audience that disagreement is expected and supported.*

### Feature deep-dives (two rows)

> ### The graph is the product
> The correction curve is not a summary of what happened — it is the control surface. Drag any of the 32 bands and the EQ updates live. Hold a band to solo it. The curve you see is the curve that ships.
>
> ### It knows when not to help
> If your mix and the reference are further apart than a tonal correction can honestly close — different arrangement, different instrumentation — Referent says so instead of applying 9 dB of shelf. A tool that refuses is a tool you can leave switched on.

*Two rows, one per support that needs a picture. The second is a feature most competitors would not mention, which is exactly why it belongs on the page.*

### Specs

> **Formats** VST3 · AU · AAX (Pro Tools 2022.9+)
> **macOS** 12 Monterey or later · Universal 2, native on Apple silicon
> **Windows** 10 (1909) or later, 64-bit
> **Sample rates** 44.1 – 192 kHz · **Latency** reported to the host; 2048 samples at 48 kHz
> **Authorisation** Licence file. Works offline. Three machines per licence.

### Testimonials

> "I run mostly acoustic jazz and I expected it to smear the low mids. It didn't — and when I pushed a reference that was too far off, it told me instead of trying."
> **Nadia Oyelaran** · Mix engineer · *Blue Room, Lagos*
>
> "I've been on it since the 1.0 beta. Three updates since, all free, and the graph has stayed the same shape — which for me is the whole point."
> **Tom Brenner** · Freelance mixer · *credits: Harbour Lights, Setlist*

*Both lead with the objection they dissolve — "will it cope with acoustic material" and "will a two-person company still be here" — not with praise. Both are attributed to a name, a role, and something checkable.*

### Pricing

> ### One price. No subscription.
>
> **Referent** — **$149** one time
> For one engineer, on up to three machines.
> · All 32 bands, no feature tiers · Free updates within the major version
> · Works offline, forever, including after we stop selling it
> **[ Download the 14-day demo ]**
>
> **Referent — Studio Site Licence** — **$490** one time
> For a studio with multiple rooms or engineers.
> · Up to ten machines · One invoice · Named support contact
> **[ Talk to us ]**
>
> *30-day refund, no questions, no form. Mail us and it's done.*

*Two plans, an axis the reader can name (machines), a who-line under each, and the refund in plain text rather than a tooltip. "Works offline, forever, including after we stop selling it" answers the two-person-company objection at the exact moment the reader is deciding to spend money.*

### FAQ

> **Is this a subscription?** No. One payment, and the version you bought keeps working. Updates within the major version are free; a future 2.0 would be a paid upgrade at a discount for existing owners.
> **What happens to my sessions if I stop using it?** Nothing — the plugin keeps working. It is not a rental and there is no server it phones home to.
> **What can't it do?** No multiband compression, no loudness maximiser, no stem separation. It is a tonal-balance tool and it is deliberately only that. Put it in front of your compressor, not instead of it.
> **Will it work on acoustic and orchestral material?** Yes, and it is more conservative there by design. If the reference is too far from your mix to correct honestly, it says so.
> **Two people build this. What happens if you stop?** The licence is a file on your machine and authorisation works offline, so the plugin does not stop when we do. If we ever shut down, the last build is released unlocked. That is in the licence terms, not just a promise here.
> **Can I use it on client work?** Yes, with no royalty and no credit requirement, on up to three of your own machines.

*Six questions. Three of them are uncomfortable. Answering "what can't it do" directly is the single highest-trust move available on a page like this.*

### Final CTA

> ## Stop A/B-ing. Start comparing.
> **[ Download the 14-day demo ]**
> Full version, no feature limits. 180 MB. No card, no account.

*Restates the claim rather than saying "Ready to get started?", and repeats the hero's exact button label — same verb, same words, same destination.*

---

## 5. The markup (Phase 5)

Layout primitives from `web-design-studio`'s `layout.css`, section shells from `assets/page-sections.css`. No bespoke layout CSS is written for this page — that is the test.

```html
<main id="main" class="page-grid sections sections--banded" data-density="spacious">

  <!-- 1. HERO — bleeds full, content back in the column via a nested grid -->
  <section class="band section bleed-full" aria-labelledby="hero-title">
    <div class="page-grid">
      <div class="cover cover--partial hero">
        <div class="cover__centre split split--2-1 split--center">
          <div class="hero__copy">
            <div class="hero__heading">
              <p class="section__eyebrow">For mixing engineers on a deadline</p>
              <h1 id="hero-title" class="hero__title">
                Match your mix to a reference track in one pass.
              </h1>
              <p class="hero__sub">
                Referent puts your mix and your reference on the same graph, 32 bands
                wide, then corrects the difference with a linear-phase EQ you can see
                and override. No presets. No guessing what changed.
              </p>
            </div>
            <div class="hero__actions">
              <div class="cluster cluster--tight">
                <a class="cta" href="/download">Download the 14-day demo</a>
                <a class="cta cta--secondary" href="#demo">Hear it on your own files</a>
              </div>
              <p class="hero__note">180 MB · macOS 12+ / Windows 10+ · No card, no account</p>
            </div>
          </div>
          <figure class="frame frame--3-2 hero__media">
            <img src="/img/referent-curve.avif" width="1200" height="800"
                 alt="Referent showing a mix curve and a reference curve across 32 bands"
                 fetchpriority="high" decoding="async">
          </figure>
        </div>
      </div>
    </div>
  </section>

  <!-- 2. DEMO — the strongest proof, placed second -->
  <section id="demo" class="band section section--surface" aria-labelledby="demo-title">
    <header class="section__header section__header--center">
      <h2 id="demo-title" class="section__title">Run it on your own material</h2>
      <p class="section__deck">
        Drop in a mix and a reference. You will see the curve before you download
        anything — nothing is uploaded, it runs locally.
      </p>
    </header>
    <div class="frame frame--rounded">
      <iframe src="/demo/embed" title="Interactive reference-matching demo" loading="lazy"></iframe>
    </div>
  </section>

  <!-- 3. PROOF STRIP — a strip, not a section: band--tight -->
  <section class="band band--tight section section--sunken" aria-label="Studios using Referent">
    <p class="logo-strip__kicker">Used on records by</p>
    <ul class="grid grid--fill grid--min-xs" role="list">
      <li class="frame frame--3-2 frame--contain">
        <img src="/img/logo-blue-room.svg" width="160" height="40" alt="Blue Room" loading="lazy">
      </li>
      <!-- five more -->
    </ul>
  </section>

  <!-- 4. VALUE PROPS — three, because the hierarchy has three supports -->
  <section class="band section" aria-labelledby="props-title">
    <header class="section__header">
      <h2 id="props-title" class="section__title">Three things it does that a preset cannot</h2>
    </header>
    <ul class="switcher switcher--max-3 grid--rows-aligned" role="list">
      <li class="feature-card">
        <h3 class="feature-card__title">You see the difference before anything changes</h3>
        <p class="feature-card__body">
          Both curves on one graph, 32 bands. Referent shows you what it is about to
          do, and you decide whether it is right.
        </p>
        <a class="feature-card__proof" href="#demo">Try it in the browser</a>
      </li>
      <!-- two more -->
    </ul>
  </section>

  <!-- 6. FEATURE DEEP-DIVE — two rows, alternating media side -->
  <section class="band section section--surface" aria-labelledby="deep-title">
    <header class="section__header">
      <h2 id="deep-title" class="section__title">The graph is the product</h2>
    </header>
    <div class="subsections">
      <div class="split split--1-2 split--center">
        <div class="stack stack--tight">
          <h3 class="section__title">Drag any band</h3>
          <p>
            The correction curve is not a summary of what happened — it is the control
            surface. Drag any of the 32 bands and the EQ updates live.
          </p>
        </div>
        <figure class="frame frame--3-2 frame--rounded">
          <img src="/img/bands.avif" width="1200" height="800" alt="Dragging a band"
               loading="lazy" decoding="async">
        </figure>
      </div>
      <!-- second row, split--2-1 to alternate the media side -->
    </div>
  </section>

  <!-- 9. PRICING -->
  <section class="band section" aria-labelledby="price-title">
    <header class="section__header section__header--center">
      <h2 id="price-title" class="section__title">One price. No subscription.</h2>
    </header>
    <ul class="switcher switcher--max-2" role="list">
      <li class="plan plan--recommended">
        <div class="plan__body">
          <p class="plan__badge">Most engineers</p>
          <div class="plan__header">
            <h3 class="plan__name">Referent</h3>
            <p class="plan__price">$149 <span class="plan__period">one time</span></p>
            <p class="plan__who">For one engineer, on up to three machines.</p>
          </div>
          <ul class="plan__features" role="list">
            <li class="plan__feature"><span class="plan__feature-mark" aria-hidden="true">+</span>
              All 32 bands, no feature tiers</li>
            <li class="plan__feature"><span class="plan__feature-mark" aria-hidden="true">+</span>
              Free updates within the major version</li>
            <li class="plan__feature"><span class="plan__feature-mark" aria-hidden="true">+</span>
              Works offline, forever, including after we stop selling it</li>
          </ul>
        </div>
        <a class="cta plan__cta" href="/download">Download the 14-day demo</a>
      </li>
      <!-- site licence -->
    </ul>
    <p class="section__deck">30-day refund, no questions, no form. Mail us and it's done.</p>
  </section>

  <!-- 10. FAQ — real <details>, works before hydration, findable by ctrl-F -->
  <section class="band section section--sunken" aria-labelledby="faq-title">
    <header class="section__header">
      <h2 id="faq-title" class="section__title">The questions we actually get</h2>
    </header>
    <div class="faq">
      <details class="faq__item" open>
        <summary class="faq__question">
          Is this a subscription?
          <span class="faq__marker" aria-hidden="true">&#9662;</span>
        </summary>
        <div class="faq__answer">
          No. One payment, and the version you bought keeps working. Updates within the
          major version are free; a future 2.0 would be a paid upgrade at a discount
          for existing owners.
        </div>
      </details>
      <!-- five more -->
    </div>
  </section>

  <!-- 11. FINAL CTA — the one inverse band on the page -->
  <section class="band band--loose section section--inverse" aria-labelledby="cta-title">
    <div class="cta-block">
      <h2 id="cta-title" class="cta-block__claim">Stop A/B-ing. Start comparing.</h2>
      <a class="cta" href="/download">Download the 14-day demo</a>
      <p class="cta-block__note">Full version, no feature limits. 180 MB. No card, no account.</p>
    </div>
  </section>

</main>
```

**What is worth noticing in that markup.**

- **Not one bespoke layout rule.** Every arrangement is `page-grid`, `cover`, `split`, `switcher`, `grid`, `frame`, `cluster`, `stack` or `subsections`. The section shells add surface and type, never arrangement.
- **Every band is a `.band`**, including the transparent ones, so the page is in exactly one rhythm mode and a seam is always `2 × --space-subsection`.
- **Full-bleed is a nested `.page-grid`**, not a negative margin — which is why the hero's background runs edge to edge without producing horizontal scroll when a scrollbar appears.
- **The hero image is not lazy-loaded** and carries `fetchpriority="high"`; it is the LCP element. Everything below it is `loading="lazy"`. Getting this backwards is the most common accidental performance regression on a marketing page.
- **Every `.frame` reserves its aspect ratio**, and every `<img>` carries `width` and `height`. That is the CLS fix, and on a landing page CLS usually manifests as a reader tapping a button that has just moved.
- **The FAQ is real `<details>`**, so it works before hydration and the browser's own find-in-page reaches the answers.
- **The demo `<iframe>` is lazy**, so a third-party embed never blocks the hero.
- **Lists are lists.** `role="list"` is on the `<ul>`s whose `list-style` is removed, because Safari drops list semantics from a list with `list-style: none`.
- **One inverse band**, at the end. Its scarcity is what makes it read as the close.

---

## 6. What was checked

| Check | Result |
|---|---|
| `audit_design.py` on `assets/page-sections.css` | clean, including `--strict` |
| `audit_design.py` on this example's extracted HTML | clean |
| Every `var(--…)` in `page-sections.css` exists in `tokens.css` or is a locally-declared Tier-3 socket | 55 from `tokens.css`, 24 local sockets, 0 missing |
| Tier-1 leakage into `@layer components` | none |
| Every section maps to an objection | yes — §3 table |
| Every proof is checkable without trusting the page | yes — §2 table |
| Every number on the page is sourced | **no** — this is a fictional product, and the specs are invented *for this document only*. In real work each one traces to a measurement |

---

Related: `assets/MESSAGE_BRIEF.md` (the template this example fills), `references/page-architecture.md` §3 (the app/plugin-download sequence used here), `references/copy-patterns.md` (every formula named in §4), `references/conversion-audit.md` (the pass this page has not yet had — it has no traffic).
