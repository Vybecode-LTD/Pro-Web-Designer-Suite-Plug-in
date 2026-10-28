# DOC-C: plugin-level documents, manifests, agents and workflow commands

Audited 2026-10-28 at main 8441ff0. Files read in full: `README.md`, `LICENSE`, `.gitattributes`, `.gitignore`, `.coderabbit.yaml`, `CLAUDE.md`, `.github/` (listed: only `assets/readme/*.svg` and `workflows/*.yml`; no templates, CODEOWNERS, FUNDING or SECURITY), `docs/` (listed: only `HANDOFF.md`, not read), `tooling/README.md`, `.claude-plugin/marketplace.json`; in the plugin: `README.md`, `CHANGELOG.md` (headers, lines 1-162, 1191-1240, 1722-1800), `CHANGELOG-earlier.md` (headers, head, the seven flagged contexts), `SECURITY.md`, `LICENSE`, `.gitattributes`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.mcp.json`, `hooks/hooks.json`, `agents/*.md` (six), `workflow-commands/*/SKILL.md` (sixteen), `shared/token-contract.md`; `tests/test_agents.py` 28-66, `test_commands.py` 98-141, `test_docs.py` 395-445, `test_mcp.py` 25-84, and the class/test listings of `test_hooks.py`, `test_release_build.py`; the distribution repository's README (decoded from `gh api`), `plugin.json`, `marketplace.json` and `SECURITY.md`; Claude Code's docs pages plugins-reference, sub-agents, skills, plugins/marketplace-reference, plugins/components, hooks, and claude.com/docs/plugins/platform-support.

Commands run: `git rev-parse`, `ls`/`find` over the tree, `cmp` of the 13 contract copies, `grep -rhoE '^\s+def test_' tests/*.py | wc -l` (1653) and `unittest` discovery (1658), `git ls-tree -r` at `v4.0.0`, `v4.0.1`, `a7b45ce` and `HEAD`, `git log -S` for two CHANGELOG lines, `git for-each-ref` tag dates, `python -B workflow-commands/*/scripts/*.py --help` (five), two scratchpad scripts checking every backticked test id in both CHANGELOGs against `tests/`, existence checks for 43 paths and 73 flags the agents and commands name, `claude plugin validate --strict` on the plugin folder, the repository root and `plugin.json` with the desktop app's bundled 2.1.308 (and the npx-cached 2.1.303), `gh api` (read-only) on both repositories: metadata, `branches/main/protection`, `rules/branches/main`, `community/profile`, `private-vulnerability-reporting`, `contents`, `git/trees/main?recursive=1`, `readme`; `gh pr view` on #162, #165, #167, #176, #187 and #207-#213; `gh release list/view`; `curl -I` on the homepage and the marketplace `$schema` URL.

## Summary

18 findings: 8 medium, 10 low. By class (counted from the headings): readme 5, manifest 3, stale 3, contradiction 2, public-face 2, changelog 1, frontmatter 1, security 1. No manifest error (all three `--strict` validations pass, with the directory checks, on 2.1.308), no missing file or flag behind any agent or command, no false statement in the disclosure.

The three that matter most: (1) the root README still marks `tw-probe` and the Tailwind v4 probe "*(4.0.0)*: on `main` but not yet in a release zip", while 4.0.0 and 4.0.1 are both released (`README.md:180,350,357`); (2) the project `CLAUDE.md` says private vulnerability reporting is on for the distribution repository (verified 2026-10-21) but the API says it is off there, and the development repository, where `SECURITY.md` sends reporters, has no root `SECURITY.md` so GitHub shows no policy; (3) three counts in shipped text are wrong: "Eight" skills run `audit_design.py` (nine declare it), the 4.0.0 entry's "221 files" (229 at the tag), and 4.0.1's date (2026-10-25 in the CHANGELOG, tagged and released 2026-10-26).

## Findings

### DOC-C-1 · medium · stale

- **Where:** `README.md:357` (markers at `README.md:180` and `README.md:350`)
- **What:** The root README says the *(4.0.0)* marker means unreleased work, but 4.0.0 and 4.0.1 are released.
- **Evidence:** Line 357: "*(4.0.0)* marks what's on `main` but not yet in a release zip: see the [CHANGELOG]". Line 180: "`tw-probe` ... *(4.0.0)*". Line 350: "*(The probe is 4.0.0.)*". `gh release list`: "Pro Web Design Suite 4.0.1 Latest v4.0.1 2026-10-26T13:24:43Z", "Pro Web Design Suite 4.0.0 v4.0.0 2026-10-24T20:48:32Z".
- **Effect:** A reader of the development repository's front page believes the Tailwind probe is not in any release.
- **Fix:** Delete the two markers and the sentence at 357, or turn the sentence into "*(4.0.0)* marks what arrived in 4.0.0".
- **Confidence:** confirmed

### DOC-C-2 · medium · contradiction

- **Where:** `plugins/pro-web-design-suite/CHANGELOG.md:99`
- **What:** The 4.0.1 section is dated a day before the tag and the release; 4.0.0's date matches its release, so the convention is the release date.
- **Evidence:** Line 99: "## 4.0.1 — 2026-10-25". `git for-each-ref`: "v4.0.1 2026-10-26 7d672d0"; `git log -1 v4.0.1`: "84f4a4f 2026-10-26 08:29:21 -0400"; release published 2026-10-26T13:24:43Z. The line was written in `74333f3 2026-10-25 14:37:27 -0400 fix(release): ship a listing icon before the directory submission (4.0.1)`. Line 121: "## 4.0.0 — 2026-10-24" against the release's 2026-10-24T20:48:32Z. The project `CLAUDE.md:17` says "tagged 2026-10-26".
- **Effect:** The shipped CHANGELOG and the GitHub release disagree on when 4.0.1 shipped.
- **Fix:** Date the section 2026-10-26, and date a section when the tag is pushed, not when the entry is written.
- **Confidence:** confirmed

### DOC-C-3 · medium · contradiction

- **Where:** `README.md:65`; `plugins/pro-web-design-suite/README.md:131-132`
- **What:** Both READMEs say eight skills run `audit_design.py` as their gate; nine skills declare it as a sibling dependency.
- **Evidence:** `README.md:65`: "Eight of them run web-design-studio's `audit_design.py` as their gate, so install **web-design-studio** beside any of them." `grep -l 'From sibling skills:.*audit_design.py' skills/*/SKILL.md | wc -l` → 9: a11y-audit-runner, client-presentation-builder, component-state-matrix, content-model-to-ui, design-critique-gate, design-system-docs, design-system-versioning, design-token-migration, landing-page-conversion (each at its `SKILL.md:20`).
- **Effect:** A user installing one `.skill` file counts on the wrong number; `landing-page-conversion` (`SKILL.md:223` runs `python -m scripts.audit_design`) is the likely one left out.
- **Fix:** "Nine of them", or name the one the count excludes and why.
- **Confidence:** likely

### DOC-C-4 · medium · stale

- **Where:** `plugins/pro-web-design-suite/CHANGELOG.md:152`
- **What:** The 4.0.0 entry's file counts are the counts of 2026-10-19, not of the 4.0.0 tag.
- **Evidence:** Line 151-152: "leave out the plugin's `tests/`, `evals/` and `tools/` (221 files where there were 477)". `git ls-tree -r v4.0.0 -- plugins/pro-web-design-suite` without those folders: 229 of 496. At `a7b45ce` (2026-10-19, where the line was written): 221 of 478. At `v4.0.1`: 230 (the project `CLAUDE.md:17`'s "230 files" is right; the distribution repository's `main` has 230 blobs).
- **Effect:** A reader checking the 4.0.0 release against the entry finds eight files unaccounted for.
- **Fix:** "229 files where there were 496", or drop the numbers from a permanent entry.
- **Confidence:** confirmed

### DOC-C-5 · medium · security

- **Where:** `CLAUDE.md:28` (the project's)
- **What:** The project map says private vulnerability reporting is on for the distribution repository; GitHub says it is off there and on for the development repository.
- **Evidence:** `CLAUDE.md:28`: "the repository, its write deploy key and `DIST_DEPLOY_KEY` are in place, and private vulnerability reporting is on (verified 2026-10-21)". `gh api repos/Vybecode-LTD/pro-web-design-suite/private-vulnerability-reporting` → `{"enabled":false}`; `.../Pro-Web-Designer-Suite-Plug-in/private-vulnerability-reporting` → `{"enabled":true}`. `SECURITY.md:5-7` sends reporters to the development repository's Security tab, which works.
- **Effect:** The documented route works; the claim about the repository the directory links as `repository` is false, and a reporter who opens that repository's Security tab finds no "Report a vulnerability" button, only the policy pointing elsewhere.
- **Fix:** Turn it on for `pro-web-design-suite` too (Settings → Code security), then correct the line; or correct the line to say which repository has it.
- **Confidence:** confirmed

### DOC-C-6 · medium · public-face

- **Where:** repository root (no `SECURITY.md`, `.github/SECURITY.md` or `docs/SECURITY.md`); `README.md:497`; `plugins/pro-web-design-suite/SECURITY.md:5-7`
- **What:** The development repository, the one both documents send security reports to, has no security policy where GitHub looks for one; the only `SECURITY.md` is inside `plugins/pro-web-design-suite/`.
- **Evidence:** `ls SECURITY.md .github/SECURITY.md docs/SECURITY.md` → all "No such file"; `gh api .../community/profile` → `"security_policy"` absent, every file null. `README.md:497`: "Report a security problem privately, as [SECURITY.md](plugins/pro-web-design-suite/SECURITY.md) says." The distribution repository has `SECURITY.md` at its root (its contents list) and so shows a policy.
- **Effect:** On github.com the development repository's Security tab shows "no security policy"; a reporter who arrives through the Security tab rather than the README has only the "Report a vulnerability" button, with no scope or supported-versions text.
- **Fix:** Add a two-line root `SECURITY.md` (or `.github/SECURITY.md`) that links to the plugin's.
- **Confidence:** confirmed

### DOC-C-7 · medium · public-face

- **Where:** both repositories' settings (not files)
- **What:** The development repository's About box is empty and neither repository has topics, branch protection, templates or push protection.
- **Evidence:** `gh api repos/Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in`: `"description":null,"homepage":null,"topics":[]`; the distribution repository: a description and `"homepage":"https://vybecod.ing"`, `"topics":[]`. `branches/main/protection` → "Branch not protected" (404) on both; `rules/branches/main` → `[]` on both. `community/profile` → `code_of_conduct`, `contributing`, `issue_template`, `pull_request_template` all null on both; `find .github -type f` lists only `assets/readme/*.svg` and `workflows/*.yml`; the distribution repository has no `.github` (404). `security_and_analysis` on both: `secret_scanning_push_protection` and `dependabot_security_updates` "disabled". The distribution repository has `has_issues: true` while `plugins/pro-web-design-suite/README.md:125` and `:348` say issues belong in the development repository. Social preview: not readable by API.
- **Effect:** Search and the directory's reviewer see a repository with no description or topics; a push to `main` is unguarded (the project's convention is PRs merged by Claude); a stray issue on the distribution repository has no watcher.
- **Fix:** Fill the About description, homepage and topics on the development repository and topics on the distribution one; add an issue template that redirects on the distribution repository or disable issues there; consider a ruleset on `main` requiring the CI check and a PR; turn on push protection.
- **Confidence:** confirmed

### DOC-C-8 · medium · stale

- **Where:** `CLAUDE.md:62` and `CLAUDE.md:74` (the project's); `plugins/pro-web-design-suite/tests/test_mcp.py:35`
- **What:** Neither path the project map gives for the desktop app's bundled CLI exists on this machine, and the suite's `find_claude()` globs the first of them, so the local `validate --strict` test skips.
- **Evidence:** `CLAUDE.md:62`: "use the desktop app's bundled CLI, `%APPDATA%\Claude\claude-code\<version>\<build>\claude.exe` (2.1.293's build folder is `83cb0bd7fed4`)"; `CLAUDE.md:74`: "Its bundled CLI is really in `C:\Users\vybec\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude-code\`". PowerShell `Get-ChildItem "$env:APPDATA\Claude\claude-code"` → nothing; `ls .../LocalCache/Roaming/Claude` → only `.user-data-left.claude_pzs8sxrjxfjjc`. `find` → `C:\Users\vybec\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\claude-code\2.1.304\aed62990b91e\claude.exe` and `...\2.1.308\c17a819afb40\claude.exe`. `test_mcp.py:35`: `glob("Claude/claude-code/*/*/claude.exe")` under `APPDATA`. The CLI on PATH is 2.1.160 (`claude --version`).
- **Effect:** `test_claude_plugin_validate_strict_passes` skips locally ("no claude CLI"); CI's `validate` job is the only guard (`test_mcp.py:62-74` pins that). An agent following the gotcha runs the 2.1.160 on PATH, which (per the docs) warns on the directory-listing fields and fails `--strict`.
- **Fix:** Put the `Claude-Data` path in both lines of `CLAUDE.md`, and let `find_claude()` also glob `%LOCALAPPDATA%/Claude-Data/*/claude-code/*/*/claude.exe`.
- **Confidence:** confirmed

### DOC-C-9 · low · manifest

- **Where:** `.claude-plugin/marketplace.json:2`; `plugins/pro-web-design-suite/.claude-plugin/marketplace.json:2`
- **What:** The `$schema` URL does not resolve.
- **Evidence:** `"$schema": "https://anthropic.com/claude-code/marketplace.schema.json"`; `curl -I` → 301 to `https://www.anthropic.com/claude-code/marketplace.schema.json` → 404 `text/html`. The marketplace reference: "`$schema` | JSON Schema URL for editor autocomplete. Ignored at load time".
- **Effect:** None at load; an editor that follows it gets an HTML 404 instead of a schema.
- **Fix:** Drop the key, or point it at a schema that exists.
- **Confidence:** confirmed

### DOC-C-10 · low · manifest

- **Where:** `.claude-plugin/marketplace.json:13,21-40` vs `plugins/pro-web-design-suite/.claude-plugin/plugin.json:5,26-53`
- **What:** The marketplace entry carries 18 keywords and a shorter description; `plugin.json` carries 26 and the long one. Claude Code shows the entry's values, so eight keywords in `plugin.json` are never shown in `/plugin`.
- **Evidence:** Set difference (plugin.json only): `color-system`, `crud-scaffolding`, `css-modules`, `keyboard-navigation`, `navigation-patterns`, `typography`, `visual-regression`, `wcag`; `descriptions equal: False`. The marketplace reference: "For a field you set on the entry, users see the entry's value, even when `plugin.json` sets a different one." `tests/test_docs.py:440-445` compares the entry with `plugin.json` for `license`, `homepage`, `author` only.
- **Effect:** `/plugin` search and the listing show the 18; the directory (reading `plugin.json`) shows the 26. Harmless, but two vocabularies drift unwatched.
- **Fix:** Decide one list and one description, or extend `test_the_marketplace_entry_names_the_plugin` to `keywords`.
- **Confidence:** confirmed

### DOC-C-11 · low · frontmatter

- **Where:** `workflow-commands/new-system/SKILL.md:5`, `deck/SKILL.md:5`, `release-check/SKILL.md:5`, `install-gate/SKILL.md:5`
- **What:** The `argument-hint` of four commands omits flags their script takes.
- **Evidence:** `new_system.py --help` has `--hue-shift`, `--gamut {srgb,p3}`, `--base`, `--snap-px`; the hint is `"BRAND [--out DIR] [--neutral-hue H] [--ratio R --dual-ratio R --fluid MIN MAX] [--force]"` (the body, line 22, names `--base` and `--snap-px`). `deck.py` and `release_check.py` take `--out DIR`; neither hint has it. `install_gate.py` takes `--force` and `--dry-run`, which the body uses (lines 16, 33); the hint lists `--dest --src --dist --build` only. The other twelve hints match their scripts' `--help`.
- **Effect:** The `/` menu's hint under-states what the user may pass.
- **Fix:** Add the missing flags, or state in the body that the hint is the common subset.
- **Confidence:** confirmed

### DOC-C-12 · low · changelog

- **Where:** `plugins/pro-web-design-suite/CHANGELOG-earlier.md:611,631,645,1358,1363,1404,1439`
- **What:** Seven test identifiers in the earlier CHANGELOG no longer exist in `tests/` (renamed since); every identifier in `CHANGELOG.md` exists.
- **Evidence:** See "CHANGELOG regression tests that do not exist" below. `CHANGELOG.md`: 102 backticked test identifiers checked, 0 missing; `CHANGELOG-earlier.md`: 118 checked, 7 missing.
- **Effect:** A reader of 3.3.0's and 3.2.x's entries cannot find the named test.
- **Fix:** Leave history as it is, or mark each "(since renamed)" once.
- **Confidence:** confirmed

### DOC-C-13 · low · readme

- **Where:** `plugins/pro-web-design-suite/README.md:293`; `shared/token-contract.md:74` (and its 13 copies); `CHANGELOG.md:19-22,82,101,106-110,114,437,902,1177`; `CHANGELOG-earlier.md:964,1886`
- **What:** The word "icon" occurs in shipped text outside `plugin.json` and image links. The listing icon is now `pro-web-design-suite-icon.png`, so none of these names its stem, and `build.py` matches the stem; but the directory's own rule is unknown and it held 4.0.1 for "label + icon" in a code span.
- **Evidence:** `README.md:293`: "`font-size: 1em` for an icon"; `token-contract.md:74`: "| `--gap-fused` | 4px | Two halves of one thing (icon + label) |"; `CHANGELOG.md:21`: "span said \"label + icon\" matched the icon by its file name"; `CHANGELOG.md:85-86`: "broader than the directory's own match, whose exact rule is unknown". `grep -rn 'pro-web-design-suite-icon'` outside `plugin.json` and `tests/` → nothing.
- **Effect:** A residual risk at the next directory check, not a defect: these are the lines to look at if it holds again.
- **Fix:** None required now. Keep the stem distinctive; never shorten it back to `icon`.
- **Confidence:** possible

### DOC-C-14 · low · readme

- **Where:** `README.md:478-484`; `plugins/pro-web-design-suite/README.md:115-127`
- **What:** Neither README tells a `web-design-suite` (3.x) user how to move to the renamed plugin; the only instructions are in the CHANGELOG.
- **Evidence:** `README.md:482`: "Update the marketplace with `/plugin marketplace update pro-web-design-suite`, update the plugin from `/plugin`, then start a new session." (a user from 3.x has the marketplace under the name `web-design-suite`). `CHANGELOG.md:135-141`: "the marketplace keeps the name it was added under, so an install from this repository becomes `pro-web-design-suite@web-design-suite` ... run `/plugin install pro-web-design-suite@web-design-suite` once."
- **Effect:** A 3.6.0 user reading the README's troubleshooting runs the wrong marketplace name.
- **Fix:** One Troubleshooting entry: "Installed before 4.0.0?" linking to the CHANGELOG's Renamed section.
- **Confidence:** confirmed

### DOC-C-15 · low · readme

- **Where:** `plugins/pro-web-design-suite/README.md:107`
- **What:** The disclosure's list of browser gates leaves out the email render, which also opens a page in Playwright.
- **Evidence:** Line 107: "**The browser gates** (accessibility, performance, the state matrix, the critique's screenshots) load the pages you name"; `workflow-commands/email-build/SKILL.md:31-33` runs `render_email.mjs` ("It needs `playwright` in the project"); `README.md:35` (root) counts "email rendering" among the gates that open a browser.
- **Effect:** The disclosure is not false (the render opens a local file, sends nothing), but the privacy page the directory links is the place every browser launch should be named.
- **Fix:** Add "the email render" to the parenthesis.
- **Confidence:** confirmed

### DOC-C-16 · low · readme

- **Where:** `README.md:35`
- **What:** The requirements table says the browser gates use Chromium, Chrome or Edge; the accessibility gate also runs Firefox and WebKit.
- **Evidence:** Line 35: "they use Playwright's own Chromium if it's installed, else your Chrome or Edge." Line 136: "in Chromium, Firefox or WebKit"; `a11y_runtime.mjs` has `--engine`; `CHANGELOG.md:47-55` (4.0.2) is about the Firefox/WebKit install hint.
- **Effect:** Two rows of the same page disagree.
- **Fix:** "Chromium by default (Playwright's, else your Chrome or Edge); the accessibility gate can also run Firefox or WebKit with `--engine`."
- **Confidence:** confirmed

### DOC-C-17 · low · readme

- **Where:** `README.md:203`; `plugins/pro-web-design-suite/README.md:205-208`
- **What:** The name a user types to call a subagent is given without the `@agent-` prefix.
- **Evidence:** `README.md:203`: "you can ask for one by name (`pro-web-design-suite:design-critic`)". The sub-agents reference: "Typed manually: `@agent-my-plugin:code-reviewer`."
- **Effect:** A user who types the bare id gets nothing; asking in prose works.
- **Fix:** "`@agent-pro-web-design-suite:design-critic`, or ask for it by name".
- **Confidence:** confirmed

### DOC-C-18 · low · manifest

- **Where:** `plugins/pro-web-design-suite/.claude-plugin/plugin.json:4,16`
- **What:** `main`'s `plugin.json` says 4.0.1 but differs from the released 4.0.1's: the icon field names a different file. The project's convention bumps `version` at the tag, so this is the expected state between releases; it is recorded because the same version now names two manifests, and `claude plugin validate` cannot tell them apart.
- **Evidence:** `diff` of the distribution repository's `plugin.json` (4.0.1, `4809e3f`) against `main`'s: only `>   "icon": "./.claude-plugin/pro-web-design-suite-icon.png",` (the released one has `./.claude-plugin/icon.png`, and the distribution's `.claude-plugin/` holds `icon.png`). `CHANGELOG.md:3`: "## 4.0.2 — unreleased"; the P60 entry at `CHANGELOG.md:19-22`.
- **Effect:** None for users (the directory tracks the distribution repository's `main`); a local install from the development repository at 4.0.1 would not be the released 4.0.1.
- **Fix:** None beyond releasing 4.0.2; if the convention ever changes, bump `version` in the same PR as a manifest change.
- **Confidence:** confirmed

## Claims vs measured

| Claim | Where | Measured | |
|---|---|---|---|
| 13 skills | `README.md:5,120`; plugin `README.md:3,25`; `plugin.json:5` | `ls skills` → 13 | ok |
| 16 commands | `README.md:5,159`; plugin `README.md:92` | 16 `workflow-commands/*/SKILL.md` | ok |
| 6 subagents | `README.md:5,201`; plugin `README.md:93` | 6 `agents/*.md` | ok |
| 5 gate tools (MCP) | `README.md:5,86,214`; plugin `README.md:104,211-213` | `mcp/design_gates.mjs:49-87`: audit_design, a11y_static, perf_audit, check_roles, diff_system | ok |
| about 1,600 tests | `CLAUDE.md:22` | 1653 `def test_`; 1658 discovered | ok |
| 23 routing cases, 11 outcome cases; "five pairs of sibling skills" | `CLAUDE.md:23`; plugin `README.md:328,336` | routing 13 + boundaries 10 = 23; build 4, systems 1, gates 1, lifecycle 2, persuasion 1, delivery 2 = 11 | ok |
| version 4.0.1 | `plugin.json:4`; plugin `README.md:247-249` | latest tag `v4.0.1` (84f4a4f); distribution `main` = `v4.0.1` = 4809e3f | ok (DOC-C-18) |
| 4.0.1 — 2026-10-25 | `CHANGELOG.md:99` | tag 2026-10-26, release 2026-10-26T13:24:43Z | **wrong** (DOC-C-2) |
| 4.0.0 — 2026-10-24 | `CHANGELOG.md:121` | release 2026-10-24T20:48:32Z | ok |
| 230 files in the distribution repository | `CLAUDE.md:17` | 230 blobs on its `main`; 230 shipped at `v4.0.1` | ok |
| "221 files where there were 477" | `CHANGELOG.md:152` | at `v4.0.0`: 229 of 496 (221 of 478 at a7b45ce, 2026-10-19) | **stale** (DOC-C-4) |
| "Eight of them run `audit_design.py`" | `README.md:65`; plugin `README.md:131` | 9 SKILL.md declare it | **wrong** (DOC-C-3) |
| 17 navigation patterns | `README.md:126`; plugin `README.md:29` | `navigation-patterns.md` §2.1-2.17 | ok |
| 18 spacing, 11 type, 5 leadings, 6 elevations, 6 durations, 8 z-indexes | `token-contract.md:13` | counted in the contract's own lists (42-44, 50, 51, 89, 61, 91) | ok |
| 7 states × 3 densities × 2 themes | plugin `README.md:32` | contract: seven states (101), density 0.875/1/1.125 (17) | ok |
| six `.mjs` scripts: five browser gates + `tw_probe.mjs` | plugin `README.md:234-235` | a11y_runtime, snapshot_matrix, critique_snapshots, render_email, measure_vitals, tw_probe (plus helper copies and two configs) | ok |
| contract byte-identical in all 13 | `README.md:155`; plugin `README.md:11`; contract line 3 | `cmp`: 13 of 13 identical to `shared/token-contract.md` | ok |
| release assets: zip, `SHA256SUMS`, one `.skill` per skill | `README.md:51,65` | v4.0.1: `pro-web-design-suite-4.0.1.zip`, `SHA256SUMS`, 13 `.skill` | ok |
| one commit per version in the distribution repository, from 4.0.0 | `README.md:47` | tags `v4.0.0` 28efdaa, `v4.0.1` 4809e3f = `main` | ok |
| install lines name the marketplace and plugin | `README.md:43-44`; plugin `README.md:121-122` | both `marketplace.json` `name` and entry `name` = `pro-web-design-suite`; `renames` maps the old id | ok |
| `privacyPolicyUrl` anchor exists in the distribution README | `plugin.json:15` | distribution README identical to plugin `README.md`; heading "What it runs, sends and stores" at line 99 → `#what-it-runs-sends-and-stores` | ok |
| `documentationUrl` `#readme`, `supportUrl` issues, `homepage` | `plugin.json:10-15` | README present at the distribution root; `has_issues: true` on the development repository; `https://vybecod.ing` → 200 | ok |
| the split between the two CHANGELOGs is explained and linked | `CHANGELOG.md:1798-1801`; `CHANGELOG-earlier.md:1-3` | both link the other; 137,280 and 142,470 bytes, under the 256 KiB named | ok |
| PR numbers in the CHANGELOG match merged PRs | `CHANGELOG.md:600,611,396,434,1124` | #187 "fix(install-gate): the workflow checks the role pairs", #176 "feat(content-model-to-ui): the scaffold writes Vue 3.5 components", #167 "docs: the 2026-10-17 session's handoff", #165 "feat: the runtime checks read through shadow roots", #162 "fix(docs): register the references' Baseline browser versions": all MERGED, each cited in a matching context | ok (5 of 5) |
| P60-P65 are #207-#213 | `CLAUDE.md:30` | `gh pr view` 207-213: titles name P60, P61, P62, P63, (211: handoff), P64, P65; all MERGED | ok |
| "A full run of both sets ... about $11 at list price" vs "the $15 a full run may cost" vs `ceiling=14` | plugin `README.md:342`; `CHANGELOG.md:1731,1762`; `evals.yml:90`; `CLAUDE.md:24` | three different quantities (an estimate, a bound, the ceiling); not contradictory, but a reader meets three figures | note |
| "Where it works" table (chat: skills and commands only; Cowork: subagents and hooks; MCP when local) | plugin `README.md:90-97` | claude.com platform-support table: Chat loads skills and commands, ignores agents, hooks and local MCP; Cowork loads all four, local MCP "when the Cowork session runs on your computer" | ok |

## The README's disclosure (what it says runs, sends and stores)

From `plugins/pro-web-design-suite/README.md:99-111`, which is the page `privacyPolicyUrl` points at (the distribution README is byte-identical):

- "Everything runs on your machine, and the plugin collects nothing." (101)
- **The hooks** "run `node hooks/design_hooks.mjs`. The router reads each prompt locally, to name the skill it needs. The design gate, the a11y gate, the token diff, the email build and the generated-file guard act only in a project whose `.design-suite.json` turns them on. The gates run the plugin's Python scripts on the file Claude just edited; the guard reads that file's first lines. The plugin's `design_hooks` option turns them all off." (103)
- **The MCP server**, "`gates`, is `node mcp/design_gates.mjs`, over stdio. Its five tools run the same scripts on your project." (104)
- **The scripts** "read the files and folders you give them, and write their reports, tokens, scaffolds and builds where you tell them: usually inside the project, or at an output path you choose. Some work in a temporary folder that they remove, such as the email hook's build (`wds-email-*` under the system's temp folder)." (105)
- **The network:** "the plugin connects only to addresses you give it, and only when you run the step that needs them." (106)
  - **The browser gates** "(accessibility, performance, the state matrix, the critique's screenshots) load the pages you name, through your own Playwright install, which they never download. A page can be on your machine or anywhere on the web, and `--urls` can name a sitemap, which they fetch to read its pages. The page then loads whatever it loads. For a signed-in audit, the `--storage-state` file's cookies and each `--header` go to the page's own origin. Nothing the gates measure is sent anywhere: the reports stay on disk." (107)
  - **`crux_check.py`** "sends a URL or origin to Google's Chrome UX Report API, with the key you set in `CRUX_API_KEY`." (108)
  - **figma-variables-sync** "shows a `curl` to Figma's REST API, with the token you set in `FIGMA_TOKEN`, for you to run." (109)
  - "The plugin stores neither key, and it has no server, telemetry or analytics of its own." (110)
- **`/install-gate`** "writes a CI workflow into your repository. That workflow runs in your CI, in Microsoft's Playwright image." (111)

For the code passes to check against: the network calls disclosed are exactly three kinds (browser gates loading named pages and sitemaps, with cookies and headers to that origin; `crux_check.py` to Google's CrUX API with `CRUX_API_KEY`; a Figma REST `curl` the user runs with `FIGMA_TOKEN`); the file writes disclosed are reports, tokens, scaffolds and builds at paths the user gives, a removed `wds-email-*` temp folder, and the CI workflow plus vendored scripts from `/install-gate`; the external tools disclosed are `node`, Python 3, the project's own Playwright (never downloaded) and axe-core, and Microsoft's Playwright image in CI. Not named: the email render as a browser launch (DOC-C-15), `tw_probe.mjs` loading the project's own `tailwindcss` (local, no network), and the ESLint/stylelint configs run by the pre-commit hook (local). `SECURITY.md:19-24` puts the same four things in scope (writes outside a given folder, hooks or tools running project-controlled code, injection or weakened RLS in a scaffold, `CRUX_API_KEY` reaching a log or another host).

## CHANGELOG regression tests that do not exist

Every identifier on a "Regression test(s):" line in `CHANGELOG.md` exists (10 on those lines; 102 backticked test identifiers in the file in all, 0 missing). In `CHANGELOG-earlier.md`, seven of 118 name tests that have since been renamed:

| Line | Identifier | What is missing |
|---|---|---|
| 611 | `test_browser_runtime.test_a_spinner_is_not_a_focus_ring` | no such method in `test_browser_runtime.py` |
| 631 | `test_browser_runtime.test_the_focus_ring_is_measured_at_each_density_the_page_declares` | no such method |
| 645 | `test_browser_runtime.test_a_best_practice_rule_is_a_warning` | no such method |
| 1358 | `test_rules_spec.test_sass` | no such method in `test_rules_spec.py` |
| 1363 | `test_sass_is_left_to_the_audit` | no module, class or method |
| 1404 | `test_layers` | no module, class or method |
| 1439 | `test_rules_spec.test_the_specs_data_is_written_into_the_gates` | no such method |

## Both repositories' public face

| Field | Development: `Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in` | Distribution: `Vybecode-LTD/pro-web-design-suite` |
|---|---|---|
| Visibility | public | public |
| Description | none | "Pro Web Design Suite, a Claude Code plugin: design tokens, measured WCAG contrast and gates that fail the build on drift. Released builds; development is in Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in." |
| Homepage | none | https://vybecod.ing |
| Topics | none | none |
| License (API) | MIT | MIT |
| Social preview | not readable by API | not readable by API |
| Issues / Discussions / Wiki | on / off / on | on / off / on |
| Default branch, protection, rulesets | `main`; none (404); `[]` | `main`; none (404); `[]` |
| Private vulnerability reporting | enabled | disabled |
| Secret scanning, push protection, Dependabot security updates | "disabled" (all) | "disabled" (all) |
| `SECURITY.md` where GitHub looks (root, `.github/`, `docs/`) | none (only `plugins/pro-web-design-suite/SECURITY.md`) | `SECURITY.md` at root, identical to the plugin's |
| CODEOWNERS, issue templates, PR template, CONTRIBUTING, CODE_OF_CONDUCT | none | none (no `.github/` at all) |
| README | the repository README (33 KB, with `.github/assets/readme/*.svg`) | the plugin README, byte-identical to `plugins/pro-web-design-suite/README.md` |
| Releases | 4.0.1 (latest, 2026-10-26), 4.0.0, 3.6.0, 3.5.0... with zip, `SHA256SUMS` and 13 `.skill` files | none (tags `v4.0.0` 28efdaa, `v4.0.1` 4809e3f; `main` = `v4.0.1`) |
| Open PRs | none; highest issue/PR number 214 | n/a |
| `.claude-plugin/` | `marketplace.json` (source `./plugins/pro-web-design-suite`) | `plugin.json` (4.0.1, icon `icon.png`), `marketplace.json` (source `./`, identical to the plugin-level copy), `icon.png` |

## What is covered well

- The manifests are valid: `claude plugin validate --strict` passes on the plugin folder, the repository root and `plugin.json` with 2.1.308 (the desktop app's bundled CLI) and 2.1.303, including the directory checks ("These checks found nothing to report"); CI runs the same three (`test_mcp.py:62-74` pins it). Every `plugin.json` key is one the manifest reference lists; `skills: ["./workflow-commands/"]` adds to the default scan, so the sixteen commands load as `/pro-web-design-suite:<name>` with `disable-model-invocation: true` (the skills reference confirms both); `userConfig.design_hooks` is read as `CLAUDE_PLUGIN_OPTION_DESIGN_HOOKS` (`design_hooks.mjs:419`), the form the docs give; `.mcp.json` is exec form with `${CLAUDE_PLUGIN_ROOT}`; `hooks.json`'s `description`, exec form and second-unit timeouts are all documented, and its three modes (`guard`, `gate`, `route`, `design_hooks.mjs:417`) cover the five hooks its description names (`gate` runs the audit, the a11y check, the token diff and the email build, lines 376-397).
- Every agent uses only documented frontmatter (`name`, `description`, `tools`, `skills`, `color`, `omitClaudeMd`), lists only real tools, none has Edit or Write, and each says when to use it; every script, reference and flag the six agents and sixteen commands name exists (43 paths, 73 flags checked), the five command scripts' `--help` match their SKILL.md bodies, and no file in the plugin references an agent or command under the old `web-design-suite:` prefix (only the four allowed forms, the rename note and `renames` keep it).
- The distribution README is byte-identical to the plugin's, so `privacyPolicyUrl`'s anchor and the CHANGELOG/SECURITY links resolve there; the plugin-level `marketplace.json` is identical to the distribution's; `SECURITY.md` is identical in both repositories; both LICENSE files read "Copyright (c) 2026 Big Haas / VybeCod.ing".
- The CHANGELOG is newest-first, every released section dated, the split explained and linked in both directions under the 256 KiB the directory allows, and all 102 test identifiers in the current file exist; the five PR numbers spot-checked match their merged titles.
- The suite already pins most of this: the six agents' fields and tools (`test_agents.py`), each command's frontmatter and that its body runs exactly what `allowed-tools` grants (`test_commands.py:108-139`), the two marketplace files' parity and the entry's `license`/`homepage`/`author` (`test_docs.py:395-445`), the README's install lines and every documented flag (`test_docs.py` `PasteableCommands`, `DocumentedFlags`), the hooks file's exec form and the opt-out option (`test_hooks.py:44-60`), and the release tree, the icon and the directory holds (`test_release_build.py`).
