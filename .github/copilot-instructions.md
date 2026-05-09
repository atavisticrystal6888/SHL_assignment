## Speckit Chat Agents

This workspace includes custom Copilot chat agents under `.github/agents` for the
core Spec Kit workflow.

When a user is asking for a specific Spec Kit phase, prefer the matching custom
agent instead of handling the workflow ad hoc:
- `speckit.constitution` for project principles and governance
- `speckit.specify` for feature specifications from natural-language requests
- `speckit.clarify` for targeted follow-up questions on ambiguous specs
- `speckit.plan` for technical planning, research, and design artifacts
- `speckit.checklist` for custom validation checklists
- `speckit.tasks` for dependency-ordered execution plans
- `speckit.analyze` for cross-artifact consistency review
- `speckit.implement` for executing the implementation plan

Use the normal workflow order `speckit.constitution` -> `speckit.specify` ->
`speckit.clarify` -> `speckit.plan` -> `speckit.tasks` ->
`speckit.analyze` -> `speckit.implement` unless the user explicitly skips a
stage. The Git helper agents support repository setup, branch creation,
validation, remotes, and commits around that flow.

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
specs/001-shl-assessment-recommender/plan.md
<!-- SPECKIT END -->
