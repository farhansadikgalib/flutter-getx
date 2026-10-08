#!/usr/bin/env python3
"""Generate lib/generated/locales.g.dart from assets/locales/*.json.

Same output format as `get generate locales assets/locales` (get_cli 1.9.1),
so projects keep working whether or not get_cli is installed. `getx` prefers
get_cli when it is available and falls back to this.

Usage:
    python locales.py [--project .]

Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import reporter
from reporter import out

HEADER = """// DO NOT EDIT. This is code generated via package:get_cli/get_cli.dart

// ignore_for_file: lines_longer_than_80_chars
// ignore: avoid_classes_with_only_static_members
"""


def flatten(data: dict, prefix: str = "") -> dict[str, str]:
    """Nested objects become parent_child keys, as get_cli does."""
    flat: dict[str, str] = {}
    for key, value in data.items():
        full = f"{prefix}_{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(flatten(value, full))
        else:
            flat[full] = str(value)
    return flat


def dart_string(value: str) -> str:
    escaped = (value.replace("\\", "\\\\").replace("'", "\\'")
               .replace("$", "\\$").replace("\n", "\\n"))
    return f"'{escaped}'"


def render(locales: dict[str, dict[str, str]]) -> str:
    keys: list[str] = []
    for values in locales.values():
        for k in values:
            if k not in keys:
                keys.append(k)
    lines = [HEADER.rstrip("\n"), "class AppTranslation {",
             "  static Map<String, Map<String, String>> translations = {"]
    lines += [f"    '{code}': Locales.{code}," for code in locales]
    lines += ["  };", "}", "", "class LocaleKeys {", "  LocaleKeys._();"]
    lines += [f"  static const {k} = '{k}';" for k in keys]
    lines += ["}", "", "class Locales {"]
    for code, values in locales.items():
        lines.append(f"  static const {code} = {{")
        lines += [f"    '{k}': {dart_string(v)}," for k, v in values.items()]
        lines.append("  };")
    lines.append("}")
    return "\n".join(lines) + "\n"


def generate(project: Path, dry_run: bool = False) -> int:
    result = reporter.current()
    files = sorted((project / "assets" / "locales").glob("*.json"))
    if not files:
        result.fail(f"no locale files in {project / 'assets/locales'}")
        out(f"error: no locale files in {project / 'assets/locales'}", file=sys.stderr)
        return 1
    # en_US first so the default language leads, then the rest alphabetically.
    files.sort(key=lambda f: (f.stem != "en_US", f.stem))
    locales = {}
    for f in files:
        try:
            locales[f.stem] = flatten(json.loads(f.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            result.fail(f"{f.name} is not valid JSON: {exc}")
            out(f"error: {f.name} is not valid JSON: {exc}", file=sys.stderr)
            return 1
    target = project / "lib/generated/locales.g.dart"
    code = render(locales)
    if dry_run:
        out(f"[dry-run] would write {target.relative_to(project)} ({len(locales)} locales)")
        result.data["dry_run"] = True
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(code, encoding="utf-8")
        out(f"wrote {target.relative_to(project)} ({len(locales)} locales, "
            f"{len(next(iter(locales.values())))} keys)")
    result.add_modified("lib/generated/locales.g.dart")
    missing = {code: [k for k in locales["en_US"] if k not in vals]
               for code, vals in locales.items() if "en_US" in locales and code != "en_US"}
    missing = {c: ks for c, ks in missing.items() if ks}
    if missing:
        result.data["missing_translations"] = missing
        for c, ks in missing.items():
            out(f"warning: {c} is missing {len(ks)} key(s): {', '.join(ks[:5])}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", default=".")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    return generate(Path(args.project).resolve(), args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
