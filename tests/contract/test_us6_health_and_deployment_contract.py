from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_health_and_only_expected_public_routes_are_exposed():
    client = TestClient(app)

    assert client.get("/").status_code == 200
    assert client.get("/").json() == {
        "service": "shl-assessment-recommender",
        "status": "ok",
        "endpoints": {"health": "/health", "chat": "/chat"},
    }
    assert client.get("/health").status_code == 200
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_chat_malformed_input_preserves_exact_contract_shape():
    client = TestClient(app)
    response = client.post("/chat", json={"messages": []})

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"reply", "recommendations", "end_of_conversation"}
    assert body["recommendations"] == []
    assert body["end_of_conversation"] is False
    assert "detail" not in body


def test_render_blueprint_declares_fastapi_start_and_health_check():
    render_yaml = Path("render.yaml").read_text(encoding="utf-8")

    assert "uvicorn app.main:app" in render_yaml
    assert "--port $PORT" in render_yaml
    assert "PYTHON_VERSION" in render_yaml
    assert "3.11.9" in render_yaml
    assert "healthCheckPath: /health" in render_yaml
