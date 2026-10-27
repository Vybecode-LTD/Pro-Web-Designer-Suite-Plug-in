# Handoff

**2026-10-27: three fixes for 4.0.2 merged (P61, P62, P63). 4.0.1 is still in the directory's review.** #208 caches CI's engine packages. #209 adds `sync_email_tokens.py`, which projects a project's `tokens.css` into its `email-tokens.json`, and brings the skill's own email file back in line with the starter. #210 makes the scaffold's default sort read a table's own time and end with the primary key. The next session starts from `dev plans/next-session-prompt.md` (§3, then §4); `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **`main` at `5f09493`** (#210's merge). No PR is open. `main`'s CI passed on #208's merge and on #209's; #210's run was in progress at the end. #207's run on `main` was cancelled by N55's slow install before #208 landed.
- **Released:** `v4.0.1` on `84f4a4f`. The distribution repository's `main` and `v4.0.1` are at `4809e3f`. 4.0.2 is unreleased and held by the owner until the reviewer decides on 4.0.1.
- **On `main` for 4.0.2** (CHANGELOG `4.0.2 — unreleased`):
  - **P60 (#207):** the icon's directory hold.
  - **P61 (#208, N55):** apt keeps the browser engines' `.deb` files in a folder the Actions cache restores and saves, so a slow mirror only costs the packages that changed.
  - **P62 (#209, N56):** email-template-system's `scripts/sync_email_tokens.py`; `references/email-workflow.md` §12 documents it.
    - It keeps an email decision while its `from` still matches `tokens.css`, and projects the entry again when the source has moved.
    - It measures every contrast note again, exits 1 under 4.5:1, and has `--check` for CI.
    - The skill's file had drifted from the starter: `--border-strong` was 2.54:1 where the starter gives 5.15:1, and nine tokens were unaccounted for.
    - SKILL.md is at 20,492 of its 20,500 bytes.
  - **P63 (#210, N57):** with no `sort_order`, `position`, `created_at` or `updated_at`, the proposed sort is the table's first NOT NULL date or timestamp, newest first. It skips arrays, deadlines (`due`, `expir…`, `deadline`, `ends`, `until`) and migration plumbing, matched as whole words. The scaffold's `DefaultSort` and its `.order()` now end with the primary key (CodeRabbit on #210).
- **The directory:** the owner submitted 4.0.1 on 2026-10-26. On 2026-10-27 it was still waiting for the reviewer's decision. Every version is held for a reviewer while the credential findings stand.
- **The execution plan:** `check_execution_plan.py` shows 0 open and 0 scheduled.

## Next steps

1. **The submission.** Ask the owner what the portal shows (Submissions → Pro Web Design Suite). The owner answers the reviewer; ask before every step in the portal.
2. **When the owner says so, release 4.0.2** (P60 to P63):
   - date the CHANGELOG section and set `plugin.json`'s `version` in the release PR;
   - run `evals.yml` (`tag=all`, about $10, the owner's OK) on its merge;
   - then tag.
3. **Or the owner picks:** one of the live check's four remaining follow-ups (each gets an N-item and a P-row first), or Part B of the distribution plan.

## Open owner decisions

- **The live check's four remaining follow-ups** (the last section of `dev plans/web-design-suite-4.0.0-live-check.md`):
  - the hover check on a JavaScript tooltip;
  - `contrast-under-overlay` on webawesome.com (21 to 147 findings a page);
  - migrating onto a codebase's own token names;
  - sending email through a real provider, which needs the owner's key.
- **Part B** of `web-design-suite-distribution-and-promotion.md`: topics and a social preview for the distribution repository, then the listings.
- **Where issues live:** the distribution repository or this one. Also whether to add a terms-of-service link.
- **`check.py`:** should it run `test_doc_snippets` and stylelint's snippet test when a reference changes?
- **`next-session-prompt.md`:** should it be split? It is about 125 KB against the workspace's 4 KB rule.
- **The owner's own install** is still 3.6.0.

## Warnings

- **This session went over its 750K-token budget.** It filled a context window and was compacted once. Report `get_usage` after every PR, and write the handoff while there is room.
- **`check.py` takes about 16 minutes** when a content-model script changes (the scaffold tests build apps). Run it in the background.
- **A release's upload can 404** right after the release is created. Rerun the failed job (`gh run rerun RUN --failed`).
- **Until #208's cache is warm**, a first run on a new runner image still downloads every engine package.
- **Two SKILL.md files are near the 20,500-byte cap:** landing-page-conversion at 20,498 and email-template-system at 20,492. An addition needs a cut.
- **Known flakes:**
  - `test_runtime_urls.EachPageHasItsTypesBudget` (Windows);
  - `test_tbt_stops_at_tti` (Windows);
  - `VitalsUnderCsp` (macOS);
  - `test_interact_at_clicks_while_the_page_hydrates`;
  - the vitals timing tests.
- **Standing:** never grep `tooling/`; the repository is public; `Vybecode-LTD/wds-gate-scratch` is the owner's to delete.
