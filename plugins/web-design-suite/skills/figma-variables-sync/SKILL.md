---
name: figma-variables-sync
description: Keep a Figma file and a codebase on one token vocabulary. Audit a design file before building it, generate tokens.css from a Figma export, push code tokens back as variables, and catch drift in CI. Not for building the page from the design (web-design-studio) or reviewing its taste (design-critique-gate).
---

# Figma Variables Sync

> **Running the scripts** — by path, from the user's project root, so `src/`
> means the project's `src/` and every output lands in the project, never
> inside this plugin:
>
> ```bash
> python "${CLAUDE_SKILL_DIR}/scripts/figma_audit.py" design/figma-variables.json
> ```
>
> The commands below are written `python scripts/<name>.py`. That form is for a project that
> has copied the scripts into its own `scripts/` folder, as CI and git hooks
> do; when you run one here, use the path form.
> This skill's scripts are in `${CLAUDE_SKILL_DIR}/scripts/` (figma_audit.py, figma_to_tokens.py).

One vocabulary, two rendering surfaces.

A design system is a set of named decisions. Figma renders those names as a
canvas; the browser renders them as a page. Neither is the system. The moment the
two hold *different* names — or the same names with different values — you no
longer have a design system, you have two design systems and a translation
meeting every sprint.

This skill keeps the names identical, moves the argument about values to before
the build, and makes drift between them a CI failure rather than a discovery.

**Read `references/token-contract.md` first.** It is the vocabulary. Everything
here assumes it.

---

## Be honest about what this can and cannot do

Nothing here reads a `.fig` file. There are three ways to get variables out of
Figma, and only one of them, the REST API, requires an Enterprise plan.

| Path | Needs | Gets you | Use it when |
|---|---|---|---|
| **Exported JSON** — the primary path | A designer with a plugin, five minutes, one file sent to you | Every variable, collection, mode, alias and scope | **Always.** This is the default |
| **Figma's MCP server** — the live path | The server connected to Claude; a Dev seat to read, a Full seat to write outside drafts | `get_variable_defs` for a selection, `search_design_system` across libraries, and `use_figma`, which runs Plugin API code that can read or create collections, modes and variables | The designer's file is open to you through the connection |
| **REST API** — the optional upgrade | A personal access token, a file key, **an Enterprise plan** | The same data, on demand, in CI | You are on Enterprise and want automation |
| **Screenshot + spec** — the fallback | Nothing | A conversation and some measurements | The file is not shareable, or the designer is not reachable |

> **`GET /v1/files/:file_key/variables/local`, `…/variables/published` and
> `POST /v1/files/:file_key/variables` are Enterprise-only, and have been since
> the Variables API launched in June 2023.** Confirm the company's plan before
> promising anyone a pipeline. On Professional or Organization the REST path is
> closed, but scripting is not: the Plugin API reads and writes variables on
> every plan, and Figma's MCP server runs Plugin API code through `use_figma`.
> Without either, the exported JSON is the path. Details and the exact payload
> shapes: `references/figma-mapping.md` §14.

Both scripts read the exported-JSON shapes and the REST shape, and detect which
they were handed. Nothing in the workflow below requires a token.

---

## The workflow

Five steps. Steps 2 and 3 are where the value is; steps 1, 4 and 5 are
mechanics.

### Step 1 — Get the data

Ask for this, in these words, and expect it back the same day:

> Can you export the variables from the file? Any of the "Variables Import
> Export" plugins does it — select all collections and all modes, export JSON,
> send me the file. If there are text and effect styles, I need those too.

| What you get | Shape | Cost | Caveat |
|---|---|---|---|
| Plugin export | `{"collections": […]}` | 5 designer-minutes | Plugin shapes differ; the scripts sniff four of them |
| Native DTCG export | `{"space": {"6": {"$value": …}}}` | 2 minutes, **if available** | Figma announced native W3C DTCG import/export rolling out from late 2025. Check the app; do not assume |
| REST pull | `{"meta": {"variables": …}}` | One curl, Enterprise only | See below |
| Screenshot + spec | Prose | An hour of meeting | Last resort; §Fallback |

**REST pull**, if you are on Enterprise:

```bash
curl -H "X-Figma-Token: $FIGMA_TOKEN" \
  "https://api.figma.com/v1/files/$FILE_KEY/variables/local" > variables.json

curl -H "X-Figma-Token: $FIGMA_TOKEN" \
  "https://api.figma.com/v1/files/$FILE_KEY/styles" > styles.json
```

The file key is the segment after `/design/` in the URL. `local` includes
unpublished drafts, which is usually what you want — the thing you are arguing
about is rarely published yet. `…/styles` is different on both counts: it needs
no Enterprise plan (scope `library_content:read`), and it returns **published**
styles only, so on a file whose styles are still drafts it comes back empty and
the style checks see nothing; export those with the plugin. It also returns
style *metadata* only, not the type properties; to get sizes you also read
`…/nodes`. See
`references/figma-mapping.md` §7.

**Fallback — a screenshot and the designer's spec.** Legitimate, and not a
failure. Measure what you can, then send back the *inferred* token list —
"reading this as `--gap-separate` between the cards and `--pad-card` inside them,
correct me" — and let the designer correct names rather than supply numbers.
Write the result into `DESIGN_DECISIONS.md`, because it is a set of assumptions
and assumptions decay.

**Commit the export.** `design/figma-variables.json`, in the repo, in the same
commit as the tokens generated from it. Without it, step 5 has nothing to compare
against and the whole sync is a one-time import.

### Step 2 — Audit before building

**This is the highest-value step in this skill.** Twenty minutes here is a day
per finding later, because a value that reaches code has a PR and a reviewer
attached to it.

```bash
python scripts/figma_audit.py design/figma-variables.json
```

It checks every value against the closed scales and the ramps and reports:

- spacing, type, radius, stroke, leading, tracking, weight, duration and z-index
  off the scale — **with the nearest legal step and the delta**
- colours off the ramps — with the nearest step and the **OKLab ΔE**, so the
  conversation is about whether anyone can see the difference rather than about
  taste
- **contrast failures** for anything used as a text role, measured in both modes
  against the surfaces it actually lands on
- tap targets under 44px
- text styles with no `--type-*` role, effect styles with no `--elevation-*`
- broken aliases, alias cycles, missing dark mode, missing interaction states

Then send it:

```bash
python scripts/figma_audit.py design/figma-variables.json \
  --format markdown --deadline "Thursday 5pm" > handoff-questions.md
```

The markdown is written to be pasted to a designer: it leads with the three
possible outcomes, gives each finding with its nearest legal alternative, and
states the timed default. **Send it once, before estimating.** Not in dribs
during the build — same information, completely different reception.

Before running anything, check the three things the script cannot see: is the
file built in auto-layout throughout, are fills and text sizes actually bound to
variables, and do focus/loading/error states exist? Those change the estimate
more than every number the audit reports.
Full procedure: `references/audit-and-reconcile.md`.

### Step 3 — Reconcile

Every mismatch resolves to exactly one of three outcomes. All three are
legitimate. A project where the answer is always the same one has a broken
process, not a perfect system.

| Outcome | When | Cost | Sign-off |
|---|---|---|---|
| **1. The design is right** — add a token | The system genuinely lacks something, and the need recurs | High; permanent, everyone inherits it | Design-system owner (Law 3) |
| **2. The system is right** — designer adjusts | The value was incidental. Nobody chose 28 on purpose | Near zero | Nobody; the designer just does it |
| **3. Both are defensible** — document the exception | A real reason that does not generalise | One hard-coded value and one paragraph, forever | Both of you, in `DESIGN_DECISIONS.md` |

**The decision rule.** Three questions, stop at the first clear answer:

1. **Will this recur** in the next six months, on another screen or from another
   person? No → outcome 2 or 3.
2. **Can the existing system express the intent**, even if not the number? Not
   "is 24 close to 28" but *does `--gap-separate` say what the designer meant*?
   Yes → outcome 2.
3. **Is the intent itself new** — a relationship the ladder cannot name? Yes →
   outcome 1, with sign-off. No → outcome 3.

Question 2 does the work and is the one that gets skipped. Most off-scale spacing
is a pixel disagreement inside an intent both sides already share.

**When it is genuinely 50/50, take outcome 3.** Documenting an exception is
reversible; adding a token is not.

**Copy-ready message.** For a single finding, this is the whole conversation:

> `brand/coral` (#ff6b35) sits next to `--accent-400` (#f57e4e) — close enough
> that they'd read as two attempts at the same colour if they ever land on the
> same screen, far enough that I can't just bind it. Was the ramp step not right
> for this, or is it carried over from an older file? If it's the second, I'll
> rebind to `accent/400` and we're done; if it's the first, tell me what
> `accent-400` was missing and I'll open a proposal.

That message works because it names both values, states the actual consequence,
offers an exit that is not "you were wrong", and asks where it came from —
which is usually "somewhere else", and then nobody has to defend it.

Worked examples of all three outcomes, the escalation path for a genuinely new
token, and the full timed-default table: `references/audit-and-reconcile.md`.

### Step 4 — Generate

Once the audit is clean (or its findings are resolved and defaults recorded):

```bash
# Figma -> code
python scripts/figma_to_tokens.py design/figma-variables.json \
  --format all --out-dir build/tokens

# or one at a time
python scripts/figma_to_tokens.py design/figma-variables.json --format css \
  --out src/styles/tokens.css
```

What it does, and what it refuses to do:

- **Collection → tier, mode → theme.** The default mode becomes `:root`; `Dark`
  becomes `[data-theme="dark"]`; density modes become `[data-density="…"]`.
- **Theme blocks hold only the re-points.** A theme block that repeats an
  inherited value looks like it owns it, and the next person edits the wrong one.
- **Aliases stay aliases.** `bg/surface → neutral/0` becomes
  `--bg-surface: var(--neutral-0)`, never a flattened hex. Flattening is the
  single most common way a sync tool destroys a design system.
- **Names are looked up, never guessed.** `Primitive/Color/Neutral/500` →
  `--neutral-500`. Anything it cannot place against the contract is emitted with
  its own slug and reported as `unmapped-name` on stderr.
- **Ramp colours snap to canonical OKLCH.** A colour whose 8-bit rendering matches
  a ramp step is emitted as that step's exact OKLCH rather than the hex round
  trip's drift — `--neutral-50` comes back as `oklch(98.2% 0.003 75)`, not hue
  84.6. Without this, near-zero-chroma colours produce a hue diff on every run.
- **Broken aliases and cycles do not crash it.** A missing target is emitted as a
  commented-out declaration so the build fails visibly; a cycle is emitted as an
  unresolvable reference and reported.
- Every file carries a **GENERATED — DO NOT EDIT** header naming its source.

Reverse, to make Figma the mirror:

```bash
python scripts/figma_to_tokens.py design/tokens.json --reverse \
  --out figma-payload.json
```

That is a body for `POST /v1/files/:file_key/variables` — collections, modes,
variables and mode values with temporary ids, `{r,g,b,a}` colours in 0..1,
`{"type":"VARIABLE_ALIAS","id":…}` references, and a `codeSyntax.WEB` of
`var(--token)` on every variable so Figma's dev mode shows the real name. It
builds the body; it never calls the API.

**Composites do not cross, in either direction.** `--type-*`, `--motion-*`,
`--shadow-*`, `--elevation-*` and the `clamp()`ed fluid steps are CSS shorthands;
a Figma variable holds one scalar. `--reverse` skips them and says so. They ship
as Figma *styles* named for the same role — see `references/figma-mapping.md`
§7, §8 and §13 (the full loss table).

### Step 5 — Keep in sync

**Pick a source of truth. Write it down. One, not both.**

The failure mode is not choosing wrong; it is not choosing, and then both sides
being edited in the same week.

| | **Code as source** | **Design as source** |
|---|---|---|
| Right for | Engineering-led teams. One or two designers, many engineers. A product where values are constrained by implementation — performance budgets, measured contrast, a11y floors | Design-led teams. A design org that owns the brand. Multiple products consuming one library. Marketing surfaces where the visual decision leads |
| The argument | Values are *verified* in code and merely *drawn* in Figma. Contrast is measured, not eyeballed; `clamp()` and `calc()` only exist here; the audit gate and the type system are here. If the canonical value lives where it cannot be verified, verification is advisory | Designers make hundreds of small decisions a week and should not file a PR for each. The library is the deliverable and it ships to more than one codebase. A value that is canonical in one repo is not canonical for the other four |
| Direction | `tokens.json` → `--reverse` → Figma | Figma → `figma_to_tokens.py` → `tokens.css` |
| Who edits | Engineers, in a PR | Designers, in Figma |
| The other side | Figma is generated and **read-only by convention** | `tokens.css` is generated and `git`-enforced read-only |
| Fails when | Designers edit the mirror anyway, because nobody told them it was a mirror | An unverifiable value ships — a contrast failure, an off-scale step — because nothing gates the design file |

Whichever you pick, put it in `DESIGN_DECISIONS.md` in one sentence, name the
person who owns the source, and say what happens when someone edits the mirror.

**Drift detection in CI.** Regenerate and compare; never let the generated file
be the thing that gets edited.

```yaml
- name: Design tokens are in sync with the Figma export
  run: |
    python scripts/figma_audit.py design/figma-variables.json --fail-on error
    python scripts/figma_to_tokens.py design/figma-variables.json --format css \
      | diff -u src/styles/tokens.css - \
      || { echo "tokens.css is stale — re-run the generator and commit"; exit 1; }
```

On Enterprise, add a scheduled job that pulls the API and opens a PR when the
file has moved. On any other plan, the committed export is the boundary: it only
changes when a human re-exports, and that is a perfectly good tripwire — the diff
in the PR shows exactly what the designer changed.

**What CI cannot catch.** A designer who changes a value in Figma and does not
re-export. The mitigation is social, not technical: the audit is part of every
handoff, and the export is committed with a date. If the date is three months
old, say so.

---

## Routing

| The situation | Go to |
|---|---|
| "The designer sent me a Figma file" | Step 1, then **step 2 before anything else** |
| "Does this design match the system?" | Step 2 |
| "They used a colour that isn't ours" | Step 3, decision rule |
| "I need tokens.css from this file" | Step 4 |
| "How do I get our tokens into Figma?" | Step 4, `--reverse` |
| "Which side wins?" | Step 5 |
| "What does a Figma collection map to?" | `references/figma-mapping.md` §2 |
| "What does auto-layout map to?" | `references/figma-mapping.md` §9 |
| "What gets lost in the sync?" | `references/figma-mapping.md` §13 |
| "What are the exact REST endpoints and the plan gate?" | `references/figma-mapping.md` §14 |
| "How do I report this without a fight?" | `references/audit-and-reconcile.md` §4 |
| "They want a new token" | `references/audit-and-reconcile.md` §10 |
| "Nobody is answering my questions" | `references/audit-and-reconcile.md` §9 |
| Inheriting a codebase that has no tokens | `design-token-migration` |
| Proving every state × theme × density renders | `component-state-matrix` |
| The system itself — scales, architecture, the audit gate | `web-design-studio` |

---

## Scripts

Both are stdlib-only Python 3.9+, run by path from the project root, and detect their
input shape: REST `variables/local`, a plugin `{"collections": […]}` export, W3C
DTCG nested tokens (including 2025.10's object values, `$ref`, `$extends` and
`$root`), or a flat list of `{name, type, value}` records. A composed colour's
opacity is Figma's percentage, 0–100, and an aliased colour keeps its link as
`color-mix(in oklch, var(--x) 8%, transparent)`. Output carries no clock time
(set `SOURCE_DATE_EPOCH` to stamp a date), so the CI drift check compares like
with like.

`figma_audit.py --tokens src/styles/tokens.css` checks colours against the
**project's** ramps — every `--<name>-<step>` in that file holding a literal
colour — instead of the studio's. A client's brand ramp is the point of the
migration that produced it; without `--tokens` it reads as eleven off-ramp errors.

Every argument of `figma_audit.py` and `figma_to_tokens.py` is in `references/scripts.md`.

---

## The nine laws, as they apply here

| Law | In this skill |
|---|---|
| 1 Tokens or nothing | A Figma variable is the design-side literal. A raw hex on a frame is the same defect as a raw hex in CSS |
| 2 Parents own the gaps | Auto-layout gap **is** parent-owned spacing. A well-built Figma file already obeys this; a positioned one cannot express it at all |
| 3 The scale is closed | The audit's tables are the closed scales, executable. Adding a step is a signed-off design-system change |
| 4 One home per component | One Figma component per code component. A detached instance is a second home |
| 5 Layers, not specificity | Modes re-point Tier 2 only, exactly as theme blocks do |
| 6 Semantic before primitive | A frame bound to `neutral/0` instead of `bg/surface` is a component reading Tier 1 |
| 7 Density is a dial | Do not ship a second set of Figma values for compact. One mode plus the multiplier |
| 8 Novel patterns pass the gate | A Figma prototype is not a keyboard spec. Ask for focus order; it is never in the file |
| 9 Nothing ships un-audited | `figma_audit.py` gates the handoff the way `audit_design.py` gates the code |
