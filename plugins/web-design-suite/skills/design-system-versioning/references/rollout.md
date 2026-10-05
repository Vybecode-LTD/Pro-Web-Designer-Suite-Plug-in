# Rollout

Shipping a design-system version to the projects that consume it, and getting it taken.

Classification decides the number. Deprecation decides the window. This file is the part where a release meets four client repos, three of which are mid-sprint, and either lands or sits unadopted for eight months until someone needs a feature and discovers they are eleven versions behind.

## Contents

1. [Distribution shapes](#1-distribution-shapes)
2. [Pinning](#2-pinning)
3. [The upgrade procedure](#3-the-upgrade-procedure)
4. [The visual diff is the acceptance test](#4-the-visual-diff-is-the-acceptance-test)
5. [Canarying](#5-canarying)
6. [Rolling back](#6-rolling-back)
7. [The support matrix](#7-the-support-matrix)
8. [Communicating a release so it gets read](#8-communicating-a-release-so-it-gets-read)
9. [Anti-patterns](#9-anti-patterns)

---

## 1. Distribution shapes

| Shape | Upgrade is | Pinning | Per-client divergence | Real cost |
|---|---|---|---|---|
| **npm package** (private registry or GitHub Packages) | `npm install @org/ds@2.1.0` | a lockfile, free | impossible without a fork, which is the point | a publish step, a registry, a release ritual |
| **git submodule** | `git -C vendor/ds checkout v2.1.0` | a commit SHA, free | possible and therefore common | every developer must remember submodules exist; half of them will not |
| **copied files** | a human, with a diff | none. You cannot tell what version a client is on | inevitable and invisible | after six months you have four design systems |
| **monorepo** (all clients in one repo) | atomic — the change and every consumer move together | not applicable | prevented by construction | every client's code in one repo, which is usually a contractual non-starter for an agency |

**For a small agency running several client projects on different versions: publish an npm package, private, and pin it per client.**

The argument, specifically:

- **Version is the whole problem you are solving.** With copied files there is no version. "Which version is client C on?" has no answer, so no changelog, no migration guide and no gate can help — every one of those tools takes a version as input.
- **A lockfile is free pinning.** Nothing to remember, nothing to configure, and `git log` on the lockfile tells you exactly when each client moved and to what.
- **A publish step is a release ritual, and the ritual is the value.** `npm publish` is the moment where the diff, the version bump, the changelog and the migration guide have to exist. Without that moment they get written "later".
- **Divergence becomes visible instead of silent.** A client who needs something different gets a theme override or a Tier-3 socket, in their own repo, reviewable — not a quietly edited copy of your `tokens.css` that nobody finds for a year.

A monorepo is genuinely better on the merits — atomic changes across every consumer, no versioning problem at all — and it is usually unavailable, because client code lives in client repos under client contracts. If you *can* monorepo, do; most of this file becomes unnecessary. Submodules are npm with worse ergonomics and no lockfile semantics; take them only where npm is impossible.

**Ship these files in the package**, not just the CSS:

```
dist/tokens.css          the system
dist/system.json         the snapshot — this is what diff_system.py reads
deprecations.json        the ledger — this is what the consumer's scan reads
mapping.json             the codemod, per release
CHANGELOG.md
UPGRADE-<version>.md     one per major
```

`system.json` and `deprecations.json` in the package are what let a consumer answer "what changed for me" and "am I using anything that is going away" without cloning your repo. They cost a few kilobytes.

---

## 2. Pinning

**Pin every consumer to an exact version. `--save-exact`, or `"@org/ds": "2.1.0"` with no caret.**

The case against floating on `^2.1.0` or, worse, `latest`:

Friday, 16:40. A client's CI runs on a push to a content branch, resolves `^2.1.0` to the 2.4.0 you published on Wednesday, picks up a re-pointed `--bg-accent`, and deploys. Nobody ran the codemod because nothing needed a codemod — it was a minor. Nobody looked at a visual diff because nobody knew a design-system version had changed. The first signal is the client, on Monday, asking why their buttons are orange.

Every part of that sequence is *correct semver behaviour*. `^2.1.0` means "any 2.x", a re-point in a design system can legitimately ship as part of a minor if you classify it wrong, and a lockfile that was regenerated for an unrelated reason will float. The defect is not in the range; it is in having a range at all for a dependency whose output is pixels.

| | Caret range | Exact pin |
|---|---|---|
| Upgrades happen | whenever a lockfile is regenerated | when a person decides |
| Who reviews the diff | nobody | the person who decided |
| A patch-level security fix | arrives free | needs a deliberate bump |
| "Which version is client C on?" | whatever resolved last | the lockfile, exactly |

The exact pin trades automatic patches for deliberate upgrades. For a dependency that renders your client's product, that trade is not close.

**Commit the lockfile.** An exact `package.json` with no committed lockfile still floats on transitive dependencies, and one of them is usually a PostCSS plugin.

**Record the version where a human can see it.** A `DESIGN-SYSTEM-VERSION` line in the client's README, or a `data-ds-version` attribute on `<html>`, answers the question during an incident without a checkout.

---

## 3. The upgrade procedure

What a consumer runs, in order. It is six steps and it is the same every time, which is the point — an upgrade that requires thought each time is an upgrade that gets postponed.

```bash
git checkout -b upgrade/ds-3.0.0

# 1. Read the guide. Not the changelog — the guide, which is written for you.
#    Breaking items only, each with what you will see if you skip it.
$EDITOR node_modules/@org/ds/UPGRADE-3.0.0.md

# 2. Take the version, exactly.
npm install @org/ds@3.0.0 --save-exact

# 3. The mechanical part. Dry run first; it prints a diff and writes nothing.
#    Do not commit yet: the upgrade is one commit, after step 6 (§6).
python -m scripts.apply_codemod ./src --mapping node_modules/@org/ds/mapping.json
python -m scripts.apply_codemod ./src --mapping node_modules/@org/ds/mapping.json --apply

# 4. The code gate. Law 9. Exits non-zero on a violation.
python -m scripts.audit_design src/ --strict

# 5. The pixel gate — the real acceptance test. See §4.
python -m scripts.generate_matrix matrix.json --out build/proof-sheet.html   # rebuild, then:
node scripts/snapshot_matrix.mjs build/proof-sheet.html \
     --baselines tests/visual/baselines --out build/matrix-report

# 6. Review the visual diff, accept it deliberately, and commit the accepted
#    baselines IN THE SAME COMMIT as the version bump and the codemod.
git add package.json package-lock.json src tests/visual/baselines
git commit -m "chore: design system 3.0.0"
```

Two things that make this reliably survivable:

- **Step 3 before step 4.** Running the auditor on un-codemodded source produces a wall of violations that are all the same violation, and the person reading them concludes the upgrade is enormous.
- **The codemod is dry-run by default and refuses files with uncommitted changes.** The one thing worse than a bad codemod is a bad codemod mixed into somebody's work in progress.

**If a step fails, stop and read it.** Every one of these tools fails with a reason and a line number. The failure mode to avoid is `|| true`.

---

## 4. The visual diff is the acceptance test

**A design-system upgrade that type-checks and lints clean can still be visually wrong. That is the normal case, not the exotic one.**

Everything in steps 3 and 4 above tests the *code*. Not one of them can see:

| What moved | Why no linter catches it |
|---|---|
| A re-pointed role | The source is unchanged. `var(--bg-accent)` is still `var(--bg-accent)`. |
| A Tier-1 value change | Same. Every call site is byte-identical. |
| A socket default | The consumer never wrote the default; they inherited it. |
| A variant's appearance | Your CSS changed, not theirs. Their diff is empty. |
| A theme-only re-point | Nothing changes in the theme the reviewer is looking at. |
| A DOM change with no visual effect | Nothing changes visually *in your repo*. In theirs, a descendant selector stopped matching. |

The only test that sees that category renders the components and compares pixels. That is `component-state-matrix`, and its baselines are the acceptance criteria for a design-system upgrade:

```bash
# Once, before you upgrade — the baselines are the "before".
node scripts/snapshot_matrix.mjs build/proof-sheet.html \
     --baselines tests/visual/baselines --update-baselines

# After the upgrade — every cell that moved, with a diff image.
node scripts/snapshot_matrix.mjs build/proof-sheet.html \
     --baselines tests/visual/baselines --out build/matrix-report
```

The proof sheet renders every component at every state × density × theme, so the diff covers the cases a spot check never reaches — the `focus-visible` row, the compact density, the dark column. A re-pointed `--bg-accent` shows up as every button cell moving at once, which is instantly legible as *one* change rather than forty.

**How to read the result:**

| Result | Means |
|---|---|
| Zero cells changed, and the release was major | Either the change does not reach your product, or your matrix does not cover the component it touched. Check which before you celebrate. |
| The cells you expected changed | Accept the baselines, in the same commit as the version bump. |
| Cells you did not expect changed | This is what the tool is for. Read the diff before accepting anything. |
| A cell changed in dark only | Almost always a theme re-point you skimmed past in the changelog. |

**Accept intentional diffs in the same commit as their cause.** A baseline update on its own is unreviewable — forty PNGs and no explanation. Alongside the version bump it reads as "we took 3.0.0, so these fourteen images changed", and a reviewer can agree or disagree with that sentence.

**If a consumer has no baselines, creating them is the first upgrade's real work** — and it is worth it on the first upgrade, not the third, because every subsequent upgrade is then a five-minute look instead of a leap of faith.

---

## 5. Canarying

**Upgrade one consumer first, all the way to production, before you touch the others.**

Pick the canary by these properties, in order: you control the deploy; it has visual baselines; it is not the client who notices everything; it uses a wide slice of the system. A small internal site or your own marketing page is ideal. The largest client is the worst possible choice and the most tempting, because it exercises the most surface.

| Stage | What it proves |
|---|---|
| Canary upgrades, CI green | The codemod is complete enough and the code gate passes |
| Canary's visual diff reviewed | The classification was right — nothing moved that the guide did not predict |
| Canary in production for one cycle | Nothing breaks under real content, real data and real viewport sizes |
| Then the rest, one at a time | Each remaining consumer is a repeat of a procedure that is known to work |

The thing a canary catches that a test suite cannot is **what the guide forgot to mention**. If the canary's visual diff shows a change the migration guide did not predict, the guide is wrong for everyone — fix the guide and re-publish it before the second consumer starts. That feedback loop is the entire value; a canary you do not read is just a slower rollout.

**Do not canary a major on the client with the nearest deadline.** Obvious, routinely ignored, because that is the repo someone is already working in.

---

## 6. Rolling back

Rolling back a design-system upgrade is cheap **if** the upgrade was one commit and the pin was exact:

```bash
git revert <the upgrade commit>   # version bump, codemod and baselines together
npm ci
```

That is the entire argument for committing the bump, the codemod and the accepted baselines together. Split across three commits, a rollback is three reverts in the right order, one of which conflicts.

| Situation | Do |
|---|---|
| Caught before merge | Close the branch. Nothing happened. |
| Caught in the canary, in production | Revert the canary. Fix the system, publish a patch, re-run the canary. |
| Caught after two consumers upgraded | Revert both. Do **not** publish a "fixed" version and tell them to upgrade again — you have already spent their attention once. |
| Caught in one consumer only, others fine | Revert that one. It is a consumer-specific interaction, and it belongs in the guide as a note. |

**Unpublishing is not a rollback.** Yanking a version from the registry breaks the lockfile of anyone who already took it, which converts one consumer's problem into everyone's. Publish a new patch that reverts the change and say plainly in the changelog that 2.1.0 is bad and why.

**A rollback is data.** Whatever the canary's visual diff failed to show you is a gap in the proof sheet's coverage. Add the missing cell before the retry, or the retry fails the same way.

---

## 7. The support matrix

**How many versions do you maintain? One. Plus whatever the deprecation window keeps alive.**

| Policy | Branches | What it costs |
|---|---|---|
| **Latest only** ← the answer for a small team | 1 | Consumers must upgrade to get anything, including fixes |
| Latest + previous major | 2 | Every fix is decided twice, cherry-picked twice, tested twice, released twice |
| Latest + LTS | 2, forever | The LTS branch quietly becomes a second design system with different values |

The argument for one:

- **A backport is not one commit.** It is a decision ("does this apply to 1.x?"), a cherry-pick, a conflict, a test run, a release and a changelog entry — for every fix, forever. At two people that is a meaningful fraction of the week.
- **The second branch drifts.** A fix lands on `main` in the token layer and on `1.x` as a component override, because the token was renamed in 2.0. Six months later the two systems render differently and nobody meant that.
- **The deprecation window already does the job.** A consumer who cannot upgrade today has one minor version of runway in which both the old and the new name work. That is the support window, and it is expressed in the ledger rather than in a branch.
- **The real request is usually not "support 1.x".** It is "we do not have budget to upgrade". §8 of `deprecation.md` has the honest options, and the cheapest one for an agency is almost always to do the migration for them.

**The exception:** a live product under a support contract that names a version. Then you maintain that branch, you scope it to security and accessibility fixes only, and you put an end date on it in writing. Everything else stays on one line.

**What "latest only" obliges you to:** upgrades must be genuinely cheap. The codemod, the guide, the visual diff, the canary — the whole of this file is what earns the right to say "there is one version".

---

## 8. Communicating a release so it gets read

A release nobody reads is a release nobody takes, and an untaken release is indistinguishable from a release you never made.

**Three artifacts, three audiences, generated rather than written:**

| Artifact | Reader | Generated by |
|---|---|---|
| `CHANGELOG.md` entry | someone deciding whether to care | `diff_system.py --format changelog` |
| `UPGRADE-<major>.md` | someone doing the upgrade, today | `diff_system.py --format migration-guide` |
| The announcement message | someone scrolling past | you, three sentences, from the above |

**The changelog answers "does this affect me".** Keep-a-Changelog sections, breaking items marked, every contrast crossing with both measured ratios. Generated from the diff, so it cannot omit something you forgot.

**The migration guide answers "what do I do".** Breaking items only, in order, each with: what changed, *what you will see if you skip it*, the blast radius, and the command. The "what you will see" line is the one that gets acted on — "`--fg-subtle` was renamed" is information, "every secondary label will render unstyled" is a task.

**The announcement is three sentences and it names the cost.** Not "3.0.0 is out with improvements". This:

> **Design system 3.0.0.** One breaking change: `--bg-accent` moved from accent-600 to accent-500, so white text on a filled button now measures 3.56:1 and no longer passes 4.5:1 — if you have small text on an accent fill, you need to look at it. Everything else is additive. Codemod and guide: `UPGRADE-3.0.0.md`; budget about twenty minutes per project.

A re-point is breaking, so it ships in a major (SKILL.md's table): announcing it as 2.1.0 is the floating-range accident of §2 waiting to happen.

Four properties worth copying: it names the *one* thing that matters, it gives the measured number, it says who is affected, and it estimates the cost. A reader can decide in eight seconds whether to open the guide, which is the only decision the announcement needs to produce.

**Send it where the work happens** — the channel people already read, not a wiki page. And send it **once**, when the release lands. A release announced three times is a release people learn to scroll past.

---

## 9. Anti-patterns

| Pattern | Why it fails |
|---|---|
| Floating on `latest` or a caret range | A design system's output is pixels. Upgrades must be a decision, not a lockfile regeneration on a Friday afternoon. |
| Copying `tokens.css` into each client | There is no version, so no changelog, guide or gate can help. Six months later there are four design systems. |
| Upgrading every consumer in one afternoon | The first one teaches you what the guide forgot. Spend that lesson on a canary, not on four clients at once. |
| A release with no visual diff anywhere | The only test that can see a re-point is the one you skipped. |
| Committing accepted baselines separately from their cause | Forty PNGs with no explanation is not a reviewable diff. |
| Batching a breaking change with nine patches | The release gets reviewed as a patch release. |
| Maintaining a second major "just for client C" | Every fix is decided twice, and the branches drift until they are two systems. |
| Unpublishing a bad version | Breaks the lockfile of everyone who already took it. Publish a revert instead. |
| A migration guide written by hand after the release | It disagrees with the diff, and the diff is right. |
| "Upgrade when you can" with no removal date | Nobody upgrades. Name the version the old name dies in. |
| Canarying on the biggest client | It exercises the most surface and it is the worst place to be wrong. |

---

## The three sentences to remember

1. **Pin exactly and upgrade deliberately** — an npm package with a committed lockfile is the only shape where "which version is client C on" has an answer, and every other tool here takes that answer as input.
2. **The visual diff is the acceptance test**, because a re-pointed role, a moved primitive and a changed socket default are all invisible to a type checker and a linter and obvious on a proof sheet.
3. **Maintain one version plus a deprecation window**, and pay for that with upgrades so cheap — codemod, guide, canary, twenty minutes — that nobody needs a second branch.
