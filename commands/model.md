---
description: Generate a null-safe Dart model (fromJson, toJson, copyWith) from a JSON sample, file, or URL
argument-hint: '<json_file_or_url> <ClassName> [--nullable field1,field2] [--hive]'
---

Generate a model in the current GetX project. Arguments: $ARGUMENTS

Skill directory: `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx`.

1. Get the JSON: a file path, a URL (fetch it once and save the response), or JSON pasted in the conversation. Save it to `assets/models/<snake_name>.json`.
2. Run:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/scripts/json_to_model.py" assets/models/<snake_name>.json <ClassName> [--nullable ...]
   ```

   Nested objects become their own classes. Use `--force` only if the user wants to overwrite an existing model.
3. With `--hive`, add `@HiveType`/`@HiveField` annotations and a `part` line, register the adapter in `main.dart`, and run build_runner, following `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/references/local-storage.md`.
4. Add a round-trip test in `test/` against the saved sample (see `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/references/testing.md`).
5. Run `flutter analyze` and report the generated classes.
