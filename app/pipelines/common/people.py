# app/pipelines/common/people.py

from __future__ import annotations

from dataclasses import dataclass

from app.core.logging import get_logger
from app.models.schemas.people import PersonCandidate
from app.transform.entity_resolution.people import (
    resolve_people,
)
from app.transform.normalization.person import (
    normalize_person,
)
from app.transform.scoring.people import (
    DecisionMakerConfidence,
    PersonRoleGroup,
    score_person,
)


logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Input / result models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ClassifiedPerson:
    """
    Person plus an already-evaluated decision-maker classification.

    Role interpretation may come from an AI assessment, but the final
    is_decision_maker value must already have passed Autlead policy.
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
# Public API
# ---------------------------------------------------------------------------


def analyze_people(
    people: list[ClassifiedPerson],
    *,
    language: str = "nl",
    decision_maker_limit: int | None = None,
) -> PeopleAnalysisResult:
    """
    Normalize, resolve, score, and rank already-classified people.

    Pipeline:

        ClassifiedPerson[]
            ↓
        deterministic normalization
            ↓
        entity resolution
            ↓
        preserve accepted classification metadata
            ↓
        deterministic scoring
            ↓
        ranking
            ↓
        AnalyzedPerson[]

    This function does not:

        - crawl websites
        - extract people
        - call an LLM
        - decide whether AI classification should be accepted
        - persist data
        - access the database
        - determine company lead quality
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
        "people_analysis_started",
        input_people=len(people),
        language=language,
    )

    # =========================================================
    # 1. NORMALIZATION
    # =========================================================

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
        normalized_people=len(
            normalized_people
        ),
    )

    # =========================================================
    # 2. ENTITY RESOLUTION
    # =========================================================

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
        normalized_people=len(
            candidate_people
        ),
        resolved_people=len(
            resolved
        ),
        duplicates_removed=duplicate_count,
    )

    # =========================================================
    # 3. CLASSIFICATION LOOKUP
    # =========================================================

    classified_by_identity = (
        _build_classification_lookup(
            normalized_people
        )
    )

    # =========================================================
    # 4. SCORING
    # =========================================================

    analyzed: list[AnalyzedPerson] = []

    for resolved_person in resolved:
        person = resolved_person.person

        classification = (
            _find_classification(
                person,
                classified_by_identity,
            )
        )

        if classification is None:
            # Defensive fallback.
            classification = ClassifiedPerson(
                person=person,
                role_group="unknown",
                is_decision_maker=False,
                confidence="low",
                reason=None,
            )

        person_score = score_person(
            person,
            role_group=(
                classification.role_group
            ),
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
                role_group=(
                    classification.role_group
                ),
                is_decision_maker=(
                    classification.is_decision_maker
                ),
                decision_maker_category=(
                    classification.role_group
                    if classification.is_decision_maker
                    else None
                ),
                confidence=(
                    classification.confidence
                ),
                reasons=tuple(
                    reasons
                ),
            )
        )

    # =========================================================
    # 5. RANKING
    # =========================================================

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
        "people_analysis_completed",
        input_people=result.input_count,
        resolved_people=(
            result.resolved_count
        ),
        duplicates_removed=(
            result.duplicate_count
        ),
        people=len(
            result.people
        ),
        decision_makers=(
            result.decision_maker_count
        ),
        primary=sum(
            1
            for item in result.decision_makers
            if (
                item.decision_maker_category
                == "primary"
            )
        ),
        secondary=sum(
            1
            for item in result.decision_makers
            if (
                item.decision_maker_category
                == "secondary"
            )
        ),
    )

    return result


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
# Classification preservation
# ---------------------------------------------------------------------------


def _build_classification_lookup(
    people: list[ClassifiedPerson],
) -> dict[str, ClassifiedPerson]:
    """
    Build a lookup used to preserve classification metadata through
    entity resolution.
    """

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
                or _classification_priority(
                    item
                )
                > _classification_priority(
                    existing
                )
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
    """
    Pick the strongest classification when duplicate people merge.
    """

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
    result: list[
        AnalyzedPerson
    ] = []

    for person in people:
        if person.is_decision_maker:
            if (
                decision_makers_seen
                >= limit
            ):
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