---
name: simplified-phase-tracker
description: 'Create and maintain a plain-language, phase-based execution plan with a progress table and done criteria. Use when users ask for non-technical explanations, must-have vs nice-to-have breakdowns, or dynamic status updates during implementation.'
argument-hint: 'Provide: objective, phases count, must-have scope, and current status.'
user-invocable: true
disable-model-invocation: false
---

# Simplified Phase Tracker

## Purpose
Turn technical implementation work into a non-technical phase plan that a non-developer can follow.

This skill does two things:
1. Explains architecture and phases in simple language.
2. Maintains a dynamic progress table with status and done criteria while execution proceeds.

## Use When
- User says they are not a developer and asks for a simplified plan.
- User asks for a one-page execution checklist.
- User asks for must-have vs nice-to-have breakdown.
- User asks to track progress by phase during implementation.
- User asks for ongoing status updates and completion criteria.

## Inputs to Collect
- Overall objective in one sentence.
- Number of phases (default 6 if unspecified).
- Scope preference: must-have only, or must-have plus nice-to-have.
- Starting phase and current completion state.
- Whether tracker should be session-scoped or persisted elsewhere.

## Output Format Rules
- Keep language plain and concise, avoid jargon.
- Always provide one scannable table with columns:
  - Phase
  - Scope
  - Status
  - Done Criteria
- Always label each task as Must-have or Nice-to-have when listing tasks.
- Provide delta updates only after each milestone (do not reprint unchanged details unless asked).

## Dynamic Tracking Workflow
1. Initialize tracker
- Create a tracker document at /memories/session/execution_tracker.md when absent.
- Populate all phases with status Not Started.
- Set one active phase to In Progress.

2. On each implementation checkpoint
- Update only changed rows.
- Move a phase to Done only when every done criterion is satisfied.
- If blocked, set status to Blocked and record one-line blocker note.

3. Progress communication
- After each meaningful step, report:
  - What changed since last update
  - Current active phase
  - Next immediate step
- Keep updates short and user-facing.

4. Completion
- Mark all must-have phases Done.
- Publish a final summary table and a short acceptance checklist.

## Done Criteria Template
Use this template per phase:
- Functional criteria: what must work
- Quality criteria: no regressions, stable behavior
- Validation criteria: tests/manual checks completed

## Standard Status Values
- Not Started
- In Progress
- Blocked
- Done

## Reusable 6-Phase Starter Model
1. Core engine correctness
2. Supporting backend capabilities
3. Primary UI structure
4. End-to-end workflow wiring
5. Secondary UX integrations
6. Verification and sign-off

## Must-have vs Nice-to-have Rule
- Must-have: required for user objective and acceptance.
- Nice-to-have: enhancements that do not block delivery.
- If scope is must-have only, exclude nice-to-have from active execution but keep as optional backlog.

## Safety and Clarity Guardrails
- Do not claim completion without verification evidence.
- Do not mark Done if any done criterion remains unmet.
- Avoid technical deep dives unless user asks.
- Keep terminology beginner-friendly.

## Suggested Tracker Row Example
| Phase | Scope | Status | Done Criteria |
|---|---|---|---|
| 1 | Core engine correctness | In Progress | Primary behavior works for agreed scenarios; no regressions in existing baseline; validation checks completed. |

## Notes for Cross-Project Reuse
- Keep this skill in personal scope so it can be used in any workspace.
- Reuse the same status vocabulary and table schema across projects for consistency.
