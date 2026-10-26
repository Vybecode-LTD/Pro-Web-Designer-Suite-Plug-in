# tooling

The real tools the plugin's tests run its configs and browser scripts through, at pinned versions. Nothing here ships with the plugin.

| Folder | Holds | Used by |
|---|---|---|
| `main/` | ESLint 10 with eslint-plugin-jsx-a11y (via the `overrides` entry the ESLint config's header documents), typescript-eslint with TypeScript 6.0, eslint-plugin-better-tailwindcss 4.9, Tailwind 4 and `@tailwindcss/node`, tailwind-merge, stylelint 17 with stylelint-config-standard 40 (and for SCSS, stylelint-config-standard-scss 17 and postcss-scss 4), Playwright 1.63 and axe-core 4.13, Vue 3.5 (its SFC compiler and server renderer) and Svelte 5 with jsdom 29, for the scaffold's Vue and Svelte output; MJML 5.4, and React 19.3 with React Email 6.11, which compile and render the email skill's framework starters | Almost every real-tool and browser test |
| `tailwind-v3/` | ESLint 10, eslint-plugin-better-tailwindcss 4.9 and Tailwind 3 (one `node_modules` can hold only one `tailwindcss`) | The ESLint config's Part 5 on Tailwind v3 |
| `release/` | `build.py`: the plugin's zip, one `.skill` file per skill and `SHA256SUMS`, from what git holds at a revision, without the plugin's `tests/`, `evals/` and `tools/`; with `--tree`, the same files unpacked, as the distribution repository holds them. It refuses a build that Anthropic's directory would block, or whose listing icon the directory would not take, and prints what it would hold for a reviewer. `icon.svg` is the source of the plugin's listing icon, rendered at 1024 px to the PNG that `plugin.json`'s `icon` names; give a bundled image a name that no shipped text uses outside `plugin.json` and Markdown image links, or the builder prints a directory hold. Two builds with the same zlib are byte-identical; Python 3.14 on Windows deflates with zlib-ng and the release's Linux with zlib, so a local build's bytes and `SHA256SUMS` differ from the release's while every file is the same: `compare.py` compares them by content. Standard-library Python | `.github/workflows/release.yml`, on a pushed `v*` tag, and `tests/test_release_build.py` |

Install both once:

```
cd tooling/main && npm ci
cd ../tailwind-v3 && npm ci
```

`npm ci` installs no browser: Playwright 1.63 has no install script. The browser tests use Playwright's pinned headless shell when it is installed (`npx playwright install --only-shell chromium`, run in `tooling/main`), and otherwise an installed Chrome or Edge, whose version is not pinned; with neither they skip. They never download a browser themselves.

The tests use these folders for any of `WDS_NODE_MODULES`, `WDS_ESLINT_MODULES`, `WDS_TAILWIND_MODULES`, `WDS_STYLELINT_MODULES` and `WDS_TAILWIND_V3_MODULES` that is not set (`tool_modules` in `tests/wds_support.py`). Set one to `off` to switch its tests off; cmd.exe and PowerShell cannot set an empty value. A `node_modules` installed on another operating system is ignored: `npm ci` installs native bindings (lightningcss) for one platform, so WSL needs its own install.

**Keep this folder beside the plugin, never above it.** Node looks for packages in every parent folder. A `node_modules` above `plugins/` would be found by the plugin's own browser scripts, in place of the stub modules the resolution tests plant.

To move to a newer version, change it in the `package.json`, run `npm install` to update the lockfile, and run the whole suite.
