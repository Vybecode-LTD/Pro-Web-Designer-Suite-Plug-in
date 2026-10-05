# A worked run, end to end

One migration, from census to verified diff, with every command and what it printed.

## 1. A worked run, end to end

An 8-file fixture: plain CSS, SCSS, two CSS Modules, JSX with inline styles and Tailwind arbitrary values, styled-components, a one-off marketing page, and a vendor override sheet. It ships with the plugin's tests (`tests/fixtures/worked-run`), and a test reruns this page against it, so every number below is what the tools print today.

```sh
python -m scripts.extract_literals ./src                 # read the census first
#   120 literal value(s) across 7 file(s).
#   distinct spacing values 22 (the closed scale has 18)
#   distinct colors 16
#   distinct shadows 4 (the elevation ladder has 6)
#   ! excluded 1 vendor file(s): src/vendor/datepicker-overrides.css
python -m scripts.extract_literals ./src --format json -o literals.json

python -m scripts.cluster_values literals.json -o ./proposal
#   cluster_values: 68 rule(s) covering 103 occurrence(s); 16 need review; 23 need a design decision.

cp proposal/tokens.css src/styles/tokens.css && git commit -am "tokens.css"

for kind in color spacing type radius stroke duration shadow z-index tracking; do
  python -m scripts.apply_codemod ./src -m proposal/mapping.json --kind "$kind" --apply
  git commit -am "migrate: $kind"
done
#   91 replacements: color 30, spacing 24, type 10, radius 9, stroke 5, duration 5, shadow 4, z-index 4
```

| | Before | After |
|---|---:|---:|
| Audit errors | 119 | **37** |
| Audit warnings | 4 | 4 |
| L1 Tokens or nothing | 103 | **24** |
| L3 The scale is closed | 5 | **2** |
| L2 Parents own the gaps | 3 | 3 |
| L4 One home per component | 2 | 2 |
| L5 Layers, not specificity | 6 | 6 |

L1 and L3 collapse; L2, L4 and L5 do not move at all, because those are phases 4e–4g and nothing has been done to them yet. **That shape is what a correct run looks like.** A migration that claims to have fixed all five laws in one codemod has either deleted something or is not measuring.

The 37 remaining errors are, in full:

| Count | Finding | Waiting on |
|---:|---|---|
| 10 | `L1 raw-spacing` | Reconciliation: `74px`, `13px`, `14px` and `12px` all-sides; the SCSS page's `20px`, `32px` and `48px` gaps and `40px` and `64px` padding; and the card's bleed shorthand, which is the L2 row's to fix |
| 5 | `L5 unlayered` | Phase 4g — the `@layer` wrapping |
| 4 | `L1 raw-color` | A `linear-gradient`, two `rgba()` scrims, and a ghost-button border with no Tier-2 role |
| 4 | `L1 raw-type` | Reconciliation: the `47px` heading and the `11px` note, plus 2 skipped by the `font:` guard because the rule also sets `font-weight` or `line-height` |
| 3 | `L2 child-margin` | Phase 4e — container by container |
| 2 | `L3 tw-arbitrary` | `py-[3px]` and `text-[11px]` — both reported |
| 2 | `L4 inline-style` | Phase 4f — hand work, a class name each |
| 2 | `L1 raw-weight` | The weights beside those raw sizes; the `--type-*` role carries them |
| 2 | `L1 raw-size` | `max-width: 1140px` and `560px`: a width token is a decision |
| 1 | `L1 raw-stroke` | `outline-offset: 2px` |
| 1 | `L1 sass-literal` | `$gutter: 24px` |
| 1 | `L5 important` | Phase 4g, after layers |

Every one is a sentence in the reconciliation report or a phase that has not run. None is a surprise, and that is the actual deliverable.
