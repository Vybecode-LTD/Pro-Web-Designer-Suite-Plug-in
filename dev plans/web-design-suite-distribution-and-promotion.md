# web-design-suite: getting listed and getting used

Research, 2026-10-19. Every rule below was read at its source that day; the sources are at the end.
Nothing here has been done yet. The items marked **owner** are decisions only the owner can make.

## Where things stand

- The repository is public, MIT, at v3.6.0. It is its own marketplace (`web-design-suite@web-design-suite`).
- On GitHub it has **no description, no topics, no homepage link, no social-preview image, and 0 stars**.
  Every listing site below ranks by stars or installs, so this costs reach everywhere.
- It is in no directory, awesome list or registry yet.

---

## A. Publishing to Anthropic's directory

### Which "official" this means

Anthropic runs four separate places. Only one takes submissions from authors:

| Place | What it is | Can we get in? |
|---|---|---|
| **Anthropic's directory** (claude.ai/directory, mirrored at claude.com/marketplace/plugins) | The catalog people browse in claude.ai, Cowork, and Claude Code (`/plugin directory`, v2.1.287+). One listing reaches all three. | **Yes.** Submit through the developer portal. This is the route. |
| `claude-plugins-official` | The marketplace Claude Code adds by itself. Anthropic's own plugins plus partners'. | **Not by submission.** The docs say it "doesn't take submissions through the directory portal"; it's open only through an Anthropic partner contact. |
| `claude-plugins-community` (`@claude-community`) | Read-only mirror of plugins that passed review, synced nightly. | Indirectly: plugins approved through the submission pipeline show up here. Pull requests to it are closed automatically. |
| `anthropics/claude-code` demo marketplace | Examples only. | No. |

So the realistic goal is **a directory listing**. That's what the docs and claude.com call publishing to Anthropic.
`claude-plugins-official` would take a partner relationship, which a directory listing with real installs might lead to later.

### Who can submit

- A **paid claude.ai plan** (Pro, Max, Team, Enterprise). On Pro and Max, from your own account.
  On Team or Enterprise, an Owner submits.
- **GitHub connected on claude.ai** in that organization, with push access to `Vybecode-LTD/pro-web-design-suite`, the distribution repository (since 4.0.0).
- The first organization to submit a repository folder **owns that listing for good**. Submit from the
  account that should own it long term (VybeCode's, not a personal one, if that matters).
- There's no partner programme to apply to first, and no separate application for "Verified" or placement:
  Anthropic decides both during review.

### The steps (developer portal, claude.ai/directory/manage)

1. **Submit new → Plugin bundle.**
2. **Source:** repository `Vybecode-LTD/pro-web-design-suite`, the plugin path empty (the plugin is at its root),
   tracked branch or tag (see *Owner decisions* below). **Validate**, fix anything **Blocking**, push, re-validate.
3. **Listing details:** read from `plugin.json` and the plugin's README. To change them, edit the repository and validate again.
4. **Data handling:** whether it reads or stores personal data, sends data anywhere, how long it keeps data, and whether it's meant for under-18s.
5. **Compliance:** a contact email, and four acknowledgements (the Directory Terms and the Directory Policy).
6. **Review and submit:** choose the GitHub push webhook (needs repo admin) or a scheduled check, and decide on auto-publish.

After that, every commit on the tracked branch or tag is validated and security-scanned. **A person reviews the first
listing before it goes live.** Review time isn't fixed. The portal shows status and, once live, installs, versions,
runs per skill and error rates. Updates need no resubmission: merge or move the tag, and the new version is scanned and published.

### How the plugin does against the directory's checks (verified locally today)

**Passes, nothing to do:**

| Check | Limit | Ours |
|---|---|---|
| Repository size as GitHub archives it | < 50 MiB | ~10.3 MiB |
| Files in the repository | < 10,000 | 559 |
| Files in the plugin folder | ≤ 512, or held for a reviewer | **477** (35 to spare, see below) |
| Any non-image file | < 256 KiB, or held | none over |
| Binary files (`.ico`, `.pdf`, `.zip`...) | held | none |
| Symlinks, submodules, LFS | blocks | none |
| `.DS_Store`, `Thumbs.db`... | blocks | none |
| `.gitattributes` `export-ignore` / `filter` | validation stops | none (only `text`/`eol`) |
| `package.json` + lockfile at the plugin root | held | none (the toolchain is in `tooling/`, outside the plugin) |
| README in the plugin folder | ≥ 40 words | ~2,570 |
| LICENSE or `license` | required | both |
| `name`, `description`, `author`, `version` | required/warning | all set |
| `npx`/`uvx` launchers unpinned | blocks | none used |
| MCP and hook paths | full from `${CLAUDE_PLUGIN_ROOT}` | yes |

**Likely "held for a reviewer" (doesn't block; a person reads the version):**

1. **Scripts the validator couldn't follow.** The plugin is a *subfolder* of the repository, and the hooks and the
   MCP server run `node ${CLAUDE_PLUGIN_ROOT}/…/*.mjs`. For a subfolder plugin, the validator follows only plain
   shell scripts, so these are held. The only ways around it are a repository whose root is the plugin, or shell-only hooks.
   A first listing gets a human review anyway, so **accept this hold**.
2. **Credentials read from the environment.** `figma-variables-sync/SKILL.md` uses `FIGMA_TOKEN`, and
   `perf-budget-gate/scripts/crux_check.py` reads `CRUX_API_KEY` and sends it to Google. The checklist holds
   any plugin that reads an env credential and sends it to a server, "even in a README example", and asks for
   a `userConfig` entry with `sensitive: true` instead. **Corrected 2026-10-19: this can't be fixed that way.**
   Claude Code gives a sensitive `userConfig` value only to hooks and MCP servers. Skill content gets a placeholder
   and the Bash tool gets nothing (manifest reference, "Reference a saved value"). `crux_check.py` is a CLI for the
   user's own CI, where a secret arrives as an environment variable, and the Figma `curl` is a step the user runs.
   So both keep their environment variables, the README discloses them (PR 3, "What it runs, sends and stores"),
   and this hold stays: a reviewer reads it.
3. **The name may be read as generic.** Names "made only of generic words" are held as possibly confusable.
   `web-design-suite` is three generic words. See *Owner decisions*.

**Also needed for the review and the Directory Policy:**

- **The README must say everything the plugin runs, sends or fetches.** That covers the hooks (what they do, that
  they're opt-in per project), the local MCP server, Playwright and the browser gates, the Figma REST API, the
  CrUX API, Supabase reads by the scaffold, and that nothing is sent anywhere else. The security scan's failure
  category is "Sends data to an undisclosed destination", so disclosure is the defence.
- **At least three working example prompts** (the policy requires them). The README probably has these in spirit; make them a labelled section.
- **A support contact** for product and security issues: a `SECURITY.md` plus GitHub Issues, or an email.
- **A privacy policy** is needed only if the plugin collects user data or connects to a remote service. It connects
  to Figma and CrUX only with the user's own key, so a short "no data collected" statement on vybecod.ing is the safe course.
- **What users get on each surface:** skills load everywhere. Agents and hooks load in Cowork and Claude Code, not in
  chat. The local MCP server (`gates`) runs only in Claude Code and on-machine Cowork. `userConfig` values aren't
  prompted for in Cowork. The README should say that chat users get the skills only.

### Before you press Submit

- `claude plugin validate --strict` on a checkout of the distribution repository, with the bundled CLI (CI validates `plugins/pro-web-design-suite` on every PR).
- Load it on each surface you want listed: Claude Code, Cowork, and an upload to claude.ai (Customize → Plugins → Upload).
- The eval suite has the "with and without the plugin" comparison the checklist suggests; quote its result in the README.

---

## B. Getting people to use it

The honest starting point: there's a lot of competition, and the leaders are free and simple. Anthropic's
`frontend-design` is a single ~50-line skill with six-figure installs. `ui-ux-pro-max-skill` has tens of thousands of stars
for a design-system generator. Neither enforces anything. **Our difference is the gate:** checks that fail the build
when the design drifts, measured contrast, and ~1,400 tests. Every channel below should lead with that and show it working.

### 1. Fix the storefront first (an afternoon; everything else depends on it)

- **GitHub "About":** a one-line description ("Claude Code plugin: design tokens, measured WCAG contrast and audits
  that fail the build when a website's design drifts"), homepage `https://vybecod.ing`, and topics
  `claude-code`, `claude-code-plugin`, `claude-code-plugins-marketplace`, `claude-skills`, `agent-skills`,
  `design-system`, `design-tokens`, `accessibility`, `wcag`, `css-architecture`, `figma`, `tailwind`.
  The `claude-code-plugin*` topics are what the automated indexes crawl (quemsah/awesome-claude-plugins indexes ~48,800 repositories by them).
- **Social-preview image** (1280×640). It's the card every link share shows. `dev plans/readme-art` can make it.
- **A 30–60 second demo** at the top of the README: Claude writes a hard-coded colour, the gate fails, Claude fixes it with a token. That one loop is the pitch.
- **A one-command install** high in the README, in both forms:
  `/plugin install pro-web-design-suite --marketplace Vybecode-LTD/pro-web-design-suite` (v2.1.275+), then the
  directory listing once it's live.
- **A page on vybecod.ing** for the plugin (the homepage field points there). This is web-facing, so the SEO directive applies.

### 2. Get listed where people browse (free and mostly passive)

| Where | How it lists | Notes |
|---|---|---|
| **Anthropic's directory** | Part A | The biggest single channel: it's inside the product. |
| **awesome-claude-code** (hesreallyhim, ~56k stars) | Web issue form only, filled in **by a human**, one resource at a time | Eligible: the repository is over 14 days old and active. The description must be one plain line, no pitch, no emoji. Its maintainer says plainly that the list follows traction, it doesn't create it. Submit, but don't count on it. |
| **claudemarketplaces.com** | Updates itself; ranks by installs, stars and usage | The topics and stars feed it. |
| **claude-plugins.dev** | Open-source community registry with a CLI | Check its repository (Kamalnrf/claude-plugins) for how to add an entry. |
| **quemsah/awesome-claude-plugins** | Automated crawl | Comes from the GitHub topics. |
| **aitmpl.com / BuildWithClaude / claudedirectory.org** | Curated directories | Each has its own form or PR; one evening covers them all. |
| **skills.sh** (`npx skills add`, Vercel) | Ranked by CLI installs; works on any GitHub repo with skills | A second audience outside Claude Code (Cursor, Codex and others). Caveat: most of our skills need web-design-studio's gate beside them, so say "install the set". |

### 3. Launch posts (one coordinated week, after 1 and 2)

- **Show HN.** Lead with the problem, not the product ("design systems are style guides nobody enforces; we put a gate
  on one"), link the repository, and be in the thread for the first few hours. The Show HN posts in this niche that did
  well asked a real question; the ones that sold a product got 1 to 11 points. Expect questions about what the hooks do on
  your machine and what gets sent where, and answer from the README's disclosure section.
- **Reddit.** r/ClaudeAI puts showcases in its "Built with Claude" megathread unless the poster has **50+ karma** (Rule 7),
  so post from an established account. r/ClaudeCode, and r/webdev or r/Frontend with a *technique* post (how measured
  OKLCH contrast or cascade layers are gated in CI), not an ad. Read each subreddit's self-promotion rule first.
- **dev.to / Medium / your blog:** two or three technique articles that solve a problem and use the plugin, such as
  "Fail the build when a colour misses WCAG AA", "Migrating a legacy CSS codebase onto tokens with a codemod", and
  "Tailwind v4 + design tokens without drift". These rank and get cited by AI answer engines, and both last longer than a launch post.
- **X / Bluesky / LinkedIn:** the demo clip, with tags for the Claude Code community. Design-system people
  (Figma community, Tokens Studio users, Design Systems Slack) are the second audience. The Figma and Tokens Studio sync is the hook for them.
- **Product Hunt:** optional, and only once the directory listing and the demo exist. It drives one day of traffic, mostly from non-developers.

### 4. Keep them (what turns installs into users)

- **Make the first five minutes succeed.** A `/web-design-suite:new-system` or "try it on this sample project" path, so
  the first run shows a passing gate instead of a wall of findings on someone's legacy code.
- **Turn on GitHub Discussions**, answer issues fast (the Directory Policy asks for maintenance anyway), and keep tagging releases with a short CHANGELOG headline.
- **Watch the portal's Usage tab** (installs, runs per skill, error rates) to see which skills people actually use, then lead the marketing with those.
- **"Mentioned in Awesome Claude Code" badge** once accepted, plus a stars badge.

---

## Owner decisions

**Decided 2026-10-19:** the plugin becomes **"Pro Web Design Suite"**: `displayName` "Pro Web Design Suite", with the
permanent id `pro-web-design-suite` (ids must be lowercase and hyphenated). The skills' prefix changes with it
(`/pro-web-design-suite:…`), and about 170 references in the code and config name the old id. It needs its own PR,
with a `renames` entry so existing installs migrate, before anything is submitted.

**Decided 2026-10-19:** `tests/`, `evals/` and `tools/` stay out of what ships. A separate **distribution
repository** holds the built plugin at its root, and `release.yml` fills it on each release. The directory follows
that repository. The rename and the distribution repository are one plan, below.

**Recommended, not yet confirmed:** submit from the paid claude.ai account that should own the listing for good,
with a connected GitHub account that can push to the distribution repository (admin, for the push webhook). The
directory tracks the distribution repository's `main`, which only ever receives releases. Auto-publish on.

## Rename and distribution plan (part of 4.0.0)

The rename changes the slash-command prefix and the MCP tool names, so it's a breaking change. It ships in **4.0.0**
(R4), which is already the active major. Its CHANGELOG entry says so.

### The two repositories

| | Development repository | Distribution repository |
|---|---|---|
| GitHub | `Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in` (unchanged) | **`Vybecode-LTD/pro-web-design-suite`** (new, public, MIT) |
| Holds | Everything: source, `tests/`, `evals/`, `tools/`, `tooling/`, CI, `dev plans/` | Only the built plugin, **at the root**: `.claude-plugin/`, `skills/`, `shared/`, `hooks/`, `mcp/`, `.mcp.json`, `agents/`, `workflow-commands/`, README, CHANGELOG, LICENSE, SECURITY.md |
| Written by | People and agents, through PRs | **Only `release.yml`**: one commit and one `v*` tag per release, fast-forward only, never force-pushed |
| Users install from | (development only) | `/plugin install pro-web-design-suite --marketplace Vybecode-LTD/pro-web-design-suite`, and the directory |
| The directory tracks | | `main` |

Why a repository root rather than a subfolder: the directory's validator follows non-shell hook and MCP scripts
only when the plugin is at a repository's root. In a subfolder, every version is held for a reviewer. At the root
the hold should clear (to confirm with the portal's **Validate**, which is free). The shipped tree drops from 477
files to about 220, well under the 512 line.

### PR 1: the rename (development repository)

- `plugin.json`: `name` `pro-web-design-suite`, `displayName` "Pro Web Design Suite". The `version` goes to 4.0.0 at the release, not in this PR.
- The development repository's `marketplace.json`: the marketplace and the entry named `pro-web-design-suite`,
  with a `renames` entry `web-design-suite → pro-web-design-suite` so existing installs migrate. Mark it as the
  development marketplace in its description, so users go to the distribution repository.
- The folder `plugins/web-design-suite` becomes `plugins/pro-web-design-suite`, so there's one name everywhere. Update the paths in CI, `release.yml`, `tooling/release/build.py` (`PLUGIN`, `TOP`, the zip name), `fail_before.py`, `check.py`, the pointer register, and the Commands block in `CLAUDE.md`.
- Every reference to the old id: about 170 in code and config, plus docs. That includes the `/web-design-suite:…`
  command prefix (hooks' router, workflow-commands, READMEs), the `mcp__plugin_web-design-suite_gates__*` tool names
  (the outcome evals grant these), and the agent names `web-design-suite:*`.
- **What doesn't change:** the thirteen skills' own names, `.design-suite.json` (a user's project file, so renaming it would break their projects), and the `WDS_` environment variables.
- After the merge, the reader's-copies rule applies: copy the three `shared/` masters over every copy if a branch below was merged.
- Timing: the folder move conflicts with every open branch. Land it when no PR from the other session is open (`gh pr list`), or right after one merges.

### PR 2: the distribution pipeline (development repository)

- **`tooling/release/stage.py`** builds the distribution tree from `git archive REV` of the plugin folder, without
  `tests/`, `evals/` and `tools/` (one `DEV_ONLY` list). It adds the distribution `marketplace.json` (one entry,
  `"source": "./"`). The output is deterministic, like `build.py`. The release zip comes from the same tree, so the zip
  and the distribution repository can't differ.
- **A directory preflight test** checks the staged tree against the checklist's rules: `plugin.json` at the root,
  ≤ 512 files, no non-image file ≥ 256 KiB, only allowed binaries, no symlinks, no OS junk, Windows-safe names, README ≥ 40 words,
  LICENSE present, no unpinned launchers, no lockfile at the root, and hook and MCP paths from `${CLAUDE_PLUGIN_ROOT}`.
  Add a positive control (a planted bad file fails it). This stands in for the portal between releases.
- **`release.yml`** gets a second job, after the GitHub release: stage the tree, clone the distribution repository,
  replace its contents, commit (`release 4.0.0 from <sha>`), tag `v4.0.0`, and push fast-forward only. It refuses if
  that tag already exists there. One `concurrency` group, actions pinned to SHAs like the rest. The credential is a
  **deploy key with write access to the distribution repository only**, held in the secret `DIST_DEPLOY_KEY`.
- A `workflow_dispatch` dry run that stages and uploads the tree as an artifact without pushing, so the pipeline can be tested before 4.0.0.
- Docs: `CLAUDE.md` (Commands, Map, the two repositories), `docs/HANDOFF.md`, `tooling/README.md`.

### PR 3: directory readiness (development repository)

The README's
disclosure section (the two keys stay environment variables; see the correction under the holds above), three example prompts, the support line, what each surface gets, and `SECURITY.md`. The README is
the one users see in the directory, so write it for them. Development notes go to the development repository's root README.

### The owner's steps (no agent does these)

1. Create the public repository `Vybecode-LTD/pro-web-design-suite`, empty, with no README or license from GitHub's form. Release.yml provides those.
2. Make a deploy key with write access on it. Put the private half in the development repository's Actions secret `DIST_DEPLOY_KEY`.
3. After 4.0.0 is released and the distribution repository is filled, open claude.ai/directory/manage → Submit new →
   Plugin bundle → `Vybecode-LTD/pro-web-design-suite`, with the path empty and the branch `main`. **Validate** first, then submit, set up the push webhook, and turn auto-publish on if offered.
4. Give the distribution repository its About description, homepage, topics and social preview (Part B1). It's the
   public front door: the directory links to it, so stars and issues gather there. The development repository's README points to it.
5. Turn on **private vulnerability reporting** for the development repository (Settings → Code security). `SECURITY.md`
   sends reports there, and it was off on 2026-10-19.

### Open owner decisions

- Issues in the distribution repository, the development repository, or both. (Recommended: the distribution repository, since that's where users land.)
- Whether to rename the development repository itself. It isn't needed, and GitHub redirects the old URL if you do.

1. **Keep the name `web-design-suite`, or rename before listing?** (Decided above.) The name is permanent once listed: a rename later
   breaks every install (the marketplace has a `renames` map, but the directory listing is tied to the name). It's
   three generic words, so it may be held for review and is hard to search for. With 0 stars, now is the cheapest moment
   to change it, e.g. to a distinctive product name with `displayName` "Pro Web Designer Suite". Keeping it is also fine;
   a hold only means a person reads it.
2. **Which account submits?** That organization owns the listing for good.
3. **What the directory tracks:** `main` (every merge goes live after its scan) or a tag the release workflow moves
   (only releases go live). A moving `release` tag fits the existing "CI is the single release creator" rule better.
4. **Auto-publish** after the first review: on, or a reviewer per version.
5. **The 512-file line.** The plugin folder holds 477 files, `tests/` and `evals/` included. Past 512 every version is
   held for a reviewer. Move `tests/` (and perhaps `evals/` and `tools/`) out of the shipped folder, or accept the holds.
   Moving them touches CI, `fail_before.py` and `WDS_PLUGIN_ROOT`, so it needs its own PR.
6. ~~Is the Figma/CrUX `userConfig` change worth doing?~~ Moot: a sensitive `userConfig` value can't reach a skill's
   script (see the correction under the holds). The keys stay environment variables, and the README discloses them.

## Suggested order

1. The rename and distribution plan above: PR 1 (rename), PR 2 (pipeline, dry-run tested), PR 3 (readiness), then the owner creates the distribution repository and its deploy key.
2. Release 4.0.0, which fills the distribution repository. Give it its About, topics and social preview.
3. Validate the distribution repository in the portal (it's free and shows the real findings before anything is submitted), then **submit**.
4. While it's in review: the demo clip, the vybecod.ing page, the directory listings in B2, one technique article.
5. Once listed: the launch week (B3), then awesome-claude-code.

## Sources (read 2026-10-19)

- Claude Code docs, [Publish and distribute a plugin](https://code.claude.com/docs/en/plugins/publish)
- Claude Code docs, [Anthropic's marketplaces](https://code.claude.com/docs/en/plugins/anthropic-marketplaces)
- claude.com, [Publish to the directory](https://claude.com/docs/directory/publish)
- claude.com, [Submit your plugin](https://claude.com/docs/plugins/submit)
- claude.com, [Plugin pre-submission checklist](https://claude.com/docs/plugins/pre-submission-checklist)
- claude.com, [Plugin feature support across platforms](https://claude.com/docs/plugins/platform-support)
- [Anthropic Software Directory Policy](https://support.claude.com/en/articles/13145358-anthropic-software-directory-policy)
- [anthropics/claude-plugins-community](https://github.com/anthropics/claude-plugins-community), [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official)
- [Claude Marketplace](https://claude.com/marketplace/plugins)
- [awesome-claude-code CONTRIBUTING.md](https://github.com/hesreallyhim/awesome-claude-code/blob/main/CONTRIBUTING.md)
- [claudemarketplaces.com](https://claudemarketplaces.com/), [claude-plugins.dev](https://claude-plugins.dev/), [quemsah/awesome-claude-plugins](https://github.com/quemsah/awesome-claude-plugins)
- [Vercel: introducing skills](https://vercel.com/changelog/introducing-skills-the-open-agent-skills-ecosystem)
- r/ClaudeAI showcase megathread moderator note on the 50-karma rule (April 2026), via search
- Third-party install and star figures (frontend-design, ui-ux-pro-max-skill) are from blogs and disagree with each other; treat them as orders of magnitude only.
