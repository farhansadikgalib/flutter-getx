#!/usr/bin/env python3
"""Add or update a translated string in every assets/locales/*.json file.

Usage:
    python add_string.py <key> "<English text>" ["<text for locale 2>" ...] [--project .]
    python add_string.py profile_title "Profile" --ar "الملف الشخصي"

Values are matched to locale files by language code with --<lang> flags
(--ar, --fr, ...). The first positional text is the English value. Locales
without a value get the English text and are listed so you can translate
them. Afterwards run `get generate locales assets/locales` (the script does
it when get_cli is available) and use `LocaleKeys.<key>.tr`.

Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import reporter
from reporter import out


def find_get() -> str | None:
    exe = shutil.which("get")
    if exe:
        return exe
    cand = Path(os.environ.get("PUB_CACHE", Path.home() / ".pub-cache")) / "bin" / "get"
    return str(cand) if cand.exists() else None


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # Pull out --<lang> value pairs before argparse sees them.
    per_lang: dict[str, str] = {}
    rest: list[str] = []
    i = 0
    while i < len(argv):
        m = re.fullmatch(r"--([a-z]{2})", argv[i])
        if m and i + 1 < len(argv):
            per_lang[m.group(1)] = argv[i + 1]
            i += 2
        else:
            rest.append(argv[i])
            i += 1

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("key", help="snake_case key, e.g. profile_title")
    parser.add_argument("english", help="English text")
    parser.add_argument("--project", default=".", help="Flutter project root (default: cwd)")
    parser.add_argument("--no-generate", action="store_true", help="skip `get generate locales`")
    parser.add_argument("--dry-run", action="store_true", help="show the values without writing")
    args = parser.parse_args(rest)

    if not re.fullmatch(r"[a-z][a-z0-9_]*", args.key):
        parser.error("key must be snake_case (letters, digits, underscores)")

    project = Path(args.project).resolve()
    locales_dir = project / "assets" / "locales"
    files = sorted(locales_dir.glob("*.json"))
    if not files:
        reporter.current().fail(f"no locale files in {locales_dir}; is this a scaffolded project?")
        sys.exit(f"error: no locale files in {locales_dir}; is this a scaffolded project?")

    result = reporter.current()
    per_lang.setdefault("en", args.english)
    untranslated = []
    for f in files:
        lang = f.stem.split("_")[0].lower()
        data = json.loads(f.read_text(encoding="utf-8"))
        value = per_lang.get(lang)
        if value is None:
            value = args.english
            untranslated.append(f.name)
        old = data.get(args.key)
        data[args.key] = value
        verb = "updated" if old is not None else "added"
        if args.dry_run:
            out(f"[dry-run] would set {f.name}: {args.key} = {value}")
        else:
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            out(f"{verb:8} {f.name}: {args.key} = {value}")
        result.add_modified(f"assets/locales/{f.name}")

    if untranslated:
        out("needs translation (English used): " + ", ".join(untranslated))
        result.data["untranslated"] = untranslated
    result.data["key"] = args.key
    if args.dry_run:
        result.data["dry_run"] = True
        out(f"use: LocaleKeys.{args.key}.tr")
        return 0

    if not args.no_generate:
        exe = find_get()
        if exe:
            r = subprocess.run([exe, "generate", "locales", "assets/locales"], cwd=project,
                               capture_output=True, text=True)
            ok = r.returncode == 0 and (project / "lib/generated/locales.g.dart").exists()
            out("regenerated lib/generated/locales.g.dart" if ok
                else "warning: get generate locales failed:\n" + (r.stdout + r.stderr)[-400:])
            if ok:
                result.add_modified("lib/generated/locales.g.dart")
            else:
                result.warn("get generate locales failed")
                result.add_next("get generate locales assets/locales")
        else:
            import locales  # same output format as get_cli
            locales.generate(project)

    out(f"use: LocaleKeys.{args.key}.tr")
    return 0


if __name__ == "__main__":
    sys.exit(main())
