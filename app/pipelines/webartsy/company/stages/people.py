# app/pipelines/webartsy/stages/people.py

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.extract.people import (
    extract_people_from_website,
    refine_people_with_ai,
)
from app.extract.people.ai import AIRefinedPerson
from app.load.postgres.people import (
    load_person,
    load_person_observation,
)
from app.pipelines.common.people import (
    ClassifiedPerson,
    PeopleAnalysisResult,
    analyze_people,
)
from app.policies.qualification.people import (
    PersonDecisionMakerAssessment,
    evaluate_person_decision_maker,
)
from app.providers.llm.groq import (
    GroqLLMProvider,
)
from app.providers.llm.groq.errors import (
    GroqProviderError,
)


logger = get_logger(__name__)


async def run_people_stage(
    *,
    session: AsyncSession,
    company_id: int,
    company_name: str,
    pages: list,
    homepage_url: str,
    provider_name: str,
    groq_provider: GroqLLMProvider,
    source_id: int | None = None,
    decision_maker_limit: int = 5,
    language: str = "nl",
) -> PeopleAnalysisResult:
    """
    Run WebArtsy people extraction, AI assessment,
    policy evaluation, analysis, and persistence.

    Pipeline:

        crawled business pages
            ↓
        deterministic extraction
            ↓
        one Groq request per company
            ↓
        semantic role/authority assessment
            ↓
        Autlead decision-maker policy
            ↓
        common people analysis/scoring
            ↓
        persistence

    Groq interprets role semantics.

    Autlead policy decides whether that assessment is accepted.

    Groq failure does not fail the people stage.
    """

    # =========================================================
    # 1. DETERMINISTIC EXTRACTION
    # =========================================================

    extracted_people = []

    logger.info(
        "webartsy_people_extraction_started",
        company_id=company_id,
        company_name=company_name,
        pages=len(pages),
    )

    for content in pages:
        page_people = extract_people_from_website(
            text=content.text or "",
            html=content.html or "",
            source_url=str(content.url),
            language=language,
        )

        extracted_people.extend(
            page_people
        )

        logger.info(
            "webartsy_people_page_extracted",
            company_id=company_id,
            company_name=company_name,
            url=str(content.url),
            extracted=len(page_people),
        )

    logger.info(
        "webartsy_people_extraction_completed",
        company_id=company_id,
        company_name=company_name,
        pages=len(pages),
        extracted_people=len(
            extracted_people
        ),
    )

    # =========================================================
    # 2. GROQ REFINEMENT / ASSESSMENT
    # =========================================================

    ai_people: list[AIRefinedPerson]

    if pages:
        logger.info(
            "webartsy_people_ai_refinement_started",
            company_id=company_id,
            company_name=company_name,
            candidates=len(
                extracted_people
            ),
        )

        try:
            ai_people = await refine_people_with_ai(
                provider=groq_provider,
                company_name=company_name,
                homepage_url=homepage_url,
                pages=pages,
                candidates=extracted_people,
            )

            logger.info(
                "webartsy_people_ai_refinement_completed",
                company_id=company_id,
                company_name=company_name,
                input_candidates=len(
                    extracted_people
                ),
                refined_people=len(
                    ai_people
                ),
            )

        except GroqProviderError as exc:
            logger.warning(
                "webartsy_people_ai_refinement_failed",
                company_id=company_id,
                company_name=company_name,
                error_type=type(exc).__name__,
                error=str(exc),
                fallback="deterministic_candidates",
            )

            ai_people = [
                AIRefinedPerson(
                    person=person,
                    ai_decision_maker=False,
                    role_group="unknown",
                    decision_maker_confidence="low",
                    decision_maker_reason=None,
                    evidence=None,
                )
                for person in extracted_people
            ]

    else:
        ai_people = [
            AIRefinedPerson(
                person=person,
                ai_decision_maker=False,
                role_group="unknown",
                decision_maker_confidence="low",
                decision_maker_reason=None,
                evidence=None,
            )
            for person in extracted_people
        ]

    # =========================================================
    # 3. POLICY EVALUATION
    # =========================================================

    classified_people = []

    for refined in ai_people:
        assessment = PersonDecisionMakerAssessment(
            role_group=refined.role_group,
            confidence=(
                refined.decision_maker_confidence
            ),
            ai_decision_maker=(
                refined.ai_decision_maker
            ),
            reason=(
                refined.decision_maker_reason
            ),
        )

        decision = evaluate_person_decision_maker(
            assessment
        )

        classified_people.append(
            ClassifiedPerson(
                person=refined.person,
                role_group=decision.role_group,
                is_decision_maker=(
                    decision.is_decision_maker
                ),
                confidence=decision.confidence,
                reason=decision.reason,
            )
        )

    # =========================================================
    # 4. PEOPLE ANALYSIS
    # =========================================================

    people_result = analyze_people(
        classified_people,
        language=language,
        decision_maker_limit=(
            decision_maker_limit
        ),
    )

    logger.info(
        "webartsy_people_analysis_completed",
        company_id=company_id,
        company_name=company_name,
        extracted_people=len(
            extracted_people
        ),
        refined_people=len(
            ai_people
        ),
        input_people=(
            people_result.input_count
        ),
        resolved_people=(
            people_result.resolved_count
        ),
        duplicates_removed=(
            people_result.duplicate_count
        ),
        people=len(
            people_result.people
        ),
        decision_makers=(
            people_result.decision_maker_count
        ),
    )

    # =========================================================
    # 5. PERSISTENCE
    # =========================================================

    observed_at = datetime.now(
        UTC
    )

    persisted_people = 0
    persisted_decision_makers = 0

    for analyzed_person in (
        people_result.people
    ):
        person_candidate = (
            analyzed_person.person
        )

        normalized_name = (
            " ".join(
                person_candidate.name.split()
            )
            .casefold()
        )

        person = await load_person(
            session,
            company_id=company_id,
            name=person_candidate.name,
            normalized_name=(
                normalized_name
            ),
            title=(
                person_candidate.title
            ),
            linkedin_url=(
                str(
                    person_candidate.linkedin_url
                )
                if person_candidate.linkedin_url
                else None
            ),
        )

        await load_person_observation(
            session,
            person_id=person.id,
            company_id=company_id,
            provider_name=provider_name,
            source_url=(
                str(
                    person_candidate.source_url
                )
                if person_candidate.source_url
                else homepage_url
            ),
            name=person_candidate.name,
            title=person_candidate.title,
            linkedin_url=(
                str(
                    person_candidate.linkedin_url
                )
                if person_candidate.linkedin_url
                else None
            ),
            source_id=source_id,
            decision_maker_score=(
                analyzed_person.score
            ),
            decision_maker_role_group=(
                analyzed_person.role_group
            ),
            decision_maker_confidence=(
                analyzed_person.confidence
            ),
            decision_maker_reasons=(
                analyzed_person.reasons_text
            ),
            observed_at=observed_at,
        )

        persisted_people += 1

        if analyzed_person.is_decision_maker:
            persisted_decision_makers += 1

    logger.info(
        "webartsy_people_persistence_completed",
        company_id=company_id,
        company_name=company_name,
        persisted_people=(
            persisted_people
        ),
        persisted_decision_makers=(
            persisted_decision_makers
        ),
    )

    return people_result