from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, and_, exists, or_, select
from sqlalchemy.orm import aliased

from app.models.persistence.company import Company
from app.models.persistence.contact_observation import ContactObservation
from app.models.persistence.person import Person
from app.models.persistence.person_observation import PersonObservation
from app.models.persistence.website_performance import WebsitePerformance
from app.models.persistence.webartsy_stage_state import WebArtsyStageState


@dataclass(frozen=True, slots=True)
class WebArtsyExportFilters:
    """Optional filters for saved WebArtsy lead exports.

    Filters compose with AND semantics. For example, supplying
    ``has_website=True`` and ``has_email=True`` exports companies that
    have both a website and at least one persisted email observation.
    """

    country: str | None = None
    city: str | None = None
    category: str | None = None

    created_after: datetime | None = None
    created_before: datetime | None = None
    updated_after: datetime | None = None
    updated_before: datetime | None = None
    enriched_after: datetime | None = None
    enriched_before: datetime | None = None

    has_website: bool = False
    has_people: bool = False
    has_decision_maker: bool = False

    has_performance: bool = False
    min_performance: int | None = None
    max_performance: int | None = None
    min_seo: int | None = None
    max_seo: int | None = None

    has_email: bool = False
    has_phone: bool = False

    has_linkedin: bool = False
    has_company_linkedin: bool = False
    has_person_linkedin: bool = False

    limit: int | None = None

    def __post_init__(self) -> None:
        _validate_score("min_performance", self.min_performance)
        _validate_score("max_performance", self.max_performance)
        _validate_score("min_seo", self.min_seo)
        _validate_score("max_seo", self.max_seo)

        if (
            self.min_performance is not None
            and self.max_performance is not None
            and self.min_performance > self.max_performance
        ):
            raise ValueError(
                "min_performance cannot be greater than max_performance"
            )

        if (
            self.min_seo is not None
            and self.max_seo is not None
            and self.min_seo > self.max_seo
        ):
            raise ValueError(
                "min_seo cannot be greater than max_seo"
            )

        if self.limit is not None and self.limit <= 0:
            raise ValueError("limit must be greater than 0")


def apply_webartsy_export_filters(
    query: Select[tuple[Company]],
    filters: WebArtsyExportFilters | None,
) -> Select[tuple[Company]]:
    """Apply composable WebArtsy export filters to a Company query."""

    if filters is None:
        return query

    if filters.country:
        query = query.where(
            Company.country.ilike(filters.country.strip())
        )

    if filters.city:
        query = query.where(
            Company.city.ilike(filters.city.strip())
        )

    if filters.category:
        category = filters.category.strip()
        query = query.where(
            Company.category.ilike(f"%{category}%")
        )

    if filters.created_after is not None:
        query = query.where(
            Company.created_at >= filters.created_after
        )

    if filters.created_before is not None:
        query = query.where(
            Company.created_at < filters.created_before
        )

    if filters.updated_after is not None:
        query = query.where(
            Company.updated_at >= filters.updated_after
        )

    if filters.updated_before is not None:
        query = query.where(
            Company.updated_at < filters.updated_before
        )

    latest_enriched_at = (
        select(WebArtsyStageState.completed_at)
        .where(
            WebArtsyStageState.company_id == Company.id,
            WebArtsyStageState.completed_at.is_not(None),
        )
        .order_by(WebArtsyStageState.completed_at.desc())
        .limit(1)
        .correlate(Company)
        .scalar_subquery()
    )

    if filters.enriched_after is not None:
        query = query.where(
            latest_enriched_at >= filters.enriched_after
        )

    if filters.enriched_before is not None:
        query = query.where(
            latest_enriched_at < filters.enriched_before
        )

    if filters.has_website:
        query = query.where(
            Company.website.is_not(None),
            Company.website != "",
        )

    if filters.has_people:
        query = query.where(
            exists(
                select(Person.id).where(
                    Person.company_id == Company.id
                )
            )
        )

    if filters.has_decision_maker:
        query = query.where(
            _decision_maker_exists()
        )

    latest_performance_score = (
        select(WebsitePerformance.performance_score)
        .where(
            WebsitePerformance.company_id == Company.id
        )
        .order_by(
            WebsitePerformance.observed_at.desc(),
            WebsitePerformance.id.desc(),
        )
        .limit(1)
        .correlate(Company)
        .scalar_subquery()
    )

    latest_seo_score = (
        select(WebsitePerformance.seo_score)
        .where(
            WebsitePerformance.company_id == Company.id
        )
        .order_by(
            WebsitePerformance.observed_at.desc(),
            WebsitePerformance.id.desc(),
        )
        .limit(1)
        .correlate(Company)
        .scalar_subquery()
    )

    if filters.has_performance:
        query = query.where(
            exists(
                select(WebsitePerformance.id).where(
                    WebsitePerformance.company_id == Company.id
                )
            )
        )

    if filters.min_performance is not None:
        query = query.where(
            latest_performance_score >= filters.min_performance
        )

    if filters.max_performance is not None:
        query = query.where(
            latest_performance_score <= filters.max_performance
        )

    if filters.min_seo is not None:
        query = query.where(
            latest_seo_score >= filters.min_seo
        )

    if filters.max_seo is not None:
        query = query.where(
            latest_seo_score <= filters.max_seo
        )

    if filters.has_email:
        query = query.where(
            _contact_kind_exists("email")
        )

    if filters.has_phone:
        query = query.where(
            _contact_kind_exists("phone")
        )

    if filters.has_company_linkedin:
        query = query.where(
            _contact_kind_exists("linkedin_company")
        )

    if filters.has_person_linkedin:
        query = query.where(
            _person_linkedin_exists()
        )

    if filters.has_linkedin:
        query = query.where(
            or_(
                _contact_kind_exists("linkedin_company"),
                _person_linkedin_exists(),
            )
        )

    if filters.limit is not None:
        query = query.limit(filters.limit)

    return query


def _contact_kind_exists(kind: str):
    return exists(
        select(ContactObservation.id).where(
            ContactObservation.company_id == Company.id,
            ContactObservation.kind == kind,
            or_(
                and_(
                    ContactObservation.normalized_value.is_not(None),
                    ContactObservation.normalized_value != "",
                ),
                and_(
                    ContactObservation.value.is_not(None),
                    ContactObservation.value != "",
                ),
            ),
        )
    )


def _person_linkedin_exists():
    return or_(
        _contact_kind_exists("linkedin_profile"),
        exists(
            select(Person.id).where(
                Person.company_id == Company.id,
                Person.linkedin_url.is_not(None),
                Person.linkedin_url != "",
            )
        ),
    )


def _decision_maker_exists():
    person = aliased(Person)
    observation = aliased(PersonObservation)
    latest_observation = aliased(PersonObservation)

    latest_scored_observation_id = (
        select(latest_observation.id)
        .where(
            latest_observation.person_id == person.id,
            latest_observation.decision_maker_score.is_not(None),
        )
        .order_by(
            latest_observation.observed_at.desc(),
            latest_observation.id.desc(),
        )
        .limit(1)
        .correlate(person)
        .scalar_subquery()
    )

    return exists(
        select(person.id)
        .join(
            observation,
            observation.person_id == person.id,
        )
        .where(
            person.company_id == Company.id,
            observation.id == latest_scored_observation_id,
            observation.decision_maker_role_group.in_(
                {"primary", "secondary"}
            ),
        )
    )


def _validate_score(
    name: str,
    value: int | None,
) -> None:
    if value is None:
        return

    if not 0 <= value <= 100:
        raise ValueError(
            f"{name} must be between 0 and 100"
        )
