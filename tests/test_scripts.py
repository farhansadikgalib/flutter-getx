"""Unit tests for the flutter-getx helper scripts.

Run from the repository root:

    python3 -m unittest discover -s tests -v

They need only Python 3.9+. Nothing here calls Flutter, get_cli or the network.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "flutter-getx" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import json_to_model  # noqa: E402
import versions  # noqa: E402


def run(script: str, *args: str, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        cwd=cwd, capture_output=True, text=True, env={**os.environ, **(env or {})},
    )


STARTER_PUBSPEC = textwrap.dedent("""\
    name: demo_app
    description: test
    environment:
      sdk: ^3.13.0

    dependencies:
      flutter:
        sdk: flutter
      cupertino_icons: ^1.0.8

    dev_dependencies:
      flutter_test:
        sdk: flutter
      flutter_lints: ^5.0.0

    flutter:
      uses-material-design: true
    """)


def make_project(tmp: Path) -> Path:
    p = tmp / "demo_app"
    (p / "lib").mkdir(parents=True)
    (p / "test").mkdir()
    (p / "pubspec.yaml").write_text(STARTER_PUBSPEC)
    (p / "lib/main.dart").write_text("// This is the theme of your application.\nvoid main() {}\n")
    (p / "test/widget_test.dart").write_text("// This is a basic Flutter widget test.\n")
    (p / "analysis_options.yaml").write_text("# This file configures the analyzer\n")
    manifest = p / "android/app/src/main/AndroidManifest.xml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n    <application/>\n</manifest>\n')
    return p


# --------------------------------------------------------------------------- #

class JsonToModelTest(unittest.TestCase):
    def gen(self, data, name="Thing", nullable=()):
        g = json_to_model.Generator(set(nullable))
        g.visit(name, data)
        return g, g.render()

    def test_types_and_nesting(self):
        g, code = self.gen({"id": 1, "price": 9.5, "ok": True, "name": "a",
                            "tags": ["x"], "rating": {"rate": 4.5}, "items": [{"sku": "1"}]})
        self.assertEqual(list(g.classes), ["Thing", "Rating", "Item"])
        self.assertIn("final int id;", code)
        self.assertIn("(json['price'] as num).toDouble()", code)
        self.assertIn("final List<String> tags;", code)
        self.assertIn("final List<Item> items;", code)
        self.assertIn("rating.toJson()", code)

    def test_null_and_forced_nullable(self):
        _, code = self.gen({"a": None, "b": "x"}, nullable={"b"})
        self.assertIn("final dynamic a;", code)
        self.assertNotIn("dynamic?", code)
        self.assertIn("final String? b;", code)
        self.assertIn("this.b,", code)
        self.assertNotIn("required this.b", code)

    def test_key_conversion_and_reserved_words(self):
        _, code = self.gen({"in_stock": True, "class": "x", "first-name": "y", "2fa": False})
        self.assertIn("final bool inStock;", code)
        self.assertIn("'in_stock': inStock", code)
        self.assertIn("classValue", code)
        self.assertIn("firstName", code)
        self.assertIn("f2fa", code)

    def test_mixed_number_list_is_double(self):
        _, code = self.gen({"vals": [1, 2.5]})
        self.assertIn("List<double> vals", code)

    def test_empty_object_and_empty_list(self):
        g, code = self.gen({"meta": {}, "list": []})
        self.assertIn("const Meta();", code)
        self.assertIn("List<dynamic> list", code)

    def test_cli_list_sample_and_file_naming(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            (t / "s.json").write_text(json.dumps([{"id": 1}, {"id": 2, "extra": "x"}]))
            r = run("json_to_model.py", "s.json", "ProductModel", "--project", ".", "--out", "m", cwd=t)
            self.assertEqual(r.returncode, 0, r.stderr)
            out = (t / "m/product_model.dart").read_text()
            self.assertIn("class ProductModel", out)
            self.assertIn("extra", out)  # merged from the second item
            r2 = run("json_to_model.py", "s.json", "ProductModel", "--out", "m", cwd=t)
            self.assertEqual(r2.returncode, 1, "must refuse to overwrite without --force")

    def test_cli_rejects_scalar_sample(self):
        with tempfile.TemporaryDirectory() as t:
            Path(t, "s.json").write_text("42")
            r = run("json_to_model.py", "s.json", "X", "--stdout", cwd=Path(t))
            self.assertNotEqual(r.returncode, 0)


class VersionsTest(unittest.TestCase):
    def test_snapshot_covers_every_managed_package(self):
        snap = versions.load_snapshot()
        missing = [n for n in versions.all_managed(include_firebase=True) if n not in snap]
        self.assertEqual(missing, [])

    def test_write_adds_moves_removes_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t, "pubspec.yaml")
            p.write_text(STARTER_PUBSPEC.replace(
                "  cupertino_icons: ^1.0.8\n",
                "  cupertino_icons: ^1.0.8\n  hive: ^2.2.3\n  rename_app: ^1.0.0\n  my_own_pkg: ^1.0.0\n"))
            r = run("versions.py", "--write", str(p), "--offline")
            self.assertEqual(r.returncode, 0, r.stderr)
            text = p.read_text()
            self.assertNotRegex(text, r"(?m)^  hive:")
            self.assertRegex(text, r"(?m)^  hive_ce: \^")
            self.assertRegex(text, r"(?m)^  my_own_pkg: \^1\.0\.0$")  # untouched
            self.assertRegex(text, r"(?ms)^  flutter:\n    sdk: flutter")  # sdk entry preserved
            deps, dev = text.split("dev_dependencies:")
            self.assertNotIn("rename_app", deps)
            self.assertIn("rename_app", dev)
            r2 = run("versions.py", "--write", str(p), "--offline")
            self.assertEqual(r2.stdout.strip(), "", "second run must change nothing")

    def test_conditional_pin_follows_build_runner(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t, "pubspec.yaml")
            p.write_text(STARTER_PUBSPEC)
            v, _ = versions.resolve(versions.all_managed(False), offline=True)
            v["build_runner"] = "2.16.1"
            versions.write_pubspec(p, v, False)
            self.assertIn('analyzer: ">=14.0.0 <14.5.0"', p.read_text())
            v["build_runner"] = "2.16.2"
            changes = versions.write_pubspec(p, v, False)
            self.assertNotIn("analyzer:", p.read_text())
            self.assertTrue(any("unpinned" in c for c in changes))

    def test_missing_pubspec_fails_cleanly(self):
        r = run("versions.py", "--write", "/nonexistent/pubspec.yaml", "--offline")
        self.assertEqual(r.returncode, 1)
        self.assertIn("not found", r.stderr)


class ScaffoldTest(unittest.TestCase):
    def test_fresh_render_then_idempotent(self):
        with tempfile.TemporaryDirectory() as t:
            p = make_project(Path(t))
            r = run("scaffold.py", str(p), "--app-title", "Demo's App", "--design-size", "390x844")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("3 replaced, 0 skipped", r.stdout)
            main = (p / "lib/main.dart").read_text()
            self.assertIn("Demo\\'s App", main)
            self.assertIn("Size(390, 844)", main)
            self.assertIn("package:demo_app/", (p / "test/widget_test.dart").read_text())
            leftovers = [f for f in p.rglob("*") if f.is_file() and "{{" in f.read_text(errors="ignore")]
            self.assertEqual(leftovers, [])
            self.assertIn("INTERNET", (p / "android/app/src/main/AndroidManifest.xml").read_text())
            self.assertIn("- assets/locales/", (p / "pubspec.yaml").read_text())
            r2 = run("scaffold.py", str(p))
            self.assertIn("0 created, 0 replaced", r2.stdout)

    def test_edited_starter_is_kept(self):
        with tempfile.TemporaryDirectory() as t:
            p = make_project(Path(t))
            (p / "lib/main.dart").write_text("// my app\nvoid main() {}\n")
            r = run("scaffold.py", str(p))
            self.assertIn("skip     lib/main.dart", r.stdout)
            self.assertEqual((p / "lib/main.dart").read_text(), "// my app\nvoid main() {}\n")

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            p = make_project(Path(t))
            before = sorted(str(f) for f in p.rglob("*"))
            r = run("scaffold.py", str(p), "--dry-run")
            self.assertIn("dry run, nothing written", r.stdout)
            self.assertEqual(before, sorted(str(f) for f in p.rglob("*")))

    def test_rejects_bad_design_size_and_missing_pubspec(self):
        with tempfile.TemporaryDirectory() as t:
            p = make_project(Path(t))
            self.assertNotEqual(run("scaffold.py", str(p), "--design-size", "big").returncode, 0)
            self.assertNotEqual(run("scaffold.py", str(Path(t) / "nope")).returncode, 0)


class NewModuleFallbackTest(unittest.TestCase):
    """Exercises the bundled-template path (no get_cli)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = make_project(Path(self.tmp.name))
        run("scaffold.py", str(self.p))

    def tearDown(self):
        self.tmp.cleanup()

    def module(self, *args):
        return run("new_module.py", *args, "--project", str(self.p), "--no-get-cli")

    def test_page_nested_and_duplicate(self):
        r = self.module("product_detail")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        routes = (self.p / "lib/app/routes/app_routes.dart").read_text()
        self.assertIn("PRODUCT_DETAIL = '/product-detail'", routes)
        ctrl = (self.p / "lib/app/modules/product_detail/controllers/product_detail_controller.dart").read_text()
        self.assertIn("extends BaseController", ctrl)
        self.assertIn("package:demo_app/", ctrl)

        r = self.module("reviews", "--on", "product_detail")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        routes = (self.p / "lib/app/routes/app_routes.dart").read_text()
        self.assertIn("REVIEWS = _Paths.PRODUCT_DETAIL + _Paths.REVIEWS", routes)
        pages = (self.p / "lib/app/routes/app_pages.dart").read_text()
        self.assertIn("children:", pages)
        imports = [l for l in pages.splitlines() if l.startswith("import '../")]
        self.assertEqual(imports, sorted(imports))

        r = self.module("home")
        self.assertEqual(r.returncode, 1)
        self.assertIn("already exists", r.stdout)

    def test_controller_and_view_targets(self):
        r = self.module("edit", "--kind", "controller", "--on", "home")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        ctrl = (self.p / "lib/app/modules/home/controllers/edit_controller.dart").read_text()
        self.assertIn("class EditController extends BaseController", ctrl)
        binding = (self.p / "lib/app/modules/home/bindings/home_binding.dart").read_text()
        self.assertIn("import '../controllers/edit_controller.dart';", binding)
        self.assertIn("Get.lazyPut<EditController>(", binding)
        self.assertIn("Get.lazyPut<HomeController>(", binding)  # existing registration kept

        # view with a same-named controller binds to it
        r = self.module("edit", "--kind", "view", "--on", "home")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        view = (self.p / "lib/app/modules/home/views/edit_view.dart").read_text()
        self.assertIn("class EditView extends BaseView<EditController>", view)
        # view without one binds to the module's controller
        self.module("details", "--kind", "view", "--on", "home")
        view = (self.p / "lib/app/modules/home/views/details_view.dart").read_text()
        self.assertIn("extends BaseView<HomeController>", view)
        self.assertIn("import '../controllers/home_controller.dart';", view)
        # views are not routed
        self.assertNotIn("DETAILS", (self.p / "lib/app/routes/app_routes.dart").read_text())

        again = self.module("edit", "--kind", "controller", "--on", "home")
        self.assertEqual(again.returncode, 1)
        self.assertIn("already exists", again.stdout)
        missing_on = self.module("x", "--kind", "controller")
        self.assertEqual(missing_on.returncode, 2)

    def test_dry_run_changes_nothing(self):
        before = sorted((str(f), f.stat().st_size) for f in self.p.rglob("*") if f.is_file())
        r = self.module("cart", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertIn("[dry-run] would create", r.stdout)
        r = self.module("edit", "--kind", "controller", "--on", "home", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        after = sorted((str(f), f.stat().st_size) for f in self.p.rglob("*") if f.is_file())
        self.assertEqual(before, after)

    def test_name_normalization_and_validation(self):
        r = self.module("Order-History")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertTrue((self.p / "lib/app/modules/order_history").is_dir())
        self.assertNotEqual(self.module("9lives").returncode, 0)
        self.assertNotEqual(self.module("x", "--on", "missing_parent").returncode, 0)


class AddStringTest(unittest.TestCase):
    def test_add_update_and_fallback(self):
        with tempfile.TemporaryDirectory() as t:
            p = make_project(Path(t))
            run("scaffold.py", str(p))
            r = run("add_string.py", "greeting", "Hi @name", "--ar", "مرحبا @name", "--project", str(p), "--no-generate")
            self.assertEqual(r.returncode, 0, r.stderr)
            ar = json.loads((p / "assets/locales/ar_AR.json").read_text())
            self.assertEqual(ar["greeting"], "مرحبا @name")
            (p / "assets/locales/fr_FR.json").write_text("{}")
            r = run("add_string.py", "greeting", "Hello @name", "--project", str(p), "--no-generate")
            self.assertIn("updated", r.stdout)
            self.assertIn("needs translation", r.stdout)
            self.assertIn("fr_FR.json", r.stdout)
            self.assertEqual(json.loads((p / "assets/locales/ar_AR.json").read_text())["greeting"], "Hello @name")

    def test_rejects_bad_key_and_missing_locales(self):
        with tempfile.TemporaryDirectory() as t:
            p = make_project(Path(t))
            self.assertNotEqual(run("add_string.py", "Bad-Key", "x", "--project", str(p), "--no-generate").returncode, 0)
            r = run("add_string.py", "ok_key", "x", "--project", str(p), "--no-generate")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("no locale files", r.stdout + r.stderr)


class DoctorTest(unittest.TestCase):
    def test_flags_legacy_problems(self):
        with tempfile.TemporaryDirectory() as t:
            p = make_project(Path(t))
            pub = p / "pubspec.yaml"
            pub.write_text(pub.read_text().replace("  cupertino_icons: ^1.0.8\n", "  cupertino_icons: ^1.0.8\n  hive: ^2.2.3\n"))
            r = run("doctor.py", "--project", str(p), "--offline")
            self.assertEqual(r.returncode, 1)
            self.assertIn("replaced packages", r.stdout)
            self.assertIn("android INTERNET permission", r.stdout)

    def test_outside_a_project(self):
        with tempfile.TemporaryDirectory() as t:
            r = run("doctor.py", "--project", t, "--offline")
            self.assertIn("project checks skipped", r.stdout)


class PackagingTest(unittest.TestCase):
    def test_commands_reference_existing_scripts(self):
        import re
        for cmd in (ROOT / "commands").glob("*.md"):
            text = cmd.read_text()
            self.assertRegex(text, r"(?m)^description: ", cmd.name)
            self.assertRegex(text, r"(?m)^argument-hint: '", f"{cmd.name}: quote argument-hint")
            for rel in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+)", text):
                rel = rel.rstrip(".`")
                if "*" in rel:
                    continue
                self.assertTrue((ROOT / rel).exists(), f"{cmd.name} references missing {rel}")

    def test_manifests_agree_on_version(self):
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
        market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
        skill = (ROOT / "skills/flutter-getx/SKILL.md").read_text()
        self.assertEqual(plugin["version"], market["plugins"][0]["version"])
        self.assertEqual(plugin["version"], market["metadata"]["version"])
        self.assertIn(f'version: "{plugin["version"]}"', skill)


if __name__ == "__main__":
    unittest.main()
