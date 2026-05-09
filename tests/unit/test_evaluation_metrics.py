from app.api.schemas import ChatResponse, Recommendation
from app.catalog.models import CatalogAssessment
from app.catalog.repository import CatalogRepository
from app.evaluation.metrics import (
    EvaluationRun,
    compare_recall_baseline,
    evaluate_chat_response,
    recall_at_k,
)


def test_recall_at_k_counts_unique_expected_items_by_url_or_name():
    expected = ["https://example.test/a", "Assessment B", "Assessment C"]
    actual = ["assessment b", "https://example.test/a", "Assessment X"]

    assert recall_at_k(expected, actual, k=10) == 2 / 3


def test_evaluate_chat_response_reports_schema_catalog_turn_and_timeout_status():
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
        recommendations=[
            Recommendation(
                name="Java 8",
                url="https://www.shl.com/products/product-catalog/view/java-8-new/",
                test_type="K",
            )
        ],
        end_of_conversation=False,
    ).model_dump()

    result = evaluate_chat_response(response, catalog=catalog, expected_urls=["https://www.shl.com/products/product-catalog/view/java-8-new/"], turn_count=4, elapsed_seconds=0.2)

    assert result.schema_pass is True
    assert result.catalog_only_pass is True
    assert result.turn_cap_pass is True
    assert result.timeout_pass is True
    assert result.recall_at_10 == 1.0
    assert result.failures == []


def test_evaluation_run_and_baseline_comparison_are_serializable_and_actionable():
    run = EvaluationRun(
        run_id="local",
        schema_pass=True,
        catalog_only_pass=True,
        turn_cap_pass=True,
        timeout_pass=True,
        recall_at_10=0.75,
        probe_results={"vague_clarification": True},
        failures=[],
    )

    assert run.to_dict()["run_id"] == "local"
    assert compare_recall_baseline(current=0.75, baseline=0.5)["status"] == "improved"
    assert compare_recall_baseline(current=0.5, baseline=0.75)["status"] == "regressed"
