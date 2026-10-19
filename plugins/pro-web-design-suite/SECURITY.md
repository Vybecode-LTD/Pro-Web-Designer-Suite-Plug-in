# Security

## Reporting a problem

Report a security problem privately, through GitHub's private vulnerability
reporting: open the [development repository's Security tab](https://github.com/Vybecode-LTD/Pro-Web-Designer-Suite-Plug-in/security)
and select **Report a vulnerability**. Please don't open a public issue for it.

Say what you found, how to reproduce it, and which version (`plugin.json`'s
`version`, or the release tag). A fix ships as a patch release, credited to
you unless you'd rather not be named.

## What's in scope

The released plugin: the skills' scripts, the hooks (`hooks/design_hooks.mjs`),
the `gates` MCP server (`mcp/design_gates.mjs`), and what `/install-gate` writes
into a project. For example:

- a script that writes outside the folder it was given, or follows a link out of it;
- a hook or MCP tool that runs something a project's files control, beyond the
  plugin's own scripts;
- a scaffold or template that ships an injection, or weakens row-level security;
- an API key (`CRUX_API_KEY`) that reaches a log, a report or any host other than
  the one it's for.

The design advice in the skills, and a project's own code, are out of scope.

## Supported versions

The latest release. A fix goes into the next release, not into older ones.
