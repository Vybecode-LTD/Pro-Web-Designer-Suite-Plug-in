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
                    "snapshots": "snapshots/"}
    }

Only `schema` is required. `tokens` holds the project's token files: a
tokens.css, or a contract.json. `emailTokens` is the email build's own
email-tokens.json, a different file that only the email scripts read.
`components` adds globs to the component files the rule spec names
(design-rules.json: file_classes). Paths are relative to the file. An unknown
key, or a value of the wrong shape, is an error that names the key.

A script finds the file by walking up from the working directory to the first
`.design-suite.json`, and stops at the repository root (a folder holding
`.git`). A flag beats the config, and the config beats the script's own
default. The hooks (P25) and the commands (P26) read it through this module.

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
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

CONFIG_NAME = ".design-suite.json"
CONFIG_SCHEMA = 1
CONTRACT_SCHEMA = "web-design-suite/contract/1"
KEYS = ("schema", "tokens", "emailTokens", "components", "stack", "budgets", "baselines")
STACKS = ("vanilla-css", "css-modules", "tailwind-v3", "tailwind-v4")
BUDGETS = ("perf", "a11y")
BASELINES = ("audit", "a11y", "perf", "docs", "snapshots")
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

    @property
    def root(self) -> Path:
        return self.path.parent


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
    if data.get("schema") != CONFIG_SCHEMA:
        raise ConfigError(f'{path}: "schema" must be {CONFIG_SCHEMA}')
    base = path.parent

    def one_path(key: str, value: Any) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise ConfigError(f'{path}: "{key}" must be a path, as a string')
        return base / value

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
                         baselines=path_map("baselines", BASELINES))


def project_config(start: Optional[Union[str, Path]] = None) -> Optional[ProjectConfig]:
    """The config that governs `start`, read and checked, or None."""
    found = find_config(start)
    return load_config(found) if found else None


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
            values = entry.values() if nested and isinstance(entry, dict) else [entry]
            if (nested and not isinstance(entry, dict)) or not all(isinstance(v, str) for v in values):
                shape = "an object of strings" if nested else "a string"
                raise ConfigError(f'{path}: "{section}.{name}" must be {shape}')
        data[section] = value
    return data
