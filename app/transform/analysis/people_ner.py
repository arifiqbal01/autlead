# app/transform/analysis/people_ner.py

from __future__ import annotations

from functools import lru_cache

import spacy
from spacy.language import Language

from app.models.schemas.people import PersonCandidate
from app.extract.people.names import clean_name_candidate
from app.extract.people.titles import extract_nearby_title


MODEL_BY_LANGUAGE = {
    "nl": "nl_core_news_sm",
    "en": "en_core_web_sm",
}


@lru_cache(maxsize=2)
def _get_nlp(
    language: str,
) -> Language:
    model_name = MODEL_BY_LANGUAGE.get(
        language,
        MODEL_BY_LANGUAGE["en"],
    )

    return spacy.load(model_name)


def extract_ner_people(
    *,
    text: str,
    source_url: str,
    language: str = "nl",
) -> list[PersonCandidate]:
    """
    Derive person candidates from unstructured text using NER.

    Only PERSON entities with nearby professional-title evidence
    are retained.

    Bare PERSON entities are deliberately discarded.
    """

    if not text or not source_url:
        return []

    language = (
        language
        if language in MODEL_BY_LANGUAGE
        else "en"
    )

    nlp = _get_nlp(language)

    # Protect spaCy against extremely large pages.
    doc = nlp(
        text[:100_000]
    )

    candidates: list[PersonCandidate] = []
    seen: set[str] = set()

    for entity in doc.ents:
        if entity.label_ not in {
            "PER",
            "PERSON",
        }:
            continue

        name = clean_name_candidate(
            entity.text
        )

        if not name:
            continue

        # Use sentence-level evidence first.
        sentence = entity.sent.text

        title = extract_nearby_title(
            sentence,
            language=language,
        )

        if not title:
            continue

        identity = name.casefold()

        if identity in seen:
            continue

        seen.add(identity)

        candidates.append(
            PersonCandidate(
                name=name,
                title=title,
                linkedin_url=None,
                source_url=source_url,
            )
        )

    return candidates