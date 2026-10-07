---
name: client-presentation-builder
description: Present design work to a client or team as reasoning, not taste, with decks, rationale, before-and-after comparisons and answers to objections. Not for critiquing the design (design-critique-gate).
---

# Client Presentation Builder

> **Running the scripts** — by path, from the user's project root, so `src/`
> means the project's `src/` and every output lands in the project, never
> inside this plugin:
>
> ```bash
> python "${CLAUDE_SKILL_DIR}/scripts/build_presentation.py" DECISION_LOG.md --audience client --dry-run
> ```
>
> The commands below are written `python -m scripts.<name>`. That form is for a project that
> has copied the scripts into its own `scripts/` folder, as CI and git hooks
> do; when you run one here, use the path form.
> This skill's scripts are in `${CLAUDE_SKILL_DIR}/scripts/` (build_presentation.py).
> From sibling skills: `${CLAUDE_PLUGIN_ROOT}/skills/web-design-studio/scripts/audit_design.py`; `${CLAUDE_PLUGIN_ROOT}/skills/design-critique-gate/scripts/critique_report.py`; `${CLAUDE_PLUGIN_ROOT}/skills/perf-budget-gate/scripts/perf_audit.py`.

A design presented without its reasoning is just taste. In a room full of people with
taste, taste loses to whoever is most senior.

This skill is for the meeting. `design-critique-gate` prepares you to survive the review by
finding what is wrong before anyone else does; this one helps you **win** it, by making the
reasoning that is already in the work legible to people who were not there while you did it.

It assumes you can do the work. The gap it closes is the other half of the job: standing in
a room full of senior designers and their clients and making the case — which is a separate
skill, learned separately, and the one nobody teaches because everyone senior has forgotten
they had to learn it.

---

## The one principle

**You are not presenting a design. You are presenting a set of decisions.**

This is not a framing trick. It is a statement about what the room is *able* to do.

A stakeholder cannot meaningfully approve a layout. They have no vocabulary for it, no
criteria, and no way to be wrong — so what comes back is a reaction, and a reaction is a
referendum on taste that the most senior person in the room wins by default.

A stakeholder can absolutely approve **"we optimised for scanning over density, because the
analytics say 70% of sessions are under forty seconds."** That has a constraint they can
check, an alternative they can prefer, and a cost they can accept or reject. It is a
business decision, which is a thing they are qualified to make and, crucially, a thing they
can be held to later.

| What you show | What the room can say | What you get |
|---|---|---|
| A layout | "I don't love it" | A second meeting, and no idea what to change |
| A layout with reasoning attached | "I don't love it, but I understand why" | A conversation about a tradeoff |
| **A decision** | "Yes — or no, because *this* constraint has changed" | A decision, and a reason it can be revisited later |

Every non-obvious choice gets the same five-part shape. It is the whole method:

> **Constraint → Options considered → Choice → Consequence → Evidence**

| Part | What it does in the room |
|---|---|
| **Constraint** | Proves something other than your preference forced this |
| **Options** | Demonstrates judgement — this is the part that makes a junior read as senior |
| **Choice** | The decision, one sentence, no hedging |
| **Consequence** | Names the cost before they find it. A cost you name is a tradeoff; a cost they find is a flaw |
| **Evidence** | Converts an assertion into a fact — or is honestly absent |

Worked conversions from flat statements into this shape:
`references/narrative-structure.md` §5.

---

## The honesty boundary

**This skill does not help anyone win an argument they should lose.**

It makes real reasoning legible. It does not manufacture justification for arbitrary
choices, and every mechanism in it is built to make that distinction easy to hold under
pressure — including in the script, which routes any decision marked `coin-flip` to the
open-questions slide and will not render it as rationale.

If a decision has no reason, the honest move is to say so and ask for the client's
preference:

> "That one is genuinely a coin flip. Both work, I have no argument for either — what do
> you prefer?"

**Teach this as a strength, because it is one.** Three mechanisms, all of them working in
your favour:

1. **It is checkable.** A room can tell the difference between a reason and a reason-shaped
   sentence, usually on the second question. A manufactured justification survives "why?"
   and dies on "why that one and not the other?" — and when it dies, it takes the credibility
   of your *real* reasons with it, because the room now has to re-evaluate all of them.
2. **It concentrates your authority.** A designer who defends everything is defending
   nothing in particular. Half a dozen defended decisions and two honest coin-flips is a far
   stronger position than eight decisions with reasons, because the six are now believable.
3. **It gives the client something real to own.** People need to contribute. Handing them
   the genuinely open choices is how you protect the decisions that are not open, and it is
   much cheaper than discovering their need to contribute when it lands on the one thing
   that was load-bearing.

The same boundary applies to numbers. **A figure you cannot defend is worse than no figure**
— `references/evidence.md` §1 — and an automated accessibility pass is never "fully
accessible" (§3 of the same file, which has the wording that does not overclaim).

---

## Workflow

### 1. Collect the evidence that already exists

Nothing here is written for the presentation. If it was, the presentation is a
reconstruction and it will sound like one.

| Input | From | Gives you |
|---|---|---|
| `DECISION_LOG.md` | `assets/DECISION_LOG.md`, kept as you worked | Every decision in the five-part shape |
| `audit.json` | `audit_design.py --json` (web-design-studio) | "Every value comes from one file" |
| `perf.json` | `perf_audit.py --json` (perf-budget-gate) | Weight against a budget agreed up front |
| `a11y.json` | `a11y_runtime.mjs --json` or `a11y_static.py --json` (a11y-audit-runner), or axe-core results | The accessibility claim you can actually make: "passes" only when it records no violations, "keyboard-tested by hand" only when the decision log has a `## Tested by hand` section, or `--manual FILE` a record, saying what was tested |
| `defence.md` | `critique_report.py --format defence` (design-critique-gate) | The decisions needing an out-loud justification, the taste calls, the flaws you are carrying |
| `shots/` | Screenshots at the width the decision was made at | The work |

**Consume the defence sheet; do not rebuild it.** `design-critique-gate` already decided
which decisions need defending and which flaws you are carrying in. Re-deriving that here
would produce a second, divergent answer to a question that has one.

```bash
python -m scripts.audit_design src/ --json > audit.json
python -m scripts.perf_audit dist/ --json > perf.json
python -m scripts.critique_report findings.json --format defence -o defence.md
```

### 2. Pick the three to five decisions this audience actually cares about

**Rarely the ones you found hardest.** The decision that cost you two days of iteration is
usually invisible and uninteresting to a client; the one you made in four minutes — putting
the turnaround time in the headline — may be the entire meeting.

Select by audience, not by effort:

| Audience | Wants, in the first ninety seconds |
|---|---|
| Client decision-maker | Risk removed and outcome. Not process |
| Client marketing lead | Whether this does the job they are measured on |
| Client developer | Whether they can maintain it after you leave |
| Agency creative director | Whether it is good, **and whether it is theirs** |
| A mixed room | The hardest. Address the person who can say no; give everyone else one slide that is obviously theirs |

Full taxonomy, the mixed-room rule, and what loses each of them:
`references/narrative-structure.md` §§1–2.

### 3. Build the narrative

Pick the structure for the situation you are actually in — first concept, iteration review,
final sign-off, redesigning something the client is attached to, internal walkthrough — from
`references/narrative-structure.md` §3. They are genuinely different shapes, not one deck
with different titles.

Two rules that apply to all of them:

- **"Here's what we made" is the weakest possible opening.** It invites evaluation before
  context, makes you the subject, and has no shape. Open with the problem in their words, the
  number that decided everything, or the question the meeting has to answer (§4).
- **Raise the parts you are not happy with yourself, early, with a plan** (`references/narrative-structure.md` §8). A flaw you
  name is a judgement call; the same flaw found by a reviewer is an oversight, and from that
  moment every other decision is re-read as a possible accident.

### 4. Generate the deck

```bash
python -m scripts.build_presentation DECISION_LOG.md --audience client --dry-run
```

Read the outline. Edit the narrative — which means editing `DECISION_LOG.md`, because the
deck is downstream of it — then build:

```bash
python -m scripts.build_presentation DECISION_LOG.md \
  --audience client \
  --audit audit.json --perf perf.json --a11y a11y.json \
  --defence defence.md --screenshots shots/ \
  --out deck.html --notes notes.md
```

### 5. Rehearse against the objections

Not the presentation — the **questions**. The deck is the easy part; you already know it.

Work `references/objection-handling.md` §1 and answer the five you expect out loud, to a
wall, in full sentences. The ones that will come: *I don't like the colour* · *it feels
empty* · *can we make the logo bigger* · *our competitor's site does X* · *can we fit more
above the fold* · silence.

Then check the two meta-skills that decide how those go: telling a taste objection from a
business objection, because they need **opposite** responses (§2), and restating an
objection before answering it (§3).

If a senior designer or a creative director is in the room, `references/objection-handling.md` §9. The single highest-value
move in it is the pre-meeting: send the deck early and ask *"anything in here you would
present differently?"* — which converts the disagreements that would have damaged you in
front of a client into a ten-minute conversation where being persuaded is free.

### 6. Capture what was decided in the room

**The deliverable everyone forgets.** Fill `assets/MEETING_RECORD.md` and send it the same
day: what was approved, what changed and who asked, what is still open with an owner and a
default, and what each change cost.

It doubles as scope protection, and it works because it is not adversarial — it is a summary
offered for correction, with a deadline on the silence: *"shout if I have any of this wrong
by Thursday, otherwise we build from this."* Six weeks later, when "we always wanted the
booking flow on the homepage" arrives, the answer is a link rather than an argument.

Then update `DECISION_LOG.md` the same day, so the next deck is assembled from what is true
now.

---

## `scripts/build_presentation.py` — stdlib Python 3, no dependencies

Assembles the deck from evidence that already exists. It invents nothing: every generated
number carries a `data-cite` naming the file and JSON path it came from, and the same map is
embedded in the deck as `#deck-provenance`, so a challenged figure is one keystroke from its
source. Anything the inputs do not contain becomes a **marked gap** — printed at build time,
listed in the speaker notes, and shown in place on the slide when you press `N`.

```bash
python -m scripts.build_presentation DECISION_LOG.md --dry-run
python -m scripts.build_presentation DECISION_LOG.md --audience team --out team.html
python -m scripts.build_presentation DECISION_LOG.md --audit audit.json --perf perf.json \
    --a11y a11y.json --defence defence.md --screenshots shots/ \
    --out deck.html --notes notes.md
python -m scripts.build_presentation DECISION_LOG.md --out deck.html --emit-css build-css/
python -m scripts.audit_design build-css/ --strict          # the deck audits clean
```

| Flag | Does |
|---|---|
| `--audience client\|team\|creative-director` | Changes emphasis **and order**, per `narrative-structure.md` §§1, 3 |
| `--audit` `--perf` `--a11y` | The suite's JSON, translated into plain language with the numbers cited |
| `--defence FILE` | The critique gate's defence sheet: taste calls become open questions, known flaws become the "what we are not happy with" slide, and a blocking item stops the build with exit 1 |
| `--screenshots DIR` | Inlined as data URIs so the deck is one file. `home--before.png` + `home--after.png` pair into a comparison automatically |
| `--handout FILE` | The deck the client keeps: the same slides in document flow, one per printed page, with no presenter notes, gaps, appendix or provenance in the file |
| `--manual FILE` | The manual test record (keyboard, screen reader) when it is kept outside the log's `## Tested by hand` |
| `--dry-run` | Prints the slide plan, the decision ranking and every gap. Writes nothing |
| `--notes FILE` | Speaker notes as markdown, ending in a pre-flight checklist of the gaps |
| `--emit-css DIR` | Writes the deck's own CSS out so the gate can be run on it |
| `--tokens FILE` | Build the deck on the client's `tokens.css` so it is in their brand |
| `--max-decisions N` | Headline decisions for client and creative-director (default 5; a team gets all of them) |

Exit `0` fine · `1` the defence sheet says do not present yet · `2` bad invocation.

**The deck is a self-contained HTML file.** Arrow keys, space and Page Up/Down navigate;
`Home`/`End` jump; `N` toggles presenter notes and the gap markers; `F` is fullscreen; `?`
shows the keyboard map; `Ctrl/Cmd+P` prints one slide per page, with the notes only while they are showing.
The PDF someone will ask for by email an hour after the meeting is `--handout`: the
same slides with no notes, gaps, appendix or provenance in the file at all.

**It is built on the suite's tokens and passes `audit_design.py --strict`.** You are
presenting a design system; a hardcoded value in your own deck is an embarrassment as well
as a bug.

### What the audience flag actually changes

Not the title. The ordering, the slide set, and which field of each decision leads.

| | `client` | `team` | `creative-director` |
|---|---|---|---|
| **Opens after the cover with** | The problem in their words | How it is built, and the gate | The premise |
| **Decisions shown** | Top 5 by relevance | **All of them** | Top 5, **hardest first** |
| **Each decision leads with** | The problem → what we did → what it costs | The decision → what you inherit | The constraint → the options rejected |
| **Rejected options** | Compact, "we also considered" | Listed | **Emphasised** — the demonstration of judgement |
| **Weaknesses appear** | Late, after the evidence | As tickets with owners | **Early**, before the visuals |
| **Closes on** | The ask, and sign-off | Where to start | What critique is wanted |

---

## Routing

| Situation | Go to |
|---|---|
| Building or restyling the system itself | `web-design-studio` |
| Proving every state renders | `component-state-matrix` |
| Proving it is fast | `perf-budget-gate` |
| Adversarial review before anyone sees it | `design-critique-gate` — **run this first** |
| Documentation for whoever inherits it | `design-system-docs` |
| **Standing in front of the people who decide** | **here** |

Within this skill:

| You want | Read |
|---|---|
| What each audience wants in the first ninety seconds | `references/narrative-structure.md` §1 |
| A room with four different audiences in it | `references/narrative-structure.md` §2 |
| The deck shape for this specific meeting | `references/narrative-structure.md` §3 |
| Redesigning something the client is attached to | `references/narrative-structure.md` §3.4 |
| How to open | `references/narrative-structure.md` §4 |
| Turning a flat statement into a decision | `references/narrative-structure.md` §5 |
| Before/after without flattering the before | `references/narrative-structure.md` §6 |
| Whether a process slide earns its place | `references/narrative-structure.md` §7 |
| Raising your own weak spots | `references/narrative-structure.md` §8 |
| The close and the ask | `references/narrative-structure.md` §9 |
| Using numbers in front of a client | `references/evidence.md` §1 |
| Saying what an audit or a budget proves, without jargon | `references/evidence.md` §2 |
| Accessibility wording that does not overclaim | `references/evidence.md` §3 |
| Performance wording that does not overclaim | `references/evidence.md` §4 |
| Screenshots, device framing, the honest crop | `references/evidence.md` §5 |
| Whether to show code | `references/evidence.md` §6 |
| "Can you just try it in blue?" | `references/evidence.md` §7 |
| The objection catalogue | `references/objection-handling.md` §1 |
| Taste objection vs business objection | `references/objection-handling.md` §2 |
| Disagreeing without damaging the relationship | `references/objection-handling.md` §§4–5 |
| Being wrong in the room | `references/objection-handling.md` §6 |
| A decision-maker who was not there | `references/objection-handling.md` §7 |
| Feedback that contradicts itself | `references/objection-handling.md` §8 |
| Presenting alongside senior designers and a creative director | `references/objection-handling.md` §9 |
| Capturing decisions the same day | `assets/MEETING_RECORD.md` |
| A token or role name | `references/token-contract.md` |

---

## Failure modes

| Failure | Why it happens | Correction |
|---|---|---|
| Presenting the artifact, not the decisions | It is what you have been staring at for two weeks | Every non-obvious choice gets constraint → options → choice → consequence → evidence, or it is cut |
| Writing the decision log the night before | The work felt more urgent | It takes two minutes per decision at the moment you make it, and the constraint and the rejected option are the two things you cannot reconstruct a week later |
| Manufacturing a reason for a coin-flip | Being asked "why?" feels like a test you must pass | Say it is a coin flip. It is the move that makes your real reasons believable |
| Three directions presented as peers | It feels generous | It is an abdication: you are asking a client to do design selection. One recommendation, with the rejected options named |
| A number with no comparison | It sounds impressive | "412 KB" is noise; "412 KB against the 600 KB budget" is an argument |
| Claiming "fully accessible" from a green tool run | The tool said pass | Automated checks fully decide 7 of the 55 A and AA criteria. `evidence.md` §3 has the wording |
| Flattering the before | It happens by accident — old screenshot, narrower window, less content | Same width, same content, same state, or do not show it |
| Hoping nobody notices the weak part | Optimism | They always notice, and it costs three times as much when they find it |
| Defending taste with data | It feels like the strong move | It reads as a dodge. Accommodate a taste objection; investigate a business one |
| Ending with "let us know what you think" | Asking feels pushy | A presentation without a specific ask gets a vague answer. Name the action, then stop talking |
| No meeting record | The meeting ended and there was another one | Send it the same day. It is the cheapest scope protection that exists and nobody objects to a summary |

---

## The three sentences to remember

1. **You are not presenting a design, you are presenting a set of decisions** — because a
   room cannot approve a layout, and it can approve a tradeoff.
2. **A decision with no reason is an open question, not a reason you have not thought of
   yet** — saying so is what makes the decisions you *do* defend believable.
3. **Whatever was decided in the room is the deliverable** — write it down the same day, or
   you will have the same meeting again in six weeks with worse information.
