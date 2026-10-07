# flutter-getx skill

A Claude skill that scaffolds and extends Flutter apps with GetX. It uses the
folder pattern from
[Flutter-GetX-with-Basic-Setup](https://github.com/farhansadikgalib/Flutter-GetX-with-Basic-Setup),
pins every package to its latest pub.dev release when it runs, and uses
[get_cli](https://pub.dev/packages/get_cli) for module generation.

The skill lives in [`skills/flutter-getx/`](skills/flutter-getx/).

## What it does

- **New project:** `flutter create`, latest package versions, the full folder
  pattern with base controller and view, Dio client, Hive CE and
  SharedPreferences, light and dark themes, English and Arabic, then
  `flutter analyze` and `flutter test` (both pass on a fresh project).
- **Existing project:** adds the pattern without overwriting your files.
- **New screen:** `get create page` plus conversion to the base classes, with a
  template fallback when get_cli is unavailable.
- **Model from JSON:** a bundled generator, because `get generate model` crashes
  on Dart 3 projects in get_cli 1.9.1.
- **Upgrade:** moves old GetX projects to current packages and APIs.
- **Push notifications:** an opt-in Firebase Cloud Messaging add-on.

Requirements: Flutter stable 3.x, Dart 3.x, Python 3.9+, network access to
pub.dev.

## Install

### Claude Code: personal skill

```bash
git clone https://github.com/farhansadikgalib/flutter-getx.git
cp -r flutter-getx/skills/flutter-getx ~/.claude/skills/flutter-getx
```

Start a new session. The skill loads automatically for GetX requests, or run
`/flutter-getx`.

### Claude Code: plugin marketplace

Inside Claude Code:

```text
/plugin marketplace add farhansadikgalib/flutter-getx
/plugin install flutter-getx@flutter-getx
```

The same works from a shell:

```bash
claude plugin marketplace add farhansadikgalib/flutter-getx
claude plugin install flutter-getx@flutter-getx
```

### skills.sh

```bash
npx skills add farhansadikgalib/flutter-getx
```

### claude.ai

1. Build the package (see "Build the package" below) or download
   `flutter-getx.skill` from the releases page.
2. In claude.ai open Settings, then Capabilities, then Skills, and upload the
   file. Code execution must be enabled.

### Claude API

The Skills API is generally available, so no beta header is needed. Upload the
packaged archive (a zip):

```bash
curl -X POST "https://api.anthropic.com/v1/skills" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -F "files[]=@dist/flutter-getx.skill;filename=flutter-getx.zip"
```

The response contains the skill `id`. Reference it in a Messages request
together with the code execution tool:

```json
"container": {
  "skills": [{ "type": "custom", "skill_id": "<id from the upload>", "version": "latest" }]
}
```

Limits: 30 MB per skill (all files, uncompressed) and 20 skills per request.
The packaged skill is about 180 KB. See the
[Skills guide](https://platform.claude.com/docs/en/build-with-claude/skills-guide)
for the full request.

## Build the package

The packager comes from Anthropic's
[skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator).
Run it from the skill-creator directory:

```bash
python3 -m scripts.package_skill /path/to/flutter-getx/skills/flutter-getx /path/to/flutter-getx/dist
```

It validates the frontmatter and writes `dist/flutter-getx.skill` without the
`evals/` folder.

## Repository layout

| Path | Contents |
| --- | --- |
| `skills/flutter-getx/SKILL.md` | the workflow Claude follows |
| `skills/flutter-getx/scripts/` | `new_project.sh`, `scaffold.py`, `versions.py`, `new_module.py`, `json_to_model.py` |
| `skills/flutter-getx/assets/templates/` | the Dart templates for a new project |
| `skills/flutter-getx/assets/module_templates/` | fallback templates for new screens |
| `skills/flutter-getx/assets/addons/firebase/` | push notification helpers |
| `skills/flutter-getx/references/` | guides Claude reads on demand |
| `skills/flutter-getx/evals/` | evaluation prompts, not packaged |
| `.claude-plugin/marketplace.json` | Claude Code marketplace manifest |
| `openspec/` | planning artifacts for this repository |

`flutter-getx-workspace/` and `dist/` are git-ignored.

## Keeping it current

Run `python3 skills/flutter-getx/scripts/versions.py` to see the latest
versions, then update the dated table in
`skills/flutter-getx/references/packages.md`. That file also lists temporary
pins, which `versions.py` applies only while they are needed. None is active
on 2026-10-07.

## License

Apache-2.0. See [`skills/flutter-getx/LICENSE.txt`](skills/flutter-getx/LICENSE.txt).
