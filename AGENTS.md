# AGENTS.md

Guidance for AI agents (Claude Code, Codex, others) and humans working on
this repository. To *use* the skill in a Flutter project, see `README.md` and
`skills/flutter-getx/SKILL.md`.

## Layout

| Path | Contents |
| --- | --- |
| `skills/flutter-getx/` | The Agent Skill: `SKILL.md`, `scripts/`, `assets/`, `references/` |
| `skills/flutter-getx/scripts/getx.py` | The `getx` CLI; every command goes through it |
| `commands/` | Claude Code slash commands; thin wrappers that run `getx ... --json --yes` |
| `.claude-plugin/` | Plugin and marketplace manifests |
| `bin/getx` | Launcher for a clone of this repo |
| `tests/` | Unit tests (`test_*.py`) and the end-to-end harness (`e2e/harness.py`) |
| `assets/brand/` | README banner |
| `openspec/` | Planning: `specs/` (current behaviour), `changes/` (proposed and archived) |

## Checks to run

Unit tests. Fast, with no Flutter or network needed; run them before every commit:

```bash
python3 -m unittest discover -s tests -v
```

Manifests:

```bash
claude plugin validate .
claude plugin validate .claude-plugin/plugin.json
```

End to end. This needs Claude Code and Flutter, takes about 30-40 minutes and costs real API usage. Run it before a release:

```bash
claude plugin marketplace add "$(pwd)"
claude plugin install flutter-getx@flutter-getx
python3 tests/e2e/harness.py --work /tmp/flutter-getx-e2e
```

## Rules

- Scripts use only the Python standard library and must run on Python 3.9.
  Start new modules with `from __future__ import annotations`; no `match`.
- Scripts print through `reporter.out()` and record changes on
  `reporter.current()`. That keeps `getx --json` output valid; never `print()`
  directly in a script.
- Templates (`assets/templates`, `module_templates`, `feature_templates`) must
  pass `flutter analyze` with no issues and `flutter test` on a fresh
  scaffold. Package versions and migration notes live in
  `skills/flutter-getx/references/packages.md`.
- Keep `version` in `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`
  and the `SKILL.md` metadata equal; a unit test enforces it.
- Commit messages and PR descriptions carry no AI attribution: no
  `Co-Authored-By` trailers, no "Generated with" lines.
