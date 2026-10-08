# Spec Delta

## Purpose

Makes flutter-getx usable from agents other than Claude Code (such as Codex) and from a plain terminal. Any of them can drive it without prompts and read its results reliably.

## ADDED Requirements

### Requirement: Non-interactive operation
Every `getx` command SHALL complete without prompting when its required arguments are given. With `--yes`, it SHALL accept default answers for any optional confirmation. A missing required argument SHALL fail with exit code 2 and a message naming the argument, never by waiting for input.

#### Scenario: Agent runs without a TTY
- **WHEN** an agent runs `getx create page:cart --yes` with stdin closed
- **THEN** the command completes and exits 0 without waiting for input

#### Scenario: Missing name
- **WHEN** an agent runs `getx create project` with no name
- **THEN** the command exits 2 with "project name required (e.g. getx create project:my_shop)"

### Requirement: Machine-readable results
With `--json`, every command SHALL print one JSON object to stdout and nothing else. The object SHALL contain `ok`, `command`, `created`, `modified`, `skipped` (paths), `next` (suggested follow-up commands), and `error` when `ok` is false. Human-readable progress SHALL go to stderr.

#### Scenario: JSON result
- **WHEN** an agent runs `getx create page:cart --json`
- **THEN** stdout parses as JSON with `ok: true` and `created` listing the three module files

#### Scenario: JSON error
- **WHEN** an agent runs `getx create page:home --json` and `home` exists
- **THEN** stdout is JSON with `ok: false` and an `error` mentioning "already exists", and the exit code is 1

### Requirement: Runnable from any agent or shell
`getx` SHALL run with only Python 3.9+ and Flutter on PATH, from either the installed skill directory or a PATH-installed launcher. It SHALL NOT depend on Claude Code environment variables.

#### Scenario: Codex
- **WHEN** the skill is installed for Codex (`npx skills add farhansadikgalib/flutter-getx --agent codex`) and Codex follows SKILL.md
- **THEN** Codex can run `getx` commands via the skill's script path and get the same results as in Claude Code

#### Scenario: Human terminal
- **WHEN** a user runs `getx install-cli` and then `getx doctor` in a new shell
- **THEN** `getx` resolves from PATH and prints the health report

### Requirement: Agent-oriented instructions
SKILL.md SHALL contain a compact command reference with the grammar, one example per target, the JSON result shape, and exit codes. An agent SHALL be able to choose and run the right command from SKILL.md alone, without reading the references.

#### Scenario: Agent picks the command
- **WHEN** an agent is asked "add a settings screen" in a scaffolded project
- **THEN** SKILL.md directs it to `getx create page:settings`, and running that succeeds
