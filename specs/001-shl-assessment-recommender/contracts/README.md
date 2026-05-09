# Contracts

This directory contains the evaluator-facing API contract for the conversational SHL assessment recommender.

- [openapi.yaml](openapi.yaml): OpenAPI 3.1 contract for `GET /health` and `POST /chat`.

The top-level `POST /chat` response schema is intentionally strict: `reply`, `recommendations`, and `end_of_conversation` are the only allowed top-level fields. Recommendation items are restricted to `name`, `url`, and `test_type` for evaluator safety unless future evaluator guidance explicitly permits additional fields.
