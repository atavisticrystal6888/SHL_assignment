# Data Model: Conversational SHL Assessment Recommender

## Entity: ChatRequest

**Purpose**: Stateless API input for the next assistant response.

**Fields**:
- `messages`: ordered list of `ConversationMessage`; required; must include the full conversation history.

**Validation Rules**:
- `messages` must not be omitted.
- Empty histories are invalid for recommendation but may receive a schema-safe clarification/error reply with empty recommendations.
- The service must not read or write server-side conversation state.

## Entity: ConversationMessage

**Purpose**: One turn in the submitted conversation history.

**Fields**:
- `role`: string enum; `user` or `assistant` for evaluator conversations.
- `content`: non-empty string after trimming.

**Validation Rules**:
- Unsupported roles must not be trusted for instruction hierarchy.
- Blank or non-string content must produce a safe response or validation error path with empty recommendations.
- Only the submitted history may be used to derive conversational context.

## Entity: UserGoalProfile

**Purpose**: Derived, non-persistent representation of the hiring need.

**Fields**:
- `role_titles`: list of extracted role names or role families.
- `skills`: list of required technical, behavioral, cognitive, language, or domain skills.
- `seniority`: optional seniority or experience band.
- `years_experience`: optional numeric or textual experience signal.
- `assessment_focus`: list of desired dimensions such as knowledge, skills, personality, aptitude, simulation, or situational judgment.
- `constraints`: list of user constraints such as duration, language, remote testing, or excluded assessment types.
- `corrections`: list of later facts that override earlier facts.
- `missing_decision_factors`: list of high-value facts still needed before recommending.
- `latest_intent`: enum: `clarify`, `recommend`, `refine`, `compare`, `refuse`, or `complete`.

**Relationships**:
- Derived from `ConversationHistory` on every request.
- Feeds `AgentDecision` and `RetrievalQuery`.

**Validation Rules**:
- Later user corrections take precedence over earlier contradictory facts.
- Missing facts must trigger at most one high-value clarification at a time.
- The profile must be rebuilt per request and never stored as session state.

## Entity: CatalogAssessment

**Purpose**: Canonical SHL product record used for retrieval, ranking, recommendation, and comparison.

**Fields**:
- `entity_id`: stable catalog identifier.
- `name`: catalog assessment name.
- `url`: catalog source URL.
- `test_type`: evaluator-facing test type code derived from catalog categories or curated mapping.
- `categories`: list of catalog categories or keys.
- `description`: catalog description text.
- `duration`: display duration or empty/unknown value.
- `duration_minutes`: optional normalized numeric duration when parseable.
- `remote_testing`: yes/no/unknown.
- `adaptive_irt`: yes/no/unknown.
- `job_levels`: list of supported job levels.
- `languages`: list of supported languages.
- `status`: scrape status.
- `eligible_for_recommendation`: boolean indicating Individual Test Solution eligibility.
- `eligibility_source`: evidence string or curated mapping reason proving the record is eligible.
- `source_snapshot`: catalog scrape timestamp or version marker.

**Relationships**:
- One `RecommendationItem` must reference one `CatalogAssessment`.
- One `ComparisonAnswer` may reference two or more `CatalogAssessment` records.
- One `EvaluationRun` validates recommendations against this catalog set.

**Validation Rules**:
- Recommendation output must only use records where `eligible_for_recommendation` is true.
- Records without source metadata or curated mapping that proves Individual Test Solution eligibility must default to ineligible.
- `name`, `url`, and `test_type` must be present before an item can be recommended.
- URLs must match the canonical catalog URL set exactly.
- Missing catalog fields must be represented as unknown rather than fabricated.

## Entity: RetrievalQuery

**Purpose**: Search/ranking input derived from the user goal and conversation state.

**Fields**:
- `query_text`: normalized user need or job-description summary.
- `required_terms`: important terms that must influence ranking.
- `preferred_categories`: desired catalog categories or test types.
- `job_level_signals`: mapped job levels from role/seniority.
- `constraints`: duration, language, remote, adaptive, or exclusion filters.
- `comparison_targets`: assessment names or aliases for comparison intent.

**Relationships**:
- Built from `UserGoalProfile`.
- Produces ranked `CatalogMatch` results.

**Validation Rules**:
- Must not include hidden instructions or prompt-injection text as ranking commands.
- Must preserve enough raw user language to handle uncommon skills.

## Entity: CatalogMatch

**Purpose**: Internal ranked candidate before final recommendation.

**Fields**:
- `assessment`: reference to `CatalogAssessment`.
- `score`: numeric ranking score.
- `matched_fields`: list of catalog fields contributing to score.
- `rationale_facts`: catalog facts used to explain the match.
- `warnings`: list of caveats such as missing exact skill match.

**Validation Rules**:
- Matches from ineligible records may support comparison but must not enter final recommendations.
- Ranking rationale must reference catalog facts or extracted user facts.

## Entity: AgentDecision

**Purpose**: Explicit policy decision for the current response.

**Fields**:
- `action`: enum: `clarify`, `recommend`, `refine`, `compare`, `refuse`, `complete`, `malformed_input`.
- `reason`: short policy reason.
- `requires_retrieval`: boolean.
- `recommendations_allowed`: boolean.
- `end_allowed`: boolean.
- `clarification_question`: optional `ClarificationQuestion`.

**State Transitions**:
- `clarify` -> `recommend` when enough context is supplied.
- `recommend` -> `refine` when the user changes constraints.
- `recommend` -> `complete` when the user confirms satisfaction.
- Any state -> `refuse` for out-of-scope or prompt-injection requests.
- Any state -> `compare` when the latest user asks for assessment differences.

**Validation Rules**:
- `recommendations_allowed` must be false for `clarify`, `refuse`, and `malformed_input`.
- `end_allowed` must be true only when the user task is complete.

## Entity: ClarificationQuestion

**Purpose**: High-value follow-up used before recommendation.

**Fields**:
- `question`: concise user-facing text.
- `missing_factor`: role, seniority, skills, focus, constraints, or comparison target.
- `why_needed`: internal reason tied to ranking or scope.

**Validation Rules**:
- Must not ask for low-value details that would risk the 8-turn cap.
- Must not repeat a question the user already answered or declined.

## Entity: RecommendationItem

**Purpose**: Public recommendation response object.

**Fields**:
- `name`: catalog assessment name.
- `url`: catalog URL.
- `test_type`: evaluator-facing test type code.

**Validation Rules**:
- Must be derived from an eligible `CatalogAssessment`.
- Must include exactly the required fields unless later evaluator guidance permits more.
- Must not appear in clarification, refusal, or malformed-input responses.
- Total recommendation count must be 1 to 10 after commitment.

## Entity: ChatResponse

**Purpose**: Public response from `POST /chat`.

**Fields**:
- `reply`: assistant text.
- `recommendations`: list of `RecommendationItem`.
- `end_of_conversation`: boolean.

**Validation Rules**:
- Must contain exactly these top-level fields.
- `recommendations` must be empty unless `AgentDecision.recommendations_allowed` is true.
- `end_of_conversation` must be true only when the agent considers the task complete.

## Entity: ConversationTrace

**Purpose**: Development/evaluation fixture for replay.

**Fields**:
- `trace_id`: stable ID such as `C1`.
- `persona_facts`: extracted user facts when available.
- `turns`: ordered user/agent turns from the public trace.
- `expected_shortlist`: catalog names/URLs inferred from labeled final recommendations.
- `notes`: trace-specific caveats.

**Validation Rules**:
- Public traces must be parsed before implementation work completes.
- Expected shortlist entries must be resolved to canonical catalog records before Recall@10 measurement.

## Entity: BehaviorProbe

**Purpose**: Binary test scenario for a required behavior.

**Fields**:
- `probe_id`: stable identifier.
- `conversation`: list of submitted request histories.
- `assertion`: expected behavior such as refusal or no early recommendation.
- `expected_result`: pass/fail predicate.

**Validation Rules**:
- Probe coverage must include off-topic refusal, vague-turn clarification, user-edit honoring, grounded comparison, hallucination resistance, and conversational coherence.

## Entity: EvaluationRun

**Purpose**: Recorded validation result for replay and probes.

**Fields**:
- `run_id`: timestamp or stable run identifier.
- `schema_pass`: boolean.
- `catalog_only_pass`: boolean.
- `turn_cap_pass`: boolean.
- `timeout_pass`: boolean.
- `recall_at_10`: optional numeric score.
- `probe_results`: map of probe ID to pass/fail.
- `failures`: list of actionable failure summaries.

**Validation Rules**:
- Failures must identify whether the root issue is schema, catalog grounding, retrieval/ranking, policy, timeout, or prompt generation.

## Entity: ApproachDocument

**Purpose**: Two-page submission document.

**Fields**:
- `design_choices`: summary of architecture and trade-offs.
- `retrieval_setup`: catalog fields and ranking strategy.
- `prompt_design`: grounded prompt/control strategy.
- `evaluation_approach`: traces, Recall@10, probes, and hard checks.
- `failed_approaches`: what did not work.
- `measurement_summary`: how improvement was measured.
- `ai_tool_usage`: what AI tools were used for.

**Validation Rules**:
- Must be no more than two pages.
- Must be consistent with implemented behavior and recorded evaluation results.
