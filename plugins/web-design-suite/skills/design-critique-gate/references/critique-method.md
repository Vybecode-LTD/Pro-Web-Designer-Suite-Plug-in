# Critique Method

How to critique so that the findings are true, ranked, and acted on. The run order lives
in `SKILL.md`; this is the craft of the critique itself.

## Contents

1. The diagnostic stance
2. Turning a suspicion into a mechanism
3. What senior reviewers notice that juniors do not
4. Severity and ordering
5. Delivering a critique
6. Critiquing your own work
7. Receiving a critique

---

## 1. The diagnostic stance

A critique is a diagnosis. A diagnosis names a cause; a review names a feeling. The
difference is not tone — it is whether the recipient can act without guessing.

**The finding shape:**

> **[what is measurably true] → [what that makes the eye or the user do] → [the fix at the
> system level]**

Everything else is commentary. Three properties fall out of the shape, and each one is
what makes a critique survive contact with a defensive room:

| Property | Why it matters |
|---|---|
| **Falsifiable** | "H2 is 1.11× body" can be checked and disagreed with on the merits. "Hierarchy is weak" can only be denied |
| **Causal** | It says *why* the reader is confused, so a different fix that removes the same cause is also correct. A verdict licenses only the fix you imagined |
| **Transferable** | A mechanism generalises. "Emphasis below 1.2× reads as noise" fixes eleven other headings; "make this bigger" fixes one |

### The before/after pair

A finding is not proven until you can name the *minimal change* that removes the symptom.
This is the critique's control experiment: if the change you propose would not visibly fix
what you described, your mechanism is wrong and you have found a different problem.

> **Symptom.** The pricing table's most expensive plan does not read as the recommended one.
> **Mechanism.** All three columns share `--elevation-card` and the same 1px border. The
> only difference is a small badge, which is below the squint threshold, so at first
> fixation there are three equal objects and the eye picks the leftmost by habit.
> **Before/after.** Raise the recommended column one elevation step and give it the accent
> border. Squint again: one column now survives. That is the proof.

Write the before/after in one clause. If you cannot, you are describing taste and should
label it.

### Adversarial about the work, generous about the intent

Assume every decision had a reason and that the reason is not visible to you. That is not
politeness — it is accuracy. Half of what looks like carelessness is a constraint you do
not know about (a CMS field limit, a legal string, an unfinished API). Ask, or state the
assumption in the finding: "assuming the badge copy is fixed, …". A finding built on a
wrong assumption is discarded along with the twelve good ones next to it.

---

## 2. Turning a suspicion into a mechanism

"Something feels off" is the start of the method, not a failure of it. The moves, in order
of how often they pay:

| Move | What it isolates |
|---|---|
| **Measure two things you think are equal** | Near-miss alignment, near-miss spacing, near-miss greys |
| **Measure two things you think are different** | An "obvious" hierarchy that is a 1.1× size step |
| **Greyscale it** | Whether hierarchy is carried by structure or propped up by color |
| **Squint or blur to ~8px** | What actually has visual weight once detail is gone |
| **Flip it horizontally** | Balance and alignment; familiarity blindness cannot survive a mirror |
| **Shrink it to 25%** | Composition and rhythm; everything craft-level disappears, and what is left is the structure |
| **Delete the image** | Whether the layout works or the photograph was carrying it |
| **Replace copy with real, longest-plausible copy** | Everything that was designed around convenient text |
| **Read the headings alone** | Whether the semantic outline is the argument you think it is |
| **Say each gap's meaning out loud** | Gaps chosen by eye. If the sentence will not finish, the value was guessed |
| **Put it on a phone** | Desktop-only generosity, tap targets, and the truth about the hero |
| **Tab through it** | Every state that was never designed |

If three moves produce nothing, record it as `"confidence": "suspected"` with what you
tried. An honest suspicion is a contribution; a suspicion asserted as fact costs you the
room for the rest of the review.

### The five-why, applied to pixels

Stop at the level where the fix is a change to the *system*, not to the instance.

> The card looks cheap → because its shadow is heavy → because it uses `--shadow-lg` →
> because the raised elevation role was never defined → because the elevation ladder has
> six shadow primitives and two roles → **the fix is two more roles, not a lighter shadow
> on this card.**

---

## 3. What senior reviewers notice that juniors do not

Eleven things. None of them is individually visible to an untrained eye; collectively they
are the entire difference between "nice" and "designed". For each: how to spot it in
seconds, the principle underneath, and the fix at the system level.

### 3.1 Inconsistent gaps at one hierarchy level

**Spot it.** Scroll to any row or list and measure two adjacent gaps that should mean the
same thing. Or: `rg -o '(gap|padding|margin)[^;:]*:\s*[^;]+;' src/components | sort | uniq -c | sort -rn`
— anything with a count of 1 is suspect.

**Principle.** Spacing is the only channel that encodes *relationship*. Two values for one
relationship makes the channel noisy, and the reader stops trusting proximity as a cue —
which means every grouping on the page works slightly less well, not just this one.

**System fix.** One relationship, one Tier-2 role from the proximity ladder. If the two
gaps genuinely differ, the relationships differ, and the *content structure* is what needs
fixing.

### 3.2 Optical misalignment

**Spot it.** Hold a straight edge (or a browser ruler) down the left of a column
containing text, an icon and a quoted line. Anything with an ascender-free start, a round
glyph, or a quotation mark will measure aligned and look indented.

**Principle.** The eye aligns *visual mass*, not bounding boxes. Round shapes, directional
glyphs and punctuation carry their mass away from the box edge, so mathematical alignment
reads as misalignment — and it reads as *sloppiness*, not as a measurement error.

**System fix.** Optical corrections live in a named Tier-3 property (`--optical-nudge`),
carry a comment stating the perceptual reason, and never exceed 2px — above 2px it is a
layout bug being papered over. See `web-design-studio/references/spacing-system.md` §7.

### 3.3 Corner radius that is not concentric

**Spot it.** Find any rounded thing inside another rounded thing. If the two radii are
equal, the corner is wrong. It reads as the inner element having been *peeled off* the
outer one.

**Principle.** Two concentric curves must have radii differing by exactly the distance
between them, or they are not concentric and the eye sees two unrelated arcs sharing a
corner. **inner = outer − inset**, with a small floor so the inner does not go square.

**System fix.** Compute it from the card's own tokens with `calc()`, expose it as a Tier-3
property, and let every nested element read it. A hand-picked inner radius drifts the
moment the padding changes.

### 3.4 Type that is on-scale but semantically wrong for its role

**Spot it.** Name the role of every text style out loud — "this is a section heading",
"this is metadata". Then check the size against what that role means elsewhere in the
product. An on-scale size doing the wrong job passes every audit and still reads wrong.

**Principle.** A scale guarantees *harmony*, not *meaning*. `--text-xl` on a caption is
perfectly on-scale and still tells the reader that a caption outranks the body it
annotates. Rank is a claim; the scale does not check your claims.

**System fix.** Components read composite `--type-*` roles, never raw `--text-*` steps.
Roles carry size, leading, tracking and weight together, which is what makes the claim
reviewable in one place.

### 3.5 A focus ring that only works on one surface

**Spot it.** Tab across a button on the page background, then one on a card, then one on
an accent-filled band or a dark footer. One of them will be invisible.

**Principle.** A ring designed as a single color has one contrast value; it needs 3:1
against *whatever is behind it*, which changes per surface. A ring that disappears on the
primary CTA is worse than no ring, because it is the control most likely to be reached by
keyboard.

**System fix.** The two-part ring from the token contract: an inner halo in the *surface*
color plus an outer ring in `--border-focus`, so it separates from any background —
`box-shadow: var(--shadow-focus)` paired with `outline: var(--stroke-focus) solid transparent`
so it survives forced-colors mode, which discards box-shadow entirely.

### 3.6 An accent used decoratively, and therefore devalued

**Spot it.** Screenshot the page, desaturate everything except the accent hue. Measure the
remaining area. More than a few percent of the surface and the accent has stopped meaning
anything.

**Principle.** Accent is a pointer, and a pointer works by exclusion. Each additional
accented element divides the signal by the number of claimants; at five, the primary
action is no more findable than the body text.

**System fix.** Write the accent's meaning into the token's comment ("the one action on
this page") and give components a non-accent emphasis tier — weight, elevation, or a
neutral border — so the next "make this stand out" has somewhere to go that is not the
accent.

### 3.7 Shadows that imply two light sources

**Spot it.** Compare the shadows of any two raised elements. Different vertical offsets,
different blur-to-offset ratios, or one with a downward offset next to one with a halo,
means two suns.

**Principle.** Elevation is a *physical* metaphor and it only reads as depth if the physics
are consistent: one light source means every shadow shares direction, and blur grows with
distance from the surface while opacity falls. Inconsistent shadows do not read as
"different styles", they read as flat objects with decoration stuck on.

**System fix.** Generate the elevation ladder from one light position, bind each step to a
role (`--elevation-card`, `--elevation-overlay`), and forbid raw `--shadow-*` in component
CSS. In dark mode, re-point the roles to *surface lightness plus a hairline*: a black
shadow on a dark surface is invisible, so depth has to be rebuilt, not dimmed.

### 3.8 An icon set drawn at mixed optical weights

**Spot it.** Line the icons up in a row at the size they ship at and squint. Some will go
grey and some will stay black. The offenders are usually a filled icon among strokes, or a
dense glyph (a grid, a calendar) next to a sparse one (a chevron).

**Principle.** Nominal stroke width is not optical weight. A 1.5px stroke on a glyph with
twelve segments puts three times the ink on screen as the same stroke on a chevron, so the
denser icon reads darker and pulls rank it was never meant to have.

**System fix.** One family, one grid, one stroke; correct density by *removing detail* from
the busy glyph, not by thinning its stroke. Icons render at the sizes the grid was drawn
for. Mixed sources are the usual cause — a set of twenty with four borrowed from a second
library never settles.

### 3.9 Headings spaced symmetrically

**Spot it.** Measure above and below any heading. Equal values are the finding.

**Principle.** Proximity is the *only* cue saying which block a heading belongs to. Equal
space gives the reader no answer, so the heading reads as floating between two sections
rather than leading the one beneath it — and the reader has to re-read to work out what it
introduces. The cost is small per heading and compounds down a long page.

**System fix.** Asymmetry belongs to the heading *role* in base type styles, not to a class
on one section: space above at the section or subsection step, space below one or two rungs
tighter. Then no author ever chooses it again.

### 3.10 A grid that is twelve columns in the file and three in reality

**Spot it.** Overlay the grid and count how many distinct left edges the content actually
uses. A twelve-column grid where everything starts at column 1, 5 or 9 is a three-column
grid with extra ceremony — and, worse, the three-column rhythm is usually inconsistent
because the twelve-column freedom hid the inconsistency.

**Principle.** A grid's value is the *constraint*, not the geometry. Twelve columns offer
so many legal positions that alignment decisions get made ad hoc, which produces the
near-miss edges in §3.2 at scale. The grid stops being a shared decision and becomes a
per-element one.

**System fix.** Name the layout primitives the page actually uses — Sidebar, Switcher,
Grid with `minmax()`, Center with a measure — and build from those. Page-level column
arithmetic is where systems go to die. If the twelve-column grid is a handoff requirement,
define the three or four *named spans* that are legal and treat anything else as a finding.

### 3.11 A hover state that shifts layout by a pixel

**Spot it.** Hover slowly across a row of cards or buttons and watch the *neighbours*, not
the hovered element. Any movement at all is the finding. The usual cause is a border going
from 1px to 2px, or padding gaining a pixel.

**Principle.** Border and padding are layout properties: changing them reflows the element
and everything downstream of it in the flex or grid line. The reader perceives it as the
page being unstable under the cursor, which reads as *broken* rather than *responsive* —
and on a trackpad, the shift can move the element out from under the pointer, producing a
hover-flicker loop.

**System fix.** Declare the resting border at its final width in a transparent color, or
use an inset `box-shadow` for the emphasis. Hover changes color, opacity and transform
only. The rule belongs in the base interactive style so that no component re-decides it.

---

## 4. Severity and ordering

The recipient will fix three things. Your entire job after finding the problems is making
sure they are the *right* three.

### The rubric

Ask the four questions in order and stop at the first yes.

| # | Question | Severity | Meaning |
|---|---|---|---|
| 1 | **Does it break?** | `blocking` | Unusable, unreadable, unreachable, or the wrong page. Someone is excluded or the work fails its purpose |
| 2 | **Does it mislead?** | `major` | The user reads the wrong thing as the point, or the design asserts a relationship the content does not have |
| 3 | **Does it cheapen?** | `minor` | Nothing fails; the work reads as almost-professional. This is where near-miss alignment, orphan sizes and three greys live |
| 4 | **Does it merely differ from my preference?** | `taste` | Label it. Always |

Two rules on top:

- **Count exposure.** The same defect on a primary CTA and on a footer link are not the
  same severity. Multiply by how many people hit it and how central it is to the job.
- **Count cost of delay.** A finding that gets harder to fix later (a token, an
  architecture decision, a content model) ranks above an equal-severity one that stays
  cheap (a color value).

### The ordering rule

Within a severity, **earlier layer wins** — premise above hierarchy above craft. The
reason is not neatness: fixing an earlier layer changes what the later findings look at,
so a craft finding reported above a hierarchy finding is work you are asking someone to
do twice.

`scripts/critique_report.py` implements exactly this ordering. If you disagree with where
something lands, change its severity, not the order.

### The taste rule

> **A finding that is not measurable and not a mechanism is taste, and it is labelled as
> taste by you before anyone else labels it.**

This is leverage, not manners. A critique that smuggles preference in among defects gets
the defects dismissed along with the preference — the recipient rejects one obvious
opinion and discounts the rest by association. Labelled taste costs nothing and buys the
defects their credibility.

Taste findings are still worth raising. They just go in their own section, phrased as a
choice rather than an error: *"I would take the accent off-hue from the category norm —
that is a brand argument, not a defect, and you may have chosen it deliberately."*

### Confidence

Three levels, and they are not decoration:

| Level | Means | Use when |
|---|---|---|
| `confirmed` | Measured or reproduced | You have the number, the screenshot, or the file:line |
| `likely` | Mechanism named, not measured | You can explain the cause but did not verify it |
| `suspected` | Symptom only | Something is wrong and you cannot yet say what |

Ship `suspected` findings. Mark them. A named suspicion invites the one person who knows
the constraint to answer it; an unnamed one turns up in the client meeting instead.

---

## 5. Delivering a critique

The format that gets acted on rather than resented:

1. **One sentence on what the work is trying to do.** It proves you read the brief and it
   gives the recipient the chance to correct the premise before you critique against it.
2. **What works, specifically, briefly.** Not a warm-up — it is information: these are the
   parts not to touch while fixing everything else. "The card rhythm is right and the
   empty state is genuinely designed" is useful. "Looks great overall!" is noise.
3. **Three findings, in consequence order.** Mechanism → evidence → fix, each one.
4. **The rest in a triage list**, not in the conversation.
5. **Taste, labelled, in its own section.**
6. **What you are unsure of**, by name.
7. **The one question you need answered** to finish the review.

### Rules of phrasing

| Do | Not |
|---|---|
| "The gap above the heading is smaller than below, so it groups with the block above" | "The spacing is off" |
| "I read the demo button first — was that the intent?" | "The hierarchy is confusing" |
| "Muted text measures 3.1:1; the floor is 4.5:1" | "The grey is too light" |
| "This is taste: I'd use a warmer neutral" | "The neutrals feel cold" |
| Critique the artifact | Critique the author |
| Give the mechanism, let them pick the fix | Redesign it in the review |

### Length

A critique longer than a page does not get read as a critique; it gets read as an attack
or as a backlog. Three findings in prose, the rest as a triage list, and a defence sheet if
a presentation is imminent. `scripts/critique_report.py` produces exactly those three
artifacts from one findings file so there is no incentive to write them separately.

---

## 6. Critiquing your own work

You cannot see your own work. You see your *intention* for it, superimposed. Every
technique below is a way of making the artifact unfamiliar enough to look at.

| Technique | What it defeats | Cost |
|---|---|---|
| **Flip it horizontally** | Composition blindness — a mirrored layout is a new image to your visual system, and imbalance jumps out | 10 s |
| **Shrink it to 25%** | Detail obsession. Only structure and rhythm survive | 10 s |
| **Greyscale it** | Color propping up a hierarchy that has no structural basis | 10 s |
| **Read it backwards** | Copy blindness — start at the last section and read up, so each block is judged without the momentum the one before it gave you | 3 min |
| **Put it on a phone** | Desktop-only generosity, tap targets, and the hero's real content | 2 min |
| **Leave it overnight** | Everything. Sleep is the only reliable familiarity solvent | 1 night |
| **Five seconds with someone else** | Your assumption about what the page communicates. Show it, take it away, ask what it was for | 1 min |
| **Explain it out loud to an empty room** | Decisions you never actually made. The sentence that will not finish is the finding | 5 min |
| **Re-read the brief last** | Scope drift; the beautiful thing you added that answers no question that was asked | 2 min |

The timed routine that puts these in order is `assets/self-review-protocol.md`.

Two failure modes specific to self-critique:

- **Finding nothing.** Means the techniques were skipped, not that the work is clean. Run
  the protocol; it forces at least one finding per layer or an explicit "checked, clean".
- **Finding everything.** Late-night self-critique produces thirty findings and a rewrite
  impulse. Rank before acting; the rubric is indifferent to how you feel at 1am.

---

## 7. Receiving a critique

The skill that makes the other six pay. Handled badly, you stop being given real feedback
— quietly, and permanently.

| Move | Why |
|---|---|
| **Ask for the mechanism** | "What made the eye go there?" converts a verdict into something you can act on, and it is a genuine question, not a defence |
| **Separate the observation from the prescription** | "The heading floats" may be right while "make it bigger" is wrong. Take the observation; you own the fix |
| **Write it down before you respond** | Answering in real time is arguing; it also loses the second and third findings while you defend the first |
| **Say the constraint once, then move on** | "The copy is fixed by legal" is context. Repeated, it is a wall, and the reviewer stops offering findings |
| **Assume the mood is data** | "Something feels cheap" from a senior reviewer is a real signal with an unfound mechanism. Find it yourself rather than dismissing it |
| **Thank them for the one that stung** | It was the expensive one. The ones that flatter were cheap to give |

Disagreeing is legitimate — but on the mechanism, not on the taste of the reviewer: *"the
gap is intentional; the section below is a different topic"* is a real answer. *"I like it"*
is not, and it is the sentence that ends the useful part of the review.

---

Related: `SKILL.md` (the run order), `references/failure-catalog.md` (symptom → mechanism →
confirm → fix, organised by layer), `assets/self-review-protocol.md` (the 20-minute timed
routine), `web-design-studio/references/review-checklist.md` (the mechanical prerequisite).
