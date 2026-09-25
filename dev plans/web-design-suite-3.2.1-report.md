# web-design-suite 3.2.1: distribution-readiness report

**2026-09-25.** The plugin moved into its own repository, and items 1–3 of the distribution checklist were done there. The plugin installed on this machine is now 3.2.1. The [completion plan](web-design-suite-completion-plan.md) covers everything left.

## Summary

- **The repository.** [Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in](https://github.com/Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in) is private; its local clone is `C:\DEV\Pro-Web-Designer-Suite-Plug-in`.
  - `main` has the four releases 3.0.0 to 3.2.0 as tagged commits. Each was checked to equal the one before plus its `.patch`.
  - The plugin is in `plugins/web-design-suite`, the repository root is a marketplace, and the project docs are in `dev plans`.
  - 3.2.1 is [PR #1](https://github.com/Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in/pull/1). CodeRabbit reviews it. Tag `v3.2.1` after the merge.
- **1. No machine paths.** The 3.0.1 CHANGELOG entry named a report by its folder on the maintainer's machine. A test now scans every shipped file for such paths.
- **2. The lint configs, run for real.** stylelint 17.15 and eslint-plugin-tailwindcss 4.4 and 3.18 ran the shipped configs for the first time. They found three bugs, and all three are fixed:
  - The stylelint config refused the plugin's own starter stylesheets 32 times, and refused the documented Tailwind entry.
  - The Tailwind v3 block of the ESLint config stopped ESLint with "Could not resolve tailwindcss".
  - Both Tailwind blocks gave `p-card px-inline-md` as a contradiction, and neither plugin flags it.
- **3. The Python floor.** Python 3.10 or newer, verified by the full suite on 3.10 to 3.14. On 3.9 the test harness fails (`ignore_cleanup_errors` is 3.10+). Every script compiles on 3.9, but that does not make it supported.
- **Tests.** 296 → 317. Inside the repository, `npm ci` in `tooling/main` and `tooling/tailwind-v3` provides every tool the tests use, at pinned versions.

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
  - The config had no room for five things: the layout primitives' geometry over tokens (`calc(var(--center-max) + var(--center-gutter) * 2)`), the focus ring's gap, `Highlight` in forced-colors mode, `100svb`, and one `:root` block per token tier.
  - It inherited a formatting rule that refused layout.css's one-line modifier tables.
  - Its inherited `url()` import notation refused the Tailwind entry. The references spell imports both ways, so the rule is now off.
  - The starter's documented one-offs carried only the audit's ignore comment, so they now carry stylelint's too.
  - None of this loosened what a component file may do. The layout exemption is a fifth documented override, and `design-rules.json` records it as a file class.
- **eslint-plugin-tailwindcss 3.18** looks for tailwindcss from the config's folder and cannot start from a relative path, so the v3 block now uses `path.resolve('tailwind.config.ts')`.
- **Both plugins** flag `p-card p-card-lg` but not `p-card px-inline-md`: Tailwind emits the longhand after the shorthand in v4 and v3 alike (measured). The examples in the comments now say so.
- **Not fixed here, measured for the plan:**
  - The audit and stylelint disagree on six constructs, among them a factor on a spacing token, `em` type and `ch` widths (plan, W2 N1).
  - 56 of the references' 170 CSS snippet files fail the stylelint config (plan, W2 N3).

## Evidence

### Test runs

Each run was from `plugins/web-design-suite`, with `PYTHONDONTWRITEBYTECODE=1` and the repository's toolchain. Nothing was borrowed from other projects this time.

| Run | Python | Result |
|---|---|---|
| `python -m unittest discover -s tests` | 3.14.5 | Ran 317 tests in 172.3 s: **OK** |
| The same | 3.12.10 | Ran 317 tests in 199.5 s: **OK** |
| The same | 3.10.20 (the floor) | Ran 317 tests in 201.5 s: **OK** |
| With `WDS_PLUGIN_ROOT` set to an unpacked 3.2.0 | 3.14.5 | Ran 309 tests in 183.2 s: **FAILED (failures=13, errors=1, skipped=1)**, as intended |
| Linux: WSL2 Ubuntu, dash as `/bin/sh` | 3.14.4 | Ran 317 tests in 114.3 s: **OK**, 55 skipped (no Node there) |

3.14 and 3.10 ran side by side, then 3.12 and the 3.2.0 run. Earlier the same day, 3.11.15 and 3.13.9 ran the suite before item 2's changes: 296 tests, OK.

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
