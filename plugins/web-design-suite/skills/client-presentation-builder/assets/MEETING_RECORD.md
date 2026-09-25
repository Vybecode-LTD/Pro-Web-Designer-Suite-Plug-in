# Meeting Record — <project> — <YYYY-MM-DD>

> **Write this the same day, before you open anything else.** The deck is the
> artifact everyone remembers and this is the one that matters. A design
> review produces decisions; decisions that live only in four people's memories
> are decisions that get re-made, and re-made decisions are the single largest
> source of unbilled work in a design engagement.
>
> **This doubles as scope protection.** It is not a legal document and it is
> not adversarial — it is a summary sent to the room within a few hours, which
> nobody objects to and everybody reads. Six weeks later, when "we always
> wanted the booking flow on the homepage" arrives, the answer is a link, sent
> without argument, rather than a disagreement about what was said in a room.
> Send it as the body of an email, not as an attachment nobody opens.

**Meeting:** `<first concept | iteration 2 | sign-off | handoff>`
**Date / duration:** `<YYYY-MM-DD, 45 min>`
**Present:** `<names and roles — mark who has decision authority>`
**Absent but affects this:** `<the person who was not in the room and will have
opinions. Name them here; §5 is about them>`
**Recording / notes by:** `<name>`

---

## 1. Approved

Decisions that are now closed. Anything in this table is done being discussed.

| # | Decision | Approved by | Conditions attached |
|---|---|---|---|
| D1 | `<as worded in DECISION_LOG.md>` | `<name>` | `<none / "if the copy fits">` |
| D4 | `<…>` | `<name>` | `<…>` |

> Use the same IDs as `DECISION_LOG.md`. Different IDs in two documents is how
> a decision gets approved twice and built once.

## 2. Changed in the room

The most important table here. What changed, **who asked**, **why**, and what
it costs — cost recorded at the moment of the change, when nobody is defensive
about it yet.

| # | Was | Now | Asked by | Reason given | Cost (time / scope / tradeoff) |
|---|---|---|---|---|---|
| D2 | `<one column>` | `<two columns on desktop>` | `<name>` | `<"looks empty on my monitor">` | `<+1 day; loses the mobile-first parity we designed for>` |

> If the reason column says "preference", write "preference". It is not an
> insult — it is the difference between a change you will cheerfully make
> again and a change that keeps coming back because the underlying problem was
> never named.

## 3. Still open

| # | Question | Owner | Needed by | What is blocked until then | Default if nobody answers |
|---|---|---|---|---|---|
| Q1 | `<which of the two headers>` | `<client name>` | `<date>` | `<build of the nav>` | `<we ship option A>` |

> **Every open item gets a default.** "We will proceed with A unless we hear
> otherwise by Friday" converts silence into a decision instead of into a
> delay, and it is the single most useful sentence in this document.

## 4. Rejected, and why

| # | Idea | Raised by | Why it did not proceed |
|---|---|---|---|
| — | `<carousel on the homepage>` | `<name>` | `<agreed to revisit after launch data>` |

> Record the rejections. An idea that was considered and set aside comes back
> in six weeks as a fresh idea unless the reasoning is written down somewhere
> the room can see it.

## 5. The person who was not there

`<The decision-maker who missed the meeting will have views, and those views
will arrive as a change request with no context. Write here: who they are,
what was decided that they have not seen, who is briefing them, and by when.
If nobody owns that briefing, the next meeting re-runs this one.>`

## 6. Next

| What | Owner | By |
|---|---|---|
| `<send this record to the room>` | `<you>` | `<today>` |
| `<update DECISION_LOG.md with the changes in §2>` | `<you>` | `<today>` |
| `<next review>` | `<both>` | `<date>` |

---

## The send

Send within four hours. The body of the email is three lines and a link:

> Thanks all. Summary of what we agreed, what changed and what is still open
> is below — shout if I have any of it wrong by `<day>`, otherwise we build
> from this.
>
> Approved: D1, D4, D5. Changed: D2 (two-column desktop, +1 day). Open: Q1,
> your call by `<date>`, default is option A.

Two things make this work and both are about tone. **Ask to be corrected** —
it is a summary offered for confirmation, not a record being asserted. And
**give the silence a deadline** — "shout by Thursday, otherwise we build from
this" is the sentence that turns a document into an agreement.

Then update `DECISION_LOG.md` the same day, so the next deck is assembled from
what is true rather than from what was true before this meeting.
