# Change Classification

Every kind of change you can make to a design system, with its severity and the reasoning. This is the file you open with a diff in the other window.

Semver was written for APIs, where "breaking" means a caller stops compiling. A design system has a second surface no compiler sees — **the rendered output** — and a consumer who changes nothing can still wake up to a different button. So the question is never "did a name disappear". It is:

> **Does a consumer's rendered output change in a way they did not ask for?**

Answer that and the version number falls out. Ask the API question instead and you will ship a re-point as a patch, which is the single most common way a design system loses its consumers' trust.

## Contents

1. [The three verdicts](#1-the-three-verdicts)
2. [Tier 1 — primitives](#2-tier-1--primitives)
3. [Tier 2 — roles](#3-tier-2--roles)
4. [Re-pointing a Tier-2 role: the argument](#4-re-pointing-a-tier-2-role-the-argument)
5. [Tier 3 — component sockets](#5-tier-3--component-sockets)
6. [Components, variants and states](#6-components-variants-and-states)
7. [DOM structure and class names](#7-dom-structure-and-class-names)
8. [Props](#8-props)
9. [System-wide: layers, themes, breakpoints](#9-system-wide-layers-themes-breakpoints)
10. [The hard cases](#10-the-hard-cases)
11. [The decision procedure](#11-the-decision-procedure)
12. [Every kind `diff_system.py` emits](#12-every-kind-diff_systempy-emits)

---

## 1. The three verdicts

| Verdict | The test | What the consumer must do |
|---|---|---|
| **major** | A name a consumer writes disappears, **or** rendered output moves without them asking | Read the guide. Run a codemod, look at a visual diff, or both. |
| **minor** | New surface. Nothing that existed resolves differently. | Nothing. Adopt it when they want it. |
| **patch** | Nothing a consumer can observe changed — comments, file layout, a re-source that resolves identically | Nothing, and nothing to read. |

Two rules that make this workable in practice:

- **Resolve before you judge.** `--pad-card: var(--space-6)` → `calc(var(--space-6) * var(--density))` looks like a re-point and resolves to the same 24px at density 1. That is a patch *and* a trap: it is only a patch if the two move in lockstep forever after. `diff_system.py` calls that `tier2-repointed-equal` and says so; you decide whether the lockstep claim is true.
- **Fallout is not a change.** Editing `--accent-600` makes `--elevation-focus` resolve differently. Nobody edited `--elevation-focus`. Listing it as its own breaking change turns a one-line edit into a six-item changelog that reads like six decisions. It is blast radius. Report it under its cause.

Below 1.0.0, semver promises nothing — `0.x.y` may break anything. Use these verdicts anyway. The discipline of deciding is the point, and on the day you ship 1.0.0 the habit already exists.

---

## 2. Tier 1 — primitives

Primitives are read by `tokens.css` and nothing else (Law 6). That *should* make them safe to change. It does not, because every role is a function of them.

| Change | Verdict | What a consumer sees | Auto-detect | Burden |
|---|---|---|---|---|
| Add a primitive (`--space-7`) | **minor** | Nothing. | yes | none |
| Remove a primitive | **major** | Every role downstream resolves to nothing — CSS drops the whole declaration, silently | yes | codemod, or a shim |
| Rename a primitive | **major** | Same as removal for anyone reading it directly, which under Law 6 should be nobody and never is | heuristic | codemod |
| **Change a primitive's value** | **major** | Everything downstream re-renders | yes | look at a visual diff |
| Change a breakpoint | **major** | Every layout switches at a different width. Nothing errors; the tablet view just arrives somewhere else | yes | review every breakpoint-dependent screen |
| Add a breakpoint | **minor** | Nothing until someone writes a query against it | yes | none |
| Add a step to a closed scale | **minor**, and suspicious | Nothing — but Law 3 says the scale is closed. A new step is usually a layout that should have been fixed | yes | none |

**Why a Tier-1 value change is major and not minor.** The instinct says "no API changed, so it is at most minor". Run it forward: you nudge `--neutral-500` two points darker to fix one placeholder. Fourteen roles resolve through it. Four of them are text roles. One of those crosses 4.5:1 *upward*, which is fine, and one crosses *downward* in dark mode, which is a WCAG failure you just shipped to three clients. No name moved. Nothing failed to compile. The output changed, unasked, everywhere. That is the definition.

**Adding a primitive is minor — but read it twice.** `--space-7` is minor by this table and wrong by Law 3. The version number is not the interesting part of that conversation.

---

## 3. Tier 2 — roles

Roles are the layer component CSS actually reads. They are the public API in the sense that matters.

| Change | Verdict | What a consumer sees | Auto-detect | Burden |
|---|---|---|---|---|
| Add a role | **minor** | Nothing. New word in the vocabulary | yes | none |
| Remove a role | **major** | `var(--gone)` drops its declaration. The element inherits, or falls back to the UA default | yes | codemod |
| Rename a role | **major** | Identical to removal, plus a replacement exists that they cannot guess | heuristic | codemod |
| **Re-point a role** | **major** | Same name, same call site, different pixels | yes | visual diff |
| Re-point a role to an identical value | **patch** | Nothing today. See the lockstep caveat in §1 | yes | none |
| Add a theme override to a role | **major**; **patch** if it resolves as before | Nothing in the default theme. In that theme the role stops following its root value, so its consumers render differently: a re-point there (§11 Q2) | yes | visual diff, in that theme |
| Change a theme override | **major** | Consumers in that theme render differently. Consumers in the other notice nothing — which is why this one reaches production | yes | visual diff, in that theme |
| Remove a theme override | **major** | The role silently falls back to its root value in that theme. Usually a dark-mode regression that light-mode review cannot see | yes | visual diff, in that theme |

**On rename detection.** No CSS file records that a rename happened; a rename is a removal and an addition that a human knows are related. `diff_system.py` pairs them when the declaration, the tier and the theme overrides all match, and labels the pairing a heuristic. Confirm it. Getting it right is the difference between a guide that says *"renamed to `--fg-faint`"* and one that says *"removed"* — which sends the reader hunting for a replacement the tool already knew about.

---

## 4. Re-pointing a Tier-2 role: the argument

This is the row people argue with, so here is the whole case.

**The objection.** "`--bg-accent` still exists. It still takes no arguments. Every consumer's CSS still parses, still passes the type checker, still lints clean. Nothing broke. That is a patch."

**The answer.** A design system's contract is not `--bg-accent exists`. Nobody writes `var(--bg-accent)` because they want a token to exist. They write it because they want *that colour* — the one they saw when they built the screen, checked against their copy, measured for contrast, and signed off with a client. The token is how they refer to the colour. Re-point it and you have changed the thing they were referring to while leaving the reference intact. That is not a patch. That is the most confusing possible shape of a breaking change, because the evidence of it is in the render and nowhere else.

Put it beside the API case:

| | Function API | Design token |
|---|---|---|
| The name | `formatDate()` | `--bg-accent` |
| The contract | the signature | **the resolved value** |
| Changing the body to return a different string | obviously breaking | — |
| Changing the value to a different colour | — | **the same thing** |

Nobody would call "`formatDate()` now returns a different format, same signature" a patch. Re-pointing a role is that change, in a language where the return value is a colour.

**The three counterarguments, answered:**

1. *"Roles exist precisely so we can re-point them."* Yes — that is what makes it **possible**, not what makes it **free**. The token layer's job is to make the change a one-line edit instead of a two-hundred-file one. It was never to make the change invisible. Cheap to perform and safe to ship are different properties.

2. *"It was a bug fix."* Sometimes true, and it is still major. See §10.1 — a fix to your system can be a regression in a consumer's product, and honesty about that is the whole game.

3. *"Our consumers will never notice."* If that is true, nothing was gained by the change either. A re-point nobody can see is a re-point nobody needed.

**The one genuine exception:** re-pointing a role that resolves to an identical value, where the new source is *definitionally* locked to the old one — `--pad-card: var(--space-6)` becoming `calc(var(--space-6) * var(--density))` at density 1. That is a refactor, and it is a patch. The moment the two sources can drift apart independently, it is a re-point wearing a refactor's clothes.

---

## 5. Tier 3 — component sockets

A component's custom properties are its public CSS API (`style-architecture.md` §7). Treat them exactly as you would props.

| Change | Verdict | What a consumer sees | Auto-detect | Burden |
|---|---|---|---|---|
| Add a socket | **minor** | Nothing, as long as the default reproduces today's rendering | yes | none |
| Remove a socket | **major** | Their override of it stops doing anything. Their CSS still parses; it simply has no effect | yes | codemod, or a shim |
| Rename a socket | **major** | Same | heuristic | codemod |
| **Change a socket's default** | **major** | Every consumer who did *not* override it renders differently — that is most of them, and they are the ones who never read the changelog | yes | visual diff |
| Change a default to a different source, same value | **patch** | Nothing | yes | none |
| Add a socket for something previously hardcoded | **minor** | Nothing, plus a new lever | yes | none |

**Adding a socket has one failure mode.** A socket whose default does *not* reproduce today's rendering is not an addition, it is a re-point announced as an addition. `extract_system.py` resolves defaults per theme; compare them.

**A socket nobody published is the only kind you may still rename.** If it has never appeared in docs, in a changelog or in an example, it is private and a rename is a patch. The moment it is documented it is API forever. This is the strongest argument for publishing your socket table deliberately rather than letting a generator publish every custom property you ever wrote.

---

## 6. Components, variants and states

| Change | Verdict | What a consumer sees | Auto-detect | Burden |
|---|---|---|---|---|
| Add a component | **minor** | Nothing | yes | none |
| Remove a component | **major** | An import that does not resolve, or a class that styles nothing | yes | manual |
| Rename a component | **major** | The import *and* every descendant selector and test query written against the old class | heuristic | partial codemod |
| Add a variant | **minor** | Nothing — `data-variant` values nobody passes yet | yes | none |
| **Remove a variant** | **major** | `data-variant="quiet"` is still legal HTML. It renders as the base variant, with no error anywhere | yes | manual |
| **Change a variant's appearance** | **major** | No API moved. The pixels did | yes | visual diff |
| Add a size | **minor** | Nothing | yes | none |
| Remove a size | **major** | Falls back to the default size, silently | yes | manual |
| Add a state | **minor**, review it | A state that rendered as `default` now renders as itself. Additive in API terms and *visible* — review it on the proof sheet | yes | visual diff |
| **Remove a state** | **major** | The state renders as `default`. No error, no warning, and a focus ring that is simply gone | yes | manual |

**Removing a variant is the worst failure shape in this table.** Removing a component throws. Removing a prop throws. Removing a variant does nothing at all — the attribute is valid, the selector no longer matches, and the element renders as the base variant. Nothing in the consumer's toolchain has an opinion. The only thing that catches it is a proof sheet (`component-state-matrix`) or a person. Deprecate variants with the same ceremony as tokens, and give them a longer window, because nothing will remind anyone.

**Adding a state is minor and still needs a look.** Nothing breaks, but a component that never had a `loading` style now has one, and it may be wrong. Minor in the changelog, a row on the proof sheet in review.

---

## 7. DOM structure and class names

The part of a design system that nobody remembers is API, until a consumer's stylesheet stops matching.

| Change | Verdict | What a consumer sees | Auto-detect | Burden |
|---|---|---|---|---|
| Add a wrapper element | **major** | `.card > .card__body` stops matching. `:first-child` selects something else. A Testing Library query that walked the tree breaks | partial: reported as `part-added`; whether it wraps existing children is yours to read | manual |
| Remove a part (`__` element) | **major** | Their descendant selector, and their test, match nothing | yes | manual |
| Add a part | **minor** | Safe, unless a consumer counts children with `> *` or `:nth-child()` | yes | review |
| Reorder children | **major** | Tab order, `:first-child`, `:nth-child()`, reading order for a screen reader | partial | manual |
| Change the root element (`div` → `button`) | **major** | Semantics, focusability, default styles, and every `div.card` selector | yes, from the element the props file renders | manual |
| Rename a class — **global CSS** | **major** | Every consumer selector and snapshot test that named it | yes, as a removed part and an added one | partial codemod |
| Rename a class — **CSS Modules** | **patch** | Nothing. The generated name was never stable and nobody could write it | yes: in a `.module.css` file, a removed part and an added one with the same properties are paired as `part-renamed-local` | none |
| Rename the *exported* class key in a module (`styles.card` → `styles.root`) | **major** | That key *is* the API, whatever the hashing does | yes | manual |

**The CSS Modules row is the one worth internalising.** Under global CSS, `.card__title` is a public name the moment it ships: a consumer can write `.card__title { font-size: 12px }` and you cannot stop them. Under CSS Modules the rendered class is `Card_title__a3f9d` and it is not a name anyone can depend on — so renaming the *local* class is invisible, while renaming the key you export (`styles.title`) is exactly as breaking as renaming a prop. The boundary moved; it did not disappear. Know which side of it each name is on before you rename anything.

**A DOM change with no visual change is still major.** This is the case that gets waved through: the screenshots are identical, the diff is a `<div>`, nothing looks different. And a consumer's `.card > p { margin-block: 0 }` now matches nothing, in production, with no error. Identical pixels in *your* repo prove nothing about a consumer who reached into your markup — and they did, because you shipped a `div` with a class on it.

---

## 8. Props

| Change | Verdict | Why | Auto-detect | Burden |
|---|---|---|---|---|
| Add an optional prop | **minor** | Existing call sites still compile | yes | none |
| Add a required prop | **major** | Every existing call site is a type error | yes | manual |
| Make an optional prop required | **major** | Same | yes | manual |
| Remove a prop | **major** | A type error at best; a silently ignored prop at worst | yes | codemod |
| **Change a prop's default** | **major** | Every call site that omitted it behaves differently, and none of them changed a line | yes | visual diff |
| Narrow a prop's type | **major** | A type error at each call site — loud, which is the good case | yes | manual |
| Widen a prop's type | **minor** in TS, **major** in spirit | Existing calls compile. But a union that gains a member changes what your `switch` must handle, and a consumer who typed against it now has an unhandled case | yes | review |
| Rename a prop | **major** | It is a removal and an addition | heuristic | codemod |
| Change a prop from `boolean` to an enum (`isLarge` → `size`) | **major** | Both a type change and a rename, and the mapping is not one-to-one | partial | manual |

**Changing a default is the prop-level twin of re-pointing a role.** No signature moved. Every omitting caller renders differently. Same verdict, same reason.

---

## 9. System-wide: layers, themes, breakpoints

| Change | Verdict | What a consumer sees | Auto-detect | Burden |
|---|---|---|---|---|
| **Reorder `@layer`** | **major** | Under Law 5, layer order is what resolves conflicts — not specificity. Reordering re-decides every conflict in the system at once, including conflicts between your CSS and theirs | yes, when both snapshots read the entry stylesheet | review everything |
| Add a layer | **major** | A new layer is inserted into a total order. Where it lands decides who wins | yes, as a changed order | review |
| Add a theme | **minor** | Nobody's current theme changed | yes | none |
| Remove a theme | **major** | Every consumer setting `data-theme` to it silently renders the default | yes | manual |
| Change a breakpoint | **major** | See §2 | yes | review responsive screens |
| Add a density | **minor** | Nobody's current density changed | yes | none |
| Remove a density | **major** | Every consumer setting `data-density` to it silently renders the default density | yes | manual |
| Change the density scale | **major**; **patch** if nothing resolves differently | Every spacing role at that density moves | yes: an override under `[data-density]`, with the roles it moves | visual diff at that density |
| Change reduced-motion behaviour | **major** | It is a render change for the users least able to absorb a surprise | yes: any override under a media condition, added, changed or removed (reduced motion, forced colours, more contrast) | review |

**Layer order deserves the loudest warning in this file.** It is one line, it is easy to "tidy", and it changes the resolution of every conflict in the system simultaneously — a blast radius no tool can enumerate, because the affected set is "every pair of rules that ever disagreed". The statement lives in the entry stylesheet, not in `tokens.css`, so give `extract_system.py` that file too: system.json records each `@layer a, b, c;` statement it reads, and `diff_system.py` compares them. It says so when a snapshot has none, or predates 3.4.0 and could not record one.

---

## 10. The hard cases

### 10.1 A bug fix to you is a breaking change to them

The scenario the gate exists for. `--fg-muted` on `--bg-sunken` measures 4.31:1. That is a WCAG failure. You darken `--neutral-600` by three points, it reaches 4.62:1, and you ship it as a patch because it is *a bug fix*.

It is a bug fix. It is also major. Both of those are true and neither cancels the other:

- For a consumer whose text sits on `--bg-sunken`, you fixed a real accessibility failure in their product.
- For a consumer who built a muted-on-canvas layout, tuned it, and had it signed off, you changed a colour they approved. Their pages look different and nobody asked them.
- For a consumer who overrode `--fg-muted` in their own theme, you changed nothing at all, and your fix did not reach their bug.

**The honest handling, in order:**

1. **Ship it as major.** Not because it is wrong, but because output moved. The severity describes the *impact*, never the intent.
2. **Say in the changelog that it was a fix, and say what was broken.** "`--fg-muted` on `--bg-sunken` measured 4.31:1 and failed SC 1.4.3. It now measures 4.62:1." A consumer who reads that upgrades willingly. A consumer who reads "colour tweaks" does not.
3. **Name the consumers it does not reach.** Anyone overriding that role still has the bug. That sentence is the most valuable one in the release.
4. **Give both ratios, for both themes.** `diff_system.py` prints them. Paste them in. A measured number is the only kind worth publishing.
5. **Do not batch it.** A contrast fix in a release with eleven other changes gets skipped by the client with the tightest budget — the one most likely to have the failure.

What you must not do is ship it as a patch because the motive was good. That is how the failure in the brief happens: someone re-points `--bg-accent` to fix a contrast bug, three client sites update, two of them now have an illegible secondary button, and nobody notices for a month — because a patch is the release nobody reviews.

### 10.2 Visual-only changes: yes, a visual regression is breaking

A shadow gets softer. A radius goes from 12px to 10px. A hover transition drops from 220ms to 140ms. No name moved, no type changed, no test failed.

**In a design system, the rendered output *is* the API.** That is not a rhetorical flourish; it is the reason the system exists. Consumers do not import it for its names. They import it so their product looks a particular way without deciding every value themselves. Changing the way it looks is changing the thing they bought.

The practical consequences:

- **A visual diff is the acceptance test, not a nice-to-have.** Type-checking and linting cannot see this category at all. `component-state-matrix` can. Wire it in.
- **"Too small to matter" is a measurement, not a feeling.** A 2px radius change across a page of cards is visible. A 2px change on one icon is not. Look at the diff and decide; do not decide first.
- **Motion is visual.** Duration and easing changes are re-points with the same verdict.
- **Severity still tracks impact, not effort.** A one-character CSS change that alters every card in every client's product is major. A forty-file refactor that changes nothing is a patch.

The exception that proves it: a change that is invisible **at every density, in every theme, at every state** is a patch — and the only way to make that claim honestly is to have rendered the cross-product and looked. Which is the same tool.

### 10.3 When the consumer reached into your internals

A consumer wrote `.card > div:nth-child(2) { display: none }` because you never gave them a way to hide that element. You refactor the markup. Their page breaks.

The tempting position is that they broke their own page: they reached past the API into markup you never published. That position is correct and it is useless, because their page is still broken and they are still your client.

The usable rule:

| Situation | Verdict | Why |
|---|---|---|
| They depended on a documented socket, part, prop or variant | **major** | Published API. No argument. |
| They depended on an undocumented class name in **global** CSS | **major** | You shipped a global name into their cascade. That publishes it, whatever your docs say. |
| They depended on an undocumented class in **CSS Modules** | **patch** | The name was hashed and never stable. They depended on build output. |
| They depended on DOM order or `:nth-child()` | **major** in practice | Nothing stopped them and nothing warned them. |
| They monkey-patched your CSS with `!important` | **patch** | Law 5 says you have no layer-order contract with `!important`. |

The two rows in the middle are the whole argument for CSS Modules in a distributed design system: it makes the boundary mechanical instead of documentary. Under global CSS every class you ship is API by accident. Under modules only what you export is.

**And in every row, the practical answer is the same:** when you change internals, say so in the changelog under a "structure" heading even though it is not an API change. It costs a line and it converts a support conversation into a search.

### 10.4 Cascading Tier-1 changes

You edit one line in the neutral ramp. `diff_system.py` reports fourteen roles.

This is the case people underestimate, every time, because the *diff* is one line and the *effect* is a page. A Tier-1 primitive sits at the root of a reference tree, and the tree is three deep in the canonical system: `--accent-600` → `--border-focus` → `--shadow-focus` → `--elevation-focus`, plus `--bg-accent` in parallel. Every leaf is a place something renders.

How to handle one without guessing:

1. **Get the transitive set, not the direct one.** `diff_system.py` prints direct roles and roles one hop further, separately, over the union of both versions' reference graphs — a role that read the primitive before and was re-pointed away from it in the same release is still affected by the release.
2. **Intersect it with the text roles and measure.** Every `--fg-*` that resolves through the edited primitive gets a before/after ratio against every surface, in every theme. Threshold crossings in *either* direction are flagged; a crossing upward is news too, because it may be the reason you made the change.
3. **Do not forget the non-text obligations.** SC 1.4.11 asks 3:1 of a control's boundary and of a focus indicator. A shifted accent moves the focus ring's contrast, and no linter calls a border "text". The diff reports those pairs as well.
4. **Then look at the proof sheet.** The numbers tell you what crossed a line. Only the render tells you what looks wrong.
5. **Ship it alone.** A cascading primitive change is the whole release. It is impossible to review alongside anything else, and batching it is how the review becomes a rubber stamp.

**The tempting shortcut to refuse:** "I will re-point only the two roles that need it and leave the primitive alone." That leaves the ramp incoherent — step 600 no longer means what step 600 means everywhere else — and Law 6 stops paying for itself. Either the primitive was wrong, in which case fix the primitive and take the blast radius, or the *role* was pointed at the wrong step, in which case re-point the role and leave the ramp alone. Deciding which of those it is takes thirty seconds and saves the next person a year.

---

## 11. The decision procedure

Given a diff, the version bump in under a minute.

```bash
python -m scripts.diff_system published/system.json candidate/system.json \
       --from-version 1.4.2 --deprecations deprecations.json
```

Then walk the four questions in order and stop at the first **yes**:

| # | Question | If yes |
|---|---|---|
| 1 | Did any name a consumer can write **disappear or change**? Token, socket, class, variant, size, state, prop, theme. | **major** |
| 2 | Does anything that already existed **resolve to a different value**? Any tier, any theme, any density. Including via a primitive edit upstream. | **major** |
| 3 | Did existing **structure or order** change? An element removed or wrapped, child order, root element, `@layer`, breakpoints. | **major** |
| 4 | Is there **new surface** — a token, socket, variant, size, state, part, optional prop, theme, density? | **minor** |
| — | Otherwise | **patch** |

The whole procedure in one sentence: **if a consumer who changed nothing would see something different, it is major; if they would see nothing different but have something new available, it is minor; otherwise patch.**

Three checks before you publish the number:

- **Every major has a deprecation record or a changelog entry that names it.** The gate enforces the first; you enforce the second.
- **Every contrast crossing is quoted with both ratios.** Never "improved contrast".
- **No breaking change is batched with a routine one.** A release with one major and nine patches gets reviewed as a patch release.

---

## 12. Every kind `diff_system.py` emits

The script prints a `[kind]` on every change. This is the index from that string back to the section that argues it, so a report and this file are never two separate arguments.

| Kind | Verdict | §  |
|---|---|---|
| `tier1-added` · `breakpoint-added` | minor | 2 |
| `tier1-removed` · `tier1-renamed` | major | 2 |
| `tier1-value-changed` · `breakpoint-changed` | major | 2, 10.4 |
| `tier2-added` | minor | 3 |
| `tier2-removed` · `tier2-renamed` | major | 3 |
| `tier2-repointed` | major | 4 |
| `tier2-repointed-equal` | patch | 1, 4 |
| `theme-override-added` | major; patch if it resolves as before | 3 |
| `theme-override-changed` · `theme-override-removed` | major | 3 |
| `theme-added` · `density-added` | minor | 9 |
| `theme-removed` · `density-removed` | major | 9 |
| `density-changed` | major; patch if nothing resolves differently | 9 |
| `condition-changed` | major | 9 |
| `socket-added` | minor | 5 |
| `socket-removed` | major | 5 |
| `socket-default-changed` | major | 5 |
| `socket-default-equal` | patch | 5 |
| `component-added` · `variant-added` · `size-added` · `state-added` | minor | 6 |
| `component-removed` · `component-renamed` | major | 6 |
| `variant-removed` · `size-removed` · `state-removed` | major | 6 |
| `variant-changed` | major | 6, 10.2 |
| `part-added` | minor | 7 |
| `part-removed` | major | 7 |
| `part-renamed-local` | patch | 7 |
| `element-changed` | major | 7 |
| `prop-added-optional` | minor | 8 |
| `prop-added-required` · `prop-removed` · `prop-type-changed` | major | 8 |
| `prop-default-changed` | major | 8 |
| `layer-order-changed` | major | 9 |
| `note-changed` · `moved` | patch | 1 |

Two verdicts the script deliberately does **not** compute, because no parser can:

- **Whether an addition is really an addition.** A socket whose default does not reproduce today's rendering is a re-point in additive clothing. The script reports the resolved default per theme; you compare them.
- **Whether a re-point that resolves identically will keep resolving identically.** `tier2-repointed-equal` is a patch on the strength of a claim about the future, and the claim is yours.

---

## The three sentences to remember

1. **Breaking is about rendered output, not about names** — a re-pointed role and a renamed one are the same verdict, and the re-point is the dangerous one because nothing complains.
2. **A Tier-1 edit is never one change** — get the transitive blast radius and the contrast delta before you pick a number, because the diff is one line and the effect is a page.
3. **A bug fix can still be breaking**, and saying so plainly — with both measured ratios and the list of consumers it does not reach — is what makes the next upgrade get read instead of skipped.
