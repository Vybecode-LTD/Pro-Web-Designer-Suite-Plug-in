# Handoff

**2026-10-18**, the day's third session: **P37 is done** (#176, #177; DL-B3 closed). **The owner chose P35 next (2026-10-18): the cheap automatable a11y checks, then engines other than Chromium, two PRs; then P41, P42 and P43 in the order the owner chooses; then R4.**

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then the work in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## 2026-10-19: the rename and the distribution repository (another session)

A second session, beside P35's, did the owner's distribution plan (`dev plans/web-design-suite-distribution-and-promotion.md`):
- **#180, merged as `b2648f8`.** The plugin is now **Pro Web Design Suite, `pro-web-design-suite`**, in `plugins/pro-web-design-suite`. Both marketplace files carry `renames`. Four formats keep the old id, because users' projects hold them; CLAUDE.md's Gotchas lists them. A Codex fix lets `build.py` and `fail_before.py` read a pre-rename `--rev`, such as `v3.6.0`.
- **#181, merged as `24774d0`.** Releases ship without `tests/`, `evals/` and `tools/` (222 files). `build.py --tree` writes the **distribution repository**'s contents, and the build refuses what Anthropic's directory blocks. `release.yml`'s `distribute` job pushes each release to `Vybecode-LTD/pro-web-design-suite`: forward only, atomic, queued, never an older tag over a newer one. CI validates the tree on every PR.
- **#182, which carries this section.** The README now has *Try it*, *Where it works* and *What it runs, sends and stores*. Add to that `SECURITY.md` and `plugin.json`'s `documentationUrl`, `supportUrl` and `privacyPolicyUrl`.

**Before R4's tag, the owner must:**
1. create the empty public repository `Vybecode-LTD/pro-web-design-suite`;
2. add a write deploy key to it, with the private half in this repository's secret `DIST_DEPLOY_KEY`;
3. turn on private vulnerability reporting here, which `SECURITY.md` sends reports to.

Without 1 and 2, `distribute` fails, though the GitHub release still happens. **After R4:**
- check that the distribution repository holds 4.0.0 at its root;
- `/plugin marketplace add Vybecode-LTD/pro-web-design-suite` installs it;
- the owner validates it at claude.ai/directory/manage and submits it (Part A of the distribution plan).

**Its warnings:**
- **Never run the rename script again.** It belongs to a one-time PR. A path in a skip list moves with the rename, and a second run renamed the `renames` key and the CHANGELOG's history before it was caught.
- **The vitals timing tests flake in CI** (`test_runtime_urls...test_a_page_type_picks_the_budget_its_page_is_held_to`, `test_runtime_reach...test_vitals_measure_the_signed_in_page_and_the_late_content`). macOS's headless shell sometimes records no LCP, which the first test's comment notes. On #181 they failed on macOS / Python 3.9 twice and on Windows / Python 3.14 once, then passed on a fresh run.
- **A sensitive `userConfig` value never reaches a skill's script.** Claude Code gives it to hooks and MCP servers only, so `CRUX_API_KEY` and `FIGMA_TOKEN` stay environment variables.

## State

- **#176, P37 part 5 (Vue)**, merged as `b20f562`.
  - `scaffold_ui.py --framework vue` writes the kit and each entity's list, detail, form and six states as Vue 3.5 single-file components: `<script setup lang="ts">`, `defineProps`, `defineEmits`, `defineModel`, slots, and each CSS Module's rules in `<style scoped>` inside `@layer components`. The seven controls share `ui/Control/Control.css` through `<style scoped src>`.
  - A root's class is named for its component (`.ui-button`), never `.root`: Vue puts a parent's scope on a child's root element.
  - `a11y_static` reads `v-bind="$attrs"` as a spread.
- **#177, P37 part 6 (Svelte)**, merged as `8d8b6f8`. `--framework svelte` writes Svelte 5 components: `$props()`, callbacks as props, snippets, and each `<style>` holding only the rules its markup uses, since Svelte drops the others with a warning. The list's state rules wait under one `svelte-ignore`.
- **The tests** (`tests/test_scaffold_frameworks.py`):
  - every component goes through the real compiler (`vue` 3.5.44; `svelte` 5.57.2 for the client and the server, with no warning);
  - the form is rendered on the server, and the ids its aria attributes name are checked;
  - the form's focus is driven through each runtime: Vue's with a minimal custom renderer, Svelte's in jsdom 29.1.1. Each has a control that fails.
  - `vue`, `svelte` and `jsdom` are pinned in `tooling/main`. jsdom 30 drops Node 20, the tooling's floor.
- **Reviews:**
  - **#176, 5 real issues**, fixed in React as well, with a test failing on `fd84910`:
    - Codex 4: a multiple select bound `String()`; an emptied number sent `NaN`; `tag-input` and `json-editor` went through `String()`, and are now marked stubs; a required radio group lacked `required`.
    - CodeRabbit 1: a state's copy that began with `:` became a directive.
  - **#177, 1 claim declined with evidence:** Svelte's spread does select a multiple select's array. A jsdom test now holds it.
- **At the end:** the plan has 13 open items, all scheduled; about 1,410 tests. This session used about 600 thousand tokens.

## Next steps

1. **P35 part 1 (GT-B6):** the four checks `automation-coverage.md` lists as automatable but no gate runs:
   - text spacing (1.4.12);
   - focus not obscured (2.4.11);
   - content on hover and focus (1.4.13);
   - reduced motion (an A/B run);
   - clipping at 200% (1.4.4 and 1.4.10).

   These belong in `a11y_runtime.mjs`, each with a fixture that fails it.
2. **P35 part 2 (GT-B9):** `--engine chromium|firefox|webkit` for axe, the names and the tab order. Ask the owner before any CI download of the Firefox and WebKit builds.
3. Then **ask the owner which of P41, P42 and P43 follows**, and then **R4**.

## Open owner decisions

- **Before R4:** create `Vybecode-LTD/pro-web-design-suite` and its `DIST_DEPLOY_KEY` deploy key, and turn on private vulnerability reporting (the 2026-10-19 section above). Also decide whether issues live in the distribution repository or here; `supportUrl` points here for now.
- The order of P41, P42 and P43 after P35.
- Whether CI may install Playwright's Firefox and WebKit for P35 part 2. Each build is a download of tens of megabytes on every run that is not cached.

## Warnings

- **`check.py` takes about 20 minutes** when a shared file changes. Never edit a file the suite reads while it runs: fix a PR below a stack in a scratchpad worktree.
- **Bash eats escapes** in a heredoc (`\\`, `\.`, `\|`), three times this session. Use the Edit tool for any text with a backslash.
- **The token counter resets on every review event.** Keep a running total.
- **A test run from the repository root** (`python -m unittest plugins/.../test_x.py`) cannot import its siblings. Run tests from `tests/`.
- **Still open from earlier:**
  - the `VitalsUnderCsp` macOS flake, and `test_interact_at_clicks_while_the_page_hydrates`;
  - `perf_audit.py` and an unbundled `@import` chain;
  - three tokens outside Display P3;
  - the default scaffold's `focus-rule-invisible` warnings: four for React and Vue, seven for Svelte, where each control owns its surface. They are warnings, with zero errors, as the tests ask.
- **Standing:** don't grep `tooling/`; the repository is public; `Vybecode-LTD/wds-gate-scratch` is the owner's to delete.
