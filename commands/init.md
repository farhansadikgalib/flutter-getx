---
description: Add the GetX folder pattern and basic elements to an existing Flutter project without overwriting files
argument-hint: '[project_dir] [--title "My App"] [--design-size 375x812]'
---

Add the GetX pattern to an existing Flutter project. Arguments: $ARGUMENTS (default project: current directory).

Skill directory: `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx`. Read `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/SKILL.md` ("Existing project") first.

1. Confirm `pubspec.yaml` exists in the project.
2. Preview, then apply:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/scripts/scaffold.py" <project_dir> --dry-run
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/scripts/versions.py" --write <project_dir>/pubspec.yaml
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/scripts/scaffold.py" <project_dir> [--app-title ...] [--design-size ...]
   ```

3. In the project: `flutter pub get`, `dart run build_runner build --delete-conflicting-outputs`, `flutter analyze`, `flutter test`.
4. `scaffold.py` never overwrites edited files. For each file it reports as skipped, tell the user and merge the template by hand where it matters, usually `lib/main.dart` against `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/assets/templates/lib/main.dart.tmpl`.
5. Report what was created, what was skipped, and analyze/test results.
