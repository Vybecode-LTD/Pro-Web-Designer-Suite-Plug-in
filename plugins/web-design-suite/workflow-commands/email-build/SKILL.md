---
name: email-build
description: Build an HTML email from its template - lint the source, compile it with the tokens, lint the result, and render it light, dark and without styles.
disable-model-invocation: true
argument-hint: "TEMPLATE.html [--transactional]"
allowed-tools:
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/skills/email-template-system/scripts/lint_email.py" *)
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/skills/email-template-system/scripts/lint_email.py" *)
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/skills/email-template-system/scripts/build_email.py" *)
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/skills/email-template-system/scripts/build_email.py" *)
  - Bash(node "${CLAUDE_PLUGIN_ROOT}/skills/email-template-system/scripts/render_email.mjs" *)
---

# Email build

Run email-template-system's build on the template the user names, from the project's root. TEMPLATE is its path (from `$ARGUMENTS`), and NAME its file name without `.html`. Without one, ask: a new email starts as a copy of one of that skill's `assets/templates/`, committed in the project. Use `python3` where `python` is not Python 3 (macOS). The email tokens are `.design-suite.json`'s `emailTokens` when it names them.

1. **Lint the source**: tokens only, no literals, utilities last.
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/email-template-system/scripts/lint_email.py" TEMPLATE --source
   ```
   An error stops the build: fix the source first.
2. **Compile**: tokens resolved, CSS inlined, the media queries kept, the Outlook scaffolding added, the plain-text part written.
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/email-template-system/scripts/build_email.py" TEMPLATE --out design-reports/email/NAME.html --text design-reports/email/NAME.txt
   ```
3. **Lint the result.** Add `--transactional` for a receipt, a password reset or any mail the user did not opt into.
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/skills/email-template-system/scripts/lint_email.py" design-reports/email/NAME.html
   ```
4. **Render** it at 375px, light, dark and with no `<style>` block (the Gmail app with a non-Google account). It needs `playwright` in the project; without it, skip this step and say so.
   ```bash
   node "${CLAUDE_PLUGIN_ROOT}/skills/email-template-system/scripts/render_email.mjs" design-reports/email/NAME.html --out design-reports/email/renders
   ```

Then tell the user:
- each lint error and warning, with its fix, and the built size against Gmail's clipping limit;
- where the HTML, the plain text and the renders are. Read the plain-text part: somebody receives it. Look at the three renders;
- what no local check covers: the paid client tests, and what the ESP does to the HTML (that skill's `references/email-workflow.md` §5 and §8).
