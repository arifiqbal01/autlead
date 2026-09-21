# app/transform/scoring/people.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.models.schemas.people import PersonCandidate


PersonRoleGroup = Literal[
    "primary",
    "secondary",
    "professional",
    "other",
    "unknown",
]

DecisionMakerConfidence = Literal[
    "high",
    "medium",
    "low",
]


# ---------------------------------------------------------------------------
# Score model
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PersonScore:
    """
    Deterministic commercial-priority score for a person.

    Role semantics are determined upstream.

    This layer does NOT:

        - interpret job titles
        - classify multilingual titles
        - call an LLM
        - decide whether AI output should be trusted
        - perform entity resolution
        - extract people

    Expected flow:

        website evidence
            ↓
        Gemini semantic assessment
            ↓
        decision-maker qualification policy
            ↓
        score_person()
    """

    person: PersonCandidate
    score: int
    role_group: PersonRoleGroup
    reasons: tuple[str, ...]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def score_person(
    person: PersonCandidate,
    *,
    role_group: PersonRoleGroup = "unknown",
    is_decision_maker: bool = False,
    decision_maker_confidence: DecisionMakerConfidence = "low",
    has_linkedin: bool | None = None,
) -> PersonScore:
    """
    Score one already-classified person.

    The semantic meaning of the person's title must already have been
    determined upstream.

    Scoring remains deterministic and explainable.
    """

    if has_linkedin is None:
        has_linkedin = bool(
            person.linkedin_url
        )

    valid_name = _looks_like_real_person_name(
        person.name
    )

    score = 0
    reasons: list[str] = []

    # ---------------------------------------------------------
    # Role authority
    # ---------------------------------------------------------

    if role_group == "primary":
        score += 100
        reasons.append(
            "primary_decision_maker_role"
        )

    elif role_group == "secondary":
        score += 70
        reasons.append(
            "secondary_decision_maker_role"
        )

    elif role_group == "professional":
        score += 30
        reasons.append(
            "professional_role"
        )

    elif role_group == "other":
        score += 15
        reasons.append(
            "other_role"
        )

    else:
        score += 5
        reasons.append(
            "unknown_role"
        )

    # ---------------------------------------------------------
    # Accepted decision-maker classification
    # ---------------------------------------------------------

    if is_decision_maker:
        reasons.append(
            "qualified_decision_maker"
        )

    # ---------------------------------------------------------
    # Semantic confidence
    # ---------------------------------------------------------

    if decision_maker_confidence == "high":
        score += 10
        reasons.append(
            "high_role_confidence"
        )

    elif decision_maker_confidence == "medium":
        score += 5
        reasons.append(
            "medium_role_confidence"
        )

    else:
        reasons.append(
            "low_role_confidence"
        )

    # ---------------------------------------------------------
    # LinkedIn identity evidence
    # ---------------------------------------------------------

    if has_linkedin:
        score += 15
        reasons.append(
            "linkedin_profile"
        )

    # ---------------------------------------------------------
    # Name quality
    # ---------------------------------------------------------

    if valid_name:
        score += 10
        reasons.append(
            "person_name"
        )

    else:
        score -= 50
        reasons.append(
            "weak_person_name"
        )

    # ---------------------------------------------------------
    # Strong person + accepted authority
    # ---------------------------------------------------------

    if (
        is_decision_maker
        and role_group in {
            "primary",
            "secondary",
        }
        and valid_name
    ):
        score += 5
        reasons.append(
            "name_role_combination"
        )

    score = max(
        0,
        min(
            score,
            150,
        ),
    )

    return PersonScore(
        person=person,
        score=score,
        role_group=role_group,
        reasons=tuple(reasons),
    )


def score_people(
    people: list[
        tuple[
            PersonCandidate,
            PersonRoleGroup,
            bool,
            DecisionMakerConfidence,
        ]
    ],
) -> list[PersonScore]:
    """
    Score and rank already-classified people.

    Each item contains:

        (
            person,
            role_group,
            is_decision_maker,
            confidence,
        )
    """

    scored = [
        score_person(
            person,
            role_group=role_group,
            is_decision_maker=is_decision_maker,
            decision_maker_confidence=confidence,
        )
        for (
            person,
            role_group,
            is_decision_maker,
            confidence,
        ) in people
    ]

    return sorted(
        scored,
        key=lambda item: (
            -item.score,
            item.person.name.casefold(),
        ),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _looks_like_real_person_name(
    value: str,
) -> bool:
    """
    Defensive name-quality check.

    Extraction and Gemini validation should remove most false positives.
    This remains as a deterministic safety check before assigning a
    strong commercial-priority score.
    """

    words = value.strip().split()

    if not 2 <= len(words) <= 4:
        return False

    blocked = {
        "gdpr",
        "cookie",
        "cookies",
        "consent",
        "settings",
        "preferences",

        "voornaam",
        "achternaam",
        "firstname",
        "lastname",

        "dental",
        "clinic",
        "clinics",
        "centrum",
        "center",
        "group",
        "groep",
        "company",
        "bedrijf",
        "agency",
        "bureau",

        "best",
        "dentist",
        "tandarts",

        "team",
        "contact",
        "appointment",
        "afspraak",

        "your",
        "our",
        "ons",
        "onze",

        "privacy",
        "terms",
        "voorwaarden",
    }

    normalized = {
        word.strip(
            ".,:;!?()[]{}\"“”‘’"
        ).casefold()
        for word in words
    }

    if normalized & blocked:
        return False

    if any(
        character.isdigit()
        for character in value
    ):
        return False

    if any(
        character in value
        for character in (
            "@",
            "/",
            "\\",
            "=",
            "<",
            ">",
        )
    ):
        return False

    return True