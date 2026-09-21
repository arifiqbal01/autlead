# app/extract/people/structured.py

from __future__ import annotations

import json
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.models.schemas.people import PersonCandidate


SCHEMA_PERSON_RE = "schema.org/Person"


def extract_structured_people(
    *,
    html: str,
    source_url: str,
    language: str = "en",
) -> list[PersonCandidate]:
    """
    Extract person candidates from structured website HTML.

    Supported structured sources:

        1. JSON-LD / Schema.org Person
        2. Schema.org microdata Person

    Extracted fields may include:

        - name
        - job title
        - LinkedIn personal profile
        - source URL

    This function does not:

        - crawl websites
        - normalize people
        - resolve identities
        - score decision makers
        - persist records

    ``language`` is currently accepted for interface consistency
    and future language-specific structured extraction rules.
    """

    del language

    if not html:
        return []

    if not source_url:
        return []

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    candidates: list[PersonCandidate] = []

    seen: set[
        tuple[
            str,
            str | None,
        ]
    ] = set()

    # ---------------------------------------------------------
    # 1. JSON-LD
    # ---------------------------------------------------------

    for candidate in _extract_json_ld_people(
        soup=soup,
        source_url=source_url,
    ):
        _append_candidate(
            candidates=candidates,
            seen=seen,
            candidate=candidate,
        )

    # ---------------------------------------------------------
    # 2. Schema.org microdata
    # ---------------------------------------------------------

    for candidate in _extract_microdata_people(
        soup=soup,
        source_url=source_url,
    ):
        _append_candidate(
            candidates=candidates,
            seen=seen,
            candidate=candidate,
        )

    return candidates


# ---------------------------------------------------------------------------
# JSON-LD
# ---------------------------------------------------------------------------


def _extract_json_ld_people(
    *,
    soup: BeautifulSoup,
    source_url: str,
) -> list[PersonCandidate]:
    candidates: list[PersonCandidate] = []

    for script in soup.find_all(
        "script",
        attrs={
            "type": "application/ld+json",
        },
    ):
        script_text = (
            script.string
            or script.get_text()
        )

        data = _parse_json_ld_script(
            script_text
        )

        if data is None:
            continue

        for person in _extract_person_objects(
            data
        ):
            candidate = _person_candidate_from_json_ld(
                person=person,
                source_url=source_url,
            )

            if candidate is not None:
                candidates.append(candidate)

    return candidates


def _person_candidate_from_json_ld(
    *,
    person: dict[str, Any],
    source_url: str,
) -> PersonCandidate | None:
    raw_name = person.get("name")

    if not isinstance(raw_name, str):
        return None

    name = _clean_text(
        raw_name
    )

    if not name:
        return None

    raw_title = person.get(
        "jobTitle"
    )

    title = (
        _clean_text(raw_title)
        if isinstance(raw_title, str)
        else None
    )

    linkedin_url = _extract_linkedin_from_same_as(
        person
    )

    return PersonCandidate(
        name=name,
        title=title,
        linkedin_url=linkedin_url,
        source_url=source_url,
        evidence="schema.org Person JSON-LD",
    )


def _extract_person_objects(
    data: Any,
) -> list[dict[str, Any]]:
    """
    Recursively locate JSON-LD objects whose @type includes Person.

    Handles structures such as:

        {
            "@type": "Person"
        }

        {
            "@graph": [
                {"@type": "Organization"},
                {"@type": "Person"}
            ]
        }

        {
            "founder": {
                "@type": "Person"
            }
        }
    """

    found: list[dict[str, Any]] = []

    if isinstance(data, dict):
        types = _type_values(
            data.get("@type")
        )

        if "person" in types:
            found.append(data)

        for key, value in data.items():
            if key in {
                "@context",
                "@type",
            }:
                continue

            found.extend(
                _extract_person_objects(
                    value
                )
            )

    elif isinstance(data, list):
        for item in data:
            found.extend(
                _extract_person_objects(
                    item
                )
            )

    return found


def _parse_json_ld_script(
    script_text: str,
) -> Any | None:
    script_text = script_text.strip()

    if not script_text:
        return None

    try:
        return json.loads(
            script_text
        )

    except (
        TypeError,
        json.JSONDecodeError,
    ):
        return None


def _type_values(
    value: Any,
) -> set[str]:
    values: set[str] = set()

    for item in _as_list(value):
        if not isinstance(item, str):
            continue

        values.add(
            item.rsplit("/", 1)[-1].casefold()
        )

    return values


def _extract_linkedin_from_same_as(
    data: dict[str, Any],
) -> str | None:
    for value in _as_list(
        data.get("sameAs")
    ):
        if not isinstance(value, str):
            continue

        url = value.strip()

        if _is_linkedin_profile_url(url):
            return url

    return None


# ---------------------------------------------------------------------------
# Schema.org microdata
# ---------------------------------------------------------------------------


def _extract_microdata_people(
    *,
    soup: BeautifulSoup,
    source_url: str,
) -> list[PersonCandidate]:
    candidates: list[PersonCandidate] = []

    for tag in soup.find_all(
        attrs={
            "itemtype": True,
        },
    ):
        if not isinstance(tag, Tag):
            continue

        if not _is_schema_person_tag(tag):
            continue

        candidate = _person_candidate_from_microdata(
            tag=tag,
            source_url=source_url,
        )

        if candidate is not None:
            candidates.append(candidate)

    return candidates


def _person_candidate_from_microdata(
    *,
    tag: Tag,
    source_url: str,
) -> PersonCandidate | None:
    name = _extract_itemprop_text(
        tag=tag,
        itemprop="name",
    )

    if not name:
        return None

    title = _extract_itemprop_text(
        tag=tag,
        itemprop="jobTitle",
    )

    linkedin_url = _extract_microdata_linkedin(
        tag
    )

    return PersonCandidate(
        name=name,
        title=title,
        linkedin_url=linkedin_url,
        source_url=source_url,
        evidence="schema.org Person microdata",
    )


def _is_schema_person_tag(
    tag: Tag,
) -> bool:
    itemtype = tag.get(
        "itemtype"
    )

    if not itemtype:
        return False

    if isinstance(itemtype, str):
        values = [
            itemtype
        ]
    else:
        values = list(
            itemtype
        )

    return any(
        SCHEMA_PERSON_RE.casefold()
        in str(value).casefold()
        for value in values
    )


def _extract_itemprop_text(
    *,
    tag: Tag,
    itemprop: str,
) -> str | None:
    element = tag.find(
        attrs={
            "itemprop": itemprop,
        }
    )

    if not isinstance(element, Tag):
        return None

    # Some schema values are stored in attributes rather than text.
    for attribute in (
        "content",
        "value",
        "title",
    ):
        value = element.get(
            attribute
        )

        if isinstance(value, str):
            cleaned = _clean_text(
                value
            )

            if cleaned:
                return cleaned

    return _clean_text(
        element.get_text(
            " ",
            strip=True,
        )
    )


def _extract_microdata_linkedin(
    tag: Tag,
) -> str | None:
    # ---------------------------------------------------------
    # Schema.org sameAs
    # ---------------------------------------------------------

    for element in tag.find_all(
        attrs={
            "itemprop": "sameAs",
        }
    ):
        if not isinstance(element, Tag):
            continue

        value = _extract_url_from_tag(
            element
        )

        if (
            value
            and _is_linkedin_profile_url(value)
        ):
            return value

    # ---------------------------------------------------------
    # Fallback: LinkedIn link inside Person block
    # ---------------------------------------------------------

    for link in tag.find_all(
        "a",
        href=True,
    ):
        href = link.get(
            "href"
        )

        if not isinstance(href, str):
            continue

        href = href.strip()

        if _is_linkedin_profile_url(
            href
        ):
            return href

    return None


def _extract_url_from_tag(
    tag: Tag,
) -> str | None:
    for attribute in (
        "href",
        "content",
        "src",
    ):
        value = tag.get(
            attribute
        )

        if isinstance(value, str):
            value = value.strip()

            if value:
                return value

    return None


# ---------------------------------------------------------------------------
# Candidate handling
# ---------------------------------------------------------------------------


def _append_candidate(
    *,
    candidates: list[PersonCandidate],
    seen: set[
        tuple[
            str,
            str | None,
        ]
    ],
    candidate: PersonCandidate,
) -> None:
    identity = (
        candidate.name.casefold().strip(),
        (
            str(candidate.linkedin_url)
            .casefold()
            .strip()
            if candidate.linkedin_url
            else None
        ),
    )

    if identity in seen:
        return

    seen.add(identity)
    candidates.append(candidate)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _as_list(
    value: Any,
) -> list[Any]:
    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [
        value
    ]


def _clean_text(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    cleaned = " ".join(
        value.split()
    )

    return cleaned or None


def _is_linkedin_profile_url(
    value: str,
) -> bool:
    return (
        "linkedin.com/in/"
        in value.casefold()
    )


__all__ = [
    "extract_structured_people",
]