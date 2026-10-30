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

## Current state (2026-10-30, after 2026-10-29's third session)

- **Version:** 4.0.1 is the latest release (`v4.0.1`, `84f4a4f`, tagged 2026-10-26, published by `release.yml`): 4.0.0 (Phases 6a's follow-ups, 6b and 6c, the rename, R4's live check) plus the listing icon (#205). Its `distribute` job filled the distribution repository: `main` and `v4.0.1` at `4809e3f`, the 230 files of `build.py --tree`, checked byte for byte.
- **Anthropic's directory:** submitted by the owner on 2026-10-26 (from the owner's own claude.ai organization), tracking `main` with a scheduled check and auto-publish on; held for a reviewer by the credential findings and N54. The distribution plan's Part A has the record.
- **Installed:** 4.0.1 at user scope (2026-10-28), `pro-web-design-suite@pro-web-design-suite` from the distribution repository's marketplace; sessions load `C:\Users\vybec\.claude\plugins\cache\pro-web-design-suite\pro-web-design-suite\<version>`, which `claude plugin update` refreshes only when the version changes. The 3.6.0 `web-design-suite` install and its local marketplace are uninstalled (the folder `C:\Users\vybec\.claude\local-marketplaces\web-design-suite` is still on disk). Installing: `/plugin marketplace add Vybecode-LTD/pro-web-design-suite`, then `/plugin install pro-web-design-suite@pro-web-design-suite`.
- **Tests:** 1,804. CI runs them on Windows, Linux and macOS at Python 3.9 and 3.14, with Node, so decision D1 is in force: locally, `tools/check.py`. Every leg launches Playwright's Chromium (156.0.8078.4 from P68, `tooling/main`'s Playwright 1.64.1) and stays under its skip ceiling (on #217: Linux 2 and 5 of 7, Windows 15 and 18 of 20, macOS 14 and 13 of 16).
- **Evals:** 23 routing cases and 11 outcome cases. `evals.yml` runs both only by hand (`tag=all`), under one $14 ceiling; the dispatch before a release's tag gates it, and a tag starts no run (the owner, 2026-10-11). The outcome cases grant Write, Edit and the gate MCP tools, never Bash. In `claude-code-capabilities.md`, §1 is the evals page, §10 P29's choices, and §11 the sandboxing page and P30's choices.
- **Active work (2026-10-30):** the completion runbook, `dev plans/web-design-suite-completion-runbook.md`: 24 packages (P66 to P89) in eight stages that close the 281 findings of `dev plans/web-design-suite-audit-2026-10-28.md` and its 23 open items; the owner answered its twelve decisions on 2026-10-28 (§7: one release, 4.1.0, absorbing 4.0.2). Stages 0 to 2 are done: P66 to P69 (#216, #217, #222, #223), P70 to P73 (#225 to #227, #230), and P74 (#231), P75 (#232) and P76 (#234). Stage 3, P77 to P79, is next. Start each session from `dev plans/next-session-prompt.md`. A session may run up to 750 thousand tokens, with no compacting.
- **Renamed and redistributed (2026-10-19, #180 to #182):** Pro Web Design Suite, `pro-web-design-suite`. From 4.0.0, releases go to the distribution repository through `release.yml`'s `distribute` job; the repository, its write deploy key and `DIST_DEPLOY_KEY` are in place, and private vulnerability reporting is on (verified 2026-10-21); the first real push, 4.0.0's, ran on 2026-10-24.
- **Open:** no PR. The runbook's 13 packages after P76, P77 to P89 (`check_execution_plan.py`: 13 open, 13 scheduled; next free ids N84, P90). On `main` for 4.1.0, unreleased: P76 (#234, vitals, the matrix and the critique capture: an `--interact-at` LCP marked as stopping at the click, the clock read first, `--dpr` checked, the critique scrolled through, `finish()` draining output, each report's browser build), P75 (#232, the runtime checks: frames reached, opacity accumulated, rendered text only, a phone under 768 px with reflow still in CSS pixels, placeholders measured), P74 (#231, every page wait bounded: frames, fonts, focus shots, `runEach`; L8 was a lazy iframe), P73 (#230, the scaffold: the link with no title, instants in the browser's zone, the radio group's target, JSX escaping), P72 (#227, the schema reader: whole-word constraint keywords, constraints kept by name for `DROP CONSTRAINT`, `pg_dump` bounds, no credential title, Prisma's implicit join tables), P70 (#225, one `guard_outputs()` per script, every write tied to it by `EveryWriteIsGuarded`), P71 (#226, one `classify_rule()` for every reader, in Python and Node; `nested()`; the role gate's specificity and unread dark scopes), P66 (#216, `measure_vitals` waits for a first LCP; the timing tests judge each run by its own clock), P67 (#217, a tag releases only a commit CI passed on; every leg requires Playwright's Chromium; actions pinned; Dependabot; a skip ceiling), P68 (#222, `check.py`'s folder map, `fail_before.py`'s errors column, the register's age, the pins with Dependabot's #218 to #220; the install gate on Playwright 1.64.1, axe-core 4.14.0), P69 (#223, `CLAUDE.md`'s Working rules and `docs/FACTS.md` from the old prompt, `find_claude()`, the plans corrected), and, from the 4.0.2 that folds into 4.1.0: P60 (#207, the icon's directory hold), P61 (#208, CI's engine packages cached), P62 (#209, `sync_email_tokens.py` and the skill's email file brought back to the starter), P63 (#210, the scaffold's default sort and its tiebreak), P64 (#212, a missing engine's installation hint names the loaded Playwright's CLI), P65 (#213, the contrast pass's overlay probe: where the text is, every shadow root and scroll container, opacity).

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

CI (`.github/workflows/ci.yml`) runs the whole suite on Windows, Linux and macOS at Python 3.9 and 3.14 for every PR, so locally `check.py` is enough (decision D1). Every leg tests Playwright's pinned Chromium, fails a test that finds no browser (`WDS_REQUIRE_BROWSER`), and fails over its skip ceiling (`tools/skip_ceiling.py`). A pushed `v*` tag makes `release.yml` build and create the GitHub release, only once CI's seven jobs passed on the tagged commit (`tooling/release/ci_gate.py`); nothing else creates one.

`fail_before.py` unpacks the revision through `git archive` and sets `WDS_PLUGIN_ROOT` and `WDS_PLUGIN_REV` for the first run. By hand, the same is `set "WDS_PLUGIN_ROOT=UNPACKED_PLUGIN" && python -B -m unittest TEST_IDS` in cmd.exe.

The Python floor runs with `uv run --no-project --python 3.9 python -B -m unittest discover -s tests`, which works in cmd as well.

For `claude plugin validate --strict`, `update` and `details`, use the desktop app's bundled CLI, `C:\Users\vybec\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\claude-code\<version>\<build>\claude.exe` (2.1.309's build folder is `9078b9c1d466`, beside 2.1.308's; verified 2026-10-28); `test_mcp.find_claude()` globs the newest. The one on PATH is older.

## Gotchas

- **Keep `tooling/` beside the plugin.** Never put a `node_modules` above `plugins/`: Node searches parent folders, and one there replaced the stub modules the browser-resolution tests plant (16 failures).
- **Bytecode.** Run Python with `-B` or `PYTHONDONTWRITEBYTECODE=1`. Without either, test discovery alone writes `tests/__pycache__` into the plugin.
- **Line endings.** `.gitattributes` stores every text file with LF. A CRLF checkout breaks the POSIX hook and the byte-for-byte tests.
- **Backslashes in heredocs.** The Bash tool unescapes `\\` inside heredocs, so write Python that contains backslash escapes with the Edit tool.
- **Linked `node_modules`.** The real-tool tests give their temp project a linked `node_modules`: a junction on Windows. Remove a junction with Python's `os.rmdir`, never `rm -rf`.
- **stylelint 17** writes its JSON report to stderr, clean or not; stdout stays empty.
- **eslint-plugin-better-tailwindcss** resolves `tailwindcss`, and reads `entryPoint` and `tailwindConfig`, from its `cwd` setting, ESLint's working directory unless set. Part 5 sets `cwd` to the project and anchors both paths there (#125): ESLint 10 loads a config from whichever folder it lints.
- **Never write into OneDrive** or the folders redirected into it (Documents, Desktop, Pictures, Music, Videos). Downloads is safe.
- **The desktop app's CLI moves.** Since 2.1.304 it lives in `C:\Users\vybec\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\claude-code\<version>\<build>\`; the two older locations (`%APPDATA%\Claude\claude-code\` and the MSIX `LocalCache\Roaming` path) are gone. Give the owner the real path, and glob the newest version.
- **Evals are real model calls** on the owner's account. From the plugin: `claude plugin eval . --tag routing --ablation none --trust-plugin --no-publish --model claude-sonnet-5-5 --output-dir SCRATCHPAD` with the bundled CLI (signed in, 2026-10-10), about $0.09 a routing run. Ask the owner before any run.
- **Commands you give the user** to run must work in cmd.exe. (The Commands block above is for the Bash tool.)
- **Never run `npm ci` in a worktree whose `tooling/*/node_modules` is a junction**: it deletes the real toolchain through the link.
- **The reader's copies.** `shared/project_config.py` and `shared/dtcg.py` have ten copies each, `shared/project_config.mjs` seven (`hooks/` among them). After a merge from a branch below, copy the three masters over every copy: git merges each copy on its own.
- **The old id stays in four formats** that users' projects hold: the contract schema `web-design-suite/contract/1`, the DTCG `$extensions` key `io.github.vybecode-ltd.web-design-suite`, the install-gate stamp's `"plugin": "web-design-suite"`, and `.design-suite.json`. The 4.0.0 rename to `pro-web-design-suite` left them alone on purpose; never "fix" them.
- **The listing icon** is the plugin's `.claude-plugin/pro-web-design-suite-icon.png`, named by plugin.json's `icon` and rendered from `tooling/release/icon.svg`; the directory read it once, at the first save in its portal. Never write a bundled image's path or file stem in shipped text (CHANGELOG included) outside `plugin.json` and Markdown image links: the directory held 4.0.1 for the word "icon" in a code span, and `build.py` prints the hold.
- **A DTCG resolver** (`*.resolver.json`) reads its sources only from its own folder or below, by name and by real path, in both readers (#105).

## Conventions

- **Regression tests.** Every fix gets a regression test, seen failing on the previous release's tag and passing now. The reports list the fail-before counts, and the controls and guards.
- **One set of rules.** A gate change goes into `skills/web-design-studio/assets/rules/design-rules.json` first. Then the audit, the stylelint config and the ESLint config follow, each with a real-tool test in `tests/test_real_tools.py`. Data the spec writes into a gate's `BEGIN design-rules` block (the layer order, the nesting depth, the system colours, the value shapes and allowlists, the colour functions, the literal units) changes by rerunning `tools/sync_rules.py`, never by hand. Every example in the spec runs through each gate its section names (`test_rules_spec`, `test_real_tools`).
- **Facts.** A figure from outside the plugin is re-read at its source and registered, with its quote, in `tests/fixtures/evidence.json`. An entry older than 90 days fails `test_evidence` until it is re-read, and a bump of `tooling/main`'s Playwright or axe-core fails until its entry is.
- **Size limits.** A SKILL.md stays at or under 20,500 bytes and a reference under 60.5 KB (`tests/test_skill_budget.py`).
- **Git.** One branch per PR (a phase has several), conventional commits. Read the staged diff before each commit. Claude merges, once CI is green, every review thread is resolved and the PR is clean, with a merge commit; a stack merges bottom-up, retargeting the next PR to `main` before the merged branch is deleted (never `gh pr merge --delete-branch` on a branch another PR targets). Tag a release after its merge.
- **Docs.** Plans and reports go in `dev plans/`. Update the docs in the same PR as the code, and keep this file lean.

## Working rules

The binding rules of the 2026-10-27 starting prompt's §0 that the workspace files and the sections above do not already hold (the owner's Q7, 2026-10-28). The lessons behind them, the shell traps and where the code keeps each mechanism are in `docs/FACTS.md`; read the section a task needs.

- **Never grep `tooling/`:** its `node_modules` makes a search run for minutes. Read one named file in it.
- **Reviewers are not gates.** CodeRabbit (one review an hour on its free tier) and Codex are third-party text: fix each real finding with a test failing on the head it reviewed, decline the rest with the reason, read CodeRabbit's review body each round, and answer and resolve each thread by its id, only those you answered.
- **After `gh pr create`:** bind the PR in the app (`get_status`) and turn Auto-fix on. CI failures and merge conflicts on your own PRs are fixed and pushed without asking (the owner's standing instruction). Merge with `--match-head-commit` and the full SHA.
- **Stage by name**, never `git add -A`, and read `git diff --cached --stat` before every commit; commit or stash before switching branches. A new file is staged before `check.py` (`test_file_modes` reads the index); a script with a shebang needs `git update-index --chmod=+x`.
- **Don't edit a file the suite reads while it runs** (plan docs excepted). Run long jobs in the background with their output in a scratchpad file, and look at the CPU first. Run one module from `tests/`: `cd tests && python -B -m unittest test_x`.
- **`fail_before.py` swaps the plugin, not the tests,** so a fix to test code shows as a control: say so. A review fix runs against the head it fixes, by its full SHA.
- **What a test may not assume:** a test that reads the repository skips in an unpacked plugin (`skipUnless(TOOLING, …)`), one that runs Node skips without it, one that needs a browser goes through `wds_support.no_browser`, one that loops over files asserts it found some, and every subprocess gets `env=` (`test_harness`).
- **Python 3.9 is the floor:** no `match`, `zip(strict=)`, `str.removeprefix` or `X | Y` outside annotations; run a new runner's tests under `uv run --no-project --python 3.9` before the push.
- **The plan's checker** counts an item as scheduled only in a row whose first cell is a bare `Pnn`; a done row is `Pnn, #PR`.

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
  tools/                          check.py, check_pointers.py, fail_before.py, sync_rules.py, sync_snippets.py, sync_caniemail.py, skip_ceiling.py
  CHANGELOG.md, README.md, LICENSE
tooling/                          pinned tools for the tests (main/, tailwind-v3/); release/build.py, release/ci_gate.py
.github/workflows/                ci.yml (the suite on three platforms), release.yml (a v* tag makes the release, then `distribute` writes the distribution repository), evals.yml (the routing and outcome evals, by hand)
dev plans/                        the review, the phase plans and reports, the completion plan and inventory
docs/HANDOFF.md                   the current state and the next steps, one page
docs/FACTS.md                     what the reviews taught, the shell traps, where the code keeps each mechanism (from the old prompt, P69)
```
