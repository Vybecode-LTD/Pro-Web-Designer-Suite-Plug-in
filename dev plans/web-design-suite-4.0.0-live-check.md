# 4.0.0: the live check (R4)

R4's live check follows R3.6's (`web-design-suite-3.6.0-live-check.md`). The owner chose, on 2026-10-22:
- **the full list** in `next-session-prompt.md` §4 (about 15 headless sessions, about $8 to $10), run in a fresh session with a full budget;
- **the evals** (`evals.yml`, `tag=all`, about $11 under its $14 ceiling) on the release PR's merge, with `headSha` checked, before the tag.

## The free checks (2026-10-22, no model call)

Run at `main` `7ed9937`, with Claude Code **2.1.308** installed from npm into a scratchpad (`npm install @anthropic-ai/claude-code@2.1.308`), since the desktop app's bundled CLI was not at its old path and the one on PATH is 2.1.160. Every `claude plugin` command ran with `CLAUDE_CONFIG_DIR` set to an empty scratch folder, so the owner's own install was never touched.

| Check | Result |
|---|---|
| `build.py --tree` | Exit 0: **229 files**, `.claude-plugin/marketplace.json` at the root (marketplace `pro-web-design-suite`, plugin `./`, `renames`). CI's `claude plugin validate --strict` job validates the same tree with the latest CLI on every PR, and passed on #199. |
| 3.6.0 under its old name | A folder marketplace holding `v3.6.0`'s `.claude-plugin` and `plugins/web-design-suite` (from `git archive`): `marketplace add` names it `web-design-suite`; `plugin install web-design-suite@web-design-suite` installs 3.6.0. |
| The update to 4.0.0 | The same folder replaced by `main`'s files, with `plugin.json` set to 4.0.0. `marketplace update web-design-suite` succeeds and **the marketplace keeps its old name**. `renames` moves `enabledPlugins` to `pro-web-design-suite@web-design-suite`, but `installed_plugins.json` is emptied: `plugin list` shows no plugin, and `plugin update web-design-suite@web-design-suite` fails with "not found". |
| The reinstall | `plugin install pro-web-design-suite@web-design-suite` installs 4.0.0, enabled. `plugin install pro-web-design-suite@pro-web-design-suite`, the command the CHANGELOG gave, **fails**: "not found in marketplace pro-web-design-suite". |

**Defect, fixed in #200:** CHANGELOG.md's *Renamed* note told an existing install to run `/plugin install pro-web-design-suite@pro-web-design-suite`. It now gives `pro-web-design-suite@web-design-suite`, and `test_docs` pins it. A new install from the distribution repository is `pro-web-design-suite@pro-web-design-suite`, as both READMEs say.

**For the paid check:** whether a session start in the desktop app installs the renamed enabled plugin by itself, or shows it as not installed until the reinstall. Run it with the owner's real flow: the development repository as a GitHub marketplace, 3.6.0 installed, then the release.

**The session start (2026-10-23, free):** with Claude Code **2.1.309**, the same throwaway flow (3.6.0 installed from a folder marketplace, the folder replaced by `main` at 4.0.0, `marketplace update`) empties `installed_plugins.json`, and then a session start, even signed out, installs `pro-web-design-suite@web-design-suite` 4.0.0 by itself. So an existing install moves at its next session start; the CHANGELOG's reinstall stays as the fallback. `build.py --tree` at `745cd95` wrote 229 files, and `claude plugin validate --strict` (2.1.309) passed on them.

## The paid sessions (2026-10-23)

The owner approved 15 sessions under a $10 cap. Each was one `claude -p` session, Claude Code 2.1.309 and `claude-sonnet-5-5`, with `--plugin-dir` on `build.py --tree`'s output at 4.0.0 (the fixes below copied in as they landed), `--setting-sources project,local`, `--permission-mode acceptEdits`, every Bash and PowerShell command allowed, and a per-session cap. **They cost $4.51 over 20 runs** (S1 and S2 split in two, S2a run twice, S15 three prompts).

**The test environment's trap:** a session that loads no skill goes looking for the plugin, and the owner's installed 3.6.0 is in `~/.claude/plugins/cache`. S2a's first run copied 3.6.0's lint block from there. A scratch `HOME` did not hide it (the model reads the user name from the project's path); what fixed it was the router naming the skill. A user upgrading from 3.6.0 keeps the old cache beside the new one, so a session that skips the skill can do the same.

| Session | The route | Project | Result |
|---|---|---|---|
| S1 | `/pro-web-design-suite:gate`; the MCP tools by their new names; #155's containment | the starter, with planted faults | **Pass** ($0.13): six planted faults; `mcp__plugin_pro-web-design-suite_gates__audit_design` refused `../outside` ("'paths' must be inside the project"). |
| S2 | Part 5's Tailwind lint block; `/tw-probe` | a new Vite 8 + Tailwind 4.3.3 app (it ships oxlint, not ESLint) | **Defect, fixed** ($0.62). The router heard nothing for "the design-system lint", and both runs copied 3.6.0's block from the installed cache. 4.0.0's Part 5, run by hand in the same project: 14 errors, `better-tailwindcss` conflicts and v4's renamed `shadow` and `rounded`. `/tw-probe` passed: 4 roles, 16 surviving namespaces named. |
| S3 | `/migrate src`, the v4 census | `adrianhajdin/react-movies` at `d4790df` (Tailwind 4.0.0) | **Defect, fixed** ($0.10). The census withheld every numeric class: a quoted Google Fonts URL holds a `;`. `tw_probe.mjs` exited 2 on the same import. After the fix: 3 numeric classes counted; the probe runs. |
| S4 | The v3 upgrade path | `adrianhajdin/project_hoobank` (Tailwind 3.4.19) with 3.6.0's v3 block | **Pass** ($0.35): the CHANGELOG's four steps, 303 problems to 216, each change explained. |
| S5 | The census, proposal and codemod (P52, P50) | Excalidraw's 62 SCSS files, sparse, at `1d4dc2c` | **Pass, with a note** ($0.20): 1,058 literals in 78 files. The session declined the colour batch, since Excalidraw has its own token layer and the proposal maps onto the contract's names. Run by hand: the codemod rewrote 51 files, LF kept, `!important` kept, the `font` resets named. |
| S6 | `a11y_static` and the audit on bindings (P50, P55) | `mutoe/vue3-realworld-example-app`, `gothinkster/angular-realworld-example-app` | **Defects, fixed** ($0.29): a sign-up password told `current-password`; a `.ts` fixture's XSS string read as an image. The rest real. |
| S7 | P34: a signed-in, client-rendered page | a local app, a seeded test user | **Pass** ($0.27): `--steps` signed in with the password from an environment variable, `--wait-for [data-ready=true]`, all four planted faults and a reflow failure. |
| S8 | P34: shadow DOM; a sitemap through `--urls` at two viewports | webawesome.com, 5 pages, 390 and 1280 | **Pass** ($0.29): 195 to 1,415 open roots a page, 0 closed or unread. |
| S9 | P35 on real sites, Chromium and WebKit | getbootstrap.com's tooltips page, cookiebot.com | **Defect, fixed in the description** ($0.60): the session wrote its own Playwright scripts. The plugin's gate, run by hand: every check in Chromium, WebKit's subset with the rest named. |
| S10 | `scaffold_ui.py --framework vue` | a new Vite + Vue 3.5.44 app | **Pass** ($0.23): `npm run build` passes; the scaffold's files audit clean. |
| S11 | `--framework svelte` | a new SvelteKit 3.1.0 app (Svelte 5.57.2) | **Pass** ($0.22): `npm run build` and `npm run check` pass. |
| S12 | `--server-actions` | a new Next.js 16.4.2 App Router app | **Pass** ($0.28): `npm run build` passes. Astro 7.4.2's new project, by hand: the audit and `a11y_static` clean. |
| S13 | The MJML theme to a send | a new MJML 5.4.1 project | **Pass, with a note** ($0.33): `lint_email` clean, the project's accent, one message to a local SMTP sink. |
| S14 | The React Email theme to a send | `create-email` (React Email 6.11.3) | **Pass, with a note** ($0.38): the same, through the sink. |
| S15 | The router, one turn each | the starter | **Pass** ($0.20): Lighthouse reached perf-budget-gate; the design lint reached the gate's MCP tool; the critique ran out of turns reading the page. |

## Follow-ups, for the owner to schedule

- **An email theme from the project's `tokens.css`** (S13, S14): the skill calls `email-tokens.json` the projection of `tokens.css`, but no script projects a project's own file; both sessions wrote one.
- **The hover check and a JavaScript tooltip** (S9): `hover` raised nothing on Bootstrap's tooltip, which vanishes when the pointer moves onto it and ignores Esc. Read the check's scope first.
- **`contrast-under-overlay` on webawesome.com** (S8): 21 to 147 a page; check the overlay detection against the page.
- **A codebase with its own token names** (S5): the migration maps onto the contract's names; the skill could say how to map onto an existing layer.
- **The scaffold's default sort** (S10): `placed_at` is not read as the time to sort by.
- **A provider send** (S13, S14): the sessions sent through a local SMTP sink; a send through a real provider needs the owner's key.
