"""Four of ruff's checks, kept without ruff (the suite is standard library only).

D9 and G16 (audit, 2026-10-14): a reviewer with lint on listed unused imports
(F401), f-strings with nothing to format (F541), locals assigned and never
read (F841, `families` in perf_audit among them) and `raise` in an `except`
with no `from` (B904), which reads as an error in the handler. Each check is
the rule's plain case, and each has a positive control here.
"""
from __future__ import annotations

import ast
import pathlib
import unittest

from wds_support import PLUGIN, TOOLING

FOLDERS = ("skills", "workflow-commands", "shared", "hooks", "tools", "tests")


def sources() -> list[pathlib.Path]:
    found = [p for folder in FOLDERS for p in sorted((PLUGIN / folder).rglob("*.py"))]
    if TOOLING:
        found.append(TOOLING / "release" / "build.py")
    return found


def unused_imports(tree: ast.Module) -> list[str]:
    """F401: a name an import binds that the module never reads. A name in
    `__all__` is read, and so is one a `del` reads or a string names whole
    (`getattr(module, "name")`)."""
    bound: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                name = alias.asname or alias.name.split(".")[0]
                bound.setdefault(name, node.lineno)
    read = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Load, ast.Del))}
    named = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    return [f"{line}: {name}" for name, line in bound.items() if name not in read | named]


def empty_fstrings(tree: ast.Module) -> list[str]:
    """F541: an f-string with no placeholder. A format spec (`{x:.2f}`) is a
    JoinedStr of its own and is not one."""
    specs = {id(n.format_spec) for n in ast.walk(tree)
             if isinstance(n, ast.FormattedValue) and n.format_spec is not None}
    return [str(n.lineno) for n in ast.walk(tree)
            if isinstance(n, ast.JoinedStr) and id(n) not in specs
            and not any(isinstance(v, ast.FormattedValue) for v in n.values)]


def unread_locals(tree: ast.Module) -> list[str]:
    """F841: a plain `name = …` in a function that the function, and the
    functions inside it, never read (`+=` and `del` read it)."""
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        read = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and not isinstance(n.ctx, ast.Store)}
        read |= {n.target.id for n in ast.walk(fn) if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name)}
        shared = {name for n in ast.walk(fn) if isinstance(n, (ast.Global, ast.Nonlocal)) for name in n.names}
        for node in ast.walk(fn):
            for target in node.targets if isinstance(node, ast.Assign) else []:
                if isinstance(target, ast.Name) and target.id not in read | shared and not target.id.startswith("_"):
                    out.append(f"{node.lineno}: {target.id} in {fn.name}()")
    return out


def raise_without_from(tree: ast.Module) -> list[str]:
    """B904: `raise X` in an `except` with no `from`; re-raising the caught
    exception, or a bare `raise`, is fine."""
    out = []
    for handler in ast.walk(tree):
        if isinstance(handler, ast.ExceptHandler):
            for node in ast.walk(ast.Module(body=handler.body, type_ignores=[])):
                if (isinstance(node, ast.Raise) and node.exc is not None and node.cause is None
                        and not (isinstance(node.exc, ast.Name) and node.exc.id == handler.name)):
                    out.append(str(node.lineno))
    return out


CHECKS = {"F401": unused_imports, "F541": empty_fstrings, "F841": unread_locals, "B904": raise_without_from}


class TheChecksFindTheirCase(unittest.TestCase):
    """The positive controls: each check finds its rule's case and passes the
    forms beside it."""

    def found(self, check, src):
        return CHECKS[check](ast.parse(src))

    def test_each_check_finds_its_case(self):
        self.assertEqual(["1: os"], self.found("F401", "import os\nimport re\nre.compile('x')\n"))
        self.assertEqual([], self.found("F401", "import os\n__all__ = ['os']\n"))
        self.assertEqual([], self.found("F401", "from __future__ import annotations\n"))
        self.assertEqual(["1"], self.found("F541", "x = f'plain'\ny = f'{x:>4}'\n"))
        self.assertEqual(["2: unused in f()"],
                         self.found("F841", "def f():\n    unused = 1\n    total = 0\n    total += 1\n"
                                            "    gone = 2\n    del gone\n    return total\n"))
        self.assertEqual([], self.found("F841", "def f():\n    seen = []\n    def g():\n        return seen\n    return g\n"))
        self.assertEqual(["4"], self.found("B904", "try:\n    pass\nexcept ValueError as exc:\n    raise TypeError(exc)\n"))
        self.assertEqual([], self.found("B904", "try:\n    pass\nexcept ValueError as exc:\n    raise\n"
                                                "try:\n    pass\nexcept ValueError as exc:\n    raise exc\n"
                                                "try:\n    pass\nexcept ValueError:\n    raise TypeError() from None\n"))


class ThePluginsPython(unittest.TestCase):

    def test_the_plugins_python_passes_each_check(self):
        files = sources()
        self.assertGreater(len(files), 100)
        for path in files:
            raw = path.read_bytes()
            lines = raw.decode("utf-8").splitlines()
            tree = ast.parse(raw)
            for code, check in CHECKS.items():
                # `# noqa: F401` on the line waives it, as for ruff (an availability probe).
                found = [f for f in check(tree) if f"noqa: {code}" not in lines[int(f.split(":")[0]) - 1]]
                with self.subTest(file=path.relative_to(path.parents[2]).as_posix(), check=code):
                    self.assertEqual([], found)


if __name__ == "__main__":
    unittest.main()
