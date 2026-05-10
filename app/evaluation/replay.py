"""Public trace fixture discovery."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.api.schemas import ChatResponse
from app.evaluation.metrics import recall_at_k


@dataclass(frozen=True)
class TraceFixture:
    trace_id: str
    path: Path
    text: str


@dataclass(frozen=True)
class ConversationTurn:
    role: str
    content: str


@dataclass(frozen=True)
class ExpectedRecommendation:
    name: str
    url: str
    test_type: str


@dataclass(frozen=True)
class ParsedTrace:
    trace_id: str
    turns: list[ConversationTurn]
    expected_shortlist: list[ExpectedRecommendation]
    notes: list[str]

    @property
    def user_turns(self) -> list[ConversationTurn]:
        return [turn for turn in self.turns if turn.role == "user"]


@dataclass(frozen=True)
class TraceReplayResult:
    trace_id: str
    schema_pass: bool
    turn_cap_pass: bool
    timeout_pass: bool
    recall_at_10: float | None
    responses: list[dict[str, Any]]
    failures: list[str]


def discover_trace_fixtures(trace_dir: Path) -> list[TraceFixture]:
    if not trace_dir.exists():
        return []
    fixtures: list[TraceFixture] = []
    for path in sorted(trace_dir.glob("C*.md")):
        fixtures.append(TraceFixture(trace_id=path.stem, path=path, text=path.read_text(encoding="utf-8")))
    return fixtures


def _extract_role_block(section: str, role: str) -> str:
    marker = f"**{role.title()}**"
    if marker not in section:
        return ""
    after_marker = section.split(marker, maxsplit=1)[1]
    next_marker = re.search(r"\n\*\*(?:User|Agent)\*\*", after_marker)
    block = after_marker[: next_marker.start()] if next_marker else after_marker
    content_lines: list[str] = []
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith(">"):
            content_lines.append(stripped.lstrip(">").strip())
        elif stripped and not stripped.startswith("_") and not stripped.startswith("|"):
            content_lines.append(stripped)
    return "\n".join(content_lines).strip()


def _extract_expected_shortlist(text: str) -> list[ExpectedRecommendation]:
    table_blocks: list[list[str]] = []
    current_block: list[str] = []
    for line in text.splitlines():
        if line.startswith("|"):
            current_block.append(line)
            continue
        if current_block:
            table_blocks.append(current_block)
            current_block = []
    if current_block:
        table_blocks.append(current_block)

    for block in reversed(table_blocks):
        items: list[ExpectedRecommendation] = []
        seen_urls: set[str] = set()
        for line in block:
            if "https://www.shl.com/products/product-catalog/view/" not in line:
                continue
            url_match = re.search(r"<(https://www\.shl\.com/products/product-catalog/view/[^>]+)>", line)
            if not url_match:
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) < 6 or not cells[0].strip().isdigit():
                continue
            url = url_match.group(1)
            if url in seen_urls:
                continue
            seen_urls.add(url)
            items.append(ExpectedRecommendation(name=cells[1].strip("* "), test_type=cells[2], url=url))
        if items:
            return items
    return []


def parse_trace_fixture(fixture: TraceFixture) -> ParsedTrace:
    turns: list[ConversationTurn] = []
    for section in re.split(r"\n### Turn \d+\n", fixture.text):
        user_content = _extract_role_block(section, "user")
        if user_content:
            turns.append(ConversationTurn(role="user", content=user_content))
        agent_content = _extract_role_block(section, "agent")
        if agent_content:
            turns.append(ConversationTurn(role="assistant", content=agent_content))
    notes = [line.strip("_ ") for line in fixture.text.splitlines() if line.strip().startswith("_No recommendations")]
    return ParsedTrace(
        trace_id=fixture.trace_id,
        turns=turns,
        expected_shortlist=_extract_expected_shortlist(fixture.text),
        notes=notes,
    )


def replay_trace(client: TestClient, trace: ParsedTrace, *, max_user_turns: int | None = None) -> TraceReplayResult:
    messages: list[dict[str, str]] = []
    responses: list[dict[str, Any]] = []
    failures: list[str] = []
    elapsed_times: list[float] = []
    user_turns = trace.user_turns[:max_user_turns] if max_user_turns is not None else trace.user_turns
    for user_turn in user_turns:
        messages.append({"role": "user", "content": user_turn.content})
        started = time.perf_counter()
        response = client.post("/chat", json={"messages": messages})
        elapsed_times.append(time.perf_counter() - started)
        body = response.json()
        responses.append(body)
        try:
            ChatResponse.model_validate(body)
        except Exception as exc:  # pragma: no cover - surfaced through result metadata
            failures.append(f"schema:{trace.trace_id}:{exc}")
            messages.append({"role": "assistant", "content": ""})
            continue
        messages.append({"role": "assistant", "content": str(body.get("reply", ""))})

    expected_urls = [item.url for item in trace.expected_shortlist]
    final_urls = [item.get("url", "") for item in responses[-1].get("recommendations", [])] if responses else []
    recall = recall_at_k(expected_urls, final_urls, k=10) if expected_urls and final_urls else None
    turn_cap_pass = len(messages) <= 8
    timeout_pass = all(elapsed <= 30 for elapsed in elapsed_times)
    if not turn_cap_pass:
        failures.append("turn_cap")
    if not timeout_pass:
        failures.append("timeout")
    return TraceReplayResult(
        trace_id=trace.trace_id,
        schema_pass=not any(failure.startswith("schema:") for failure in failures),
        turn_cap_pass=turn_cap_pass,
        timeout_pass=timeout_pass,
        recall_at_10=recall,
        responses=responses,
        failures=failures,
    )


def replay_fixtures(client: TestClient, trace_dir: Path, *, max_user_turns: int | None = None) -> list[TraceReplayResult]:
    return [replay_trace(client, parse_trace_fixture(fixture), max_user_turns=max_user_turns) for fixture in discover_trace_fixtures(trace_dir)]
