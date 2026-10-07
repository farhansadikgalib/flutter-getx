# Proposal

## Why

Setting up a production-grade Flutter GetX app the way [Flutter-GetX-with-Basic-Setup](https://github.com/farhansadikgalib/Flutter-GetX-with-Basic-Setup) does it (base controller/view, safe Dio client, Hive + SharedPreferences, theming, translations, connection manager, get_cli-registered routes) takes hours of copy-paste every time, and the reference repo is pinned to 2023-era packages (hive 2.2.3, firebase_core 2.x, flutter_lints 3, `MaterialStateProperty`, `textScaleFactor`) that no longer build cleanly on Flutter 3.47 / Dart 3.13. A publishable Claude skill turns that setup into a repeatable, version-current workflow Claude can run for any new project or feature module.

## What Changes

- Add a new Agent-Skills-compliant skill folder `skills/flutter-getx/` (SKILL.md with frontmatter, `references/`, `scripts/`, `assets/`, `evals/`) that validates with `quick_validate.py` and packages into a `.skill` file for claude.ai, the Claude API, and Claude Code plugin marketplaces.
- Ship a project scaffolder that produces the reference repo's folder pattern (`lib/app/{components,core,data,modules,routes,services}`, `lib/config/{theme,translations}`, `lib/utils`) plus modernized versions of its basic elements: `BaseController`/`BaseView`/`PageState`, `InitialBinding`, `ConnectionManagerController`, `BaseClient` (Dio) with `ApiException`/`ApiCallStatus`, `MyWidgetsAnimator`, `CustomSnackBar`, loading overlay, `MyHive`, `MySharedPref`, `MyTheme`/`MyStyles`/light+dark colors, `LocalizationService` + `Strings` keys with en_US/ar_AR, `AppPages`/`Routes`, and a `home` module.
- Pin every dependency to the latest pub.dev release at implementation time (resolved on 2026-10-07: get 4.7.3, dio 5.11.1, logger 2.8.0, flutter_screenutil 5.9.3, hive_ce 2.20.2 / hive_ce_flutter 2.4.0 / hive_ce_generator 1.11.3, shared_preferences 2.5.6, connectivity_plus 7.3.2, flutter_easyloading 4.0.2, shimmer 4.0.0, google_fonts 9.0.0, flutter_svg 2.3.0, image_picker 1.2.4, url_launcher 6.3.3, flutter_lints 6.0.0, build_runner 2.16.1, cupertino_icons 2.0.0, flutter_launcher_icons 0.14.4, change_app_package_name 1.5.0, rename_app 1.6.6, pretty_dio_logger 1.4.0, http_mock_adapter 0.6.1) and rewrite template code for the APIs those versions expose (e.g. `WidgetStateProperty`, `TextScaler`, `Color.withValues`, `List<ConnectivityResult>` streams, `SvgPicture` `colorFilter`, `ColorScheme.fromSeed`). Include a script that re-queries pub.dev so the skill stays current after publish.
- Integrate [get_cli 1.9.1](https://pub.dev/packages/get_cli) as the module generator: the skill installs/activates it, uses `get create page|controller|view|provider`, `get generate model|locales`, `get install`, and `get sort`, and post-processes generated pages so controllers extend `BaseController` and views extend `BaseView` and are registered in `AppPages`.
- Make Firebase Messaging + awesome_notifications an opt-in add-on (`references/firebase-fcm.md`) rather than part of the default scaffold, so a freshly generated app runs without `google-services.json`.
- Add evaluation prompts (`evals/evals.json`) covering new-project setup, adding a module, and adding an API-backed feature, so the skill can be iterated with the skill-creator loop.

## Capabilities

### New Capabilities
- `skill-packaging`: The skill folder's structure, frontmatter, triggering description, progressive-disclosure layout, validation, and `.skill` packaging so it can be published to claude.ai, the Claude API, and Claude Code marketplaces.
- `getx-project-scaffolding`: Generating a new Flutter app (or upgrading an existing one) into the reference folder pattern with the basic elements present, every dependency at its latest pub.dev version, and the result passing `flutter analyze` and `flutter test`.
- `getx-module-generation`: Adding a feature module (page, controller, view, binding, provider, model, locale keys) through get_cli and conforming it to the project's base classes and route table.
- `getx-architecture-guidance`: The reference material Claude reads to write idiomatic GetX code on top of the scaffold: state management choices, dependency injection, navigation, networking via the safe client, theming, localization, local storage, and current-version API migration notes.

### Modified Capabilities
<!-- none: the project has no existing specs -->

## Impact

- **New files**: everything under `skills/flutter-getx/` (SKILL.md, `references/*.md`, `scripts/*.sh|py`, `assets/templates/**`, `evals/evals.json`, LICENSE). A sibling `flutter-getx-workspace/` holds eval runs and is git-ignored.
- **Tooling assumed on the user's machine**: Flutter stable (3.47.x verified locally), Dart 3.13, `dart pub global activate get_cli` (the currently activated `get` binary is stale and fails with "Invalid kernel binary format version"; reactivation fixes it), Python 3 with `pyyaml` for packaging, network access to pub.dev.
- **Dependencies replaced relative to the reference repo**: `hive`/`hive_flutter`/`hive_generator` (unmaintained since 2022–2023, SDK upper bound `<3.0.0`) are replaced by `hive_ce`/`hive_ce_flutter`/`hive_ce_generator`; `firebase_core`/`firebase_messaging`/`awesome_notifications` move to the opt-in add-on.
- **License**: the reference repo is Apache-2.0; the skill ships its own `LICENSE.txt` (Apache-2.0) and credits the source repo in SKILL.md.
- **No existing project code is modified**; the repo currently contains only OpenSpec scaffolding.
