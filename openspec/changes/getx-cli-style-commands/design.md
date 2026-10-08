# Design

## Context

See proposal.md for motivation. Current state, observed in the repo:

- `commands/` holds nine slash commands (`new`, `init`, `page`, `feature`, `model`, `string`, `upgrade`, `fcm`, `doctor`). Each calls one of seven scripts in `skills/flutter-getx/scripts/` through `${CLAUDE_PLUGIN_ROOT}`, and each script has its own argparse CLI (`new_module.py <name> --on <parent>`, `json_to_model.py <file> <Class>`, `add_string.py <key> <text> --ar ...`).
- `feature` and `fcm` have no single script; Claude follows the command's steps. End-to-end QA on 2026-10-07 passed 17 of 17 cases after the Firebase placeholder fix, which is still uncommitted.
- get_cli's grammar, verified locally against get_cli 1.9.1: `get create page:x [on y]`, `get create controller:x on y`, `get create view:x on y`, `get generate model on y with file.json`, `get generate locales assets/locales`, `get install pkg`, `get init`. `get generate model` crashes on Dart 3, and `get create screen` uses a different layout.
- Claude Code plugin commands are always namespaced as `/<plugin>:<command>`. The user chose to keep the plugin name `flutter-getx`.
- The machine has Python 3.9.6, so new Python must stay 3.9-compatible: `from __future__ import annotations`, no `match`.

## Goals / Non-Goals

**Goals:**
- One parser and dispatcher (`getx.py`) that every surface goes through, so behaviour cannot drift between Claude Code, Codex and the terminal.
- Grammar close enough to get_cli that `get create page:cart on home` becomes `getx create page:cart on home` by changing one word.
- Deterministic operations scripted. Judgment work, such as implementing a described page or fixing analyzer output, stays in the slash command and skill instructions.

**Non-Goals:**
- Reimplementing get_cli. `getx` still calls `get` for page creation and locale generation when available.
- A pub.dev or Homebrew distribution of the `getx` CLI. It ships inside the skill.
- `get sort`, `get update`, `get remove` equivalents. Users can call get_cli directly for those.
- Screenshots of generated apps (the user chose a banner only).

## Decisions

### D1. `getx.py` is a thin dispatcher over the existing scripts
The parser tokenises `verb target:name [on module] [with source] [--flags]` and calls functions imported from the existing modules (`new_module.main`, `json_to_model.main`, `add_string.main`, `scaffold.main`, `versions.main`, `doctor.main`), or runs `new_project.sh` for `create project`. The existing scripts keep their CLIs, so CI, tests and older docs keep working.
- Alternative rejected: merging all scripts into one large file. Bigger diff, and it breaks the 23 existing unit tests for no user benefit.
- Alternative rejected: shelling out to each script. It loses structured results for `--json` and doubles process startup.

To support `--json`, each script's work function returns a result object (`created`, `modified`, `skipped`, `next`) rather than only printing. The current `print` calls move behind a reporter that writes to stderr in JSON mode. These are small refactors of the existing `main` functions.

### D2. Grammar and argument rules

| Input | Parsed as |
|---|---|
| `create page:cart on home` | verb=create, target=page, name=cart, on=home |
| `create page:"Order History"` | name=order_history (snake_case) |
| `create feature:products with https://api/x` | with=URL |
| `generate model:Product with sample.json on shop` | class=Product, with=file, on=shop |
| `create string:checkout "Checkout" --ar "الدفع"` | positional text, per-language flags |
| `install fcm` / `install lottie` | add-on keyword, otherwise a pub package |

- `on` and `with` are bare words, as in get_cli, and are only recognised after a `target:name` token.
- Unknown verbs and targets get a suggestion from `difflib.get_close_matches`, and exit 2.
- `create project:<name>` is the only project form; a missing name exits 2 with an example. get_cli's interactive `get create project` is not reproduced, because it would block agents.

### D3. Exit codes and output channels
0 means success, 1 means the operation failed (exists, analyze failed, network), 2 means invalid usage. Human progress goes to stderr. Stdout carries the summary in normal mode and exactly one JSON object with `--json`. This lets agents parse stdout safely while humans see everything.

### D4. Which verbs the CLI fully automates

| Verb/target | CLI does | Slash command adds |
|---|---|---|
| create project | runs new_project.sh (analyze and test included) | report and next steps |
| init | versions + scaffold + pub get + build_runner | merge advice for skipped files |
| create page / controller / view | new_module | implements described behaviour |
| create string | add_string | translation when only English is given |
| generate model / locales | json_to_model (URL fetch with urllib) / get generate locales | Hive annotations if asked |
| install pkg / fcm | versions lookup + pubspec edit + pub get / copies add-on files, placeholder options, Podfile hooks | flutterfire guidance |
| create feature | model + page + remote source + controller/view/test **from templates** | adapts fields to the UI the user asked for |
| upgrade | versions --write + hive_ce import rewrite + build_runner | fixes the remaining analyzer issues |
| doctor | doctor.py | explains fixes |

`create feature` moves from instruction-only to template-backed. New templates in `assets/feature_templates/` produce the users-list pattern from `references/networking.md` (remote source, controller with `ApiCallStatus`, view with `MyWidgetsAnimator`, controller test), parameterised by the model class and its first two string fields. This makes `getx create feature:...` useful without an AI, and gives agents a compiling starting point.

`install fcm` moves from instruction-only to scripted for the deterministic parts: pubspec, copying helpers, the placeholder options file, the `main.dart` wiring at a known anchor (`await MySharedPref.init();`), and the Podfile platform and hooks when `ios/Podfile` exists.

### D5. controller and view targets
`new_module.py` gains `--kind controller|view` with a required `--on`. A controller is written from `module_templates/controller.dart.tmpl` and inserted into the module binding as `Get.lazyPut<XController>(() => XController())` before the closing brace of `dependencies()`. A view is written from `view.dart.tmpl` and is not routed, matching get_cli. Both refuse to overwrite.

### D6. Slash commands: six files that delegate to `getx`
`commands/{create,generate,init,install,upgrade,doctor}.md`. Each body:
1. Runs `python3 "${CLAUDE_PLUGIN_ROOT}/skills/flutter-getx/scripts/getx.py" <verb> $ARGUMENTS --json --yes`.
2. Reads the JSON. On `ok: false`, it explains the error and the fix.
3. If the arguments include free text after the grammar (for example `create page:profile showing ...`), it implements that text in the created files. `getx.py` ignores trailing free text in a `--json --yes` run and returns it as `"note"` so the command can act on it.
4. Runs `flutter analyze`, fixes issues, and reports.

`argument-hint` shows the grammar, for example `'page:<name> [on <module>] | controller:<name> on <module> | feature:<name> with <url> | project:<name> | string:<key> "<text>"'`.

### D7. Getting `getx` onto PATH
- `bin/getx` at the repo root is a POSIX sh launcher that finds `skills/flutter-getx/scripts/getx.py` relative to itself and runs `python3`.
- `getx install-cli [--dir ~/.local/bin]` writes a small launcher script there that points at the skill's current location (plugin cache, `~/.claude/skills`, `~/.codex/skills`, or a clone). If the directory is not on PATH, it prints the export line. It never edits shell rc files.
- Without installing, agents call `python3 <skill>/scripts/getx.py ...`; SKILL.md says this explicitly.

### D8. Codex and other agents
- Install routes: `npx skills add farhansadikgalib/flutter-getx --agent codex` (verified in the QA round that the CLI accepts `--agent`), or a manual copy to `~/.codex/skills/flutter-getx`.
- SKILL.md frontmatter stays spec-compliant. The body gets a "Command reference" section near the top: grammar, a target table, the JSON shape and exit codes, in about 40 lines.
- No AGENTS.md in the skill. AGENTS.md is repository guidance for contributors; add one at the repo root for people developing this repo (run tests, validate the plugin).

### D9. README banner
- `assets/brand/banner.svg`, about 1280x400: Flutter blue to GetX purple gradient, the title "flutter-getx", the tagline, and the line `/flutter-getx:create page:home` in a monospace pill.
- `banner.png` is rendered from the SVG with `rsvg-convert` or `sips` for clients that do not render SVG.
- The README references the PNG with SVG alt text and keeps the badges below the image.
- Repo-root assets are outside the packaged skill, so the `.skill` file stays small.

### D10. Versioning and migration
v0.3.0. Every old command maps to a new one, listed in the README under "Upgrading from 0.2" and in the release notes:
`new` → `create project:`, `page` → `create page:`, `feature` → `create feature:`, `model` → `generate model:`, `string` → `create string:`, `fcm` → `install fcm`; `init`, `upgrade` and `doctor` are unchanged.

## Risks / Trade-offs

- [Removing nine commands breaks muscle memory for v0.2.0 users, published the same day] → The mapping table goes in the README and release notes. Usage is near zero so far, so the cost is minimal now and only grows later.
- [`--json` refactor of the scripts can regress existing behaviour] → Keep each script's CLI output identical in non-JSON mode. The 23 existing unit tests and the 17-case end-to-end harness must still pass, and new tests cover the parser and JSON output.
- [Template-backed `create feature` produces a generic UI] → It is a compiling starting point. The slash command and the skill adapt it to the described UI, and the README says so.
- [`install fcm` editing `main.dart` and the Podfile by anchor can fail on customised files] → On a missing anchor, skip that edit, report it in `skipped` with the manual step, and never guess.
- [SVG banners render inconsistently] → Ship the PNG and reference it from the README.
- [Plugin commands remain long (`/flutter-getx:create ...`)] → This is the user's choice. The terminal form `getx create ...` is short, and the README leads with both.

## Migration Plan

1. Archive `create-flutter-getx-skill` so its specs move into `openspec/specs/`.
2. Commit the pending testing-round work (Firebase placeholder, CI workflow, unit tests) as its own commit.
3. Land this change; release v0.3.0 with the mapping table.

Rollback: v0.2.0 stays tagged with its release asset. The exact syntax for pinning a Claude Code marketplace to a git tag is checked during implementation and documented in the release notes.

## Open Questions

- Exact marketplace syntax for pinning a git tag, used only in the rollback note. It does not affect the design.
