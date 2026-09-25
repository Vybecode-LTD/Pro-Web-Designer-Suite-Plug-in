# Design Token Migration — Plan

> **How to use this template.** Fill in every `<>` from the output of Phases 1–3;
> none of it should be estimated by feel. Delete this block and any section that
> genuinely does not apply — but delete it deliberately, because each one exists
> because a migration failed without it.
>
> This document is the approval artifact. Send it, not a chat message. It is
> also the thing you will be held to in eight weeks, so under-promise in §4 and
> §9.

**Project:** `<client / product>`
**Repository:** `<repo>` @ `<base commit>`
**Author:** `<name>`  **Date:** `<date>`
**Design partner (required):** `<name>` — owns every decision in §5
**Engineering owner of the gate (required):** `<name>` — owns §8

---

## 1. Why now

`<Two or three sentences. Name the recurring cost that is already being paid,
not the untidiness. Examples that work: "dark mode has been scoped three times
and abandoned three times", "the rebrand needs to ship in Q3", "the
accessibility audit failed on contrast in eleven places", "designers filed 34
spacing bugs last quarter and we closed 11". Examples that do not work: "the CSS
is messy".>`

---

## 2. What is actually in there

From `python -m scripts.extract_literals <src> --format json`, run on `<commit>`:

| Measure | Count | For reference |
|---|---:|---|
| Files with styles | `<n>` | |
| Hardcoded values total | `<n>` | |
| …in component files | `<n>` (`<n>`%) | Also break Laws 2, 4 and 6 |
| Distinct spacing values | `<n>` | The closed scale has **18** |
| Occurrences off the 4px grid | `<n>` | |
| Distinct colors | `<n>` | |
| Distinct font sizes | `<n>` | The type scale has **11** |
| Distinct shadows | `<n>` | The elevation ladder has **6** |
| Distinct z-indexes | `<n>` | The ladder has **8** |
| Audit violations at baseline | `<n>` errors, `<n>` warnings | |

From `reconciliation.md`:

| Outcome | Occurrences | Share |
|---|---:|---:|
| Mechanically replaceable | `<n>` | `<n>`% |
| — needs a human to look at the diff | `<n>` | `<n>`% |
| Needs a design decision | `<n>` | `<n>`% |

> The third row is the only one with a person's name on it. It is the schedule.

---

## 3. Scope

### In

`<List the directories, in migration order — leaves first. Name them.>`

- [ ] `<src/components/…>` — `<n>` files, `<n>` literals
- [ ] `<src/features/…>`
- [ ] `<src/pages/…>`

### Out, and why

| Excluded | Reason | Handled how |
|---|---|---|
| `<vendor/, node_modules/>` | Third-party, has an upstream | `@layer vendor` — layered, never edited |
| `<marketing/landing-*>` | Deliberately off-system, `<not edited since date>` | Frozen behind the baseline |
| `<legacy/admin>` | `<being replaced in Q4>` | Frozen behind the baseline |

### Explicitly not in this project

- Consolidating styling technologies (`<SCSS + CSS Modules + styled-components>` stay as they are; they will all read the same tokens)
- Any visual redesign
- Any component API change

---

## 4. Phases and effort

| Phase | Deliverable | Effort | Calendar | Risk |
|---|---|---|---|---|
| 1 Inventory | `literals.json`, census | `<2h>` | `<wk 1>` | None — changes nothing |
| 2–3 Cluster & propose | `tokens.css`, `mapping.json`, `reconciliation.md` | `<1d>` + `<2–4d review>` | `<wk 1>` | None to code |
| 4a Colors | Codemod batch | `<1d>` | `<wk 2>` | Low |
| 4b Radius / stroke / shadow / motion | Codemod batches | `<1d>` | `<wk 2>` | Low |
| 4c Type | Codemod + sibling cleanup | `<1d>` | `<wk 3>` | Medium |
| 4d Spacing | Codemod batch | `<1–2d>` | `<wk 3>` | **Medium-high** — values move |
| 4e Law 2: child margins → parent gap | Hand work, per container | `<2–5d>` | `<wk 4–5>` | **High** — changes layout |
| 4f Law 4: inline styles | Hand work, per component | `<1d / 30 components>` | `<wk 5–6>` | Medium |
| 4g Law 5: layers, `!important` | Hand work | `<1–3d>` | `<wk 6>` | Medium |
| 5 Verify | Audit diff + VRT per batch | `<0.5d per batch>` | throughout | — |
| 6 Gate | Baseline + CI + pre-commit hook | `<2h>` | **`<wk 1>`** | None |

**Total: `<n>` days of one person, of which roughly `<n>` are design review rather than engineering.**

Phases 4e–4g are optional and can be deferred indefinitely behind the baseline. Everything before them delivers value on its own.

---

## 5. Decisions needed from design

These block Phase 4. Each is a row in `reconciliation.md` and each needs a name and a date.

| # | Decision | Options | Occurrences | Owner | Due |
|---|---|---|---:|---|---|
| 1 | `<22px padding>` | `<20px --pad-inline-sm / 24px --pad-card>` | `<n>` | `<name>` | `<date>` |
| 2 | `<47px heading>` | `<44px --type-h1 / fluid --text-5xl>` | `<n>` | | |
| 3 | `<the four near-identical grays>` | `<consolidate to --fg-muted / keep two>` | `<n>` | | |
| 4 | `<brand accent seed>` | `<derived #xxxxxx / the official brand hex>` | — | | |

### Contrast changes requiring sign-off

| Original | Proposed role / surface | Before | After | Verdict |
|---|---|---:|---:|---|
| `<#6b6b6b>` | `<--fg-subtle on --bg-sunken>` | `<4.77:1>` | `<4.60:1>` | `<PASS>` |

> Any row that crosses 4.5:1 or 3:1 downward is a blocker, not a note.

---

## 6. Risk and mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| A snapped value visibly moves something | **High** | Low | Every value moving >2px is listed in `reconciliation.md` and gets before/after screenshots in its own commit |
| A Law 2 change collapses a layout | Medium | **High** | One container per commit; measured gaps before and after; §7 rollback |
| A color maps to the wrong role | Medium | Medium | Measured contrast table reviewed before Phase 4a; color batch is one revert |
| Branch rots against main | Medium | Medium | Strangler-fig: each directory merges within a day. Conflicts resolved by re-running the codemod, never by hand |
| Migration stalls after Phase 3 | **High** | Low | The baseline lands in week 1, so the debt is already frozen. Stalling costs the remaining fix, not the whole benefit |
| The gate gets disabled | Medium | **High** | Named owner in this document's header; pre-commit hook plus CI; baseline regenerated only after a migration batch, never to silence a failure |
| A codemod corrupts a file | Low | **High** | Dry-run by default; refuses files with uncommitted changes; atomic temp-file writes behind brace-balance and declaration-count checks |

---

## 7. Rollback

- Branch `<migrate/tokens>`, tagged `<migration-base>` before the first change.
- One commit per batch, message naming the batch and the replacement count.
- Revert one batch: `git revert <sha>`.
- Revert everything: `git revert --no-commit <migration-base>..HEAD && git commit`.
- `revert`, never `reset` — the branch is shared by then.

| Symptom | Action |
|---|---|
| One component looks wrong | Fix forward — it is one token and you know the batch |
| One page looks wrong | Revert that batch, re-run with `--skip-review`, re-apply |
| Anything functionally broken | Revert immediately, investigate after |
| Contrast regression | Revert the color batch — the mapping is wrong everywhere, not here |

---

## 8. Definition of done

Not "the migration is finished". Finished is:

- [ ] `tokens.css` is on main, imported first, and is the only file with literal values in the migrated regions
- [ ] `python -m scripts.audit_design <src>` exits **0** against the committed baseline
- [ ] `.design-baseline.json` is committed, and has only shrunk since it was created
- [ ] The gate runs in CI **and** in a pre-commit hook, owned by `<name>`
- [ ] Every in-scope directory in §3 is checked off
- [ ] Every decision in §5 is resolved, with the decision recorded in `reconciliation.md`
- [ ] No contrast ratio decreased below 4.5:1 (body) or 3:1 (large text, UI) — measured, not assumed
- [ ] Visual regression run on every in-scope route; every diff either approved or fixed
- [ ] Dark mode toggles correctly with **zero** component-level overrides — this is the real test of whether the token layer works
- [ ] `<n>` remaining violations are documented, frozen and attributed to a named out-of-scope region

### The number we are committing to

| | At baseline | At done |
|---|---:|---:|
| Audit errors | `<n>` | `<n>` |
| Audit warnings | `<n>` | `<n>` |
| Violations growing per week | `<n>` | **0** |

> The last row is the one that matters. A frozen 190 is a schedulable problem;
> a growing 40 is a condition.

---

## 9. What we are not promising

- **Not "no visual changes."** Snapping 13px to 12px moves something. We promise no *unreviewed* visual change.
- **Not a completion date for Phases 4e–4g.** They are a burndown behind a gate that already holds.
- **Not that the remaining `<n>` violations will reach zero.** `<Region>` is deliberately out of scope and staying frozen.

---

## 10. Progress

Updated `<weekly>`, from `python -m scripts.audit_design <src> --json`.

| Week | Total | Frozen | Fixed | Merged |
|---|---:|---:|---:|---|
| 0 | `<n>` | 0 | 0 | Inventory |
| 1 | `<n>` | `<n>` | 0 | `tokens.css` + baseline — **debt stops growing** |
| 2 | | | | |
