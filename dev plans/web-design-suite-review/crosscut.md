# Cross-cutting review — plugin level (prefix XC)

Reviewer: lead. Scope: packaging, README, tests/CI, Claude Code integration, cross-platform
docs, scale and Python compatibility. Skill content is reviewed in the sibling files.

## A. Issues

- **XC-A1 · medium · README.md:111–114** — "Quick start on an inherited codebase" fails as
  written. Step 1 (`extract_literals ./src --format report`) writes no `literals.json`, so
  step 2 exits 2 ("Create it first: … --format json -o literals.json"); steps 3–4 pass the
  mapping as the path to rewrite and omit `-m`, so both exit 2 ("the following arguments are
  required: -m/--mapping"). Verified by running the sequence. Fix: `extract_literals ./src
  --format json -o literals.json` and `apply_codemod ./src -m proposal/mapping.json --kind
  spacing [--apply]`. All 134 distinct documented invocations were parsed with each script's
  real argparse parser — these two README lines are the only ones rejected.
- **XC-A2 · low · README.md:83–84** — install instructions use a placeholder
  (`/plugin marketplace add <this repo>`) and the short plugin name; the id is
  `web-design-suite@web-design-suite`, and the zip/local-folder route the author actually uses
  is not described.
- **XC-A3 · medium · README.md:11, 87** — "any single `.skill` file works standalone" and "each
  `.skill` file installs with the Add skill button": no `.skill` files ship and nothing in the
  repo builds them; and at least eight skills run web-design-studio's `audit_design` (or cite
  its references), so a standalone skill cannot run its own gate. The claim needs qualifying
  or the scripts vendoring.
- **XC-A4 · low · packaging** — running a script the documented way (`python -m scripts.X` from
  the skill folder) writes `__pycache__` into the installed plugin (seen in the live install
  after real use). No `.gitignore`; a zip built from the folder would ship bytecode. Root
  cause is XC-A8 (`-m` caches bytecode; running a script by path does not cache the main
  module); `sys.dont_write_bytecode = True` in each script closes the rest.
- **XC-A5 · low · shared/token-contract.md** — referenced by nothing; its role (master copy the
  13 are synced from?) is undocumented and the "byte-identical in all thirteen" claim is not
  enforced by any test (it holds today: 14 identical copies).

- **XC-A6 · medium · a11y-audit-runner/scripts/a11y_static.py:963, 683, 1249** — quadratic on
  large pages: 500 rows 1.5 s → 1,000 3.2 s → 2,000 11.8 s → 4,000 46 s, and a 2.8 MB page
  (20k rows) did not finish in 180 s. Profile (2,000 rows, 15.6 s): `ancestors_of()` 8.2 s
  self time building 8M list entries and `ids_with_for()` 2.7 s — both recomputed for every
  control at line 963 (`_labelled(t, ids_with_for(open_tags), a, ancestors_of(t))`) — plus
  1.9 s of `str.count` for line numbers. Fix: compute the `for=` id set once per document,
  keep a parent stack/pointers for ancestors, precompute newline offsets and `bisect`.
- **XC-A7 · medium · design-token-migration/scripts/extract_literals.py:380–382** —
  super-linear on long lines, which is what minified CSS looks like: 96 KB on one line 1.5 s,
  387 KB 12.5 s; one 20k-layer declaration 139 s. 8.6 of 10.9 s (profiled) is
  `line_col()`'s `text.count("\n", 0, offset)` + `text.rfind("\n", 0, offset)` per literal.
  A 1–2 MB committed bundle would take minutes. Fix: one newline index per file + `bisect`.
  (Everything else scaled fine: 1,500 files/60k rules 54 s; perf_audit on 2,000 files 9 s;
  extract_system on 8k tokens/400 components 8 s; 600-table schema 1 s, scaffold 11 s;
  8k-row email lint 1.4 s; unterminated comments, 100k-char selectors, 3,000-deep nesting,
  50k unclosed tags and a 200k-space attribute all handled without a crash.)
- **XC-A8 · medium · every SKILL.md with a script** — the invocation contract is ambiguous.
  Skills say `python -m scripts.audit_design src/` and "run from the skill root", but `-m
  scripts.X` needs the *skill* folder as cwd (or on PYTHONPATH) while `src/` is relative to
  the *user's project*. Nothing says which wins, and no SKILL.md uses Claude Code's
  `${CLAUDE_SKILL_DIR}` / `${CLAUDE_PLUGIN_ROOT}` substitutions (0 matches). Taking "run from
  the skill root" literally writes relative outputs (`-o literals.json`, `--write-baseline`)
  into the installed plugin, silently misses the project's `.design-baseline.json` (default is
  cwd-relative), and leaves `__pycache__` in the install (XC-A4 is a symptom). Verified: all
  21 scripts already run by file path from any cwd (`python <abs>/scripts/X.py --help` exit 0;
  the two with sibling imports have a path fallback), so the fix is docs-only — see XC-C10.
- **XC-A9 · medium · web-design-studio/scripts/audit_design.py:225, 1165** — baseline keys
  embed the path exactly as walked from the argument, so a baseline only matches the same
  path spelling from the same cwd. Verified: baseline written with `src/` from the project
  root → `src/`, `src`, `./src` exit 0, but the absolute path to the same folder exits 1 with
  all 4 baselined findings back, even with `--baseline <absolute file>`; and a missing default
  baseline is skipped silently. Combined with XC-A8 this is the likeliest way the "turn the gate
  on today" story breaks. Fix: key on the path relative to the baseline file's directory
  (resolve both sides), and print a note when no baseline was found. Lesser, same code: keys
  omit the line and the filter is set membership, so a copy of a baselined line in the same
  file is also masked (L1173) — acceptable if documented, or store per-key counts.

## B. Gaps

- **XC-B1** — the plugin ships only skills: 0 agents, 0 hooks, 0 commands, 0 MCP/LSP servers
  (`claude plugin details`). Law 9 ("nothing ships un-audited") is not enforced on Claude's own edits.
- **XC-B2** — no eval suite, so there is no evidence the skills fire on the right prompts or beat
  the no-plugin baseline. Claude Code 2.1.280 has `claude plugin eval` (cases + graders +
  with/without ablation + cost cap) — see claude-code-capabilities.md.
- **XC-B3** — the test suite is regression/guard tests only (72); there is no smoke test per
  documented command, no CI workflow, and no declared minimum Python. Verified: all 72 pass on
  Python 3.12.10 as well as 3.14; every script parses with 3.8 grammar.
- **XC-B4** — no CHANGELOG (the suite teaches semver and changelogs for design systems but keeps
  none itself), no contributor/architecture notes for the suite's internals.
- **XC-B5** — docs are bash-first: 38 backslash line continuations, 9 `&&`/`||`, 5 `/tmp/`
  paths, `$(…)`, `VAR=value cmd`, `python3`; Windows/PowerShell is mentioned 39 times in
  1.5 MB. Claude runs these fine through Git Bash; a person pasting into cmd.exe or PowerShell
  5.1 cannot.
- **XC-B6** — discoverability in a heavy environment: in this machine's sessions the 13 skills
  are listed by name only (descriptions dropped by the skill-listing budget), so automatic
  triggering rests on the names. The 13 descriptions total ≈11.8k characters, more than the
  whole 8,000-character fallback budget on their own; plugin skills are not affected by the
  user's `skillOverrides`. Separately, a new session here starts with ~222k tokens of
  system prompt, tools and skill listing — the Haiku-based guide agent could not start at all.

## C. Improvements

- **XC-C1 · L · high** — eval suite (`evals/`): per-skill triggering cases (`tool_used: Skill`)
  plus outcome graders (e.g. "build a pricing section" → `audit_design --strict` clean, no raw
  literals), run with ablation to prove value; CI with a cost ceiling. Constraints from
  claude-code-capabilities.md: `--threshold` defaults to 1.0; trigger-only cases
  (`Read, Glob, Grep, Skill`) run natively, but any case that runs a script needs
  `--allow-tools "Bash(python *)"`, which needs an OS sandbox — WSL2 on this machine.
- **XC-C2 · M · high** — opt-in design-gate hook: PostToolUse on Edit/Write of
  css/scss/jsx/tsx runs `audit_design` on the changed file and feeds findings back to Claude
  (`additionalContext`), exec form (`python` + `${CLAUDE_PLUGIN_ROOT}/…`) so it works on
  Windows. The plugin is installed user-scope, so the hook fires in every project: it must
  no-op unless the repo opts in (config file present), with a `userConfig` boolean as the
  global off switch.
- **XC-C3 · M · high** — user-invocable workflows, built as skills with
  `disable-model-invocation: true` (commands are now skills; this also keeps them out of the
  crowded listing): `/gate` (design + perf + a11y static in one run), `/install-gate` (vendor
  scripts, configs and the pre-commit hook into a repo — the step the README assumes but never
  automates), `/critique` (adversarial critique in a subagent), `/new-system` (brand colour →
  ramp, type scale, starter styles).
- **XC-C4 · M · medium** — subagents (design-critic, a11y-auditor) so heavy references load in
  an isolated context rather than the main one.
- **XC-C5 · S · high** — promote this review's harnesses to permanent tests: every documented
  command parses with its real parser; every § pointer resolves; the 14 token-contract copies
  are identical; descriptions parse as YAML and stay ≤1024 chars; README quick starts run as
  doc-tests.
- **XC-C6 · M · medium** — build and release: `tools/build.py` producing the plugin zip and the
  13 `.skill` files reproducibly (no bytecode), CHANGELOG, `claude plugin tag`, and a GitHub
  Actions matrix (Windows/Linux/macOS × Python 3.10–3.14 + Node) running tests, validate and
  evals.
- **XC-C7 · M · medium** — token efficiency: SKILL.md files are 17–28 KB (≈4.4–6.9k tokens per
  invocation); references total 1.54 MB (web-design-studio 617 KB). Aim for SKILL.md ≲12 KB by
  moving tables and worked examples into references; tighten each description to lead with its
  most distinctive triggers (they are 776–955 chars).
- **XC-C8 · M · medium** — one project config file (`.design-suite.json`: token files,
  component globs, stack, budgets, baselines) read by every script, the hook and the commands.
- **XC-C9 · S · low** — cross-platform docs: PowerShell/cmd equivalents for the few shell-only
  recipes, or a single `python -m scripts.gate` entry point so no shell syntax is needed.
- **XC-C10 · S · high** — fixes XC-A8: write every documented command as
  `python "${CLAUDE_SKILL_DIR}/scripts/audit_design.py" src/`, run from the user's project
  root, and cross-skill calls as `${CLAUDE_PLUGIN_ROOT}/skills/web-design-studio/scripts/…`.
  Claude then gets an absolute path it can run from the project root, with no cwd guessing and
  nothing written into the install. Add `allowed-tools` for the plugin's own scripts (the
  documented `Bash(${CLAUDE_SKILL_DIR}/scripts/… *)` pattern) so gates run without a
  permission prompt. Keep the `python -m scripts.X` form in the README for humans and CI.

## Reviewed / commands

`claude plugin validate --strict` (manifests; now also skills) — passed · `claude plugin
details` — 13 skills, ~3,052 always-on tokens · test suite — 72/72 on Python 3.14 and 3.12.10 ·
argparse parse of all 134 documented invocations (harness in the session scratchpad) · README
quick starts run as written · measured description lengths, SKILL.md/reference sizes,
bash-only constructs · scale/hostile-input probe and cProfile of the two slow cases (XC-A6/A7)
· all 21 scripts run by file path from an unrelated cwd (`--help`, exit 0) · SKILL.md
frontmatter keys (only `name`, `description` in all 13 — spec-clean for claude.ai upload) ·
baseline experiment for XC-A9 (4 findings, 5 path spellings, 2 cwds).
