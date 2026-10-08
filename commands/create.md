---
description: get_cli-style create - project, page, controller, view, feature (API screen), or translated string
argument-hint: 'project:<name> | page:<name> [on <module>] | controller:<name> on <module> | view:<name> on <module> | feature:<name> with <url|json> | string:<key> "<text>"'
---

Run `getx create $ARGUMENTS`.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/scripts/getx.py" create $ARGUMENTS --json --yes
```

How to run it:

- Run from the user's project root (or pass `--project <dir>`).
- Pass the user's arguments through unchanged, quoting any word that contains spaces or apostrophes. Add `--json --yes`.
- Read the single JSON object printed on stdout: `ok`, `created`, `modified`, `skipped`, `next`, `error`, plus command-specific fields. Progress goes to stderr.
- Exit code 2 means the arguments were invalid: show the user the corrected command from `error` (it includes a suggestion), do not guess.
- On `ok: false`, explain `error` in one sentence and the fix.

Then do what the script cannot:

- **project**: report the path and that `flutter analyze` and `flutter test` passed (the script ran both).
- **page / controller / view**: if the JSON has a `note` (free text after the arguments, e.g. `page:profile showing the saved user's email`), implement it in the created controller and view, following `${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/references/state-management.md`. Put user-visible text in locales with `getx create string:...`.
- **feature**: the script generated a working list screen from templates. If the user described a different UI (grid, detail page, search), adapt the view and controller. Translate the new keys listed in `next` for every non-English locale with `getx create string:<key> "<English>" --ar "<Arabic>"`.
- **string**: if only English was given and the JSON lists `untranslated` locales, translate the text yourself and run the command again with `--<lang> "<text>"` for each.

Finish with `flutter analyze` (fix anything it reports) and, for features, `flutter test`. Report the created files, the route if any (`Get.toNamed(Routes.X)`), and the next command to try.

No arguments? Show `python3 "${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/scripts/getx.py" help create` and ask what to create.
