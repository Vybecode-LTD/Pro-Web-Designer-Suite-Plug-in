---
name: email-template-system
description: Build HTML email that survives Outlook, Gmail and dark mode, compiling the design tokens into inlined, table-based markup. Use for templates and newsletters. Not for copywriting or ESP setup.
---

# Email Template System

> **Running the scripts** — by path, from the user's project root, so `src/`
> means the project's `src/` and every output lands in the project, never
> inside this plugin:
>
> ```bash
> python "${CLAUDE_SKILL_DIR}/scripts/build_email.py" emails/my-email.html --out build/my-email.html
> ```
>
> The commands below are written `python -m scripts.<name>`. That form is for a project that
> has copied the scripts into its own `scripts/` folder, as CI and git hooks
> do; when you run one here, use the path form.
> This skill's scripts are in `${CLAUDE_SKILL_DIR}/scripts/` (build_email.py, lint_email.py, render_email.mjs).

Every agency client eventually needs email, and email is the one place where **this suite's laws must be deliberately broken**. HTML email has no cascade layers, no custom properties you can rely on, no `gap`, no flexbox or grid in the client that matters most, and `<style>` blocks that several clients strip entirely.

That is a real, principled exception, and it deserves to be owned explicitly rather than improvised badly the night before a send.

## The principle

> **The token file stays the source of truth. Email is a compile target.**

You never hand-write a hex in an email template. You author against the same Tier-2 role tokens the website uses, in a readable `<style>` block with classes, and a build step resolves them to literal values and inlines them onto the elements.

**The laws are not abandoned. They move from runtime to build time.**

This reframing is the whole skill. Without it, "email is different" becomes a licence for a second, undisciplined design system that drifts from the first one within a quarter — and the drift is invisible, because nobody opens last quarter's email next to this quarter's website.

---

## The exception, stated precisely

| Law | In email | What replaces it |
|---|---|---|
| **1. Tokens or nothing** | **Holds — at build time.** Source templates use `var(--token)`; the compiler resolves them. A literal hex in a source template is the same violation it has always been. | `assets/email-tokens.json`, `build_email.py`, `lint_email.py --source` |
| **2. Parents own the gaps** | **Bends.** There is no `gap`, and child `margin` is unreliable in the Word engine and absent on `div`s in Samsung Mail. | The parent `<table>` owns the gap: `padding` on the content `<td>` for space *inside* a band, a **spacer `<tr>`** for space *between* bands. A content element still never sets its own outer spacing. |
| **3. The scale is closed** | **Narrows.** 13 of the 18 spacing steps, in px; type has email's own steps. | — |
| **4. One home** | **Inverted — on purpose, by a tool.** Everything ends up inlined, which is the maximum dispersal the web law exists to prevent. | The rule becomes: **no human hand-writes an inline style.** The *source* still has exactly one home per component, and a reviewer still predicts its appearance from one rule. The compiler does the dispersal, deterministically, and `lint_email.py` proves the result. |
| **5. Layers, not specificity** | **Gone.** There is nothing to layer. | **Source order is the only layer order.** Utilities are declared last or they lose silently at equal specificity. `!important` becomes *correct* in the media query, because that block must beat the inline styles the compiler wrote — the thing layers existed to avoid is the thing email requires. |
| **6. Semantic before primitive** | **Holds.** Templates read roles (`--fg-muted`), never ramp steps. | — |
| **7. Density is a dial** | **Holds, resolved early.** No `calc()` at runtime, so the dial is turned at export. | A second token file for a compact variant — never a second set of styles. |
| **8. Novel patterns pass the gate** | **Holds, harder.** No JavaScript, no focus states, no hover for most readers. | If it needs interaction, it is a link to a page. |
| **9. Nothing ships un-audited** | **Holds.** Different auditor, same rule. | `python -m scripts.lint_email build/*.html` exits clean. |

**Laws 3, 6, 7, 8 and 9 hold unchanged. Law 1 holds at build time. Law 2 changes mechanism, not principle. Law 4 is inverted by a tool, not by a person. Law 5 is genuinely gone.**

That is the entire exception. Anything beyond it — a hardcoded colour, a hand-tuned 27px gap, a second font stack — is not "email being different." It is drift.

---

## Quick start

```bash
# 1. Start from a template that already compiles clean — copied INTO the project,
#    where it is committed; the plugin's copy is replaced on every update
mkdir -p emails
cp "${CLAUDE_SKILL_DIR}/assets/templates/transactional-receipt.html" emails/my-email.html

# 2. Edit the copy — tokens only, no literals, utilities declared last
python -m scripts.lint_email emails/my-email.html --source

# 3. Compile: resolve tokens, inline the CSS, keep the media queries,
#    add the Outlook scaffolding, write the plain-text part, report bytes
python -m scripts.build_email emails/my-email.html \
    --out build/my-email.html --text build/my-email.txt

# 4. Gate it
python -m scripts.lint_email build/my-email.html

# 5. Read the plain-text part with your own eyes. Somebody receives it.
cat build/my-email.txt
```

Python scripts: stdlib. `render_email.mjs`: Node and Playwright.

---

## What the compile actually does

Worth seeing once, because it is what makes the exception credible rather than a slogan.

**You author this:**

```html
<style>
  .card    { background-color: var(--bg-surface); border: var(--email-edge); }
  .h2      { font-size: var(--type-h2-size); line-height: var(--type-h2-line);
             font-weight: var(--type-h2-weight); color: var(--fg-strong); margin: 0; }
  .muted   { color: var(--fg-muted); }          /* utilities last */
  @media only screen and (max-width: var(--email-bp-stack)) {
    .h2 { font-size: 22px !important; }
  }
</style>
…
<td class="card"><h2 class="h2">Ten-year repair promise</h2></td>
```

**The compiler emits this:**

```html
<style>
@media only screen and (max-width: 600px){.h2{font-size:22px!important}}
</style>
…
<td class="card" style="background-color:#ffffff;border:1px solid #e7e5e2">
  <h2 class="h2" style="font-size:24px;line-height:30px;font-weight:700;color:#080706;margin:0">
    Ten-year repair promise</h2></td>
```

Note what survived and what did not. The media query stays, since its condition is evaluated at runtime, and so does the class it matches. Everything else became an attribute. No human typed `#080706`, and nobody will: change `--neutral-950` once and every template that reads `--fg-strong` moves with it.

---

## Workflow

### 1. Get the tokens into email form

`assets/email-tokens.json` is the email-safe **projection** of `tokens.css` — not a second token system. Every entry is `survives`, `substituted` (with a documented reason), or listed in `dropped` with what to use instead.

The substitutions that matter: `oklch()` → hex, `clamp()` → the anchor that fits a 600px column, `calc()` → resolved arithmetic, the `font` shorthand → size/line/weight triples, elevation → a 1px border, web fonts → a websafe stack. Every colour carries its measured contrast ratio.

Referencing a dropped token is a **hard build error**, not a silent nothing. `var(--elevation-card)` fails the build and tells you to use `--email-edge`.

### 2. Author the source template

Start from one of the three in `${CLAUDE_SKILL_DIR}/assets/templates/` — copy it into the project first. They are complete and they compile:

| Template | Shows |
|---|---|
| `transactional-receipt.html` | line items, a totals row, a well, a single CTA, transactional footer |
| `product-announcement.html` | hero image, two columns that stack without a media query, bulletproof button |
| `newsletter.html` | text-forward, pull quote, captioned image, the best deliverability profile of the three |

Authoring rules, in full, in `references/email-workflow.md` §1. The short version: tokens everywhere, classes in one `<style>` block, **utilities declared last**, inline `style` only for genuinely per-instance values.

### 3. Build

```bash
python -m scripts.build_email "${CLAUDE_SKILL_DIR}/assets/templates/transactional-receipt.html" \
    --out build/receipt.html --text build/receipt.txt
```

Resolves tokens, inlines with real cascade ordering, keeps media queries, adds the MSO scaffolding and plain-text part, and reports bytes against Gmail's clipping threshold.

### 4. Lint

```bash
python -m scripts.lint_email build/receipt.html --transactional
```

Exits non-zero on anything that breaks in a named client: Law 9 for email.

### 5. Test

Free checks first: `node scripts/render_email.mjs build/x.html` shows light, dark and no-`<style>` at 375px. `references/email-workflow.md` §4 lists them; §5 gives the five paid client combinations worth the budget, in priority order. The one people skip and should not: **the Gmail app signed in with a non-Google account**, where the `<style>` block does not apply at all.

### 6. Hand off

`references/email-workflow.md` §8 covers what Klaviyo, Mailchimp, Postmark and SendGrid each do to your HTML, the merge-tag differences, and the four settings to turn off so the ESP does not undo the build.

---

## The five things that break email

Ranked by how often they are the actual cause. Full detail in `references/email-client-matrix.md`.

**1. The Word engine.** Classic Outlook for Windows renders with Microsoft *Word's* layout engine. No `max-width`, no `border-radius`, no flex, no grid, no background images, unreliable `margin`. Ghost tables supply the width, VML supplies the button shape, `padding` on a `<td>` supplies all spacing. Microsoft's replacement (new Outlook, Chromium) ignores all of it harmlessly — so one file serves both, and sources disagree on whether the old one dies in 2026, 2027 or 2029. Keep the branch.

**2. The 120-DPI scaling bug.** On a Windows display at 125% scaling — the default on a modern laptop — the Word engine scales `font-size` and does not scale HTML `width` attributes. Text grows 20%, its container does not, layout bursts. Invisible on a standard-DPI test machine. `<o:PixelsPerInch>96</o:PixelsPerInch> ` defuses it; the compiler adds it.

**3. GANGA.** The Gmail app signed in with a non-Google account does **not apply embedded `<style>` at all**, and blocks images by default. Same app, same icon, materially poorer renderer. Anything that lives only in the `<style>` block is absent for those readers — which is why the layout must be correct without it, and why fluid-hybrid beats media queries as the default.

**4. Gmail's two size ceilings.** 102 KB of HTML (measured: 102,400 bytes) and it clips, hiding everything past the cut — the footer, the unsubscribe link, the tracking pixel — behind "View entire message." Separately, 16,384 bytes of `<style>` content, counted across every `<style>` element. Each element that crosses the ceiling is removed **whole**, along with every element after it, so one block over the ceiling loses all of its CSS. Past it the build splits the retained CSS into blocks in authoring order, so only the tail is lost: put what matters first. The build reports both.

**5. Dark mode, which you do not control.** Three behaviours: respect (Apple Mail, and the Outlook apps other than classic Windows for the media query), partial colour inversion (most Outlook, Gmail Android), full forced inversion (Gmail iOS, classic Outlook). You cannot opt out of forced inversion anywhere. Design light, avoid pure `#000`/`#fff` because inversion algorithms key on the extremes, add the `prefers-color-scheme` block because Apple Mail, Outlook for Mac, Outlook.com, the Outlook mobile apps and Samsung Email 6.1 honour it, then stop.

---

## The spacing discipline, in one place

Law 2 is the law people quietly drop in email, and dropping it is why email spacing drifts within three campaigns. The replacement is mechanical and short enough to memorise.

> **The parent `<table>` owns every gap.** `padding` on the content `<td>` for space *inside* a band. A **spacer `<tr>`** for space *between* bands. A content element never sets its own outer spacing.

| The space is | Use | Because |
|---|---|---|
| Inside a band — gutter, card inset | `padding` on the `<td>` | The `<td>` is the box; padding is its inset. One owner. |
| Between two sibling content rows | a spacer `<tr>` | Two rows cannot both own the space between them. A dedicated row owns it, visibly. |
| Between two columns | a gutter `<td>` of fixed width | Same argument, horizontal. |
| Between a heading and its own paragraph | `padding-top` on the paragraph | Deliberate exception: these are one unit, not two siblings. |

```html
<tr><td style="height:24px;font-size:0;line-height:0;">&nbsp;</td></tr>
```

All four parts are load-bearing: the height is the gap, `font-size:0` and `line-height:0` stop the `&nbsp;` contributing its own line box (or your 24px gap is 24px *plus a line of text*, differently per client), and the `&nbsp;` itself stops several clients — including the Word engine — collapsing an empty cell to zero.

**Why not just `padding-bottom` on every content cell.** Same reason child margins fail on the web: the last row then carries a gap that should not exist, and email cannot express `:last-child`. A spacer row is inserted *between* things by construction, so there is never a trailing one.

Full decision table and the `cellpadding` trap in `references/email-architecture.md` §3.

---

## When you are handed an existing email

Common, and the instinct to rewrite it is usually right but not always affordable.

1. **Lint it first.** `python -m scripts.lint_email their-template.html` on the file as it stands. The error count is the argument for whatever you propose next, and it is specific: "nine layout tables with no `role="presentation"`, four images with no alt, body text at 2.9:1, and it clips in Gmail at 118 KB."
2. **Decide by where the values live.** If the colours and sizes are consistent literals, it is mechanical: extract them to `email-tokens.json`, replace with `var()`, and you have a source template. If they are inconsistent — three greys that meant to be one — that is a migration, and `design-token-migration` owns the extract-and-cluster pass.
3. **Never edit the compiled file.** The moment someone hand-edits built HTML, the source stops being the truth and the next build silently reverts them. `build/` belongs in `.gitignore`.
4. **Keep the ghost tables and the VML** unless you have opens data proving classic Outlook is at zero for that list. They cost a few hundred bytes and every modern client ignores them for free.

---

## Scripts

Both are stdlib-only Python 3, no dependencies.

### `scripts/build_email.py` — the compiler

| Flag | Does |
|---|---|
| `--out FILE` | compiled HTML (default: stdout) |
| `--tokens FILE` | default: `.design-suite.json`'s `emailTokens`, else `assets/email-tokens.json` |
| `--text FILE` | also write the plain-text alternative |
| `--text-only` | emit only the plain-text part |
| `--no-inline` | resolve tokens, leave the CSS in `<style>` |
| `--no-mso` | skip the Outlook namespaces, PixelsPerInch and font rule |
| `--minify` | collapse whitespace; conditional comments are protected |
| `--keep-comments` | keep authoring comments |
| `--width N` | wrap column for the text part (default 72) |
| `--strict` | exit 1 on any warning |

Exit `0` compiled · `1` over the clipping threshold (or `--strict` with warnings) · `2` bad invocation or an unresolved token.

**The inliner implements the real cascade**, not an approximation: element / class / id / descendant / child selectors with correct specificity ordering, then source order, with a normal stylesheet declaration below an existing inline `style`, and `!important` inverting the whole stack. Selectors it cannot resolve to a static element set — pseudo-classes, attribute selectors, anything inside `@media` — are retained as CSS rather than guessed at. A rule whose selector list mixes both is split.

### `scripts/lint_email.py` — the gate

Checks unresolved `var()`, unsupported CSS per the matrix, layout tables missing `role="presentation"`, images without `alt` or explicit dimensions, missing `lang`/`<title>`/charset/preheader/MSO font rule, relative URLs, size against both Gmail thresholds, measured contrast against the nearest resolvable background, in light and with the retained dark rules applied, non-descriptive link text, a missing unsubscribe link, forms and scripts, text below the 13px email floor, and inline widths over a phone's.

| Flag | Does |
|---|---|
| `--format report\|json` | human or machine readable |
| `--source` | Law 1 on a source template |
| `--transactional` | demote the unsubscribe check for receipts and password resets |
| `--strict` | warnings fail too |
| `--ignore a,b` | silence named checks |
| `--verbose` | list every occurrence instead of collapsing repeats |
| `-o FILE` | write the output |

Exit `0` clean · `1` at least one error · `2` bad invocation.

Every `error` traces to a row in `references/email-client-matrix.md`, or with `--source` to Law 1.

---

## The requests you will actually get

The common requests, and the answer to each, are in `references/email-workflow.md` §10.

---

## Routing

| Situation | Go to |
|---|---|
| Building or restyling the system itself | `web-design-studio` |
| An inherited codebase not yet on tokens | `design-token-migration` |
| Design file and code have drifted apart | `figma-variables-sync` |
| Every state × density × theme renders | `component-state-matrix` |
| Copy, offer and persuasion on a landing page | `landing-page-conversion` |
| **The design system has to reach an inbox** | **here** |
| Adversarial review before a client sees it | `design-critique-gate` |

Within this skill:

| You want | Read |
|---|---|
| the token vocabulary | `references/token-contract.md` |
| what breaks in which client, with sources and dates | `references/email-client-matrix.md` |
| the Word engine, VML, 120-DPI, ghost tables | `references/email-client-matrix.md` §3 |
| Gmail's sanitiser and the GANGA case | `references/email-client-matrix.md` §4 |
| the two size ceilings | `references/email-client-matrix.md` §7 |
| dark mode, and what cannot be controlled | `references/email-client-matrix.md` §8 |
| what I could not verify | `references/email-client-matrix.md` §9 |
| the table skeleton and why each level exists | `references/email-architecture.md` §1 |
| spacing discipline — the table-shaped Law 2 | `references/email-architecture.md` §3 |
| the component set, with complete markup | `references/email-architecture.md` §4 |
| bulletproof buttons | `references/email-architecture.md` §6 |
| fluid-hybrid vs media queries | `references/email-architecture.md` §7 |
| images, alt text, weight budget | `references/email-architecture.md` §8 |
| accessibility in an email client | `references/email-architecture.md` §9 |
| the source format and the build step | `references/email-workflow.md` §1–2 |
| preheader text done properly | `references/email-workflow.md` §3 |
| what to test free vs what to pay for | `references/email-workflow.md` §4–5 |
| deliverability that lives in the HTML | `references/email-workflow.md` §6 |
| the plain-text part | `references/email-workflow.md` §7 |
| ESP handoff and merge-tag portability | `references/email-workflow.md` §8 |
| the pre-send checklist | `references/email-workflow.md` §9 |
| every token substitution and its reason | `assets/email-tokens.json` |

---

## The three sentences to remember

1. **The token file is the source of truth and email is a compile target** — the laws move from runtime to build time, they do not get suspended.
2. **Law 2 changes mechanism, not principle**: there is no `gap`, so the parent table owns the space — cell padding inside a band, a spacer row between bands, and a content element still never sets its own outer spacing.
3. **Inline styles are the only styles every client agrees to render**, which is why Law 4 is inverted by a tool and never by a person — the source keeps its one home, and the linter proves the output.
