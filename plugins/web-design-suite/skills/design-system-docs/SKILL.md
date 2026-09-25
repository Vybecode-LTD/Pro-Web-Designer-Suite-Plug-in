---
name: design-system-docs
description: Generate a design system's documentation from its own source — a token reference with resolved values and measured contrast, a component reference whose API tables are extracted from each component's Tier-3 socket block, and a living style guide that cannot drift because nothing in it was transcribed. Use for documenting a design system, a component library reference or gallery, token documentation, a living style guide, "document our design system", a Storybook alternative without Storybook, onboarding a new developer onto a design system, documenting component props and CSS custom-property APIs, publishing a style guide, and keeping docs in sync with code. Reach for it whenever anyone mentions design system docs, component docs, a props table, a CSS API, a token reference, a docs site, stale or drifting documentation, or "where is this documented" — and any time a component library exists that nobody has ever written down.
---

# Design System Docs

Hand-written design system documentation is worse than no documentation.

That is not a provocation, it is the failure sequence. Someone writes "`--fg-subtle` on `--bg-sunken`, 4.6:1, passes AA." Six months later the neutral ramp is retuned by one step. The page still says 4.6:1. A reviewer checks the docs instead of measuring, ships the screen, and the contrast failure reaches production **through** the documentation. With no page at all, that reviewer would have measured.

Every fact in a design system already exists, written down, in a machine-readable form, in the source. A second copy maintained by humans is not documentation — it is an unsynchronised cache with no invalidation.

So: **generate the what, write the why.**

---

## The division of labour

| Content | Who writes it | Why |
|---|---|---|
| Token name, value, tier, resolved value | generated | It is a transcription. Transcriptions drift. |
| Theme re-points, density scaling | generated | Reading them out of the theme block is exact; reading them out of memory is not. |
| Contrast ratios | generated | A measured number in a doc is the only kind worth having. |
| The Tier-3 socket table — defaults, accepted types, what consumes each | generated | It is already declared at the top of the component's root rule. |
| Variants, sizes, implemented states, parts | generated | The selectors are the spec. |
| Props, types, defaults | generated | The TypeScript is the spec. |
| **Why this decision and not the obvious one** | **written** | Not in the source at all. |
| **The tradeoff that was accepted** | **written** | Same. |
| **When NOT to use this component** | **written** | The most valuable section of any component page, and the one a parser cannot produce. |
| **What was deprecated and what replaced it** | **written** | Deletion leaves no trace to extract. |

A parser can tell you that `--bg-accent` is `--accent-600`. It cannot tell you that `--accent-500` is the brand anchor but measures 3.56:1 against white, which is legal above 24px and illegal on a 14px button label — so the role took 600 while the brand kept 500. That sentence is the entire reason the token layer exists, and it lives in a human's head until a human types it.

---

## The key insight

**A component's Tier-3 socket block is its API documentation, already written, already in the file.**

```css
.button {
  --button-pad-inline: var(--pad-inline-md);
  --button-radius:     var(--radius-lg);
  --button-bg:         var(--bg-surface);
  /* Interaction is an OVERLAY, not a replacement fill: one hover rule
     darkens every variant, including variants that do not exist yet. */
  --button-overlay:    transparent;
```

That block already states the property name, the default, the tier it sources from, and — in the comment — the *why*. `style-architecture.md` §7 makes the claim explicit: a component's custom properties are its public CSS API, exactly as its props are its JavaScript API. Nobody has to maintain a second copy of that table. It just has to be extracted and rendered, with the comment carried across as prose.

Everything else follows. Variants are the selectors that re-point sockets. States are the selectors with pseudo-classes and ARIA attributes. Parts are the `__` classes. The whole component page is a projection of one file.

---

## Who the pages are for

Five people arrive at design system documentation and only one of them is reading it front to back. The order of every page in this skill is set by what each needs first, and none of them need your architecture diagram.

| Reader | Arrives asking | Needs first |
|---|---|---|
| A developer **using** a component | "how do I make this one narrower?" | the socket table and one working example |
| A developer **changing** a component | "what breaks if I rename this?" | who consumes each socket, and the deprecation path |
| A designer **checking a value** | "what is our card padding?" | the resolved value, at density 1, in both themes |
| A newcomer **learning the system** | "why are there three greys?" | the principles, then the proximity ladder, then nothing else today |
| A reviewer **verifying a claim** | "does this actually pass AA?" | the measured ratio and the date it was measured |

The reviewer is the one who decides whether the documentation is a liability. Full audience model, and the page order that falls out of it, in `references/documentation-model.md` §2.

---

## Why not Storybook

Storybook is a good answer to a different question. It renders components in isolation with controls — which is a development environment, not a reference. Reach for this skill instead when:

| You want | Storybook | Here |
|---|---|---|
| A props table | from the TS, at runtime, in a browser | from the TS, at build, in a static file |
| A **CSS custom-property** API table | no concept of one | the socket block, extracted |
| Resolved token values | you inspect the DOM | computed and printed, with the `var()` chain |
| Measured contrast | an addon, if configured | a column, always, from the same maths as the ramp generator |
| CI that fails on stale docs | no | `--check`, exit 1 |
| Install cost | a build system, a config, a dependency tree | two stdlib Python files |

The two coexist without friction: Storybook is where a component is *developed*, this is where it is *published*. If you already run Storybook, keep it and add `--check` to CI — the drift gate is the part Storybook has no answer for.

---

## Workflow

### 1. Point it at the source

```bash
python -m scripts.extract_system styles/ src/components/ --out system.json --report
```

Directories, files or globs. Anything matching `tokens.css` / `theme.css` is read as a token file, other CSS as component CSS, `.ts`/`.tsx`/`.jsx` as prop sources. Name them explicitly when auto-detection guesses wrong:

```bash
python -m scripts.extract_system \
  --tokens styles/tokens.css --tokens styles/brand.css \
  --components "src/components/**/*.css" \
  --props "src/components/**/*.tsx" \
  --prose docs/prose --out system.json --report
```

`system.json` is deterministic — sorted, no timestamps, paths relative to `--root`. **Commit it.** It is the baseline that step 4 diffs against, and a timestamp in it would make every run report drift.

Read the `--report` summary before you build anything. It will already have found things.

### 2. Generate

```bash
python -m scripts.build_docs system.json --out docs-site/ --prose docs/prose
```

Four pages, no build step, no network, opens from `file://`: an overview, a token reference with live swatches and the contrast column, a component reference with socket tables and a rendered instance per variant and per state, and a patterns page if you have written any. Plus a search box, a theme switcher and a density switcher — because a docs site that cannot show you dark mode is documenting half a system.

### 3. Fill the gaps the generator cannot infer

The site will tell you, per component, that it has the *what* and none of the *why*. Write markdown into `--prose` and it is merged by filename:

```
docs/prose/
  overview.md                    the landing page body
  principles.md                  the principles page
  tokens/color.md                prepended to the colour group
  components/button.md           appended to the button page
  components/button.example.html replaces the generated example markup
  patterns/empty-states.md       one pattern page
```

**Generated and hand-written content never share a file.** Everything under `--out` is disposable and is rewritten on every run; nothing under `--prose` is ever written to. That is what makes regeneration safe: a build cannot eat your prose because a build never opens it for writing.

What to write, in order of value: *when not to use this* · the tradeoff · the why behind a non-obvious default · the deprecation and its replacement. Full per-page model in `references/documentation-model.md`.

### 4. Detect drift in CI

```bash
python -m scripts.extract_system styles/ src/ --out build/system.json
python -m scripts.build_docs build/system.json --baseline docs/system.json \
       --prose docs/prose --check
```

Exit 1 and a readable report — not a JSON dump — naming each thing that changed: a token that was removed, a default that moved, a contrast ratio that crossed 4.5:1, a socket that was deleted (which is a breaking change to a published API), a hand-written ratio that no longer matches the measurement, a page for a component that no longer exists.

Wire it next to the audit gate; they fail for different reasons and both failures are actionable:

```bash
python -m scripts.audit_design src/ --strict                    # Law 9: the code
python -m scripts.build_docs build/system.json --out build/docs \
       --emit-css build/docs-chrome.css --emit-examples build/examples
python -m scripts.audit_design build/docs-chrome.css --strict   # the site obeys the laws
python -m scripts.audit_design build/examples --strict          # so does every example
python -m scripts.build_docs build/system.json --baseline docs/system.json \
       --prose docs/prose --check                               # nothing drifted
```

Full wiring, including the GitHub Actions file, is in `references/drift-detection.md` §6.

### 5. Publish

The site is static and self-contained; any file host will do. Commit `system.json` alongside it in the same commit as the code change that caused it — a baseline updated on its own is unreviewable, and alongside its cause it reads as "this changed, so these forty numbers changed."

---

## Two things the generator does that are worth knowing about

**Every code example in the docs is extracted and linted like source.** `--emit-examples DIR` writes each fenced block to a real file so `audit_design.py` reads it like any other stylesheet, and `--check` verifies that every `var(--x)` in an example still resolves and every `.class` it styles is still a part the component publishes. A wrong example is worse than a missing one: people copy examples, and nobody copies an absence.

**The site obeys the nine laws itself.** It is a demonstration of the system it documents, so a hardcoded value in its own chrome is a bug. `--emit-css` writes the chrome stylesheet out as a real file to be audited, and it deliberately carries no `@generated` marker — `audit_design.py` skips generated files, and a skipped audit proves nothing.

---

## What the extraction finds that nobody asked for

The `gaps` section of `system.json` is the part teams act on first. All of it comes free, because documenting a thing means reading it closely enough to notice it is wrong.

| Gap | What it means |
|---|---|
| `missing-state` | An interactive component with no rule for one of the seven states. An unwritten state renders as `default`, so nothing fails and nobody notices. |
| `unconsumed-socket` | A Tier-3 property declared on the root that no declaration reads. Published API that does nothing — wire it up or delete it before someone depends on it. |
| `orphan-token` | Declared and referenced by nothing. A spare ramp step is fine; an unread Tier-2 role is a decision nobody took. |
| `tier1-leak` | A component reading a primitive that has a role (Law 6). Documenting it as API would publish a mistake. |
| `no-theme-coverage` | Every socket resolves identically in light and dark. Either it is colourless or its colours are not roles. |
| `undocumented-component` | Exists in code, has no hand-written page. |
| `orphan-doc` | A page for a component that no longer exists — an instruction to use something that is gone. |
| `theme-repoints-tier1` | A theme block re-pointing a primitive. Either a documented exception or a role that was never made. |
| `weak-state` | `:focus-within` but no `:focus-visible` — the container lights up, the control that actually has focus does not. |

---

## The honest limits

Static resolution ends where the browser begins, and the docs say so rather than guessing:

| Construct | What you get |
|---|---|
| `var()` chains, `calc()`, `min()`, `max()` | the exact value |
| `clamp()` with a `vw` term | the range, labelled fluid — `64px … 144px`, not a fake single number |
| `em`, `ch`, `ex`, `%`, `cq*` | reported unresolved, with what it is relative to |
| `oklch()` / hex | the value, the hex and the measured contrast |
| a translucent role over an unknown surface | no contrast figure at all, because the honest answer is "it depends what is behind it" |

Everything unresolved lands in `limits` and is printed on the site. A doc that admits what it cannot compute is trusted on the things it can.

---

## Adopting this on a system that already has hand-written docs

Do not delete the old pages and do not port them by hand. Both roads end in a half-migrated docs site that nobody trusts.

1. **Extract first, publish nothing.** `--out /tmp/docs --report`. Read the gap list. Some of it is news.
2. **Diff the old pages against the new ones by eye, once.** Every disagreement is either a stale sentence or a parser bug, and you want to know which before anyone else sees the site. Expect the stale sentences to outnumber the bugs several to one; that ratio *is* the argument for the change.
3. **Keep only the prose.** Move the *why* paragraphs, the tradeoffs and the when-not-to-use sections into `--prose`, one file per component. Delete every table, every value and every ratio you moved past — those are now generated, and a second copy is the exact problem you are fixing.
4. **Turn on `--check` before you publish**, with the first `system.json` committed as the baseline. A drift gate added later never gets added.
5. **Announce one rule**: values are never typed by hand again. The first person to paste a ratio into a page is the person who restarts the rot.

---

## Anti-patterns

| Pattern | Why it fails |
|---|---|
| A hand-maintained props table | The TS moved on Tuesday. The table did not. |
| A screenshot of a component | Goes stale silently and invisibly. Render a live instance styled by the component's own stylesheet. |
| A contrast ratio typed from memory | The one number in the whole page a reviewer will act on without re-checking. |
| Generated output committed into the same file as prose | The next regeneration eats the prose, so the next person stops regenerating. |
| Documenting a private property as if it were API | Now it is API. A Tier-3 socket nobody published is the only kind you may still rename. |
| A docs site with no dark mode | Half the system undocumented, and the half most likely to be broken. |
| `system.json` with a timestamp in it | Every CI run reports drift, so the team turns the gate off within a week. |
| A page per component with no *when not to use* | The reader's actual question, unanswered, on every page. |
| Docs built from a manifest someone maintains by hand | A second source of truth, which is the original disease under a new name. |

---

## Routing

| Situation | Go to |
|---|---|
| Building or restyling the system itself | `web-design-studio` |
| An inherited codebase not yet on tokens | `design-token-migration` |
| Design file and code have drifted apart | `figma-variables-sync` |
| Proving every state × density × theme actually renders | `component-state-matrix` |
| **Writing the system down so other people can use it** | **here** |
| Copy, offer and persuasion on a landing page | `landing-page-conversion` |
| Adversarial review before a client sees it | `design-critique-gate` |

Neighbouring skills, precisely: `component-state-matrix` renders the cross-product to prove the system *works*; this skill renders one instance per variant to show a reader what it *is*. Both read component CSS; only the matrix is a test. If a state looks wrong on a docs page, go and look at the proof sheet.

Within this skill:

| You want | Read |
|---|---|
| the token vocabulary | `references/token-contract.md` |
| what a doc must contain, in what order, for which reader | `references/documentation-model.md` |
| the page model for a token, a component, a pattern | `references/documentation-model.md` §4–7 |
| what must never be generated, and why | `references/documentation-model.md` §8 |
| how a design system is parsed out of its source | `references/extraction.md` |
| tier classification, and the exceptions that trap a naive parser | `references/extraction.md` §2 |
| resolving `var()` / `calc()` / `clamp()` without a browser | `references/extraction.md` §5 |
| the six ways documentation rots, and the CI check for each | `references/drift-detection.md` |
| CI wiring | `references/drift-detection.md` §6 |

---

## Scripts

### `scripts/extract_system.py` — stdlib Python 3, no dependencies

| Flag | Does |
|---|---|
| `paths…` | files, directories or globs; classified by name and extension |
| `--tokens PATH` | a token file, explicitly (repeatable) |
| `--components PATH` | a component stylesheet, directory or glob (repeatable) |
| `--props PATH` | a TS/TSX/JSX source for props and JSDoc (repeatable) |
| `--prose DIR` | enables the `undocumented-component` and `orphan-doc` gaps |
| `--out FILE` | where `system.json` goes (default: stdout) |
| `--root DIR` | output paths are made relative to this |
| `--root-font-size PX` | the `rem` basis for static resolution (default 16) |
| `--report` | a human summary to stderr |
| `--strict` | exit 1 if any error-severity gap was found |
| `--color-impl PATH` / `--check-color-impl` | bind to, or verify against, the studio's colour math |

Exit `0` extracted · `1` `--strict` with errors · `2` bad invocation.

**On the contrast column:** it uses the OKLab/WCAG functions from `web-design-studio/scripts/generate_color_ramp.py`. When the suite is installed whole, that module is imported and used directly; shipped standalone, a byte-identical vendored copy runs instead, and `--check-color-impl` proves the two agree on a set of probe pairs. Two implementations of contrast in one suite is how a docs page says 4.48:1 and a ramp generator says 4.52:1 for the same pair, and how a reviewer learns to trust neither.

### `scripts/build_docs.py` — stdlib Python 3, no dependencies

| Flag | Does |
|---|---|
| `--out DIR` | the site (required unless `--check` runs alone) |
| `--prose DIR` | hand-written markdown, merged by filename, never written to |
| `--root DIR` | resolves the source paths recorded in `system.json` |
| `--project NAME` | the title on every page |
| `--only NAME` | one component; repeatable or comma-separated |
| `--no-examples` | skip the rendered instances and the forced-state stylesheet |
| `--check` | drift mode: diff against the baseline, check every hand-written claim, exit non-zero |
| `--baseline FILE` | the committed `system.json` to diff against (default `<out>/assets/system.json`) |
| `--emit-css FILE` | the site's own chrome stylesheet, for `audit_design.py` |
| `--emit-examples DIR` | every fenced code example as a real file, to be linted like source |

Exit `0` built / no drift · `1` drift found · `2` bad invocation.

The rendered examples mirror each pseudo-class state rule onto a `data-force-state` attribute — `.button:hover:not(:disabled)` and `.button[data-force-state~="hover"]:not(:disabled)` have identical specificity (0,3,0), so the mirror wins on document order alone, in the same layer and the same at-rule context. That is how a focus ring appears on a static page without a mouse. A `:not(...)` is left alone: it is a guard, not a state.

---

## The three sentences to remember

1. **Generate the what, write the why** — everything a parser can read, it should read, and everything it cannot is the part worth a human's afternoon.
2. **The Tier-3 socket block is the API documentation**, already written, already in the file; nobody maintains a second copy of it and nobody should.
3. **A stale doc is worse than a missing one**, because a reviewer trusts it instead of measuring — so every claim, including every code example, is checked against the source in CI.
