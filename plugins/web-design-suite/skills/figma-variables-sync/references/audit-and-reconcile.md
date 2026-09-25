# The Pre-Build Audit, and What to Do With It

The argument about whether a value belongs to the system happens exactly once per
project. The only question is *when*. Held before the build it costs twenty
minutes; held during the build it costs a day per instance, because by then the
value is in code, the code is in a PR, and the PR has a reviewer with an opinion.

This document is the procedure for holding it early, and the ladder for
resolving each finding without either side losing.

## Contents

1. [What the audit checks, and why each one](#1-what-the-audit-checks-and-why-each-one)
2. [Running it](#2-running-it)
3. [Reading the output](#3-reading-the-output)
4. [Reporting it so a designer reads it](#4-reporting-it-so-a-designer-reads-it)
5. [The three-outcome ladder](#5-the-three-outcome-ladder)
6. [Worked example: the design is right](#6-worked-example-the-design-is-right)
7. [Worked example: the system is right](#7-worked-example-the-system-is-right)
8. [Worked example: both are defensible](#8-worked-example-both-are-defensible)
9. [The timed default](#9-the-timed-default)
10. [Escalation: proposing a new token](#10-escalation-proposing-a-new-token)
11. [The things the script cannot see](#11-the-things-the-script-cannot-see)

---

## 1. What the audit checks, and why each one

Each check exists because of a specific way handoffs fail. The "why" column is
the sentence to use when someone asks whether the check is worth running.

| Check | Code | Sev | Why this one exists |
|---|---|---|---|
| Spacing off the 18-step scale | `OFF_SCALE_SPACING` | error | The most common finding by volume. 28 and 18 are the two that show up most, and each one that reaches code is a value with no rule behind it, so it can never be called wrong and never gets fixed |
| Font size off the type scale | `OFF_SCALE_TYPE` | error | A 15px that reaches production makes 14 and 16 both look like mistakes |
| Radius, stroke, leading, tracking, weight, duration, z-index off scale | `OFF_SCALE_*` | warn | Lower volume, same disease. Warn rather than error because a one-off radius rarely propagates |
| Colour not on a ramp | `OFF_RAMP_COLOR` | error | A hex in a design file becomes a hex in a stylesheet, and the rebrand becomes find-and-replace. Reports the nearest ramp step and the OKLab ΔE so the conversation is about a number, not a vibe |
| Text colour below 4.5:1 (3:1 for large) | `CONTRAST_FAIL` | error | The only finding that is a legal issue as well as a quality one. Contrast is measured, never assumed (contract, accessibility floor) |
| Interactive size under 44px | `TAP_TARGET` | error | WCAG 2.2 SC 2.5.8 sets 24×24 as the floor; `--tap-min` sets 44, because 24 is a legal minimum and not a usable one |
| Text style with no `--type-*` role | `UNMAPPED_TEXT_STYLE` | error | One style per role, not one per usage. Ten roles is the whole type system; an eleventh is a fork |
| Effect style with no `--elevation-*` role | `UNMAPPED_EFFECT_STYLE` | warn | `Shadow 12 Soft` cannot be re-tuned without renaming it everywhere, so it never gets re-tuned |
| Semantic colour collection with one mode | `MISSING_DARK_MODE` | warn | Dark mode added later arrives as component overrides, which is the failure Law 6 exists to prevent |
| Missing interaction roles | `MISSING_STATE` | warn | A role that does not exist in the file gets invented during the build by whoever gets there first |
| Alias pointing at nothing | `BROKEN_ALIAS` | error | A library was not exported, or a variable was deleted. Either way the value in the file is not the value you think |
| Alias cycle | `ALIAS_CYCLE` | error | No value at the end of it; renders as an invalid custom property, which usually looks like black on black |

**Severity is about propagation, not about how wrong something is.** An error
multiplies if it reaches code — a spacing value that becomes the precedent for
the next one, a colour copied into three components, a contrast failure that
ships. A warning stays local.

**Two checks the script deliberately does not attempt**, because both need the
node tree rather than the variables, and both take ten seconds by hand:
**detached instances** (select all on a page, compare the components-vs-frames
count — each one is a fork that arrives in code as a one-off component) and
**absolute positioning** (`figma-mapping.md` §9). Do both before you run
anything; they change the estimate more than any number the audit reports.

---

## 2. Running it

```bash
# The default: a terminal report, exit 1 if anything at all is found
python scripts/figma_audit.py variables.json

# What you send the designer
python scripts/figma_audit.py variables.json --format markdown > handoff-questions.md

# What CI reads
python scripts/figma_audit.py variables.json --format json

# REST dump plus the file's styles
python scripts/figma_audit.py rest-dump.json --styles file-styles.json

# Loosen the gate once the errors are resolved and only warnings remain
python scripts/figma_audit.py variables.json --fail-on error
```

Input shapes are detected automatically — the REST `variables/local` response, a
plugin's `{"collections": […]}` export, W3C DTCG nested tokens, or a flat list of
`{name, type, value}` records. Force one with `--shape` if detection guesses
wrong.

Exit codes: `0` clean, `1` findings at or above `--fail-on` (default: any
finding), `2` the input could not be read or contained nothing.

---

## 3. Reading the output

Work the list in this order. It is ordered by what each finding costs you if it
reaches the build, not by how many there are.

1. **`CONTRAST_FAIL` first.** It is the only one with a legal dimension, and it
   is the only one where "ship it and fix later" has a real cost attached.
2. **`BROKEN_ALIAS` / `ALIAS_CYCLE` next.** These mean the export is wrong or
   incomplete. Every other number in the file is suspect until they are cleared,
   because a broken alias means a library did not come across and there may be
   two hundred more values you never saw.
3. **`OFF_RAMP_COLOR` with a ΔE under 0.03.** Below the just-noticeable
   threshold: almost certainly an eyedropper error, not a decision. These are
   free wins — the designer will agree in one message.
4. **`OFF_SCALE_SPACING` and `OFF_SCALE_TYPE`.** The volume findings. Most
   resolve to "nearest step, fine".
5. **`OFF_RAMP_COLOR` with a ΔE over 0.03.** Far enough to be deliberate, which
   makes it a design-system change (§10), not a fix.
6. **Everything else.**

**On ΔE.** The audit reports ΔE<sub>OK</sub>, Euclidean distance in OKLab, where
roughly 0.02 is a just-noticeable difference. It beats "these hexes are
different" because it says whether anyone could *see* it, which is what decides
whether the conversation is about precision or about taste.

**On false positives.** The check is built to have none on on-scale values. If it
reports one, that is a bug in the script, not a judgement call — the scales are
closed sets and membership is arithmetic. Report it rather than working around
it.

---

## 4. Reporting it so a designer reads it

The `--format markdown` output is written for this. Four things make the
difference between a list that gets answered and a list that gets resented.

**Send it once, before estimating.** Not in dribs during the build. A single
message before the work starts reads as diligence; the fourth Slack message on
Wednesday reads as obstruction, and it is the same information.

**Lead with the decision, not the defect.** "These are twelve decisions that need
an owner" is true and is heard. "I found twelve problems in your file" is also
true and is not. Nothing in the audit is a mistake until someone decides it is.

**Give the number and the alternative in the same line.** `28px → nearest step is
24px (--space-6), 4px away` is a statement someone can agree or disagree with in
two seconds. "This spacing is off-system" is an accusation with no exit.

**Name the three outcomes up front, and mean it.** The markdown output opens with
them. If you have never once taken outcome 1 — added a token because the design
was right — nobody will believe outcome 1 is real, and every subsequent audit
gets read as a rejection queue. Spend outcome 1 early, on something real.

### What not to do

| Don't | Because |
|---|---|
| Send raw terminal output | Colour codes, exit statuses and the word ERROR twelve times |
| Report the same colour once per surface | The audit already collapses this to the worst case |
| Fix it silently and move on | You have made a design decision on the designer's behalf and told nobody. That is how two vocabularies start |
| Escalate to a manager | It is a twelve-line list. Send the list |
| Lead with the Laws | Cite them when asked. Opening with "Law 3 says the scale is closed" is an appeal to a document the designer did not write |

---

## 5. The three-outcome ladder

Every mismatch resolves to one of three outcomes. All three are legitimate, and a
project where the answer is always the same one has a broken process rather than
a perfect system.

| Outcome | When | Cost | Who signs off |
|---|---|---|---|
| **1. The design is right** — add a token | The design needs something the system genuinely lacks, and the need will recur | High: a new token is permanent and everyone inherits it | Design-system owner (Law 3) |
| **2. The system is right** — the designer adjusts | The value was incidental. Nobody chose 28 on purpose | Near zero: one nudge in Figma | Nobody. The designer just does it |
| **3. Both are defensible** — document the exception | There is a real reason, and it does not generalise | Medium: one hard-coded value, one paragraph, forever | The pair of you, in `DESIGN_DECISIONS.md` |

### The decision rule

Three questions, in order. Stop at the first clear answer.

> **1. Will this recur?** Will a second screen, component or designer need the
> same value within six months? *No* → outcome 2 or 3.
>
> **2. Can the existing system express the intent, even if not the number?** Not
> "is 24 close to 28" — *does `--gap-separate` say what the designer meant*? If
> the relationship is right and only the pixel is off, the system already has the
> answer. *Yes* → outcome 2.
>
> **3. Is the intent itself new?** A relationship the ladder cannot name, a
> colour role the palette has no step for, a type role outside the ten.
> *Yes* → outcome 1, with sign-off. *No* → outcome 3.

Question 2 does the work and question 2 is the one that gets skipped. Most
off-scale spacing is a *pixel* disagreement inside an intent both sides already
share, and once that is said out loud the answer takes ten seconds.

**When it is genuinely 50/50, take outcome 3.** Documenting an exception is
reversible; adding a token is not. An unnecessary token is still in the file two
years later, used by three components that should have used a role. A documented
exception that turns out to be a pattern gets promoted later, cheaply, with
evidence.

---

## 6. Worked example: the design is right

**Finding**

```
ERROR  space/section-gap   Primitives / Value
       60px is not a step on the spacing scale
       nearest legal step is 64px (--space-16), -4px away
```

**The conversation.** 64 is available and 4px away, so this looks like a routine
outcome 2. It is not. The designer set 60 on a marketing page where the section
rhythm was tuned at 1440, where sections read correctly at 60 and slightly loose
at 64. The real finding is underneath: **there is no fixed correct answer**,
because the right gap at 390px is nowhere near the right gap at 1440px.

**Run the rule.** Recur? Yes — every marketing page has section rhythm. Can the
system express the intent? `--space-section` is `--space-fluid-xl`, a clamp from
64 to 144. So the system *does* have the answer, and the designer was
hand-approximating a fluid value at one viewport.

**Outcome.** Outcome 1, but not the one it looked like. No new spacing step. What
is missing is a *Figma-side representation of the fluid steps*, which the file
has no way to hold (`figma-mapping.md` §4 — `clamp()` cannot cross). Resolution:
eight annotation variables in Primitives — `space/fluid-xl-min` = 64,
`space/fluid-xl-max` = 144 and the same pair for the other three steps — scoped
`GAP`, described as "endpoints of `--space-fluid-xl`; the value between them is
computed in code". The designer checks both endpoints; the build uses one token.

**What got written down**

```md
## 2026-09-17 — fluid spacing endpoints in Figma

Figma variables cannot hold clamp(). The four --space-fluid-* steps are now
represented in the Primitives collection as eight endpoint variables
(space/fluid-{sm,md,lg,xl}-{min,max}), annotation only: they are never bound to
a frame. Designers check section rhythm at 390 and 1440 against the endpoints.
Code keeps one token per step. Proposed by <designer>, signed off by <owner>.
Cost of not doing this: every marketing page arrives with a hand-tuned section
gap that is off-scale at exactly one viewport width.
```

**Why this is the instructive example.** The first read said "60 → 64, done". The
right answer was a structural gap in how the two tools talk, and it was three
questions away. Outcome 1 is rarely a new number; it is usually a missing
*name*.

---

## 7. Worked example: the system is right

**Finding**

```
ERROR  brand/coral   Primitives / Value
       #ff6b35 is not on any ramp
       nearest ramp step is --accent-400 (dEok 0.039) -- far enough to be a
       deliberate choice, which makes it a design-system change, not a fix.
```

**The conversation.** ΔE 0.039 is above the just-noticeable threshold, so the
script correctly refuses to call it an eyedropper error. But "deliberate" and
"considered" are not the same thing. The message to send is one line:

> `brand/coral` (#ff6b35) sits next to `--accent-400` (#f57e4e) — close enough
> that they'd read as two attempts at the same colour if they ever appear on the
> same screen, far enough that I can't just bind it. Was the ramp step not right,
> or is this from an older file?

The answer was the second one. It came from a deck.

**Run the rule.** Recur? No. Can the system express the intent — a warm orange
accent? Yes, `--accent-400` is that colour. Stop at question 2.

**Outcome.** Outcome 2. Designer deletes `brand/coral` and rebinds the two frames
using it to `accent/400`. Elapsed time: four minutes, including the message.

**The general shape.** Most outcome-2 findings are *provenance* problems, not
taste problems — a value carried in from a deck, a pitch file, a component copied
from another project, an eyedropper on a screenshot. The question that resolves
them fastest is not "why 28?" but **"where did this come from?"**, because the
honest answer is usually "somewhere else", and then nobody has to defend it.

---

## 8. Worked example: both are defensible

**Finding**

```
ERROR  control/button-height   Primitives / Value
       36px is below the 44px minimum touch target
```

**The conversation.** The 36px control is a table row's inline action, in a
data-dense admin tool used on desktop with a mouse for eight hours a day. At 44
the table shows nine rows instead of twelve, a real cost to the people who live
in it. The designer is right about their users. The system is also right: 44 is
the floor, the product will eventually be opened on a tablet, and SC 2.5.8 has no
"but it's an admin tool" clause.

**Run the rule.** Recur? Yes — every dense table wants this. Can the system
express the intent? Partly: `--density: 0.875` is exactly "this subtree is
compact". But density scales *spacing* and does not scale `--tap-min`, and must
not, because a floor that scales is not a floor. Is the intent new? No.

**Outcome.** Outcome 3, with a technique that satisfies both sides: the button's
*visual* box is 36px, its *hit area* is 44px, achieved with padding that
overflows the visual bounds. The row keeps its height, the target keeps its size,
nothing in the contract bends. This is the standard resolution for tap-target
findings; reach for it before either side concedes.

**What got written down**

```md
## 2026-09-17 — 36px inline row actions in DataTable

DataTable row actions render a 36px visual control inside a 44px hit area
(negative-margin padding, see DataTable.module.css). --tap-min is unchanged and
still 44; the exception is that the VISUAL size is below it, which SC 2.5.8 does
not require. Twelve rows per screen vs nine measurably matters for the ops team
(observed in <research doc>). Do not copy this into any other component: outside
a dense table, 36px visual controls read as broken. Agreed <designer> / <owner>.
```

Note what that entry does: it records the *decision*, the *evidence*, the
*mechanism*, and — most importantly — **the boundary**. An undocumented exception
becomes a precedent within one sprint. A documented one with "do not copy this
into any other component" is a decision that stays where it was made.

---

## 9. The timed default

Handoff must never stall waiting for an answer. The audit goes out with a
deadline and a stated default, and when the deadline passes the default applies.

**The rule**

> Every open question has a stated default and a stated deadline. If the deadline
> passes with no answer, the default applies, and every default taken is listed
> in the PR description so any of them is a one-line revert.

**The defaults, by finding type**

| Finding | Default if nobody answers |
|---|---|
| Off-scale spacing / type / radius / stroke / leading / tracking / weight | Nearest legal step |
| Off-ramp colour, ΔE < 0.03 | Nearest ramp step |
| Off-ramp colour, ΔE ≥ 0.03 | Nearest ramp step, **and the row stays open** — this one is a real decision and the default is a placeholder, not a resolution |
| Contrast failure | Move the foreground one ramp step away from the surface and re-measure. **Never** ship the failing value |
| Tap target under 44 | 44px hit area, visual size unchanged |
| Unmapped text style | Map to the closest `--type-*` role by size |
| Unmapped effect style | Map to the closest `--elevation-*` by blur radius |
| Missing dark mode | Generate dark by the light mapping, flag every generated value for review |
| Missing states | Implement all seven from the contract's defaults |

**Deadlines that work.** Same-day for anything blocking the first component;
end-of-next-day for the rest. `--deadline "Thursday 5pm"` writes it into the
markdown output.

**Why it works:** it moves the cost of silence onto the person who is silent
without making anyone the bad guy. The designer who is heads-down for two days
gets a sensible result instead of a blocked developer, and the developer never
sends a third reminder.

**The one way it fails:** the defaults are not actually listed in the PR. A
default nobody can find is not a default, it is a silent decision — the exact
thing this procedure exists to prevent. List every one, in the PR body, with its
finding code. If there are twelve, list twelve.

---

## 10. Escalation: proposing a new token

Outcome 1 is a change to the design system, and Law 3 makes the scale closed on
purpose: the day you add `--space-7` is the day the scale stops being a
constraint and becomes a menu. So the path is deliberately not frictionless.

### The bar

A new Tier-1 primitive must clear all four:

1. **A real design decision requires a step that does not exist.** Not "it felt
   tight". The existing steps have been tried and named.
2. **It will recur.** Two or more independent uses, ideally by different people.
3. **None of the four alternatives applies.** From `spacing-system.md` §2: it is
   not an optical correction; it is not compensating for a wrong neighbouring
   value; the element is not the wrong size; and it is not actually a *size*
   rather than a *space* (a 22px avatar is a size, and sizes have their own
   tokens).
4. **The name is a role, not a value.** If the best name anyone can produce is
   `--space-7`, the answer is no. A step that cannot be named for what it does is
   a value looking for a home.

A new **Tier-2 role** is a much lower bar and mostly waved through: roles are
cheap, they are the vocabulary the team speaks, and they add no new values. If
the proposal can be satisfied by a new role over an existing primitive, that is
almost always the right answer and needs no ceremony.

### The proposal

Six lines. Anything longer is a sign the answer is no.

```md
## Token proposal: --gap-inline-fused

Tier:        2 (role -> --space-0-5)
Value:       2px @1x
Need:        Icon+label pairs at 12px type. --gap-fused (4px) reads as a
             deliberate separation at that size; the pair stops reading as
             one object.
Evidence:    Badge, Tag, InlineStatus, TableCell status chip — four components,
             three authors, all independently landed on 2px.
Alternative: --gap-fused everywhere and accept the looser optical result.
             Rejected: it is visible at 12px and below, which is most of our
             dense UI.
Cost:        One role. No new primitive — --space-0-5 already exists.
```

### Who signs off, and how fast

| Change | Approver | Turnaround |
|---|---|---|
| A new Tier-2 role over an existing primitive | The design-system owner alone | Same day |
| A new Tier-1 primitive | Owner + one other regular contributor | Within the week |
| A new ramp step | Owner + a contrast re-check of the whole ramp | Within the week |
| A change to an existing primitive's value | Owner, plus a visual diff of everything that reads it | Never same-day |

**Do not block the build on it.** Take the timed default, ship, land the token in
a follow-up that replaces the default. A proposal that holds up a release gets
approved for the wrong reason, and a token approved under deadline pressure is a
token nobody re-examines.

### After it lands

A new token is done when all four are true: it is in `tokens.css` with a comment
saying why it exists; it is in the Figma Primitives or Semantic collection with
the same name and a description; `references/token-contract.md` is updated **in
every skill in the suite**, because a fork here is how the suite stops being a
suite; and the scale tables in `scripts/figma_audit.py` are updated in the same
commit.

That last one gets missed. The audit's tables *are* the contract, in executable
form. If they disagree with `tokens.css`, the audit reports the token you just
added as off-scale — and lies with great confidence about everything else.

---

## 11. The things the script cannot see

The audit reads variables and style metadata. A file can pass it cleanly and
still be unbuildable. Check these by hand, in this order, before you run
anything — and note that the top three change the *estimate*, which is worth more
than everything the script reports.

| Check | How | What it means |
|---|---|---|
| **Absolute positioning** | Open a few frames; look for auto-layout badges | Every gap is a measurement rather than a decision; responsive behaviour is unspecified and you will be inventing it (`figma-mapping.md` §9) |
| **Detached instances** | Select all on a page; compare component vs frame counts | Each one is a fork that arrives as a one-off component |
| **Variables actually bound** | Click a frame's fill and a text style's size — variable chip or bare number? | Bare numbers mean the token layer in the file is decorative and the next export will not match this one |
| **Number of viewports drawn** | Count the artboards | One artboard = no responsive story; you are choosing the breakpoints |
| **The seven states** | Look for focus, loading and error variants | Figma libraries usually draw four. The three missing ones are the three that decide whether the thing works |
| **Empty and loading states** | Look for them on anything that fetches | Anything that fetches gets designed empty and loading states, not defaulted ones (contract) |
| **Real content** | Look for "Lorem", perfectly-sized names, three-item lists | A design that only works at one content length is a design you will renegotiate at build time |
| **Focus order** | Ask | Figma cannot express it. Somebody has to decide it, and the default DOM order is a decision, not an absence of one |
| **Motion** | Ask | Prototype links are not durations. `--motion-*` pairs a duration with an easing; a prototype gives you neither |

**The one-line version to send before anything else:**

> Before I audit the values — is this file built in auto-layout throughout, are
> the text styles and fills bound to variables rather than typed, and are there
> focus/loading/error states anywhere? Those three change the estimate much more
> than anything I'll find in the numbers.
