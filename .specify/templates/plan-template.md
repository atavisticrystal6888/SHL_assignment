# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]  
**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]  
**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]  
**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]  
**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]
**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]  
**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]  
**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]  
**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]
**Catalog Source**: [SHL product catalog ingestion/filtering approach or NEEDS CLARIFICATION]
**Conversation Fixtures**: [public trace usage/evaluator replay plan or NEEDS CLARIFICATION]
**Agent Decision Policy**: [when to ask/retrieve/recommend/refine/compare/refuse/end or NEEDS CLARIFICATION]
**Deployment Target**: [public FastAPI hosting target and cold-start assumptions or NEEDS CLARIFICATION]
**Approach Document**: [2-page submission outline owner/status or NEEDS CLARIFICATION]
**Programming/AI-Assisted Development Rationale**: [defensible coding and AI-tool/no-code usage notes or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [ ] Catalog-only grounding is preserved and restricted to SHL Individual Test Solutions.
- [ ] The plan decomposes ambiguous hiring intent into explicit retrieval, ranking, prompting, and refusal trade-offs.
- [ ] The design explains how vague requests are clarified, how refinements update results, and how comparisons stay grounded.
- [ ] The implementation remains evaluator-compliant: stateless FastAPI `POST /chat`, exact response schema, `GET /health` returning `{"status": "ok"}` with HTTP 200, max 8 turns, and 30-second request budget.
- [ ] Recommendations are empty while clarifying/refusing and contain 1 to 10 items with catalog-backed `name`, `url`, and `test_type` after commitment.
- [ ] Prompt and retrieval context use catalog fields, the full conversation history, and extracted user goals, with clear handling for corrections and missing preferences.
- [ ] Validation covers schema compliance, catalog-only outputs, refusals, refinements, comparisons, public conversation traces, Recall@10, hallucination resistance, conversational incoherence, and behavior probes.
- [ ] Implementation quality covers non-happy-path request histories and can be defended in technical review, including any AI-assisted code.
- [ ] Deployment readiness covers a public API endpoint, reachable `/health` and `/chat`, and practical cold-start behavior.
- [ ] Submission readiness covers the 2-page approach document with retrieval, prompt, evaluation, lessons learned, and AI-tool disclosure.
- [ ] Any added architectural complexity is justified by measurable improvement in recall, latency, or operational robustness.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
