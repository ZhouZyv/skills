# Zyv Zhou's Skills

[English](README.en.md) | 中文

个人 agent skill 仓库，通过 Claude Code plugin 分发，也可直接复制或软链到本机使用。包含三个 skill：客观技术文档、发布版写作、五阶段开发工作流。

## Skills

三个 skill 的定位与边界：

| Skill | 作用 | 什么时候用 |
|-------|------|-----------|
| [tech-doc-writer](skills/tech-doc-writer/SKILL.md) | 把原始素材整理成客观、准确、可复现的技术文档（工程/架构/原理/流程/协议均可） | 有代码库/笔记/素材，想沉淀成一份像样的技术文档 |
| [calm-dev-writer](skills/calm-dev-writer/SKILL.md) | 把技术文档改写成面向读者的发布版 | 想发到公众号/知乎/博客，要带判断和风格 |
| [riper-5](skills/riper-5/SKILL.md) | 五阶段开发工作流：Research → Diverge → Plan → Execute → Review | 复杂功能、重构、架构变更，动手前要计划 |

**tech-doc-writer 和 calm-dev-writer 是一条流水线**：前者产出客观文档（不带观点、只陈述事实与原理），后者把它改写成发布版（带判断、带温度、带克制反讽）。纯知识沉淀用 tech-doc-writer，可发布的文章用 calm-dev-writer，两者不可混用。

### tech-doc-writer

把原始技术素材（代码库、代码、技术笔记、会议记录、访谈）整理成客观、准确、结构化、可复现的技术文档。以通用技术主题为主线、实例做贯穿载体，主题不限（工程化、架构、功能原理、流程、协议、概念）；代码库主题用结构树做锚点，概念/流程主题用术语表/阶段流做锚点。回答"是什么、为什么这么设计、怎么落地"三问。配置逐字准确，不写观点、不编造内容。

### calm-dev-writer

把技术文档或素材改写成面向读者的发布版本，用"冷静工程师"的口吻：冷静为骨、观点为髓、克制反讽为活人感。判断可信优先于情绪共鸣，承认不确定性。温度两档可调（默认冷静、可升微暖），按平台调节，但判断和事实不变。没有作者素材时降级为客观分析型，不装作者视角。改写 tech-doc-writer 产出时有固定转换动作：结构树压缩、"为什么"提炼为判断、反例转成"代价"、配置片段逐字保留。

### riper-5

五阶段开发工作流：Research → Diverge → Plan → Execute → Review，每阶段需用户确认后才推进。面向复杂功能、多模块重构、架构变更；单行修复、简单问答直接处理，不必走完整流程。遇到信息缺失或外部依赖不可用时暂停并说明，不猜测、不绕过。

## 安装

### 方式一：Claude Code plugin（推荐）

```bash
claude plugin marketplace add https://github.com/ZhouZyv/skills
claude plugin install zhouzyv-skills
```

或在会话内用 `/plugin` 命令操作。更新随 plugin 版本发布自动到达。

### 方式二：npx skills（任何 agent）

```bash
npx skills add ZhouZyv/skills
```

按提示选择要装的 skill 和目标 agent。

### 方式三：软链（for tinkerers）

```bash
git clone https://github.com/ZhouZyv/skills.git
cd skills
bash scripts/link-skills.sh
```

会把 `skills/` 下每个 skill 软链到 `~/.claude/skills` 和 `~/.agents/skills`，此后 `git pull` 即更新。

## 仓库结构

```text
skills/
├── .claude-plugin/    # Claude Code plugin 分发配置
├── scripts/           # link-skills.sh 软链脚本
├── CLAUDE.md          # 维护纪律：新增/修改/下线 skill 流程
├── LICENSE
└── skills/
    ├── tech-doc-writer/SKILL.md
    ├── calm-dev-writer/SKILL.md
    └── riper-5/SKILL.md
```

## 维护

新增、修改、下线 skill 的流程见 [CLAUDE.md](CLAUDE.md)。

## License

[MIT](LICENSE)
