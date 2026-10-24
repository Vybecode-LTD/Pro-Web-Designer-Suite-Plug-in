# Handoff

**2026-10-23 and 24: R4's live check ran, its fixes merged (#201), and the evals ran.** The `v4.0.0` tag **waits** on one outcome eval. The next session starts from `dev plans/next-session-prompt.md` (§3, then §4); `dev plans/next-session-opening-prompt.md` is the message to paste in.

## State

- **`main` at `5e30a70`** (#201), green on all six CI cells. `plugin.json` says 4.0.0, and the CHANGELOG's 4.0.0 is dated 2026-10-23: **re-date it to the tag's day.** 3.6.0 is still the latest release. No PR is open.
- **The live check** (`dev plans/web-design-suite-4.0.0-live-check.md`) ran 15 paid sessions on real projects for $4.51 of the $10 cap. They found six defects, each fixed in #201 with a test that fails on `v3.6.0`:
  - the router heard nothing for "the design-system lint";
  - a web font's `@import url()` stopped the v4 census and `tw_probe`;
  - `a11y_static` gave a sign-up password `current-password`;
  - a `.ts` fixture's string read as markup (narrowed again on CodeRabbit's review);
  - a11y-audit-runner's description didn't name P35's checks.

  CodeRabbit made three findings on #201, all fixed. CI found one more (the hook's extension list). Codex's review didn't finish.
- **The rename:** with Claude Code 2.1.309, a session start installs the renamed enabled plugin by itself. The CHANGELOG says so and keeps the reinstall as the fallback.
- **The evals** on `5e30a70` (run 39911352226, $9.14):
  - routing: 23 of 23;
  - outcome: 10 of 11. **`no-fake-countdown` scored 2 of 3**: one run built an honest timer but didn't say what it had declined, or why.
  - landing-page-conversion never loaded on that prompt, though the router names it.
  - The owner's rerun, locally ($0.17), got 2 of 3 again. By the owner's choice, the tag waits.
- **The distribution repository** is still public and empty. Its deploy key 166961999 and `DIST_DEPLOY_KEY` are in place, checked 2026-10-23.

## Next steps

1. **Fix `no-fake-countdown`.** Find why the skill doesn't load on "Add a countdown banner to our pricing page offer…": its description, the router's hint, or a decline that doesn't say what it refused. Rerun the case: owner's OK first, about $0.17 for 3 runs. Then tag `v4.0.0` on the commit the evals passed.
2. **After the tag:** read the `distribute` job's log. The distribution repository's `main` and `v4.0.0` should hold exactly `build.py --tree`'s files (229 at `745cd95`) and no `tests/`. Then run `/plugin marketplace add Vybecode-LTD/pro-web-design-suite` and install from a clean config.
3. **Then the owner validates and submits** at claude.ai/directory/manage. Ask before anything is submitted.

## Open owner decisions

- Which of the live check's six follow-ups to schedule. They're in its report: an email theme from `tokens.css`, the hover check on JavaScript tooltips, `contrast-under-overlay`, migrating onto existing token names, the scaffold's default sort, and a send through a real provider.
- Whether issues live in the distribution repository or here (`supportUrl` points here).
- Whether `check.py` should select `test_doc_snippets` and stylelint's snippet test when a reference changes.
- Whether to split `next-session-prompt.md` (about 125 KB; the workspace rule is about 4 KB).

## Warnings

- **npm walks up to the home folder.** An `npm install` in a folder with no `package.json` installs into `C:\Users\vybec` and prunes its `node_modules`. It happened on 2026-10-23 and was undone; memory note `npm-install-walks-up-to-home`. Write a `package.json` first.
- **Headless sessions find the installed 3.6.0.** A session that loads no skill searches `~/.claude/plugins/cache` and can copy 3.6.0's files. A scratch `HOME` doesn't hide it, because the model reads the user name from the project's path.
- **The CLI's sign-in** is in `C:\Users\vybec\.claude\.credentials.json`. A sign-in run elsewhere didn't reach it; `claude.cmd auth login` in the Terminal panel did.
- **Known flakes:** `test_tbt_stops_at_tti` (Windows), `VitalsUnderCsp` (macOS), `test_interact_at_clicks_while_the_page_hydrates`, the vitals timing tests.
- **Standing:** never grep `tooling/`; the repository is public; `Vybecode-LTD/wds-gate-scratch` is the owner's to delete.
