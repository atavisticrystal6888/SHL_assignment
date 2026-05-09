# Catalog Coverage

## Source Snapshot

- Source URL: `https://www.shl.com/solutions/products/product-catalog/`
- Snapshot timestamp: `2026-05-08T11:25:35.672501+00:00`
- Raw artifact: `data/raw/shl_product_catalog.json`
- Processed artifact: `data/processed/catalog.json`
- Coverage artifact: `data/processed/catalog_coverage.json`

## Record Counts

- Total normalized records: 377
- Eligible recommendation records: 377
- Ineligible records: 0
- Status counts: `ok` = 377

Eligibility is defined as: status ok, canonical SHL product URL, explicit source metadata, and not a Pre-packaged Job Solution.

## Required Grounding Fields

Each processed record preserves the fields required for recommendation grounding, comparison answers, and evaluator validation: `entity_id`, `name`, `url`, `test_type`, `categories`, `description`, `duration`, `remote_testing`, `adaptive_irt`, `job_levels`, `languages`, `eligible_for_recommendation`, and `eligibility_source`.

## Coverage Distribution

Top category counts in the current snapshot are `Knowledge & Skills` = 240, `Personality & Behavior` = 67, `Simulations` = 43, `Ability & Aptitude` = 32, `Competencies` = 19, and `Biodata & Situational Judgment` = 17.

Top job-level counts are `Mid-Professional` = 304, `Professional Individual Contributor` = 296, `Graduate` = 140, `Manager` = 117, and `Entry-Level` = 114.

The largest language counts are `English (USA)` = 321, `English International` = 74, `Latin American Spanish` = 51, `French` = 50, `Italian` = 47, `Dutch` = 45, and `Chinese Simplified` = 45.