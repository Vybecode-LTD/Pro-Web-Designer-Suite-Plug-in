# Narrative Structure

How to sequence a design presentation so the reasoning arrives before the picture. The
principle — you are presenting decisions, not designs — lives in `SKILL.md`; this is the
structure that makes it survive a room.

## Contents

1. The audience taxonomy, and the first ninety seconds
2. The mixed room
3. Deck structures for the five situations
4. The opening
5. Framing a decision
6. Before and after, done honestly
7. Showing the work
8. The parts you are not happy with
9. The close, and the ask

---

## 1. The audience taxonomy, and the first ninety seconds

Everyone in the room is asking a question in the first ninety seconds, and it is not the
same question. Answer the wrong one and everything afterwards is heard as avoidance.

| Who | The question they are actually asking | What they want first | What loses them |
|---|---|---|---|
| **Client decision-maker** | "Is this going to work, and what is it going to cost me?" | The outcome, and the risk you have already removed | Process. They are not buying your method, they are buying an absence of problems |
| **Client marketing lead** | "Will this do the job I will be measured on?" | The mechanism by which it produces leads, sign-ups, bookings | Craft talk. Optical alignment does not appear on their dashboard |
| **Client developer** | "Can I maintain this after you leave?" | The system: tokens, components, states, the gate | Vision language. They have inherited three of those and they all rotted |
| **Agency creative director** | "Is this good, and is it *ours*?" | Your judgement — the calls, the rejected options | Justification by data alone. A deck of numbers reads as a designer who cannot see |
| **The absent decision-maker** | (nothing, yet) | — | Everything. §2 and `objection-handling.md` §8 |

### 1.1 The client's decision-maker

They are buying certainty. Every sentence should reduce the number of ways this can go
wrong for them personally.

- **Open with risk removed, not with work done.** "The three things that could have gone
  wrong on this project were X, Y and Z. Here is where each one landed."
- **Cost is a fact, not an apology.** Every decision has one. Saying it first is what makes
  you sound like someone who has done this before.
- **Never make them adjudicate a design argument.** If you and their marketing lead
  disagree, resolve it before the meeting or present it as a named open question with a
  recommendation. A decision-maker forced to pick a side in a taste fight remembers the
  meeting as a mess.

### 1.2 The client's marketing lead

They will be asked "did the new site work?" in three months. Give them the answer they will
give.

- **Name the metric before the design.** "The number we optimised for is completed
  bookings, not time on page."
- **Show the path.** Walk one user from arrival to conversion, out loud, once. This is the
  only slide they will retell accurately.
- **Hand them ammunition.** One sentence they can repeat internally — "it loads in under
  two seconds on a phone, which is where two thirds of our traffic is" — is worth more to
  them than any screen in the deck.

### 1.3 The client's developer

The person most able to kill the project quietly, by declaring it unmaintainable after you
leave. Win them in the first two minutes and they will defend your decisions in rooms you
are not in.

- **Lead with the system, not the screens.** Tokens, the component contract, the seven
  states, the gate. `evidence.md` §2 has the translation.
- **Show them a thing that saves them work.** The state matrix. The audit in pre-commit.
  The fact that dark mode is a re-point, not a fork.
- **Answer "what happens when I need a component you did not build" before they ask it.**
  The invention protocol is the answer, and it reads as respect for their future.

### 1.4 The agency's creative director

Two questions, not one, and the second is the one that gets missed. *Is it good* is about
judgement. *Is it ours* is about whether the work belongs in this studio's body of work —
and a junior who only answers the first reads as competent but generic.

- **Lead with the premise.** One sentence naming the argument the work makes. A director
  can tell inside ten seconds whether a premise is interesting, and everything else in the
  deck is evaluated as evidence for it.
- **Show what you rejected.** The rejected option is the whole demonstration of judgement.
  A decision with no alternative reads as a first idea kept.
- **Bring the weakness yourself** (§8). This is the single strongest move available to a
  junior in a senior room, and it costs nothing.
- **Do not out-argue them on taste.** `objection-handling.md` §9.

---

## 2. The mixed room

The default and the hardest: a decision-maker, a marketing lead, a developer and your own
creative director, in one call, with forty minutes.

**The rule: address the person who can say no, and give everyone else one slide that is
obviously theirs.**

Not because the others matter less — because a deck that tries to satisfy four audiences
equally satisfies none, and the person who can say no is the one whose unanswered question
stalls the project. Everyone else needs to see that their question was *taken seriously*,
which one well-aimed slide accomplishes.

| Move | How |
|---|---|
| **Sequence for the decision-maker** | Outcome, decisions, cost, ask. That is the spine |
| **Give the developer one slide** | The system slide, presented in thirty seconds with a sentence directed at them by name: "Priya, this is the part you will live with" |
| **Give the marketing lead one slide** | The conversion path, same treatment |
| **Give your creative director nothing** | They are not the audience in a client room. Brief them beforehand. Presenting *at* your own CD in front of a client is how a review turns into an internal argument the client watches |
| **Park depth** | "There is a longer version of that for you and me, Priya — can I send it after?" This is not a dodge; it protects everyone else's forty minutes and it is heard as competence |

**The seating rule, which is really a scheduling rule.** If two people in the room have
genuinely opposed interests — a marketing lead who wants six things above the fold and a
developer who has to build them — you have a pre-meeting to run, not a presentation. Find
that out by asking each of them one question beforehand.

---

## 3. Deck structures for the five situations

Each structure below is a sequence of slide *jobs*, not slide titles.
`scripts/build_presentation.py` implements the client, team and creative-director orderings;
these are what it is implementing and why.

### 3.1 First concept presentation

The riskiest meeting. Nobody has seen anything, so the room's expectations are unmanaged
and its reaction is unrehearsed.

| # | Job | Why here |
|---|---|---|
| 1 | The problem, in their words | Earns the right to show anything. Also proves you listened, which is most of trust |
| 2 | What we learned that changed our approach | The pivot from brief to concept. If nothing changed, you did not research |
| 3 | **The idea, in one sentence** | Say it before showing it. A room that reads a screen before hearing the idea invents its own |
| 4 | The idea, on screen — one flagship view | One. Not three directions |
| 5 | Three decisions that produced it | Constraint → options → choice → consequence |
| 6 | What it does not do yet | Scope, stated now, before it is assumed |
| 7 | Open questions | Where their preference genuinely decides |
| 8 | The ask | "Do we develop this direction?" |

**Do not present three directions.** It feels generous and it is an abdication: you are
asking a client to do design selection, which they cannot do, and you are signalling that
you have no judgement about which is right. Present one, with the two you rejected named as
rejected, with reasons. If the client relationship genuinely requires options, present one
recommendation and two clearly-labelled alternates — never three peers.

### 3.2 Iteration review

The room has seen it before. Their attention is on **what changed**, and every second spent
re-showing what did not change is a second you lose.

| # | Job |
|---|---|
| 1 | What you asked for last time — their list, read back verbatim |
| 2 | What we changed, item by item, with the item they asked for beside it |
| 3 | What we did not change, and why — **this is the slide** |
| 4 | What changed that you did not ask for, and why |
| 5 | Open questions and the ask |

Slide 3 is the one people skip, and it is the one that decides whether the next round is
productive. An unaddressed request that goes unmentioned is heard as "they ignored me", and
the same request comes back louder. Naming it — "we did not do this one, here is the
constraint that stopped us, here is what we did instead" — converts a grievance into a
decision.

### 3.3 Final sign-off

The purpose is a decision, not a demonstration. Structure everything toward the signature.

| # | Job |
|---|---|
| 1 | What we agreed, and what we built — side by side |
| 2 | Everything that changed since the last review, with who asked |
| 3 | The evidence: performance, accessibility, browsers, the system |
| 4 | Known issues, with owners and dates |
| 5 | What happens after sign-off — deploy, handover, support, what costs extra |
| 6 | **The specific ask: "are we approved to launch on the 6th?"** |

**Post-sign-off scope must be named in the room.** Not as a threat — as a service. "After
today, changes go into phase two and I will quote them. That is not me being difficult, it
is so that the launch date holds." Saying it out loud, once, in front of everyone, is worth
more than the same sentence in the contract.

### 3.4 Redesigning something the client is attached to

The most delicate presentation in this file, and the one where good work most often loses.
Someone in that room made the old thing, or paid for it, or defended it internally, or
chose the colour personally. Every criticism of it is a criticism of them, whether or not
you mean it that way — and if the founder made it themselves, the old site is not a design
artifact, it is a story about starting the company.

**The rule: the old design was correct for its constraints. The constraints changed.**

This is not diplomacy, it is almost always true. The old site was built when the company
had four services rather than eleven, when 20% of traffic was mobile rather than 68%, when
there was no booking system to integrate. Say that, and mean it, and the room stops
defending and starts comparing.

| Do | Do not |
|---|---|
| "The old site was built for a business that took bookings by phone. That is the thing that changed" | "The old site is dated" |
| Name one thing the old site did well and **keep it** — visibly, deliberately, with credit | Present a clean slate. A total replacement says everything before was worthless |
| Show before/after at the same width, same content, same state (§6) | Flatter the before by cropping it, ageing it, or screenshotting it on a broken viewport |
| Attribute changes to evidence: "68% of sessions are on a phone" | Attribute changes to taste: "it needed modernising" |
| Let them tell you what they are attached to — ask, early, "is there anything here you would be sad to lose?" | Discover it by removing it |
| Keep the thing they are attached to if it is not actively harmful | Win an argument about the logo on day one |

**The attachment question, asked in the kickoff, saves the presentation.** People will tell
you. "My wife took that photograph." "That tagline was my father's." Then either keep it or
raise it deliberately with a plan — and raising it yourself, early, is the entire difference
between a conversation and an ambush.

### 3.5 Internal walkthrough for the team who will extend the work

Different job: you are not seeking approval, you are transferring a model. The failure mode
is the team politely agreeing and then quietly rebuilding it their way.

| # | Job |
|---|---|
| 1 | How it is put together — layers, tokens, the component contract |
| 2 | The decisions that are load-bearing, and what breaks if they are reversed |
| 3 | The decisions that are **not** load-bearing — say which, explicitly |
| 4 | The gates, run live: `audit_design.py`, `perf_audit.py` |
| 5 | Known debt, as tickets with owners |
| 6 | Where to start, and who to ask |

Slide 3 is what makes the rest credible. A walkthrough where everything is sacred gets
ignored wholesale, because a developer who cannot tell a deliberate constraint from an
accident treats all of it as an accident.

---

## 4. The opening

**"Here's what we made" is the weakest possible opening**, for three mechanical reasons:

1. **It invites evaluation before context.** The room starts judging the artifact with none
   of the constraints that produced it, and first impressions are load-bearing — you do not
   get a second one.
2. **It makes you the subject.** "What we made" is about you. The work is about them.
3. **It has no shape.** Nothing follows from it, so the next sentence is usually a feature
   list, and a feature list is the format in which nothing is remembered.

Open with one of these instead:

| Opening | Sounds like | Use when |
|---|---|---|
| **The problem restated** | "You told us the phone eats your mornings — forty bookings a week, most of them by voice. Everything here is downstream of that" | Almost always. It is the default for a reason |
| **The number that decided everything** | "Median session on your current site is forty-one seconds. That single number is why this page looks the way it does" | There is a genuinely decisive number |
| **The constraint you accepted** | "We had a hundred kilobytes for fonts and no type licence. Here is what we did with that" | A creative director, who reads constraint work as craft |
| **The thing that changed since last time** | "Three things changed since the last review, and one of them changed the layout" | Iteration reviews |
| **The question the meeting has to answer** | "By the end of this call I need a yes or a no on the booking flow, because the build starts Monday" | Sign-off, and any meeting at risk of wandering |

Then, in the second minute: **say what you are going to ask for.** A room that knows the
destination listens differently — it evaluates each decision against the decision it is
being asked to make, rather than wondering where this is going.

---

## 5. Framing a decision

The whole method, in one shape. Every non-obvious choice in the deck gets it.

> **Constraint → Options considered → Choice → Consequence → Evidence**

| Part | What it does in the room | Failure if missing |
|---|---|---|
| **Constraint** | Establishes that something other than your preference forced this | Without it, it is taste, and taste loses to seniority |
| **Options** | Demonstrates judgement. This is the part that makes a junior read as senior | It reads as the first idea, kept |
| **Choice** | The decision, in one sentence, no hedging | Hedging is heard as "not decided yet", which invites the room to decide for you |
| **Consequence** | Names the cost before they find it | A cost they discover is a flaw; a cost you name is a tradeoff |
| **Evidence** | Converts assertion into fact | Without it, say so — "that one is judgement" — rather than implying one |

### 5.1 Worked conversions

| Flat statement | In the shape |
|---|---|
| "We went with a single-column form." | "Two thirds of bookings start on a phone. We could have done a two-column desktop layout — it scans faster on a big monitor, and it doubles the states we have to design and test. We chose one column at every width. The desktop form is taller and a laptop user scrolls once more. We took that trade because the phone is where the bookings are." |
| "We used a lot of white space." | "Median session is forty-one seconds, so the page gets one idea per screen. The alternative was fitting the services list above the fold, which we tried — it pushed the booking button below it. We optimised for scanning over density. The cost is more scrolling for someone who already knows what they want." |
| "The buttons are orange." | "The accent is used for exactly one thing: the next action. It appears three times on the page. Making the newsletter sign-up orange as well was the obvious request, and we turned it down, because the moment two things are orange, neither one means 'this is the thing to press'." |
| "We removed the carousel." | "The carousel had five slides and the analytics show 2% of visitors ever saw slide two. We could have kept it and fixed the timing. We replaced it with the one message that was on slide one. The cost is that four teams who each had a slide now share one message, and that is a conversation we should have today." |

Two properties every conversion has. **The constraint is external** — analytics, a budget, a
device, their own words — never "it felt cluttered". And **the cost is real** — if you
cannot name what the choice cost, either you have not understood the decision or there was
never a real alternative, and in the second case it was not a decision worth presenting.

### 5.2 The decision nobody asked about

Some decisions are load-bearing and invisible. Present them anyway, briefly, in a list
rather than a slide each: they are the evidence that the parts nobody is looking at were
also decided. Three sentences buys the room's trust in the ninety percent of the work they
will never inspect.

---

## 6. Before and after, done honestly

Before/after is the most persuasive slide in design and the easiest to cheat, which is why a
room that has been cheated once discounts every comparison you ever show it again.

**The trap: flattering the before.** Usually not deliberate. You screenshot the old site on
a narrow window, with the cookie banner up, on a page with three items when the new one has
twelve, at a moment when the hero image had not loaded.

| Rule | Why |
|---|---|
| **Same viewport width, same device frame** | A different width is a different design. This is the one people break most |
| **Same content, same state** | Real content both sides, or placeholder both sides. Never twelve real items against three lorem ones |
| **Same scroll position, or show the full page both sides** | A cropped before is an argument, not a comparison |
| **Dismiss the cookie banner on both, or neither** | |
| **Label what changed in one sentence** | Otherwise the room reads whatever it notices first, which is usually the colour |
| **Show a before that you would defend** | If the old design is genuinely fine in a place, say so. It costs nothing and it buys the rest |

**The honest crop rule:** you may crop to the region under discussion, provided you crop
both sides identically and say you cropped. "This is the top 900 pixels of both, at 1280
wide" takes two seconds and removes the entire category of objection.

**When not to show before/after at all:** when the client made the before. Then show the
after and talk about the constraints that changed (§3.4). Putting someone's own work on a
screen next to yours, labelled "before", is a public comparison of you and them, and you
will win the slide and lose the room.

---

## 7. Showing the work

A process slide earns its place when it **changes what the room believes about the outcome**.
Otherwise it is you asking for credit for effort, and the room can tell.

| Process slide | Earns its place? | Why |
|---|---|---|
| "We looked at 40 competitors" as a wall of logos | No | Proves activity, not insight. Unless one of them changed a decision — then show that one |
| The one wireframe that got rejected, and the reason | **Yes** | It explains the current design's shape, and demonstrates judgement |
| Your Figma file, zoomed out, with 200 frames | No | Reads as "look how hard this was". A client hears "look how much of my money went into things I will not receive" |
| A user quote that overturned your assumption | **Yes** | It is evidence, and it transfers the decision from you to a user |
| The full sitemap on one slide | Only if structure is the decision | Otherwise it is a reference document, and reference documents go in the appendix |
| "Here's our process" — five arrows in a row | Never | It is about your agency. Nobody has ever bought anything because of a five-arrow diagram |

**The test:** delete the slide. If the next slide is now harder to believe, keep it. If the
deck just got shorter, it was self-indulgent.

**Where process really belongs:** inside a decision, as the options line. "We tried three
versions of this list; the one that worked put the turnaround time first" is a process
slide's entire value in one sentence, positioned where it does work.

---

## 8. The parts you are not happy with

**Raise them yourself, early, with a plan.** This is the highest-leverage habit in this file
and the most counter-intuitive, so here is the mechanism rather than the advice.

A room is doing two things at once: evaluating the work, and calibrating how much to trust
your evaluation of the work. When you volunteer a weakness, the second process resolves in
your favour — you are visibly the person with the most accurate picture of the work in the
room, which is exactly the person whose judgement about the *rest* of it should be trusted.
When a reviewer finds it first, the second process resolves the other way, and every
remaining decision is re-examined as a possible oversight.

| Same fact, two framings | How it lands |
|---|---|
| "The error state on the booking form is not designed yet. It is on the list for Thursday, and here is the state it will use" | A managed project |
| (reviewer finds it) "What happens if the submit fails?" … "Ah — we have not done that yet" | An unmanaged project, and now they are looking for more |

**How to raise it, in four beats:** name it plainly, say why it is like that, say what it
costs right now, say when it is fixed and who owns it. No apology — an apology invites
reassurance, which wastes the room's time and makes the item bigger than it is.

**What not to raise.** Things that are not actually problems ("the kerning on the footer is
not perfect") — raising those is fishing for reassurance and it spends credibility on
nothing. Raise items a competent reviewer would find, not items only you can see.

---

## 9. The close, and the ask

**A presentation without a specific ask gets a vague answer.** "Let us know what you think"
produces "looks great, just a few thoughts" — which is not approval, cannot be built on, and
guarantees a second meeting.

The close has four parts and takes ninety seconds:

1. **What we decided together today.** Two or three sentences. This is the sentence they
   will repeat to whoever was not there, so make it the sentence you want repeated.
2. **What is still open, and who owns it** — each with a date and a default: "we will
   proceed with A unless we hear otherwise by Friday". That sentence converts silence into a
   decision instead of a delay.
3. **The ask, named as a specific action.** Not "thoughts?". One of: "Are we approved to
   build this?" · "Can you confirm the launch date?" · "Which of the two do you prefer?" ·
   "Who signs this off, and can we get them on a call this week?"
4. **Then stop talking.** The pause is the ask. Filling it with more explanation reopens
   everything you just closed, and the person who was about to say yes now has a new thing
   to consider.

Immediately afterwards, write `assets/MEETING_RECORD.md` and send it the same day. What was
decided in the room is a deliverable, and it is the one everyone forgets — which is why six
weeks later the conversation about what was agreed is an argument rather than a link.
