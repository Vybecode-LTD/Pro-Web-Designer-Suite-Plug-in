# tooling

The real tools the plugin's tests run its configs and browser scripts through, at pinned versions. Nothing here ships with the plugin.

| Folder | Holds | Used by |
|---|---|---|
| `main/` | ESLint 10 with eslint-plugin-jsx-a11y (via the `overrides` entry the ESLint config's header documents), typescript-eslint with TypeScript 6.0, eslint-plugin-tailwindcss 4, Tailwind 4 and `@tailwindcss/node`, tailwind-merge, stylelint 17 with stylelint-config-standard 40, Playwright 1.63 and axe-core 4.13 | Almost every real-tool and browser test |
| `tailwind-v3/` | ESLint 10, eslint-plugin-tailwindcss 3 and Tailwind 3 (one `node_modules` can hold only one `tailwindcss`) | The Tailwind v3 block of the ESLint config's Part 5 |
| `release/` | `build.py`: the plugin's zip, one `.skill` file per skill and `SHA256SUMS`, from what git holds at a revision, byte-identical on a rebuild. Standard-library Python | `.github/workflows/release.yml`, on a pushed `v*` tag, and `tests/test_release_build.py` |

Install both once:

```
cd tooling/main && npm ci
cd ../tailwind-v3 && npm ci
```

`npm ci` installs no browser: Playwright 1.63 has no install script. The browser tests use Playwright's pinned headless shell when it is installed (`npx playwright install --only-shell chromium`, run in `tooling/main`), and otherwise an installed Chrome or Edge, whose version is not pinned; with neither they skip. They never download a browser themselves.

The tests use these folders for any of `WDS_NODE_MODULES`, `WDS_ESLINT_MODULES`, `WDS_TAILWIND_MODULES`, `WDS_STYLELINT_MODULES` and `WDS_TAILWIND_V3_MODULES` that is not set (`tool_modules` in `tests/wds_support.py`). Set one to `off` to switch its tests off; cmd.exe and PowerShell cannot set an empty value. A `node_modules` installed on another operating system is ignored: `npm ci` installs native bindings (lightningcss) for one platform, so WSL needs its own install.

**Keep this folder beside the plugin, never above it.** Node looks for packages in every parent folder. A `node_modules` above `plugins/` would be found by the plugin's own browser scripts, in place of the stub modules the resolution tests plant.

To move to a newer version, change it in the `package.json`, run `npm install` to update the lockfile, and run the whole suite.
