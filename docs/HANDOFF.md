# Handoff

**2026-10-07**, after P20 (#64), P21 in two parts (#65, #66), P44 (#67) and this docs PR. Phase 4 (3.4.0) is under way; 3.3.0 is the latest release.

**The next session starts from `dev plans/next-session-prompt.md`** (orientation, then P22 and P23 in detail). `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **Merged this session:** #64 to #67, each with CI green on its head, every thread answered and resolved, CodeRabbit finished and GitHub clean; then this handoff PR. No PR is open.
- **What they did:**
  - **#64, P20: the scaffold.** Every interview answer reaches the output (`.money` with the currency's own minor-unit scale through `formatMinorUnits`, `.cardinality`, `.label_column`, `.options`, `.zone`, `.shape`, `.default_sort`; `.naive_timestamp` and `.storage` stay advisory, and SKILL.md says so). The forms carry the a11y wiring screen-patterns.md promises: `aria-describedby` and `aria-invalid` on the control, a radio group as `<Field group>` (a fieldset whose legend has the id the group names), one live region, the summary focused once per submit attempt. `server/<table>.schema.ts` (zod) and `server/<table>_schema.py` (pydantic 2) mirror the constraints the form reads, inventions marked. Closes DL-A8, DL-A9, DL-B2.
  - **#65, P21 part 1: the deck's data and print.** `--a11y` reads the suite's own JSON (`a11y_runtime.mjs --json`, `a11y_static.py --json`) as well as axe results, one shape per file; `--handout` writes the client's copy with nothing presenter-only in it; print shows notes only while they are showing; a reversed decision (status, a `Reversed to:` line, or a `## Reversals` row) is shown as reversed on a "What changed since last time" slide; evidence.md's "Say this" lines carry placeholders from the measured files and the coverage of automated tools is cited as a range from the register; `--manual FILE`. Closes PS-A5, A6, A7, A10.
  - **#66, P21 part 2: the presenter window and the docs.** `P` opens a presenter window kept in step over a BroadcastChannel and a direct `postMessage` link (local files); `## Since last time` in the log is read back on the changed slide, a request not done with no reason is a gap; the flaws slide comes before the visuals in every order; `Stage: iteration review` and `Stage: sign-off` reorder the deck; the meeting record claims no legal effect; the landing worked example's painted bands bleed; objection-handling.md §10 is the playbook for a client who rejects the whole direction. Closes PS-A12, A13, A19, B7, C1.
  - **#67, P44: Gmail's limits registered.** 102 KB (the ESPs' figure; the byte-exact 102,400 is measured, which the docs now say) and 16,384 bytes (email-bugs #90) in `evidence.json` for the four email docs; `FIGURE` reads byte counts; the test binds both email scripts' constants to the register. Closes N36.
- **The reviews found 23 real issues** (Codex 11, CodeRabbit 12), each fixed with a test failing on the head it reviewed: among them pydantic's null handling and `AwareDatetime`, exclusive CHECK bounds in both schemas, the boolean controls' error wiring, the summary focus per attempt, JSX-escaped options, the `Reversed to:` line as the only marker, best-practice findings and mixed shapes in the a11y loader, the static audit's "file(s) with findings" label, the sign-off ask at slide 2, the per-file channel and the file:// fallback, negative and placeholder cells in the requests table, and the scripts' Gmail constants bound to the register. Nothing was declined.
- **The plan:** 68 open items, 68 scheduled (`check_execution_plan.py`). Tests: 724.

## Next steps

1. **P22**, the critique: `covers`, notes and `status` in merges, the right counts, and `critique_snapshots.mjs` for the "needs a human" checks (PS-C2, A17, A20, A21, B5, C5). M-L: split it.
2. **P23**, the persuasion references and facts (PS-A8, A9, A14, A15, A16, A18, A22). M.
3. Then P45 (N35, Law 6 in stylelint and ESLint) and R2, the 3.4.0 release.

## Warnings

- **SKILL.md budgets:** client-presentation-builder is at 20,498 bytes of 20,500 and email-template-system at 20,475, after component-state-matrix (20,450), perf-budget-gate (20,405) and design-system-versioning (20,401). A word added there is a word cut elsewhere; detail goes in the references.
- **A `#PRNUM` placeholder** in the inventory and the plan is replaced in the commit right after `gh pr create` (CodeRabbit has a learning for it); do not merge one.
- **The plan checker** reads only rows whose first cell is exactly `P<n>`: a split PR keeps its open half as `P<n>` and the done half as `P<n> part 1, #N`.
- **Stacked PRs:** CodeRabbit skips a PR whose base is not `main`; after retargeting, comment `@coderabbitai review`. A merge commit made with `--no-edit` lacks the attribution line: amend it.
- **`fail_before.py` swaps the plugin, not the tests:** a doc assertion reads the doc through `SKILLS` (which honours `WDS_PLUGIN_ROOT`), never through `__file__`, or it is a control by construction.
- **Bash heredocs eat backslashes**, which also breaks a `\n` inside a Python string in a heredoc script: write such scripts with the Write tool.
- **GitHub had a partial outage on 2026-10-07** (pushes refused with 500 for about ten minutes): retry `git push` every minute until it lands; nothing on this side needs fixing.
- **Still open from earlier:** `--warning-700`, `--danger-100` and `--info-100` fall outside Display P3; `check_roles.py` measures a colour outside sRGB with its channels clipped; the hydration test fails with the run's numbers if it recurs; the worked examples are tests (`TheWorkedRun`, `TheWorkedRelease`); a local build never matches the release's checksums (compare with `tooling/release/compare.py`); don't grep `tooling/`; the repository is public.
