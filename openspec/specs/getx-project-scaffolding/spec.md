# getx-project-scaffolding Specification

## Purpose
Defines what a project produced by the skill must look like and do: the reference folder pattern, the basic elements present and wired, every dependency at its latest release, and a build that passes analysis and tests on first run.

## Requirements

### Requirement: Scaffold produces the reference folder pattern
When asked to set up a new GetX project, the skill SHALL create the directory layout `lib/app/{components,core/base,core/binding,core/connection_manager,data/local,data/models,data/remote,modules,routes,services}`, `lib/config/{theme,translations}`, `lib/utils`, and `assets/{images,vectors,lottie,locales,models}`.

#### Scenario: Fresh project
- **WHEN** the user asks for a new Flutter GetX app named `my_shop`
- **THEN** after the skill finishes, every directory listed above exists under `my_shop/` and `lib/main.dart` references the routes, initial binding, theme, and translations from those directories

#### Scenario: Existing project
- **WHEN** the user runs the skill inside an existing Flutter project that lacks the pattern
- **THEN** the skill adds missing directories and files without overwriting files that already exist, and reports each skipped file

### Requirement: Basic elements are present and wired
The scaffold SHALL include working implementations of: base controller with page state, base view with app bar/body/connection banner hooks, initial binding, connectivity manager, safe API client with typed exceptions and call status, widget animator keyed on call status, snackbar/toast helpers, loading overlay, Hive and SharedPreferences wrappers, light/dark theme with persisted toggle, localization service with persisted locale and at least en_US and ar_AR, route table, and a `home` module demonstrating theme and language switching.

#### Scenario: App boots to home
- **WHEN** `flutter run` is executed on the scaffolded project
- **THEN** the home screen renders with a working theme toggle and language toggle that persist across restart

#### Scenario: API call surfaces errors
- **WHEN** a controller calls the safe API client against an unreachable host
- **THEN** the call completes without an uncaught exception and the error handler receives a typed exception carrying the URL and a user-facing message

### Requirement: Dependencies are the latest stable releases
The scaffold SHALL declare each dependency at the latest stable pub.dev version available at the time the skill is run, using the version-lookup script, and SHALL replace unmaintained packages from the reference repo with their maintained successors (hive family → hive_ce family).

#### Scenario: Version lookup
- **WHEN** the version-lookup script is run with a package name
- **THEN** it prints that package's latest non-prerelease version from pub.dev, or a clear error if offline

#### Scenario: No stale pins
- **WHEN** `flutter pub outdated` is run on the fresh scaffold immediately after generation
- **THEN** no direct dependency is reported as upgradable to a newer stable version

### Requirement: Scaffold passes analysis and tests on first run
The generated project SHALL pass `flutter analyze` with zero errors and zero warnings under `flutter_lints` and SHALL pass `flutter test`.

#### Scenario: Clean analysis
- **WHEN** `flutter analyze` runs on the fresh scaffold
- **THEN** the output reports no issues, including no deprecation warnings for the pinned package versions

#### Scenario: Template tests pass
- **WHEN** `flutter test` runs on the fresh scaffold
- **THEN** all tests pass, including the shipped widget test and a unit test for the API client using the mock adapter

### Requirement: Firebase messaging is opt-in
The default scaffold SHALL NOT depend on Firebase packages; the skill SHALL offer FCM and local notifications as a separately documented add-on that the user explicitly requests.

#### Scenario: Default run needs no Firebase config
- **WHEN** a fresh scaffold is run without `google-services.json` or `GoogleService-Info.plist`
- **THEN** the app starts normally

#### Scenario: Add-on requested
- **WHEN** the user asks for push notifications
- **THEN** the skill follows the add-on reference, adds the Firebase packages at their latest versions, and wires the FCM helper into startup
