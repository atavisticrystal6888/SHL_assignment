from fastapi.testclient import TestClient

from app.catalog.repository import CatalogRepository
from app.main import app
from app.settings import settings


def test_recommendations_are_eligible_catalog_items_and_not_padded():
    client = TestClient(app)
    catalog = CatalogRepository.from_path(settings.catalog_path)
    response = client.post(
        "/chat",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "Hiring a senior Linux networking engineer. Assess Linux and networking technical skills.",
                }
            ]
        },
    )

    recommendations = response.json()["recommendations"]
    assert 1 <= len(recommendations) <= 10
    for recommendation in recommendations:
        assert catalog.contains_url(recommendation["url"], eligible_only=True)
        assert "pre-packaged" not in recommendation["name"].lower()
