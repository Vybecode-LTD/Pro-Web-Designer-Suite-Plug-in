---
name: design-token-migration
description: Migrating or refactoring an existing codebase onto a design token system. Use this whenever someone inherits, adopts or cleans up CSS they did not write — "our CSS is a mess", a client codebase full of margin-top:13px and #3a3a3a, legacy stylesheets, inline styles, !important, magic numbers, a dozen near-identical grays, inconsistent spacing, or a design system that has to be adopted on a site that already ships. Extracts every hardcoded value in the repo, clusters them into the decisions they were trying to be, derives a tokens.css from the codebase's own values, generates a reviewable codemod, and proves it worked with a before/after audit diff. Strangler-fig by default: incremental, per-directory, with a baseline that freezes the remaining debt instead of a rewrite nobody approves. Covers plain CSS/SCSS, CSS Modules, styled-components/Emotion, Tailwind arbitrary values, Bootstrap/Material overrides, and inline-style-heavy React.
---

# Design Token Migration

Getting an inherited codebase onto the system in `references/token-contract.md`, without a rewrite and without a regression.

This is the hard half of design systems work. Building a token system on a greenfield project is a pleasant afternoon. Getting four hundred files of somebody else's CSS onto one — while the product ships every Tuesday, while nobody has time, and while the person who wrote it has left — is the job people actually pay for, and it is the job that most often fails.

It fails for one reason: **the migration is proposed as a rewrite, and a rewrite is a bet nobody can approve.** Everything below exists to avoid that.

---

## The migration philosophy

Six positions. Every script and every reference file in this skill is one of them, implemented.

**1. Inventory before opinion.** You cannot negotiate a migration you cannot size, and you cannot size one you have not counted. The first artifact is a census: every literal value, its property, its file, its line. No changes. Nothing is more persuasive to a skeptical engineering manager than a number they can verify.

**2. The values already contain the system.** A codebase with `12px`, `13px`, `14px` and `15px` does not have four spacing decisions. It has one, made four times, on four Thursdays, by three people, none of whom could see the others. The migration's job is to find the decision, not to impose one. A token system derived from the codebase's own values gets adopted; one imported from a style guide gets ignored.

**3. The scale stays closed.** The derived system snaps onto the contract's existing steps. It never adds `--space-7` to absorb an awkward 28px. The closed scale is the entire mechanism — the moment you widen it to settle an argument it becomes a menu and stops doing its job. Values that do not fit are *reported*, not accommodated. That report is where the design work is.

**4. Mechanical and judgment work are separated, hard.** Replacing `#3a3a3a` with `var(--fg-default)` in two hundred places is a script's afternoon. Deciding whether the 22px padding should become 20 or 24 is a designer's week. Mixing them produces a 500-file diff that gets rubber-stamped, and rubber-stamped diffs are how a migration ships a regression on the pricing page.

**5. Incremental by construction.** One kind of value at a time, one directory at a time, one commit each. The gate goes on **today**, with a baseline, so the existing debt is frozen while it is paid down. A migration that must complete before it delivers value will not complete.

**6. Proof, not vibes.** Before/after audit counts, measured contrast, visual regression shots. "Looks fine to me" is not a verification step, and on someone else's codebase it is not even an opinion.

---

## The six-phase workflow

Work them in order. Each phase's output is the next phase's input, and each one is safe to stop at — which is the point, because most migrations stop somewhere in the middle and the ones that survive are the ones that left the codebase better at the stopping point.

| Phase | Produces | Changes code? | Who decides |
|---|---|---|---|
| 1 Inventory | `literals.json`, a census | No | Nobody yet |
| 2 Cluster | The decisions behind the values | No | The script proposes |
| 3 Propose | `tokens.css`, `mapping.json`, `reconciliation.md` | No | **A human, on every row of the reconciliation** |
| 4 Codemod | Reviewable diffs, in batches | Yes | Review per batch |
| 5 Verify | Audit diff + visual regression | No | Whoever owns quality |
| 6 Hold the line | Baseline + gate in CI | No | The team, forever |

### Phase 1 — Inventory

```sh
python -m scripts.extract_literals ./src                              # read it
python -m scripts.extract_literals ./src --format json -o literals.json
python -m scripts.extract_literals ./src --format csv  -o literals.csv # for the client
```

Walks CSS, SCSS, LESS, JS, JSX, TS and TSX. Finds literals in CSS declarations, SCSS/LESS variables, JSX `style={{}}` objects, styled-components and Emotion template literals, Tailwind arbitrary values, and hex colors in JS strings. Records kind, raw text, normalized form, property, file, line, column, and whether the file is one where Laws 2, 4 and 6 bite.

It deliberately does **not** count values inside comments, quoted strings or `url()`. Those are not design decisions, and counting them inflates the estimate you are about to put in front of a client.

Vendor stylesheets and `tokens.css` are excluded by default. Pass `--include-vendor` once, to see the true total, then never again — you layer vendor CSS, you do not migrate it.

Read the output before doing anything else. The headline block at the bottom is the whole business case: *distinct spacing values vs the 18 the scale has; distinct colors; occurrences off the 4px grid.*

### Phase 2 — Cluster

The intellectual core, and the reason this skill is not a `sed` script.

```sh
python -m scripts.cluster_values literals.json -o ./proposal
```

Four separate algorithms, because four kinds of value fail in four different ways:

| Kind | Method | Why that method |
|---|---|---|
| Spacing | Snap to the nearest 4px-scale step within a tolerance band; ties broken by frequency, then downward | The crowd is the decision and the outlier is the typo. Collapsing space is safer than expanding it into an overflow |
| Color | Single-linkage clustering by OKLab ΔE, with a diameter cap and two guards | Near-duplicates form chains (`#333` → `#343434` → `#3a3a3a`) and chains are exactly what must collapse |
| Type | Snap to the type scale; ties broken **upward** | Text does not shrink to settle a tie |
| Shadow | Cluster by structural signature — layer count, blur, offset — not by alpha | Somebody eyeballed the alpha at 3pm. The geometry is the decision |
| Duration | Round to the five steps, then pair with an easing | A duration and an easing in separate tokens drift apart inside a quarter |
| Z-index | Rank, then band by magnitude | `9999` never meant "very high". It meant "higher than the last person's 999" |

The full method, including the ΔE threshold and its calibration, is in **`references/extraction-and-clustering.md`**. Read it before you defend a clustering decision to a designer, because you will have to.

### Phase 3 — Propose

Same command; the outputs are the proposal:

- **`tokens.css`** — the contract's exact token names, with the accent ramp seeded from *this codebase's* most-used chromatic color and the neutral hue read off *its own* grays. Every token carries a `was:` comment naming the literals it absorbed. That comment is the audit trail for the codemod and the answer to "why is this 16 and not 18" three months from now.
- **`mapping.json`** — every original literal to its token, in the form the codemod consumes.
- **`reconciliation.md`** — **the document you actually review.** Three tables: what is mechanically replaceable, what moves more than 2px and needs eyes on a screenshot, and every value with no home plus a recommendation.

The reconciliation report is the deliverable. The `tokens.css` is a first draft of a conversation; the reconciliation is the conversation. Walk a designer through it before a single file changes.

**Do not skip the contrast table.** Every proposed foreground role is measured against the surface it actually lands on, before and after. A migration that improves consistency and quietly drops body text from 5.1:1 to 4.2:1 has failed, and it will fail an accessibility audit six months later when it is expensive.

### Phase 4 — Codemod

Dry run first. Always.

```sh
python -m scripts.apply_codemod ./src --mapping proposal/mapping.json
```

Then apply in batches. **One kind at a time, one commit each.**

```sh
python -m scripts.apply_codemod ./src -m proposal/mapping.json --kind color   --apply
git commit -am "migrate: colors to role tokens"
python -m scripts.apply_codemod ./src -m proposal/mapping.json --kind spacing --apply
git commit -am "migrate: spacing to the closed scale"
```

Batching is not ceremony. A 500-file diff gets rubber-stamped; a 40-file diff of one kind gets read. And when something looks wrong three days later, `git revert` on a one-kind commit is a thirty-second fix rather than an archaeology project.

**The commit between batches is load-bearing, not tidiness.** The codemod refuses files with uncommitted changes, so a loop that runs every `--kind` without committing applies the first batch and skips every file in all the rest. It says so, loudly, on every skipped file, and exits 1 — but if you are piping to `/dev/null` you will not see it.

The codemod handles the cases that break naive find-and-replace: comments, strings, `url()`, `calc()` (it recurses into it — those literals survive every migration because grep cannot see inside parentheses), negative values (`-13px` → `calc(var(--gap-related) * -1)`, which keeps the relationship rather than inventing a negative token), and shorthands where only some slots map (`padding: 22px 26px` correctly maps the inline slot and leaves the ambiguous block slot alone).

It refuses to touch a file with uncommitted changes. It writes to a temp file in the same directory and moves it into place only after brace-balance and declaration-count checks pass. A file is never left half-written.

**Four things it will not do, on purpose:**

| Left behind | Why | Where it goes |
|---|---|---|
| Child `margin-*` (Law 2) | Deleting a child margin without adding the parent's `gap` collapses the layout. It is a layout change, not a value swap | Phase 4e, by hand, one container at a time — see `migration-strategies.md` §6 |
| JSX `style={{…}}` (Law 4) | The value can be tokenized, but the *declaration* has to move into a stylesheet, which means a class name. A codemod that invents class names is a codemod nobody reviews | Phase 4f |
| `!important` (Law 5) | Removing it changes which rule wins. That is a cascade fix | Phase 4g, after layers are in |
| Vendor CSS | You layer it, you do not migrate it | Never |

### Phase 5 — Verify

`audit_design.py` is the sibling `web-design-studio` skill's gate — the same script, unmodified, so the number you report is the number that skill enforces. Copy it into the project or invoke it from wherever the suite is installed; do not fork it.

```sh
# before, on the commit you branched from
git stash && python -m scripts.audit_design ./src --json > /tmp/before.json && git stash pop
python -m scripts.audit_design ./src --json > /tmp/after.json
```

Report the delta by law. A real migration moves L1 and L3 to near zero and leaves L2, L4 and L5 roughly where they were — those are the phases you have not done yet, and saying so is more credible than a round number.

Visual regression matters more than the audit here, because the audit cannot see a 4px shift. The cheap version that actually gets run:

1. Screenshot every page and every Storybook story on the base commit.
2. Apply one batch.
3. Screenshot again, diff the PNGs.
4. Anything with a diff over ~0.1% of pixels gets a human. Everything else ships.

Order the review by the reconciliation's "moves more than 2px" table — those are the only rows where a pixel diff is expected, and if something *else* moved, you have found a bug.

### Phase 6 — Hold the line

A migration that ends without a gate regenerates its own debt within two quarters. Measured, not guessed.

```sh
python -m scripts.audit_design ./src --write-baseline .design-baseline.json
git add .design-baseline.json && git commit -m "freeze the remaining design debt"
```

From here, only **new** violations fail. The debt is frozen rather than growing, and the baseline file shrinking over time is the burndown chart — it is a real artifact, in the repo, that nobody has to maintain.

Wire it into CI and into a pre-commit hook. The pre-commit hook matters more: CI tells you after you context-switched.

---

## Reference routing

| Read this | When |
|---|---|
| `references/token-contract.md` | Always, first. The nine laws, the three tiers, every token name. You may not invent a name outside it |
| `references/extraction-and-clustering.md` | Phases 1–3. How the literals are found, how they are clustered, the ΔE threshold and why, the hard cases, the consolidate-vs-separate decision rule |
| `references/migration-strategies.md` | Before Phase 4, and before any conversation about scope. Strangler-fig vs big-bang vs leaf-first, the selection rule, baseline-and-freeze, Law 2 migration, rollback, keeping the branch from rotting, the burndown |
| `references/framework-migrations.md` | When you know the stack. Plain CSS/SCSS, CSS Modules, styled-components/Emotion, Tailwind, framework overrides, inline-style React — each with real before/after |
| `assets/MIGRATION_PLAN.md` | When someone has to approve this. Fill it in; do not send a chat message |

---

## Script reference

All three are stdlib-only Python 3. Run them from this skill's root.

### `extract_literals.py` — the census

```sh
python -m scripts.extract_literals ./src
python -m scripts.extract_literals ./src --format json -o literals.json
python -m scripts.extract_literals ./src --format csv -o literals.csv
python -m scripts.extract_literals ./src --kind color --kind length --top 40
python -m scripts.extract_literals . --include-vendor      # the true total, once
```

| Flag | Effect |
|---|---|
| `--format report\|json\|csv` | Human, machine, or spreadsheet |
| `--kind KIND` | Repeatable: length, color, font-size, radius, duration, shadow, z-index, border-width, line-height, easing, tracking, color-function |
| `--top N` | Values listed per kind in the report (default 20) |
| `--min-count N` | Drop values occurring fewer than N times |
| `--include-vendor` / `--include-tokens` | Widen the walk |

### `cluster_values.py` — the proposal

```sh
python -m scripts.cluster_values literals.json -o ./proposal
python -m scripts.cluster_values literals.json -o ./proposal --spacing-tolerance 2
python -m scripts.cluster_values literals.json -o ./proposal --accent '#e8440a'
python -m scripts.cluster_values literals.json --dry-run     # report only
```

| Flag | Default | Meaning |
|---|---|---|
| `--spacing-tolerance PX` | 3.0 | How far a length may move to reach a step. Beyond this it is reported, not snapped |
| `--type-tolerance PX` | 3.0 | The same, for font sizes |
| `--color-tolerance DE` | 0.025 | OKLab ΔE below which two colors are one decision (≈7 sRGB code values) |
| `--duration-tolerance MS` | 60 | How far a duration may move |
| `--accent COLOR` | derived | Pin the brand seed instead of deriving it from the most-used chromatic color |

Tighten `--spacing-tolerance` to 2 on a codebase with real design intent behind its numbers; loosen it to 4 on one where everything was eyeballed. The tolerance you pick is the migration's single biggest risk dial, and the reconciliation report tells you what it bought you.

### `apply_codemod.py` — the mechanical part

```sh
python -m scripts.apply_codemod ./src -m proposal/mapping.json           # dry run
python -m scripts.apply_codemod ./src -m proposal/mapping.json --kind color --apply
python -m scripts.apply_codemod ./src -m proposal/mapping.json --only 'src/components/**' --apply
python -m scripts.apply_codemod ./src -m proposal/mapping.json --skip-review --apply
python -m scripts.apply_codemod ./src -m proposal/mapping.json --report
```

| Flag | Effect |
|---|---|
| *(none)* | Dry run. Unified diff to stdout. **The default** |
| `--apply` | Write. The only way anything changes |
| `--kind KIND` | Batch by kind. Repeatable |
| `--only GLOB` | Scope to part of the tree. Repeatable |
| `--skip-review` | Apply only the confident replacements; leave the ones that move a value visibly |
| `--report` / `--no-diff` | Counts instead of the diff |
| `--force` | Write over files with uncommitted changes. You will not need this |

Exit codes: 0 clean, 1 something was skipped (read the list — every skip is deliberate and explains itself), 2 bad invocation.

---

## A worked run, end to end

A real 8-file fixture — plain CSS, SCSS, two CSS Modules, JSX with inline styles and Tailwind arbitrary values, styled-components, a one-off marketing page, and a vendor override sheet. 223 literals.

```sh
python -m scripts.extract_literals ./src --format json -o literals.json
#   223 literal value(s) across 8 file(s)
#   distinct spacing values 27  (the closed scale has 18)
#   distinct colors         22
#   distinct shadows         6

python -m scripts.cluster_values literals.json -o ./proposal
#   81 rule(s) covering 180 occurrence(s); 24 need review;
#   53 need a design decision

cp proposal/tokens.css src/styles/tokens.css && git commit -am "tokens.css"

for kind in color spacing type radius stroke duration shadow z-index tracking; do
  python -m scripts.apply_codemod ./src -m proposal/mapping.json --kind "$kind" --apply
  git commit -am "migrate: $kind"
done
#   135 replacements across 7 files
```

| | Before | After |
|---|---:|---:|
| Audit errors | 151 | **46** |
| Audit warnings | 12 | 12 |
| L1 Tokens or nothing | 123 | **30** |
| L3 The scale is closed | 18 | **6** |
| L2 Parents own the gaps | 4 | 4 |
| L4 One home per component | 12 | 12 |
| L5 Layers, not specificity | 6 | 6 |

L1 and L3 collapse; L2, L4 and L5 do not move at all, because those are phases 4e–4g and nothing has been done to them yet. **That shape is what a correct run looks like.** A migration that claims to have fixed all five laws in one codemod has either deleted something or is not measuring.

The 46 remaining errors are, in full:

| Count | Finding | Waiting on |
|---:|---|---|
| 12 | `L4 inline-style` | Phase 4f — hand work, a class name each |
| 8 | `L1 raw-spacing` | Reconciliation: `22px` (20 or 24?), `34px`, `74px`, `13px` all-sides |
| 7 | `L1 raw-type` | Reconciliation: `47px` heading, `11px` meta, plus 5 skipped by the `font:` guard because the rule also sets `font-weight` |
| 5 | `L5 unlayered` | Phase 4g — the `@layer` wrapping |
| 5 | `L1 raw-color` | A `linear-gradient`, a `rgba()` scrim, two status tints with no Tier-2 role |
| 4 | `L2 child-margin` | Phase 4e — container by container |
| 4 | `L3 tw-arbitrary` | `py-[62px]`, `max-w-[1140px]`, `tracking-[-0.02em]`, `duration-[180ms]` — all reported |
| 1 | `L5 important` | Phase 4g, after layers |

Every one is a sentence in the reconciliation report or a phase that has not run. None is a surprise, and that is the actual deliverable.

---

## How to sell this to a client or a team

Migration only happens if somebody approves it. That approval is a business decision, and "the CSS is messy" is not a business case — it is a complaint, and it will be weighed against a feature. Make the argument properly.

### The argument

**Lead with the count, not the aesthetics.** Run Phase 1 and open with it: *"There are 1,431 hardcoded values across 212 files. 612 of them are the same eleven decisions repeated. 84% are mechanically replaceable in an afternoon."* That sentence is checkable, and it converts a taste argument into an arithmetic one.

**Name the cost that is already being paid.** Nobody funds tidiness. They fund the removal of a recurring cost, and this one is always already there:

| Symptom they already have | What it actually is |
|---|---|
| "Dark mode is a huge project" | Colors are hardcoded, so there is nothing to re-point. This is the big one — dark mode on a tokenized codebase is a day |
| "Every rebrand is a rewrite" | Same cause. A brand change should be one ramp seed |
| "The designer keeps filing 4px bugs" | Two owners for every gap. Each bug is real, individually trivial and collectively infinite |
| "Nobody can find where a style comes from" | Six homes per component. The cost is paid in minutes per developer per day, which is the largest number in this table |
| "Our accessibility audit failed on contrast" | Contrast was assumed, never measured. Roles make it measurable once instead of per-screen |

**Be specific about what they get at each stopping point.** This is the part that wins the meeting. Phases 1–3 cost days and deliver a document, and the document is useful even if nothing else happens. Phase 4 can stop after any batch. Phase 6 works on a codebase that is 20% migrated — that is the whole point of the baseline.

**Give the honest estimate, including the part that is not automatable.** Inflated confidence is how the second migration never gets funded.

| Phase | Cost, 150–400 file codebase | Risk |
|---|---|---|
| 1 Inventory | 1–2 hours, mostly reading | None. Changes nothing |
| 2–3 Cluster + propose | 1 day for the scripts, **2–4 days of design review** | None to the code. The review is where the time goes and it cannot be skipped |
| 4a Colors | 1 day including review | Low. Mechanical, visually verifiable |
| 4b Radius, stroke, shadow, motion | 1 day | Low. Few occurrences, contained |
| 4c Type | 1 day | Medium. Also removes the sibling `line-height` / `font-weight` declarations by hand |
| 4d Spacing | 1–2 days | **Medium.** Every snapped value moves something. This is where the screenshots earn their keep |
| 4e Law 2 (child margins → parent gap) | 2–5 days | **High.** Changes layout. Container by container, never bulk |
| 4f Law 4 (inline styles) | 1 day per ~30 offending components | Medium. Manual, but each one is small |
| 4g Law 5 (`!important`, layers) | 1–3 days | Medium. Do it after layers are in, never before |
| 5 Verify | Half a day per batch | — |
| 6 Gate | 2 hours | None |

Total for a typical mid-size app: **two to three weeks of one person's time**, of which roughly a third is design review rather than engineering, and about half is optional (4e–4g can be deferred behind the baseline indefinitely).

**Offer the small version first.** Most teams should hear: *"Give me two days. I will produce the inventory, the proposed token file and the reconciliation report. Nothing changes. Then you decide."* Approval for two days of read-only work is nearly free, and by the end of it the case makes itself with their own numbers.

### What not to promise

- **Not "no visual changes."** Snapping 13px to 12px moves something. Promise no *unreviewed* visual changes, and mean it.
- **Not a completion date for the whole thing.** Promise Phase 6 — the gate, with the baseline — and describe the rest as a burndown. This is true, and it is also the shape that survives a reprioritization.
- **Not that it will be fun.** Phases 4e–4g are tedious. Saying so makes the rest of the estimate credible.

### When to refuse

Say no, and say why, when:

- **The codebase is being replaced within two quarters.** Migrate the new one properly instead.
- **There is no design partner.** Phase 3's reconciliation needs someone with the authority to decide that 22px becomes 24. Without that, you are guessing on their behalf and you will be blamed for it.
- **Nobody will own the gate.** Without Phase 6 you are doing the work twice. Get the CI commitment before Phase 4, in writing, or stop after Phase 3 and hand over the document.
