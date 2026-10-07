# Failure Catalog

The ways professional-looking work fails, by run-order layer. Four lines each: **Seen as** (the symptom a
reviewer experiences), **Mechanism** (what physically causes it), **Confirm** (prove it in under a minute),
**Fix** (the change that stops the class, not the instance). IDs are stable — cite them: `"ref":
"failure-catalog L4-1"`. A number missing from a layer (L4-2, L5-2, L6-3, L8-2, L8-3) is retired,
never reused.

## The ten that make work read as "almost professional"

Not the worst failures — the ones that cost most relative to how easy they are to fix, because each is
invisible alone and unmistakable in aggregate. A reviewer who can name none of them still walks away saying
"it feels a bit off".

| # | Failure | ID |
|---|---|---|
| 1 | Near-miss alignment — edges 1–3px apart | L4-1 |
| 2 | Three-ish shades of the same grey | L6-2 |
| 3 | A type scale with one orphan size | L5-1 |
| 4 | Generous desktop spacing that never adapted to mobile | L4-3 |
| 5 | A hero that is beautiful and says nothing | L1-2 |
| 6 | Inconsistent border radii across components | L5-3 |
| 7 | Motion that is all one duration | L8-1 |
| 8 | Empty states that were never designed | L7-1 |
| 9 | A dark mode that is an inversion rather than a redesign | L6-5 |
| 10 | Stock imagery at odds with the type voice | L2-2 |

---

## Layer 1 — Premise

### L1-1 · The right page for the wrong problem
**Seen as.** Competent work nobody can argue with and nobody wants.
**Mechanism.** The brief named an outcome ("fewer support tickets") and the design answered a proxy ("a
better help page"); everything after is internally consistent, which is why it survives review — consistency
is not correctness.
**Confirm.** Write the brief's outcome and the page's job on one line each; the second must entail the
first.
**Fix.** Restate the problem in the deliverable, above the design.

### L1-2 · A hero that is beautiful and says nothing
**Seen as.** A gorgeous first screen that leaves you with no idea what the product does.
**Mechanism.** The headline was written to fit the composition, and abstractions typeset beautifully —
short, no awkward proper nouns — so the copy that survives the layout is the copy that says least.
**Confirm.** Cover the logo and imagery: could a competitor ship this hero unchanged? Read the H1 aloud and
ask someone what the company sells.
**Fix.** Write the claim first and design to it, setting type to the real sentence including its longest
word. A layout that only works with vague copy *is* the finding.

### L1-3 · Designed for the demo, not the data
**Seen as.** Beautiful with six items; broken with six hundred, or with one.
**Mechanism.** Composition was tuned against placeholder content of convenient length and count, so real
outliers meet a layout that has no rule for them.
**Confirm.** Render with 0, 1 and 200 items; a 60-character name; a 7-figure number.
**Fix.** Put content constraints in the system: a stated truncation strategy, a `minmax()` grid, a designed
zero state, a documented maximum.

---

## Layer 2 — First impression

### L2-1 · It reads as a category before it reads as a thing
**Seen as.** "That looks like a SaaS landing page" — and nothing more specific.
**Mechanism.** Every distinguishing decision came from the same reference set as everyone else's, so the
work is competent *because* it is average.
**Confirm.** Five-second test on someone new; if they remember the layout rather than the content, nothing
landed.
**Fix.** Be deliberately unusual on exactly one axis — type, color, rhythm or photography — and conventional
on the rest. One axis reads as confident; four read as chaotic.

### L2-2 · Stock imagery at odds with the type voice
**Seen as.** Precise, restrained typography carrying warm, grinning, soft-lit stock photos; something is
insincere and nobody can point at it.
**Mechanism.** Type and image are both voice, usually chosen by different people against different
references, and the reader perceives the mismatch as the brand not knowing itself — which is read as
dishonesty, not as an art-direction slip.
**Confirm.** Three adjectives for the type, three for the imagery; non-overlapping lists are the finding. Or
delete the images — if the page improves, they were fighting it.
**Fix.** Image direction belongs in the design system beside the type roles: subject, crop, lighting, color
temperature, and what is banned.

### L2-3 · Everything the same weight at squint
**Seen as.** A pleasant page with no entry point.
**Mechanism.** Emphasis was applied evenly — every section got a heading, a card and an icon — so no object
is strongest and the eye defaults to reading order, which you did not design.
**Confirm.** Blur to ~8px; fewer than two dominant blocks is the finding.
**Fix.** The page skeleton declares one dominant block per screenful. Emphasis is a budget, and a primitive
that treats every section identically spends it flat.

---

## Layer 3 — Hierarchy

### L3-1 · Two primary actions
**Seen as.** Hesitation at the moment the page had free attention.
**Mechanism.** Two elements with the same fill, size and weight make two equal claims, so the eye compares
instead of acting — emphasis works by exclusion, and the second primary removes the first one's advantage
rather than adding a path.
**Confirm.** Squint; two objects surviving at equal weight means no primary.
**Fix.** Three real button tiers and a documented one-primary rule. Without a credible secondary, every
"make this stand out" becomes another primary.

### L3-2 · A size step below 1.2×
**Seen as.** Headings that do not feel like headings.
**Mechanism.** Below roughly 1.2× a size difference reads as variation, not rank, so the heading is
technically larger and functionally invisible and the reader falls back to reading everything.
**Confirm.** Measure and divide: 18 over 16 is 1.125 — that is the bug.
**Fix.** Pick the ratio from the archetype (dense UI 1.125–1.2, editorial 1.25–1.333) and separate roles
that must read as different ranks by more than one step. Rank is a role decision.

### L3-3 · The semantic outline is not the visual one
**Seen as.** Reads fine, navigates badly, screen-reads as nonsense.
**Mechanism.** Headings were chosen by size rather than rank — an `h4` because 20px looked right, an `h2`
skipped — so the two hierarchies diverge and only one is available to assistive technology and to search.
**Confirm.** Read the `h1`–`h6` sequence alone; it should be the page's argument.
**Fix.** Level is semantic and appearance comes from a `--type-*` role applied independently; a component
offering a heading `size` must also take a `level`.

---

## Layer 4 — Structure and rhythm

### L4-1 · Near-miss alignment
**Seen as.** The page looks hand-assembled rather than composed, and nobody can say why.
**Mechanism.** Two edges 1–3px apart: below ~4px the offset is too small to read as intentional and too
large for the eye to accept as a line, so it registers as imprecision — the exact perception separating
"almost professional" from "professional".
**Confirm.** Run a ruler down the column's left edges; grep for near-duplicate insets (`22px` beside
`24px`).
**Fix.** Page inset is one `--gutter-page` role read by the page container and never set by sections.
Alignment inherited from a shared parent cannot drift.

### L4-3 · Generous desktop spacing that never adapted to mobile
**Seen as.** On a phone, endless scrolling through air — sparse and slow rather than calm.
**Mechanism.** 96–128px of section padding was chosen against a 1440px canvas where it is 7% of the width;
at 390px the same value is a quarter of the viewport *height*, so each boundary costs a third of a screen
and the rhythm collapses where scroll is most expensive.
**Confirm.** Open at 390px and count screenfuls between the first and second real content.
**Fix.** Fluid roles — `--space-section`, clamped between the 380px and 1440px anchors — so rhythm scales
with the viewport instead of being re-picked per breakpoint.

### L4-4 · No section rhythm
**Seen as.** One long undifferentiated column, however good each section is alone.
**Mechanism.** Section separation was picked locally, so the page has no beat and the reader gets no sense
of progress or stopping points — visible as a scroll-depth cliff, not a visual complaint.
**Confirm.** Shrink to 25% and scroll, looking for a repeating beat; more than two distinct top-level
separation values is the finding.
**Fix.** Three rhythm roles — `--space-section`, `--space-subsection`, `--space-block` — and nothing between
them.

## Layer 5 — Craft

### L5-1 · A type scale with one orphan size
**Seen as.** Nearly harmonious type with one element that sits oddly.
**Mechanism.** Every size belongs to a ratio except one — 19px among 14/16/32, usually introduced to fix a
single wrapping problem — and sizes on a scale look chosen where a size off it looks nudged until it fit.
**Confirm.** List every distinct `font-size`; a value used exactly once is a missing role or drift.
**Fix.** It is a role (name it, token it, reuse it) or it is drift (delete it). A one-off size is never the
answer to a wrapping problem; the measure is.

### L5-3 · Inconsistent border radii across components
**Seen as.** A set of components that do not look like a set.
**Mechanism.** 8px button, 6px input, 10px card, 4px badge: each defensible, together saying nobody decided.
Radius is one of the strongest family-resemblance cues there is, so mismatches read as *assembled from
parts* even when everything else matches.
**Confirm.** Lay one of each component side by side at the same scale, or count distinct `border-radius`
values — more than four is the finding.
**Fix.** Bind radius to component *size class*, not to the component: small controls one step, cards the
next, overlays the next. Nested elements compute their radius from the parent — see critique-method §3.3.

## Layer 6 — Color and contrast

### L6-1 · Contrast assumed rather than measured
**Seen as.** Nothing, on the reviewer's monitor; everything, on a laptop at 40% brightness.
**Mechanism.** Muted greys are chosen for how quiet they look in a bright room on a good display, but the
floor is a measurement — 4.5:1 body, 3:1 large text and UI boundaries — and it is routinely missed by
exactly the colors that look most refined.
**Confirm.** A contrast picker on body, muted, placeholder, disabled-adjacent, and text on accent;
`--fg-subtle` on `--bg-sunken` fails most often.
**Fix.** Contrast is an obligation on the *role*, not the value: generate ramps with the matrix printed, and
re-measure both themes whenever a role is re-pointed.

### L6-2 · Three-ish shades of the same grey
**Seen as.** Muddy, unresolved text color with no hierarchy to show for it.
**Mechanism.** `#6b6b6b`, `#6e6e6e` and `#707070` are indistinguishable side by side, so they buy no
hierarchy, yet differ enough that no single replacement fixes them — drift made visible, three people's eyes
or one person's on three days.
**Confirm.** Extract every color literal and sort; values within ~5% lightness are one color typed three
times.
**Fix.** Two foreground roles with stated meanings (`--fg-muted`, `--fg-subtle`), each with a contrast
obligation. A third grey requires a third *meaning*, not a third hex.

### L6-4 · Semantic color used decoratively
**Seen as.** A red badge meaning "new", beside a red meaning "failed".
**Mechanism.** Danger, warning and success are a signalling channel that works because it is reserved;
spending red on emphasis costs the product its ability to say "something is wrong" anywhere, not just here.
**Confirm.** For every intent color: does it report state or decorate? Then — is any state carried by color
alone? About 1 in 12 men have a color vision deficiency ([NEI](https://www.nei.nih.gov/learn-about-eye-health/eye-conditions-and-diseases/color-blindness)), and the most
common kind makes red and green hard to tell apart.
**Fix.** Intent roles reserved by documented rule, and every state using one also carries an icon, a label
or a shape.

### L6-5 · A dark mode that is an inversion rather than a redesign
**Seen as.** Flat, harsh and slightly wrong — photos look odd, the brand color is one nobody chose, cards
have no depth.
**Mechanism.** Inversion is arithmetic, not design, and three things break at once: shadows vanish because
black on a dark surface is nothing, pure white on pure black halates and fatigues, and hue rotation moves
the accent off-brand. Depth in dark mode comes from *surface lightness*, which an inversion has no concept
of.
**Confirm.** Toggle and look at every surface; `rg -n 'dark' src/components/` — any hit is an automatic
fail, because a component needed CSS to survive a theme change.
**Fix.** Re-point Tier-2 roles only: raised surfaces get lighter rather than shadowed, shadow roles re-point
to a hairline plus a lighter surface, text steps back from pure white, and the accent is re-derived at the
same hue for a dark background.

### L6-6 · Text over imagery with no guaranteed contrast
**Seen as.** Legible on the one photograph it was tested with.
**Mechanism.** Contrast against an image is a per-pixel property, so a headline over a dark corner passes
until the CMS gets a brighter photo — and there is no failure mode short of unreadable.
**Confirm.** Swap in the brightest, busiest plausible image and measure at the worst pixel.
**Fix.** A scrim or gradient guaranteeing the floor regardless of image, built into the media component
rather than added per instance.

---

## Layer 7 — States and edges

### L7-1 · Empty states that were never designed
**Seen as.** A heading over nothing — the product looks broken exactly when a new user is deciding whether
it works.
**Mechanism.** Design happened against populated data because that is what the composition needed, yet the
zero case is the *first* state every new user sees, so it is over-weighted in their judgement and
under-weighted in the process.
**Confirm.** Render every collection at zero, then at one item (it stretches a grid), then "filtered to
nothing" (a different message).
**Fix.** The collection primitive takes an empty slot as a *required* prop — name what belongs here, offer
the action that creates it.

### L7-2 · A centred spinner where a skeleton belongs
**Seen as.** A jump when content arrives; a page that feels slower than it is.
**Mechanism.** A spinner replaces a known layout with an unknown one, so the eye cannot pre-position and
arrival reflows everything.
**Confirm.** Throttle the network, record, and watch for layout shift on arrival.
**Fix.** Loading is a state of the component, sized from the same tokens as the loaded state; a skeleton
whose dimensions are not the content's is decoration.

### L7-3 · Disabled with no reason given
**Seen as.** A greyed-out button and a user with nowhere to go.
**Mechanism.** Disabled says "not now" without saying why or what would change it, and it is routinely below
3:1 — so the element carrying the blocked information is the least legible thing on screen.
**Confirm.** For every disabled control, is the reason visible without hovering? Measure it.
**Fix.** Prefer enabled-with-validation; where disabled is right, the component requires a reason string
rendered beside it, not in a tooltip.

### L7-4 · Raw error strings and vanishing toasts
**Seen as.** "Error: request failed (422)", or a message gone before it is read.
**Mechanism.** The error path was implemented rather than designed: an error must answer what happened, what
it means and what to do next, a transport string answers none, and a timed toast additionally assumes the
user was looking.
**Confirm.** Force every failure path and read each message aloud against the three questions.
**Fix.** Errors are content with a defined shape, rendered inline beside what failed and tied to it with
`aria-describedby`. Toasts confirm; they do not report failure.

### L7-5 · Long content never tested
**Seen as.** A wrapped button, a truncated name with no tooltip, a table cell shoving its neighbours off
screen.
**Mechanism.** Built with placeholder text that fit, while real names, translations (often 30% longer) and
large numbers are the normal case rather than the edge.
**Confirm.** A 60-character name, a 7-figure number, a German translation, `dir="rtl"`.
**Fix.** Per-slot behaviour defined in the component — wrap, truncate with a title, or clamp at n lines —
tested with the longest plausible value.

---

## Layer 8 — Interaction and motion

### L8-1 · Motion that is all one duration
**Seen as.** Interactions uniformly sluggish or uniformly abrupt; nothing feels calibrated.
**Mechanism.** One value — usually `all 300ms ease` — everywhere: a hover needs to feel instant (~120ms) and
a panel deliberate (~300ms), so at one duration the hover feels sticky and the panel rushed, while `all`
animates properties nobody chose, including the layout ones.
**Confirm.** Grep every `transition` and `animation`; one distinct duration, or `all`, is the finding.
**Fix.** Motion roles bound to jobs — `--motion-hover`, `--motion-enter`, `--motion-exit`, `--motion-expand`
— entrances decelerating, exits accelerating. Name the properties; never `all`.

### L8-4 · Animation with no job
**Seen as.** Content fading in on scroll and making the reader wait; movement nobody can account for.
**Mechanism.** It was added because the page felt static, but motion that does not show origin, confirm an
action or cover a wait is a delay the reader pays for — and above-the-fold entrances delay exactly the
content people came for.
**Confirm.** Name each animation's job in one clause; then emulate `prefers-reduced-motion: reduce` and
check nothing hangs, since transitions zeroed hard enough to skip `transitionend` leave components stuck
open.
**Fix.** Motion roles named after jobs make a jobless animation hard to express; above-the-fold content
never animates in.

### L8-5 · Affordance that lies
**Seen as.** Users clicking the card instead of the link inside it, or not clicking the thing that is
clickable.
**Mechanism.** Elevation, cursor, color and underline were applied for aesthetics rather than meaning, so
the page's claims about what is interactive are wrong — card elevation in particular reads as "pressable"
whether or not it is.
**Confirm.** Point at every raised, colored or underlined element and say whether it is interactive.
**Fix.** Interactive treatments are reserved to interactive components; a clickable card makes the whole
card the control with one accessible name.

---

## Layer 9 — Conformance

### L9-1 · Token drift
**Seen as.** Nothing — until a rebrand takes three weeks instead of an afternoon.
**Mechanism.** Literals and Tier-1 tokens in component rules are decisions nobody can find, so they survive
every theme, density and brand change unchanged, diverging further each time.
**Confirm.** `python -m scripts.audit_design <path>`. Any finding, not "only warnings".
**Fix.** Add the missing Tier-2 *role*, not the missing value — every failure is a diagnosis of the system,
per the checklist's "what to do when a check fails".

### L9-2 · A `dark` selector inside a component
**Seen as.** Dark mode that works, at the cost of a second set of styles.
**Mechanism.** A component needing CSS to survive a theme toggle means a Tier-2 role is carrying two
meanings, and the component is compensating for a naming failure one level up.
**Confirm.** `rg -n 'dark' src/components/` — expect zero hits.
**Fix.** Split the role in two and re-point both in each theme.

### L9-3 · `!important` and the z-index bid war
**Seen as.** A stacking bug fixed by adding a digit.
**Mechanism.** Both are override order decided by force instead of structure: `!important` inverts layer
order and makes the *next* override strictly harder, and a four-digit z-index is a bid the next person will
raise.
**Confirm.** `rg -n '!important|z-index:\s*[0-9]{3,}'`.
**Fix.** Move the rule to the correct cascade layer; use the closed z-index ladder. Both are architecture
problems wearing a value costume.

---

## Layer 10 — Presentation readiness

### L10-1 · A decision you cannot defend out loud
**Seen as.** A hedge in the meeting — "I think it was because…" — after which the room stops trusting the
rest of the file.
**Mechanism.** The decision was made by iteration and never converted into a reason; it may be right, but an
undefended decision reads as an accident.
**Confirm.** Walk the page giving a one-sentence reason for every non-obvious choice — any sentence needing
a hedge is the finding.
**Fix.** `DESIGN_DECISIONS.md` written as decisions are made, plus `critique_report.py --format defence`
before every presentation.

### L10-2 · Taste presented as fact
**Seen as.** A reviewer disagrees with one opinion and discounts everything around it.
**Mechanism.** An unlabelled preference invites a fight on its own terms, and once one finding is revealed
as preference the rest inherit the suspicion.
**Confirm.** For each claim: measurable, or a mechanism? Neither means taste.
**Fix.** Taste findings carry `is_taste: true` and print in their own section, phrased as a choice with a
named alternative.

### L10-3 · A known flaw left unnamed
**Seen as.** The reviewer finds the thing you already knew about, and it becomes the subject of the meeting.
**Mechanism.** A flaw you raise is a judgement call with a scoped fix; the same flaw raised by someone else
is an oversight, and it recalibrates how carefully they read everything else.
**Confirm.** List what you would fix with another two days — that list is the script.
**Fix.** The "known flaws you are carrying in" section of the defence sheet, with the fix and its cost
beside each.

### L10-4 · Presented at the wrong fidelity
**Seen as.** A structural review that spends forty minutes on a font choice.
**Mechanism.** High-fidelity surfaces invite surface feedback, so a polished comp shown when you need
agreement on structure returns color opinions.
**Confirm.** Name the decision you need out of the meeting; does the fidelity match it?
**Fix.** Greyscale wireframes for structure, full comps for surface — and say at the top which feedback you
are asking for.

---

## Catalogued in `critique-method.md` §3

Eleven further failures get the same treatment — spot it in seconds, the principle, the system fix — in
`references/critique-method.md` §3, because they are also the things a senior reviewer notices first.
They are listed here so this file remains the index.

| Failure | Layer | Where |
|---|---|---|
| Inconsistent gaps at one hierarchy level | Structure | critique-method §3.1 |
| Optical misalignment | Craft | critique-method §3.2 |
| Corner radius that is not concentric | Craft | critique-method §3.3 |
| Type on-scale but semantically wrong for its role | Craft | critique-method §3.4 |
| A focus ring that only works on one surface | Interaction | critique-method §3.5 |
| An accent used decoratively, and therefore devalued | Color | critique-method §3.6 |
| Shadows that imply two light sources | Craft | critique-method §3.7 |
| An icon set drawn at mixed optical weights | Craft | critique-method §3.8 |
| Headings spaced symmetrically | Craft | critique-method §3.9 |
| A grid that is 12 columns in the file and 3 in reality | Structure | critique-method §3.10 |
| A hover state that shifts layout by a pixel | Interaction | critique-method §3.11 |

---

Related: `SKILL.md` (run order), `references/critique-method.md` (stance, severity, delivery),
`web-design-studio/references/review-checklist.md` (the 91 mechanical checks),
`web-design-studio/references/spacing-system.md` §7 and §13.
