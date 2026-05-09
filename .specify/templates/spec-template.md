# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`  
**Created**: [DATE]  
**Status**: Draft  
**Input**: User description: "$ARGUMENTS"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently - e.g., "Can be fully tested by [specific action] and delivers [specific value]"]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 3 - [Brief Title] (Priority: P3)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- What happens when [boundary condition]?
- How does system handle [error scenario]?

## Scope Boundaries *(mandatory)*

<!--
  ACTION REQUIRED: State the boundaries that keep the feature grounded.
  For this project, be explicit about allowed SHL data sources, prohibited
  recommendations, and any off-topic or refusal behavior.
-->

- **In Scope**: [Identify the allowed SHL catalog slice and supported user intents]
- **Out of Scope**: [List excluded offerings, unsupported advice, and refusal cases]
- **Grounding Rules**: [State which claims, URLs, and comparisons must trace to canonical catalog records]

## Context Engineering & Agent Decisions *(mandatory)*

<!--
  ACTION REQUIRED: Define how the agent uses the catalog, the user's goal, and
  the conversation history. The assignment evaluates whether the agent knows
  when to ask, retrieve, answer, recommend, refine, compare, refuse, and finish.
-->

- **User Goal Extraction**: [State how role, skills, seniority, constraints, and corrections are captured from messages]
- **Catalog Context**: [State which canonical catalog fields feed retrieval, ranking, prompts, and comparisons]
- **Decision Policy**: [State when the agent clarifies, retrieves, recommends, refines, compares, refuses, or ends]
- **Conversation Variability**: [State how the feature handles out-of-order facts, corrections, missing preferences, and non-fixed replay scripts]
- **Defensibility**: [State how design choices, AI-assisted code, and failed approaches will be explained and measured]

## API Contract & Evaluator Behavior *(mandatory)*

<!--
  ACTION REQUIRED: Fill this section with the externally visible API and
  evaluator behavior required by the assignment. Keep it declarative and
  testable.
-->

- **Health Check**: `GET /health` MUST return `{"status": "ok"}` with HTTP 200.
- **Chat Request**: `POST /chat` MUST accept a stateless `messages` array containing the full conversation history.
- **Chat Response**: `POST /chat` MUST return exactly `reply`, `recommendations`, and `end_of_conversation`.
- **Recommendation Shape**: Recommendations MUST be empty while clarifying or refusing, and MUST contain 1 to 10 catalog-backed items with `name`, `url`, and `test_type` after commitment.
- **Evaluator Limits**: Conversations MUST fit within 8 total turns and each request MUST fit within 30 seconds.
- **Replay Behavior**: Requirements MUST account for users who volunteer facts out of order, correct themselves, or decline to provide preferences absent from their facts.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST [specific capability, e.g., "allow users to create accounts"]
- **FR-002**: System MUST [specific capability, e.g., "validate email addresses"]  
- **FR-003**: Users MUST be able to [key interaction, e.g., "reset their password"]
- **FR-004**: System MUST [data requirement, e.g., "persist user preferences"]
- **FR-005**: System MUST [behavior, e.g., "log all security events"]
- **FR-006**: System MUST [state how the feature preserves grounded responses and scope compliance]
- **FR-007**: System MUST [state how the feature ingests and filters the entire SHL catalog]
- **FR-008**: System MUST [state how the feature supports clarification, recommendation, refinement, and comparison behavior]
- **FR-009**: System MUST [state how the feature refuses off-topic, legal, general hiring advice, and prompt-injection attempts]
- **FR-010**: System MUST [state how catalog data, user goals, and conversation history are transformed into retrieval and prompt context]
- **FR-011**: System MUST [state the decision policy for asking, retrieving, recommending, refining, comparing, ending, and refusing]

*Example of marking unclear requirements:*

- **FR-012**: System MUST handle missing seniority by [NEEDS CLARIFICATION: default behavior not specified - ask follow-up or proceed with broad shortlist?]
- **FR-013**: System MUST use [NEEDS CLARIFICATION: retrieval and LLM approach not specified - raw SDK, framework, vector search, or keyword search?]

### Key Entities *(include if feature involves data)*

- **[Entity 1]**: [What it represents, key attributes without implementation]
- **[Entity 2]**: [What it represents, relationships to other entities]

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: [Measurable metric, e.g., "Users can complete account creation in under 2 minutes"]
- **SC-002**: [Measurable metric, e.g., "System handles 1000 concurrent users without degradation"]
- **SC-003**: [User satisfaction metric, e.g., "90% of users successfully complete primary task on first attempt"]
- **SC-004**: [Business metric, e.g., "Reduce support tickets related to [X] by 50%"]
- **SC-005**: [Evaluator metric, e.g., "All responses pass exact schema validation"]
- **SC-006**: [Retrieval metric, e.g., "Mean Recall@10 improves against public conversation traces"]
- **SC-007**: [Behavior metric, e.g., "All probes for hallucination resistance and conversational incoherence pass"]
- **SC-008**: [Review metric, e.g., "Approach document explains design trade-offs, failed approaches, measurements, and AI-tool use"]

## Assumptions

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right assumptions based on reasonable defaults
  chosen when the feature description did not specify certain details.
-->

- [Assumption about target users, e.g., "Users have stable internet connectivity"]
- [Assumption about scope boundaries, e.g., "Mobile support is out of scope for v1"]
- [Assumption about data/environment, e.g., "Existing authentication system will be reused"]
- [Dependency on existing system/service, e.g., "Requires access to the existing user profile API"]
