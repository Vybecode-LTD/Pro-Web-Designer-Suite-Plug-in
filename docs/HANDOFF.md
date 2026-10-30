# Handoff

**2026-10-30 (the third session of 2026-10-29): stage 2 closed. P75 (#232) and P76 (#234) are merged.**
- **P75, #232, the runtime checks:** CodeRabbit's round on `d8a2414`: a textarea and a list box measured once, a control under an ancestor at `opacity: 0` skipped, reflow at a phone width run in a desktop context (a page with no viewport meta is 980 px wide on a phone, so 320 was not 320 CSS px), the opacity message's comma, `scripts.md`'s matrix exception and `mobile` field. **Declined, with the source:** "Firefox refuses `isMobile`": Playwright 1.64.1's `ffBrowser.ts` sends it in `Browser.setDefaultViewport`; the Firefox engine test now also runs at 390x844, and CI's Linux leg (engines required) passed it.
- **P76, #234, vitals, the matrix and the critique capture:** an `--interact-at` run's LCP is marked as stopping at the click (`lcpBeforeClick`), with one run without the click beside it (`unclicked`), neither held to `lcp_ms`; the page's clock read first in `clickDuringLoad`; notes for a metric some runs lacked and for a `--urls` page with no LCP; `--dpr` above 0 in three scripts; the critique scrolls the page through before each capture; `finish()` in `browser_common.mjs` drains stdout and stderr before exit; every report names its browser build (`browserVersion`); JS-B-17's dead code gone, with a real-tool ESLint test of the five scripts and `shared/`. **Review (Codex, CodeRabbit on `7883bfd`):** the `--urls` report marks a pre-click LCP; the `lcp_ms` exemption needs a run that clicked; the scroll covers the whole page, up to 15 s; the failure paths drain too; the a11y text report names the build.

## State

- **`main` = this PR's merge**, on #234's merge `1bc2481` and #232's `4453fa6`.
- **Open:** none.
- **Released:** `v4.0.1`; P60 to P76 on `main` for 4.1.0.
- **Tests:** 1,804 (`unittest` discovery).
- **The plans:** `check_execution_plan.py` 13 open, 13 scheduled (N71 to N83). Next free ids: **N84, P90**; the next PR is #236 (this one is #235).

## Next steps

1. **Stage 3, P77 to P79** (the runbook's §4, in order): P77 `a11y_static.py` (N71), P78 `audit_design.py` and the studio (N72), P79 design-token-migration (N73).
2. **P78 also takes** two names ESLint's `no-unused-vars` flags outside P76's files: `web-design-studio/scripts/tw_probe.mjs:183` (`m`) and the starter's `assets/starter/theme-init.js:14` (`catch (e)`; the starter is quoted in the references, so `sync_snippets.py` follows). Then widen `test_real_tools.TheBrowserScriptsLeaveNothingUnused` to every `.mjs` and `.js` the plugin ships.

## Open owner steps

- **The four GitHub settings** (the runbook's §3): not done, as of 2026-10-30.
- **Delete `Vybecode-LTD/wds-gate-scratch`** (Q12).
- **Auto-fix on a PR another session opened** can only be turned on by the owner; for #232 this session read its CI by hand at break points.

## Warnings

- **A `shared/` change makes `check.py` run most of the suite**: 1,487 tests in 27 minutes here. After it passes, `check.py --base SHA` runs only what changed since.
- **SKILL.md budgets:** perf-budget-gate 20,496 and design-critique-gate 20,498 of 20,500 bytes. `docs/FACTS.md`'s byte table must match (`test_docs.TheAuditsDocsLows`).
- **The Bash heredoc unescapes `\\` and trips on quotes:** write patch scripts with the Write tool and run them from a file.
- **CodeRabbit's free tier** skipped #234 at first ("review limit reached"); `@coderabbitai review` once the limit has reset (asked too early, it declines).
- **A reviewer's claim about a library** (Firefox and `isMobile` here): read the pinned copy's code, one named file in `tooling/`, before fixing.
- **`scaffold_ui.py` is 1,239 bytes under the directory's 262,144-byte hold** (unchanged).
- **Budget:** about 560K of the 750K cap at the close (the app's counter).
