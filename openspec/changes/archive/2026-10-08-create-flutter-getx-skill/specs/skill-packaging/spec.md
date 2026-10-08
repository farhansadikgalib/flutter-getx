# Spec Delta

## Purpose

Defines how the flutter-getx skill is laid out, described, validated, and packaged so that Claude triggers it reliably and it can be uploaded to claude.ai, the Claude API, or a Claude Code plugin marketplace without rejection.

## ADDED Requirements

### Requirement: Skill folder conforms to the Agent Skills specification
The skill SHALL live in a directory named `flutter-getx` containing exactly one `SKILL.md` whose YAML frontmatter has `name: flutter-getx`, a non-empty `description` of at most 1024 characters with no angle brackets, and only the keys `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`.

#### Scenario: Validation passes
- **WHEN** the skill-creator `quick_validate.py` script is run against the skill directory
- **THEN** it exits 0 and prints "Skill is valid!"

#### Scenario: Nested SKILL.md is rejected
- **WHEN** any additional `SKILL.md` exists under the skill directory outside `evals/`
- **THEN** validation fails and the packager refuses to build

### Requirement: Description triggers on GetX work without naming the skill
The frontmatter description SHALL state what the skill does and list concrete triggering contexts: creating a new Flutter app with GetX, scaffolding the folder pattern, adding a page/module/controller/binding/route, using get_cli, and upgrading an existing GetX project's packages.

#### Scenario: User describes GetX work implicitly
- **WHEN** a user asks to "set up a new flutter project with getx and a home screen, api layer and dark mode" without naming the skill
- **THEN** the description contains the terms needed for Claude to select the skill (GetX, Flutter, scaffold, module, get_cli)

#### Scenario: Unrelated Flutter work does not trigger
- **WHEN** a user asks about Riverpod or Bloc state management with no GetX mention
- **THEN** the description does not claim those frameworks

### Requirement: Progressive disclosure keeps SKILL.md lean
`SKILL.md` SHALL stay under 500 lines and hold only the workflow and selection logic; detailed material SHALL live in `references/`, executable steps in `scripts/`, and Dart templates in `assets/`, each referenced from `SKILL.md` with guidance on when to read or run it.

#### Scenario: Reference lookup
- **WHEN** Claude needs the full package version table or migration notes
- **THEN** `SKILL.md` points it to a specific file under `references/` rather than inlining the table

#### Scenario: Line budget
- **WHEN** `wc -l SKILL.md` is run
- **THEN** the count is below 500

### Requirement: Skill packages into a distributable archive
The skill SHALL package with the skill-creator `package_skill.py` into `flutter-getx.skill`, excluding `evals/`, `__pycache__`, `node_modules`, `.pyc` and `.DS_Store` content.

#### Scenario: Package build
- **WHEN** `python -m scripts.package_skill <path>/skills/flutter-getx <dist>` is run from the skill-creator directory
- **THEN** `<dist>/flutter-getx.skill` is created and listing the archive shows `flutter-getx/SKILL.md` at its root and no `evals/` entries

### Requirement: Licensing and attribution are explicit
The skill SHALL include an Apache-2.0 `LICENSE.txt`, set `license` in the frontmatter, and credit the reference repository URL in `SKILL.md`.

#### Scenario: Attribution present
- **WHEN** a reader opens `SKILL.md`
- **THEN** the reference repository URL and the license name are visible

### Requirement: Skill is installable in Claude Code from the repository
The repository SHALL expose the skill so Claude Code can load it from `skills/flutter-getx/` either by copying into `.claude/skills/` or through a plugin marketplace manifest.

#### Scenario: Local install
- **WHEN** the `skills/flutter-getx` folder is copied to `~/.claude/skills/flutter-getx`
- **THEN** a new Claude Code session lists `flutter-getx` among available skills and `/flutter-getx` loads it
