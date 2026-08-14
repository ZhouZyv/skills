# riper-5 skill

A structured five-phase workflow skill for AI-assisted software development: Research -> Diverge -> Plan -> Execute -> Review.

Use it for complex feature work, multi-file refactors, architecture changes, database/API/LLM pipeline changes, and any task where understanding and planning before implementation prevents wasted work.

## Installation

riper-5 ships in the [skills repo](https://github.com/ZhouZyv/skills). Install via Claude Code plugin (`claude plugin install zhouzyv-skills`) or `npx skills add ZhouZyv/skills`, then pick `riper-5`.

## When to Use

Ask Codex or Claude to enter the RIPER workflow with prompts such as:

- `RIPER`
- `five-step mode`
- `research mode`
- `follow the process`
- `enter planning mode`

For simple questions, single-line fixes, or quick information lookups, the full workflow is unnecessary. Handle those directly.

## Workflow

```text
Research -> Diverge -> Plan -> Execute -> Review
```

- **Research**: Understand the request, read code, and confirm facts. No implementation.
- **Diverge**: Explore multiple approaches, compare tradeoffs, and wait for the user to choose a direction.
- **Plan**: Turn the chosen direction into a clear, executable checklist.
- **Execute**: Implement according to the plan and record any necessary minor adjustments.
- **Review**: Verify requirements, plan alignment, code quality, and remaining risks.

## Core Rules

- Start each reply by declaring the current mode, for example `Mode: Research`.
- Use `Known / Unknown / Risk` to separate confirmed facts, open questions, and identified risks.
- Do not treat unconfirmed information as fact.
- Mode transitions require explicit user confirmation.
- If critical information, permissions, or external dependencies are missing, pause and explain the blocker.

## Files

- `SKILL.md`: Full skill instructions and operating protocol.
