#!/usr/bin/env bash
# Create a new Flutter app with the GetX folder pattern, latest packages,
# generated code, and a passing analyze + test run.
#
# Usage:
#   new_project.sh <app_name> [--org com.example] [--platforms android,ios]
#                  [--title "My App"] [--design-size 375x812] [--dir <parent>]
#
# <app_name> must be a valid Dart package name (lowercase, underscores).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() { sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-1}"; }

[[ $# -ge 1 ]] || usage
case "$1" in -h|--help) usage 0 ;; esac

NAME="$1"; shift
ORG="com.example"
PLATFORMS="android,ios"
TITLE=""
DESIGN="375x812"
PARENT="$(pwd)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --org) ORG="$2"; shift 2 ;;
    --platforms) PLATFORMS="$2"; shift 2 ;;
    --title) TITLE="$2"; shift 2 ;;
    --design-size) DESIGN="$2"; shift 2 ;;
    --dir) PARENT="$2"; shift 2 ;;
    -h|--help) usage 0 ;;
    *) echo "unknown option: $1" >&2; usage ;;
  esac
done

if [[ ! "$NAME" =~ ^[a-z][a-z0-9_]*$ ]]; then
  echo "error: '$NAME' is not a valid Dart package name (use lowercase and underscores)" >&2
  exit 1
fi

PROJECT="$PARENT/$NAME"
if [[ -e "$PROJECT" ]]; then
  echo "error: $PROJECT already exists. To add the pattern to an existing app run:" >&2
  echo "  python3 $SCRIPT_DIR/scaffold.py $PROJECT" >&2
  exit 1
fi

command -v flutter >/dev/null || { echo "error: flutter is not on PATH" >&2; exit 1; }
command -v python3 >/dev/null || { echo "error: python3 is not on PATH" >&2; exit 1; }

step() { printf '\n==> %s\n' "$*"; }

step "flutter create ($PLATFORMS)"
flutter create --org "$ORG" --platforms "$PLATFORMS" "$PROJECT"

step "pin latest package versions"
python3 "$SCRIPT_DIR/versions.py" --write "$PROJECT/pubspec.yaml"

step "render GetX folder pattern"
TITLE_ARGS=()
[[ -n "$TITLE" ]] && TITLE_ARGS=(--app-title "$TITLE")
python3 "$SCRIPT_DIR/scaffold.py" "$PROJECT" --design-size "$DESIGN" ${TITLE_ARGS[@]+"${TITLE_ARGS[@]}"}

cd "$PROJECT"

step "flutter pub get"
flutter pub get

step "generate Hive adapters"
dart run build_runner build --delete-conflicting-outputs

step "flutter analyze"
flutter analyze

step "flutter test"
flutter test

step "done"
echo "Project ready at $PROJECT"
echo "Add a screen with: python3 $SCRIPT_DIR/new_module.py <name> --project $PROJECT"
