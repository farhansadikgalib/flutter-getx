# Tasks

## 1. Toolchain verification and skill skeleton

- [x] 1.1 Re-activate get_cli with `dart pub global activate get_cli` and verify `get --version` prints 1.9.1 on Flutter 3.47 / Dart 3.13; record the outcome (and any resolution error) in `references/get-cli.md` troubleshooting section
- [x] 1.2 Create `skills/flutter-getx/` with `SKILL.md` (frontmatter per design D7), `LICENSE.txt` (Apache-2.0), `references/`, `scripts/`, `assets/templates/`, `evals/`; verify `python quick_validate.py skills/flutter-getx` from the skill-creator scripts dir prints "Skill is valid!"
- [x] 1.3 Add repo-level `.gitignore` (ignore `flutter-getx-workspace/`, `dist/`, `__pycache__/`, `.DS_Store`) and `README.md` describing install paths; verify `git status` after `git init` shows no workspace or dist files

## 2. Version lookup script and package reference

- [x] 2.1 Write `scripts/versions.py` that queries pub.dev for the managed package list, prints `name: version`, and with `--write <pubspec>` rewrites `^` constraints; verify `python scripts/versions.py get dio` prints the current latest versions and `--write` on a sample pubspec updates only managed entries
- [x] 2.2 Implement offline fallback in `versions.py` that reads the snapshot table from `references/packages.md` and warns; verify by running with network disabled (`env HTTPS_PROXY=127.0.0.1:9` or similar) and confirming snapshot values are used
- [x] 2.3 Write `references/packages.md` with the dated version table (as of 2026-10-07), purpose of each package, the hive→hive_ce replacement, and the API migration table from design D4; verify every package in `versions.py` appears in the table and vice versa

## 3. Dart templates for the basic elements

- [x] 3.1 Port `core/` templates (base_controller, base_view, page_state, initial_binding, connection_manager_{binding,controller,type}) to `assets/templates/lib/app/core/**` using `List<ConnectivityResult>` and a plain controller field; verify by rendering into a throwaway `flutter create` app and running `flutter analyze` with zero issues
- [x] 3.2 Port `services/` templates (api_client with Dio + pretty_dio_logger, api_exceptions, api_call_status) and `components/` (api_error_widget, custom_snackbar, custom_loading_overlay, my_widgets_animator); verify `flutter analyze` is clean in the throwaway app
- [x] 3.3 Port `data/` templates: `my_hive.dart` on hive_ce_flutter, `my_shared_pref.dart`, `user_model.dart` with hive_ce annotations, and a `data/remote/` placeholder; verify `dart run build_runner build --delete-conflicting-outputs` generates `user_model.g.dart` and analysis is clean
- [x] 3.4 Port `config/theme` templates (my_theme, my_styles, my_fonts, light/dark colors, theme extensions) using `WidgetStateProperty`, `withValues`, explicit `ColorScheme`, and `theme`/`darkTheme`/`themeMode` wiring; verify `flutter analyze` reports no deprecation warnings
- [x] 3.5 Port `config/translations` templates (localization_service, strings_enum, en_US, ar_AR) plus `assets/locales/en_US.json` and `ar_AR.json`, with `LocalizationService.keys` merging get_cli's generated `AppTranslation` when present; verify `get generate locales assets/locales` runs on the throwaway app and the app compiles with both sources
- [x] 3.6 Port `routes/` (app_pages, app_routes), `modules/home/**` (BaseView-based view with theme and language toggles, `colorFilter` SVGs), `utils/constants.dart`, `main.dart` (ScreenUtilInit, `TextScaler.noScaling`, hive/shared-pref init), `analysis_options.yaml`, and the three SVG vectors; verify `flutter run -d <any device or macos>` boots to home and both toggles persist after restart
- [x] 3.7 Write `assets/templates/test/` with the widget test and an `api_client_test.dart` using `http_mock_adapter` asserting success and 404 paths; verify `flutter test` passes in the throwaway app

## 4. Scaffold script

- [x] 4.1 Write `scripts/scaffold.py <project_dir> [--app-name] [--design-size WxH] [--dry-run]` that renders every template to its destination, substitutes placeholders, creates asset directories, skips existing files with a report, and appends managed assets/fonts entries to `pubspec.yaml`; verify `--dry-run` lists all files and a real run on a fresh `flutter create` app produces the directory tree from the scaffolding spec
- [x] 4.2 Add an end-to-end `scripts/new_project.sh <name> [--org] [--platforms]` that runs `flutter create`, `versions.py --write`, `scaffold.py`, `flutter pub get`, `build_runner`, `flutter analyze`, `flutter test`; verify it completes with exit 0 on a clean machine path and `flutter pub outdated` reports no upgradable direct dependency
- [x] 4.3 Run `scaffold.py` a second time on the same project and verify it changes nothing and prints every file as skipped (idempotency scenario)

## 5. Module generation script

- [x] 5.1 Write `scripts/new_module.py <name> [--on <parent>]` that checks/activates get_cli, runs `get create page:`, post-processes controller and view to `BaseController`/`BaseView`, verifies route registration, and refuses to overwrite an existing module; verify adding `profile` to the scaffolded app yields the three files, `Routes.PROFILE == '/profile'`, and `flutter analyze` is clean
- [x] 5.2 Add the bundled-template fallback path (`assets/templates/module/**`) used when get_cli is unavailable, including route insertion into `app_pages.dart`; verify by running with `PATH` stripped of the pub cache bin and confirming identical output files
- [x] 5.3 Verify nested generation (`new_module.py settings --on profile`) and the duplicate-module refusal; both must leave `flutter analyze` clean and print the expected messages
- [x] 5.4 Write `references/get-cli.md` covering install/activation, every command the skill uses (`create page/controller/view/provider`, `generate model/locales`, `install/remove`, `sort`), the `pubspec.yaml` `get_cli:` options, the post-processing the skill applies, and the fallback; verify each command listed runs as written on the throwaway app

## 6. Architecture references and SKILL.md body

- [x] 6.1 Write `references/folder-structure.md`, `state-management.md`, `navigation-and-di.md`, `networking.md` (with the full API-backed controller + animator view example), each with a compilable example copied from the templates; verify each example file compiles when dropped into the throwaway app
- [x] 6.2 Write `references/theming.md`, `localization.md`, `local-storage.md`, `testing.md` (mock adapter, `Get.testMode`, Hive test path, controller status-transition test); verify the testing example passes under `flutter test`
- [x] 6.3 Write `references/firebase-fcm.md` as the opt-in add-on with latest `firebase_core`/`firebase_messaging`/`awesome_notifications` versions and the modernized `FcmHelper`/`AwesomeNotificationsHelper`; verify the add-on steps compile in the throwaway app after adding a placeholder `firebase_options.dart`
- [x] 6.4 Write the `SKILL.md` body (when to use, quick start, workflow, conventions, reference map, verification checklist, attribution to the reference repo); verify `wc -l` is under 500 and every referenced file path exists

## 7. Evals and first iteration

- [x] 7.1 Write `evals/evals.json` with the three prompts from design D8 and objective assertions (directories exist, analyze exit 0, route registered, versions match pub.dev); verify the JSON parses and matches `references/schemas.md` in skill-creator
- [x] 7.2 Run iteration 1 per the skill-creator workflow (with-skill and baseline runs into `flutter-getx-workspace/iteration-1/`), grade, aggregate with `aggregate_benchmark.py`, and generate the review viewer; verify `benchmark.md` exists and the with-skill pass rate exceeds baseline
- [x] 7.3 Fold review feedback into SKILL.md and references; verify re-running `quick_validate.py` still passes and `flutter analyze` on a fresh scaffold stays clean

## 8. Packaging and publish readiness

- [x] 8.1 Add `.claude-plugin/marketplace.json` referencing `skills/flutter-getx`; verify `/plugin marketplace add <local path>` followed by install lists `flutter-getx` in a fresh Claude Code session
- [x] 8.2 Run `python -m scripts.package_skill skills/flutter-getx dist/`; verify `dist/flutter-getx.skill` exists, `unzip -l` shows `flutter-getx/SKILL.md` and no `evals/` entries
- [x] 8.3 Copy the skill to `~/.claude/skills/flutter-getx` and verify a new session triggers it on "set up a new flutter project with getx and a home screen, api layer and dark mode" without naming the skill
- [ ] 8.4 Update README.md with upload instructions for claude.ai (custom skills), the Claude API, Claude Code marketplace, and `npx skills add`; verify every command in the README is copy-paste runnable
