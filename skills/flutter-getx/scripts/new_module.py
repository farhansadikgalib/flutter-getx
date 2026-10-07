#!/usr/bin/env python3
"""Add a feature module (binding, controller, view, route) to a GetX project.

Usage:
    python new_module.py <name> [--on <parent_module>] [--project <dir>] [--no-get-cli]

Steps:
  1. Refuse if the module already exists (nothing is changed).
  2. Make sure get_cli works; re-activate it once if the binary is stale.
  3. Run `get create page:<name> [on <parent>]` so get_cli writes the files
     and registers the route. Without get_cli, write the same files from
     assets/module_templates/ and register the route here.
  4. Replace the generated controller and view with versions that extend the
     project's BaseController / BaseView.
  5. Verify the route is registered in app_pages.dart.

<name> is snake_case (e.g. product_detail). Only the Python standard library
is used.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
MODULE_TEMPLATES = SKILL_ROOT / "assets" / "module_templates"


# --------------------------------------------------------------------------- #
# naming
# --------------------------------------------------------------------------- #

def pascal(snake: str) -> str:
    return "".join(part.capitalize() for part in snake.split("_"))


def screaming(snake: str) -> str:
    return snake.upper()


def kebab(snake: str) -> str:
    return snake.replace("_", "-")


# --------------------------------------------------------------------------- #
# project helpers
# --------------------------------------------------------------------------- #

def package_name(project: Path) -> str:
    m = re.search(r"^name:\s*([a-z0-9_]+)\s*$", (project / "pubspec.yaml").read_text(), re.M)
    if not m:
        sys.exit("error: could not read `name:` from pubspec.yaml")
    return m.group(1)


def find_module_dir(modules_root: Path, name: str) -> Path | None:
    """A module is any directory named <name> that has a controllers/ child."""
    for path in modules_root.rglob(name):
        if path.is_dir() and (path / "controllers").is_dir():
            return path
    return None


def render(template: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


# --------------------------------------------------------------------------- #
# get_cli
# --------------------------------------------------------------------------- #

def get_executable() -> str | None:
    """`get` on PATH, else the pub-cache bin (activation does not edit PATH)."""
    found = shutil.which("get")
    if found:
        return found
    pub_cache = Path(os.environ.get("PUB_CACHE", Path.home() / ".pub-cache"))
    candidate = pub_cache / "bin" / ("get.bat" if os.name == "nt" else "get")
    return str(candidate) if candidate.exists() else None


def get_cli_works() -> bool:
    exe = get_executable()
    if exe is None:
        return False
    try:
        result = subprocess.run([exe, "-v"], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return False
    output = result.stdout + result.stderr
    return result.returncode == 0 and "Invalid kernel binary" not in output and "Error" not in output


def ensure_get_cli() -> bool:
    if get_cli_works():
        return True
    if shutil.which("dart") is None:
        return False
    print("get_cli missing or stale; running `dart pub global activate get_cli`")
    subprocess.run(["dart", "pub", "global", "activate", "get_cli"], check=False)
    return get_cli_works()


def run_get_cli(project: Path, name: str, parent: str | None) -> bool:
    cmd = [get_executable() or "get", "create", f"page:{name}"]
    if parent:
        cmd += ["on", parent]
    print("$ " + " ".join(cmd))
    result = subprocess.run(cmd, cwd=project, capture_output=True, text=True)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode == 0


# --------------------------------------------------------------------------- #
# fallback route registration (mirrors get_cli's output shape)
# --------------------------------------------------------------------------- #

def _matching_bracket(text: str, open_idx: int) -> int:
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] in "([{":
            depth += 1
        elif text[i] in ")]}":
            depth -= 1
            if depth == 0:
                return i
    raise ValueError("unbalanced brackets in app_pages.dart")


def register_route(project: Path, name: str, parent: str | None, module_rel: str) -> None:
    routes_dir = project / "lib/app/routes"
    pages_file = routes_dir / "app_pages.dart"
    routes_file = routes_dir / "app_routes.dart"
    const = screaming(name)
    cls = pascal(name)

    # app_routes.dart: Routes + _Paths constants
    routes = routes_file.read_text()
    route_value = f"_Paths.{screaming(parent)} + _Paths.{const}" if parent else f"_Paths.{const}"
    routes = re.sub(
        r"(abstract class Routes \{.*?)(\n\})",
        lambda m: m.group(1) + f"\n  static const {const} = {route_value};" + m.group(2),
        routes, count=1, flags=re.S,
    )
    routes = re.sub(
        r"(abstract class _Paths \{.*?)(\n\})",
        lambda m: m.group(1) + f"\n  static const {const} = '/{kebab(name)}';" + m.group(2),
        routes, count=1, flags=re.S,
    )
    routes_file.write_text(routes)

    # app_pages.dart: imports + GetPage
    pages = pages_file.read_text()
    imports = (
        f"import '../modules/{module_rel}/bindings/{name}_binding.dart';\n"
        f"import '../modules/{module_rel}/views/{name}_view.dart';\n"
    )
    pages = pages.replace("\npart 'app_routes.dart';", imports + "\npart 'app_routes.dart';", 1)
    # Keep relative imports sorted, as get_cli does.
    lines = pages.split("\n")
    rel = [i for i, l in enumerate(lines) if l.startswith("import '../")]
    if rel:
        block = sorted(lines[rel[0]:rel[-1] + 1])
        lines[rel[0]:rel[-1] + 1] = block
        pages = "\n".join(lines)

    entry = (
        f"GetPage(\n"
        f"      name: _Paths.{const},\n"
        f"      page: () => const {cls}View(),\n"
        f"      binding: {cls}Binding(),\n"
        f"    ),"
    )

    if parent:
        anchor = pages.find(f"name: _Paths.{screaming(parent)},")
        if anchor == -1:
            sys.exit(f"error: parent route _Paths.{screaming(parent)} not found in app_pages.dart")
        page_open = pages.rfind("GetPage(", 0, anchor) + len("GetPage")
        page_close = _matching_bracket(pages, page_open)
        block = pages[page_open:page_close]
        children = block.find("children: [")
        if children == -1:
            insert_at = page_close
            snippet = f"  children: [\n        {entry}\n      ],\n    "
        else:
            list_open = page_open + children + len("children: ")
            insert_at = _matching_bracket(pages, list_open)
            snippet = f"  {entry}\n      "
        pages = pages[:insert_at] + snippet + pages[insert_at:]
    else:
        list_open = pages.find("routes = [") + len("routes = ")
        list_close = _matching_bracket(pages, list_open)
        pages = pages[:list_close] + f"  {entry}\n  " + pages[list_close:]

    pages_file.write_text(pages)


# --------------------------------------------------------------------------- #
# main flow
# --------------------------------------------------------------------------- #

def write_templates(module_dir: Path, values: dict[str, str], which: list[str]) -> None:
    targets = {
        "controller": module_dir / "controllers" / f"{values['snake_name']}_controller.dart",
        "view": module_dir / "views" / f"{values['snake_name']}_view.dart",
        "binding": module_dir / "bindings" / f"{values['snake_name']}_binding.dart",
    }
    for kind in which:
        src = MODULE_TEMPLATES / f"{kind}.dart.tmpl"
        dest = targets[kind]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(render(src.read_text(), values))
        print(f"wrote    {dest}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", help="module name in snake_case, e.g. product_detail")
    parser.add_argument("--on", dest="parent", help="create inside this existing module")
    parser.add_argument("--project", default=".", help="Flutter project root (default: cwd)")
    parser.add_argument("--no-get-cli", action="store_true", help="skip get_cli and use bundled templates")
    args = parser.parse_args(argv)

    name = args.name.strip().lower().replace("-", "_")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        parser.error("name must be snake_case letters, digits and underscores")

    project = Path(args.project).resolve()
    modules_root = project / "lib/app/modules"
    if not (project / "pubspec.yaml").exists() or not (project / "lib/app/routes/app_pages.dart").exists():
        sys.exit("error: not a scaffolded GetX project (missing pubspec.yaml or lib/app/routes/app_pages.dart)")

    existing = find_module_dir(modules_root, name)
    if existing:
        print(f"module '{name}' already exists at {existing.relative_to(project)}; nothing changed")
        return 1

    parent_dir: Path | None = None
    if args.parent:
        parent_dir = find_module_dir(modules_root, args.parent)
        if parent_dir is None:
            sys.exit(f"error: parent module '{args.parent}' not found")

    module_dir = (parent_dir or modules_root) / name
    module_rel = module_dir.relative_to(modules_root).as_posix()
    values = {
        "package_name": package_name(project),
        "snake_name": name,
        "class_name": pascal(name),
    }

    used_get_cli = False
    if not args.no_get_cli and ensure_get_cli():
        used_get_cli = run_get_cli(project, name, args.parent)
        if not used_get_cli:
            print("warning: get_cli failed; falling back to bundled templates")

    if used_get_cli:
        # get_cli wrote binding/controller/view and the route; conform the
        # controller and view to the project's base classes.
        write_templates(module_dir, values, ["controller", "view"])
    else:
        if not args.no_get_cli:
            print("notice: get_cli unavailable; generated from bundled templates instead")
        write_templates(module_dir, values, ["controller", "view", "binding"])
        register_route(project, name, args.parent, module_rel)

    pages = (project / "lib/app/routes/app_pages.dart").read_text()
    if f"_Paths.{screaming(name)}" not in pages:
        sys.exit("error: route was not registered in app_pages.dart")

    if shutil.which("dart"):
        subprocess.run(
            ["dart", "format", "lib/app/routes", f"lib/app/modules/{module_rel}"],
            cwd=project, capture_output=True,
        )

    print(f"\nmodule '{name}' ready: lib/app/modules/{module_rel}")
    print(f"route:  Routes.{screaming(name)}   navigate with Get.toNamed(Routes.{screaming(name)})")
    print(f"source: {'get_cli' if used_get_cli else 'bundled templates'}")
    print("next:   flutter analyze")
    return 0


if __name__ == "__main__":
    sys.exit(main())
