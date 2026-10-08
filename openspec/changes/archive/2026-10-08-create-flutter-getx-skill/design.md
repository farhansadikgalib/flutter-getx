# Design

## Context

See proposal.md for motivation. Observed facts that shape the approach:

- The repo is empty apart from OpenSpec scaffolding, so the skill folder and its evals are the only deliverable.
- The reference repo (cloned and read in full during planning) has 45 Dart files. Its structure is `lib/app/{components,core,data,modules,routes,services}`, `lib/config/{theme,translations}`, `lib/utils`, with `lib/app/routes/app_routes.dart` already marked as get_cli-generated. Its code targets Dart `>=3.2.2` and contains APIs now deprecated or removed on Flutter 3.47: `MaterialStateProperty`, `textScaleFactor`, `useInheritedMediaQuery`, `withOpacity`, `ColorScheme.fromSwatch`, `SvgPicture(color:)`, and a `ConnectivityResult`-typed stream (connectivity_plus 6+ emits `List<ConnectivityResult>`).
- `hive 2.2.3` and `hive_generator 2.0.1` are unmaintained and their generator does not resolve against `build_runner 2.16`. `hive_ce` is the maintained drop-in fork with the same annotations.
- get_cli 1.9.1 (Aug 2024) is the latest release. The locally activated binary fails with "Invalid kernel binary format version", which is a stale snapshot, not an incompatibility; `dart pub global activate get_cli` rebuilds it. Its page template emits `GetxController`/`GetView`, not the reference's `BaseController`/`BaseView`, and it registers routes in `lib/app/routes/app_pages.dart` using the same `_Paths`/`Routes` shape the reference already uses.
- The Agent Skills spec and skill-creator's `quick_validate.py` constrain frontmatter keys, name format, description length (≤1024 chars) and single-SKILL.md packaging. Local skill-creator tooling (`package_skill.py`, `run_loop.py`, eval viewer) is available at the synced path.
- Flutter 3.47.5 / Dart 3.13.4 is installed locally; this is the verification target.

## Goals / Non-Goals

**Goals:**
- One skill directory that works unchanged in Claude Code, claude.ai upload, and the Skills API.
- Scaffold output that is byte-for-byte reproducible from bundled templates, so evals can assert on it.
- Latest versions resolved at run time, with a static snapshot in the reference for offline use.
- get_cli used for what it is good at (module and model generation, route registration, locale keys) and bypassed where it conflicts with the pattern (project init overwrites `lib/`).

**Non-Goals:**
- Supporting GetX 5 preview or the `get_server` backend.
- Generating platform folders beyond what `flutter create` produces.
- Replacing the user's own design system; theme files are starting points.
- Running the skill-creator eval loop during this change (tasks include a first iteration only; later iterations are follow-up work).

## Decisions

### D1. Skill lives at `skills/flutter-getx/`, not the repo root
The spec requires the directory name to equal `name`. The repo root already carries `openspec/`, `.claude/`, `.agents/`, which would be swept into a package. `skills/<name>/` matches the anthropics/skills and plugin-marketplace layout and lets `flutter-getx-workspace/` sit as a git-ignored sibling. Alternative rejected: root-level `SKILL.md` (would package OpenSpec artifacts).

### D2. Templates are real Dart files under `assets/templates/`, rendered by a Python script
Each template mirrors its destination path (`assets/templates/lib/app/core/base/base_controller.dart.tmpl`) with `{{app_name}}`-style placeholders only where needed (package name, app title, design size). A single `scripts/scaffold.py` copies and substitutes. Why Python over shell: path handling, idempotent "skip if exists" logic, and a dry-run flag are far simpler; Python 3 is already required by `package_skill.py`. Why not get_cli's `get init`: it overwrites `lib/` wholesale and does not know about `core/`, `config/`, `services/`. Alternative rejected: ask Claude to write each file from the reference doc every time (slow, inconsistent, untestable).

### D3. Project creation sequence
1. `flutter create --org <org> --platforms <list> <name>` (user-supplied; default android,ios).
2. `scripts/versions.py --write pubspec.yaml` queries `https://pub.dev/api/packages/<pkg>` for each managed package, writes `^<latest>` constraints, and falls back to the snapshot table in `references/packages.md` when offline (printing a warning).
3. `scripts/scaffold.py <project>` lays down templates, `analysis_options.yaml`, assets folders, locale JSON, and a widget test.
4. `flutter pub get`, `dart run build_runner build --delete-conflicting-outputs` (for the Hive adapter), `flutter analyze`, `flutter test`.
5. Activate get_cli and run `get sort --relative` is **not** run by default; it renames files with the separator and would diverge from templates. Documented as optional.

### D4. Package replacements and API modernization
| Reference | Chosen | Reason |
|---|---|---|
| hive / hive_flutter / hive_generator | hive_ce / hive_ce_flutter / hive_ce_generator | maintained; same `@HiveType`/`@HiveField` annotations; generator works with current build_runner |
| firebase_core / firebase_messaging / awesome_notifications in base | opt-in add-on | default app must run without Firebase config |
| `MaterialStateProperty`, `MaterialState` | `WidgetStateProperty`, `WidgetState` | removed in current Flutter |
| `textScaleFactor: 1.0` | `textScaler: TextScaler.noScaling` | deprecated |
| `GetMaterialApp(builder: Theme(...))` + `useInheritedMediaQuery` | `theme`, `darkTheme`, `themeMode` on `GetMaterialApp`; `Get.changeThemeMode` | `useInheritedMediaQuery` removed; proper theme switching |
| `ColorScheme.fromSwatch` | explicit `ColorScheme(...)` built from the color classes | deprecated |
| `withOpacity` | `withValues(alpha:)` | deprecated |
| `SvgPicture(color:)` | `colorFilter: ColorFilter.mode(...)` | removed in flutter_svg 2.x |
| `onConnectivityChanged.listen((ConnectivityResult r))` | `List<ConnectivityResult>`; treat `contains(none)` as offline | connectivity_plus 6+ |
| `flutter_lints 3.0.1` | `flutter_lints ^6.0.0` | current lint set; templates must be clean under it |
| `BaseController` holding `Get.find<ConnectionManagerController>().obs` | plain field `final connection = Get.find<ConnectionManagerController>()` | the reference wraps a controller in `.obs`, which is unnecessary and triggers lints |

The full table with versions (as of 2026-10-07) and the `versions.py` output format goes in `references/packages.md`.

### D5. Module generation = get_cli + post-process, with template fallback
`scripts/new_module.py <name> [--on <parent>]`:
1. Check `get --version`; if it fails, run `dart pub global activate get_cli` once; if still failing, use bundled module templates and print a notice.
2. Run `get create page:<name> [on <parent>]`.
3. Rewrite the generated controller (`extends GetxController` → `extends BaseController`, add import) and view (`extends GetView<X>` → `extends BaseView<X>`, replace `build` with `appBar`/`body` overrides).
4. Verify `app_pages.dart` gained the route; if get_cli could not (e.g. non-standard file), insert the entry.
5. Refuse to run if `lib/app/modules/<name>/` already exists.

Why not custom get_cli templates: get_cli supports custom files only for `create controller/view ... with <file>`, not for `create page`, and the `with` path must be local or a URL; post-processing is simpler and keeps route registration from get_cli. Alternative rejected: skipping get_cli entirely (the user explicitly wants it used, and its route registration and `generate model`/`generate locales` are genuinely useful).

### D6. Localization: get_cli locale JSON is the single source of strings
Revised during implementation. The reference uses a hand-written `Strings` class plus per-locale Dart maps. Keeping both that and get_cli's generated `AppTranslation`/`LocaleKeys` meant two key sets that drift. The scaffold now ships `assets/locales/en_US.json` and `ar_AR.json` and the generated `lib/generated/locales.g.dart`; `LocalizationService.keys` returns `AppTranslation.translations`. Code uses `LocaleKeys.hello.tr`. Adding a string means editing the JSON files and running `get generate locales assets/locales`. A pre-generated `locales.g.dart` template is bundled so the app compiles even when get_cli is unavailable.

### D7. SKILL.md structure
Frontmatter: `name`, `description` (pushy, lists trigger phrases), `license: Apache-2.0`, `compatibility: Requires Flutter stable 3.x, Dart 3.x, Python 3, network access to pub.dev; get_cli is activated automatically`, `metadata: {author, version, source}`. Body sections: When to use, Quick start (new project / existing project / add module), Workflow (numbered steps invoking the scripts), Conventions (naming, where things go), Reference map (which `references/*.md` to read for which task), Verification checklist (`flutter analyze`, `flutter test`, `flutter run`), Attribution. Target ≤ 250 lines.

`references/`: `folder-structure.md`, `state-management.md`, `navigation-and-di.md`, `networking.md`, `theming.md`, `localization.md`, `local-storage.md`, `get-cli.md`, `packages.md`, `testing.md`, `firebase-fcm.md`.

### D8. Evals
`evals/evals.json` with three prompts: (1) new app with a home screen, dark mode and Arabic; (2) add a "products" module that lists items from a public JSON API; (3) upgrade an existing older GetX project to current packages. Assertions check directory existence, `flutter analyze` exit code, route registration, and pinned versions matching pub.dev. Workspace at `flutter-getx-workspace/` (git-ignored).

### D9. Distribution
`python -m scripts.package_skill skills/flutter-getx dist/` from the skill-creator directory produces `dist/flutter-getx.skill` for claude.ai/API upload. For Claude Code, add `.claude-plugin/marketplace.json` at repo root referencing `skills/flutter-getx` so `/plugin marketplace add farhansadikgalib/flutter-getx` works; a README documents both paths plus `npx skills add`.

## Risks / Trade-offs

- [get_cli 1.9.1 may not resolve against Dart 3.13 at activation time] → `new_module.py` falls back to bundled templates; `references/get-cli.md` documents the fallback and the `dart pub global activate get_cli --overwrite` retry. Verified during task 1.
- [Latest-version lookup drifts after publish, so templates may hit new breaking changes] → `versions.py` fetches live and `packages.md` snapshot is dated; SKILL.md tells Claude to run `flutter analyze` and fix deprecations before finishing. Keep `^` constraints so minor updates flow.
- [hive_ce API differs subtly from hive (import path `package:hive_ce_flutter/hive_flutter.dart`, adapter registration)] → templates written and tested against hive_ce; migration note in `packages.md`.
- [Post-processing get_cli output is regex-based and could break if get_cli changes its template] → anchor on exact strings get_cli 1.9.1 emits, verify with `flutter analyze` after rewrite, and fall back to template generation if the expected anchors are absent.
- [Skill description too broad triggers on non-GetX Flutter work] → description names GetX explicitly and excludes other state managers; description-optimization loop is a documented follow-up.
- [Network required for versions and get_cli activation] → offline fallback to snapshot table; `flutter create` and scaffolding work offline.
- [Template Dart files inside a skill package may be flagged by upload scanners as code] → they are plain text templates with `.tmpl` suffix; no executables beyond Python scripts.

## Migration Plan

Greenfield; no deployment or rollback. Publishing steps are in tasks: package, validate, upload to claude.ai, and tag a repo release.

## Open Questions

- Which organization id (`--org`) and default platforms to bake into the quick-start prompt. Defaults to `com.example` and `android,ios`; the skill asks the user when absent. Does not affect specs or tasks.
- Whether to also publish the skill to skills.sh. Does not change the skill contents; README can add the command later.
