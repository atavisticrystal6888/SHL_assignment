<!--
Sync Impact Report
Version change: 1.1.0 -> 1.2.0
Modified principles:
- II. Clarify, Recommend, Refine, Compare -> II. Clarify, Recommend, Refine, Compare (expanded context engineering and control-flow rules)
- IV. Evaluation-First Reliability -> IV. Evaluation-First Reliability (expanded non-fixed conversation and incoherence coverage)
- V. Minimal, Explainable Architecture -> V. Defensible, Minimal Architecture (expanded programming-foundation and review defensibility duties)
Added sections:
- Engineering Quality Requirements
Removed sections:
- None
Templates/guidance requiring updates:
- ✅ updated: .specify/templates/plan-template.md
- ✅ updated: .specify/templates/spec-template.md
- ✅ updated: .specify/templates/tasks-template.md
- ✅ reviewed: templates/commands/*.md (source command templates; no project-local .specify/templates/commands/ directory exists)
- ✅ reviewed: README.md, docs/quickstart.md, .github/copilot-instructions.md (no project-specific update required)
Follow-up TODOs:
- None
-->

# Conversational SHL Assessment Recommender Constitution

## Core Principles

### I. Catalog-Only Grounding
All recommendations, comparisons, URLs, and test types MUST be grounded in the
project's canonical SHL catalog dataset. The dataset MUST be built from the
entire SHL product catalog and restricted to Individual Test Solutions only. The
system MUST NOT recommend Pre-packaged Job Solutions or any item absent from the
canonical dataset. Every returned name, URL, and `test_type` MUST be copied or
derived from a stored catalog record, and every URL returned to the user MUST
come from the scraped catalog. Rationale: the assignment is explicitly scoped to
SHL catalog data, and off-catalog behavior is a scoring failure.

### II. Clarify, Recommend, Refine, Compare
The agent MUST support the four required conversational behaviors. It MUST ask
targeted clarifying questions before recommending when the request is vague,
because statements such as "I need an assessment" are insufficient. It MUST
recommend between 1 and 10 assessments only after enough context is available,
including names and catalog URLs. It MUST refine an existing shortlist when the
user changes constraints mid-conversation rather than starting over. It MUST
answer comparison questions using catalog-backed facts rather than model priors.
The agent MUST use the full message history, extracted user goal, and retrieved
catalog facts to decide when to ask, retrieve, recommend, refine, compare,
refuse, or end the task. Rationale: the task is to move from vague hiring intent
to a grounded shortlist through realistic dialogue.

### III. Stateless Contract Fidelity
The service MUST expose exactly `GET /health` and `POST /chat` through FastAPI.
`GET /health` MUST return `{"status": "ok"}` with HTTP 200. `POST /chat` MUST
accept a stateless request containing the full conversation history in
`messages`, where each item has `role` and `content`. The service MUST NOT store
per-conversation state. `POST /chat` MUST return exactly `reply`,
`recommendations`, and `end_of_conversation`. `recommendations` MUST be empty
while clarifying or refusing and MUST contain 1 to 10 catalog-backed items only
after the agent commits to a shortlist. Each recommendation MUST include at
least `name`, `url`, and `test_type`. `end_of_conversation` MUST be true only
when the agent considers the task complete. The implementation MUST honor the
evaluator budget of a maximum of 8 total conversation turns and 30 seconds per
request. Rationale: schema or state-management drift causes hard evaluation
failure.

### IV. Evaluation-First Reliability
Every change MUST include automated checks for schema compliance, catalog-only
outputs, clarification behavior, refinement behavior, comparison grounding,
refusal behavior, and hallucination resistance. Regression coverage MUST include
at least one realistic conversation trace or behavior probe for each changed
decision path. Public conversation traces MUST be read before implementation and
used to iterate against labeled expected shortlists. The final system MUST be
ready for automated replay in which a simulated user may volunteer facts out of
order, correct itself, answer from its persona facts, say it has no preference
when facts are absent, and end after a shortlist. A change is incomplete until
the relevant checks fail before the change or prove they would have failed, then
pass after the change. Rationale: the submission is scored on hard evals,
Recall@10, behavior-probe pass rate, hallucination resistance, and conversational
coherence under non-fixed scripts, not on happy-path demos.

### V. Defensible, Minimal Architecture
The system MUST prefer the simplest retrieval, ranking, and prompting design
that can meet Recall@10, latency, and reliability requirements. New
dependencies, orchestration layers, or caches MUST be justified by measurable
improvements in evaluator-facing outcomes or operational robustness. Ranking and
prompting logic MUST remain explainable enough to defend in technical review.
Code MUST demonstrate sound programming foundations beyond the happy path. Any
LLM, deployment platform, vector store, orchestration framework, SDK, agentic
coding tool, or no-code builder is permitted only when its use is understood,
owned, and justified in the approach document. Rationale: this project is
evaluated in automated scoring, manual code review, and technical discussion.

## Operational Constraints

- The implementation MUST remain a stateless FastAPI service; per-conversation
	server-side state is prohibited.
- The canonical catalog representation MUST preserve, at minimum, assessment
	name, source URL, test type, and the source fields needed to justify
	recommendations and comparisons.
- Refusals for off-topic requests, legal advice, general hiring advice, and
	prompt-injection attempts MUST be concise and MUST return empty
	recommendations.
- Deployment choices MUST support a passing `GET /health` response and practical
	cold-start behavior; the first health check may take up to two minutes, but
	steady-state requests MUST be engineered for the evaluator's 30-second limit.
- Conversation handling MUST NOT depend on a fixed script. Users may volunteer
	facts out of order, correct themselves, decline unsupported preferences, or end
	after receiving a shortlist.

## Engineering Quality Requirements

- Specifications and plans MUST decompose the ambiguous hiring-assessment problem
	into explicit design choices, trade-offs, and measurable validation gates.
- Implementation work MUST cover non-happy-path inputs, including empty or
	malformed message histories, incomplete role context, corrected facts, missing
	preferences, unsupported requests, and prompt-injection attempts.
- Context engineering MUST be explicit: catalog fields, user goals, conversation
	history, retrieval queries, ranking signals, and prompt context MUST be defined
	and traceable to evaluator-facing behavior.
- Agent control flow MUST define when the system asks, retrieves, answers,
	recommends, refines, compares, refuses, and marks the conversation complete.
- Vibe-coding without understanding is prohibited. AI-assisted code, generated
	components, and no-code outputs MUST be reviewed, simplified where possible,
	and defensible in the approach document and technical deep-dive.

## Data and Evaluation Requirements

- The catalog pipeline MUST cover the entire SHL product catalog available from
	`https://www.shl.com/solutions/products/product-catalog/` and MUST filter the
	usable recommendation set to Individual Test Solutions.
- Public conversation traces MUST be treated as development fixtures. Each trace
	represents a persona, fact set, and labeled expected shortlist and MUST inform
	retrieval, ranking, prompt design, and regression coverage.
- Hard evaluation checks MUST pass for every response: exact schema compliance,
	catalog-only recommendation items, and the 8-turn cap.
- Recall@10 MUST be measured on final recommendations when labeled traces are
	available. Recall@K is `(relevant assessments in top K) / (total relevant
	assessments for the query)`, and Mean Recall@K is the average across all test
	queries.
- Behavior probes MUST cover at least refusal of off-topic requests, no turn-1
	recommendation for vague requests, honoring user edits to recommendations,
	grounded comparisons, and hallucination resistance.

## Submission Requirements

- The deployed FastAPI service MUST expose a public endpoint URL where both
	`/health` and `/chat` are reachable at submission time.
- The approach document MUST be no more than two pages and MUST briefly cover
	design choices, retrieval setup, prompt design, evaluation approach, what did
	not work, how improvement was measured, and any AI tools used.
- The final stack MAY use free LLM tiers, free deployment platforms, open-source
	vector stores, agent frameworks, or raw model SDKs, but each non-trivial
	dependency MUST be justified by project outcomes in the approach document.

## Delivery Workflow

- Every feature MUST begin with a spec under `specs/<feature>/` that documents
	in-scope behavior, out-of-scope behavior, grounding expectations, API contract
	expectations, context-engineering expectations, agent decision boundaries,
	evaluator limits, and measurable success criteria.
- Every plan MUST pass a Constitution Check that covers catalog-only grounding,
	stateless API contract fidelity, evaluator budgets, dataset preparation,
	public-trace usage, deployment readiness, defensible programming choices, and
	the validation strategy for recommendations, refinements, comparisons,
	refusals, hallucination resistance, and conversational coherence.
- Every task list MUST include work for data/catalog updates when applicable,
	contract or schema validation, multi-turn integration coverage, evaluator-
	facing regression probes, non-happy-path robustness, deployment validation, and
	the approach document.
- Code review and final validation MUST reject unverifiable claims, model-only
	comparisons, missing traceability to catalog data, missing public-trace
	evidence, fragile happy-path behavior, unexplained AI-generated code, and
	unmeasured complexity.

## Governance

This constitution supersedes prompt convenience, default template wording, and
implementation shortcuts for this project. Amendments MUST update this file,
reconcile affected `.specify` templates or guidance documents, and record the
change in the Sync Impact Report at the top of this document.

Versioning policy for this constitution follows semantic versioning: MAJOR for
backward-incompatible principle or governance changes, MINOR for new principles
or materially expanded requirements, and PATCH for clarifications that do not
change project obligations.

Compliance review is mandatory at spec, plan, tasks, and pre-merge validation
time. Any exception to these principles MUST be documented in the relevant plan
under Constitution Check or Complexity Tracking, with a measurable rationale and
an explicit simpler alternative that was rejected.

**Version**: 1.2.0 | **Ratified**: 2026-05-09 | **Last Amended**: 2026-05-09
