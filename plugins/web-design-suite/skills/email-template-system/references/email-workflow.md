# Email Workflow

Authoring, building, testing, sending. `email-architecture.md` is what to build; this is how the work moves from a token file to an inbox without anyone hand-editing compiled HTML at 11pm.

## Contents

1. [The source-template format](#1-the-source-template-format)
2. [The build step](#2-the-build-step)
3. [Preheader text](#3-preheader-text)
4. [Testing: what you can check for free](#4-testing-what-you-can-check-for-free)
5. [Testing: what needs a rendering service](#5-testing-what-needs-a-rendering-service)
6. [Deliverability that lives in the HTML](#6-deliverability-that-lives-in-the-html)
7. [The plain-text part](#7-the-plain-text-part)
8. [ESP handoff](#8-esp-handoff)
9. [The pre-send checklist](#9-the-pre-send-checklist)

---

## 1. The source-template format

A source template is ordinary HTML with two differences from a sent email: **it uses `var(--token)` everywhere a value appears**, and **its CSS lives in a readable `<style>` block with classes** instead of in inline attributes.

```
assets/templates/          source templates, token-authored, version-controlled
assets/email-tokens.json   the token projection (see the contract)
build/                     compiler output — gitignored, never hand-edited
```

### The rules

1. **No literal hexes, sizes or spacing values.** Every value is `var(--token)`. `lint_email.py --source` catches them in the source, where they are still cheap to fix: a hand-written colour or a `var()` of a dropped token is an error that names the token to use, and a length or weight literal a warning that names the role holding the same value. On the built file it catches what survived.
2. **Classes in a `<style>` block, one rule per component.** Law 4 survives here: a reviewer predicts a component's appearance from one rule.
3. **Utilities last.** Email has no cascade layers, so **source order is the only layer order there is**. A single-class utility (`.muted`) beats a single-class component rule (`.line-item`) only if it is declared after it. Declared before, it loses silently at equal specificity — and because the compiler implements the real cascade, you get exactly what CSS says you asked for.
4. **Inline `style` only for per-instance values** — the one padding that differs on this one row. Everything repeated belongs in a class.
5. **Mark blocks that must survive as CSS.** Media queries, `prefers-color-scheme`, `[x-apple-data-detectors]` and any `:hover` are retained automatically because they cannot be resolved to a static element set. A block you want kept verbatim gets `<style data-embed="keep">`.
6. **Merge tags in a neutral form** — `{{order_number}}` — and translate at handoff (§8).

### What the compiler retains versus inlines

| Selector | Fate |
|---|---|
| `.card`, `td`, `#hero`, `.card .title`, `div > p` | **inlined** |
| anything with `:`, `[`, `~`, `+` | **retained** |
| anything inside `@media` or `@supports` | **retained** |
| `@font-face`, `@keyframes` | **retained verbatim** |
| a rule with both kinds of selector in its list | **split** — inlinable parts inlined, the rest retained |

---

## 2. The build step

```bash
python -m scripts.build_email assets/templates/transactional-receipt.html \
    --out build/receipt.html \
    --text build/receipt.txt

python -m scripts.lint_email build/receipt.html --transactional
```

That is the whole pipeline. As a Makefile:

```make
TEMPLATES := $(wildcard assets/templates/*.html)
BUILT     := $(patsubst assets/templates/%.html,build/%.html,$(TEMPLATES))

build/%.html: assets/templates/%.html assets/email-tokens.json
	@mkdir -p build
	python -m scripts.build_email $< --out $@ --text $(@:.html=.txt)

.PHONY: all lint clean
all: $(BUILT)
lint: all
	python -m scripts.lint_email $(BUILT)
clean:
	rm -rf build
```

And as a CI gate — `lint_email.py` exits non-zero on any error, which is the whole point:

```yaml
- name: Build and lint email templates
  run: |
    make all
    python -m scripts.lint_email build/*.html
```

### What the compiler does, in order

1. Resolves `var(--token)` everywhere — `<style>` blocks including `@media` preludes, `style` attributes, presentational attributes, and inside MSO conditional comments. An unknown token with no fallback is a hard error.
2. Parses the `<style>` blocks and splits rules into inlinable and retained.
3. Inlines with the real cascade: specificity, then source order, with `!important` and the existing `style` attribute in their correct positions.
4. Rewrites the survivors into one `<style>` block.
5. Injects the `v:`/`o:` namespaces and the `[if mso]` block: `<o:PixelsPerInch>96</o:PixelsPerInch>` and the font rule that gives the Word engine Arial.
6. Drops authoring comments — keeping conditional comments and ESP directives.
7. Generates the plain-text alternative from the DOM.
8. Reports bytes against the clipping threshold.

### Flags worth knowing

| Flag | When |
|---|---|
| `--text FILE` | always — the plain-text part is a deliverable (§7) |
| `--text-only` | to read the text part before shipping it |
| `--no-inline` | to eyeball the resolved cascade before committing to inlining |
| `--minify` | when you are near the clipping threshold; saves roughly 5–10% |
| `--keep-comments` | when your ESP parses comment markers the default filter does not know |
| `--strict` | in CI: any warning fails |

---

## 3. Preheader text

The inbox list shows the sender, the subject, and then **the first text found in the body**. With no preheader, that is your logo's alt text, or "View in browser", on every client, for every reader. It is the second-most-read line of your email and it is free.

```html
<div data-preheader="1"
     style="display:none;font-size:1px;line-height:1px;max-height:0;max-width:0;
            opacity:0;overflow:hidden;mso-hide:all;">
  Order 41822 · $313.23 · Arriving Thursday
  &zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;
</div>
```

**Every declaration is doing work.** `display:none` alone is not enough — several clients ignore it in the inbox-preview extraction, and Outlook needs `mso-hide:all`. The combination of `display:none`, zero dimensions, `opacity:0` and `overflow:hidden` is what hides it in all of them.

**The `&zwnj;&nbsp;` padding** is the part that looks like superstition and is not. Clients pull a fixed *character count* into the preview. If your preheader is 40 characters and the client wants 100, it grabs the next 60 from your body — which is your logo alt text. Padding with zero-width non-joiners separated by non-breaking spaces fills the quota with nothing visible. (`&zwnj;` alone can be collapsed by some clients; alternating with `&nbsp;` is what makes it stick.)

**Write it as a second subject line, not a summary.** 35–100 characters. `build_email.py` excludes it from the plain-text part automatically; `lint_email.py` errors if it is missing and warns if it is under ~15 visible characters.

---

## 4. Testing: what you can check for free

Do all of this before you spend a cent on a rendering service. It catches most of what a service would find.

| Check | How |
|---|---|
| Unresolved tokens, unsupported CSS, contrast in light and dark, inline widths without `<style>`, alt text, size, structure | `python -m scripts.lint_email build/*.html` |
| Light, dark and no-`<style>` at 375px | `node scripts/render_email.mjs build/receipt.html` writes three PNGs and exits 1 when a mode is wider than the screen. Images are not fetched; their alt text stands in. |
| The plain-text part | `python -m scripts.build_email src.html --text-only` and **read it** |
| Images blocked | Open the built file in a browser with images disabled. The email must still make sense. |
| Real inbox rendering, free tier | Send to your own Gmail, Outlook.com and iCloud accounts. Three of the nine environments, at no cost. |
| **GANGA** | Add an Outlook.com or Yahoo account to the Gmail app on a phone. This is the single highest-value free test: `render_email.mjs` strips the `<style>`, but only the app shows the rest of what it does. |
| Delivered byte size | Gmail → **Show original**. This is the number the clipping threshold applies to, after your ESP's rewrites. |
| Dark mode | Toggle dark mode on the phone with the email open in Apple Mail, then in Gmail iOS. Two different behaviours, one minute. |
| Every link | Click every one from a real send. Merge tags that look fine in the template resolve to `https://example.com/orders/` with nothing after it. |
| Screen reader | VoiceOver in Apple Mail (`Cmd+F5`). If you hear "table, 4 rows" before any content, a `role="presentation"` is missing. |

### The browser preview lies

A built email in Chrome is a useful proofreading surface and nothing more. It has a cascade, `max-width`, web fonts and no sanitiser. It will never show you the Word engine or a clip, and GANGA only as far as `render_email.mjs`'s no-`<style>` mode goes.

---

## 5. Testing: what needs a rendering service

Litmus, Email on Acid and Testi@ run your HTML on real clients and screenshot the result. They are the only way to see classic Outlook without a Windows machine. They cost money, so spend it in priority order.

**If you can test five combinations,** test these — chosen for maximum *distinct rendering engines* per test, not for market share:

| # | Combination | Uniquely catches |
|---|---|---|
| 1 | **Classic Outlook for Microsoft 365, Windows, at 125% display scaling** | The Word engine *and* the 120-DPI bug together. The single highest-yield test that exists. (Outlook 2019 left support in October 2025, and 2021 leaves on 2026-10-13; classic Outlook for Microsoft 365 is the same Word engine, supported until at least 2029.) |
| 2 | **Gmail app on Android with a non-Google account (GANGA)** | The stripped `<style>` block. Nothing else shows you this. |
| 3 | **Apple Mail on iOS, dark mode** | Your `prefers-color-scheme` block, plus the largest mobile share. |
| 4 | **Gmail web, desktop** | The sanitiser, the clip, and the largest webmail share. |
| 5 | **Outlook.com web, dark mode** | Partial colour inversion and the `[data-ogsc]` rewrite. |

**Numbers 6 through 10, in order:** new Outlook for Windows (Chromium — the future, and confirms your conditional comments are inert there); Gmail app on iOS in dark mode (full forced inversion, the worst case); Apple Mail on macOS; Outlook for Mac; Yahoo web.

**What to buy.** A one-month subscription around a template rebuild, not a standing one. Templates change rarely; clients change slowly. Test the template when you build it, then spot-check each campaign with free sends.

---

## 6. Deliverability that lives in the HTML

Authentication (SPF, DKIM, DMARC), list hygiene and sending reputation matter far more than markup. But four things in the HTML itself move the needle, and one of them is commonly got backwards.

**1. Text-to-image ratio.** An email that is one large image with no text is a classic spam signature, and it is *also* completely invisible to every reader with images blocked. Aim for a substantial majority of your message as real text. There is no magic ratio; the test is "does this email still work with images off?"

**2. Markup that reads as spam.** Hidden text beyond the preheader, `<form>`, `<script>`, `<iframe>`, base64 images, link text that does not match its href, and URL shorteners in place of your own domain. `lint_email.py` errors on the structural ones.

**3. Link domains.** Every link should point at a domain you control, or at your ESP's tracking domain **branded to your own** (`links.yourbrand.com`, not `sendgrid.net`). A message whose links all point at a shared tracking domain inherits that domain's reputation, including everyone else's.

**4. The plain-text part.** Its absence is a mild spam signal on its own, and a bad one — auto-generated, tag-stripped mush — is worse. See §7.

**One-click unsubscribe.** Bulk senders to Gmail and Yahoo are expected to support `List-Unsubscribe` and `List-Unsubscribe-Post` headers. Those are ESP configuration, not HTML, but your body link must still exist and must still work: a reader who cannot find unsubscribe presses "report spam", which costs far more than the unsubscribe would have.

---

## 7. The plain-text part

> **The plain-text alternative is a deliverable, not an afterthought.** Somebody reads it.

Who: readers on text-only clients and some accessibility setups, anyone whose gateway strips HTML, several smartwatch and in-car previews, and every spam filter that compares the two parts and treats a mismatch as a signal.

**What a bad one looks like** — and it is the default from most tooling: tags stripped by regex, navigation and alt text interleaved with body copy, raw URLs mid-sentence, no structure. It is worse than no text part, because it is evidence you are automating without looking.

`build_email.py` generates it from the DOM, not from a regex over the HTML, which is what lets it: skip the preheader, skip `aria-hidden` spacers, underline headings, keep list bullets, put each table row on one line, and attach each link's href after its label.

```
What a ten-year guarantee actually costs
========================================

We repaired 1,412 jackets last year. That is up from 890 the year
before, which sounds like a quality problem and is actually the
opposite …

Read the full breakdown <https://example.com/letters/47>
```

**Then read it.** `--text-only` prints it to stdout. Check: does the first line make sense on its own; is the call to action present with its URL; is the unsubscribe there; are there stray `&mdash;` or merge tags that did not resolve. Thirty seconds, every send.

---

## 8. ESP handoff

Every ESP transforms your HTML on the way out. Knowing what each does is the difference between a template that survives the handoff and one that gets rebuilt in a drag-and-drop editor by someone who does not know why the ghost tables are there.

### What they all do

- **Rewrite every link** for click tracking. This grows the HTML — a long URL with tracking parameters can be several hundred bytes — which is why you leave headroom under the clipping threshold.
- **Append a tracking pixel** before `</body>`.
- **Expand merge tags**, which changes byte count in ways your template cannot predict. A `{{first_name}}` that is usually 5 characters is 34 for somebody.
- **Inject an unsubscribe footer** if your template lacks one. It will not match your design.

### Per-platform

| Platform | Merge tag | Conditional | Worth knowing |
|---|---|---|---|
| **Klaviyo** | `{{ first_name }}` / `{{ person.first_name }}` | `{% if %}…{% endif %}` (Django-ish) | Preserves custom HTML well. Uses `{% raw %}` blocks if your content contains literal braces. Drag-and-drop and HTML templates are separate object types — pick HTML and stay there. |
| **Mailchimp** | `*\|FNAME\|*` | `*\|IF:…\|* … *\|END:IF\|*` | Editable regions are `mc:edit="name"` attributes on containers. Without them the template is not editable in their UI, which is usually what you want. Mailchimp's own inliner can be left on or off; leave it **off** — you already inlined. |
| **Postmark** | `{{name}}` (Mustachio) | `{{#items}}…{{/items}}` sections and `{{^name}}` inverted sections; no `{{#if}}` | Transactional-focused, minimal transformation, keeps your HTML close to intact. Has a built-in inliner you should disable. |
| **SendGrid** | `{{name}}` (Handlebars) or `-name-` (legacy substitution tags) | `{{#if}}` | Two template systems (Dynamic vs Legacy) with different syntax; confirm which one the account is on before writing a tag. |
| **Customer.io** | `{{customer.first_name}}` (Liquid) | `{% if %}` | Liquid throughout, including in subject lines. |
| **Braze** | `{{${first_name}}}` (Liquid + Connected Content) | `{% if %}` | The `${}` wrapper around attribute names is easy to get wrong. |

### Keeping a template portable

1. **Author with one neutral syntax** — `{{token_name}}` — and translate at handoff with a small substitution map. Do not author against a platform.
2. **Turn the ESP's inliner off.** Two inliners produce duplicated and contradictory declarations, and theirs does not know about your retained media queries.
3. **Turn the ESP's "responsive" or "mobile optimisation" toggle off.** It rewrites your layout and will discard the ghost tables.
4. **Never paste built HTML into a WYSIWYG editor.** Every one of them reformats on save. Use the platform's raw-HTML or code-template mode, or its API.
5. **Keep the source template in git; the built file is an artefact.** If someone edits the sent HTML directly, that change is gone at the next build. Enforce it with `build/` in `.gitignore`.
6. **Re-lint after the ESP.** Send a test, open **Show original**, save it, and run `lint_email.py` over *that*. It is the only way to see the real delivered size and the rewritten links.

---

## 9. The pre-send checklist

Run it every time. It is short because the compiler and the linter already did the mechanical parts.

**Build**

- [ ] `make all && python -m scripts.lint_email build/*.html` exits 0
- [ ] Byte size under 90 KB, measured on a **real test send** via Show original
- [ ] The plain-text part read end to end, not skimmed

**Content**

- [ ] Subject line and preheader written together, and they do not repeat each other
- [ ] `<title>` matches the subject line
- [ ] Every merge tag has a tested fallback — send yourself one with an empty profile
- [ ] Every link clicked from a real send, including the unsubscribe
- [ ] Physical postal address present (CAN-SPAM, commercial email)
- [ ] Legal/expiry copy accurate and dated

**Rendering**

- [ ] Images blocked: still comprehensible, alt text carries the message
- [ ] Phone, portrait: no horizontal scroll, tap targets ≥ 44px
- [ ] Dark mode on a phone: nothing unreadable, logo still visible
- [ ] Classic Outlook: button is a filled rectangle, columns are side by side, no giant text
- [ ] GANGA: layout stacks correctly with the `<style>` block gone

**Send**

- [ ] Sender name and reply-to correct, and reply-to is a monitored inbox
- [ ] Segment and suppression list confirmed — read the count out loud
- [ ] Seed list receives it first
- [ ] Someone is available for the hour after send

---

Related: `references/email-client-matrix.md` (what breaks where), `references/email-architecture.md` (how to build it), `scripts/build_email.py`, `scripts/lint_email.py`, `scripts/render_email.mjs`.

---

## 10. The requests you will actually get, and the answer

| They say | What is happening | Do |
|---|---|---|
| "It looks broken in Outlook" | The Word engine. Almost always `max-width` with no ghost table, a `div` layout, or `margin`. | `email-client-matrix.md` §3, then rebuild the skeleton from `email-architecture.md` §1 |
| "The text is huge in Outlook but only on my colleague's machine" | The 120-DPI bug at 125% display scaling. | the `<o:PixelsPerInch>` block — the compiler adds it |
| "The button lost its rounded corners" | `border-radius` in the Word engine. | VML `roundrect`, `email-architecture.md` §6 |
| "There's a gap under every image" | Images are not `display:block`; the baseline descender space is showing. | `display:block`, always |
| "The two columns didn't stack on my phone" | A media query that got stripped — likely GANGA. | fluid-hybrid, `email-architecture.md` §7 |
| "Gmail cut my email off" | 102,400 bytes. | `--minify`, drop base64 images, measure via Show original |
| "My media queries just vanished" | The 16,384-byte `<style>` ceiling: Gmail removes every `<style>` element that crosses it, and every one after. | inline more; only queries and pseudo-classes need to stay |
| "It's unreadable in dark mode" | Forced or partial inversion. | `email-client-matrix.md` §8 — and be honest about what cannot be fixed |
| "Can we use our brand font?" | No, not as the design. | build on the websafe stack, layer `@font-face` as decoration |
| "Can it have a carousel / accordion / countdown?" | Interactive email. Works in Apple Mail, nowhere that matters. | a static frame that links to a page |
| "Just make it one big image" | Invisible with images blocked, and a spam signature. | `email-workflow.md` §6 |
