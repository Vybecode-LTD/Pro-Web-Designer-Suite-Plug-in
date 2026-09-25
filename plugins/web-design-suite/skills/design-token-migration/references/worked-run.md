# A worked run, end to end

One migration, from census to verified diff, with every command and what it printed.

## 1. A worked run, end to end

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
