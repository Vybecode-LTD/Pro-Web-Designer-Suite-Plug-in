# PY-D: a11y_static, perf_audit, crux_check, generate_matrix, critique_report, build_presentation, brief_to_log, lint_claims

Audited 2026-10-28 at main 8441ff0. Files read in full: `plugins/pro-web-design-suite/skills/a11y-audit-runner/scripts/a11y_static.py`, `skills/perf-budget-gate/scripts/perf_audit.py`, `skills/perf-budget-gate/scripts/crux_check.py`, `skills/component-state-matrix/scripts/generate_matrix.py`, `skills/design-critique-gate/scripts/critique_report.py`, `skills/client-presentation-builder/scripts/build_presentation.py`, `skills/landing-page-conversion/scripts/brief_to_log.py`, `skills/landing-page-conversion/scripts/lint_claims.py`; the six skills' `SKILL.md`; `client-presentation-builder/assets/DECISION_LOG.md`. Skimmed: `a11y-audit-runner/references/scripts.md` §1, `perf-budget-gate/references/budgets.md` (schema and units), `references/diagnosis.md` §5, `references/ci-integration.md` (the preload rules), `landing-page-conversion/references/conversion-audit.md` §13. Tests consulted (grepped for the cases below): `tests/test_static_checks.py`, `test_content_and_a11y.py`, `test_perf_audit.py`, `test_lint_claims.py`, `test_brief_to_log.py`, `test_presentation.py`, `test_deck.py`, `test_json_guards.py`, `test_baseline_keys.py`. None of them covers the cases reported here except `address-line2` (only the `type="number"` guard, G9) and `Math.random` (the stock-count case, not the CSS one). Commands run: each script against fixtures written to `C:\Users\vybec\AppData\Local\Temp\claude\C--DEV-Pro-Web-Designer-Suite-Plug-in\d484deaf-54ec-437b-be40-bf3f426dae3e\scratchpad\py-d\` (quoted under each finding); `uv run --no-project --python 3.9 python -B` importing all eight scripts (every one imports clean on 3.9.25).

## Summary

30 findings: 4 high, 11 medium, 15 low. By class (counted from the headings): bug 17, gap 5, dead-code 4, inconsistency 3, risk 1. No critical: nothing writes outside the project, every output goes through `refuse_overwrite`, no key is echoed, and the ordering of every report is deterministic. The three that matter most: (1) `a11y_static.py` fails a commit on the canonical `:focus:not(:focus-visible) { outline: none }` idiom and on a commented-out `// outline: none;` in SCSS, both as errors (PY-D-1, PY-D-2); (2) `a11y_static.py`'s SC 1.3.5 hint patterns are unanchored substrings, so `units`, `community` and `opportunity_id` are errors demanding `autocomplete="address-line2"` (PY-D-3); (3) `lint_claims.py` reports `invented-scarcity`, an error, on every `el.style.left = Math.random() * …` in a particle or confetti animation (PY-D-27). The deck builder and the perf gate have medium false-negative gaps rather than false positives: template placeholders in `## Brief` and `## Ask` reach the deck unflagged (PY-D-21), and `font-no-metric-fallback` goes silent for every family once any one family has a fallback (PY-D-13).

## Findings

### PY-D-1 · high · bug

- **Where:** `plugins/pro-web-design-suite/skills/a11y-audit-runner/scripts/a11y_static.py:1734` (and 1740-1748)
- **What:** The CSS audit blanks `/* */` comments only, so in `.scss`, `.less` and `.pcss` (all in `CSS_EXT`, line 105) a `//` line comment inside a rule is read as a live declaration. A commented-out `// outline: none;` beside a real `box-shadow` ring becomes a `focus-ring-shadow-only` error; alone it becomes `outline-none-no-replacement`.
- **Evidence:** `src = re.sub(r"/\*.*?\*/", …, text, flags=re.S)` at 1734; the declaration regex at 1740 then matches `outline: none` inside the comment. Run: `python -B a11y_static.py scss/` on `.btn:focus { // outline: none;\n box-shadow: 0 0 0 2px red; }` → `3  error  K focus-ring-shadow-only  \`.btn:focus\` replaces the outline with \`box-shadow\` alone.`, exit 1.
- **Effect:** The pre-commit hook refuses commits over a comment; the finding names a line that sets nothing.
- **Fix:** For the Sass/Less extensions, also blank `//` to end of line outside strings and outside `url(`…`)` before scanning (the same scanner `perf_audit.strip_css_comments` uses, extended). Regression test: the SCSS fixture above must be clean.
- **Confidence:** confirmed

### PY-D-2 · high · bug

- **Where:** `plugins/pro-web-design-suite/skills/a11y-audit-runner/scripts/a11y_static.py:1746` (to 1770)
- **What:** `outline-none-no-replacement` looks for a replacement indicator in the same rule only, so the standard `:focus:not(:focus-visible) { outline: none }` idiom (MDN's and the focus-visible polyfill's recommended pattern, paired with a `:focus-visible` ring rule) is an error.
- **Evidence:** Run on `.btn:focus:not(:focus-visible) { outline: none; }\n.btn:focus-visible { outline: 2px solid var(--border-focus); outline-offset: 2px; }` → `1  error  K outline-none-no-replacement  \`.btn:focus:not(:focus-visible)\` sets \`outline: none\` and provides no replacement indicator.`, exit 1. The fix text itself says "If you genuinely want no ring for MOUSE users, that is what `:focus-visible` already does for you", which is exactly what this selector expresses.
- **Effect:** A correct stylesheet fails the gate; the only way through is a pragma or a baseline entry.
- **Fix:** Treat a selector whose own compound contains `:not(:focus-visible)` as mouse-only and skip the rule (or pass it when another rule in the file with the same subject has a `:focus-visible` ring). Regression test from the fixture above.
- **Confidence:** confirmed

### PY-D-3 · high · bug

- **Where:** `plugins/pro-web-design-suite/skills/a11y-audit-runner/scripts/a11y_static.py:310` (also 313, 322)
- **What:** `PERSONAL_FIELD_HINTS` are searched as unanchored substrings of the field's name/id/placeholder/aria-label, so `apartment|suite|unit` matches `units`, `community`, `opportunity_id`, `unit_price`; `town` matches `downtown`; `mobile` matches `mobile_os`. G9 guarded only `type="number"` (line 1556). Each hit is a `missing-autocomplete` error (1.3.5).
- **Evidence:** Run on `<input id="u" name="units" type="text">`, `name="community"`, `name="opportunity_id"` (each with a `<label for>`) → three lines `error  F missing-autocomplete  <input name="…"> collects the user's own data and has no \`autocomplete\` (expected \`address-line2\`).`, exit 1.
- **Effect:** Ordinary product fields fail the gate as personal-data fields, and the advised token would be wrong to add.
- **Fix:** Anchor the short tokens on letter boundaries (`(?<![a-z])(apartment|apt|suite|unit)(?![a-z])`, `(?<![a-z])town(?![a-z])`, `(?<![a-z])mobile(?![a-z])`, so `units` and `community` stop matching while `apt_unit` and `apt-unit` still hint) and match each attribute separately rather than the joined haystack (see PY-D-8). Regression test: the three fields above stay clean; `name="apt_unit"` still hints.
- **Confidence:** confirmed

### PY-D-4 · medium · bug

- **Where:** `plugins/pro-web-design-suite/skills/a11y-audit-runner/scripts/a11y_static.py:745` (747-748) against 958, 975, 985, 1000, 1009, 1020, 1028, 1036, 1054, 1071, 1128, 1137, 1145, 1256, 1321, 1364
- **What:** `a11y-audit-ignore-next-line` marks the comment's line and the one after it, but attribute rules report at the attribute's own line (`t.attr_lines.get(attr, line)`). A tag formatted one prop per line (Prettier's JSX default) puts the `aria-*`, `role`, `alt`, `tabindex`, `autocomplete` or `lang` attribute two or more lines below the pragma, which then does nothing.
- **Evidence:** Run on a `.tsx` with `{/* a11y-audit-ignore-next-line: R -- … */}` followed by `<div\n role="group"\n aria-labeledby="x"\n>` → `7  error  R aria-unknown-attr  \`aria-labeledby\` is not an ARIA attribute`, exit 1 (the pragma is on line 4, the tag opens on line 5).
- **Effect:** The documented escape hatch fails on the most common JSX formatting; users reach for `ignore-file`.
- **Fix:** In `add()`, also consult the pragma set for the tag's opening line (pass `t.line` alongside the attribute line), or extend a pragma to the whole tag that starts on the next line. Regression test with the fixture above.
- **Confidence:** confirmed

### PY-D-5 · medium · bug

- **Where:** `plugins/pro-web-design-suite/skills/a11y-audit-runner/scripts/a11y_static.py:946` (948, 1377-1394)
- **What:** Any `<title>` element sets `has_title`, including an SVG's `<title>` inside `<body>`, so a document with no head title passes `no-title`; and since the last `<title>` wins, an empty SVG `<title>` after the real one raises `empty-title`.
- **Evidence:** `if name == "title": has_title = True; title_text = inner` at 946-948. Run on a full document whose `<head>` has only `<meta charset>` and whose `<main>` holds `<svg><title>Icon</title></svg>` → `a11y static: clean`, exit 0.
- **Effect:** A 2.4.2 failure the gate advertises (`references/scripts.md` §1: "missing/empty `<title>`") is missed on any page with inline SVG icons.
- **Fix:** Only count a `<title>` whose ancestors (via `ancestors_of`) contain no `svg` and, for documents, that sits inside `head`. Regression test: the fixture must report `no-title`.
- **Confidence:** confirmed

### PY-D-6 · medium · bug

- **Where:** `plugins/pro-web-design-suite/skills/a11y-audit-runner/scripts/a11y_static.py:1316` (1319-1326)
- **What:** `label = a.get("aria-label") or a.get("aria-labelledby")` mixes a name with an id; the `\bnav\b` test then matches ids like `nav-title` (`-` is a word boundary), and the message prints the id as `aria-label="…"`.
- **Evidence:** Run on `<nav aria-labelledby="nav-title"><h2 id="nav-title">Docs</h2>…</nav>` → `2  warn  S landmark-label-noise  \`<nav aria-label="nav-title">\` repeats the role in the label.`
- **Effect:** A false warning on the recommended labelling mechanism, with a message that misquotes the markup; under `--strict` it fails.
- **Fix:** Run the "repeats the role" check on `aria-label` only (for `aria-labelledby`, resolve the id's element text when it is in the file, else skip); quote the attribute actually present. Regression test from the fixture.
- **Confidence:** confirmed

### PY-D-7 · medium · bug

- **Where:** `plugins/pro-web-design-suite/skills/a11y-audit-runner/scripts/a11y_static.py:1287` (1288-1289)
- **What:** `vague-link-text` uses the inner text first and `aria-label` only when the text is empty, but the accessible name is the `aria-label` when both exist (the precedence the duplicate-name check at 1306-1307 gets right).
- **Evidence:** Run on `<a href="/report" aria-label="Read the 2026 accessibility report">Read more</a>` → `5  warn  N vague-link-text  Link text is "read more".`
- **Effect:** A link named exactly as the fix text recommends ("extend the name") is still flagged.
- **Fix:** `txt = norm_text(aria-label) if aria-label not in (None, EXPR) and non-empty else norm_text(inner)`; keep a separate 2.5.3 check that the label contains the visible text. Regression test from the fixture.
- **Confidence:** confirmed

### PY-D-8 · medium · bug

- **Where:** `plugins/pro-web-design-suite/skills/a11y-audit-runner/scripts/a11y_static.py:1551` (1553-1556, with the `^…$` patterns at 299, 301, 305, 310-314, 321-323)
- **What:** `_personal_field` joins name, id, placeholder and aria-label into one string and searches each pattern once, so anchored hints (`^name$`, `^city$`, `^state$`, `^tel$`, `^address$`, `^url$`, `^dob$`…) match only when the field has exactly one of those attributes. The same field is reported or not depending on whether it carries an `id`.
- **Evidence:** Run on `<input id="n1" name="name" type="text">` (clean) and `<input id="name" type="text">` → `3  error  F missing-autocomplete  <input id="name"> … (expected \`name\`).` in the same file.
- **Effect:** 1.3.5 coverage is arbitrary for the commonest names, and a labelled field with an id (the form the F rules themselves demand) is the one that escapes.
- **Fix:** Search each attribute value separately (`any(re.search(p, v) for v in values)`). Regression test: both inputs above must report.
- **Confidence:** confirmed

### PY-D-9 · low · gap

- **Where:** `plugins/pro-web-design-suite/skills/a11y-audit-runner/scripts/a11y_static.py:1033`
- **What:** `aria-dangling-ref` runs only `if … and ids`, so a file with no `id` attribute at all never reports a dangling `aria-labelledby`/`aria-describedby`/`aria-controls`, even a complete document (`saw_html`), where the reference cannot resolve anywhere.
- **Evidence:** Run on a full document whose only reference is `<button aria-labelledby="missing-id">Go</button>` → `a11y static: clean`, exit 0.
- **Effect:** The one case where the reference is certainly broken is the one not reported.
- **Fix:** Drop the `and ids` guard when `doc_like` (keep it for fragments). Regression test from the fixture.
- **Confidence:** confirmed

### PY-D-10 · low · gap

- **Where:** `plugins/pro-web-design-suite/skills/a11y-audit-runner/scripts/a11y_static.py:1799` (1801)
- **What:** `focus-ring-transition` matches the literal `outline` in the `transition` value, so `transition: all .2s` on a focus rule, which transitions the outline too, is not reported.
- **Evidence:** Run on `.a:focus-visible { outline: 2px solid red; transition: all .2s; }` → clean.
- **Effect:** The commonest form of the fade is missed.
- **Fix:** Also warn when the value names `all` and the rule sets an outline. Regression test from the fixture.
- **Confidence:** confirmed

### PY-D-11 · low · dead-code

- **Where:** `plugins/pro-web-design-suite/skills/a11y-audit-runner/scripts/a11y_static.py:620`
- **What:** `a.get("tabindex", a.get("tabIndex", ""))` can never reach the `tabIndex` key: `scan_tags` stores every attribute name lower-cased (`bound_attr` returns `raw.lower()` at 426/442, stored at 567-569).
- **Evidence:** `grep -n tabIndex a11y_static.py` → only line 620.
- **Effect:** None; misleading to a reader.
- **Fix:** Drop the fallback. No test needed.
- **Confidence:** confirmed

### PY-D-12 · low · gap

- **Where:** `plugins/pro-web-design-suite/skills/a11y-audit-runner/scripts/a11y_static.py:1232` (1253-1264)
- **What:** `autocomplete="off"` on a personal-data field passes both the missing and the invalid check: `off` is a valid token but does not identify the field's purpose, so 1.3.5 is still unmet (and `lint_claims.py` does warn on it, as `autocomplete-off`).
- **Evidence:** Run on `<input id="f" type="text" name="email" autocomplete="off">` with a label → no F finding.
- **Effect:** The two gates disagree on the same field; the a11y one, which names 1.3.5, is the one that is silent.
- **Fix:** When `_personal_field` returns a hint and the value is `off`, report `missing-autocomplete` as a warning with the hint. Regression test from the fixture.
- **Confidence:** confirmed

### PY-D-13 · medium · bug

- **Where:** `plugins/pro-web-design-suite/skills/perf-budget-gate/scripts/perf_audit.py:911` (915-929)
- **What:** `font-no-metric-fallback` is raised only `if not metric_families`: once any face in the file has `size-adjust`/overrides, a face of another family with no fallback (the `any(fam in other …)` test fails for it) falls through to nothing.
- **Evidence:** Run on a stylesheet with `Inter` + `Inter Fallback` (metrics) + `Fraunces` (no fallback) → `perf audit: clean — every budget holds.`
- **Effect:** The rule works on the first family and then switches itself off for every later one, which is the realistic shape (a body face with a fallback, a display face without).
- **Fix:** Report each face that has no matching metric family, once per family; drop the `if not metric_families` branch. Regression test from the fixture (expect one warning naming Fraunces).
- **Confidence:** confirmed

### PY-D-14 · medium · inconsistency

- **Where:** `plugins/pro-web-design-suite/skills/perf-budget-gate/scripts/perf_audit.py:1402` (1405-1414)
- **What:** `font-not-preloaded` fires for every face not preloaded, while its own fix text says to preload "the ONE face used above the fold" because "preloading five makes all five slower" (and `references/budgets.md` line 68 and `diagnosis.md` §4.4 say the same). A site that follows the advice can never be warning-clean, so `--strict` always fails with two or more faces.
- **Evidence:** Run with `inter.woff2` preloaded (`crossorigin`) and a second `@font-face` for Fraunces → `1  warn  L font-not-preloaded  \`Fraunces\` is never preloaded (fraunces.woff2).`
- **Effect:** The rule asks for what the skill tells the reader not to do; teams baseline or pragma it and lose the real signal (no face preloaded at all).
- **Fix:** Warn only when no face in the page is preloaded (or at most once, listing the faces), or demote the per-face case to a note. Regression test: the fixture above must be clean.
- **Confidence:** confirmed

### PY-D-15 · medium · inconsistency

- **Where:** `plugins/pro-web-design-suite/skills/perf-budget-gate/scripts/perf_audit.py:666` (679-689)
- **What:** `img-no-dimensions` accepts `aspect-ratio` only in the element's inline `style`, but the fix text says "Put the INTRINSIC pixel size in the attributes, or set `aspect-ratio` in CSS", and `references/diagnosis.md` line 145 says the same. The CSS pass already collects per-class widths (965-975) but not aspect ratios.
- **Evidence:** Run on `<img class="avatar" src="a.png" alt="" fetchpriority="high">` with `.avatar { aspect-ratio: 1; width: 48px; }` in the linked stylesheet → `2  error  C img-no-dimensions  \`<img>\` has no width/height: a.png.`
- **Effect:** Following the printed fix does not clear the error (Law 4 forbids the inline style that would); only attributes or a pragma do.
- **Fix:** Collect `aspect-ratio` per class/id in `audit_css` like `widths`, and resolve `img-no-dimensions` in `check_oversized_images`'s cross-file stage (or reword the fix to "attributes, or `aspect-ratio` in an inline style"). Regression test from the fixture.
- **Confidence:** confirmed

### PY-D-16 · low · dead-code

- **Where:** `plugins/pro-web-design-suite/skills/perf-budget-gate/scripts/perf_audit.py:112` (111-114, 1586-1587)
- **What:** `SKIP_DIRS` holds `".next/cache"`, but `iter_files` compares single directory names, so it never matches; every dot-prefixed entry (`.git`, `.venv`, `.turbo`, `.cache`, `.parcel-cache`, `.vercel`) is also redundant with `not d.startswith(".")`.
- **Evidence:** `dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]` at 1586-1587.
- **Effect:** None at runtime; a maintainer may believe `.next/` is partly scanned.
- **Fix:** Reduce the set to the non-dot names and note that dot folders are skipped wholesale. No test needed.
- **Confidence:** confirmed

### PY-D-17 · low · dead-code

- **Where:** `plugins/pro-web-design-suite/skills/perf-budget-gate/scripts/perf_audit.py:931` (937, 949)
- **What:** The regex also matches `animation`/`animation-name`, but both rules below it are guarded by `prop.startswith("transition")`, so an animation match is computed and discarded.
- **Evidence:** Lines 937 and 949 both begin `if prop.startswith("transition")`.
- **Effect:** None; `@keyframes` on layout properties go unreported while the code looks as if it covers them.
- **Fix:** Either drop the alternation or add the keyframes check it implies. No test needed for the removal.
- **Confidence:** confirmed

### PY-D-18 · low · gap

- **Where:** `plugins/pro-web-design-suite/skills/perf-budget-gate/scripts/perf_audit.py:1305`
- **What:** `check_growth` skips a category whose baseline total is 0 (`if not before: continue`), so a category that was empty at baseline time (no fonts, no media) can grow without limit until the absolute budget catches it.
- **Evidence:** The `continue` at 1305-1306; `growth_summary` at 1340-1343 prints such rows as `+0.0%`.
- **Effect:** The "which commit did it" signal is absent exactly when a new category appears.
- **Fix:** Report growth from zero as its own line (`grew from 0 to X`) when `after > 0`. Regression test: a baseline with `font: 0` and a build with one font file.
- **Confidence:** confirmed

### PY-D-19 · low · inconsistency

- **Where:** `plugins/pro-web-design-suite/skills/perf-budget-gate/scripts/perf_audit.py:107` (109)
- **What:** `.ico` is listed among the "already entropy-coded" `PRECOMPRESSED` formats, but ICO is uncompressed BMP data that gzips well; it is counted raw while every other text-like asset is gzipped.
- **Evidence:** `PRECOMPRESSED = {…, ".ico"}` at 107-109; the comment at 105-106.
- **Effect:** An over-count only (the direction the docstring prefers); the comment is wrong.
- **Fix:** Drop `.ico` from the set or correct the comment. No test needed.
- **Confidence:** confirmed

### PY-D-20 · low · risk

- **Where:** `plugins/pro-web-design-suite/skills/perf-budget-gate/scripts/crux_check.py:146`
- **What:** The API key is sent as `?key=` in the URL. The script never prints it and refuses `--key`, but a query string is recorded by proxies, corporate TLS inspectors and `CRUX_API_URL` servers' access logs. Google's APIs accept the same key in the `X-Goog-Api-Key` request header, which URL-based records (access logs, referrers, browser history) do not keep; a proxy or TLS inspector can still log headers, so the header is a narrower exposure, not none.
- **Evidence:** `url + "?key=" + urllib.parse.quote(key, safe="")` at 146; the docstring at 30-34 acknowledges the key "travels in it".
- **Effect:** A low, documented exposure that a one-line change removes.
- **Fix:** Send the key in `X-Goog-Api-Key` and keep the URL clean; `test_crux_check.py`'s recorded-response path is unaffected.
- **Confidence:** confirmed

### PY-D-21 · medium · gap

- **Where:** `plugins/pro-web-design-suite/skills/client-presentation-builder/scripts/build_presentation.py:1383` (1394-1395, 1541-1549)
- **What:** Header fields (317-318) and decision fields (173-179) still holding the template's `<…>` placeholder become gaps, but the `## Brief`, `## Premise` and `## Ask` sections are rendered as quoted prose with no placeholder check, so the template's own guidance text reaches the deck as the client's brief and the presenter's ask.
- **Evidence:** `python -B build_presentation.py DECISION_LOG.md --dry-run` on the untouched `assets/DECISION_LOG.md` → slide 2 `brief` and slide 7 `ask` carry no GAP line; the built `deck.html`'s brief slide body begins `&lt;Two or three sentences, in the client's own words…` and the ask slide `&lt;The three things you need said out loud…`, with no gap marker.
- **Effect:** The docstring's rule ("Anything the inputs do not contain becomes a marked gap … never a plausible-sounding guess") does not hold for the two slides that open and close the deck.
- **Fix:** In `_brief` and `_ask`, treat a section whose text, stripped of backticks, is one or more `PLACEHOLDER` matches as absent (fall through to the existing "No `## Brief`" / "No `## Ask`" gaps). Regression test: the template must produce both gaps.
- **Confidence:** confirmed

### PY-D-22 · medium · bug

- **Where:** `plugins/pro-web-design-suite/skills/client-presentation-builder/scripts/build_presentation.py:799` (796-806)
- **What:** `blk_prose` treats any paragraph that starts with `-` or `*` as a bullet list and strips leading `*`, so a prose section written as `**Goal:** reduce support tickets` (bold-led lines, the form the template uses for every field) renders as `Goal:** reduce support tickets`.
- **Evidence:** Built from a log whose `## Brief` holds `**Goal:** reduce support tickets by a third.` and `**Constraint:** 68% of sessions are on mobile.` → brief slide body `<li><span data-quoted="decision-log">Goal:** reduce support tickets by a third.</span></li><li>…Constraint:** 68% …</li>`.
- **Effect:** Mangled text on the opening slide, in the client's quoted words.
- **Fix:** Detect a bullet by `- ` or `* ` (marker plus space), not by a leading `*`. Regression test from the fixture.
- **Confidence:** confirmed

### PY-D-23 · low · bug

- **Where:** `plugins/pro-web-design-suite/skills/client-presentation-builder/scripts/build_presentation.py:575` (1228-1237)
- **What:** For the suite's own shapes (`a11y_static.py --json`, `a11y_runtime.mjs --json`) the impact is the finding's severity (`error`/`warning`), but the impact table lists only axe's `critical … unspecified`, so it renders as a header with no rows, and `serious` (1226-1227) is always 0.
- **Evidence:** Built with `--a11y a11y.json` from `a11y_static.py --json` → the a11y slide holds `<table class='dtable'>` with `Impact | Elements` and an empty `<tbody>`, while the rule table below it lists four rules.
- **Effect:** An empty table on the accessibility slide; the "critical + serious" provenance entry cites a sum of nothing.
- **Fix:** Map `error`→`serious`, `warning`→`moderate` for the suite's shapes, or skip the table when no listed impact is present. Regression test: the suite-shaped input must not render an empty table.
- **Confidence:** confirmed

### PY-D-24 · medium · bug

- **Where:** `plugins/pro-web-design-suite/skills/landing-page-conversion/scripts/brief_to_log.py:263` (264-268, 304)
- **What:** On a CRLF decision log, `head = log[:at].rstrip("\n")` leaves a trailing `\r`, so `head.endswith("---")` is false: the new blocks are appended after the template's rule instead of before it, with `\n`-only line endings inside a `\r\n` file.
- **Evidence:** `--into` on a log written with `\r\n` → bytes `…**Status:** decided\r\n\r\n---\r\n\r\n\n### D2 — Assumed: …\n\n**Status:** open\n…## Since last time\r\n`; the same log with `\n` → the blocks land before `---`, as the docstring promises.
- **Effect:** On Windows (the owner's machine; PowerShell and most editors write CRLF) the rule ends up in the wrong place and the file has mixed line endings, which `.gitattributes`-normalised repos show as a whole-file diff.
- **Fix:** Detect the log's newline (`"\r\n" if "\r\n" in log else "\n"`), strip and re-join with it, and build `render()`'s output with it. Regression test: the CRLF fixture must place the blocks before `---` and keep one newline style.
- **Confidence:** confirmed

### PY-D-25 · low · bug

- **Where:** `plugins/pro-web-design-suite/skills/design-critique-gate/scripts/critique_report.py:706` (707, 909-915)
- **What:** "Layers with no findings" is computed from the findings left after `--layer` and `--min-severity` filtering, so a filtered layer is announced as clean.
- **Evidence:** Two findings (hierarchy major, craft minor) with `--layer craft` → `## Layers with no findings` lists `Hierarchy`.
- **Effect:** A critique narrowed to one layer claims the others are clean.
- **Fix:** Compute the clean list from the unfiltered findings (or omit the section when a filter is active). Regression test from the fixture.
- **Confidence:** confirmed

### PY-D-26 · low · dead-code

- **Where:** `plugins/pro-web-design-suite/skills/component-state-matrix/scripts/generate_matrix.py:942`
- **What:** `plan()`'s `themes` parameter is unused: every grid's `make_cell` writes the `@theme` placeholder and `render_grid` (1122-1125) iterates the themes itself. Not a feature never wired; the only caller (1579) passes it for nothing.
- **Evidence:** `grep -n "plan(" generate_matrix.py` → the definition at 942 and the one call at 1579; `themes` does not appear in the body (943-1028).
- **Effect:** None.
- **Fix:** Remove the parameter. No test needed.
- **Confidence:** confirmed

### PY-D-27 · high · bug

- **Where:** `plugins/pro-web-design-suite/skills/landing-page-conversion/scripts/lint_claims.py:71` (321-324)
- **What:** `invented-scarcity` (an error) fires when `Math.random` sits within three lines of any `SCARCITY_WORD`, and that list holds `left`, the CSS property every particle, confetti and float animation sets from `Math.random()`.
- **Evidence:** Run on `p.style.left = Math.random() * 100 + "%";` → `particles.js:3  error  invented-scarcity  A count made up with Math.random()` (twice, the `top` line is within three lines of `left`), exit 1.
- **Effect:** A landing page with a background animation fails the lint on an error, with a message accusing it of a fabricated count.
- **Fix:** Require the scarcity word as a whole word in a count context (`\b(?:left|remaining|in stock|sold|bought|booked|viewing|watching)\b` and not preceded by `style.` / `.left =` / `left:`), or require a digit or `Math.floor`/`round` on the same line. Regression test from the fixture, plus the existing stock-count case must still fire.
- **Confidence:** confirmed

### PY-D-28 · low · bug

- **Where:** `plugins/pro-web-design-suite/skills/landing-page-conversion/scripts/lint_claims.py:232` (233)
- **What:** `struck-price` fires on any `<s>`, `<del>` or `<strike>` whose text contains a digit, not only a price.
- **Evidence:** Run on `<s>Task 2: write the tests</s>` and `<del>Chapter 3</del>` → two `warning  struck-price  A struck-through price, "Task 2: write the tests"` lines.
- **Effect:** A changelog, a to-do list or a revised chapter number is reported as a "was" price.
- **Fix:** Require `MONEY` (or a digit with a currency word) rather than any digit. Regression test from the fixture.
- **Confidence:** confirmed

### PY-D-29 · low · bug

- **Where:** `plugins/pro-web-design-suite/skills/component-state-matrix/scripts/generate_matrix.py:1086` (912-914, 935, 1088-1091)
- **What:** Cell ids are built from `slug()`, which lower-cases and collapses punctuation, so two variants, sizes or fixtures that differ only in case or separators collide; `_IdSet` then reports "a generator bug — please report the manifest" for what is a manifest error, and the names are never validated.
- **Evidence:** A manifest with `"variants": ["Primary", "primary"]` → `generate_matrix: internal: duplicate cell id 'btn--p_state--f_default--v_primary--…'. … This is a generator bug — please report the manifest that produced it.`, exit 2.
- **Effect:** The wrong party is blamed and the fix (rename the variant) is not stated.
- **Fix:** Validate that variants, sizes and fixture names are unique after `slug()` in `Component.__init__` with a `ManifestError` naming the pair. Regression test from the fixture.
- **Confidence:** confirmed

### PY-D-30 · low · bug

- **Where:** `plugins/pro-web-design-suite/skills/component-state-matrix/scripts/generate_matrix.py:624` (625, 582, 731; 1706-1709)
- **What:** Two robustness holes in the exit-2 promise ("bad arguments or an invalid manifest"): `state_detect` and `state_attrs` are taken as given, so a list or string there raises `AttributeError` at 582/731 as a traceback; and `--out` and `--emit-css` are each checked against the inputs but not against each other, so the same path for both silently overwrites the sheet with the chrome CSS.
- **Evidence:** `self.state_detect = raw.get("state_detect", {})` at 624 with `overrides.get(part, …)` at 582; the overwrite loop at 1706-1709 checks `dest` against `inputs` only.
- **Effect:** A traceback instead of the named-field message every other manifest error gets; a lost sheet in the second case.
- **Fix:** Validate both as objects of lists/strings in `Component.__init__`; refuse `--emit-css` equal to `--out`. Regression tests for each.
- **Confidence:** likely (read, not run)

## Static-analysis candidates, resolved

- `a11y_static.py:1504` ARG001 `t` in `_labelled`: harmless; the parameter is never read. Drop it (and the redundant `or a.get(…) == EXPR` halves at 1506 and 1508, which `not in (None, "")` already covers).
- `a11y_static.py:1524` ARG001 `t` in `_has_name`: harmless; drop it.
- `perf_audit.py:749` and `:752` ARG002 `line` in `_tag_source`/`_tag_use`: fine by design; the handlers are found by `getattr(self, f"_tag_{tag}")` (584-586) and must share one signature.
- `generate_matrix.py:942` ARG001 `themes` in `plan`: a dead parameter, not an unwired feature (PY-D-26).
- `critique_report.py:823` ARG001 `c` in `render_summary`: fine by design; the four renderers share a signature and `main` calls them uniformly (917-924). Harmless.
- `build_presentation.py:1603` B009 `getattr(obj, 'source')`: style only; all three facts classes define `source`, so `obj.source` is equivalent.

## What is covered well

Input shapes are guarded everywhere a prior audit bit (G15, E13, Codex on #138): malformed baselines, budgets and reports are named by key and never traceback, including the `"totals": [1]` baseline I tried (`load_baseline` reads it as "not a list of finding keys … auditing everything"). Every reader decodes through `json.detect_encoding`, so BOM and UTF-16 files work; every writer goes through `refuse_overwrite`, including the screenshots and caption files `build_presentation.py` inlines. The JSX/Vue/Angular binding sentinel (`EXPR`) consistently means "cannot tell" and never "empty" across the a11y rules, and the pragma tag matching (category, rule or ALL) is uniform in all four gate scripts. `crux_check.py` is clean: the key never reaches stdout, stderr or an argument, the 404/no-data case is distinguished from other HTTP errors, a saved response for another page or form factor is refused, and the lab-median-of-zero case is handled as documented. The token rebind in `generate_matrix.py` is derived from the token file, and the forced-state mirror keeps at-rule context and guards (`:not()`, `:has()`) intact. All eight scripts import under Python 3.9.25 with no syntax or runtime-annotation problem, and every report sorts by `(file, line, severity)` or an explicit rank, so output is deterministic apart from the dated header in `render_notes`.
