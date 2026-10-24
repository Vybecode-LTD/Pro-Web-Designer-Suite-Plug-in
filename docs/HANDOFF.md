# Handoff

**2026-10-24: `v4.0.0` is tagged and distributed.** #203 fixed most of `no-fake-countdown`, the owner tagged on its merge with the case at 2 of 3, and the case's reliability is scheduled as P58. The next session starts from `dev plans/next-session-prompt.md` (§3, then §4); `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **`main` at the docs PR's merge**, after `d9125b7` (#203). CI was green on all six cells. No PR should be open.
- **4.0.0 is released.** `v4.0.0` is on `d9125b7`, and `release.yml`'s run 40131424330 built the release (the zip, 13 `.skill` files, `SHA256SUMS`). Its `distribute` job filled `Vybecode-LTD/pro-web-design-suite`: `main` and `v4.0.0` at `28efdaa`.
  - The distribution repository holds `build.py --tree`'s 229 files, byte for byte, with no `tests/`, `evals/` or `tools/`.
  - `claude plugin marketplace add Vybecode-LTD/pro-web-design-suite` and an install into an empty config folder gave 4.0.0, enabled, with the same 229 files.
- **#203** (`no-fake-countdown`):
  - **The skill loads.** landing-page-conversion's description names offers, countdowns and urgency. The router's hint says "pages that convert, offers and urgency" and routes urgency devices near an offer, dark patterns, fake deadlines and fake countdowns (CodeRabbit's finding).
  - **A decline opens with its reason.** The ethics boundary's first rule gives the opening sentence: "I didn't build [what was asked]: [the pattern] deceives because [why]."
  - **The evals:**
    - local, 3 of 3;
    - the outcome suite on the merge (run 40124204320, $5.06), 10 of 11. `no-fake-countdown` got 2 of 3: one run loaded the skill and reported an honest timer as a build.
  - The live check's report, "The evals", has every run and its cost. The session's evals cost $6.81.
- **N52 / P58:** the case passes about five runs in six. Its 3-of-3 bar fails about four times in ten with nothing broken.

## Next steps

1. **The owner submits to Anthropic's directory** at claude.ai/directory/manage, under Submit new, then Plugin bundle, from `Vybecode-LTD/pro-web-design-suite`. The distribution plan's Part A covers it. **Ask before anything is submitted.**
2. **Then the owner chooses** what comes next: P58, or the live check's six follow-ups.

## Open owner decisions

- **P58's bar.** The criterion stays, but should the bar be a rate over more runs?
- **The live check's six follow-ups** (its report's last section): an email theme from `tokens.css`, the hover check on JavaScript tooltips, `contrast-under-overlay`, migrating onto existing token names, the scaffold's default sort, and a send through a real provider.
- **Where issues live:** the distribution repository or here (`supportUrl` points here).
- **`check.py`:** should it select `test_doc_snippets` and stylelint's snippet test when a reference changes?
- **The prompt file:** should `next-session-prompt.md` be split? It is about 125 KB, against the workspace rule of about 4 KB.
- **The owner's own install** is still 3.6.0, from a local marketplace.

## Warnings

- **A deep config folder breaks a marketplace clone on Windows** with "Filename too long" (the 260-character limit). Use a short `CLAUDE_CONFIG_DIR`, such as `%TEMP%\pwds-cfg`.
- **CI's evals run Claude Code 2.1.293; local runs used 2.1.309.** No difference is shown, but CI keeps no transcripts. Use `--keep-temp` locally to read one.
- **landing-page-conversion's SKILL.md is 20,498 of its 20,500 bytes.** Any addition needs a cut.
- **npm walks up to the home folder.** An `npm install` in a folder with no `package.json` installs into `C:\Users\vybec` (memory note `npm-install-walks-up-to-home`).
- **Known flakes:** `test_tbt_stops_at_tti` (Windows), `VitalsUnderCsp` (macOS), `test_interact_at_clicks_while_the_page_hydrates`, the vitals timing tests.
- **Standing:** never grep `tooling/`; the repository is public; `Vybecode-LTD/wds-gate-scratch` is the owner's to delete.
