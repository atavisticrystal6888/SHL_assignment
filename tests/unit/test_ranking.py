import httpx

from app.catalog.models import CatalogAssessment
from app.retrieval.index import build_catalog_index
from app.conversation.extractor import UserGoalProfile
from app.llm.client import LLMClient
from app.retrieval.query import build_retrieval_query
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


def test_rank_catalog_boosts_named_assessments_in_long_query():
    verify = CatalogAssessment(
        entity_id="1",
        name="SHL Verify Interactive G+",
        url="https://www.shl.com/products/product-catalog/view/shl-verify-interactive-g/",
        test_type="A",
        categories=["Ability & Aptitude"],
        description="Measures general cognitive ability.",
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    graduate = CatalogAssessment(
        entity_id="2",
        name="Graduate Scenarios",
        url="https://www.shl.com/products/product-catalog/view/graduate-scenarios/",
        test_type="B",
        categories=["Biodata & Situational Judgment"],
        description="Situational judgment scenarios for graduate hires.",
        job_levels=["Graduate"],
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    unrelated = CatalogAssessment(
        entity_id="3",
        name="Global Skills Development Report",
        url="https://www.shl.com/products/product-catalog/view/global-skills-development-report/",
        test_type="A",
        categories=["Ability & Aptitude"],
        description="Development report.",
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    index = build_catalog_index([unrelated, graduate, verify])

    matches = rank_catalog(
        index,
        "We run a graduate management trainee scheme. Drop the OPQ. Final list: Verify G+ and Graduate Scenarios.",
        limit=2,
        preferred_categories=["ability", "situational judgment"],
        job_level_signals=["graduate"],
    )

    assert {match.assessment.entity_id for match in matches} == {"1", "2"}


def test_rank_catalog_boosts_required_skill_terms():
    hipaa = CatalogAssessment(
        entity_id="1",
        name="HIPAA (Security)",
        url="https://www.shl.com/products/product-catalog/view/hipaa-security/",
        test_type="K",
        categories=["Knowledge & Skills"],
        description="Measures HIPAA security knowledge.",
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
    index = build_catalog_index([personality, hipaa])

    matches = rank_catalog(
        index,
        "Healthcare admin role with HIPAA-critical work.",
        limit=1,
        preferred_categories=["skills", "personality"],
        required_terms=["HIPAA"],
    )

    assert matches[0].assessment.entity_id == "1"


def test_rank_catalog_boosts_known_aliases_to_canonical_assessment():
    verify_interactive = CatalogAssessment(
        entity_id="1",
        name="SHL Verify Interactive G+",
        url="https://www.shl.com/products/product-catalog/view/shl-verify-interactive-g/",
        test_type="A",
        categories=["Ability & Aptitude"],
        description="Interactive general ability assessment.",
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    verify_short = CatalogAssessment(
        entity_id="2",
        name="Verify - G+",
        url="https://www.shl.com/products/product-catalog/view/verify-g/",
        test_type="A",
        categories=["Ability & Aptitude"],
        description="General ability assessment.",
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    index = build_catalog_index([verify_short, verify_interactive])

    matches = rank_catalog(index, "Final list: Verify G+ and Graduate Scenarios.", limit=1)

    assert matches[0].assessment.entity_id == "1"


def test_rank_catalog_preserves_focus_coverage_for_full_battery_requests():
    ability = CatalogAssessment(
        entity_id="1",
        name="SHL Verify Interactive G+",
        url="https://www.shl.com/products/product-catalog/view/shl-verify-interactive-g/",
        test_type="A",
        categories=["Ability & Aptitude"],
        description="Interactive general ability assessment.",
        job_levels=["Graduate"],
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
        job_levels=["Graduate"],
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    situational = CatalogAssessment(
        entity_id="3",
        name="Graduate Scenarios",
        url="https://www.shl.com/products/product-catalog/view/graduate-scenarios/",
        test_type="B",
        categories=["Biodata & Situational Judgment"],
        description="Situational judgment scenarios for graduate hires.",
        job_levels=["Graduate"],
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    unrelated = CatalogAssessment(
        entity_id="4",
        name="Cardiology and Diabetes Management (New)",
        url="https://www.shl.com/products/product-catalog/view/cardiology-and-diabetes-management-new/",
        test_type="K",
        categories=["Knowledge & Skills"],
        description="Measures cardiology and diabetes knowledge.",
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    index = build_catalog_index([unrelated, situational, personality, ability])

    matches = rank_catalog(
        index,
        "Graduate management trainee full battery with cognitive personality and situational judgment coverage.",
        limit=3,
        preferred_categories=["ability", "personality", "situational judgment"],
        job_level_signals=["graduate"],
    )

    assert {match.assessment.entity_id for match in matches} == {"1", "2", "3"}


def test_rank_catalog_uses_language_and_locale_for_contact_center_simulations():
    svar_us = CatalogAssessment(
        entity_id="1",
        name="SVAR Spoken English (US) (New)",
        url="https://www.shl.com/products/product-catalog/view/svar-spoken-english-us-new/",
        test_type="K",
        categories=["Simulations"],
        description="Spoken English screening for US contact center calls.",
        languages=["English (USA)"],
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    svar_uk = CatalogAssessment(
        entity_id="2",
        name="SVAR Spoken English (UK) (New)",
        url="https://www.shl.com/products/product-catalog/view/svar-spoken-english-uk-new/",
        test_type="K",
        categories=["Simulations"],
        description="Spoken English screening for UK contact center calls.",
        languages=["English (UK)"],
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    generic = CatalogAssessment(
        entity_id="3",
        name="Contact Center Call Simulation (New)",
        url="https://www.shl.com/products/product-catalog/view/contact-center-call-simulation-new/",
        test_type="S",
        categories=["Simulations"],
        description="Customer service call simulation for contact center hiring.",
        languages=["English (USA)", "English (UK)"],
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    index = build_catalog_index([generic, svar_uk, svar_us])

    matches = rank_catalog(
        index,
        "High-volume contact centre screening for inbound English US calls.",
        limit=2,
        preferred_categories=["simulation"],
        required_terms=["contact center", "customer service", "English", "US"],
        language_signals=["English"],
        locale_signal="US",
    )

    assert matches[0].assessment.entity_id == "1"


def test_build_retrieval_query_adds_role_family_seed_assessments():
    query = build_retrieval_query(
        UserGoalProfile(
            latest_user_text="We run a graduate management trainee scheme and need a full battery.",
            role_titles=["Graduate management trainee"],
            assessment_focus=["ability", "personality", "situational judgment"],
        )
    )

    assert "Occupational Personality Questionnaire OPQ32r" in query.seed_assessment_names
    assert "SHL Verify Interactive G+" in query.seed_assessment_names
    assert "Graduate Scenarios" in query.seed_assessment_names


def test_build_retrieval_query_adds_customer_service_and_locale_specific_seeds():
    query = build_retrieval_query(
        UserGoalProfile(
            latest_user_text="We are screening entry-level contact centre agents for English US inbound calls.",
            role_titles=["Contact centre agents"],
            skills=["Customer Service"],
            assessment_focus=["simulation", "personality"],
            languages=["English"],
            locale="US",
        )
    )

    assert "Contact Center Call Simulation (New)" in query.seed_assessment_names
    assert "Customer Service Phone Simulation" in query.seed_assessment_names
    assert "Entry Level Customer Serv-Retail & Contact Center" in query.seed_assessment_names
    assert "SVAR Spoken English (US) (New)" in query.seed_assessment_names


def test_build_retrieval_query_adds_healthcare_admin_and_rust_infra_seeds():
    healthcare_query = build_retrieval_query(
        UserGoalProfile(
            latest_user_text="Hiring bilingual healthcare admin staff with patient records and HIPAA work.",
            role_titles=["Healthcare admin staff"],
            skills=["HIPAA"],
            assessment_focus=["skills", "personality"],
        )
    )
    rust_query = build_retrieval_query(
        UserGoalProfile(
            latest_user_text="Hiring a senior Rust engineer for high-performance networking infrastructure.",
            role_titles=["Rust engineer"],
            skills=["Rust", "Networking", "Linux"],
            assessment_focus=["skills"],
            seniority="senior",
        )
    )

    assert "Medical Terminology (New)" in healthcare_query.seed_assessment_names
    assert "Microsoft Word 365 - Essentials (New)" in healthcare_query.seed_assessment_names
    assert "Dependability and Safety Instrument (DSI)" in healthcare_query.seed_assessment_names
    assert "Occupational Personality Questionnaire OPQ32r" in healthcare_query.seed_assessment_names
    assert "Workplace Health and Safety (New)" not in healthcare_query.seed_assessment_names
    assert "SHL Verify Interactive G+" in rust_query.seed_assessment_names
    assert "Smart Interview Live Coding" in rust_query.seed_assessment_names
    assert "Linux Programming (General)" in rust_query.seed_assessment_names
    assert "Networking and Implementation (New)" in rust_query.seed_assessment_names


def test_build_retrieval_query_adds_verify_g_and_honors_rest_exclusion_for_senior_technical_refinement():
    query = build_retrieval_query(
        UserGoalProfile(
            latest_user_text="Add AWS and Docker. Drop REST - the API design signal will already come through in Spring and the live interview.",
            role_titles=["Senior Full-Stack Engineer"],
            skills=["Java", "SQL", "Angular", "AWS", "Docker", "Spring"],
            assessment_focus=["skills"],
            seniority="mid-level",
            excluded_terms=["REST"],
        )
    )

    assert "SHL Verify Interactive G+" in query.seed_assessment_names
    assert "RESTful Web Services (New)" not in query.seed_assessment_names


def test_build_retrieval_query_adds_safety_and_office_simulation_seeds():
    safety_query = build_retrieval_query(
        UserGoalProfile(
            latest_user_text="Hiring plant operators for a chemical facility where safety and compliance matter most.",
            role_titles=["Plant operators"],
            assessment_focus=["personality", "skills"],
        )
    )
    office_query = build_retrieval_query(
        UserGoalProfile(
            latest_user_text="Screen admin assistants for Excel and Word. Add simulations.",
            role_titles=["Admin assistants"],
            skills=["Excel", "Word"],
            assessment_focus=["skills", "simulation"],
        )
    )

    assert "Workplace Health and Safety (New)" in safety_query.seed_assessment_names
    assert "Manufac. & Indust. - Safety & Dependability 8.0" in safety_query.seed_assessment_names
    assert "Microsoft Excel 365 (New)" in office_query.seed_assessment_names
    assert "Microsoft Word 365 (New)" in office_query.seed_assessment_names


def test_build_retrieval_query_prefers_short_office_simulations_when_requested():
    office_query = build_retrieval_query(
        UserGoalProfile(
            latest_user_text="Screen admin assistants for Excel and Word with quick simulations.",
            role_titles=["Admin assistants"],
            skills=["Excel", "Word"],
            assessment_focus=["skills", "simulation"],
            constraints=["prefer_short"],
        )
    )

    assert "Microsoft Excel 365 - Essentials (New)" in office_query.seed_assessment_names
    assert "Microsoft Word 365 - Essentials (New)" in office_query.seed_assessment_names


def test_build_retrieval_query_adds_exact_contact_center_locale_seeds():
    query = build_retrieval_query(
        UserGoalProfile(
            latest_user_text="Hiring contact centre advisers for customer calls.",
            role_titles=["Contact centre advisers"],
            languages=["English"],
            locale="UK",
            assessment_focus=["simulation"],
        )
    )

    assert "Contact Center Call Simulation (New)" in query.seed_assessment_names
    assert "Entry Level Customer Serv-Retail & Contact Center" in query.seed_assessment_names
    assert "SVAR - Spoken English (U.K.)" in query.seed_assessment_names


def test_rank_catalog_boosts_seed_assessments_into_shortlist():
    excel = CatalogAssessment(
        entity_id="1",
        name="MS Excel (New)",
        url="https://www.shl.com/products/product-catalog/view/ms-excel-new/",
        test_type="K",
        categories=["Knowledge & Skills"],
        description="Measures Excel knowledge.",
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    word = CatalogAssessment(
        entity_id="2",
        name="MS Word (New)",
        url="https://www.shl.com/products/product-catalog/view/ms-word-new/",
        test_type="K",
        categories=["Knowledge & Skills"],
        description="Measures Word knowledge.",
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    opq = CatalogAssessment(
        entity_id="3",
        name="Occupational Personality Questionnaire OPQ32r",
        url="https://www.shl.com/products/product-catalog/view/occupational-personality-questionnaire-opq32r/",
        test_type="P",
        categories=["Personality & Behavior"],
        description="Measures workplace personality preferences.",
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    unrelated = CatalogAssessment(
        entity_id="4",
        name="Linux Administration (New)",
        url="https://www.shl.com/products/product-catalog/view/linux-administration-new/",
        test_type="K",
        categories=["Knowledge & Skills"],
        description="Measures Linux administration skills.",
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    index = build_catalog_index([unrelated, opq, word, excel])

    matches = rank_catalog(
        index,
        "Admin assistants who use Excel and Word daily.",
        limit=3,
        preferred_categories=["skills"],
        required_terms=["Excel", "Word"],
        seed_assessment_names=["Occupational Personality Questionnaire OPQ32r"],
    )

    assert {match.assessment.entity_id for match in matches} >= {"1", "2", "3"}


def test_rank_catalog_dedupes_report_variants_by_family():
    graduate = CatalogAssessment(
        entity_id="1",
        name="Graduate Scenarios",
        url="https://www.shl.com/products/product-catalog/view/graduate-scenarios/",
        test_type="B",
        categories=["Biodata & Situational Judgment"],
        description="Situational judgment scenarios for graduate hires.",
        job_levels=["Graduate"],
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    graduate_profile = CatalogAssessment(
        entity_id="2",
        name="Graduate Scenarios Profile Report",
        url="https://www.shl.com/products/product-catalog/view/graduate-scenarios-profile-report/",
        test_type="B",
        categories=["Biodata & Situational Judgment"],
        description="Profile report for Graduate Scenarios.",
        job_levels=["Graduate"],
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    verify = CatalogAssessment(
        entity_id="3",
        name="SHL Verify Interactive G+",
        url="https://www.shl.com/products/product-catalog/view/shl-verify-interactive-g/",
        test_type="A",
        categories=["Ability & Aptitude"],
        description="Interactive general ability assessment.",
        job_levels=["Graduate"],
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    verify_alias = CatalogAssessment(
        entity_id="4",
        name="Verify - G+",
        url="https://www.shl.com/products/product-catalog/view/verify-g/",
        test_type="A",
        categories=["Ability & Aptitude"],
        description="General ability assessment.",
        job_levels=["Graduate"],
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    index = build_catalog_index([verify_alias, graduate_profile, verify, graduate])

    matches = rank_catalog(
        index,
        "Graduate management trainee full battery with ability and situational judgment.",
        limit=4,
        preferred_categories=["ability", "situational judgment"],
        seed_assessment_names=["SHL Verify Interactive G+", "Graduate Scenarios"],
        job_level_signals=["graduate"],
    )

    assert [match.assessment.entity_id for match in matches] == ["3", "1"]


def test_rank_catalog_prunes_seeded_padding_when_battery_is_already_covered():
    verify = CatalogAssessment(
        entity_id="1",
        name="SHL Verify Interactive G+",
        url="https://www.shl.com/products/product-catalog/view/shl-verify-interactive-g/",
        test_type="A",
        categories=["Ability & Aptitude"],
        description="Interactive general ability assessment.",
        job_levels=["Graduate"],
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    opq = CatalogAssessment(
        entity_id="2",
        name="Occupational Personality Questionnaire OPQ32r",
        url="https://www.shl.com/products/product-catalog/view/occupational-personality-questionnaire-opq32r/",
        test_type="P",
        categories=["Personality & Behavior"],
        description="Measures workplace personality preferences.",
        job_levels=["Graduate"],
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    graduate = CatalogAssessment(
        entity_id="3",
        name="Graduate Scenarios",
        url="https://www.shl.com/products/product-catalog/view/graduate-scenarios/",
        test_type="B",
        categories=["Biodata & Situational Judgment"],
        description="Situational judgment scenarios for graduate hires.",
        job_levels=["Graduate"],
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    noisy = CatalogAssessment(
        entity_id="4",
        name="Digital Readiness Development Report - Manager",
        url="https://www.shl.com/products/product-catalog/view/digital-readiness-development-report-manager/",
        test_type="D",
        categories=["Ability & Aptitude"],
        description="Development report for digital readiness.",
        job_levels=["Graduate"],
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    index = build_catalog_index([noisy, graduate, opq, verify])

    matches = rank_catalog(
        index,
        "Graduate management trainee full battery with cognitive personality and situational judgement.",
        limit=4,
        preferred_categories=["ability", "personality", "situational judgment"],
        seed_assessment_names=[
            "SHL Verify Interactive G+",
            "Occupational Personality Questionnaire OPQ32r",
            "Graduate Scenarios",
        ],
        job_level_signals=["graduate"],
    )

    assert [match.assessment.entity_id for match in matches] == ["1", "2", "3"]


def test_rank_catalog_keeps_seeded_non_focus_match_with_multi_focus_queries():
    simulation = CatalogAssessment(
        entity_id="1",
        name="Contact Center Call Simulation (New)",
        url="https://www.shl.com/products/product-catalog/view/contact-center-call-simulation-new/",
        test_type="S",
        categories=["Simulations"],
        description="Call simulation for contact center roles.",
        job_levels=["Entry-Level"],
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    skills = CatalogAssessment(
        entity_id="2",
        name="Customer Service Phone Simulation",
        url="https://www.shl.com/products/product-catalog/view/customer-service-phone-simulation/",
        test_type="S",
        categories=["Simulations", "Knowledge & Skills"],
        description="Phone simulation for customer service roles.",
        job_levels=["Entry-Level"],
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    personality = CatalogAssessment(
        entity_id="3",
        name="Entry Level Customer Serv-Retail & Contact Center",
        url="https://www.shl.com/products/product-catalog/view/entry-level-customer-serv-retail-and-contact-center/",
        test_type="P",
        categories=["Personality & Behavior", "Competencies"],
        description="Entry-level retail and contact center customer service solution.",
        job_levels=["Entry-Level"],
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    filler_one = CatalogAssessment(
        entity_id="4",
        name="Retail Sales and Service Simulation",
        url="https://www.shl.com/products/product-catalog/view/retail-sales-and-service-simulation/",
        test_type="S",
        categories=["Simulations", "Knowledge & Skills"],
        description="Retail sales simulation.",
        job_levels=["Entry-Level"],
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    filler_two = CatalogAssessment(
        entity_id="5",
        name="Data Entry Numeric Split Screen - US",
        url="https://www.shl.com/products/product-catalog/view/data-entry-numeric-split-screen-us/",
        test_type="S",
        categories=["Simulations", "Knowledge & Skills"],
        description="Numeric data entry simulation.",
        job_levels=["Entry-Level"],
        eligible_for_recommendation=True,
        eligibility_source="eligible:catalog_product_record",
    )
    index = build_catalog_index([personality, filler_two, filler_one, skills, simulation])

    matches = rank_catalog(
        index,
        "entry-level contact center simulation and retail contact-center screen in english uk",
        limit=4,
        preferred_categories=["simulation", "skills"],
        required_terms=["English", "UK", "contact center", "entry-level"],
        seed_assessment_names=[
            "Contact Center Call Simulation (New)",
            "Customer Service Phone Simulation",
            "Entry Level Customer Serv-Retail & Contact Center",
        ],
    )

    assert [match.assessment.entity_id for match in matches] == ["1", "2", "3"]


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
        model="llama-3.3-70b-versatile",
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
        model="llama-3.3-70b-versatile",
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
