# Pro Web Design Suite

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

## Try it

Three prompts to start with, in a project folder:

1. *"Set up a design system for this site: brand colour #e8440a, a type scale and a spacing scale, and check every text colour against WCAG AA."* web-design-studio writes `tokens.css` with the scales and the roles, and the contrast check measures each pair.
2. *"Audit the styles in `src/` for hard-coded values and anything off the spacing scale."* The audit (`audit_design.py`) reports each finding by its law, with file and line.
3. *"We inherited this codebase. Move its colours and spacing onto tokens."* design-token-migration takes a census of every literal, proposes the tokens, and writes a codemod that a reviewer checks batch by batch.

Then `/pro-web-design-suite:gate` runs the design, accessibility and performance gates in one pass.

## Where it works

| | Claude Code | Cowork | Claude chat |
|---|---|---|---|
| The thirteen skills and the sixteen commands | Yes | Yes | Yes, as skills |
| The six subagents | Yes | Yes | No |
| The hooks (the gates after each edit, the router) | Yes | Yes | No |
| The `gates` MCP server | Yes | When the session runs on your computer | No |

The skills' scripts need Python 3.9 or newer, and the browser gates need Node and Playwright, wherever Claude runs them.

## What it runs, sends and stores

Everything runs on your machine, and the plugin collects nothing.

- **The hooks** run `node hooks/design_hooks.mjs`. The router reads each prompt locally, to name the skill it needs. The design gate, the a11y gate, the token diff, the email build and the generated-file guard act only in a project whose `.design-suite.json` turns them on. The gates run the plugin's Python scripts on the file Claude just edited; the guard reads that file's first lines. The plugin's `design_hooks` option turns them all off.
- **The MCP server**, `gates`, is `node mcp/design_gates.mjs`, over stdio. Its five tools run the same scripts on your project.
- **The scripts** read and write files in your project only: reports, tokens, scaffolds and builds. The browser gates open the pages you name, through your own Playwright install. They download no browser and send no page anywhere.
- **The network:** the plugin makes one call to a third party, and only when you ask for it. `crux_check.py` sends a URL or origin to Google's Chrome UX Report API, with the key you set in `CRUX_API_KEY`. figma-variables-sync shows a `curl` to Figma's REST API, with the token you set in `FIGMA_TOKEN`, for you to run. Neither key is stored by the plugin, and nothing else leaves your machine.
- **`/install-gate`** writes a CI workflow into your repository. That workflow runs in your CI, in Microsoft's Playwright image.

---

## Install

**As a plugin** — everything at once. In Claude Code, add this repository as a
marketplace, then install the plugin by its full id:

```
/plugin marketplace add Vybecode-LTD/pro-web-design-suite
/plugin install pro-web-design-suite@pro-web-design-suite
```

The repository is public, so this works for anyone. It holds the plugin as released, one commit per version. The development repository, `Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`, holds the tests, the evals and the issues, and works as a marketplace too. To install from a release zip
instead, unpack it and add the unpacked `pro-web-design-suite` folder, the one that holds
`.claude-plugin/marketplace.json`, in place of the repository's name.

**As individual skills** — from 3.3.0, each GitHub release attaches one `.skill` file
per skill, packaged as Anthropic's skill-creator packages one, and a skill folder can be
installed on its own too. Eight of them run web-design-studio's `audit_design.py` as
their gate, so install web-design-studio beside any of them.

**As a repo** — extract `skills/web-design-studio/assets/starter/styles/` into your project, wire the configs from `assets/configs/`, and point Claude Code at it.

**The hooks** come with the plugin, and need `node` on the PATH. The gates, the token
diff, the email build and the guard act only where a project's `.design-suite.json`
turns them on; the router runs in every project:

```json
{"schema": 1, "tokens": "src/styles/tokens.css",
 "baselines": {"system": "published/system.json"},
 "hooks": {"designGate": true, "a11yGate": true, "tokenDiff": true, "emailBuild": true,
           "generatedFiles": true}}
```

- **`designGate`:** after each edit Claude makes to a stylesheet, template or script,
  `audit_design.py` runs on that file, and Claude hears what it found. It, the a11y gate,
  the token diff and the email build need Python 3 (`WDS_PYTHON`, else `python3`,
  `python` or `py -3`).
- **`a11yGate`:** after each edit to markup, JSX or CSS, `a11y_static.py` runs on that
  file, and Claude hears its findings with the audit's.
- **`tokenDiff`:** after each edit to one of the project's `tokens`, `diff_system.py`
  compares them with the published snapshot, `baselines.system`. Claude hears the
  breaking changes and the contrast pairs that crossed a WCAG floor; an additive edit is
  silent, and so is the hook until the snapshot exists.
- **`emailBuild`:** after each edit to an email template (the config's `emails` globs,
  `emails/**/*.html` by default), `lint_email.py` checks the source, `build_email.py`
  builds it into a temporary folder, and `lint_email.py` checks the build. Claude hears
  the errors.
- **`generatedFiles`:** Claude may not edit a file that says it is generated
  (`DO NOT EDIT`), and is told to change its source.
- **The router:** another hook names the skill a prompt needs, when a crowded skill
  listing has dropped the descriptions.

The plugin's `design_hooks` option, set to false in `/config`, turns them all off.

**The commands** are skills only you invoke, so they stay out of Claude's skill listing:

- **`/pro-web-design-suite:gate`** runs the design, accessibility and performance gates on
  the project in one pass, with one verdict. Each reads the project's `.design-suite.json`.
- **`/pro-web-design-suite:install-gate`** vendors the gate scripts into the project's
  `scripts/` and writes `.github/workflows/design-gates.yml`. The workflow runs the three
  gates on Linux in the Playwright image built for the project's own `playwright`, and the
  static gates on Windows. A job you run by hand records the baselines where the gates
  run, for you to review and commit.
- **`/pro-web-design-suite:new-system BRAND`** starts a system from a brand colour: the
  ramps, a type scale and the starter styles, with every role pair's contrast checked.
- **`/pro-web-design-suite:contrast`** checks the role pairs in the project's tokens, or one
  foreground on one background.
- **`/pro-web-design-suite:tw-probe`** compiles a Tailwind v4 project's entry with its own
  tailwindcss: every role class its theme declares must generate, none of Tailwind's
  stock classes may, and it reports on any class you name.
- **`/pro-web-design-suite:migrate`** takes a token migration's census and proposes the
  mapping. It changes nothing.
- **`/pro-web-design-suite:release-check`** extracts, diffs and gates the system against the
  published snapshot, then writes the changelog entry and, for a breaking change, the
  migration guide.
- **`/pro-web-design-suite:figma-sync EXPORT`** audits a Figma export, then generates the
  tokens and shows what they would change.
- **`/pro-web-design-suite:docs-check`** checks that the docs still describe the code.
- **`/pro-web-design-suite:schema-to-screens SCHEMA`** turns a database schema into screens,
  asking you what only you can answer, and stops on a blocking security finding.
- **`/pro-web-design-suite:email-build TEMPLATE`** lints, compiles and renders an HTML email.
- **`/pro-web-design-suite:deck`** builds the client deck from the audits and a critique, and
  stops on a blocking finding.
- **`/pro-web-design-suite:gate-a11y`**, **`gate-perf`** and **`gate-matrix`** run the
  browser halves of the gates on a served or built page.
- **`/pro-web-design-suite:critique`** has the design critic, a subagent that did not build
  the work, critique it, and reports its findings.

**The subagents** work in their own context and return only their findings. None has the
Edit or Write tool, and each is told to leave the work unchanged, but each runs the
skills' scripts through Bash, so they are not a sandbox. Claude hands work to them when
it fits, or you can ask by name:
`design-critic`, `gate-runner`, `a11y-auditor`, `design-auditor`,
`supabase-security-reviewer` and `codemod-batch-reviewer` (each as
`pro-web-design-suite:<name>`).

**The gates as tools.** An MCP server, `gates`, starts with the plugin (it needs `node`,
and Python 3 for the scripts). Its five tools run a gate in the project's folder and
return the script's JSON, its exit code and a verdict: `audit_design`, `a11y_static`,
`perf_audit`, `check_roles` and `diff_system`. Claude calls them by name
(`mcp__plugin_pro-web-design-suite_gates__audit_design`), and so can a permission rule or
a skill's `allowed-tools`. A report too long for Claude's context keeps the head of its
longest lists, nested ones too, and says how many it left out. A path Claude passes
must be inside the project, through any link, and so must every link under a folder
it passes (`node_modules` and `.git` aside); the token files `.design-suite.json`
names are read wherever they are.

The reports go in `design-reports/`, which a project usually leaves out of git.

**In CI**, `scripts/` is where every recipe in the skills expects the scripts
(`python -m scripts.audit_design`), so after `/pro-web-design-suite:install-gate` a clean
checkout has them. For another skill's script in CI, such as `diff_system.py` or
`build_docs.py`, check the plugin out at a release tag and run the script by path,
`python PLUGIN/skills/SKILL/scripts/SCRIPT.py`. A script run by path finds the
helpers beside it, so it needs no `PYTHONPATH`.

---

## Running the scripts

Every script is plain Python and needs **Python 3.9 or newer**; the six `.mjs`
scripts (the five browser gates and `tw_probe.mjs`) need Node instead. The lint configs need a Node that stylelint 17 and
ESLint 10 both support: 20.19 or newer on the 20 line, 22.13 or newer on the 22
line, or 24 and later. Run the scripts
**by path, from your project's root**, so `src/` means your `src/` and every output
lands in your project, never inside the plugin.

Below, `WDS` is the plugin's `skills` folder. Claude Code keeps each installed version
in its own folder, `.claude/plugins/cache/pro-web-design-suite/pro-web-design-suite/<version>`, under your home
folder. Set `WDS` once per terminal, in your shell's form (with the version you have):

| Shell | Set it once | Then |
|---|---|---|
| bash, zsh, Git Bash | `WDS="$HOME/.claude/plugins/cache/pro-web-design-suite/pro-web-design-suite/3.6.0/skills"` | paste the commands as they are |
| PowerShell | `$WDS = "$HOME/.claude/plugins/cache/pro-web-design-suite/pro-web-design-suite/3.6.0/skills"` | paste the commands as they are |
| cmd | `set "WDS=%USERPROFILE%/.claude/plugins/cache/pro-web-design-suite/pro-web-design-suite/3.6.0/skills"` | write `%WDS%` where a command says `$WDS` |

Each command below is one line, and `"$WDS/…"` is all the shell expands, which bash
and PowerShell do the same way. (The skills' own docs write commands for bash, which
is where Claude Code runs them: Git Bash, on Windows.)

## Quick start on a new project

Tokens: derive the ramp from the brand and check its contrast, then print the
starter's type scale.

```bash
python "$WDS/web-design-studio/scripts/generate_color_ramp.py" "#e8440a" --name accent --format css
python "$WDS/web-design-studio/scripts/generate_type_scale.py" --preview
```

Build: copy `tokens.css`, `reset.css`, `base.css` and `layout.css` from the starter.
Then gate it, with the design gate, the performance gate and the accessibility gate:

```bash
python "$WDS/web-design-studio/scripts/audit_design.py" src/ --strict
python "$WDS/perf-budget-gate/scripts/perf_audit.py" dist/ --strict
python "$WDS/a11y-audit-runner/scripts/a11y_static.py" src/ --strict
```

## Quick start on an inherited codebase

Take a census of what is actually there, as a report and then as data. Cluster it into
what it was trying to be. Run the codemod dry, then for real. Freeze the rest as a
baseline.

```bash
python "$WDS/design-token-migration/scripts/extract_literals.py" ./src --format report
python "$WDS/design-token-migration/scripts/extract_literals.py" ./src --format json -o literals.json
python "$WDS/design-token-migration/scripts/cluster_values.py" literals.json -o proposal/
python "$WDS/design-token-migration/scripts/apply_codemod.py" ./src -m proposal/mapping.json --kind spacing
python "$WDS/design-token-migration/scripts/apply_codemod.py" ./src -m proposal/mapping.json --kind spacing --apply
python "$WDS/web-design-studio/scripts/audit_design.py" ./src --write-baseline .design-baseline.json
```

---

## What the gate actually catches

`audit_design.py` is stdlib-only Python 3 and understands cascade layers, component vs token files, and the documented exceptions (`margin:auto`, the owl selector in a parent's rule, `calc(var(--t) * -1)`, `em` as a ratio for an offset and `font-size: 1em` for an icon, `vw` as relational). It reads stylesheets, JS/TS/JSX, and the `<style>` blocks, `style=""` attributes and class lists of HTML, Vue, Svelte and Astro files (HTML email is `lint_email`'s job). A literal beside a `var()` is still a literal, and rules inside `@media` / `@container` are checked like any other. A folder with nothing auditable in it is an error, not a pass.

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

The suite's own tests live in the development repository's `plugins/pro-web-design-suite/tests/`: a release leaves out `tests/`, `evals/` and `tools/`. They need Python 3.9 or newer (they run on 3.9 to 3.14); git and a POSIX `sh` for the hook and recipe tests; Node for the browser-script and real-tool tests. From the plugin root:

```bash
python -B -m unittest discover -s tests -v
```

Set `WDS_PLUGIN_ROOT` to run the same tests against another copy of the suite — that is how every fix is shown failing on the release before it. Two kinds of tests need tools from npm:
- The real-browser tests (runtime contrast, modal and iframe focus, the matrix's state check, the starter CSS in Chromium) run when `WDS_NODE_MODULES` points at a `node_modules` holding `playwright` and `axe-core`. They never download a browser.
- The real-tool tests run the shipped ESLint, stylelint and Tailwind configs through the real tools. They take their tools from `WDS_ESLINT_MODULES`, `WDS_STYLELINT_MODULES`, `WDS_TAILWIND_MODULES` and `WDS_TAILWIND_V3_MODULES`; `tests/test_real_tools.py` says what each must hold.

In the plugin's repository, `npm ci` in `tooling/main` and `tooling/tailwind-v3` installs every one of those tools at pinned versions (a browser apart: see `tooling/README.md`), and the tests find them without any variable set (a toolchain installed for another operating system is ignored). Set a variable to `off` to switch its tests off.

## Evals

`evals/`, in the development repository, holds cases for `claude plugin eval` (Claude Code 2.1.269 or later). For each skill there is a request phrased as a user would type it, which should load that skill. For five pairs of sibling skills there is a request for one that must never load the other. Every run is a real model call on your account. From the plugin root:

```bash
claude plugin eval . --tag routing --ablation none --runs 1 --no-publish
```

A routing case cannot pass without the plugin, so `--ablation none` skips the no-plugin arm and halves the cost. `--runs 1` is for iterating; the default is 3. The cases grant no shell, so they run on native Windows too, and the results go in `evals/results/`.

The outcome cases, one folder per area (`build`, `systems`, `gates`, `lifecycle`, `persuasion`, `delivery`), give Claude a task and grade what it wrote, with the plugin and without it, so the difference (Δ) is what the plugin adds. They write files, run the design audit and the contrast check through the plugin's MCP server, and copy their starting project in with a scaffold script from this folder:

```bash
claude plugin eval . --tag outcome --runs 1 --scaffold --allow-real-servers --no-publish --allow-tools Write Edit mcp__plugin_pro-web-design-suite_gates__audit_design mcp__plugin_pro-web-design-suite_gates__check_roles
```

They grant no shell either, since the MCP server runs outside the sandbox. A full run of both sets, three runs each, costs about $11 at list price.

What changed in each release is in `CHANGELOG.md`.

## Support

Report a bug or ask a question in [the development repository's issues](https://github.com/Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in/issues). Report a security problem privately, as `SECURITY.md` says.

---

## License

MIT.
