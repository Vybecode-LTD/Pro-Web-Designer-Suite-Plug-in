# Handoff

**2026-10-10**, after P26 parts 2 and 3 (#87, #88), P27 part 1 (#89) and this docs PR. 3.4.0 is the latest release; Phase 5 (3.5.0, a full Claude Code plugin) is under way.

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then P27 part 2 (the two hooks) and P28 (the MCP server, `bin/`, the LSP spike) in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **Merged this session:** #87, #88 and #89. Each had CI green on its head, every thread answered and resolved, CodeRabbit finished and GitHub clean. They were stacked and merged bottom-up, each retargeted to `main` before its base branch was deleted. This docs PR follows. No other PR is open.
- **What they did:**
  - **#87, P26 part 2: the systems and the lifecycle.** `/new-system` (a brand colour to the starter system, role pairs checked), `/contrast`, `/migrate` (the census), `/release-check` (extract, diff, gate, changelog, guide), `/figma-sync` (audit, questions or tokens, diff) and `/docs-check`. `figma_audit.py` gained `--out`; `extract_literals.py -o` creates its folder.
  - **#88, P26 part 3: delivery, persuasion and the runtime gates.** `/schema-to-screens` (stops on a blocking security finding), `/email-build`, `/deck` (stops on a blocking critique finding) and `/gate-a11y`, `/gate-perf`, `/gate-matrix`, whose browser steps run through `node`. `introspect_schema.py`'s outputs create their folder. PS-C11 closes.
  - **#89, P27 part 1: the subagents.** `design-critic`, `gate-runner`, `a11y-auditor`, `design-auditor`, `supabase-security-reviewer` and `codemod-batch-reviewer` in `agents/`, none able to edit a file, and `/critique`, which hands the work to the critic and saves its findings unedited. XC-C3, XC-C4, PS-C4, SS-C6 and LC-C9 close.
- **The reviews found 16 real issues** (9 on #87, 3 on #88, 4 on #89), each fixed with a test failing on the head it reviewed, and CI found one more (Python 3.9's argparse). The lessons are in the next-session prompt's §0.
- **The plan:** 41 open items, 41 scheduled (`check_execution_plan.py`). Tests: about 904. Fifteen workflow commands and six agents.

## Next steps

1. **P27 part 2:** the two hooks P25 closed without: GT-C9's `a11y_static` on the edited file and DL-C7's email build and lint, each behind a new `hooks` key in both readers. Decide first how an email template is recognised.
2. **P28:** an MCP server for the gates, then `bin/` (only with the owner's yes: it keeps the plugin out of claude.ai and Cowork installs) and an LSP spike.
3. Then P29 and P30 (the evals), and R3 (3.5.0).

## Warnings

- **Nothing new has run in a live session.** The installed plugin is 3.4.0. Before R3, load the branch's plugin (`claude --plugin-dir plugins/web-design-suite`) on Windows and check:
  - the hooks: the gate on a real edit, the token diff, the guard's refusal, how often the router speaks;
  - each of the fifteen commands, including that its `allowed-tools` spare the prompt, and that a quoted colour reaches the runner;
  - each agent, and that `/critique` reaches `web-design-suite:design-critic` by that name.
- **The CI template has not run on GitHub.** Before R3, install it in a scratch repository and push.
- **Open question:** `perf_audit.py --src` reports the starter's own `index.css` `@import` lines as `css-import` LCP errors, so a project started with `/new-system` fails `/gate --src`'s performance gate. The starter means a bundler to inline them. Decide whether the perf gate should skip an entry stylesheet a bundler inlines, or the starter should stop using `@import`.
- **Worth the owner's look:** the router runs in every project unless `design_hooks` is off; the gate, the token diff and the guard are opt-in.
- **A merge from below leaves copies behind.** Seven `project_config.mjs` copies and ten `project_config.py` copies: after every merge, copy both masters over them.
- **`check.py` prints only the first failure.** When it reports more, run the suite directly and grep `^FAIL:`.
- **The token counter** reset about 20 times this session, on every review event. This session used about 580 thousand.
- **SKILL.md budgets:** client-presentation-builder, email-template-system and landing-page-conversion 20,497 bytes of 20,500; perf-budget-gate 20,494; component-state-matrix 20,493.
- **Still open from earlier:**
  - The hydration timing test flakes on Windows 3.14 runners (re-run it).
  - `--warning-700`, `--danger-100` and `--info-100` fall outside Display P3.
  - `check_roles.py` clips a colour outside sRGB.
  - The worked examples are tests.
  - A local build never matches the release's checksums.
  - Don't grep `tooling/`.
  - The repository is public.
