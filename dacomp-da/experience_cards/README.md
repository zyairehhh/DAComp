# DA Experience Cards

This folder stores reusable, atomic experience cards for DAComp-DA tasks.

## Design goals
- Generic and reusable across tasks (not task-specific cheat sheets).
- Retrieval-friendly (`when_to_use`, `keywords`, `tags`) for future indexing.
- Actionable in one short read during agent execution.

## Structure
- `index.json`: catalog with metadata used by the agent retriever.
- `cards/*.md`: one atomic experience per file.

## Authoring rules
- Keep each card focused on one subtask decision.
- Always include a clear `When to use` section.
- Include concrete checks or templates that can be executed quickly.
