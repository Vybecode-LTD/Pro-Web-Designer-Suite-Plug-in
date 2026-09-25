# design-token-migration bug hunt

`$SKILL` = `plugin\skills\design-token-migration` (run everything from here). `$FIX` = a messy
fixture built for this hunt: plain CSS, SCSS (vars/nesting/mixins/`darken()`), 2 CSS Modules,
styled-components, Tailwind arbitrary values in TSX, inline-style-heavy JSX, Bootstrap-style
`!important` overrides, near-dup greys/13-14-15px, hex/rgb/hsl/named colors, a CRLF file, a
non-ASCII-named+content file, a path with spaces — committed to git and migrated kind-by-kind
exactly per SKILL.md's worked example.

## Bugs

**MIG-1** · crash · `scripts/cluster_values.py:2373` (`sys.stdout.write(report)` in `main()`) ·
`--dry-run` crashes on any real Windows terminal (no `PYTHONIOENCODING`) whenever the
reconciliation report contains a "review" row or a contrast regression, because those sections
use `Δ` (U+0394) and `⚠` (U+26A0), neither representable in cp1252.
Repro (from `$SKILL`, `$env:PYTHONIOENCODING=$null`):
`python -m scripts.cluster_values $FIX\literals.json --dry-run`
Observed: `UnicodeEncodeError: 'charmap' codec can't encode character '⚠' in position 1193`,
traceback, exit 1. The non-dry-run path is fine (writes `reconciliation.md` with explicit
`encoding="utf-8"`) — only `--dry-run`'s stdout write is affected.
Fix: `sys.stdout.write(report)` → wrap with the same ASCII-safe fallback other CLIs use, or
`sys.stdout.buffer.write(report.encode(sys.stdout.encoding or "utf-8", "replace"))`.
Confidence: high.

**MIG-2** · wrong-result · `scripts/cluster_values.py:495` vs `:497` (`tw_prop_class`) · Tailwind
arbitrary `max-w-[…]`, `min-w-[…]`, `max-h-[…]`, `min-h-[…]` are misclassified as prop-class
`"gap"` (margin) instead of `"size"`, because `if prefix.startswith(("m","gap","space")): return
"gap"` fires first and `"max-w"`/`"min-w"`/`"min-h"`/`"max-h"` all start with `"m"` — the exact
`{"w","h","min-w","max-w","min-h","max-h"}` check on the next line is unreachable for them. A
value that snaps onto the *spacing* scale then gets a nonsense Tailwind class invented for a
`maxWidth`/`minHeight` utility.
Repro (from `$SKILL`): extract+cluster a TSX with `className="max-w-[16px] min-h-[16px]"`, then
`python -m scripts.apply_codemod $FIX\src\components\TailwindThing.tsx -m $FIX\proposal\mapping.json --kind spacing`
Observed diff: `max-w-[16px] min-h-[16px]` → `max-w-grouped min-h-grouped` (mapping.json:
`{"match":["max-w-[16px]"],"replacement":"max-w-grouped","token":"--gap-grouped","prop_classes":["gap"]}`).
`max-w-grouped`/`min-h-grouped` are not Tailwind utilities in any default or `--gap-*`-themed
config — this corrupts the class and silently breaks the element's sizing after `--apply`.
Also fragments reporting: `max-w-[1140px]` (CSS `max-width:1140px` = same decision) lands in a
different unmapped bucket than the Tailwind one, printing two separate "no home" entries instead
of merging them.
Fix: move the `{"w","h","min-w","max-w","min-h","max-h"}` check before the `startswith(("m",...))` check, or exclude `min-`/`max-` prefixes from the `m`-prefix branch.
Confidence: high.

**MIG-3** · wrong-result · `scripts/extract_literals.py:1000-1024` (`extract_js`, JSX inline-style
loop) · Every hex color written as a quoted string inside a JSX `style={{...}}` object is counted
**twice**: once correctly via `parse_style_object`/`literals_from_value` (context
`inline-style`), and again via the later "bare hex colors in JS strings" pass
(`JS_HEX_STRING_RE`), because — unlike the styled-components loop just above it, which calls
`claim(m.start(), ...)` — the JSX-style loop never marks its range consumed.
Repro (from `$SKILL`): a file with `style={{ color: "#3a3a3a" }}`, then
`python -m scripts.extract_literals <file> --format json -o out.json`, inspect entries where
`normalized=="#3a3a3a"`.
Observed: two literals at the *identical* file/line/col — `{"context":"inline-style","prop":"color",...}`
and `{"context":"js-string","prop":"",...}` — for one source token. In the full fixture this
inflated the "N literal value(s) across N file(s)" headline (the number SKILL.md says to lead
with when selling a migration: *"There are 1,431 hardcoded values..."*) and double-counted the
"a color constant in JavaScript" unmapped bucket.
Fix: call `claim(m.start(), end)` in the JSX-style loop the same way the styled-components loop
does, before the "bare hex colors in JS strings" pass runs.
Confidence: high.

**MIG-4** · wrong-result · `scripts/cluster_values.py` (`cluster_spacing`, `cluster_color_phase`,
etc. — no context filter) · Literals whose `context=="inline-style"` are pooled into the same
`css_items` bucket as real CSS/styled-components declarations and counted toward
"Mechanically replaceable" rules, but `apply_codemod.py`'s `plan_js()` **never** processes JSX
`style={{...}}` objects (by design, Law 4) — with no `Skip` entry or any other warning, the file
is simply absent from the diff.
Repro (from `$SKILL`): `python -m scripts.apply_codemod $FIX\src\components\InlineHeavy.jsx -m $FIX\proposal\mapping.json --kind color` → `0 replacement(s) in 0 file(s)`, no mention of the file
anywhere, yet `mapping.json`'s rule `co-001-fg` (`--fg-muted`) claims `"occurrences": 9` including
`InlineHeavy.jsx:3`'s inline `color:"#3a3a3a"`. Cross-referencing literals.json against
value-rules in this fixture: 5 of 62 (8%) "mechanically replaceable" occurrences were phantom
inline-style ones that can never be applied.
Observed vs expected: reconciliation.md's headline table (`| Mechanically replaceable | 65 | 70% |`)
overstates what the codemod can actually do — directly undermines SKILL.md's own sales pitch
("84% are mechanically replaceable in an afternoon") and philosophy #4 ("mechanical and judgment
work are separated, hard").
Fix: exclude `context=="inline-style"` from the replaceable-rule buckets (route to `unmapped`
with a "Law 4 — Phase 4f" reason instead), or subtract inline-style occurrences from the
reconciliation's "Mechanically replaceable" row.
Confidence: high.

**MIG-5** · portability · `scripts/apply_codemod.py:637-673` (`git_root`, `dirty_files`) · When
the git repo's **absolute path** contains any non-ASCII character, `git_root()`'s
`subprocess.run(..., text=True)` (decodes as cp1252, the known issue) mangles the returned
top-level path into a string that doesn't exist on disk. `dirty_files()`'s
`git -C <mangled-root> status ...` then fails outright, so `dirty_files()` returns `None` for the
**whole repo**, and `apply_codemod` prints "git status failed; treating every file as clean" and
`--apply`s over files with uncommitted changes, no further warning. Separately,
`dirty_files()`'s `name.strip('"')` (line 669) never un-escapes git's `core.quotepath` octal
escaping (` M "src/t\303\266kens-nam\303\251.css"`), so a dirty file whose *name* (not just repo
path) is non-ASCII is missed even when the repo root is plain ASCII and resolves fine —
reproduced identically on WSL, so this half is cross-platform.
Repro (from `$SKILL`, git repo at e.g. `...\gít repö\`, `user.name`/`email` set, gpgsign off):
commit a baseline, hand-edit `src\tökens-namé.css` without committing, then
`python -m scripts.apply_codemod "...\gít repö\src" -m "...\proposal\mapping.json" --kind spacing --apply`
Observed: `apply_codemod: git status failed; treating every file as clean.`, then the dirty
file's diff is shown and **written**, discarding the uncommitted edit. Control repros in a
plain-ASCII repo and one with only spaces in the path (`git with spaces\repo dir`) both correctly
print `SKIP ... has uncommitted changes` and leave the file untouched — isolating the break to
non-ASCII, not spaces. Directly contradicts SKILL.md: "the one thing worse than a bad codemod is
a bad codemod mixed into somebody's work in progress."
Fix: decode both git subprocess calls with `encoding="utf-8"` explicitly; unescape git's C-style
octal path-quoting in `dirty_files()` before building `entry`, or pass `-c core.quotepath=false`.
Confidence: high.

**MIG-6** · wrong-result · `scripts/apply_codemod.py:294-302` (`Mapping.load`) · A missing-schema
or unparseable `mapping.json` raises `SystemExit(f"apply_codemod: ... is not readable JSON...")`
— `SystemExit` with a **string** argument makes the interpreter print it and exit with status
**1**, not the documented **2** ("bad invocation"). Exit 1 is otherwise documented to mean
"something was skipped (read the list)", so a CI script branching on exit code cannot tell a
corrupt/wrong mapping file from a normal partial-skip run. (The sibling "no such mapping" check a
few lines above correctly `return 2`s — only the two schema/parse `raise SystemExit` paths are
affected.)
Repro (from `$SKILL`): `echo '{"foo":1}' > bad.json` then
`python -m scripts.apply_codemod $FIX\src -m bad.json` → prints the "not readable JSON.../is not
a codemod mapping" message, exit code **1**. Compare `python -m scripts.cluster_values bad.json --dry-run` → same class of error, correctly exits **2**.
Fix: `print(msg, file=sys.stderr); return 2` (matching every other bad-invocation path in both
scripts) instead of `raise SystemExit(msg)`.
Confidence: high.

**MIG-7** · broken-doc · `scripts/cluster_values.py:390` (`Z_LADDER`) vs
`references/token-contract.md:13,91` · The contract states "8 z-indexes" and lists the ladder as
`--z-base --z-raised --z-sticky --z-dropdown --z-overlay --z-modal --z-toast --z-tooltip` (8
names), but `Z_LADDER` in the script omits `--z-base`, leaving only 7. `cluster_z()`'s own
generated note ("N distinct z-indexes for an **7**-rung ladder") therefore contradicts the
contract it's supposed to mirror exactly (the same file's header comment says "these mirror
references/token-contract.md exactly"). Functionally harmless today only because
`extract_literals.py` already drops literal `z-index:0`, so `--z-base` would never be assigned —
but the mismatched count is user-visible in every z-index reconciliation note.
Confidence: medium (harmless in current usage, but a real drift from the stated contract).

## Tested and OK

- `extract_literals`: all three `--format` values (report/json/csv); `--kind`/`--top`/`--min-count`;
  `--include-vendor` and `--include-tokens` correctly widen the walk (verified counts change);
  vendor dir and pre-existing `tokens.css` correctly excluded by default; nonexistent path and
  unknown `--kind` both exit 2 with a clear message.
- Correctness on tricky inputs: comments, quoted strings, and `url(...)` are never touched;
  `clip-path: path("M13 14 L15 13 Z")` (SVG path numbers in a string) untouched; partial-match
  guard holds (`113px`, `213px` never conflated with `13px`); CRLF file, non-ASCII filename +
  content (`légàcy/tokens-café.css`), and a directory with a space in it (`legacy pages/Old
  Page.css`) are all read and rewritten correctly on Windows.
- `cluster_values`: full worked run (extract → cluster → per-`--kind` `apply` → commit, for
  color/type/spacing/radius/stroke/duration/shadow/z-index/tracking) produced sensible
  closed-scale tokens with provenance `was:` comments; `--accent`, `--spacing-tolerance`,
  `--dry-run` (non-crashing cases) all work; missing/bad-schema `literals.json` exits 2 cleanly.
- `apply_codemod`: dry-run vs `--apply`; `--kind` batching; `--only` glob (`*Card.module.css`
  correctly scoped to one file); `--skip-review` (11→2 occurrences, correctly dropping the
  review-flagged cluster); `--report`/`--no-diff`; `--force` overriding a dirty-file skip.
  Negative values: `margin-top: -13px` → `calc(var(--gap-related) * -1)`. Shorthand slot
  splitting: `padding: 9px 17px` → distinct `--pad-block-sm`/`--pad-inline-md` per slot;
  `padding: 15px 20px` → only the mappable slot rewritten, the other left literal. `transition:
  transform 220ms ease-out, opacity 180ms ease` → per-layer `--motion-enter`/`--motion-hover`
  pairs. `font-size` → `font: var(--type-*)` correctly **skipped** (with a clear message) when
  the same rule also sets `font-weight`. Dirty-tree refusal and `SKIP ... — commit or stash
  first, or pass --force` verified correct in a plain-ASCII repo and in a repo whose path
  contains only spaces (`git with spaces\repo dir`). Full idempotency: re-running the entire
  mapping against an already-migrated tree produces 0 further edits.
- Windows vs WSL (Python 3.14.4, same fixture via `/mnt/c/...`): `extract_literals --format json`
  produced byte-for-byte identical `literals.json` (same 40 entries, same order), and
  `cluster_values` on those identical inputs produced byte-for-byte identical
  `mapping.json`/`tokens.css`/`reconciliation.md` — no ordering or path-separator divergence in
  Phases 1-3 (aside from the OS-native path string the caller itself supplied).
- Phase 5/6: `web-design-studio`'s `audit_design.py` runs cleanly against the migrated tree;
  `--write-baseline` then `--baseline` correctly suppresses all recorded findings ("design audit:
  clean — all nine laws hold").

## Could not test

- Commit-signing-specific git paths: `commit.gpgsign` was off in this environment, so the
  "staged/untracked only" fallback for signed repos was not exercised.
- `--kind easing` end-to-end `apply_codemod` (no `cubic-bezier()`/`steps()` literal existed in a
  context `apply_codemod` scans — `cluster_easing` itself was not independently exercised).
- SKILL.md Phase 5's literal `git stash && audit && git stash pop` sequence, end to end — the
  fixture's history was fully committed per-batch (as instructed), leaving no working-tree diff
  to stash meaningfully.
- Large-codebase (150-400 file) timing/estimate claims from SKILL.md's business-case section —
  impractical to fabricate at that scale in this session.
