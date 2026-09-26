# Web Design Suite

Thirteen Claude skills for designing and building websites that look considered and **stay coherent when more than one person touches them**.

The suite exists because most design-system advice is a style guide — a document everyone agrees with and nobody enforces. This is a system with a gate on it. Every rule here is checkable by a script, and the script is wired into a pre-commit hook.

---

## The Nine Laws

Every skill in the suite enforces the same nine laws. They are reproduced verbatim in each skill's `references/token-contract.md` — byte-identical in all thirteen — so each skill carries the laws with it. Most still need web-design-studio beside them to run the gate; see **As individual skills** below.

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

**As a plugin** — everything at once. Add the folder (or the git URL) that holds
`.claude-plugin/marketplace.json`, then install by its full id:

```
/plugin marketplace add path/to/web-design-suite
/plugin install web-design-suite@web-design-suite
```

**As individual skills** — a skill folder can be installed on its own, but eight of
them run web-design-studio's `audit_design.py` as their gate, so install
web-design-studio beside any of them. (No packaged `.skill` files ship yet.)

**As a repo** — extract `skills/web-design-studio/assets/starter/styles/` into your project, wire the configs from `assets/configs/`, and point Claude Code at it.

---

Every script is plain Python and needs **Python 3.9 or newer**; the three browser
scripts need Node instead. The lint configs need a Node that stylelint 17 and
ESLint 10 both support: 20.19 or newer on the 20 line, 22.13 or newer on the 22
line, or 24 and later. Run the scripts
**by path, from your project's root**, so `src/` means your `src/` and every output
lands in your project, never inside the plugin. Below, `WDS` is the plugin's
`skills` folder (for a local install, `~/.claude/local-marketplaces/web-design-suite/skills`).

## Quick start on a new project

```bash
# 1. Tokens — derive the ramp from the brand, verify contrast
python "$WDS/web-design-studio/scripts/generate_color_ramp.py" "#e8440a" --name accent --format css
python "$WDS/web-design-studio/scripts/generate_type_scale.py" --base 16 --ratio 1.2 --fluid 380 1440 --preview

# 2. Build. Copy tokens.css / reset.css / base.css / layout.css.

# 3. Gate
python "$WDS/web-design-studio/scripts/audit_design.py" src/ --strict    # the design gate
python "$WDS/perf-budget-gate/scripts/perf_audit.py" dist/ --strict      # the performance gate
python "$WDS/a11y-audit-runner/scripts/a11y_static.py" src/ --strict     # the accessibility gate
```

## Quick start on an inherited codebase

```bash
M="$WDS/design-token-migration/scripts"
python "$M/extract_literals.py" ./src --format report                   # what is actually there
python "$M/extract_literals.py" ./src --format json -o literals.json     # the same, as data
python "$M/cluster_values.py" literals.json -o proposal/                 # what it was trying to be
python "$M/apply_codemod.py" ./src -m proposal/mapping.json --kind spacing          # dry run
python "$M/apply_codemod.py" ./src -m proposal/mapping.json --kind spacing --apply
python "$WDS/web-design-studio/scripts/audit_design.py" ./src --write-baseline .design-baseline.json  # freeze the rest
```

---

## What the gate actually catches

`audit_design.py` is stdlib-only Python 3 and understands cascade layers, component vs token files, and the documented exceptions (`margin:auto`, the owl selector in a parent's rule, `calc(var(--t) * -1)`, `em` as a ratio, `vw` as relational). It reads stylesheets, JS/TS/JSX, and the `<style>` blocks, `style=""` attributes and class lists of HTML, Vue, Svelte and Astro files (HTML email is `lint_email`'s job). A literal beside a `var()` is still a literal, and rules inside `@media` / `@container` are checked like any other. A folder with nothing auditable in it is an error, not a pass.

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

The suite's own tests live in `tests/` and need Python 3.9 or newer (they run on 3.9 to 3.14); git and a POSIX `sh` for the hook and recipe tests; Node for the browser-script and real-tool tests. From the plugin root:

```bash
python -B -m unittest discover -s tests -v
```

Set `WDS_PLUGIN_ROOT` to run the same tests against another copy of the suite — that is how every fix is shown failing on the release before it. Two kinds of tests need tools from npm:
- The real-browser tests (runtime contrast, modal and iframe focus, the matrix's state check, the starter CSS in Chromium) run when `WDS_NODE_MODULES` points at a `node_modules` holding `playwright` and `axe-core`. They never download a browser.
- The real-tool tests run the shipped ESLint, stylelint and Tailwind configs through the real tools. They take their tools from `WDS_ESLINT_MODULES`, `WDS_STYLELINT_MODULES`, `WDS_TAILWIND_MODULES` and `WDS_TAILWIND_V3_MODULES`; `tests/test_real_tools.py` says what each must hold.

In the plugin's repository, `npm ci` in `tooling/main` and `tooling/tailwind-v3` installs every one of those tools at pinned versions (a browser apart: see `tooling/README.md`), and the tests find them without any variable set (a toolchain installed for another operating system is ignored). Set a variable to `off` to switch its tests off.

What changed in each release is in `CHANGELOG.md`.

---

## License

MIT.
