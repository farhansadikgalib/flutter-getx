<div align="center">

# Flutter GetX for Claude

**Production-ready Flutter apps with GetX, from a single command.**

A Claude Code plugin and Agent Skill that scaffolds a clean GetX architecture, pins every package to its latest
pub.dev release, and adds pages, API features, models and translations with get_cli.

[![Release](https://img.shields.io/github/v/release/farhansadikgalib/flutter-getx?color=0175C2)](https://github.com/farhansadikgalib/flutter-getx/releases)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](skills/flutter-getx/LICENSE.txt)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-D97757)](#install)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skills-compatible-6B4FBB)](https://agentskills.io)
[![Flutter](https://img.shields.io/badge/Flutter-3.47-02569B?logo=flutter)](https://flutter.dev)
[![GetX](https://img.shields.io/badge/GetX-4.7-8A2BE2)](https://pub.dev/packages/get)

</div>

---

## Quick start

```text
/plugin marketplace add farhansadikgalib/flutter-getx
/plugin install flutter-getx@flutter-getx
```

Then, in any folder:

```text
/flutter-getx:new my_shop
/flutter-getx:feature products https://fakestoreapi.com/products
/flutter-getx:string checkout "Checkout" --ar "الدفع"
```

`my_shop` is created, builds, and passes `flutter analyze` and `flutter test` on the first run. The products screen
loads from the API with loading, error-with-retry, empty and pull-to-refresh states, plus tests.

You can also just ask in plain words: *"Create a Flutter app with GetX, dark mode and Arabic"*. The skill triggers
on its own.

## Commands

| Command | What it does |
| --- | --- |
| `/flutter-getx:new <app_name>` | New app with the folder pattern, latest packages, generated code, and passing analyze and tests |
| `/flutter-getx:init [dir]` | Adds the pattern to an existing Flutter app; never overwrites your files |
| `/flutter-getx:page <name> [--on parent]` | Page with binding, controller, view and route, built on the base classes |
| `/flutter-getx:feature <name> <endpoint>` | API-backed screen end to end: model, data source, states, view, route, tests |
| `/flutter-getx:model <json> <ClassName>` | Null-safe model with `fromJson`, `toJson`, `copyWith`; nested objects become classes |
| `/flutter-getx:string <key> "<text>"` | Adds a string to every locale and regenerates `LocaleKeys` |
| `/flutter-getx:upgrade [dir]` | Moves an old GetX project to current packages and Flutter APIs, then fixes what breaks |
| `/flutter-getx:fcm` | Adds Firebase Cloud Messaging with local display and tap-to-route |
| `/flutter-getx:doctor [dir]` | Checks Flutter, Dart and get_cli, and audits a project against the pattern |

`/flutter-getx:new` accepts `--org com.acme`, `--platforms android,ios,web`, `--title "My Shop"` and
`--design-size 390x844` (your Figma artboard).

## What you get

```text
lib/
├── main.dart                 Hive + SharedPreferences init, ScreenUtil, GetMaterialApp
├── app/
│   ├── components/           error widget with retry, loading overlay, snackbars, state animator
│   ├── core/
│   │   ├── base/             BaseController (page state, logger), BaseView (scaffold, offline banner)
│   │   ├── binding/          InitialBinding for app-wide services
│   │   └── connection_manager/  live connectivity status
│   ├── data/
│   │   ├── local/            Hive CE and SharedPreferences wrappers
│   │   ├── models/           models and generated adapters
│   │   └── remote/           one data source per API resource
│   ├── modules/home/         binding · controller · view
│   ├── routes/               get_cli-managed routes
│   └── services/             Dio client: typed errors, timeouts, debug logging
├── config/
│   ├── theme/                light and dark themes, persisted toggle, ThemeExtensions
│   └── translations/         JSON-driven locales (English, Arabic, RTL)
└── generated/locales.g.dart  get_cli LocaleKeys
```

Plus tests for the home screen, the theme toggle, the API client, Hive storage and the language switch.

**Built in:**

- Every package resolved to its latest stable version when you run the command, with an offline fallback.
- Current Flutter APIs throughout: `WidgetStateProperty`, `withValues`, `TextScaler`, list-based connectivity results.
- Maintained `hive_ce` instead of the abandoned `hive`.
- Network access granted for Android release builds and macOS, which `flutter create` leaves out.
- get_cli for pages and locales, with identical bundled templates when get_cli isn't available.

## Install

### Claude Code plugin (recommended)

Gives you the slash commands above plus the skill.

```text
/plugin marketplace add farhansadikgalib/flutter-getx
/plugin install flutter-getx@flutter-getx
```

### skills.sh

Installs the skill for Claude Code and other agents that support Agent Skills. You get plain-language use, without the
slash commands.

```bash
npx skills add farhansadikgalib/flutter-getx
```

### claude.ai

Download `flutter-getx.skill` from the [latest release](https://github.com/farhansadikgalib/flutter-getx/releases/latest),
then upload it under **Settings, then Capabilities, then Skills**. Code execution must be on. claude.ai can't run
Flutter for you, so the skill there guides and writes code rather than running the project scripts.

### Claude API

The Skills API is generally available, so no beta header is needed:

```bash
curl -X POST "https://api.anthropic.com/v1/skills" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -F "files[]=@flutter-getx.skill;filename=flutter-getx.zip"
```

Reference the returned id with `"container": {"skills": [{"type": "custom", "skill_id": "<id>", "version": "latest"}]}`.
See the [Skills guide](https://platform.claude.com/docs/en/build-with-claude/skills-guide).

### Manual

```bash
git clone https://github.com/farhansadikgalib/flutter-getx.git
cp -r flutter-getx/skills/flutter-getx ~/.claude/skills/flutter-getx
```

## Requirements

| Tool | Version | Notes |
| --- | --- | --- |
| Flutter | stable 3.x (verified on 3.47.5) | `flutter` on PATH |
| Dart | 3.x (verified on 3.13.4) | ships with Flutter |
| Python | 3.9 or newer | runs the helper scripts; standard library only |
| get_cli | 1.9.1 | optional; activated automatically when needed |

Run `/flutter-getx:doctor` to check everything at once.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `get: Invalid kernel binary format version` | Your get_cli predates your Dart SDK. Run `dart pub global activate get_cli`. |
| `get: command not found` | Add `$HOME/.pub-cache/bin` to PATH. The commands also find it there on their own. |
| `get generate model` crashes with a null check error | Known get_cli 1.9.1 bug on Dart 3. Use `/flutter-getx:model` instead. |
| `build_runner` fails with a `contextFeatures` error | analyzer and build_runner are out of step. Re-run `/flutter-getx:upgrade`; it applies the right pin automatically. |
| No network on a release Android build or on macOS | Run `/flutter-getx:doctor`; it flags missing permissions, and `/flutter-getx:init` adds them. |
| Offline | Version lookup falls back to the dated snapshot in `references/packages.md` and warns. |

## How it works

The plugin is a thin layer of slash commands over one Agent Skill:

```text
.claude-plugin/        plugin and marketplace manifests
commands/              the /flutter-getx:* commands
skills/flutter-getx/
├── SKILL.md           workflow Claude follows
├── scripts/           new_project.sh, scaffold.py, versions.py, new_module.py,
│                      json_to_model.py, add_string.py, doctor.py
├── assets/            Dart templates, module templates, Firebase add-on
└── references/        guides Claude reads on demand: networking, state, theming, testing, ...
```

The scripts do the deterministic work: rendering templates, pinning versions, generating models. Claude does the
judgment work: wiring features, fixing analyzer output, adapting to your existing code. Every template is verified
with `flutter analyze` and `flutter test` before release.

## Contributing

Issues and pull requests are welcome.

- Keep package versions current: `python3 skills/flutter-getx/scripts/versions.py` prints the latest, and
  `skills/flutter-getx/references/packages.md` holds the dated table and migration notes.
- Validate before opening a PR:

  ```bash
  claude plugin validate .
  claude plugin validate .claude-plugin/plugin.json
  ```

- Planning notes for each change live in `openspec/`.

## Credits

The folder pattern and original basic elements come from
[Flutter-GetX-with-Basic-Setup](https://github.com/farhansadikgalib/Flutter-GetX-with-Basic-Setup).
Pages and locales use [get_cli](https://pub.dev/packages/get_cli).

## License

[Apache-2.0](skills/flutter-getx/LICENSE.txt)
