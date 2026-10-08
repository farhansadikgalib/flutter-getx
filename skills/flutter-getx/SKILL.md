---
name: flutter-getx
description: Scaffold and extend Flutter apps with GetX using a production folder pattern (app/core, data, modules, routes, services, config/theme, config/translations, utils) and get_cli. Use whenever the user wants a new Flutter project with GetX, asks to set up GetX architecture, bindings, routes, a base controller or base view, a Dio API client, Hive or SharedPreferences storage, dark mode or localization in a GetX app, wants to add a page, module, screen, controller, view, API feature, model or translated string (get_cli-style `getx create page:x`), or wants to upgrade an older GetX project to current package versions. Trigger even if the user only says "getx", "get_cli", "GetMaterialApp" or "Obx" without asking for a scaffold.
license: Apache-2.0
compatibility: Requires Flutter stable 3.x and Dart 3.x on PATH, Python 3.9+, and network access to pub.dev for version lookup. get_cli is activated automatically with dart pub global activate.
metadata:
  author: farhansadikgalib
  version: "0.3.0"
  source: https://github.com/farhansadikgalib/Flutter-GetX-with-Basic-Setup
---

# Flutter GetX

Build Flutter apps on GetX with a fixed, proven layout: base controller and
view, a safe Dio client, Hive and SharedPreferences, light/dark themes,
JSON-driven translations, a connectivity banner, and get_cli-managed routes.
Every package is pinned to its latest pub.dev release when the command runs.

All work goes through one command, `getx`, with get_cli's grammar. It works
the same for you (Claude Code, Codex, any agent) and for a human in a
terminal.

## Command reference

Run `getx` as `python3 SKILL_DIR/scripts/getx.py ...`, where `SKILL_DIR` is
the directory containing this file. If the user installed the launcher
(`getx install-cli`), plain `getx ...` works too. Run from the project root or
pass `--project <dir>`.

```text
getx <verb> [<target>:<name>] [on <module>] [with <source>] [flags]
```

| Command | Does |
|---|---|
| `getx create project:<name>` | New app: pattern, latest packages, codegen, analyze and test. `--org` `--platforms android,ios` `--title "App"` `--design-size 375x812` `--dir <parent>` |
| `getx create page:<name> [on <module>]` | Module (binding, controller, view) and route; nested with `on` |
| `getx create controller:<name> on <module>` | Controller registered in the module binding |
| `getx create view:<name> on <module>` | Extra view in a module, not routed |
| `getx create feature:<name> with <url\|file\|json>` | API list screen: model, data source, loading/error/empty/refresh states, route, tests |
| `getx create string:<key> "<English>" --ar "<Arabic>"` | String in every locale, `LocaleKeys` regenerated |
| `getx generate model:<Class> with <url\|file\|json> [on <module>]` | Null-safe model; nested objects become classes. `--nullable a,b` `--force` |
| `getx generate locales` | `lib/generated/locales.g.dart` (get_cli, or the bundled generator) |
| `getx init` | Add the pattern to an existing Flutter app; never overwrites edited files |
| `getx install <package> [--dev]` | Latest stable version from pub.dev, then `flutter pub get` |
| `getx install fcm` | Firebase push add-on (packages, helpers, `main.dart`, Podfile, placeholder options) |
| `getx upgrade` | Latest packages, hive to hive_ce, mechanical API fixes, analyzer report |
| `getx doctor` | Toolchain and project health check |
| `getx help [verb]` | Grammar and examples |

Names are normalized to snake_case (`page:"Order History"` becomes
`order_history`). Words after the arguments are returned as `note`.

**For agents, always add `--json --yes`.** Stdout is then exactly one JSON
object; progress goes to stderr:

```json
{"command": "getx create page:cart", "ok": true,
 "created": ["lib/app/modules/cart/controllers/cart_controller.dart", "..."],
 "modified": ["lib/app/routes/app_routes.dart", "lib/app/routes/app_pages.dart"],
 "skipped": [], "next": ["flutter analyze"], "route": "Routes.CART"}
```

On failure `ok` is false and `error` says why. Exit codes: 0 success, 1 the
operation failed (for example the module already exists), 2 invalid usage.
The `error` for exit code 2 contains the corrected command; use it instead of
guessing. Add `--dry-run` to preview any write.

## Pick the command

| The user wants | Run |
|---|---|
| A new app | `getx create project:<name>` (ask only for the name if missing) |
| GetX structure in an existing Flutter app | `getx init` |
| A screen | `getx create page:<name>`, then implement what they described |
| A screen that loads data from an API | `getx create feature:<name> with <endpoint>` |
| A model from a JSON response | `getx generate model:<Class> with <source>` |
| A new string or language | `getx create string:<key> "<text>" --ar "<text>"` |
| A package | `getx install <package>` |
| Push notifications | `getx install fcm`, then `references/firebase-fcm.md` |
| Upgrade an old GetX project | `getx upgrade`, then fix what it reports |
| Check setup or diagnose a project | `getx doctor` |
| Colors, fonts, dark mode, caching, navigation | the matching file in the reference map below |

In Claude Code with the plugin, the same commands exist as
`/flutter-getx:create`, `/flutter-getx:generate`, `/flutter-getx:init`,
`/flutter-getx:install`, `/flutter-getx:upgrade` and `/flutter-getx:doctor`.

## After the command: your part

`getx` does the deterministic work. These need judgment:

- **Described pages.** For `create page:profile showing the saved email with
  a logout button`, `getx` returns the description as `note`; implement it in
  the created controller and view.
- **Features.** The generated list screen is a working start. Adapt it if the
  user wants a grid, detail page or search. `getx` writes English into every
  locale; translate the keys it lists in `next`.
- **Strings.** If only English was given, translate it yourself and pass
  `--<lang> "<text>"` for each other locale.
- **Existing projects.** `init` never overwrites edited files. For each
  `skipped` entry, offer to merge the template by hand, usually `lib/main.dart`
  against `assets/templates/lib/main.dart.tmpl`.
- **Upgrades.** Fix every error in `analyzer.remaining` using the migration
  table in `references/packages.md`, apply the platform steps there, and run
  `flutter test`.
- **Firebase.** `flutterfire configure`, the APNs key and Xcode capabilities
  need the user's accounts; list them.

Without Python or a shell (for example on claude.ai), follow the same
workflows by hand using the templates in `assets/` and the references.

## Conventions

Follow these in all code you write for this pattern; the reasons are in the
references.

* Controllers extend `BaseController`; views extend `BaseView<C>` and
  implement `appBar` and `body`. Never put a `Scaffold` in a module view.
* State lives in controllers as `.obs`; views read it inside the smallest
  possible `Obx`. Network-backed regions use `Rx<ApiCallStatus>` and
  `MyWidgetsAnimator`.
* HTTP goes through a source in `lib/app/data/remote/` that calls
  `BaseClient.safeApiCall`. No direct `Dio()` or `GetConnect` in modules.
* Navigate by name (`Get.toNamed(Routes.X)`) so bindings run. Register
  per-screen dependencies in the module binding, app-wide ones in
  `InitialBinding`.
* Strings go in `assets/locales/*.json` (add them with `getx create string:...`)
  and are read as `LocaleKeys.key.tr`.
* Colors and text styles come from the theme. No hex literals in modules.
* Use current APIs: `WidgetStateProperty`, `withValues(alpha:)`,
  `colorFilter` on `SvgPicture`, list-based connectivity results.
* Import `package:get/get.dart` with `hide Response` in files that also import
  Dio.

## Reference map

Read only what the task needs.

| File | Read when |
|---|---|
| `references/folder-structure.md` | deciding where a file goes, naming |
| `references/state-management.md` | `.obs` vs `GetBuilder`, workers, lifecycle |
| `references/navigation-and-di.md` | routes, arguments, middleware, bindings |
| `references/networking.md` | any API call; full list-screen example |
| `references/theming.md` | colors, fonts, dark mode, ThemeExtension, screenutil |
| `references/localization.md` | strings, languages, RTL, fonts per language |
| `references/local-storage.md` | SharedPreferences keys, Hive boxes and adapters |
| `references/testing.md` | writing tests for controllers, API, Hive, widgets |
| `references/get-cli.md` | any get_cli command, troubleshooting `get` |
| `references/packages.md` | versions, temporary pins, deprecated API replacements |
| `references/firebase-fcm.md` | push notifications add-on |

## Before you finish

Run these in the project and fix anything they report:

```bash
flutter analyze   # expect: No issues found!
flutter test      # expect: All tests passed!
```

Tell the user what was created, anything listed in `skipped`, and any
temporary pin from `references/packages.md` that applied.

## Attribution

Folder pattern and original basic elements:
[Flutter-GetX-with-Basic-Setup](https://github.com/farhansadikgalib/Flutter-GetX-with-Basic-Setup)
(Apache-2.0). This skill is released under Apache-2.0; see `LICENSE.txt`.
