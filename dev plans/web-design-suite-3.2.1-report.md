# web-design-suite 3.2.1: distribution-readiness report

**2026-09-25.** The plugin moved into its own repository, and items 1–3 of the distribution checklist were done there. The plugin installed on this machine is now 3.2.1. The [completion plan](web-design-suite-completion-plan.md) covers everything left.

## Summary

- **The repository.** [Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in](https://github.com/Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in) is private; its local clone is `C:\DEV\Pro-Web-Designer-Suite-Plug-in`.
  - `main` has the four releases 3.0.0 to 3.2.0 as tagged commits. Each was checked to equal the one before plus its `.patch`.
  - The plugin is in `plugins/web-design-suite`, the repository root is a marketplace, and the project docs are in `dev plans`.
  - 3.2.1 is [PR #1](https://github.com/Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in/pull/1). It was reviewed before it merged (see *The review before release*); tag `v3.2.1` after the merge.
- **1. No machine paths.** The 3.0.1 CHANGELOG entry named a report by its folder on the maintainer's machine. A test now scans every shipped file for such paths.
- **2. The lint configs, run for real.** stylelint 17.15 and eslint-plugin-tailwindcss 4.4 and 3.18 ran the shipped configs for the first time. They found three bugs, and all three are fixed:
  - The stylelint config refused the plugin's own starter stylesheets 32 times, and refused the documented Tailwind entry.
  - The Tailwind v3 block of the ESLint config stopped ESLint with "Could not resolve tailwindcss".
  - Both Tailwind blocks gave `p-card px-inline-md` as a contradiction, and neither plugin flags it.
- **3. The Python floor.** Python 3.10 or newer, verified by the final suite (339 tests) on each of 3.10 to 3.14. On 3.9 the test harness fails (`ignore_cleanup_errors` is 3.10+). Every script compiles on 3.9, but that does not make it supported.
- **Tests.** 296 → 339: 21 for items 1–3, 15 more from the review, 6 from CodeRabbit's second review, and 1 from its third. Inside the repository, `npm ci` in `tooling/main` and `tooling/tailwind-v3` provides every tool the tests use but the browser, at pinned versions.

## Where everything is

| What | Where |
|---|---|
| The installed plugin, which sessions load | `C:\Users\vybec\.claude\local-marketplaces\web-design-suite`: `claude plugin update` moved it from 3.2.0 to 3.2.1 |
| Package | `C:\Users\vybec\Downloads\web-design-suite-plugin-3.2.1.zip`: 225 entries, 1,568,691 bytes, SHA-256 `abd86e9a55529f743d82d1f41cae3413621586d3c2b97753001a421678b71adf` |
| What changed since 3.2.0 | `git diff v3.2.0 fix/3.2.1-distribution-readiness -- plugins`. There are no more `.patch` files: the tags hold the history |
| Release notes | `plugins/web-design-suite/CHANGELOG.md` |
| Test tools | `tooling/` and its README |
| Everything left | [web-design-suite-completion-plan.md](web-design-suite-completion-plan.md) and [the inventory](web-design-suite-completion-inventory.md) |

## What running the real tools found

- **stylelint**, on the starter's four stylesheets:
  - The config had no room for `Highlight` in forced-colors mode or for `100svb`. Both are allowed now, and the system colours only inside the forced-colors query.
  - Three layout primitives computed a box inline (`calc(var(--center-max) + var(--center-gutter) * 2)`). They route it through a socket now, as layout.css already did elsewhere.
  - It inherited a formatting rule that refused layout.css's one-line modifier tables.
  - Its inherited `url()` import notation refused the Tailwind entry. The references spell imports both ways, so the rule is now off.
  - The starter's documented one-offs, the focus ring's gap and tokens.css's per-section `:root` blocks carry stylelint disable comments that give the reason.
  - For a component file, two things are newly allowed: a system colour inside `@media (forced-colors: active)`, and `100svb`/`100svh`/`100dvb`. Nothing else loosened. (The first version of this release said nothing loosened while it did; see the review.)
- **eslint-plugin-tailwindcss 3.18** looks for tailwindcss from the config's folder and cannot start from a relative path, so the v3 block now gives an absolute path, anchored at the nearest `package.json` above the config: ESLint 10 loads a config from whichever folder it lints.
- **Both plugins** flag `p-card p-card-lg` but not `p-card px-inline-md`: Tailwind emits the longhand after the shorthand in v4 and v3 alike (measured). The examples in the comments now say so.
- **Not fixed here, measured for the plan:**
  - The audit and stylelint disagree on six constructs, among them a factor on a spacing token, `em` type and `ch` widths (plan, W2 N1).
  - 56 of the references' 170 CSS snippet files fail the stylelint config (plan, W2 N3).

## The review before release

3.2.1 was reviewed before it merged: ten finder angles over the PR (line by line, removed behaviour, cross-file, language pitfalls, derived configs, reuse, simplification, efficiency, altitude, CLAUDE.md conventions), each candidate checked by a verifier with the real tools, then a gap sweep; and CodeRabbit's full review. They found 31 distinct problems. 30 were confirmed and fixed here. One was refuted: the p-card note that each Part 5 block repeats is load-bearing, because each block is copied on its own and the tests read its examples from it.

**What the review found in 3.2.1 as first written:**
- **stylelint.** The fifth override, for layout files, sat after the component override and replaced its allowlist, so a component in a `layout/` folder (`src/components/layout/Header.css`, `packages/ui/layout.css`) lost Law 2, while the audit still refused the margin. Its geometry regex backtracked exponentially: a 10-decimal value took 26–30 s in stylelint, a 24-digit run 76 s, a JS float hours. It also let a layout file multiply a token by any number (`* 1.5`, an invented step), and switched off two rules for the whole class for reasons that were not what fired. System colours were allowed in every colour property of every file, and only in PascalCase; a hand-built box-shadow ring was allowed in components; and token files lost `no-duplicate-selectors` for every selector.
- **ESLint Part 5.** The v3 path was resolved from wherever ESLint runs; ESLint 10 loads a config from each linted file's folder, so a run from a monorepo root crashed ("Cannot find module …tailwind.config.ts") or linted against the wrong theme. Both blocks reported every class of the starter's own CSS (`stack`, `cluster`: 13 errors on the documented primitives, 39 on `scaffold_ui`'s output), and the deleted caveat was still needed. The v3 whitelist listed utilities the plugin already learns from the config, and `motion-.*` hid typos of them. The v4 `functions` list was untested, because the fixture used `cn`, a default.
- **Tests and tools.** The machine-path scan missed Windows paths as JSON and source code write them, and WSL paths. `ast.parse(feature_version=)` let a PEP 701 f-string pass that 3.10 refuses. The tool defaults were written into `os.environ`, so every script under test saw them; "an empty value switches the tests off" could not be done from cmd.exe or PowerShell, and `NODE_PATH` turned them back on; a Windows `node_modules` would have been used from WSL. Results were keyed by paths that differ on macOS (`/var` and `/private/var`); a relative tool path broke under `cwd=tmp`; fixtures were written CRLF. The zip builder packed untracked files, took modes from the previous zip (so N5's executable bits could never ship), refused deletions, was not reproducible, and exited 0 when its own `testzip` failed.
- **Docs.** The Node floor ignored ESLint 10's gap (Node 21, 22.0–22.12 and 23 are out); the Upgrading note left out layout.css; this report said nothing loosened what a component may do; and the plan's N1 row 1, N5, the floor command and SB-A25's status were wrong.

**How it was fixed.** The fifth override is gone: layout.css derives its three computed boxes through sockets, as it did elsewhere, and marks the two rules the file trips with disable comments that give the real reasons. A new rule, `design/system-colors-in-forced-colors`, confines system colours to forced-colors mode, in any case. The reset's gap ring and tokens.css's two repeated `:root` blocks carry disable comments; the component ring is refused again. Part 5 anchors the v3 path at the nearest `package.json` above the config and whitelists the starter's classes in `ownClasses`, which a test keeps in step with layout.css. The harness has one resolver (`tool_roots`, `tool_modules`) with `off` as the switch. The floor interpreter compiles every script and runs every `--help`. The builder reads git.

**Fail-before.** The final suite, run against this PR's first head (`8b27ff7`) through `WDS_PLUGIN_ROOT`, ran 319 tests in 502 s: **FAILED (failures=4, errors=2)**, as intended.
- `StylelintConfig` could not set up: on the 30-digit fixture, stylelint ran into the test's 300 s timeout (the geometry regex).
- `TailwindPluginV3` could not load: "Cannot find module …	ailwind.config.ts", with ESLint run from the folder above the project.
- Failed: the v4 block reported the starter's own classes; five file-class overrides instead of four; no rule scoping the system colours; no `ownClasses` to cover layout.css.
- With the 30-digit fixture left out, the stylelint class runs on `8b27ff7`, and 8 of its subtests fail: both layout-folder components, the layout factor, the component ring, the duplicate dark block, the two system colours outside forced-colors mode, and `highlight` in lower case inside it.
- The zip builder's 3 new tests fail against `8b27ff7`'s builder.
- Guards that pass on both: the starter and the documented entries, the refusals and allowances that already held, the machine-path pattern check and the harness tests (they test the test code), and the floor interpreter (the scripts ran on 3.10 before too).

**CodeRabbit's second review**, of those fixes at `00fb5f2`, raised four more points and kept one open. All five are fixed.
- **Git's repository variables.** Inherited from a git hook or a shell, `GIT_DIR` and the like pointed the builder at another repository, and the tests' git commands too: 19 test subprocesses got no environment of their own, and the hook tests built theirs from `os.environ`. Run with `GIT_DIR` set to a scratch repository, `00fb5f2`'s hook test passed and left `components/card.css` staged in that repository's index. The builder now drops the variables `git rev-parse --local-env-vars` names and runs git from the repository's top folder. `env()` drops them for every test subprocess, every call passes it, and a test holds both.
- **What the zip leaves out.** The builder skipped a tracked symbolic link, and a file that `export-ignore` keeps out of `git archive`, and still reported success. It now checks what it packed against `git ls-tree` and refuses, writing nothing.
- **The plan.** N6 and the handoff still asked for decision 2, which was made; the rule on two Python versions gave no command for 3.14; and the zip check compared a folder with an archive stream.

Against `00fb5f2`, the 6 new tests fail (5 failures, 1 error): the 3 builder tests against its builder, and the 3 harness tests against its harness, with the new test files placed beside it. With the fix, the same scratch repository's index stays empty through the hook and migration tests.

**CodeRabbit's third review**, at `ee1b050`, raised two points. Both are fixed.
- **Executable bits.** The builder took each file's mode from the tar that `git archive` writes, and git's `tar.umask` setting masks those bits: with `tar.umask=0111`, a script git tracks as `100755` went into the zip as 0644. The builder now takes the mode from `git ls-tree`, the list it already checks the zip against.
- **The zip check.** The zip unpacks to `web-design-suite/`, but `git archive` of the plugin unpacks to `plugins/web-design-suite/`, so step 4's `diff -r` compared different roots. Step 4, the plan's fail-before rule and CLAUDE.md now extract with `tar --strip-components=1`, which Windows' `tar.exe` and Git Bash's tar both accept.

Against `ee1b050`'s builder, the new test fails (the script comes out as `0o100644`); with the fix, it passes.

## Evidence

### Test runs

Each run was from `plugins/web-design-suite`, with `PYTHONDONTWRITEBYTECODE=1` and the repository's toolchain. Nothing was borrowed from other projects this time.

| Run | Python | Result |
|---|---|---|
| `python -B -m unittest discover -s tests`, the final suite | 3.14.5 | Ran 339 tests in 276.6 s: **OK** |
| The same | 3.13.9 | Ran 339 tests in 318.7 s: **OK** |
| The same | 3.12.12 | Ran 339 tests in 319.5 s: **OK** |
| The same | 3.11.15 | Ran 339 tests in 285.5 s: **OK** |
| The same | 3.10.20 (the floor) | Ran 339 tests in 294.5 s: **OK** |
| With `WDS_PLUGIN_ROOT` set to `8b27ff7`, the review's fail-before | 3.14.5 | Ran 319 tests in 502.0 s: **FAILED (failures=4, errors=2)**, as intended |
| CodeRabbit's second review: the new test files beside `00fb5f2`'s builder and harness | 3.14.5 | Ran 14 tests: **FAILED (failures=5, errors=1)**, as intended |
| CodeRabbit's third review: the builder test file against `ee1b050`'s builder | 3.14.5 | Ran 7 tests: **FAILED (failures=1)**, as intended |
| Linux: WSL2 Ubuntu, dash as `/bin/sh` | 3.14.4 | Ran 339 tests in 181.3 s: **OK**, 59 skipped (no Node there, and no floor interpreter or toolchain for Linux) |
| Before CodeRabbit's third review: 338 tests | 3.10.20 to 3.14.5, and Linux | **OK** on each (Linux: 59 skipped) |
| Before CodeRabbit's second review: 332 tests | 3.10.20 to 3.14.5, and Linux | **OK** on each (Linux: 59 skipped) |
| Before the review: 317 tests | 3.14.5, 3.12.10, 3.10.20 | **OK** in 172.3, 199.5 and 201.5 s |
| Before the review: with `WDS_PLUGIN_ROOT` set to an unpacked 3.2.0 | 3.14.5 | Ran 309 tests in 183.2 s: **FAILED (failures=13, errors=1, skipped=1)**, as intended |

The final 3.14, 3.10 and 3.11 runs went side by side, then 3.12, 3.13 and Linux together. The first Linux run of the final suite failed one new test: git on Linux reads file modes from the disk, so the zip test's `git add` put 0644 back over the `+x` it had staged. The test now makes the file executable on disk as well.

Against 3.2.0:
- 14 of the 21 new tests fail, eight of them because the v3 class cannot even load.
- 6 pass on both versions. They are guards: the refusal fixtures, the 3.10 grammar parse, and four v4-plugin checks that already held.
- 1 skips on 3.2.0: its fixture is the non-conflict example that only the corrected comment gives.
- 2 of 3.2.0's own tests fail there, as expected. `test_file_globs` changed for the new layout class, and the pointer register records the one new pointer.

The first run with the toolchain at the repository root failed 16 browser-resolution tests. Node looks for packages in every parent folder, so the real Playwright above the plugin replaced the stub modules the tests plant. The toolchain now sits beside the plugin in `tooling/`, and `tooling/README.md` says why.

### Other checks

- `claude plugin validate --strict` (bundled CLI 2.1.281) passed three times: for the repository root's marketplace, for the plugin folder, and for `plugin.json`.
- `audit_design.py skills --strict`: clean, L1–L6, across 13 files.
- **Zip.** Built by `tooling/release/build_zip.py` with the 3.2.0 zip's layout; `testzip` OK. Extracted, then `diff -r` against the plugin folder: no differences.
- **Install.** `diff -r` finds the installed copy identical to the repository's plugin. `claude plugin update` moved it from 3.2.0 to 3.2.1, and the cache under `~/.claude/plugins/cache` now matches it, so the stale cache the 3.2.0 report noted is gone.
- **Repository import.** 3.0.0 plus `3.0.0-to-3.0.1.patch` equals the 3.0.1 zip, and the same holds for each later step. The 3.2.0 zip equals the installed 3.2.0. The same nine executable files as in the zips are marked executable in git, and every text file is stored with LF.

## What was not tested

- **macOS.** Nothing has run there (plan, W9).
- **The v3 plugin on older lines.** Only eslint-plugin-tailwindcss 3.18.3 on ESLint 10.11 ran; older 3.x releases and ESLint 9 did not.
- **Browser and real-tool tests on Linux.** That WSL has no Node.
- **The references' CSS.** It was measured against stylelint, not fixed (plan, W2).
