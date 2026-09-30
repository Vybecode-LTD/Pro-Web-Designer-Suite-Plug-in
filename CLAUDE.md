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

## Current state (2026-09-30)

- **Version:** 3.2.1, released: PR #1 merged as `63932cf` and tagged `v3.2.1`. `main` holds 3.0.0 to 3.2.1 as tagged commits. 3.3.0 is in progress: the Python 3.9 floor (N6, PR #4) and the audit's false cleans (SB-A9 with N11, PR #5) are merged.
- **Installed:** 3.2.1 from `63932cf`. The marketplace is `C:\Users\vybec\.claude\local-marketplaces\web-design-suite`, a copy of `plugins/web-design-suite`, but sessions load `C:\Users\vybec\.claude\plugins\cache\web-design-suite\web-design-suite\<version>`, which `claude plugin update` refreshes only when the version changes.
- **Tests:**
  - 350, passing on Python 3.9 and 3.14 on Windows.
  - Linux passes with the Node tests skipped.
  - macOS has never been run.
- **Active work:** phase 3 (3.3.0) of `dev plans/web-design-suite-completion-plan.md`, as small PRs. Next: N12, the migration tool's copy of SB-A9's `//` bug, then W1, the Supabase access boundary.
- **Open from the review** (the inventory has each item): 58 issues, none high; 43 gaps plus 4 partly done; 46 improvements plus 6 partly done.

## Commands

For the Bash tool (Git Bash), from the repository root:

```bash
npm ci --prefix tooling/main          # once; it downloads no browser (tooling/README.md)
npm ci --prefix tooling/tailwind-v3   # once
cd plugins/web-design-suite
python -B -m unittest discover -s tests                     # the suite: 350 tests; -B keeps bytecode out of the plugin
WDS_PLUGIN_ROOT=<unpacked older release> python -B -m unittest discover -s tests   # fail-before
python tools/check_pointers.py        # § pointers; --write-register after editing one, then read the diff
python tools/sync_snippets.py --check # starter code quoted in the references
python skills/web-design-studio/scripts/audit_design.py skills --strict
```

Get an older release with `git archive v3.2.1 plugins/web-design-suite | tar --strip-components=1 -x -C <scratch folder>`, which unpacks the plugin as `<scratch folder>/web-design-suite`. In cmd.exe the fail-before run is `set "WDS_PLUGIN_ROOT=<folder>" && python -B -m unittest discover -s tests`.

The Python floor runs with `uv run --no-project --python 3.9 python -B -m unittest discover -s tests`, which works in cmd as well. Linux runs through WSL, from PowerShell; the release procedure in the plan gives the exact command.

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
tooling/                          pinned tools for the tests (main/, tailwind-v3/); release/build_zip.py
dev plans/                        the review, the phase plans and reports, the completion plan and inventory
docs/HANDOFF.md                   the current state and the next steps, one page
```
