"""Tests for the getx command grammar, help, exit codes and JSON output.

Run from the repository root:

    python3 -m unittest discover -s tests -v

No Flutter, get_cli or network needed: commands that would touch a project run
with --dry-run or against a fake project, and `--no-get-cli` forces templates.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "flutter-getx" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import getx  # noqa: E402
from test_scripts import make_project, run  # noqa: E402


def getx_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / "getx.py"), *args], cwd=cwd,
                          capture_output=True, text=True, stdin=subprocess.DEVNULL)


class ParserTest(unittest.TestCase):
    def p(self, line: str) -> dict:
        import shlex
        return getx.parse(shlex.split(line))

    def test_design_d2_rows(self):
        c = self.p("create page:cart on home")
        self.assertEqual((c["verb"], c["target"], c["name"], c["on"]), ("create", "page", "cart", "home"))
        c = self.p('create page:"Order History"')
        self.assertEqual(getx.snake(c["name"]), "order_history")
        c = self.p("create feature:products with https://api/x")
        self.assertEqual((c["target"], c["with"]), ("feature", "https://api/x"))
        c = self.p("generate model:Product with sample.json on shop")
        self.assertEqual((c["target"], c["name"], c["with"], c["on"]), ("model", "Product", "sample.json", "shop"))
        c = self.p('create string:checkout "Checkout" --ar "الدفع"')
        self.assertEqual((c["name"], c["text"], c["lang"]), ("checkout", ["Checkout"], {"ar": "الدفع"}))
        c = self.p("install fcm")
        self.assertEqual((c["verb"], c["text"]), ("install", ["fcm"]))
        c = self.p("install lottie --dev")
        self.assertEqual((c["text"], c["flags"].get("--dev")), (["lottie"], True))

    def test_flags_anywhere_and_free_text(self):
        c = self.p('--json create page:profile showing the saved "user\'s" email --yes')
        self.assertTrue(c["flags"]["--json"] and c["flags"]["--yes"])
        self.assertEqual(c["text"], ["showing", "the", "saved", "user's", "email"])
        c = self.p("create project:my_shop --platforms android,ios --title='My Shop'")
        self.assertEqual(c["flags"]["--platforms"], "android,ios")
        self.assertEqual(c["flags"]["--title"], "My Shop")

    def test_aliases_and_help(self):
        self.assertEqual(self.p("")["verb"], "help")
        self.assertEqual(self.p("-v")["verb"], "version")
        self.assertEqual(self.p("help create")["topic"], "create")
        self.assertEqual(self.p("new page:x")["verb"], "create")

    def test_invalid_usage(self):
        for line, fragment in [
            ("creat page:cart", "Did you mean: getx create page:cart"),
            ("create pag:cart", "Did you mean: getx create page:cart"),
            ("create", "create needs a target"),
            ("generate modle:X with a.json", "Did you mean: getx generate model:X"),
            ("create page:x --jsno", "did you mean --json"),
            ("create page:x --project", "--project needs a value"),
        ]:
            with self.assertRaises(getx.UsageError) as ctx:
                self.p(line)
            self.assertIn(fragment, str(ctx.exception), line)


class CliTest(unittest.TestCase):
    def test_help_and_version_exit_zero(self):
        r = getx_cli("help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("usage: getx", r.stdout)
        for verb in ("create", "generate", "init", "install", "upgrade", "doctor", "install-cli"):
            r = getx_cli("help", verb)
            self.assertEqual(r.returncode, 0, verb)
            self.assertIn(f"getx {verb}", r.stdout)
        self.assertIn(getx.VERSION, getx_cli("--version").stdout)

    def test_usage_errors_exit_two(self):
        for args in (["creat", "page:x"], ["create", "project"], ["create", "controller:edit"],
                     ["create", "feature:x"], ["create", "string:k"], ["generate", "model:X"],
                     ["install"], ["help", "creat"]):
            r = getx_cli(*args)
            self.assertEqual(r.returncode, 2, args)
            self.assertTrue(r.stderr.startswith("getx: "), args)

    def test_json_contract(self):
        r = getx_cli("create", "project", "--json")
        self.assertEqual(r.returncode, 2)
        d = json.loads(r.stdout)
        for key in ("ok", "command", "created", "modified", "skipped", "next", "error"):
            self.assertIn(key, d)
        self.assertFalse(d["ok"])
        self.assertIn("project name required (e.g. getx create project:my_shop)", d["error"])
        self.assertEqual(json.loads(getx_cli("version", "--json").stdout)["version"], getx.VERSION)


class ProjectCommandTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = make_project(Path(self.tmp.name))
        run("scaffold.py", str(self.p))

    def tearDown(self):
        self.tmp.cleanup()

    def g(self, *args):
        return getx_cli(*args, "--project", str(self.p), "--no-get-cli")

    def tree(self):
        return sorted((str(f), f.read_bytes()) for f in self.p.rglob("*") if f.is_file())

    def test_dry_run_writes_nothing(self):
        before = self.tree()
        for args in (["create", "page:cart"], ["create", "page:cart", "on", "home"],
                     ["create", "controller:edit", "on", "home"], ["create", "view:edit", "on", "home"],
                     ["create", "string:hi", "Hi"], ["generate", "locales"],
                     ["generate", "model:Thing", "with", '{"id": 1, "r": {"a": 2}}']):
            r = self.g(*args, "--dry-run", "--json")
            self.assertEqual(r.returncode, 0, f"{args}: {r.stdout}{r.stderr}")
            self.assertTrue(json.loads(r.stdout).get("dry_run"), args)
        self.assertEqual(before, self.tree())

    def test_page_json_and_exists(self):
        r = self.g("create", "page:cart", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        self.assertTrue(d["ok"])
        self.assertIn("lib/app/modules/cart/controllers/cart_controller.dart", d["created"])
        self.assertIn("lib/app/routes/app_routes.dart", d["modified"])
        self.assertEqual(d["route"], "Routes.CART")
        self.assertEqual(r.stdout.count("\n{"), 0, "stdout must be one JSON object")

        r = self.g("create", "page:cart", "--json")
        self.assertEqual(r.returncode, 1)
        d = json.loads(r.stdout)
        self.assertFalse(d["ok"])
        self.assertIn("already exists", d["error"])

    def test_free_text_becomes_note(self):
        r = self.g("create", "page:profile", "showing", "the", "user", "--json")
        self.assertEqual(json.loads(r.stdout)["note"], "showing the user")

    def test_model_inline_json_and_locales_fallback(self):
        r = self.g("generate", "model:Order", "with", '[{"id": 1, "lines": [{"sku": "a"}]}]', "--json")
        d = json.loads(r.stdout)
        self.assertTrue(d["ok"], d)
        self.assertEqual(d["classes"], ["Order", "Line"])
        self.assertTrue((self.p / "lib/app/data/models/order_model.dart").exists())
        r = self.g("create", "string:greeting", "Hello", "--ar", "مرحبا", "--json")
        self.assertTrue(json.loads(r.stdout)["ok"])
        r = self.g("generate", "locales", "--json")
        d = json.loads(r.stdout)
        self.assertEqual(d["generator"], "bundled")
        self.assertIn("static const greeting = 'greeting';",
                      (self.p / "lib/generated/locales.g.dart").read_text())

    def test_model_from_url_on_module(self):
        import http.server
        import threading

        body = json.dumps({"id": 7, "name": "Ada", "address": {"city": "London"}}).encode()

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/users/7"
            r = self.g("generate", "model:Customer", "with", url, "on", "home", "--json")
        finally:
            server.shutdown()
        d = json.loads(r.stdout)
        self.assertTrue(d["ok"], d)
        self.assertEqual(d["classes"], ["Customer", "Address"])
        self.assertEqual(d["model_file"], "lib/app/modules/home/data/models/customer_model.dart")
        self.assertTrue((self.p / "assets/models/customer.json").exists())
        r = self.g("generate", "model:Customer", "with", url, "on", "missing_module", "--json")
        self.assertEqual(r.returncode, 1)

    def test_install_cli_writes_launcher(self):
        bindir = Path(self.tmp.name) / "bin"
        r = getx_cli("install-cli", "--dir", str(bindir), "--json")
        d = json.loads(r.stdout)
        self.assertTrue(d["ok"])
        launcher = bindir / "getx"
        self.assertTrue(launcher.exists())
        v = subprocess.run([str(launcher), "version"], capture_output=True, text=True)
        self.assertIn(getx.VERSION, v.stdout)


class LocalesGeneratorTest(unittest.TestCase):
    def test_matches_get_cli_format(self):
        import locales
        code = locales.render({"en_US": {"a": "It's $5", "b_c": "x"}, "ar_AR": {"a": "ي"}})
        self.assertIn("    'en_US': Locales.en_US,", code)
        self.assertIn("  static const b_c = 'b_c';", code)
        self.assertIn("    'a': 'It\\'s \\$5',", code)
        self.assertTrue(code.startswith("// DO NOT EDIT. This is code generated via package:get_cli/get_cli.dart"))
        self.assertEqual(locales.flatten({"x": {"y": "1"}}), {"x_y": "1"})


if __name__ == "__main__":
    unittest.main()
