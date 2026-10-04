# dev plans

The review, plans and reports behind web-design-suite. The plugin itself is in `plugins/web-design-suite`.

**Start with the [execution plan](web-design-suite-execution-plan.md).** It schedules everything left, PR by PR. The [completion plan](web-design-suite-completion-plan.md) says what each item needs.

Every release is also a tagged commit, from `v3.0.0` on. So `git diff v3.1.0 v3.2.0 -- plugins` shows what a patch below holds.

| File | What it is |
|---|---|
| **`web-design-suite-execution-plan.md`** | **The schedule for everything left** (2026-10-02). Every open item and N-item in one of 44 PRs, P0–P43, over phases 3 to 6 and four releases. It also has the decisions the user made on 2026-10-02, the efficiency rules, the lean protocol per PR, and phase 7, an eval-driven method for going past the review. |
| `check_execution_plan.py` | Fails if an open item is missing from the execution plan's schedule or placed twice. Run it after changing the plan or the inventory. |
| `next-session-prompt.md` | **The prompt to start the next session from.** Orientation, then P5 (N3, the rest of SB-C9, N32) in detail, then P6 if the budget allows. Rewrite it at the end of every session. |
| `web-design-suite-completion-plan.md` | **What each item needs.** Phases 3 to 6 (3.3.0 onward) in fourteen workstreams, W1–W14. It covers every open review item and what phase 2 and 3.2.1 found. It also has the rules of the work, the decisions only the user can make, and the release procedure. |
| `web-design-suite-completion-inventory.md` | All 265 review items, each with its status: fixed in a release, or planned in a workstream. It replaces the review's ✔ marks; update a row when its item is fixed. |
| `web-design-suite-bugfix-report.md` | Bug-fix report, 3.0.0 → 3.0.1. The 38 bugs fixed, what was judged not a bug, the commands run with their results, and what could not be tested. |
| `web-design-suite-bughunt/` | Raw findings from the six parallel bug-hunt passes over the plugin, one file per skill group. They are the inputs to the bug-fix report. |
| `web-design-suite-review.md` | Full review of 3.0.1 (2026-09-23) in three parts: (A) 138 issues, 28 of them high severity; (B) 52 gaps; (C) 75 improvements. Also a four-phase roadmap and the method. This is the summary; the detail is in the folder below. Its ✔ marks are out of date, so the inventory holds the real status. |
| `web-design-suite-review/` | The review's detail files, one per area: `crosscut.md` (XC), `studio-systems.md` (SS), `studio-build.md` (SB), `lifecycle.md` (LC), `gates.md` (GT), `persuasion.md` (PS) and `delivery.md` (DL). Also: `claude-code-capabilities.md`, the Claude Code plugin features with doc links; `verification.md`, which claims the lead re-checked and how; and `persuasion-fixtures/`, repro inputs for the PS findings. |
| `web-design-suite-3.1.0-plan.md` | Work plan for phase 1 of the review (3.1.0): 14 items mapped to review IDs, with status. |
| `web-design-suite-3.1.0-report.md` | Phase 1 report, 3.0.1 → 3.1.0 (2026-09-24). Every fix by review ID with its regression test. Also the test runs (151 tests; fail-before on 3.0.1), what was not tested, and what phase 2 picks up. |
| `web-design-suite-3.2.0-plan.md` | Work plan for phase 2 of the review (3.2.0): tests that tie the docs to the code, `check_roles.py`, one shared rule spec, the A7 and A8 doc corrections, an evidence register, leaner SKILL.md files and the 3.1.0 leftovers. It has the status, notes on what was done along the way, and where the work departed from the plan. |
| `web-design-suite-3.2.0-report.md` | Phase 2 report, 3.1.0 → 3.2.0 (2026-09-25). Each plan item mapped to its tests. Also the test runs (296 tests; fail-before on 3.1.0; Linux), the controls and guards, the skills' token costs, what was not tested, and what is still open. |
| `web-design-suite-3.2.1-report.md` | 3.2.1 report (2026-09-25). The move into this repository, and items 1–3 before distribution: no machine paths; the stylelint config and the Tailwind ESLint blocks run through the real tools, and fixed; the Python floor. Also the test runs (317 tests on Python 3.10–3.14 and Linux) and the zip with its SHA-256. |
| `w1-supabase-facts.md` | Facts for phase 3's W1, the Supabase access boundary (DL-B1, DL-B2): Supabase's key types and what each may reach, quoted from its docs on 2026-09-25. |

The reports name files on the maintainer's machine: the installed plugin, the release zips, the `.patch` files, and before 3.2.1 the node_modules the browser tests borrowed. Those paths are records of what was run, not setup instructions.
