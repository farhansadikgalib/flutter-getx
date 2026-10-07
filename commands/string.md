---
description: Add or update a translated string in every locale and regenerate LocaleKeys
argument-hint: '<key> "<English text>" [--ar "<Arabic text>"] [--<lang> "<text>"]'
---

Add a translated string to the current GetX project. Arguments: $ARGUMENTS

Skill directory: `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx`.

1. If the user gave only English, translate it yourself for every other locale in `assets/locales/` and pass each with `--<lang>`.
2. Run from the project root:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/scripts/add_string.py" <key> "<English>" --ar "<Arabic>" [...]
   ```

3. Report the key and how to use it: `LocaleKeys.<key>.tr` (or `.trParams({...})` when the text contains `@name` placeholders).
