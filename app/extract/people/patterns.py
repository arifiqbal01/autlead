# app/extract/people/patterns.py

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Title boundaries
# ---------------------------------------------------------------------------
#
# Do not use a loose \b around short titles such as:
#
#     CEO
#     CTO
#     COO
#     CFO
#     CMO
#     VP
#     Dr
#
# because these are especially prone to matching inside larger words.
#
# Example:
#
#     Cookie
#
# must never produce:
#
#     COO
#
# The explicit lookarounds require the title to be outside a word-like
# character boundary, including accented Unicode letters.
# ---------------------------------------------------------------------------

_TITLE_START = r"(?<![\wÀ-ÖØ-öø-ÿ])"
_TITLE_END = r"(?![\wÀ-ÖØ-öø-ÿ])"


# ---------------------------------------------------------------------------
# English titles
# ---------------------------------------------------------------------------

TITLE_RE = re.compile(
    rf"""
    {_TITLE_START}
    (
        CEO
        | CTO
        | CMO
        | COO
        | CFO

        | Founder
        | Co[- ]Founder
        | Owner

        | Managing\s+Director
        | General\s+Manager
        | Commercial\s+Director
        | Operations?\s+Director
        | Technical\s+Director
        | Director

        | Managing\s+Partner
        | Partner

        | President
        | Vice\s+President
        | VP

        | Consultant
        | Specialist
        | Developer
        | Designer
        | Engineer
        | Architect
        | Lawyer
        | Solicitor
        | Accountant
        | Researcher
        | Scientist
        | Principal

        | Professor
        | Prof\.?
        | Doctor
        | Dr\.?

        | Head\s+of\s+\w+(?:\s+\w+){{0,3}}
        | Lead(?:\s+\w+){{0,3}}

        | Manager
    )
    {_TITLE_END}
    """,
    re.IGNORECASE | re.UNICODE | re.VERBOSE,
)


# ---------------------------------------------------------------------------
# Dutch titles
# ---------------------------------------------------------------------------

DUTCH_TITLE_RE = re.compile(
    rf"""
    {_TITLE_START}
    (
        Dhr\.?
        | Mevr\.?
        | Mw\.?
        | Drs\.?
        | Ir\.?
        | Ing\.?
        | Prof\.?
        | Professor

        | Algemeen\s+Directeur
        | Commercieel\s+Directeur
        | Operationeel\s+Directeur
        | Technisch\s+Directeur
        | Directeur

        | Mede[- ]?eigenaar
        | Eigenaar
        | Ondernemer
        | Mede[- ]?oprichter
        | Oprichter

        | Beherend\s+Vennoot
        | Managing\s+Partner
        | Vennoot
        | Partner

        | Bestuurder
        | Bestuurslid

        | Praktijkeigenaar
        | Praktijkhouder
        | Praktijkmanager
        | Vestigingsmanager
        | Bedrijfsleider
        | Locatiemanager
        | Regiomanager
        | Manager

        | Projectmanager
        | Accountmanager
        | Teamleider
        | Teamlead

        | Consultant
        | Specialist
        | Onderzoeker
        | Wetenschapper

        | Hoofd
            (?:\s+van)?
            (?:\s+\w+){{0,3}}

        | CEO
        | CTO
        | CMO
        | COO
        | CFO
    )
    {_TITLE_END}
    """,
    re.IGNORECASE | re.UNICODE | re.VERBOSE,
)


# ---------------------------------------------------------------------------
# Name pattern
# ---------------------------------------------------------------------------
#
# This intentionally remains a candidate detector rather than a complete
# person-name validator.
#
# Validation/filtering belongs in names.py.
#
# Supported examples:
#
#     John Smith
#     Jan de Vries
#     Jan van der Berg
#     Peter O'Connor
#     Anne-Marie Jansen
#     Jana Stickelbruck
# ---------------------------------------------------------------------------

NAME_RE = re.compile(
    r"""
    (?<![\wÀ-ÖØ-öø-ÿ])
    (?P<name>
        [A-ZÀ-ÖØ-Ý]
        [A-Za-zÀ-ÖØ-öø-ÿ'’\-]+

        (?:
            \s+
            (?:
                [A-ZÀ-ÖØ-Ý]
                [A-Za-zÀ-ÖØ-öø-ÿ'’\-]+

                |
                van
                |
                de
                |
                den
                |
                der
                |
                het
                |
                te
                |
                ten
                |
                ter
                |
                op
                |
                aan
            )
        ){1,3}
    )
    (?![\wÀ-ÖØ-öø-ÿ])
    """,
    re.UNICODE | re.VERBOSE,
)


# ---------------------------------------------------------------------------
# LinkedIn
# ---------------------------------------------------------------------------

LINKEDIN_PROFILE_RE = re.compile(
    r"""
    https?://
    (?:www\.)?
    linkedin\.com/in/
    [A-Za-z0-9%._~-]+
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ---------------------------------------------------------------------------
# Anchor extraction
# ---------------------------------------------------------------------------

ANCHOR_RE = re.compile(
    r"""
    <a
        [^>]*?
        href\s*=\s*
        (?:
            "([^"]+)"
            |
            '([^']+)'
            |
            ([^\s>]+)
        )
        [^>]*>
        (.*?)
    </a>
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)