# Selling the migration

How to argue for the migration to a client or a team, and what not to promise.

## 1. The argument

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

---

## 2. What not to promise

- **Not "no visual changes."** Snapping 13px to 12px moves something. Promise no *unreviewed* visual changes, and mean it.
- **Not a completion date for the whole thing.** Promise Phase 6 — the gate, with the baseline — and describe the rest as a burndown. This is true, and it is also the shape that survives a reprioritization.
- **Not that it will be fun.** Phases 4e–4g are tedious. Saying so makes the rest of the estimate credible.
