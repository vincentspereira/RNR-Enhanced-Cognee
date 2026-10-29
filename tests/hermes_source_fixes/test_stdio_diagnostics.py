"""Source/unit-only stdio diagnostics tests; MCP and startup are doubles.

Only selected real AST nodes execute. No dotenv files, imports of the server,
maintenance schedulers, providers, models or service calls are allowed here.
"""
import ast
import asyncio
from contextlib import redirect_stdout, redirect_stderr
import io
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "bin/enhanced_cognee_mcp_server.py"


def execute_nodes(nodes, namespace):
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SERVER), "exec"), namespace)


class StdioDiagnosticsTests(unittest.TestCase):
    def test_startup_diagnostics_do_not_contaminate_protocol_stdout(self):
        tree = ast.parse(SERVER.read_text())
        main = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "main")
        events = []

        async def init():
            events.append("init")

        async def sprint():
            events.append("sprint")

        async def cleanup():
            events.append("cleanup")

        protocol = '{"jsonrpc":"2.0","id":1,"result":{}}\n'

        async def stdio():
            events.append("stdio")
            sys.stdout.write(protocol)

        namespace = {
            "sys": sys, "init_enhanced_stack": init,
            "init_sprint8_modules": sprint, "cleanup_enhanced_stack": cleanup,
            "mcp": SimpleNamespace(run_stdio_async=stdio),
            "_STDIO_OUTPUT": None,
        }
        execute_nodes([main], namespace)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            asyncio.run(namespace["main"]())
        self.assertEqual(events, ["init", "sprint", "stdio", "cleanup"])
        self.assertEqual(out.getvalue(), protocol)
        self.assertIn("RNR Enhanced Cognee MCP Server", err.getvalue())
        self.assertIn("add_memory: Add memory entry", err.getvalue())
        self.assertTrue(err.getvalue().isascii())

    def test_environment_load_diagnostic_uses_stderr(self):
        tree = ast.parse(SERVER.read_text())
        env = next(n for n in tree.body if isinstance(n, ast.If)
                   and any(isinstance(child, ast.Call)
                           and isinstance(child.func, ast.Attribute)
                           and child.func.attr == "exists"
                           for child in ast.walk(n.test)))
        path = SimpleNamespace(exists=lambda: True)
        loaded = []
        out, err = io.StringIO(), io.StringIO()
        with patch.dict("sys.modules", {"dotenv": SimpleNamespace(load_dotenv=loaded.append)}):
            with redirect_stdout(out), redirect_stderr(err):
                execute_nodes([env], {"env_path": path, "sys": sys,
                                      "_STDIO_OUTPUT": out,
                                      "os": SimpleNamespace(getenv=lambda *args: "1")})
        self.assertEqual(loaded, [path])
        self.assertEqual(out.getvalue(), "")
        self.assertIn("OK Loaded environment from:", err.getvalue())

    def test_cloud_and_shutdown_diagnostics_use_stderr(self):
        tree = ast.parse(SERVER.read_text())
        entry = tree.body[-1]
        for cloud_error in (False, True):
            with self.subTest(cloud_error=cloud_error):
                served = []

                async def serve(**kwargs):
                    served.append(kwargs)
                    if cloud_error:
                        raise RuntimeError("fixture cloud failure")

                def run(coro):
                    if coro.cr_code.co_name == "main":
                        coro.close()
                        raise KeyboardInterrupt
                    return asyncio.run(coro)

                async def main():
                    pass

                args = SimpleNamespace(serve_url="https://fixture.invalid", serve_api_key="")
                parser = SimpleNamespace(add_argument=lambda *a, **k: None, parse_args=lambda: args)
                argparse = SimpleNamespace(ArgumentParser=lambda **kwargs: parser)
                namespace = {
                    "__name__": "__main__", "sys": sys,
                    "os": SimpleNamespace(environ={}),
                    "asyncio": SimpleNamespace(run=run), "main": main,
                }
                out, err = io.StringIO(), io.StringIO()
                with patch.dict("sys.modules", {
                    "argparse": argparse,
                    "cognee.api.v1.serve.serve": SimpleNamespace(serve=serve),
                }):
                    with redirect_stdout(out), redirect_stderr(err):
                        execute_nodes([entry], namespace)
                self.assertEqual(served, [{"url": args.serve_url, "api_key": None}])
                self.assertEqual(out.getvalue(), "")
                self.assertIn("Server stopped", err.getvalue())
                self.assertIn("WARN" if cloud_error else "OK Cloud", err.getvalue())


if __name__ == "__main__":
    unittest.main()
