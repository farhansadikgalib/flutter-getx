---
description: Check Flutter, Dart, Python and get_cli, and audit the current project against the GetX pattern
argument-hint: '[--offline]'
---

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/scripts/getx.py" doctor $ARGUMENTS --json --yes
```

The JSON has `checks` (status, check, detail) and `next` (fix commands). Summarize in plain language: what is fine, and for each FAIL or warning the one command that fixes it (for example `getx upgrade`, `getx init`, `dart pub global activate get_cli`). Offer to run the fixes; do not change files unless the user asks.
