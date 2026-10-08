#!/usr/bin/env python3
"""Add a feature module (binding, controller, view, route) to a GetX project.

Usage:
    python new_module.py <name> [--on <parent_module>] [--project <dir>] [--no-get-cli] [--dry-run]
    python new_module.py <name> --kind controller --on <module>   # controller, registered in the binding
    python new_module.py <name> --kind view --on <module>         # view (not routed), like get_cli

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

import reporter
from reporter import out

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
        reporter.current().fail("could not read `name:` from pubspec.yaml")
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
    out("get_cli missing or stale; running `dart pub global activate get_cli`")
    subprocess.run(["dart", "pub", "global", "activate", "get_cli"], check=False)
    return get_cli_works()


def run_get_cli(project: Path, name: str, parent: str | None) -> bool:
    cmd = [get_executable() or "get", "create", f"page:{name}"]
    if parent:
        cmd += ["on", parent]
    out("$ " + " ".join(cmd))
    result = subprocess.run(cmd, cwd=project, capture_output=True, text=True)
    out(result.stdout, end="")
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

def write_templates(module_dir: Path, values: dict[str, str], which: list[str],
                    project: Path | None = None) -> None:
    targets = {
        "controller": module_dir / "controllers" / f"{values['snake_name']}_controller.dart",
        "view": module_dir / "views" / f"{values['snake_name']}_view.dart",
        "binding": module_dir / "bindings" / f"{values['snake_name']}_binding.dart",
    }
    for kind in which:
        template = "view_only" if kind == "view" and values.get("controller_class") else kind
        src = MODULE_TEMPLATES / f"{template}.dart.tmpl"
        dest = targets[kind]
        dest.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text()
        if kind == "view" and values.get("controller_class"):
            text = text.replace("{{class_name}}Controller", values["controller_class"])
            text = text.replace("{{snake_name}}_controller.dart", values["controller_file"])
        dest.write_text(render(text, values))
        out(f"wrote    {dest}")
        reporter.current().add_created(_rel(dest, project))


def _rel(path: Path, project: Path | None) -> str:
    try:
        return path.resolve().relative_to(project.resolve()).as_posix() if project else str(path)
    except ValueError:
        return str(path)


def _fail(message: str, code: int = 1) -> int:
    """Record an error, print it like the script always has, and return the exit code."""
    reporter.current().fail(message)
    out(message if code == 1 else f"error: {message}")
    return code


def register_controller(binding: Path, name: str) -> None:
    """Import the controller and add a Get.lazyPut to the binding's dependencies()."""
    cls = pascal(name)
    text = binding.read_text()
    imp = f"import '../controllers/{name}_controller.dart';"
    if imp not in text:
        imports = [m.end() for m in re.finditer(r"^import .*;$", text, re.M)]
        at = imports[-1] if imports else 0
        text = text[:at] + ("\n" if at else "") + imp + ("" if at else "\n") + text[at:]
    anchor = text.find("void dependencies()")
    if anchor == -1:
        raise ValueError(f"no dependencies() method in {binding.name}")
    body_open = text.index("{", anchor)
    body_close = _matching_bracket(text, body_open)
    entry = f"    Get.lazyPut<{cls}Controller>(\n      () => {cls}Controller(),\n    );\n  "
    head = text[:body_close].rstrip() + "\n"
    text = head + entry + text[body_close:]
    binding.write_text(text)


def create_part(args, name: str, project: Path, modules_root: Path) -> int:
    """`--kind controller|view`: add one file to an existing module."""
    result = reporter.current()
    if not args.parent:
        return _fail(f"{args.kind} needs a module: add --on <module> (e.g. {args.kind}:{name} on home)", 2)
    module_dir = find_module_dir(modules_root, args.parent)
    if module_dir is None:
        return _fail(f"module '{args.parent}' not found", 2)
    folder = "controllers" if args.kind == "controller" else "views"
    dest = module_dir / folder / f"{name}_{args.kind}.dart"
    if dest.exists():
        return _fail(f"{args.kind} '{name}' already exists at {_rel(dest, project)}; nothing changed")

    values = {"package_name": package_name(project), "snake_name": name, "class_name": pascal(name)}
    binding = module_dir / "bindings" / f"{module_dir.name}_binding.dart"
    if args.kind == "view":
        own = module_dir / "controllers" / f"{name}_controller.dart"
        ctrl_snake = name if own.exists() else module_dir.name
        values["controller_class"] = f"{pascal(ctrl_snake)}Controller"
        values["controller_file"] = f"{ctrl_snake}_controller.dart"

    if args.dry_run:
        out(f"[dry-run] would create   {_rel(dest, project)}")
        result.add_created(_rel(dest, project))
        if args.kind == "controller":
            out(f"[dry-run] would modify   {_rel(binding, project)}")
            result.add_modified(_rel(binding, project))
        result.data["dry_run"] = True
        return 0

    write_templates(module_dir, values, [args.kind], project)
    if args.kind == "controller":
        if binding.exists():
            register_controller(binding, name)
            out(f"updated  {binding}")
            result.add_modified(_rel(binding, project))
        else:
            result.add_skipped(_rel(binding, project), "binding not found; register the controller by hand")
    if shutil.which("dart"):
        subprocess.run(["dart", "format", str(module_dir)], cwd=project, capture_output=True)
    if args.kind == "controller":
        out(f"\ncontroller '{pascal(name)}Controller' ready in {_rel(module_dir, project)}")
        out(f"use:    Get.find<{pascal(name)}Controller>()")
    else:
        out(f"\nview '{pascal(name)}View' ready in {_rel(module_dir, project)} "
            f"(uses {values['controller_class']}; not routed)")
    out("next:   flutter analyze")
    result.add_next("flutter analyze")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", help="module name in snake_case, e.g. product_detail")
    parser.add_argument("--on", dest="parent", help="create inside this existing module")
    parser.add_argument("--kind", choices=["page", "controller", "view"], default="page",
                        help="page (default): full module and route; controller/view: one file in --on module")
    parser.add_argument("--project", default=".", help="Flutter project root (default: cwd)")
    parser.add_argument("--no-get-cli", action="store_true", help="skip get_cli and use bundled templates")
    parser.add_argument("--dry-run", action="store_true", help="list planned changes without writing")
    args = parser.parse_args(argv)
    result = reporter.current()

    name = args.name.strip().lower().replace("-", "_").replace(" ", "_")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        parser.error("name must be snake_case letters, digits and underscores")

    project = Path(args.project).resolve()
    modules_root = project / "lib/app/modules"
    if not (project / "pubspec.yaml").exists() or not (project / "lib/app/routes/app_pages.dart").exists():
        result.fail("not a scaffolded GetX project (missing pubspec.yaml or lib/app/routes/app_pages.dart)")
        sys.exit("error: not a scaffolded GetX project (missing pubspec.yaml or lib/app/routes/app_pages.dart)")

    if args.kind != "page":
        return create_part(args, name, project, modules_root)

    existing = find_module_dir(modules_root, name)
    if existing:
        return _fail(f"module '{name}' already exists at {existing.relative_to(project)}; nothing changed")

    parent_dir: Path | None = None
    if args.parent:
        parent_dir = find_module_dir(modules_root, args.parent)
        if parent_dir is None:
            result.fail(f"parent module '{args.parent}' not found")
            sys.exit(f"error: parent module '{args.parent}' not found")

    module_dir = (parent_dir or modules_root) / name
    module_rel = module_dir.relative_to(modules_root).as_posix()
    values = {
        "package_name": package_name(project),
        "snake_name": name,
        "class_name": pascal(name),
    }

    if args.dry_run:
        for kind, folder in (("controller", "controllers"), ("view", "views"), ("binding", "bindings")):
            rel = f"lib/app/modules/{module_rel}/{folder}/{name}_{kind}.dart"
            out(f"[dry-run] would create   {rel}")
            result.add_created(rel)
        for rel in ("lib/app/routes/app_routes.dart", "lib/app/routes/app_pages.dart"):
            out(f"[dry-run] would modify   {rel}")
            result.add_modified(rel)
        out(f"route:  Routes.{screaming(name)}")
        result.data.update({"dry_run": True, "route": f"Routes.{screaming(name)}"})
        return 0

    used_get_cli = False
    if not args.no_get_cli and ensure_get_cli():
        used_get_cli = run_get_cli(project, name, args.parent)
        if not used_get_cli:
            out("warning: get_cli failed; falling back to bundled templates")
            result.warn("get_cli failed; used bundled templates")

    if used_get_cli:
        # get_cli wrote binding/controller/view and the route; conform the
        # controller and view to the project's base classes.
        write_templates(module_dir, values, ["controller", "view"], project)
        result.add_created(_rel(module_dir / "bindings" / f"{name}_binding.dart", project))
    else:
        if not args.no_get_cli:
            out("notice: get_cli unavailable; generated from bundled templates instead")
            result.warn("get_cli unavailable; used bundled templates")
        write_templates(module_dir, values, ["controller", "view", "binding"], project)
        register_route(project, name, args.parent, module_rel)
    result.add_modified("lib/app/routes/app_routes.dart")
    result.add_modified("lib/app/routes/app_pages.dart")

    pages = (project / "lib/app/routes/app_pages.dart").read_text()
    if f"_Paths.{screaming(name)}" not in pages:
        result.fail("route was not registered in app_pages.dart")
        sys.exit("error: route was not registered in app_pages.dart")

    if shutil.which("dart"):
        subprocess.run(
            ["dart", "format", "lib/app/routes", f"lib/app/modules/{module_rel}"],
            cwd=project, capture_output=True,
        )

    out(f"\nmodule '{name}' ready: lib/app/modules/{module_rel}")
    out(f"route:  Routes.{screaming(name)}   navigate with Get.toNamed(Routes.{screaming(name)})")
    out(f"source: {'get_cli' if used_get_cli else 'bundled templates'}")
    out("next:   flutter analyze")
    result.data.update({"route": f"Routes.{screaming(name)}", "source": "get_cli" if used_get_cli else "templates"})
    result.add_next("flutter analyze")
    return 0


if __name__ == "__main__":
    sys.exit(main())
