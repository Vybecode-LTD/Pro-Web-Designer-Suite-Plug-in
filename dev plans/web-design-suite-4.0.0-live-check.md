# 4.0.0: the live check (R4)

R4's live check follows R3.6's (`web-design-suite-3.6.0-live-check.md`). The owner chose, on 2026-10-22:
- **the full list** in `next-session-prompt.md` §4 (about 15 headless sessions, about $8 to $10), run in a fresh session with a full budget;
- **the evals** (`evals.yml`, `tag=all`, about $11 under its $14 ceiling) on the release PR's merge, with `headSha` checked, before the tag.

## The free checks (2026-10-22, no model call)

Run at `main` `7ed9937`, with Claude Code **2.1.308** installed from npm into a scratchpad (`npm install @anthropic-ai/claude-code@2.1.308`), since the desktop app's bundled CLI was not at its old path and the one on PATH is 2.1.160. Every `claude plugin` command ran with `CLAUDE_CONFIG_DIR` set to an empty scratch folder, so the owner's own install was never touched.

| Check | Result |
|---|---|
| `build.py --tree` | Exit 0: **229 files**, `.claude-plugin/marketplace.json` at the root (marketplace `pro-web-design-suite`, plugin `./`, `renames`). CI's `claude plugin validate --strict` job validates the same tree with the latest CLI on every PR, and passed on #199. |
| 3.6.0 under its old name | A folder marketplace holding `v3.6.0`'s `.claude-plugin` and `plugins/web-design-suite` (from `git archive`): `marketplace add` names it `web-design-suite`; `plugin install web-design-suite@web-design-suite` installs 3.6.0. |
| The update to 4.0.0 | The same folder replaced by `main`'s files, with `plugin.json` set to 4.0.0. `marketplace update web-design-suite` succeeds and **the marketplace keeps its old name**. `renames` moves `enabledPlugins` to `pro-web-design-suite@web-design-suite`, but `installed_plugins.json` is emptied: `plugin list` shows no plugin, and `plugin update web-design-suite@web-design-suite` fails with "not found". |
| The reinstall | `plugin install pro-web-design-suite@web-design-suite` installs 4.0.0, enabled. `plugin install pro-web-design-suite@pro-web-design-suite`, the command the CHANGELOG gave, **fails**: "not found in marketplace pro-web-design-suite". |

**Defect, fixed in #200:** CHANGELOG.md's *Renamed* note told an existing install to run `/plugin install pro-web-design-suite@pro-web-design-suite`. It now gives `pro-web-design-suite@web-design-suite`, and `test_docs` pins it. A new install from the distribution repository is `pro-web-design-suite@pro-web-design-suite`, as both READMEs say.

**For the paid check:** whether a session start in the desktop app installs the renamed enabled plugin by itself, or shows it as not installed until the reinstall. Run it with the owner's real flow: the development repository as a GitHub marketplace, 3.6.0 installed, then the release.

## The paid sessions

To be run in the R4 session, from `next-session-prompt.md` §4's list.
