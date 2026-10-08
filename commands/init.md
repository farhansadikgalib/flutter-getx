---
description: Add the GetX folder pattern, latest packages, and basic elements to an existing Flutter app without overwriting your files
argument-hint: '[--title "My App"] [--design-size 375x812] [--dry-run]'
---

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/scripts/getx.py" init $ARGUMENTS --json --yes
```

How to run it:

- Run from the user's project root (or pass `--project <dir>`).
- Pass the user's arguments through unchanged, quoting any word that contains spaces or apostrophes. Add `--json --yes`.
- Read the single JSON object printed on stdout: `ok`, `created`, `modified`, `skipped`, `next`, `error`, plus command-specific fields. Progress goes to stderr.
- Exit code 2 means the arguments were invalid: show the user the corrected command from `error` (it includes a suggestion), do not guess.
- On `ok: false`, explain `error` in one sentence and the fix.

The script pins the latest packages, renders the pattern, runs `flutter pub get` and build_runner. For each entry in `skipped` (files the user had already edited), tell the user and offer to merge the template by hand, usually `lib/main.dart` against `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/assets/templates/lib/main.dart.tmpl`. Finish with `flutter analyze` and `flutter test`.
