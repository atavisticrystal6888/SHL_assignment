import httpx

from app.catalog.models import CatalogAssessment
from app.retrieval.index import build_catalog_index
from app.conversation.extractor import UserGoalProfile
from app.llm.client import LLMClient
from app.retrieval.ranker import CatalogMatch, rank_catalog, rerank_catalog_with_llm, rerank_catalog_with_llm_result


def test_rank_catalog_prioritizes_matching_eligible_records():
    java = CatalogAssessment(
        entity_id="1",
        name="Java 8 (New)",
        url="https://www.shl.com/products/product-catalog/view/java-8-new/",
        test_type="K",
        categories=["Knowledge & Skills"],
        description="Measures Java programming knowledge.",
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    sales = CatalogAssessment(
        entity_id="2",
        name="Sales Concepts",
        url="https://www.shl.com/products/product-catalog/view/sales-concepts/",
        test_type="K",
        categories=["Knowledge & Skills"],
        description="Measures sales knowledge.",
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    index = build_catalog_index([sales, java])

    matches = rank_catalog(index, "Java developer technical skills", limit=1)

    assert matches[0].assessment.name == "Java 8 (New)"


def test_rank_catalog_filters_ineligible_records():
    ineligible = CatalogAssessment(
        entity_id="1",
        name="Java Job Solution",
        url="https://www.shl.com/products/product-catalog/view/java-job-solution/",
        test_type="K",
        categories=["Knowledge & Skills"],
        description="Java",
        eligible_for_recommendation=False,
        eligibility_source="ineligible:pre_packaged_job_solution",
    )
    index = build_catalog_index([ineligible])

    assert rank_catalog(index, "Java", limit=10) == []


def test_rerank_catalog_with_llm_reorders_existing_candidates_only():
    java = CatalogAssessment(
        entity_id="1",
        name="Java 8 (New)",
        url="https://www.shl.com/products/product-catalog/view/java-8-new/",
        test_type="K",
        categories=["Knowledge & Skills"],
        description="Measures Java programming knowledge.",
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    personality = CatalogAssessment(
        entity_id="2",
        name="Occupational Personality Questionnaire OPQ32r",
        url="https://www.shl.com/products/product-catalog/view/occupational-personality-questionnaire-opq32r/",
        test_type="P",
        categories=["Personality & Behavior"],
        description="Measures workplace personality preferences.",
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    matches = [
        CatalogMatch(java, 0.9, ["name"], [java.name], []),
        CatalogMatch(personality, 0.8, ["name"], [personality.name], []),
    ]

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"ordered_entity_ids": ["2", "1"]}'}}]},
        )

    client = LLMClient(
        api_key="test-key",
        base_url="https://example.com/v1",
        model="openai/gpt-oss-120b",
        transport=httpx.MockTransport(handler),
    )

    reranked = rerank_catalog_with_llm(
        matches,
        UserGoalProfile(
            latest_user_text="Add personality tests for this engineering hire.",
            role_titles=["Engineer"],
            assessment_focus=["personality"],
        ),
        client,
        limit=2,
    )

    assert [match.assessment.entity_id for match in reranked] == ["2", "1"]


def test_rerank_catalog_with_llm_result_reports_status():
    java = CatalogAssessment(
        entity_id="1",
        name="Java 8 (New)",
        url="https://www.shl.com/products/product-catalog/view/java-8-new/",
        test_type="K",
        categories=["Knowledge & Skills"],
        description="Measures Java programming knowledge.",
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    matches = [CatalogMatch(java, 0.9, ["name"], [java.name], [])]

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"ordered_entity_ids": ["1"]}'}}]},
        )

    client = LLMClient(
        api_key="test-key",
        base_url="https://example.com/v1",
        model="openai/gpt-oss-120b",
        transport=httpx.MockTransport(handler),
    )

    result = rerank_catalog_with_llm_result(
        matches,
        UserGoalProfile(
            latest_user_text="Assess Java skills.",
            role_titles=["Engineer"],
            assessment_focus=["skills"],
        ),
        client,
        limit=1,
    )

    assert result.llm_status == "llm_success"
    assert [match.assessment.entity_id for match in result.matches] == ["1"]
