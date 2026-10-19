# Email Architecture

How to build an email so it survives the matrix. `references/email-client-matrix.md` says what breaks; this says what to build instead.

The governing idea: **email has no cascade, so structure carries the meaning that CSS carries on the web.** On the web a `<div>` is neutral and the stylesheet decides everything. In email the element *is* the decision — a `<td>` with padding is the only spacing primitive that works in every client, so the table skeleton is not legacy styling, it is the layout engine.

## Contents

1. [The skeleton, and why each level exists](#1-the-skeleton-and-why-each-level-exists)
2. [The head, and the MSO scaffolding](#2-the-head-and-the-mso-scaffolding)
3. [Spacing discipline — Law 2, table-shaped](#3-spacing-discipline--law-2-table-shaped)
4. [The component set](#4-the-component-set)
5. [Elevation without shadows](#5-elevation-without-shadows)
6. [Bulletproof buttons](#6-bulletproof-buttons)
7. [Responsive: fluid-hybrid versus media queries](#7-responsive-fluid-hybrid-versus-media-queries)
8. [Images](#8-images)
9. [Accessibility in email](#9-accessibility-in-email)
10. [Anti-patterns](#10-anti-patterns)

---

## 1. The skeleton, and why each level exists

Three nesting levels, and every one of them is load-bearing. This is the part people trim first and regret.

```html
<body style="margin:0;padding:0;width:100%;background-color:#faf9f7;">

  <!-- 1. WRAPPER — full width, owns the page background. -->
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#faf9f7;">
    <tr>
      <td align="center" style="padding-top:48px;padding-bottom:48px;">

        <!-- 2. GHOST TABLE — Word engine only; supplies the fixed width
             that max-width cannot. Invisible to every other client. -->
        <!--[if mso]>
        <table role="presentation" align="center" cellpadding="0" cellspacing="0"
               border="0" style="width:600px;"><tr><td>
        <![endif]-->

        <!-- 3. CONTAINER — the 600px column. -->
        <table role="presentation" align="center" cellpadding="0" cellspacing="0"
               border="0" style="width:100%;max-width:600px;background-color:#ffffff;">

          <!-- 4. CONTENT ROWS — one <tr> per band of content. -->
          <tr>
            <td style="padding-left:24px;padding-right:24px;padding-top:24px;">
              …
            </td>
          </tr>

        </table>

        <!--[if mso]></td></tr></table><![endif]-->

      </td>
    </tr>
  </table>
</body>
```

| Level | Exists because | Delete it and |
|---|---|---|
| `<body>` background | Several clients ignore a background set only on `<body>` | the page behind your container is white in some clients and grey in others |
| **1. Wrapper table** | `<body>` styling is unreliable; a full-width table is not | the canvas colour does not reach the edges, and the container floats on a white page |
| `align="center"` on the `<td>` | `margin:0 auto` does nothing in the Word engine | the email is left-aligned in Outlook and centred everywhere else |
| **2. Ghost table** | The Word engine ignores `max-width` entirely | Outlook renders the container full-width — 1400px of 16px text on a wide monitor |
| **3. Container** | One column, one width, one place to change it | nothing holds the 600px constraint outside Outlook |
| **4. Content rows** | A `<tr>` is the only reliable vertical unit | you are back to margins, which the Word engine collapses |

**Why 600px.** Not superstition: it is the widest column that fits the classic Outlook reading pane at 100% zoom on a 1024px-wide window without a horizontal scrollbar. Everything else follows from that one number. `--email-width-inner` (552px) is 600 minus two 24px gutters, and it is the width every full-bleed image inside the padding must be.

**Nesting depth.** Three levels of table is the floor, not a target. Each additional nesting level is another place the Word engine can round a width, and Outlook's own rendering gets measurably slower past about six. If a component needs a fourth level, check whether a `<td>` with padding does the same job.

---

## 2. The head, and the MSO scaffolding

Every line earns its place. Nothing here is cargo. `build_email.py` adds the namespaces and the `[if mso]` block; the rest you write once per template.

```html
<!DOCTYPE html>
<html lang="en" dir="ltr"
      xmlns:v="urn:schemas-microsoft-com:vml"
      xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="x-apple-disable-message-reformatting">
<meta name="format-detection" content="telephone=no,address=no,email=no,date=no">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>Your receipt from Northbeam — order 41822</title>

<!--[if mso]>
<noscript><xml><o:OfficeDocumentSettings>
  <o:AllowPNG/><o:PixelsPerInch>96</o:PixelsPerInch>
</o:OfficeDocumentSettings></xml></noscript>
<style type="text/css">
  table, td, div, p, a, h1, h2, h3, li, blockquote { font-family: Arial, Helvetica, sans-serif !important; }
</style>
<![endif]-->
</head>
```

| Line | Without it |
|---|---|
| `<!DOCTYPE html>` | several clients drop to quirks mode and your box model changes |
| `lang="en"` | a screen reader reads English copy with the system language's phonemes |
| `dir="ltr"` | free now, and it matters the day you localise to Arabic or Hebrew |
| `xmlns:v` / `xmlns:o` | the VML and `o:` elements are unrecognised |
| `charset=utf-8` | a smart quote renders as `â€™` |
| `viewport` | Android clients zoom a 600px layout out to fit a 360px screen |
| `x-apple-disable-message-reformatting` | iOS re-flows your layout on its own initiative |
| `format-detection` | iOS auto-links dates and addresses and restyles them blue |
| `color-scheme` | Apple clients auto-invert instead of using your dark block |
| `<title>` | no accessible name, and no tab title in "view in browser" |
| `<o:PixelsPerInch>96</o:PixelsPerInch>` | the 120-DPI bug — see `email-client-matrix.md` §3 |
| `<o:AllowPNG/>` | Outlook may convert your PNGs to a lower-fidelity format |
| the MSO font rule | the Word engine cannot resolve `-apple-system`, walks the stack, matches nothing, and lands on its own default **serif**. This is the single most common "why does this look like a 1998 memo" cause. |

---

## 3. Spacing discipline — Law 2, table-shaped

Law 2 says *parents own the gaps*. Email has no `gap`, and child `margin` is unreliable in the Word engine and absent on `div`s in Samsung Mail. So the law does not disappear; it changes mechanism.

> **In email, a gap is owned by the parent `<table>` — expressed either as padding on the content `<td>` or as a dedicated spacer `<tr>`. A content element never sets its own outer spacing.**

The two mechanisms are not interchangeable, and picking the wrong one is what makes email spacing drift.

### The decision table

| The space is | Use | Because |
|---|---|---|
| **Inside** a band — the gutter, the inset of a card | `padding` on the `<td>` | The `<td>` is the box; padding is its inset. One owner. |
| **Between** two sibling content rows | a **spacer `<tr>`** | Two rows cannot both own the space between them. A dedicated row owns it, and it is visible in the markup. |
| Between two columns in a row | a **gutter `<td>`** of fixed width | Same argument, horizontal. |
| Around the whole container | `padding` on the wrapper's `<td>` | The wrapper is the parent of the container. |
| Between a heading and its own paragraph | `padding-top` on the paragraph | Exception, and a deliberate one: these are one unit, not two siblings. |

### The spacer row, written correctly

```html
<tr>
  <td style="height:24px;font-size:0;line-height:0;">&nbsp;</td>
</tr>
```

All four parts are required:

- **`height`** — the actual gap. Always a token value.
- **`font-size:0` and `line-height:0`** — without them the `&nbsp;` contributes its own line box, and your 24px gap is 24px *plus a line of text*, differently in every client.
- **`&nbsp;`** — an empty `<td>` is collapsed to zero height by several clients, including the Word engine. The non-breaking space gives it something to be tall about.

**Never nest a spacer row inside a content `<td>`.** It belongs as a sibling `<tr>` in the same table, or the parent no longer owns the gap.

### Why padding-only does not work

The tempting simplification is to put all spacing in `padding-bottom` on each content `<td>` and skip spacer rows. It fails for the same reason child margins fail on the web: **the last row then carries a gap that should not exist**, and you end up with `:last-child` logic that email cannot express. A spacer row is a sibling; it is inserted *between* things by construction, so there is never a trailing one.

### Do not use `cellpadding`

`cellpadding="24"` applies to every cell in the table, including your spacer rows, and it is not equal to CSS padding in the Word engine. Always `cellpadding="0" cellspacing="0" border="0"` on every table, and put spacing in CSS on the specific `<td>` that owns it.

---

## 4. The component set

Nine components carry essentially every email an agency ships. All markup below is what the compiler emits after inlining; author it with classes and let `build_email.py` produce this.

### Header

```html
<tr><td style="padding:24px;">
  <img src="https://cdn.example.com/logo-2x.png" width="132" height="28"
       alt="Northbeam" style="width:132px;height:28px;display:block;">
</td></tr>
<tr><td style="height:1px;background-color:#e7e5e2;font-size:0;line-height:0;">&nbsp;</td></tr>
```

### Hero image

```html
<tr><td>
  <a href="https://example.com/ridgeline">
    <img src="https://cdn.example.com/hero-1200.jpg" width="600" height="330"
         alt="The Ridgeline Jacket in Deep Pine, worn on a wet coastal trail"
         style="width:100%;max-width:600px;height:auto;display:block;border:0;">
  </a>
</td></tr>
```

Source at 1200px, `width` attribute at 600. The attribute is what the Word engine sizes from; the CSS is what everyone else scales with. A linked image must have real alt text, or the link has no accessible name.

### Text block

```html
<tr>
  <td style="padding-left:24px;padding-right:24px;">
    <h1 style="margin:0;font-family:Arial,sans-serif;font-size:32px;line-height:38px;
               font-weight:700;color:#080706;">Three new colours. Same jacket.</h1>
    <p style="margin:0;padding-top:16px;font-family:Arial,sans-serif;font-size:16px;
              line-height:26px;color:#171512;">Slate, Ochre and Deep Pine…</p>
  </td>
</tr>
```

`margin:0` on every heading and paragraph, always. Client default margins differ by tens of pixels and will wreck a carefully-spaced column. The intentional spacing is `padding-top` on the paragraph, because a heading and its paragraph are one unit.

### Two-column that stacks — see §7. ### Button — see §6.

### Divider

```html
<tr>
  <td style="padding-left:24px;padding-right:24px;">
    <div style="height:1px;background-color:#e7e5e2;font-size:0;line-height:0;">&nbsp;</div>
  </td>
</tr>
```

A coloured 1px block, not an `<hr>` — `<hr>` styling is inconsistent across the matrix.

### Image with caption

```html
<td style="padding-left:24px;padding-right:24px;">
  <img src="https://cdn.example.com/bench-1104.jpg" width="552" height="310"
       alt="A repair technician patching a cuff at the Wharf Road bench"
       style="width:100%;max-width:552px;height:auto;display:block;">
  <p style="margin:0;padding-top:8px;font-family:Arial,sans-serif;font-size:13px;
            line-height:20px;color:#5f5c57;">Marisol, who has re-cuffed more
    Ridgelines than anyone alive.</p>
</td>
```

552px, not 600 — the image lives inside the 24px gutters. The caption is *not* a repeat of the alt text: alt describes the image for someone who cannot see it, the caption adds something for someone who can. Saying the same thing twice means a screen reader hears it twice.

### Well / callout

```html
<td style="padding-left:24px;padding-right:24px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#f3f1ef;border-radius:8px;">
    <tr><td style="padding:16px;">…</td></tr>
  </table>
</td>
```

A nested table, not a `<div>` — the Word engine will not reliably paint a background or apply padding on a `div`.

### Footer with unsubscribe

```html
<td style="background-color:#f3f1ef;padding:24px;">
  <p style="margin:0;font-family:Arial,sans-serif;font-size:13px;line-height:20px;
            color:#5f5c57;">Northbeam Supply Co., 118 Wharf Road, Portland, OR 97209</p>
  <p style="margin:0;padding-top:8px;font-family:Arial,sans-serif;font-size:13px;
            line-height:20px;color:#5f5c57;">You subscribed at northbeam.example.com.
    <a href="https://example.com/preferences?e=…" style="color:#9b3400;">Change what we
    send you</a> or <a href="https://example.com/unsubscribe?e=…"
    style="color:#9b3400;">unsubscribe</a>.</p>
</td>
```

13px, not 11px. The physical postal address is a CAN-SPAM requirement for commercial email, and legal text that nobody can read is not a defence — it is the same liability in smaller type.

---

## 5. Elevation without shadows

`box-shadow` is ignored by the Word engine and flattened elsewhere, so the six-step elevation ladder does not survive. Three replacements, in order of preference:

**1. A border.** `--email-edge` (`1px solid #e7e5e2`) separates a surface from its canvas as well as `--elevation-card` did, and it works everywhere.

**2. Surface contrast.** `--bg-surface` (white) on `--bg-canvas` (`#faf9f7`) reads as lifted without any border at all. This is the cheapest option and usually enough.

**3. A table-based shadow**, when real depth is genuinely wanted:

```html
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
  <tr>
    <td style="background-color:#e7e5e2;padding-bottom:2px;padding-right:2px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
             style="background-color:#ffffff;">
        <tr><td style="padding:24px;">…</td></tr>
      </table>
    </td>
  </tr>
</table>
```

An offset solid block behind the surface. It is a hard-edged shadow, not a soft one, and that is the honest version of the effect at this fidelity. Use it once per email at most; two of them looks like a mistake.

---

## 6. Bulletproof buttons

A button is the highest-stakes component in an email — it is the click — and it is the one `border-radius` breaks. The technique is a two-branch component: VML for the Word engine, a padded anchor for everyone else.

```html
<td align="left">
  <!--[if mso]>
  <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml"
               xmlns:w="urn:schemas-microsoft-com:office:word"
               href="https://example.com/orders/41822"
               style="height:48px;v-text-anchor:middle;width:212px;"
               arcsize="25%" stroke="f" fillcolor="#c64600">
    <w:anchorlock/>
    <center style="color:#ffffff;font-family:Arial,sans-serif;font-size:16px;
                   font-weight:bold;">View your order</center>
  </v:roundrect>
  <![endif]-->
  <!--[if !mso]><!-- -->
  <a href="https://example.com/orders/41822"
     style="display:inline-block;padding:14px 28px;background-color:#c64600;
            color:#ffffff;font-family:Arial,sans-serif;font-size:16px;line-height:20px;
            font-weight:700;text-decoration:none;border-radius:8px;mso-hide:all;">View
     your order</a>
  <!--<![endif]-->
</td>
```

### Why each piece

- **`display:inline-block` + `padding` on the `<a>`**, not padding on a `<td>` with the anchor inside. Padding on the cell means the *cell* is the big target and the *anchor* is only the text — so on a phone, the top third of what looks like a button does nothing. Padding on the anchor makes the entire coloured rectangle the link. This is the whole argument for the padded-anchor form.
- **`align="left"` on the containing `<td>`** rather than `text-align:center` on a parent `div`: the Word engine ignores `text-align` on non-cell parents.
- **`v-text-anchor:middle`** vertically centres the VML label; without it the text sits at the top.
- **`<w:anchorlock/>`** stops Word treating the shape as a draggable object.
- **`arcsize`** is a percentage of the shorter side. 48px tall × `25%` = 12px radius. `50%` is a pill.
- **`mso-hide:all`** on the anchor is belt-and-braces: the `[if !mso]` branch should already hide it from Word.
- **The VML width is literal.** VML does not grow with its content. Measure the longest label you will ever use — including the German translation — and size it to that.

### Tap target

`padding: 14px 28px` at `font-size:16px; line-height:20px` produces a 48px-tall box: above the 44px minimum, with room for the Word engine's rounding. That is why `--email-button-pad` is `14px 28px` and not a rounder number.

### Ghost buttons

An outlined button is a border and a transparent fill. In the Word engine the fill is not transparent, it is *unset*, and VML has no border-radius without `stroke="t"` plus `strokecolor`. It is buildable and it is rarely worth it — a low-contrast outlined button on a phone in sunlight is a usability problem before it is a rendering one.

---

## 7. Responsive: fluid-hybrid versus media queries

Two strategies. They are not equal, and the default is the less famous one.

### Media-query responsive

Fixed desktop layout; a `@media (max-width: 600px)` block restacks it. Clean to write, and it fails completely in every client that drops the `<style>` block — which includes **GANGA**, the Gmail app with a non-Google account. Those readers get the desktop layout crushed into a phone.

### Fluid-hybrid (the default)

The layout is correct *without any media query*, using three mechanisms that stack:

```html
<td style="font-size:0;">
  <!--[if mso]>
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width:552px;">
    <tr><td style="width:264px;" valign="top">
  <![endif]-->

  <div style="width:100%;max-width:264px;display:inline-block;vertical-align:top;">
    … column one …
  </div>

  <!--[if mso]></td><td style="width:24px;">&nbsp;</td><td style="width:264px;" valign="top"><![endif]-->

  <div style="width:24px;display:inline-block;font-size:0;line-height:0;" aria-hidden="true">&nbsp;</div>

  <div style="width:100%;max-width:264px;display:inline-block;vertical-align:top;">
    … column two …
  </div>

  <!--[if mso]></td></tr></table><![endif]-->
</td>
```

| Mechanism | Handles |
|---|---|
| `max-width` + `display:inline-block` | Every modern client. On a 375px screen two 264px boxes cannot sit side by side, so the second **wraps** — stacking with no media query and no `<style>` block. |
| The `[if mso]` ghost table | The Word engine, which ignores `max-width`. It gets explicit 264px cells. |
| `font-size:0` on the parent `<td>` | Kills the whitespace between the `inline-block` divs, which would otherwise add ~4px and break the arithmetic. Each column resets its own font-size. |

**Why this is the default:** it is correct in the Word engine, correct in Chromium Outlook, correct in Apple Mail, and correct in GANGA — four engines, one technique, zero dependence on CSS surviving. The media query then becomes a pure enhancement: padding tightening, headline sizes dropping. If it is stripped, nothing is *broken*; it is just less refined.

Add the media query too. But make it the second thing.

```css
@media only screen and (max-width: 600px) {
  .pad { padding-left: 20px !important; padding-right: 20px !important; }
  .h1  { font-size: 26px !important; line-height: 32px !important; }
  .col { max-width: 100% !important; }
  .gutter { width: 0 !important; font-size: 0 !important; }
}
```

`!important` on every declaration, because these rules must beat the inline styles the compiler wrote. This is the one place `!important` is correct in this entire suite — Law 5 banned it on the web because it inverts layer order, and email has no layers to invert.

**Column arithmetic.** 552px inner width, two columns, one 24px gutter: `(552 − 24) ÷ 2 = 264`. Keep the ghost-table cell widths and the `max-width` values identical, or the Word engine and everyone else disagree about where the fold is.

---

## 8. Images

### Retina sizing

Export at **2×**, set the `width`/`height` **attributes** to the 1× display size, and set `width` in CSS as well.

```html
<img src="hero-1200.jpg" width="600" height="330" alt="…"
     style="width:100%;max-width:600px;height:auto;display:block;">
```

The attributes are what the Word engine sizes from — it does not read the CSS. Omit them and a 1200px source renders at 1200px and bursts the column. `height:auto` in CSS lets everyone else scale proportionally when `width:100%` kicks in.

### `display:block`

On every image, without exception. An inline image sits on the text baseline, and the descender space below it renders as a 3–5px gap — differently in each client. It is the most common "why is there a mystery gap under my image" cause, and `display:block` is the whole fix.

### Alt text that carries meaning

Images are blocked by default in several clients and on many corporate gateways, and a blocked image with no alt is a silent hole where your message was.

| Image | Bad alt | Good alt |
|---|---|---|
| Logo | `logo` | `Northbeam` |
| Hero product shot | `hero image` | `The Ridgeline Jacket in Deep Pine, worn on a wet coastal trail` |
| Spacer / tracking pixel | *(omit)* | `alt=""` |
| Image that is the whole link | `button` | `View your order` |

Style the alt text as well — many clients render it in the space the image would have occupied, and an unstyled alt in 12px Times on white is a worse fallback than it needs to be. Put `font-family`, `font-size` and `color` on the `<img>` itself; they apply to the alt text when the image does not load.

**A linked image with `alt=""` is a link with no accessible name.** A screen reader announces it as its URL. `lint_email.py` flags this as an error.

### Background-image fallbacks

Always set a `background-color` alongside. In the Word engine the CSS background image does not exist at all; in GANGA it frequently does not load. If the image is what makes the text readable, the colour must do the same job alone.

For the Word engine specifically, use the VML `v:rect`/`v:fill` pattern from `email-client-matrix.md` §3, and set `color` on `v:fill` as the blocked-image fallback.

**The GANGA quirk worth knowing:** a background image alone does not trigger the "display images" prompt, because there is no visible broken image to prompt about. Including one real `<img>` in the message gives the reader something to click.

### Weight budget

| Item | Budget |
|---|---|
| Total HTML (after ESP processing) | **under 90 KB** — see the ESP-documented 102 KB clipping threshold; 102,400 bytes is the measured value, `email-client-matrix.md` §7 |
| Retained `<style>` block | under 2 KB (Gmail drops past 16,384 bytes) |
| Any single image | under 200 KB |
| All images combined | under 1 MB |
| Number of images | as few as the message needs |

**Never base64-encode an image.** It counts against the HTML part's clipping threshold — a single 40 KB image becomes ~54 KB of HTML — and Gmail and Outlook block `data:` URIs anyway. Host the image.

---

## 9. Accessibility in email

A screen reader in an email client is a genuinely different environment from a screen reader in a browser, and the differences all cut the same way: **you have less to work with, so the basics matter more.**

What is different: there are no landmarks, because the client owns the page structure and your email is a fragment inside it. There is no skip link worth writing. Focus order is whatever the client gives you. There is no live region, no ARIA widget worth attempting, and no JavaScript. What remains is document semantics — which is exactly what a nested table skeleton destroys unless you say otherwise.

### The floor

**1. `role="presentation"` on every layout table.** Non-negotiable and the highest-impact single line in the file. Without it, a screen reader announces "table, 4 rows, 1 column" for each of the three-to-six nested tables before any content — for every band of the email. With it, the tables vanish from the accessibility tree and the content reads as a document.

```html
<table role="presentation" cellpadding="0" cellspacing="0" border="0">
```

A real data table — a receipt's line items, arguably — is the one exception, and then it needs `<th>` and real headers, not `role="presentation"`.

**2. `lang` on `<html>`.** A screen reader chooses a pronunciation engine from it. Without it, English copy is read with the system language's phonemes.

**3. A real `<title>`.** It is the document's accessible name, and the page title when a reader clicks "view in browser."

**4. Semantic headings in order.** One `<h1>`, then `<h2>`, then `<h3>` — no levels skipped. Screen reader users navigate an email by heading exactly as they navigate a page. A `<p>` styled to look like a heading is invisible to that.

**5. Link text that works out of context.** A screen reader can list every link in the message with no surrounding prose. "Read more" six times is six identical rows. `lint_email.py` treats this as an error. That is this skill's choice, not Level A: SC 2.4.4 (Level A) lets the surrounding sentence explain a link, and the rule for links read out of context is 2.4.9 (Link Only), Level AAA. Email readers list links out of context all the time, so the skill holds 2.4.9.

**6. Measured contrast.** 4.5:1 for body text, 3:1 for large text (24px, or 18.66px bold). Email is read on phones in sunlight more than any other medium, so the floor really is a floor. Every role pair in `assets/email-tokens.json` carries its measured ratio; `lint_email.py` re-measures the built file.

**7. A real text size.** 16px body, 13px minimum for anything else. iOS Mail auto-enlarges text below about 13px and does it **per element**, so one small legal line grows and the container beside it does not.

**8. Never convey meaning with colour alone.** A red "overdue" and a green "paid" that differ only in colour are the same word to a reader who cannot distinguish them.

**9. `aria-hidden="true"` on spacer and gutter elements.** A gutter div containing `&nbsp;` is announced as "blank" otherwise.

### What not to bother with

`tabindex`, `aria-label` on layout elements, `role="main"`, skip links, and `alt` on a tracking pixel beyond `alt=""`. None of them help in an email client and several confuse the ones that do read ARIA.

---

## 10. Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| A `<div>`-based layout | The Word engine will not reliably apply background, padding or width to a `div`. |
| `display:flex` "because Gmail supports it" | Gmail keeps `display:flex` and strips the flex sub-properties, so your columns become rows — in Gmail only. |
| `margin-bottom` on a content block | Collapses unpredictably in the Word engine, absent on `div`s in Samsung Mail. Use a spacer row. |
| A spacer row without `font-size:0;line-height:0` | The `&nbsp;` adds its own line box; your 24px gap is 24px plus a line, differently per client. |
| An empty `<td>` as a spacer | Collapsed to zero height by several clients. |
| `cellpadding="24"` | Applies to every cell in the table, including the spacers, and does not equal CSS padding in the Word engine. |
| Padding on the `<td>` around a button instead of on the `<a>` | The visible rectangle is bigger than the tap target. On a phone, the top of the button does nothing. |
| A media query as the only stacking mechanism | GANGA readers get the desktop layout on a phone, and nothing in your QA will show it. |
| `<img>` without `width`/`height` attributes | The Word engine sizes from the attributes. A 2× source renders at 2×. |
| `<img>` without `display:block` | 3–5px of phantom space under it, different in every client. |
| Base64 images | Counts against the clipping threshold at ~1.37× the file size, and blocked in Gmail and Outlook anyway. |
| A layout table without `role="presentation"` | Every nested table is announced before any content. |
| 11px legal text | iOS Mail enlarges it per element and breaks the alignment. |
| `!important` in an inline style, written as `! important` | Yahoo strips `!important` when it has a space before it. |
| A CSS comment in the retained `<style>` block | Bytes against Gmail's style limit. (Yahoo desktop used to ignore every rule after a comment; that no longer reproduces.) The compiler strips them. |
| A dark-designed email | A client that force-inverts turns it light, with your dark-mode logo assets still in it. |
| Hand-writing a hex in a template | Law 1. The compiler exists so you never have to. |

---

Related: `references/email-client-matrix.md` (what each client does), `references/email-workflow.md` (building, testing, sending), `references/token-contract.md` (the vocabulary), `scripts/build_email.py` (the compiler), `scripts/lint_email.py` (the gate).
