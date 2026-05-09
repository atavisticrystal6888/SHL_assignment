# Research: Conversational SHL Assessment Recommender

## Decision: Use Python 3.11+ with FastAPI and Pydantic v2

**Rationale**: The assignment requires FastAPI endpoints and a stateless JSON API. Python 3.11+ is widely supported on free deployment platforms and is compatible with FastAPI, Pydantic v2, pytest, and common retrieval libraries. It also avoids deployment risk from newer Python runtimes that may not be available on free hosts.

**Alternatives considered**: Python 3.14 from the local development environment was rejected for deployment compatibility risk. Node.js was rejected because the assignment already requires FastAPI and the local artifacts are Python-oriented.

## Decision: Store catalog data as normalized repository-local files loaded at startup

**Rationale**: The current catalog size is small enough for in-memory loading: 377 records in the provided development catalog. A normalized `data/processed/catalog.json` artifact preserves deterministic recommendation inputs, allows URL/name/test-type validation, and avoids adding operational database complexity for a take-home evaluator service.

**Alternatives considered**: PostgreSQL, pgvector, or cloud object storage were rejected for v1 because they add deployment and state-management complexity without a clear need at this scale. Live scraping on every request was rejected because it creates latency and availability risk.

## Decision: Use deterministic guardrails plus scikit-learn TF-IDF ranking before optional LLM generation

**Rationale**: The evaluator scores catalog-only correctness, schema compliance, and Recall@10. Deterministic extraction, eligibility filtering, and ranking keep recommendations auditable. A scikit-learn TF-IDF index over normalized fields such as name, categories, job levels, description, duration, and languages is sufficient for the catalog size and can be improved with synonyms and trace-derived terms. An optional LLM can help phrase replies, comparisons, and clarifications only after retrieval has produced grounded facts.

**Alternatives considered**: A fully LLM-driven recommender was rejected because it risks hallucinated products and URLs. A full vector database was deferred because the catalog is small and TF-IDF ranking is easier to defend. BM25 remains a possible later swap only if measured Recall@10 improves. A framework-heavy agent graph was rejected unless later measurement shows it improves recall or reliability.

## Decision: Treat agent policy as explicit control flow, not free-form chat

**Rationale**: The required behaviors are known: clarify, recommend, refine, compare, refuse, and end. An explicit policy layer can decide which behavior applies from the full conversation history, the latest user turn, extracted facts, and retrieval confidence. This keeps recommendations empty while clarifying/refusing and prevents premature shortlist generation.

**Alternatives considered**: A single prompt that decides everything was rejected because it is harder to test and easier to drift from schema and catalog constraints. A fixed script was rejected because evaluator users may volunteer facts out of order or correct themselves.

## Decision: Validate every response after generation

**Rationale**: Schema drift and off-catalog recommendations are hard evaluation failures. Post-generation validation can enforce top-level response fields, empty recommendations during clarification/refusal, recommendation count limits, catalog URL membership, and required recommendation keys before a response leaves the service.

**Alternatives considered**: Relying on prompt instructions alone was rejected as too fragile. Allowing extra top-level fields was rejected because the assignment says the response schema is non-negotiable.

## Decision: Use public trace markdown files as development fixtures

**Rationale**: `Documents/GenAI_SampleConversations/C1.md` through `C10.md` provide examples of the expected conversational dynamics, shortlist style, and final outcomes. Parsing these into replay fixtures supports regression testing and Recall@10 measurement where expected shortlists are recoverable.

**Alternatives considered**: Manual spot-checking was rejected because it does not scale or catch regressions. Treating traces only as examples was rejected because the assignment explicitly says to review and iterate against them.

## Decision: Measure Recall@10 and behavior probes separately

**Rationale**: The assignment scores hard evals, Recall@10, and behavior probe pass rate as separate concerns. Separating metrics makes failures easier to debug: retrieval/ranking issues affect Recall@10, while policy/schema/refusal issues affect probes and hard evals.

**Alternatives considered**: A single aggregate score was rejected because it hides failure categories. Only testing final recommendations was rejected because behavior probes cover no-turn-1 recommendation, refusal, user edits, comparison grounding, and hallucination resistance.

## Decision: Deploy as a single Render-hosted public FastAPI service

**Rationale**: The submission asks for a public API endpoint where `/health` and `/chat` are reachable. Render Web Service is a straightforward default for a Python ASGI app with public routing and cold-start behavior that can be validated against the assignment limits. A single service minimizes moving parts and keeps the stateless API easy to test. Startup can load processed catalog artifacts, while each request derives all conversation state from `messages`.

**Alternatives considered**: Fly, Railway, Modal, and Hugging Face Spaces remain viable fallback hosts if Render constraints appear. A multi-service architecture was rejected because the evaluator only needs a public HTTP API and the constitution rejects unmeasured complexity. Server-side sessions were rejected because the API must be stateless.

## Decision: Draft the approach document as an implementation deliverable

**Rationale**: Manual review expects concise explanation of design choices, retrieval setup, prompt design, evaluation approach, failed attempts, measured improvement, and AI-tool usage. Treating it as a tracked deliverable prevents it from becoming a last-minute narrative detached from implementation evidence.

**Alternatives considered**: Writing the document only after deployment was rejected because measurements and failed approaches must be captured during iteration.
