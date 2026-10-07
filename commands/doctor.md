---
description: Check the Flutter/Dart/get_cli toolchain and audit the current project against the GetX pattern
argument-hint: '[project_dir] [--offline]'
---

Run a health check. Arguments: $ARGUMENTS (default project: current directory).

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/scripts/doctor.py" --project <dir> [--offline]
```

Summarize the result in plain language. For each FAIL and warning, give the one command or command name that fixes it (for example `dart pub global activate get_cli`, `/flutter-getx:upgrade`, `/flutter-getx:init`). Offer to apply the fixes; do not change files unless the user asks.
