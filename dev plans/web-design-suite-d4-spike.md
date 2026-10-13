# D4: the Tailwind lint plugin, the spike (2026-10-13)

Decision D4 of the execution plan: Part 5 of `eslint.design.config.mjs` stays on eslint-plugin-tailwindcss or moves to eslint-plugin-better-tailwindcss, decided by a spike that runs both over the same fixtures. **The owner chose the move on 2026-10-13**, for both Tailwind majors, after reading the result below. It ships in 4.0.0 (P36 part 1).

## The versions, read on the day

From the npm registry, 2026-10-13:

| Package | Version | Published | Peers |
|---|---|---|---|
| eslint-plugin-better-tailwindcss | 4.9.0 | 2026-10-05 | eslint `^7.0.0 \|\| ^8.0.0 \|\| ^9.0.0 \|\| ^10.0.0` (optional), tailwindcss `^3.3.0 \|\| ^4.1.17`, oxlint (optional) |
| eslint-plugin-tailwindcss | 4.4.0 | 2026-08-21 | eslint `^9.0.0 \|\| ^10.0.0`, tailwindcss `^4.0.0` |
| eslint-plugin-tailwindcss | 3.18.3 | 2026-04-13 | (the v3 line) |

The rule table is better-tailwindcss's README at the `v4.9.0` tag (https://github.com/schoero/eslint-plugin-better-tailwindcss/blob/v4.9.0/README.md); the settings are its `docs/settings/settings.md` at that tag, which says `entryPoint` and `tailwindConfig` are "Relative to the current working directory".

## The run

One project, written by `spike_run.py` (v4) and `spike_run3.py` (v3) in the session's scratchpad: the starter's `index.tailwind.css`, `theme.css`, `tokens.css`, `base.css` and `layout.css` for v4, and `tailwind.config.ts` for v3. One JSX file per fixture. ESLint 10.11.0 ran from the folder above the project, as from a monorepo root, with Tailwind 4.3.3 and 3.4.19.

- **A** is today's Part 5: eslint-plugin-tailwindcss 4.4.0 (`cssConfigPath`) on v4 and 3.18.3 (`config`) on v3, with `no-custom-classname`, `no-contradicting-classname` and `enforces-shorthand`.
- **B** is better-tailwindcss 4.9.0 with `no-unknown-classes`, `no-conflicting-classes`, `enforce-shorthand-classes`, `no-duplicate-classes` and `no-deprecated-classes`.
- **C** is B with `detectComponentClasses` and the selectors extended for `classNames()`, and no `ignore` list.

| Fixture | A | B | C |
|---|---|---|---|
| `p-card bg-surface text-default` (roles) | pass | pass | pass |
| `bg-surfce`, `stak`, `motion-hovr` (typos) | refused | refused | refused |
| `p-4 bg-neutral-800` (off the replaced scale) | refused | refused | refused |
| `cx('bg-surfce')` | refused | refused | refused |
| `classNames('bg-surfce', { 'p-crad': on })` | both refused | **passed** (not a default helper) | both refused |
| `p-card p-card-lg` (conflict) | v4 and v3 | **v4 only** | v4 |
| `p-card px-inline-md` (not a conflict) | pass | pass | pass |
| `pt-card pb-card` | `py-card` | `py-card` | `py-card` |
| `stack cluster--tight with-sidebar__rail u-isolate` (the starter's own) | pass (whitelist) | pass (ignore) | **refused**: they are in `@layer layout`, not `components` |
| `card card__title` (`@layer components`) | refused | refused | **pass**, and the typo `crad` refused |
| `p-card p-card` | (v3: a shorthand message) | duplicate | duplicate |
| `!p-card` | pass | (with the important-position rule) refused | pass |
| `@md:p-card` after `--*: initial` | refused | refused | refused |
| `motion-safe:`, `motion-reduce:`, `forced-colors:`, `starting:`, `not-hover:`, `dark:` on role classes (v4) | pass | pass | pass |
| `duration-300`, `z-50`, `ring-2`, `bg-accent/37`, `p-(--space-6)`, `space-y-related`, `divide-y` | pass | pass | pass |

Neither plugin refuses the literal utilities in the last row. Part 1 of the config already does, with no plugin (`LITERAL_UTILITY`, `OPACITY_MODIFIER`, `TIER1_SHORTHAND`, `SPACE_BETWEEN`), and it refuses `!important` in either position (`IMPORTANT_MODIFIER`), so Part 5 needs neither `no-restricted-classes` nor the important-position rule.

**Time.** The first runs, on packages installed a minute before, took A 13.9 s and B 7.4 s on v4, and A 20.7 s and B 2.9 s on v3. Warm, over three runs each, the two are the same: v4 A 1.7 to 2.2 s, B 3.0 to 4.4 s, C 2.0 to 2.4 s; v3 A 2.6 to 3.0 s, B 2.2 to 2.8 s. The cold figures were the disk, not the plugins. (The owner was first told "2 to 7 times faster", from the cold runs, and the correction followed before any code was written.)

## The decision

Move to better-tailwindcss, on both majors, with C's settings and B's `ignore` list for the layout primitives:

- one plugin and one block for v3 and v4, where today a v3 project pins another plugin's old major;
- the same typos, off-scale classes and v4 conflicts, plus duplicates and, on v4, the classes v4 keeps only for compatibility;
- on v4 a component's own classes need no whitelist entry;
- `classNames()` and `classnames()` read as Part 2 reads them, through `getDefaultSelectors()`.

The cost: v3 loses the conflict check, which the CHANGELOG's 4.0.0 entry says.

The rule tests an `ignore` entry unanchored (`getCachedRegex(ignoredClass).test(className)`, against the whole class with its variants), so every `ownClasses` entry carries `^…$`, and `OwnClassesCoverTheStarter` holds it.
