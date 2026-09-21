# app/cli/webartsy_saved.py

from __future__ import annotations

import argparse
from datetime import UTC, datetime

from app.core.database.session import SessionFactory
from app.load.exports.webartsy import export_webartsy_leads
from app.load.exports.webartsy_filters import WebArtsyExportFilters


def _parse_datetime(
    value: str,
) -> datetime:
    """
    Parse an ISO-8601 date or datetime.

    Examples:
        2026-08-29
        2026-08-29T14:30:00
        2026-08-29T14:30:00+05:00
        2026-08-29T09:30:00Z

    Naive values are interpreted as UTC.
    """

    normalized = value.strip()

    if normalized.endswith("Z"):
        normalized = (
            normalized[:-1]
            + "+00:00"
        )

    try:
        parsed = datetime.fromisoformat(
            normalized
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Expected ISO-8601 date/datetime, for example "
            "'2026-08-29' or "
            "'2026-08-29T14:30:00+05:00'."
        ) from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=UTC
        )

    return parsed


def _score(
    value: str,
) -> int:
    """
    Parse a Lighthouse-style score between 0 and 100.
    """

    try:
        score = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Score must be an integer from 0 to 100."
        ) from exc

    if not 0 <= score <= 100:
        raise argparse.ArgumentTypeError(
            "Score must be between 0 and 100."
        )

    return score


def _positive_int(
    value: str,
) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Value must be a positive integer."
        ) from exc

    if number <= 0:
        raise argparse.ArgumentTypeError(
            "Value must be greater than 0."
        )

    return number


def build_parser(
    parser: argparse.ArgumentParser | None = None,
) -> argparse.ArgumentParser:
    if parser is None:
        parser = argparse.ArgumentParser(
            description=(
                "Export previously saved WebArtsy data "
                "with optional lead filters."
            ),
        )

    # ---------------------------------------------------------
    # Output
    # ---------------------------------------------------------

    parser.add_argument(
        "--export-dir",
        default="exports",
        help=(
            "Directory where the CSV export will be written. "
            "Default: exports"
        ),
    )

    parser.add_argument(
        "--limit",
        type=_positive_int,
        help=(
            "Maximum number of companies to export."
        ),
    )

    # ---------------------------------------------------------
    # Company/location
    # ---------------------------------------------------------

    parser.add_argument(
        "--country",
        help=(
            "Filter by country, for example AE, UAE, "
            "Netherlands, or Nederland depending on stored data."
        ),
    )

    parser.add_argument(
        "--city",
        help=(
            "Filter by city."
        ),
    )

    parser.add_argument(
        "--category",
        help=(
            "Filter companies whose category contains this text."
        ),
    )

    # ---------------------------------------------------------
    # Company timestamps
    # ---------------------------------------------------------

    parser.add_argument(
        "--created-after",
        type=_parse_datetime,
        metavar="DATETIME",
        help=(
            "Companies created on or after this ISO-8601 "
            "date/time."
        ),
    )

    parser.add_argument(
        "--created-before",
        type=_parse_datetime,
        metavar="DATETIME",
        help=(
            "Companies created before this ISO-8601 "
            "date/time."
        ),
    )

    parser.add_argument(
        "--updated-after",
        type=_parse_datetime,
        metavar="DATETIME",
        help=(
            "Companies updated on or after this ISO-8601 "
            "date/time."
        ),
    )

    parser.add_argument(
        "--updated-before",
        type=_parse_datetime,
        metavar="DATETIME",
        help=(
            "Companies updated before this ISO-8601 "
            "date/time."
        ),
    )

    # ---------------------------------------------------------
    # WebArtsy enrichment timestamps
    # ---------------------------------------------------------

    parser.add_argument(
        "--enriched-after",
        type=_parse_datetime,
        metavar="DATETIME",
        help=(
            "Companies whose latest completed WebArtsy "
            "stage is on or after this date/time."
        ),
    )

    parser.add_argument(
        "--enriched-before",
        type=_parse_datetime,
        metavar="DATETIME",
        help=(
            "Companies whose latest completed WebArtsy "
            "stage is before this date/time."
        ),
    )

    # ---------------------------------------------------------
    # Website / people
    # ---------------------------------------------------------

    parser.add_argument(
        "--has-website",
        action="store_true",
        help=(
            "Only export companies with a website."
        ),
    )

    parser.add_argument(
        "--has-people",
        action="store_true",
        help=(
            "Only export companies with at least one "
            "persisted person."
        ),
    )

    parser.add_argument(
        "--has-decision-maker",
        action="store_true",
        help=(
            "Only export companies with at least one "
            "primary or secondary decision maker."
        ),
    )

    # ---------------------------------------------------------
    # Website performance
    # ---------------------------------------------------------

    parser.add_argument(
        "--has-performance",
        action="store_true",
        help=(
            "Only export companies with website "
            "performance data."
        ),
    )

    parser.add_argument(
        "--min-performance",
        type=_score,
        metavar="0-100",
        help=(
            "Minimum latest website performance score."
        ),
    )

    parser.add_argument(
        "--max-performance",
        type=_score,
        metavar="0-100",
        help=(
            "Maximum latest website performance score."
        ),
    )

    parser.add_argument(
        "--min-seo",
        type=_score,
        metavar="0-100",
        help=(
            "Minimum latest SEO score."
        ),
    )

    parser.add_argument(
        "--max-seo",
        type=_score,
        metavar="0-100",
        help=(
            "Maximum latest SEO score."
        ),
    )

    # ---------------------------------------------------------
    # Contact information
    # ---------------------------------------------------------

    parser.add_argument(
        "--has-email",
        action="store_true",
        help=(
            "Only export companies with at least one email."
        ),
    )

    parser.add_argument(
        "--has-phone",
        action="store_true",
        help=(
            "Only export companies with at least one phone."
        ),
    )

    # ---------------------------------------------------------
    # LinkedIn
    # ---------------------------------------------------------

    parser.add_argument(
        "--has-linkedin",
        action="store_true",
        help=(
            "Only export companies with either a company "
            "LinkedIn or a person's LinkedIn."
        ),
    )

    parser.add_argument(
        "--has-company-linkedin",
        action="store_true",
        help=(
            "Only export companies with a company "
            "LinkedIn URL."
        ),
    )

    parser.add_argument(
        "--has-person-linkedin",
        action="store_true",
        help=(
            "Only export companies with at least one "
            "person LinkedIn URL."
        ),
    )

    return parser


async def run(
    args: argparse.Namespace,
) -> None:
    filters = WebArtsyExportFilters(
        country=args.country,
        city=args.city,
        category=args.category,

        created_after=args.created_after,
        created_before=args.created_before,

        updated_after=args.updated_after,
        updated_before=args.updated_before,

        enriched_after=args.enriched_after,
        enriched_before=args.enriched_before,

        has_website=args.has_website,

        has_people=args.has_people,
        has_decision_maker=args.has_decision_maker,

        has_performance=args.has_performance,

        min_performance=args.min_performance,
        max_performance=args.max_performance,

        min_seo=args.min_seo,
        max_seo=args.max_seo,

        has_email=args.has_email,
        has_phone=args.has_phone,

        has_linkedin=args.has_linkedin,
        has_company_linkedin=(
            args.has_company_linkedin
        ),
        has_person_linkedin=(
            args.has_person_linkedin
        ),

        limit=args.limit,
    )

    async with SessionFactory() as session:
        export_path = await export_webartsy_leads(
            session=session,
            output_dir=args.export_dir,
            filters=filters,
        )

    print(
        f"CSV export: {export_path}"
    )
