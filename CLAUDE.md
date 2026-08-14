# 维护纪律

本仓库是个人 agent skill 仓库，通过 Claude Code plugin 分发。所有 skill 都放在 `skills/` 下，每个都是正式发布的：

- `skills/<name>/` — 正式 skill，进入 `.claude-plugin/plugin.json` 的 `skills` 数组，随 plugin 分发

## 新增一个 skill

1. 在 `skills/<name>/` 建目录，写 `SKILL.md`，必须含 frontmatter（`name` + `description`，`name` 与目录名一致）
2. 加入 `.claude-plugin/plugin.json` 的 `skills` 数组（这是正式发布集）
3. 在 README.md 加一行，链接到它的 `SKILL.md`
4. 跑 `scripts/link-skills.sh` 软链到本地 harness（`~/.claude/skills`、`~/.agents/skills`）

## 修改一个 skill

改完 `SKILL.md` 后：

- 检查 README 对该 skill 的描述是否仍准确，不准确就改
- 若影响定位/触发词，同步更新 plugin.json 的 `description`

## 下线一个 skill

1. 从 `.claude-plugin/plugin.json` 的 `skills` 数组移除
2. 从 README.md 移除该行
3. 重跑 `scripts/link-skills.sh`

## 版本

`.claude-plugin/plugin.json` 的 `version` 是分发版本号。每次发布（加/改/下线 skill）递增。用户 `/plugin install` 后靠版本变化收到更新。
