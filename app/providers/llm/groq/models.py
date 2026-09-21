from typing import Literal

from pydantic import BaseModel, Field


class GroqExtractedPerson(BaseModel):
    name: str = Field(...)

    title: str | None = Field(
        default=None,
        description=(
            "Only the person's professional title. "
            "Do not include explanations or evidence."
        ),
    )

    linkedin_url: str | None = None
    source_url: str | None = None

    evidence: str | None = Field(
        default=None,
        description=(
            "Short website evidence supporting the person's "
            "identity and role."
        ),
    )

    decision_maker: bool = False

    role_group: Literal[
        "primary",
        "secondary",
        "professional",
        "other",
        "unknown",
    ] = "unknown"

    decision_maker_confidence: Literal[
        "high",
        "medium",
        "low",
    ] = "low"

    decision_maker_reason: str | None = Field(
        default=None,
        description=(
            "Short evidence-based explanation for the "
            "decision-maker classification."
        ),
    )


class GroqPeopleExtraction(BaseModel):
    people: list[GroqExtractedPerson] = Field(
        default_factory=list,
    )