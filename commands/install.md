---
description: Add a pub package at its latest version, or the Firebase push-notification add-on (install fcm)
argument-hint: '<package> [--dev] | fcm'
---

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/scripts/getx.py" install $ARGUMENTS --json --yes
```

How to run it:

- Run from the user's project root (or pass `--project <dir>`).
- Pass the user's arguments through unchanged, quoting any word that contains spaces or apostrophes. Add `--json --yes`.
- Read the single JSON object printed on stdout: `ok`, `created`, `modified`, `skipped`, `next`, `error`, plus command-specific fields. Progress goes to stderr.
- Exit code 2 means the arguments were invalid: show the user the corrected command from `error` (it includes a suggestion), do not guess.
- On `ok: false`, explain `error` in one sentence and the fix.

- **package**: report the version added (`version`, `section`).
- **fcm**: the script added packages and helpers, wired `main.dart`, wrote a placeholder `lib/firebase_options.dart` (only if none existed), and patched `ios/Podfile`. Handle anything in `skipped` by hand following `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/references/firebase-fcm.md`. Tell the user the steps in `next` that need their accounts: `flutterfire configure`, the APNs key, and the Xcode capabilities.

Run `flutter analyze` last, then write the final report. For `fcm`, the report must end with the remaining manual steps from `next` (`flutterfire configure`, APNs key, Xcode capabilities), because the user needs them after this message.
