# OPS: CI, release, evals, tooling and the distribution repository

Audited 2026-10-28 at main 8441ff0. Files read in full: `.github/workflows/ci.yml`, `release.yml`, `evals.yml`; `tooling/README.md`, `tooling/main/package.json`, `tooling/tailwind-v3/package.json`; `tooling/release/build.py`, `tooling/release/compare.py`; every file under `plugins/pro-web-design-suite/evals/` (154: every `prompt.md`, `case.yaml`, `graders/*.md` and `scaffold.sh` whole; the 17 fixture files under `files/` to their first 1,500 bytes, which cut the four 2,365-byte and the one 2,460-byte `tokens.css`); `plugins/pro-web-design-suite/tests/test_evals.py`; `dev plans/web-design-suite-review/claude-code-capabilities.md` §1 and §11; `docs/HANDOFF.md` lines 44–60. Commands run (read-only; nothing tagged, pushed, dispatched or installed): `gh api` on both repositories' branch protection, rulesets, settings, deploy keys, tags, commits, trees (`main` and `v4.0.1`), README, releases, runs, jobs and artifacts, and on `meta`; `gh secret list`, `gh variable list`, `gh release view v4.0.1`, `gh release list`, `gh run list` (ci, release, evals), `gh run view --log` (CI run 40681521613, eval runs 40322921492, 40124204320, 39911352226, 38413504502, release run 40330031855 attempt 1), `gh release download v4.0.1 -p '*.zip'`; `python -B tooling/release/build.py <empty> --tree <empty>` at HEAD; `python -I` zipfile listing and git-blob hashing of the zip; `git diff --stat v4.0.1 HEAD -- plugins/pro-web-design-suite`, `git diff --name-only --diff-filter=D`, `git log -S`; `npm outdated --json` and `npm audit --json` on both tooling folders (no install; all pins are devDependencies, so `--omit=dev` would have audited nothing and was not used); `curl` of GitHub's workflow-syntax docs; `claude.exe plugin validate --strict` five times with the desktop app's bundled CLI, **2.1.308** (`C:\Users\vybec\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\claude-code\2.1.308\c17a819afb40\claude.exe`; the one on PATH is 2.1.160; CI's validate job ran 2.1.312 today; evals.yml pins 2.1.293).

## Summary

15 findings: 2 high, 4 medium, 9 low. By class (counted from the headings): ci 6, evals 2, release 2, tooling 2, distribution 1, secrets 1, validate 1. The release artefacts, the distribution repository and `claude plugin validate --strict` are clean: the v4.0.1 zip's 230 files equal the distribution tree's 230 blobs hash for hash, the distribution's `main` is the `v4.0.1` tree, both commits are the bot's, and validate passes on the plugin, the marketplace root, `plugin.json`, the built tree and its marketplace manifest with no note. The three most important findings: (1) nothing is required to merge to `main` (no branch protection, no ruleset), and CI's concurrency group cancels `main`'s own runs (5 of the last 60 pushes), so a commit can reach `main` red or unverified; (2) a `v*` tag releases and distributes without checking CI on the tagged commit, and `main` is red right now (8441ff0, macOS · 3.14, a known timing flake), while the directory auto-publishes from the distribution repository; (3) CI's `validate` job installs the Claude Code CLI unpinned (2.1.312 today, against evals' 2.1.293 and the local 2.1.308), so a CLI release can turn an unrelated PR red or quietly relax a check.

## Findings

### OPS-1 · high · ci

- **Where:** repository setting (`main`, Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in); `.github/workflows/ci.yml:13-15`
- **What:** `main` has no branch protection and no ruleset, so nothing is required to merge: no status check, no review, force-pushes and direct pushes allowed. The CI concurrency group also cancels `main`'s run when the next merge lands.
- **Evidence:** `gh api repos/Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in/branches/main/protection` → `{"message":"Branch not protected", "status":"404"}`; `gh api .../rulesets` → `[]`; repository settings `allow_auto_merge: false, delete_branch_on_merge: false`. `ci.yml:14-15`: `group: ci-${{ github.event.pull_request.number || github.ref }}` / `cancel-in-progress: true`, so a push to `main` is group `ci-refs/heads/main`. `gh run list --workflow ci.yml --branch main --event push --limit 60` → `{"cancelled":5,"failure":6,"success":49}`.
- **Effect:** the owner's rule "merge on CI green" is procedural only: a red PR merges with one click, a direct push skips CI and review, and 5 of the last 60 `main` commits have no completed CI run because the next merge cancelled theirs. A later tag on such a commit releases it (OPS-2).
- **Fix:** a ruleset on `main` that requires a pull request, requires the seven CI checks (`ubuntu-latest · Python 3.9`, `… 3.14`, the Windows and macOS pairs, `claude plugin validate --strict`) and blocks force-pushes and deletion; keep cancellation for PRs only: `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`.
- **Confidence:** confirmed

### OPS-2 · high · release

- **Where:** `.github/workflows/release.yml:7-9`, `18-66`, `73-143`
- **What:** a pushed `v*` tag builds, creates the release and writes the distribution repository without checking that CI passed on the tagged commit; the only gates are the tag-equals-`plugin.json` check (lines 36-44) and `build.py`'s own refusals.
- **Evidence:** `release.yml:7-9` `on: push: tags: ["v*"]`; no step in either job reads a check-run or a CI run. `main` at 8441ff0 is red now: CI run 40681521613, `macos-latest · Python 3.14`, step `The suite`, `FAIL: test_a_page_type_picks_the_budget_its_page_is_held_to (test_runtime_urls.EachPageHasItsTypesBudget…)`, the other six legs green. The project `CLAUDE.md` records the directory "tracking `main` [of the distribution repository] with a scheduled check and auto-publish on".
- **Effect:** `git tag v4.0.2 && git push --tags` on a red or cancelled commit publishes it to GitHub and to the distribution repository, from which the directory auto-publishes; the release cannot be rewritten by design (`release.yml:119-122`), so the fix is a new version.
- **Fix:** before `Build the zip…`, a step that requires every CI check on `$GITHUB_SHA` to have concluded `success`: `gh api "repos/$GITHUB_REPOSITORY/commits/$GITHUB_SHA/check-runs" --jq '[.check_runs[] | select(.app.slug=="github-actions") | .conclusion] | all(.=="success") and length>0'` and, taking the latest check run per name (a rerun leaves several), each of the seven required names present with conclusion `success`, failing otherwise; as a workflow step, with `GH_TOKEN` in its `env` block (`GH_TOKEN: ${{ github.token }}`, read scope); or make `release.yml` run on `workflow_run` of CI's success and verify the tag there.
- **Confidence:** confirmed

### OPS-3 · medium · ci

- **Where:** `.github/workflows/ci.yml:151-152`; `.github/workflows/evals.yml:54`
- **What:** the `validate` job installs the Claude Code CLI unpinned, so each run validates with whatever npm's `latest` is; the evals pin 2.1.293 and the local bundled CLI is 2.1.308.
- **Evidence:** `ci.yml:152` `run: npm install --global @anthropic-ai/claude-code`; today's run 40681521613 printed `2.1.312 (Claude Code)`; `evals.yml:54` `npm install --global @anthropic-ai/claude-code@2.1.293`; the bundled CLI reports `2.1.308 (Claude Code)`. `build.py:297` refuses, for the plugin's own `hooks.json`, a launcher that runs a package "without an exact version", the same rule.
- **Effect:** a CLI release that adds a strict check (as 2.1.309 added `ICON_MISSING`, per `CHANGELOG.md` 4.0.1) turns an unrelated PR red; one that relaxes a check lets a problem through unnoticed; three CLIs disagree about what "valid" means, and the eval pin is 19 releases behind what users run.
- **Fix:** pin `@anthropic-ai/claude-code@2.1.312` in `ci.yml` (a comment with the date), move `evals.yml` to the same pin after one dispatched run, and bump both deliberately when the directory's checks change.
- **Confidence:** confirmed

### OPS-4 · medium · ci

- **Where:** `.github/workflows/ci.yml:115-119` (the suite), whole file (no `upload-artifact`, no retry); `docs/HANDOFF.md:55-60`
- **What:** the timing tests the handoff lists as known flakes fail `main` outright: no retry, no artefact with the measured numbers, so each red run costs a rerun and a judgement call.
- **Evidence:** run 40681521613 on 8441ff0: `AssertionError: Lists differ: [('home', []), ('strict', ['lcp'])] != [('home', []), ('strict', [])]` in `test_runtime_urls.py:177` (the strict budget measured an LCP breach on the macOS runner; `macos-latest · Python 3.9` passed the same commit); `HANDOFF.md:56-60` lists `test_runtime_urls.EachPageHasItsTypesBudget`, `test_tbt_stops_at_tti`, `VitalsUnderCsp`, `test_interact_at_clicks_while_the_page_hydrates` and "the vitals timing tests" as known flakes; 6 failures in the last 60 `main` pushes. `ci.yml` has no `actions/upload-artifact` and no `retry`.
- **Effect:** `main` reads red for a reason that is not the code; with OPS-1 and OPS-2 the owner must decide by eye whether a red is a flake before tagging.
- **Fix:** separate the measurement from the classification in those tests (classify recorded vitals against the budgets; measure once in a test that asserts only that a number came back), or mark them with a one-retry decorator that re-measures; upload `tests`' reports and the measured JSON on failure (`if: failure()`), 7-day retention.
- **Confidence:** confirmed

### OPS-5 · medium · evals

- **Where:** `plugins/pro-web-design-suite/evals/` (file list); `tests/test_evals.py:53-57`, `115-116`
- **What:** six of the thirteen skills have no outcome case and four have no boundary case; pairs the descriptions make easy to confuse are uncovered.
- **Evidence:** the 11 outcome cases exercise web-design-studio (5: `build/*`, `systems/brand-tokens`), a11y-audit-runner, figma-variables-sync, design-system-versioning, landing-page-conversion, content-model-to-ui and email-template-system; none exercises client-presentation-builder, component-state-matrix, design-critique-gate, design-system-docs, design-token-migration or perf-budget-gate. `PAIRS` (`test_evals.py:53-57`) holds five pairs; client-presentation-builder, content-model-to-ui, email-template-system and perf-budget-gate appear in no boundary case. From the skills' descriptions: perf-budget-gate × a11y-audit-runner (both "fail the build" "in CI"), design-critique-gate × client-presentation-builder (both "before a client sees" / "to a client"), design-token-migration × web-design-studio (tokens into a codebase), content-model-to-ui × web-design-studio (React screens on the system), design-system-versioning × design-token-migration (renaming tokens), email-template-system × web-design-studio (the same tokens, compiled) are uncovered.
- **Effect:** a regression in the instructions of the six skills, or the router choosing perf-budget-gate for an accessibility gate, passes the evals that gate a release.
- **Fix:** one outcome case per uncovered skill (the recorded cost is about $0.45 a case for three runs in both arms: outcome 11 cases cost $4.98 on 2026-10-23, so six more fit the $14 ceiling with routing's $4.16), and three boundary pairs (perf-budget-gate ↔ a11y-audit-runner, design-critique-gate ↔ client-presentation-builder, design-token-migration ↔ web-design-studio), with `PAIRS` and the counts at `test_evals.py:115-116` updated.
- **Confidence:** confirmed

### OPS-6 · low · evals

- **Where:** `evals/build/pricing-section/graders/audit-clean.md:4`, `evals/build/stretched-card/graders/audit-clean.md:4`, `evals/build/tailwind-button/graders/audit-clean.md:4`; `tests/test_evals.py:275-276`
- **What:** `audit-clean` matches any gate's pass verdict anywhere in the trace, not `audit_design`'s.
- **Evidence:** the pattern is `verdict\\*"\s*:\s*\\*"pass` on `target: trace`; `mcp/design_gates.mjs:206` writes `{ tool: name, exit, verdict, report }` for all five tools, so a `check_roles` or `a11y_static` pass satisfies it; `systems/brand-tokens/graders/contrast-pass.md` names its tool (`check_roles\\*"\s*,\s*\\*"exit\\*"\s*:\s*0\s*,…`); `test_evals.py` `SAMPLES["audit-clean"]` lists no other tool's pass among the misses (`mcp_result("check_roles", 0, "pass")` is a miss only for `contrast-pass`, line 278). A run that passes the audit and then breaks the file also keeps the earlier `pass`.
- **Effect:** the "audit passed it" step grader can pass a run in which the design audit never ran or last failed.
- **Fix:** `audit_design\\*"\s*,\s*\\*"exit\\*"\s*:\s*0\s*,\s*\\*"verdict\\*"\s*:\s*\\*"pass` in the three graders, and `mcp_result("check_roles", 0, "pass")` added to `audit-clean`'s misses.
- **Confidence:** confirmed

### OPS-7 · medium · tooling

- **Where:** `tooling/tailwind-v3/package-lock.json`, `tooling/main/package-lock.json` (test-only; the plugin ships no dependency)
- **What:** `npm audit` reports one high and one moderate advisory in the Tailwind v3 toolchain and one moderate plus four low in the main one; Dependabot shows none.
- **Evidence:** `npm audit --prefix tooling/tailwind-v3 --json`: `source-map-js: high … event-loop denial of service through indexed source-map section offsets, range 1.0.0 - 1.2.1, fixAvailable True`; `postcss-selector-parser: moderate … Quadratic complexity in flat selector parsing, range <6.1.5, fixAvailable True`. `--prefix tooling/main`: `{"low": 4, "moderate": 1, "high": 0, "critical": 0}`: `fast-uri: moderate … URI scheme spoofing, range 3.0.0 - 3.1.8, fixAvailable True`; `react-email`, `@react-email/render`, `html-to-text`, `deepmerge`: low, whose fix is a downgrade to `react-email 5.2.11` (`isSemVerMajor: True`). `gh api .../dependabot/alerts?state=open` → `0`; vulnerability alerts enabled (`204`), `dependabot_security_updates: disabled`.
- **Effect:** the tests run a vulnerable `source-map-js` on every PR's fixture; harmless to users, but the directory's reviewer reads lockfiles when they ship (they do not) and the figure is wrong in any "security scan shows zero HIGH" claim (the workspace's pre-deploy gate).
- **Fix:** in the next chore PR, lockfile-only bumps: `npm update source-map-js postcss-selector-parser --prefix tooling/tailwind-v3` and `npm update fast-uri --prefix tooling/main`, then the suite; leave the react-email chain until upstream moves past `html-to-text 9.0.5`.
- **Confidence:** confirmed

### OPS-8 · low · tooling

- **Where:** `tooling/main/package.json:9-30`, `tooling/tailwind-v3/package.json:7-11`; `tests/test_recipes.py:531, 540-544, 553-555, 575`; `tests/test_commands.py:446`; `tests/fixtures/evidence.json:290-301`
- **What:** eight pins are a minor or patch behind; no pin is a major behind by accident (TypeScript 7 is outside typescript-eslint's peer range, jsdom 30 drops Node 20, Tailwind 3 is the v3 folder's purpose). Seven pins are asserted exactly by tests, so a bump is a two-file change, and the evidence register's typescript-eslint entry names 8.71.0 as "latest" while the pin is 8.70.1 and npm's latest is 8.72.1.
- **Evidence:** the table below. `evidence.json:294` `"claim": "typescript-eslint's latest release, 8.71.0, …"`, `"checked": "2026-10-04"`; `package.json:28` `"typescript-eslint": "8.70.1"`.
- **Effect:** stale minors only; a bump that forgets `test_recipes.py` or `install_gate.py`'s `TESTED_PLAYWRIGHT` fails the suite, which is the design.
- **Fix:** a monthly chore PR folded into the next feature PR (the owner's rule), or Dependabot groups for `tooling/main` and `tooling/tailwind-v3` (OPS-9); re-read the typescript-eslint evidence at the pinned version.
- **Confidence:** confirmed

### OPS-9 · low · ci

- **Where:** `.github/` (no `dependabot.yml`); `.github/workflows/ci.yml:37, 41, 46, 78, 108`
- **What:** nothing updates the actions or the npm pins. `ci.yml` pins actions to mutable tags; `release.yml` and `evals.yml` pin to commit SHAs that only a hand edit moves.
- **Evidence:** `ls .github/` → `assets workflows`; `ci.yml:37` `actions/checkout@v7`, `:41` `astral-sh/setup-uv@v10.2.0`, `:46` `actions/setup-node@v7`, `:78` `actions/cache/restore@v6`, `:108` `actions/cache/save@v6`; `release.yml:27, 32, 88, 93` and `evals.yml:43, 48, 143` are 40-hex SHAs with version comments.
- **Effect:** the SHA pins protect the jobs that hold a key (the audit's D2) but age silently; the tag pins in `ci.yml` move under the job without a diff.
- **Fix:** `.github/dependabot.yml` with `package-ecosystem: github-actions` (weekly, so SHA pins get a PR with the new SHA and comment) and two `npm` entries for `tooling/main` and `tooling/tailwind-v3` (monthly, grouped), labelled so they fold into the next feature PR.
- **Confidence:** confirmed

### OPS-10 · low · secrets

- **Where:** repository settings, Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in
- **What:** secret-scanning push protection is off on a public repository, and Dependabot security updates are off.
- **Evidence:** `gh api repos/Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in --jq .security_and_analysis` → `secret_scanning: disabled, secret_scanning_push_protection: disabled, dependabot_security_updates: disabled`. The secrets themselves are two (`ANTHROPIC_API_KEY` 2026-10-10, `DIST_DEPLOY_KEY` 2026-10-19), no variables; each is read by one step (table below); no workflow uses `pull_request_target`; `ci.yml` runs on `pull_request` with `contents: read` and no secret, so a fork's PR gets nothing.
- **Effect:** the directive "no secret ever committed" relies on the staged-diff rule alone; GitHub's push protection, free for public repositories, would refuse a push that carries a known key pattern.
- **Fix:** Settings → Code security: enable push protection (and secret scanning alerts); consider Dependabot security updates for `tooling/`.
- **Confidence:** confirmed

### OPS-11 · low · distribution

- **Where:** Vybecode-LTD/pro-web-design-suite (settings)
- **What:** the distribution repository has Issues and Wiki on, and no ruleset on `main`, although its README and `release.yml:67-72` say only the workflow writes it and the issues live in the development repository.
- **Evidence:** `gh api repos/Vybecode-LTD/pro-web-design-suite` → `{"default_branch":"main","private":false,"has_issues":true,"has_wiki":true}`; `.../branches/main/protection` → 404; `.../rulesets` → `[]`; branches: `main` only; commits: `4809e3f github-actions[bot] Pro Web Design Suite 4.0.1`, `28efdaa github-actions[bot] Pro Web Design Suite 4.0.0` (nobody by hand so far); deploy keys: one, `166961999`, `read_only: false`, "release.yml distribute (Pro-Web-Designer-Suite-Plug-in)".
- **Effect:** a user files an issue where nobody reads; a hand push to `main` (the owner's own, by mistake) is possible and the next release would commit on top of it; the workflow still refuses to replace a newer tag (`release.yml:123-127`) and never forces (`:141`), so the content stays right.
- **Fix:** turn Issues and Wiki off; a ruleset on `main` that restricts updates to the deploy key as its bypass actor.
- **Confidence:** confirmed

### OPS-12 · low · validate

- **Where:** `plugins/pro-web-design-suite/CLAUDE.md` ("Commands", the `claude plugin validate` paragraph, and "Gotchas", "The desktop app is an MSIX package")
- **What:** the documented path of the bundled CLI no longer exists; the CLI moved folders and versions.
- **Evidence:** `ls C:\Users\vybec\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude-code\` → no such directory (the `Claude` folder holds one zero-byte marker); `%APPDATA%\Claude\` holds `claude_desktop_config.json` only; `find` found `C:\Users\vybec\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\claude-code\2.1.304\aed62990b91e\claude.exe` and `…\2.1.308\c17a819afb40\claude.exe`; the latter reports `2.1.308 (Claude Code)`.
- **Effect:** the next session's `validate` runs the 2.1.160 on PATH, or spends a search.
- **Fix:** replace both lines with `C:\Users\vybec\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\claude-code\<version>\<build>\claude.exe` (2.1.308's build folder is `c17a819afb40`).
- **Confidence:** confirmed

### OPS-13 · low · ci

- **Where:** `.github/workflows/ci.yml:115-128`; `tests/wds_support.py`
- **What:** a leg passes however many tests skip; only two skips are turned into failures (`WDS_REQUIRE_ENGINES` on Linux, `WDS_REQUIRE_PYDANTIC`), so a broken tool resolution that skipped every real-tool test would still be green.
- **Evidence:** run 40681521613: `ubuntu … 3.9: OK (skipped=2)`, `… 3.14: OK (skipped=5)`, `windows … 3.9: OK (skipped=15)`, `… 3.14: OK (skipped=18)`, `macos … 3.9: OK (skipped=14)`, `… 3.14: FAILED (failures=1, skipped=13)`; `grep WDS_REQUIRE tests/*.py` → only `test_runtime_engines.py` and `test_scaffold.py`; no test or step reads the skip count.
- **Effect:** `tool_modules()` returning nothing (a moved `tooling/`, a changed env name) would silently remove the real-tool and browser tests from CI.
- **Fix:** on Linux, `WDS_REQUIRE_TOOLS=1` that makes `needs_*` decorators in `wds_support.py` fail instead of skip, or a final step that fails when the leg's `skipped=` exceeds a per-OS ceiling.
- **Confidence:** confirmed

### OPS-14 · low · ci

- **Where:** `.github/workflows/ci.yml:88-92`, `64-111`
- **What:** P61 (#208) caches apt's `.deb` files, not the browsers: the Chromium headless shell, Firefox and WebKit download from Playwright's CDN on every Linux run.
- **Evidence:** `ci.yml:91` `npx playwright install --only-shell --with-deps chromium firefox webkit`; the cache steps (`:75-82`, `:106-111`) cover `/var/cache/wds-debs/*.deb` only; no step caches `~/.cache/ms-playwright`.
- **Effect:** several hundred MB a run, the CDN's speed in the 45-minute budget (the Linux legs took 632 s and 806 s today).
- **Fix:** `actions/cache` on `~/.cache/ms-playwright` keyed by the `playwright` version in `tooling/main/package-lock.json`, with the install step after it.
- **Confidence:** confirmed

### OPS-15 · low · release

- **Where:** `tooling/release/build.py:362-363`, `475-477` (another pass audits the code; reported here for what the release log shows)
- **What:** the "removed since the previous tag" list misses a renamed file, because `git diff --diff-filter=D` runs with rename detection on.
- **Evidence:** `git diff --name-only --diff-filter=D v4.0.1 HEAD -- plugins/pro-web-design-suite` → empty; `git diff --name-status` → `R100 …/.claude-plugin/icon.png → …/pro-web-design-suite-icon.png`; the HEAD build printed no `removed since v4.0.1:` line.
- **Effect:** the release log would not record that `.claude-plugin/icon.png` left the plugin; the distribution commit is right regardless (`git rm -r` then copy, `release.yml:133-134`).
- **Fix:** add `--no-renames` to the diff at `build.py:363`.
- **Confidence:** confirmed

## claude plugin validate --strict: full output

`C:\Users\vybec\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\claude-code\2.1.308\c17a819afb40\claude.exe --version` → `2.1.308 (Claude Code)`.

Target `C:\DEV\Pro-Web-Designer-Suite-Plug-in\plugins\pro-web-design-suite` (exit 0):

```
Validating marketplace manifest: C:\DEV\Pro-Web-Designer-Suite-Plug-in\plugins\pro-web-design-suite\.claude-plugin\marketplace.json

Plugin directory checks for C:\DEV\Pro-Web-Designer-Suite-Plug-in\plugins\pro-web-design-suite. The plugin directory is the catalog that plugins are submitted to; this is a subset of what it runs.

About these checks:

  ❯ This folder also holds a marketplace manifest. The plugin directory treats such a folder as a plugin, so these checks cover only the plugin in this folder. To check another plugin that the marketplace lists, run validate on that plugin's folder.

✔ These checks found nothing to report

The directory also runs a safety scan and a policy review that this command does not.

✔ Validation passed
```

Target `C:\DEV\Pro-Web-Designer-Suite-Plug-in` (the marketplace root; exit 0):

```
Validating marketplace manifest: C:\DEV\Pro-Web-Designer-Suite-Plug-in\.claude-plugin\marketplace.json

✔ Validation passed
```

Target `…\plugins\pro-web-design-suite\.claude-plugin\plugin.json` (exit 0): `Validating plugin manifest: …\plugin.json`, then the same directory-checks block as the first target, `✔ These checks found nothing to report`, `✔ Validation passed`.

Target the `--tree` output folder (the distribution shape, `…\scratchpad\ops\tree-head`; exit 0): `Validating marketplace manifest: …\tree-head\.claude-plugin\marketplace.json`, the same directory-checks block, `✔ These checks found nothing to report`, `✔ Validation passed`.

Target `…\tree-head\.claude-plugin\marketplace.json` (exit 0): `Validating marketplace manifest: …`, `✔ Validation passed`.

CI's `validate` job (`ci.yml:141-165`) runs the same five targets with the unpinned CLI (2.1.312 today) and passed on 8441ff0.

## build.py --tree vs the distribution repository's main

`python -B tooling/release/build.py <empty> --tree <empty>` at 8441ff0 printed:

```
wrote …\ops\build-head from 8441ff057158: pro-web-design-suite-4.0.1.zip (313 entries, 231 files, 37 executable), 13 .skill files, SHA256SUMS; testzip: OK
  tree: …\ops\tree-head (231 files)
```

No `warning:` and no `directory hold:` line (the icon's stem is now `pro-web-design-suite-icon`, which no shipped text names). The zip is still named 4.0.1 because `plugin.json` says `"version": "4.0.1"` while `CHANGELOG.md:3` says `## 4.0.2 — unreleased`; `release.yml:36-44` would refuse a `v4.0.2` tag until the bump.

The distribution repository's `main` (`gh api …/git/trees/main?recursive=1`, `truncated: false`) holds 230 blobs, and its tree at `v4.0.1` is the same 230 blobs with the same SHAs (`diff` empty). The HEAD tree holds 231 files. The name diff:

| Path | Distribution `main` (4.0.1) | HEAD tree | Explained by |
|---|---|---|---|
| `.claude-plugin/icon.png` | present | absent | P60 (#207): renamed, `git diff --name-status v4.0.1 HEAD` → `R100 icon.png → pro-web-design-suite-icon.png` |
| `.claude-plugin/pro-web-design-suite-icon.png` | absent | present | P60 (#207) |
| `skills/email-template-system/scripts/sync_email_tokens.py` | absent | present | P62 (#209) |

Every other name matches. `git diff --stat v4.0.1 HEAD -- plugins/pro-web-design-suite` lists 29 files (2,571 insertions, 307 deletions): `plugin.json` (the icon's name), the rename, `CHANGELOG.md`, `shared/browser_common.mjs` and its five skill copies (P64/P65), `a11y_runtime.mjs` and three a11y references (P65), `introspect_schema.py`, `scaffold_ui.py` and `field-mapping.md` (P63), the email skill's `SKILL.md`, `email-tokens.json`, `email-workflow.md` and `sync_email_tokens.py` (P62), and ten test files that never ship. Nothing unexplained.

The HEAD tree's `.claude-plugin/marketplace.json` names the plugin at `"source": "./"` with `"renames": {"web-design-suite": "pro-web-design-suite"}`; top level: `.claude-plugin` (3), `.gitattributes`, `.mcp.json`, `CHANGELOG-earlier.md`, `CHANGELOG.md`, `LICENSE`, `README.md`, `SECURITY.md`, `agents` (6), `hooks` (3), `mcp` (1), `shared` (5), `skills` (184), `workflow-commands` (22); no `tests/`, `evals/` or `tools/`.

The distribution repository: default branch `main`, public, one branch, tags `v4.0.1 4809e3f` and `v4.0.0 28efdaa`, two commits both authored and committed by `github-actions[bot]` ("Pro Web Design Suite 4.0.1", "… 4.0.0"), `pushed_at 2026-10-26T13:24:57Z` (the v4.0.1 `distribute` job ran 13:24:48–13:25:00). Its README's install block: `/plugin marketplace add Vybecode-LTD/pro-web-design-suite` then `/plugin install pro-web-design-suite@pro-web-design-suite`, with the zip alternative ("the unpacked `pro-web-design-suite` folder, the one that holds `.claude-plugin/marketplace.json`"), which the zip's layout matches.

Release mechanics verified: `concurrency: { group: distribute, queue: max }` (`release.yml:82-84`) is a documented key (GitHub's workflow-syntax page lists `queue: max` beside `cancel-in-progress`), added in `4241c99` and used by two green runs. The pinned host key at `release.yml:114` equals `gh api meta --jq .ssh_keys` (`ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl`). Re-run and re-tag: `distribute` refuses an existing tag (`:119-122`) and an older version (`:123-127`), pushes `main` and the tag with `--atomic` (`:141`), so a failed push reruns clean and a release is never rewritten; the `release` job reruns clean too, because `gh release create` uploads into a draft that it discards on failure: the v4.0.1 run (40330031855) is `run_attempt 2`; attempt 1 failed at `Create the release` with `HTTP 404: Not Found (https://uploads.github.com/repos/…/releases/424278932/assets?label=&name=a11y-audit-runner.skill)`, and the release that exists is `424280807` with no draft left (`gh api …/releases` lists six releases, all `draft=false`). The handoff's advice (`HANDOFF.md:52`, `gh run rerun RUN --failed`) is right.

## The release zip vs the distribution tree at v4.0.1

`gh release download v4.0.1 -p '*.zip' -D …\scratchpad\ops\release\` → `pro-web-design-suite-4.0.1.zip`, 2,553,371 bytes, SHA-256 `50b3308d95d8283b58b6264e999e8d162f221686c376dc122bd45c64eafbff99`. Listed with `python -I` from another folder: 312 entries, 230 files, one top-level folder `pro-web-design-suite/`; `testzip()` clean; every entry dated `2026-10-26 12:29:20` (the tagged commit's time); modes 193 × `0644`, 37 × `0755`. Each file's git blob hash (`sha1("blob <size>\0" + bytes)`) against the tree API at `v4.0.1`: **230 same, 0 differ, 0 only in the zip, 0 only in the tree.** The zip and the distribution tree are the same files, byte for byte.

Assets (`gh release view v4.0.1`): 15: `pro-web-design-suite-4.0.1.zip` (2,553,371), `SHA256SUMS` (1,312), and 13 `.skill` files, one per skill: a11y-audit-runner (205,503), client-presentation-builder (124,339), component-state-matrix (94,087), content-model-to-ui (210,127), design-critique-gate (89,949), design-system-docs (117,708), design-system-versioning (128,433), design-token-migration (178,674), email-template-system (190,847), figma-variables-sync (129,560), landing-page-conversion (94,557), perf-budget-gate (153,978), web-design-studio (547,826). The body is the CHANGELOG's 4.0.1 section inlined (`release.yml:49-58`), not a link to it; the tag `v4.0.1` is an annotated tag by VybeCodeLTD on `84f4a4f`, `targetCommitish: main`.

## Pinned tooling vs latest

`npm outdated --json` on 2026-10-28; "latest" = npm's `latest` tag. "Test pin" = where the suite asserts the version, so a bump needs that edit too.

| Package (folder) | Pinned | Latest | Behind | Test pin |
|---|---|---|---|---|
| eslint (main, tailwind-v3) | 10.11.0 | 10.13.0 | minor | `test_recipes.py:575` (the config header must say "run this config on 10.11.0.") |
| eslint-plugin-better-tailwindcss (main, tailwind-v3) | 4.9.0 | 4.10.0 | minor | — (`test_recipes.py` evidence comment at 4.9.0) |
| eslint-plugin-jsx-a11y | 6.10.2 | 6.10.2 | — | `test_recipes.py:567` (the `overrides` block) |
| typescript-eslint | 8.70.1 | 8.72.1 | minor | `evidence.json:290-301` names 8.71.0 as latest (checked 2026-10-04) |
| typescript | 6.0.3 | 7.0.2 | **major**, deliberate: typescript-eslint's peer range is `<6.1.0`; the shipped header says `typescript@~6.0` | `evidence.json:303-310` (7.0.2 as "the version an unpinned install gets") |
| stylelint | 17.15.0 | 17.16.0 | minor | — |
| stylelint-config-standard | 40.0.0 | 40.0.0 | — | `test_recipes.py` (major 40) |
| stylelint-config-standard-scss | 17.0.0 | 17.0.0 | — | `test_recipes.py:531` exact |
| postcss-scss | 4.0.9 | 4.0.9 | — | `test_recipes.py:531` exact |
| playwright | 1.63.0 | 1.64.1 | minor | `test_commands.py:446` = `install_gate.py:48` `TESTED_PLAYWRIGHT = "1.63.0"` |
| axe-core | 4.13.0 | 4.14.0 | minor | — |
| tailwindcss (main), @tailwindcss/node | 4.3.3 | 4.3.3 | — | — |
| tailwindcss (tailwind-v3) | 3.4.19 | 4.3.3 | **major**, the folder's purpose (`tooling/README.md`) | — |
| tailwind-merge | 3.7.0 | 3.7.0 | — | — |
| vue | 3.5.44 | 3.5.44 | — | `test_recipes.py:540-544` exact, and the lock's compiler-sfc/server-renderer |
| svelte | 5.57.2 | 5.57.3 | patch | `test_recipes.py:553` exact |
| jsdom | 29.1.1 | 30.1.3 | **major**, deliberate: jsdom 30 drops Node 20 (`test_recipes.py:548-556`) | `test_recipes.py:553` exact, plus the engines range |
| mjml | 5.4.1 | 5.4.1 | — | — |
| react, react-dom | 19.3.1 | 19.3.1 | — | — |
| react-email | 6.11.3 | 6.11.4 | patch | — |

`npm audit`: main `{"low": 4, "moderate": 1, "high": 0, "critical": 0}` of 699 packages; tailwind-v3 `{"moderate": 1, "high": 1}` (OPS-7).

What the shipped docs tell users to install, against these pins: `skills/web-design-studio/assets/configs/eslint.design.config.mjs:21, 35` `npm i -D eslint@^10 eslint-plugin-jsx-a11y`, `npm i -D typescript-eslint typescript@~6.0`, `:958` `npm i -D eslint-plugin-better-tailwindcss`; `stylelint.config.mjs:11-12` `stylelint@^17 stylelint-config-standard@^40`, `postcss-scss@^4 stylelint-config-standard-scss@^17`; `tailwind.config.ts:29` `tailwindcss@^3`; the a11y, matrix, critique, email and perf scripts' `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm i -D -E playwright axe-core` (no version); `install_gate.py:137, 243` pins `playwright@1.63.0` (= `TESTED_PLAYWRIGHT`, test-checked). Every range contains the pinned test version; nothing shipped names a version the tests do not run.

## Evals: coverage by skill

The configuration is per case (`prompt.md` frontmatter; `case.yaml` only for `context.scaffold_script`), there is no suite-level file. Routing cases: `tags: [routing]`, `allowed_tools: [Skill]`, `max_turns: 10`; boundary cases `tags: [routing, boundary]`; outcome cases `tags: [outcome, <area>]`, `allowed_tools: [Read, Glob, Grep, Skill]`, `max_turns` 10–30, `timeout_seconds` 300–600. `evals.yml`: `workflow_dispatch` only (`tag` routing | outcome | all, `runs` 1–50, default 3), the secret `ANTHROPIC_API_KEY`, CLI `2.1.293`, `--model claude-sonnet-5-5 --judge-model claude-haiku-5-5 --threshold 1.0 --trust-plugin --no-publish`, ceiling `--max-cost-usd 14` (D5's $15 less one run in flight; the outcome set gets what routing left, and under $1 left it stops with an error); routing `--ablation none`; outcome `--ablation with-without --scaffold --allow-real-servers --allow-tools Write Edit "mcp__plugin_pro-web-design-suite_gates__*"` (never Bash; the grant matches `.mcp.json`'s `gates` server and the plugin's name); artefact `eval-results` (`$RUNNER_TEMP/evals/`, always; 107,058 bytes for the green run, expires 2027-01-24); step summary from `routing.json` and `outcome.json`. The figures agree: $15 budget, $14 ceiling, $9.55 spent on the green run (`execution-plan.md:315`), "about $10" in the handoff.

Last runs (`gh run list --workflow evals.yml`): 2026-10-26 **success** on `84f4a4f` (routing 23 of 23, outcome 11 of 11, `no-fake-countdown` 3 of 3, $9.55); 2026-10-24 failure on `d9125b7` (`no-fake-countdown` 2 of 3, `completion-plan.md:173`); 2026-10-23 failure on `5e30a70` (routing 23 of 23 at $4.16, outcome 10 of 11 at $4.98, `no-fake-countdown` 2 of 3, `4.0.0-live-check.md:60`); 2026-10-13 failure on `d2c1f9b` (the outcome set wrote its JSON and exited 1; the case is not recorded in the dev plans I read); 2026-10-10 cancelled (a `push`, before the trigger was cut to dispatch only). Each log also prints, once per routing case, `mocks: "plugin:pro-web-design-suite:gates" has no mock and is NOT started`: expected, the routing set does not pass `--allow-real-servers`.

Drift: none found. No prompt names a skill or the plugin (`test_evals.py:133-135`); the `expected_outcome` fields name `pro-web-design-suite:<skill>`; the skill graders accept any prefix (`(?:[\w-]+:)?`); the gate graders' shape matches `mcp/design_gates.mjs:206` (`{tool, exit, verdict, report}`); the fixtures' `.design-suite.json` keys (`schema`, `tokens`, `components`, `stack: tailwind-v4`, `hooks.emailBuild`) are all in `shared/project_config.py:97-108`; `lifecycle/dtcg-export` asks for the 2025.10 colour objects `shared/dtcg.py` writes; no old id outside the four allowed forms and no old command prefix appears. `claude-code-capabilities.md` §11 still spells the grant `mcp__plugin_web-design-suite_gates__*` as P30 chose it; a historical record, and `evals.yml:113` carries the renamed one.

| Skill | Routing case | Boundary cases (must load / must not) | Outcome cases |
|---|---|---|---|
| a11y-audit-runner | `routing/a11y-audit-runner` | ↔ design-critique-gate (both ways); ↔ component-state-matrix (both ways) | `gates/axe-not-compliance` |
| client-presentation-builder | `routing/client-presentation-builder` | **none** | **none** |
| component-state-matrix | `routing/component-state-matrix` | ↔ a11y-audit-runner (both ways) | **none** |
| content-model-to-ui | `routing/content-model-to-ui` | **none** | `delivery/profile-form` |
| design-critique-gate | `routing/design-critique-gate` | ↔ a11y-audit-runner (both ways) | **none** |
| design-system-docs | `routing/design-system-docs` | ↔ design-system-versioning (both ways) | **none** |
| design-system-versioning | `routing/design-system-versioning` | ↔ design-system-docs (both ways) | `lifecycle/repoint-is-major` |
| design-token-migration | `routing/design-token-migration` | ↔ figma-variables-sync (both ways) | **none** |
| email-template-system | `routing/email-template-system` | **none** | `delivery/receipt-email` |
| figma-variables-sync | `routing/figma-variables-sync` | ↔ design-token-migration (both ways) | `lifecycle/dtcg-export` |
| landing-page-conversion | `routing/landing-page-conversion` | ↔ web-design-studio (both ways) | `persuasion/no-fake-countdown` |
| perf-budget-gate | `routing/perf-budget-gate` | **none** | **none** |
| web-design-studio | `routing/web-design-studio` | ↔ landing-page-conversion (both ways) | `build/pricing-section`, `build/stretched-card`, `build/tailwind-button`, `build/vendor-datepicker`, `systems/brand-tokens` |

13 routing cases (one per skill), 10 boundary cases (5 pairs, both directions), 11 outcome cases in six areas; `test_evals.py` pins these counts, the fields, the grader options, every regex against its samples, the scaffolds and the fixtures' clean audit, and runs the router hook on every prompt. Uncovered pairs and skills: OPS-5.

## Secrets, variables and permissions

| Item | Value | Used by |
|---|---|---|
| `ANTHROPIC_API_KEY` (secret, set 2026-10-10) | — | `evals.yml:71`, the `Run the suite` step's env only; checked non-empty before any run (`:75-78`) |
| `DIST_DEPLOY_KEY` (secret, set 2026-10-19) | the private half of deploy key 166961999 | `release.yml:102`, the `Commit it…` step's env only; written to a 0600 file, used through `GIT_SSH_COMMAND` with `IdentitiesOnly`, `StrictHostKeyChecking=yes` and a pinned `known_hosts`, removed after the push (`:109-115, 142`) |
| `github.token` | — | `release.yml:62`, `GH_TOKEN` on `Create the release` only; `checkout` keeps no credential (`persist-credentials: false`, `:30, 91`, `evals.yml:45`) |
| Variables | none (`gh variable list` empty) | — |
| Deploy key 166961999 on pro-web-design-suite | `read_only: false`, title "release.yml distribute (Pro-Web-Designer-Suite-Plug-in)", created 2026-10-19 | the only key on that repository |
| `ci.yml` `permissions` | `contents: read` (workflow level, `:17-18`); no secret; runs on `push: main`, `pull_request`, `workflow_dispatch` | — |
| `release.yml` `permissions` | `contents: write` at the workflow level (`:11-12`, the `release` job needs it to create the release); `distribute` narrows to `contents: read` (`:77-78`) | — |
| `evals.yml` `permissions` | `contents: read` (`:31-32`); `setup-node` caches nothing (`:51`) | — |
| `pull_request_target` | used nowhere | — |
| Actions pinning | `ci.yml` by tag (`checkout@v7`, `setup-node@v7`, `cache/restore@v6`, `cache/save@v6`, `setup-uv@v10.2.0`); `release.yml` and `evals.yml` by SHA with version comments (`test_evals.py:511-518` asserts it for evals) | OPS-9 |
| Repository security settings | secret scanning, push protection and Dependabot security updates disabled; vulnerability alerts enabled, 0 open | OPS-10 |

## What is covered well

The release pipeline is the strongest part of the ops: one creator (`release.yml`), the tag checked against `plugin.json`, a deterministic builder that refuses what the directory blocks and prints what it holds, 15 assets that match the distribution tree hash for hash, a distribution job that is fast-forward-only, atomic, refuses an existing or older tag, trusts no host on first use, holds one write-scoped deploy key in one step, and reruns clean after the upload 404 that 4.0.1 hit. The eval suite is small but disciplined: free tests pin every case's shape and every regex's behaviour, the cost ceiling is enforced and shared, no case can run a shell, the key reaches one step and the trigger is manual only. CI runs the whole suite on six OS × Python legs with `-B`, runs the pointer, snippet, rules, plan and audit checks that `check.py` runs locally (and `test_caniemail` covers `sync_caniemail --check` inside the suite), validates the plugin, the marketplace and the built distribution tree on every PR, and keeps `contents: read` with no secret in reach of a fork.
