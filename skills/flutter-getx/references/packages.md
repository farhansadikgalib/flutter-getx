# Packages: versions, purpose, and migration notes

Snapshot date: **2026-10-07**. `scripts/versions.py` queries pub.dev live and
only falls back to this table when offline. Run it (or `flutter pub outdated`)
before trusting these numbers; keep `^` constraints so patch and minor updates
flow through `flutter pub upgrade`.

Verified toolchain for this snapshot: Flutter 3.47.5 stable, Dart 3.13.4.

## Managed packages

Column 2 is parsed by `versions.py` as the offline snapshot; keep the
`| name | version |` shape intact.

| Package | Version | Section | Why it is here |
|---|---|---|---|
| `get` | 4.7.3 | dependencies | State management, DI, routing, snackbars, i18n (`.tr`) |
| `logger` | 2.8.0 | dependencies | Readable logs instead of `print` |
| `flutter_screenutil` | 5.9.3 | dependencies | Responsive sizes (`.w`, `.h`, `.sp`, `.r`) from a design artboard |
| `dio` | 5.11.1 | dependencies | HTTP client behind the safe API client |
| `pretty_dio_logger` | 1.4.0 | dependencies | Request/response logging interceptor |
| `hive_ce` | 2.20.2 | dependencies | Local NoSQL database (maintained fork of hive) |
| `hive_ce_flutter` | 2.4.0 | dependencies | `Hive.initFlutter()` without path_provider boilerplate |
| `shared_preferences` | 2.5.6 | dependencies | Key-value persistence (theme, locale, tokens) |
| `connectivity_plus` | 7.3.2 | dependencies | Network status stream for the connection banner |
| `flutter_easyloading` | 4.0.2 | dependencies | Global loading HUD |
| `shimmer` | 4.0.0 | dependencies | Skeleton loading placeholders |
| `google_fonts` | 9.0.0 | dependencies | Fonts without bundling TTFs |
| `flutter_svg` | 2.3.0 | dependencies | SVG assets (theme/language icons) |
| `image_picker` | 1.2.4 | dependencies | Camera/gallery picking |
| `url_launcher` | 6.3.3 | dependencies | Open links, mail, phone |
| `cupertino_icons` | 2.0.0 | dependencies | iOS-style icons |
| `flutter_lints` | 6.0.0 | dev_dependencies | Current recommended lint set; templates are clean under it |
| `build_runner` | 2.16.2 | dev_dependencies | Runs the Hive adapter generator |
| `hive_ce_generator` | 1.11.3 | dev_dependencies | Generates `*.g.dart` type adapters |
| `http_mock_adapter` | 0.6.1 | dev_dependencies | Mocks Dio in tests |
| `flutter_launcher_icons` | 0.14.4 | dev_dependencies | Generate app icons from one image |
| `change_app_package_name` | 1.5.0 | dev_dependencies | Rename the Android/iOS bundle id |
| `rename_app` | 1.6.6 | dev_dependencies | Rename the launcher label |

## Temporary pins

`versions.py` writes a pin only while its condition holds for the versions it
resolved, and removes a pin it wrote earlier once the condition stops
holding. Add a row here whenever you add an entry to `EXTRA_PINS`.

| Package | Constraint | Applied when | Status on 2026-10-07 |
|---|---|---|---|
| `analyzer` | `">=14.0.0 <14.5.0"` | build_runner resolves to 2.16.1. analyzer 14.5.0 removed the `contextFeatures` setter that 2.16.1 calls. | Inactive. build_runner 2.16.2 (released 2026-10-07) works with analyzer 14.5. |

Symptom when the pin is needed but missing:

```
Error: The setter 'contextFeatures' isn't defined for the type 'AnalysisOptionsImpl'.
```

## Opt-in add-on: Firebase Cloud Messaging

Not in the default scaffold. See `firebase-fcm.md`; written by
`versions.py --write pubspec.yaml --firebase`.

| Package | Version | Section | Why it is here |
|---|---|---|---|
| `firebase_core` | 4.15.0 | dependencies | Initialises Firebase |
| `firebase_messaging` | 16.7.0 | dependencies | FCM token and message handlers |
| `awesome_notifications` | 0.12.1 | dependencies | Local notification display for FCM payloads |

## Tooling (global, not in pubspec)

| Tool | Version | Install |
|---|---|---|
| `get_cli` | 1.9.1 | `dart pub global activate get_cli` |

## Replacements relative to the reference repo

| Reference repo used | Scaffold uses | Reason |
|---|---|---|
| `hive ^2.2.3`, `hive_flutter ^1.1.0`, `hive_generator` | `hive_ce`, `hive_ce_flutter`, `hive_ce_generator` | hive has had no release since 2022 and its generator does not resolve against current `build_runner`/`analyzer`. hive_ce keeps the same `@HiveType`/`@HiveField` annotations and `Box` API. Import path changes to `package:hive_ce_flutter/hive_flutter.dart`. |
| `firebase_core ^2`, `firebase_messaging ^14`, `awesome_notifications ^0.9` in base deps | opt-in add-on at current majors | A fresh app must run without `google-services.json`. |
| `flutter_lints 3.0.1` | `flutter_lints ^6.0.0` | Newer rule set; several Flutter APIs the reference used are now flagged. |
| tools in `dependencies` (`flutter_launcher_icons`, `change_app_package_name`, `rename_app`) | `dev_dependencies` | They are build-time tools and should not ship in the app. |

## API migrations applied in the templates

These are the concrete differences between the reference repo's Dart code
and what compiles cleanly on the pinned versions. Apply the same rules to any
new code you write.

| Old (reference repo) | New (templates) | Package / reason |
|---|---|---|
| `MaterialStateProperty`, `MaterialState` | `WidgetStateProperty`, `WidgetState` | Flutter 3.19+ rename; old names removed |
| `MediaQuery.of(context).copyWith(textScaleFactor: 1.0)` | `MediaQuery.withNoTextScaling(child: ...)` or `textScaler: TextScaler.noScaling` | `textScaleFactor` deprecated |
| `GetMaterialApp(useInheritedMediaQuery: true, builder: Theme(...))` | `GetMaterialApp(theme:, darkTheme:, themeMode:)` | `useInheritedMediaQuery` removed; let GetX switch `themeMode` |
| `ColorScheme.fromSwatch(...)` | explicit `ColorScheme(...)` built from the color classes | `fromSwatch` deprecated |
| `color.withOpacity(0.5)` | `color.withValues(alpha: 0.5)` | wide-gamut color API |
| `SvgPicture.asset(path, color: c)` | `SvgPicture.asset(path, colorFilter: ColorFilter.mode(c, BlendMode.srcIn))` | flutter_svg 2.x removed `color` |
| `onConnectivityChanged.listen((ConnectivityResult r) ...)` | `.listen((List<ConnectivityResult> results) ...)`; offline when `results.contains(ConnectivityResult.none)` | connectivity_plus 6+ emits a list (a device can be on wifi and ethernet at once) |
| `checkConnectivity()` returns `ConnectivityResult` | returns `List<ConnectivityResult>` | same change |
| `final connectionController = Get.find<X>().obs` | `final connection = Get.find<X>()` | Wrapping a controller in `.obs` is pointless and trips lints |
| `Get.showOverlay(...)` | kept, but the overlay widget uses theme colors, not hard-coded white | still available in get 4.7 |
| `ScreenUtilInit(useInheritedMediaQuery: true, rebuildFactor: ...)` | `ScreenUtilInit(designSize:, minTextAdapt: true, splitScreenMode: true, child: ...)` | `useInheritedMediaQuery` removed in screenutil 5.9 |
| `Hive.initFlutter()` from `hive_flutter` | same call from `hive_ce_flutter` | import path only |
| `flutter_lints` 3 allowed `Key? key` + `super(key: key)` | `super.key` | `use_super_parameters` lint |

## Upgrading an old project: beyond pubspec

`versions.py --write` removes `hive`, `hive_flutter` and `hive_generator` and
moves build tools out of `dependencies`. These steps it cannot do; all were
needed to upgrade the reference repo (2023 template) on 2026-10-07:

| Area | Change | Why |
|---|---|---|
| Dart SDK constraint | `environment: sdk: ^3.13.0` | google_fonts 9 and shimmer 4 require Dart 3.13+ |
| Android Gradle | Gradle 9.3.1, AGP 9.1.0, Kotlin 2.4.0, Java 17 | Gradle 7.x does not run on Java 21; current plugins need the newer toolchain |
| Android SDK levels | `compileSdk`, `minSdk`, `targetSdk` from `flutter.*` instead of hard-coded numbers | firebase_messaging needs minSdk 23+ |
| iOS deployment target | 15.0 (Podfile, Xcode project, `AppFrameworkInfo.plist`) | Firebase iOS SDK 12 |
| macOS deployment target | 10.15 | same |
| Tests | replace empty `test/widget_test.dart` | an empty test file fails `flutter test` on load |
| Assets | create every folder declared under `flutter: assets:` | missing folders are a build error |

The fastest way to get the platform files right: run
`flutter create --org <org> --platforms <list> /tmp/ref_app` and copy
`android/settings.gradle*`, `android/build.gradle*`,
`android/app/build.gradle*` and `android/gradle/wrapper/gradle-wrapper.properties`
across, re-applying the project's `applicationId`, signing config and any
plugins (for example `com.google.gms.google-services`).

## Keeping this file current

1. `python scripts/versions.py` prints live versions; compare with the table.
2. Update the table and the snapshot date together.
3. Render a fresh scaffold and run `flutter analyze`; add any new deprecation
   fix to the migration table above.
