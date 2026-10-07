---
description: Upgrade an existing GetX project to the latest packages and current Flutter APIs, then fix what breaks
argument-hint: '[project_dir] [--firebase]'
---

Upgrade a GetX project. Arguments: $ARGUMENTS (default project: current directory).

Skill directory: `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx`. Follow the "Upgrade" section of `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/SKILL.md` and the tables in `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/references/packages.md`.

1. Baseline: `python3 "${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/scripts/doctor.py" --project <dir>` and `flutter analyze` (note the issue count).
2. `python3 "${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/scripts/versions.py" --write <dir>/pubspec.yaml` (add `--firebase` if the project uses Firebase), then `flutter pub get`.
3. Hive to hive_ce imports, build_runner, keeping every `typeId` and field index.
4. Platform files and SDK constraint per "Upgrading an old project" in `packages.md`.
5. Fix every `flutter analyze` issue using the migration table. Do not change app behaviour.
6. `flutter test`; add the scaffold's tests from `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/assets/templates/test/` if the project has none.
7. Report before/after issue counts, package changes, platform changes, and anything left for the user (signing, Firebase config).
