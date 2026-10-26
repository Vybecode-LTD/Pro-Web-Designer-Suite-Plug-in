# Handoff

**2026-10-26: 4.0.1 is released and submitted to Anthropic's directory, and P60 is on `main` for 4.0.2.** 4.0.1 adds the listing icon (#205), the owner submitted it from the portal, P58 closed with no change, and #207 cleared the icon's directory hold for the next release. The next session starts from `dev plans/next-session-prompt.md` (§3, then §4); `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **`main` at #207's merge** (P60), after `54fecc8` (#206, the docs, squash-merged so a commit holding the owner's email never reached `main`). No PR should be open.
- **4.0.1 is released.** `v4.0.1` is on `84f4a4f`. `release.yml`'s run 40330031855 failed once, on a 404 from GitHub's upload host for the first asset (gh removed the half-made release), and passed on a rerun of the failed job. The distribution repository's `main` and `v4.0.1` are at `4809e3f`: 230 files, byte for byte `build.py --tree` at `v4.0.1`, and `claude plugin validate --strict` reports nothing.
- **#205 (P59, N53):** the listing icon, a token grid in VybeCode's colours (`tooling/release/icon.svg`; the owner chose it of two drafts). The directory reads a plugin's icon once, at its first save in the portal. `build.py` refuses an icon it would not take (a whole PNG with valid CRCs, square, 512 to 2048 px, under 2,000,000 bytes) and holds an image path quoted as code. CodeRabbit's five findings were all fixed.
- **The evals on `84f4a4f`** (run 40322921492, `tag=all`): routing 23 of 23, outcome 11 of 11, $9.55.
- **The directory:** submitted 2026-10-26 by the owner, from their own claude.ai organization. It tracks `main` with a **scheduled check only** and auto-publish on. Validation passed with 13 warnings and 7 policy holds: six credential findings (`FIGMA_TOKEN`, `CRUX_API_KEY`, a Supabase example, two scanner misreads) and N54's image hold. **At 2026-10-26's end: In review, waiting for a reviewer** (the security scan passed; the icon is waiting for review too); the portal says there is nothing to do.
- **#207 (P60, N54), unreleased (4.0.2):** the icon renamed to a stem no shipped text uses, named by plugin.json's `icon`; `build.py` reads it from there and holds a bundled image whose path or whole-word stem appears in any shipped text but plugin.json and image links. That is a superset: 13 shipped scripts and stylesheets say "icon" and the directory flagged none, so its own rule is unknown.
- **P58 / N52 closed, no change** (the owner): 6 of 6 locally with transcripts ($0.53), 14 of 15 runs since #203.
- The session's evals cost $10.08.

## Next steps

1. **The submission.** Its page in the portal (claude.ai/directory/manage → Submissions) shows the scan and the reviewer's decision; questions go to the contact email. The owner answers them.
2. **Then the owner chooses:** releasing 4.0.2 (P60 alone; an `evals.yml` run gates the tag), one of the live check's six follow-ups (each gets an N-item and a P-row first), or Part B of the distribution plan (promotion). Nothing is open in the plan (0 open, 0 scheduled).
3. **After any later release:** the directory checks `main` about every 6 hours; **Check for new commits** on the plugin's page scans at once. Every version is held for a reviewer while the credential findings stand.

## Open owner decisions

- **The live check's six follow-ups** (its report's last section): an email theme from `tokens.css`, the hover check on JavaScript tooltips, `contrast-under-overlay`, migrating onto existing token names, the scaffold's default sort, and a send through a real provider.
- **Part B** of `web-design-suite-distribution-and-promotion.md`: the distribution repository has no topics or social preview yet.
- **Where issues live:** the distribution repository or here (`supportUrl` points here). The listing has no terms-of-service link (optional).
- **`check.py`:** should it select `test_doc_snippets` and stylelint's snippet test when a reference changes?
- **The prompt file:** should `next-session-prompt.md` be split? It is about 125 KB, against the workspace rule of about 4 KB.
- **The owner's own install** is still 3.6.0, from a local marketplace.

## Warnings

- **The portal saves a draft at the first Validate** ("Draft saved in this tab"), and the icon is read then. Changing the icon later does not change the listing's.
- **A release's upload can 404** right after the release is created. Rerun the failed job (`gh run rerun RUN --failed`); nothing is left behind.
- **A new flake:** `test_runtime_urls.EachPageHasItsTypesBudget` on Windows (the strict page recorded no LCP), on #204's merge; the rerun passed.
- **The bundled CLI** isn't under `%APPDATA%\Claude\claude-code` from Git Bash any more; the 2.1.309 CLI in `222f4831-…`'s scratchpad (`cc/`) and `unset.txt` work. CI's evals run 2.1.293.
- **landing-page-conversion's SKILL.md is 20,498 of its 20,500 bytes.** Any addition needs a cut.
- **npm walks up to the home folder**, and a deep config folder breaks a marketplace clone on Windows (memory notes).
- **Known flakes:** `test_tbt_stops_at_tti` (Windows), `VitalsUnderCsp` (macOS), `test_interact_at_clicks_while_the_page_hydrates`, the vitals timing tests.
- **Standing:** never grep `tooling/`; the repository is public; `Vybecode-LTD/wds-gate-scratch` is the owner's to delete.
