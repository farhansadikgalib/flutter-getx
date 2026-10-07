---
description: Create a new Flutter app with the GetX folder pattern, latest packages, and passing tests
argument-hint: '<app_name> [--org com.acme] [--platforms android,ios] [--title "My App"] [--design-size 375x812]'
---

Create a new Flutter GetX project. Arguments: $ARGUMENTS

Skill directory: `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx`. Read `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/SKILL.md` first if you have not in this session.

1. If no app name was given, ask for one (snake_case). Default the rest: `--org com.example`, `--platforms android,ios`, title from the name, `--design-size 375x812`.
2. Run, from the directory the user wants the project in (default: current directory):

   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/scripts/new_project.sh" <app_name> [options from the arguments]
   ```

3. If any step fails, read the error, fix the cause, and finish the remaining steps by hand (`flutter pub get`, `dart run build_runner build --delete-conflicting-outputs`, `flutter analyze`, `flutter test`).
4. Report: project path, packages pinned, `flutter analyze` and `flutter test` results, and the next commands to try: `/flutter-getx:page`, `/flutter-getx:feature`.
