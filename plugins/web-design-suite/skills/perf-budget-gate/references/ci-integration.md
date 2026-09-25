# Making the Gate Stick

A performance gate fails for one reason: it cries wolf. A job that goes red because a CI runner was busy teaches a team that red means "re-run it", and three weeks later somebody deletes the job. Everything below is aimed at one target — **a failure must mean something changed, and nothing else.**

---

## 1. Where each layer runs

The two layers have different costs and different reliability, so they belong in different places.

| | `perf_audit.py` (static) | `measure_vitals.mjs` (runtime) |
|---|---|---|
| Runtime | ~1 second | ~1 minute for 5 runs |
| Determinism | **Total** | Variable, needs care |
| Needs | Python 3, nothing else | A browser, a served build |
| Runs on | **every commit** — pre-commit + PR | **PR**, and on main after merge |
| Blocks a merge | Yes, hard | Yes, with headroom |
| Answers | "did the artifact change?" | "did the experience change?" |

**Install the static layer first and get it green before you add the runtime layer.** Most teams do the opposite: they start with Lighthouse in CI, get flaky results in the first week, add `continue-on-error: true`, and now have a job that measures nothing. The static layer catches most real regressions — an un-preloaded font, a lazy-loaded LCP image, a 900 KB hero, a bundle that grew 40% — deterministically, on every commit, for a second of CI time. Earn the trust there, then spend it.

---

## 2. Pre-commit: the static layer only

```bash
#!/usr/bin/env bash
# .githooks/pre-commit — design and performance, one gate
set -euo pipefail

CHANGED=$(git diff --cached --name-only --diff-filter=ACM)
[ -z "$CHANGED" ] && exit 0

# Law 9 — the code is clean.
python -m scripts.audit_design $CHANGED

# The build output is what ships, so weigh that, and scan source for markup
# problems in the files that actually changed.
if [ -d dist ]; then
  python -m scripts.perf_audit dist/ --src src/ --budget perf-budget.json
fi
```

Two things to get right:

- **Never put the runtime layer in a pre-commit hook.** A minute of browser time per commit is how a team discovers `--no-verify`.
- **Guard on `dist/` existing.** A hook that fails because somebody has not built yet is a hook that gets bypassed, and a bypassed hook protects nothing.

---

## 3. The PR job

```yaml
# .github/workflows/perf.yml
name: perf
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

      - run: npm ci
        env:
          PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD: '1'   # the image already has one

      - run: npm run build

      # Gate 1 — the design laws. Deterministic, one second.
      - name: design audit
        run: python -m scripts.audit_design src/ --strict

      # Gate 2 — the static performance budget. Deterministic, one second.
      - name: perf audit
        run: |
          python -m scripts.perf_audit dist/ --src src/ \
            --budget perf-budget.json \
            --baseline .perf-baseline.json \
            --json > perf-static.json || STATIC=$?
          python -m scripts.perf_audit dist/ --src src/ \
            --budget perf-budget.json --baseline .perf-baseline.json
          exit ${STATIC:-0}

      # Gate 3 — the real numbers. Slow, noisy, gated with headroom.
      - name: serve
        run: npx --yes serve dist -l 8080 &
      - name: wait for server
        run: npx --yes wait-on http://127.0.0.1:8080 -t 30000
      - name: measure vitals
        run: |
          node scripts/measure_vitals.mjs http://127.0.0.1:8080/ \
            --runs 7 --throttle slow4g \
            --budget perf-budget.ci.json \
            --json > perf-runtime.json
          node scripts/measure_vitals.mjs http://127.0.0.1:8080/ \
            --runs 0 --quiet || true

      - if: always()
        uses: actions/upload-artifact@v4
        with:
          name: perf-reports
          path: |
            perf-static.json
            perf-runtime.json
```

Notes, in order of how often they bite:

- **`if: always()` on the upload.** A report you can only download when the job passed is a report you can never use.
- **`PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`.** `measure_vitals.mjs` launches with an explicit `executablePath` and will never download. Set the env var anyway so `npm ci` does not pull 150 MB on every run.
- **A separate `perf-budget.ci.json` for the runtime gate.** Same schema, looser `lab` numbers. §4 explains why that is honesty rather than cheating.
- **Serve the build over HTTP.** `file://` has no network stack: TTFB is ~0, resource priorities do not apply, and throttling barely bites. Every number flatters you.

---

## 4. Keeping the runtime layer non-flaky

Each item below removes one class of false failure. Skipping any one of them will cost you more time than implementing all of them.

| Source of variance | What to do | Where |
|---|---|---|
| A single run is a rumour | `--runs 5` minimum, 7 if you can afford it; the **median** is reported | built in |
| Cold vs warm cache | Fresh context per run; `--warm` is a separate, deliberate measurement | built in |
| Browser version drift | **Pin it.** Chromium 140 and 141 do not schedule identically. Pin the Playwright version in `package-lock.json` and the binary in the image. | yours |
| CPU contention on the runner | 4× CPU throttling via CDP makes the *relative* cost stable, not the absolute | `--throttle` |
| Network variance | CDP network emulation, so the numbers do not depend on the runner's uplink | `--throttle` |
| Timezone / locale drift | `locale: 'en-US'`, `timezoneId: 'UTC'` on the context | built in |
| OS colour scheme leaking in | `colorScheme: 'light'` pinned | built in |
| Late shifts missed | `--settle 3000` after load before reading the observers | `--settle` |
| Real third-party origins | They change under you and can be down. **Record and replay, or stub them.** | yours |
| Different geography per runner | Pin the runner region, or accept that absolute numbers are not comparable across regions | yours |

### The headroom argument

**CI runners are noisy, and no amount of throttling makes them quiet.** A shared virtual machine with unpredictable neighbours will produce a 15–25% spread on LCP even on an unchanged page. `measure_vitals.mjs` prints that spread and warns when it exceeds 25%.

So a CI threshold set at the Core Web Vitals "good" line will go red on a page that did not change. The honest response is **not** to pretend the noise is not there, and **not** to disable the job. It is to run two different budgets:

| Budget | LCP | Used by | Meaning |
|---|---|---|---|
| **The real one** — `perf-budget.json` | 2500 ms | the team, the roadmap, field verification | the promise you made |
| **The CI one** — `perf-budget.ci.json` | 3200 ms | the PR gate | the promise plus measured runner noise |

Set the CI number empirically: run the job **ten times on an unchanged main**, take the maximum observed median, and add 10%. Write that procedure in a comment in the file, and re-run it whenever you change runner type or browser version.

**Then make the gap visible.** The CI gate at 3200 ms is not the goal — it is the noise floor. If your real median sits at 3100 ms, CI is green and you are failing your users. That is why the field data loop in §7 is not optional.

An alternative worth knowing: gate on the **delta against main** rather than an absolute number. Measure the PR branch and main in the same job on the same runner, and fail if the PR is more than X% worse. This cancels most runner noise, at the cost of doubling the job time and being blind to slow drift.

---

## 5. Adopting it on a site that is already slow

The gate must be able to go on **today**, on a site that is comprehensively over budget, without failing. Otherwise it goes on "after the perf sprint", which is to say never.

```bash
# 1. Look at the damage. Do not fix anything yet.
python -m scripts.perf_audit dist/ --budget perf-budget.json

# 2. Freeze it. Records today's findings AND today's byte totals.
python -m scripts.perf_audit dist/ --budget perf-budget.json \
  --write-baseline .perf-baseline.json
git add .perf-baseline.json

# 3. Turn the gate on. It is green.
python -m scripts.perf_audit dist/ --budget perf-budget.json
```

From here:

- **Existing violations do not fail.** They are recorded by a key that excludes the line number, so unrelated edits above them do not resurrect them.
- **New violations fail immediately.** The debt stops growing the day you commit the baseline, which is the entire point.
- **Growth still fails.** The baseline stores byte totals per category, so a PR that adds 40% to the JS bundle fails against `growth.js_pct` even though the absolute budget was already blown. This is the check that does the most work on a legacy codebase, because it is the only one that can be green on day one and still catch a real regression on day two.

Pay the debt down **per page type or per directory**, not all at once, and re-record the baseline in the same commit as the fix so the diff shows both. A baseline update on its own is unreviewable; a baseline update next to the change that earned it reads as "this got better, so this line disappeared".

---

## 6. Reporting a regression so it gets fixed

A gate that fails with `Error: budget exceeded` produces a re-run, not a fix. Three things turn a red build into an action:

**1. Name the delta, not the state.** "js is 210 KB" invites "so?". "js grew +40 KB (+31%) since main: 130 KB → 170 KB" names a commit.

**2. Put it where the argument is happening.** A PR comment, not a log file forty scrolls deep.

```bash
python -m scripts.perf_audit dist/ --json > perf.json
node -e '
  const d = require("./perf.json");
  const rows = d.findings.filter(f => f.severity === "error")
    .map(f => `| ${f.cat} | \`${f.rule}\` | ${f.message} |`);
  const led = d.ledger.bytes;
  console.log(`### Performance gate\n`);
  console.log(`| | bytes |\n|---|---|`);
  for (const [k, v] of Object.entries(led)) console.log(`| ${k} | ${(v/1000).toFixed(1)} KB |`);
  if (rows.length) console.log(`\n| | rule | what |\n|---|---|---|\n${rows.join("\n")}`);
' > comment.md
gh pr comment "$PR" --body-file comment.md
```

**3. Include the fix text.** `perf_audit.py`'s `fix` field explains the mechanism, not just the rule — that is deliberate, because a developer who understands *why* a lazy LCP image costs a second fixes it once and never writes it again. Do not strip it with `--quiet` in the report that humans read; `--quiet` is for machine consumption.

One more that costs nothing: **post the report on green runs too**, collapsed. A weight ledger in every PR makes size a thing people notice before it is a problem, which is worth more than any single gate.

---

## 7. One command, alongside the design gate

The two gates fail for different reasons and both failures are actionable, so run them together and give a reviewer one line to look at.

```json
{
  "scripts": {
    "gate": "npm run gate:design && npm run gate:perf",
    "gate:design": "python -m scripts.audit_design src/ --strict",
    "gate:perf": "python -m scripts.perf_audit dist/ --src src/ --budget perf-budget.json",
    "gate:vitals": "node scripts/measure_vitals.mjs http://127.0.0.1:8080/ --runs 7 --throttle slow4g --budget perf-budget.ci.json"
  }
}
```

The ordering is deliberate. `audit_design.py` runs first because it is the cheapest and its failures are the most mechanical. `perf_audit.py` runs second on the **build output**, which means it needs a build and therefore belongs after. `measure_vitals.mjs` runs only in CI, only on a served build.

They overlap in exactly one place, and it is the right one. `audit_design.py` flags `transition: all` as a design violation (it animates properties nobody chose); `perf_audit.py` flags a transition on `width` as a performance one (it relayouts every frame and shifts siblings). Same line of CSS, two independent reasons, and a developer who sees both understands the rule better than one who sees either.

**Exit codes are identical across all three** — `0` clean, `1` violations, `2` bad invocation — so `&&` chaining does the right thing and no wrapper script is needed.

---

## 8. Closing the loop with field data

Everything above gates on a proxy. The thing that actually matters is **p75 of real user data**, and no CI job can produce it.

```
  PR ──► static gate ──► runtime gate ──► merge ──► deploy
                                                      │
                                                      ▼
                                              field data (CrUX / RUM)
                                                      │
                                     ┌────────────────┘
                                     ▼
                     does the lab profile still describe reality?
```

Three habits, in order of value:

1. **Ship a RUM library** (`web-vitals` is ~2 KB) and record LCP, INP and CLS with attribution. Segment by device class, connection and route. This is the only way to know which of your pages is actually slow.
2. **Check CrUX monthly** for the origin. It is free, it is p75, it is 28-day rolling, and it is what search actually sees.
3. **When lab and field disagree, the field is right.** Your throttle profile, device class or measured page is wrong. Fix the profile — do not argue with the users.

The concrete trigger to re-derive: **field p75 is more than 1.5× your lab median.** That means the lab is measuring a page, a device or a network your users do not have, and every budget downstream of it is aimed at the wrong target. Re-run the derivation in `references/budgets.md` §1 with the device and connection your analytics actually show.
