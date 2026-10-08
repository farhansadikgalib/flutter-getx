#!/usr/bin/env python3
"""Render the GetX folder pattern and basic elements into a Flutter project.

Usage:
    python scaffold.py <project_dir> [--app-title "My App"] [--design-size 375x812] [--dry-run]

What it does:
  * Copies every file under assets/templates/ into the project, substituting
    {{package_name}}, {{app_title}}, {{design_width}}, {{design_height}}.
  * Never overwrites a file that already exists, except the untouched starter
    files `flutter create` generates (lib/main.dart, test/widget_test.dart,
    analysis_options.yaml). Every skipped file is reported.
  * Adds the asset folders to pubspec.yaml's `flutter:` section.

It does not touch dependencies (run versions.py --write) and does not run
build_runner (the Hive adapter `*.g.dart` files are generated afterwards).
Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import reporter
from reporter import out

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_ROOT / "assets" / "templates"
TEMPLATE_SUFFIX = ".tmpl"

ASSET_DIRS = ["assets/images/", "assets/vectors/", "assets/lottie/", "assets/locales/"]

# Files `flutter create` writes that we may replace, with a marker proving the
# file is still the untouched starter. If the marker is missing the user has
# edited the file and it is skipped like any other existing file.
STARTER_MARKERS = {
    "lib/main.dart": "This is the theme of your application.",
    "test/widget_test.dart": "This is a basic Flutter widget test.",
    "analysis_options.yaml": "This file configures the analyzer",
}


def read_package_name(project: Path) -> str:
    pubspec = project / "pubspec.yaml"
    if not pubspec.exists():
        reporter.current().fail(f"{pubspec} not found; run `flutter create` first")
        sys.exit(f"error: {pubspec} not found; run `flutter create` first")
    m = re.search(r"^name:\s*([a-z0-9_]+)\s*$", pubspec.read_text(encoding="utf-8"), re.M)
    if not m:
        reporter.current().fail("could not read `name:` from pubspec.yaml")
        sys.exit("error: could not read `name:` from pubspec.yaml")
    return m.group(1)


def is_untouched_starter(path: Path, rel: str) -> bool:
    marker = STARTER_MARKERS.get(rel)
    if marker is None or not path.exists():
        return False
    return marker in path.read_text(encoding="utf-8", errors="ignore")


def render(text: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    leftover = re.findall(r"\{\{[a-z_]+\}\}", text)
    if leftover:
        raise ValueError(f"unknown placeholders: {sorted(set(leftover))}")
    return text


def add_assets_to_pubspec(project: Path, dry_run: bool) -> list[str]:
    pubspec = project / "pubspec.yaml"
    lines = pubspec.read_text(encoding="utf-8").splitlines()
    text = "\n".join(lines)
    missing = [d for d in ASSET_DIRS if f"- {d}" not in text]
    if not missing:
        return []

    # Locate the top-level `flutter:` section (not the `flutter:` sdk entry,
    # which is indented under dependencies).
    try:
        flutter_idx = next(i for i, l in enumerate(lines) if l.rstrip() == "flutter:")
    except StopIteration:
        lines += ["", "flutter:", "  uses-material-design: true"]
        flutter_idx = len(lines) - 2

    assets_idx = next(
        (i for i in range(flutter_idx + 1, len(lines))
         if lines[i].startswith("  assets:") and not lines[i].startswith("   ")),
        None,
    )
    if assets_idx is None:
        # Insert right after `uses-material-design` (or after `flutter:`).
        anchor = next(
            (i for i in range(flutter_idx + 1, len(lines)) if "uses-material-design" in lines[i]),
            flutter_idx,
        )
        new = ["", "  assets:"] + [f"    - {d}" for d in missing]
        lines[anchor + 1:anchor + 1] = new
    else:
        lines[assets_idx + 1:assets_idx + 1] = [f"    - {d}" for d in missing]

    if not dry_run:
        pubspec.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return [f"pubspec.yaml: added asset {d}" for d in missing]


def ensure_network_access(project: Path, dry_run: bool) -> list[str]:
    """Grant outbound network access on platforms that deny it by default.

    The API client and google_fonts both need it. `flutter create` only adds
    INTERNET to Android's debug manifest, and the macOS sandbox blocks
    outgoing connections without the network.client entitlement.
    """
    changes: list[str] = []

    manifest = project / "android/app/src/main/AndroidManifest.xml"
    if manifest.exists():
        text = manifest.read_text(encoding="utf-8")
        if "android.permission.INTERNET" not in text:
            text = re.sub(
                r"(<manifest[^>]*>)",
                r'\1\n    <uses-permission android:name="android.permission.INTERNET"/>',
                text,
                count=1,
            )
            if not dry_run:
                manifest.write_text(text, encoding="utf-8")
            changes.append("android main manifest: added INTERNET permission")

    for name in ("DebugProfile.entitlements", "Release.entitlements"):
        ent = project / "macos/Runner" / name
        if not ent.exists():
            continue
        text = ent.read_text(encoding="utf-8")
        if "com.apple.security.network.client" in text:
            continue
        text = text.replace(
            "</dict>",
            "\t<key>com.apple.security.network.client</key>\n\t<true/>\n</dict>",
            1,
        )
        if not dry_run:
            ent.write_text(text, encoding="utf-8")
        changes.append(f"macos {name}: added network.client entitlement")

    return changes


def scaffold(project: Path, values: dict[str, str], dry_run: bool) -> int:
    created, replaced, skipped = [], [], []

    for src in sorted(p for p in TEMPLATES.rglob("*") if p.is_file()):
        rel = src.relative_to(TEMPLATES).as_posix()
        if rel.endswith(TEMPLATE_SUFFIX):
            rel = rel[: -len(TEMPLATE_SUFFIX)]
        dest = project / rel

        if dest.exists():
            if is_untouched_starter(dest, rel):
                replaced.append(rel)
            else:
                skipped.append(rel)
                continue
        else:
            created.append(rel)

        if dry_run:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.name.endswith(TEMPLATE_SUFFIX):
            dest.write_text(render(src.read_text(encoding="utf-8"), values), encoding="utf-8")
        else:
            dest.write_bytes(src.read_bytes())

    pubspec_changes = add_assets_to_pubspec(project, dry_run)
    pubspec_changes += ensure_network_access(project, dry_run)

    result = reporter.current()
    prefix = "[dry-run] would " if dry_run else ""
    for rel in created:
        out(f"{prefix}create   {rel}")
        result.add_created(rel)
    for rel in replaced:
        out(f"{prefix}replace  {rel}  (untouched flutter create starter)")
        result.add_modified(rel)
    for rel in skipped:
        out(f"skip     {rel}  (already exists)")
        result.add_skipped(rel, "already exists")
    for change in pubspec_changes:
        out(f"{prefix}{change}")
        result.add_modified(_changed_file(change))
    out(
        f"\n{len(created)} created, {len(replaced)} replaced, {len(skipped)} skipped"
        + (" (dry run, nothing written)" if dry_run else "")
    )
    if dry_run:
        result.data["dry_run"] = True
    if created or replaced:
        out("next: dart run build_runner build --delete-conflicting-outputs")
        result.add_next("dart run build_runner build --delete-conflicting-outputs")
    return 0


def _changed_file(change: str) -> str:
    """Map a change-log line to the file it touched."""
    if change.startswith("pubspec.yaml"):
        return "pubspec.yaml"
    if change.startswith("android main manifest"):
        return "android/app/src/main/AndroidManifest.xml"
    m = re.match(r"macos (\S+):", change)
    return f"macos/Runner/{m.group(1)}" if m else change


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project_dir")
    parser.add_argument("--app-title", help="title shown by GetMaterialApp (default: from package name)")
    parser.add_argument("--design-size", default="375x812", help="Figma/XD artboard WxH (default 375x812)")
    parser.add_argument("--dry-run", action="store_true", help="list actions without writing")
    args = parser.parse_args(argv)

    project = Path(args.project_dir).resolve()
    package = read_package_name(project)

    m = re.fullmatch(r"(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)", args.design_size)
    if not m:
        parser.error("--design-size must look like 375x812")

    title = args.app_title or " ".join(w.capitalize() for w in package.split("_"))
    values = {
        "package_name": package,
        "app_title": title.replace("'", "\\'"),
        "design_width": m.group(1),
        "design_height": m.group(2),
    }
    return scaffold(project, values, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
