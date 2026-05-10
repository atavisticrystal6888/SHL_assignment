# SHL Assessment Recommender Submission Summary

## Overview

I built the system as a stateless FastAPI service with exactly two evaluator-facing endpoints: `GET /health` and `POST /chat`. Every chat call carries the full conversation history, so the agent makes decisions from submitted context instead of relying on server-side session state. I kept the serving layer deliberately narrow because the assignment is scored on schema compliance, catalog grounding, and consistent multi-turn behavior under an 8-turn cap.

The core design choice was to separate policy, retrieval, and rendering. Policy decides whether to clarify, recommend, refine, compare, or refuse. Retrieval produces a catalog-backed candidate set, and rendering turns that decision into the required response schema.

## Design Choices

I normalized the SHL product catalog into a local canonical artifact and restricted recommendations to Individual Test Solutions only. The current processed snapshot contains 377 eligible records. Every returned recommendation is validated against this repository-local catalog before it is sent back, which prevents fabricated URLs or off-catalog items.

I chose a deterministic baseline rather than a fully LLM-driven recommender because the hard evaluation criteria reward exact schema output, catalog-only grounding, and consistent replay behavior. I still kept an optional LLM path, but only as a constrained helper for intent extraction, candidate reranking, and reply rewriting. If the provider is disabled or malformed, the system falls back to the deterministic path.

I also treated comparison as a separate path from recommendation. Comparison questions such as asking for the difference between two named assessments should not require role or seniority context, and they should not populate `recommendations` unless the user is explicitly asking for a shortlist.

## Retrieval Setup

For retrieval, I used a local TF-IDF index over name, test type, categories, description, duration, job levels, and languages. The index uses English stop-word removal and 1-2 gram features, with light normalization for spelling variants such as behaviour/behavior and judgement/judgment.

Ranking starts with cosine similarity, then applies small, explainable boosts for signals that matter in hiring requests: requested assessment focus, exact skill or role terms, job level, language/locale, and explicit references to known assessments. The reranker also supports exclusions and mid-conversation corrections, deduplicates closely related assessment families, and prunes low-value padding so the system does not fill the response to 10 items unless the matches are still defensible.

I did not use a vector database. With 377 records, TF-IDF is fast, transparent, and easier to tune than a heavier semantic retrieval stack. For this assignment, explainability and repeatability mattered more than maximizing modeling sophistication.

## Prompt Design

Prompting is intentionally narrow. Each prompt starts with grounding rules that forbid inventing product names, URLs, durations, languages, compliance claims, or other catalog facts. JSON-producing prompts also add a strict JSON-only instruction.

There are three prompt types:

1. Intent extraction from the full conversation history into a controlled set of fields.
2. Candidate reranking over already retrieved assessments, without allowing the model to introduce new items.
3. Grounded reply rewriting so the user-facing text is concise while the JSON schema remains application-controlled.

This keeps the LLM, when enabled, inside a small box while retrieval, catalog validation, and final response structure remain deterministic.

## Evaluation Method And Improvement Tracking

I evaluated the system at four levels:

1. Unit and contract tests for schema shape, catalog normalization, ranking behavior, and malformed input handling.
2. Integration tests for each required behavior: clarification, recommendation, refusal, refinement, comparison, and non-happy paths.
3. A replay harness over the 10 provided public traces to check schema compliance, turn-cap compliance, timeout compliance, and Recall@10 where labeled shortlists were recoverable.
4. Behavior probes for common evaluator-facing failures such as premature recommendation, refusal gaps, hallucinated comparisons, and broken refinement.

The recorded local evidence in this repo is: 49 scoped tests passed, replay across C1-C10 passed schema/turn-cap/timeout checks, and the labeled public-trace Mean Recall@10 baseline is 0.30. I used these metrics as the main signal for improvement, especially after changes to intent policy or ranking heuristics.

I also measured improvement by converting observed failures into explicit tests or probes. That let me check whether a change actually fixed the target behavior instead of only changing the wording of a reply.

## What Did Not Work

Several approaches either failed outright or produced unstable behavior:

- A more LLM-heavy approach made schema compliance and catalog grounding harder to guarantee, so I reduced the model to an optional helper instead of a decision maker.
- Early versions of the policy recommended too soon on vague first turns, so I added explicit missing-factor checks before allowing recommendations.
- Naive comparison detection can misfire on generic wording like "comparing candidates," so I separated comparison into a stricter path.
- Padding every shortlist toward 10 results diluted relevance, so I added family deduplication and padding-pruning.

## AI Tool Usage

I used AI-assisted coding tools for scaffolding tests, implementation passes, and review support. The final system behavior was accepted only after local validation through tests, replay checks, and explicit catalog/schema gates.