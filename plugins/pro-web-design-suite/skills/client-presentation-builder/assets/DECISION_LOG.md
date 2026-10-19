# Decision Log — <project>

> **Fill this in as the work happens, not the night before the meeting.**
> Two minutes per decision, at the moment you make it, while the alternative
> you rejected is still in your head. A decision written up a week later is a
> reconstruction, and a reconstruction is what taste sounds like under
> questioning.
>
> `scripts/build_presentation.py` reads this file. Keep the field names.
> Everything else — order, extra prose, your own sections — is yours.

**Project:** `<product / engagement>`
**Client:** `<company>`
**Presenter:** `<your name>`
**Date:** `<YYYY-MM-DD>`
**Stage:** `<first concept | iteration 2 | final sign-off | internal handoff>`

---

## Brief

`<Two or three sentences, in the client's own words where you can quote them.
What they asked for, what they are actually worried about, and the one number
or fact that constrains everything else. This is the strongest opening slide
you own — "here's what we made" is the weakest.>`

## Premise

`<One sentence: the argument the work makes. Only needed for a creative
director, who is buying your judgement rather than your output. If you cannot
write it, the work has two ideas and will present as neither.>`

## Ask

`<The three things you need said out loud in the room. A presentation without a
specific ask gets a vague answer, and a vague answer is a second meeting.>`

- `<Sign-off on the four decisions below, or a named objection to one.>`
- `<A preference on the open questions.>`
- `<Confirmation of the date we are building to.>`

---

## Decisions

> One block per decision. **Constraint → Options → Choice → Consequence →
> Evidence** is the whole method: a stakeholder cannot approve a layout, but
> they can absolutely approve "we optimised for scanning over density because
> 70% of sessions are under 40 seconds."
>
> | Field | Required? | The test it has to pass |
> |---|---|---|
> | `Constraint` | **yes** | Something outside your preference forced this. No constraint → it is taste, and it belongs under `Status: coin-flip` |
> | `Options` | **yes** | What you would have done instead. A decision with no rejected option reads as a first idea kept |
> | `Choice` | **yes** | What you actually did, in one sentence, no hedging |
> | `Consequence` | **yes** | What it costs. Naming the cost yourself is what makes the rest believable |
> | `Evidence` | if it exists | A file, a number, a quote, a session recording. **No evidence is fine — inventing one is not** |
> | `Status` | default `decided` | `decided` · `coin-flip` · `open` · `reversed`. A reversed decision (by status, or by a row in `## Reversals`) is never argued as current: it goes on the "What changed since last time" slide, as reversed |
> | `Reversed to` | if reversed | What replaced it, when the `## Reversals` row does not say |
> | `Audience` | optional | `client` · `team` · `creative-director` · `all`. Drives which 3–5 lead the deck |
> | `Tags` | optional | `conversion, forms, tokens, perf, type, colour…` — used for ranking |
> | `Say` | optional | The exact sentence you will use out loud. Write it once, here |

### D1 — `<the decision, as a headline a non-designer understands>`

**Status:** decided
**Audience:** client, team
**Tags:** `<conversion, forms>`
**Constraint:** `<the thing outside your control that forced this: analytics,
a technical limit, a legal requirement, the client's own words, a deadline>`
**Options:** `<option A — what it would have bought>; <option B — why it lost>`
**Choice:** `<what you did>`
**Consequence:** `<what it costs, honestly — there is always something>`
**Evidence:** `<analytics 2026-08: 68% of sessions on mobile; perf.json: total
412 KB against a 600 KB budget>`
**Say:** `<the one sentence, out loud, no hedging>`

### D2 — `<…>`

**Status:** decided
**Audience:** creative-director
**Tags:** `<type, hierarchy>`
**Constraint:**
**Options:**
**Choice:**
**Consequence:**
**Evidence:**

### D3 — `<a decision you genuinely have no argument for>`

**Status:** coin-flip
**Audience:** client
**Options:** `<option A>; <option B>`
**Consequence:** `<what changes either way — usually "nothing structural">`
**Say:** That one is genuinely a coin flip. Either works and I have no
argument for one over the other — what do you prefer?

> **A coin-flip is never dressed up as rationale.** The builder routes it to
> the open-questions slide on purpose. A designer who can say "I don't have a
> reason for that one" is believed about the decisions they *do* defend — and
> a room that catches you manufacturing a reason stops believing all of them
> at once. This is the single highest-return line in the whole method.

---

## How to fill this in fast

**At the moment of the decision, write the constraint and the options.** Those
are the two you will not be able to reconstruct later — the constraint gets
absorbed into "obviously", and the rejected option disappears entirely once
the chosen one exists on screen.

**Choice and consequence can wait until the end of the day.** They are still
true in six hours.

**Evidence is a pointer, not a paragraph.** `perf.json: ledger.bytes.total` is
enough; `build_presentation.py` reads the number out of the file itself and
prints the file and JSON path next to it, so nobody has to trust your memory.

**If you cannot write a constraint, that is information, not a failure.** Set
`Status: coin-flip` and move on. Half a dozen defended decisions and two
honest coin-flips is a far stronger position than eight decisions with
manufactured reasons, because the second kind collapses the moment one of them
is questioned properly.

---

## Since last time

<!-- An iteration review (Stage: iteration review, in the header) opens with
this: their list from the last round, read back verbatim, and what became of
each item. The row that was not done is the slide (narrative-structure.md
§3.2): say the constraint that stopped it and what was done instead, or it is
heard as "they ignored me". Delete the example row. -->

| You asked | What we did | If not, why not |
|---|---|---|
| `<their words>` | `<the change, with its decision id>` | `<the constraint, and what was done instead>` |

## Tested by hand

<!-- What was checked manually, by whom, when: "Keyboard: every page, Tab and
Shift+Tab, 2026-09-20 (A. Name)". The deck claims "keyboard-tested by hand" ONLY
when this section says so; with it empty, the accessibility slide says no manual
pass is recorded. -->

## Reversals

> When a decision is overturned — by the client, by a constraint you found
> late, or by you — do not edit the original. Add a row. The history of a
> reversed decision is the cheapest possible answer to "why can't we just go
> back to what we had in March".

| Date | Decision | Reversed to | Who asked | What it cost |
|---|---|---|---|---|
| `<date>` | `<D4>` | `<what replaced it>` | `<name>` | `<hours / scope / a compromise>` |
