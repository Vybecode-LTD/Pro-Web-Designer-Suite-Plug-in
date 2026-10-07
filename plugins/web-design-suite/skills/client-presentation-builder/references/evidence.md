# Evidence

Turning the suite's machine output into things a non-technical room finds persuasive —
without overclaiming, because one number you cannot defend costs you every number you can.

## Contents

1. The rule about numbers
2. The translation table
3. Accessibility, worded honestly
4. Performance, worded honestly
5. Screenshots and visual comparison
6. When to show code
7. "Can you just try it in blue?"

---

## 1. The rule about numbers

**A number you cannot defend is worse than no number.** The moment you say "it's 40%
faster" and someone asks "than what, measured how?", you have converted a persuasive claim
into a credibility problem — and the room now applies the same doubt to the four claims you
*could* have defended.

Three rules, and they are the whole of this section:

**1. Every number needs its comparison.** A figure alone is noise. "412 KB" means nothing;
"412 KB against the 600 KB budget we set in June, which is what a 2.5-second load on a
mid-range phone allows" means something and is unarguable because the arithmetic is visible.

| Bare | With its comparison |
|---|---|
| "The page is 412 KB" | "412 KB against the 600 KB we budgeted" |
| "LCP is 1.9 seconds" | "1.9 seconds where anything under 2.5 counts as good, on a throttled mid-range phone" |
| "Zero audit violations" | "Zero — meaning every colour and every spacing value on the site comes from one file" |
| "Three accessibility issues" | "Three, all on one form, all fixed by Thursday — down from the forty-one the old site has today" |

**2. Say which thing you measured.** Lab or field, build or source, one page or the whole
site, throttled or not. The honest version of a lab number is *"on the build we are
shipping, on a throttled connection, on my machine"* — it is a regression detector against
itself, not a prediction of what any individual user experiences.

**3. Never present a lab metric as a user-experience guarantee.** "It loads in 1.9 seconds"
is a claim about a measurement. "Your customers will see it in 1.9 seconds" is a claim about
the world, and the first time someone's phone takes six seconds on hotel wifi, you said it.
The defensible form: *"in our measurements on a mid-range phone on 4G it renders in under
two seconds, and we have a check in the build that stops it regressing."* The second clause
is the durable part and the part clients actually value.

**Where the numbers come from.** `scripts/build_presentation.py` reads every figure out of
the JSON itself and records the file and the JSON path beside it in the deck's provenance
block. Nothing is typed from memory, and when a number is challenged you can open the
source in one keystroke — which is most of the argument.

---

## 2. The translation table

What each artifact is, what it actually proves, and the sentence to say to someone who does
not care what a token is. **The right-hand column is the deliverable**; the artifact is
only the receipt.

| Artifact | What it proves | Say this |
|---|---|---|
| `audit_design.py` clean | No hardcoded values; every value resolves through the token layer | "Every value on this site comes from the design system. A brand change is one file, not a month" |
| `audit_design.py` with a baseline | The debt is frozen and cannot grow | "There is old code we have not converted. It is written down, it cannot get worse, and we pay it down per area" |
| A **component state matrix** | Every state of every component has been designed, not defaulted | "Here is every state of every component — loading, empty, error, disabled. Nothing on this site is undesigned, including the parts users only see on a bad day" |
| The **seven states** on a component | Someone thought about the failure cases | "This is what the form looks like when the network drops. Most sites find that out from a customer" |
| `perf_audit.py` within budget | The page weight is inside a number agreed before the build | "It weighs `<total>` against a budget of `<budget>` agreed before the build, and the build fails if someone makes it heavier" — the figures from `perf.json`; a byte count is never a load time, which only `measure_vitals.mjs` can give |
| A **performance budget file** | The number was derived, not wished for | "The budget is two and a half seconds on a mid-range Android on slow 4G. Everything else is arithmetic from that" |
| `measure_vitals.mjs` output | Real browser timings across runs | "Measured in a real browser, five runs, median reported — not a single lucky load" |
| An **axe-core / a11y report** | An automated WCAG pass, plus whatever you tested by hand | §3 — this one has to be worded carefully |
| **Measured contrast** | The colour decisions are not preferences | "Every text colour was measured, not judged. The muted grey clears the legibility floor at `<ratio>` to 1" — the ratio from `check_roles.py`, for the pair you name |
| **Dark theme as a token re-point** | The system layer is real, not decorative | "Dark mode is `<N>` re-pointed tokens in one file, because no component knows what colour it is" — count the dark block in `tokens.css` before you say the number |
| `DESIGN_DECISIONS.md` | The reasoning survives the team | "When you hire a developer in a year, the reasons are in the repo. They will not 'fix' something that was deliberate" |
| **Generated documentation** | The docs cannot drift from the code | "The documentation is generated from the code, so it cannot go stale — the usual failure with a style guide" |
| The **critique gate's defence sheet** | You have already run the hostile review | (Never shown to a client. It is the prep, not the deliverable) |

### 2.1 Three rules for using the table

**Translate the consequence, not the mechanism.** Nobody outside the room cares that
`--gap-related` exists. They care that the site will still look right in two years when
somebody else has been editing it.

**One artifact, one sentence, then stop.** The instinct after building something rigorous is
to explain the rigour. The rigour is why they should believe the sentence; it is not the
sentence. If they want the mechanism they will ask, and then you have a genuinely interested
audience instead of a patient one.

**Do not show a clean report as the evidence.** A screenshot of a terminal printing "clean"
is meaningless to a client and slightly insulting to a developer, who will assume it was
cherry-picked. Say the sentence; offer the file.

### 2.2 From JSON to a sentence, worked

The translation is mechanical once you see it. Take the raw value, attach its comparison,
then state the consequence to *them* — and drop the tool's name unless someone asks.

```json
// perf.json
"ledger": { "bytes": { "total": 412331, "image": 180204, "font": 41100 } },
"budget": { "bytes": { "total": 600000 } }
```

| Stage | What you have |
|---|---|
| The raw value | `ledger.bytes.total` = 412331 |
| With its unit | "412 KB" |
| With its comparison | "412 KB against the 600 KB budget — about 69% of it" |
| With its consequence | "It is comfortably inside the weight we budgeted for a two-second load on a mid-range phone, which leaves room for the photography in phase two" |

That last row is the sentence you say. The three above it are what you say if someone asks
where it came from — which is why the deck keeps them: `build_presentation.py` records the
file and the JSON path beside every figure it renders.

```json
// a11y.json (axe-core)
"violations": [ { "id": "label", "impact": "critical", "nodes": [ … ] } ]
```

| Stage | What you have |
|---|---|
| The raw value | one violation, `critical`, one node |
| With its comparison | "one, down from the forty-one the current site has" |
| With its consequence | "One field on the booking form has no label, which means a screen reader announces it as 'edit text' with no clue what to type. It is fixed Thursday" |

**The tell that you have translated properly:** the sentence contains no tool name, no
acronym the room has not already used, and one number. If it contains three numbers, you
have read the report aloud rather than translated it, and the room will remember none of
them.

---

## 3. Accessibility, worded honestly

The one place in the deck where overclaiming can be disproved by a single user, and where
the wrong wording can create a legal exposure for your client that they did not know they
were accepting.

**Automated tools fully decide 7 of the 55 WCAG 2.2 A and AA success criteria, and part of 31 more** (`a11y-audit-runner/references/automation-coverage.md` §3). Measured, the coverage is a range, and the deck cites it as one: in the UK government's 2017 test the best single tool found 41% of 143 planted barriers, and Deque's 2021 study puts automation at 57% of issues by volume. "Roughly a third" is not a figure either study gives. They cannot judge
whether alt text is *accurate*, whether a heading order matches the *meaning*, whether a
custom control is operable in a real screen reader, or whether an error message is
*comprehensible*. A green axe run means "no machine-detectable failures", which is a real
and useful thing and is not the same as "accessible".

| Never say | Say instead |
|---|---|
| "The site is fully accessible" | "The site passes an automated WCAG 2.2 AA check and we have tested it by keyboard by hand" |
| "It's WCAG compliant" | "It meets WCAG 2.2 AA on the criteria we can test, which is most but not all of them" |
| "It's screen-reader friendly" | "We tested the booking flow in VoiceOver. We have not tested every page in every reader" |
| "It's legally compliant" | "This is a technical standard, not legal advice. If you need a compliance statement, you need an audit by a specialist — I can recommend one" |
| "We fixed all the accessibility issues" | "We fixed everything the tools found and everything the keyboard pass found. A user test with an assistive-technology user is the next step and it is not in this phase" |

**The sentence that works with a nervous client**, and the reason it works: *"Accessibility
is not a checkbox, it is a floor we designed to from the start. Every colour was measured
rather than judged, every interactive element works by keyboard, and every form field has a
real label. The automated check is clean. What I cannot tell you from an automated check is
whether it is genuinely pleasant to use with a screen reader — that takes a user, and I would
recommend budgeting for it."*

That closes with honesty and an upsell, and the honesty is what makes the upsell land.

---

## 4. Performance, worded honestly

| Never say | Say instead |
|---|---|
| "The site loads in 1.2 seconds" | "In our tests on a mid-range phone on 4G, the main content appears in about 1.2 seconds" |
| "It scores 100 on Lighthouse" | "It is inside every budget we set. The score is a lab number on one machine; the number that matters is what your actual visitors experience, and we will watch that after launch" |
| "It's 40% faster" | "The old homepage was 3.4 MB, this one is 412 KB — about eight times lighter. What that means in seconds is `measure_vitals.mjs`'s median on a mid-range phone, which we quote; arithmetic from bytes is not a timing" |
| "It's optimised" | "There is a check in the build that fails if a page goes over its weight budget, so it stays fast after we leave" |

**The durable claim is the gate, not the number.** Any agency can ship one fast page. The
thing worth paying for is that it is still fast in eight months after four people have added
things — and that is a claim about a pre-commit hook, which is verifiable, rather than about
a measurement, which decays.

**When the numbers are bad.** Say so, in order: what it is, why, what it costs, when it is
fixed. "The gallery page is over budget — 1.1 MB against 600 KB — because the client's image
library is uncompressed originals. Fixing it is a batch conversion and half a day, and it is
in phase two." A bad number you present is a project being managed. A bad number they find
is a project that is not.

---

## 5. Screenshots and visual comparison

| Question | Answer | Why |
|---|---|---|
| **What size?** | The width the decision was made at. One screen per slide, as large as the slide allows | A design shown at 40% is a design nobody can evaluate, and the room will evaluate it anyway |
| **Device frame?** | A plain frame for mobile, none for desktop | A phone frame communicates "this is a phone" instantly. A laptop mockup on a beach communicates that you had time to spare |
| **Real content?** | Always, or say it is not | Lorem ipsum in a client presentation says the copy problem has not been solved. Longest and shortest real cases beat average ones |
| **How many?** | As few as make the argument | A grid of nine thumbnails is a contact sheet. Nobody reads a contact sheet, they scan it and form an impression you did not choose |
| **Annotated?** | One annotation per screen, maximum | Two annotations means the eye chooses, and it will choose the wrong one |
| **Scroll?** | Show the fold line explicitly when the fold is the decision | Otherwise the room debates the fold for ten minutes with no shared definition of where it is |

**The honest-crop rule.** Crop freely to the region under discussion — *provided* the crop
is identical on both sides of a comparison and you say what you cropped. "This is the top 900
pixels of both, at 1280 wide." Two seconds, and it removes an entire category of objection
before it forms.

**Retina exports are a trap in a deck.** A 3× export of a full page can be 4 MB; a deck of
twelve is 50 MB and will not go through an email gateway, and the meeting starts with you
apologising for a download. Export at the size you are showing.
`scripts/build_presentation.py` inlines the images so the deck works with no network — which
makes the file size entirely your responsibility.

---

## 6. When to show code

**Rarely.** Almost never to a client, occasionally to a client's developer, sometimes to a
creative director who came up through the front end.

It buys exactly one thing: proof that the thing you claimed in English is literally true.
That is worth spending when the claim is the load-bearing one and it sounds too good.

| Situation | Show | Why it lands |
|---|---|---|
| "A rebrand is one file" | Eight lines of the token file, and the sentence "these are the only colours that exist" | Makes an abstract claim concrete in four seconds |
| "Dark mode is a re-point" | The theme block, with the observation that no component name appears in it | The absence is the proof, and it is visible even to a non-developer |
| A developer asks how a component is themed | The component's socket block — its Tier-3 custom properties | This is the API they will use. Nothing else answers it as fast |
| Anything else | Nothing | Code on screen shifts the room into evaluating code, and everyone who cannot read it disengages |

**Rules when you do.** Under twelve lines. Syntax-highlighted and large enough to read from
a laptop on a call. Say what it proves *before* you show it, so nobody has to parse it to
find the point. Never scroll a code block in front of a room.

---

## 7. "Can you just try it in blue?"

The most common request in design, and the answer depends entirely on which of two very
different things is being asked.

### 7.1 Tell the two apart

| It is a preference you should simply accommodate | It is a change that breaks the system |
|---|---|
| Changes a value the system already parameterises | Requires a new rule, a new component, or an exception |
| Costs minutes | Costs a re-derivation, a re-test, or a new thing to maintain |
| No downstream consequence | Breaks contrast, breaks a state, breaks a pattern used in nine places |
| "Make the accent a bit warmer" | "Make this one button a different shape from all the other buttons" |
| "Use the other photo" | "Add a second navigation bar under the first" |
| "Shorter headline" | "Fit six more things above the fold" |

### 7.2 If it is a preference, just do it

Say yes quickly and without visible reluctance. It costs you nothing and it buys something
real: **the credibility to say no to the next one.** A designer who resists every change
gets ignored on all of them; a designer who says yes eight times and then says "this one I
would push back on" is listened to on the ninth, because the contrast is the signal.

Where it is genuinely free, offer it before it is asked: "the accent is one value — if you
want to see it warmer or cooler, that is a two-minute change and I can show you both."

### 7.3 If it breaks the system, explain the mechanism, not the principle

The losing move is defending the *system*. Nobody outside the room owes your architecture
any loyalty, and "it breaks the design system" sounds like your convenience being ranked
above their request.

The winning move is naming the **consequence to them**, then offering a route to what they
actually want.

| Losing | Winning |
|---|---|
| "That breaks the design system" | "I can do that — it means this button stops matching the other nine, so we either change one and it looks like a mistake, or we change all ten. Happy to do either, they are different sizes of job" |
| "That colour doesn't meet contrast" | "That blue on white measures 3.1 to 1 and text needs 4.5. It is legible on your monitor and it is not on a phone in daylight. Here is the same blue two steps darker, which measures 4.8 and reads as the same colour" |
| "We designed it that way for a reason" | "The reason it is like that is [the constraint]. If that constraint has changed, the decision should change too — has it?" |
| "That's not best practice" | "The risk is [specific consequence]. If you are comfortable with that, I will build it" |

**Three properties of the winning column.** It says yes first, so the conversation is about
cost rather than permission. It states a consequence, which is checkable, instead of a
principle, which is arguable. And it leaves the decision with them — which is where it
belongs, because it is their site, and a client who is told "no" remembers it longer than a
client who is told what it costs and chooses.

**When it is genuinely dangerous**, objection-handling.md §5 has the rule. A lawful choice
that only costs them, you note and build. An accessibility failure (a contrast failure, a
broken tap target), you hold: build the version that meets their goal and the standard, and
put the risk of the other in writing. "I've built the button at the nearest shade that
meets the accessibility standard. The exact one you asked for is below it, which is why I
haven't built it: if it is ever changed to that, an accessibility complaint will land
there." Anything deceptive or unlawful, you
decline and offer the honest version, and a question of law goes to their lawyer. Your job
is to make sure the decision was informed, not to win it.
