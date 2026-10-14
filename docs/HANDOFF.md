# Handoff

**2026-10-13, second session**, after P36's first three parts (Phase 6b, 4.0.0) and this docs PR. **Next: P36's last part** (LC-B5's v4 `--spacing` census and N40), unless the owner picks another workstream.

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then the work in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **Phase 6b has begun.** The owner chose P36 (Tailwind v4) first. Three PRs merged, each with CI green on its head, every thread resolved and GitHub clean:
  - **#125, P36 part 1, decision D4: the breaking change.**
    - Part 5 of `eslint.design.config.mjs` moves to **eslint-plugin-better-tailwindcss 4.9.0**: one block for Tailwind v4 (`entryPoint`) and v3 (`tailwindConfig`), with the plugin's `cwd` set to the project.
    - The spike (`dev plans/web-design-suite-d4-spike.md`) ran both plugins over the same fixtures, and the owner chose the move. v3 loses the conflict check.
    - The CHANGELOG has `## 4.0.0 — unreleased`, with the upgrade steps. Codex 2 and CodeRabbit 1 (the same `cwd` finding); Codex's `cx` claim was declined with evidence.
  - **#126, P36 part 2, SB-C3: `tw_probe.mjs` and `/tw-probe`**, the sixteenth command.
    - It compiles a v4 entry with the project's own tailwindcss.
    - Every `@theme` role must give its class, and none of a stock sample may generate.
    - Two review rounds: Codex 5 and CodeRabbit 2, all fixed with tests (inline sources, `url()` imports, names that own several classes, the prefix, the skill path). It also fixed the audit, which read `${file}.css` as an emotion template.
  - **#127, P36 part 3, SB-B5: stack-tailwind.md §2.10**, v4's variants after `--*: initial`.
    - Container queries become literal `@custom-variant`s; it covers `motion-reduce:`, `forced-colors:`, `starting:`, `not-*`, `@reference` in modules, and `@source inline()`.
    - Each claim is compiled from the reference by a test. Codex: no findings.
- **The owner's decisions:** P36 first; D4, the switch for both majors; N40 scheduled with P36's last part (the ΔE colour match from R3.6's live check).
- **At the end:** `main` is this docs PR's merge. No other PR is open. The checkout is on `main`, with no other worktree.
- **The plan:** 21 open items, 21 scheduled. About 1,119 tests.

## Next steps

1. **P36's last part** (the plan's `P36` row): LC-B5's rest and N40.
   - A v4 project that keeps `--spacing` has every numeric class, so the census counts `p-4` at its value, the proposal maps it, and the codemod rewrites it.
   - framework-migrations.md §5 gets Move 1 in v4's form, with `tw_probe` as its check.
   - `cluster_values.py` matches a colour by hue family and chroma, not ΔE alone.
2. Then the owner's next workstream: P34, P35, P37, P41, or P42 and P43.
3. R4 follows R3.6's order: a live check, the release PR, the evals on its merge, the tag.

## Open owner decisions

- Which workstream follows P36.

## Warnings

- **Bash heredocs eat backslashes.** It happened four times this session. Write such code with the Write tool into a script file, or use Edit.
- **A doc's own example finds the bug.** Compiling §2.10's block found `tw_probe`'s inline-source bug.
- **The audit is a gate on the plugin's own scripts too:** a JS file is read for CSS-in-JS, and `test_powershell_json` refuses `JSON.parse(fs.readFileSync(…))`.
- **CodeRabbit reviews a stacked PR when it is retargeted to `main`.** That review is not a gate.
- **The masters and their copies.** After a merge from below, copy `shared/dtcg.py` and both `project_config` masters over every copy. This session touched none.
- **Still open from earlier:**
  - `perf_audit.py` and an unbundled `@import` chain;
  - the TBT flake on macOS;
  - `test_critique_snapshots`;
  - three tokens outside Display P3;
  - a local build never matches the release's checksums;
  - don't grep `tooling/`;
  - the repository is public;
  - `Vybecode-LTD/wds-gate-scratch` is the owner's to delete.
