# Drift Detection

Documentation does not go wrong all at once. It goes wrong one true sentence at a time, each of which was true when it was written. This file is the catalogue of how that happens, the check for each case, and the CI wiring that makes the checks fire before a human reads the wrong number.

The premise: **a stale doc is worse than a missing one.** A missing page costs a reader ten minutes. A stale page costs them a production bug, because they trusted it instead of measuring — and then it costs the docs site its credibility, which is unrecoverable. After the second wrong number, people stop reading, and everything else on the site becomes wasted work.

## Contents

1. [The six failure modes](#1-the-six-failure-modes)
2. [The baseline diff](#2-the-baseline-diff)
3. [Checking hand-written claims](#3-checking-hand-written-claims)
4. [Every code example is linted like source](#4-every-code-example-is-linted-like-source)
5. [What a good drift report looks like](#5-what-a-good-drift-report-looks-like)
6. [Gate wiring](#6-gate-wiring)
7. [Keeping the gate alive](#7-keeping-the-gate-alive)

---

## 1. The six failure modes

| # | Failure | Looks like | Caught by |
|---|---|---|---|
| 1 | A documented token no longer exists | a page telling people to use `--gap-distinct`, deleted last month | baseline diff: `token removed` · prose scan: every `--token` mention must resolve |
| 2 | A documented default no longer matches | the props table says `variant="default"`, the code says `"secondary"` | baseline diff: `default changed` / `prop default` |
| 3 | A hand-written contrast figure is now wrong | "4.92:1, passes AA" beside a ramp that was retuned | prose scan: every `N.NN:1` near a token pair is recomputed |
| 4 | A component doc for a deleted component | a page for `tooltip`, removed in March | `orphan-doc` gap |
| 5 | An undocumented new component | shipped three sprints ago, still has no page | `undocumented-component` gap · baseline diff: `component added` |
| 6 | A code example that no longer works | copies a `var()` that is gone, or styles a part that never existed | example extraction + `audit_design.py` · `--check` reference validation |

Each is a different mechanism, and no single one catches the others. A baseline diff cannot see a wrong sentence; a prose scan cannot see a socket that was quietly renamed; neither can tell you an example stopped compiling. All three run.

### The one that gets missed

Failure 3 is the one worth building the whole gate for. The other five are annoyances — a reader hits a dead link, shrugs, and greps. A wrong contrast figure is *actioned*: a reviewer looks it up precisely because they are being careful, gets a confident number, approves, and ships the accessibility failure **through the documentation**. The care is what makes it dangerous. Without the page, that reviewer would have measured.

---

## 2. The baseline diff

`system.json` is committed. Every CI run extracts a fresh one and compares.

```bash
python -m scripts.extract_system styles/ src/ --out build/system.json
python -m scripts.build_docs build/system.json --baseline docs/system.json \
       --prose docs/prose --check
```

What the diff reports, and why each line is phrased the way it is:

| Change | Reported as |
|---|---|
| token added / removed | removal names the old value, because every page that mentions it is now wrong |
| token value changed | old → new |
| **token re-resolved** | the token's own declaration did not change; something it references did |
| tier changed | Tier 1 → Tier 2 is a change in *who may read it*, which is an API change |
| contrast changed | old → new, with `** now below 4.5:1 **` when it crosses the threshold |
| component added / removed | removal notes that its page now documents something gone |
| socket added / removed | removal is flagged as **a breaking change to a published API** |
| socket default changed | old → new |
| state added / removed | a removed state is a regression until proven otherwise |
| prop added / removed / default changed | old → new |

**The re-resolution line is the one that earns the tool.** Change `--accent-600` by one step and the direct diff is a single line. The full report is nine, because `--bg-accent`, `--border-focus` and both rings of `--shadow-focus` all point at it, in two themes, and one contrast pair crossed 4.5:1. Nobody making that one-line change traces that chain by hand, and the page that quotes the old ratio is three directories away.

```
token changed    --accent-600: oklch(56.5% 0.176 42) → oklch(62.0% 0.190 42)
token re-resolved --bg-accent [light]: #c64600 → #df5200 (its own value did not
                 change — something it references did)
contrast changed --fg-on-accent on --bg-accent [light]: 4.92:1 → 3.94:1
                 ** now below 4.5:1 **
components/button.md:18: states 4.92:1; measured 3.94:1, 5.84:1
```

Four findings from one number. The last one is a sentence a person wrote.

---

## 3. Checking hand-written claims

The prose is not generated, so the baseline diff cannot see inside it. It is scanned instead, on every `--check` run, for the three kinds of claim that can go stale:

**Token mentions.** Every `--token-name` in every prose file must exist as a token or as a socket. A mention that does not resolve is reported with its file and line. This is cheap, catches failure 1 completely, and has almost no false-positive rate — the syntax is distinctive enough that a `--token` in prose is essentially always a reference.

**Contrast figures.** Any `N.NN:1` on a line is checked against the measured value for any token pair named on the same line. Three outcomes:

- it matches a measured pair — silence;
- it matches none of them — `states 4.92:1; measured 3.94:1, 5.84:1`, with the real values;
- the line names no measurable pair at all — reported as an **unverifiable** number, because a ratio in a doc that cannot be traced to two tokens is a number nobody can ever maintain. That finding is not a nag. It is the request to rewrite the sentence so that the next tool run can check it.

**Component pages.** A file at `prose/components/<name>.md` whose `<name>` is not a component in the source is failure 4, reported by path.

The deeper point: **write prose that is checkable.** "`--fg-subtle` on `--bg-sunken` measures 4.60:1" is a sentence a machine can verify forever. "Our muted text passes AA on most backgrounds" is a sentence nobody can ever check, which means it will be wrong eventually and nothing will notice. Naming the tokens is not pedantry; it is what converts a claim into a test.

---

## 4. Every code example is linted like source

**A wrong example is worse than a missing one**, because people copy examples and nobody copies an absence. An example is production code that happens to live in a markdown file, and it gets the same gate.

Two layers.

### Extraction and audit

```bash
python -m scripts.build_docs build/system.json --out build/docs \
       --emit-examples build/examples
python -m scripts.audit_design build/examples --strict
```

Every fenced block with a known language is written out as a real file — `.css`, `.scss`, `.tsx`, `.jsx`, `.ts`, `.js`, `.html` — under a name derived from its source page, and then audited exactly like the rest of the codebase. An example that hardcodes a colour, sets a child margin, reads a Tier-1 primitive or reaches for `!important` fails the build, in the docs, where it would otherwise teach several hundred people to do the same.

This is not hypothetical politeness. Documentation examples are the single most-copied code in any design system, and they are traditionally the least reviewed: they are written once, in prose, by someone explaining a thing rather than shipping it.

### Reference validation

`--check` additionally verifies, without running a browser:

- every `var(--x)` in an example resolves to a token or a socket that exists;
- every `.component__part` it styles is a part the component actually publishes.

```
components/card.md: example 1 uses `--pad-gone`, which is not a token or a socket
components/card.md: example 1 styles `.card__missing`, which is not a part this
                    component publishes
```

The second one is subtle and worth the code: an example that styles a part which was renamed still *lints* clean — it is valid CSS, it just silently does nothing. Only the system model knows it is wrong.

---

## 5. What a good drift report looks like

Four properties, learned from the reports that get ignored:

**Readable, not a JSON dump.** The reader is a developer who just changed one line and is now looking at CI output. A diff of two 200KB JSON files is technically complete and practically useless; nobody has ever found a contrast regression in one.

**Every line says what changed and why it matters.** `socket removed button.--button-radius` is a fact. `socket removed — a published CSS API was deleted; this is a breaking change` is a fact plus the consequence, and the consequence is the part that changes what the developer does next.

**Grouped by cause, not by file.** One token change producing nine findings should read as one event. The re-resolution lines explicitly say the token's own declaration did not change, so the reader looks upward for the cause instead of investigating nine symptoms.

**It names the fix.** The report ends with the instruction: re-run the extractor, fix every hand-written claim listed, and commit it all in the same change as the cause. A gate that reports without instructing gets satisfied by whatever makes it quiet, which is usually deleting the check.

---

## 6. Gate wiring

Four commands, four different failure modes, all cheap:

```bash
# 1. the code obeys the laws (Law 9)
python -m scripts.audit_design src/ --strict

# 2. extract, and fail on error-severity gaps
python -m scripts.extract_system styles/ src/components/ \
       --prose docs/prose --out build/system.json --report --strict

# 3. build; the site's own chrome and every example are audited like source
python -m scripts.build_docs build/system.json --out build/docs --prose docs/prose \
       --emit-css build/docs-chrome.css --emit-examples build/examples
python -m scripts.audit_design build/docs-chrome.css --strict
python -m scripts.audit_design build/examples --strict

# 4. nothing drifted since the committed baseline
python -m scripts.build_docs build/system.json --baseline docs/system.json \
       --prose docs/prose --check
```

As a workflow:

```yaml
name: design-system-docs
on: [pull_request]

jobs:
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }

      - name: Audit the source
        run: python -m scripts.audit_design src/ --strict

      - name: Extract the system
        run: |
          python -m scripts.extract_system styles/ src/components/ \
            --prose docs/prose --out build/system.json --report

      - name: Build the site
        run: |
          python -m scripts.build_docs build/system.json --out build/docs \
            --prose docs/prose --emit-css build/docs-chrome.css \
            --emit-examples build/examples

      - name: The site and its examples obey the laws too
        run: |
          python -m scripts.audit_design build/docs-chrome.css --strict
          python -m scripts.audit_design build/examples --strict

      - name: Drift gate
        run: |
          python -m scripts.build_docs build/system.json \
            --baseline docs/system.json --prose docs/prose --check

      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: docs-site, path: build/docs }
```

Three details that matter more than they look:

- **`if: always()` on the upload.** A site you can only download when the build passed is a site you can never use to investigate why it failed.
- **The chrome stylesheet carries no `@generated` marker.** `audit_design.py` skips generated files, so marking it would turn step 3 into a no-op that reports success. A skipped audit proves nothing, and a green check that proves nothing is worse than no check.
- **Extraction does not use `--strict` in the workflow above.** Existing gaps should not block unrelated pull requests on day one; turn it on once the list is empty, or baseline it. The drift gate is the one that must be strict from the first day, because it only ever fires on something this change caused.

---

## 7. Keeping the gate alive

A drift gate dies in one of three ways, and all three are preventable.

**It fires on things nobody caused.** Usually a timestamp in `system.json`, occasionally an unsorted collection. The output must be byte-stable on unchanged input, or the team learns within a week that red means nothing. Test it: run the extractor twice and diff.

**Updating the baseline becomes routine and unreviewed.** A commit that only updates `docs/system.json` is unreviewable — forty numbers moved and the diff contains no reason. **Commit the baseline in the same change as the code that moved it**, where it reads as "this token changed, so these forty numbers changed" and a reviewer can check the one line that mattered.

**The findings are noise.** This is the slow death. An unreferenced Tier-1 ramp step reported at the same severity as a deleted socket teaches people to skim, and a skimmed report is an ignored report. Severity has to discriminate: `error` for things that are wrong, `warning` for things that are probably wrong, `info` for things that are worth knowing once. If more than a handful of `error`s are open and nobody is acting on them, the calibration is wrong, not the team.

And one rule that is worth more than the gate: **values are never typed by hand again.** The gate catches the rot; this prevents it. The first person to paste a number into a page is the person who restarts the cycle, and no amount of CI will find the one they paste correctly today and that goes stale next quarter — because the gate can only check a claim that names its tokens.

---

## The three sentences to remember

1. **A stale doc is worse than a missing one**, because a careful reader acts on it instead of measuring, and the care is what makes it dangerous.
2. **Every code example is extracted and linted like source** — examples are the most-copied and least-reviewed code in any design system.
3. **Write claims that a machine can check** — "`--fg-subtle` on `--bg-sunken` measures 4.60:1" is verifiable forever; "our muted text passes AA" is wrong eventually and nothing will ever notice.

Related: `references/extraction.md` (what the baseline is made of), `references/documentation-model.md` (what belongs in prose in the first place), `web-design-studio/scripts/audit_design.py` (the gate this one runs beside).
