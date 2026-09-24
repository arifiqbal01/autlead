# app/pipelines/enrichment/people.py

from __future__ import annotations

from dataclasses import dataclass
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
from app.models.schemas.crawling import WebsiteContent
from app.models.schemas.people import PersonCandidate
from app.policies.qualification.people import (
    PersonDecisionMakerAssessment,
    evaluate_person_decision_maker,
)
from app.providers.llm.groq import GroqLLMProvider
from app.providers.llm.groq.errors import GroqProviderError
from app.transform.entity_resolution.people import resolve_people
from app.transform.normalization.person import normalize_person
from app.transform.scoring.people import (
    DecisionMakerConfidence,
    PersonRoleGroup,
    score_person,
)


logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ClassifiedPerson:
    """
    Person plus an already-evaluated decision-maker classification.

    AI may interpret the person's role, but ``is_decision_maker`` must
    already have passed Autlead policy.
    """

    person: PersonCandidate

    role_group: PersonRoleGroup
    is_decision_maker: bool
    confidence: DecisionMakerConfidence

    reason: str | None = None


@dataclass(frozen=True, slots=True)
class AnalyzedPerson:
    """
    Canonical person plus deterministic scoring and classification metadata.
    """

    person: PersonCandidate

    score: int
    role_group: PersonRoleGroup

    is_decision_maker: bool
    decision_maker_category: str | None

    confidence: DecisionMakerConfidence
    reasons: tuple[str, ...]

    @property
    def reasons_text(self) -> str:
        return " | ".join(
            self.reasons
        )


@dataclass(frozen=True, slots=True)
class PeopleAnalysisResult:
    """
    Result of normalization, entity resolution, scoring, and ranking.
    """

    people: list[AnalyzedPerson]

    input_count: int
    resolved_count: int
    duplicate_count: int

    @property
    def decision_makers(
        self,
    ) -> list[AnalyzedPerson]:
        return [
            person
            for person in self.people
            if person.is_decision_maker
        ]

    @property
    def decision_maker_count(
        self,
    ) -> int:
        return len(
            self.decision_makers
        )


# ---------------------------------------------------------------------------
# Enrichment orchestration
# ---------------------------------------------------------------------------


async def enrich_people(
    *,
    session: AsyncSession,
    company_id: int,
    company_name: str,
    pages: list[WebsiteContent],
    homepage_url: str,
    provider_name: str,
    groq_provider: GroqLLMProvider,
    source_id: int | None = None,
    decision_maker_limit: int = 5,
    language: str = "nl",
) -> PeopleAnalysisResult:
    """
    Extract, classify, analyze, and persist people for one company.

    Flow:

        crawled business pages
            ↓
        deterministic extraction
            ↓
        AI role/authority assessment
            ↓
        Autlead decision-maker policy
            ↓
        normalization + entity resolution
            ↓
        deterministic scoring + ranking
            ↓
        persistence

    AI interprets role semantics.

    Autlead policy decides whether the AI assessment is accepted.

    A Groq provider failure does not fail people enrichment; deterministic
    candidates are retained with a conservative unknown/low classification.

    Transaction ownership belongs to the caller.
    """

    # ------------------------------------------------------------------
    # 1. Deterministic extraction
    # ------------------------------------------------------------------

    extracted_people: list[PersonCandidate] = []

    logger.info(
        "people_extraction_started",
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
            "people_page_extracted",
            company_id=company_id,
            company_name=company_name,
            url=str(content.url),
            extracted=len(page_people),
        )

    logger.info(
        "people_extraction_completed",
        company_id=company_id,
        company_name=company_name,
        pages=len(pages),
        extracted_people=len(extracted_people),
    )

    # ------------------------------------------------------------------
    # 2. AI refinement / assessment
    # ------------------------------------------------------------------

    ai_people: list[AIRefinedPerson]

    if pages:
        logger.info(
            "people_ai_refinement_started",
            company_id=company_id,
            company_name=company_name,
            candidates=len(extracted_people),
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
                "people_ai_refinement_completed",
                company_id=company_id,
                company_name=company_name,
                input_candidates=len(extracted_people),
                refined_people=len(ai_people),
            )

        except GroqProviderError as exc:
            logger.warning(
                "people_ai_refinement_failed",
                company_id=company_id,
                company_name=company_name,
                error_type=type(exc).__name__,
                error=str(exc),
                fallback="deterministic_candidates",
            )

            ai_people = _build_fallback_people(
                extracted_people
            )

    else:
        ai_people = _build_fallback_people(
            extracted_people
        )

    # ------------------------------------------------------------------
    # 3. Autlead policy evaluation
    # ------------------------------------------------------------------

    classified_people: list[ClassifiedPerson] = []

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

    logger.info(
        "people_classification_completed",
        company_id=company_id,
        company_name=company_name,
        classified_people=len(classified_people),
    )

    # ------------------------------------------------------------------
    # 4. Analysis
    # ------------------------------------------------------------------

    people_result = analyze_people(
        classified_people,
        language=language,
        decision_maker_limit=decision_maker_limit,
    )

    logger.info(
        "people_analysis_completed",
        company_id=company_id,
        company_name=company_name,
        extracted_people=len(extracted_people),
        refined_people=len(ai_people),
        input_people=people_result.input_count,
        resolved_people=people_result.resolved_count,
        duplicates_removed=people_result.duplicate_count,
        people=len(people_result.people),
        decision_makers=people_result.decision_maker_count,
    )

    # ------------------------------------------------------------------
    # 5. Persistence
    # ------------------------------------------------------------------

    observed_at = datetime.now(UTC)

    persisted_people = 0
    persisted_decision_makers = 0

    for analyzed_person in people_result.people:
        person_candidate = analyzed_person.person

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
            normalized_name=normalized_name,
            title=person_candidate.title,
            linkedin_url=(
                str(person_candidate.linkedin_url)
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
                str(person_candidate.source_url)
                if person_candidate.source_url
                else homepage_url
            ),
            name=person_candidate.name,
            title=person_candidate.title,
            linkedin_url=(
                str(person_candidate.linkedin_url)
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
        "people_persistence_completed",
        company_id=company_id,
        company_name=company_name,
        persisted_people=persisted_people,
        persisted_decision_makers=(
            persisted_decision_makers
        ),
    )

    return people_result


# ---------------------------------------------------------------------------
# Deterministic analysis
# ---------------------------------------------------------------------------


def analyze_people(
    people: list[ClassifiedPerson],
    *,
    language: str = "nl",
    decision_maker_limit: int | None = None,
) -> PeopleAnalysisResult:
    """
    Normalize, resolve, score, and rank already-classified people.

    This function performs deterministic analysis only.
    """

    if not people:
        logger.info(
            "people_analysis_skipped",
            reason="no_people",
            input_people=0,
        )

        return PeopleAnalysisResult(
            people=[],
            input_count=0,
            resolved_count=0,
            duplicate_count=0,
        )

    logger.info(
        "people_deterministic_analysis_started",
        input_people=len(people),
        language=language,
    )

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    normalized_people = [
        ClassifiedPerson(
            person=normalize_person(
                item.person,
                language=language,
            ),
            role_group=item.role_group,
            is_decision_maker=(
                item.is_decision_maker
            ),
            confidence=item.confidence,
            reason=item.reason,
        )
        for item in people
    ]

    logger.info(
        "people_normalization_completed",
        input_people=len(people),
        normalized_people=len(normalized_people),
    )

    # ------------------------------------------------------------------
    # Entity resolution
    # ------------------------------------------------------------------

    candidate_people = [
        item.person
        for item in normalized_people
    ]

    resolved = resolve_people(
        candidate_people,
        language=language,
    )

    duplicate_count = (
        len(candidate_people)
        - len(resolved)
    )

    logger.info(
        "people_entity_resolution_completed",
        normalized_people=len(candidate_people),
        resolved_people=len(resolved),
        duplicates_removed=duplicate_count,
    )

    # ------------------------------------------------------------------
    # Classification lookup
    # ------------------------------------------------------------------

    classified_by_identity = (
        _build_classification_lookup(
            normalized_people
        )
    )

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    analyzed: list[AnalyzedPerson] = []

    for resolved_person in resolved:
        person = resolved_person.person

        classification = _find_classification(
            person,
            classified_by_identity,
        )

        if classification is None:
            classification = ClassifiedPerson(
                person=person,
                role_group="unknown",
                is_decision_maker=False,
                confidence="low",
                reason=None,
            )

        person_score = score_person(
            person,
            role_group=classification.role_group,
            is_decision_maker=(
                classification.is_decision_maker
            ),
            decision_maker_confidence=(
                classification.confidence
            ),
        )

        reasons = list(
            person_score.reasons
        )

        if classification.reason:
            reasons.append(
                classification.reason
            )

        analyzed.append(
            AnalyzedPerson(
                person=person,
                score=person_score.score,
                role_group=classification.role_group,
                is_decision_maker=(
                    classification.is_decision_maker
                ),
                decision_maker_category=(
                    classification.role_group
                    if classification.is_decision_maker
                    else None
                ),
                confidence=classification.confidence,
                reasons=tuple(reasons),
            )
        )

    # ------------------------------------------------------------------
    # Ranking
    # ------------------------------------------------------------------

    ranked = sorted(
        analyzed,
        key=lambda item: (
            not item.is_decision_maker,
            -item.score,
            _confidence_rank(
                item.confidence
            ),
            item.person.name.casefold(),
        ),
    )

    if (
        decision_maker_limit is not None
        and decision_maker_limit >= 0
    ):
        ranked = _limit_decision_makers(
            ranked,
            limit=decision_maker_limit,
        )

    result = PeopleAnalysisResult(
        people=ranked,
        input_count=len(people),
        resolved_count=len(resolved),
        duplicate_count=duplicate_count,
    )

    logger.info(
        "people_deterministic_analysis_completed",
        input_people=result.input_count,
        resolved_people=result.resolved_count,
        duplicates_removed=result.duplicate_count,
        people=len(result.people),
        decision_makers=result.decision_maker_count,
        primary=sum(
            1
            for item in result.decision_makers
            if item.decision_maker_category == "primary"
        ),
        secondary=sum(
            1
            for item in result.decision_makers
            if item.decision_maker_category == "secondary"
        ),
    )

    return result


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------


def select_decision_makers(
    result: PeopleAnalysisResult,
    *,
    limit: int = 5,
) -> list[AnalyzedPerson]:
    if limit <= 0:
        return []

    return result.decision_makers[
        :limit
    ]


def select_best_decision_maker(
    result: PeopleAnalysisResult,
) -> AnalyzedPerson | None:
    if not result.decision_makers:
        return None

    return result.decision_makers[0]


# ---------------------------------------------------------------------------
# AI fallback
# ---------------------------------------------------------------------------


def _build_fallback_people(
    people: list[PersonCandidate],
) -> list[AIRefinedPerson]:
    """
    Preserve deterministic candidates when AI refinement is unavailable.
    """

    return [
        AIRefinedPerson(
            person=person,
            ai_decision_maker=False,
            role_group="unknown",
            decision_maker_confidence="low",
            decision_maker_reason=None,
            evidence=None,
        )
        for person in people
    ]


# ---------------------------------------------------------------------------
# Classification preservation
# ---------------------------------------------------------------------------


def _build_classification_lookup(
    people: list[ClassifiedPerson],
) -> dict[str, ClassifiedPerson]:
    result: dict[
        str,
        ClassifiedPerson,
    ] = {}

    for item in people:
        for key in _person_identity_keys(
            item.person
        ):
            existing = result.get(
                key
            )

            if (
                existing is None
                or _classification_priority(item)
                > _classification_priority(existing)
            ):
                result[key] = item

    return result


def _find_classification(
    person: PersonCandidate,
    lookup: dict[
        str,
        ClassifiedPerson,
    ],
) -> ClassifiedPerson | None:
    for key in _person_identity_keys(
        person
    ):
        classification = lookup.get(
            key
        )

        if classification is not None:
            return classification

    return None


def _person_identity_keys(
    person: PersonCandidate,
) -> tuple[str, ...]:
    keys: list[str] = []

    if person.linkedin_url:
        keys.append(
            f"linkedin:{str(person.linkedin_url).casefold()}"
        )

    normalized_name = (
        " ".join(
            person.name.split()
        )
        .casefold()
    )

    if normalized_name:
        keys.append(
            f"name:{normalized_name}"
        )

    return tuple(
        keys
    )


def _classification_priority(
    person: ClassifiedPerson,
) -> tuple[int, int, int]:
    role_rank = {
        "primary": 5,
        "secondary": 4,
        "professional": 3,
        "other": 2,
        "unknown": 1,
    }

    confidence_rank = {
        "high": 3,
        "medium": 2,
        "low": 1,
    }

    return (
        1
        if person.is_decision_maker
        else 0,
        role_rank.get(
            person.role_group,
            0,
        ),
        confidence_rank.get(
            person.confidence,
            0,
        ),
    )


# ---------------------------------------------------------------------------
# Limit helpers
# ---------------------------------------------------------------------------


def _limit_decision_makers(
    people: list[AnalyzedPerson],
    *,
    limit: int,
) -> list[AnalyzedPerson]:
    if limit < 0:
        return people

    decision_makers_seen = 0
    result: list[AnalyzedPerson] = []

    for person in people:
        if person.is_decision_maker:
            if decision_makers_seen >= limit:
                continue

            decision_makers_seen += 1

        result.append(
            person
        )

    return result


# ---------------------------------------------------------------------------
# Confidence helpers
# ---------------------------------------------------------------------------


def _confidence_rank(
    value: str,
) -> int:
    return {
        "high": 0,
        "medium": 1,
        "low": 2,
    }.get(
        value,
        3,
    )