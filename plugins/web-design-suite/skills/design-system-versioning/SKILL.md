---
name: design-system-versioning
description: Version a design system or token library without breaking the projects that consume it — classify every change as major/minor/patch by whether a consumer's rendered output moves, generate the changelog and migration guide from the diff, deprecate a token or component with a codemod and a removal date, and roll the update out to several client projects, verified. Use for semver for design tokens, breaking changes in a design system, "we changed a token and something broke", renaming or removing a token, component or variant, writing a changelog or migration guide, upgrading a consumer to a new design-system version, and managing a component API over time. Reach for it whenever anyone mentions a version bump, a breaking change, a deprecation, a codemod, a changelog, pinning a design-system version, "is this a major", or a client project that is several versions behind.
---

# Design System Versioning

> **Running the scripts** — by path, from the user's project root, so `src/`
> means the project's `src/` and every output lands in the project, never
> inside this plugin:
>
> ```bash
> python "${CLAUDE_SKILL_DIR}/scripts/diff_system.py" published/system.json build/system.json
> ```
>
> The commands below are written `python -m scripts.<name>`. That form is for a project that
> has copied the scripts into its own `scripts/` folder, as CI and git hooks
> do; when you run one here, use the path form.
> This skill's scripts are in `${CLAUDE_SKILL_DIR}/scripts/` (deprecate.py, diff_system.py).
> From sibling skills: `${CLAUDE_PLUGIN_ROOT}/skills/web-design-studio/scripts/audit_design.py`; `${CLAUDE_PLUGIN_ROOT}/skills/design-system-docs/scripts/build_docs.py`; `${CLAUDE_PLUGIN_ROOT}/skills/design-system-docs/scripts/extract_system.py`; `${CLAUDE_PLUGIN_ROOT}/skills/web-design-studio/scripts/generate_color_ramp.py`; `${CLAUDE_PLUGIN_ROOT}/skills/component-state-matrix/scripts/snapshot_matrix.mjs`.

The suite now produces ten kinds of artifact and has no story for **changing** them.

Here is the failure, concretely. Someone re-points `--bg-accent` from the 600 step to the 500 step to fix a contrast complaint. It is one line. It ships as a patch, because no name changed and nothing broke. Three client sites take it on their next dependency refresh. Two of them have a secondary button with 14px white text on that fill, which now measures **3.56:1** where it measured 4.92:1. Nothing failed. No test went red. Nobody notices for a month, and the person who finds it is a client.

Every step of that is reasonable and the outcome is an accessibility regression shipped to production through a patch release. The defect is in the classification, and the classification is wrong because it asked the API question.

---

## The key insight

Semver was written for APIs, where "breaking" means a caller stops compiling. A design system has a second surface no compiler sees — **the rendered output** — and a consumer who changes nothing can still wake up to a different button. So the question is never "did a name disappear". It is:

> **Does a consumer's rendered output change in a way they did not ask for?**

That reframing does not map cleanly onto how semver is usually taught, and the places it diverges are exactly where the damage happens:

| Change | Semver instinct | Correct here | Why |
|---|---|---|---|
| Rename a Tier-2 role | major | **major** | Agreed. The easy one. |
| **Re-point a Tier-2 role** | patch — nothing broke | **major** | Same name, same call site, different pixels. Nothing complains, which is what makes it dangerous. |
| Add a Tier-2 role | minor | **minor** | Agreed. Nobody reads it yet. |
| **Change a Tier-1 primitive's value** | patch — it is internal | **major** | It is the root of a reference tree. Everything downstream re-renders, and the blast radius is a page, not a line. |
| **Change a socket's default** | minor — additive-ish | **major** | Every consumer who did *not* override it renders differently. That is most of them. |
| **Remove a variant** | major | **major**, and the worst shape | `data-variant="quiet"` stays legal HTML and renders as the base variant. No error anywhere. |
| Rename a class under CSS Modules | major | **patch** | The rendered name was hashed and never depended on. The exported key still is. |
| Change DOM with no visual change | patch | **major** | Their descendant selectors and their tests were written against your markup. |

The full taxonomy — every kind of change, its verdict, what a consumer sees, whether a tool can detect it, and the migration burden — is `references/change-classification.md`. It is the content of this skill; everything else is machinery for applying it.

---

## The four moments you reach for this

| You are about to | You need first |
|---|---|
| Pick a version number for a release | the diff, the blast radius, the contrast deltas — §3 of the workflow |
| Rename or delete something with consumers | the deprecation contract and the shim — `references/deprecation.md` §1, §4 |
| Take a new version into a client project | the migration guide and the visual diff — `references/rollout.md` §3, §4 |
| Explain why a client's site changed | the diff between the version they were on and the one they took |

The last row is the one people arrive with, usually phrased as *"we changed a token and something broke"*. Run the diff between their two versions first; the answer is almost always a re-point or a primitive edit that shipped as a patch, and the contrast table usually names the symptom before the client does.

---

## Workflow

### 1. Snapshot the current system

```bash
python -m scripts.extract_system styles/ src/components/ --out published/system.json
```

That is `design-system-docs`' extractor, and its `system.json` is the snapshot format this skill reads. **Commit it, tagged with the release.** A version you cannot diff against is a version you cannot reason about, and the snapshot is deterministic — sorted, no timestamps — so it produces a reviewable diff rather than noise.

No snapshot yet? `diff_system.py` reads two `tokens.css` files directly. You lose the component layer — sockets, variants, states, props — which is where a third of the taxonomy lives.

### 2. Make the change

Normally, on a branch, with the audit gate green.

### 3. Classify it automatically

```bash
python -m scripts.diff_system published/system.json build/system.json \
       --from-version 1.4.2 --deprecations deprecations.json
```

Every change, its category, its severity, the consumer-facing description, the transitive blast radius, and the contrast delta for every pair that moved. Then a recommended bump with the reason.

Read it before you argue with it. It will already have found the thing you did not mean to change.

### 4. If it is breaking, provide the deprecation path *before* the removal

Not after. A deprecation a consumer has not had a chance to act on is a removal with an apology attached.

```bash
python -m scripts.deprecate add --name=--fg-subtle --kind token \
    --since 2.1.0 --removal 3.0.0 --replacement=--fg-faint \
    --reason "…" --source styles/tokens.css --mapping build/mapping.json
```

That records the promise in `deprecations.json`, injects a machine-readable marker above the declaration, and emits a codemod in `apply_codemod.py`'s own format. Then ship the **shim** — the old name aliased to the new one, for one minor version. It is ugly and it converts a major into a minor, which is the difference between an upgrade every client must schedule and one nobody has to think about.

### 5. Generate the changelog and the migration guide from the diff

```bash
python -m scripts.diff_system published/system.json build/system.json \
       --from-version 1.4.2 --format changelog        -o CHANGELOG.part.md
python -m scripts.diff_system published/system.json build/system.json \
       --from-version 1.4.2 --format migration-guide  -o UPGRADE-2.0.0.md
```

Generated, not written, for the same reason the docs are: a hand-written migration guide disagrees with the diff, and the diff is right. The guide carries breaking items only, each with what changed, **what you will see if you skip it**, the blast radius, and the command.

### 6. Roll it out per consumer, verified

Pin exactly. Canary one consumer to production first. Then, per consumer: read the guide, run the codemod, run the audit, run the proof sheet, **look at the visual diff**, commit the bump and the accepted baselines together.

Step 5 of that list is the acceptance test. A design-system upgrade that type-checks and lints clean can still be visually wrong; that is the normal case. `references/rollout.md` is the whole procedure.

---

## A worked release

Four edits to the canonical `tokens.css`, which is roughly what a real release looks like: one rename, one ramp nudge, one re-point, one addition, one comment.

```
RECOMMENDED BUMP   MAJOR   1.4.2 -> 2.0.0
because            tier-2 role renamed: --fg-subtle
changes            3 major · 1 minor · 1 patch

  [tier1-value-changed]  --accent-600
      value        #c64600  ->  #d45003
      blast·roles        2  --bg-accent, --border-focus
      blast·transitive   2  --elevation-focus, --shadow-focus

  [tier2-renamed]  --fg-subtle  ->  --fg-faint
      deprecation  MISSING — this is what the gate fails on

  [tier2-repointed]  --bg-accent
      value        #c64600  ->  #e75b12
      detail       var(--accent-600)  ->  var(--accent-500)

CONTRAST — 7 pair(s) moved
  light  --fg-on-accent on --bg-accent    4.92:1   3.56:1  CROSSED 4.5:1 DOWNWARD
         caused by --accent-600, --bg-accent
  light  --border-focus on --bg-surface   4.92:1   4.26:1  moved, no threshold crossed
```

Four things to notice, because they are the reason the tool exists:

- **The one-line ramp nudge is four roles deep.** `--accent-600` → `--border-focus` → `--shadow-focus` → `--elevation-focus`, plus `--bg-accent` in parallel. Nobody edited the last three; they are reported under their cause rather than as three more decisions.
- **The re-point is the accessibility regression**, and it is the change that looks most harmless in a diff. 4.92:1 → 3.56:1 is the scenario at the top of this file, caught before it shipped.
- **The focus ring moved too.** `--border-focus` against `--bg-surface` went 4.92 → 4.26. It is not text, so no linter has an opinion, and SC 1.4.11 still asks 3:1 of it.
- **Only the rename fails the gate.** The value change and the re-point are equally breaking and there is no deprecation record that could help them — a changelog entry and a visual diff are their remedy.

Record the deprecation, ship the shim, and the same rename classifies as **minor**: `--fg-faint` added, `--fg-subtle` re-pointed to it with an identical resolved value in both themes. That is one command's difference between a release every client must schedule and one nobody has to think about.

---

## The gate

```bash
python -m scripts.diff_system published/system.json build/system.json \
       --deprecations deprecations.json      # exit 1 if a name vanished unannounced
```

The gate asks one question: **did a name disappear that nobody was warned about?**

It is deliberately narrower than "is anything breaking". A value change and a re-point are breaking too, and a deprecation record cannot help a consumer whose pixels moved — only a changelog entry and a visual diff can. So removals and renames fail the gate, and everything else is reported. `--gate major` is there for teams who want a ledger record against every breaking change; `--gate none` turns it off.

Without `--deprecations` the gate is advisory and exits 0. A gate that fails on its first honest run gets wrapped in `|| true` within a week.

Wire it beside the gates it does not overlap with:

```bash
python -m scripts.audit_design src/ --strict                       # Law 9: the code
python -m scripts.build_docs build/system.json --baseline docs/system.json --check
python -m scripts.diff_system published/system.json build/system.json \
       --deprecations deprecations.json                            # the version
node scripts/snapshot_matrix.mjs build/proof-sheet.html \
     --baselines tests/visual/baselines --out build/matrix-report  # the pixels
```

Four failures, four different causes, all actionable.

---

## What the diff finds that nobody asked for

| Finding | Why it matters |
|---|---|
| **Transitive blast radius** | One primitive edit, and the report names the roles that read it directly, the roles one hop further, and the components downstream of both — over the union of both versions' reference graphs, so a role re-pointed *away* from it in the same release still shows up. |
| **Contrast deltas with threshold crossings** | Every text role that resolves through a changed colour, measured before and after, in every theme, with a flag when it crossed 4.5:1 or 3:1 **in either direction**. An upward crossing is news too: it is usually why the change was made. |
| **SC 1.4.11 pairs, not just text** | A shifted accent moves the focus ring's contrast against the page. No linter calls a border "text", so nobody checks it. |
| **Fallout separated from decisions** | A token whose resolution moved because something upstream moved is reported as blast radius, not as its own breaking change. One edit stays one changelog line instead of becoming six. |
| **Rename detection** | A vanished name and a new name holding an identical declaration are paired, and the pairing is labelled a heuristic. It is the difference between a guide that says "renamed to `--fg-faint`" and one that says "removed". |
| **Re-points that resolve identically** | Classified `patch`, explicitly, so a genuine refactor does not inflate a release — and so the lockstep claim gets made out loud where somebody can disagree with it. |

---

## The honest limits

| What | Why the tool cannot decide it |
|---|---|
| Whether an addition is really an addition | A socket whose default does not reproduce today's rendering is a re-point in additive clothing. The tool prints the resolved default per theme; you compare them. |
| Whether a rename really is a rename | No CSS file records it. The pairing is a heuristic over identical declarations. Confirm it. |
| Layer order, from `system.json` | The `@layer a, b, c;` statement lives in the entry stylesheet and the snapshot does not record it. The diff compares it when both inputs are CSS that carries it, and says so when they do not. Diff that one file by eye; a reorder is major. |
| Whether a visual change is "too small to matter" | That is a measurement, not a feeling, and the measurement is a proof sheet. |
| Usage in a repo you did not scan | A clear scan is evidence about the repos you scanned and nothing else. |
| Anything computed at runtime | A token whose value is set by JavaScript is outside the snapshot entirely. |

---

## Adopting this on a system that already ships

Five steps, and the first one produces value before you have decided on any policy.

1. **Snapshot what is live and tag it.** `extract_system.py` against the deployed version, committed as `published/system.json`. Whatever number is on it today becomes version zero; you are not renumbering history.
2. **Diff your working branch against it.** Expect to find something you did not know you had changed. That finding is the argument for the rest of this, and it is cheaper made once than made in a meeting.
3. **Write the ledger for what you have already broken.** Every token you renamed in the last year that still has a consumer on the old name gets a record and a shim. This is dull and it takes an afternoon and it is the moment the promise becomes real.
4. **Turn the gate on with `--deprecations`.** Later never happens.
5. **Announce one rule:** no release without a diff. Not a policy document — the one habit that makes the other four keep working.

---

## Anti-patterns

| Pattern | Why it fails |
|---|---|
| Classifying by "did anything break" | Re-points and primitive edits break nothing and change everything. |
| Shipping a re-point as a patch because it was a bug fix | Severity describes impact, never intent. It can be both a fix and a major; say so, with both measured ratios. |
| Removing in the release that deprecated it | The consumer meets the announcement and the removal in one diff, so the announcement did nothing. |
| A deprecation with no removal version | It becomes permanent surface nobody is allowed to delete. |
| A codemod that covers 60% with no list of the other 40% | Worse than none: they run it, it looks clean, they ship the 40%. |
| A hand-written migration guide | It disagrees with the diff, and the diff is right. |
| A changelog that says "improved contrast" | The one number a reviewer would have acted on, omitted. |
| Floating consumers on `latest` or a caret range | A design system's output is pixels. Upgrades must be a decision, not a lockfile regeneration. |
| Copying `tokens.css` into each client | There is no version, so nothing here can help. In six months there are four design systems. |
| Upgrading four clients in one afternoon | The first one teaches you what the guide forgot. Spend that on a canary. |
| Maintaining a second major for one client | Every fix decided twice, and the branches drift until they are two systems. |
| Batching a breaking change with nine patches | The release gets reviewed as a patch release. |
| A release with no visual diff anywhere | The only test that can see the whole category, skipped. |

---

## Routing

| Situation | Go to |
|---|---|
| Building or restyling the system itself | `web-design-studio` |
| An inherited codebase not yet on tokens | `design-token-migration` |
| Design file and code have drifted apart | `figma-variables-sync` |
| Proving every state × density × theme renders | `component-state-matrix` |
| Writing the system down so others can use it | `design-system-docs` |
| **Changing a system other projects already depend on** | **here** |
| Adversarial review before a client sees it | `design-critique-gate` |

Neighbouring skills, precisely:

- **`design-token-migration`** moves *one* codebase onto the system, once. This skill moves *many* codebases between versions of it, repeatedly. It reuses that skill's codemod engine rather than growing a second one — every deprecation emits a `mapping.json` that `apply_codemod.py` applies.
- **`design-system-docs`** produces the `system.json` this skill diffs, and its `--check` mode catches doc drift. Same snapshot, two questions: *is the documentation still true* versus *what does this change cost a consumer*.
- **`component-state-matrix`** is the acceptance test for an upgrade. It is the only tool in the suite that can see a re-point.

Within this skill:

| You want | Read |
|---|---|
| the token vocabulary | `references/token-contract.md` |
| every kind of change and its verdict | `references/change-classification.md` |
| the argument for re-pointing being breaking | `references/change-classification.md` §4 |
| DOM changes, CSS Modules versus global class names | `references/change-classification.md` §7 |
| a fix that is breaking, and visual-only regressions | `references/change-classification.md` §10 |
| the version bump in under a minute | `references/change-classification.md` §11 |
| the deprecation contract and its timeline | `references/deprecation.md` §1 |
| the replacement shim, and why the ugliness is worth it | `references/deprecation.md` §4 |
| what a codemod genuinely cannot do | `references/deprecation.md` §6 |
| proving a removal is safe | `references/deprecation.md` §7 |
| npm versus submodule versus copied files | `references/rollout.md` §1 |
| the upgrade procedure a consumer runs | `references/rollout.md` §3 |
| why the visual diff is the acceptance test | `references/rollout.md` §4 |
| how many versions to maintain | `references/rollout.md` §7 |

---

## Scripts

### `scripts/diff_system.py` — stdlib Python 3, no dependencies

| Flag | Does |
|---|---|
| `old` `new` | two snapshots: `system.json`, `tokens.css`, or a directory containing one |
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

**On reading `tokens.css` directly:** `design-system-docs`' extractor is imported and run in-process when it is reachable, so there is one tier classifier and one resolver in the suite rather than two. The vendored fallback exists so the skill works standalone, and it produces identical classifications on the canonical token file.

### `scripts/deprecate.py` — stdlib Python 3, no dependencies

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

---

## The three sentences to remember

1. **Breaking means the consumer's rendered output moved without them asking** — which makes a re-pointed Tier-2 role exactly as breaking as a renamed one, and far more dangerous, because nothing in anybody's toolchain complains.
2. **The deprecation path ships before the removal, never after**, with its codemod and with the honest list of what the codemod cannot reach — and the shim that keeps both names alive for one minor version is what turns a scheduled emergency into a chore.
3. **The visual diff is the acceptance test**, because everything else in the release pipeline reads source, and the whole category of change this skill exists for leaves the source untouched.
