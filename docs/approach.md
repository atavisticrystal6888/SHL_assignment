# Approach

## Design Choices

The service is a stateless FastAPI API exposing `GET /health` and `POST /chat` only. Each chat request carries the full message history, so clarification, recommendation, refinement, comparison, refusal, and malformed-input handling are derived from the submitted payload rather than server-side state. Default FastAPI documentation routes are disabled for the evaluator surface.

## Retrieval Setup

The recommender loads a normalized repository-local SHL catalog artifact at runtime. Recommendations are restricted to eligible catalog records and validated before return, while comparison answers may use read-only catalog facts such as name, URL, test type, categories, duration, remote testing, adaptive/IRT status, job levels, languages, and description. TF-IDF ranking over catalog text provides deterministic shortlist ordering with small, explainable boosts for requested categories and constraints.

## Prompt and Policy Design

The current implementation uses deterministic policy and rendering as the safe baseline. The policy layer still chooses clarify, recommend, refine, compare, or refuse from the latest user turn plus full history, but a Groq-backed adapter can now contribute in three constrained places when configured: filling missing intent signals from the conversation, reranking the already-filtered candidate shortlist, and rewriting reply text. Retrieval, recommendation objects, and catalog validation remain deterministic. If the provider is unavailable, malformed, or inconsistent, the service falls back to the deterministic path.

## Evaluation Approach

Validation includes exact schema checks, catalog-only recommendation checks, public trace replay metadata, Recall@10 helpers, behavior probes, turn-cap checks, timeout flags, and deployment contract checks. Current local evidence is recorded in `docs/evaluation-results.md`: 49 scoped feature tests pass, `scripts/run_replay.py` reports schema, turn-cap, and timeout pass for all public traces under cap-aware replay, all six behavior probes pass, and the current labeled-trace Mean Recall@10 baseline is 0.30.

## Failed Approaches and Iteration Notes

The implementation avoids a fully LLM-driven recommender because that would make schema and catalog grounding harder to prove. It also avoids a vector database for the current 377-record catalog; local TF-IDF is simpler, fast enough, and easier to defend. Comparison handling was separated from recommendation because comparison questions should not require role/seniority context or populate `recommendations` unless the user asks for a shortlist.

## AI Tool Usage

AI assistance was used for scaffolding tests, implementation passes, and review prompts. The final behavior is checked through local tests and explicit validation gates, and implementation trade-offs remain documented here for technical review.
