# Pro Web Designer Suite

The source of **web-design-suite**, a Claude Code plugin. It has thirteen skills for designing and building websites that stay coherent under multiple developers: a closed token system, one styling home per component, cascade layers, measured WCAG 2.2 AA contrast, and validators that fail the build on drift.

| Where | What |
|---|---|
| [`plugins/web-design-suite`](plugins/web-design-suite) | The plugin. Its [README](plugins/web-design-suite/README.md) describes the skills, and its [CHANGELOG](plugins/web-design-suite/CHANGELOG.md) the releases. |
| [`dev plans`](dev%20plans) | The review, the phase plans and the reports. |
| [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) | Makes this repository a plugin marketplace. |

## Install

In Claude Code:

```
/plugin marketplace add Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in
/plugin install web-design-suite@web-design-suite
```

The repository is private, so installing from it needs a GitHub account with access. You can also install from a release zip: unpack it, then add the unpacked `web-design-suite` folder as the marketplace.

## Releases

Each release is a tagged commit: `v3.0.0`, `v3.0.1`, `v3.1.0` and `v3.2.0`. Only the `plugins/web-design-suite` folder is installed, so nothing outside it ships to users.

## License

MIT. See [`plugins/web-design-suite/LICENSE`](plugins/web-design-suite/LICENSE).
