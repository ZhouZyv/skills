# Zyv Zhou's Skills

English | [中文](README.md)

A personal agent skills repository, distributed as a Claude Code plugin and also usable by copying or symlinking to your local harness. Five skills: an objective technical-doc writer, a publication-style writing skill, a five-phase development workflow, a dating strategist, and a legal advisor.

> The writing skills (`tech-doc-writer`, `calm-dev-writer`) and the personal-assistant skills (`love-strategist`, `legal-advisor`) are authored in Chinese — their trigger descriptions and instructions assume a Chinese context. `riper-5` works in any language.

## Skills

Positioning and boundaries of the five skills:

| Skill | What it does | When to use |
|-------|--------------|-------------|
| [tech-doc-writer](skills/tech-doc-writer/SKILL.md) | Turns raw material into an objective, accurate, reproducible technical document | You have code/notes/material and want a solid engineering doc |
| [calm-dev-writer](skills/calm-dev-writer/SKILL.md) | Rewrites a technical doc into a reader-facing publication with clear judgment and voice | You want to publish to a blog/WeChat/Zhihu, with opinions and style |
| [riper-5](skills/riper-5/SKILL.md) | Five-phase development workflow: Research → Diverge → Plan → Execute → Review | Complex features, refactors, architecture changes — plan before you build |
| [love-strategist](skills/love-strategist/SKILL.md) | Reads chat history to gauge relationship stage and signals, then gives progression strategy and style-matched messages | Dating/crush topics: "how do I reply", "is she into me" |
| [legal-advisor](skills/legal-advisor/SKILL.md) | General legal Q&A plus evidence analysis from chat/payment records, with statute citations and action paths | Disputes (loans, contracts, labor, consumer): "the company owes me wages", "how do I sue" |

**tech-doc-writer and calm-dev-writer are one pipeline**: the former produces an objective document (no opinions, just facts and principles), the latter rewrites it for readers (with judgment, warmth, and dry humor). Use tech-doc-writer for pure knowledge; use calm-dev-writer for publishable articles. Don't mix the two.

### tech-doc-writer

Organizes raw material (codebases, code, technical notes, meeting notes, interviews) into an objective, accurate, structured, reproducible engineering document. The technical topic is the main line; the project is the running example. Answers three questions: what it is, why it's configured this way, and how to reproduce it. Configuration is verbatim-accurate; no opinions, no fabrication.

### calm-dev-writer

Rewrites a technical document or material into a reader-facing publication in the "calm engineer" voice: calm shell, opinion as the spine, restrained irony as the human touch. Credible judgment beats emotional resonance; uncertainty is acknowledged. Temperature is adjustable (calm by default, warmer by platform), but judgment and facts don't move. Without author material, it degrades to an objective analysis — it won't fake a first-person voice.

### riper-5

A five-phase development workflow: Research → Diverge → Plan → Execute → Review, each phase advancing only after explicit user confirmation. For complex features, multi-module refactors, and architecture changes. Single-line fixes and simple Q&A are handled directly — the full flow isn't needed. When information is missing or external dependencies are unavailable, it pauses and explains rather than guessing or working around.

### love-strategist

A dating strategist: extracts real signals from chat history (statistics plus close reading), gauges relationship stage, reads attraction signals, builds a profile of the other person, and proposes progression strategy with messages matched to their texting style. Evidence first; pacing follows signals, not calendars. Refuses manipulative tactics, and honestly advises stopping when the other person has clearly said no. Works with chat exports from any platform (JSON with auto-detected fields, or plain text), with a stdlib-only preprocessing script; case files live in `./chat-intel/`.

### legal-advisor

A legal advisor: general legal consultation and dispute evidence analysis. Extracts evidence from chat records and payment bills, characterizes the legal relationship (loan / gift / unjust enrichment), builds an evidence checklist, and lays out step-by-step remedies. Statute numbers must come from retrieval or are flagged as unverified; output includes a disclaimer. Works with chat exports from any platform and mainstream payment bills such as WeChat Pay and Alipay (xlsx/csv, column names auto-detected), with a stdlib-only preprocessing script; case files live in `./legal-cases/`.

## Installation

### Option 1: Claude Code plugin (recommended)

```bash
claude plugin marketplace add https://github.com/ZhouZyv/skills
claude plugin install zhouzyv-skills
```

Or use `/plugin` inside a session. Updates arrive automatically with plugin releases.

### Option 2: npx skills (any agent)

```bash
npx skills add ZhouZyv/skills
```

Pick the skills you want and the target agent.

### Option 3: Symlink (for tinkerers)

```bash
git clone https://github.com/ZhouZyv/skills.git
cd skills
bash scripts/link-skills.sh
```

Symlinks every skill under `skills/` into `~/.claude/skills` and `~/.agents/skills`; a `git pull` keeps them current.

## Repository layout

```text
skills/
├── .claude-plugin/    # Claude Code plugin distribution config
├── scripts/           # link-skills.sh symlink script
├── CLAUDE.md          # maintenance discipline: add/modify/remove skill flow
├── LICENSE
└── skills/
    ├── tech-doc-writer/SKILL.md
    ├── calm-dev-writer/SKILL.md
    ├── riper-5/SKILL.md
    ├── love-strategist/SKILL.md
    └── legal-advisor/SKILL.md
```

## Maintenance

See [CLAUDE.md](CLAUDE.md) for the skill lifecycle (add, modify, remove).

## License

[MIT](LICENSE)
