---
description: Add Firebase Cloud Messaging push notifications with local display and tap-to-route
argument-hint: '[project_dir]'
---

Add push notifications to a GetX project. Arguments: $ARGUMENTS (default: current directory).

Skill directory: `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx`. Follow `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/references/firebase-fcm.md` step by step.

1. `python3 "${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/scripts/versions.py" --write pubspec.yaml --firebase` and `flutter pub get`.
2. Check for `lib/firebase_options.dart`. If it is missing, copy the placeholder `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/assets/addons/firebase/lib/firebase_options.dart` to `lib/firebase_options.dart` so the app keeps compiling, and tell the user to run `flutterfire configure` with their Firebase account (it replaces the placeholder). Never overwrite an existing `firebase_options.dart`.
3. Copy `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/assets/addons/firebase/lib/utils/*.dart` into `lib/utils/` and wire them into `main.dart` after `MySharedPref.init()`.
4. Apply the iOS deployment target and Podfile hooks from the reference.
5. Run `flutter analyze` and `flutter test`; both must pass with the placeholder in place. Report the remaining manual steps (flutterfire configure, APNs key, Xcode capabilities).
