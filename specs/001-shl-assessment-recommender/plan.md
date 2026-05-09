# Implementation Plan: Conversational SHL Assessment Recommender

**Branch**: `001-shl-assessment-recommender` | **Date**: 2026-05-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-shl-assessment-recommender/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Build a stateless FastAPI service that converts vague hiring intent into a
catalog-grounded SHL assessment shortlist through dialogue. The service will use
the scraped SHL product catalog as canonical data, filter recommendations to
Individual Test Solutions, derive user goals from the full request history, and
combine deterministic retrieval/ranking with a tightly constrained LLM response
step for clarification, comparison, refinement, and refusal behavior. Planning
also covers public-trace replay, Recall@10 measurement, behavior probes, public
deployment readiness, and the required two-page approach document.

## Technical Context

**Language/Version**: Python 3.11+ for broad FastAPI and free-hosting compatibility  
**Primary Dependencies**: FastAPI, Pydantic v2, Uvicorn, httpx, beautifulsoup4/lxml for catalog refresh, scikit-learn for local TF-IDF retrieval/ranking, optional Groq-backed chat-completions provider selected by environment variable with deterministic fallback when no key is configured  
**Storage**: Repository-local JSON/normalized artifact files loaded read-only at startup; no per-conversation database or server-side session storage  
**Testing**: pytest, FastAPI TestClient/httpx, JSON Schema or Pydantic validation, replay fixtures for public traces, behavior-probe tests  
**Target Platform**: Render Web Service running a public Linux FastAPI deployment with cold-start health checks  
**Project Type**: Single backend web service with supporting evaluation and catalog-preparation scripts  
**Performance Goals**: `/health` returns HTTP 200 after service wake-up; 95% of steady-state `/chat` replay/probe calls complete under 30 seconds; final public-trace recommendations report Mean Recall@10  
**Constraints**: Stateless `POST /chat`; exact top-level response schema for all chat outcomes including malformed input; recommendations empty while clarifying/refusing; 1 to 10 catalog-backed recommendations after commitment; max 8 total conversation turns; every URL from canonical catalog; submitted service exposes only `/health` and `/chat` by disabling default docs routes  
**Scale/Scope**: 377 current scraped catalog records, 10 public trace fixtures, additional hidden traces/probes expected by evaluator  
**Catalog Source**: `Documents/shl_product_catalog.json` and public SHL catalog URL, normalized to canonical records with explicit eligibility evidence for Individual Test Solutions; records without source metadata or curated mapping proving eligibility are treated as ineligible  
**Conversation Fixtures**: `Documents/GenAI_SampleConversations/C1.md` through `C10.md`, parsed into replay scenarios and expected shortlist checks where labels are recoverable  
**Agent Decision Policy**: Deterministic guardrails classify clarify/retrieve/recommend/refine/compare/refuse/end; LLM output is constrained by retrieved catalog facts and post-validated before response; if the LLM adapter is disabled or fails, deterministic renderer paths still return schema-safe grounded responses  
**Deployment Target**: Render Web Service as the default submission target; keep ASGI startup and environment configuration portable enough to move to Fly, Railway, Modal, or Hugging Face Spaces if Render constraints appear during implementation  
**Approach Document**: Two-page document drafted during implementation polish, covering design choices, retrieval setup, prompt design, evaluation, failed attempts, measured improvement, and AI-tool use  
**Programming/AI-Assisted Development Rationale**: AI assistance is allowed for scaffolding and review, but implementation logic, evaluation results, and trade-offs must be explainable in technical review

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Catalog-only grounding is preserved and restricted to SHL Individual Test Solutions.
- [x] The plan decomposes ambiguous hiring intent into explicit retrieval, ranking, prompting, and refusal trade-offs.
- [x] The design explains how vague requests are clarified, how refinements update results, and how comparisons stay grounded.
- [x] The implementation remains evaluator-compliant: stateless FastAPI `POST /chat`, exact response schema, `GET /health` returning `{"status": "ok"}` with HTTP 200, max 8 turns, and 30-second request budget.
- [x] Recommendations are empty while clarifying/refusing and contain 1 to 10 items with catalog-backed `name`, `url`, and `test_type` after commitment.
- [x] Prompt and retrieval context use catalog fields, the full conversation history, and extracted user goals, with clear handling for corrections and missing preferences.
- [x] Validation covers schema compliance, catalog-only outputs, refusals, refinements, comparisons, public conversation traces, Recall@10, hallucination resistance, conversational incoherence, and behavior probes.
- [x] Implementation quality covers non-happy-path request histories and can be defended in technical review, including any AI-assisted code.
- [x] Deployment readiness covers a public API endpoint, reachable `/health` and `/chat`, and practical cold-start behavior.
- [x] Submission readiness covers the 2-page approach document with retrieval, prompt, evaluation, lessons learned, and AI-tool disclosure.
- [x] Any added architectural complexity is justified by measurable improvement in recall, latency, or operational robustness.

## Project Structure

### Documentation (this feature)

```text
specs/001-shl-assessment-recommender/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── openapi.yaml     # FastAPI contract for evaluator-facing endpoints
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
app/
├── main.py                 # FastAPI app, /health, /chat wiring
├── api/
│   └── schemas.py          # Request/response Pydantic models
├── catalog/
│   ├── ingest.py           # Catalog refresh/normalization
│   ├── repository.py       # Read-only catalog access
│   └── models.py           # CatalogAssessment model
├── conversation/
│   ├── extractor.py        # Stateless user-goal extraction from messages
│   ├── policy.py           # ask/retrieve/recommend/refine/compare/refuse/end policy
│   └── renderer.py         # Response text and recommendation formatting
├── retrieval/
│   ├── index.py            # Lexical/hybrid index building
│   └── ranker.py           # Deterministic ranking and tie-breaking
├── llm/
│   ├── client.py           # Optional raw SDK adapter
│   └── prompts.py          # Grounded prompt templates
└── evaluation/
    ├── replay.py           # Public trace replay harness
    ├── metrics.py          # Recall@K and schema/catalog checks
    └── probes.py           # Behavior probes

tests/
├── contract/
│   └── test_chat_contract.py
├── integration/
│   ├── test_replay_public_traces.py
│   └── test_behavior_probes.py
└── unit/
    ├── test_catalog_normalization.py
    ├── test_goal_extraction.py
    └── test_ranking.py

data/
├── raw/shl_product_catalog.json
├── processed/catalog.json
└── traces/public/

docs/
└── approach.md
```

**Structure Decision**: Use a single FastAPI backend with separate modules for
API schema, catalog normalization, stateless conversation policy, retrieval,
optional LLM prompting, and evaluation. This keeps evaluator-facing behavior
testable without introducing frontend or database complexity.

## Phase 0 Research Summary

See [research.md](research.md) for resolved technical decisions. No open
clarifications remain.

## Phase 1 Design Summary

- Data model: [data-model.md](data-model.md)
- API contract: [contracts/openapi.yaml](contracts/openapi.yaml)
- Validation quickstart: [quickstart.md](quickstart.md)

## Post-Design Constitution Check

- [x] Catalog-only grounding remains central: canonical catalog records own all recommendation names, URLs, and test types.
- [x] Stateless API contract remains exact and is captured in the OpenAPI contract.
- [x] Public traces, Recall@10, schema checks, catalog-only checks, and behavior probes are represented in the data model and quickstart.
- [x] Added complexity is limited to separable retrieval/ranking and optional LLM adapter layers, justified by recall and grounded-response quality.
- [x] Deployment and approach-document readiness are included as implementation deliverables.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
