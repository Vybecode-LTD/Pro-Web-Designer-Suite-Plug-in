---
name: design-critique-gate
description: Adversarial design review before a client sees the work, with ranked findings that name the mechanism behind each problem. Use for 'does this look professional'. Not for accessibility audits.
---

# Design Critique Gate

> **Running the scripts** — by path, from the user's project root, so `src/`
> means the project's `src/` and every output lands in the project, never
> inside this plugin:
>
> ```bash
> python "${CLAUDE_SKILL_DIR}/scripts/critique_report.py" findings.json --audit audit.json
> ```
>
> The commands below are written `python -m scripts.<name>`. That form is for a project that
> has copied the scripts into its own `scripts/` folder, as CI and git hooks
> do; when you run one here, use the path form.
> This skill's scripts are in `${CLAUDE_SKILL_DIR}/scripts/` (critique_report.py).
> From sibling skills: `${CLAUDE_PLUGIN_ROOT}/skills/web-design-studio/scripts/audit_design.py`.

The expensive failure is not a bug. It is standing in front of a senior designer or a
client with work that comes apart in the first ninety seconds — because in those ninety
seconds you lose the room, and every good decision in the file afterwards is heard as an
excuse.

This skill is that ninety seconds, run by you, first. It assumes the work is flawed and
goes looking in the order a real critic's eye moves.

Two things it is not:

- **It is not the checklist.** `web-design-studio/references/review-checklist.md` is 92
  mechanical checks and `web-design-studio/scripts/audit_design.py` is the machine gate.
  Those verify
  **conformance** — that the work obeys the system. This skill judges **quality and
  argument** — whether the work is any good and whether you can defend it. Run the
  checklist first; a critique of a page that fails conformance is a critique of noise.
- **It is not harsh adjectives.** "The hierarchy is weak" is not a finding, it is a mood.
  A finding names the mechanism: *the gap between the heading and its body is larger than
  the gap between sections, so the heading reads as floating rather than leading.* One is
  arguable, actionable and checkable. The other is a fight.

---

## The one rule

**Every finding names a mechanism, not a verdict.**

A finding is not done until you can state it in this shape:

> **[what is physically true] → [what that causes the eye or the user to do] → [the fix at the system level]**

| Verdict (useless) | Mechanism (a finding) |
|---|---|
| "Hierarchy is weak" | H2 is 20px and body is 18px — a 1.11 ratio. Below about 1.2 the eye reads a size change as noise, not rank, so the section headings are not functioning as headings |
| "Feels cramped" | Card inset is 16px while the gap between cards is 24px. The container is tighter than the space around it, so the cards read as bursting rather than holding |
| "Colors are off" | Muted text measures 3.1:1 on the surface against a 4.5:1 floor. It is not a taste problem, it is unreadable in daylight |
| "Needs more polish" | Three border radii in one row: 8px on the button, 6px on the input, 10px on the card. Nothing is wrong individually; together they say nobody decided |

If you cannot name the mechanism, you have a *suspicion*. Log it with
`"confidence": "suspected"` and keep going — a suspicion you write down is honest; a
suspicion dressed as a verdict is how critiques get dismissed wholesale.

Full method, including the diagnostic moves for converting a suspicion into a mechanism:
`references/critique-method.md`.

---

## The run order

Critique in the order attention actually moves. **A finding at layer 1 makes every finding
below it moot** — there is no point spacing-correcting a page that answers the wrong
question, and no point in color work under a hierarchy that sends the eye to the wrong
object. Work down. Stop and report when a layer produces a blocking finding, because
fixing it changes everything beneath.

| # | Layer | The question | Time |
|---|---|---|---|
| 1 | **Premise** | Is this solving the stated problem at all? | 2 min |
| 2 | **First impression** | What does it communicate before it is read? | 1 min |
| 3 | **Hierarchy** | Does the eye go where it should, in the order intended? | 3 min |
| 4 | **Structure and rhythm** | Grouping, proximity, alignment, section beat | 4 min |
| 5 | **Craft** | Spacing precision, optical corrections, type detail, corners | 5 min |
| 6 | **Color and contrast** | Measured, never judged | 3 min |
| 7 | **States and edges** | Seven states, plus empty / loading / error / long / RTL | 4 min |
| 8 | **Interaction and motion** | Affordance, feedback, keyboard, reduced motion | 3 min |
| 9 | **Conformance** | The auditor and the 92 checks | 2 min |
| 10 | **Presentation readiness** | Can you defend every non-obvious decision out loud? | 3 min |

### 1 — Premise

Before anything visual. Read the brief, then read the page, and answer in one sentence
what this page is for and who is on it. If the sentence needs an "and also", the page has
two jobs and will do neither.

- **Probe.** Cover the design. Write the one action the page exists to produce. Uncover.
  Is that action the most prominent thing on screen?
- **Probe.** Name the reader's state of mind arriving. A pricing page reached from a
  comparison article and one reached from a logged-in upgrade prompt are different pages.
- **Failure signature.** Solving a stated problem with an unstated one — the brief said
  "reduce support tickets", the design added a beautiful search that ranks by recency.
- **What it moots.** Everything. A wrong-page failure cannot be fixed by spacing, and a
  critique that opens with spacing on a wrong page has wasted the room's attention.

### 2 — First impression

The pre-reading layer. You get this once per person, and you have already burned yours,
which is why the techniques in `references/critique-method.md` §"Defeating familiarity
blindness" exist.

- **The 5-second test.** Look for five seconds, look away, write what you remember and
  what you think the page is for. Wrong answers are findings, and the mechanism is
  whatever won the attention you needed elsewhere.
- **The squint test.** Squint until type is unreadable. What remains are the value blocks.
  The primary action should be one of the two strongest. If the blocks are all the same
  weight, there is no hierarchy and layer 3 is already answered.
- **The 10-foot test.** Stand back. Composition survives; detail does not. Anything that
  falls apart at distance has a structure problem wearing a craft costume.
- **Failure signature.** The page reads as a *category* ("a SaaS landing page") before it
  reads as a *thing* ("the tool that closes your books in a day").

### 3 — Hierarchy

Rank is a claim: this matters more than that. Check whether the page's visual claims match
its actual priorities.

- **Probe.** Trace your first three fixations with a finger. Compare to the intended
  order. Divergence is the finding, and the mechanism is whatever grabbed the eye —
  usually size, contrast, isolation or color, in that order of strength.
- **Probe.** Count the things competing for "most important". Two primary buttons, an
  accent-colored badge and a full-bleed image is four claims and therefore zero.
- **Probe.** Read only the headings, in order. If that outline is not the page's argument,
  the visual hierarchy and the semantic one have separated.
- **Failure signature.** Emphasis spent on what is *easy* to emphasise (a hero image, a
  gradient) rather than on what the reader needs (the number, the action, the proof).

### 4 — Structure and rhythm

Grouping is spacing's only job. Check that the spacing says what the content means.

- **Probe.** For each gap, say out loud what it means: "16 because the label annotates the
  input". Cannot finish the sentence → it was eyeballed. This is the proximity ladder in
  `token-contract.md`, used as an interrogation.
- **Probe.** Same relationship, two values anywhere on the page? That is the single most
  common structural defect and it is always a system fix, never a local one.
- **Probe.** Draw the alignment lines. How many distinct left edges are there? More than
  two or three in a column and the page has no spine.
- **Probe.** Scroll fast at 1440 and at 390. Is there a beat? A page with no section rhythm
  reads as one long undifferentiated column no matter how good each section is.
- **Reference.** `web-design-studio/references/spacing-system.md` §13 is the debugging
  procedure; run it whenever the layout "feels off" and you cannot name why.

### 5 — Craft

Where "almost professional" is decided. None of these is individually noticeable; together
they are the entire difference. The catalogue with spot-in-seconds instructions is
`references/failure-catalog.md`, layer 5.

- Optical alignment vs mathematical alignment (§7 of the spacing reference is the theory).
- Concentric corners: inner radius = outer − inset, with a floor.
- Type detail: tracking on display sizes and on uppercase, measure between 60–75ch,
  headings asymmetrically spaced, no orphan sizes.
- Edge treatment: one border weight per elevation level; shadows implying one light source.
- Icon set drawn at one optical weight, not one nominal stroke width.

### 6 — Color and contrast

**Measured, never judged.** Open a contrast picker. Every judgement here is a number or it
is not a finding.

- Body ≥ 4.5:1, large text and UI boundaries ≥ 3:1, focus ring ≥ 3:1 against *both*
  adjacent surfaces.
- Count the accent's surface area. More than a few percent and it has been spent
  decoratively, which costs you the ability to point at anything.
- Toggle dark mode and look at every surface. An inversion is not a theme — shadows become
  mud, and depth has to be rebuilt from surface lightness plus a hairline.
- Semantic colors used decoratively (a red that means "look" rather than "wrong") is a
  major finding: it destroys the channel you need for real errors.

### 7 — States and edges

The work is judged on the default state and used in the others.

- Seven states on every interactive element: default, hover, focus-visible, active,
  disabled, loading, error. `:active` and loading are the two that get skipped.
- Empty, loading, error designed — not defaulted. An empty state is the first state a new
  user sees, so it is the one that decides whether they believe the product works.
- Longest plausible content, shortest plausible content, zero. A 60-character name, a
  7-figure number, a one-item grid.
- `dir="rtl"` and 200% zoom. Both find physical properties doing logical properties' jobs.

### 8 — Interaction and motion

- Does anything that looks interactive fail to be, or vice versa? Affordance is a claim too.
- Tab the whole page with no mouse. Reachable, visible, escapable, in visual order.
- Every animation: name its job in one clause — *shows where this came from*, *confirms the
  tap*, *covers the wait*. No clause, no animation.
- Hover must not change layout. A border-width or padding change on hover shifts the
  element and its neighbours; the page twitches under the cursor and reads as broken.
- `prefers-reduced-motion: reduce` honoured without breaking transition-end handlers.

### 9 — Conformance

Cite, do not re-implement. This layer is two commands:

```bash
python -m scripts.audit_design <path> --json > audit.json     # web-design-studio
```

then work `web-design-studio/references/review-checklist.md` — all 92 checks, twelve
groups. Fold the machine output into the critique rather than reporting it separately:

```bash
python -m scripts.critique_report findings.json --audit audit.json
```

Conformance findings rank *below* judgement findings of the same severity, deliberately.
A hundred token violations are one afternoon; a hierarchy that sends the eye to the wrong
object is a re-design.

### 10 — Presentation readiness

The last question is not "is it good", it is **"can I defend it out loud"**.

- Every non-obvious decision has a one-sentence answer, the alternative you rejected, and
  what the choice costs. If the answer needs hedging, the decision is not made yet.
- Every preference is labelled as a preference *by you, first*. A reviewer who discovers
  an unlabelled taste call reads every other decision as accidental.
- Every known flaw you are carrying in is named before anyone else names it. A flaw you
  raise is a judgement call; the same flaw raised by the reviewer is an oversight.

```bash
python -m scripts.critique_report findings.json --format defence
```

---

## Severity, and the taste rule

Rank by consequence, not by how much it annoys you.

| Severity | Test | Example |
|---|---|---|
| **blocking** | It breaks | Unreadable contrast, no focus indicator, wrong page |
| **major** | It misleads | Two primaries; heading grouped with the wrong block |
| **minor** | It cheapens | 2px alignment miss; an orphan type size; three near-identical greys |
| **taste** | It merely differs from preference | You would have picked a different accent hue |

**Taste findings are always labelled as taste.** This is not politeness, it is leverage: a
critique that mixes preference into defects gets the defects dismissed along with the
preference. Label it, separate it, and your defects survive the meeting. The rubric and
the ordering rules are in `references/critique-method.md` §"Severity and ordering".

**Report three.** Not thirty. The top three get fixed; a list of thirty gets skimmed, and
the recipient picks the three that are easiest rather than the three that matter.

```bash
python -m scripts.critique_report findings.json --summary
```

---

## Routing

| You are doing | Read |
|---|---|
| Any critique at all | `references/critique-method.md` — the stance, the moves, the delivery format |
| Naming what you can see but not diagnose | `references/failure-catalog.md` — symptom → mechanism → confirm → system fix |
| Critiquing your own work before a meeting | `assets/self-review-protocol.md` — the timed 20-minute routine |
| Writing the critique up | `assets/CRITIQUE_TEMPLATE.md`, then `scripts/critique_report.py` |
| Checking a token or role name | `references/token-contract.md` |
| Mechanical conformance | `web-design-studio/references/review-checklist.md` + `scripts/audit_design.py` |
| A layout that feels off and you cannot say why | `web-design-studio/references/spacing-system.md` §13, then §7 for optical |

---

## The script

`scripts/critique_report.py` — stdlib only, Python 3.

```bash
python -m scripts.critique_report findings.json                  # ranked critique
python -m scripts.critique_report findings.json --format triage  # ticket-tracker lines
python -m scripts.critique_report findings.json --format defence # out-loud defence sheet
python -m scripts.critique_report findings.json --summary        # top three, nothing else
python -m scripts.critique_report findings.json --audit audit.json --fail-on blocking
```

Findings are JSON. Each one carries `layer`, `severity`, `title`, `mechanism`, `evidence`,
`fix`, `confidence` and `is_taste`, plus `status` (`open` | `fixed`) and optional `covers`;
the schema is in the script's docstring and the shape is the same one
`assets/CRITIQUE_TEMPLATE.md` fills in by hand. `--audit` folds `audit_design.py --json`
output in as conformance findings, collapsed by rule, deduplicated against anything you
already wrote up by hand — a whole rule only when your finding claims it (the rule id in
`covers`, or in backticks), and otherwise site by site, so a group of eleven violations is
not silently deleted because you mentioned one of them, or used the word "important".
A rule raised with `--audit-blocking` is never folded, and every merge is reported on
stderr. The defence sheet carries every open major and minor finding — confirmed ones
first, suspicions labelled as suspicions — and drops the ones marked `fixed`.

---

## How the critique is delivered

Adversarial about the work, never about the person — including when the person is you.
Full guidance in `references/critique-method.md` §"Delivering a critique"; the minimum:

1. **Lead with what works, specifically and briefly.** Not warm-up. It establishes that
   you looked, and it tells the recipient which parts not to change while fixing the rest.
2. **Three findings, in consequence order**, each as mechanism → evidence → fix.
3. **Taste in its own section**, labelled.
4. **Name what you are unsure of.** "I think the eye goes here first; check with someone
   who has not seen it" is worth more than a confident wrong call.
5. **End at the system level.** Every fix is a change to a token, a role, a component API
   or a rule — never a local patch. A local patch is the mechanism by which the next
   critique finds the same class of problem again.

---

## Failure modes of critique itself

| Failure | Why it happens | Correction |
|---|---|---|
| Listing thirty findings | It feels thorough | Rank and cut to three. The rest go in the triage list |
| Verdicts instead of mechanisms | Faster, and it sounds confident | Every finding gets the "→ causes → because" shape or it is downgraded to a suspicion |
| Critiquing the fix you already imagined | You solved it, then justified it | Name the mechanism before the fix. If the mechanism does not survive writing down, the fix was taste |
| Skipping layer 1 because the page looks good | Visual quality is more fun to discuss | Premise first, always. Beautiful work on the wrong page is the most expensive failure in the list |
| Taste smuggled in as a defect | You want it your way | If it is not measurable and not a mechanism, it is taste. Label it |
| Grinding craft on a draft | Habit | Match the pass to the stage: premise and hierarchy on a wireframe, craft on a build |
| Self-critique that finds nothing | Familiarity blindness | Run `assets/self-review-protocol.md`. You cannot see your own work unaltered |

---

## The three sentences to remember

1. **Mechanism, not verdict** — a finding you cannot state as a cause is a mood.
2. **Layer order is consequence order** — a premise failure makes every craft finding
   beneath it a waste of the room's attention.
3. **Three findings, labelled taste separately** — because three get fixed, and a
   preference smuggled in as a defect takes the real defects down with it.
