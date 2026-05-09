# Tasks: Conversational SHL Assessment Recommender

**Input**: Design documents from `/specs/001-shl-assessment-recommender/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/openapi.yaml](contracts/openapi.yaml), [quickstart.md](quickstart.md)

**Tests**: Required. The specification and local tasks template require contract, integration, replay, and behavior-probe coverage for evaluator-facing behavior.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently after shared foundation work is complete.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches a different file or has no dependency on incomplete tasks
- **[Story]**: User story label for story-phase tasks only
- **File paths**: Every task names the exact file or directory path to create or modify

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the FastAPI project skeleton, dependency entry points, configuration, and deployment placeholders.

- [X] T001 Create project directories `app/`, `app/api/`, `app/catalog/`, `app/conversation/`, `app/retrieval/`, `app/llm/`, `app/evaluation/`, `data/raw/`, `data/processed/`, `data/traces/public/`, `tests/contract/`, `tests/integration/`, `tests/unit/`, `docs/`, and `scripts/`
- [X] T002 Update `pyproject.toml` with FastAPI, Pydantic v2, Uvicorn, httpx, scikit-learn, beautifulsoup4, lxml, and required pytest dependencies
- [X] T003 [P] Create package marker files in `app/__init__.py`, `app/api/__init__.py`, `app/catalog/__init__.py`, `app/conversation/__init__.py`, `app/retrieval/__init__.py`, `app/llm/__init__.py`, and `app/evaluation/__init__.py`
- [X] T004 [P] Add runtime configuration example in `.env.example`
- [X] T005 [P] Add Render deployment skeleton in `render.yaml`
- [X] T006 [P] Create approach document outline in `docs/approach.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared catalog, API schema, validation, retrieval, and test infrastructure required by all user stories.

**Critical**: No user story implementation should begin until this phase is complete.

- [X] T007 Copy the provided SHL catalog source into `data/raw/shl_product_catalog.json`
- [X] T008 [P] Define `CatalogAssessment` and `CatalogCoverageSummary` models in `app/catalog/models.py`
- [X] T009 Implement catalog normalization, explicit eligibility-source mapping, and Individual Test Solution filtering in `app/catalog/ingest.py`
- [X] T010 Generate the processed canonical catalog artifact in `data/processed/catalog.json`
- [X] T011 Generate catalog coverage metadata in `data/processed/catalog_coverage.json`
- [X] T012 Implement read-only catalog loading, URL membership checks, and name lookup in `app/catalog/repository.py`
- [X] T013 [P] Define `ConversationMessage`, `ChatRequest`, `Recommendation`, and `ChatResponse` schemas in `app/api/schemas.py`
- [X] T014 Implement exact response-schema, catalog-only validation helpers, and `/chat` validation-error normalization in `app/api/validators.py`
- [X] T015 [P] Implement environment and path settings in `app/settings.py`
- [X] T016 [P] Add FastAPI app skeleton with `GET /health`, `POST /chat`, disabled default docs routes, and dispatch stubs in `app/main.py`
- [X] T017 Copy public trace fixtures `Documents/GenAI_SampleConversations/C1.md` through `Documents/GenAI_SampleConversations/C10.md` into `data/traces/public/`
- [X] T018 [P] Implement public trace fixture discovery skeleton in `app/evaluation/replay.py`
- [X] T019 [P] Implement TF-IDF index construction over canonical catalog fields in `app/retrieval/index.py`
- [X] T020 Implement initial ranking pipeline with eligibility filtering and deterministic tie-breaking in `app/retrieval/ranker.py`
- [X] T021 [P] Define optional LLM adapter interface with deterministic no-key fallback in `app/llm/client.py`
- [X] T022 [P] Define grounded prompt templates and prompt context limits in `app/llm/prompts.py`
- [X] T023 [P] Add foundational catalog, Pre-packaged exclusion, eligibility-default, schema, and malformed-chat tests in `tests/unit/test_catalog_normalization.py` and `tests/unit/test_api_schemas.py`

**Checkpoint**: Foundation ready. User stories can now be implemented in priority order or in parallel by separate contributors.

---

## Phase 3: User Story 1 - Clarify Vague Hiring Intent (Priority: P1) MVP

**Goal**: For incomplete requests, ask a targeted clarification question, return no recommendations, and keep the conversation open.

**Independent Test**: Submit a vague first user message to `POST /chat`; verify the response asks for decision-critical context, `recommendations` is empty, and `end_of_conversation` is false.

### Tests for User Story 1

- [X] T024 [P] [US1] Add contract tests for vague-request and malformed-input empty recommendations in `tests/contract/test_us1_clarification_contract.py`
- [X] T025 [P] [US1] Add integration tests for vague role and missing seniority flows in `tests/integration/test_us1_clarification.py`
- [X] T026 [P] [US1] Add no-turn-1-recommendation behavior probe in `tests/integration/test_us1_clarification_probe.py`
- [X] T027 [P] [US1] Add user-goal extraction unit tests for missing factors in `tests/unit/test_goal_extraction.py`

### Implementation for User Story 1

- [X] T028 [US1] Implement vague-goal extraction and missing-decision-factor detection in `app/conversation/extractor.py`
- [X] T029 [US1] Implement clarify action selection in `app/conversation/policy.py`
- [X] T030 [US1] Implement concise clarification response rendering in `app/conversation/renderer.py`
- [X] T031 [US1] Wire the `/chat` clarification flow through `app/main.py`

**Checkpoint**: User Story 1 is independently testable as the first MVP increment.

---

## Phase 4: User Story 2 - Recommend a Grounded Shortlist (Priority: P1)

**Goal**: Return 1 to 10 catalog-backed SHL Individual Test Solutions with `name`, `url`, and `test_type` when enough hiring context exists.

**Independent Test**: Submit a complete hiring need to `POST /chat`; verify exact schema, 1 to 10 recommendations, catalog-only names and URLs, and no fabricated product fields.

### Tests for User Story 2

- [X] T032 [P] [US2] Add contract tests for committed shortlist shape in `tests/contract/test_us2_recommendation_contract.py`
- [X] T033 [P] [US2] Add integration tests for a complete Java developer hiring need in `tests/integration/test_us2_grounded_recommendation.py`
- [X] T034 [P] [US2] Add catalog-only, Individual Test Solution eligibility, Pre-packaged exclusion, and no-padding behavior probe in `tests/integration/test_us2_catalog_grounding_probe.py`
- [X] T035 [P] [US2] Add ranking and top-10 selection unit tests in `tests/unit/test_ranking.py`

### Implementation for User Story 2

- [X] T036 [US2] Implement retrieval query construction from extracted user goals in `app/retrieval/query.py`
- [X] T037 [US2] Implement recommendation scoring, category boosts, and top-10 selection in `app/retrieval/ranker.py`
- [X] T038 [US2] Implement recommendation item rendering with catalog `name`, `url`, and `test_type` in `app/conversation/renderer.py`
- [X] T039 [US2] Implement recommend action selection and confidence thresholds in `app/conversation/policy.py`
- [X] T040 [US2] Wire retrieval and recommendation flow through `app/main.py`

**Checkpoint**: User Story 2 can produce evaluator-safe recommendations independently of later refinement and comparison work.

---

## Phase 5: User Story 5 - Refuse Out-of-Scope or Unsafe Requests (Priority: P1)

**Goal**: Refuse or redirect off-topic, legal, non-SHL, and prompt-injection requests while preserving exact schema and empty recommendations.

**Independent Test**: Submit off-topic, legal, non-SHL, and prompt-injection requests to `POST /chat`; verify concise refusal or redirect, empty recommendations, and exact top-level schema.

### Tests for User Story 5

- [X] T041 [P] [US5] Add contract tests for refusal responses with empty recommendations in `tests/contract/test_us5_refusal_contract.py`
- [X] T042 [P] [US5] Add integration tests for legal, general hiring, and non-SHL requests in `tests/integration/test_us5_refusal.py`
- [X] T043 [P] [US5] Add prompt-injection resistance behavior probe in `tests/integration/test_us5_prompt_injection_probe.py`

### Implementation for User Story 5

- [X] T044 [US5] Implement out-of-scope and prompt-injection intent detection in `app/conversation/policy.py`
- [X] T045 [US5] Implement safe refusal and redirect response rendering in `app/conversation/renderer.py`
- [X] T046 [US5] Add refusal-specific response validation in `app/api/validators.py`
- [X] T047 [US5] Wire refusal flow through `app/main.py`

**Checkpoint**: User Story 5 protects catalog grounding and schema compliance before more advanced conversation behaviors are added.

---

## Phase 6: User Story 3 - Refine a Shortlist Mid-Conversation (Priority: P2)

**Goal**: Update recommendations when the user adds constraints, removes an item, or corrects earlier facts, using only the submitted full conversation history.

**Independent Test**: Submit a multi-turn history where the user changes constraints after a shortlist; verify the revised response honors the latest instruction and keeps still-valid context.

### Tests for User Story 3

- [X] T048 [P] [US3] Add contract tests for multi-turn refinement response shape in `tests/contract/test_us3_refinement_contract.py`
- [X] T049 [P] [US3] Add integration tests for adding personality tests and dropping OPQ in `tests/integration/test_us3_refinement.py`
- [X] T050 [P] [US3] Add user-edit and correction behavior probe in `tests/integration/test_us3_user_edits_probe.py`

### Implementation for User Story 3

- [X] T051 [US3] Implement correction, exclusion, and constraint extraction in `app/conversation/extractor.py`
- [X] T052 [US3] Implement refine action selection and prior-shortlist interpretation in `app/conversation/policy.py`
- [X] T053 [US3] Apply exclusions, duration preferences, category additions, and corrected facts in `app/retrieval/ranker.py`
- [X] T054 [US3] Render acknowledgement and revised shortlist responses in `app/conversation/renderer.py`
- [X] T055 [US3] Wire full-history refinement flow through `app/main.py`

**Checkpoint**: User Story 3 can be validated without server-side conversation state.

---

## Phase 7: User Story 4 - Compare Catalog Assessments (Priority: P2)

**Goal**: Answer comparison questions using only catalog-backed facts and avoid recommendations unless the user asks for a shortlist.

**Independent Test**: Ask a comparison question for catalog assessments such as OPQ and GSA; verify the response uses stored fields and returns empty recommendations unless a shortlist is requested.

### Tests for User Story 4

- [X] T056 [P] [US4] Add contract tests for comparison responses without unintended recommendations in `tests/contract/test_us4_comparison_contract.py`
- [X] T057 [P] [US4] Add integration tests for OPQ, GSA, and ambiguous assessment comparisons in `tests/integration/test_us4_comparison.py`
- [X] T058 [P] [US4] Add hallucination-resistance comparison probe in `tests/integration/test_us4_hallucination_probe.py`

### Implementation for User Story 4

- [X] T059 [US4] Implement assessment alias and ambiguity resolution in `app/catalog/repository.py`
- [X] T060 [US4] Implement comparison intent and target extraction in `app/conversation/extractor.py`
- [X] T061 [US4] Implement compare action selection in `app/conversation/policy.py`
- [X] T062 [US4] Render catalog-grounded comparison answers in `app/conversation/renderer.py`
- [X] T063 [US4] Wire comparison flow through `app/main.py`

**Checkpoint**: User Story 4 is testable as a read-only catalog-grounded answer path.

---

## Phase 8: User Story 6 - Support Evaluator Replay and Submission Review (Priority: P3)

**Goal**: Provide replay, metrics, behavior-probe execution, deployment validation, and approach documentation for automated and manual review.

**Independent Test**: Run public trace replay, behavior probes, schema/catalog checks, and deployment health checks; verify the approach document reflects actual implementation and measurements.

### Tests for User Story 6

- [X] T064 [P] [US6] Add health, exact-route exposure, default-docs-disabled, and deployment contract tests in `tests/contract/test_us6_health_and_deployment_contract.py`
- [X] T065 [P] [US6] Add public trace replay integration tests in `tests/integration/test_replay_public_traces.py`
- [X] T066 [P] [US6] Add complete behavior-probe suite tests, including conversational incoherence, in `tests/integration/test_behavior_probes.py`
- [X] T067 [P] [US6] Add Recall@K and evaluator metadata unit tests in `tests/unit/test_evaluation_metrics.py`

### Implementation for User Story 6

- [X] T068 [US6] Implement public trace parsing and replay execution in `app/evaluation/replay.py`
- [X] T069 [US6] Implement Recall@K, baseline comparison, schema, catalog-only, turn-cap, timeout, and failure-category metrics in `app/evaluation/metrics.py`
- [X] T070 [US6] Implement behavior probe definitions and runner in `app/evaluation/probes.py`
- [X] T071 [US6] Add evaluator replay command entry point in `scripts/run_replay.py`
- [X] T072 [US6] Update implementation evidence and AI-tool usage in `docs/approach.md`
- [X] T073 [US6] Document public endpoint, exact-route exposure, default-docs-disabled, and cold-start timing validation in `docs/deployment.md`
- [X] T074 [US6] Finalize Render deployment configuration in `render.yaml`

**Checkpoint**: User Story 6 makes the service ready for replay evaluation and submission review.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final checks, documentation alignment, and robustness coverage across all user stories.

- [X] T075 [P] Add malformed-history, missing-preference, and contradictory-fact robustness tests in `tests/integration/test_non_happy_paths.py`
- [X] T076 [P] Add catalog coverage report documentation in `docs/catalog-coverage.md`
- [X] T077 Run full pytest regression and record Recall@10 baseline comparison results in `docs/evaluation-results.md`
- [X] T078 Validate quickstart commands and record corrections in `specs/001-shl-assessment-recommender/quickstart.md`
- [ ] T079 Validate public `/health`, cold-start timing, `/chat`, and disabled default docs routes and record final URL in `docs/deployment.md`
- [X] T080 Trim `docs/approach.md` to two pages and align it with `docs/evaluation-results.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1) has no dependencies and can start immediately.
- Foundational (Phase 2) depends on Setup and blocks all user stories.
- User stories depend on Foundational completion.
- Polish depends on all desired user stories for the release scope.

### User Story Completion Order

- US1 Clarify Vague Hiring Intent (P1) is the MVP checkpoint and can start immediately after Foundation.
- US2 Recommend a Grounded Shortlist (P1) can start after Foundation and benefits from US1 clarification gates.
- US5 Refuse Out-of-Scope or Unsafe Requests (P1) can start after Foundation and should be complete before public replay hardening.
- US3 Refine a Shortlist Mid-Conversation (P2) can start after Foundation, but depends conceptually on US2 recommendation rendering.
- US4 Compare Catalog Assessments (P2) can start after Foundation and shares catalog lookup with US2.
- US6 Support Evaluator Replay and Submission Review (P3) can start after Foundation for harness work, but final validation depends on US1, US2, US3, US4, and US5.

### Story Dependencies

- US1 has no dependency on other stories.
- US2 has no hard dependency on US1, but should reuse US1 extraction and policy primitives when available.
- US5 has no dependency on US1 or US2 and can be implemented independently after Foundation.
- US3 depends on recommendation concepts from US2 for revised shortlists.
- US4 depends on catalog lookup from Foundation and may reuse retrieval aliases from US2.
- US6 depends on all implemented behavior paths for final replay and submission readiness.

---

## Parallel Execution Examples

### User Story 1

```text
Task: T024 Add contract tests in tests/contract/test_us1_clarification_contract.py
Task: T025 Add integration tests in tests/integration/test_us1_clarification.py
Task: T026 Add behavior probe in tests/integration/test_us1_clarification_probe.py
Task: T027 Add unit tests in tests/unit/test_goal_extraction.py
```

### User Story 2

```text
Task: T032 Add contract tests in tests/contract/test_us2_recommendation_contract.py
Task: T033 Add integration tests in tests/integration/test_us2_grounded_recommendation.py
Task: T034 Add behavior probe in tests/integration/test_us2_catalog_grounding_probe.py
Task: T035 Add ranking unit tests in tests/unit/test_ranking.py
```

### User Story 5

```text
Task: T041 Add contract tests in tests/contract/test_us5_refusal_contract.py
Task: T042 Add integration tests in tests/integration/test_us5_refusal.py
Task: T043 Add behavior probe in tests/integration/test_us5_prompt_injection_probe.py
```

### User Story 3

```text
Task: T048 Add contract tests in tests/contract/test_us3_refinement_contract.py
Task: T049 Add integration tests in tests/integration/test_us3_refinement.py
Task: T050 Add behavior probe in tests/integration/test_us3_user_edits_probe.py
```

### User Story 4

```text
Task: T056 Add contract tests in tests/contract/test_us4_comparison_contract.py
Task: T057 Add integration tests in tests/integration/test_us4_comparison.py
Task: T058 Add behavior probe in tests/integration/test_us4_hallucination_probe.py
```

### User Story 6

```text
Task: T064 Add health/deployment contract tests in tests/contract/test_us6_health_and_deployment_contract.py
Task: T065 Add public trace replay tests in tests/integration/test_replay_public_traces.py
Task: T066 Add behavior probe suite in tests/integration/test_behavior_probes.py
Task: T067 Add evaluation metric tests in tests/unit/test_evaluation_metrics.py
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 Setup.
2. Complete Phase 2 Foundational work.
3. Complete Phase 3 User Story 1.
4. Validate that vague requests ask targeted clarification questions with empty recommendations.
5. Continue to US2 and US5 before any public submission because recommendation and refusal are P1 evaluator behaviors.

### Incremental Delivery

1. Foundation ready: catalog, schema, validation, retrieval skeleton, and FastAPI endpoint stubs.
2. US1 ready: clarification behavior is reliable.
3. US2 ready: grounded recommendations are available.
4. US5 ready: unsafe and out-of-scope inputs are contained.
5. US3 ready: multi-turn user edits work from stateless history.
6. US4 ready: comparisons are catalog-grounded.
7. US6 ready: replay, metrics, deployment validation, and submission documentation are complete.

### Parallel Team Strategy

1. Complete Setup and Foundation as shared work.
2. Split P1 stories after Foundation: one contributor on US1, one on US2, one on US5.
3. Split P2 stories after shared P1 primitives stabilize: one contributor on US3, one on US4.
4. Keep US6 harness work running alongside implementation, then finalize replay and deployment evidence after all behavior paths are present.

---

## Validation Checklist

- All tasks use `- [ ] T###` checklist format.
- User-story tasks include `[US1]`, `[US2]`, `[US3]`, `[US4]`, `[US5]`, or `[US6]` labels.
- Setup, Foundational, and Polish tasks intentionally omit story labels.
- Parallelizable tasks are marked `[P]` only when they touch separate files or independent artifacts.
- Each user story includes required tests before implementation tasks.
- Every task includes at least one exact file or directory path.
- Remediation coverage includes schema-safe malformed input, Individual Test Solution eligibility evidence, exact-route exposure, conversational incoherence probes, cold-start timing, Recall@10 baseline comparison, and deterministic LLM fallback.
