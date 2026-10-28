# TEST: the test suite, CI and the local runner

Audited 2026-10-28 at main 8441ff0. Commands run: `git rev-parse --short HEAD`; `python -B -m unittest test_agents test_evidence test_pointers` (21 tests, OK, 30 s); AST passes over `tests/*.py` (test counts, duplicate names, no-assert tests, class state set in tests, skip conditions); `python -B` calls of `tools/check.py`'s `affected()` against 60 sample paths; a static check of every test id `CHANGELOG.md` names against `tests/`; `git status --ignored`; greps listed inline. No whole-suite run, no `npm ci`, nothing under `tooling/` read but `tooling/README.md`.

## Summary

19 findings: 0 critical, 3 high, 8 medium, 8 low. By class: test-gap 2, weak-test 3, flake 5, infra 5, hygiene 2, stale-evidence 2.

1. About 200 of the 1,644 tests need a Chromium, and on every CI leg they turn into silent skips when none starts: only Firefox and WebKit (Linux) and the Pydantic test are made to fail instead (`WDS_REQUIRE_ENGINES`, `WDS_REQUIRE_PYDANTIC`); nothing requires a Chromium, so a broken headless-shell install or a runner image without Chrome would leave CI green with the browser gates untested (TEST-1).
2. `tools/check.py` selects tests by substring of the changed file's stem or its skill folder, so an edit to four of the six agents, to `new_system.py` or `release_check.py` selects no test at all, and a reference edit in 11 of the 13 skills runs neither `test_doc_snippets` nor the stylelint/ESLint snippet tests (TEST-2, TEST-3). CI's full run is the only net.
3. `tools/fail_before.py` counts an error as a failure and prints no reason, so a test that cannot even run on the old tree (a script the tag does not have, an import error) reads as "fixed" in the table, which is the evidence the CHANGELOG cites (TEST-4). Every one of the 94 test ids the CHANGELOG names exists.

## Findings

### TEST-1 · high · infra
- **Where:** `.github/workflows/ci.yml:100-105`; `plugins/pro-web-design-suite/tests/test_runtime_engines.py:49-56`; `tests/test_browser_runtime.py:70-71` (and the same `skipTest("no usable browser…")` in 12 helper methods across the browser modules).
- **What:** 166 tests sit in classes gated on a Playwright toolchain, plus 30 in `test_runtime_wcag_checks`' subclasses: about 200 in all. Each runs a script and, when it exits 2 saying no browser started, calls `self.skipTest`. Only `EachEngine.runtime` turns that skip into a failure, and only when `WDS_REQUIRE_ENGINES` is set, which CI sets on Linux alone; `grep -n WDS_REQUIRE tests/*.py` finds no other guard.
- **Evidence:** `ci.yml:103`: `WDS_REQUIRE_ENGINES: ${{ runner.os == 'Linux' && '1' || '' }}`; `test_runtime_engines.py:52-56`: `if os.environ.get("WDS_REQUIRE_ENGINES"): self.fail(...)` else `self.skipTest(...)`; `test_browser_runtime.py:70`: `if proc.returncode == 2 and b"browser" in proc.stderr.lower(): self.skipTest(...)`. On Windows and macOS the Chromium comes from the runner image's Chrome or Edge (`shared/browser_common.mjs:186-201`), not from Playwright: `ci.yml:85-88` installs browsers on Linux only.
- **Effect:** If `npx playwright install --only-shell chromium` stops working on Linux, or a runner image drops Chrome, every browser gate (a11y runtime, vitals, the matrix, the critique snapshots, the email render) goes untested and the run still prints OK (skipped=N). Nobody reads N.
- **Fix:** Add a `WDS_REQUIRE_BROWSER` that every "no usable browser" skip consults (one helper in `wds_support.py`, as `EachEngine.runtime` does), and set it on all three legs; or assert in CI that the skipped count stays under a ceiling.
- **Confidence:** confirmed

### TEST-2 · high · test-gap
- **Where:** `plugins/pro-web-design-suite/tools/check.py:58-62`; `tests/test_agents.py:33,38,55,70,83` (`AGENTS.glob("*.md")`).
- **What:** For a file outside `skills/`, `affected()` makes one key, the file name or the script's stem, and selects the test modules whose source text contains it. `test_agents.py` globs the agents folder, so its source names only `design-critic` (line 105's test). Likewise `test_commands.py` runs `new_system.py` and `release_check.py` through the command lines in each `SKILL.md` (`${CLAUDE_SKILL_DIR}/scripts/…`, `test_commands.py:495-499`), so the test's own source never names those stems.
- **Evidence:** `check.affected([path], sources)` with the real test sources: `agents/a11y-auditor.md -> []`, `agents/codemod-batch-reviewer.md -> []`, `agents/design-auditor.md -> []`, `agents/gate-runner.md -> []`, `agents/supabase-security-reviewer.md -> ['test_pointers']`, `agents/design-critic.md -> ['test_agents']`; `workflow-commands/new-system/scripts/new_system.py -> []`; `workflow-commands/release-check/scripts/release_check.py -> []`.
- **Effect:** An agent's frontmatter can break (a field a plugin agent ignores, a tool that writes, a preloaded skill that does not exist), or `/new-system` and `/release-check` can stop running, and `check.py` reports "the affected tests (none)" and passes. CI catches it a push later, after the branch is pushed once "green".
- **Fix:** In `affected()`, map `agents/*` to `test_agents` (and `test_pointers`), and `workflow-commands/<cmd>/…` to `test_commands` (plus `test_deck` for `deck`), by folder rather than by stem; `test_tools.CheckChoosesTheTests` should get a case for each.
- **Confidence:** confirmed

### TEST-3 · medium · test-gap
- **Where:** `plugins/pro-web-design-suite/tools/check.py:60-61`; `tests/test_doc_snippets.py:168-171`; `tests/test_real_tools.py:261,688`.
- **What:** A reference under `skills/<skill>/references/` adds the skill folder name as a key, so every module whose source mentions the skill runs (9 to 41 modules, over-inclusive). But `test_doc_snippets`, which audits every CSS/TSX/JSX block in all thirteen skills' markdown, is selected only when the skill's name appears in its source, and the two snippet tests in `test_real_tools` (stylelint on the references' CSS, ESLint on their TSX) only for `web-design-studio`. This answers the handoff's open question.
- **Evidence:** one reference per skill through `affected()`: `a11y-audit-runner … -> 26 modules; []`, `client-presentation-builder -> 11; []`, `component-state-matrix -> 13; []`, `content-model-to-ui -> 14; []`, `design-critique-gate -> 15; []`, `design-system-docs -> 16; ['test_rules_spec']`, `design-system-versioning -> 13; []`, `design-token-migration -> 18; ['test_rules_spec']`, `email-template-system -> 19; ['test_doc_snippets']`, `figma-variables-sync -> 12; []`, `landing-page-conversion -> 9; []`, `perf-budget-gate -> 18; []`, `web-design-studio -> 41; ['test_doc_snippets', 'test_real_tools', 'test_rules_spec']` (the list shows which of the three snippet modules were picked).
- **Effect:** A CSS block pasted into eleven skills' references can fail the design audit or stylelint and `check.py` will not run the test that says so; `sync_snippets --check` (run every time) covers only code quoted from the starter.
- **Fix:** In `affected()`, any `.md` under `skills/*/references/` or a `SKILL.md` adds `test_doc_snippets` and `test_real_tools` (or the two snippet classes) outright.
- **Confidence:** confirmed

### TEST-4 · high · infra
- **Where:** `plugins/pro-web-design-suite/tools/fail_before.py:72-79,149-156,204-209`.
- **What:** The runner counts `addFailure` and `addError` alike (`failed += 1`) and records no message. The table prints `FAIL (n)` / `ok` / `skipped` and the verdict. A test that errors on the old tree because the script it runs did not exist at the tag (`FileNotFoundError` from `run_py`, or an `ImportError` in a `load_script`) is `FAIL (1)` before and `fixed` now, indistinguishable from an assertion that failed for the fix's reason. The docstring's "A failing test shows its failures and errors" (line 23) is not what the output does.
- **Evidence:** lines 77-79: `def addError(self, test, err): if isinstance(test, unittest.TestCase): self.row(test)["failed"] += 1; return`; line 153: `return f"FAIL ({row['failed']})"`; `test_tools.FailBefore.test_each_verdict` (lines 128-146) asserts only the `(before, now, verdict)` triples. The CHANGELOG cites this table as the fail-before evidence for every fix (nine "Regression test" entries, e.g. line 39-45).
- **Effect:** A regression test added with a new script, or a test whose fixture the old tree lacks, "fails before" for the wrong reason and proves nothing about the bug; the reviewer cannot tell from the table.
- **Fix:** Keep failure and error counts apart (`errors` column), store the first line of each `err` and print it under the row; have `verdict()` call a before-run error "fixed?" rather than "fixed". Add a `test_fake` case whose before-run raises (a missing file) to `test_tools`.
- **Confidence:** confirmed

### TEST-5 · medium · flake
- **Where:** `tests/test_runtime_urls.py:86-92,162-180` (`EachPageHasItsTypesBudget`).
- **What:** One test runs `measure_vitals.mjs` over two pages (`--runs 1 --settle 500 --throttle off`) under a 600-second `subprocess.run` timeout and reads the breaches per page. The only timing assumption is that the child finishes inside 600 s; the assertions themselves (LCP over 1 ms breaks the strict budget, under 60,000 ms keeps the home one) cannot flake. No retry, no tolerance beyond the timeout.
- **Evidence:** line 87: `run_node(..., timeout=600, ...)`; lines 174-176 explain that a run with no LCP also exits 1, so the test reads `breaches`, not the exit. `docs/HANDOFF.md:51`: under an MSVC build at 100 % CPU the test timed out at 600 s; alone it passes in 4 s.
- **Effect:** Under load the whole `check.py` fails on this test with a `TimeoutExpired` error, not a wrong measurement.
- **Fix:** It is CPU starvation, not a test bug: say so in the error (catch `TimeoutExpired` in `Served.node` and fail with "timed out at 600 s; the machine was busy") and keep the 600 s. A retry would only hide a hung browser.
- **Confidence:** confirmed

### TEST-6 · medium · flake
- **Where:** `tests/test_browser_runtime.py:502-518` (`VitalsMeasures.test_tbt_stops_at_tti`).
- **What:** Two runs with `--settle 9000`. A 250 ms task at 6,000 ms must start at or after the run's TTI median and be marked `after-tti`; a task at 1,000 ms must start before TTI and be counted. The assumption is that the page reaches TTI (five quiet seconds) between 1 s and 6 s on the page's clock. On a slow Windows runner, loading can push the quiet window past 6 s, so the late task starts before TTI and the first assertion fails.
- **Evidence:** lines 508-511: `out = self.vitals(late.replace("{at}", "6000"), "--throttle", "off", "--settle", "9000") … self.assertGreaterEqual(task["start"], out["stats"]["tti"]["median"])`. Tolerance: the 9 s settle and `task["duration"] - 50` on TBT (line 518); no retry.
- **Effect:** A red CI leg for timing, not for the TTI bound it tests.
- **Fix:** Read `tti` first and only then assert the late task's place (skip with the measured TTI when it is past 5,500 ms), or schedule the late task at `max(6000, tti + 500)` from inside the page as `test_interact_at_clicks_while_the_page_hydrates` already anchors its task to the page's clock.
- **Confidence:** likely

### TEST-7 · medium · flake
- **Where:** `tests/test_browser_runtime.py:388-413` (`VitalsUnderCsp`).
- **What:** One run per variant with `--settle 1500`. The page shifts its content 200 ms after the first paint; the test asserts CLS over 0.1 without the CSP and under 0.01 with it. If the first paint comes late on the runner, the shift lands after the 1,500 ms settle window and the measured CLS is 0, failing the first assertion (the positive control), which is the macOS flake the handoff names.
- **Evidence:** lines 396-399 (the `PerformanceObserver` on `paint` plus `setTimeout(…, 200)`), line 403 (`"--settle", "1500"`), line 412 (`self.assertGreater(self.cls(""), 0.1)`). No retry, no second run.
- **Effect:** A red macOS leg that says nothing about the CSP bypass it guards.
- **Fix:** Settle longer (the `--settle 9000` the TBT test uses costs 8 s) or, better, have the page write a marker when the shift ran and assert the shift happened before asserting its CLS.
- **Confidence:** likely

### TEST-8 · medium · flake
- **Where:** `tests/test_browser_runtime.py:520-558` (`test_interact_at_clicks_while_the_page_hydrates`) and `446-500` (the other `VitalsMeasures` tests).
- **What:** The click at 2,500 ms must land inside a 3-second task that starts at 1,500 ms on the page's clock; the assertions are `clickedAt <= 2800`, INP >= 500, TBT >= 1000, and the control's INP under half the hydrating click's. The upper bound (`<= 2800`) is the one a slow runner breaks: the button must be found and clicked within 300 ms of schedule. The other vitals tests assert lower bounds only (TTFB >= 140/540, INP >= 200, blocking >= 150), which a slow runner cannot break.
- **Evidence:** lines 530-532: `"--interact-at", "2500"` then `self.assertLessEqual(out["perRun"][0]["clickedAt"], 2800, "the click came late")`; the docstring (lines 521-528) records two earlier timing fixes to this test. No retry.
- **Effect:** A red leg under load; the fix history shows it has been moved twice.
- **Fix:** Loosen `2800` to the task's end minus a margin (the click only has to land during the 1,500-4,500 ms task), which keeps the property and drops the 300 ms race.
- **Confidence:** likely

### TEST-9 · low · flake
- **Where:** `tests/test_recipes.py:810-821` (`test_the_safe_triangle_holds_and_a_click_keeps_a_hovered_panel`).
- **What:** The only retry in the suite: up to three browser runs, passing if one of them gives all four outcomes. The comment says the diagonal still failed "now and then" on a loaded macOS runner even on the fake clock.
- **Evidence:** lines 815-819: `for _ in range(3): seen = self.scenario(...); if seen == want: break` then `self.assertEqual(seen, want)`.
- **Effect:** A mega-menu safe triangle that holds two runs in three passes; the test cannot tell a flaky runner from a flaky recipe.
- **Fix:** Count the runs and fail when more than one of three disagrees, or record which outcome flaked in the failure message so a real regression in one outcome is visible.
- **Confidence:** confirmed

### TEST-10 · medium · infra
- **Where:** `.github/workflows/ci.yml:85-88,100-105`; `plugins/pro-web-design-suite/shared/browser_common.mjs:145-149,186-201`.
- **What:** On Windows and macOS the browser tests run against whatever Chrome or Edge the runner image ships, which the image updates without notice; only Linux runs Playwright's pinned headless shell. The three legs therefore test three Chromium versions, none recorded in the run.
- **Evidence:** `ci.yml:85`: `if: runner.os == 'Linux'` on the only `playwright install`; `browser_common.mjs:146-148`: the candidates are the sandbox default, Playwright's own, then `installedBrowsers()`; `tooling/README.md`: "otherwise an installed Chrome or Edge, whose version is not pinned".
- **Effect:** A test that passes on Linux's pinned build and fails on Windows (or the reverse) may be a browser difference, not a bug; the handoff's Windows and macOS flakes are on the unpinned legs. A Chrome update on the image can turn a leg red (or green) with no change in the repository.
- **Fix:** Install the headless shell on all three legs (`npx playwright install --only-shell chromium` is small; the `--with-deps` apt cost is Linux-only), and print the launched browser's label and version in the scripts' `--json` output so a run says what it measured.
- **Confidence:** confirmed

### TEST-11 · low · infra
- **Where:** `.github/workflows/ci.yml:146`.
- **What:** The `validate` job installs `@anthropic-ai/claude-code` unpinned, so the validator's rules drift with each CLI release while the suite's own facts pin 2.1.269 as the evals floor (`tests/fixtures/evidence.json`, entry 45).
- **Evidence:** `run: npm install --global @anthropic-ai/claude-code`; `claude --version` is printed but not compared with anything.
- **Effect:** A CLI release can fail (or newly pass) `claude plugin validate --strict` with no change in the repository, and a build the owner validated locally with 2.1.293 may be judged by a different version in CI.
- **Fix:** Pin the version (`@anthropic-ai/claude-code@2.1.293`) and bump it on purpose, as the Node tools are pinned.
- **Confidence:** confirmed

### TEST-12 · medium · infra
- **Where:** `.github/workflows/ci.yml:26-33,100-105`; `tests/test_policies.py:246-251`; `tests/test_runtime_engines.py:42-80`; `tests/test_token_migration.py:1148`; `tests/test_precommit_hook.py:357-360`; `tests/test_mcp.py:52`.
- **What:** Each leg runs the whole suite (no sharding, no retries, `timeout-minutes: 45`), but some groups run on one leg only: Firefox and WebKit (3 tests) and Postgres (8 tests, `PoliciesRunOnPostgres`) on Linux, where CI puts them on PATH; the POSIX file-mode test and the symlink hook test on Linux and macOS. `test_mcp.TheServerFile.test_claude_plugin_validate_strict_passes` skips on every suite leg (no `claude` CLI there) and is covered only by the separate `validate` job, which `test_ci_validates_what_the_skipped_test_would` (`test_mcp.py:62`) checks.
- **Evidence:** `ci.yml:85-88` (engines and Postgres on PATH, Linux only); `test_policies.py:251`: `@unittest.skipIf(_postgres(), _postgres())` where `_postgres()` needs `initdb`, `pg_ctl`, `psql` on PATH; the skip table below.
- **Effect:** The Postgres policies and the two engines have one leg's evidence; a Windows-only path bug in them is invisible. That is a known trade (P35, P61), not a defect; it is listed so the owner sees the count.
- **Fix:** None needed now; if Windows parity matters, the Windows image has PostgreSQL under `PGBIN` and the step could add it to PATH as the Linux one does.
- **Confidence:** confirmed

### TEST-13 · medium · stale-evidence
- **Where:** `tests/fixtures/evidence.json` (79 entries); `tests/test_evidence.py:188-198`.
- **What:** The register's tests hold every quoted figure to an entry with a `checked` date in `YYYY-MM-DD` form, but nothing reads the date's age: an entry checked in September stays valid for ever. Entries whose sources move: the npm registry's `latest` (entries 20-21, TypeScript 7.0.2 and typescript-eslint 8.71.0, checked 2026-10-04), Claude Code's evals requirement 2.1.269 (entry 45, 2026-10-16), the 20 web-features `.dist` files whose Baseline status changes monthly (entries 46-65, 2026-10-16; `@scope` quotes "Chrome 143, Firefox 146, Safari 26.4"), Figma's plan limits (33-37, 2026-10-11), Supabase's "end of 2026" key deadline (17, 2026-10-01), and the twelve entries checked 2026-09-25 (GDS 2017, Deque 2021, WebAIM Million 2026, Screen Reader Survey #10, NN/g, Baymard, Deloitte, DOJ).
- **Evidence:** `test_evidence.py:193`: `self.assertRegex(entry["checked"], r"^\d{4}-\d{2}-\d{2}$")` is the only use of `checked`; the dates by count: 2026-09-25 ×12, 10-01 ×2, 10-04 ×3, 10-05 ×4, 10-06 ×2, 10-07 ×5, 10-11 ×5, 10-16 ×33, 10-21 ×13.
- **Effect:** A doc can quote a moved figure with a green register.
- **Fix:** A test that lists entries older than N days (90 for studies, 30 for registries and Baseline) as a warning in its message, so the next session re-reads them; and `sync_caniemail.py --data` style refresh commands for the registry entries.
- **Confidence:** confirmed

### TEST-14 · low · stale-evidence
- **Where:** `tests/fixtures/caniemail.json:5`; `tooling/README.md` (Playwright 1.63, axe-core 4.13); `tests/test_commands.py:314-414`.
- **What:** The caniemail pin is `last_update_date: 2026-09-16`, six weeks old; the matrix and the linter are held in step with it (`test_caniemail`), not with caniemail. The Playwright and axe-core versions the suite tests are pinned in `tooling/` (read only through its README here) and the install-gate fixtures name 1.62.1/1.63.0 and axe-core 4.11.0 as example values, so no test asserts which versions the gates were proven on.
- **Evidence:** `caniemail.json:5`: `"last_update_date": "2026-09-16 13:05:00 +0000"`; `test_commands.py:445-447` reads the Playwright pin from `tooling/main/package.json` for the install gate's default image, which is the one place a tooling version reaches a test.
- **Effect:** The email matrix can lag caniemail by months with every test green; a Playwright bump in `tooling/` changes what the browser tests prove without a test saying so.
- **Fix:** Re-read caniemail (`sync_caniemail.py --data`) at each release; register the pinned Playwright and axe-core in `evidence.json` or the CHANGELOG's release notes.
- **Confidence:** confirmed

### TEST-15 · low · weak-test
- **Where:** `tests/test_numbers.py:46-58,67-76` (`VerifiedRatios`).
- **What:** The "Verified 4.60:1 (--neutral-500 on --neutral-100)" claims in the docs are recomputed with `generate_color_ramp.py`'s own `contrast_ratio_oklch` and `parse_color`, the code the claims come from. A wrong OKLCH-to-sRGB conversion would verify its own numbers.
- **Evidence:** line 57: `return self.gen.contrast_ratio_oklch(self.gen.parse_color(...), self.gen.parse_color(...))`. Mitigation: `test_check_roles.py:78-86` has an independent sRGB WCAG `contrast()` applied to the browser's rendered ink (`ORDERS`, lines 74-75), and `test_check_roles.py:178-180` asserts a hard-coded `4.40:1` from `generate_color_ramp --check`.
- **Effect:** Low: the generator's math is cross-checked elsewhere, but this test is not the proof its name suggests.
- **Fix:** Compute the expected ratio in the test with its own sRGB oracle (as `test_check_roles.contrast` does) for at least one pair.
- **Confidence:** confirmed

### TEST-16 · low · weak-test
- **Where:** `tests/test_harness.py:156-164` (`test_cleanup_leaves_behind_what_it_cannot_delete`).
- **What:** No assertion: the test passes when `holder.cleanup()` does not raise while a file is held open. It does not assert the file was left behind, and on POSIX (where the delete succeeds) it asserts nothing about the path either.
- **Evidence:** lines 159-164: `with open(... "held.txt", "w") as held: held.write("x"); held.flush(); holder.cleanup()`; the only call is `self.addCleanup(shutil.rmtree, holder.name, ignore_errors=True)`.
- **Effect:** The harness's own claim (the 3.9 shim at `wds_support.py:175-190`) is checked only as "no exception".
- **Fix:** Assert `os.path.exists(held.name)` on Windows after cleanup, and that the folder is gone on POSIX.
- **Confidence:** confirmed

### TEST-17 · low · weak-test
- **Where:** `tests/test_content_and_a11y.py:255-264`; the 114 `subprocess.run` calls without `check=` the static pass listed.
- **What:** Two tests assert only exit 0 (`test_template_with_attrs_and_content_is_accepted`, `test_attrs_without_content_is_accepted`); both are marked as guards for the refusal tests beside them, which is fine. Of the 114 unchecked `subprocess.run` calls, 113 are followed within ten lines by a `returncode` assertion, a `return proc` to a helper that asserts, or an `output(proc)` read; the one that is not is `test_policies.py:280`, `pg_ctl … stop` in `tearDownClass`. None swallows a failing script.
- **Evidence:** the classification script over `ruff-tests.txt` (`no returncode/assert/return/stdout within 10 lines: 1`, `test_policies.py:280 … tearDownClass`).
- **Effect:** none found.
- **Fix:** none.
- **Confidence:** confirmed

### TEST-18 · low · hygiene
- **Where:** `plugins/pro-web-design-suite/tests/__pycache__/` (`wds_support.cpython-314.pyc`, `wds_support.cpython-39.pyc`); `tooling/release/__pycache__/`; `tests/wds_support.py:24`.
- **What:** `wds_support.py` sets `sys.dont_write_bytecode = True` in its body, which runs after Python has already compiled and cached `wds_support` itself, so a run without `-B` writes exactly that one `.pyc` into the plugin (which is what the folder holds, for 3.9 and 3.14). `check.py` and `fail_before.py` set `PYTHONDONTWRITEBYTECODE`; the files came from a by-hand run. `tooling/release/__pycache__` is `build.py`'s, from a run without `-B`. Both are git-ignored (`git status --ignored`: `!! tests/__pycache__/`, `!! tooling/release/__pycache__/`), and `build.py` reads from `git archive`, so neither can ship.
- **Evidence:** `ls tests/__pycache__` → 2 files, both `wds_support`; `test_tools.py:146` asserts fail_before leaves "no bytecode".
- **Effect:** none shipped; a dirty-looking tree.
- **Fix:** Nothing in code can stop the first module's own `.pyc`; keep the `-B` rule, or add a `.gitignore`d `sitecustomize` is not worth it. Say so in the CLAUDE.md gotcha (it already says "test discovery alone writes tests/__pycache__").
- **Confidence:** confirmed

### TEST-19 · low · hygiene
- **Where:** `tests/test_email.py`, `tests/test_perf_audit.py`, `tests/test_project_config.py`, `tests/test_schema_sources.py`.
- **What:** Four of 68 test files have no `if __name__ == "__main__": unittest.main()` guard. Harmless under `discover` and `-m unittest module`, inconsistent with the other 64.
- **Evidence:** AST pass: `files without unittest.main guard: 4`.
- **Effect:** `python tests/test_email.py` runs nothing.
- **Fix:** Add the guard.
- **Confidence:** confirmed

## Coverage map

Mentions are test files whose source names the script's stem (count of mentions in parentheses). Verdict: covered = behaviour asserted on output, not just exit codes.

| Script | Test files | Verdict |
|---|---|---|
| `shared/project_config.py` (10 copies) | project_config (53 tests), dtcg, diagnostics, encodings, json_guards, out_guard, versioning, email_tokens, email_frameworks, figma_sync | covered |
| `shared/dtcg.py` (10 copies) | dtcg (71), project_config, versioning, figma_sync, contract | covered |
| `shared/project_config.mjs` (7 copies) | project_config (8), real_tools (11), dtcg, release_build | covered |
| `shared/browser_common.mjs` | browser_scripts (22: resolution, fallback, install hint), check_roles, modern_css, out_guard, runtime_reach, runtime_shadow, release_build | covered |
| `hooks/design_hooks.mjs` | hooks (48: guard, gate, a11y gate, email build, token diff, router), evals (the router agrees with the routing cases) | covered |
| `hooks/hooks.json` | hooks.TheHooksFile (4), release_build | covered |
| `mcp/design_gates.mjs`, `.mcp.json` | mcp (21: handshake, tool list, protocol errors, each gate, path refusal, report cut, timeout), evals, release_build | covered |
| `a11y-audit-runner/a11y_runtime.mjs` | browser_runtime (34), runtime_wcag_checks (30), runtime_shadow (9), runtime_urls (9), runtime_reach (11), runtime_engines (10), facts, recipes, commands, json_guards, out_guard | covered (browser) |
| `a11y-audit-runner/a11y_static.py` | content_and_a11y (83), hooks, mcp, stacks, baseline_keys, encodings, utf8_output, precommit_hook | covered |
| `client-presentation-builder/build_presentation.py` | presentation (27), deck, json_guards, out_guard, encodings, powershell_json | covered |
| `component-state-matrix/generate_matrix.py` | content_and_a11y, generated_output, contract, json_guards, out_guard | covered |
| `component-state-matrix/snapshot_matrix.mjs` | browser_runtime.MatrixSeesStateChanges (6), browser_scripts, recipes | covered (browser) |
| `content-model-to-ui/introspect_schema.py` | schema_sources (34), content_and_a11y, policies, scaffold, json_guards, out_guard | covered |
| `content-model-to-ui/scaffold_ui.py` | scaffold (39), scaffold_frameworks (23), policies (20, 8 on a real Postgres), content_and_a11y, contract, generated_output | covered |
| `design-critique-gate/critique_report.py` | presentation (8 mentions), commands, deck, json_guards, out_guard, powershell_json | covered |
| `design-critique-gate/critique_snapshots.mjs` | critique_snapshots (6), runtime_reach, runtime_shadow, browser_scripts, agents | covered (browser) |
| `design-system-docs/build_docs.py` | docs, recipes, system_figma_email, versioning, generated_output, json_guards, project_config | covered |
| `design-system-docs/extract_system.py` | versioning (13), project_config (16), system_figma_email, rules_spec, recipes, out_guard, encodings | covered |
| `design-system-versioning/deprecate.py` | versioning (26), dtcg (35), system_figma_email, encodings, real_tools | covered |
| `design-system-versioning/diff_system.py` | versioning (16), dtcg, diagnostics, hooks, mcp, project_config, out_guard, commands | covered |
| `design-token-migration/apply_codemod.py` | token_migration (87, with 4 git-gated), docs, diagnostics, powershell_json | covered |
| `design-token-migration/cluster_values.py` | token_migration (11), diagnostics, dtcg, out_guard, powershell_json | covered |
| `design-token-migration/extract_literals.py` | token_migration (11), audit_design, stacks, rules_spec, out_guard, encodings | covered |
| `email-template-system/build_email.py` | email (48), email_frameworks, email_rtl, email_tokens, hooks, facts, evidence, out_guard | covered |
| `email-template-system/export_email_theme.py` | email_frameworks (25: MJML and React Email compiled by the real tools, lint, browser) | covered |
| `email-template-system/lint_email.py` | email (10 mentions), caniemail (16), email_frameworks, email_rtl, system_figma_email, hooks, doc_snippets | covered |
| `email-template-system/render_email.mjs` | email.RenderEmail (3), browser_scripts | covered (browser) |
| `email-template-system/sync_email_tokens.py` | email_tokens (24), json_guards | covered |
| `figma-variables-sync/figma_audit.py` | figma_sync (44), docs, diagnostics, system_figma_email, project_config | covered |
| `figma-variables-sync/figma_common.py` | figma_sync (4 mentions, read through `self.read(load_script(...))`), docs, dtcg, versioning | covered |
| `figma-variables-sync/figma_to_tokens.py` | figma_sync (24), dtcg (13), system_figma_email, diagnostics, contract | covered |
| `landing-page-conversion/brief_to_log.py` | brief_to_log (12), out_guard | covered |
| `landing-page-conversion/lint_claims.py` | lint_claims (15), brief_to_log | covered |
| `perf-budget-gate/crux_check.py` | crux_check (10), json_guards | covered |
| `perf-budget-gate/measure_vitals.mjs` | browser_runtime.VitalsMeasures/VitalsUnderCsp (6), runtime_urls, runtime_reach, recipes, browser_scripts.VitalsTiming (fake clocks), commands | covered (browser) |
| `perf-budget-gate/perf_audit.py` | perf_audit (6), content_and_a11y, mcp, recipes, baseline_keys, static_checks | covered |
| `web-design-studio/audit_design.py` | audit_design (84), rules_spec (12), doc_snippets, hooks, mcp, precommit_hook, commands, 20 others | covered |
| `web-design-studio/check_roles.py` | check_roles (23, 2 in a browser), commands, mcp, precommit_hook, utf8_output | covered |
| `web-design-studio/generate_color_ramp.py` | numbers (self-referential, TEST-15), check_roles (`--check`, hard-coded 4.40:1), starter_css | covered |
| `web-design-studio/generate_type_scale.py` | numbers (the starter's 11 steps byte-for-byte, refusals, presets) | covered |
| `web-design-studio/tw_probe.mjs` | tw_probe (23), commands, audit_design | covered |
| `tools/check.py` | tools.CheckChoosesTheTests (4), CheckReportsOnAnyConsole, CheckReadsTheChanges | covered; its gaps are TEST-2/3 |
| `tools/check_pointers.py` | pointers (5) | covered |
| `tools/fail_before.py` | tools.FailBefore (3) + FailBeforeAcrossTheRename (3), file_modes | covered; TEST-4 |
| `tools/sync_caniemail.py` | caniemail.Refresh (5), facts | covered |
| `tools/sync_rules.py` | tools.SyncRules (8), rules_spec | covered |
| `tools/sync_snippets.py` | doc_snippets (4) | covered |
| `workflow-commands/deck/scripts/deck.py` | commands (7, via the SKILL.md's command lines) | covered |
| `workflow-commands/gate/scripts/run_gates.py` | commands.TheGateCommand (5) | covered |
| `workflow-commands/install-gate/scripts/install_gate.py` | commands.TheInstallGate (20), dtcg, encodings | covered |
| `workflow-commands/new-system/scripts/new_system.py` | commands (6, via SKILL.md) | covered; check.py selects none (TEST-2) |
| `workflow-commands/release-check/scripts/release_check.py` | commands (7, via SKILL.md) | covered; check.py selects none (TEST-2) |
| `tooling/release/build.py`, `compare.py` | release_build (41: zip, .skill files, SHA256SUMS, DEV_ONLY, the directory holds, the icon, compare), static_checks | covered |
| `assets/configs/eslint.design.config.mjs` | real_tools (DesignEslintConfig 6, TailwindPluginV4/V3 4, TheGatesReadTheProject 7, OwnClassesCoverTheStarter), recipes, audit_design | covered (real ESLint) |
| `assets/configs/stylelint.config.mjs` | real_tools.StylelintConfig (10) + TheGatesReadTheProject, rules_spec, recipes | covered (real stylelint) |
| `agents/*.md` (6) | agents (7): the six names, only honoured frontmatter fields, tools with no Edit/Write, preloaded skills exist, every script named exists, what each writes is said, `/critique` hands to the critic | covered |
| `workflow-commands/*/SKILL.md` (16) | commands (62): manifest adds the folder, each is user-invoked with allowed tools, and each command's body lines are run as written (install-gate 20, gate 5, new-system 6, release-check 7, deck 7, and one or more for contrast, tw-probe, figma-sync, critique, migrate, docs-check, schema-to-screens, email-build, gate-a11y, gate-perf, gate-matrix) | covered |
| `hooks.json`, `.mcp.json` | see above | covered |

No script has zero tests; none is smoke-only.

## Skips by condition

CI installs on every leg: uv (Python 3.9 and 3.14), Node 22, `npm ci` in `tooling/main` and `tooling/tailwind-v3` (ESLint, stylelint, Tailwind 3 and 4, Playwright 1.63 without a browser, axe-core, js-yaml, MJML, React Email, TypeScript, Vue, Svelte). Linux only: `playwright install --only-shell --with-deps chromium firefox webkit` and Postgres on PATH. Windows and macOS have git, bash (Git Bash), Chrome and Edge from the image.

| Condition | Tests (count) | Runs on | Effectively untested? |
|---|---|---|---|
| no Node (`NODE`) | 42 across browser_scripts, commands, content_and_a11y, docs, email, figma_sync (10), hooks, json_guards, mcp, out_guard, powershell_json, project_config, recipes, runtime_*, real_tools | all legs | no |
| no Playwright+axe (`MODULES`, `PLAYWRIGHT`, `playwright_modules()`, `a11y_modules()`, `AXE`, `BROWSER_MODULES`) | ~196: browser_runtime 34, runtime_wcag_checks 30, runtime_shadow 9, runtime_urls 7, runtime_reach 8, runtime_engines 4, critique_snapshots 5, check_roles 2, email 3, email_rtl 1, modern_css 7, starter_css 5, recipes 9, commands 4, facts 3, persuasion_docs 1 | all legs (Linux: headless shell; Windows/macOS: the image's Chrome/Edge) | no, but a failed launch is a skip on every leg (TEST-1) |
| no Chromium at run time (`skipTest("no usable browser…")` in 12 helpers) | the same ~196 | all legs | see TEST-1 |
| no Firefox / WebKit (`EachEngine`, `WDS_REQUIRE_ENGINES`) | 3 (`test_firefox…`, `test_webkit…`, `test_an_engine_that_skips_bare_links…`) | Linux only; fails there if an engine will not start | one leg |
| no Chrome/Edge installed (`installed_browsers()`) | 1 (`test_a_browser_that_will_not_start_falls_back_to_chrome_or_edge`) | all legs (every image has Chrome) | no |
| no js-yaml (`needs_yaml`, `YAML_MODULES`) | 28 (agents 3, commands, evals 11) | all legs | no |
| no ESLint / stylelint / Tailwind / tailwind-merge / lint plugin (`ESLINT_MODULES`, `STYLELINT_MODULES`, `TAILWIND_MODULES`, `TAILWIND_V4_LINT`, `TAILWIND_V3_LINT`, `TAILWIND`, `TAILWIND_V3`) | real_tools 33, tw_probe 24 | all legs | no |
| no MJML / React Email / TypeScript / Vue / Svelte | email_frameworks 7, scaffold 3, scaffold_frameworks (helper skips) | all legs | no |
| no git (`GIT`) | token_migration 4, docs 2, harness 1, tools (FakeRepository: 6 fail_before/check tests), release_build 27 (`GIT and BUILDER`) | all legs | no |
| no POSIX sh (`GIT and SH`) | precommit_hook 21 | all legs (Git's sh on Windows) | no |
| no symlink privilege | 1 (`test_the_index_mode_never_writes_through_a_staged_symlink`) | Linux, macOS (Windows runners lack the privilege) | two legs |
| Windows (`os.name == "nt"`) | 1 (`test_a_rewritten_file_keeps_its_mode`) | Linux, macOS | two legs |
| no Postgres on PATH (`_postgres()`) | 8 (`PoliciesRunOnPostgres`) | Linux only | one leg (TEST-12) |
| no `claude` CLI (`CLAUDE`) | 1 (`test_claude_plugin_validate_strict_passes`) | no suite leg; the `validate` job runs the same commands | covered by the other job, not the suite |
| no floor interpreter (`FLOOR_PYTHON`, via `uv python find 3.9`) | 3 (docs 2, brief_to_log 1) | all legs (uv is installed) | no |
| no bash (`BASH`, not system32's) | 1 + TheWorkflow 10 (`WORKFLOW and NODE and YAML_MODULES and BASH`) | all legs | no |
| not in the repository (`REPO`, `TOOLING`, `BUILDER`, `COMPARE`, `MODES`, "no repository around the tests") | release_build 14, recipes 3, commands 1, evals 1, file_modes 1, docs 4, mcp 1, pointers 1, doc_snippets 1 | all legs (CI checks out the repository); skip only in a release's copy | no |
| no pydantic | 1 | skipped in the suite step on every leg; run in its own step with `WDS_REQUIRE_PYDANTIC` | no |
| content-dependent (`NotAConflict` absent; Unicode file names; local fonts; `interpolate-size`) | 4 | all legs today (the config's comment names `p-card px-inline-md`; Chrome ≥ 129 everywhere) | no |
| `@unittest.skip("on purpose")` | 0 real tests: it is inside `test_tools.FAKE_TESTS`, a string fixture | n/a | n/a |

Skipped on every CI leg: only `test_mcp.TheServerFile.test_claude_plugin_validate_strict_passes`, whose work the `validate` job does; `test_mcp.py:62` checks that the job runs it.

## Known flakes

- **`test_runtime_urls.EachPageHasItsTypesBudget`** (TEST-5): one `measure_vitals.mjs` child, 600 s timeout, two pages, one run each; the assertions cannot flake, the timeout can. No retry.
- **`test_tbt_stops_at_tti`** (TEST-6): assumes TTI falls between 1 s and 6 s on the page clock; 9 s settle, 50 ms TBT slack; no retry.
- **`VitalsUnderCsp`** (TEST-7): assumes the first paint plus 200 ms falls inside a 1,500 ms settle; no retry; the positive control is the side that fails.
- **`test_interact_at_clicks_while_the_page_hydrates`** (TEST-8): `clickedAt <= 2800` for a click scheduled at 2,500 ms; the task is anchored to the page clock (two earlier fixes); no retry.
- **The vitals timing tests** (`VitalsMeasures`, 5 tests): lower bounds (TTFB ≥ 140/540, INP ≥ 200, blocking ≥ 150, INP ≥ 500, TBT ≥ 1000) that a slow runner cannot break, plus the two upper bounds above.
- The only `time.sleep` is the fixture server's 9-second `/hang` (`test_browser_runtime.py:426`); the only retry loop is TEST-9. Subprocess timeouts run from 60 s to 900 s (`test_token_migration`); CI's job timeout is 45 min with no retry step.

## CHANGELOG regression tests that do not exist

none. The CHANGELOG names 94 distinct test ids in backticks (modules, classes and tests); each module, class and test exists in `tests/` (static AST check; `test_an_image_named_outside_an_image_link_is_held` is a bare test name at `test_release_build.py:520`).

## Evidence register

`tests/fixtures/evidence.json`: 79 entries, each with claim, source, url, checked, quote and docs; 3 `not_statistics` exemptions. `checked` dates: 2026-09-25 (12), 2026-10-01 (2), 10-04 (3), 10-05 (4), 10-06 (2), 10-07 (5), 10-11 (5), 10-16 (33), 10-21 (13). `tests/fixtures/section-pointers.json`: 395 pointers (from, to, section, heading), no dates. `tests/fixtures/caniemail.json`: `last_update_date 2026-09-16`, api 1.0.4. The register's tests keep docs and entries in step but read no age (TEST-13).

Candidates for re-reading, as registered (not fetched): npm `latest` for TypeScript (7.0.2) and typescript-eslint 8.71.0's peer range (2026-10-04); Claude Code evals floor 2.1.269 (2026-10-16); the 20 web-features `.dist` Baseline lines (2026-10-16), above all `@scope` (Chrome 143, Firefox 146, Safari 26.4), `view-transitions`, `scroll-driven-animation` (Safari 26+), `interpolate-size` (Chrome/Edge 129 only); Figma plan and REST limits (2026-10-11); Supabase legacy-key deadline "end of 2026" (2026-10-01); WebAIM Million 2026 and Screen Reader Survey #10 (2026-09-25); caniemail (2026-09-16); the pinned Playwright 1.63 and axe-core 4.13 (`tooling/README.md`), which no evidence entry registers. WCAG 2.2 entries (66-69) were read 2026-10-21.

## Tests per file

68 files, 1,644 test functions (AST count; `CLAUDE.md` says about 1,600). CI runs all of them on each of the six legs, unsharded; `check.py` runs the affected modules locally.

| File | Tests | File | Tests | File | Tests |
|---|---|---|---|---|---|
| test_token_migration | 87 | test_recipes | 36 | test_contract | 16 |
| test_audit_design | 84 | test_schema_sources | 34 | test_caniemail | 16 |
| test_content_and_a11y | 83 | test_numbers | 34 | test_lint_claims | 15 |
| test_dtcg | 71 | test_browser_runtime | 34 | test_starter_css | 14 |
| test_commands | 62 | test_runtime_wcag_checks | 30 | test_system_figma_email | 12 |
| test_project_config | 53 | test_evals | 29 | test_rules_spec | 12 |
| test_persuasion_docs | 49 | test_presentation | 27 | test_brief_to_log | 12 |
| test_hooks | 48 | test_tools | 26 | test_runtime_reach | 11 |
| test_email | 48 | test_email_frameworks | 25 | test_harness | 11 |
| test_docs | 47 | test_email_tokens | 24 | test_runtime_engines | 10 |
| test_figma_sync | 44 | test_tw_probe | 23 | test_crux_check | 10 |
| test_versioning | 43 | test_scaffold_frameworks | 23 | test_runtime_urls | 9 |
| test_real_tools | 43 | test_check_roles | 23 | test_runtime_shadow | 9 |
| test_release_build | 41 | test_browser_scripts | 22 | test_out_guard | 9 |
| test_facts | 40 | test_precommit_hook | 21 | test_evidence | 9 |
| test_scaffold | 39 | test_mcp | 21 | test_diagnostics | 9 |
| test_policies | 20 | test_deck | 21 | test_powershell_json | 8 |
| test_email_rtl | 18 | test_modern_css | 8 | test_agents | 7 |
| test_stacks | 17 | test_perf_audit | 6 | test_json_guards | 6 |
| test_encodings | 6 | test_critique_snapshots | 6 | test_baseline_keys | 6 |
| test_utf8_output | 5 | test_skill_budget | 5 | test_pointers | 5 |
| test_doc_snippets | 4 | test_static_checks | 3 | test_generated_output | 3 |
| test_file_modes | 1 | | | | |

Longest-running, by what they start (no timing markers exist): the ~200 browser tests (each a Node child that launches a browser; 240-600 s timeouts), `PoliciesRunOnPostgres` (initdb and a server per class), `test_real_tools` (real ESLint and stylelint, 300-600 s timeouts), `test_token_migration` (87 tests, one with a 900 s timeout, 4 with git repositories), `test_release_build` (27 tests each building a repository and a zip), `test_precommit_hook` (21 git+sh runs), `test_evals.TheWorkflow` (10 bash runs). The handoff puts a full `check.py` at about 20 minutes on an idle machine.

## Static-analysis candidates, resolved

- PLW1510 ×114 (`subprocess.run` without `check`): 113 are asserted on `returncode`, returned to an asserting helper, or read through `output(proc)` within ten lines; the one left is `test_policies.py:280`, `pg_ctl stop` in `tearDownClass`. None swallows a failing script (TEST-17).
- B023 `test_check_roles.py:44`: the lambda captures loop variable `dark` but is consumed by `re.subn` in the same iteration; false positive.
- B023 `test_commands.py:501`: the lambda captures `value` and is consumed by `re.sub` in the same iteration; false positive. ARG005 (`m` unused) is `re.sub`'s callback signature.
- B008 `test_doc_snippets.py:189`: `plugin: pathlib.Path = pathlib.Path(__file__).resolve().parents[1]` is a constant evaluated once on purpose (the suite's own `sync_snippets.py`, never `WDS_PLUGIN_ROOT`'s); keep.
- RET503 `test_rules_spec.py:292`: the fall-through ends in `self.fail(...)`, which raises; false positive.
- ARG005 `test_crux_check.py:154-155`: `lambda r: None` placeholders in a case table; fine. PERF102 `test_dtcg.py:98`: style only.

## What is covered well

Every shipped script, config, agent, command, hook and the MCP server has behaviour tests, most on real output and many against the real tools (ESLint 10, stylelint 17, Tailwind 3 and 4, MJML, React Email, TypeScript, Vue, Svelte, Playwright with Chromium, Firefox and WebKit, a real Postgres). The spec's examples run through each gate they name (`test_rules_spec`, `test_real_tools`); the references' own snippets pass the audit; the starter's numbers are recomputed; external figures and Baseline lines are registered with quotes and held to the docs; the fail-before protocol has its own tests, across the 4.0.0 rename; `check.py`'s selection has unit tests for the cases it handles; the browser scripts' resolution is tested with planted stubs, with no download ever. No duplicate test names, no order-dependent class state, no `assertTrue(True)`, no Python 3.10 idioms in test code (the one `removesuffix` is guarded), no test writes into the repository, and all 94 test ids the CHANGELOG cites exist.
