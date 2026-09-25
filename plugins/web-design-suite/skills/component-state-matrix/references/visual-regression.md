# Visual Regression Without the Burden

Screenshot diffing fails for one reason: it cries wolf. A suite that fails on a font-hinting difference teaches a team that red means "re-run it", and three weeks later somebody deletes the job. Everything below is aimed at the same target — **a failure must mean something changed on purpose or by accident, and nothing else.**

---

## 1. Screenshot components, not pages

| | Page-level | Component-level (this skill) |
|---|---|---|
| A padding change in one button | one huge diff | one cell |
| A new section added above | every following pixel differs | nothing |
| "What broke?" | read the image | read the filename |
| Baseline churn per release | high | proportional to actual change |
| Flake surface | the whole page | one box |

The generated proof sheet puts a `data-cell-id` on every stage, and `snapshot_matrix.mjs` calls `element.screenshot()` on each one. A failing run names the cell:

```
fail   button--p_state--f_default--v_primary--s_default--st_hover--d_comfortable--t_dark
```

That string *is* the bug report: primary button, hover, dark, comfortable. You have not opened the image yet and you already know where to look.

The corollary: **do not screenshot the chrome.** The cell's label, the row header and the grid rules are not under test, and including them means renaming a row invalidates every baseline in it. The `data-cell-id` sits on `.msheet__stage` — the themed canvas plus the component — and nothing else.

---

## 2. Deterministic rendering

Every item here removes one class of false failure. Skipping any one of them will cost you more time than implementing all of them.

| Source of nondeterminism | Fix | Where in `snapshot_matrix.mjs` |
|---|---|---|
| Web fonts still loading | `await document.fonts.ready` before the first shot | page setup |
| Animations mid-flight | `animation-play-state: paused`, `animation-delay: -1ms` | `FREEZE_CSS` |
| Transitions mid-flight | `transition-duration: 1ms` (not `0` — `transitionend` still has to fire) | `FREEZE_CSS` |
| Motion preference | `reducedMotion: 'reduce'` on the context | context options |
| Blinking text caret | `caret-color: transparent` + `caret: 'hide'` | `FREEZE_CSS`, screenshot opts |
| Scrollbars appearing at some widths | `scrollbar-width: none`, `--hide-scrollbars` | `FREEZE_CSS`, launch args |
| `Date.now()` in rendered content | freeze `Date` before page scripts run | `STUB_JS` via `addInitScript` |
| `Math.random()` in rendered content | seeded xorshift | `STUB_JS` |
| Locale / timezone drift between machines | `locale: 'en-US'`, `timezoneId: 'UTC'` | context options |
| OS dark-mode preference leaking in | `colorScheme: 'light'` — the sheet sets `data-theme` itself | context options |
| Subpixel text antialiasing | `--disable-lcd-text`, `--font-render-hinting=none` | launch args |
| Colour management | `--force-color-profile=srgb` | launch args |
| Device pixel ratio | `deviceScaleFactor` pinned (default 1) | context options |
| Layout not settled after injecting CSS | two `requestAnimationFrame`s | page setup |

Two that are **not** in the script and are yours to own:

- **Fonts must be local.** A Google Fonts request that is slow or blocked renders a fallback face and diffs every text cell. Self-host, or embed as base64, or set `font-display: block` and wait. Never fetch a font over the network in a visual test.
- **The browser build must be pinned.** Chromium 140 and Chromium 141 do not rasterise identically. Pin the Playwright version in `package-lock.json` and pin the browser binary in the image. A browser upgrade is a baseline-refresh event; plan it like one.

---

## 3. The anti-flake checklist

Run before you turn the job on, and again whenever someone says "it's flaky".

- [ ] Run the suite **three times** against unchanged code. Any cell that fails once is flaky; fix the cause, do not raise the threshold.
- [ ] Run it on CI hardware, not only on a laptop. Different GPU, different rasteriser.
- [ ] Run it in the **container the CI uses**, with the same fonts installed. Missing fonts is the number-one cause of "passes locally, fails in CI".
- [ ] Confirm no cell contains a date, a relative time ("2 minutes ago"), a random ID, or a live avatar URL.
- [ ] Confirm every image in a fixture is local and committed.
- [ ] Confirm the viewport is fixed and no cell depends on the window height.
- [ ] Confirm the sheet has no `position: fixed` chrome overlapping a cell.
- [ ] Confirm the run is serial, or that parallel workers each get their own browser context.

If a cell is genuinely nondeterministic and cannot be fixed — a live map, a video frame — **exclude it**, do not loosen the global threshold for it. One excluded cell with a comment is honest; a threshold of 0.05 to accommodate it makes every other cell in the suite blind to a 5% change.

### Excluding honestly

Two ways, in order of preference:

1. **Fix the fixture.** A cell showing "2 minutes ago" should show a frozen timestamp. A cell fetching an avatar should reference a committed PNG. Nine times in ten the nondeterminism is in the content fixture and you wrote that fixture yourself.
2. **Drop the component from the manifest's `states` or `content`, with a `note` saying why.** The component is then visibly absent from the sheet rather than silently passing.

What not to do: keep the cell and raise `--threshold`. A global knob turned to accommodate one cell blinds every other cell in the suite, and nothing in the repo records that that is what happened.

### Triaging a red run

| Pattern in the failing cell ids | Almost always |
|---|---|
| every id contains `t_dark`, none contains `t_light` | a colour that dark mode cannot re-point, or a shadow resolved against the wrong canvas |
| every id contains `p_density` | a padding or radius that stopped scaling |
| all ids share one `v_` value | a variant's sockets changed — check whether you meant to |
| all ids share one `st_` value | a state rule changed, or a new state rule now matches where it did not |
| one component, every cell | the component's root rule or a token it reads |
| every component, every cell | a token, a font, or the browser version |
| a scattering with no pattern, all just over threshold | flake — go back to the checklist above, do not raise the threshold |

Read the ids before you open a single image. Most of the time the pattern tells you the cause and the images only confirm it.

---

## 4. Thresholds

### Why per-pixel is the wrong metric

A naive comparator asks "is `rgb(51,51,51)` equal to `rgb(52,51,51)`?" and says no. That metric has two failure modes at once:

- **Too sensitive** where it does not matter: a 1/255 shift in a shadow's alpha fails the run.
- **Too blind** where it does: it weights a blue-channel change the same as a green-channel change, though the eye is roughly six times more sensitive to green. A perceptually large change can score the same as an invisible one.

`snapshot_matrix.mjs` compares in **YIQ** space, weighting luma far above chroma, then normalises to 0..1:

```
Δ = 0.5053·ΔY² + 0.299·ΔI² + 0.1957·ΔQ²
```

That is the same metric `pixelmatch` uses, implemented on a canvas inside the browser so there is no native module to install. A pixel counts as different only when `Δ` exceeds `--pixel-threshold`, **and** no pixel in its 3×3 neighbourhood in the other image is within tolerance. The neighbourhood escape is what makes sub-pixel antialiasing free: a glyph edge that moved a third of a pixel has a near-identical neighbour; a button that turned red does not.

### The two knobs

| Flag | Asks | Default | Raise it when |
|---|---|---|---|
| `--pixel-threshold` | how different does *one pixel* have to be to count | `0.03` | your renderer has unavoidable antialiasing jitter |
| `--threshold` | what fraction of pixels may count before the cell fails | `0.002` | never, as a reflex — see below |

`0.002` of a 300×200 cell is 120 pixels. That is about one glyph's worth of antialiasing and nothing more. It will catch a 1px padding change, a radius change, a border colour change, and any fill change. The per-pixel default matters as much: at `0.10` (a distance of ~352) the suite's own 4% hover overlay (~51) and 8% pressed overlay (~210) were invisible, so deleting `:hover` or `:active` passed every cell. At `0.03` (~32) both count.

Every run also checks, with no baseline at all, that each hover, active and focus-visible cell **differs** from its default cell. A state that renders pixel-for-pixel like default has no style for that state; it fails on the first run instead of being recorded as a baseline and enshrined.

**Do not tune `--threshold` to make a failure go away.** Tune it once, on a clean tree, to the point where three consecutive runs pass with margin, and then leave it. If a real change is passing under it, lower it. The value belongs in the CI config with a comment saying who chose it and why — a threshold nobody can explain is a threshold that drifts upward forever.

**Size changes bypass the threshold entirely.** If the baseline is 148×44 and the current is 148×48, the cell fails with `size changed 148x44 → 148x48` and no ratio is computed. A box that changed size is always a design change, never noise.

---

## 5. Reviewing and accepting intentional diffs

Most diffs are intentional. The workflow has to make accepting them cheap, or people stop making intentional changes.

```
1. Change the CSS.
2. Regenerate the sheet.          python -m scripts.generate_matrix matrix.json --out build/sheet.html
3. Run the diff.                  node snapshot_matrix.mjs build/sheet.html --baselines tests/visual/baselines
4. Open build/matrix-report/index.html. Failures first, worst first.
5. For each failure, answer ONE question: did I mean to do this?
      yes -> continue
      no  -> fix the CSS, go to 2
6. Accept:                        node snapshot_matrix.mjs ... --update-baselines
7. Commit the CSS change and the baseline change IN THE SAME COMMIT.
```

Step 7 is the one that matters. A baseline update in its own commit is unreviewable — the reviewer sees a wall of binary changes with no cause. In the same commit, the diff reads: *"padding changed here, and these 14 images changed as a result."* That is a review a person can do.

Three rules for the review:

- **A diff you cannot explain is a bug, not a baseline update.** `--update-baselines` on a failure you did not investigate converts a caught regression into a permanent one.
- **Count the cells.** Change one button variant and 14 cells fail? Plausible. Change one button variant and 140 cells fail? You touched a token, not a component — go and look at what else reads it.
- **Read the cell ids before the images.** If every failing id contains `t_dark` and none contains `t_light`, you have a theme bug, and you knew that before opening a single PNG.

### New cells and orphan baselines

| Status | Meaning | Fails the run? |
|---|---|---|
| `new` | a cell with no baseline | **yes**, by default — an unreviewed cell is not a passing cell. `--allow-new` opts out. |
| `orphan` | a baseline with no cell | no — it is reported, and `--update-baselines --prune` removes it |

A *renamed* cell produces both at once: `new` for the new id, `orphan` for the old. The `new` is what fails the run, which is correct — the renamed cell has never been looked at.

---

## 6. Storing baselines

There is no free option. Pick deliberately.

| | In the repo | Artifact / object storage |
|---|---|---|
| Review | in the PR diff, next to the cause | a link, in another tab |
| Setup | none | a bucket, credentials, a retention policy |
| Repo size | grows forever; PNGs do not delta-compress | flat |
| `git clone` | slower every release | unaffected |
| Bisecting an old regression | works | depends on retention |
| Offline / forks | works | needs credentials |

**Default to in-repo**, and keep it viable with three habits:

1. **Keep cells small.** A 300×200 PNG of a button is ~4 KB. A full-page screenshot is 400 KB. This is the strongest argument for component-level shots after reviewability.
2. **Prune orphans every time.** `--update-baselines --prune` on the release commit.
3. **Watch the number.** Past roughly 2,000 baselines or 50 MB, move to object storage or Git LFS. Below that the review benefit wins easily.

The pruned profile is what keeps you under that line: 108 cells per component instead of 1,260.

---

## 7. CI wiring

Run the auditor and the matrix as two gates in one job. They fail for different reasons and both failures are actionable.

```yaml
# .github/workflows/design.yml
name: design
on: [pull_request]

jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm }
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      # Deps. The browser is already in the image; never download one here.
      - run: npm ci
        env:
          PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD: '1'

      # Gate 1 — Law 9. The code is clean.
      - name: audit
        run: python -m scripts.audit_design src/ --strict

      # Build the sheet, and audit the sheet's own chrome while we are here.
      - name: build proof sheet
        run: |
          python -m scripts.generate_matrix matrix.json \
            --out build/proof-sheet.html \
            --emit-css build/matrix-chrome.css \
            --strict
          python -m scripts.audit_design build/matrix-chrome.css

      # Gate 2 — the result is clean.
      - name: visual regression
        run: |
          node scripts/snapshot_matrix.mjs build/proof-sheet.html \
            --baselines tests/visual/baselines \
            --out build/matrix-report \
            --threshold 0.002

      - if: always()
        uses: actions/upload-artifact@v4
        with:
          name: matrix-report
          path: build/matrix-report
```

Notes on that file, in order of how often they bite:

- **`if: always()` on the artifact upload.** A report you can only download when the job passed is a report you can never use.
- **`PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`.** `snapshot_matrix.mjs` launches with an explicit `executablePath` and will never download. Set the env var anyway so `npm ci` does not either — otherwise every CI run pulls ~150 MB.
- **`--strict` on `generate_matrix`** fails the build on a state-coverage gap. Turn it on once the existing gaps are closed, not before; a permanently-red gate is a disabled gate.
- **Two gates, not one job each.** They share the checkout and the deps, and a reviewer wants both results on one line.

For non-GitHub CI the shape is identical: install, audit, generate, snapshot, upload the report directory.

---

## 8. The cheaper alternative

Some teams will not adopt Playwright, and that is a legitimate position — it is a browser binary, a CI image, a baseline store and a review habit. The proof sheet still earns its keep without any of it.

**The static review ritual:**

1. Generate the sheet on every release branch: `python -m scripts.generate_matrix matrix.json --out proof-sheet.html`.
2. Commit it, or attach it to the release ticket. It is one self-contained HTML file with no external requests — it opens from a file:// URL, an email attachment, or a shared drive.
3. One person scrolls it, in this order: **focus-visible row → dark theme column → compact density → the content pass**. Ten minutes.
4. Print it. The sheet ships a print stylesheet that drops the controls, un-sticks the axis headers and keeps each pass on one page. A printed matrix on a desk gets marked up by people who would never open a CI report.

What you keep: state coverage flags, the density proof, the dark-mode proof, the content-fixture proof, and a shared artefact the whole team can point at.

What you lose: the ability to catch a one-pixel regression, and the guarantee that somebody actually looked.

**The honest middle:** run the static ritual at each release, and add the snapshot job later, for the three components that break most often, using `--only`:

```bash
node snapshot_matrix.mjs build/proof-sheet.html --only button --only input --only table-row
```

A narrow suite that runs is worth more than a complete suite that is disabled.
