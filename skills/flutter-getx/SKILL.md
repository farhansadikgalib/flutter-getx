---
name: flutter-getx
description: Scaffold and extend Flutter apps with GetX using a production folder pattern (app/core, data, modules, routes, services, config/theme, config/translations, utils) and get_cli. Use whenever the user wants a new Flutter project with GetX, asks to set up GetX architecture, bindings, routes, a base controller or base view, a Dio API client, Hive or SharedPreferences storage, dark mode or localization in a GetX app, wants to add a page, module, screen, controller, provider or model with get_cli, or wants to upgrade an older GetX project to current package versions. Trigger even if the user only says "getx", "get_cli", "GetMaterialApp" or "Obx" without asking for a scaffold.
license: Apache-2.0
compatibility: Requires Flutter stable 3.x and Dart 3.x on PATH, Python 3.9+, and network access to pub.dev for version lookup. get_cli is activated automatically with dart pub global activate.
metadata:
  author: farhansadikgalib
  version: "0.1.0"
  source: https://github.com/farhansadikgalib/Flutter-GetX-with-Basic-Setup
---

# Flutter GetX

Build Flutter apps on GetX with a fixed, proven layout: base controller and
view, a safe Dio client, Hive and SharedPreferences, light/dark themes,
JSON-driven translations, a connectivity banner, and get_cli-managed routes.
Every package is pinned to its latest pub.dev release at the moment you run
the scripts.

`SKILL_DIR` below means the directory containing this file. Run scripts with
`python3 SKILL_DIR/scripts/<name>.py` or `bash SKILL_DIR/scripts/<name>.sh`.

## Pick the task

| The user wants | Do |
|---|---|
| A new app | **New project** below |
| GetX structure in an existing Flutter app | **Existing project** below |
| A new screen or feature | **Add a module** |
| A model from a JSON response | **Add a model** |
| A screen that loads data from an API | **Add a module**, **Add a model**, then follow `references/networking.md` |
| A new string or language | `references/localization.md` |
| Colors, fonts, dark mode | `references/theming.md` |
| Caching or settings on device | `references/local-storage.md` |
| Push notifications | `references/firebase-fcm.md` (opt-in add-on) |
| Upgrade an old GetX project's packages | **Upgrade** |

If the user's request is vague, ask only for what you cannot default: app
name (snake_case), and optionally org id, platforms, and design artboard size.

## New project

```bash
bash SKILL_DIR/scripts/new_project.sh my_shop \
  --org com.acme --platforms android,ios --title "My Shop" --design-size 375x812
```

Defaults: `--org com.example`, `--platforms android,ios`, title from the name,
`375x812`. The script runs, in order, and stops on the first failure:

1. `flutter create`
2. `versions.py --write pubspec.yaml` (latest versions from pub.dev; offline it
   falls back to the dated snapshot in `references/packages.md` and warns)
3. `scaffold.py` (renders `assets/templates/`, adds asset folders to pubspec,
   grants network access on Android release and macOS)
4. `flutter pub get`, `dart run build_runner build --delete-conflicting-outputs`
5. `flutter analyze` and `flutter test` (the scaffold ships passing tests)

Report the project path, the screens it has (home), and how to add the next one.

## Existing project

```bash
python3 SKILL_DIR/scripts/versions.py --write pubspec.yaml   # adds/updates only managed packages
python3 SKILL_DIR/scripts/scaffold.py . --dry-run             # preview
python3 SKILL_DIR/scripts/scaffold.py .
flutter pub get && dart run build_runner build --delete-conflicting-outputs
flutter analyze && flutter test
```

`scaffold.py` never overwrites an existing file. It only replaces
`lib/main.dart`, `test/widget_test.dart` and `analysis_options.yaml` when they
are still the untouched `flutter create` starters. It prints every skipped
file: for each, tell the user and merge by hand when it matters (usually
`main.dart`: compare with `assets/templates/lib/main.dart.tmpl`).

If the project already uses GetX with a different layout, move existing
screens into `lib/app/modules/<name>/` one at a time and register them in
`app_pages.dart`; do not delete the user's code.

## Add a module

```bash
python3 SKILL_DIR/scripts/new_module.py product_detail            # lib/app/modules/product_detail
python3 SKILL_DIR/scripts/new_module.py reviews --on product_detail  # nested route /product-detail/reviews
```

The script refuses if the module exists, ensures get_cli works (re-activating
a stale install), runs `get create page:...` so get_cli registers the route,
then rewrites the controller to extend `BaseController` and the view to extend
`BaseView` with `appBar` / `body` overrides. Without get_cli it produces the
identical files from `assets/module_templates/`. Then fill in the controller
and view, and navigate with `Get.toNamed(Routes.PRODUCT_DETAIL)`.

Do not use `get init`, `get create project`, `get create screen` or
`get generate model`; `references/get-cli.md` explains why and lists the
get_cli commands that are safe.

## Add a model

Save a representative JSON response under `assets/models/`, then:

```bash
python3 SKILL_DIR/scripts/json_to_model.py assets/models/product.json ProductModel --nullable discount
```

Writes `lib/app/data/models/product_model.dart` with `fromJson`, `toJson`,
`copyWith`, one class per nested object. Mark fields the API may omit with
`--nullable`. To cache it in Hive, add annotations and run build_runner
(`references/local-storage.md`).

## Upgrade

1. `python3 SKILL_DIR/scripts/versions.py --write pubspec.yaml` (add
   `--firebase` if the project uses FCM), then `flutter pub get`. The script
   also removes `hive`/`hive_flutter`/`hive_generator` and moves build tools
   to `dev_dependencies`.
2. Switch Hive imports to `package:hive_ce/hive.dart` and
   `package:hive_ce_flutter/hive_flutter.dart`, then run build_runner. Keep
   every `typeId` and field index so stored data still opens.
3. Apply the platform and SDK changes in `references/packages.md` ("Upgrading
   an old project"): Dart constraint, Android Gradle toolchain, iOS/macOS
   deployment targets, empty test files, missing asset folders.
4. `flutter analyze`, then fix every issue using the migration table in
   `references/packages.md`. connectivity_plus list results are usually the
   only compile errors; the rest are deprecations and flutter_lints 6 rules.
5. `flutter test`; if the project had no real tests, add the scaffold's tests
   from `assets/templates/test/` adapted to its package name.

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
* Strings go in `assets/locales/*.json` and are read as `LocaleKeys.key.tr`
  after `get generate locales assets/locales`.
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

Tell the user what was created, any file `scaffold.py` skipped, and any
temporary pin from `references/packages.md` that applied.

## Attribution

Folder pattern and original basic elements:
[Flutter-GetX-with-Basic-Setup](https://github.com/farhansadikgalib/Flutter-GetX-with-Basic-Setup)
(Apache-2.0). This skill is released under Apache-2.0; see `LICENSE.txt`.
