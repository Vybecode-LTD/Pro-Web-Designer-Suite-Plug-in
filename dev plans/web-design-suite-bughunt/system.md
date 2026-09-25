# Bug hunt report — design-system-docs & design-system-versioning

Scope: `scripts/extract_system.py`, `build_docs.py` (design-system-docs); `scripts/diff_system.py`,
`deprecate.py` (design-system-versioning). Fixtures: the real `web-design-studio` starter
`tokens.css` plus two hand-written components (`button.css`, `card.css`) with sockets, variants,
states, and deliberate gaps (tier1-leak, unconsumed-socket, missing-state).

## Bugs

**SYS-1** · wrong-result / portability · `design-system-docs/scripts/extract_system.py:1732,1740` (also `:1442`) · high confidence
`system.json` is not OS-independent even though SKILL.md promises "deterministic … paths relative
to `--root`. Commit it." Two causes: (a) the `undocumented-component`/`orphan-doc` gap emitters
build `"where": str(prose_dir / "components" / f"{name}.md")` directly, skipping the `self.rel()`
helper (line 1440) every other path goes through — so they embed the **full local absolute path**
(e.g. `C:\Users\<user>\...\prose\components\card.md`) into the committed JSON and into the
*published* HTML (confirmed in `docs-site/index.html`'s gap list). (b) `self.rel()` itself returns
`str(Path(...))`, backslash-separated on Windows, forward-slash on Linux/WSL, so every `"file"`
field in the document differs between OSes. Repro: run
`python -m scripts.extract_system styles/ components/ --prose prose/ --root . --out a.json` on
Windows, then the same command via `wsl bash -c "... python3 -m scripts.extract_system ..."`
against the same tree; diff the two outputs — every token/component `file:` field flips separator,
and `orphan-doc`/`undocumented-component` `where` fields differ completely (`C:\Users\vybec\...
\card.md` vs `/mnt/c/Users/vybec/.../card.md`). Confirmed this does **not** flip
`build_docs.py --check`'s exit code (`diff_systems()` never compares `file`/`gaps`), but it makes
every regeneration of the committed baseline produce spurious full-file diffs, and it leaks the
generating machine's username/directory into a page meant for public hosting. Fix: route every
path through `self.rel()`, and have `rel()` return `.as_posix()` instead of `str(Path(...))`.

**SYS-2** · wrong-result · `design-system-versioning/scripts/deprecate.py:713-714` (`cmd_retire`) · high confidence
`deprecate retire` is documented (`references/deprecation.md:247`, worked example) as "refuses
outright unless you pass `--force`" when removal isn't proven safe. The actual check is
`usage = entry.get("usage") or {}; if usage.get("total") and not args.force: refuse`. A deprecation
that has **never been scanned at all** has `usage == {}`, so `usage.get("total")` is falsy and
retire proceeds silently with no warning and no `--force` needed — even though `status` itself
prints "NEVER SCANNED … Do not delete on the strength of the plan alone" for the exact same record.
Repro (from `design-system-versioning/`): `python -m scripts.deprecate --ledger dep.json add
--name=--fg-subtle --kind token --since 2.1.0 --removal 3.0.0 --replacement=--fg-faint --reason x`
then immediately `python -m scripts.deprecate --ledger dep.json retire --name=--fg-subtle` →
observed: `retired --fg-subtle …`, exit 0, ledger now has `"status": "removed"` with `"usage": {}`.
Contrast with the working path: run `scan <repo-that-still-uses-it> --record` first, then `retire`
without `--force` → correctly refused, exit 1, "was last seen 1 time(s) … pass --force". The gate
only distinguishes "confirmed 0 hits" from "in use"; it never distinguishes "confirmed 0 hits" from
"never checked", which is exactly the case the tool's own philosophy ("answer 'is it safe to
remove' with a scan, not a date") says should block. Fix: refuse (absent `--force`) whenever
`"scanned"`/`"total"` is missing from `usage`, not only when `total` is truthy.

**SYS-3** · crash · three sites, see below · high confidence
Real users (plain `cmd`/PowerShell, git hooks, CI) run Python on Windows with the cp1252 console
codepage, not UTF-8 (this harness's shell forces `PYTHONIOENCODING=utf-8`, masking it). Three
documented, everyday invocations crash with `UnicodeEncodeError` when `PYTHONIOENCODING` is unset,
because they `sys.stdout.write()`/`print()` raw non-cp1252 characters (`\u2192` "→") straight to the
default stream instead of the file paths, which correctly use `.write_text(encoding="utf-8")`:
  1. `design-system-docs/scripts/build_docs.py:1410` (`print(f"  {p}")` inside the `--check` report
     loop). Repro (from `design-system-docs/`, `$env:PYTHONIOENCODING` unset):
     `python -m scripts.build_docs new/system.json --baseline old/system.json --check` where the
     two snapshots differ by any token *value* (triggers `diff_systems()`'s
     `f"token changed …: {old} \u2192 {new}"` at build_docs.py:1190). Observed: traceback,
     `UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'`, only the header line and
     first finding reach the console before the crash — the rest of the drift report is lost.
  2. `design-system-versioning/scripts/diff_system.py:2182` (`sys.stdout.write(text)`, the
     no-`-o` branch). Repro: `python -m scripts.diff_system old.json new.json --format changelog`
     (no `-o`) or `--format migration-guide` — both build prose with a hardcoded "→"
     (diff_system.py:1818/1846/1877/1880/1893). Traceback, same `UnicodeEncodeError`. `--format
     report` and `--format json` happened not to crash on my fixtures (they use ASCII `->` in the
     one place tested), but they share the identical no-`-o` `sys.stdout.write(text)` path, so any
     "why"/note string containing "→" would crash them too.
  3. `design-system-docs/scripts/extract_system.py:1968` (`sys.stdout.write(text)`, default
     `--out -`). Repro: `python -m scripts.extract_system styles/ components/ --root .` (omit
     `--out`, its documented default is stdout) against any real `tokens.css` — crashes near the
     start of the JSON.
Fix: `sys.stdout.reconfigure(encoding="utf-8")` (or wrap stdout) at the top of each script's
`main()`, matching what the file-write paths already do.

**SYS-4** · wrong-result / broken-doc · `design-system-docs/scripts/build_docs.py:1289-1314` (`check_examples`) · high confidence
SKILL.md states plainly: "`--check` verifies that every `var(--x)` in an example still resolves and
every `.class` it styles is still a part the component publishes… A wrong example is worse than a
missing one." `check_examples()` only globs `prose.rglob("*.md")` (line 1298) and lints fenced
` ```css ` blocks found by `render_markdown`. A `components/<name>.example.html` override (the
mechanism SKILL.md's own workflow section documents for "replaces the generated example markup") is
a `.html` file, never matched by that glob, and is read verbatim via `read_prose()` /
`example_markup()` (build_docs.py:1034) with **no validation at all**, in both build and `--check`
modes. Repro (from `design-system-docs/`): put
`<button class="button" style="color: var(--this-token-does-not-exist)"><span
class="button__nonexistent-part">Click me</span></button>` in `prose/components/button.example.html`,
then run `python -m scripts.build_docs new/system.json --baseline old/system.json --prose prose/
--check`. Observed: exit 1 with one unrelated finding only (a deliberately wrong contrast claim in
another file) — the bogus token and the nonexistent part are never mentioned. A normal `--out` build
then renders `var(--this-token-does-not-exist)` and `button__nonexistent-part` verbatim into the
published `components.html` (confirmed present in all 8 rendered state/variant cells). Fix: have
`check_examples()` (and `--emit-examples`) also scan `components/*.example.html` files for
`var(--x)`/`.class` references, the same way `.md` fenced blocks are checked.

## Tested and OK

- `extract_system.py --report` correctly detects and labels `missing-state`, `tier1-leak`,
  `unconsumed-socket`, `orphan-token`, `theme-repoints-tier1`, `orphan-doc`, `undocumented-component`
  against the fixture; `--strict` semantics not separately re-tested beyond gap severities shown.
- `--check-color-impl` passes (agrees with `web-design-studio/generate_color_ramp.py` on 6 probe
  pairs) for both `extract_system.py` and `diff_system.py`.
- Independently hand-verified three WCAG numbers the tool reports: `--accent-600` vs white ≈ 4.92:1
  (OKLab→linear-sRGB by hand, got 4.922); `--fg-subtle` on `--bg-sunken` light = 4.60:1 and
  `--fg-subtle` on `--bg-canvas` dark = 8.22:1, both matching the *token file's own* numeric
  comments exactly.
- `build_docs.py` full site build (`--out`, `--prose`, `--emit-css`, `--emit-examples`, `--project`,
  no `--only`/`--no-examples` variance tested beyond a smoke check) produces well-formed HTML
  (custom parser: balanced tags, no duplicate `id`s) with all internal `href`/`#anchor` links
  resolving, across all 4 generated pages.
- `--check` drift flow: passes cleanly (byte-identical `fc.exe` diff) on an unchanged regeneration;
  correctly fails, with the exact SKILL.md worked-example numbers, after a token value edit
  (4.92:1 → 3.56:1 crossing flagged); correctly catches a deliberately wrong hand-typed contrast
  claim in prose (`9.99:1` vs measured `6.35`/`13.80`) while leaving a correct claim (`4.60:1`)
  silent; correctly flags a prose page for a deleted component (`orphan-doc`).
- `diff_system.py` classifications matched `references/change-classification.md` exactly across 9
  constructed variants: Tier-2 rename (major, gate fails) → same rename **with** an added-role +
  identical-value shim (minor, gate passes, exact match to SKILL.md's worked example); Tier-2
  re-point (major, contrast crossing 4.92→3.56 reproduced exactly); Tier-1 primitive value change
  (major, correct transitive blast radius `--bg-accent`/`--border-focus` direct,
  `--elevation-focus`/`--shadow-focus` transitive — exact match to SKILL.md's worked example);
  Tier-1 removal with zero real consumers vs. with real consumers (both major; blast radius
  correctly empty vs. populated); Tier-2 addition (minor); socket removed/added/default-changed
  (major/minor/major, matching the "socket default changed" = major rule). All 4 `--format` outputs
  (report/json/changelog/migration-guide) inspected and internally consistent for the same diff.
  `--gate names/major/none` all behave distinctly; `--no-contrast`/`--no-upstream` not separately
  verified beyond not crashing.
- `diff_system.py` is robust to the SYS-1 cross-OS noise: diffing a Windows-generated vs.
  WSL-generated `system.json` of the *identical* source reports zero changes (`0 major · 0 minor ·
  0 patch`), confirming its own comparator normalizes past path differences even though the raw
  JSON files are not byte-identical.
- `deprecate add`: both `--name=--fg-subtle` and `--name --fg-subtle` (space form) parse correctly;
  removal-window validation refuses `--removal` equal to or a patch-only step after `--since` (exit
  2, clear message), and `--force` overrides it; re-running `add` against an already-marked source
  is idempotent — updates the existing `@deprecated` comment in place rather than duplicating it.
- `deprecate scan`: correctly labels a plain `color: var(--x)` hit `codemod`, a shorthand
  (`border: 1px solid var(--x)`) hit `manual` ("`border` is not in the rule's property list"), and a
  JS string literal hit `manual` ("a token inside JS/markup …") — exactly matching the limits listed
  in `references/deprecation.md §6`. `--record`, `--fail-on-usage` (exit 1 on hits), `--limit 0`
  (truncates with an "… and N more" note, no crash), and both `report`/`json` formats all correct.
- `deprecate status`/`retire` interaction when usage **is** recorded: `status --version` correctly
  reports "STILL IN USE" (exit 1); `retire` without `--force` correctly refuses (exit 1) with the
  documented message; contrast this with the SYS-2 bug above.
- Cross-skill chaining: `deprecate add --mapping` emits a `design-token-migration/mapping@1` file
  that `apply_codemod.py --mapping` (dry run) loads and applies without error, correctly rewriting
  `color: var(--fg-subtle)` → `color: var(--fg-faint)` in a consumer fixture.
- Unicode + CRLF: a CRLF-terminated `tokens.css` with a unicode token name (`--café-fg`), a unicode
  + emoji comment, extracted and built end-to-end with no crash or mangling — the token id, note
  text and emoji all appear correctly in the generated HTML and its embedded search index JSON.
- Missing/empty inputs: an empty styles directory and a nonexistent path both produce a clean
  `exit 2` argparse-style error ("no token file found …"), not a crash or traceback.

## Could not test

- `--props` (TS/TSX prop-table extraction) in `extract_system.py` — my fixtures are CSS-only; the
  JSDoc/defaults/types extraction path (extraction.md §8) was not exercised.
- Node-based neighbors mentioned in the SKILL.md wiring examples (`snapshot_matrix.mjs`,
  `audit_design.py`'s own gates) — out of my assigned scope and WSL has no Node; only referenced
  read-only to check the mapping/codemod chain.
- `design-token-migration` internals beyond the one mapping-compatibility smoke test above (owned
  by another hunter).
- Full multi-consumer canary rollout procedure (`references/rollout.md`) — a process description,
  not independently scriptable in the time available.
- Ledger/scan behavior at scale (many deprecations, many consumer repos) — only 1-3 of each tested.
