from app.catalog.ingest import build_coverage_summary, normalize_catalog, normalize_record


def test_normalize_record_marks_catalog_product_eligible():
    record = normalize_record(
        {
            "entity_id": "1",
            "name": "Java 8 (New)",
            "link": "https://www.shl.com/products/product-catalog/view/java-8-new/",
            "status": "ok",
            "duration": "30 minutes",
            "remote": "yes",
            "adaptive": "no",
            "keys": ["Knowledge & Skills"],
            "job_levels": ["Mid-Professional"],
            "languages": ["English (USA)"],
            "description": "Measures Java knowledge.",
            "scraped_at": "2026-05-08T00:00:00+00:00",
        }
    )

    assert record.eligible_for_recommendation is True
    assert record.eligibility_source == "eligible:catalog_product_record"
    assert record.test_type == "K"
    assert record.duration_minutes == 30


def test_prepackaged_job_solution_is_ineligible():
    record = normalize_record(
        {
            "entity_id": "2",
            "name": "Pre-packaged Job Solution - Sales",
            "link": "https://www.shl.com/products/product-catalog/view/sales-job-solution/",
            "status": "ok",
            "keys": ["Knowledge & Skills"],
            "description": "A pre-packaged job solution.",
        }
    )

    assert record.eligible_for_recommendation is False
    assert record.eligibility_source == "ineligible:pre_packaged_job_solution"


def test_missing_source_metadata_defaults_to_ineligible():
    record = normalize_record(
        {
            "entity_id": "3",
            "name": "Unknown Assessment",
            "status": "ok",
            "keys": ["Ability & Aptitude"],
        }
    )

    assert record.eligible_for_recommendation is False
    assert record.eligibility_source == "ineligible:missing_source_metadata"


def test_coverage_summary_counts_records():
    records = normalize_catalog(
        [
            {
                "entity_id": "1",
                "name": "Java 8 (New)",
                "link": "https://www.shl.com/products/product-catalog/view/java-8-new/",
                "status": "ok",
                "keys": ["Knowledge & Skills"],
                "scraped_at": "2026-05-08T00:00:00+00:00",
            },
            {
                "entity_id": "2",
                "name": "Missing Link",
                "status": "ok",
                "keys": ["Ability & Aptitude"],
            },
        ]
    )

    summary = build_coverage_summary(records)

    assert summary.total_records == 2
    assert summary.eligible_records == 1
    assert summary.ineligible_records == 1
    assert summary.status_counts["ok"] == 2
