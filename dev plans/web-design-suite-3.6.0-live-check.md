# 3.6.0: the live check (R3.6, 2026-10-13)

Before the release, each route 3.6.0 changed ran in a real Claude Code session. 3.6.0 adds no hook, command, agent or MCP tool, so the check followed the changed routes instead: one headless session per route, eight in all, plus three reruns. The owner approved eight sessions at about $1.20 to $2.00, capped at $4, and then the three reruns.

## How

- **The sessions.** Each was one `claude -p` session, run with Claude Code 2.1.295 and `claude-sonnet-5-5` on the owner's Max plan.
  - `--plugin-dir` loaded the plugin exported from `main`: `2ecdcc5` (after #119) for the eight, and `05d2508` (after #120) for S1's rerun.
  - `--setting-sources project,local` kept the user's settings, and so their installed plugins, out.
  - Each session was capped at $0.60 ($0.80 for `/schema-to-screens`), with `--permission-mode acceptEdits`.
- **The allow-list.** The first pass allowed `Bash(python *)`, `Bash(python3 *)`, `Bash(node *)` and the gate MCP tools, as R3 did.
  - It refused Claude's compound commands (`S=…; python …`, `cd … && …`), so two sessions went around the scripts.
  - The reruns allowed every Bash and PowerShell command, and `--add-dir` the plugin, so the skills' references could be read too.
- **The projects.** Each session had a fresh copy of a scratch project: the starter's styles, `.design-suite.json`, and the session's own inputs:
  - S2: a Figma REST export, with a Theme collection (Light, Dark) and a Density collection.
  - S3: a Tokens Studio export with `$themes` and math.
  - S4: the starter's roles moved to `light-dark()`, with one dark branch planted too weak.
  - S5: a Vue file (a SCSS block with `color.adjust()`, `:style` and `style=""`), a Svelte file, and an MUI file (`sx` and `styled({})`).
  - S6: `shop.prisma`.
  - S8: a published DTCG `tokens.json` that marks `--bg-highlight` `$deprecated`, a current `tokens.css` without it, and an empty ledger.
- **A free dry run first.** S8's route was run by hand before any session, and it found the first defect (#119).

## What ran

The first pass cost **$2.33** at list price, and the reruns **$0.59**: **$2.92** in all.

| Session | The route (3.6.0 item) | Result |
|---|---|---|
| S1, Figma on the Professional plan | `--reverse --format plugin-script` (P32) | **Defect, #120.** It found no route from `tokens.css`, and `--reverse` read the DTCG files as a flat map. The session wrote its own generator. The rerun after #120 ($0.19) ran `figma_to_tokens.py styles/tokens.css --reverse --format plugin-script` and got a Light and a Dark mode on 62 semantic variables. |
| S2, a Figma export to a DTCG resolver | `--format dtcg --out-dir` (P31 part 3) | The first pass wrote the files by hand, since the allow-list refused its commands. The rerun ($0.17) used the converter: `tokens.json`, `theme-dark.json`, `density-compact.json` and `tokens.resolver.json`, with `figma_audit.py`'s findings carried through. |
| S3, a Tokens Studio export to CSS | the Studio reader (P31 part 2) | **Defect, #121.** In both runs, the second with every command allowed, the session wrote its own Node converter: no route reached figma-variables-sync without the word "Figma". Run by hand, the plugin's converter turns `{space.base} * 4` into `1rem`; the session's own wrote `calc()` in px. |
| S4, `light-dark()` roles | `check_roles` through the MCP server (P33) | **Pass.** It measured 168 combinations and found the 8 planted failures (`--fg-muted` in dark, 2.74 to 3.11:1), with a one-line fix. |
| S5, `/migrate src` | the census of Vue, Svelte and CSS-in-JS (P39) | **Pass.** 26 values in all 3 files. Note: the proposal mapped a grey (`#6b7280`) to `--fg-warning` by ΔE alone, which the session itself questioned (the matcher predates 3.6.0). |
| S6, `/schema-to-screens prisma/schema.prisma` | Prisma (P40) | **Pass.** 6 entities, a join table and 60 questions; the scaffold and the audit; a security pass that says "unknown", not "clean", since Prisma carries no RLS. |
| S7, a card headline and a delete dialog | `cqi`, the top layer, `:user-invalid` (P38) | **Pass.** `clamp(…, 8cqi, …)` in an inline-size container, a `<dialog>` opened with `showModal()`, and an error shown on `:user-invalid`. `audit_design --strict` is clean: the audit refused raw text sizes in the component, so the session added two roles. |
| S8, `/release-check` with a `$deprecated` | the mark reaches the gate (P31 part 4) | **Pass after #119.** It recommends major (`--bg-highlight` removed), and the gate passes on the mark. Its fixture predates #119's record, so 53 tokens still read as added; with a file from the current writer, by hand: 1 major, 0 minor. |

## What it found

- **#119, `diff_system.py`** (the dry run). A published DTCG file against the stylesheet it was written from was a major release for an unchanged system:
  - 27 primitives were spelt another way (`oklch(88%)` for `oklch(88.0%)`, `0px … 0px` for `0 …`, `cubic-bezier(0, 0, 1, 1)` for `linear`);
  - the 53 tokens a DTCG file cannot hold read as added.

  The fix compares by parsed value, and the DTCG writer keeps what it leaves out, with values and marks, in its `$extensions`. Codex found 7 more real issues over three rounds.
- **#120, `figma_to_tokens.py --reverse`** (S1). It had no route from a `tokens.css`. Given a DTCG file, it made variables of the file's groups, or of a resolver's own keys, with exit 0 and no Dark mode. It now reads all three, with themes as modes. Codex found 3 more real issues and CodeRabbit 1.
- **#121, the router** (S3). A Tokens Studio prompt without the word "Figma" heard no skill. The router and the skill's description now name Tokens Studio.
- **Notes, not defects:**
  - A narrow allow-list sends a headless session around the scripts, and a read outside the project is refused unless the plugin folder is added with `--add-dir`.
  - `cluster_values.py` matches a colour to a role by ΔE alone, so a grey can land on `--fg-warning`.
