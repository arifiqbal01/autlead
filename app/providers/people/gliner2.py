from __future__ import annotations

from typing import Any

from gliner2 import GLiNER2

from app.models.schemas.people import PersonCandidate


class GLiNER2PeopleExtractionProvider:
    """
    GLiNER2-backed people extraction provider.

    GLiNER2 handles semantic extraction.
    This provider adapts its output into Autlead's
    PersonCandidate schema.

    The provider does not:
        - score people
        - resolve duplicate people
        - decide who is a decision maker
        - persist data
        - perform lead qualification
    """

    DEFAULT_MODEL = "fastino/gliner2-base-v1"

    def __init__(
        self,
        *,
        model_name: str = DEFAULT_MODEL,
    ) -> None:
        self.model_name = model_name
        self._model: GLiNER2 | None = None

    def _get_model(self) -> GLiNER2:
        """
        Lazily load the model.

        Loading is intentionally deferred until the first extraction
        operation so importing the provider does not immediately load
        the model into memory.
        """

        if self._model is None:
            self._model = GLiNER2.from_pretrained(
                self.model_name,
            )

        return self._model

    def extract(
        self,
        *,
        text: str,
        source_url: str,
        language: str = "nl",
    ) -> list[PersonCandidate]:
        """
        Extract person candidates from text.

        Language is currently retained as part of the provider
        contract. GLiNER2 itself performs multilingual extraction;
        language-specific prompting can be introduced later without
        changing the provider interface.
        """

        if not text.strip():
            return []

        if not source_url.strip():
            raise ValueError(
                "source_url must not be empty",
            )

        model = self._get_model()

        result = model.extract_json(
            text,
            self._schema(language),
        )

        return self._to_candidates(
            result,
            source_url=source_url,
        )

    @staticmethod
    def _schema(
        language: str,
    ) -> dict[str, list[str]]:
        """
        Return the structured extraction schema.

        Descriptions are deliberately explicit because website text
        frequently contains names, professions, organizations and
        navigation text in close proximity.
        """

        if language.casefold() == "nl":
            return {
                "people": [
                    (
                        "name::str::"
                        "Volledige naam van een echte persoon. "
                        "Geen bedrijfsnaam, teamnaam, navigatietekst "
                        "of algemene beschrijving."
                    ),
                    (
                        "title::str::"
                        "Functietitel, beroep of rol van deze persoon, "
                        "zoals tandarts, praktijkeigenaar, directeur, "
                        "oprichter, manager of mondhygiënist."
                    ),
                    (
                        "linkedin_url::str::"
                        "LinkedIn profiel-URL van deze persoon, "
                        "indien expliciet aanwezig."
                    ),
                ],
            }

        return {
            "people": [
                (
                    "name::str::"
                    "Full name of a real individual. "
                    "Do not return company names, team names, "
                    "navigation text or generic descriptions."
                ),
                (
                    "title::str::"
                    "Job title, profession or business role of "
                    "the person, such as dentist, owner, founder, "
                    "director or manager."
                ),
                (
                    "linkedin_url::str::"
                    "LinkedIn profile URL belonging to this person, "
                    "if explicitly present."
                ),
            ],
        }

    @staticmethod
    def _to_candidates(
        result: dict[str, Any],
        *,
        source_url: str,
    ) -> list[PersonCandidate]:
        """
        Convert GLiNER2 structured output into PersonCandidate objects.
        """

        raw_people = result.get(
            "people",
            [],
        )

        if not isinstance(raw_people, list):
            return []

        candidates: list[PersonCandidate] = []

        for raw_person in raw_people:
            if not isinstance(raw_person, dict):
                continue

            name = _clean_string(
                raw_person.get("name"),
            )

            if not name:
                continue

            title = _clean_string(
                raw_person.get("title"),
            )

            linkedin_url = _clean_string(
                raw_person.get("linkedin_url"),
            )

            candidates.append(
                PersonCandidate(
                    name=name,
                    title=title,
                    linkedin_url=linkedin_url,
                    source_url=source_url,
                )
            )

        return _deduplicate_candidates(
            candidates,
        )


def _clean_string(
    value: Any,
) -> str | None:
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    return value


def _deduplicate_candidates(
    people: list[PersonCandidate],
) -> list[PersonCandidate]:
    """
    Remove exact extraction duplicates.

    Entity resolution remains outside the provider.
    """

    seen: set[tuple[str, str | None]] = set()
    result: list[PersonCandidate] = []

    for person in people:
        linkedin = (
            str(person.linkedin_url).casefold().rstrip("/")
            if person.linkedin_url
            else None
        )

        identity = (
            person.name.casefold(),
            linkedin,
        )

        if identity in seen:
            continue

        seen.add(identity)
        result.append(person)

    return result