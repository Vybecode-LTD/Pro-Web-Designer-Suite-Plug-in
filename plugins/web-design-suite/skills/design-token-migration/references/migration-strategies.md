# Migration Strategies

How to sequence a token migration so that it finishes, or so that stopping halfway still leaves the codebase better than you found it.

The technical work is in `extraction-and-clustering.md` and the scripts. This file is about the thing that actually decides the outcome: **order, scope and commitment**. Most failed migrations were technically correct.

## Contents

1. [The three strategies](#1-the-three-strategies)
2. [The selection rule](#2-the-selection-rule)
3. [Baseline-and-freeze, in detail](#3-baseline-and-freeze-in-detail)
4. [Per-directory order: why you start at the leaves](#4-per-directory-order-why-you-start-at-the-leaves)
5. [Batch order within a directory](#5-batch-order-within-a-directory)
6. [Migrating Law 2 safely](#6-migrating-law-2-safely)
7. [Migrating Law 4 and Law 5](#7-migrating-law-4-and-law-5)
8. [Rollback](#8-rollback)
9. [Keeping a migration branch from rotting](#9-keeping-a-migration-branch-from-rotting)
10. [The burndown](#10-the-burndown)
11. [Anti-patterns](#11-anti-patterns)

---

## 1. The three strategies

### Big-bang

One branch. Every file. Merged at once.

**When it works:** under ~40 files, one developer, no parallel feature work, and a test suite or a Storybook that covers the visual surface.

**Why it usually does not:** the branch is unreviewable, so it gets approved rather than reviewed. It conflicts with every other branch in flight, so it gets rebased until someone gives up. And its value is zero until the day it lands, which means any reprioritization destroys all of it. A big-bang migration is a bet that nothing else will be urgent for three weeks, and something else is always urgent.

**If you do it:** still commit per kind (`--kind color`, then `--kind spacing`), so the *history* is reviewable even though the branch is not. That one habit is what makes a bisect possible six weeks later.

### Strangler-fig — the default

Stand the new system up beside the old one, migrate region by region, and let the old one shrink until it is empty.

Concretely: `tokens.css` lands first, on its own, changing nothing. Then each directory is migrated and merged independently, smallest first. The gate goes on immediately with a baseline (§3), so unmigrated code is frozen while migrated code is enforced.

**Why it is the default:** every merge is small enough to review, value arrives continuously, and the work survives being interrupted — which it will be. There is no "migration branch" to rot because there is no long-lived branch at all.

**The cost:** the codebase is visibly half-migrated for weeks, and some component somewhere reads a token while its sibling reads a literal. That is genuinely ugly and it is genuinely fine. The baseline makes the inconsistency measurable instead of merely annoying.

### Leaf-first

A refinement of strangler-fig rather than an alternative: order the regions by dependency depth and start with the leaves — the components nothing else styles.

**When it matters:** on a codebase with real cross-component styling (`.pricing-page .card__title { … }`). Migrating a container before its children means migrating the same declarations twice, once in the container's reach-in rules and again when you get to the child.

---

## 2. The selection rule

Score the codebase, then read the row. Do not negotiate with it — the inputs are facts.

| Input | Value | Points |
|---|---|---|
| Files with styles | < 40 | 0 |
| | 40–150 | 2 |
| | > 150 | 4 |
| Visual test coverage | Storybook or VRT over most components | 0 |
| | Storybook over some | 1 |
| | None | 3 |
| Developers touching CSS in a typical week | 1 | 0 |
| | 2–4 | 2 |
| | 5+ | 4 |
| Release cadence | Monthly or slower | 0 |
| | Weekly | 1 |
| | Continuous | 3 |

| Total | Strategy |
|---|---|
| 0–3 | **Big-bang** is safe. One branch, per-kind commits, one review |
| 4–8 | **Strangler-fig.** Directory by directory, merged independently |
| 9+ | **Strangler-fig + leaf-first + baseline on day one.** Do not attempt more than one directory per week, and get the CI gate in before the second directory |

Two overrides that beat the score:

- **No design partner → stop after Phase 3 regardless of score.** The reconciliation report needs someone with the authority to decide that 22px becomes 24. Without that you are guessing on their behalf, and you will be blamed for the guess.
- **A rewrite is already funded within two quarters → do not migrate.** Put the effort into the token contract for the new codebase.

---

## 3. Baseline-and-freeze, in detail

The single highest-leverage move in this skill, and the one people skip.

### The mechanism

```sh
python -m scripts.audit_design ./src --write-baseline .design-baseline.json
git add .design-baseline.json
git commit -m "freeze the remaining design debt"
```

The baseline records a stable identity for every existing violation — file, rule and snippet, deliberately **not** the line number, so that editing the line above does not resurrect it. From that commit on, the gate fails only on violations the baseline does not contain.

### Why this beats a rewrite

| | Rewrite | Baseline-and-freeze |
|---|---|---|
| Time until the debt stops growing | The day it merges. Maybe never | **Today** |
| Approval needed | A project | A two-hour PR |
| Value if abandoned halfway | Zero | Everything already frozen stays frozen |
| Effect on parallel feature work | Blocks or conflicts | None. New code is simply held to the standard |
| Reviewability | One enormous diff | One JSON file |

The insight is that **the debt's rate of growth matters more than its size.** A codebase with 1,400 violations that cannot grow is a finite, schedulable problem. A codebase with 400 violations growing by 30 a week is not a problem, it is a condition. Turning the gate on today converts the second into the first, and it does it before anybody has agreed to fix anything.

### Why it beats turning the gate on without one

Because otherwise the gate is red on day one, and a build that is always red is a build nobody reads. Within a week someone adds `--no-verify` to their muscle memory and you have spent your credibility for nothing. A gate's only asset is that red means something.

### Working the baseline down

The file is a JSON array of violation keys. It only shrinks. Two rules keep it honest:

1. **Regenerate it only after a migration batch**, never to "fix" a failing build. A baseline regenerated to silence a failure is a `.eslintignore` with extra steps, and it is how this ends up in the same graveyard as the last lint rollout.
2. **Never add an entry by hand.** If a genuine exception exists, it gets an inline pragma with a named reason, visible in review:

```css
/* stylelint-disable-next-line design/component-margins, selector-max-type -- design-audit-ignore-next-line: L2 -- CMS-controlled rich text, see ADR-014 */
.cms-body h2 { margin-block-start: var(--space-subsection); }
```

A pragma survives review because it is argued. A baseline entry survives review because nobody reads JSON.

### Two gates, two jobs

```sh
# pre-commit: only what you touched, fast, before the context switch —
# web-design-studio's shipped hook, not a hand-written one
cp <web-design-studio>/assets/configs/pre-commit-design-gate.sh .git/hooks/pre-commit
cp <web-design-studio>/assets/configs/pre-commit-design-gate.sh .git/hooks/commit-msg

# CI: everything, against the baseline
python -m scripts.audit_design ./src
```

Use the shipped hook rather than a two-line `git diff --cached` loop. It exits at once on an empty commit; without that, the audit falls back to the whole tree, and a hook that takes forty seconds on an empty commit is a hook that gets removed. It also keeps file names with spaces in one piece, which `$FILES` unquoted does not, and it runs the accessibility floor too when `scripts/a11y_static.py` is vendored.

The pre-commit hook matters more, because CI tells you after you have moved on and the cost of a fix triples once you have.

---

## 4. Per-directory order: why you start at the leaves

Order directories by how many other things style them. Migrate the ones nothing reaches into first.

A typical order:

| Order | Region | Why here |
|---|---|---|
| 1 | `tokens.css` alone | Lands the vocabulary. Changes nothing. Merge it on its own and let it sit for a day |
| 2 | Primitives: `Button`, `Badge`, `Input`, `Icon` | Leaves. Nothing styles them from outside. High occurrence counts, so the biggest number moves first |
| 3 | Composites: `Card`, `Table`, `Modal`, `Menu` | Built from migrated primitives; any reach-in rules are now visible against a tokenized child |
| 4 | Layout: page shells, grids, containers | Where Law 2 lives. Do this only after the children are stable, because this is the phase that moves pixels |
| 5 | Pages and routes | The most one-off values, the least reuse, the lowest value per hour |
| 6 | Marketing / landing pages | Often deliberately off-system. Frequently correct to leave behind the baseline forever |
| — | Vendor overrides | Never. Layer them |

Four reasons the leaves come first, in order of how much they matter:

1. **Highest occurrence per file.** A `Button.module.css` migration might replace forty literals across the app's rendered output. A page file replaces six.
2. **Lowest blast radius.** A button that is 1px tighter is a diff. A page container that is 4px tighter reflows everything inside it.
3. **Proof it works.** The first merged directory is the one that buys you the rest of the project. Pick one that is small, visible and boring.
4. **Reach-in rules become visible.** Once `Card.module.css` reads tokens, a `.pricing-page .card__title { font-size: 20px }` in a page file stands out as the Law 4 violation it always was.

---

## 5. Batch order within a directory

Inside one directory, apply one kind at a time, in this order, committing between each.

| # | Batch | Risk | Why here |
|---|---|---|---|
| 1 | `--kind color` | Low | Mechanical, high volume, visually obvious if wrong. Best confidence-per-hour in the whole project |
| 2 | `--kind radius`, `--kind stroke` | Low | Small, boring, near-invisible. Good second commit |
| 3 | `--kind shadow`, `--kind duration` | Low | Few occurrences, contained. The elevation swap is visible but flattering |
| 4 | `--kind type` | Medium | Whole-declaration rewrites. Leaves sibling `line-height` / `font-weight` to delete by hand |
| 5 | `--kind spacing` | **Medium-high** | Every snapped value moves something. This is what the screenshots are for |
| 6 | `--kind z-index` | Medium | Small but semantic. Review every single one against real stacking contexts |
| 7 | Law 2, by hand | **High** | §6. Never bulk |
| 8 | Law 4, by hand | Medium | §7 |
| 9 | Law 5 + layers | Medium | §7. Last, because it changes who wins |

Colors first is not arbitrary. It produces the largest visible win with the least layout risk, which is what gets the second batch approved.

---

## 6. Migrating Law 2 safely

> **A child never sets its own outer margin. Space between siblings comes from the parent's `gap`.**

This is the only law that cannot be migrated value by value, because fixing it changes layout. A codemod that deletes `margin-bottom: 16px` from a card without adding `gap: var(--gap-grouped)` to the container does not produce a tokenized layout; it produces a collapsed one. **The codemod deliberately refuses to touch it.**

### The procedure, per container

Work one container at a time. Never more.

**Step 1 — find the containers, not the children.**

```sh
python -m scripts.audit_design ./src --law L2 --json | \
  python -c "import json,sys,collections; \
  c=collections.Counter(f['file'] for f in json.load(sys.stdin)); \
  [print(n,f) for f,n in c.most_common()]"
```

The files at the top own the most orphaned margins. Each one is a container whose parent forgot to own the gap.

**Step 2 — measure what the gap actually is right now.** Not what the margin says. In a flex or grid container, adjacent margins do *not* collapse and the effective gap is `margin-bottom + margin-top`. In a block container they *do* collapse and the effective gap is `max(margin-bottom, margin-top)`. Two different answers from the same CSS, which is precisely why nobody can predict this by reading it.

Measure it in the browser:

```js
const kids = [...el.children];
console.table(kids.slice(1).map((k, i) => ({
  between: `${i}→${i + 1}`,
  gap: Math.round(k.getBoundingClientRect().top -
                  kids[i].getBoundingClientRect().bottom),
})));
```

**Step 3 — set the parent's gap to the measured value's nearest rung, chosen by relationship.**

```css
/* before: two owners, unpredictable result. example: before */
.list { display: flex; flex-direction: column; }
.list-item { margin-bottom: 16px; }
.list-item:last-child { margin-bottom: 0; }   /* the tell */
```

```css
/* after: one owner */
.list { display: flex; flex-direction: column; gap: var(--gap-grouped); }
```

That `:last-child { margin-bottom: 0 }` is the diagnostic. It only exists to undo a margin that should never have been set, and its presence is proof the pattern was always wrong.

**Step 4 — delete the child margins and the `:last-child` reset in the same commit.** Doing it in two commits means the intermediate state has double spacing, and somebody will screenshot that intermediate state.

**Step 5 — screenshot before and after.** This is the batch where you get it wrong.

### The three legal exceptions

Do not migrate these; they are correct:

| Pattern | Why it is legal |
|---|---|
| `margin: auto` / `margin-inline: auto` | Alignment, not spacing. It positions the element within its own box |
| `calc(var(--token) * -1)` | Cancelling a known token — a media bleed inside a padded card. The relationship is visible and it points at the same token it cancels |
| `> * + *` written in the **parent's** rule | The owl idiom. The parent still owns the gap; it is just expressing it as a margin because the container is not flex or grid |

The owl selector is the escape hatch for prose and CMS output where you cannot control the markup:

```css
.prose > * + * { margin-block-start: var(--space-block); }
```

Legal, because the rule lives in the parent's file and the parent still decides.

---

## 7. Migrating Law 4 and Law 5

### Law 4 — one home per component's styles

Inline styles cannot be codemodded, because moving a declaration into a stylesheet requires a class name, and a codemod that invents class names is a codemod nobody reviews.

Do them by hand, in batches of about ten components. The transformation is always the same shape:

```jsx
/* before — five homes for one table cell. example: before */
<td style={{ padding: '9px 11px', color: '#333333' }}>{r.name}</td>
```

```tsx
/* after — one home, in the stylesheet */
<td className={styles.cell}>{r.name}</td>
```
```css
.cell { padding: var(--pad-block-sm) var(--pad-inline-sm); color: var(--fg-default); }
```

The one legal inline style survives untouched: every key a custom property, passing a runtime *number* into the cascade.

```jsx
<li className={styles.card} style={{ '--card-span': span } as React.CSSProperties}>
```
```css
.card { grid-column: span var(--card-span, 1); }
```

This is different in kind, not in degree. It sets no visual property; it sets a variable. The visual decision stays in the stylesheet, stays themeable, stays lintable, and has a default for when the value is absent.

### Law 5 — layers, not specificity

Do this **after** the value migration, never before. Introducing layers changes which rule wins, and doing that while values are also changing makes every regression ambiguous.

The order that works:

1. **Declare the layer statement once**, first, before every `@import`, in the entry stylesheet:
   ```css
   @layer reset, vendor, tokens, base, layout, components, utilities, overrides;
   ```
   A layer's position is fixed the first time its name is used, so this line must come before anything that uses one.
2. **Wrap each existing file in the layer it belongs to.** Mechanical, one file per commit, no value changes in the same commit.
3. **Wrap vendor CSS in a low layer** — `@layer vendor` declared before `components`. This is the move that lets you delete `!important` instead of fighting it (`framework-migrations.md` §6).
4. **Then delete the `!important`s**, one file at a time, checking each. Most of them exist to beat a specificity fight that the layer order now settles. The ones that remain are usually beating *inline* styles, which means the real fix is Law 4 and belongs in that batch instead.

`!important` is not merely rude — it **inverts** layer order: an `!important` in an *earlier* layer beats one in a *later* layer. Every one you leave in makes the next override strictly harder, which is why removing them is worth a batch of its own.

---

## 8. Rollback

Every batch must be revertible in under a minute, by someone who was not involved. That property is what makes the risk acceptable, and it costs nothing if you set it up first.

**Before starting:**

```sh
git switch -c migrate/tokens
git tag migration-base                # the escape hatch
```

**During, one commit per batch**, message naming the batch and the count:

```
migrate(components): colors → role tokens [43 replacements, 7 files]
```

**Revert one batch:**
```sh
git revert <sha>          # values only — always safe, no manual conflict
```

**Revert everything:**
```sh
git revert --no-commit migration-base..HEAD && git commit -m "revert token migration"
```

**Why revert and not reset:** a migration branch is usually shared by the time anything goes wrong, and `reset` on a shared branch creates a second incident on top of the first.

### The rollback decision rule

| Symptom | Action |
|---|---|
| One component looks wrong | Fix forward. It is one token, and you know which batch |
| One *page* looks wrong | Revert that batch, re-run with `--skip-review`, re-apply. Something in the report's "Replacements to review" table was wrong |
| Anything is functionally broken (clipping, overflow, unclickable) | Revert immediately, investigate after. Almost always a z-index or a Law 2 batch |
| Contrast regression reported | Revert the color batch. Do not fix forward: the ramp mapping is wrong and it is wrong everywhere |

### What is not revertible

Law 2 work, once child margins are deleted and containers have gaps, is intertwined with real layout changes and usually with markup. Treat each Law 2 container as its own commit, merged on its own, and do not batch more than a handful before merging. This is the main reason Law 2 comes last.

---

## 9. Keeping a migration branch from rotting

A long-lived migration branch dies of merge conflicts. Every conflict is in a file somebody else also edited, and the resolution is always "take the teammate's version, re-run the codemod" — which is tedious enough that after the fourth time the branch gets abandoned.

Five habits, in order of effect:

**1. Do not have a long-lived branch.** Strangler-fig exists precisely so that each directory is a branch that lives for a day. This solves the problem rather than managing it.

**2. Rebase daily, never merge.** A migration branch's history should stay linear so that `git revert` on a batch still works after the fact.

**3. Resolve every conflict by re-running, never by hand.** During a *rebase* the sides are swapped: `--ours` is main — the teammate's version — and `--theirs` is your migration commit. Taking `--theirs` keeps your already-migrated file and silently drops their change; the codemod then finds nothing to replace and exits 0. Take `--ours`, then migrate it again:
   ```sh
   git checkout --ours -- path/to/conflicted.css
   git add path/to/conflicted.css
   python -m scripts.apply_codemod path/to/conflicted.css -m proposal/mapping.json --apply
   git add path/to/conflicted.css
   git rebase --continue
   ```
   The first `git add` marks the conflict resolved, which the codemod needs — it refuses files with uncommitted changes. The mapping is deterministic, so the result is the teammate's edit, migrated. Hand-resolving a tokenization conflict is how one file ends up half-migrated, and nobody will ever notice.

**4. Land `tokens.css` on main first, alone.** It changes no rendering. Once it is on main, every subsequent branch is only *using* tokens, not introducing them, and the conflict surface halves.

**5. Turn the gate on early so main stops moving away from you.** Every violation added to main while you are migrating is one you migrate twice. The baseline (§3) is what stops that, and it is why it belongs at the start of the project rather than the end.

---

## 10. The burndown

A migration without a visible number stops being a priority the moment something else happens. The audit provides the number for free.

```sh
python -m scripts.audit_design ./src --json | \
  python -c "import json,sys,collections; \
  d=json.load(sys.stdin); c=collections.Counter(f['law'] for f in d); \
  print(json.dumps({'total': len(d), **dict(sorted(c.items()))}))"
```

Run it on every commit to main, append to a CSV, and put it on a wall. What makes it a good burndown rather than a vanity metric:

- **Break it down by law, not just a total.** The laws fall at different rates and in a known order: L1 and L3 collapse in the codemod phases, L2 and L4 fall slowly by hand, L5 falls in one step when layers land. A chart that shows that shape is a chart people trust, because it matches what they can see happening.
- **Also chart the baseline file's length.** It only shrinks, and it shrinks in visible steps — one per merged directory. That is the most honest progress signal in the project.
- **Report *frozen* separately from *fixed*.** "1,431 violations, 0 growing" on day two is a genuine win and it is the one that pays for the rest of the work. Conflating it with "fixed" is how you end up promising a completion date you did not mean to.

A realistic shape for a mid-size app:

| Week | Total | Frozen | Fixed | What happened |
|---|---|---:|---:|---|
| 0 | 1,431 | 0 | 0 | Inventory |
| 1 | 1,431 | 1,431 | 0 | `tokens.css` + baseline merged. **Debt stops growing** |
| 2 | 1,120 | 1,120 | 311 | Colors, all directories |
| 3 | 812 | 812 | 619 | Spacing + radius + shadow, leaf components |
| 4 | 640 | 640 | 791 | Type; layout directory |
| 6 | 380 | 380 | 1,051 | Layers land; `!important` batch |
| 9 | 190 | 190 | 1,241 | Law 2, container by container |
| — | 190 | 190 | — | Remainder is marketing pages, deliberately frozen |

The last row is not a failure. Ending with a documented, frozen, non-growing remainder — and a gate that keeps it that way — is what success looks like on a real codebase.

---

## 11. Anti-patterns

| Anti-pattern | Why it fails | Instead |
|---|---|---|
| Migrating everything in one branch on a 200-file repo | Unreviewable, unrebasable, zero value until it lands | Strangler-fig, directory by directory |
| Turning the gate on with no baseline | Red on day one, ignored by day five, `--no-verify` by day ten | `--write-baseline`, then only new violations fail |
| Regenerating the baseline to fix a red build | It is now a `.eslintignore`. The gate is dead | Fix the violation, or add an argued inline pragma |
| Adding `--space-18` to absorb an 18px value | The scale is the mechanism. One exception makes it a menu | Snap it, or report it and let a designer decide |
| Codemodding child margins into gaps | Deletes spacing without adding it back. Collapsed layout | Container by container, by hand, with screenshots |
| Migrating vendor CSS | It has an upstream. It comes back on the next update | Layer it |
| Starting with the page files | Lowest occurrence, highest blast radius, least reuse | Leaves first |
| Doing values and layers in the same commit | Every regression becomes ambiguous | Layers after values, always |
| "We'll do the token file at the end" | Then nothing is enforceable during the migration | `tokens.css` lands first, alone, changing nothing |
| Promising no visual change | Snapping 13px to 12px moves something. You will be caught | Promise no *unreviewed* visual change |
