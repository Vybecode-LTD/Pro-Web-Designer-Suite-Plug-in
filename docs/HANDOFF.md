# Handoff

**2026-10-07**, after P45 (#73), R2 (#74) and this docs PR. **3.4.0 is released**, which completes Phase 4. Phase 5 (3.5.0, a full Claude Code plugin) is next.

**The next session starts from `dev plans/next-session-prompt.md`**: orientation, then P24 and P25 in detail. `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **Merged this session:** #73 and #74, each with CI green on its head, every thread answered and resolved, CodeRabbit finished and GitHub clean. This handoff PR follows. No other PR is open.
- **What they did:**
  - **#73, P45: Law 6 in stylelint and the ESLint config (N35).**
    - The spec's `tiers` lists reach both configs through `sync_rules.py`.
    - stylelint's new `design/tier1-primitive` refuses a primitive that has a role in the `components` layer (by the layer's full name), and anywhere in a component file. Token and theme files are exempt, including those in a component folder.
    - ESLint's `TIER1_SHORTHAND` is built from the spec. The null-outs pass, and a type hint (`text-(length:--text-lg)`) no longer hides a primitive. An inline socket filled from a primitive is refused.
    - The audit shares one `tier1_advice()`, and reads the layer by its full name too.
  - **#74, R2: release 3.4.0.** The version, the README's `WDS` paths, the CHANGELOG heading and summary.
    - Merged as `5990347` and tagged `v3.4.0`. `release.yml` published the zip, the 13 `.skill` files and `SHA256SUMS` (15 assets).
    - Installed here: `claude plugin update` took the plugin from 3.3.0 to 3.4.0. **Restart Claude Code to load it.**
- **The reviews found 2 real issues on #73**, each fixed with a test that fails on the head it reviewed:
  - Codex: a token file in a component folder got Law 6 back from the later component override, which now comes first.
  - CodeRabbit: `@layer base.components` was read as the components layer.

  #74 had no findings.
- **Phase 5's first step:** `claude-code-capabilities.md` §5 holds the 2026-10-07 re-check against the changelog (2.1.293) and the manifest reference:
  - Mods (2.1.287) are a new kind of plugin hook, and P25 should weigh them.
  - `bin/` keeps a plugin out of claude.ai and Cowork installs, which bears on P28.
  - Several anchors moved.
- **The plan:** 54 open items, 54 scheduled (`check_execution_plan.py`). Tests: 755.

## Next steps

1. **P24**, the project contract: `.design-suite.json` read by the scripts, and a `contract.json` that `extract_system` generates. It is L, so do it in two parts. The prompt has the scope.
2. **P25**, the hooks: the opt-in design gate, the generated-file block, `diff_system` after a tokens edit, and the prompt router.
3. Then P26 to P30, and R3 (3.5.0).

## Warnings

- **The desktop app's CLI is 2.1.288**, in the build folder `36aa8c97bf86`. CLAUDE.md's Commands now says so.
- **SKILL.md budgets:**
  - client-presentation-builder: 20,498 bytes of 20,500
  - landing-page-conversion: 20,497
  - email-template-system: 20,475
- **`browser_common.mjs` has five copies.** Change `shared/` and copy it over all five. A Python reader for `.design-suite.json` would follow the same pattern.
- **The token counter resets at each app event.** It reset about six times this session; keep a running total. This session used about 420 thousand tokens: two PRs, one review round, the release, the re-check and these docs.
- **Codex reviewed only the head each PR opened with** (`accb8d6` on #73), not the fix pushed after it.
- **Bash heredocs eat backslashes.** Three times this session, a `\\n` in a Python heredoc became a newline, and once a Windows path broke the script. Write such scripts with the Write tool.
- **Still open from earlier:**
  - `--warning-700`, `--danger-100` and `--info-100` fall outside Display P3.
  - `check_roles.py` measures a colour outside sRGB with its channels clipped.
  - The worked examples are tests (`TheWorkedRun`, `TheWorkedRelease`).
  - A local build never matches the release's checksums.
  - Don't grep `tooling/`.
  - The repository is public.
