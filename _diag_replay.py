"""Deep diagnostic: replay each conversation and compare final shortlist vs expected."""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
from app.evaluation.replay import discover_trace_fixtures, parse_trace_fixture
from app.main import app

client = TestClient(app)

for fixture in discover_trace_fixtures(Path("data/traces/public")):
    trace = parse_trace_fixture(fixture)
    messages = []
    responses = []
    for ut in trace.user_turns[:4]:
        messages.append({"role": "user", "content": ut.content})
        resp = client.post("/chat", json={"messages": messages})
        body = resp.json()
        responses.append(body)
        messages.append({"role": "assistant", "content": str(body.get("reply", ""))})

    print(f"\n{'='*80}")
    print(f"TRACE: {trace.trace_id}  ({len(trace.user_turns)} total user turns, replayed {min(4, len(trace.user_turns))})")
    print(f"{'='*80}")

    # Show each turn
    for i, ut in enumerate(trace.user_turns[:4]):
        body = responses[i]
        recs = body.get("recommendations", [])
        eoc = body.get("end_of_conversation", False)
        print(f"\n--- Turn {i+1} ---")
        print(f"  USER: {ut.content[:120]}")
        print(f"  REPLY: {body.get('reply','')[:200]}")
        print(f"  end_of_conversation: {eoc}")
        print(f"  recommendations ({len(recs)}): {[r.get('name','') for r in recs]}")

    # Compare final shortlist
    expected_names = [e.name for e in trace.expected_shortlist]
    expected_urls = set(e.url for e in trace.expected_shortlist)
    final_recs = responses[-1].get("recommendations", [])
    actual_names = [r.get("name", "") for r in final_recs]
    actual_urls = set(r.get("url", "") for r in final_recs)

    matched = expected_urls & actual_urls
    missing = expected_urls - actual_urls
    extra = actual_urls - expected_urls

    print(f"\n  EXPECTED ({len(expected_names)}): {expected_names}")
    print(f"  ACTUAL   ({len(actual_names)}): {actual_names}")
    print(f"  MATCHED:  {len(matched)}/{len(expected_urls)}")
    if missing:
        missing_names = [e.name for e in trace.expected_shortlist if e.url in missing]
        print(f"  MISSING:  {missing_names}")
    if extra:
        extra_names = [r.get('name','') for r in final_recs if r.get('url','') in extra]
        print(f"  EXTRA:    {extra_names}")
