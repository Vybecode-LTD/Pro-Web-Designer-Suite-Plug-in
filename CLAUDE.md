# CLAUDE.md: Pro Web Designer Suite (web-design-suite)

The binding directives are in `C:\DEV\CLAUDE.md` and `C:\DEV\DIRECTIVES.md`, which Claude Code loads for every folder under `C:\DEV`. This file is the project map. Where the two differ, this file wins.

## Project

- **What:** web-design-suite, a Claude Code plugin. Thirteen skills for designing and building websites that stay coherent under multiple developers: tokens, style architecture, measured contrast, and gates that fail the build on drift.
- **Stack:**
  - The scripts and tests are Python 3.9 or newer, standard library only.
  - Node 20.19+, 22.13+ or 24+ (ESLint 10's range) is needed for the browser scripts and the real-tool tests.
  - The skills and references are Markdown.
- **Repository:** https://github.com/Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in. It is public (since 2026-09-28), and MIT-licensed like the plugin.
- **Type:** a Claude Code plugin marketplace. It is not a web app and not a desktop app, so the SEO and software-release directives do not apply.

## Current state (2026-10-02)

- **Version:** 3.2.1, released: PR #1 merged as `63932cf` and tagged `v3.2.1`. `main` holds 3.0.0 to 3.2.1 as tagged commits. 3.3.0 is in progress: the Python 3.9 floor (N6, PR #4), the audit's false cleans (SB-A9 with N11, PR #5) and the migration tool's copy of them (N12, PR #6) are merged; the scripts on Sass (SB-A24 with N13, PR #7) and W1's reference (DL-A5, DL-B1's §9, DL-C4, PR #8) are merged too. W1's security pass and `scaffold_ui --strict` (PRs #9, #10) are merged; merged on 2026-10-02: #12 (the parser on real `db pull` and `gen types` output), #13 (the scaffold's policies and `lib/supabase.ts`), #14 (the canonical entry stylesheets and `vendor` in the layer order) and #15 (the execution plan). Open on 2026-10-02: #16 (P0: what the reviews of #12 to #15 found, N16 to N25 and N29) and #17 (P1, stacked on #16: CI, the release build, `fail_before.py` and `check.py`, N5).
- **Installed:** 3.2.1 from `63932cf`. The marketplace is `C:\Users\vybec\.claude\local-marketplaces\web-design-suite`, a copy of `plugins/web-design-suite`, but sessions load `C:\Users\vybec\.claude\plugins\cache\web-design-suite\web-design-suite\<version>`, which `claude plugin update` refreshes only when the version changes.
- **Tests:** 432. CI (#17) runs them on Windows, Linux and macOS at Python 3.9 and 3.14, with Node; its first runs found one platform bug (fixed) and two Windows-only tests (fixed). Locally, `tools/check.py`; the full suite passed on 3.14 and 3.9 on Windows.
- **Active work:** `dev plans/web-design-suite-execution-plan.md`, which schedules every open item in PRs P2–P43 (P0 and P1 are #16 and #17). Next: green CI on #17 if it is not, then P2 (the spec generates the gates' rule sections) and P3 (the gates agree). Start each session from `dev plans/next-session-prompt.md`. A session may run up to 750 thousand tokens, with no compacting.
- **Open:** 151 items, every one scheduled in the execution plan (`check_execution_plan.py`).

## Commands

For the Bash tool (Git Bash), from the repository root:

```bash
npm ci --prefix tooling/main          # once; it downloads no browser (tooling/README.md)
npm ci --prefix tooling/tailwind-v3   # once
cd plugins/web-design-suite
python -B tools/check.py              # every PR: pointers, snippets, the plan, the audit, budgets, the affected tests
python -B tools/fail_before.py <test ids> [--rev REV]      # the fail-before table; REV defaults to the latest v* tag
python -B -m unittest discover -s tests                     # the whole suite; -B keeps bytecode out of the plugin
python tools/check_pointers.py        # § pointers; --write-register after editing one, then read the diff
python tools/sync_snippets.py --check # starter code quoted in the references
python skills/web-design-studio/scripts/audit_design.py skills --strict
cd ../.. && python -B tooling/release/build.py <empty folder> [--rev REV]   # the zip, the .skill files, SHA256SUMS
```

CI (`.github/workflows/ci.yml`) runs the whole suite on Windows, Linux and macOS at Python 3.9 and 3.14 for every PR, so locally `check.py` is enough (decision D1). A pushed `v*` tag makes `release.yml` build and create the GitHub release; nothing else creates one.

`fail_before.py` unpacks the revision through `git archive` and sets `WDS_PLUGIN_ROOT` and `WDS_PLUGIN_REV` for the first run. By hand, the same is `set "WDS_PLUGIN_ROOT=<unpacked plugin>" && python -B -m unittest <ids>` in cmd.exe.

The Python floor runs with `uv run --no-project --python 3.9 python -B -m unittest discover -s tests`, which works in cmd as well.

For `claude plugin validate --strict`, `update` and `details`, use the desktop app's bundled CLI, `%APPDATA%\Claude\claude-code\<version>\claude.exe`. The one on PATH is older.

## Gotchas

- **Keep `tooling/` beside the plugin.** Never put a `node_modules` above `plugins/`: Node searches parent folders, and one there replaced the stub modules the browser-resolution tests plant (16 failures).
- **Bytecode.** Run Python with `-B` or `PYTHONDONTWRITEBYTECODE=1`. Without either, test discovery alone writes `tests/__pycache__` into the plugin.
- **Line endings.** `.gitattributes` stores every text file with LF. A CRLF checkout breaks the POSIX hook and the byte-for-byte tests.
- **Backslashes in heredocs.** The Bash tool unescapes `\\` inside heredocs, so write Python that contains backslash escapes with the Edit tool.
- **Linked `node_modules`.** The real-tool tests give their temp project a linked `node_modules`: a junction on Windows. Remove a junction with Python's `os.rmdir`, never `rm -rf`.
- **stylelint 17** writes its JSON report to stderr, clean or not; stdout stays empty.
- **eslint-plugin-tailwindcss 3.18** needs an absolute config path, anchored at the project: ESLint 10 loads a config from whichever folder it lints.
- **Never write into OneDrive** or the folders redirected into it (Documents, Desktop, Pictures, Music, Videos). Downloads is safe.
- **Commands you give the user** to run must work in cmd.exe. (The Commands block above is for the Bash tool.)
- **Never run `npm ci` in a worktree whose `tooling/*/node_modules` is a junction**: it deletes the real toolchain through the link.

## Conventions

- **Regression tests.** Every fix gets a regression test, seen failing on the previous release's tag and passing now. The reports list the fail-before counts, and the controls and guards.
- **One set of rules.** A gate change goes into `skills/web-design-studio/assets/rules/design-rules.json` first. Then the audit, the stylelint config and the ESLint config follow, each with a real-tool test in `tests/test_real_tools.py`.
- **Facts.** A figure from outside the plugin is re-read at its source and registered, with its quote, in `tests/fixtures/evidence.json`.
- **Size limits.** A SKILL.md stays at or under 20,500 bytes and a reference under 60.5 KB (`tests/test_skill_budget.py`).
- **Git.** One branch per phase, conventional commits and a PR. Tag after the merge. Read the staged diff before each commit.
- **Docs.** Plans and reports go in `dev plans/`. Update the docs in the same PR as the code, and keep this file lean.

## Map

```
.claude-plugin/marketplace.json   the repository as a marketplace; the plugin is at ./plugins/web-design-suite
plugins/web-design-suite/         the plugin (the only folder that ships)
  skills/<13 skills>/             SKILL.md, references/, scripts/, assets/
  shared/token-contract.md        the master copy of the contract (13 copies must match it)
  tests/                          the suite; fixtures/ holds the pointer and evidence registers
  tools/                          check_pointers.py, sync_snippets.py
  CHANGELOG.md, README.md, LICENSE
tooling/                          pinned tools for the tests (main/, tailwind-v3/); release/build.py
.github/workflows/                ci.yml (the suite on three platforms), release.yml (a v* tag makes the release)
dev plans/                        the review, the phase plans and reports, the completion plan and inventory
docs/HANDOFF.md                   the current state and the next steps, one page
```
