# get_cli with this folder pattern

get_cli 1.9.1 (latest, Aug 2024), verified on Flutter 3.47.5 / Dart 3.13.4
on 2026-10-07. Every command below was run against a scaffolded project.

## Contents

1. Install and troubleshooting
2. Commands to use
3. Commands to avoid
4. What the skill changes after get_cli runs
5. pubspec options

## 1. Install and troubleshooting

```bash
dart pub global activate get_cli
get -v            # prints the GET CLI banner and version
```

Pub installs `get` into `~/.pub-cache/bin`. If that is not on PATH, either
add it or call `~/.pub-cache/bin/get` directly. `getx` checks
both locations.

| Symptom | Cause | Fix |
|---|---|---|
| `Can't load Kernel binary: Invalid kernel binary format version` | The `get` snapshot was built by an older Dart SDK. Common after a Flutter upgrade. | `dart pub global activate get_cli` rebuilds it. |
| `get: command not found` right after activation | `~/.pub-cache/bin` not on PATH | `export PATH="$PATH:$HOME/.pub-cache/bin"` |
| `get generate model` prints `Null check operator used on a null value` from `PubspecUtils.nullSafeSupport` | get_cli reads the SDK constraint under a key its pubspec parser no longer provides. Affects every Dart 3 project. | Use `getx generate model:<Class> with <json>` instead (section 3). |
| Activation fails offline | needs pub.dev | `getx` falls back to bundled templates and prints a notice (or pass `--no-get-cli`). |

## 2. Commands to use

Run them from the project root.

### Pages (modules)

Prefer `getx create page:<name> [on <parent>]`. It wraps the
command below and then conforms the files (section 4).

```bash
get create page:profile                 # lib/app/modules/profile/{bindings,controllers,views}
get create page:settings on profile     # nested: lib/app/modules/profile/settings/...
```

What get_cli does:

* Writes `<name>_binding.dart`, `<name>_controller.dart`, `<name>_view.dart`.
* Adds `Routes.PROFILE` / `_Paths.PROFILE = '/profile'` to `app_routes.dart`.
  Multi-word names become kebab paths: `product_detail` gives `/product-detail`.
* Adds a `GetPage` to `AppPages.routes` and sorts the imports.
* For `on <parent>`, nests the `GetPage` under the parent's `children:` and
  sets `Routes.SETTINGS = _Paths.PROFILE + _Paths.SETTINGS` (full path
  `/profile/settings`).

### Extra controller or view inside a module

Prefer `getx create controller:edit on profile` and `getx create view:edit on profile`: they write files that already extend `BaseController`/`BaseView` and register the controller in the binding. The notes below describe what raw get_cli produces if you use it directly.

```bash
get create controller:edit on profile   # also adds Get.lazyPut<EditController> to profile_binding.dart
get create view:edit on profile
```

The generated controller extends `GetxController` with empty `onInit`,
`onReady`, `onClose` overrides that trip the `unnecessary_overrides` lint.
Change it to `extends BaseController` and delete the empty overrides. Change
the view to `extends BaseView<EditController>` with `appBar` and `body`
overrides, as in `assets/module_templates/view.dart.tmpl`.

### Locale keys

```bash
# edit assets/locales/en_US.json and ar_AR.json (same keys in both), then:
get generate locales assets/locales
```

Regenerates `lib/generated/locales.g.dart` with `AppTranslation.translations`
and `LocaleKeys.<key>`. `LocalizationService.keys` already returns
`AppTranslation.translations`, so new keys work immediately as
`LocaleKeys.my_key.tr`. Nested JSON objects flatten to `parent_child` keys.

### Packages

```bash
get install lottie                # dart pub add lottie
get install mocktail --dev
get remove lottie
```

These only wrap `dart pub add/remove`. When you add a package, prefer
`python scripts/versions.py <pkg>` to confirm the version, then add it.

### Import sorting (optional)

```bash
get sort lib/app/modules/profile --skipRename
```

A path is required. Formats files and sorts imports. Always pass
`--skipRename`; without it get_cli renames files using the separator setting
and they stop matching the templates.

## 3. Commands to avoid

| Command | Why | Do instead |
|---|---|---|
| `get create project`, `get init` | `get init` overwrites everything in `lib/` with get_cli's own layout. | `getx create project:<name>` or `getx init` |
| `get create screen:<name>` | Belongs to the "clean" layout: writes to `lib/presentation/` and `lib/infrastructure/navigation/`, outside this pattern. | `getx create page:<name>` |
| `get generate model ...` | Crashes on Dart 3 projects in 1.9.1 (see troubleshooting). | `getx generate model:Product with sample.json` |
| `get create provider:<name> on <module>` | Works, but generates a `GetConnect` class that bypasses `BaseClient`, so you lose the shared Dio config, logging and typed errors. | A data source in `lib/app/data/remote/` that calls `BaseClient.safeApiCall` (see `networking.md`). |

## 4. What the skill changes after get_cli runs

`getx create page` keeps get_cli's binding and route registration and replaces
only the controller and view:

| File | get_cli writes | Skill rewrites to |
|---|---|---|
| controller | `extends GetxController`, counter sample, empty lifecycle overrides | `extends BaseController`, one reactive field, no empty overrides |
| view | `extends GetView<X>` with its own `Scaffold` | `extends BaseView<X>` overriding `appBar` and `body`; the base supplies the scaffold and offline banner |

Imports in the rewritten files use `package:<app>/app/core/base/...` so the
same template works at any nesting depth.

## 5. pubspec options

get_cli reads an optional `get_cli:` block in `pubspec.yaml`. Leave both
unset; the templates and scripts assume the defaults.

```yaml
get_cli:
  separator: "."     # default "_" ; "." would produce home.controller.dart
  sub_folder: false  # default true ; false flattens bindings/controllers/views
```
