# Handoff

**2026-10-04**, after P6 (#28, #29), P7 (#31, #32) and their docs PRs were merged into `main`.

**The next session starts from `dev plans/next-session-prompt.md`.** It has the orientation, then P8 in detail (hygiene, and docs that work in cmd and PowerShell), then R1, the 3.3.0 release, if the budget allows.

## State

- **3.2.1 is released** (`v3.2.1`, `63932cf`) and installed. 3.3.0 is in progress on `main`, unreleased.
- **Merged this session**, each with CI green on its head, every review thread answered and resolved, and GitHub reporting it clean:
  - **P6, #28 and #29: the generators reproduce the starter.**
    - The type scale's default is `--preset studio`, and a step under 11px is refused.
    - typography.md has the 2.5× fluid-type bound.
    - The colour generator has `--gamut p3`, `--neutral-hue` and `--anchor-seed`.
  - **P7 part 1, #31: the contract's missing roles.**
    - The roles: `--fg-on-success/-warning/-danger`, `--border-invalid` and `--motion-travel-xs/-sm/-md`.
    - They are in every consumer, and `check_roles.py` holds them (100 pairs).
    - Invalid fields no longer look focused.
  - **P7 part 2, #32: the starter's files and comments.**
    - `utilities.css`, `overrides.css` and `theme-init.js` ship.
    - The contradicted comments are fixed.
    - reset.css drops `html:has(:target)` smooth scrolling and uses `svh`.
- **The reviews found 13 real issues across #28 to #32.** Each code fix has a test that fails on the head it reviewed.
- **Tests:** 498. **The plan:** 132 open items, all scheduled (`check_execution_plan.py`).

## Next steps

1. **The next session:** P8 (XC-A2, XC-A5, XC-B5, XC-C9, N4, N7, N8, N9, N10).
2. Then R1, the 3.3.0 release, then Phase 4 (3.4.0).

## Warnings

- **accessibility.md is 60,400 bytes against a 60,500 limit.** N4, in P8, splits it. Until then, any addition there needs a trim.
- **Two findings are not yet items:**
  - `--warning-700`, `--danger-100` and `--info-100` fall outside Display P3;
  - stack-vanilla-css.md prefixes layout primitives `.l-stack`, where the starter's are `.stack`.
- **The gate still clips.** `check_roles.py` measures a colour outside sRGB with its channels clipped, while the ramp report takes the worse of clipping and chroma reduction.
- **`check_roles.py` now requires the new roles.** A `tokens.css` without them exits 2 (the CHANGELOG's Upgrading section says so).
- **Resolve only the threads you answered.** A resolve-all loop on #31 closed two unread findings.
- **The full local suite can pass 20 minutes** when other projects load the machine. Give a background `check.py` `timeout` 3600000.
- **The token counter resets** on a user message and on a `<ci-monitor-event>`: keep a running total.
- **Bash heredocs eat backslashes**, and **don't grep `tooling/`**.
- **The repository is public.** Commit nothing private.
