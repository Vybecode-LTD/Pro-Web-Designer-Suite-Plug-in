# The Documentation Model

What design system documentation must contain, in what order, and which half of it a machine may write.

This file is the specification `build_docs.py` implements. Read it before you decide a page needs a section the generator does not produce — and before you decide it does not need one it does.

## Contents

1. [The one rule](#1-the-one-rule)
2. [The five readers](#2-the-five-readers)
3. [The page order that falls out](#3-the-page-order-that-falls-out)
4. [The token page](#4-the-token-page)
5. [The component page](#5-the-component-page)
6. [The pattern page](#6-the-pattern-page)
7. [The principles page](#7-the-principles-page)
8. [What must never be generated](#8-what-must-never-be-generated)
9. [The two-file rule](#9-the-two-file-rule)
10. [Getting the why out of a busy person](#10-getting-the-why-out-of-a-busy-person)
11. [Versioning, deprecation and the changelog](#11-versioning-deprecation-and-the-changelog)
12. [Anti-patterns](#12-anti-patterns)

---

## 1. The one rule

**A documentation page is a list of answers. Write the questions first.**

Almost every bad design system site is organised around the *structure of the system* — a nav of Foundations, Components, Patterns, Resources — rather than around what anyone arriving actually wants. The structure is not wrong; it is just not an answer. Somebody landed on that page mid-task with a question, and the page opened with a paragraph about the philosophy of tokens.

So the method is: enumerate the questions people arrive with, sort them by frequency, and put the answer to the most frequent one above the fold. Everything in this file is that exercise, already done.

The four questions that account for most arrivals:

| Question | Frequency | Answered by |
|---|---|---|
| "What is the value of X?" | constant | the token table's resolved column |
| "How do I make this component do Y?" | constant | the socket table and the props table |
| "Am I allowed to do Z?" | frequent, high stakes | the *when not to use this* section |
| "Why is it like this?" | rare, decisive | the hand-written rationale |

The first two are generated and are the bulk of the page. The third and fourth are hand-written and are the reason anyone comes back.

---

## 2. The five readers

They want different things, they arrive by different routes, and only one of them is reading top to bottom.

### The developer USING a component

Arrives from an editor, mid-task, with a component already on screen that is 4px too wide. Wants: the socket table, one working example, and to leave. Will not read prose. Will copy the first code block they see, so the first code block must be correct and idiomatic — a wrong example is worse than a missing one because absences do not get pasted into production.

**Needs first:** the API tables. **Tolerance for philosophy:** zero.

### The developer CHANGING a component

Arrives asking "what breaks if I rename this?". Wants the blast radius: which sockets are consumed by what, which selectors re-point them, who else in the codebase reads them. This reader is why the socket table has a *consumed by* and a *re-pointed by* column, and why removing a socket is reported by `--check` as a breaking change rather than as a diff line.

**Needs first:** consumers and the deprecation path. **Failure mode:** ships a rename that silently no-ops every consumer's override, because a CSS custom property that nobody sets is not an error.

### The designer CHECKING a value

Arrives from a design tool asking "what is our card padding, actually?". Wants a number, at density 1, in both themes, without installing anything. Does not want `calc(var(--space-6) * var(--density))` — that is a true answer to a question they did not ask.

**Needs first:** the resolved value. **This is why** the token table prints `24px` beside the source expression rather than instead of it, and why fluid values print `64px … 144px` rather than a single number that is wrong at both ends.

### The newcomer LEARNING the system

Arrives on day two, from a link in an onboarding doc, with an hour. Wants a shape they can hold in their head: three tiers, one direction of flow, a closed scale, a proximity ladder. Will not remember eleven type steps and does not need to.

**Needs first:** the principles page, then the proximity ladder, then nothing else today. **Failure mode:** a site that opens with 205 tokens in a table, which teaches that the system is a list of values rather than a set of decisions.

### The reviewer VERIFYING a claim

Arrives sceptical, usually in a PR, asking "does this actually pass AA?". This is the reader who decides whether the documentation is an asset or a liability, because they are the one who will *act* on a number without re-deriving it.

**Needs first:** the measured ratio, and evidence it was measured rather than remembered. **This reader is the entire argument of this skill.** Give them a hand-typed 4.6:1 and they will ship a contrast failure through your documentation. Give them a generated column and the same review catches it.

---

## 3. The page order that falls out

Per page, top to bottom, in descending order of how often the section is the reason someone opened it:

| Page | Order |
|---|---|
| Overview | what this is → the four numbers (tokens, components, themes, open gaps) → prose intro → the gap list → the static-resolution limits → the source files |
| Token group | one-line role of the group → the hand-written *why* for this group → Tier 1 table → Tier 2 table → contrast |
| Component | what it is → anatomy → live examples → states → CSS API → props → keyboard → gaps → hand-written prose |
| Pattern | the problem → the solution → when it applies → when it does not → the components it composes |
| Principles | one sentence per law → the consequence of breaking it → where it is enforced |

Two deliberate choices in the component order that look wrong and are not:

**Examples before the API tables.** The reader using a component recognises their case visually in a second and never reads the table. The reader changing a component scrolls past the examples without cost. Optimise for the frequent reader.

**Hand-written prose last, not first.** It is the most valuable content on the page and it goes at the bottom, because it is the content people come back for deliberately rather than the content they arrived for. Putting the tradeoffs essay above the props table costs the frequent reader a scroll on every visit, forever.

---

## 4. The token page

One row per token. Every column is generated.

| Column | Content | Why it is there |
|---|---|---|
| Swatch | the resolved colour, composited if translucent | A hex code is not a colour anyone can see. |
| Name | the custom property, plus the source comment as a note | The comment is the only *why* that already exists in the token file. |
| Tier | 1, 2 or 3 | Tells a component author in one glance whether they may read it. |
| Source value | the declaration, verbatim | The `var()` chain is the relationship; deleting it hides the structure. |
| Resolved | the computed value, or a range, or "unresolved" and why | The designer's question, answered. |
| Per-theme columns | the value in each theme, or "same" | What re-points in dark mode is the single most misremembered fact in any system. |
| Density | the value at compact and spacious, when it scales | Proves Law 7 on the page rather than asserting it. |
| Read by | how many tokens and components reference it | Zero is a finding, not a number. |

Then, once per token group, the things a per-row table cannot carry:

- **Where it is legal to read this from.** Tier 1: `tokens.css` only. Tier 2: component CSS. Tier 3: that component's own file. This is Law 6 restated at the point of use, which is the only place anyone reads a law.
- **What re-points it in each theme**, with the selector. "`--fg-muted` becomes `--neutral-300` under `[data-theme="dark"]`" is a fact a developer needs twice a year and cannot find any other way.
- **Contrast, where relevant.** Every `--fg-*` role against every surface, in every theme, measured. Not asserted, not carried over from the last redesign, and not present at all for translucent roles — their ratio depends on what is behind them, and the honest answer is a refusal.

**The exception table belongs on this page.** `--space-section`, `--space-subsection`, `--space-block` and `--space-fluid-*` live in the `--space-*` namespace and are Tier 2. Every reader who has learned "`--space-*` is Tier 1" will get this wrong, so the page says it out loud rather than relying on the tier column being noticed.

---

## 5. The component page

This is the page that justifies the skill. Eight sections, seven of them generated.

### 5.1 What it is — one paragraph

Generated from the component's JSDoc when there is one, hand-written when there is not. One sentence on what it does, one on when it is the right choice. If it takes three paragraphs, the component does two jobs.

### 5.2 Anatomy — the parts

Every `.component__part` class, and what each one sets. This is the contract for anyone building a variant: parts are addressable, everything else is not. Extracted from the selectors, so it cannot list a part that was deleted.

### 5.3 Live examples — one per variant, size and renderable state

Rendered instances, styled by the component's actual stylesheet, not screenshots. A screenshot goes stale silently; a live instance changes when the CSS changes, which is the whole point.

States that are attributes (`disabled`, `loading`, `error`) render directly. States that are pseudo-classes (`hover`, `focus-visible`, `active`) are shown by mirroring each rule onto a `data-force-state` attribute at identical specificity — see `extraction.md` §7. Without that, a docs page can never show a focus ring, which is the state most worth showing.

### 5.4 States — all seven, including the absent ones

The table lists all seven states whether or not the component implements them, and marks the gaps. **Listing only what exists proves nothing**: a state that was never written produces no selector, no violation and no visible difference — it renders as `default`. A table showing `loading — no rule` is the only artefact that makes the absence visible.

Each row also carries what the state must *not* do, because that is where the bugs are: hover must compose over the variant rather than replace it; loading must not change the box; disabled must not read as the brand accent.

### 5.5 The CSS API — the Tier-3 socket table

The heart of the page, and already written in the source.

| Column | From |
|---|---|
| Property | the declaration on the component root |
| Default | its value, verbatim |
| Accepts | inferred from the default's kind — `<length>`, `<color>`, `<time> <easing-function>` |
| Resolves to | the computed value, per theme |
| Consumed by | which CSS properties read it. Empty is a finding: published API that does nothing. |
| Re-pointed by | which variant/size/state selectors change it |

Plus one line of policy the table cannot carry: **anything not in this table is private.** Adding a socket is routine; removing or renaming one is a breaking change with a deprecation path.

### 5.6 Props — the JavaScript API

Name, type, default, and the JSDoc. Extracted from the TS interface and the destructuring defaults, so the default column cannot disagree with the code — which the hand-maintained version always eventually does, usually in the direction of the value that *used* to be the default.

### 5.7 Keyboard and ARIA

Partly generated: the rendered element carries a contract (`<button>` is Enter/Space-activated and focusable; `<a href>` is Enter-activated), and that much is inferable and worth stating. Everything beyond the element's own contract — arrow-key roving focus, Escape-to-close, the `aria-expanded` relationship between a trigger and its panel — has to be written by hand, and the page says so explicitly rather than implying that a two-row table is the whole story.

State expressed as a real ARIA attribute is generated from the selectors: if the CSS styles `[aria-invalid="true"]`, the page can say the error state is carried by `aria-invalid`, and a reviewer can check that the component actually sets it.

### 5.8 Do / don't, and when not to use this

Hand-written. Always. See §8.

### 5.9 Related components

Hand-written, and worth the two minutes: "use `Link` when it navigates" prevents more bugs than any amount of prose about buttons.

---

## 6. The pattern page

A pattern is a composition of components that solves a recurring problem — an empty state, a destructive confirmation, a multi-step form. Patterns are the least documented and most re-invented part of every design system.

Nothing on a pattern page can be generated, because a pattern exists in nobody's source file. Its structure:

1. **The problem**, stated as the situation a user is in — not as the widget. "The user has filtered a list down to nothing", not "empty state component".
2. **The solution**, as a rendered composition with the markup.
3. **When it applies**, concretely enough to be checkable.
4. **When it does not**, with the alternative named.
5. **The components it composes**, linked, so the reader can get the API from there rather than having it duplicated here.

The one rule: **a pattern page never restates a component's API.** Link. A duplicated socket table is a second copy, and a second copy drifts by definition.

---

## 7. The principles page

The shortest page and the one that makes the rest legible. One entry per law: the law in a sentence, the consequence of breaking it, and where it is enforced.

The enforcement column is what separates this from a values statement. "Tokens or nothing — a hardcoded colour is a colour dark mode cannot re-point — enforced by `audit_design.py` L1" is a rule. The same sentence without the third clause is an aspiration, and every reader can tell the difference.

Keep it to the nine laws and the three tiers. A principles page that grows past two screens has become a second copy of the reference.

---

## 8. What must never be generated

This is the section to read twice.

| Never generated | Because |
|---|---|
| **Rationale** | Why `--bg-accent` is `--accent-600` and not the brand's `--accent-500` is a contrast decision taken by a person. The source shows the *what* — 600 — and cannot show the reasoning that white on 500 measures 3.56:1, which is legal above 24px and illegal on a 14px button label. |
| **Tradeoffs accepted** | "This component does not support a third level of nesting; we decided the layout that needs one is wrong." No parser will ever recover that. |
| **Deprecation reasons** | Deletion leaves no trace. The socket is simply gone, and `--check` will report it as removed — but only a human can say *what to use instead* and *why it went*. |
| **When NOT to use this** | The most valuable section of any component page, and structurally unreachable: it is about the cases the component does not handle, which by definition are not in its source. |
| **Content guidance** | "Button labels are verbs" is not in the CSS. |
| **Accessibility intent beyond the element** | The keyboard map for a composite widget is a design decision, not a fact about a stylesheet. |
| **Anything with a "should"** | A generator reports what is. The moment a sentence says what *ought* to be, a person wrote it, and the docs should show that it was a person. |

The point is not that generators are limited. It is that **the generatable content is the cheap half**, and a team that spends its documentation budget hand-maintaining props tables has none left for the half that only it can write. The generator exists to buy that time back.

A good test for any sentence in a docs site: *could this be wrong tomorrow without anyone noticing?* If yes, it should have been generated. If no — if it is a judgement, a reason, a boundary — it is exactly what a person should be writing.

---

## 9. The two-file rule

**Generated and hand-written content live in separate files. Always.**

The failure this prevents is specific and fatal. A docs page is generated with placeholder sections for prose. Someone fills them in. Three weeks later the generator runs and overwrites the file. The prose is gone, or worse, half of it survives inside a stale table. After that happens once, the team stops regenerating — and the docs go back to being hand-maintained, which is where they started, except now there is a script nobody runs.

The mechanism:

```
docs/
  prose/                       hand-written · never written to by any script
    overview.md
    principles.md
    tokens/color.md
    components/button.md
    components/button.example.html
    patterns/empty-states.md
  system.json                  generated · committed · the drift baseline
  site/                        generated · disposable · rebuilt every run
```

- Everything under `site/` is deleted and rewritten on every build. Nothing in it is ever edited.
- Nothing under `prose/` is ever opened for writing by a script. Not to reformat it, not to insert a marker, not once.
- The join happens at build time, by filename convention. `components/button.md` is appended to the button page; `tokens/color.md` is prepended to the colour group; `components/button.example.html` replaces the generated example markup for that one component.
- A prose file that matches nothing is reported (`orphan-doc`) rather than silently dropped, because a page that documents a deleted component is an instruction to use something that no longer exists.
- A component with no prose file is reported (`undocumented-component`), and its page says so in place of the missing section: *"Everything above is the what; the why is missing, and a parser cannot produce it."* An honest hole is better than a page that looks complete.

The include mechanism is filename convention rather than an include directive inside the generated file, and that is the whole trick. A directive would have to live in the generated file, which means a person would eventually edit the generated file, which is the thing the rule exists to prevent.

---

## 10. Getting the why out of a busy person

The hard part of this skill is not the parser. It is that the sections only a human can write are the sections a human has to be persuaded to write. Three things that work:

**Ask for the argument you lost, not for documentation.** "Why is `--bg-accent` 600 and not 500?" gets a two-sentence answer with a number in it. "Please document the colour tokens" gets nothing, for weeks.

**Write from the gap list.** Every entry in `gaps` is a question with a name attached: someone deliberately did not implement the loading state on the button, and that decision has a reason. Ask about the twelve gaps and you have twelve paragraphs of the highest-value content on the site.

**Take dictation from the code review.** The best *when not to use this* paragraphs already exist, as comments on pull requests, written in anger. Move them.

And one thing that does not work: a template with empty headings. Nobody fills in an empty heading. A generated page that says "the why is missing here, and here is what the code already shows" produces prose; a page with `## Rationale\n\nTODO` produces a TODO that outlives the component.

---

## 11. Versioning, deprecation and the changelog

Every design system eventually removes something, and removal is where documentation earns or loses its reputation. A socket that disappears without a page is a support ticket per consumer, forever.

### The rule

**Adding a Tier-3 socket is routine. Removing or renaming one is a breaking change.** Same for a prop, same for a variant value, same for a token anything outside `tokens.css` reads. The socket table is a published API precisely because it is documented; the moment it appears on a page, someone is allowed to depend on it.

That cuts both ways, and the useful direction is the one people forget: **a property you never documented is the only kind you may still rename.** Publishing a table has a cost. Do not publish private plumbing into it out of completeness.

### What a deprecation entry contains

Four things, all hand-written, because none of them survive in the source after the deletion lands:

| Field | Example |
|---|---|
| What is going | `--card-elevation` |
| What replaces it | `--card-shadow`, same accepted type |
| Why | "Named for a role that no longer exists after elevation became a shadow pair." |
| When it stops working | the release, not "soon" |

A deprecation with no replacement named is not a deprecation, it is an announcement of a problem. If there genuinely is no replacement, say *that*, explicitly — "there is no replacement; the pattern it supported was wrong" is a complete and useful answer, and readers stop searching for the successor that does not exist.

### The changelog is generated, the migration notes are not

`--check` already produces the list of what changed between two committed `system.json` files, in the right vocabulary: tokens added and removed, defaults moved, sockets deleted, contrast crossed. That list is the skeleton of a release note and costs nothing.

What it cannot produce is the sentence next to each line saying what to do about it. Take the generated diff, add one line per breaking entry, publish. The generated half keeps the list complete — which is the half that humans get wrong, because the change you forget to mention is always the one you did not notice you made.

---

## 12. Anti-patterns

| Pattern | Why it fails |
|---|---|
| A nav organised by the system's structure | Nobody arrives wanting "Foundations". They arrive wanting a number. |
| A component page with no *when not to use* | Leaves the reader's actual question unanswered while looking complete. |
| Prose and tables in one generated file | The next regeneration eats the prose, and the team stops regenerating. |
| A hand-maintained props table | Wrong within a sprint, and wrong in the direction of the previous default. |
| Screenshots of components | Stale silently and invisibly. Render live instances. |
| A single "Tokens" page with 205 rows | Teaches that the system is a list of values, not a set of decisions. Group them. |
| Listing only the states a component implements | Proves your code matches your code. The absent states are the finding. |
| Documenting a private custom property | It is now public API, and you have lost the right to rename it. |
| A contrast figure with no measurement behind it | The one number a reviewer will trust without re-deriving, which is why it is the one number that must be generated. |
| Restating a component's API on a pattern page | A second copy, which drifts by definition. |

---

## The three sentences to remember

1. **Write the questions first** — a page is a list of answers, ordered by how often each is the reason somebody opened it.
2. **The generatable half is the cheap half**; a team hand-maintaining props tables has no budget left for the rationale, the tradeoffs and the *when not to use this*, which is the only content it can write.
3. **Generated and hand-written content never share a file**, because the day a regeneration eats somebody's prose is the day the team stops regenerating.

Related: `references/extraction.md` (how the generated half is read out of the source), `references/drift-detection.md` (how both halves are kept honest), `references/token-contract.md` (the vocabulary).
