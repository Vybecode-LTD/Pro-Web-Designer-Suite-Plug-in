"""The project contract: a project's `.design-suite.json`, and the
`contract.json` that design-system-docs' extract_system.py writes from its
tokens (P24: XC-C8, LC-C1, LC-B3). Standard library only; Python 3.9 or newer.

shared/project_config.py is the master. Each skill whose scripts read it keeps
a byte-identical copy beside them, so a skill installed on its own still has
one (test_project_config holds every copy to the master).

`.design-suite.json`, at the project's root:

    {
      "schema": 1,
      "tokens": ["src/styles/tokens.css"],
      "emailTokens": "emails/email-tokens.json",
      "components": ["src/widgets/**/*.css"],
      "stack": "tailwind-v4",
      "budgets": {"perf": "perf-budget.json", "a11y": "a11y-budget.json"},
      "baselines": {"audit": ".design-baseline.json", "a11y": ".a11y-baseline.json",
                    "perf": ".perf-baseline.json", "docs": "docs/baseline.json",
                    "snapshots": "snapshots/", "system": "published/system.json"},
      "hooks": {"designGate": true, "generatedFiles": true, "tokenDiff": true}
    }

Only `schema` is required. `tokens` holds the project's token files: a
tokens.css, or a contract.json. `emailTokens` is the email build's own
email-tokens.json, a different file that only the email scripts read.
`components` adds globs to the component files the rule spec names
(design-rules.json: file_classes). `baselines.system` is the published
snapshot that diff_system.py compares against. `hooks` turns on the plugin's
hooks for this project: `designGate` audits each file Claude edits,
`generatedFiles` refuses an edit to a generated file, and `tokenDiff` diffs
the token files against the published snapshot after each edit to one. Paths
are relative to the file. An unknown key, or a value of the wrong shape, is an
error that names the key.

A script finds the file by walking up from the working directory to the first
`.design-suite.json`, and stops at the repository root (a folder holding
`.git`). A flag beats the config, and the config beats the script's own
default. The hooks (P25) and the commands (P26) read it through this module.
shared/project_config.mjs is the same reader for Node, held to this one by
tests/test_project_config.py: the browser scripts and the stylelint and
ESLint configs read the project through it.

`contract.json` holds a token system's default values, by tier:

    {
      "schema": "web-design-suite/contract/1",
      "sources": ["src/styles/tokens.css"],
      "ramps": {"accent": {"500": "oklch(62% 0.19 45)"}},
      "scales": {"space": {"4": "1rem"}, "radius": {"md": "0.5rem"}},
      "roles": {"--bg-surface": "var(--neutral-0)"},
      "breakpoints": {"md": "48rem"},
      "constants": {"--density": "1"}
    }

`ramps` are the Tier-1 colours named `--<ramp>-<step>` with a numeric step;
`scales` the other Tier-1 values, by their first name segment; `breakpoints`
the `--bp-*` values; `constants` a Tier-1 value whose name has one segment
(`--density`); `roles` every Tier-2 token as written. Only a token with a
default value is in it: one declared only in a theme or under a condition is
not. Theme and density overrides stay in extract_system's system.json.

read_tokens() gives the scripts one view of a project's token files, in the
contract's sections, whether a file is a contract.json or a tokens.css (P24
part 2). A tokens.css is read the way extract_system reads a default: the
custom properties of a rule whose selector starts with `:root` (or `html`,
`:where(:root)`, `*`), outside any at-rule but `@layer`, and with no theme or
density selector that names a value. Its tiers come from the value alone: a
value that reads another token is a role, and a literal is Tier 1, which is
extract_system's rule for a name its lists do not cover. extract_system reads
the name first, so a contract.json is the exact form. On the starter's
tokens.css the two differ on seven roles with a literal value (`--bg-hover`,
`--space-fluid-sm`) and on `--shadow-focus`, which reads a token; none is a
ramp step or a breakpoint.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple, Union

CONFIG_NAME = ".design-suite.json"
CONFIG_SCHEMA = 1
CONTRACT_SCHEMA = "web-design-suite/contract/1"
KEYS = ("schema", "tokens", "emailTokens", "components", "stack", "budgets", "baselines", "hooks")
STACKS = ("vanilla-css", "css-modules", "tailwind-v3", "tailwind-v4")
BUDGETS = ("perf", "a11y")
BASELINES = ("audit", "a11y", "perf", "docs", "snapshots", "system")
HOOKS = ("designGate", "generatedFiles", "tokenDiff")     # the plugin's hooks a project turns on (P25)
CONTRACT_SECTIONS = ("ramps", "scales", "roles", "breakpoints", "constants")


class ConfigError(ValueError):
    """A .design-suite.json or contract.json this module cannot accept. The
    message names the file and the key."""


@dataclass
class ProjectConfig:
    path: Path
    tokens: List[Path] = field(default_factory=list)
    email_tokens: Optional[Path] = None
    components: List[str] = field(default_factory=list)
    stack: Optional[str] = None
    budgets: Dict[str, Path] = field(default_factory=dict)
    baselines: Dict[str, Path] = field(default_factory=dict)
    hooks: Dict[str, bool] = field(default_factory=dict)

    @property
    def root(self) -> Path:
        return self.path.parent

    def is_component(self, path: Union[str, Path]) -> bool:
        """True when `path` matches one of `components`, read relative to the
        config's folder: `*` and `?` stay within a folder, and `**/` is any
        number of folders, none included."""
        try:
            rel = Path(path).resolve().relative_to(self.root).as_posix()
        except ValueError:
            return False                    # outside the project
        return any(glob_regex(g).match(rel) for g in self.components)


def glob_regex(pattern: str) -> "re.Pattern[str]":
    """A `components` glob as a regex over a path with forward slashes."""
    out, i = [], 0
    pattern = pattern.replace("\\", "/").lstrip("/")
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def find_config(start: Optional[Union[str, Path]] = None) -> Optional[Path]:
    """The `.design-suite.json` that governs `start` (default: the working
    directory), or None: the first one walking up, never past the folder
    that holds `.git`."""
    here = Path(start if start is not None else Path.cwd()).resolve()
    if here.is_file():
        here = here.parent
    for folder in (here, *here.parents):
        candidate = folder / CONFIG_NAME
        if candidate.is_file():
            return candidate
        if (folder / ".git").exists():
            return None
    return None


def _read_json(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_bytes())    # json finds the encoding, a BOM included
    except OSError as exc:
        raise ConfigError(f"{path}: {exc.strerror or exc}") from exc
    except ValueError as exc:
        raise ConfigError(f"{path}: not JSON ({exc})") from exc


def load_config(path: Union[str, Path]) -> ProjectConfig:
    """Read and check a `.design-suite.json`, with every path resolved
    against its folder."""
    path = Path(path).resolve()
    data = _read_json(path)
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: the top level must be an object")
    unknown = sorted(set(data) - set(KEYS))
    if unknown:
        raise ConfigError(f"{path}: unknown key {unknown[0]!r}; the keys are {', '.join(KEYS)}")
    schema = data.get("schema")
    if isinstance(schema, bool) or schema != CONFIG_SCHEMA:   # `true == 1` in Python, not in JSON
        raise ConfigError(f'{path}: "schema" must be {CONFIG_SCHEMA}')
    base = path.parent

    def one_path(key: str, value: Any) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise ConfigError(f'{path}: "{key}" must be a path, as a string')
        return Path(os.path.normpath(base / value))         # `../shared/tokens.css` too

    def path_list(key: str) -> List[Path]:
        value = data.get(key, [])
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            raise ConfigError(f'{path}: "{key}" must be a path or a list of paths')
        return [one_path(key, v) for v in value]

    def path_map(key: str, names: Sequence[str]) -> Dict[str, Path]:
        value = data.get(key, {})
        if not isinstance(value, dict):
            raise ConfigError(f'{path}: "{key}" must be an object')
        extra = sorted(set(value) - set(names))
        if extra:
            raise ConfigError(f'{path}: unknown key {extra[0]!r} in "{key}"; '
                              f'the keys are {", ".join(names)}')
        return {name: one_path(f"{key}.{name}", v) for name, v in value.items()}

    def hook_flags() -> Dict[str, bool]:
        value = data.get("hooks", {})
        if not isinstance(value, dict):
            raise ConfigError(f'{path}: "hooks" must be an object')
        extra = sorted(set(value) - set(HOOKS))
        if extra:
            raise ConfigError(f'{path}: unknown key {extra[0]!r} in "hooks"; the keys are {", ".join(HOOKS)}')
        bad = next((k for k, v in value.items() if not isinstance(v, bool)), None)
        if bad is not None:
            raise ConfigError(f'{path}: "hooks.{bad}" must be true or false')
        return dict(value)

    components = data.get("components", [])
    if isinstance(components, str):
        components = [components]
    if not isinstance(components, list) or not all(isinstance(g, str) and g for g in components):
        raise ConfigError(f'{path}: "components" must be a glob or a list of globs')
    stack = data.get("stack")
    if stack is not None and stack not in STACKS:
        raise ConfigError(f'{path}: "stack" must be one of {", ".join(STACKS)}')
    email = data.get("emailTokens")
    return ProjectConfig(path=path, tokens=path_list("tokens"),
                         email_tokens=one_path("emailTokens", email) if email is not None else None,
                         components=list(components), stack=stack,
                         budgets=path_map("budgets", BUDGETS),
                         baselines=path_map("baselines", BASELINES), hooks=hook_flags())


def project_config(start: Optional[Union[str, Path]] = None) -> Optional[ProjectConfig]:
    """The config that governs `start`, read and checked, or None."""
    found = find_config(start)
    return load_config(found) if found else None


def config_path(config: Optional[ProjectConfig], section: str, key: str) -> Optional[str]:
    """The config's `budgets.perf`, `baselines.a11y`… as a string, or None,
    for a script's `flag or config_path(...) or default`."""
    value = getattr(config, section).get(key) if config is not None else None
    return str(value) if value is not None else None


def token_sources(flag: Union[None, str, Sequence[str]],
                  start: Optional[Union[str, Path]] = None) -> Tuple[List[Path], Optional[Path]]:
    """The token files a script reads: the flag's when given, else the
    config's. Returns them with the config's path when it supplied them."""
    if flag:
        return [Path(f) for f in ([flag] if isinstance(flag, str) else flag)], None
    config = project_config(start)
    if config and config.tokens:
        return list(config.tokens), config.path
    return [], None


def is_contract(path: Union[str, Path]) -> bool:
    """A token file named `*.json` is a contract.json; anything else is CSS."""
    return Path(path).suffix.lower() == ".json"


def read_contract(path: Union[str, Path]) -> Dict[str, Any]:
    """Read and check a contract.json."""
    data = _read_json(Path(path))
    if not isinstance(data, dict) or data.get("schema") != CONTRACT_SCHEMA:
        raise ConfigError(f'{path}: not a contract.json ("schema" is not "{CONTRACT_SCHEMA}")')
    for section in CONTRACT_SECTIONS:
        value = data.get(section, {})
        if not isinstance(value, dict):
            raise ConfigError(f'{path}: "{section}" must be an object')
        nested = section in ("ramps", "scales")
        for name, entry in value.items():
            if section == "ramps" and isinstance(entry, dict):
                step = next((s for s in entry if not (s.isascii() and s.isdigit())), None)   # not `²`
                if step is not None:
                    raise ConfigError(f'{path}: "ramps.{name}.{step}" must be a numeric step')
            values = entry.values() if nested and isinstance(entry, dict) else [entry]
            if (nested and not isinstance(entry, dict)) or not all(isinstance(v, str) for v in values):
                shape = "an object of strings" if nested else "a string"
                raise ConfigError(f'{path}: "{section}.{name}" must be {shape}')
        data[section] = value
    return data


RAMP_STEP = re.compile(r"^--([a-z][a-z0-9]*(?:-[a-z][a-z0-9]*)*)-([0-9]+)$")    # `\d` takes `٥`
COLOUR_LITERAL = re.compile(r"^(?:#[0-9a-f]{3,8}|(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\()", re.I)
ROOT_SELECTOR = re.compile(r"^(?::root|html|:where\(:root\)|\*)(?![\w-])")
THEME_OR_DENSITY = re.compile(r"\[data-(?:theme|density)\s*[~|^$*]?=")


@dataclass
class ProjectTokens:
    """A project's tokens, in the contract's sections (read_tokens)."""
    sources: List[Path] = field(default_factory=list)
    ramps: Dict[str, Dict[str, str]] = field(default_factory=dict)
    scales: Dict[str, Dict[str, str]] = field(default_factory=dict)
    roles: Dict[str, str] = field(default_factory=dict)
    breakpoints: Dict[str, str] = field(default_factory=dict)
    constants: Dict[str, str] = field(default_factory=dict)

    def values(self) -> Dict[str, str]:
        """Every name, as `--name`, with its default value."""
        out: Dict[str, str] = {}
        for ramp, steps in self.ramps.items():
            out.update((f"--{ramp}-{step}", value) for step, value in steps.items())
        for head, steps in self.scales.items():
            out.update((f"--{head}-{step}", value) for step, value in steps.items())
        out.update((f"--bp-{name}", value) for name, value in self.breakpoints.items())
        out.update(self.constants)
        out.update(self.roles)
        return out

    def tiers(self) -> Dict[str, int]:
        """Every name, as `--name`, with its tier."""
        return {name: 2 if name in self.roles else 1 for name in self.values()}

    def discard(self, name: str) -> None:
        """Remove `name` from whichever section holds it."""
        self.roles.pop(name, None)
        self.constants.pop(name, None)
        if name.startswith("--bp-"):
            self.breakpoints.pop(name[len("--bp-"):], None)
        for section in (self.ramps, self.scales):
            for head in list(section):
                if name.startswith(f"--{head}-"):
                    section[head].pop(name[len(head) + 3:], None)
                    if not section[head]:
                        del section[head]

    def add(self, name: str, value: str, tier: int) -> None:
        """File one default value in its section, as extract_system's
        contract_of does."""
        ramp = RAMP_STEP.match(name)
        if tier == 2:
            self.roles[name] = value
        elif name.startswith("--bp-"):
            self.breakpoints[name[len("--bp-"):]] = value
        elif ramp and COLOUR_LITERAL.match(value):
            self.ramps.setdefault(ramp.group(1), {})[ramp.group(2)] = value
        else:
            head, _, step = name[2:].partition("-")
            if step:
                self.scales.setdefault(head, {})[step] = value
            else:
                self.constants[name] = value


def _css_blocks(text: str) -> Iterator[Tuple[List[str], str]]:
    """Each declaration in a stylesheet with the preludes around it,
    outermost first. Quotes and brackets are skipped, so a `;` in a data URL
    does not end a declaration."""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    stack: List[str] = []
    start, depth, quote, i = 0, 0, "", 0
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == "\\":
                i += 1
            elif ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        elif depth == 0 and ch in "{};":
            chunk = text[start:i].strip()
            if ch == "{":
                stack.append(chunk)
            else:
                if chunk:
                    yield list(stack), chunk
                if ch == "}" and stack:
                    stack.pop()
            start = i + 1
        i += 1


def _css_tokens(path: Path) -> ProjectTokens:
    try:
        text = Path(path).read_bytes().decode("utf-8-sig", errors="replace")
    except OSError as exc:
        raise ConfigError(f"{path}: {exc.strerror or exc}") from exc
    defaults: Dict[str, str] = {}
    for preludes, declaration in _css_blocks(text):
        name, colon, value = declaration.partition(":")
        name, value = name.strip(), " ".join(value.split())    # as extract_system writes it
        if not (colon and name.startswith("--") and value and preludes):
            continue
        rule, outer = preludes[-1], preludes[:-1]
        if (all(p.lower().startswith("@layer") for p in outer)
                and ROOT_SELECTOR.match(rule)                # `:root, [data-theme]` too
                and not THEME_OR_DENSITY.search(rule)):
            defaults[name] = value                   # the cascade: the last one wins
    tokens = ProjectTokens(sources=[Path(path)])
    for name, value in defaults.items():
        tokens.add(name, value, 2 if "var(" in value else 1)
    return tokens


def read_tokens(paths: Sequence[Union[str, Path]]) -> ProjectTokens:
    """A project's token files, contract.json or tokens.css, read in order
    into one ProjectTokens. A later file's value wins, step by step for a
    ramp or a scale, so two files may each hold part of one ramp; a name a
    later file files in another section leaves the earlier one (Codex on #78)."""
    out = ProjectTokens(sources=[Path(p) for p in paths])
    for path in out.sources:
        if is_contract(path):
            data = read_contract(path)
            part = ProjectTokens(ramps=data["ramps"], scales=data["scales"], roles=data["roles"],
                                 breakpoints=data["breakpoints"], constants=data["constants"])
        else:
            part = _css_tokens(path)
        for name in part.values():
            out.discard(name)
        for section in ("ramps", "scales"):
            mine = getattr(out, section)
            for name, steps in getattr(part, section).items():
                mine.setdefault(name, {}).update(steps)
        for section in ("roles", "breakpoints", "constants"):
            getattr(out, section).update(getattr(part, section))
    for name, steps in out.ramps.items():
        out.ramps[name] = dict(sorted(steps.items(), key=lambda kv: int(kv[0])))
    return out
