# The project contract

What a project tells the suite once, instead of flag by flag on every script: where its tokens are, which files are components, which stack it uses, its budgets and its baselines. Two files carry it. `.design-suite.json` is the project's own, written by hand. `contract.json` is generated from the project's tokens.

## 1. `.design-suite.json`

At the project's root:

```json
{
  "schema": 1,
  "tokens": ["src/styles/tokens.css"],
  "emailTokens": "emails/email-tokens.json",
  "components": ["src/widgets/**/*.css"],
  "stack": "tailwind-v4",
  "budgets": {"perf": "perf-budget.json", "a11y": "a11y-budget.json"},
  "baselines": {"audit": ".design-baseline.json", "a11y": ".a11y-baseline.json",
                "perf": ".perf-baseline.json", "docs": "docs/baseline.json",
                "snapshots": "snapshots/", "system": "published/system.json"},
  "hooks": {"designGate": true, "generatedFiles": true, "tokenDiff": true}
}
```

| Key | Holds |
|---|---|
| `schema` | `1`. The only key required |
| `tokens` | The project's token files: a `tokens.css`, a `contract.json`, or a list. A later file's value wins, step by step for a ramp or a scale, so two files may each hold part of one ramp |
| `emailTokens` | The email build's own `email-tokens.json`, a different file that only the email scripts read |
| `components` | Globs that add to the component files the rule spec names. `*` and `?` stay within a folder, and `**/` is any number of folders, none included |
| `stack` | `vanilla-css`, `css-modules`, `tailwind-v3` or `tailwind-v4` |
| `budgets` | `perf` and `a11y`: the budget files |
| `baselines` | `audit`, `a11y`, `perf`, `docs` and `snapshots`: where each gate keeps its baseline. `system`: the published snapshot, the system as consumers have it, which `diff_system.py` compares against |
| `hooks` | Turns the plugin's hooks on for this project, each `true` or `false`. `designGate`: after each edit Claude makes to a file the audit reads, `audit_design.py` runs on it, in the config's folder, and Claude hears what it found. `generatedFiles`: Claude may not edit a file that says it is generated (`DO NOT EDIT`, `@generated`) in its first 800 characters, and is told to change its source. `tokenDiff`: after each edit Claude makes to one of the config's `tokens`, `diff_system.py` compares them with `baselines.system`, and Claude hears the release that makes, each breaking change and each contrast pair that crossed a WCAG floor. An additive edit is silent, and so is the hook until the snapshot exists |

- **Finding it.** A script walks up from the working directory to the first `.design-suite.json`, and never past the folder that holds `.git`: a config above the repository is not the repository's.
- **Paths** are relative to the file, so the scripts agree from any working directory.
- **Precedence.** A flag, or a path named on the command line, beats the config, and the config beats the script's own default. `--tokens other.css` replaces the config's token files; the config's other keys still hold.
- **Mistakes.** An unknown key, or a value of the wrong shape, stops the script with exit 2 and a message that names the key. So does a token file it lists that does not exist.

Each skill whose scripts read the config keeps a copy of the plugin's `shared/project_config.py` beside them, so a skill installed on its own still has one. Its docstring is the schema.

## 2. `contract.json`

design-system-docs' `extract_system.py --contract FILE` writes it from the project's tokens: the token system's default values, by tier.

| Section | Holds |
|---|---|
| `ramps` | Each Tier-1 colour named `--<ramp>-<step>` with a numeric step, in step order |
| `scales` | The other Tier-1 values, by their first name segment: `space`, `radius`, `text`… |
| `breakpoints` | `--bp-*` |
| `constants` | A Tier-1 value whose name has one segment: `--density` |
| `roles` | Every Tier-2 token, as written |

Only a token with a default value is in it; one declared only in a theme or under a condition is not.

A script that takes a `tokens.css` instead reads it the same way: the custom properties of a rule whose selector starts with `:root` (or `html`, `:where(:root)`, `*`), outside any at-rule but `@layer`, and with no theme or density selector that names a value. It cannot see what extract_system sees, so it takes a token's tier from its value alone: a value that reads another token is a role, and a literal is Tier 1. extract_system reads the name first. On the starter's `tokens.css` the two disagree about eight names, none of them a ramp step or a breakpoint: seven roles with a literal value (`--bg-hover`, `--space-fluid-sm`) and `--shadow-focus`, which reads a token. A `contract.json` is the exact form; give the scripts one when a project's roles matter.

## 3. What each script takes from the project's tokens

Each takes `--tokens FILE` (repeatable), a `tokens.css` or a `contract.json`, and without it the token files the config lists.

| Skill | Script | What the project's tokens change |
|---|---|---|
| web-design-studio | `audit_design.py` | A token file the project names is a token file wherever it sits (`src/design/system.css`), so its literals are allowed. The ramps it declares (`--brand-500`) are Tier-1 colours with a role, so a component reading one is a Law 6 leak, as `--accent-500` is. The config's `components` globs add to the component files, and `baselines.audit` is the baseline without `--baseline` |
| web-design-studio | `stylelint.config.mjs`, `eslint.design.config.mjs` | What the audit takes, read from the working directory with no flag. For stylelint, a token file the project names is a token file, so its literals are allowed. A step of a ramp it declares has a role in both configs: stylelint refuses it in a component file or a `components` layer, and ESLint in an inline custom property and in a `(--name)` class |
| figma-variables-sync | `figma_audit.py` | Its ramps replace the studio's ramps of the same name. A scale it declares (spacing, radius, type, stroke, z, duration, leading, tracking, weight, breakpoints) replaces the studio's: its steps, not both, so the scale stays closed. A fluid `clamp()` type step counts at both ends |
| figma-variables-sync | `figma_to_tokens.py` | Its names join the vocabulary, so `color/brand/500` comes back as `--brand-500`, recognised, in its tier. The starter's names keep theirs. A ramp step it writes in OKLCH comes back as that exact value |
| design-system-docs | `extract_system.py` | Reads the CSS token files, and writes `contract.json` with `--contract` |
| design-system-versioning | `diff_system.py` | Takes a `contract.json` as either snapshot. Without an `old` snapshot, it is `baselines.system`. Without a `new` one, the candidate is the project's token files: its tokens.css files as one snapshot, or, when the list holds a contract, every file read as above, in order, as a contract. Against a contract, the other side is cut down to what a contract holds, default values and tiers, so a theme or a note it leaves out is not a change |
| design-token-migration | `cluster_values.py` | Its steps of the contract's six ramps (`neutral`, `accent` and the four status ramps) replace the derived ones, step by step, and `tokens.css` writes its values. A step it lacks is built as before, from its own accent step nearest 500. `--accent` beats its accent ramp. A ramp the contract does not name has no roles to land on, and the reconciliation report says so |

## 4. Who reads the other keys

A flag beats each of these, and each falls back to the script's own default.

| Key | Read by |
|---|---|
| `components` | web-design-studio's `audit_design.py`, and its stylelint and ESLint configs. For ESLint, a JSX or TSX file a glob matches is a component file |
| `stack` | content-model-to-ui's `scaffold_ui.py`: `tailwind-v3` and `tailwind-v4` scaffold Tailwind; `css-modules` and `vanilla-css` scaffold CSS Modules, the nearer of its two |
| `emailTokens` | email-template-system's `build_email.py` and `lint_email.py --source`. They never read `tokens`: the email build has its own projection of the system |
| `tokens` (CSS only) | client-presentation-builder's `build_presentation.py`, which builds the deck on the project's `tokens.css` files, in order. A contract cannot style a deck |
| `budgets.perf` | perf-budget-gate's `perf_audit.py` and `measure_vitals.mjs` |
| `budgets.a11y` | a11y-audit-runner's `a11y_runtime.mjs` |
| `baselines.audit` | web-design-studio's `audit_design.py` |
| `baselines.a11y` | a11y-audit-runner's `a11y_static.py` |
| `baselines.perf` | perf-budget-gate's `perf_audit.py` |
| `baselines.docs` | design-system-docs' `build_docs.py --check`. A baseline the config names but that is missing is an error, as a named `--baseline` is |
| `baselines.snapshots` | component-state-matrix's `snapshot_matrix.mjs` |
| `baselines.system` | design-system-versioning's `diff_system.py`, as `old` when none is named, and the `tokenDiff` hook |

**The Node reader.** `project_config.mjs`, a copy of the plugin's `shared/project_config.mjs`, finds and checks the config by the same rules as `project_config.py`, with the same messages, and reads the token files as `read_tokens()` does; a test runs both readers on the same files, and the component globs on the same paths. The browser scripts reach it through `projectConfig()`, which their `browser_common.mjs` re-exports. The two lint configs import it from their own folder, so a project copies `project_config.mjs` with them; stylelint matches its overrides with micromatch, so the config translates each `components` glob into micromatch globs that match the same files.

**Vendored alone.** A project that copied `audit_design.py` or `a11y_static.py` into its own `scripts/` before 3.5.0, as the hook recipe said, has no `project_config.py` beside it. Each then runs as it did; the audit says that the config is not read, and refuses `--tokens`. Copy `project_config.py` across to turn the config on.

**The commands.** `/web-design-suite:gate` runs the audit, `a11y_static.py` and `perf_audit.py` from the project's root, so each reads the config as above. `/web-design-suite:install-gate` vendors them, with both readers, into the project's `scripts/`, and writes `baselines.audit`, `baselines.a11y` and `baselines.perf` into the CI workflow's baseline job.

**Not read by** `crux_check.py`, which compares field data with a lab report and has no budget of its own.
