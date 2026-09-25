# Bug hunt report — client-presentation-builder & design-critique-gate

Environment: Windows 11, Windows PowerShell 5.1, Python 3.14.5 (cp1252 locale), plugin
copied to a scratch workdir and run from each skill's own folder, per instructions.

## Bugs

**PRES-1 · portability (breaks the documented pipeline) · `build_presentation.py:356` (`_read_json`), `critique_report.py:359` (`_read`) · high confidence**
Both read JSON via plain `.read_text(encoding="utf-8")`, which does not skip a UTF-8 BOM.
The exact documented command `... --json > audit.json` (`client-presentation-builder/
SKILL.md:118-119`, `design-critique-gate/SKILL.md:193`, `critique_report.py:23`'s own
docstring, `design-critique-gate/assets/self-review-protocol.md:20`), run in Windows
PowerShell, writes a UTF-8-BOM'd file — confirmed with a control test (`python -c
"print('{}')" > f` gets a BOM; `Path.write_text(encoding='utf-8')` does not; the identical
command under WSL bash produces no BOM). Repro, from `client-presentation-builder/` with an
`audit.json` produced exactly as documented:
```
python -m scripts.build_presentation DECISION_LOG.md --audit audit.json --dry-run
```
Observed: `build_presentation: audit.json is not valid JSON (Unexpected UTF-8 BOM (decode
using utf-8-sig): ...). ... use `--json > file`.`, exit 2 — the error even recommends the
command that caused it. Same failure for `critique_report.py findings.json --audit
audit.json` and for stdin. Fix: read with `encoding="utf-8-sig"` in both functions.

**PRES-2 · crash · `build_presentation.py:2372`, `sys.stdout.write(render_outline(...))` · high confidence**
`--dry-run` (SKILL.md step 4: "Read the outline") crashes with `UnicodeEncodeError` if the
decision log contains any character outside cp1252 — realistic, since the log is meant to
quote the client's own words. Repro, `client-presentation-builder/`, PowerShell with
`$env:PYTHONIOENCODING=$null` (i.e. a real user's default, not this harness's):
```
python -m scripts.build_presentation decision_log_unicode.md --dry-run | Out-String
```
(title contains 🚀). Observed: `UnicodeEncodeError: 'charmap' codec can't encode
characters in position 81-89`, exit 1 (raw traceback). Non-dry-run builds are unaffected
because the deck/notes are files written with explicit `encoding="utf-8"`; only stdout
paths crash. Fix: `sys.stdout.reconfigure(encoding="utf-8")` (or `errors=
"backslashreplace"`) at the top of `main()`.

**PRES-3 · crash · `critique_report.py:805`, `sys.stdout.write(text)` · high confidence**
Same class of crash for every output path that skips `-o`: default `critique`, `--format
triage`/`defence`, `--summary` (verified default and `--summary`; the others share the
same line). Repro, `design-critique-gate/`, `$env:PYTHONIOENCODING=$null`:
```
python -m scripts.critique_report findings_unicode.json --summary | Out-String
```
(a finding title contains 😀). Observed: `UnicodeEncodeError ... character '\U0001f600'`,
exit 1. `-o file.md` with the same input exits 0 (file writes are explicit utf-8). Same fix
as PRES-2.

**PRES-4 · crash · `build_presentation.py:2260` (`emit_css`) and `:2384` (`--notes`) · high confidence**
`-o/--out` guards its parent dir (`out_path.parent.mkdir(parents=True, exist_ok=True)`) and
`critique_report.py`'s `-o` catches `OSError` and exits 2 cleanly — `--notes` and
`--emit-css` have no equivalent, so a bad path is an uncaught traceback, exit 1, not the
documented "2 bad invocation". Repro 1, `client-presentation-builder/`:
```
python -m scripts.build_presentation decision_log_good.md -o out.html --notes no_such_subdir\notes.md
```
→ uncaught `FileNotFoundError` at line 2384. Repro 2 (target exists as a plain file):
```
New-Item -Force blocked -ItemType File
python -m scripts.build_presentation decision_log_good.md -o out2.html --emit-css blocked
```
→ uncaught `FileExistsError: [WinError 183]` at line 2260. Compare
`critique_report.py findings.json -o no_such_dir\out.md` → clean `critique_report: cannot
write ...`, exit 2. Fix: wrap both the same way.

**PRES-5 · cosmetic · `build_presentation.py:1604`/`1612` (`.dlist`/`--dlist-key`) + `:1906` (`.help__panel`) · high confidence**
The `?`/`H` keyboard-help panel reuses `.dlist` (built for short decision-field labels).
Its key column (`minmax(auto, var(--measure-narrow))`, up to 48ch) is fine on a full-width
slide, but the help panel is capped at `--width-form` (28rem/448px) on any screen size. Long
shortcut text ("← / ↑ / BACKSPACE / PAGE UP") eats most of that width, leaving ~50-70px for
the value column, so answers wrap one word per line and are barely legible. Reproduced
visually in Chromium at the default pane size and at an emulated 1440×900 viewport —
identical, since the cap is a fixed length. Repro: build any deck, open it, press `H`. Fix:
a wider key column or a two-line row for the help panel specifically.

**PRES-6 · wrong-result · `parse_decision_log`, `build_presentation.py` ~line 259-266 · medium confidence**
Two `### D1 — ...` headings in one log are not detected as a collision — the auto-numbering
fallback only fires when a block has no `D<n>` prefix at all — so both `Decision` objects
keep `ident="D1"` and both appear in the deck/appendix/notes labelled identically, with no
way to tell them apart. Repro, `client-presentation-builder/`:
```
python -m scripts.build_presentation decision_log_dup_id.md --audience team --dry-run
```
Observed: outline shows `4. decision First one [D1]` and `5. decision Second one, same id
[D1]`. Not a crash. Fix: warn or auto-disambiguate (`D1`, `D1-b`) on a repeated ident.

## Tested and OK

- `audit_design.py --strict` on the deck's `--emit-css` output is genuinely clean (0
  findings) — the SKILL.md claim holds. Programmatically cross-checked every `var(--x)`
  used in `DECK_CSS` (96 refs) and in `deck-tokens.css` (73 refs): zero undefined.
- Full pipeline end to end: real `audit_design.py --json` / `perf_audit.py --json` on
  fixtures → `critique_report.py --format defence` → `build_presentation.py` for all three
  audiences with `--audit --perf --a11y --defence --screenshots --notes --emit-css` combined.
- Deck HTML well-formed (`html.parser`, no tag mismatches) for all three audiences;
  `#deck-provenance` JSON parses and matches the cited input files/JSON paths.
- Keyboard nav verified live in Chromium: arrows/Space/PageUp-Down/Home/End move slides and
  update counter/progress/`aria-live`; `N` toggles notes and shows the right per-slide gaps
  in place; help overlay opens with correct content (layout bug is PRES-5).
- Before/after pairing (`home--before.png`+`home--after.png`) and a captioned single shot
  (`hero.png`+`hero.txt`) both work; >6 screenshots triggers the "not placed" gap correctly.
- Decision ranking hand-verified for `client` audience (audience/tag/evidence/consequence
  scoring) — matches the documented formula exactly.
- All documented exit codes reproduced: 0 clean; 1 when the defence sheet has a blocking
  item (deck still written); 2 for bad invocation (missing file, zero decisions parsed,
  `--max-decisions 0`, bad `--tokens`/`--screenshots`, malformed `--audit`/`--perf`/`--a11y`
  shape) — all with clear messages. Confirmed identically for CRLF logs and paths with spaces.
- `critique_report.py`: all 3 `--format`s, `--summary`, `--audit` merge (dedup by rule and
  by file:line; arithmetic checked: 5 hand + 3 collapsed machine = 8, tally matched),
  `--audit-blocking`, `--layer`, `--min-severity`, `--no-taste`, every `--fail-on` value,
  stdin (`-`), empty findings, unknown severity/layer (clean exit 2), missing file.
  Duplicate finding IDs don't break ranking, only produce duplicate triage HTML-comment
  anchors — cosmetic, not filed separately.
- `CRITIQUE_TEMPLATE.md`'s `findings.json` shape and section headings, and
  `DECISION_LOG.md`/`MEETING_RECORD.md` field names, all match what the two scripts parse.

## Could not test

- Real print-to-PDF rendering (`Ctrl/Cmd+P`) — `@media print` CSS read and looks internally
  consistent (chrome hidden, notes shown, `break-after: page`), but had no way to capture
  actual paginated print output from the sandboxed browser tool.
- `--tokens` with a client file that omits variables `DECK_CSS` needs — an authoring
  concern, not a script defect; the fallback chain to the bundled tokens works correctly.
- Screenshot sets >10MB (the email-gateway warning threshold) — skipped as low-value; the
  size arithmetic is simple and clearly correct by inspection.
