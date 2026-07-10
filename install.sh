#!/usr/bin/env bash
# repo-learning 跨 agent skill 安装脚本
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_NAME="repo-learning"

TARGETS=(
  "$HOME/.agents_skills/$SKILL_NAME:primary (~/.agents_skills/$SKILL_NAME)"
  "$HOME/.claude/skills/$SKILL_NAME:Claude (~/.claude/skills/$SKILL_NAME)"
  "$HOME/.config/opencode/skills/$SKILL_NAME:opencode"
  "$HOME/.codex/skills/$SKILL_NAME:Codex (~/.codex/skills/$SKILL_NAME)"
)

FORCE=0
LINK=0
UNINSTALL=0

usage() {
  cat <<EOF
Usage: ./install.sh [--link] [--force] [--uninstall]
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --link) LINK=1 ;;
    --force) FORCE=1 ;;
    --uninstall) UNINSTALL=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
  shift
done

install_one() {
  local target="$1"
  local label="$2"
  if [[ -e "$target" && "$target" -ef "$SOURCE_DIR" ]]; then
    echo "source (already active): $label"
    return 0
  fi
  if [[ -e "$target" ]]; then
    if [[ "$FORCE" -eq 1 ]]; then
      rm -rf "$target"
    else
      echo "skip (exists): $label"
      return 0
    fi
  fi
  mkdir -p "$(dirname "$target")"
  if [[ "$LINK" -eq 1 ]]; then
    ln -s "$SOURCE_DIR" "$target"
  else
    rsync -a --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' "$SOURCE_DIR/" "$target/"
  fi
  echo "installed: $label"
}

uninstall_one() {
  local target="$1"
  local label="$2"
  if [[ -e "$target" && "$target" -ef "$SOURCE_DIR" ]]; then
    echo "keep source: $label"
    return 0
  fi
  if [[ -L "$target" || -d "$target" ]]; then
    rm -rf "$target"
    echo "removed: $label"
  fi
}

if [[ "$UNINSTALL" -eq 1 ]]; then
  for entry in "${TARGETS[@]}"; do
    IFS=':' read -r target label <<< "$entry"
    uninstall_one "$target" "$label"
  done
  exit 0
fi

for entry in "${TARGETS[@]}"; do
  IFS=':' read -r target label <<< "$entry"
  install_one "$target" "$label"
done

echo "Done. Restart your agent session to pick up the skill."
