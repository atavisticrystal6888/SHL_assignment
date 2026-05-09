# Feature Specification: Conversational SHL Assessment Recommender

**Feature Branch**: `001-shl-assessment-recommender`  
**Created**: 2026-05-09  
**Status**: Ready for Planning  
**Input**: User description: "Prepare an extensive specification documentation for the SHL AI Intern assignment: build a conversational SHL assessment recommender grounded in the SHL product catalog, exposed through a stateless FastAPI service, evaluated through replay traces, Recall@10, behavior probes, and submission materials."

## Problem Context & Evaluation Audience

Hiring managers and recruiters often begin assessment selection with uncertain language, partial role descriptions, or job-description excerpts rather than catalog-specific terminology. The feature must convert that conversational intent into a defensible SHL assessment shortlist without requiring the user to know product names, test categories, or filtering vocabulary.

The primary user is a hiring manager or recruiter selecting assessments for a role. Secondary audiences are the automated replay evaluator and manual reviewers who inspect whether the design, code, context engineering, and AI-assisted development choices are reliable and explainable.

The feature is successful only when it satisfies both user-facing needs and evaluator-facing constraints: helpful dialogue, grounded recommendations, exact schema compliance, catalog-only outputs, bounded conversation length, measurable Recall@10, and clear refusal behavior.

## Evaluation Model Summary

- **Hard evaluation gates**: Every response must satisfy the exact schema, every recommendation must come from the catalog, and each conversation must stay within 8 total turns.
- **Retrieval quality measure**: Final recommendation lists are evaluated with Mean Recall@10 across public and holdout traces where labeled expected assessments exist.
- **Behavior probes**: Small conversations check specific behaviors such as refusing off-topic requests, avoiding turn-1 recommendations for vague input, honoring user edits, grounding comparisons, resisting hallucination, and maintaining conversational coherence.
- **Manual review**: Reviewers assess whether the implementation demonstrates sound programming, problem decomposition, context engineering, agent-design judgment, and defensible use of AI tools.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clarify Vague Hiring Intent (Priority: P1)

A hiring manager or recruiter starts with an incomplete request such as "I need an assessment" or "I am hiring a Java developer." The agent must identify missing decision-critical information and ask targeted clarifying questions before producing any recommendation shortlist.

**Why this priority**: Clarification is required before the system can produce grounded recommendations. Recommending too early is explicitly evaluated and can fail behavior probes.

**Independent Test**: Can be fully tested by submitting a vague first user message to `POST /chat` and verifying that the response asks a relevant follow-up question, returns no recommendations, and keeps `end_of_conversation` false.

**Acceptance Scenarios**:

1. **Given** a user asks only for "an assessment", **When** the chat endpoint responds, **Then** the reply asks for role, skills, seniority, job context, or other decision-critical information and `recommendations` is empty.
2. **Given** a user provides a role but omits seniority and assessment focus, **When** the chat endpoint responds, **Then** the agent asks a concise clarifying question rather than guessing a final shortlist.
3. **Given** a user says it has no preference for a requested detail, **When** the conversation continues, **Then** the agent proceeds using the available facts and does not ask the same unresolved preference again.
4. **Given** the evaluator enforces an 8-turn cap, **When** the agent clarifies, **Then** each question must collect high-value information and avoid unnecessary back-and-forth.

---

### User Story 2 - Recommend a Grounded Shortlist (Priority: P1)

A hiring manager provides enough detail, such as a job description, role title, skill set, seniority, or workplace context. The agent returns a shortlist of 1 to 10 SHL Individual Test Solutions that match the hiring need, including catalog names, catalog URLs, and test types.

**Why this priority**: Producing a high-quality catalog-backed shortlist is the central value of the assignment and drives Recall@10 scoring.

**Independent Test**: Can be fully tested by submitting a complete hiring need and verifying that the response has the exact schema, includes 1 to 10 catalog-only recommendations, and contains no off-catalog names or URLs.

**Acceptance Scenarios**:

1. **Given** a user provides a job description for a mid-level Java developer who works with stakeholders, **When** the agent has enough context, **Then** it returns a concise reply and a shortlist containing only relevant catalog-backed assessments.
2. **Given** the final shortlist is returned, **When** each recommendation is inspected, **Then** every item includes at least `name`, `url`, and `test_type` copied or derived from a canonical catalog record.
3. **Given** more than 10 catalog matches are plausible, **When** the agent responds, **Then** it returns no more than 10 recommendations and prioritizes the strongest matches.
4. **Given** only one strong catalog match is available, **When** the agent responds, **Then** it may return a single recommendation rather than padding the list with weak matches.
5. **Given** a recommendation includes explanatory text in `reply`, **When** the response is reviewed, **Then** the explanation references the user need and catalog facts without inventing product properties.

---

### User Story 3 - Refine a Shortlist Mid-Conversation (Priority: P2)

A user changes constraints after receiving or approaching a shortlist, such as adding personality tests, excluding long assessments, or correcting the seniority level. The agent updates the recommendation set using the full conversation history and the latest user instruction.

**Why this priority**: Real conversations are non-linear. The evaluator may volunteer facts out of order or correct prior statements, and the assignment specifically requires refinement rather than restarting.

**Independent Test**: Can be fully tested by running a multi-turn conversation in which the user changes constraints and verifying that the next response reflects the updated constraints while retaining still-valid context.

**Acceptance Scenarios**:

1. **Given** a prior shortlist for a software developer, **When** the user says "Actually, add personality tests", **Then** the revised shortlist includes appropriate personality or behavior assessments where catalog facts support them.
2. **Given** the user corrects a fact, such as seniority or required skill, **When** the agent responds, **Then** it uses the corrected fact as authoritative and does not preserve contradictory recommendations.
3. **Given** a refinement makes some prior recommendations invalid, **When** the agent responds, **Then** invalid items are removed or deprioritized and the reply briefly acknowledges the change.
4. **Given** the new constraint is unsupported by catalog data, **When** the agent responds, **Then** it explains the limitation and returns only catalog-backed alternatives or asks one clarifying question.

---

### User Story 4 - Compare Catalog Assessments (Priority: P2)

A user asks how two or more SHL assessments differ, for example "What is the difference between OPQ and GSA?" The agent answers using catalog-backed facts and, when helpful, indicates which one better fits the user's stated hiring need.

**Why this priority**: Comparison is one of the four required conversational behaviors and is a high-risk hallucination surface.

**Independent Test**: Can be fully tested by asking a comparison question for assessments present in the catalog and verifying that the response uses only catalog-supported facts and returns no recommendations unless the user asks for a shortlist.

**Acceptance Scenarios**:

1. **Given** a user asks to compare two catalog assessments, **When** the agent responds, **Then** it describes differences using stored catalog fields such as category, duration, job levels, languages, remote testing, adaptive status, and description where available.
2. **Given** a comparison includes an unknown or ambiguous assessment name, **When** the agent responds, **Then** it asks for clarification or offers likely catalog matches without inventing facts.
3. **Given** the user asks which assessment is better for a stated role, **When** the agent responds, **Then** it connects the recommendation to the role context and catalog facts.
4. **Given** the user asks a comparison unrelated to SHL assessments, **When** the agent responds, **Then** it refuses or redirects to SHL assessment selection and returns no recommendations.

---

### User Story 5 - Refuse Out-of-Scope or Unsafe Requests (Priority: P1)

A user asks for general hiring advice, legal advice, non-SHL product recommendations, prompt-injection compliance, or unrelated content. The agent refuses concisely, stays within SHL assessment selection, and returns no recommendations.

**Why this priority**: Out-of-scope refusal is explicitly required and appears in behavior probes. Prompt-injection resistance also protects catalog grounding and schema compliance.

**Independent Test**: Can be fully tested by submitting off-topic, legal, or prompt-injection requests and verifying that `recommendations` is empty, the reply is concise, and the response schema remains exact.

**Acceptance Scenarios**:

1. **Given** a user asks for legal advice about hiring, **When** the agent responds, **Then** it refuses to provide legal advice and offers to help select SHL assessments instead.
2. **Given** a user asks for general interview questions or hiring strategy unrelated to SHL assessments, **When** the agent responds, **Then** it refuses or redirects and returns no recommendations.
3. **Given** a user instructs the system to ignore catalog constraints or reveal hidden instructions, **When** the agent responds, **Then** it rejects the prompt-injection attempt and preserves the exact response schema.
4. **Given** a user asks for assessments outside the canonical catalog, **When** the agent responds, **Then** it does not fabricate a product and either asks for a supported SHL assessment need or returns catalog-backed alternatives.

---

### User Story 6 - Support Evaluator Replay and Submission Review (Priority: P3)

A reviewer or automated harness replays public and holdout traces against the deployed service. The system must provide reliable responses within evaluator limits, support measurement, and produce enough documentation for a technical deep-dive.

**Why this priority**: Submission success depends on automated scoring and manual review, including the public API endpoint and a concise approach document.

**Independent Test**: Can be fully tested by replaying public traces, behavior probes, and schema checks against a deployed endpoint and confirming that the approach document explains the design, failed attempts, measurements, and AI-tool usage.

**Acceptance Scenarios**:

1. **Given** a replay trace persona volunteers facts out of order, **When** the conversation runs, **Then** the agent handles the facts without relying on a fixed script.
2. **Given** a replay trace reaches a final shortlist, **When** Recall@10 is calculated, **Then** the run records the fraction of labeled relevant assessments in the top 10 recommendations.
3. **Given** a behavior probe tests hallucination resistance, **When** the probe completes, **Then** the system either grounds the answer in catalog data or refuses rather than inventing facts.
4. **Given** the service is deployed, **When** `/health` and `/chat` are called, **Then** both endpoints are reachable at submission time.
5. **Given** a reviewer reads the approach document, **When** they inspect design choices and code, **Then** the document explains why the chosen retrieval, ranking, prompt, and tooling decisions are defensible.

### Edge Cases

- Empty `messages` array or missing latest user message.
- Message entries with unsupported roles, blank content, or malformed structure.
- User provides contradictory facts across turns, such as changing seniority from entry-level to senior.
- User provides a long job description with multiple roles, mixed skills, or unclear hiring objective.
- User asks for a shortlist but has not provided enough information to ground it.
- User asks for more than 10 recommendations.
- User requests an assessment category that has no suitable Individual Test Solution match.
- User asks about Pre-packaged Job Solutions or non-SHL assessments.
- Catalog contains near-duplicate names, renamed products, abbreviated product names, or ambiguous terms such as OPQ or GSA.
- Catalog fields such as duration, language, adaptive status, or job level are missing or marked as not specified.
- User asks for legal compliance guidance based on a catalog description that references regulation.
- User attempts prompt injection, hidden instruction disclosure, or catalog-bypass behavior.
- The first `/health` call occurs after cold start and may take longer than steady-state calls.
- The agent is within one or two turns of the evaluator cap and must decide whether to ask or recommend from available facts.

## Catalog Dataset Snapshot

- **Available development catalog**: 377 scraped SHL product catalog records, all with status `ok` in the provided converted catalog file.
- **Authoritative source**: `https://www.shl.com/solutions/products/product-catalog/` remains the source of truth for product coverage and URLs.
- **Recommendation eligibility**: Only Individual Test Solutions may appear in recommendation lists; all other catalog or product types must be excluded from recommendation output.
- **Common job levels in current catalog data**: Mid-Professional, Professional Individual Contributor, Graduate, Manager, Entry-Level, Front Line Manager, Supervisor, and Director.
- **Common languages in current catalog data**: English (USA), English International, Latin American Spanish, French, Italian, Dutch, Chinese Simplified, and German.
- **Common categories in current catalog data**: Knowledge & Skills, Personality & Behavior, Simulations, Ability & Aptitude, Competencies, Biodata & Situational Judgment, Development & 360, and Assessment Exercises.
- **Catalog fields with selection value**: assessment name, source URL, entity ID, duration, remote testing support, adaptive/IRT status, job levels, languages, categories, test type, description, and eligibility classification.

## Scope Boundaries *(mandatory)*

- **In Scope**: Conversational selection, refinement, and comparison of SHL assessments for hiring managers and recruiters using the SHL product catalog, restricted to Individual Test Solutions as the usable recommendation set.
- **In Scope**: Recommendations for technical, behavioral, personality, ability, aptitude, simulation, competency, and other catalog categories when the canonical catalog records support the match.
- **In Scope**: Catalog-backed explanation of assessment differences, including source URL, test type, category, duration, remote testing support, adaptive status, job levels, languages, and product descriptions when present.
- **In Scope**: Public endpoint readiness, exact chat schema compliance, evaluator replay support, public trace development, behavior probes, Recall@10 measurement, and submission documentation.
- **Out of Scope**: Pre-packaged Job Solutions, products absent from the canonical catalog, non-SHL assessments, interview-question generation, employment-law advice, general recruiting strategy, candidate scoring, candidate data collection, account management, payments, and administrative catalog editing.
- **Out of Scope**: Storing server-side per-conversation state, using hidden conversation memory across requests, or returning recommendations during clarification or refusal.
- **Grounding Rules**: Every recommendation name, URL, and test type must trace to a canonical catalog record. Every comparison fact must trace to catalog fields. The agent must not invent product capabilities, availability, regulatory interpretations, URLs, or test types.
- **Grounding Rules**: The catalog ingestion process must cover the entire available SHL product catalog and must record which products are eligible for recommendation as Individual Test Solutions.

## Context Engineering & Agent Decisions *(mandatory)*

- **User Goal Extraction**: The system must extract and update role title, job description text, required skills, seniority, years of experience, stakeholder needs, assessment focus, desired test categories, constraints, corrections, and explicit exclusions from the full message history.
- **Catalog Context**: The canonical context for retrieval, ranking, prompts, and comparisons must include assessment name, source URL, test type, categories, duration, remote testing support, adaptive/IRT status, job levels, languages, description, entity ID or equivalent stable identifier, and recommendation eligibility.
- **Decision Policy**: The agent must clarify when the current facts are too vague for a useful shortlist, retrieve and rank when there is enough role or job-description context, recommend only after commitment, refine when the user changes constraints, compare when the user asks about differences, refuse off-scope requests, and mark completion only when the task has been satisfied.
- **Conversation Variability**: The system must handle non-fixed replay behavior: facts may arrive out of order, the simulated user may correct itself, the user may decline preferences that are absent from its facts, and the user may end after receiving a shortlist.
- **Defensibility**: The design must document trade-offs for retrieval, ranking, prompt context, refusal handling, and tool usage. AI-assisted code or generated components must be reviewed and explained in the approach document.
- **Turn Budget Strategy**: Clarifying questions must be targeted and high-value so the conversation can complete within 8 total turns.
- **Completion Strategy**: `end_of_conversation` must remain false while clarifying, refusing, or waiting for the user's decision, and must be true only when the agent considers the assessment-selection task complete.

## API Contract & Evaluator Behavior *(mandatory)*

- **Health Check**: `GET /health` must return exactly `{"status": "ok"}` with HTTP 200.
- **Chat Request**: `POST /chat` must accept a stateless JSON body containing `messages`, where each message has `role` and `content`.
- **Chat Request**: Each `POST /chat` request must contain the complete conversation history needed for the next response; the service must not depend on prior server-side conversation state.
- **Chat Response**: `POST /chat` must return exactly `reply`, `recommendations`, and `end_of_conversation` as top-level response fields.
- **Recommendation Shape**: `recommendations` must be empty while clarifying or refusing. After the agent commits to a shortlist, it must contain 1 to 10 catalog-backed recommendation objects.
- **Recommendation Fields**: Each recommendation must include at least `name`, `url`, and `test_type`. Additional fields may be included only if they remain schema-compatible with the evaluator and are catalog-backed.
- **Evaluator Limits**: Conversations must fit within 8 total turns, including both user and assistant messages, and each chat request must complete within 30 seconds.
- **Cold Start**: The first health check may take up to 2 minutes on cold-start hosting, but steady-state chat responses must be engineered for the evaluator timeout.
- **Replay Behavior**: Requirements must account for users who volunteer facts out of order, correct themselves, answer from trace facts, say they have no preference when facts are absent, and end after receiving a shortlist.
- **Hard Failure Conditions**: Schema drift, off-catalog recommendations, more than 10 recommendations, non-empty recommendations during refusal or clarification, and reliance on server-side conversation state are submission-breaking failures.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System must expose a readiness endpoint that confirms service availability through the exact health-check response.
- **FR-002**: System must expose a chat endpoint that accepts a complete stateless conversation history and returns the next assistant reply.
- **FR-003**: System must validate incoming chat messages for required structure, supported roles, and usable content before generating an agent response.
- **FR-004**: System must preserve the exact top-level chat response schema: `reply`, `recommendations`, and `end_of_conversation`.
- **FR-005**: System must keep `recommendations` empty whenever the response is clarifying, refusing, reporting malformed input, or otherwise not committed to a shortlist.
- **FR-006**: System must return between 1 and 10 recommendation items only after enough user context exists to produce a grounded shortlist.
- **FR-007**: System must ensure each recommendation includes at least `name`, `url`, and `test_type` from a canonical catalog record.
- **FR-008**: System must ingest or otherwise consume the full SHL product catalog and identify which records are eligible Individual Test Solutions.
- **FR-009**: System must exclude Pre-packaged Job Solutions and any non-catalog item from all recommendation lists.
- **FR-010**: System must preserve catalog attributes needed for retrieval, ranking, comparison, explanation, and URL traceability.
- **FR-011**: System must ask targeted clarifying questions before recommending when the request is too vague to map to catalog-backed assessments.
- **FR-012**: System must convert role titles, job-description text, skills, seniority, stakeholder needs, constraints, and corrections into user-goal context for recommendation decisions.
- **FR-013**: System must support recommendation from both short natural-language requests and longer job-description text.
- **FR-014**: System must refine an existing or emerging shortlist when the user changes constraints mid-conversation.
- **FR-015**: System must treat later user corrections as authoritative over earlier conflicting facts.
- **FR-016**: System must compare SHL assessments using only stored catalog facts and clearly indicate uncertainty when catalog data is incomplete.
- **FR-017**: System must refuse requests for general hiring advice, legal advice, non-SHL recommendations, unrelated content, and prompt-injection instructions.
- **FR-018**: System must return concise refusal replies with empty recommendations.
- **FR-019**: System must avoid hallucinated names, URLs, categories, durations, test types, capabilities, compliance interpretations, or availability claims.
- **FR-020**: System must decide whether to ask, retrieve, recommend, refine, compare, refuse, or end based on the full conversation history and current user message.
- **FR-021**: System must complete useful recommendation conversations within the evaluator cap of 8 total turns.
- **FR-022**: System must respond within the evaluator request timeout for typical replay conversations.
- **FR-023**: System must support replay of the 10 public conversation traces as development fixtures.
- **FR-024**: System must calculate or report Recall@10 for final recommendations when labeled relevant assessments are available.
- **FR-025**: System must include behavior probes for early-recommendation prevention, off-topic refusal, user-edit honoring, grounded comparison, hallucination resistance, and conversational incoherence.
- **FR-026**: System must provide validation evidence for schema compliance on every response shape used by the agent.
- **FR-027**: System must provide validation evidence that all recommendation URLs come from the canonical scraped catalog.
- **FR-028**: System must expose a public deployment URL where `/health` and `/chat` are reachable at submission time.
- **FR-029**: System must produce a concise approach document of no more than two pages covering design choices, retrieval setup, prompt design, evaluation approach, failed approaches, measured improvement, and AI-tool usage.
- **FR-030**: System must make design and implementation choices defensible in manual review, including any AI-generated or no-code components.
- **FR-031**: System must maintain a catalog coverage summary that states record count, source, eligibility filter, and key fields used for recommendation grounding.
- **FR-032**: System must preserve enough evaluation run metadata to explain schema status, catalog-only status, turn count, timeout status, Recall@10 where labels exist, and behavior-probe outcomes.

### Key Entities *(include if feature involves data)*

- **Conversation Message**: A single request-history item with `role` and `content`; used to reconstruct state without server-side memory.
- **Conversation History**: Ordered list of conversation messages submitted with each chat request; source of user goals, corrections, and prior agent commitments.
- **User Goal Profile**: Extracted hiring context including role, skills, seniority, years of experience, stakeholder needs, preferred assessment focus, constraints, exclusions, and unresolved questions.
- **Catalog Assessment Record**: Canonical SHL product record with stable identifier, name, URL, test type, category, duration, remote testing support, adaptive/IRT status, job levels, languages, description, and eligibility status.
- **Recommendation Item**: Response object derived from a catalog assessment record and containing at least `name`, `url`, and `test_type`.
- **Clarification Question**: Targeted question used to collect missing high-value facts before recommending.
- **Comparison Answer**: Catalog-grounded explanation of differences between assessments, optionally tied to the user's hiring context.
- **Refusal Response**: In-scope boundary response for unsupported, unsafe, legal, general hiring, prompt-injection, or non-SHL requests; always has empty recommendations.
- **Conversation Trace**: Public or holdout evaluation scenario with persona facts and labeled expected shortlist.
- **Behavior Probe**: Small conversation with a binary assertion for a required behavior such as refusing off-topic requests or avoiding hallucination.
- **Evaluation Run**: Replay result containing schema status, catalog-only status, turn count, timeout status, final recommendations, Recall@10 where labels exist, and behavior-probe outcomes.
- **Approach Document**: Two-page submission artifact explaining design, retrieval, prompts, evaluation, failed attempts, measured improvements, and AI-tool use.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of `/health` checks return `{"status": "ok"}` with HTTP 200 after the service is awake.
- **SC-002**: 100% of tested chat responses contain exactly the required top-level fields: `reply`, `recommendations`, and `end_of_conversation`.
- **SC-003**: 100% of clarification, refusal, malformed-input, or out-of-scope responses return an empty `recommendations` array.
- **SC-004**: 100% of committed shortlist responses return between 1 and 10 recommendations.
- **SC-005**: 100% of recommendation items in evaluated responses match canonical catalog records by name and URL.
- **SC-006**: 100% of returned recommendation URLs come from the scraped SHL catalog.
- **SC-007**: 100% of public trace replay conversations complete within 8 total turns.
- **SC-008**: 95% of steady-state chat requests in replay and probe runs complete within 30 seconds.
- **SC-009**: The first cold-start health check completes within 2 minutes on the selected deployment platform.
- **SC-010**: Mean Recall@10 is measured across all public traces with labeled expected shortlists and is tracked after each ranking or prompt change.
- **SC-011**: Public-trace Mean Recall@10 improves or remains stable after each intentional retrieval, ranking, or prompt change.
- **SC-012**: Behavior probes pass for off-topic refusal, no turn-1 recommendation on vague input, honoring user edits, grounded comparison, hallucination resistance, and conversational incoherence.
- **SC-013**: At least one regression test or probe covers each changed agent decision path before the feature is marked ready for planning completion.
- **SC-014**: The approach document is no more than 2 pages and covers design choices, retrieval setup, prompt design, evaluation approach, failed approaches, measured improvement, and AI-tool usage.
- **SC-015**: A reviewer can trace each final recommendation and comparison claim back to canonical catalog fields without relying on model prior knowledge.
- **SC-016**: Catalog coverage documentation states the ingested record count, source URL, eligible recommendation filter, and fields used for grounding before implementation is considered ready for submission.

## Quality Attributes

- **Reliability**: The service must preserve schema compliance and refusal behavior across malformed input, vague input, off-topic input, and multi-turn correction scenarios.
- **Groundedness**: Recommendation and comparison outputs must be traceable to canonical catalog records rather than model memory or inferred product facts.
- **Conversation Efficiency**: Clarifying questions must collect enough information to support a useful shortlist within the 8-turn evaluator cap.
- **Explainability**: Ranking choices, prompt context, retrieval inputs, refusal decisions, and failed approaches must be explainable in the approach document and technical review.
- **Operational Readiness**: The deployed service must be reachable, handle cold-start health checks, and respond to typical evaluator calls within timeout expectations.
- **Maintainability**: Catalog ingestion, context extraction, ranking, refusal, and evaluation logic must remain separable enough that changes can be tested without destabilizing unrelated agent behavior.

## Assumptions

- The provided scraped catalog contains 377 SHL product catalog records and is available as a development source, while the public SHL catalog remains the authoritative source for catalog coverage.
- The usable recommendation set must be restricted to Individual Test Solutions even if the raw product catalog includes broader product types or development-focused offerings.
- Public conversation traces are available separately and can be loaded as development fixtures before implementation.
- The service is intended for hiring managers and recruiters selecting assessments, not for candidates taking assessments.
- The system does not need user accounts, persistent conversation storage, candidate records, payment workflows, or administrative catalog-management screens.
- The response schema may include extra recommendation fields only if future evaluator guidance allows them; the minimum required recommendation fields are `name`, `url`, and `test_type`.
- When catalog data is missing or ambiguous, the system must disclose uncertainty, ask a clarifying question, or avoid the unsupported claim rather than inventing details.
- Free LLM tiers, deployment platforms, vector stores, agent frameworks, raw model SDKs, or no-code tools may be used if they are justified in the approach document.
- Legal or regulatory references appearing in product descriptions are catalog facts, not legal advice; the agent must not interpret them as legal guidance.
- Development will prioritize evaluator reliability and defensible code over broad feature breadth.
