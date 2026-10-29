"""Five of ruff's checks, kept without ruff (the suite is standard library only).

D9 and G16 (audit, 2026-10-14): a reviewer with lint on listed unused imports
(F401), f-strings with nothing to format (F541), locals assigned and never
read (F841, `families` in perf_audit among them) and `raise` in an `except`
with no `from` (B904), which reads as an error in the handler. Each check is
the rule's plain case, and each has a positive control here.
"""
from __future__ import annotations

import ast
import pathlib
import re
import unittest

from wds_support import PLUGIN, TOOLING

FOLDERS = ("skills", "workflow-commands", "shared", "hooks", "tools", "tests")
LINE_BREAK = re.compile(r"\r\n|\r|\n")


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
    exception, or a bare `raise`, is fine. Each raise is judged by the handler
    it is in, once, and a function or class a handler defines is not in it
    (CodeRabbit on #160)."""
    out = []

    def visit(node, handler):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                visit(child, None)
                continue
            if (handler is not None and isinstance(child, ast.Raise) and child.exc is not None
                    and child.cause is None
                    and not (isinstance(child.exc, ast.Name) and child.exc.id == handler.name)):
                out.append(str(child.lineno))
            visit(child, child if isinstance(child, ast.ExceptHandler) else handler)
    visit(tree, None)
    return out


def unclosed_opens(tree: ast.Module) -> list[str]:
    """SIM115's plain case, T10 (audit, 2026-10-14): `open(…).read()` leaves
    the file to the collector, a ResourceWarning under -W error."""
    return [str(n.lineno) for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Call) and isinstance(n.func.value.func, ast.Name)
            and n.func.value.func.id == "open"]


CHECKS = {"F401": unused_imports, "F541": empty_fstrings, "F841": unread_locals, "B904": raise_without_from,
          "SIM115": unclosed_opens}


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
        nested = ("try:\n    pass\nexcept ValueError as outer:\n    try:\n        pass\n"
                  "    except KeyError as inner:\n        raise inner\n    def later():\n        raise TypeError()\n"
                  "    try:\n        pass\n    except KeyError:\n        raise TypeError(outer)\n")
        self.assertEqual(["13"], self.found("B904", nested))      # once, by its own handler (CodeRabbit on #160)
        in_def = "def g():\n    try:\n        pass\n    except OSError:\n        raise SystemExit(2)\n"
        self.assertEqual(["5"], self.found("B904", in_def))       # a handler inside a function still counts
        self.assertEqual(["1"], self.found("SIM115", "data = open('a').read()\nwith open('b') as fh:\n    fh.read()\n"))


def loops_without_subtest(tree: ast.Module) -> list[str]:
    """T8 (audit, 2026-10-14): an assertion in a test method's loop with no
    `subTest` around it stops the loop at its first failure and hides the rest.
    Each assertion is judged, not each loop: a loop that holds a subTest can
    still assert outside it (Codex on #160). A subTest outside the loop covers
    it too, and a function that is no method on `self` is not read."""
    def is_subtest(node):
        return isinstance(node, ast.With) and any(
            isinstance(i.context_expr, ast.Call) and isinstance(i.context_expr.func, ast.Attribute)
            and i.context_expr.func.attr == "subTest" for i in node.items)

    out = []

    def visit(node, method, looped, covered):
        for child in ast.iter_child_nodes(node):
            own, loop, cover = method, looped, covered
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                own = (not isinstance(child, ast.Lambda) and bool(child.args.args)
                       and child.args.args[0].arg == "self")
                loop = cover = False
            elif isinstance(child, (ast.For, ast.AsyncFor)):   # a case loop; a while follows a chain
                loop = True
            elif is_subtest(child):
                cover = True
            if (own and loop and not cover and isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Attribute) and child.func.attr.startswith("assert")
                    and isinstance(child.func.value, ast.Name) and child.func.value.id == "self"):
                out.append(str(child.lineno))
            visit(child, own, loop, cover)
    visit(tree, False, False, False)
    return out


class TheTestsLoops(unittest.TestCase):

    def test_an_assertion_loop_reports_each_case(self):
        flagged = ("class T:\n    def test_x(self):\n        for v in (1, 2):\n            self.assertTrue(v)\n"
                   "        for v in (1, 2):\n            with self.subTest(v=v):\n                self.assertTrue(v)\n"
                   "        for v in (1, 2):\n            self.assertTrue(v)\n"                  # beside a subTest
                   "            for w in (3, 4):\n                with self.subTest(w=w):\n"
                   "                    self.assertTrue(w)\n"
                   "        with self.subTest(case=1):\n            for v in (1, 2):\n"
                   "                self.assertTrue(v)\n")
        self.assertEqual(["4", "9"], loops_without_subtest(ast.parse(flagged)))
        tests = sorted((PLUGIN / "tests").glob("test_*.py"))
        self.assertGreater(len(tests), 40)
        for path in tests:
            with self.subTest(file=path.name):
                self.assertEqual([], loops_without_subtest(ast.parse(path.read_bytes())))


def runs_alone(tree: ast.Module) -> bool:
    """The module ends a direct run with `unittest.main()` under the
    `__name__ == "__main__"` guard, and imports unittest to call it."""
    imported = any(isinstance(n, ast.Import) and any(a.name == "unittest" for a in n.names) for n in tree.body)
    for node in tree.body:
        if (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__"
                and [getattr(c, "value", None) for c in node.test.comparators] == ["__main__"]):
            calls = [n.func for n in ast.walk(node) if isinstance(n, ast.Call)]
            return imported and any(isinstance(f, ast.Attribute) and f.attr == "main"
                                    and isinstance(f.value, ast.Name) and f.value.id == "unittest" for f in calls)
    return False


class TheTestFilesRunAlone(unittest.TestCase):
    """TEST-19 (audit, 2026-10-28): four test files had no `__main__` guard,
    so `python tests/test_email.py` ran nothing (CodeRabbit on #222)."""

    def test_the_check_finds_its_case(self):
        self.assertTrue(runs_alone(ast.parse('import unittest\nif __name__ == "__main__":\n    unittest.main()\n')))
        for source in ("import unittest\n",                                         # no guard
                       'if __name__ == "__main__":\n    unittest.main()\n',          # unittest not imported
                       'import unittest\nif __name__ == "__main__":\n    pass\n'):     # nothing run
            with self.subTest(source=source):
                self.assertFalse(runs_alone(ast.parse(source)))

    def test_every_test_file_runs_alone(self):
        tests = sorted((PLUGIN / "tests").glob("test_*.py"))
        self.assertGreater(len(tests), 40)
        self.assertEqual([], [p.name for p in tests if not runs_alone(ast.parse(p.read_bytes()))])


class ThePluginsPython(unittest.TestCase):

    def test_the_plugins_python_passes_each_check(self):
        files = sources()
        self.assertGreater(len(files), 100)
        for path in files:
            raw = path.read_bytes()
            # The parser's own line breaks, not splitlines()' (a form feed is
            # none to it), so a finding's line is the line (CodeRabbit on #160).
            lines = LINE_BREAK.split(raw.decode("utf-8"))
            tree = ast.parse(raw)
            for code, check in CHECKS.items():
                # `# noqa: F401` on the line waives it, as for ruff (an availability probe).
                found = [f for f in check(tree) if f"noqa: {code}" not in lines[int(f.split(":")[0]) - 1]]
                with self.subTest(file=path.relative_to(path.parents[2]).as_posix(), check=code):
                    self.assertEqual([], found)


if __name__ == "__main__":
    unittest.main()
