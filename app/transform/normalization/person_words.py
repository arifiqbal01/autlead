# app/transform/normalization/person_words.py

from __future__ import annotations


# ---------------------------------------------------------------------------
# Language configuration
# ---------------------------------------------------------------------------

LANGUAGE_ALIASES: dict[str, str] = {
    "en": "en",
    "en-us": "en",
    "en-gb": "en",
    "en-au": "en",
    "en-ca": "en",
    "english": "en",
    "nl": "nl",
    "nl-nl": "nl",
    "nl-be": "nl",
    "dutch": "nl",
    "flemish": "nl",
}


SUPPORTED_LANGUAGES: frozenset[str] = frozenset(
    {
        "en",
        "nl",
    }
)


# ---------------------------------------------------------------------------
# Person titles and professional roles
# ---------------------------------------------------------------------------
#
# Generic person/professional vocabulary.
#
# This answers:
#
#     "What title or professional role is associated with this person?"
#
# It does NOT answer:
#
#     "Is this person a decision maker?"
#
# Decision-maker roles are maintained separately below.
# ---------------------------------------------------------------------------

PERSON_TITLES: dict[str, dict[str, str]] = {
    "en": {
        # Personal / academic titles
        "mr": "Mr.",
        "mr.": "Mr.",
        "mrs": "Mrs.",
        "mrs.": "Mrs.",
        "ms": "Ms.",
        "ms.": "Ms.",
        "ms.": "Ms.",
        "miss": "Miss",

        "dr": "Dr.",
        "dr.": "Dr.",
        "doctor": "Doctor",

        "prof": "Prof.",
        "prof.": "Prof.",
        "professor": "Professor",

        "eng": "Eng.",
        "eng.": "Eng.",

        # Executive / business roles
        "ceo": "CEO",
        "cto": "CTO",
        "cfo": "CFO",
        "cmo": "CMO",
        "coo": "COO",
        "cio": "CIO",
        "cso": "CSO",
        "cpo": "CPO",

        "founder": "Founder",
        "co founder": "Co-Founder",
        "co-founder": "Co-Founder",
        "cofounder": "Co-Founder",

        "owner": "Owner",
        "co owner": "Co-Owner",
        "co-owner": "Co-Owner",

        "director": "Director",
        "managing director": "Managing Director",
        "executive director": "Executive Director",
        "commercial director": "Commercial Director",
        "operations director": "Operations Director",
        "technical director": "Technical Director",

        "general manager": "General Manager",
        "manager": "Manager",

        "partner": "Partner",
        "managing partner": "Managing Partner",
        "senior partner": "Senior Partner",

        "president": "President",
        "vice president": "Vice President",
        "vp": "VP",

        "head": "Head",
        "team lead": "Team Lead",
        "teamlead": "Team Lead",
        "lead": "Lead",

        # Professional roles
        "consultant": "Consultant",
        "specialist": "Specialist",
        "principal": "Principal",

        "engineer": "Engineer",
        "architect": "Architect",
        "developer": "Developer",
        "designer": "Designer",
        "researcher": "Researcher",
        "scientist": "Scientist",

        "lawyer": "Lawyer",
        "solicitor": "Solicitor",
        "attorney": "Attorney",

        "accountant": "Accountant",
        "auditor": "Auditor",

        # Common professional roles
        "dentist": "Dentist",
        "surgeon": "Surgeon",
        "orthodontist": "Orthodontist",
        "physician": "Physician",
        "nurse": "Nurse",
        "pharmacist": "Pharmacist",
        "veterinarian": "Veterinarian",
    },
    "nl": {
        # Personal / academic titles
        "dhr": "Dhr.",
        "dhr.": "Dhr.",
        "mevr": "Mevr.",
        "mevr.": "Mevr.",
        "mw": "Mw.",
        "mw.": "Mw.",

        "dr": "Dr.",
        "dr.": "Dr.",
        "drs": "Drs.",
        "drs.": "Drs.",

        "prof": "Prof.",
        "prof.": "Prof.",
        "professor": "Professor",

        "mr": "Mr.",
        "mr.": "Mr.",
        "ir": "Ir.",
        "ir.": "Ir.",
        "ing": "Ing.",
        "ing.": "Ing.",

        # Dutch executive / ownership roles
        "directeur": "Directeur",
        "algemeen directeur": "Algemeen Directeur",
        "adjunct-directeur": "Adjunct-Directeur",
        "adjunct directeur": "Adjunct-Directeur",

        "commercieel directeur": "Commercieel Directeur",
        "operationeel directeur": "Operationeel Directeur",
        "technisch directeur": "Technisch Directeur",
        "financieel directeur": "Financieel Directeur",

        "eigenaar": "Eigenaar",
        "mede-eigenaar": "Mede-Eigenaar",
        "mede eigenaar": "Mede-Eigenaar",

        "oprichter": "Oprichter",
        "medeoprichter": "Medeoprichter",
        "mede-oprichter": "Medeoprichter",
        "mede oprichter": "Medeoprichter",

        "ondernemer": "Ondernemer",

        "vennoot": "Vennoot",
        "beherend vennoot": "Beherend Vennoot",

        "partner": "Partner",
        "managing partner": "Managing Partner",

        "bestuurder": "Bestuurder",
        "bestuurslid": "Bestuurslid",
        "directielid": "Directielid",

        # Dutch management roles
        "manager": "Manager",
        "bedrijfsleider": "Bedrijfsleider",
        "locatiemanager": "Locatiemanager",
        "vestigingsmanager": "Vestigingsmanager",
        "regiomanager": "Regiomanager",

        "praktijkeigenaar": "Praktijkeigenaar",
        "praktijkhouder": "Praktijkhouder",
        "praktijkmanager": "Praktijkmanager",

        "projectmanager": "Projectmanager",
        "accountmanager": "Accountmanager",
        "teamleider": "Teamleider",
        "teamlead": "Teamlead",
        "afdelingshoofd": "Afdelingshoofd",
        "hoofd": "Hoofd",

        # Dutch professional roles
        "consultant": "Consultant",
        "specialist": "Specialist",
        "onderzoeker": "Onderzoeker",
        "wetenschapper": "Wetenschapper",

        "ingenieur": "Ingenieur",
        "architect": "Architect",
        "ontwikkelaar": "Ontwikkelaar",
        "ontwerper": "Ontwerper",

        "advocaat": "Advocaat",
        "accountant": "Accountant",
        "boekhouder": "Boekhouder",
        "auditor": "Auditor",

        # Medical / professional roles
        "arts": "Arts",
        "tandarts": "Tandarts",
        "kaakchirurg": "Kaakchirurg",
        "chirurg": "Chirurg",
        "orthodontist": "Orthodontist",
        "implantoloog": "Implantoloog",

        "mondhygiënist": "Mondhygiënist",
        "mondhygienist": "Mondhygiënist",

        "apotheker": "Apotheker",
        "verpleegkundige": "Verpleegkundige",
        "fysiotherapeut": "Fysiotherapeut",
        "dierenarts": "Dierenarts",

        # International business roles commonly used in Dutch websites
        "ceo": "CEO",
        "cto": "CTO",
        "cfo": "CFO",
        "cmo": "CMO",
        "coo": "COO",
        "cio": "CIO",
        "cso": "CSO",
        "cpo": "CPO",
    },
}


# ---------------------------------------------------------------------------
# Decision-maker roles
# ---------------------------------------------------------------------------
#
# Separate from PERSON_TITLES.
#
# A person can have a professional title without being a decision maker.
#
# Example:
#
#     Dentist
#     Consultant
#     Developer
#
# does not automatically imply decision-making authority.
#
# Whereas:
#
#     Owner
#     Founder
#     Director
#     Eigenaar
#     Directeur
#
# is stronger decision-maker evidence.
# ---------------------------------------------------------------------------

DECISION_MAKER_ROLES: dict[str, frozenset[str]] = {
    "en": frozenset(
        {
            "owner",
            "business owner",
            "founder",
            "co-founder",
            "cofounder",
            "ceo",
            "chief executive officer",
            "president",
            "director",
            "managing director",
            "executive director",
            "general manager",
            "commercial director",
            "operations director",
            "operational director",
            "technical director",
            "partner",
            "managing partner",
            "senior partner",
            "principal",
            "practice owner",
            "practice manager",
            "business manager",
            "head of",
        }
    ),
    "nl": frozenset(
        {
            "eigenaar",
            "ondernemer",
            "oprichter",
            "medeoprichter",
            "mede-oprichter",
            "directeur",
            "algemeen directeur",
            "commercieel directeur",
            "operationeel directeur",
            "technisch directeur",
            "financieel directeur",
            "bestuurder",
            "bestuurslid",
            "directielid",
            "vennoot",
            "beherend vennoot",
            "zaakvoerder",
            "firmant",
            "partner",
            "managing partner",
            "praktijkeigenaar",
            "praktijkhouder",
            "praktijkmanager",
            "vestigingsmanager",
            "bedrijfsleider",
            "ceo",
            "chief executive officer",
        }
    ),
}


COMBINED_DECISION_MAKER_ROLES: frozenset[str] = frozenset(
    role
    for roles in DECISION_MAKER_ROLES.values()
    for role in roles
)


# ---------------------------------------------------------------------------
# Name particles
# ---------------------------------------------------------------------------

NAME_PARTICLES: dict[str, frozenset[str]] = {
    "en": frozenset(
        {
            "de",
            "del",
            "della",
            "di",
            "du",
            "la",
            "le",
            "van",
            "von",
        }
    ),
    "nl": frozenset(
        {
            "de",
            "den",
            "der",
            "van",
            "van de",
            "van den",
            "van der",
            "van het",
            "van 't",
            "vande",
            "vanden",
            "vander",
            "te",
            "ten",
            "ter",
            "op",
            "aan",
            "in",
            "uit",
            "bij",
        }
    ),
}


def combined_name_particles() -> frozenset[str]:
    """Return Dutch + English surname particles."""

    return frozenset(
        particle
        for particles in NAME_PARTICLES.values()
        for particle in particles
    )


# ---------------------------------------------------------------------------
# Name prefixes
# ---------------------------------------------------------------------------

NAME_PREFIXES: dict[str, frozenset[str]] = {
    "en": frozenset(
        {
            "dr",
            "dr.",
            "mr",
            "mr.",
            "mrs",
            "mrs.",
            "ms",
            "ms.",
            "miss",
            "prof",
            "prof.",
        }
    ),
    "nl": frozenset(
        {
            "dhr",
            "dhr.",
            "mevr",
            "mevr.",
            "mw",
            "mw.",
            "dr",
            "dr.",
            "drs",
            "drs.",
            "prof",
            "prof.",
            "mr",
            "mr.",
            "ir",
            "ir.",
            "ing",
            "ing.",
        }
    ),
}


def combined_name_prefixes() -> frozenset[str]:
    """Return Dutch + English name prefixes."""

    return frozenset(
        prefix
        for prefixes in NAME_PREFIXES.values()
        for prefix in prefixes
    )


# ---------------------------------------------------------------------------
# Website / UI vocabulary
# ---------------------------------------------------------------------------

WEBSITE_WORDS: dict[str, frozenset[str]] = {
    "en": frozenset(
        {
            "about",
            "about us",
            "appointment",
            "book",
            "booking",
            "contact",
            "home",
            "learn",
            "more",
            "our",
            "read",
            "review",
            "reviews",
            "services",
            "team",
            "our team",
            "our people",
            "leadership",
            "management",
            "board",
            "staff",
            "people",
            "view",
            "welcome",
            "why",
            "choose",
            "careers",
            "career",
            "news",
            "blog",
            "privacy",
            "terms",
            "cookie",
            "cookies",
            "consent",
            "settings",
            "preferences",
        }
    ),
    "nl": frozenset(
        {
            "over",
            "over ons",
            "afspraak",
            "afspraken",
            "boeken",
            "contact",
            "home",
            "meer",
            "ons",
            "onze",
            "lees",
            "recensie",
            "recensies",
            "diensten",
            "team",
            "ons team",
            "onze mensen",
            "directie",
            "management",
            "bestuur",
            "bestuurders",
            "medewerkers",
            "mensen",
            "bekijk",
            "welkom",
            "waarom",
            "kiezen",
            "vacatures",
            "vacature",
            "nieuws",
            "blog",
            "privacy",
            "voorwaarden",
            "cookie",
            "cookies",
            "consent",
            "instellingen",
            "voorkeuren",
        }
    ),
}


def combined_website_words() -> frozenset[str]:
    """Return Dutch + English website/UI vocabulary."""

    return frozenset(
        word
        for words in WEBSITE_WORDS.values()
        for word in words
    )


# ---------------------------------------------------------------------------
# People/team page paths
# ---------------------------------------------------------------------------

PERSON_PAGE_PATHS: dict[str, tuple[str, ...]] = {
    "en": (
        "/about",
        "/about-us",
        "/our-team",
        "/team",
        "/our-people",
        "/people",
        "/leadership",
        "/management",
        "/board",
        "/staff",
        "/contact",
    ),
    "nl": (
        "/over-ons",
        "/ons-team",
        "/team",
        "/onze-mensen",
        "/mensen",
        "/directie",
        "/management",
        "/bestuur",
        "/organisatie",
        "/medewerkers",
        "/over-de-praktijk",
        "/contact",
    ),
}


def combined_person_page_paths() -> tuple[str, ...]:
    """Return Dutch + English people/team page paths."""

    return tuple(
        path
        for paths in PERSON_PAGE_PATHS.values()
        for path in paths
    )


# ---------------------------------------------------------------------------
# Generic sentence words
# ---------------------------------------------------------------------------

SENTENCE_WORDS: dict[str, frozenset[str]] = {
    "en": frozenset(
        {
            "a",
            "about",
            "after",
            "also",
            "an",
            "and",
            "are",
            "as",
            "at",
            "been",
            "being",
            "but",
            "by",
            "can",
            "clearly",
            "did",
            "does",
            "done",
            "for",
            "from",
            "get",
            "has",
            "have",
            "he",
            "her",
            "here",
            "his",
            "how",
            "i",
            "in",
            "is",
            "it",
            "its",
            "me",
            "my",
            "of",
            "on",
            "one",
            "our",
            "patient",
            "patients",
            "professional",
            "really",
            "she",
            "that",
            "the",
            "their",
            "them",
            "they",
            "this",
            "to",
            "very",
            "was",
            "we",
            "were",
            "what",
            "which",
            "who",
            "with",
            "you",
            "your",
        }
    ),
    "nl": frozenset(
        {
            "aan",
            "als",
            "bij",
            "de",
            "een",
            "en",
            "er",
            "heeft",
            "hebben",
            "het",
            "hier",
            "hij",
            "hoe",
            "in",
            "is",
            "jij",
            "kan",
            "kunnen",
            "maar",
            "met",
            "mij",
            "naar",
            "niet",
            "om",
            "ons",
            "ook",
            "op",
            "over",
            "te",
            "voor",
            "van",
            "was",
            "wat",
            "we",
            "werd",
            "wie",
            "wordt",
            "zijn",
            "zij",
            "ze",
            "zoals",
        }
    ),
}


def combined_sentence_words() -> frozenset[str]:
    """Return Dutch + English sentence vocabulary."""

    return frozenset(
        word
        for words in SENTENCE_WORDS.values()
        for word in words
    )


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

NAME_CREDENTIALS: frozenset[str] = frozenset(
    {
        "a.b.",
        "a.b",
        "ba",
        "b.a.",
        "b.a",
        "bsc",
        "b.sc",
        "msc",
        "m.sc",
        "ma",
        "m.a.",
        "mba",
        "phd",
        "ph.d.",
        "md",
        "m.d.",
        "dds",
        "dmd",
        "bds",
        "mbbs",
        "fcps",
        "jd",
        "llm",
        "ll.m.",
        "rn",
        "cpa",
        "pe",
    }
)


# ---------------------------------------------------------------------------
# Language helpers
# ---------------------------------------------------------------------------


def normalize_language(
    language: str | None,
) -> str:
    """
    Return the canonical language code.

    Unknown languages fall back to English.
    """

    if not language:
        return "en"

    value = language.strip().casefold()

    return LANGUAGE_ALIASES.get(
        value,
        "en",
    )


def supported_languages() -> frozenset[str]:
    """Return supported canonical languages."""

    return SUPPORTED_LANGUAGES


# ---------------------------------------------------------------------------
# Title helpers
# ---------------------------------------------------------------------------


def title_mapping(
    language: str | None = None,
) -> dict[str, str]:
    """
    Return the title mapping for one language.

    Kept as a compatibility helper for existing normalization code.
    """

    language = normalize_language(language)

    return PERSON_TITLES[language]


def combined_person_titles() -> dict[str, str]:
    """
    Return the combined Dutch + English title mapping.

    Dutch values take precedence when the same lookup key exists.
    """

    combined = dict(
        PERSON_TITLES["en"],
    )

    combined.update(
        PERSON_TITLES["nl"],
    )

    return combined


def combined_title_mapping() -> dict[str, str]:
    """Compatibility alias for the combined title mapping."""

    return combined_person_titles()


def normalize_title(
    value: str,
    language: str | None = None,
) -> str | None:
    """
    Normalize a title using one language vocabulary.
    """

    value = value.strip().casefold()

    if not value:
        return None

    return title_mapping(language).get(value)


def normalize_combined_title(
    value: str,
) -> str | None:
    """
    Normalize a title using the combined Dutch + English vocabulary.
    """

    value = value.strip().casefold()

    if not value:
        return None

    return combined_person_titles().get(value)


def is_person_title(
    value: str,
    language: str | None = None,
) -> bool:
    """Return whether a value is a known person title."""

    return normalize_title(
        value,
        language=language,
    ) is not None


def is_combined_person_title(
    value: str,
) -> bool:
    """Return whether a value is a known Dutch or English title."""

    return normalize_combined_title(value) is not None


# ---------------------------------------------------------------------------
# Decision-maker helpers
# ---------------------------------------------------------------------------


def decision_maker_roles(
    language: str | None = None,
) -> frozenset[str]:
    """Return decision-maker roles for one language."""

    language = normalize_language(language)

    return DECISION_MAKER_ROLES[language]


def combined_decision_maker_roles() -> frozenset[str]:
    """Return Dutch + English decision-maker roles."""

    return COMBINED_DECISION_MAKER_ROLES


# ---------------------------------------------------------------------------
# Name helpers
# ---------------------------------------------------------------------------


def name_particles(
    language: str | None = None,
) -> frozenset[str]:
    """Return surname particles for one language."""

    language = normalize_language(language)

    return NAME_PARTICLES[language]


def name_prefixes(
    language: str | None = None,
) -> frozenset[str]:
    """Return name prefixes for one language."""

    language = normalize_language(language)

    return NAME_PREFIXES[language]


def is_name_particle(
    value: str,
    language: str | None = None,
) -> bool:
    """Return whether a value is a recognized surname particle."""

    normalized = value.strip().casefold()

    return normalized in {
        item.casefold()
        for item in name_particles(language)
    }


def is_combined_name_particle(
    value: str,
) -> bool:
    """Return whether a value is a Dutch or English surname particle."""

    normalized = value.strip().casefold()

    return normalized in {
        item.casefold()
        for item in combined_name_particles()
    }


def is_name_prefix(
    value: str,
    language: str | None = None,
) -> bool:
    """Return whether a value is a recognized name prefix."""

    normalized = value.strip().casefold()

    return normalized in {
        item.casefold()
        for item in name_prefixes(language)
    }


def is_combined_name_prefix(
    value: str,
) -> bool:
    """Return whether a value is a Dutch or English name prefix."""

    normalized = value.strip().casefold()

    return normalized in {
        item.casefold()
        for item in combined_name_prefixes()
    }


def combined_name_particles() -> frozenset[str]:
    """Return Dutch + English surname particles."""

    return frozenset(
        particle
        for particles in NAME_PARTICLES.values()
        for particle in particles
    )


def combined_name_prefixes() -> frozenset[str]:
    """Return Dutch + English name prefixes."""

    return frozenset(
        prefix
        for prefixes in NAME_PREFIXES.values()
        for prefix in prefixes
    )


__all__ = [
    "COMBINED_DECISION_MAKER_ROLES",
    "DECISION_MAKER_ROLES",
    "LANGUAGE_ALIASES",
    "NAME_CREDENTIALS",
    "NAME_PARTICLES",
    "NAME_PREFIXES",
    "PERSON_PAGE_PATHS",
    "PERSON_TITLES",
    "SENTENCE_WORDS",
    "SUPPORTED_LANGUAGES",
    "WEBSITE_WORDS",
    "combined_decision_maker_roles",
    "combined_name_particles",
    "combined_name_prefixes",
    "combined_person_page_paths",
    "combined_person_titles",
    "combined_sentence_words",
    "combined_title_mapping",
    "combined_website_words",
    "decision_maker_roles",
    "is_combined_name_particle",
    "is_combined_name_prefix",
    "is_combined_person_title",
    "is_name_particle",
    "is_name_prefix",
    "is_person_title",
    "name_particles",
    "name_prefixes",
    "normalize_combined_title",
    "normalize_language",
    "normalize_title",
    "person_titles",
    "supported_languages",
    "title_mapping",
]