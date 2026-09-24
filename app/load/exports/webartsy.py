from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.load.exports.webartsy_filters import (
    WebArtsyExportFilters,
    apply_webartsy_export_filters,
)
from app.models.persistence.company import Company
from app.models.persistence.contact_observation import ContactObservation
from app.models.persistence.person import Person
from app.models.persistence.person_observation import PersonObservation
from app.models.persistence.website_performance import WebsitePerformance
from app.models.persistence.technology_observation import (
    TechnologyObservation,
)

@dataclass(frozen=True, slots=True)
class WebArtsyLeadExport:
    company_id: int
    company_name: str

    website: str | None
    domain: str | None
    country: str | None
    city: str | None
    address: str | None
    category: str | None

    people: str | None
    decision_makers: str | None

    technologies: str | None

    performance_score: int | None
    seo_score: int | None

    email: str | None
    phone: str | None

    linkedin_company_urls: str | None
    linkedin_profile_urls: str | None
    facebook_urls: str | None
    instagram_urls: str | None
    x_urls: str | None
    youtube_urls: str | None
    tiktok_urls: str | None


@dataclass(frozen=True, slots=True)
class _ContactExportData:
    email: str | None
    phone: str | None

    linkedin_company_urls: str | None
    linkedin_profile_urls: str | None

    facebook_urls: str | None
    instagram_urls: str | None
    x_urls: str | None
    youtube_urls: str | None
    tiktok_urls: str | None


@dataclass(frozen=True, slots=True)
class _PeopleExportData:
    people: str | None
    decision_makers: str | None


async def export_webartsy_leads(
    *,
    session: AsyncSession,
    output_dir: str | Path = "app/load/exports",
    filters: WebArtsyExportFilters | None = None,
) -> Path:
    """
    Export one CSV row per company matching the supplied filters.

    The CSV intentionally contains lead-facing fields only.
    Internal timestamps and operational metadata remain in PostgreSQL
    and can still be used by export filters.
    """

    exported_at = datetime.now(
        UTC
    )

    rows = await _collect_export_rows(
        session=session,
        filters=filters,
    )

    directory = Path(
        output_dir
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = (
        exported_at
        .astimezone()
        .strftime(
            "%Y-%m-%d_%H-%M-%S"
        )
    )

    output_path = (
        directory
        / f"webartsy_leads_{timestamp}.csv"
    )

    fieldnames = [
        "company_id",
        "company_name",

        "website",
        "domain",
        "country",
        "city",
        "address",
        "category",

        "people",
        "decision_makers",

        "technologies",

        "performance_score",
        "seo_score",

        "outreach",
        "phone",

        "linkedin_company_urls",
        "linkedin_profile_urls",

        "facebook_urls",
        "instagram_urls",
        "x_urls",
        "youtube_urls",
        "tiktok_urls",
    ]

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for row in rows:
            csv_row: dict[
                str,
                object,
            ] = {}

            for field in fieldnames:
                csv_row[field] = getattr(
                    row,
                    field,
                )

            writer.writerow(
                csv_row
            )

    return output_path


async def _collect_export_rows(
    *,
    session: AsyncSession,
    filters: WebArtsyExportFilters | None,
) -> list[WebArtsyLeadExport]:
    """
    Build exactly one export row per matching persisted company.

    Company filtering happens in PostgreSQL before related enrichment
    data is loaded.

    Related records are loaded in batches to avoid per-company and
    per-person N+1 queries.
    """

    company_query = (
        select(Company)
        .order_by(
            Company.id
        )
    )

    company_query = (
        apply_webartsy_export_filters(
            company_query,
            filters,
        )
    )

    companies = list(
        (
            await session.scalars(
                company_query
            )
        ).all()
    )

    if not companies:
        return []

    company_ids = [
        company.id
        for company in companies
    ]

    technologies_by_company = await _load_technologies(
        session=session,
        company_ids=company_ids,
    )

    performance_by_company = (
        await _load_latest_performance(
            session=session,
            company_ids=company_ids,
        )
    )

    contacts_by_company = (
        await _load_contacts(
            session=session,
            company_ids=company_ids,
        )
    )

    people_by_company = (
        await _load_people(
            session=session,
            company_ids=company_ids,
        )
    )

    person_ids = [
        person.id
        for people in people_by_company.values()
        for person in people
    ]

    observations_by_person = (
        await _load_latest_scored_person_observations(
            session=session,
            person_ids=person_ids,
        )
    )

    rows: list[
        WebArtsyLeadExport
    ] = []

    for company in companies:
        performance = (
            performance_by_company.get(
                company.id
            )
        )

        contact_data = _build_contact_data(
            contacts_by_company.get(
                company.id,
                [],
            )
        )

        people_data = _build_people_data(
            people=people_by_company.get(
                company.id,
                [],
            ),
            observations_by_person=(
                observations_by_person
            ),
        )

        technology_data = _build_technology_data(
            technologies_by_company.get(
                company.id,
                [],
            )
        )

        rows.append(
            WebArtsyLeadExport(
                company_id=company.id,
                company_name=company.name,

                website=company.website,
                domain=company.domain,
                country=company.country,
                city=company.city,
                address=company.address,
                category=company.category,

                people=(
                    people_data.people
                ),

                decision_makers=(
                    people_data.decision_makers
                ),

                technologies=technology_data,

                performance_score=(
                    performance.performance_score
                    if performance is not None
                    else None
                ),

                seo_score=(
                    performance.seo_score
                    if performance is not None
                    else None
                ),

                email=(
                    contact_data.email
                ),

                phone=(
                    contact_data.phone
                ),

                linkedin_company_urls=(
                    contact_data.linkedin_company_urls
                ),

                linkedin_profile_urls=(
                    contact_data.linkedin_profile_urls
                ),

                facebook_urls=(
                    contact_data.facebook_urls
                ),

                instagram_urls=(
                    contact_data.instagram_urls
                ),

                x_urls=(
                    contact_data.x_urls
                ),

                youtube_urls=(
                    contact_data.youtube_urls
                ),

                tiktok_urls=(
                    contact_data.tiktok_urls
                ),
            )
        )

    return rows


async def _load_technologies(
    *,
    session: AsyncSession,
    company_ids: list[int],
) -> dict[int, list[TechnologyObservation]]:
    technologies = list(
        (
            await session.scalars(
                select(TechnologyObservation)
                .where(
                    TechnologyObservation.company_id.in_(
                        company_ids
                    )
                )
                .order_by(
                    TechnologyObservation.company_id,
                    TechnologyObservation.observed_at.desc(),
                    TechnologyObservation.id.desc(),
                )
            )
        ).all()
    )

    grouped: dict[
        int,
        list[TechnologyObservation],
    ] = defaultdict(list)

    for technology in technologies:
        grouped[
            technology.company_id
        ].append(
            technology
        )

    return dict(grouped)


async def _load_latest_performance(
    *,
    session: AsyncSession,
    company_ids: list[int],
) -> dict[
    int,
    WebsitePerformance,
]:
    """
    Load the latest WebsitePerformance record for each company.
    """

    performances = list(
        (
            await session.scalars(
                select(
                    WebsitePerformance
                )
                .where(
                    WebsitePerformance.company_id.in_(
                        company_ids
                    )
                )
                .order_by(
                    WebsitePerformance.company_id,
                    WebsitePerformance.observed_at.desc(),
                    WebsitePerformance.id.desc(),
                )
                .distinct(
                    WebsitePerformance.company_id
                )
            )
        ).all()
    )

    return {
        performance.company_id: performance
        for performance in performances
    }


async def _load_contacts(
    *,
    session: AsyncSession,
    company_ids: list[int],
) -> dict[
    int,
    list[ContactObservation],
]:
    """
    Load all contact observations for the selected companies.
    """

    contacts = list(
        (
            await session.scalars(
                select(
                    ContactObservation
                )
                .where(
                    ContactObservation.company_id.in_(
                        company_ids
                    )
                )
                .order_by(
                    ContactObservation.company_id,
                    ContactObservation.observed_at.desc(),
                    ContactObservation.id.desc(),
                )
            )
        ).all()
    )

    grouped: dict[
        int,
        list[ContactObservation],
    ] = defaultdict(
        list
    )

    for contact in contacts:
        grouped[
            contact.company_id
        ].append(
            contact
        )

    return dict(
        grouped
    )


async def _load_people(
    *,
    session: AsyncSession,
    company_ids: list[int],
) -> dict[
    int,
    list[Person],
]:
    """
    Load all persisted people for the selected companies.
    """

    people = list(
        (
            await session.scalars(
                select(
                    Person
                )
                .where(
                    Person.company_id.in_(
                        company_ids
                    )
                )
                .order_by(
                    Person.company_id,
                    Person.id,
                )
            )
        ).all()
    )

    grouped: dict[
        int,
        list[Person],
    ] = defaultdict(
        list
    )

    for person in people:
        grouped[
            person.company_id
        ].append(
            person
        )

    return dict(
        grouped
    )


async def _load_latest_scored_person_observations(
    *,
    session: AsyncSession,
    person_ids: list[int],
) -> dict[
    int,
    PersonObservation,
]:
    """
    Load the latest scored decision-maker observation
    for each selected person.
    """

    if not person_ids:
        return {}

    observations = list(
        (
            await session.scalars(
                select(
                    PersonObservation
                )
                .where(
                    PersonObservation.person_id.in_(
                        person_ids
                    ),
                    PersonObservation.decision_maker_score.is_not(
                        None
                    ),
                )
                .order_by(
                    PersonObservation.person_id,
                    PersonObservation.observed_at.desc(),
                    PersonObservation.id.desc(),
                )
                .distinct(
                    PersonObservation.person_id
                )
            )
        ).all()
    )

    return {
        observation.person_id: observation
        for observation in observations
    }


def _build_people_data(
    *,
    people: list[Person],
    observations_by_person: dict[
        int,
        PersonObservation,
    ],
) -> _PeopleExportData:
    """
    Aggregate people and decision-maker data into company CSV fields.
    """

    people_values: list[
        str
    ] = []

    decision_maker_values: list[
        str
    ] = []

    for person in people:
        person_parts = [
            person.name
        ]

        if person.title:
            person_parts.append(
                person.title
            )

        if person.linkedin_url:
            person_parts.append(
                str(
                    person.linkedin_url
                )
            )

        person_text = (
            " | ".join(
                person_parts
            )
        )

        if (
            person_text
            not in people_values
        ):
            people_values.append(
                person_text
            )

        observation = (
            observations_by_person.get(
                person.id
            )
        )

        if observation is None:
            continue

        role_group = (
            observation.decision_maker_role_group
        )

        score = (
            observation.decision_maker_score
        )

        if role_group not in {
            "primary",
            "secondary",
        }:
            continue

        decision_parts = [
            person.name
        ]

        if person.title:
            decision_parts.append(
                person.title
            )

        if score is not None:
            decision_parts.append(
                f"score={score}"
            )

        decision_parts.append(
            f"role={role_group}"
        )

        if (
            observation.decision_maker_confidence
        ):
            decision_parts.append(
                "confidence="
                f"{observation.decision_maker_confidence}"
            )

        decision_text = (
            " | ".join(
                decision_parts
            )
        )

        if (
            decision_text
            not in decision_maker_values
        ):
            decision_maker_values.append(
                decision_text
            )

    return _PeopleExportData(
        people=(
            "; ".join(
                people_values
            )
            if people_values
            else None
        ),

        decision_makers=(
            "; ".join(
                decision_maker_values
            )
            if decision_maker_values
            else None
        ),
    )

def _build_technology_data(
    technologies: list[TechnologyObservation],
) -> str | None:
    values: list[str] = []

    for observation in technologies:
        technology = observation.name

        if observation.version:
            technology = (
                f"{technology} {observation.version}"
            )

        if technology not in values:
            values.append(
                technology
            )

    if not values:
        return None

    return "; ".join(values)


def _build_contact_data(
    contacts: list[
        ContactObservation
    ],
) -> _ContactExportData:
    """
    Aggregate contact observations into one deduplicated company set.

    GitHub observations are intentionally excluded from the lead export.
    """

    values: dict[
        str,
        list[str],
    ] = {
        "outreach": [],
        "phone": [],

        "linkedin_company": [],
        "linkedin_profile": [],

        "facebook": [],
        "instagram": [],
        "x": [],
        "youtube": [],
        "tiktok": [],
    }

    for contact in contacts:
        kind = (
            contact.kind
        )

        if kind not in values:
            continue

        value = (
            contact.normalized_value
            or contact.value
        )

        if not value:
            continue

        if (
            value
            not in values[kind]
        ):
            values[
                kind
            ].append(
                value
            )

    def join(
        kind: str,
    ) -> str | None:
        items = (
            values[kind]
        )

        if not items:
            return None

        return "; ".join(
            items
        )

    return _ContactExportData(
        email=join(
            "outreach"
        ),

        phone=join(
            "phone"
        ),

        linkedin_company_urls=join(
            "linkedin_company"
        ),

        linkedin_profile_urls=join(
            "linkedin_profile"
        ),

        facebook_urls=join(
            "facebook"
        ),

        instagram_urls=join(
            "instagram"
        ),

        x_urls=join(
            "x"
        ),

        youtube_urls=join(
            "youtube"
        ),

        tiktok_urls=join(
            "tiktok"
        ),
    )
