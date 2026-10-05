# Deprecation

How to remove something from a design system without breaking anyone.

A deprecation is not a label. It is a **promise with four stages and a date**, and the only thing that makes it worth more than a comment is that every stage is checkable by a machine. This file is the contract, the markers, the codemod rule, the evidence, and the one anti-pattern that causes most of the pain.

## Contents

1. [The contract](#1-the-contract)
2. [The ledger](#2-the-ledger)
3. [Markers in the source](#3-markers-in-the-source)
4. [The replacement shim](#4-the-replacement-shim)
5. [Every deprecation ships with its codemod](#5-every-deprecation-ships-with-its-codemod)
6. [What a codemod genuinely cannot do](#6-what-a-codemod-genuinely-cannot-do)
7. [Evidence: is it safe to remove yet](#7-evidence-is-it-safe-to-remove-yet)
8. [When a consumer will not upgrade](#8-when-a-consumer-will-not-upgrade)
9. [One deprecation, end to end](#9-one-deprecation-end-to-end)
10. [Anti-patterns](#10-anti-patterns)

---

## 1. The contract

| Stage | Version | What you ship | What you owe the consumer |
|---|---|---|---|
| **Announce** | `X.Y.0` (minor) | Both names work. Ledger record, marker in the source, changelog entry under **Deprecated**. | The replacement, the removal version, and the reason — in their terms, not yours. |
| **Warn** | every release after | The marker stays. The linter surfaces it. The old name keeps working. | Silence. You already said it; repeating it in each changelog trains people to skip changelogs. |
| **Migrate** | any time | The codemod, in `apply_codemod.py`'s format, and the honest list of what it cannot reach. | A command they can run, and a list of the call sites they must edit by hand. |
| **Remove** | `X+1.0.0` (major) | The declaration, the marker and the ledger rule, deleted in one commit. | Evidence that nobody was still using it — or an explicit decision that you are breaking them anyway. |

**The minimum window is one minor version, and the practical minimum is one client's release cadence.** A small agency shipping monthly can announce in 2.1.0 and remove in 3.0.0 six weeks later. An agency with a client who deploys quarterly cannot: that client meets the announcement and the removal in the same upgrade, which is not a deprecation, it is a removal with extra steps. Set the window from the slowest consumer you actually have, not from your own release rhythm.

`deprecate.py` refuses a record whose removal is not at least a minor version after the announcement, and refuses one where removal precedes announcement outright. `--force` exists; if you use it, put the reason in `--notes` so the next person knows it was deliberate.

**What ends the window is evidence, not the calendar.** A removal version is a plan. §7 is how you find out whether the plan is safe.

---

## 2. The ledger

`deprecations.json` is the single machine-readable record. It lives in the design system's repo, beside `tokens.css`, and it is committed.

```bash
python -m scripts.deprecate add --name=--fg-subtle --kind token \
    --since 2.1.0 --removal 3.0.0 --replacement=--fg-faint \
    --reason "The name described a contrast intent the ramp no longer matched." \
    --notes "If you re-point --fg-subtle in your own theme block, re-point the override too." \
    --source styles/tokens.css --mapping build/mapping.json
```

```json
{
  "name": "--fg-subtle",
  "kind": "token",
  "since": "2.1.0",
  "removal": "3.0.0",
  "replacement": "--fg-faint",
  "codemod": "mechanical",
  "reason": "The name described a contrast intent the ramp no longer matched.",
  "notes": "If you re-point --fg-subtle in your own theme block, re-point the override too.",
  "recorded": "2026-09-17",
  "status": "active",
  "marker": "styles/tokens.css:280",
  "usage": { "scanned": "2026-09-17", "total": 5, "consumers": { "client-a": 5, "client-b": 0 } }
}
```

| Field | Why it exists |
|---|---|
| `kind` | `token` · `socket` · `component` · `variant` · `state` · `prop` · `theme` · `repoint`. Decides which codemod shape is even possible. |
| `since` / `removal` | The promise. `status --version 3.0.0` reads these to answer "what is due". |
| `replacement` | Empty is legal and means "there is no one-to-one" — which changes the codemod from mechanical to a conversation. |
| `codemod` | `mechanical` · `manual` · `none`. Set it to `manual` and the mapping stops emitting a rule, which is the correct outcome for §6's cases. |
| `reason` | Written for a consumer. "Renamed for clarity" is not a reason; "the name claimed a contrast score the ramp no longer met" is. |
| `notes` | What the codemod will not do for them. This is the field that prevents a support ticket. |
| `usage` | Written by `scan --record`. This is what turns "is it safe to remove" from a feeling into a number. |

**The ledger is what makes the release gate possible.** `diff_system.py --deprecations deprecations.json` exits non-zero when a name vanished with no record. Without the ledger it has nothing to check against, so it reports and does not fail — which is the right default, because a gate that fails on its first honest run gets wrapped in `|| true` within a week.

---

## 3. Markers in the source

A deprecation that exists only in a changelog is invisible at the call site, and the call site is where someone decides to keep using it.

One grammar, both languages:

```css
/* @deprecated --fg-subtle since=2.1.0 use=--fg-faint remove=3.0.0 codemod=dep-fg-subtle — The name claimed a contrast score the ramp no longer met. */
--fg-subtle:      var(--fg-faint);
```

```ts
/** @deprecated Banner since=2.1.0 use=Callout remove=3.0.0 codemod=dep-banner — Callout carries the same variants plus `dismissible`. */
export function Banner(props: BannerProps) { … }
```

`deprecate.py add --source FILE` injects it, finds the declaration itself, matches the indent, and is idempotent: re-running after you improve the reason **replaces** the marker rather than stacking a second one. If it cannot find the declaration it says so and prints the line for you to paste, rather than guessing at a location.

| Who reads the marker | How |
|---|---|
| A developer | It is the line above the thing they were about to use. |
| An editor | `@deprecated` in a JSDoc block gets a strikethrough in every major editor, for free. |
| `grep` / CI | `@deprecated <name> since=… use=… remove=…` parses with one regex. |
| `deprecate.py status` | Cross-checks the ledger against what is actually marked. |
| `audit_design.py` | Unaffected — a comment breaks no law. Verify this after injection; a marker that fails the gate is a marker people delete. |

**Why `key=value` and not prose.** Prose markers rot into six different phrasings across four files, and nothing can read them. The structured half is for machines and the prose half after the em-dash is for people. Both, in one line, or you will end up maintaining two.

### Surfacing them in CI

Three checks, each failing for a different reason, all cheap:

```bash
# 1. The ledger and the source agree — every active record has its marker.
python -m scripts.deprecate status --version "$NEXT_VERSION"     # exit 1: due and still in use

# 2. Nothing vanished without a record.
python -m scripts.diff_system published/system.json build/system.json \
       --deprecations deprecations.json                           # exit 1: the gate

# 3. The marked file still obeys the nine laws. A comment breaks none of them,
#    but verify it rather than assume it: a marker that fails the gate is a
#    marker somebody deletes.
python -m scripts.audit_design styles/ src/ --strict
```

In a **consumer's** repo, one more, as a warning rather than a failure:

```bash
# Fail the build only once the removal version is the one you are about to take.
python -m scripts.deprecate --ledger node_modules/@your-org/design-system/deprecations.json \
       scan ./src --fail-on-usage
```

Stylelint and ESLint have no native concept of a deprecated custom property, and writing a plugin for one is not worth an afternoon — the marker regex plus `scan` covers it, and `scan` also tells you which hits the codemod will and will not reach, which a lint rule never would. Where the design system ships TypeScript, `@deprecated` in the JSDoc is already surfaced by every editor and by `tsc` with no configuration at all; that is free and worth taking.

---

## 4. The replacement shim

**Keep the old name working, aliased to the new one, for one minor version.**

```css
--fg-faint:       var(--neutral-500);
/* @deprecated --fg-subtle since=2.1.0 use=--fg-faint remove=3.0.0 codemod=dep-fg-subtle — … */
--fg-subtle:      var(--fg-faint);
```

It is ugly. Two names for one value is exactly what a token system exists to prevent, and it will sit in your file for months. Ship it anyway, because of what it does to the release:

| Without the shim | With the shim |
|---|---|
| The rename is **major** | The rename is **minor** — a new role added, the old one re-pointed to it with an identical resolved value |
| Every consumer must act, at once, or break | Every consumer acts when they next touch the code |
| The upgrade and the migration are the same event | They are two events, and only the first one is urgent |
| A client who does not upgrade stays on an old version of the whole system | They take the release and migrate later |

That last row is the one that matters for an agency. Without a shim, a rename holds every client's entire upgrade hostage to one codemod. With it, the release is boring and the codemod is a chore someone does on a Tuesday.

**Alias to the new name, never duplicate the value.** `--fg-subtle: var(--fg-faint)` follows every theme override and every future re-point automatically. `--fg-subtle: var(--neutral-500)` is a second copy that silently stops tracking the first the moment dark mode re-points one of them — which is the exact bug the alias was supposed to prevent.

**When a shim is not possible:**

| Case | Why | Do instead |
|---|---|---|
| A component whose replacement has different DOM | You cannot alias markup | Ship both components. Delete the old one in the major. |
| A required prop added | There is no value to alias | Ship it optional with a default, warn, require it in the major. |
| A removed variant | `data-variant="quiet"` cannot alias to another variant without duplicating the rules | Duplicate the rules. It is three lines and it buys a whole version. |
| A re-point that was the point of the release | Aliasing would undo it | No shim exists. This is a plain major; §10.1 of `change-classification.md` is how you write it up. |

**Delete the shim in the release you promised.** A shim that outlives its removal version teaches consumers that removal versions are decorative, and the next one gets ignored too.

---

## 5. Every deprecation ships with its codemod

**The rule: if you cannot say how a consumer migrates, you are not ready to deprecate.** Not "they can search and replace" — a command they run.

```bash
python -m scripts.deprecate mapping -o build/mapping.json
# the consumer, in their repo:
python -m scripts.apply_codemod ./src --mapping build/mapping.json          # dry run
python -m scripts.apply_codemod ./src --mapping build/mapping.json --apply
```

The mapping is emitted in `design-token-migration`'s own `mapping.json` format, and applied by that skill's `apply_codemod.py`. That is deliberate: a second codemod engine in one suite is a second set of bugs about comments, strings, `url()`, shorthands and negative values, and the first engine already solved all of them.

**Which scope, and why.** `apply_codemod`'s per-slot pass deliberately skips any slot that already contains `var(--` — its job is literals → tokens, and rewriting inside an existing `var()` is not that job. So a token rename is emitted as **declaration-scope** rules, one per property, where the engine replaces the whole declaration:

```json
{
  "id": "dep-fg-subtle-color",
  "scope": "declaration",
  "kind": "color",
  "match": ["var(--fg-subtle)"],
  "props": ["color"],
  "replacement": "color: var(--fg-faint)"
}
```

Shadows go the other way: `box-shadow` is matched as a whole *value* with no `var()` guard, so an `--elevation-*` rename emits one clean value-scope rule. Component and variant renames emit a `tailwind`-scope rule, which is the one place the engine rewrites an identifier inside a `className` string rather than a value.

`--kind` on the emitted rules matches `apply_codemod`'s own vocabulary (`color`, `spacing`, `type`, `radius`, `shadow`, `z-index`, …), so a consumer can run one kind at a time and commit between batches, exactly as in a migration.

---

## 6. What a codemod genuinely cannot do

Publish this list with the guide. A migration guide that promises a clean codemod and delivers a 60% one costs more trust than one that says "five of these, by hand, here they are".

| Case | Why it cannot be mechanical |
|---|---|
| **A semantic split** — `--fg-muted` becomes `--fg-secondary` and `--fg-tertiary`, chosen by context | The correct replacement depends on what the text *is*, which is in the designer's head. A codemod would have to guess, and a wrong guess is worse than no change because it looks migrated. |
| **A component whose replacement has different DOM** | `<Banner>` → `<Callout>` may need a child restructured, a prop renamed and a slot filled. Rewriting the tag alone produces code that compiles and renders wrong. |
| **A Tier-3 socket default: `--card-fg: var(--fg-subtle)`** | `apply_codemod` skips custom-property declarations on purpose — they are the system's own layer, not a call site. Re-point these by hand; there are never many. |
| **A shorthand: `border-bottom: 1px solid var(--fg-subtle)`** | The rule matches a whole declaration value. Enumerating every surrounding text is not a rule, it is a regex nobody can review. |
| **A token inside JS or markup** — `style={{ color: "var(--fg-subtle)" }}` | The engine reads styled-components bodies and `className` strings. An arbitrary string in an inline style is not either. (It is also a Law 4 violation, so the fix is bigger than the rename.) |
| **A consumer's own theme override of the old name** | It is in *their* file, re-pointing *your* role. Only they know whether it should follow the rename. This belongs in `notes`. |
| **A prop whose type changed shape** — `isLarge: boolean` → `size: 'sm'\|'lg'` | The mapping is not one-to-one and the absent case (`isLarge={false}`) may mean `'sm'` or may mean "default". |

`deprecate.py scan` labels every call site `codemod` or `manual`, with the reason, so the honest list is generated from the consumer's actual code rather than from your memory. It reads each declaration on a line, so a one-line rule is labelled as the codemod treats it, and a colour rename beside a `font-weight` is a codemod hit: the codemod's font guard applies only where a rewrite turns another property into the `font` shorthand.

Set `--codemod manual` on the ledger record for these. The mapping then emits no rule for it and lists it under `unmapped` with the reason, which is more useful than a rule that half-works.

---

## 7. Evidence: is it safe to remove yet

```bash
python -m scripts.deprecate scan ../client-a ../client-b ../client-c --record
```

```
--fg-subtle   since 2.1.0 · removal 3.0.0 · codemod mechanical
  client-a                  5 hit(s)   1 codemod · 4 manual
      src/components/card.css:4    [manual]  --card-meta-fg: var(--fg-subtle);
          why: a custom-property declaration — apply_codemod skips those on purpose
      …
  client-b                  0 hits   clear

VERDICT
  --fg-subtle            NOT SAFE to remove — 5 hit(s) in 1 of 2 consumer(s), 4 of them need a human
```

`--record` writes the counts into the ledger, so `status --version 3.0.0` can answer "what is due, and is anything still using it" months later without re-cloning anything. `status` exits 1 when something due for removal is still in use; `retire` refuses outright unless you pass `--force`.

**The honest limit, stated by the tool itself:** a clear scan is evidence about the repos you scanned and nothing else. A consumer you did not clone is a consumer you did not check. For an agency running several client projects this is fine — you have all of them on disk. For a public package it is not, and the only substitutes are download telemetry (which tells you about versions, not tokens) and a long window.

**Three habits that make the evidence trustworthy:**

- **Scan before every major, not once.** Usage changes between the announcement and the removal, usually upward, because someone copied a file.
- **Scan the branches people actually deploy**, not `main` on a repo nobody has merged into since spring.
- **Re-scan after the consumers run the codemod.** The point is to watch the number go to zero. A deprecation that never reaches zero is telling you the codemod does not cover the real usage.

---

## 8. When a consumer will not upgrade

It happens: a client with no budget, a frozen project, an agency contract that ended. The deprecation window expires and they are still on 2.x.

| Option | When it is right | The real cost |
|---|---|---|
| **Remove anyway; they stay pinned on 2.x** | The default, and usually correct | They get no fixes, including security and accessibility ones. Say this to them in writing, once. |
| **Keep the shim one more major** | The consumer is large, the shim is three lines, the cost is cosmetic | Every extension teaches everyone that removal dates are soft. Do it at most once, and say it is the last one. |
| **Maintain a 2.x branch** | Contractual obligation, or a live product you are paid to support | Two branches means every fix is decided twice. §7 of `rollout.md` argues you should almost never do this. |
| **Do the migration for them** | A client project you have commit access to | An afternoon, once, and it ends the problem permanently. For an agency this is nearly always the cheapest row in the table. |

**The one thing that is never right** is delaying the removal indefinitely without saying so. The shim stays, the marker stays, and the next deprecation you announce is believed by nobody — including you.

For an agency specifically: the last row is underrated. You have the repos. You have the codemod. `scan` tells you exactly how many hits there are, and four of five are usually mechanical. "We will do it for you next Tuesday" resolves more deprecations than any amount of changelog writing.

---

## 9. One deprecation, end to end

`--fg-subtle` is renamed to `--fg-faint`. Two client projects consume the system. Here is the whole thing, in the order it happens.

**2.1.0 — announce.** Add `--fg-faint`, alias the old name to it, record it, mark it, emit the mapping.

```bash
python -m scripts.deprecate add --name=--fg-subtle --kind token \
    --since 2.1.0 --removal 3.0.0 --replacement=--fg-faint \
    --reason "…" --notes "…" --source styles/tokens.css --mapping build/mapping.json
python -m scripts.diff_system published/system.json build/system.json --from-version 2.0.4
```

The diff says **minor**, not major: `--fg-faint` added, `--fg-subtle` re-pointed to a value that resolves identically. That is the shim earning its keep — the rename ships in a release nobody has to schedule.

**2.1.0 — the changelog.** The entry goes under **Deprecated**, generated from the ledger, not from the diff:

```
### Deprecated
- `--fg-subtle` — still works, removed in `3.0.0`. Use `--fg-faint`. …
```

**Between 2.1.0 and 3.0.0 — migrate.** In each client repo, one command and a look:

```bash
python -m scripts.apply_codemod ./src --mapping build/mapping.json           # dry run
python -m scripts.apply_codemod ./src --mapping build/mapping.json --apply
python -m scripts.audit_design src/ --strict
```

Then the handful `scan` labelled `manual`. There are usually four or five.

**Before 3.0.0 — check.**

```bash
python -m scripts.deprecate scan ../client-a ../client-b --record
python -m scripts.deprecate status --version 3.0.0
```

Zero hits in both, or the removal waits. `status` exits 1 while anything is outstanding, so this can sit in the release workflow rather than in somebody's memory.

**3.0.0 — remove.** Delete the alias, the marker and the rule, in one commit, and retire the record:

```bash
python -m scripts.deprecate retire --name=--fg-subtle
```

Elapsed: two releases and about twenty minutes of work per consumer. The alternative — renaming it in one release — is the same twenty minutes, compressed into an afternoon everybody has to find at the same time, plus one client who did not and whose secondary text is now unstyled.

---

## 10. Anti-patterns

| Pattern | Why it fails |
|---|---|
| **Removing in the release that deprecated it** | The one that causes most of the pain. A consumer who upgrades from 2.0 to 3.0 sees the announcement and the removal in the same diff, so the announcement did nothing. `deprecate.py` refuses this without `--force`. |
| A deprecation with no removal version | It never gets removed. It becomes permanent surface that everyone is vaguely embarrassed by and nobody may delete. |
| A deprecation with no replacement and no note | The consumer's only option is to invent one. They will invent a different one per project. |
| "Deprecated" in a comment, nowhere else | Not in the ledger, so the gate cannot see it; not in the changelog, so nobody was told. |
| A codemod that covers 60% with no list of the other 40% | Worse than no codemod: they run it, it exits clean-ish, and they ship the 40%. |
| Duplicating the value in the shim instead of aliasing | The two copies drift the first time a theme re-points one of them. |
| Deprecating ten things in one release | Nobody migrates ten things. They migrate zero and pin the version. |
| Removing on the calendar with no scan | You had the evidence available and chose the plan instead. |
| A shim that outlives its removal version | Teaches consumers that removal versions are decorative. |
| Deprecating something nobody uses | Free to delete, so just delete it. The ceremony is for things with consumers. |

---

## The three sentences to remember

1. **Never remove in the release you deprecated in** — a window a consumer cannot act inside is not a window, and one minor version is the floor, set by your slowest client's cadence rather than your own.
2. **Every deprecation ships with its codemod and with the honest list of what the codemod cannot reach**, because a guide that promises clean and delivers 60% costs more trust than one that says "five by hand, here they are".
3. **Answer "is it safe to remove" with a scan, not a date** — the ledger holds the plan, `scan --record` holds the evidence, and only one of those can tell you a client copied the token into a file you forgot about.
