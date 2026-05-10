"""Test all sample conversations against Render deployment."""
from __future__ import annotations
import json, sys, re, time
from pathlib import Path
import urllib.request

RENDER_URL = "https://shl-assessment-recommender-zh5s.onrender.com/chat"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.evaluation.replay import discover_trace_fixtures, parse_trace_fixture


def post_chat(messages):
    data = json.dumps({"messages": messages}).encode()
    req = urllib.request.Request(RENDER_URL, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


for fixture in discover_trace_fixtures(Path("data/traces/public")):
    trace = parse_trace_fixture(fixture)
    messages = []
    responses = []
    for ut in trace.user_turns[:4]:
        messages.append({"role": "user", "content": ut.content})
        body = post_chat(messages)
        responses.append(body)
        messages.append({"role": "assistant", "content": str(body.get("reply", ""))})

    print(f"\n{'='*80}")
    print(f"TRACE: {trace.trace_id}  ({len(trace.user_turns)} total user turns, replayed {min(4, len(trace.user_turns))})")
    print(f"{'='*80}")

    for i, ut in enumerate(trace.user_turns[:4]):
        body = responses[i]
        recs = body.get("recommendations", [])
        eoc = body.get("end_of_conversation", False)
        print(f"\n--- Turn {i+1} ---")
        print(f"  USER: {ut.content[:120]}")
        print(f"  REPLY: {body.get('reply','')[:200]}")
        print(f"  end_of_conversation: {eoc}")
        print(f"  recommendations ({len(recs)}): {[r.get('name','') for r in recs]}")

    expected_urls = set(e.url for e in trace.expected_shortlist)
    final_recs = responses[-1].get("recommendations", [])
    actual_urls = set(r.get("url", "") for r in final_recs)
    matched = expected_urls & actual_urls
    missing = expected_urls - actual_urls
    extra = actual_urls - expected_urls

    expected_names = [e.name for e in trace.expected_shortlist]
    actual_names = [r.get("name", "") for r in final_recs]
    print(f"\n  EXPECTED ({len(expected_names)}): {expected_names}")
    print(f"  ACTUAL   ({len(actual_names)}): {actual_names}")
    print(f"  MATCHED:  {len(matched)}/{len(expected_urls)}")
    if missing:
        missing_names = [e.name for e in trace.expected_shortlist if e.url in missing]
        print(f"  MISSING:  {missing_names}")
    if extra:
        extra_names = [r.get('name','') for r in final_recs if r.get('url','') in extra]
        print(f"  EXTRA:    {extra_names}")
