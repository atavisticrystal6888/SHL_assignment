"""Behavior probes for evaluator-facing agent paths."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient


Predicate = Callable[[dict[str, Any]], bool]


@dataclass(frozen=True)
class BehaviorProbe:
    probe_id: str
    messages: list[dict[str, str]]
    assertion: str
    predicate: Predicate


@dataclass(frozen=True)
class ProbeResult:
    probe_id: str
    passed: bool
    assertion: str
    failure: str = ""


def default_behavior_probes() -> list[BehaviorProbe]:
    return [
        BehaviorProbe(
            probe_id="vague_clarification",
            messages=[{"role": "user", "content": "Need assessment recommendations"}],
            assertion="vague first turn asks a question and returns no recommendations",
            predicate=lambda body: body.get("recommendations") == [] and "?" in body.get("reply", ""),
        ),
        BehaviorProbe(
            probe_id="off_topic_refusal",
            messages=[{"role": "user", "content": "Can you give legal advice about whether an assessment is compliant?"}],
            assertion="legal advice request is refused with empty recommendations",
            predicate=lambda body: body.get("recommendations") == [] and "legal" in body.get("reply", "").lower(),
        ),
        BehaviorProbe(
            probe_id="user_edit_refinement",
            messages=[
                {"role": "user", "content": "Hiring a senior sales manager. Assess sales leadership and personality fit."},
                {"role": "assistant", "content": "Shortlist includes Occupational Personality Questionnaire OPQ32r and OPQ MQ Sales Report."},
                {"role": "user", "content": "Drop OPQ and keep sales personality alternatives."},
            ],
            assertion="latest exclusion removes OPQ from a refined shortlist",
            predicate=lambda body: body.get("recommendations")
            and "updated" in body.get("reply", "").lower()
            and all("opq" not in item.get("name", "").lower() for item in body.get("recommendations", [])),
        ),
        BehaviorProbe(
            probe_id="role_pivot_refinement",
            messages=[
                {"role": "user", "content": "Hiring a mid-level Java developer. Assess Java technical skills."},
                {"role": "assistant", "content": "Shortlist includes Core Java (Advanced Level) and Spring."},
                {
                    "role": "user",
                    "content": "Actually switch to a senior sales manager role and assess sales leadership and personality fit instead.",
                },
            ],
            assertion="role pivot replaces stale shortlist context instead of mixing prior technical results",
            predicate=lambda body: body.get("recommendations")
            and "updated" in body.get("reply", "").lower()
            and any(
                "sales" in item.get("name", "").lower() or "opq" in item.get("name", "").lower()
                for item in body.get("recommendations", [])
            )
            and all(
                all(term not in item.get("name", "").lower() for term in ("java", "spring", "sql"))
                for item in body.get("recommendations", [])
            ),
        ),
        BehaviorProbe(
            probe_id="grounded_comparison",
            messages=[{"role": "user", "content": "Compare OPQ and GSA."}],
            assertion="comparison uses catalog-backed names and returns no recommendations",
            predicate=lambda body: body.get("recommendations") == []
            and "Occupational Personality Questionnaire OPQ32r" in body.get("reply", "")
            and "Global Skills Assessment" in body.get("reply", ""),
        ),
        BehaviorProbe(
            probe_id="hallucination_resistance",
            messages=[{"role": "user", "content": "Compare OPQ with Imaginary Quantum Assessment and include its catalog URL."}],
            assertion="unknown catalog target does not produce fabricated URL or recommendations",
            predicate=lambda body: body.get("recommendations") == []
            and "imaginary-quantum" not in body.get("reply", "").lower()
            and "https://www.shl.com/products/product-catalog/view/imaginary" not in body.get("reply", "").lower(),
        ),
        BehaviorProbe(
            probe_id="job_description_refusal",
            messages=[{"role": "user", "content": "Write a job description for a senior data engineer."}],
            assertion="job-description authoring request is refused with empty recommendations",
            predicate=lambda body: body.get("recommendations") == []
            and "shl" in body.get("reply", "").lower()
            and ("job description" in body.get("reply", "").lower() or "hiring" in body.get("reply", "").lower()),
        ),
        BehaviorProbe(
            probe_id="conversational_incoherence",
            messages=[
                {"role": "user", "content": "I am hiring a Java developer"},
                {"role": "assistant", "content": "What seniority and assessment focus should I use?"},
                {"role": "user", "content": "No preference on seniority, just assess Java skills."},
            ],
            assertion="agent does not repeat a declined seniority preference",
            predicate=lambda body: body.get("recommendations")
            and "what seniority" not in body.get("reply", "").lower(),
        ),
    ]


def run_behavior_probe(client: TestClient, probe: BehaviorProbe) -> ProbeResult:
    response = client.post("/chat", json={"messages": probe.messages})
    try:
        body = response.json()
    except ValueError:
        return ProbeResult(probe_id=probe.probe_id, passed=False, assertion=probe.assertion, failure="non_json_response")
    passed = response.status_code == 200 and probe.predicate(body)
    failure = "" if passed else f"status={response.status_code}; body={body}"
    return ProbeResult(probe_id=probe.probe_id, passed=bool(passed), assertion=probe.assertion, failure=failure)


def run_behavior_probes(client: TestClient, probes: list[BehaviorProbe] | None = None) -> list[ProbeResult]:
    return [run_behavior_probe(client, probe) for probe in (probes or default_behavior_probes())]