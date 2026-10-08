"""Multi-step operations behind `getx`: feature, install, install fcm, init, upgrade.

Each function records what it did on `reporter.current()` and returns an exit
code (0 ok, 1 failed). Single-step operations live in the original scripts
(new_module.py, json_to_model.py, add_string.py, scaffold.py, versions.py,
doctor.py); this module composes them.

Only the Python standard library is used.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import reporter
from reporter import out

SCRIPTS = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPTS.parent
FEATURE_TEMPLATES = SKILL_ROOT / "assets" / "feature_templates"
FIREBASE_ADDON = SKILL_ROOT / "assets" / "addons" / "firebase" / "lib"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def snake(text: str) -> str:
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", text.strip())
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return re.sub(r"_+", "_", text)


def pascal(name: str) -> str:
    return "".join(p[:1].upper() + p[1:] for p in snake(name).split("_") if p)


def camel(name: str) -> str:
    p = pascal(name)
    return p[:1].lower() + p[1:]


def singular(name: str) -> str:
    if name.endswith("ies"):
        return name[:-3] + "y"
    if name.endswith("ses") or name.endswith("xes"):
        return name[:-2]
    if name.endswith("s") and not name.endswith("ss"):
        return name[:-1]
    return name


def run(cmd: list[str], cwd: Path, label: str | None = None, timeout: int = 1800) -> tuple[int, str]:
    """Run a command, streaming a one-line label through out(); return (code, output)."""
    if label:
        out(f"==> {label}")
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    return p.returncode, p.stdout + p.stderr


def call_script(module: Any, argv: list[str]) -> int:
    """Run another script's main() in-process, collecting into the current result."""
    result = reporter.current()
    try:
        code = module.main(argv)
    except SystemExit as exc:  # scripts use sys.exit("error: ...") / argparse
        if isinstance(exc.code, str):
            msg = exc.code[7:] if exc.code.startswith("error: ") else exc.code
            result.fail(msg)
            out(exc.code, file=sys.stderr)
            result.error_printed = True
            return 1
        code = exc.code or 0
        if code == 2 and result.ok:
            result.fail("invalid arguments (see usage above)")
    if not result.ok:
        result.error_printed = True  # the script printed its own error
    return int(code or 0)


def rel(path: Path, project: Path) -> str:
    try:
        return path.resolve().relative_to(project.resolve()).as_posix()
    except ValueError:
        return str(path)


def fetch_json(source: str, project: Path) -> Any:
    """Load JSON from a URL, a file path, or a literal JSON string."""
    s = source.strip()
    if s.startswith("http://") or s.startswith("https://"):
        req = urllib.request.Request(s, headers={"Accept": "application/json", "User-Agent": "flutter-getx"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.load(resp)
    if s[:1] in "[{":
        return json.loads(s)
    path = Path(s)
    if not path.is_absolute():
        path = (project / s) if (project / s).exists() else Path.cwd() / s
    return json.loads(path.read_text(encoding="utf-8"))


def find_list(data: Any) -> tuple[list | None, str | None]:
    """Return (items, key) for a JSON list response or an object wrapping one."""
    if isinstance(data, list):
        return data, None
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return value, key
    return None, None


def flutter_pub_get(project: Path) -> bool:
    code, output = run(["flutter", "pub", "get"], project, "flutter pub get")
    if code != 0:
        reporter.current().fail("flutter pub get failed: " + output.strip().splitlines()[-1][:300]
                                if output.strip() else "flutter pub get failed")
        return False
    reporter.current().add_modified("pubspec.lock")
    return True


def needs_build_runner(project: Path) -> bool:
    for f in (project / "lib").rglob("*.dart"):
        text = f.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"^part '.+\.g\.dart';", text, re.M):
            return True
    return False


def build_runner(project: Path) -> bool:
    code, output = run(["dart", "run", "build_runner", "build", "--delete-conflicting-outputs"],
                       project, "dart run build_runner build")
    if code != 0:
        reporter.current().fail("build_runner failed: " + output.strip()[-400:])
        return False
    return True


def analyze_issues(project: Path) -> tuple[int, int, list[str]]:
    """Return (errors, total issues, first issue lines) from flutter analyze."""
    code, output = run(["flutter", "analyze", "--no-fatal-infos", "--no-fatal-warnings"], project)
    lines = [l.strip() for l in output.splitlines() if " • " in l]
    errors = sum(1 for l in lines if l.startswith("error"))
    order = {"error": 0, "warning": 1, "info": 2}
    lines.sort(key=lambda l: order.get(l.split(" ", 1)[0], 3))
    return errors, len(lines), lines[:15]


# --------------------------------------------------------------------------- #
# install <package>
# --------------------------------------------------------------------------- #

def install_package(project: Path, package: str, dev: bool, dry_run: bool, offline: bool) -> int:
    import versions

    result = reporter.current()
    pubspec = project / "pubspec.yaml"
    if not pubspec.exists():
        result.fail("no pubspec.yaml here; run inside a Flutter project or pass --project")
        return 1
    if not re.fullmatch(r"[a-z][a-z0-9_]*", package):
        result.fail(f"'{package}' is not a valid pub package name")
        return 2
    if offline:
        version = versions.load_snapshot().get(package)
        if version is None:
            result.fail(f"offline and '{package}' is not in the snapshot; run online")
            return 1
    else:
        try:
            version = versions.fetch_latest(package)
        except urllib.error.HTTPError as exc:
            result.fail(f"'{package}' was not found on pub.dev" if exc.code == 404 else f"pub.dev error: {exc}")
            return 1
        except (urllib.error.URLError, KeyError, ValueError, OSError) as exc:
            result.fail(f"could not reach pub.dev: {exc}")
            return 1

    section = "dev_dependencies" if dev else "dependencies"
    other = "dependencies" if dev else "dev_dependencies"
    lines = pubspec.read_text(encoding="utf-8").splitlines()
    entries = versions._entries(lines, section)
    if package in versions._entries(lines, other):
        result.fail(f"{package} is already in {other}; remove it there first or use the other section")
        return 1
    new_line = f"  {package}: ^{version}"
    if package in entries:
        idx = entries[package]
        if lines[idx].rstrip().endswith(":"):
            result.add_skipped("pubspec.yaml", f"{package} uses a path/git/sdk source; left unchanged")
            out(f"{package} uses a path/git/sdk source; left unchanged")
            return 0
        action = "unchanged" if lines[idx] == new_line else "updated"
        lines[idx] = new_line
    else:
        bounds = versions._section_bounds(lines, section)
        if bounds is None:
            lines += ["", f"{section}:"]
            bounds = (len(lines) - 1, len(lines))
        lines.insert(bounds[1], new_line)
        action = "added"

    out(f"{'[dry-run] would set' if dry_run else action} {section}.{package}: ^{version}")
    result.data.update({"package": package, "version": version, "section": section})
    if dry_run:
        result.data["dry_run"] = True
        result.add_modified("pubspec.yaml")
        return 0
    if action != "unchanged":
        pubspec.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result.add_modified("pubspec.yaml")
    return 0 if flutter_pub_get(project) else 1


# --------------------------------------------------------------------------- #
# install fcm
# --------------------------------------------------------------------------- #

MAIN_ANCHOR = "await MySharedPref.init();"
FCM_WIRING = """

  // Push notifications (flutter-getx fcm add-on). Local notifications first so
  // FCM can display through them. Without Firebase configured, FcmHelper logs
  // and the app keeps running.
  await AwesomeNotificationsHelper.init();
  await FcmHelper.initFcm();"""
PODFILE_HOOK = """  awesome_pod_file = File.expand_path(File.join('plugins', 'awesome_notifications', 'ios', 'Scripts', 'AwesomePodFile'), '.symlinks')
  require awesome_pod_file
  update_awesome_pod_build_settings(installer)
"""
PODFILE_TAIL = """
# awesome_notifications 0.10+ (added by flutter-getx fcm add-on)
awesome_pod_file = File.expand_path(File.join('plugins', 'awesome_notifications', 'ios', 'Scripts', 'AwesomePodFile'), '.symlinks')
require awesome_pod_file
update_awesome_main_target_settings('Runner', File.dirname(File.realpath(__FILE__)), flutter_root)
"""


def install_fcm(project: Path, dry_run: bool, offline: bool) -> int:
    import versions

    result = reporter.current()
    if not (project / "pubspec.yaml").exists():
        result.fail("no pubspec.yaml here; run inside a Flutter project or pass --project")
        return 1
    if not (project / "lib/app/data/local/my_shared_pref.dart").exists():
        result.fail("the fcm add-on needs the GetX pattern; run `getx init` first")
        return 1

    # 1. packages
    if dry_run:
        out("[dry-run] would add firebase_core, firebase_messaging, awesome_notifications")
        result.add_modified("pubspec.yaml")
    else:
        if call_script(versions, ["--write", str(project / "pubspec.yaml"), "--firebase"]
                       + (["--offline"] if offline else [])) != 0:
            return 1

    # 2. helper files and placeholder options (never overwrite)
    copies = [(FIREBASE_ADDON / "utils" / n, project / "lib/utils" / n)
              for n in ("awesome_notifications_helper.dart", "fcm_helper.dart")]
    copies.append((FIREBASE_ADDON / "firebase_options.dart", project / "lib/firebase_options.dart"))
    for src, dest in copies:
        r = rel(dest, project)
        if dest.exists():
            reason = ("kept your existing Firebase config" if dest.name == "firebase_options.dart"
                      else "already exists")
            result.add_skipped(r, reason)
            out(f"skip     {r}  ({reason})")
            continue
        out(f"{'[dry-run] would create' if dry_run else 'create  '} {r}")
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
        result.add_created(r)
    if not (project / "lib/firebase_options.dart").exists() or \
            "Placeholder written by the flutter-getx skill" in (project / "lib/firebase_options.dart").read_text():
        result.add_next("flutterfire configure   # connects your Firebase project and replaces the placeholder")

    # 3. main.dart wiring
    main = project / "lib/main.dart"
    text = main.read_text(encoding="utf-8") if main.exists() else ""
    if "FcmHelper.initFcm" in text:
        result.add_skipped("lib/main.dart", "already calls FcmHelper.initFcm()")
    elif MAIN_ANCHOR not in text:
        result.add_skipped("lib/main.dart", f"anchor `{MAIN_ANCHOR}` not found; add AwesomeNotificationsHelper.init() "
                                            "and FcmHelper.initFcm() to main() by hand")
        out("skip     lib/main.dart  (anchor not found; wire FcmHelper by hand)")
    else:
        imports = ("import 'utils/awesome_notifications_helper.dart';\n"
                   "import 'utils/fcm_helper.dart';\n")
        last_import = list(re.finditer(r"^import .*;\n", text, re.M))[-1]
        text = text[:last_import.end()] + imports + text[last_import.end():]
        text = text.replace(MAIN_ANCHOR, MAIN_ANCHOR + FCM_WIRING, 1)
        out(f"{'[dry-run] would modify' if dry_run else 'modify  '} lib/main.dart")
        if not dry_run:
            main.write_text(text, encoding="utf-8")
        result.add_modified("lib/main.dart")

    # 4. iOS Podfile
    podfile = project / "ios/Podfile"
    if podfile.exists():
        pod = podfile.read_text(encoding="utf-8")
        changed = False
        new_pod, n = re.subn(r"^#?\s*platform :ios, '[\d.]+'", "platform :ios, '15.0'", pod, count=1, flags=re.M)
        if n and new_pod != pod:
            pod, changed = new_pod, True
        if "update_awesome_pod_build_settings" not in pod:
            m = re.search(r"^post_install do \|installer\|\n(.*?)^end\n", pod, re.M | re.S)
            if m:
                insert_at = m.end() - len("end\n")
                pod = pod[:insert_at] + PODFILE_HOOK + pod[insert_at:] + PODFILE_TAIL
                changed = True
            else:
                result.add_skipped("ios/Podfile", "no post_install block; add the awesome_notifications hooks "
                                                  "from references/firebase-fcm.md")
        if changed:
            out(f"{'[dry-run] would modify' if dry_run else 'modify  '} ios/Podfile")
            if not dry_run:
                podfile.write_text(pod, encoding="utf-8")
            result.add_modified("ios/Podfile")
    result.add_next("Xcode: enable Push Notifications and Background Modes > Remote notifications; "
                    "upload an APNs key in Firebase")

    if dry_run:
        result.data["dry_run"] = True
        return 0
    return 0 if flutter_pub_get(project) else 1


# --------------------------------------------------------------------------- #
# create feature
# --------------------------------------------------------------------------- #

TITLE_KEYS = ("title", "name", "label", "username", "headline", "email")
SUBTITLE_KEYS = ("price", "subtitle", "description", "body", "email", "category", "status", "id")


def _pick_fields(fields: list) -> tuple[Any, Any]:
    by_key = {f.key: f for f in fields}
    strings = [f for f in fields if f.type == "String"]
    title = next((by_key[k] for k in TITLE_KEYS if k in by_key and by_key[k].type == "String"), None) \
        or (strings[0] if strings else None) or (fields[0] if fields else None)
    rest = [f for f in fields if f is not title and f.kind in ("prim", "int", "double")]
    subtitle = next((by_key[k] for k in SUBTITLE_KEYS if k in by_key and by_key[k] is not title
                     and by_key[k].kind in ("prim", "int", "double")), None) or (rest[0] if rest else None)
    return title, subtitle


def _text_expr(field: Any) -> str:
    if field is None:
        return "''"
    if field.type == "String":
        return f"item.{field.name}{' ?? ' + repr('') if field.nullable else ''}"
    return "'${item." + field.name + "}'"


def create_feature(project: Path, name: str, source: str, dry_run: bool, no_get_cli: bool) -> int:
    import json_to_model
    import new_module
    import add_string

    result = reporter.current()
    if not (project / "lib/app/routes/app_pages.dart").exists():
        result.fail("not a scaffolded GetX project; run `getx init` first")
        return 1
    name = snake(name)
    item = singular(name)
    model_class = pascal(item) + "Model"
    module_dir = project / "lib/app/modules" / name
    if module_dir.exists():
        result.fail(f"module '{name}' already exists; nothing changed")
        return 1

    # 1. sample
    try:
        data = fetch_json(source, project)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        result.fail(f"could not load sample from {source}: {exc}")
        return 1
    items, list_key = find_list(data)
    sample = items[0] if items else data
    if not isinstance(sample, dict):
        result.fail("the response is not a JSON object or a list of objects")
        return 1
    is_url = source.startswith("http://") or source.startswith("https://")
    endpoint = source if is_url else f"/{name}"
    list_access = ("response.data as List<dynamic>" if items is not None and list_key is None
                   else f"(response.data as Map<String, dynamic>)['{list_key}'] as List<dynamic>"
                   if list_key else "<dynamic>[response.data]")
    mock_body = json.dumps([sample] if list_key is None else {list_key: [sample]}, ensure_ascii=False)
    empty_body = "[]" if list_key is None else json.dumps({list_key: []})

    gen = json_to_model.Generator(set())
    gen.visit(model_class, sample)
    title, subtitle = _pick_fields(gen.classes[model_class])
    values = {
        "package_name": new_module.package_name(project),
        "snake_name": name, "class_name": pascal(name), "camel_name": camel(name),
        "item_snake": item, "model_class": model_class,
        "endpoint": endpoint.replace("\\", "\\\\").replace("'", "\\'").replace("$", "\\$"),
        "list_access": list_access,
        "title_expr": _text_expr(title), "subtitle_expr": _text_expr(subtitle),
        "item_class": pascal(item),
        "mock_body": mock_body,
        "empty_body": empty_body,
        "title_value": str(sample.get(title.key, "")) if title else "",
    }
    planned = [
        f"assets/models/{item}.json",
        f"lib/app/data/models/{item}_model.dart",
        f"lib/app/data/remote/{item}_remote_source.dart",
        f"lib/app/modules/{name}/bindings/{name}_binding.dart",
        f"lib/app/modules/{name}/controllers/{name}_controller.dart",
        f"lib/app/modules/{name}/views/{name}_view.dart",
        f"test/{name}_controller_test.dart",
    ]
    for p in planned:
        if (project / p).exists() and not p.startswith("lib/app/modules"):
            result.fail(f"{p} already exists; nothing changed")
            return 1
    if dry_run:
        for p in planned:
            out(f"[dry-run] would create   {p}")
            result.add_created(p)
        for p in ("lib/app/routes/app_routes.dart", "lib/app/routes/app_pages.dart",
                  "assets/locales/en_US.json", "assets/locales/ar_AR.json"):
            out(f"[dry-run] would modify   {p}")
            result.add_modified(p)
        result.data.update({"dry_run": True, "model": model_class, "endpoint": endpoint})
        return 0

    # 2. model
    sample_path = project / "assets/models" / f"{item}.json"
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    sample_path.write_text(json.dumps(sample, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result.add_created(rel(sample_path, project))
    if call_script(json_to_model, [str(sample_path), model_class, "--project", str(project)]) != 0:
        return 1

    # 3. page (route, binding) then feature controller/view on top
    page_args = [name, "--project", str(project)] + (["--no-get-cli"] if no_get_cli else [])
    if call_script(new_module, page_args) != 0:
        return 1
    files = {
        "remote_source.dart.tmpl": project / "lib/app/data/remote" / f"{item}_remote_source.dart",
        "controller.dart.tmpl": module_dir / "controllers" / f"{name}_controller.dart",
        "view.dart.tmpl": module_dir / "views" / f"{name}_view.dart",
        "controller_test.dart.tmpl": project / "test" / f"{name}_controller_test.dart",
    }
    for tmpl, dest in files.items():
        text = (FEATURE_TEMPLATES / tmpl).read_text(encoding="utf-8")
        for k, v in values.items():
            text = text.replace("{{" + k + "}}", v)
        leftover = re.findall(r"\{\{[a-z_]+\}\}", text)
        if leftover:
            result.fail(f"internal template error in {tmpl}: {leftover}")
            return 1
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        result.add_created(rel(dest, project))
        out(f"wrote    {rel(dest, project)}")

    # 4. strings (English everywhere; the slash command or a human translates)
    label = name.replace("_", " ")
    call_script(add_string, [f"{name}_title", label[:1].upper() + label[1:],
                             "--project", str(project), "--no-generate"])
    call_script(add_string, [f"no_{name}_yet", f"No {label} yet", "--project", str(project)])

    if shutil.which("dart"):
        subprocess.run(["dart", "format", "lib", "test"], cwd=project, capture_output=True)
    out(f"\nfeature '{name}' ready: Routes.{name.upper()} loads {endpoint}")
    result.data.update({"route": f"Routes.{name.upper()}", "model": model_class, "endpoint": endpoint,
                        "title_field": title.key if title else None,
                        "subtitle_field": subtitle.key if subtitle else None})
    if result.data.get("untranslated"):
        result.add_next("translate the new keys in " + ", ".join(result.data["untranslated"]))
    result.add_next("flutter analyze")
    result.add_next("flutter test")
    return 0


# --------------------------------------------------------------------------- #
# init and upgrade
# --------------------------------------------------------------------------- #

def init_project(project: Path, title: str | None, design_size: str | None, dry_run: bool, offline: bool) -> int:
    import scaffold
    import versions

    result = reporter.current()
    if not (project / "pubspec.yaml").exists():
        result.fail(f"no pubspec.yaml in {project}; run `getx create project:<name>` for a new app")
        return 1
    args = [str(project)] + (["--app-title", title] if title else []) + \
        (["--design-size", design_size] if design_size else [])
    if dry_run:
        return call_script(scaffold, args + ["--dry-run"])
    if call_script(versions, ["--write", str(project / "pubspec.yaml")] + (["--offline"] if offline else [])):
        return 1
    if call_script(scaffold, args):
        return 1
    if not flutter_pub_get(project):
        return 1
    if needs_build_runner(project) and not build_runner(project):
        return 1
    result.add_next("flutter analyze")
    result.add_next("flutter test")
    return 0


HIVE_IMPORTS = {
    "package:hive/hive.dart": "package:hive_ce/hive.dart",
    "package:hive_flutter/hive_flutter.dart": "package:hive_ce_flutter/hive_flutter.dart",
    "package:hive_flutter/adapters.dart": "package:hive_ce_flutter/adapters.dart",
}
MECHANICAL_FIXES = [
    (re.compile(r"\bMaterialStateProperty\b"), "WidgetStateProperty"),
    (re.compile(r"\bMaterialState\b"), "WidgetState"),
    (re.compile(r"\.withOpacity\(([^()]*)\)"), r".withValues(alpha: \1)"),
]


def upgrade_project(project: Path, firebase: bool | None, dry_run: bool, offline: bool) -> int:
    import versions

    result = reporter.current()
    pubspec = project / "pubspec.yaml"
    if not pubspec.exists():
        result.fail(f"no pubspec.yaml in {project}")
        return 1
    if firebase is None:
        firebase = bool(re.search(r"^  firebase_(core|messaging):", pubspec.read_text(), re.M))

    before_errors = before_total = None
    if not dry_run and shutil.which("flutter"):
        run(["flutter", "pub", "get"], project, "baseline: flutter pub get")
        before_errors, before_total, _ = analyze_issues(project)
        out(f"baseline: {before_total} analyzer issues ({before_errors} errors)")

    args = ["--write", str(pubspec)] + (["--firebase"] if firebase else []) + (["--offline"] if offline else [])
    if dry_run:
        out("[dry-run] would update pubspec.yaml to the latest versions (versions.py --write)")
        result.add_modified("pubspec.yaml")
    elif call_script(versions, args):
        return 1

    rewrites = 0
    for f in sorted((project / "lib").rglob("*.dart")) + sorted((project / "test").rglob("*.dart")):
        if f.name.endswith(".g.dart"):
            continue
        text = f.read_text(encoding="utf-8")
        new = text
        for old, rep in HIVE_IMPORTS.items():
            new = new.replace(old, rep)
        for pattern, rep in MECHANICAL_FIXES:
            new = pattern.sub(rep, new)
        if new != text:
            rewrites += 1
            out(f"{'[dry-run] would modify' if dry_run else 'modify  '} {rel(f, project)}")
            if not dry_run:
                f.write_text(new, encoding="utf-8")
            result.add_modified(rel(f, project))
    if dry_run:
        result.data["dry_run"] = True
        return 0

    if not flutter_pub_get(project):
        return 1
    if needs_build_runner(project):
        build_runner(project)
    after_errors, after_total, first = analyze_issues(project)
    out(f"after: {after_total} analyzer issues ({after_errors} errors)")
    result.data["analyzer"] = {"before": {"issues": before_total, "errors": before_errors},
                               "after": {"issues": after_total, "errors": after_errors},
                               "remaining": first}
    if after_total:
        result.add_next("fix the remaining analyzer issues using references/packages.md (migration table)")
    result.add_next("apply the platform steps in references/packages.md (Upgrading an old project)")
    result.add_next("flutter test")
    return 0
