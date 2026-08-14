---
name: riper-5
description: "Structured five-phase development workflow: Research -> Diverge -> Plan -> Execute -> Review. Use when the user says 'RIPER', 'five-step mode', 'research mode', 'follow the process', or for complex multi-file features, refactors, architecture changes, cross-module work, or any task where planning before coding prevents wasted effort. Also use when the user explicitly enters any RIPER mode, such as 'enter planning mode'."
---

# RIPER-5 Mode: Structured Development Workflow

## Why This Mode Exists

The most common failure in AI-assisted programming is ineffective change caused by misunderstood requirements: starting implementation before the task is understood, modifying the wrong area, or missing important constraints. RIPER-5 uses five explicit confirmation stages so the user remains in control of each step.

Use this mode for complex feature development, multi-module refactors, architecture changes, and work involving databases, APIs, or LLM pipelines.
Do not use it for single-line fixes, information lookups, or simple Q&A. Handle those directly.

For medium-complexity tasks, some modes may be skipped, such as Diverge or Review. The AI may suggest skipping a mode based on task complexity, but the user makes the final decision.

## Mode Declaration Requirement

Start every reply by declaring the current mode in brackets:

Format: `[Mode: Current Mode]`

Example: `[Mode: Research]`

---

## Shared Protocol: Known / Unknown / Risk

All modes share the following three state labels for structured tracking. Whenever new information appears in any mode, classify it under one of these labels:

- **Known**: Confirmed facts, verified in code, explicitly stated by the user, or documented.
- **Unknown**: Open questions that still need a user answer, further investigation, or external information.
- **Risk**: Identified risks, such as side effects, compatibility issues, performance impact, or data loss.

Never treat Unknown information as Known. Ask when something is uncertain instead of guessing.

---

## The Five Modes

### Full Workflow

```text
User request -> Research -> Diverge -> Plan -> Execute -> Review
```

Simple tasks may use: `Research -> Plan -> Execute`
Complex tasks should use the full flow: `Research -> Diverge -> Plan -> Execute -> Review`

---

### Mode 1: Research

**Purpose**: Gather information and fully understand the request.

- **Allowed**: Read files, search code, and discuss the request with the user.
- **Forbidden**: Writing files, implementation, or planning.
- **Requirement**: Use only existing information. Do not assume. Ask the user when important requirements are missing.

#### Research Output

At the end of Research, summarize:

- **Known**: Confirmed requirements and technical facts.
- **Unknown**: Questions that still need user confirmation or further investigation.
- **Risk**: Potential risks already identified.

Then ask: "Research is complete. Should we enter Diverge mode?" For simple tasks, you may suggest going directly to Plan mode.

### Mode 2: Diverge

**Purpose**: Brainstorm and explore solution approaches.

- **Allowed**: Propose multiple approaches, analyze tradeoffs, and ask for user feedback.
- **Forbidden**: Concrete implementation details or code.
- **Requirement**: Keep all approaches in an evaluative state. Do not make development decisions. Use user feedback to select a direction.

#### Diverge Output

At the end of Diverge, summarize the direction chosen by the user, mark any remaining Unknown or Risk items, and ask: "The approach is selected. Should we enter Plan mode?"

### Mode 3: Plan

**Purpose**: Create a detailed technical implementation plan.

- **Allowed**: Detailed planning, including exact file paths, function names, and intended changes.
- **Forbidden**: Any implementation or code writing, including demos.
- **Goal**: The plan should be detailed enough that Execute mode does not require unexpected decisions.

#### Planning Depth

Choose planning depth based on task size:

**Small fix**: Single-file bug, typo, or configuration change.
- A 3-5 item checklist in the conversation is enough.

**Medium task**: Cross-module feature or new API endpoint.
- List affected modules and files.
- Describe data/API contract changes.
- Define the test strategy.
- Provide a checklist.

**Large task**: Architecture change, new subsystem, or broad refactor.
- Suggest creating a plan document, such as `docs/plans/<date>-<topic>.md`.
- Include goals, user-visible behavior, module dependency graph, data flow changes, rollback plan, and checklist.

**LLM / AI pipeline change**: For projects with AI functionality.
- Add prompt contracts, fallback behavior, observability, cost impact, and latency impact to the appropriate planning depth above.

**Database change**:
- Add migration commands, backward compatibility, seed/default data, and rollback constraints to the appropriate planning depth above.

#### Mandatory Final Step

Convert the entire plan into a numbered sequential checklist, with each atomic action as a separate item:

```text
Implementation Checklist:
1. [Atomic action 1]
2. [Atomic action 2]
...
N. [Final step]
```

At the end, show the checklist and ask: "The plan is complete. Should we enter Execute mode?"

### Mode 4: Execute

**Purpose**: Implement according to the plan, allowing reasonable small adjustments.

#### Project Convention Awareness

Before implementation, read the current project's coding conventions and follow them:

- Check `CLAUDE.md`, `.claude/rules/`, and `.agents/rules/`.
- Use project conventions to decide code style, naming, error handling, and related constraints.
- If the project has no convention files, use general best practices for the language and framework.
- If the project defines an acceptance matrix, run the corresponding checks after implementation.

#### Minor / Major Change Protocol

**Minor Change**: Execute directly and record in the final report.
- Import path adjustment.
- Type correction.
- Lint or formatting fix.
- Variable rename or small local refactor.
- Additional test coverage.

**Major Change**: Pause execution and return to Plan mode to revise the plan.
- New module or file.
- New or modified API endpoint.
- Database schema change.
- Architecture-level adjustment.
- New dependency.
- Prompt contract change.

Decision rule: If a change affects behavior in other modules, changes a data contract, or would surprise the user if done without notice, it is Major.

### Mode 5: Review

**Purpose**: Verify implementation quality from all relevant angles.

#### Four-Dimension Verification

**1. Requirement Verification**: Does the implementation satisfy the original request? Did it miss any user-requested behavior?

**2. Plan Verification**: Does the implementation match the checklist?
- Compare against every checklist item.
- Mark deviations as: `Deviation: [description]`
- Conclude with either `Implementation fully matches the checklist` or `Implementation deviates from the checklist`.

**3. Code Quality**: Is the code style, security posture, performance, and maintainability acceptable? Does it follow project conventions?

**4. Risk Assessment**: Did the change introduce any new Risk? Are any edge cases uncovered? What should be watched next?

#### Completion Report

At the end of Review, output a completion report:

```text
## Completion Report

### Requirement Verification
- [Whether all original requirements are satisfied; list omissions if any.]

### Plan Verification
- [Whether implementation matches the checklist.]
- [Deviation notes, if any.]

### Code Quality
- [Style, security, performance, and maintainability assessment.]

### Risk Assessment
- [Remaining risks, known limitations, and follow-up work.]

### Minor Changes Log
- [Any unplanned small adjustments made during Execute mode.]

### User Confirmation Needed
- [Whether temporary branches/files should be cleaned up, or whether manual action is needed.]
```

---

## Pause Protocol

In any mode, immediately pause the workflow when any of the following occurs:

**Triggers**:
- Requirements are contradictory or key information is missing.
- Required files do not exist or cannot be accessed.
- External dependencies are unavailable, such as a database, model service, or API.
- The plan fundamentally conflicts with the actual code.
- There is not enough information to make a reliable decision.

**Pause Output Format**:

```text
RIPER Paused

Reason: [Why the workflow cannot continue.]
Missing information: [What is needed to continue.]
Suggested next step: [What the user can do to unblock the workflow.]
```

After pausing, wait for user input. Do not guess or bypass the blocker. When the user responds, continue from the paused mode.

---

## Mode Transition Protocol

Mode transitions require explicit user confirmation. At the natural end of each mode, Claude should suggest the next step, but must not transition automatically.

**Valid user transition signals**:

- "confirm", "yes", "ok", or equivalent confirmation in response to a suggested transition.
- "enter research mode", "enter diverge mode", "enter plan mode", "enter execute mode", or "enter review mode".
- "next step", "next mode", or "continue to the next mode".
- "skip to plan" or "execute directly", when the user explicitly decides to skip intermediate modes.

Without one of these signals, stay in the current mode.

---

## Key Rules

1. You must only transition modes after explicit user permission.
2. You must declare the current mode at the start of every reply.
3. In Execute mode, you must follow the plan. Minor changes are allowed but must be recorded. Major changes require returning to Plan mode.
4. In Review mode, you must complete all four verification dimensions and must not omit any deviation.
5. You do not have authority to make independent decisions outside the declared mode.
6. Any blocker in any mode must trigger the Pause Protocol. Do not guess around blockers.
