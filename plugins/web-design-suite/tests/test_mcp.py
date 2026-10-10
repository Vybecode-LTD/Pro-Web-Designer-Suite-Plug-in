"""The plugin's MCP server (P28, XC-B1).

.mcp.json runs mcp/design_gates.mjs under node, and Claude Code talks to it
over stdio: JSON-RPC 2.0, one message per line. It lists five tools, the
gates, and each call runs the skill's script in the project's folder and
returns the script's JSON with its exit code and a verdict. Each case here
sends the messages Claude Code sends.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import unittest

from wds_support import NODE, PLUGIN, TempDirTest, env, output

SERVER = PLUGIN / "mcp" / "design_gates.mjs"
TOOLS = ["audit_design", "a11y_static", "perf_audit", "check_roles", "diff_system"]
LEAK = "@layer components {\n  .card {\n    color: var(--neutral-700);\n  }\n}\n"
CLEAN = "@layer components {\n  .card {\n    color: var(--fg-default);\n  }\n}\n"
PAGE = '<!doctype html>\n<html lang="en">\n<head><title>Home</title></head>\n<body>\n<main>\n{}\n</main>\n</body>\n</html>\n'
STARTER = PLUGIN / "skills" / "web-design-studio" / "assets" / "starter" / "styles" / "tokens.css"


def find_claude():
    """WDS_CLAUDE, else the newest CLI the desktop app bundles on Windows: the
    one on PATH can be older than the manifest checks (CLAUDE.md)."""
    named = os.environ.get("WDS_CLAUDE")
    if named:
        return named
    bundled = sorted(pathlib.Path(os.environ.get("APPDATA", "-")).glob("Claude/claude-code/*/*/claude.exe"),
                     key=lambda p: [int(n) if n.isdigit() else 0 for n in p.parent.parent.name.split(".")])
    return str(bundled[-1]) if bundled else None


CLAUDE = find_claude()


class TheServerFile(unittest.TestCase):
    def test_mcp_json_runs_the_server_under_node(self):
        """Exec form with `node`, the one name node has on every system, as the
        hooks run (claude-code-capabilities.md §6); Claude Code substitutes
        ${CLAUDE_PLUGIN_ROOT} in a stdio server's args (§9)."""
        config = json.loads((PLUGIN / ".mcp.json").read_text(encoding="utf-8"))
        self.assertEqual({"gates": {"command": "node", "args": ["${CLAUDE_PLUGIN_ROOT}/mcp/design_gates.mjs"]}},
                         config["mcpServers"])

    @unittest.skipUnless(CLAUDE, "no claude CLI (WDS_CLAUDE, or the desktop app's bundled one)")
    def test_claude_plugin_validate_strict_passes(self):
        """From 2.1.281 the validator checks each server in .mcp.json too: an
        entry it would drop, an undeclared ${user_config.KEY} (§9)."""
        proc = subprocess.run([CLAUDE, "plugin", "validate", "--strict",
                               str(PLUGIN / ".claude-plugin" / "plugin.json")],
                              env=env(), capture_output=True, timeout=120)
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertIn("Validation passed", proc.stdout.decode("utf-8", "replace"))

    def test_every_tool_runs_a_script_the_plugin_has(self):
        scripts = re.findall(r"script: '([^']+)'", SERVER.read_text(encoding="utf-8"))
        self.assertEqual(len(TOOLS), len(scripts))
        for script in scripts:
            with self.subTest(script=script):
                self.assertTrue((PLUGIN / script).is_file())


@unittest.skipUnless(NODE, "node is not installed")
class ServerTest(TempDirTest):
    def setUp(self):
        super().setUp()
        self.write(".git/HEAD", "x\n")

    def session(self, *messages, **changes):
        """The replies, by id, to `messages` sent as one session that ends when
        stdin closes."""
        changes.setdefault("WDS_PYTHON", sys.executable)
        changes.setdefault("CLAUDE_PROJECT_DIR", str(self.tmp))
        text = "".join(m if isinstance(m, str) else json.dumps(m) + "\n" for m in messages)
        proc = subprocess.run([NODE, str(SERVER)], input=text.encode(), cwd=self.tmp.parent, env=env(**changes),
                              capture_output=True, timeout=300)
        self.assertEqual(0, proc.returncode, output(proc))
        replies = [json.loads(line) for line in proc.stdout.decode("utf-8").splitlines()]
        self.assertTrue(all(r["jsonrpc"] == "2.0" for r in replies))
        return {r.get("id"): r for r in replies}

    def call(self, tool, arguments=None, **changes):
        reply = self.session({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                              "params": {"name": tool, "arguments": arguments or {}}}, **changes)[1]
        return reply

    def result(self, tool, arguments=None, **changes):
        """The tool's payload, from a call that ran."""
        reply = self.call(tool, arguments, **changes)
        self.assertIn("result", reply, reply)
        [content] = reply["result"]["content"]
        self.assertFalse(reply["result"]["isError"], content["text"])
        return json.loads(content["text"])


class TheProtocol(ServerTest):
    def test_the_handshake(self):
        replies = self.session(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "initialize", "params": {"protocolVersion": "1999-01-01"}},
            {"jsonrpc": "2.0", "id": 3, "method": "ping"})
        self.assertEqual([1, 2, 3], sorted(replies))                    # a notification has no reply
        version = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
        first = replies[1]["result"]
        self.assertEqual("2025-06-18", first["protocolVersion"])
        self.assertEqual({"name": "web-design-suite-gates", "version": version}, first["serverInfo"])
        self.assertIn("tools", first["capabilities"])
        self.assertEqual("2025-06-18", replies[2]["result"]["protocolVersion"])   # one it does not speak: its newest
        self.assertEqual({}, replies[3]["result"])

    def test_the_tools_are_listed_with_their_schemas(self):
        tools = self.session({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})[1]["result"]["tools"]
        self.assertEqual(TOOLS, [t["name"] for t in tools])
        for tool in tools:
            with self.subTest(tool=tool["name"]):
                schema = tool["inputSchema"]
                self.assertEqual(("object", False), (schema["type"], schema["additionalProperties"]))
                self.assertTrue(tool["description"])
                self.assertTrue(tool["annotations"]["readOnlyHint"])
        self.assertEqual(["tokens"], tools[3]["inputSchema"]["required"])

    def test_mistakes_are_protocol_errors(self):
        call = lambda n, name, arguments: {"jsonrpc": "2.0", "id": n, "method": "tools/call",   # noqa: E731
                                           "params": {"name": name, "arguments": arguments}}
        replies = self.session(
            call(1, "audit", {}),
            call(2, "audit_design", {"path": "src"}),
            call(3, "audit_design", {"paths": "src"}),
            call(4, "check_roles", {}),
            call(5, "diff_system", {"new": "tokens.css"}),
            call(6, "a11y_static", {"strict": "yes"}),
            {"jsonrpc": "2.0", "id": 7, "method": "resources/list"},
            "{not json\n")
        expected = {1: (-32602, "unknown tool 'audit'"), 2: (-32602, "unknown argument 'path'"),
                    3: (-32602, "'paths' must be a list of paths"), 4: (-32602, "'tokens' is required"),
                    5: (-32602, "'new' needs 'old'"), 6: (-32602, "'strict' must be true or false"),
                    7: (-32601, "no method 'resources/list'"), None: (-32700, "not JSON")}
        for n, (code, message) in expected.items():
            with self.subTest(id=n):
                self.assertEqual(code, replies[n]["error"]["code"])
                self.assertIn(message, replies[n]["error"]["message"])


class TheGates(ServerTest):
    def test_the_audit_finds_a_leak(self):
        self.write("src/components/card.css", LEAK)
        payload = self.result("audit_design", {"paths": ["src"]})
        self.assertEqual(("audit_design", 1, "fail"), (payload["tool"], payload["exit"], payload["verdict"]))
        self.assertEqual(["tier1-leak"], [f["rule"] for f in payload["report"]])
        self.write("src/components/card.css", CLEAN)
        self.assertEqual("pass", self.result("audit_design", {"paths": ["src"]})["verdict"])

    def test_the_projects_config_reaches_the_script(self):
        """The scripts run in the project's folder, so its .design-suite.json counts."""
        self.write(".design-suite.json", json.dumps({"schema": 1, "tokens": "src/brand/palette.css",
                                                     "components": ["src/widgets/**"]}))
        self.write("src/brand/palette.css", "@layer tokens {\n  :root {\n    --brand-500: #b4400a;\n  }\n}\n")
        self.write("src/widgets/card.css", "@layer layout {\n  .card {\n    color: var(--brand-500);\n  }\n}\n")
        payload = self.result("audit_design", {"paths": ["src/widgets"]})
        self.assertIn("tier1-leak", [f["rule"] for f in payload["report"]])

    def test_the_a11y_checks(self):
        self.write("index.html", PAGE.format('<img src="hero.png">'))
        payload = self.result("a11y_static", {"paths": ["index.html"]})
        self.assertEqual("fail", payload["verdict"])
        self.assertEqual(["img-no-alt"], [f["rule"] for f in payload["report"]["findings"]])

    def test_the_contrast_of_the_starters_roles(self):
        self.write("tokens.css", STARTER.read_text(encoding="utf-8"))
        payload = self.result("check_roles", {"tokens": "tokens.css"})
        self.assertEqual("pass", payload["verdict"])
        self.assertTrue(payload["report"])

    def test_the_token_diff(self):
        old = "@layer tokens {\n  :root {\n    --neutral-0: #fff;\n    --bg-surface: var(--neutral-0);\n  }\n}\n"
        self.write("published/tokens.css", old)
        self.write("tokens.css", old.replace("--bg-surface", "--bg-canvas"))
        payload = self.result("diff_system", {"old": "published/tokens.css", "new": "tokens.css"})
        self.assertEqual("major", payload["report"]["bump"]["level"])

    def test_the_build_weigh_in(self):
        self.write("dist/index.html", PAGE.format("<p>Hello</p>"))
        self.write("dist/app.css", "body { margin: 0; }\n")
        payload = self.result("perf_audit", {"paths": ["dist"]})
        self.assertIn(payload["verdict"], ("pass", "fail"))
        self.assertIsInstance(payload["report"], dict)

    def test_a_path_is_never_an_option(self):
        """A path the model passes reaches the script after `--`, so
        `--write-baseline=x.json` is a file name, never the option."""
        self.write("index.html", PAGE.format('<img src="hero.png">'))
        reply = self.call("a11y_static", {"paths": ["--write-baseline=x.json"]})
        self.assertTrue(reply["result"]["isError"])
        self.assertIn("no such path: --write-baseline=x.json", reply["result"]["content"][0]["text"])
        self.assertFalse((self.tmp / "x.json").exists())

    def test_a_long_report_is_cut_to_fit(self):
        """Claude Code warns past 10,000 tokens of tool output and stops at
        25,000, so a report keeps the head of its longest list within 60,000
        characters and counts the rest."""
        rules = "".join(f"  .c{n} {{ color: var(--neutral-700); }}\n" for n in range(6000))
        self.write("src/components/many.css", "@layer components {\n" + rules + "}\n")
        reply = self.call("audit_design", {"paths": ["src"]})
        text = reply["result"]["content"][0]["text"]
        self.assertLessEqual(len(text), 60000)
        payload = json.loads(text)
        [cut] = payload["truncated"]["lists"]
        self.assertEqual(("the report", 6000, len(payload["report"])), (cut["list"], cut["total"], cut["shown"]))
        self.assertGreater(cut["shown"], 50)
        self.assertIn("run audit_design.py", payload["truncated"]["rest"])

    def test_a_long_nested_list_is_cut_too(self):
        """Codex on #92: most of perf_audit's report is the nested
        `ledger.assets`, which a cut of the top-level lists alone left whole,
        past the limit."""
        self.write("dist/index.html", PAGE.format("<p>Hello</p>"))
        for n in range(1200):
            self.write(f"dist/assets/chunk-{n:04d}-with-a-long-hashed-name.js", "x;")
        reply = self.call("perf_audit", {"paths": ["dist"]})
        text = reply["result"]["content"][0]["text"]
        self.assertLessEqual(len(text), 60000)
        payload = json.loads(text)
        cuts = {c["list"]: c for c in payload["truncated"]["lists"]}
        self.assertIn("ledger.assets", cuts)
        self.assertEqual(1201, cuts["ledger.assets"]["total"])
        self.assertEqual(len(payload["report"]["ledger"]["assets"]), cuts["ledger.assets"]["shown"])
        self.assertIn("findings", payload["report"])

    def test_a_timeout_is_said_as_one(self):
        """CodeRabbit on #92: a script stopped at the time limit read as
        `stopped (exit null)`."""
        self.write("tokens.css", STARTER.read_text(encoding="utf-8"))
        reply = self.call("check_roles", {"tokens": "tokens.css"}, WDS_MCP_TIMEOUT_MS="1")
        self.assertTrue(reply["result"]["isError"])
        text = reply["result"]["content"][0]["text"]
        self.assertIn("check_roles took longer than 0.001 seconds and was stopped", text)
        self.assertIn("WDS_MCP_TIMEOUT_MS", text)

    def test_a_report_with_nothing_left_to_cut_gives_way(self):
        """CodeRabbit on #92: a report past the limit with every list cut, one
        long text, was returned whole."""
        script = (f"import {{ fit }} from {json.dumps(SERVER.as_uri())};\n"
                  "const long = 'x'.repeat(100000);\n"
                  "const cases = [{ note: long }, { findings: [1, 2, 3], note: long }];\n"
                  "console.log(JSON.stringify(cases.map((report) => fit({ tool: 'check_roles', exit: 0, "
                  "verdict: 'pass', report }))));\n")
        proc = subprocess.run([NODE, "--input-type=module", "-e", script], env=env(), capture_output=True,
                              timeout=60)
        self.assertEqual(0, proc.returncode, output(proc))
        self.assertEqual(b"", proc.stderr)
        for payload in json.loads(proc.stdout):
            with self.subTest(keys=sorted(payload)):
                self.assertIsNone(payload["report"])
                self.assertIn("with every list cut", payload["truncated"]["omitted"])
                self.assertIn("run check_roles.py", payload["truncated"]["rest"])
                self.assertEqual(("check_roles", "pass"), (payload["tool"], payload["verdict"]))
                self.assertLessEqual(len(json.dumps(payload)), 60000)

    def test_a_script_that_stops_or_no_python_is_said(self):
        reply = self.call("check_roles", {"tokens": "missing.css"})
        self.assertTrue(reply["result"]["isError"])
        self.assertIn("check_roles stopped (exit 2)", reply["result"]["content"][0]["text"])
        reply = self.call("check_roles", {"tokens": "missing.css"}, WDS_PYTHON=str(self.tmp / "no-python"))
        self.assertIn("need Python 3", reply["result"]["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
