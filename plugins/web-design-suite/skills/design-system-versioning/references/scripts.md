# The two scripts, in full

Every argument of `diff_system.py` and `deprecate.py`. `SKILL.md` has the workflow; this is the reference behind it.

## 1. `scripts/diff_system.py` — stdlib Python 3, no dependencies

| Flag | Does |
|---|---|
| `old` `new` | two snapshots: `system.json`, `tokens.css`, a `contract.json`, or a directory containing one. Without `old`, the published snapshot the project's `.design-suite.json` names (`baselines.system`); without `new`, the token files it lists (web-design-studio's `references/project-contract.md`) |
| `--format report\|json\|changelog\|migration-guide` | output shape (default `report`) |
| `-o FILE` | write there instead of stdout |
| `--from-version X.Y.Z` | the version `old` shipped as; yields a real recommended version |
| `--project NAME` · `--date YYYY-MM-DD` | used by the changelog and guide |
| `--deprecations FILE` | the ledger; makes the gate binding |
| `--gate names\|major\|none` | `names` (default): a vanished name with no record fails |
| `--mapping PATH` | the codemod path quoted in the migration guide |
| `--no-contrast` | skip the contrast pass |
| `--no-upstream` | use the vendored token parser even when `design-system-docs` is reachable |
| `--color-impl PATH` / `--check-color-impl` | bind to, or verify against, the studio's colour maths |

Exit `0` clean · `1` the gate fired · `2` bad invocation.

**On the contrast column:** it uses the OKLab/WCAG functions from `web-design-studio/scripts/generate_color_ramp.py`, imported directly when the suite is installed whole and vendored byte-identically otherwise, with `--check-color-impl` proving the two agree on six probe pairs. Ratios are computed from the resolved OKLCH text, never from the 8-bit hex — quantising first reports 4.91:1 where the ramp generator reports 4.92:1, and a suite whose tools disagree in the second decimal is a suite nobody quotes.

**On a `contract.json`:** design-system-docs' `extract_system.py --contract` writes it, the default value and tier of every token. It holds no themes, densities, conditions, notes, layers or components, so when either snapshot is one, the other is cut down to the same before the diff: the default values and tiers are compared, and the report says so. A contract diffed against the `tokens.css` it came from has no changes.

**On reading `tokens.css` directly:** `design-system-docs`' extractor is imported and run in-process when it is reachable, so there is one tier classifier and one resolver in the suite rather than two. The vendored fallback exists so the skill works standalone, and it produces identical classifications on the canonical token file.

---

## 2. `scripts/deprecate.py` — stdlib Python 3, no dependencies

| Command | Does |
|---|---|
| `add` | record a deprecation, inject the marker, emit the codemod |
| `status [--version X.Y.Z]` | what is pending, what is due, what is still in use |
| `scan REPO…` | actual usage across consumer repos, per call site, labelled `codemod` or `manual` |
| `mapping [-o FILE]` | re-emit the whole ledger's `mapping.json` |
| `retire --name NAME` | mark it removed; refuses while the last scan shows usage |

| `add` flag | Does |
|---|---|
| `--name` `--kind` | the subject; `token` · `socket` · `component` · `variant` · `state` · `prop` · `theme` · `repoint` |
| `--since` `--removal` | the promise. A removal less than a minor version away is refused |
| `--replacement` | what to use instead; omit when there is no one-to-one |
| `--reason` `--notes` | why, and what the codemod will not do for them |
| `--codemod auto\|mechanical\|manual\|none` | `auto` is mechanical when a replacement exists |
| `--source FILE` | inject the marker here (repeatable); idempotent |
| `--mapping FILE` | write the ledger's codemod mapping |
| `--force` · `--dry-run` | override the window check · write nothing |

| `scan` flag | Does |
|---|---|
| `--record` | write the counts into the ledger as evidence |
| `--fail-on-usage` | exit 1 if anything is still in use |
| `--limit N` · `--format report\|json` | call sites printed per consumer · output shape |

Exit `0` fine · `1` something due is still in use, or `--fail-on-usage` found hits · `2` bad invocation.

**Option values that start with `--`.** Every subject this script takes is a CSS custom property, so `--name --fg-subtle` is the common case and argparse reads the value as another flag. Both `--name=--fg-subtle` and `--name --fg-subtle` work; the second is normalised before parsing, and only when the follower is not itself a known flag.

**On the emitted mapping.** `apply_codemod`'s per-slot pass deliberately skips any slot already containing `var(--` — its job is literals → tokens. So a token rename is emitted as declaration-scope rules, one per property; shadows go through the value scope, which has no such guard; component and variant renames use the tailwind scope, the one place the engine rewrites an identifier rather than a value. What that does not reach — socket defaults, shorthands, rules that also set a font property, tokens inside JS — is listed in `references/deprecation.md` §6, and `scan` labels every one of those call sites `manual` with the reason, so the honest list is generated from the consumer's real code rather than from memory.
