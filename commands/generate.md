---
description: get_cli-style generate - a null-safe model from JSON (file, URL, or pasted), or the LocaleKeys file
argument-hint: 'model:<ClassName> with <file.json|url> [on <module>] [--nullable a,b] [--hive] | locales'
---

Run `getx generate $ARGUMENTS`.

If the user pasted JSON in the conversation instead of a file or URL, pass it inline as one quoted argument after `with`.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/scripts/getx.py" generate $ARGUMENTS --json --yes
```

How to run it:

- Run from the user's project root (or pass `--project <dir>`).
- Pass the user's arguments through unchanged, quoting any word that contains spaces or apostrophes. Add `--json --yes`.
- Read the single JSON object printed on stdout: `ok`, `created`, `modified`, `skipped`, `next`, `error`, plus command-specific fields. Progress goes to stderr.
- Exit code 2 means the arguments were invalid: show the user the corrected command from `error` (it includes a suggestion), do not guess.
- On `ok: false`, explain `error` in one sentence and the fix.

Then:

- **model**: report the classes (`classes` in the JSON) and file. With `--hive`, add `@HiveType`/`@HiveField` annotations and a `part` line, register the adapter in `main.dart`, and run `dart run build_runner build --delete-conflicting-outputs`, following `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/references/local-storage.md`. Fields the API may omit need `--nullable`; rerun with `--force` if the user agrees.
- **locales**: report `generator` (get_cli or bundled) and any `missing_translations`; offer to fill them.

Finish with `flutter analyze`.
