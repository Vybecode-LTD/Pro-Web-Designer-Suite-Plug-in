# Handoff

**2026-10-22, second session: P41 part 3 is done** (DL-B4, #198), so Phase 6b is complete and no item is open (`check_execution_plan.py`: 0 open, 0 scheduled). **R4, the 4.0.0 release, is the next session's whole job.** The owner then asked for R4 here and chose the full live check in a fresh session: this session ran only **R4's free checks**, which found the rename's upgrade command wrong (**#200**, `dev plans/web-design-suite-4.0.0-live-check.md`).

**The next session starts from `dev plans/next-session-prompt.md`** (§3, then §4). `dev plans/next-session-opening-prompt.md` is the message to paste in.

## 2026-10-19: the rename and the distribution repository (another session)

A second session, beside P35's, did the owner's distribution plan (`dev plans/web-design-suite-distribution-and-promotion.md`):
- **#180, merged as `b2648f8`.** The plugin is now **Pro Web Design Suite, `pro-web-design-suite`**, in `plugins/pro-web-design-suite`. Both marketplace files carry `renames`. Four formats keep the old id, because users' projects hold them (CLAUDE.md's Gotchas). `build.py` and `fail_before.py` read a pre-rename `--rev` such as `v3.6.0`.
- **#181, merged as `24774d0`.** Releases ship without `tests/`, `evals/` and `tools/`. `build.py --tree` writes the **distribution repository**'s contents, and the build refuses what Anthropic's directory blocks. `release.yml`'s `distribute` job pushes each release to `Vybecode-LTD/pro-web-design-suite`: forward only, atomic, queued, never an older tag over a newer one.
- **#182.** The README has *Try it*, *Where it works* and *What it runs, sends and stores*; `SECURITY.md`; `plugin.json`'s `documentationUrl`, `supportUrl` and `privacyPolicyUrl`.

**The owner's three steps before R4 are done** (verified 2026-10-21): the distribution repository exists, public and empty; its write deploy key (id 166961999) pairs with the secret `DIST_DEPLOY_KEY`; private vulnerability reporting is on. R4's `distribute` job is the key's first real push; if it fails, the GitHub release still happens. **After R4:** check the distribution repository holds 4.0.0 at its root (the files `build.py --tree` writes: 229 at `3184a09`), that the Claude Code command `/plugin marketplace add Vybecode-LTD/pro-web-design-suite` installs it, and the owner validates and submits it at claude.ai/directory/manage.

## State

- **`main` at `7ed9937`** (#199, the docs), with #200 (the rename's upgrade command and R4's free checks) on top. 3.6.0 is the latest release; 4.0.0 is unreleased, with Phases 6a, 6b and 6c all in it.
- **#198, P41 part 3 (DL-B4)**, merged as `3184a09`. `email-template-system/scripts/export_email_theme.py` writes the email tokens as an `<mjml><mj-head>` to `mj-include` (`--format mjml`) or a React Email theme module with `withMso()` (`--format react-email`). The starters `assets/templates/mjml/` and `react-email/` compile with MJML 5.4.1 and React Email 6.11.3 to HTML that passes `lint_email.py --strict`, and a browser test reads their dark mode, phone sizes and gutter. email-workflow.md §11; Maizzle routed away. The router hears React Email, Maizzle and `mj-` tags. Three gate fixes came out of it: `lint_email` measured a hidden preheader's contrast and read a `font-size:0` column wrapper as text, and `audit_design` failed a React Email template (it now leaves one, and an `@generated` file, to the email lint).
- **`tooling/main`** gains `mjml` 5.4.1, `react` and `react-dom` 19.3.1, and `react-email` 6.11.3 (+259 packages, test-only; the owner's OK, 2026-10-22). `@react-email/components` and its per-component packages are deprecated on npm, so its replacement `react-email` is the one pinned.
- **Reviews on #198:** Codex 2 (the gutter read the surface class; a commented-out import skipped the audit) and CodeRabbit 3 (one the same gutter finding, two declined with reasons it then withdrew). Each fix fails on `9e7e61f`, the head reviewed.
- **At the end:** 0 open items; about 1,590 tests.

## Next steps

1. **R4, the 4.0.0 release**, in the order `dev plans/next-session-prompt.md` §4 gives: a live check of what changed (the owner's OK and an estimate first), the release PR, the evals on its merge (the owner's OK, about $11), the tag, then the distribution checks above.

## Open owner decisions

- **Decided 2026-10-22:** the full live check (about $8 to $10, in a fresh session; show the owner the session list and the cap once), and the evals on the release PR's merge (about $11).
- Whether issues live in the distribution repository or here; `supportUrl` points here for now.
- Whether to start the proposed follow-up: `check.py` should select `test_doc_snippets` and stylelint's snippet test when a reference changes.
- `dev plans/next-session-prompt.md` is about 124 KB; the workspace's rule for a starting prompt is about 4 KB. Whether to split it: a short prompt that points at a reference file holding §0's lessons and §2's facts.

## Warnings

- **Never edit a file the suite reads while `check.py` runs.** This session did once (answering a review), stopped the run with `TaskStop` and ran it again.
- **Bash heredocs eat backslashes**, three more times this session (`\n` in a test string, `\b` in a router regex). Write any text with a backslash with the Write or Edit tool.
- **MJML 5 ignores `mj-include` unless it is allowed** (`--config.allowIncludes true`, or `ignoreIncludes: false` in Node); the CLI warns, `mjml2html` says nothing. `mjml2html` returns a promise.
- **React Email 6:** `Preview` writes a `<title>` unless `useTitleTag={false}`; a `Section`'s padding is on its cell; React renders no comment, hence `withMso()`.
- **Keep each shipped file under 262,144 bytes** (`test_release_build`). CHANGELOG.md is about 126 KB.
- **This Windows machine refuses Playwright's unsigned Firefox build.** Firefox's tests skip locally and run on CI's Linux cells. Never touch the system security setting.
- **Known flakes:** `test_tbt_stops_at_tti` (Windows), `VitalsUnderCsp` (macOS), `test_interact_at_clicks_while_the_page_hydrates`, the vitals timing tests. Check a failure touches nothing the PR changed before rerunning.
- **Still open from earlier:** `perf_audit.py` and an unbundled `@import` chain; three tokens outside Display P3; the default scaffold's `focus-rule-invisible` warnings.
- **Standing:** don't grep `tooling/`; the repository is public; `Vybecode-LTD/wds-gate-scratch` is the owner's to delete.
