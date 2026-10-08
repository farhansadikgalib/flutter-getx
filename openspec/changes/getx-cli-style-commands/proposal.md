# Proposal

## Why

The nine v0.2.0 commands (`/flutter-getx:new`, `:page`, `:feature`, `:model`, `:string`, ...) each have their own argument style, so users have to learn them one by one. Flutter developers already know get_cli's grammar (`get create page:home on profile`, `get generate model on home with user.json`). Reusing that grammar makes the plugin familiar on first use. Today the commands also only work inside Claude Code. Codex and other agents, and humans in a terminal, have to call five different Python scripts with different flags. One get_cli-style entry point would serve all three audiences, and a banner image would make the README read like a finished project.

## What Changes

- **BREAKING** Replace the nine commands with six get_cli-style commands under the existing `flutter-getx` plugin name:
  - `/flutter-getx:create project:<name>`, `page:<name> [on <parent>]`, `controller:<name> on <module>`, `view:<name> on <module>`, `feature:<name> with <endpoint|json>`, `string:<key> "<text>"`
  - `/flutter-getx:generate model:<ClassName> with <json|url> [on <module>]`, `generate locales`
  - `/flutter-getx:init`, `/flutter-getx:install <package|fcm>`, `/flutter-getx:upgrade`, `/flutter-getx:doctor`
- Add one terminal CLI, `getx`, that accepts exactly the same grammar (`getx create page:cart on home`). The slash commands, the skill, Codex, other agents and humans all go through it. It adds `getx help`, `--dry-run`, `--json` (machine-readable results for agents), `--yes` (no prompts), and stable exit codes.
- Add `getx install-cli` to put `getx` on the user's PATH.
- Add `controller:` and `view:` targets. They conform to `BaseController`/`BaseView` and register the controller in the module binding, matching get_cli's `create controller:x on y`.
- Make agent use explicit. SKILL.md gains a command reference written for agents. The repo documents installing the skill for Codex (via skills.sh `--agent codex` or `~/.codex/skills`). Every subcommand runs non-interactively when given its arguments.
- Rewrite the README around the new grammar with a branded banner image (SVG in the repo, plus a PNG fallback), a get_cli-to-flutter-getx comparison table, and sections for Claude Code, Codex/other agents, and terminal use.
- Bump to v0.3.0 and ship a migration note mapping each old command to its new form.

## Capabilities

### New Capabilities
- `getx-command-interface`: The single get_cli-style command grammar (create, generate, init, install, upgrade, doctor), its targets and modifiers (`on`, `with`), help, dry-run, JSON output and exit codes. It covers the `getx` CLI and the plugin slash commands that delegate to it.
- `agent-interoperability`: Using the skill and the `getx` CLI from agents other than Claude Code (Codex, skills.sh-installed agents) and from a plain terminal. It covers non-interactive operation, machine-readable output, and the install paths for each agent.

### Modified Capabilities
<!-- none: openspec/specs/ is empty because create-flutter-getx-skill has not been archived yet. The behaviour it specified (scaffolding, module generation, packaging) is reused unchanged, not modified. -->

## Impact

- **Replaced:** `commands/*.md` (nine files) become six. Users of v0.2.0 commands must switch to the new forms; the README and release notes carry the mapping.
- **New:** `skills/flutter-getx/scripts/getx.py` (dispatcher), a `bin/getx` launcher, `assets/brand/banner.svg` and `banner.png`, and tests for the grammar parser.
- **Changed:** `SKILL.md` (command reference for agents), `README.md`, `.claude-plugin/*.json` (version 0.3.0), and `new_module.py` (adds controller/view targets). The existing scripts stay as the implementation behind `getx`; their CLIs keep working.
- **Unaffected:** templates, references, scaffold output, package pinning.
- **Housekeeping:** the testing round's uncommitted work (Firebase options placeholder, CI workflow, `tests/test_scripts.py`) is committed with this change, and `create-flutter-getx-skill` should be archived first so its specs move to `openspec/specs/`.
