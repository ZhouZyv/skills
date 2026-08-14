#!/usr/bin/env bash
# 将仓库内所有正式 skill 软链到各 agent harness 的 skill 目录：
#   - ~/.claude/skills  — Claude Code
#   - ~/.agents/skills  — Codex 等 Agent Skills 兼容 harness
# 每个条目是指向本仓库的软链，`git pull` 即更新已安装的 skill。
# 新增/改名/删除 skill 后重跑本脚本。
# 仅正式 skill（skills/ 根下的）会被链接；in-progress/ 和 deprecated/ 不链接。
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
DESTS=("$HOME/.claude/skills" "$HOME/.agents/skills")

# 收集正式 skill：skills/ 根下含 SKILL.md 的目录
names=()
srcs=()
while IFS= read -r -d '' skill_md; do
  src="$(dirname "$skill_md")"
  names+=("$(basename "$src")")
  srcs+=("$src")
done < <(find "$REPO/skills" -name SKILL.md -not -path '*/node_modules/*' -not -path '*/in-progress/*' -not -path '*/deprecated/*' -print0)

for DEST in "${DESTS[@]}"; do
  # 若 $DEST 本身是指向本仓库的软链，逐 skill 软链会写回仓库自身，检测并退出。
  if [ -L "$DEST" ]; then
    resolved="$(readlink "$DEST")"
    case "$resolved" in
      "$REPO"|"$REPO"/*)
        echo "error: $DEST 是指向本仓库的软链 ($resolved)。" >&2
        echo "移除它（rm \"$DEST\"）后重跑，脚本会重建为真实目录。" >&2
        exit 1
        ;;
    esac
  fi

  mkdir -p "$DEST"

  for i in "${!names[@]}"; do
    name="${names[$i]}"
    src="${srcs[$i]}"
    target="$DEST/$name"

    # 目标是真实目录（非软链）时备份而非删除，避免丢数据
    if [ -e "$target" ] && [ ! -L "$target" ]; then
      backup="$target.bak.$$"
      mv "$target" "$backup"
      echo "backed up real dir $target -> $backup"
    fi

    ln -sfn "$src" "$target"
    echo "linked $name -> $src ($DEST)"
  done
done
