# Handoff

**2026-10-04**, after P6 (#28, #29) and this docs PR were merged into `main`.

**The next session starts from `dev plans/next-session-prompt.md`.** It has the orientation, then P7 in detail (the contract's missing roles, the files the starter refers to, and the comments the files contradict), then P8 if the budget allows.

## State

- **3.2.1 is released** (`v3.2.1`, `63932cf`) and installed. 3.3.0 is in progress on `main`, unreleased.
- **Merged this session:** P6, in two stacked PRs with merge commits, each with CI green on its head, every review thread resolved, and GitHub reporting it clean.
  - **#28, the type generator** (SS-B5, and the type halves of SS-A9, SS-B7 and SS-C5).
    - `--preset studio` prints tokens.css's `--text-*` exactly, and it is the default when no scale flag is given.
    - A ratio run with a step or a fluid minimum under 11px exits 2, and names the ways out computed for that run. `--allow-small` forces it.
    - typography.md §10 adds Barvian's 2.5× bound (registered in `evidence.json`) and the starter hero's zoom figures; §15 checks both.
    - Codex found that `--snap-px` could round a fluid span past 2.5×; every emitted span is checked now.
  - **#29, the colour generator** (SS-B6, and the colour halves of SS-A9, SS-B7 and SS-C5).
    - `--gamut p3`, `--neutral-hue` and `--anchor-seed` are new, and `NEUTRAL_L[500]` is 0.535.
    - SKILL.md's Phase 1 commands now print the starter's 24 ramp steps.
    - `generate_type_scale.py --fluid-space` prints the fluid spacing.
- **Why the generator moved, not the starter.** The starter's accent holds one hue and has P3 tints, on purpose. Regenerating it with the defaults would have changed ten steps and every contrast claim on them.
- **Tests:** 485. **The plan:** 137 open items, all scheduled (`check_execution_plan.py`).

## Next steps

1. **The next session:** P7 (SB-B4, SS-B2, SS-C9, SS-A17, SS-A18). Check what 3.2.0 already added before building.
2. Then P8 (hygiene, and docs that work in cmd and PowerShell), then R1, the 3.3.0 release.

## Warnings

- **Three status colours are outside even Display P3:** `--warning-700`, `--danger-100` and `--info-100`, found in P6 and not yet an item. The next session's prompt says how to handle them.
- **The generators are held to the starter now.** A change to tokens.css's ramps or type scale must keep SKILL.md's Phase 1 commands reproducing it (`test_numbers.TypeScale`, `ColourRamps`).
- **The contract has 14 byte-identical copies, and the deck's tokens are the starter's, byte for byte.** Edit the master, then copy.
- **The token counter resets** on a user message and on a `<ci-monitor-event>`: keep a running total.
- **Bash heredocs eat backslashes.** Write anything with a backslash through the Write or Edit tool, or a script file.
- **Don't grep `tooling/`**: its `node_modules` makes the search run for minutes.
- **The repository is public.** Commit nothing private.
