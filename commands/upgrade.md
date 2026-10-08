---
description: Upgrade an existing GetX project to the latest packages and current Flutter APIs, then fix what breaks
argument-hint: '[--firebase] [--dry-run]'
---

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/scripts/getx.py" upgrade $ARGUMENTS --json --yes
```

How to run it:

- Run from the user's project root (or pass `--project <dir>`).
- Pass the user's arguments through unchanged, quoting any word that contains spaces or apostrophes. Add `--json --yes`.
- Read the single JSON object printed on stdout: `ok`, `created`, `modified`, `skipped`, `next`, `error`, plus command-specific fields. Progress goes to stderr.
- Exit code 2 means the arguments were invalid: show the user the corrected command from `error` (it includes a suggestion), do not guess.
- On `ok: false`, explain `error` in one sentence and the fix.

The script updates every managed package, replaces hive with hive_ce, applies mechanical API fixes, runs build_runner, and reports `analyzer.before`, `analyzer.after` and `analyzer.remaining`. Your job is to finish it:

1. Fix every remaining analyzer error and warning using the migration table in `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/references/packages.md` (for example connectivity_plus now returns `List<ConnectivityResult>`). Do not change app behaviour.
2. Apply the platform steps in "Upgrading an old project" in the same file (Dart constraint, Android Gradle toolchain, iOS/macOS deployment targets) when the project needs them.
3. Run `flutter analyze` until it reports no errors, then `flutter test`; add the scaffold tests from `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/assets/templates/test/` if the project has none.
4. Report before and after issue counts and anything left for the user (signing, Firebase config).
