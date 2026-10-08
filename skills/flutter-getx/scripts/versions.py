#!/usr/bin/env python3
"""Look up the latest stable pub.dev version of the packages this skill manages,
and optionally pin them into a pubspec.yaml.

Usage:
    python versions.py                      # print every managed package
    python versions.py get dio              # print only these packages
    python versions.py --json               # machine-readable output
    python versions.py --write pubspec.yaml # add/update managed deps in a pubspec
    python versions.py --write pubspec.yaml --firebase   # also add the FCM add-on
    python versions.py --offline            # skip pub.dev, use the snapshot table

Only the Python standard library is used. When pub.dev is unreachable the
script falls back to the dated snapshot in references/packages.md and prints a
warning, so scaffolding still works offline.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import reporter
from reporter import out
from typing import Callable

SKILL_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_FILE = SKILL_ROOT / "references" / "packages.md"
PUB_API = "https://pub.dev/api/packages/{name}"
TIMEOUT_SECONDS = 15

# The packages the scaffold relies on, grouped by the pubspec section they go in.
MANAGED: dict[str, list[str]] = {
    "dependencies": [
        "get",
        "logger",
        "flutter_screenutil",
        "dio",
        "pretty_dio_logger",
        "hive_ce",
        "hive_ce_flutter",
        "shared_preferences",
        "connectivity_plus",
        "flutter_easyloading",
        "shimmer",
        "google_fonts",
        "flutter_svg",
        "image_picker",
        "url_launcher",
        "cupertino_icons",
    ],
    "dev_dependencies": [
        "flutter_lints",
        "build_runner",
        "hive_ce_generator",
        "http_mock_adapter",
        "flutter_launcher_icons",
        "change_app_package_name",
        "rename_app",
    ],
}

# Constraints written verbatim (not looked up) to work around upstream breakage.
# Each pin applies only while its condition holds for the resolved versions;
# once it stops holding, --write removes the pin again. Document each one in
# references/packages.md.
EXTRA_PINS: dict[str, dict[str, tuple[str, "Callable[[dict[str, str]], bool]"]]] = {
    "dev_dependencies": {
        # analyzer 14.5.0 removed a setter build_runner 2.16.1 calls; fixed in 2.16.2.
        "analyzer": (">=14.0.0 <14.5.0", lambda v: v.get("build_runner") == "2.16.1"),
    },
}

# Packages the scaffold replaces. --write removes them from every section.
REPLACED: dict[str, str] = {
    "hive": "hive_ce",
    "hive_flutter": "hive_ce_flutter",
    "hive_generator": "hive_ce_generator",
}

# Opt-in add-on (see references/firebase-fcm.md). Only written with --firebase.
FIREBASE_ADDON: list[str] = [
    "firebase_core",
    "firebase_messaging",
    "awesome_notifications",
]


def all_managed(include_firebase: bool) -> list[str]:
    names = MANAGED["dependencies"] + MANAGED["dev_dependencies"]
    if include_firebase:
        names += FIREBASE_ADDON
    return names


# --------------------------------------------------------------------------- #
# Lookup
# --------------------------------------------------------------------------- #

def fetch_latest(name: str) -> str:
    """Return the latest stable version string from pub.dev.

    pub.dev's `latest` field already excludes prereleases whenever a stable
    release exists, so no extra filtering is needed.
    """
    req = urllib.request.Request(
        PUB_API.format(name=name),
        headers={"Accept": "application/vnd.pub.v2+json", "User-Agent": "flutter-getx-skill"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        data = json.load(resp)
    if data.get("isDiscontinued"):
        replacement = data.get("replacedBy")
        hint = f" (replaced by {replacement})" if replacement else ""
        out(f"warning: {name} is discontinued on pub.dev{hint}", file=sys.stderr)
    return data["latest"]["version"]


def load_snapshot() -> dict[str, str]:
    """Parse `| package | version |` rows from references/packages.md."""
    versions: dict[str, str] = {}
    if not SNAPSHOT_FILE.exists():
        return versions
    row = re.compile(r"^\|\s*`?([a-z0-9_]+)`?\s*\|\s*([0-9][^|\s]*)\s*\|")
    for line in SNAPSHOT_FILE.read_text(encoding="utf-8").splitlines():
        m = row.match(line)
        if m:
            versions[m.group(1)] = m.group(2)
    return versions


def resolve(names: list[str], offline: bool) -> tuple[dict[str, str], bool]:
    """Return {name: version} and whether the snapshot was used for any entry."""
    snapshot = load_snapshot()
    result: dict[str, str] = {}
    used_snapshot = False
    for name in names:
        version: str | None = None
        if not offline:
            try:
                version = fetch_latest(name)
            except (urllib.error.URLError, TimeoutError, KeyError, ValueError, OSError) as exc:
                out(f"warning: pub.dev lookup failed for {name}: {exc}", file=sys.stderr)
        if version is None:
            version = snapshot.get(name)
            if version is None:
                out(f"error: no snapshot version for {name}; cannot continue offline", file=sys.stderr)
                sys.exit(2)
            used_snapshot = True
        result[name] = version
    if used_snapshot:
        out(
            f"warning: used snapshot versions from {SNAPSHOT_FILE.name}; "
            "run again online or `flutter pub upgrade` later",
            file=sys.stderr,
        )
    return result, used_snapshot


# --------------------------------------------------------------------------- #
# pubspec editing (text based, preserves everything we do not manage)
# --------------------------------------------------------------------------- #

def _section_bounds(lines: list[str], header: str) -> tuple[int, int] | None:
    """Return (start, end) line indexes of a top-level mapping section.

    `start` is the header line; `end` is the index of the first line after the
    section's indented body (exclusive).
    """
    for i, line in enumerate(lines):
        if line.rstrip() == f"{header}:":
            j = i + 1
            while j < len(lines) and (lines[j].startswith(" ") or lines[j].strip() == "" or lines[j].lstrip().startswith("#")):
                j += 1
            # Trim trailing blank/comment lines back into the gap after the section.
            while j > i + 1 and lines[j - 1].strip() == "":
                j -= 1
            return i, j
    return None


def _remove_entry(lines: list[str], idx: int) -> None:
    """Delete a two-space-indented key and any deeper-indented lines under it."""
    end = idx + 1
    while end < len(lines) and lines[end].startswith("    "):
        end += 1
    del lines[idx:end]


def _entries(lines: list[str], header: str) -> dict[str, int]:
    bounds = _section_bounds(lines, header)
    if bounds is None:
        return {}
    start, end = bounds
    key_re = re.compile(r"^  ([a-z0-9_]+):")
    return {m.group(1): i for i in range(start + 1, end) if (m := key_re.match(lines[i]))}


def write_pubspec(path: Path, versions: dict[str, str], include_firebase: bool) -> list[str]:
    """Add or update managed dependencies. Returns a change log.

    Also removes packages listed in REPLACED, moves managed packages that sit in
    the wrong section, and adds or removes EXTRA_PINS by their condition.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    changes: list[str] = []

    sections = {
        "dependencies": list(MANAGED["dependencies"]) + (FIREBASE_ADDON if include_firebase else []),
        "dev_dependencies": list(MANAGED["dev_dependencies"]),
    }
    home = {name: header for header, names in sections.items() for name in names}

    # 1. Remove replaced packages and managed packages in the wrong section.
    for header in sections:
        while True:
            entries = _entries(lines, header)
            victim = next(
                (n for n in entries
                 if n in REPLACED or (n in home and home[n] != header)),
                None,
            )
            if victim is None:
                break
            _remove_entry(lines, entries[victim])
            if victim in REPLACED:
                changes.append(f"removed {header}.{victim} (replaced by {REPLACED[victim]})")
            else:
                changes.append(f"moved {victim}: {header} -> {home[victim]}")

    # 2. Add or update managed packages and conditional pins.
    for header, names in sections.items():
        if _section_bounds(lines, header) is None:
            if lines and lines[-1].strip():
                lines.append("")
            lines.append(f"{header}:")
        start, end = _section_bounds(lines, header) or (len(lines) - 1, len(lines))
        present = _entries(lines, header)
        insert_at = end

        for name, (constraint, applies) in EXTRA_PINS.get(header, {}).items():
            line = f'  {name}: "{constraint}"'
            if applies(versions):
                if name in present:
                    if lines[present[name]] != line:
                        lines[present[name]] = line
                        changes.append(f"pinned {header}.{name}: {constraint}")
                else:
                    lines.insert(insert_at, line)
                    insert_at += 1
                    changes.append(f"pinned {header}.{name}: {constraint}")
            elif name in present and lines[present[name]] == line:
                _remove_entry(lines, present[name])
                insert_at -= 1
                changes.append(f"unpinned {header}.{name} (no longer needed)")
            present = _entries(lines, header)

        for name in names:
            constraint = f"^{versions[name]}"
            if name in present:
                idx = present[name]
                old = lines[idx]
                # Leave sdk/path/git style multi-line entries untouched.
                if old.rstrip().endswith(":"):
                    continue
                new = f"  {name}: {constraint}"
                if old != new:
                    lines[idx] = new
                    changes.append(f"updated {header}.{name}: {old.strip()} -> {constraint}")
            else:
                lines.insert(insert_at, f"  {name}: {constraint}")
                insert_at += 1
                changes.append(f"added {header}.{name}: {constraint}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return changes


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("packages", nargs="*", help="package names (default: every managed package)")
    parser.add_argument("--json", action="store_true", help="print JSON instead of `name: version` lines")
    parser.add_argument("--write", metavar="PUBSPEC", help="add/update managed deps in this pubspec.yaml")
    parser.add_argument("--firebase", action="store_true", help="include the Firebase/FCM add-on packages")
    parser.add_argument("--offline", action="store_true", help="use the snapshot table only")
    args = parser.parse_args(argv)

    names = args.packages or all_managed(args.firebase)
    versions, _ = resolve(names, offline=args.offline)

    if args.write:
        pubspec = Path(args.write)
        if not pubspec.exists():
            reporter.current().fail(f"{pubspec} not found")
            out(f"error: {pubspec} not found", file=sys.stderr)
            return 1
        missing = [n for n in all_managed(args.firebase) if n not in versions]
        if missing:
            extra, _ = resolve(missing, offline=args.offline)
            versions.update(extra)
        changes = write_pubspec(pubspec, versions, args.firebase)
        for change in changes:
            out(change)
        result = reporter.current()
        if changes:
            result.add_modified(pubspec.name)
        result.data["pubspec_changes"] = changes
        return 0

    if args.json:
        out(json.dumps(versions, indent=2))
    else:
        for name, version in versions.items():
            out(f"{name}: {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
