from __future__ import annotations

from typing import Protocol

from app.models.schemas.people import PersonCandidate


class PeopleExtractionProvider(Protocol):
    """
    Provider contract for extracting people from website content.

    Implementations must convert their external extraction mechanism
    into Autlead-compatible PersonCandidate records.
    """

    def extract(
        self,
        *,
        text: str,
        source_url: str,
        language: str = "nl",
    ) -> list[PersonCandidate]:
        ...