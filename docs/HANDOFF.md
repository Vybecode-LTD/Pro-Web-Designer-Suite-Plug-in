# Handoff

**2026-10-04**, after P8 (#34, #35) and R1 (#36): 3.3.0 is released and installed.

**The next session starts from `dev plans/next-session-prompt.md`.** It has the orientation, then Phase 4's first PRs in detail: P9 (one copy of the runtime helpers, and N34) and P10 (a11y_runtime).

## State

- **3.3.0 is released.** #36 merged as `88a4886`, tagged `v3.3.0`; `release.yml` published the zip, 13 `.skill` files and `SHA256SUMS`, the repository's first GitHub release. The local marketplace and the plugin cache hold the released 190 files, byte for byte, and `claude plugin details` reports 3.3.0.
- **Merged this session**, each with CI green on its head, every review thread answered and resolved, and GitHub reporting it clean:
  - **P8 part 1, #34: hygiene.**
    - accessibility.md's testing procedure is `accessibility-testing.md`; accessibility.md is 52,963 bytes (was 60,400 against 60,500).
    - The token contract names `shared/token-contract.md` as the master copy.
    - `test_docs.Manifests` holds the repository's marketplace to the plugin's.
    - The review's header points at the inventory; the vanilla stack's rule 4 names the starter's `.stack` (N33).
  - **P8 part 2, #35: docs that paste into bash, PowerShell and cmd.**
    - The README installs from GitHub, and gives `WDS` in bash, PowerShell and cmd forms, at the installed version's path.
    - `python3` and `/tmp/` are gone from the skills' shell fences.
    - The ESLint config pins `typescript@~6.0` beside typescript-eslint.
  - **R1, #36:** the version, the README's paths and its `.skill` line, and the CHANGELOG heading.
- **The reviews found 6 real issues** in #34 to #36: Codex one on #34, CodeRabbit one on #34, three on #35 (the fence reader, continued installs, `python3` at a line's end), one on #36. Each code fix has a test that fails on the head it reviewed. Two suggestions were declined with reasons in their threads.
- **Tests:** 513. **The plan:** 124 open items, all scheduled (`check_execution_plan.py`).

## Next steps

1. **The next session:** P9 (GT-C13, N34), then P10 (GT-A5, GT-A14, GT-C2, SB-B3).
2. Then the rest of Phase 4 (P11 to P23), and R2, the 3.4.0 release.

## Warnings

- **N34: the release build is byte-identical only with the same zlib.** Windows' Python 3.14 deflates with zlib-ng, the CI's with zlib, so a local build's checksums never match the release's. Compare archives by content (names, CRCs, uncompressed sizes, dates, modes) until P9 gives the builder that comparison.
- **The README's `WDS` paths name the version.** A release PR updates them with `plugin.json`; `test_docs.PasteableCommands` fails until it does.
- **`fail_before.py` swaps the plugin, not the tests.** A fix to test code shows as a control there; show it failing by running the new assertions against the old file (`git show COMMIT:path/to/file`, with the reviewed head and the file's path in place of the two placeholders), as this session did.
- **Still open from earlier:** `--warning-700`, `--danger-100` and `--info-100` fall outside Display P3; `check_roles.py` measures a colour outside sRGB with its channels clipped.
- **Resolve only the threads you answered,** and give a background `check.py` `timeout` 3600000.
- **The token counter resets** on a user message and on a `<ci-monitor-event>`: keep a running total.
- **Bash heredocs eat backslashes** (twice this session), and **don't grep `tooling/`**.
- **The repository is public.** Commit nothing private.
