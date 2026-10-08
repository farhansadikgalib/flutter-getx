# Tasks

## 1. Housekeeping

- [x] 1.1 Archive `create-flutter-getx-skill` (`/opsx:archive`) and verify `openspec/specs/` contains its four capabilities
- [x] 1.2 Commit the pending testing-round work (Firebase options placeholder, updated `commands/fcm.md` and `firebase-fcm.md`, `.github/workflows/ci.yml`, `tests/test_scripts.py`) as its own commit with no Claude attribution; verify `python3 -m unittest discover -s tests` passes first

## 2. Structured results in the existing scripts

- [x] 2.1 Add a shared `reporter.py` (result object with `created`, `modified`, `skipped`, `next`, `error`; human output to stderr in JSON mode) and refactor `new_module.py`, `json_to_model.py`, `add_string.py`, `scaffold.py`, `versions.py` and `doctor.py` so their work functions return it; verify the 23 existing unit tests pass unchanged and non-JSON output is byte-identical for a sample run of each script
- [x] 2.2 Add `--kind controller|view` with required `--on` to `new_module.py` (controller registered in the module binding; view not routed; both refuse to overwrite); verify with unit tests on the template fallback path and with `flutter analyze` on a scaffolded app after `create controller:edit on home`

## 3. The `getx` dispatcher

- [x] 3.1 Write `scripts/getx.py`: tokeniser for `verb target:name [on m] [with s] [text] [--flags]`, snake_case normalisation, `help`/`help <verb>`, typo suggestions via difflib, exit codes 0/1/2, `--json`, `--yes`, `--dry-run`, `--project`; verify with parser unit tests covering every row of design D2 and the invalid-usage cases in the specs
- [x] 3.2 Wire the verbs: `create project|page|controller|view|string`, `generate model|locales`, `init`, `upgrade`, `doctor`, `install <pkg>` (latest pub.dev version, `flutter pub get`); verify each with a unit or integration test, and verify `--dry-run` leaves the tree unchanged (hash before and after)
- [x] 3.3 `generate model:X with <url>`: fetch with urllib, save to `assets/models/`, generate; `on <module>` writes under `lib/app/modules/<module>/data/models/`; verify against a local `http.server` fixture in the tests
- [x] 3.4 `create feature:<name> with <url|json>`: add `assets/feature_templates/` (remote source, controller with ApiCallStatus, view with MyWidgetsAnimator and RefreshIndicator, controller test) and generate from them using the model's first string fields; verify on a fresh scaffold that `flutter analyze` and `flutter test` pass with jsonplaceholder `/posts`
- [x] 3.5 `install fcm`: scripted pubspec, helper copy, placeholder `firebase_options.dart` (never overwrite), `main.dart` wiring at the `MySharedPref.init()` anchor, Podfile platform and hooks when `ios/Podfile` exists; missing anchors go into `skipped` with the manual step; verify analyze and test pass and a debug APK builds
- [x] 3.6 `upgrade`: `versions --write`, hive to hive_ce import rewrite, build_runner, and a list of the remaining analyzer issues in `next`; verify on the legacy reference repo that hive packages and imports are gone, no `MaterialStateProperty`/`withOpacity` remain, and every remaining analyzer error is listed in the JSON `analyzer.remaining` for the agent to fix (revised: package upgrades legitimately introduce API errors such as connectivity_plus list results; the e2e harness checks that script plus agent ends at 0 errors)
- [x] 3.7 `install-cli [--dir]` and repo-root `bin/getx` launcher; verify `getx doctor` runs from a fresh shell after install, and that the launcher works from a plugin-cache path, `~/.claude/skills`, and a clone

## 4. Slash commands

- [x] 4.1 Replace `commands/*.md` with `create`, `generate`, `init`, `install`, `upgrade`, `doctor` per design D6 (run `getx ... --json --yes`, act on `note`, then analyze); verify `claude plugin validate .claude-plugin/plugin.json` passes and the old nine files are gone
- [x] 4.2 Update the QA harness (`scratchpad/qa/harness.py` moved to `tests/e2e/harness.py`) to the new grammar, add cases for `create controller`, `install lottie`, `--dry-run`, `--json` and typo suggestions, and run it against a local plugin install; verify every case passes

## 5. Agent interoperability

- [x] 5.1 Add the "Command reference" section near the top of SKILL.md (grammar, target table, JSON shape, exit codes, how to run without PATH) and update the workflows to use `getx`; verify `quick_validate.py` passes and SKILL.md stays under 500 lines
- [x] 5.2 Verify Codex install: `npx skills add farhansadikgalib/flutter-getx --agent codex --yes` into a scratch project, then run `python3 .codex/skills/flutter-getx/scripts/getx.py create page:cart --json` (or the path the CLI reports) in a scaffolded app; record the exact path and command in the README
- [x] 5.3 Add repo-root `AGENTS.md` for contributors (how to run unit tests, the e2e harness and plugin validation; the no-Claude-attribution commit rule); verify each command in it runs

## 6. README, banner, release

- [x] 6.1 Create `assets/brand/banner.svg` (design D9) and render `banner.png`; verify both open and the PNG is under 300 KB
- [x] 6.2 Rewrite README: banner, one-line pitch, a get_cli to flutter-getx comparison table, quick start for Claude Code, Codex/other agents, and terminal, the command reference, JSON output for agents, "Upgrading from 0.2" mapping, and the existing install, requirements and troubleshooting sections updated; verify every command shown runs as written
- [x] 6.3 Bump to 0.3.0 in `plugin.json`, `marketplace.json` and SKILL.md metadata; repackage the `.skill`; verify the manifest-version unit test and `claude plugin validate` pass
- [x] 6.4 Commit (no Claude attribution), push, tag `v0.3.0`, release with the `.skill` asset and the migration table; verify a fresh `/plugin marketplace add farhansadikgalib/flutter-getx` install lists exactly the six new commands, then remove the test install
