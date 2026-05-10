import pytest
from fastapi.testclient import TestClient

from app.api.schemas import ChatResponse, Recommendation
from app.api.validators import parse_chat_request, validate_chat_response
from app.catalog.models import CatalogAssessment
from app.catalog.repository import CatalogRepository
from app.main import app


def test_parse_valid_chat_request():
    request, malformed = parse_chat_request({"messages": [{"role": "user", "content": "I need an assessment"}]})

    assert malformed is None
    assert request is not None
    assert request.messages[0].role == "user"


def test_parse_malformed_chat_request_returns_schema_safe_response():
    request, malformed = parse_chat_request({"messages": []})

    assert request is None
    assert malformed is not None
    assert set(malformed.model_dump().keys()) == {"reply", "recommendations", "end_of_conversation"}
    assert malformed.recommendations == []
    assert malformed.end_of_conversation is False


def test_validate_rejects_recommendations_when_not_allowed():
    response = ChatResponse(
        reply="Not allowed",
        recommendations=[Recommendation(name="Java 8", url="https://www.shl.com/products/product-catalog/view/java-8-new/", test_type="K")],
        end_of_conversation=False,
    )

    with pytest.raises(ValueError, match="recommendations must be empty"):
        validate_chat_response(response, recommendations_allowed=False)


def test_validate_rejects_off_catalog_recommendation_url():
    catalog = CatalogRepository(
        [
            CatalogAssessment(
                entity_id="1",
                name="Java 8",
                url="https://www.shl.com/products/product-catalog/view/java-8-new/",
                test_type="K",
                eligible_for_recommendation=True,
                eligibility_source="eligible:catalog_product_record",
            )
        ]
    )
    response = ChatResponse(
        reply="Shortlist",
        recommendations=[Recommendation(name="Made Up", url="https://example.com/made-up", test_type="K")],
        end_of_conversation=False,
    )

    with pytest.raises(ValueError, match="not eligible catalog URL"):
        validate_chat_response(response, catalog=catalog, recommendations_allowed=True)


def test_health_and_chat_stubs_preserve_exact_public_shape():
    client = TestClient(app)

    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/docs").status_code == 404
    response = client.post("/chat", json={"messages": [{"role": "user", "content": "I need an assessment"}]})

    assert response.status_code == 200
    assert set(response.json().keys()) == {"reply", "recommendations", "end_of_conversation"}
    assert response.json()["recommendations"] == []


def test_catalog_assessment_normalizes_known_excel_record_name():
    assessment = CatalogAssessment(
        entity_id="4207",
        name="Microsoft \n    365 (New)",
        url="https://www.shl.com/products/product-catalog/view/microsoft-excel-365-new/",
        test_type="K",
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )

    assert assessment.name == "Microsoft Excel 365 (New)"


def test_browser_routes_render_html_pages():
    client = TestClient(app)

    landing = client.get("/", headers={"accept": "text/html"})
    assert landing.status_code == 200
    assert "text/html" in landing.headers["content-type"]
    assert "Assessment recommendations with a browser entrypoint." in landing.text

    health = client.get("/health", headers={"accept": "text/html"})
    assert health.status_code == 200
    assert "text/html" in health.headers["content-type"]
    assert "Service Health" in health.text

    chat = client.get("/chat", headers={"accept": "text/html"})
    assert chat.status_code == 200
    assert "text/html" in chat.headers["content-type"]
    assert "SHL Recommender Session" in chat.text


def test_health_json_override_bypasses_browser_html_negotiation():
    client = TestClient(app)

    response = client.get("/health?format=json", headers={"accept": "text/html"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["content-type"].startswith("application/json")


def test_malformed_chat_endpoint_avoids_default_fastapi_error_body():
    client = TestClient(app)
    response = client.post("/chat", json={"messages": []})

    assert response.status_code == 200
    assert set(response.json().keys()) == {"reply", "recommendations", "end_of_conversation"}
    assert "detail" not in response.json()
    assert response.json()["recommendations"] == []
