---
description: Add Firebase Cloud Messaging push notifications with local display and tap-to-route
argument-hint: '[project_dir]'
---

Add push notifications to a GetX project. Arguments: $ARGUMENTS (default: current directory).

Skill directory: `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx`. Follow `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/references/firebase-fcm.md` step by step.

1. `python3 "${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/scripts/versions.py" --write pubspec.yaml --firebase` and `flutter pub get`.
2. Check for `lib/firebase_options.dart`. If missing, the user must run `flutterfire configure` with their Firebase account; tell them and continue with the code steps.
3. Copy `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/assets/addons/firebase/lib/utils/*.dart` into `lib/utils/` and wire them into `main.dart` after `MySharedPref.init()`.
4. Apply the iOS deployment target and Podfile hooks from the reference.
5. Run `flutter analyze`; report the remaining manual steps (APNs key, flutterfire).
