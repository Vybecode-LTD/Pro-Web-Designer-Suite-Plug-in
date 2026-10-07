# Email Client Matrix

What actually renders, in the clients that actually have share, as of **September 2026**.

This file exists because email advice has an unusually short half-life and an unusually long tail of repetition. Half of what is on the first page of a search for "HTML email best practices" describes a client that has since been replaced, or repeats a limitation Microsoft or Google fixed years ago. The rest is right but undated, which is the same problem wearing a suit.

**Rule for this document:** a claim is either sourced and dated, or marked unverified. Where sources conflict, the conflict is stated and the safe path is given. Nothing here is folklore repeated because it sounds like the sort of thing that would be true.

Every `error`-severity check in `scripts/lint_email.py` traces to a row below.

## Contents

1. [The clients that matter, and why](#1-the-clients-that-matter-and-why)
2. [The capability matrix](#2-the-capability-matrix)
3. [The Word engine, in detail](#3-the-word-engine-in-detail)
4. [Gmail, in detail](#4-gmail-in-detail)
5. [The new Outlook, and the transition nobody has finished](#5-the-new-outlook-and-the-transition-nobody-has-finished)
6. [Apple Mail, Yahoo, Samsung, Thunderbird](#6-apple-mail-yahoo-samsung-thunderbird)
7. [Size limits and clipping](#7-size-limits-and-clipping)
8. [Dark mode](#8-dark-mode)
9. [What I could not verify](#9-what-i-could-not-verify)

---

## 1. The clients that matter, and why

Nine rendering environments, not nine apps. Several apps share an engine; several apps *are* two engines depending on which account is signed in, which is the single most under-appreciated fact in email development.

| # | Environment | Engine | Why it is on the list |
|---|---|---|---|
| 1 | **Outlook Windows, classic** | Microsoft **Word** | The one that breaks things. Frozen by design. |
| 2 | **New Outlook for Windows** | **Chromium** via WebView2 | Microsoft's replacement. Different engine, different bugs. |
| 3 | **Outlook.com / Outlook Web** | Chromium-family, server-side CSS rewriting | Same family as #2; rewrites your CSS before you see it. |
| 4 | **Outlook for Mac** | WebKit-family (modern builds) | Not the Word engine. Never has been. |
| 5 | **Gmail web** | Chromium, with an aggressive server-side sanitiser | Largest single webmail. |
| 6 | **Gmail app, Google account** | Chromium/WebKit host + the same sanitiser | The mobile default. |
| 7 | **Gmail app, non-Google account (GANGA)** | Same app, **reduced** sanitiser output | A different renderer inside the same icon. |
| 8 | **Apple Mail (macOS + iOS)** | WebKit | The most capable. Also the one Mail Privacy Protection sits in front of. |
| 9 | **Yahoo / AOL, Samsung Mail, Thunderbird** | Assorted | The long tail that still breaks specific things. |

**Environment 7 is the one people forget.** "GANGA" — Gmail App with Non-Google Account — is what a reader gets when they add an Outlook, Yahoo or corporate IMAP account to the Gmail app. It is the same app, the same icon, the same inbox, and a materially poorer renderer: embedded `<style>` is not applied, and images are blocked by default. A design that depends on a `<style>` block for anything load-bearing is broken for those readers and for nobody else, which is why it survives QA.

---

## 2. The capability matrix

**Legend:** ✅ works · ⚠️ partial, read the note · ❌ never · — not applicable

| Feature | Outlook Win (Word) | New Outlook | Outlook Web | Outlook Mac | Gmail web | Gmail app (Google) | **GANGA** | Apple Mail | Yahoo | Samsung | Thunderbird |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `<style>` in `<head>` | ⚠️ ¹ | ✅ | ⚠️ ² | ✅ | ⚠️ ³ | ⚠️ ³ | **❌** | ✅ | ⚠️ ⁴ | ⚠️ | ⚠️ |
| `<style>` in `<body>` | ⚠️ | ✅ | ⚠️ | ✅ | ❌ | ❌ | ❌ | ✅ | ⚠️ | ⚠️ | ⚠️ |
| `@media` queries | ❌ | ⚠️ ⁵ | ⚠️ ⁵ | ⚠️ | ⚠️ ⁶ | ✅ | ❌ | ✅ | ⚠️ ⁷ | ⚠️ ⁸ | ✅ |
| `@media (prefers-color-scheme)` | ❌ | ⚠️ | ✅ ²³ | ✅ ²³ | ❌ | ❌ | ❌ | ✅ | ❌ | ⚠️ ²³ | ❌ ²³ |
| `display:flex` | ❌ | ✅ | ✅ | ✅ ⁹ | ✅ ¹⁰ | ✅ ¹⁰ | ❌ | ✅ | ✅ | ✅ | ✅ |
| `display:grid` | ❌ | ✅ | ✅ | ✅ ⁹ | ✅ ¹⁰ | ✅ ¹⁰ | ❌ | ✅ | ✅ | ✅ | ✅ |
| `max-width` | ❌ ¹¹ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `border-radius` | ❌ ¹² | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Web fonts (`@font-face`) | ❌ | ⚠️ | ❌ | ✅ | ❌ ¹³ | ❌ ¹³ | ❌ | ✅ | ❌ | ⚠️ | ⚠️ |
| `background-image` (CSS) | ❌ ¹⁴ | ✅ | ⚠️ | ✅ | ⚠️ ¹⁵ | ⚠️ ¹⁵ | ❌ ¹⁶ | ✅ | ✅ | ✅ | ✅ |
| `background-size` | ❌ | ✅ | ⚠️ | ✅ | ❌ ¹⁵ | ❌ ¹⁵ | ❌ | ✅ | ⚠️ | ⚠️ | ✅ |
| `position` | ❌ | ✅ | ⚠️ | ✅ | ❌ ¹⁷ | ❌ ¹⁷ | ❌ | ✅ | ❌ | ❌ | ⚠️ |
| CSS custom properties | ❌ | ⚠️ | ❌ | ❌ | ⚠️ ¹⁸ | ⚠️ ¹⁸ | ❌ | ✅ | ❌ | ❌ | ❌ |
| `<svg>` | ❌ | ⚠️ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ⚠️ | ⚠️ |
| `<video>` | ❌ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ⚠️ |
| `:hover` | ❌ | ✅ | ⚠️ | ✅ | ❌ ¹⁹ | ❌ | ❌ | ✅ | ⚠️ | ⚠️ | ✅ |
| `padding` on `<td>` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `margin` on `<div>` | ⚠️ ²⁰ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ ²¹ | ✅ |
| `gap` | ❌ | ✅ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Conditional comments / VML | ✅ | ❌ ²² | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

### Notes

1. **Word engine `<style>`** — supported, but with a documented ordering bug: a style must be *declared before the markup it applies to*, and rules that reference a later element are unreliable. `caniemail.com` records this as "buggy support… styles must be declared before use." Since the compiler inlines almost everything, this rarely bites.
2. **Outlook Web** applies a server-side rewrite before rendering: it prefixes class names, rewrites some selectors, and injects its own dark-mode overrides keyed on `[data-ogsc]` / `[data-ogsb]`. Your `<style>` block is not the one that runs.
3. **Gmail `<style>`** — supported in `<head>` since the September 2016 update, **not** in `<body>`, and with a hard size ceiling (§7). Gmail also drops the whole block on some parse errors — historically including nested at-rules.
4. **Yahoo** supports `<style>`. Two old quirks no longer reproduce in `caniemail.com`'s tests: desktop webmail ignored every rule after a CSS comment (gone by 2023-01), and the Android app stripped the first `<head>` (gone by 2025-06). `build_email.py` still strips comments, because they are bytes against Gmail's limit.
5. **New Outlook / Outlook Web media queries** — support is reported as partial and nested media queries are explicitly not supported (and are removed in builds 16.80+). Sources disagree on how complete plain `max-width` support is. **Safe path: do not require a media query for the layout to be correct.** See §7 of `email-architecture.md` — fluid-hybrid first, media query as enhancement.
6. **Gmail web media queries** is the sharpest live disagreement in this document. `caniemail.com` lists Gmail Desktop Webmail as *partial* (no nested, no height-based queries), Email on Acid's long-running Gmail article says embedded styles and media queries arrived in 2016 and work, and at least one 2026 rendering guide flatly states Gmail web "ignores" media queries. All three can be simultaneously true in practice, because **a desktop Gmail reading pane is wider than any `max-width` breakpoint you would set**, so a mobile-first media query never fires there and looks identical to "not supported." Treat Gmail web as: the block parses, the query may be evaluated, and it will not match on desktop anyway.
7. **Yahoo** supports only `screen`, `min-width`, `max-width`, `min-height`, `max-height`. No `and`-chained feature queries beyond that.
8. **Samsung Mail** media-query support is reported as depending on account type (Exchange vs IMAP) and app version. Unverifiable without a device farm; assume no.
9. **Outlook for Mac** is WebKit-family, and `caniemail.com` records `display:flex` and `display:grid` as supported in 16.80. Still not worth relying on, when a table does the job in every client.
10. **Gmail and flex/grid** — `caniemail.com` records `display:flex` as supported in Gmail since 2019, and `display:grid` on the web since 2026-03. Neither works with a non-Google account (GANGA). Gmail also rejects `flex-direction: column` on every platform (tested 2023-01) while keeping `display:flex`, so a flex column arrives in Gmail as a row. Do not use it.
11. **`max-width` in the Word engine** is not supported at all. This is the entire reason ghost tables exist: the conditional-comment table supplies the fixed width the Word engine needs while `max-width` handles everyone else.
12. **`border-radius`** is ignored by the Word engine — corners render square. That is acceptable degradation for a card. It is not acceptable for a pill-shaped button that carries brand identity, which is what VML `roundrect` is for (§3).
13. **Gmail web fonts** — only Roboto and Google Sans are available; other Google Fonts are excluded. Everything else falls back. Build the design on the fallback stack and treat a brand face as decoration.
14. **Word engine background images** require VML (`v:rect` / `v:fill`), because the engine has no CSS `background-image` support. A `background-color` must always accompany it.
15. **Gmail background images** work via the `background` *shorthand* (`background: url(…) center / cover no-repeat`) but `background-size` as a standalone property is not supported. Gmail has also historically rolled out changes that strip CSS carrying background images; verify at send time rather than assuming last year's result.
16. **GANGA background images** frequently do not appear because images are blocked by default and a background image alone does not trigger the "display images" prompt — there must be a real `<img>` in the message to give the reader something to click. This is the documented "fake background image" technique.
17. **Gmail strips `position` entirely.** There is nothing to position against and no way to fake it.
18. **CSS custom properties in Gmail** are listed as *partial* on `caniemail.com`: Gmail recognises the `var()` function but provides no way to declare a variable, and the mobile apps do not support it with non-Google accounts. In other words `var()` in Gmail is a function whose argument can never be defined. That is not support; it is the shape of support. Outlook (all Windows versions, Outlook.com, macOS, iOS, Android), Yahoo, Samsung and Thunderbird have no support at all. **This single row is why this skill compiles tokens rather than shipping them.**
19. **`:hover`** — Gmail does not support it except in webmail, per Email on Acid's Gmail reference. Since you cannot tell which reader is in which, design the resting state to be obviously clickable and treat hover as decoration.
20. **`margin` in the Word engine** is honoured inconsistently and collapses unpredictably. `padding` on a `<td>` is honoured reliably. This is the mechanical reason email spacing is table padding, not margins (see `email-architecture.md` §3).
21. **Samsung Mail** is reported to apply `margin` on paragraphs and headings but not on `div`s or tables.
22. **New Outlook ignores conditional comments and VML entirely** — they are inert comments to a Chromium engine. This is the good news of the transition: one file can serve both engines, because each ignores what is addressed to the other. Downlevel-revealed comments (`<!--[if !mso]><!-- -->…<!--<![endif]-->`) are what make the non-Word branch visible to everyone else.
23. **`prefers-color-scheme`**, per `caniemail.com` (tested 2023-03-08): Outlook.com, Outlook for Mac and the Outlook iOS and Android apps honour it, and also mark what they recolour with `data-og*` attributes. Samsung Email honours it in 6.1, not 6.0. Thunderbird honoured it in 68.4, but not in 78.5 or 91.13, the latest versions tested.

---

## 3. The Word engine, in detail

Classic Outlook for Windows renders email with **Microsoft Word's HTML engine**, and has since Outlook 2007. Not a browser engine that is behind — a word processor's layout engine, which was never trying to be a browser. Most "Outlook bugs" are Word behaving exactly as a word processor should.

### Why `mso-` conditionals exist

Word's engine recognises Microsoft's downlevel conditional comments. Every other client sees a comment and skips it. This gives you a branch inside a single file:

```html
<!--[if mso]>
  <!-- Word engine ONLY. Everything else sees a comment. -->
<![endif]-->

<!--[if !mso]><!-- -->
  <!-- Everything EXCEPT the Word engine. Note the odd syntax: the comment
       closes early, so the markup between is live for normal parsers. -->
<!--<![endif]-->
```

Targeting specific versions is possible (`[if mso 16]`, `[if gte mso 9]`), and is almost always the wrong instinct. Write one branch for the Word engine and one for everyone else.

### The 120-DPI scaling problem

The nastiest Word-engine bug, because it is invisible on a standard-DPI test machine and mangles the email for every reader on a 125%-scaled Windows display — which, on a modern laptop, is the default.

**What happens:** Word converts *some* values to points (which scale with DPI) and leaves *others* as pixels (which do not). `font-size` in CSS scales. HTML `width`/`height` attributes do not. So at 125% scaling the text grows 20% and the column it lives in does not, and the layout bursts.

**The three-part fix** — `build_email.py` applies all three:

```html
<html xmlns:v="urn:schemas-microsoft-com:vml"
      xmlns:o="urn:schemas-microsoft-com:office:office" lang="en">
<head>
<!--[if mso]>
<noscript><xml><o:OfficeDocumentSettings>
  <o:AllowPNG/>
  <o:PixelsPerInch>96</o:PixelsPerInch>
</o:OfficeDocumentSettings></xml></noscript>
<![endif]-->
```

1. **Declare the `o:` namespace** on `<html>`, or the element below is not recognised.
2. **Pin PPI to 96.** This forces consistent scaling regardless of the system DPI.
3. **Express structural widths in CSS as well as attributes** — `<td width="300" style="width:300px;">`. The CSS is what scales consistently once PPI is pinned; the attribute is the fallback.

Known caveat: Outlook 2007 does not honour the PPI setting the same way, and there is no way to target by DPI separately. 96 is the best single answer.

### `width` versus `mso-width`, and why `margin` is unreliable

| You wrote | Word engine does | Write instead |
|---|---|---|
| `max-width: 600px` | ignores it; the table goes full width | a ghost table at a fixed `width` |
| `margin: 0 auto` | ignores `auto`; no centring | `<table align="center">` |
| `margin-bottom: 24px` on a `<div>` | collapses or drops it | a spacer `<tr>`, or `padding-bottom` on a `<td>` |
| `padding: 24px` on a `<div>` | unreliable | `padding` on the `<td>` |
| `cellpadding="8"` | applied, but not equal to CSS padding | add `mso-padding-alt: 8px 8px 8px 8px` |
| `cellspacing="4"` | applied inconsistently | add `mso-cellspacing: 4px` |
| `line-height: 1.6` | rounds unpredictably at display sizes | `line-height: 26px` |

**`padding` on a `<td>` is the one spacing mechanism that works everywhere in the matrix.** That is not a stylistic preference; it is the reason the whole architecture is tables.

### VML: the two things it is actually for

VML is Microsoft's pre-SVG vector language. Two uses survive, both inside `[if mso]`.

**Rounded / filled buttons** — because `border-radius` is ignored:

```html
<!--[if mso]>
<v:roundrect xmlns:v="urn:schemas-microsoft-com:vml"
             xmlns:w="urn:schemas-microsoft-com:office:word"
             href="https://example.com/orders/1234"
             style="height:48px;v-text-anchor:middle;width:212px;"
             arcsize="25%" stroke="f" fillcolor="#c64600">
  <w:anchorlock/>
  <center style="color:#ffffff;font-family:Arial,sans-serif;font-size:16px;font-weight:bold;">
    View your order
  </center>
</v:roundrect>
<![endif]-->
```

`arcsize` is a **percentage of the shorter side**, not a pixel radius: `arcsize="50%"` is a pill, `arcsize="25%"` on a 48px-tall button is a 12px radius. `<w:anchorlock/>` stops Word turning the shape into a draggable object. `stroke="f"` removes the default border. Width and height must be literal — VML does not grow with its content, so a translated label that runs long will clip. Measure the longest string you will ever put in it.

**Background images** — because the engine has no CSS `background-image`:

```html
<!--[if mso]>
<v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false"
        style="width:600px;height:330px;">
  <v:fill type="frame" src="https://cdn.example.com/hero.jpg" color="#171512"/>
  <v:textbox inset="0,0,0,0"><div><![endif]-->
      <!-- the real content goes here, visible to everyone -->
<!--[if mso]></div></v:textbox></v:rect><![endif]-->
```

The `color` attribute on `v:fill` is the fallback fill when the image is blocked. Set it, always.

**Both techniques are shrinking in value**, because new Outlook ignores VML completely and reads the non-MSO branch. The cost of keeping them is a few hundred bytes; the cost of dropping them is a broken button for every reader still on classic Outlook, which is a population measured in years, not months (§5).

---

## 4. Gmail, in detail

Gmail's renderer is a Chromium engine behind a **server-side sanitiser**, and the sanitiser is the part that matters. It rewrites your document before the engine ever sees it.

**What it does:**

- Strips external stylesheets and `@import`. There is no such thing as a linked stylesheet in email.
- Strips `<style>` in `<body>`. Head only.
- Enforces a **16,384-byte ceiling** on `<style>` content, counted across every `<style>` element (previously documented as 8,192 in 2017, raised since). Each element that crosses the ceiling is **removed whole**, along with every element after it (email-bugs #90), so a single block over the ceiling loses all of its CSS. Counting appears to happen before Gmail's own class-prefixing pass.
- Strips `position`, `transform`, `animation`, negative margins, and flex sub-properties.
- Does not support attribute selectors such as `div[class="content"]`.
- Rewrites class names, so any selector you did not inline is operating on names you do not control.

**The GANGA case restated, because it is the one that silently halves your QA:** in the Gmail app signed in with a non-Google account, embedded `<style>` is **not applied at all**, and images are blocked by default. Anything that lives only in the `<style>` block — the entire media query, the whole dark-mode block, a `:hover` — is absent. Your inline styles are the design for those readers.

That is the practical argument for inlining, stated without ideology: **inlined styles are the only styles every environment in the matrix agrees to render.**

---

## 5. The new Outlook, and the transition nobody has finished

New Outlook for Windows runs **Chromium via WebView2**, the same engine family as Edge and Outlook.com. Everything in the "why Outlook is hard" canon stops applying to it: flexbox works, `border-radius` works, two-column layouts render without intervention, `max-width` is honoured. And conditional comments and VML are inert.

**The timeline is genuinely contested, and this matters for how long you keep the ghost tables:**

| Source | Claim |
|---|---|
| Microsoft Learn (updated 2026-02-23) | Existing installations of classic Outlook, perpetual and subscription, are supported **until at least 2029** |
| Microsoft lifecycle | Office 2021, which includes Outlook 2021, retires on **2026-10-13**; Office 2019 retired in October 2025. This is the "October 2026" in many 2026 posts: the end of one perpetual version, not of classic Outlook |
| Really Good Emails (2026) | Classic Outlook is on Microsoft's roadmap **through at least 2029**, with no published end date; enterprise accounts do not transition by default until a tentative **May 2027** |
| Industry estimates cited in the same posts | The installed base of Word-engine Outlook stays significant in conservative enterprises **into 2028–2029** |

These are not quite contradictory — "support ends" and "people stop using it" are different events, and Microsoft has moved this date before. **The safe path: keep the Word-engine branch.** It costs a few hundred bytes in a conditional comment that every modern client ignores for free. Drop it when a client's own analytics show classic Outlook opens at zero, not when a blog post says the date has passed.

The transition is also the reason to prefer **fluid-hybrid over media queries**: fluid-hybrid is correct in the Word engine (via ghost tables), correct in Chromium Outlook (via `max-width`), and correct in GANGA (via `inline-block` wrapping) — three engines, one technique, no media query required.

---

## 6. Apple Mail, Yahoo, Samsung, Thunderbird

**Apple Mail (macOS + iOS)** is WebKit and the most capable client in the matrix: flexbox, grid, media queries, web fonts, `border-radius`, background images, `-webkit-` animations, real `prefers-color-scheme` support, and CSS custom properties. It is the only environment where a modern CSS email would work. It is not a licence to write one, because it is one of nine.

Two Apple-specific behaviours to handle:

- **`x-apple-data-detectors`.** iOS auto-links anything that looks like a date, address or phone number and restyles it blue. Neutralise it with an attribute-selector rule in the retained `<style>` block, plus `<meta name="format-detection" content="telephone=no,address=no,email=no,date=no">`.
- **Mail Privacy Protection.** Apple pre-fetches images through a proxy for Mail users who enabled it, which fires your tracking pixel whether or not a human looked. This inflates open rates, by as much as your share of Apple Mail readers with the protection on. It does not change how your HTML renders; it changes what your open rate means. Measure clicks.

**Yahoo / AOL** share a renderer. Two specific traps: `height` is rewritten to `min-height`, and `!important` written with a space before it (`! important`) is removed, so write `!important` without a space. Two older traps no longer reproduce in `caniemail.com`'s tests: rules after a CSS comment (desktop, gone by 2023) and the Android app stripping the first `<head>` (gone by 2025).

**Samsung Mail** decides layout from HTML `width` attributes, supports transitions but not keyframes, and applies `margin` to paragraphs and headings but not to `div`s or tables. Media-query behaviour reportedly varies with account type and app version.

**Thunderbird** is Gecko. It honoured `prefers-color-scheme` in 68, but not in 78 or 91, the latest versions `caniemail.com` tested. Its `<style>` support is reported inconsistently across versions.

---

## 7. Size limits and clipping

Two independent ceilings. Cross either and content silently disappears.

### Gmail clipping — 102 KB, measured at 102,400 bytes

**The number is 102,400 bytes**, which is 100 KiB, which is ~102.4 kB. The "is it 100 or 102?" argument is entirely a units confusion: tools that report "100 KB" are reporting 100 × 1024, and macOS reports the same file as "approximately 102 KB" because it divides by 1000. There is one threshold. Google does not publish it: the ESPs' documentation says 102 KB (Mailmodo and DailyStory, re-read 2026-10-07), and the byte-exact figure comes from measurement (Alice Li's testing, linked at the end of this file), so the build reports bytes against 102,400 and the docs call the threshold 102 KB.

Three things people get wrong about it:

1. **It counts the HTML part only.** Testing reported in 2026 found that adding hundreds of kilobytes of plain-text and AMP MIME parts did not change the result — those parts are measured separately.
2. **Measure the *delivered* message, not your template.** Link-tracking rewrites, merge-tag expansion, personalisation and the ESP's own CSS processing all add bytes after you hand the file over. Use Gmail's **Show original** on a real test send.
3. **What is lost is the footer.** Gmail truncates and hides the remainder behind "View entire message." The end of an email is the unsubscribe link, the physical address, and the tracking pixel — so a clipped email is simultaneously a compliance problem and a measurement problem.

`build_email.py` reports the figure on every build and exits 1 when it is exceeded. Aim to stay under ~90 KB so the ESP's additions have somewhere to go.

### Gmail `<style>` ceiling — 16,384 bytes

Separate from the above, and it bites earlier than you would think on a template with a large dark-mode block. **Gmail removes every `<style>` element that crosses the ceiling, and every one after it**, so the failure mode is "my media queries vanished," not "my CSS looks half-applied." Past the ceiling, `build_email.py` splits the retained CSS into blocks of about 4 KB in authoring order, so Gmail keeps the first ones: write the retained CSS most important first. Since the compiler inlines nearly everything, a healthy retained block is under 1 KB — the three templates in `assets/templates/` produce 600–750 bytes.

---

## 8. Dark mode

The hardest thing to be honest about, because the honest answer is *you do not control this*.

### The three behaviours

Every client does one of three things to an email when the reader is in dark mode:

| Behaviour | What it means | Who does it |
|---|---|---|
| **Respect** | Honours `prefers-color-scheme` and `color-scheme`; leaves your colours alone otherwise | Apple Mail (macOS/iOS). Outlook for Mac, Outlook.com and the Outlook iOS/Android apps honour the media query too, while also rewriting some colours (below). Samsung Email 6.1 |
| **Partial inversion** | Selectively rewrites *some* colours — typically backgrounds and near-black/near-white text — and leaves the rest | Outlook.com / Outlook Web (via injected `[data-ogsc]`/`[data-ogsb]` attributes), Outlook Mac, Outlook iOS/Android, Gmail Android, new Outlook Windows, GANGA |
| **Full forced inversion** | Rewrites the whole palette algorithmically, including your logo and your pale text | Gmail iOS, classic Outlook Windows |

Sources disagree at the margins — particularly on Gmail web (some describe it as leaving rich HTML alone, others as applying Chromium-style darkening) and on new Outlook Windows (described as "likely web-style partial", i.e. nobody has tested it properly). **Safe path: assume partial inversion everywhere except Apple Mail and Thunderbird, and design so that partial inversion cannot produce an unreadable pair.**

### The meta tags

```html
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
```

`color-scheme` is recognised by Apple/WebKit clients and is what tells them you have handled dark mode deliberately, so they should not intervene. `supported-color-schemes` is the legacy Apple spelling, kept for older devices. Neither is a universal control, and neither stops Gmail iOS or Outlook Windows from inverting anything.

### The techniques, and what each actually buys

| Technique | Works in | Buys you |
|---|---|---|
| `color-scheme` / `supported-color-schemes` meta | Apple, WebKit | "I handled it, do not auto-invert" |
| `@media (prefers-color-scheme: dark)` block | Apple Mail; Outlook for Mac, Outlook.com, Outlook iOS and Android; Samsung Email 6.1 | Real authored dark colours |
| `[data-ogsc]` / `[data-ogsb]` selectors | Outlook.com and other Outlook clients that inject them | Corrective overrides where Outlook rewrote something badly |
| PNG with a light *and* dark safe appearance | Everywhere | A logo that survives inversion |
| Avoiding pure `#000000` and `#ffffff` | Everywhere | Inversion algorithms key on the extremes; near-black and near-white are rewritten most aggressively. The token set's `--neutral-900` (`#171512`) and `--neutral-50` (`#faf9f7`) are deliberately not the extremes. |
| A visible border around light logos | Everywhere | A white-on-white logo after inversion becomes a bordered box rather than nothing |

### What cannot be controlled, stated plainly

- **You cannot opt out of forced inversion** in Gmail iOS or classic Outlook Windows. No meta tag, no media query, no `!important` prevents it.
- **You cannot predict which colours get rewritten** under partial inversion. Outlook's rewriting is heuristic and has changed between versions.
- **You cannot test your way to certainty**, because the behaviour depends on client version, OS version and the reader's specific setting, and vendors ship changes without announcement.
- **A dark-designed email is riskier than a light one**, because a client that force-inverts a dark design produces a light one with dark-mode logo assets in it.

**The practical position:** design light, with a palette whose colours are still legible if lightness is flipped, using images that read on both. Add the `prefers-color-scheme` block because it is nearly free and Apple Mail, the Outlook apps other than classic Windows, and Samsung Email 6.1 honour it. Verify contrast in both directions. Then stop — further effort buys unpredictability, not control.

**Re-point every colour the block reaches.** The dark block's rules are `!important`, so they beat the inline colours the build wrote. `a { color: var(--email-dark-link) !important }` turns a button's white label into the dark link colour on the accent fill, 2.56:1 in the shipped templates before 3.4.0; a `.button { color: var(--fg-on-accent) !important }` rule wins it back, since a class beats an element. And a colour set in light mode that the block never re-points, such as an accent eyebrow, stays light-mode dark on the dark surface. `lint_email.py`'s `dark` check applies the retained block as a client that honours it does and measures both.

---

## 9. What I could not verify

Stated explicitly so nobody mistakes an assumption for a finding.

| Claim | Status |
|---|---|
| New Outlook's exact media-query support | **Unresolved.** Sources say "partial" and "only partial support for media queries" without specifying which parts. Treat media queries as an enhancement there. |
| Gmail web media-query behaviour | **Sources conflict** (note 6). The practical answer holds regardless, but the underlying fact is not settled. |
| Whether Gmail still drops the whole `<style>` block on a nested at-rule | **Unverified in 2026.** Documented historically; not retested. Avoid nested at-rules regardless — several clients remove them. |
| Samsung Mail media-query support by account type | **Unverified.** Reported as version- and account-dependent; needs a device to confirm. |
| Classic Outlook's true end-of-life date | Supported until **at least 2029** (Microsoft, §5). October 2026 is Office 2021's retirement, not classic Outlook's; May 2027 is a tentative enterprise switch-over date. |
| Exact current share of blocked-image opens | **Not established.** Widely repeated figures are old and vary by audience type. The design rule (alt text must carry meaning) does not depend on the number. |
| Gmail iOS dark-mode inversion details | **Directionally verified, mechanically not.** Described consistently as high-risk full inversion; the exact algorithm is undocumented. |
| Whether Gmail counts the HTML part's raw or transfer-encoded bytes | **Unverified.** Measure the delivered message via Show original and do not rely on the distinction. |

---

## Sources

- [New Outlook vs Classic Outlook: Email Rendering in 2026 — EmailMavlers](https://emailmavlers.com/blog/new-outlook-vs-classic-outlook-email-rendering/)
- [Classic Outlook vs the new Outlook: what's actually changing — Really Good Emails](https://reallygoodemails.com/school/blog/classic-vs-new-outlook-rendering-changes)
- [The Complete Guide to Email Client Rendering Differences in 2026 — mailpeek](https://dev.to/mailpeek/the-complete-guide-to-email-client-rendering-differences-in-2026-243f)
- [Gmail HTML Email Development: Why Your CSS Is Not Working — Email on Acid](https://www.emailonacid.com/blog/article/email-development/12-things-you-must-know-when-developing-for-gmail-and-gmail-mobile-apps-2/)
- [Gmail limits `<style>` to 16 kB — hteumeuleu/email-bugs #90](https://github.com/hteumeuleu/email-bugs/issues/90)
- [Does Gmail clip at 102KB or 100KB? What it's actually counting — Alice Li](https://alicelicode.medium.com/does-gmail-clip-at-102kb-or-100kb-what-its-actually-counting-728c8c7497d2)
- [Correcting Outlook DPI Scaling Issues — Courtney Fantinato](https://www.courtneyfantinato.com/correcting-outlook-dpi-scaling-issues/)
- [Bulletproof Email Buttons: Why VML Still Matters in 2026 — MiN8T](https://min8t.com/articles/bulletproof-email-buttons)
- [Email Client Dark Mode Support Matrix — MailMode](https://www.mailmode.app/learn/email-client-dark-mode-support-matrix)
- [`<style>` element support — Can I email](https://www.caniemail.com/features/html-style/)
- [`@media` support — Can I email](https://www.caniemail.com/features/css-at-media/)
- [CSS variables support — Can I email](https://www.caniemail.com/features/css-variables/)
- [`display:grid` support — Can I email](https://www.caniemail.com/features/css-display-grid/)
- ["Fake" Background Image Technique for GANGA — FreshInbox](https://freshinbox.com/blog/fake-background-image-technique-for-gmail-app-for-non-google-accounts-ganga/)
- [Apple Mail Privacy Protection: The 2026 Guide — Sender](https://www.sender.net/blog/apple-mail-privacy-protection/)

Related: `references/email-architecture.md` (how to build against these constraints), `references/email-workflow.md` (how to test them), `scripts/lint_email.py` (the machine-readable form of this file).
