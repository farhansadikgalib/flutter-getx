#!/usr/bin/env python3
"""Check the toolchain and, inside a Flutter project, how it matches the GetX pattern.

Usage:
    python doctor.py [--project <dir>] [--offline]

Toolchain checks: flutter, dart, python, get_cli (and whether its snapshot is
stale), and reachability of pub.dev.

Project checks (when --project, or the current directory, holds a pubspec.yaml):
folder pattern present, managed packages behind pub.dev, replaced hive
packages still declared, missing Android/macOS network permissions,
analysis_options setup, and whether generated files exist.

Exit code is 0 when nothing is marked FAIL. Only the Python standard library
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

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import versions  # noqa: E402  (sibling script)

OK, WARN, FAIL = "ok", "warn", "FAIL"
results: list[tuple[str, str, str]] = []


def report(status: str, check: str, detail: str = "") -> None:
    results.append((status, check, detail))


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 120) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


# --------------------------------------------------------------------------- #
# toolchain
# --------------------------------------------------------------------------- #

def check_toolchain(offline: bool) -> None:
    if shutil.which("flutter"):
        code, out = run(["flutter", "--version"])
        line = out.splitlines()[0] if out else ""
        report(OK if code == 0 else FAIL, "flutter", line or out[:120])
    else:
        report(FAIL, "flutter", "not on PATH; install Flutter stable")

    if shutil.which("dart"):
        code, out = run(["dart", "--version"])
        report(OK if code == 0 else FAIL, "dart", out.splitlines()[-1] if out else "")
    else:
        report(FAIL, "dart", "not on PATH")

    py = sys.version_info
    report(OK if py >= (3, 9) else FAIL, "python", f"{py.major}.{py.minor}.{py.micro} (needs 3.9+)")

    exe = shutil.which("get")
    if exe is None:
        cand = Path(os.environ.get("PUB_CACHE", Path.home() / ".pub-cache")) / "bin" / "get"
        exe = str(cand) if cand.exists() else None
    if exe is None:
        report(WARN, "get_cli", "not installed; run: dart pub global activate get_cli "
                                "(new_module.py falls back to templates without it)")
    else:
        code, out = run([exe, "-v"])
        if "Invalid kernel binary" in out:
            report(WARN, "get_cli", "stale snapshot; run: dart pub global activate get_cli")
        elif code == 0:
            m = re.search(r"Version:\s*([0-9.]+)", out)
            report(OK, "get_cli", f"{m.group(1) if m else 'installed'} at {exe}")
        else:
            report(WARN, "get_cli", out[:160])

    if offline:
        report(WARN, "pub.dev", "skipped (--offline)")
    else:
        try:
            v = versions.fetch_latest("get")
            report(OK, "pub.dev", f"reachable (get {v})")
        except Exception as exc:  # noqa: BLE001
            report(WARN, "pub.dev", f"unreachable ({exc}); versions.py will use the snapshot")


# --------------------------------------------------------------------------- #
# project
# --------------------------------------------------------------------------- #

PATTERN_DIRS = [
    "lib/app/core/base",
    "lib/app/core/binding",
    "lib/app/data/local",
    "lib/app/data/models",
    "lib/app/modules",
    "lib/app/routes",
    "lib/app/services",
    "lib/config/theme",
    "lib/config/translations",
    "assets/locales",
]


def declared(pubspec_text: str) -> dict[str, str]:
    return dict(re.findall(r"^  ([a-z0-9_]+):\s*[\"']?([^\s\"'#]*)", pubspec_text, re.M))


def check_project(project: Path, offline: bool) -> None:
    pubspec = project / "pubspec.yaml"
    text = pubspec.read_text(encoding="utf-8")
    deps = declared(text)

    missing = [d for d in PATTERN_DIRS if not (project / d).is_dir()]
    if not missing:
        report(OK, "folder pattern", "all core directories present")
    elif len(missing) == len(PATTERN_DIRS):
        report(WARN, "folder pattern", "not scaffolded; run /flutter-getx:init or scaffold.py")
    else:
        report(WARN, "folder pattern", "missing: " + ", ".join(missing))

    if "get" not in deps:
        report(WARN, "get dependency", "GetX is not in pubspec.yaml")

    old = [n for n in versions.REPLACED if n in deps]
    if old:
        report(FAIL, "replaced packages", f"{', '.join(old)} still declared; run /flutter-getx:upgrade")

    managed = [n for n in versions.all_managed(include_firebase=True) if n in deps]
    if managed and not offline:
        try:
            latest, _ = versions.resolve(managed, offline=False)
            stale = []
            for n in managed:
                cur = deps[n].lstrip("^")
                if cur and cur[0].isdigit() and cur != latest[n]:
                    stale.append(f"{n} {cur} -> {latest[n]}")
            if stale:
                report(WARN, "package versions", f"{len(stale)} behind: " + "; ".join(stale[:6])
                       + (" ..." if len(stale) > 6 else ""))
            else:
                report(OK, "package versions", f"{len(managed)} managed packages at latest")
        except SystemExit:
            report(WARN, "package versions", "could not resolve latest versions")

    manifest = project / "android/app/src/main/AndroidManifest.xml"
    if manifest.exists():
        has = "android.permission.INTERNET" in manifest.read_text(encoding="utf-8")
        report(OK if has else FAIL, "android INTERNET permission",
               "present" if has else "missing in main manifest: release builds cannot reach the network")

    for name in ("DebugProfile.entitlements", "Release.entitlements"):
        ent = project / "macos/Runner" / name
        if ent.exists():
            has = "com.apple.security.network.client" in ent.read_text(encoding="utf-8")
            report(OK if has else FAIL, f"macOS {name}",
                   "network.client present" if has else "network.client missing: all requests fail")

    analysis = project / "analysis_options.yaml"
    if analysis.exists():
        a = analysis.read_text(encoding="utf-8")
        if "constant_identifier_names" not in a and (project / "lib/app/routes/app_routes.dart").exists():
            report(WARN, "analysis_options", "get_cli route constants will trip constant_identifier_names")

    models = list((project / "lib").rglob("*.dart")) if (project / "lib").exists() else []
    needs_gen = [p for p in models if "part '" in p.read_text(encoding="utf-8", errors="ignore")
                 and ".g.dart'" in p.read_text(encoding="utf-8", errors="ignore")]
    missing_gen = [p for p in needs_gen if not p.with_name(p.stem + ".g.dart").exists()]
    if missing_gen:
        report(FAIL, "generated code", f"{len(missing_gen)} file(s) need build_runner: "
               "dart run build_runner build --delete-conflicting-outputs")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", default=".", help="Flutter project root (default: cwd)")
    parser.add_argument("--offline", action="store_true", help="skip pub.dev lookups")
    args = parser.parse_args(argv)

    print("Toolchain")
    check_toolchain(args.offline)
    project = Path(args.project).resolve()
    in_project = (project / "pubspec.yaml").exists()
    if in_project:
        check_project(project, args.offline)

    width = max(len(c) for _, c, _ in results)
    printed_project_header = False
    for i, (status, check, detail) in enumerate(results):
        if in_project and not printed_project_header and check == "folder pattern":
            print(f"\nProject: {project}")
            printed_project_header = True
        mark = {"ok": "  ok  ", "warn": " warn ", "FAIL": " FAIL "}[status]
        print(f"[{mark}] {check.ljust(width)}  {detail}")
    if not in_project:
        print(f"\n(no pubspec.yaml in {project}; project checks skipped)")

    fails = sum(1 for s, _, _ in results if s == FAIL)
    warns = sum(1 for s, _, _ in results if s == WARN)
    print(f"\n{fails} failing, {warns} warnings")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
