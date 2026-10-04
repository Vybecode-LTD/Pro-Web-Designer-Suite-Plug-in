# Color System

How this studio picks, builds, binds and audits color. The ramps live in Tier 1 of
`assets/starter/styles/tokens.css`; the roles components actually read live in Tier 2.
Generate every ramp with `scripts/generate_color_ramp.py` — it implements the exact
curves described here and prints the contrast matrix, so no step of this document is
a matter of taste you have to eyeball.

Law 1 governs this file: **no component ever contains a color literal.** A hex code in
a component is a bug report waiting to be filed.

---

## 1. Why OKLCH

Every color space we could author in answers one question: *if I change this number,
what happens to what the eye sees?* Only OKLCH answers it honestly.

| Space | Change L / lightness by 10% | Change hue, keep L | Verdict |
|---|---|---|---|
| `hsl()` | `hsl(60 100% 50%)` (yellow) and `hsl(240 100% 50%)` (blue) are both "50% light". They are not remotely the same brightness. | Lightness lurches | Unusable for ramps |
| `rgb()` / hex | No lightness channel at all | No hue channel at all | Unusable for reasoning |
| `lab()` / `lch()` | Perceptually uniform, but blues shift hue as they lighten (the Lab blue-purple problem) | Visible purple drift | Nearly good |
| `oklch()` | Uniform: L 0.50 → 0.60 is the same perceived step at every hue | Hue holds | **Use this** |

### The L / C / H mental model

- **L (0–1, written 0–100%)** — perceived lightness. Not luminance, not Photoshop's
  "value". L 0.50 is the midpoint your eye calls middle gray. Because it is uniform,
  `--accent-500` (L 0.645) and `--neutral-500` (L 0.580) read as related weights, and
  swapping a brand's hue never breaks the ramp's rhythm. That one property is why the
  ladder survives a rebrand.
- **C (0 → ~0.322 in sRGB)** — chroma: colorfulness in absolute terms. Unlike HSL
  saturation it is *not* normalized per hue, which is the point — C 0.15 is the same
  colorfulness at hue 40 and hue 260. It is unbounded in principle, so a given (L, C, H)
  can simply not exist in sRGB; see gamut mapping below.
- **H (0–360°)** — hue angle. Landmarks: **25** red, **40** ember, **70** amber,
  **110** yellow, **145** green, **180** teal, **220** cyan-blue, **260** blue,
  **295** violet, **330** magenta, **350** pink.

Three rules follow immediately, and they are the whole reason we author here:

1. **To build a ramp, vary L and leave H alone.** In HSL you would vary L *and* fight
   the hue shift; here the ramp stays one pigment.
2. **To rebrand, change H and leave L alone.** The contrast matrix barely moves.
3. **To fix a "too loud" brand, lower C.** Nothing else changes.

### Browser support and the fallback

`oklch()` is supported in every evergreen browser (Chrome/Edge 111+, Safari 15.4+,
Firefox 113+) — roughly 2023 onward. Our floor is "last two versions", so we author
OKLCH directly. Two things to keep honest:

- **Wide-gamut headroom.** On a P3 display `oklch()` addresses colors sRGB hex cannot
  express, so the same token gets richer on better hardware with no second palette. Our
  generated ramps are gamut-mapped *to sRGB*, so they are safe everywhere and do not
  exploit that headroom — a deliberate trade for one palette instead of two.
- **If a project genuinely needs an older floor**, do not hand-maintain a second set of
  hex values. Fall back at the *primitive* tier only, where the duplication is eleven
  lines instead of every component:

```css
@layer tokens {
  :root {
    --accent-500: #e16037;                    /* sRGB fallback, from the generator */
  }
  @supports (color: oklch(0% 0 0)) {
    :root {
      --accent-500: oklch(64.5% 0.170 38);    /* real value */
    }
  }
}
```

Tier 2 and every component are untouched. That is Law 1 earning its keep.

---

## 2. Building a ramp that reads as designed

A ramp is three curves, not one interpolation. `scripts/generate_color_ramp.py` holds
them as `L_CURVE`, `C_CURVE` and `H_DRIFT`; they are reproduced here so you can reason
about a ramp without reading Python.

### 2.1 The lightness curve

```
step:   50     100    200    300    400    500    600    700    800    900    950
L:      0.970  0.935  0.880  0.805  0.720  0.645  0.565  0.470  0.380  0.300  0.210
Δ:        -.035  -.055  -.075  -.085  -.075  -.080  -.095  -.090  -.080  -.090
```

It is deliberately **not** linear. Two perceptual facts drive the shape:

- **The top is compressed (Δ 0.035 from 50→100).** Near white, small lightness
  differences are highly visible — tints at L 0.97 and L 0.90 read as two unrelated
  colors, not two steps of one. Tints must crowd or the light end breaks into stripes.
- **The middle is stretched (Δ 0.085–0.095 through 300→800).** This band does the real
  work: fills, text, borders, hover. Steps here must be *unambiguously* different,
  because a designer choosing between 600 and 700 needs to see why.
- **The bottom stops at 0.210, not 0.** Below roughly L 0.15 hue and chroma stop being
  readable — every dark color converges on the same hole. A near-black `950` wastes a
  step; true near-blacks belong to the neutral ramp (`--neutral-1000`, L 0.080), where
  they are structural rather than chromatic.

The neutral ramp uses its own `NEUTRAL_L` curve, lower from 400 down, because neutrals
must reach further into the dark to build dark-mode surfaces.

### 2.2 The chroma curve

Chroma is stored as a **fraction of the seed's chroma**, peaking at 500:

```
step:   50     100    200    300    400    500    600    700    800    900    950
C×:     0.106  0.223  0.415  0.628  0.840  1.000  0.936  0.787  0.628  0.479  0.330
```

Holding chroma constant across a ramp is the single most common mistake, and it fails at
both ends:

- **At 50–100, constant chroma turns neon.** At L 0.97 there is almost no room between
  the color and white, so any real chroma reads as a screaming fluorescent wash — the
  classic "highlighter yellow alert banner". Tints want ~10–22% of peak chroma. They
  should whisper the hue, not state it.
- **At 900–950, constant chroma turns muddy.** Deep colors with high chroma sit at the
  edge of the gamut where sRGB cannot render them cleanly; they clip, lose hue
  definition and read as dirty brown or bruised navy. Shades want ~33–48% of peak.
- **Peak belongs at 500, slightly wide.** 400 and 600 stay near peak (0.84 / 0.94) so the
  brand has three usable "loud" steps — fill, hover, dark-mode text — rather than one.

### 2.3 Hue drift

Each step rotates a few degrees along the shortest arc toward an anchor: steps lighter
than 500 rotate toward the **cool anchor (250°)**, darker steps toward the **warm anchor
(45°)**.

```
step:   50   100  200  300  400  500  600  700  800  900  950
|Δh|:   4.0  3.2  2.4  1.6  0.8  0.0  1.0  2.0  3.0  4.0  5.0
        <-------- toward 250° --------|--------- toward 45° -------->
```

Why bother, when the swing is under 10°? Because a ramp with a fixed hue is a
mathematical object and the eye knows it. Real pigment never holds one hue across a value
range: it takes the color of the light in its highlights and of the ambient fill in its
shadows. This drift is a cool key with a warm bounce — the difference between "generated"
and "chosen".

One consequence of taking the *shortest* arc: a blue seed (H 263) gets cyan-leaning tints
(→ 259) and violet-leaning shades (→ 267), exactly how good blue ramps behave; an ember
seed (H 38) gets red-pink tints (→ 34) and amber shades (→ 43). If a hue looks wrong
under the rule, pass `--hue-shift 0` and say why in the ramp's comment — never hand-edit
the output.

### 2.4 Gamut mapping

An (L, C, H) triple can name a color sRGB cannot produce. The wrong fix is clamping RGB
channels: that shifts **both** lightness and hue, and a step that silently got lighter no
longer matches its neighbours or its audited ratio. The right fix, and what the generator
does: **binary-search chroma downward, holding L and H exactly**, until the color is in
gamut — you lose colorfulness and keep the ramp's structure.

Expect heavy clipping at the light end of warm hues; sRGB has no saturated near-white
orange, so a −33% clip at step 50 is normal and invisible. Clipping above ~10% in the
**400–700** band is the real warning — the seed is more chromatic than the hue can hold
and the mid-ramp will read flat. Lower the seed's C and regenerate. The script flags
exactly this case and stays quiet about the other.

---

## 3. 60 / 30 / 10, expressed in tokens

The classic ratio is usually taught as a mood-board exercise. In a token system it is a
measurable constraint on surface area:

| Share | Role | Tokens | What it is |
|---|---|---|---|
| ~60% | Dominant | `--bg-canvas` | The page. Near-neutral. The reader should never notice it. |
| ~30% | Secondary | `--bg-surface`, `--bg-sunken`, `--bg-raised`, `--border-*` | Cards, wells, dividers — the structure. Still neutral, separated from canvas by L, not by hue. |
| ~10% | Accent | `--bg-accent`, `--fg-accent`, `--fg-link`, `--border-focus` | Every chromatic pixel on the page, combined. |

Two working rules fall out:

- **The 10% is a budget, not a target.** On a typical page it means one primary button,
  the links, the focus ring and one chart series. If a screen has three accent-filled
  buttons, two of them are lying about their importance — demote them to a token pairing
  of `--bg-surface` + `--border-default`.
- **Foreground text is not part of the 30%.** `--fg-default` is near-black by area but
  reads as figure, not ground. Count backgrounds, borders and fills.

The fastest way to check a design: screenshot it, desaturate it, and confirm the layout
still has hierarchy. If it collapses, the design was carried by hue and will fail
section 8.

---

## 4. Choosing a palette from a brief

A decision procedure, in order. Do not skip to step 3 because the client said "blue".

**Step 1 — extract the adjectives.** Three at most, from the brief's own words. If the
brief says "we want to feel like Stripe", the adjectives are *technical, premium, calm* —
translate the reference into attributes before you translate attributes into numbers.

**Step 2 — map adjectives to a hue family.** Use the table. Where adjectives conflict
(*energetic* + *clinical*), the hue comes from the **dominant** adjective and the
**chroma budget from the restraining one**. That is how "technical but warm" resolves:
warm hue, technical (lower) chroma.

**Step 3 — set the chroma budget at step 500.** This is the single number that decides
whether the brand reads as premium or as a discount banner. It is almost always lower
than instinct suggests.

**Step 4 — set neutral temperature** (section 5), matched to the accent's hue.

**Step 5 — generate, audit, and check the failure modes** — sections 7 and 8, before a
single component is written.

| Adjective | Hue range (OKLCH °) | Chroma at 500 | Neutral hue / chroma | Notes |
|---|---|---|---|---|
| Trustworthy | 240–265 (blue) | 0.12–0.16 | 250–265 / 0.003–0.005 | The default for finance, health, gov. Boring is the feature. |
| Premium | any; hue matters less than restraint | **0.07–0.12** | matched hue / 0.004–0.006 | Premium is *low chroma + wide L range*. High chroma always reads cheap. |
| Energetic | 25–60 (red-orange) | 0.18–0.22 | 50–70 / 0.006–0.008 | Needs a disciplined 10% budget or it becomes exhausting. |
| Clinical | 195–225 (cyan-blue) | 0.08–0.12 | 215–230 / 0.003–0.004 | Cool neutral is mandatory; a warm gray reads unhygienic here. |
| Warm | 50–85 (amber) | 0.14–0.18 | 60–80 / 0.006–0.010 | The one family where a visibly warm neutral is the point. |
| Technical | 255–290 (blue-violet) | 0.13–0.17 | 265–280 / 0.004–0.005 | Violet-leaning blue reads as "engineered"; pure 260 reads as "enterprise". |
| Editorial | 15–35 (ink red) or accent-less | 0.10–0.15 | 40–60 / 0.005–0.008 | Often the strongest move is *no* accent: near-black type, one red rule. |
| Playful | 330–355 (pink) or 140–160 (green) | 0.19–0.24 | matched / 0.006 | Only family where a second accent hue is defensible — see section 11. |
| Luxurious | 85–100 (gold) or 290–310 (violet) | 0.06–0.11 | matched / 0.005–0.007 | Luxury is dark canvas + tiny chroma + generous space, not gold everywhere. |
| Calm | 150–185 (sage-teal) | 0.06–0.10 | 160–180 / 0.003–0.005 | Keep 500 under 0.10 or "calm" becomes "minty". |

**Chroma budget, restated as a rule of thumb:** 0.06–0.11 reads considered; 0.12–0.17
reads confident; 0.18–0.23 reads loud; above 0.24 reads like a sale. There is no hue at
which 0.28 reads expensive.

---

## 5. Neutral temperature

**Pure gray is the tell of an undesigned interface.** `oklch(58% 0 0)` is a color no
physical material produces: every real surface reflects something. On a screen, pure
neutrals also sit dead against the display's slight warmth and read as flat, plastic,
cheap.

The fix is small and non-negotiable: **give the neutral 0.003–0.010 chroma at the accent's
hue.**

| Chroma | Reads as |
|---|---|
| 0.000 | Cheap. Screen-gray. Default-stylesheet energy. |
| 0.003–0.005 | Correct for tints and near-whites. Felt, not seen. |
| 0.006–0.010 | Correct for mid and dark steps, where more chroma is needed to register at all. |
| 0.012+ | No longer neutral. It now competes with the accent and muddies every surface stacked on it. |

Note the curve inside that range: the generator's `NEUTRAL_C` runs 0.003 → 0.009 → 0.004
from 50 to 1000, peaking mid-ramp. The reason is the same as for accents — near white and
near black, chroma has no room to be subtle, so it must be reduced.

**Match the neutral's hue to the accent's** (or to within ~30° of it). This is what makes
a palette cohere: the grays are quietly the same pigment family as the brand, so a card
sitting on canvas next to a primary button doesn't read as two unrelated systems. The
starter tokens use hue 75 neutrals under a hue 42 accent — close enough to relate, far
enough to stay clearly neutral.

Generate it, don't guess it:

```bash
python -m scripts.generate_color_ramp 'oklch(58% 0.009 70)' --name neutral --neutral
```

---

## 6. Semantic role mapping

Tier 1 ramps are raw material. This table is the contract that turns them into a system.
**Components read only the left-hand names.** It is generated from the starter's `tokens.css` by
`scripts/check_roles.py --table`, and a test keeps the two identical, so it cannot drift from the
tokens again.

<!-- check_roles:table -->
| Tier-2 role | Light | Dark | On the canvas, light / dark |
|---|---|---|---|
| `--bg-canvas` | `--neutral-50` | `--neutral-1000` |  |
| `--bg-surface` | `--neutral-0` | `--neutral-950` |  |
| `--bg-raised` | `--neutral-0` | `--neutral-900` |  |
| `--bg-sunken` | `--neutral-100` | `--neutral-1000` |  |
| `--bg-inverse` | `--neutral-900` | `--neutral-100` |  |
| `--fg-default` | `--neutral-900` | `--neutral-100` | 17.37:1 / 18.50:1 |
| `--fg-strong` | `--neutral-950` | `--neutral-50` | 19.10:1 / 19.73:1 |
| `--fg-muted` | `--neutral-600` | `--neutral-300` | 6.35:1 / 13.80:1 |
| `--fg-subtle` | `--neutral-500` | `--neutral-400` | 4.91:1 / 8.22:1 |
| `--fg-disabled` | `--neutral-400` | `--neutral-700` | 2.40:1 / 2.12:1 |
| `--fg-accent` | `--accent-700` | `--accent-400` | 6.92:1 / 7.91:1 |
| `--fg-link` | `--accent-700` | `--accent-400` | 6.92:1 / 7.91:1 |
| `--fg-on-accent` | `--neutral-0` | `--neutral-1000` |  |
| `--fg-on-inverse` | `--neutral-50` | `--neutral-900` |  |
| `--border-subtle` | `--neutral-200` | `--neutral-900` | 1.20:1 / 1.14:1 |
| `--border-default` | `--neutral-300` | `--neutral-800` | 1.43:1 / 1.42:1 |
| `--border-strong` | `--neutral-500` | `--neutral-500` | 4.91:1 / 4.02:1 |
| `--border-focus` | `--accent-600` | `--accent-600` | 4.67:1 / 4.23:1 |
| `--bg-accent` | `--accent-600` | `--accent-500` |  |
| `--bg-accent-hover` | `--accent-700` | `--accent-400` |  |
| `--fg-danger` | `--danger-700` | `--danger-400` | 7.72:1 / 5.65:1 |
| `--bg-danger` | `--danger-500` | `--danger-500` |  |
<!-- /check_roles:table -->

Why each role maps where it does:

- `--bg-canvas` is never pure white in light: a `#fff` canvas under `#fff` cards leaves no room to separate them.
- In light the card (`--bg-surface`) is *lighter* than the canvas; in dark it is lighter too. See below.
- `--bg-raised`: dark mode gains elevation by lightening, not by shadowing.
- `--bg-sunken`: wells, inputs and code blocks recede by going *toward* the canvas extreme.
- `--bg-inverse` is a true flip, for tooltips and inverse bands.
- `--fg-disabled` is exempt from contrast minima (SC 1.4.3 excludes disabled controls), but only if it is genuinely non-interactive.
- `--fg-accent` and `--fg-link` are not the fill's step: accent text must be *darker* than 500 on light and *lighter* on dark.
- `--border-subtle` and `--border-default` are dividers, decorative and exempt from 3:1. `--border-strong` marks a control's boundary, and clears 3:1 on every surface.
- `--border-focus` must clear 3:1 against the surface it sits on; the canvas-coloured gap in the ring separates it from the component.
- `--bg-accent` is the fill, and its foreground, `--fg-on-accent`, is the thing that changes between themes.

### Dark mode is not an inversion

Flipping the ramp produces something that technically has contrast and looks wrong. Four
reasons, each with a concrete consequence:

1. **Elevation reverses physically, not numerically.** A surface closer to the viewer
   catches more light, so a card is *lighter* than its canvas in light mode — and *still
   lighter* in dark mode. Dark UI puts the darkest value at the very back and lightens
   everything as it comes forward. An inversion makes raised surfaces darker, which reads
   as a hole in the page. Hence `--bg-canvas: --neutral-1000`, `--bg-surface:
   --neutral-950`, `--bg-raised: --neutral-900`.
2. **Shadows stop working.** A black shadow on a near-black surface is invisible; a
   heavier one is a gray smear. Depth comes from the surface ladder above, plus
   optionally a 1px top hairline at `oklch(100% 0 0 / 0.06)` for a lit edge. (The starter
   keeps faint shadows at 0.30–0.44 alpha purely for contact; *separation* is still L.)
3. **Chroma must drop ~10–15%.** Chromatic sensitivity falls at low ambient adaptation,
   and saturated color on a dark field halates — edges bloom, fine type smears. Generate
   dark-specific steps with `--chroma-scale 0.85` if the brand runs hot.
4. **Accent lightness must rise.** `--accent-500` on `--neutral-1000` measures 5.84:1 —
   legal, but tiring to read. `--accent-400` measures 7.91:1 and is the correct dark
   `--fg-link`. Hence `--fg-accent` → 700 in light, 400 in dark: *the role is constant,
   the step is not.*

### The gate: `check_roles.py`

Run it on every change to `tokens.css`; the pre-commit hook does, once the script is vendored. It
resolves each role per theme (light, dark, and `.inverse` in both) and checks the pairs components
put together: every text role on every surface at 4.5:1, status text, labels on fills, text in an
inverse band on its parent theme's `--bg-inverse`, and control borders and the focus ring at 3:1.
The starter passes all of them. Two were fixed by hand before the tool existed, and they show what
it is for:

- **`--fg-subtle` is placeholder text**, which is real text under SC 1.4.3. On an evenly spaced
  ramp it fails. The ramp's 500 sits at L 53.5% instead, which gives 4.91:1 (--neutral-500 on
  --neutral-50) on the canvas and 4.60:1 (--neutral-500 on --neutral-100) on the sunken well, the
  worst light surface it lands on.
- **White on a mid-lightness accent fails at label size**: 3.56:1 (--neutral-0 on --accent-500).
  The light `--bg-accent` is therefore `--accent-600`, where white measures 4.92:1 (--neutral-0 on
  --accent-600). The dark theme keeps `--accent-500` and turns the label dark: 5.84:1
  (--neutral-1000 on --accent-500).

Both are ordinary outcomes of a mid-lightness palette. Catch them with the script, not in a VPAT.

---

## 7. WCAG 2.2 contrast

### The math

WCAG 2.x contrast is a ratio of **relative luminance**, computed on linearized sRGB:

```
For each channel c in {R, G, B}, given c_srgb in 0..1:
    c_lin = c_srgb / 12.92                      if c_srgb <= 0.04045
    c_lin = ((c_srgb + 0.055) / 1.055) ^ 2.4    otherwise

L = 0.2126 * R_lin + 0.7152 * G_lin + 0.0722 * B_lin

ratio = (L_lighter + 0.05) / (L_darker + 0.05)      → 1.0 .. 21.0
```

The `+ 0.05` is a flare constant modelling ambient light reflecting off the screen; it is
why the scale tops out at 21:1 rather than infinity. The weights are why yellow text is
so hard to place (green dominates luminance at 0.7152) and blue so easy to make dark
(blue contributes 0.0722 — a fully saturated blue is nearly as dark as black to this
formula).

Note what the formula does **not** include: chroma, hue, font weight, or size. This is
the source of every complaint about WCAG 2.x, and also why it is auditable.

### The thresholds, and exactly what they apply to

| Ratio | SC | Applies to |
|---|---|---|
| **4.5:1** | 1.4.3 Contrast (Minimum), AA | All text and images of text below 24px regular / 19px bold. Includes placeholders, help text, captions, disabled-looking-but-actually-active controls, and text in images. |
| **3:1** | 1.4.3, AA | Large text: ≥ 18pt (24px) regular, or ≥ 14pt (18.66px) bold. Round the bold size up to 19px in practice. |
| **3:1** | 1.4.11 Non-text Contrast, AA | (a) UI component boundaries required to identify the control — input borders, toggle tracks, checkbox outlines; (b) states that convey meaning — checked, selected, error; (c) graphics required to understand content — chart lines, icon-only buttons, required-field markers. Against *adjacent* colors. |
| **3:1** | 2.4.13 Focus Appearance (AAA in 2.2; this skill holds it as a floor) | The focus indicator's own pixels, between the focused and unfocused states, over an area at least as large as a 2px-thick perimeter of the control. Contrast against the adjacent colours is 1.4.11's requirement, the row above. Not being hidden by author content is 2.4.11 Focus Not Obscured (Minimum), the AA criterion. The starter's ring (`reset.css` §7) meets the geometry with a 2px outline in `--border-focus`, offset 2px, plus a 2px `--bg-canvas` gap ring, which is what makes it visible on *any* surface. |
| **7:1** | 1.4.6 Contrast (Enhanced), AAA | Body text, when the project targets AAA. |
| **4.5:1** | 1.4.6, AAA | Large text under AAA. |
| — | 1.4.3 exceptions | Pure decoration, inactive/disabled controls, logotypes. Do not stretch these; "it's decorative" is not a defense for a low-contrast icon that is the only affordance. |

Check any pair in one command:

```bash
python -m scripts.generate_color_ramp --check 'oklch(47.5% 0.009 75)' 'oklch(98.2% 0.003 75)'
# → 6.35:1 — PASS 4.5, PASS 3.0, FAIL 7.0 (AAA)
```

### APCA, honestly

APCA was proposed as WCAG 3's contrast method. The working group took it out of the WCAG 3 drafts in July 2023, and what replaces it is still undecided. It models what WCAG 2.x ignores: polarity (dark
text on light is easier than the reverse at the same ratio), font size and weight, and
spatial frequency. It yields an Lc value from about -108 to 106 — roughly Lc 75 for body
text, 60 for medium, 45 for large headings, 30 as a non-text floor. It is better
perceptual science, and it will tell you some WCAG-passing pairs are unreadable and some
WCAG-failing pairs are fine.

**Design with APCA's intuitions; ship against WCAG 2.x numbers.** WCAG 2.2 is what
procurement, VPATs, audits and lawsuits reference today; WCAG 3 is years from normative.
Where they disagree, 4.5:1 wins and you note the disagreement. Never tell a client a
pairing is fine because APCA likes it.

---

## 8. Color vision deficiency

About 1 in 12 men and 1 in 200 women. Three types matter:

| Type | Prevalence | Effect |
|---|---|---|
| Deuteranomaly / deuteranopia | ~6% of men | Red–green confusion. Reds and greens collapse toward yellow-brown. |
| Protanomaly / protanopia | ~2% of men | Red–green confusion, plus reds appear *darker* — a red error state can drop below its expected contrast. |
| Tritanomaly / tritanopia | ~0.01% | Blue–yellow confusion. Rare but brutal for blue/teal data viz. |

**The rule: hue is never the only carrier of meaning** (SC 1.4.1). A green "paid" pill
and a red "overdue" pill are the same pill to 6% of men.

Redundant encoding, in order of cost:

1. **Text.** "Paid" / "Overdue". Almost always the right answer and almost always skipped.
2. **Icon shape.** ✓ / ! / ×. Distinguishable at a glance and at small size.
3. **Lightness.** Because OKLCH separates L from H, you can guarantee two states differ
   in L by ≥ 0.20 — that difference survives every CVD type, since CVD affects hue
   discrimination, not lightness.
4. **Position, weight, pattern.** For charts: dash patterns and direct labels beat legends.

**Sanity-checking a palette** — three passes, in order:

- **Grayscale.** Desaturate the whole screen. Every state that meant something different
  must still look different. This single check catches most failures because it tests
  criterion 3 above.
- **Simulate.** Chrome DevTools → Rendering → *Emulate vision deficiencies* covers all
  three types plus blurred vision. Check the states, the charts, and the focus ring.
- **Check the ramp against itself.** Any two ramp steps used to distinguish two things
  must be ≥ 2 steps apart. Adjacent steps (600 vs 700) are a lightness whisper; they
  encode emphasis, never category.

Status hues get special care, and hue is not enough. Our `--success-500` (L 62%, H 152)
and `--danger-500` (L 58%, H 25) are 4 L-points apart, 1.39:1 (--success-500 on
--danger-500): under deuteranopia both read as a similar brown, and lightness does not
separate them. So a status is never carried by colour alone (SC 1.4.1): every one pairs
its colour with an icon and a word.

---

## 9. State colors as overlays

Do not create `--btn-primary-hover`, `--btn-ghost-hover`, `--card-hover`,
`--row-hover`. That list grows as the product does, every entry must be re-derived for
dark mode, and half of them will drift.

Compose states as **translucent overlays** that sit on top of whatever surface is there:

```css
@layer tokens {
  :root {
    --bg-hover:  oklch(0% 0 0 / 0.04);     /* darken, on light surfaces */
    --bg-active: oklch(0% 0 0 / 0.08);
  }
  [data-theme="dark"] {
    --bg-hover:  oklch(100% 0 0 / 0.06);   /* lighten, on dark surfaces */
    --bg-active: oklch(100% 0 0 / 0.10);
  }
}

@layer components {
  /* One rule. Works on canvas, on a card, in a sunken well, in both themes. */
  .button          { background: var(--bg-surface) linear-gradient(var(--bg-hover), var(--bg-hover));
                     background-size: 0 0; }
  .button:hover    { background-size: 100% 100%; }
  .button:active   { background-image: linear-gradient(var(--bg-active), var(--bg-active)); }
}
```

Why it scales: **N variants × M states collapses from N×M tokens to M tokens.** A new
variant ships with correct hover behaviour for free; a theme change re-points two values.
And because the overlay is a *color* with alpha rather than `opacity` on the element, the
text on top stays at full strength (section 11).

The one exception: **selected** is a semantic state, not a physical one, so it keeps its
own token (`--bg-selected`: `--accent-50` light, `--accent-950` dark). Selection means
something; hover is just a finger hovering.

---

## 10. Gradients that don't band

Banding comes from three causes, and all three have fixes.

```css
/* tokens.css, Tier 2: a brand gradient is a decision, so it is a role and
   the ramp steps stay out of component code. */
:root {
  /* 1. Interpolate in oklch, not sRGB. sRGB interpolation dips through a dead
        gray zone between distant hues; oklch keeps chroma up across the blend. */
  /* 2. Three or more stops. Two-stop gradients over a large area have no
        information to dither against. */
  /* 3. Keep the L delta modest across a huge field — a 0.6 L swing over 1200px
        is a lot of 8-bit steps to fake. */
  --bg-hero: linear-gradient(
    in oklch to bottom right,
    var(--accent-700) 0%,
    var(--accent-600) 38%,
    var(--accent-500) 72%,
    var(--accent-400) 100%
  );
}

.hero {
  background-image: var(--bg-hero);
  position: relative;
  isolation: isolate;
}

/* 4. Grain. 2-4% noise destroys banding by dithering the 8-bit steps, and adds
      the texture that makes a large color field look intentional. */
.hero::after {
  content: "";
  position: absolute;
  inset: 0;
  /* stylelint-disable-next-line declaration-property-value-allowed-list -- design-audit-ignore-next-line: L1 -- behind .hero's content, inside its own stacking context (isolation: isolate); not a page layer */
  z-index: -1;
  opacity: 0.03;                    /* 0.02-0.04. Above 0.05 it reads as dirt. */
  pointer-events: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}
```

`in oklch` shipped later than `oklch()` itself (Firefox 127 against 113, Safari 16.2
against 15.4), and an engine without it draws the sRGB default. For hue-spanning gradients add
`in oklch longer hue` or `shorter hue` explicitly — the default arc is rarely what you
meant when the endpoints are more than 180° apart.

Text on a gradient must be audited against the **worst** stop, not the average.

---

## 11. Anti-patterns

| Anti-pattern | Why it fails | Instead |
|---|---|---|
| `color: #000` for body text | Pure black on near-white is a 21:1 glare wall; it induces halation, especially for dyslexic and astigmatic readers, and it looks like unstyled HTML. | `--fg-default` (`--neutral-900`, 17.4:1). Plenty. |
| `background: #fff` for the page | Leaves nowhere to put a card. Every surface then needs a border to exist. | `--bg-canvas` = `--neutral-50`; cards get `--neutral-0` and separate by L. |
| White text on a saturated accent | A mid-L accent gives ~3.5:1 with white — fails body text. Chroma also makes white "vibrate" on the edge. | Darken the fill to 600, or use the accent's own 950 as the foreground. Both measured in section 6. |
| Two accent hues competing | The 10% budget now has two claimants; nothing is primary and every screen needs a debate. | One accent. Express variety through the ramp's L range, not a second hue. A second hue is justified only for *categorical* data or a genuinely dual-brand product. |
| `--danger-500` because the designer liked the red | Semantic colors are a shared vocabulary. Spending red on decoration means the next real error is invisible. | Use an accent step. Status ramps are reserved, always. |
| Hardcoded hex in a component | Law 1. It will not theme, will not respond to density, and will not appear in any audit. | A Tier-2 role. If no role fits, add one — Tier 2 is cheap. |
| `opacity: 0.5` on a whole element for a muted/disabled look | Opacity composites the *entire subtree*, so the text fades along with the background, contrast collapses unpredictably against whatever is behind, and nested opacity multiplies. | Translucent *colors*: `color: var(--fg-disabled); background: var(--bg-disabled)`. Section 9. |
| A ramp with constant chroma | Neon tints, muddy shades. Section 2.2. | Generate it. |
| Pure-gray neutrals | Section 5. | 0.003–0.010 chroma at the accent's hue. |
| Per-variant hover tokens | Combinatorial explosion, guaranteed drift. | Overlays. Section 9. |

---

## 12. Worked example — "premium audio software, technical but warm"

**Step 1 — adjectives.** *premium*, *technical*, *warm*.

**Step 2 — hue.** *Warm* is the dominant sensory word and the one the client will check
for, so the hue comes from the warm family (50–85). But *technical* pulls cooler and
*premium* resists yellow (yellow at high chroma reads as caution tape). Land at the
bottom of the warm band, on the orange side: **H 38** — ember, not amber. It reads as
heat and filament rather than as sunshine.

**Step 3 — chroma budget.** *Energetic* would justify 0.20. *Premium* caps it at ~0.12,
*technical* at ~0.17. The restraining adjectives win: **C 0.170 at step 500.** Confident,
not loud. (For comparison, the starter's default Ember sits at 0.188 — audibly more
aggressive, which is right for a marketing site and wrong for a tool people stare at for
six hours.)

**Step 4 — neutral.** Warm brief, so the neutral goes warm too, but a hue-38 neutral would
read pink at the light end. Rotate to **H 70** (amber-gray) at the standard 0.003–0.009
budget: close enough to relate to the accent, far enough to stay unmistakably neutral.
The canvas at `oklch(98.2% 0.003 70)` is `#faf9f7` — paper, not screen.

**Step 5 — generate and audit.**

```bash
python -m scripts.generate_color_ramp 'oklch(64.5% 0.17 38)' --name accent
python -m scripts.generate_color_ramp 'oklch(58% 0.009 70)' --name neutral --neutral
```

The resulting Tier-1 block, verbatim from the generator:

```css
@layer tokens {
  :root {
    /* Neutral — warm graphite at the accent's temperature. */
    --neutral-0:    oklch(100% 0 0);        /* #ffffff */
    --neutral-50:   oklch(98.2% 0.003 70);  /* #faf9f7 */
    --neutral-100:  oklch(96% 0.004 70);    /* #f3f1ef */
    --neutral-200:  oklch(92.2% 0.005 70);  /* #e7e5e2 */
    --neutral-300:  oklch(86.5% 0.006 70);  /* #d5d2ce */
    --neutral-400:  oklch(71.5% 0.008 70);  /* #a6a29e */
    --neutral-500:  oklch(58% 0.009 70);    /* #7e7975 */
    --neutral-600:  oklch(47.5% 0.009 70);  /* #605b57 */
    --neutral-700:  oklch(38.5% 0.008 70);  /* #47433f */
    --neutral-800:  oklch(28% 0.007 70);    /* #2b2825 */
    --neutral-900:  oklch(19.5% 0.006 70);  /* #171412 */
    --neutral-950:  oklch(13% 0.005 70);    /* #080706 */
    --neutral-1000: oklch(8% 0.004 70);     /* #020201 */

    /* Accent — Filament. H 38, peak C 0.170. */
    --accent-50:  oklch(97% 0.015 34);      /* #fff2ef */
    --accent-100: oklch(93.5% 0.033 34.8);  /* #ffe2db */
    --accent-200: oklch(88% 0.065 35.6);    /* #ffc9bb */
    --accent-300: oklch(80.5% 0.107 36.4);  /* #fca78f */
    --accent-400: oklch(72% 0.143 37.2);    /* #ef8161 */
    --accent-500: oklch(64.5% 0.170 38);    /* #e16037  brand anchor */
    --accent-600: oklch(56.5% 0.159 39);    /* #c04c21 */
    --accent-700: oklch(47% 0.134 40);      /* #963914 */
    --accent-800: oklch(38% 0.107 41);      /* #6f290b */
    --accent-900: oklch(30% 0.081 42);      /* #4e1c06 */
    --accent-950: oklch(21% 0.056 43);      /* #2d0e02 */
  }
}
```

**What the audit says, and what we do about it:**

| Pairing | Ratio | Decision |
|---|---|---|
| `--accent-700` on canvas | 6.88:1 | `--fg-link`, `--fg-accent`. Confirmed. |
| `--accent-600` on canvas | 4.64:1 | Legal for body but thin. Use for icons and borders, not paragraphs. |
| `--accent-500` on canvas | 3.36:1 | Fills and large type only. Never body text. |
| white on `--accent-500` | 3.54:1 | **Fails.** Buttons fill with `--accent-600` (white → 4.89:1) — or keep 500 and set `--fg-on-accent: var(--accent-950)` for 5.06:1. |
| `--accent-400` on `--neutral-1000` | 7.90:1 | Dark-mode `--fg-link`. AAA, comfortably. |
| `--accent-500` on `--neutral-1000` | 5.87:1 | Dark-mode fills and large type. Legible but not for long reading. |
| `--neutral-600` on canvas | 6.35:1 | `--fg-muted`. Confirmed. |
| `--neutral-500` on canvas | 4.07:1 | **Fails 4.5:1.** Non-text UI only — do not use for placeholders. |
| Clipping at 50 / 100 / 200 | −17% / −12% / −8% | Normal for a warm hue near white. The 400–700 band is untouched, so the brand band is intact. |

Two of eleven pairings needed a decision. That is a normal, healthy audit — and it
happened before a single component was written, which is the entire point.

---

## 13. Ship checklist

Law 9. Every one of these is mechanical; none is a judgement call.

- [ ] Every ramp came out of `scripts/generate_color_ramp.py`. No hand-tuned steps.
- [ ] Neutral chroma is 0.003–0.010, at a hue within ~30° of the accent.
- [ ] Exactly one accent hue, unless categorical data forced a second.
- [ ] Every Tier-2 color role is bound in **both** themes; no `.dark` selector exists in
      any component file.
- [ ] Dark mode lightens as surfaces come forward, and its accent steps differ from light.
- [ ] Contrast matrix run for both themes; body text ≥ 4.5:1, UI boundaries and the focus
      ring ≥ 3:1 against *both* neighbours.
- [ ] Grayscale screenshot still has hierarchy; every color-coded state has a second
      encoding.
- [ ] DevTools vision-deficiency emulation run across states, charts and focus.
- [ ] Zero color literals outside `tokens.css` — `grep -rnE "#[0-9a-fA-F]{3,8}\b" src/`
      returns nothing but SVG assets.
- [ ] No `opacity` used to mute an element that contains text.
