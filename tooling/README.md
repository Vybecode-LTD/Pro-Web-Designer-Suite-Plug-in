# tooling

The real tools the plugin's tests run its configs and browser scripts through, at pinned versions. Nothing here ships with the plugin.

| Folder | Holds | Used by |
|---|---|---|
| `main/` | ESLint 10 with eslint-plugin-jsx-a11y (via the `overrides` entry the ESLint config's header documents), typescript-eslint with TypeScript 6.0, eslint-plugin-tailwindcss 4, Tailwind 4 and `@tailwindcss/node`, tailwind-merge, stylelint 17 with stylelint-config-standard 40, Playwright 1.63 and axe-core 4.13 | Almost every real-tool and browser test |
| `tailwind-v3/` | ESLint 10, eslint-plugin-tailwindcss 3 and Tailwind 3 (one `node_modules` can hold only one `tailwindcss`) | The Tailwind v3 block of the ESLint config's Part 5 |

Install both once:

```
cd tooling/main && npm ci
cd ../tailwind-v3 && npm ci
```

Set `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` for the first one if the machine already has the browser Playwright 1.63 uses. The tests launch a headless shell and fall back to an installed Chrome or Edge, so they never download a browser.

`tests/wds_support.py` points `WDS_NODE_MODULES`, `WDS_ESLINT_MODULES`, `WDS_TAILWIND_MODULES`, `WDS_STYLELINT_MODULES` and `WDS_TAILWIND_V3_MODULES` here when they are not set. Set one to an empty string to switch its tests off.

**Keep this folder beside the plugin, never above it.** Node looks for packages in every parent folder. A `node_modules` above `plugins/` would be found by the plugin's own browser scripts, in place of the stub modules the resolution tests plant.

To move to a newer version, change it in the `package.json`, run `npm install` to update the lockfile, and run the whole suite.
