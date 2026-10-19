---
name: tw-probe
description: Check what a Tailwind v4 project's theme generates - every role class it declares, none of Tailwind's stock classes, and any class you name - with the project's own tailwindcss.
disable-model-invocation: true
argument-hint: "[--entry FILE] [CLASS ...] [--expect CLASS] [--refuse CLASS]"
allowed-tools:
  - Bash(node "${CLAUDE_PLUGIN_ROOT}/skills/web-design-studio/scripts/tw_probe.mjs" *)
---

# Tailwind probe

Compile the project's Tailwind v4 entry stylesheet with the project's own tailwindcss, from the project's root, and check what it generates. Tailwind writes no CSS for a class it does not know and says nothing, so this is how "the theme removed `p-4`" and "`bg-surface` exists" become facts.

ENTRY is the file the user named, else `src/styles/index.css`, else the stylesheet that imports `tailwindcss` (search `src/` and `app/` for `@import "tailwindcss`). OPTIONS is `$ARGUMENTS` without the entry: classes to report on, `--expect CLASS` for one that must generate, `--refuse CLASS` for one that must not.

```bash
node "${CLAUDE_PLUGIN_ROOT}/skills/web-design-studio/scripts/tw_probe.mjs" --entry ENTRY OPTIONS
```

Then tell the user:
- the verdict, with the counts: the theme variables that give a class and how many generate, and how many of Tailwind's defaults still generate;
- for a stock class that generates: the default that survived, and the line that clears it in the `@theme` block (`--spacing: initial`, or `--*: initial` for every namespace; stack-tailwind.md §2.3 lists what that takes away);
- for a theme variable whose class does not generate: the variable, and that its name is not one Tailwind turns into a utility;
- for a class the user named that generates nothing: Tailwind drops it without a word, so it is not on the theme. Name the role class to use instead (Law 3), never an arbitrary value.

`tw_probe.mjs` exits 1 when a check fails and 2 when it cannot run: no tailwindcss 4 in the project (run it from the project's root, after its install), no entry, or a stylesheet it imports that cannot be read. On Tailwind 3 it exits 2: there Part 5 of `eslint.design.config.mjs`, with its `tailwindConfig` line, checks the classes. Do not edit the theme unless the user asks.
