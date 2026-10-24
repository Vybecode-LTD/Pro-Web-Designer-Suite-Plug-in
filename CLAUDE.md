# CLAUDE.md: Pro Web Design Suite (pro-web-design-suite)

The binding directives are in `C:\DEV\CLAUDE.md` and `C:\DEV\DIRECTIVES.md`, which Claude Code loads for every folder under `C:\DEV`. This file is the project map. Where the two differ, this file wins.

## Project

- **What:** Pro Web Design Suite (`pro-web-design-suite`; `web-design-suite` until 4.0.0), a Claude Code plugin. Thirteen skills for designing and building websites that stay coherent under multiple developers: tokens, style architecture, measured contrast, and gates that fail the build on drift.
- **Stack:**
  - The scripts and tests are Python 3.9 or newer, standard library only.
  - Node 20.19+, 22.13+ or 24+ (ESLint 10's range) is needed for the browser scripts and the real-tool tests.
  - The real-tool tests' pinned packages are in `tooling/main` (ESLint, stylelint, Playwright, Tailwind, Vue, Svelte, MJML, React Email); `tooling/README.md` lists them.
  - The skills and references are Markdown.
- **Repository:** https://github.com/Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in, where the plugin is developed. It is public (since 2026-09-28), and MIT-licensed like the plugin. From 4.0.0, users install from the **distribution repository**, https://github.com/Vybecode-LTD/pro-web-design-suite, which holds the built plugin at its root (no `tests/`, `evals/` or `tools/`). Only `release.yml`'s `distribute` job writes it, with the `DIST_DEPLOY_KEY` deploy key; nobody commits to it by hand. Anthropic's directory reads it.
- **Type:** a Claude Code plugin marketplace. It is not a web app and not a desktop app, so the SEO and software-release directives do not apply.

## Current state (2026-10-24)

- **Version:** 4.0.0 is the latest release (`v4.0.0`, `d9125b7`, tagged 2026-10-24, published by `release.yml`): Phases 6a's follow-ups, 6b and 6c, the rename, and R4's live check (`dev plans/web-design-suite-4.0.0-live-check.md`). Its `distribute` job filled the distribution repository: `main` and `v4.0.0` at `28efdaa`, the 229 files of `build.py --tree`, checked byte for byte, and installed cleanly from GitHub.
- **Installed:** 3.6.0, from the release zip (2026-10-13). The marketplace is `C:\Users\vybec\.claude\local-marketplaces\web-design-suite`, a copy of `plugins/web-design-suite`, but sessions load `C:\Users\vybec\.claude\plugins\cache\web-design-suite\web-design-suite\<version>`, which `claude plugin update` refreshes only when the version changes. 4.0.0 installs with `/plugin marketplace add Vybecode-LTD/pro-web-design-suite`; moving the owner's own install is theirs to do.
- **Tests:** about 1,600. CI runs them on Windows, Linux and macOS at Python 3.9 and 3.14, with Node, so decision D1 is in force: locally, `tools/check.py`.
- **Evals:** 23 routing cases and 11 outcome cases. `evals.yml` runs both only by hand (`tag=all`), under one $14 ceiling; the dispatch before a release's tag gates it, and a tag starts no run (the owner, 2026-10-11). The outcome cases grant Write, Edit and the gate MCP tools, never Bash. In `claude-code-capabilities.md`, §1 is the evals page, §10 P29's choices, and §11 the sandboxing page and P30's choices.
- **Active work:** none in flight. Next: the owner submits to Anthropic's directory (claude.ai/directory/manage, the distribution plan's Part A; ask before anything is submitted), then chooses among P58 (`no-fake-countdown`'s reliability, N52: 2 of 3 in `evals.yml` on `d9125b7`, five of six runs over the session) and the live check's six follow-ups. Start each session from `dev plans/next-session-prompt.md`. A session may run up to 750 thousand tokens, with no compacting.
- **Renamed and redistributed (2026-10-19, #180 to #182):** Pro Web Design Suite, `pro-web-design-suite`. From 4.0.0, releases go to the distribution repository through `release.yml`'s `distribute` job; the repository, its write deploy key and `DIST_DEPLOY_KEY` are in place, and private vulnerability reporting is on (verified 2026-10-21); the first real push, 4.0.0's, ran on 2026-10-24.
- **Open:** N52, scheduled as P58 (`check_execution_plan.py`: 1 open, 1 scheduled).

## Commands

For the Bash tool (Git Bash), from the repository root:

```bash
npm ci --prefix tooling/main          # once; it downloads no browser (tooling/README.md)
npm ci --prefix tooling/tailwind-v3   # once
cd plugins/pro-web-design-suite
python -B tools/check.py              # every PR: pointers, snippets, the plan, the audit, budgets, the affected tests
python -B tools/fail_before.py TEST_IDS [--rev REV]      # the fail-before table; REV defaults to the latest v* tag
python -B -m unittest discover -s tests                     # the whole suite; -B keeps bytecode out of the plugin
python tools/check_pointers.py        # § pointers; --write-register after editing one, then read the diff
python tools/sync_snippets.py --check # starter code quoted in the references
python tools/sync_rules.py --check    # the spec's data in the gates; without --check it rewrites the blocks
python tools/sync_caniemail.py --check   # caniemail's data in the email matrix and lint; --data FILE refreshes it
python skills/web-design-studio/scripts/audit_design.py skills --strict
cd ../.. && python -B tooling/release/build.py EMPTY_FOLDER [--rev REV] [--tree EMPTY_FOLDER]   # the zip, the .skill files, SHA256SUMS; --tree: the distribution repository's files
```

CI (`.github/workflows/ci.yml`) runs the whole suite on Windows, Linux and macOS at Python 3.9 and 3.14 for every PR, so locally `check.py` is enough (decision D1). A pushed `v*` tag makes `release.yml` build and create the GitHub release; nothing else creates one.

`fail_before.py` unpacks the revision through `git archive` and sets `WDS_PLUGIN_ROOT` and `WDS_PLUGIN_REV` for the first run. By hand, the same is `set "WDS_PLUGIN_ROOT=UNPACKED_PLUGIN" && python -B -m unittest TEST_IDS` in cmd.exe.

The Python floor runs with `uv run --no-project --python 3.9 python -B -m unittest discover -s tests`, which works in cmd as well.

For `claude plugin validate --strict`, `update` and `details`, use the desktop app's bundled CLI, `%APPDATA%\Claude\claude-code\<version>\<build>\claude.exe` (2.1.293's build folder is `83cb0bd7fed4`). The one on PATH is older.

## Gotchas

- **Keep `tooling/` beside the plugin.** Never put a `node_modules` above `plugins/`: Node searches parent folders, and one there replaced the stub modules the browser-resolution tests plant (16 failures).
- **Bytecode.** Run Python with `-B` or `PYTHONDONTWRITEBYTECODE=1`. Without either, test discovery alone writes `tests/__pycache__` into the plugin.
- **Line endings.** `.gitattributes` stores every text file with LF. A CRLF checkout breaks the POSIX hook and the byte-for-byte tests.
- **Backslashes in heredocs.** The Bash tool unescapes `\\` inside heredocs, so write Python that contains backslash escapes with the Edit tool.
- **Linked `node_modules`.** The real-tool tests give their temp project a linked `node_modules`: a junction on Windows. Remove a junction with Python's `os.rmdir`, never `rm -rf`.
- **stylelint 17** writes its JSON report to stderr, clean or not; stdout stays empty.
- **eslint-plugin-better-tailwindcss** resolves `tailwindcss`, and reads `entryPoint` and `tailwindConfig`, from its `cwd` setting, ESLint's working directory unless set. Part 5 sets `cwd` to the project and anchors both paths there (#125): ESLint 10 loads a config from whichever folder it lints.
- **Never write into OneDrive** or the folders redirected into it (Documents, Desktop, Pictures, Music, Videos). Downloads is safe.
- **The desktop app is an MSIX package.** Its bundled CLI is really in `C:\Users\vybec\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude-code\`; Claude's tools see it under `%APPDATA%`, the owner's terminal does not. Give the owner the real path.
- **Evals are real model calls** on the owner's account. From the plugin: `claude plugin eval . --tag routing --ablation none --trust-plugin --no-publish --model claude-sonnet-5-5 --output-dir SCRATCHPAD` with the bundled CLI (signed in, 2026-10-10), about $0.09 a routing run. Ask the owner before any run.
- **Commands you give the user** to run must work in cmd.exe. (The Commands block above is for the Bash tool.)
- **Never run `npm ci` in a worktree whose `tooling/*/node_modules` is a junction**: it deletes the real toolchain through the link.
- **The reader's copies.** `shared/project_config.py` and `shared/dtcg.py` have ten copies each, `shared/project_config.mjs` seven (`hooks/` among them). After a merge from a branch below, copy the three masters over every copy: git merges each copy on its own.
- **The old id stays in four formats** that users' projects hold: the contract schema `web-design-suite/contract/1`, the DTCG `$extensions` key `io.github.vybecode-ltd.web-design-suite`, the install-gate stamp's `"plugin": "web-design-suite"`, and `.design-suite.json`. The 4.0.0 rename to `pro-web-design-suite` left them alone on purpose; never "fix" them.
- **A DTCG resolver** (`*.resolver.json`) reads its sources only from its own folder or below, by name and by real path, in both readers (#105).

## Conventions

- **Regression tests.** Every fix gets a regression test, seen failing on the previous release's tag and passing now. The reports list the fail-before counts, and the controls and guards.
- **One set of rules.** A gate change goes into `skills/web-design-studio/assets/rules/design-rules.json` first. Then the audit, the stylelint config and the ESLint config follow, each with a real-tool test in `tests/test_real_tools.py`. Data the spec writes into a gate's `BEGIN design-rules` block (the layer order, the nesting depth, the system colours, the value shapes and allowlists, the colour functions, the literal units) changes by rerunning `tools/sync_rules.py`, never by hand. Every example in the spec runs through each gate its section names (`test_rules_spec`, `test_real_tools`).
- **Facts.** A figure from outside the plugin is re-read at its source and registered, with its quote, in `tests/fixtures/evidence.json`.
- **Size limits.** A SKILL.md stays at or under 20,500 bytes and a reference under 60.5 KB (`tests/test_skill_budget.py`).
- **Git.** One branch per PR (a phase has several), conventional commits. Read the staged diff before each commit. Claude merges, once CI is green, every review thread is resolved and the PR is clean, with a merge commit; a stack merges bottom-up, retargeting the next PR to `main` before the merged branch is deleted (never `gh pr merge --delete-branch` on a branch another PR targets). Tag a release after its merge.
- **Docs.** Plans and reports go in `dev plans/`. Update the docs in the same PR as the code, and keep this file lean.

## Map

```
.claude-plugin/marketplace.json   the repository as a marketplace; the plugin is at ./plugins/pro-web-design-suite
plugins/pro-web-design-suite/     the plugin; it ships without its tests/, evals/ and tools/ (build.py's DEV_ONLY)
  skills/<13 skills>/             SKILL.md, references/, scripts/, assets/
  shared/token-contract.md        the master copy of the contract (13 copies must match it)
  shared/dtcg.py                  DTCG 2025.10 and Tokens Studio, read and write (a copy beside each project_config.py)
  hooks/                          hooks.json and design_hooks.mjs: the opt-in gate, token diff and guard, the router
  workflow-commands/              the sixteen commands only the user invokes (/gate, /new-system, /deck...), added by plugin.json's `skills`
  agents/                         the six subagents (design-critic, gate-runner, the auditors and reviewers)
  mcp/, .mcp.json                 the MCP server: the gates as tools (node design_gates.mjs)
  evals/                          claude plugin eval cases: routing/ (one per skill), boundaries/ (sibling pairs), and outcome cases in build/, systems/, gates/, lifecycle/, persuasion/, delivery/
  tests/                          the suite; fixtures/ holds the pointer and evidence registers
  tools/                          check.py, check_pointers.py, fail_before.py, sync_rules.py, sync_snippets.py, sync_caniemail.py
  CHANGELOG.md, README.md, LICENSE
tooling/                          pinned tools for the tests (main/, tailwind-v3/); release/build.py
.github/workflows/                ci.yml (the suite on three platforms), release.yml (a v* tag makes the release, then `distribute` writes the distribution repository), evals.yml (the routing and outcome evals, by hand)
dev plans/                        the review, the phase plans and reports, the completion plan and inventory
docs/HANDOFF.md                   the current state and the next steps, one page
```
