# Web Design Suite

Thirteen Claude skills for designing and building websites that look considered and **stay coherent when more than one person touches them**.

The suite exists because most design-system advice is a style guide — a document everyone agrees with and nobody enforces. This is a system with a gate on it. Every rule here is checkable by a script, and the script is wired into a pre-commit hook.

---

## The Nine Laws

Every skill in the suite enforces the same nine laws. They are reproduced verbatim in each skill's `references/token-contract.md` — byte-identical in all thirteen — so any single `.skill` file works standalone.

1. **Tokens or nothing.** Literals live in exactly one file.
2. **Parents own the gaps.** A child never sets its own outer margin.
3. **The scale is closed.** Nothing between the steps.
4. **One home per component's styles.** Predict its appearance from one file.
5. **Layers, not specificity.** No `!important`, no IDs, nesting depth 2.
6. **Semantic before primitive.** Components read roles, never primitives.
7. **Density is a dial.**
8. **Novel patterns pass the gate.**
9. **Nothing ships un-audited.**

---

## The thirteen skills

| Skill | Owns |
|---|---|
| **web-design-studio** | The system. Tokens, spacing, style architecture, color, typography, layout, 17 navigation patterns, the invention protocol, accessibility, handoff, and `audit_design.py` — the gate. |
| **design-token-migration** | Getting an inherited codebase onto the system. Extract → cluster → propose → codemod → verify → freeze. |
| **figma-variables-sync** | Keeping design files and code speaking one vocabulary, and auditing a Figma file *before* the build. |
| **component-state-matrix** | Proving every component renders correctly across 7 states × 3 densities × 2 themes. |
| **landing-page-conversion** | The content and persuasion layer — positioning, message hierarchy, section sequencing, copy. |
| **design-critique-gate** | The adversarial pass before a client sees it. |
| **design-system-docs** | Documentation generated from the code, so it cannot drift. |
| **content-model-to-ui** | A database schema turned into on-system screens. |
| **email-template-system** | The same tokens compiled to HTML email, where these laws must bend. |
| **perf-budget-gate** | The performance sibling of the design gate. |
| **a11y-audit-runner** | The runtime accessibility gate — axe, keyboard, focus, forced-colors. |
| **design-system-versioning** | Changing the system without breaking its consumers. |
| **client-presentation-builder** | Making the case for the work in the room. |

**The usual chain on a client project:**

```
design-token-migration   (if you inherited it)
      ↓
figma-variables-sync     (if a designer handed it over)
      ↓
web-design-studio        ← design and build here
      ↓
content-model-to-ui      (if it is data-driven)
      ↓
landing-page-conversion  (if the page has to sell)
      ↓
component-state-matrix   (prove every state renders)
      ↓
perf-budget-gate         (prove it is fast)
      ↓
a11y-audit-runner        (prove it is usable by everyone)
      ↓
design-critique-gate     (survive the review)
      ↓
design-system-docs       (so the next person can use it)
      ↓
client-presentation-builder  (win the room)
      ↓
ship
      ↓
design-system-versioning (governs every change from here on)

email-template-system runs off to the side — same tokens, different
compile target, and the one place the laws deliberately bend.
```

---

## Install

**As a plugin** — everything at once:

```
/plugin marketplace add <this repo>
/plugin install web-design-suite
```

**As individual skills** — each `.skill` file installs with the *Add skill* button.

**As a repo** — extract `skills/web-design-studio/assets/starter/styles/` into your project, wire the configs from `assets/configs/`, and point Claude Code at it.

---

## Quick start on a new project

```bash
# 1. Tokens — derive the ramp from the brand, verify contrast
python -m scripts.generate_color_ramp "#e8440a" --name accent --format css
python -m scripts.generate_type_scale --base 16 --ratio 1.2 --fluid 380 1440 --preview

# 2. Build. Copy tokens.css / reset.css / base.css / layout.css.

# 3. Gate
python -m scripts.audit_design src/ --strict      # the design gate
python -m scripts.perf_audit dist/ --strict      # the performance gate
python -m scripts.a11y_static src/ --strict      # the accessibility gate
```

## Quick start on an inherited codebase

```bash
python -m scripts.extract_literals ./src --format report        # what is actually there
python -m scripts.cluster_values literals.json --out proposal/  # what it was trying to be
python -m scripts.apply_codemod proposal/mapping.json --kind spacing   # dry run
python -m scripts.apply_codemod proposal/mapping.json --kind spacing --apply
python -m scripts.audit_design ./src --write-baseline .design-baseline.json  # freeze the rest
```

---

## What the gate actually catches

`audit_design.py` is stdlib-only Python 3 and understands cascade layers, component vs token files, and the documented exceptions (`margin:auto`, the owl selector in a parent's rule, `calc(var(--t) * -1)`, `em` as a ratio, `vw` as relational).

- **L1** raw lengths, colors, shadows, durations, easings, radii, z-indexes, font sizes and weights — including literals **disguised inside a Tier-3 socket declaration**, which look tokenized and are not
- **L2** child margins in components, and Tailwind `space-x/y-*`
- **L3** off-scale values and Tailwind arbitrary values
- **L4** JSX inline styles that set visual properties, plus a **cross-file pass** catching a class styled from two files or the same property owned twice
- **L5** `!important`, ID selectors, nesting depth, unlayered stylesheets, layer-statement order and position
- **L6** Tier-1 primitives read from component code

Escape hatches are comment pragmas, so every exception is visible in review:

```css
/* design-audit-ignore-next-line: L2 -- CMS flow container, see ADR-014 */
```

Adopt it on a legacy repo with `--write-baseline`: the gate goes on today and the existing debt is frozen rather than growing.

---

## Regression tests

The suite's own tests live in `tests/` and need only Python 3 (Node for the browser-script tests, which use a stub instead of a real browser). From the plugin root:

```bash
python -m unittest discover -s tests -v
```

Set `WDS_PLUGIN_ROOT` to run the same tests against another copy of the suite.

---

## License

MIT.
